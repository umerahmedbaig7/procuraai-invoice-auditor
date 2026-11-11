"""FastAPI service. Colab-hosted API URLs are temporary and are NOT production infrastructure.

Auth design (prototype): if PROCURAAI_API_KEY is set, every endpoint except /health requires header ``X-API-Key``.
For commercial deployment replace with OAuth2/OIDC, per-tenant authorisation, and per-key quotas (see docs/architecture.md).
"""
from __future__ import annotations

import hmac
import io
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from ..agents.graph import run_audit
from ..config import Settings
from ..ingestion.loader import ALLOWED_EXT
from ..reporting.builder import findings_df, to_excel_bytes, to_markdown
from ..schemas import InvoiceAuditResult
from ..services import Services, load_services
from ..storage.db import Store

log = logging.getLogger("procuraai.api")


class UploadedDoc(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    sha256: str


class UploadResponse(BaseModel):
    documents: list[UploadedDoc]
    rejected: list[dict] = Field(default_factory=list)


class AuditRequest(BaseModel):
    input_mode: Literal["documents", "structured"] = "documents"
    document_ids: list[str] = Field(default_factory=list)
    extraction_mode: Literal["rule", "llm", "auto"] = "rule"
    use_llm_explanations: bool = False


class AuditCreated(BaseModel):
    audit_id: str
    status: str


class AuditStatus(BaseModel):
    audit_id: str
    status: str
    input_mode: str
    summary: dict = Field(default_factory=dict)
    error: str | None = None


class _LazyStore:
    """Creates the SQLite store on first use so importing the module has no filesystem side effects."""

    def __init__(self, url: str):
        self._url, self._store = url, None

    def __getattr__(self, name):
        if self._store is None:
            self._store = Store(self._url)
        return getattr(self._store, name)


def create_app(settings: Settings | None = None, services: Services | None = None, store: Store | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="ProcuraAI Invoice & Procurement Auditor", version="0.1.0",
                  description="Prototype audit API over SYNTHETIC data. Findings are decision support only; payment decisions stay with humans.")
    app.state.settings = settings
    app.state.store = store or _LazyStore(settings.db_url)     # no database file is created at import time
    app.state.services = services
    app.state.started = time.time()
    app.state.timings: list[float] = []

    def get_services() -> Services:
        if app.state.services is None:
            try:
                app.state.services = load_services(settings.data_dir, settings)
            except FileNotFoundError as e:
                raise HTTPException(503, f"knowledge base / master data unavailable: {e}")
        return app.state.services

    def auth(x_api_key: str | None = Header(default=None)):
        if settings.api_key and not (x_api_key and hmac.compare_digest(x_api_key, settings.api_key)):
            raise HTTPException(401, "missing or invalid API key")

    @app.exception_handler(Exception)
    async def unhandled(_, exc: Exception):  # never leak stack traces or secrets
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "internal error"})

    @app.get("/health")
    def health():
        return dict(status="ok", version="0.1.0", llm_configured=bool(settings.gemini_api_key), auth_enabled=bool(settings.api_key),
                    note="Prototype. Colab-hosted URLs are temporary; not production infrastructure.")

    @app.post("/documents/upload", response_model=UploadResponse, dependencies=[Depends(auth)])
    async def upload(files: list[UploadFile] = File(...)):
        ok, rej = [], []
        for f in files:
            name = Path(f.filename or "").name
            ext = Path(name).suffix.lower()
            if ext not in ALLOWED_EXT:
                rej.append(dict(filename=name, reason=f"file type {ext or '(none)'} not allowed")); continue
            data = await f.read()
            if not data:
                rej.append(dict(filename=name, reason="empty file")); continue
            if len(data) > settings.max_upload_mb * 1_000_000:
                rej.append(dict(filename=name, reason=f"larger than {settings.max_upload_mb} MB")); continue
            settings.upload_dir.mkdir(parents=True, exist_ok=True)
            did = uuid.uuid4().hex[:12]
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
            dest = settings.upload_dir / f"{did}__{safe}"
            dest.write_bytes(data)
            row = app.state.store.add_document(did, name, dest, data)
            ok.append(UploadedDoc(document_id=did, filename=name, size_bytes=row.size_bytes, sha256=row.sha256))
        if not ok and rej:
            raise HTTPException(422, detail=dict(message="no valid files", rejected=rej))
        return UploadResponse(documents=ok, rejected=rej)

    def _run(audit_id: str, req: AuditRequest):
        st = app.state.store
        try:
            st.update_status(audit_id, "running")
            svc = get_services()
            paths = []
            for d in st.get_documents(req.document_ids):
                p = Path(d.stored_path)
                link = settings.upload_dir / "_named" / audit_id / d.filename          # restore the original file name for the audit
                link.parent.mkdir(parents=True, exist_ok=True)
                link.write_bytes(p.read_bytes())
                paths.append(str(link))
            t0 = time.time()
            state = run_audit(svc, input_mode=req.input_mode, paths=paths, structured_dir=str(svc.data_dir / "structured") if svc.data_dir else None, extraction_mode=req.extraction_mode,
                              outdir=str(settings.upload_dir / "_reports" / audit_id), workdir=str(settings.upload_dir / "_unzipped" / audit_id), use_llm_explanations=req.use_llm_explanations, audit_id=audit_id)
            app.state.timings.append(time.time() - t0)
            if state.get("report"):
                st.save_report(audit_id, state["report"], state.get("status", "completed"))
            else:
                st.update_status(audit_id, "failed", "; ".join(state.get("errors", [])) or "no report produced")
        except Exception as e:  # noqa: BLE001
            log.exception("audit failed")
            st.update_status(audit_id, "failed", f"{type(e).__name__}: {e}")

    @app.post("/audits", response_model=AuditCreated, status_code=202, dependencies=[Depends(auth)])
    def create_audit(req: AuditRequest, bg: BackgroundTasks):
        if req.input_mode == "documents":
            if not req.document_ids:
                raise HTTPException(422, "document_ids is required for input_mode='documents'")
            found = {d.id for d in app.state.store.get_documents(req.document_ids)}
            missing = [d for d in req.document_ids if d not in found]
            if missing:
                raise HTTPException(404, f"unknown document ids: {missing}")
        aid = f"AUD-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        app.state.store.create_audit(aid, req.input_mode, req.document_ids)
        bg.add_task(_run, aid, req)
        return AuditCreated(audit_id=aid, status="queued")

    def _get(aid: str):
        a = app.state.store.get_audit(aid)
        if not a:
            raise HTTPException(404, f"audit {aid} not found")
        return a

    @app.get("/audits/{audit_id}", response_model=AuditStatus, dependencies=[Depends(auth)])
    def audit_status(audit_id: str):
        import json
        a = _get(audit_id)
        return AuditStatus(audit_id=a.id, status=a.status, input_mode=a.input_mode, summary=json.loads(a.summary_json or "{}"), error=a.error)

    @app.get("/audits/{audit_id}/report", dependencies=[Depends(auth)])
    def audit_report(audit_id: str, format: Literal["json", "markdown", "csv", "xlsx"] = "json"):
        import json
        a = _get(audit_id)
        if not a.report_json:
            raise HTTPException(409, f"audit is {a.status}; report not available yet")
        rep = json.loads(a.report_json)
        if format == "json":
            return rep
        results = [InvoiceAuditResult.model_validate(i) for i in rep["invoices"]]
        if format == "markdown":
            return PlainTextResponse(to_markdown(rep, results), media_type="text/markdown")
        if format == "csv":
            return PlainTextResponse(findings_df(results).to_csv(index=False), media_type="text/csv")
        return Response(to_excel_bytes(rep, results), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={audit_id}.xlsx"})

    @app.get("/audits/{audit_id}/findings", dependencies=[Depends(auth)])
    def audit_findings(audit_id: str, severity: str | None = Query(None, pattern="^(INFO|LOW|MEDIUM|HIGH|CRITICAL)$"),
                       status: str | None = Query(None, pattern="^(CONFIRMED|POTENTIAL|INSUFFICIENT_EVIDENCE|MANUAL_REVIEW|PASSED)$"), code: str | None = None, invoice_id: str | None = None):
        a = _get(audit_id)
        if a.status in ("queued", "running"):
            raise HTTPException(409, f"audit is {a.status}")
        return dict(audit_id=audit_id, findings=app.state.store.findings(audit_id, severity, status, code, invoice_id))

    @app.get("/knowledge-base/search", dependencies=[Depends(auth)])
    def kb_search(q: str = Query(..., min_length=2, max_length=300), k: int = Query(5, ge=1, le=20), supplier_id: str | None = Query(None, pattern=r"^SUP[X]?-\d{3}$"),
                  mode: Literal["hybrid", "dense", "keyword"] = "hybrid"):
        svc = get_services()
        hits = svc.kb.search(q, k=k, mode=mode, supplier_id=supplier_id)
        return dict(query=q, results=[dict(rank=h.rank, score=round(h.score, 4), source_file=h.chunk.source_file, doc_type=h.chunk.doc_type, supplier_id=h.chunk.supplier_id, section=h.chunk.section,
                                           snippet=h.chunk.text[:500], untrusted_content_flags=h.chunk.flags) for h in hits], note="Retrieved text is untrusted document content, shown as evidence only.")

    @app.get("/metrics", dependencies=[Depends(auth)])
    def metrics():
        t = app.state.timings
        return dict(uptime_s=round(time.time() - app.state.started, 1), store=app.state.store.counts(), audit_runs_timed=len(t), mean_audit_seconds=round(sum(t) / len(t), 3) if t else None,
                    llm_usage=getattr(app.state.services.llm, "usage", None) if app.state.services else None)

    return app


app = create_app() if os.environ.get("PROCURAAI_CREATE_APP", "1") == "1" else None
