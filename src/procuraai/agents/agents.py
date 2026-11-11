"""The four agent stages. Each is a plain, testable class with an explicit input/output contract on ``AuditState``.

Agent 1 DocumentIntelligenceAgent   in: paths | structured tables   out: invoices, pos, dcs, extraction_log, ingestion_errors, normalization
Agent 2 ProcurementEvidenceAgent    in: invoices, pos             out: evidence_context, evidence_fn (RAG, citations)
Agent 3 ReconciliationAuditAgent    in: invoices, pos, dcs        out: results (deterministic findings)
Agent 4 ReportingReviewAgent        in: results                   out: report, review_queue, output_files

LLM use is limited to extraction (Agent 1, optional) and explanations (Agent 4, optional). Everything else is deterministic.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd

from .. import taxonomy as T
from ..audit.engine import AuditEngine, DocumentStore
from ..config import Settings
from ..extraction.llm import LLMError, LLMUnavailable, explain_finding, extract_invoice_with_llm
from ..extraction.pipeline import extract_file
from ..extraction.rule_based import extract_document
from ..extraction.structured import load_structured_dir
from ..ingestion.loader import ExtractedDocument, IngestionError, ingest_paths, load_file, safe_extract_zip, validate_upload
from ..rag.evidence import make_evidence_fn
from ..reporting.builder import build_report, template_explanation, write_reports
from ..schemas import DeliveryChallanRecord, InvoiceAuditResult, InvoiceRecord, PurchaseOrderRecord
from ..services import Services

log = logging.getLogger("procuraai.agents")


class AuditState(TypedDict, total=False):
    audit_id: str
    input_mode: str                      # "documents" | "structured"
    extraction_mode: str                 # "rule" | "llm" | "auto"
    paths: list[str]
    structured_dir: str
    workdir: str
    outdir: str
    use_llm_explanations: bool
    invoices: list[InvoiceRecord]
    pos: list[PurchaseOrderRecord]
    dcs: list[DeliveryChallanRecord]
    extraction_log: list[dict]
    ingestion_errors: list[dict]
    normalization: dict
    evidence_context: dict
    evidence_fn: Any
    results: list[InvoiceAuditResult]
    report: dict
    review_queue: list[dict]
    output_files: dict
    errors: list[str]
    status: str
    timings: dict


# ---------------------------------------------------------------------------------------------
class DocumentIntelligenceAgent:
    name = "document_intelligence"

    def __init__(self, svc: Services):
        self.svc = svc

    def _extract_one(self, path: Path, mode: str, log_: list[dict]):
        t0 = time.time()
        entry = dict(file=path.name, requested_mode=mode, llm_fallback=None)
        try:
            if mode in ("llm", "auto") and path.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md"):
                doc = load_file(path, ocr=True)
                if doc.doc_type == "INVOICE" and self.svc.llm_available:
                    try:
                        rec = extract_invoice_with_llm(self.svc.llm, doc.text, path.name)
                        rec.page_count = len(doc.pages)
                        entry.update(doc_type="INVOICE", method="llm", confidence=rec.extraction_confidence)
                        return rec, entry, t0
                    except (LLMError, LLMUnavailable) as e:       # never pretend the LLM succeeded
                        entry["llm_fallback"] = f"{type(e).__name__}: {e}"
                elif doc.doc_type == "INVOICE":
                    entry["llm_fallback"] = "LLM not configured; rule-based extraction used" if mode == "auto" else "LLM requested but unavailable; rule-based extraction used"
            doc, rec = extract_file(path)
            entry.update(doc_type=doc.doc_type, method=rec.extraction_method if rec else "none", confidence=rec.extraction_confidence if rec else 0.0, text_method=doc.method)
            if rec is None:
                entry["note"] = f"document type {doc.doc_type} is not an invoice/PO/DC; skipped for reconciliation"
            return rec, entry, t0
        except Exception as e:  # noqa: BLE001
            entry.update(error=f"{type(e).__name__}: {e}")
            return None, entry, t0

    def run(self, state: AuditState) -> dict:
        t0 = time.time()
        errors: list[dict] = []
        extraction_log: list[dict] = []
        invoices: list[InvoiceRecord] = []
        pos: list[PurchaseOrderRecord] = []
        dcs: list[DeliveryChallanRecord] = []
        if state.get("input_mode") == "structured":
            S = load_structured_dir(state["structured_dir"])
            reg_path = Path(state["structured_dir"]) / "document_registry.csv"
            if reg_path.exists():
                reg = pd.read_csv(reg_path)
                rec = {r.source_file: pd.to_datetime(r.received_at).to_pydatetime() for r in reg.itertuples()}
                for i in S["invoices"]:
                    i.received_at = rec.get(i.source_file)
            invoices, pos, dcs = S["invoices"], S["purchase_orders"], S["delivery_challans"]
            extraction_log = [dict(file=i.source_file, doc_type="INVOICE", method="csv", confidence=1.0) for i in invoices]
        else:
            work = Path(state.get("workdir") or "processed/unzipped")
            flat: list[Path] = []
            for p in map(Path, state.get("paths", [])):
                try:
                    validate_upload(p, Settings().max_upload_mb)
                    flat += safe_extract_zip(p, work / p.stem) if p.suffix.lower() == ".zip" else [p]
                except (IngestionError, OSError) as e:
                    errors.append(dict(file=p.name, error=str(e)))
            registry = {}
            for p in flat:
                if p.name == "document_registry.csv":
                    registry = {r.source_file: pd.to_datetime(r.received_at).to_pydatetime() for r in pd.read_csv(p).itertuples()}
            for i, p in enumerate(flat):
                if p.suffix.lower() in (".csv", ".xlsx"):
                    continue                      # tabular files are master/reference data, not documents to audit
                rec, entry, t1 = self._extract_one(p, state.get("extraction_mode", "rule"), extraction_log)
                entry["seconds"] = round(time.time() - t1, 3)
                extraction_log.append(entry)
                if "error" in entry:
                    errors.append(dict(file=p.name, error=entry["error"]))
                    continue
                if rec is None:
                    continue
                if rec.doc_type == "INVOICE":
                    rec.received_at = registry.get(p.name) or datetime.fromtimestamp(p.stat().st_mtime)
                    invoices.append(rec)
                elif rec.doc_type == "PURCHASE_ORDER":
                    pos.append(rec)
                elif rec.doc_type == "DELIVERY_CHALLAN":
                    dcs.append(rec)
        # normalization trace (supplier / product matches with original + normalized values)
        from ..normalization import ProductMatcher, SupplierMatcher
        sm, pm = SupplierMatcher(self.svc.master.suppliers, self.svc.cfg), ProductMatcher(self.svc.master.products, self.svc.cfg)
        norm = {}
        for inv in invoices:
            norm[inv.invoice_id] = dict(supplier=sm.match(inv.supplier_name, inv.supplier_tax_id).model_dump(), products=[pm.match(l.product_code, l.description).model_dump() for l in inv.lines],
                                        missing_fields=inv.missing_fields)
        tm = dict(state.get("timings", {}))
        tm["document_intelligence_s"] = round(time.time() - t0, 3)
        return dict(invoices=invoices, pos=pos, dcs=dcs, extraction_log=extraction_log, ingestion_errors=errors, normalization=norm, timings=tm)


class ProcurementEvidenceAgent:
    name = "procurement_evidence"

    def __init__(self, svc: Services):
        self.svc = svc

    def run(self, state: AuditState) -> dict:
        t0 = time.time()
        m, kb = self.svc.master, self.svc.kb
        pos = {p.po_number: p for p in state.get("pos", []) if p.po_number}
        ctx = {}
        from ..normalization import SupplierMatcher
        sm = SupplierMatcher(m.suppliers, self.svc.cfg)
        for inv in state.get("invoices", []):
            mr = sm.match(inv.supplier_name, inv.supplier_tax_id)
            po = pos.get(inv.po_number or "")
            ref = (po.po_date if po and po.po_date else inv.invoice_date)
            ag = m.agreement_for(mr.matched_id, ref) if (mr.matched_id and ref) else None
            ctx[inv.invoice_id] = dict(supplier_id=mr.matched_id, reference_date=str(ref) if ref else None, reference_basis="PO date" if po and po.po_date else "invoice date",
                                       agreement_id=ag.agreement_id if ag else None, effective=f"{ag.effective_from}..{ag.effective_to}" if ag else None,
                                       freight_policy=ag.freight_policy if ag else None, volume_discount=f"{ag.volume_discount_pct}% from {ag.volume_discount_min_qty}" if ag else None,
                                       policy_passages=[e.model_dump() for code in ("QTY_EXCEEDS_ORDERED", "TAX_CALC_ERROR") for e in kb.evidence_for(code, None)[:1]])
        tm = dict(state.get("timings", {}))
        tm["procurement_evidence_s"] = round(time.time() - t0, 3)
        return dict(evidence_context=ctx, evidence_fn=make_evidence_fn(kb), timings=tm)


class ReconciliationAuditAgent:
    name = "reconciliation_audit"

    def __init__(self, svc: Services):
        self.svc = svc

    def run(self, state: AuditState) -> dict:
        t0 = time.time()
        engine = AuditEngine(self.svc.master, DocumentStore.from_lists(state.get("pos", []), state.get("dcs", [])), self.svc.cfg, evidence_fn=state.get("evidence_fn"))
        results = engine.audit_batch(state.get("invoices", []), state["audit_id"])
        tm = dict(state.get("timings", {}))
        tm["reconciliation_audit_s"] = round(time.time() - t0, 3)
        return dict(results=results, timings=tm)


class ReportingReviewAgent:
    """Consolidates findings, applies documented severity/confidence rules, routes uncertain cases to human review.

    Severity: taxonomy default per finding type, escalated by the engine for pricing (>=5% -> HIGH). Overall invoice status:
      FLAGGED (any confirmed/potential finding) > MANUAL_REVIEW (only review/insufficient-evidence items) > PASSED_WITH_NOTES (INFO only) > PASSED.
    Confidence: min(finding confidence, extraction confidence); deterministic checks on structured data = 1.0, OCR/LLM extraction < 1.0.
    """
    name = "reporting_review"

    def __init__(self, svc: Services):
        self.svc = svc

    def run(self, state: AuditState) -> dict:
        t0 = time.time()
        results: list[InvoiceAuditResult] = state.get("results", [])
        llm_errors = []
        n_llm = 0
        if state.get("use_llm_explanations") and self.svc.llm_available:
            for r in results:
                for f in r.findings:
                    if f.status == T.PASSED or n_llm >= 40:
                        continue
                    try:
                        ex = explain_finding(self.svc.llm, f.model_dump(mode="json", exclude={"evidence", "explanation"}), [e.model_dump() for e in f.evidence])
                        f.explanation, f.explanation_source = f"{ex.explanation} Next step: {ex.next_step}", "llm"
                        n_llm += 1
                    except (LLMError, LLMUnavailable) as e:
                        llm_errors.append(f"{f.finding_id}: {e}")
                        break
        elif state.get("use_llm_explanations"):
            llm_errors.append("LLM explanations requested but no LLM is configured; template explanations used")
        for r in results:
            for f in r.findings:
                if not f.explanation:
                    f.explanation, f.explanation_source = template_explanation(f), "template"
        queue = state.get("review_queue") or [dict(invoice_id=r.invoice_id, invoice_number=r.invoice_number, supplier=r.supplier_name, status=r.overall_status, reasons=r.unresolved_questions[:6])
                                              for r in results if r.human_review_status == "PENDING"]
        tm = dict(state.get("timings", {}))
        tm["reporting_review_s"] = round(time.time() - t0, 3)
        meta = dict(input_mode=state.get("input_mode"), extraction_mode=state.get("extraction_mode"), extraction_log=state.get("extraction_log", []), ingestion_errors=state.get("ingestion_errors", []),
                    pipeline_errors=state.get("errors", []), llm_usage=getattr(self.svc.llm, "usage", None), llm_explanations_written=n_llm, llm_notes=llm_errors, service_notes=self.svc.notes, timings=tm,
                    documents={"invoices": len(state.get("invoices", [])), "purchase_orders": len(state.get("pos", [])), "delivery_challans": len(state.get("dcs", []))})
        report = build_report(state["audit_id"], results, meta)
        report["review_queue"] = queue
        files = write_reports(state["outdir"], report, results) if state.get("outdir") else {}
        return dict(report=report, review_queue=queue, output_files=files, timings=tm, status="completed" if not state.get("errors") else "completed_with_errors")
