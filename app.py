"""ProcuraAI Streamlit dashboard.  Run:  streamlit run app.py

Two back-ends: (1) the in-process audit package (default) or (2) a running FastAPI service (set the API URL in the sidebar).
The Gemini API key is read server-side from the environment only; it is never rendered or sent to the browser.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from procuraai.agents.graph import run_audit  # noqa: E402
from procuraai.config import Settings  # noqa: E402
from procuraai.reporting.builder import findings_df, invoices_df, to_excel_bytes, to_markdown  # noqa: E402
from procuraai.schemas import InvoiceAuditResult  # noqa: E402
from procuraai.services import load_services  # noqa: E402

st.set_page_config(page_title="ProcuraAI Auditor", layout="wide")
st.title("ProcuraAI - Invoice & Procurement Compliance Auditor")
st.caption("Prototype on SYNTHETIC data. Findings are decision support; every payment decision stays with a human.")

settings = Settings()
with st.sidebar:
    st.header("Setup")
    data_dir = st.text_input("Dataset folder (master data + contracts/policies)", os.environ.get("PROCURAAI_DATA_DIR", "procuraai-data"))
    backend = st.radio("Back-end", ["In-process package", "FastAPI service"], index=0)
    api_url = st.text_input("API base URL", "http://127.0.0.1:8000") if backend == "FastAPI service" else None
    api_key = st.text_input("API key for the service (optional)", type="password") if backend == "FastAPI service" else None
    extraction_mode = st.selectbox("Extraction mode", ["rule", "auto", "llm"], help="'rule' works offline. 'auto'/'llm' use Gemini when GEMINI_API_KEY is set on the server, otherwise fall back and say so.")
    explain = st.checkbox("LLM explanations (needs Gemini key)", value=False)
    st.write("Gemini key configured on this server:", "yes" if settings.gemini_api_key else "no")
    if st.button("Test Gemini connection") :
        from procuraai.extraction.llm import GeminiClient
        ok, msg = GeminiClient(settings.gemini_api_key, settings.gemini_model, 30, 1).ping()
        (st.success if ok else st.error)(msg)
    st.caption(f"Upload limit per file: {settings.max_upload_mb} MB (env PROCURAAI_MAX_UPLOAD_MB; Streamlit's own limit is in .streamlit/config.toml)")


@st.cache_resource(show_spinner="Loading master data and building the knowledge base...")
def get_services(d: str):
    return load_services(d)


tab_up, tab_sum, tab_find, tab_ev, tab_prev, tab_dl = st.tabs(["1 Upload & run", "2 Summary", "3 Findings", "4 Evidence", "5 Document preview", "6 Downloads"])

with tab_up:
    files = st.file_uploader("Upload invoices, purchase orders, delivery challans (PDF, PNG/JPG, TXT, ZIP)", accept_multiple_files=True, type=["pdf", "png", "jpg", "jpeg", "txt", "md", "zip", "csv"])
    c1, c2 = st.columns(2)
    run_upload = c1.button("Run audit on uploaded files", type="primary", disabled=not files)
    run_sample = c2.button("Run audit on the sample dataset (structured tables)")
    if run_upload or run_sample:
        try:
            with st.status("Running audit...", expanded=True) as status:
                if backend == "In-process package":
                    svc = get_services(data_dir)
                    st.write(" | ".join(svc.notes))
                    out = tempfile.mkdtemp()
                    if run_upload:
                        paths = []
                        for f in files:
                            p = Path(out) / Path(f.name).name
                            p.write_bytes(f.getvalue()); paths.append(str(p))
                        state = run_audit(svc, "documents", paths=paths, extraction_mode=extraction_mode, outdir=out, workdir=out + "/unz", use_llm_explanations=explain)
                    else:
                        state = run_audit(svc, "structured", structured_dir=str(Path(data_dir) / "structured"), outdir=out, use_llm_explanations=explain)
                    st.session_state["report"], st.session_state["files"] = state.get("report"), state.get("output_files", {})
                    st.session_state["uploads"] = {f.name: f.getvalue() for f in (files or [])}
                    for e in state.get("errors", []) + [x["error"] for x in state.get("ingestion_errors", [])]:
                        st.warning(e)
                    status.update(label=f"Audit {state['audit_id']}: {state['status']}", state="complete")
                else:
                    import httpx
                    h = {"X-API-Key": api_key} if api_key else {}
                    ids = []
                    if run_upload:
                        r = httpx.post(f"{api_url}/documents/upload", files=[("files", (f.name, f.getvalue())) for f in files], headers=h, timeout=120)
                        r.raise_for_status(); ids = [d["document_id"] for d in r.json()["documents"]]
                    r = httpx.post(f"{api_url}/audits", json=dict(input_mode="documents" if run_upload else "structured", document_ids=ids, extraction_mode=extraction_mode, use_llm_explanations=explain), headers=h, timeout=60)
                    r.raise_for_status(); aid = r.json()["audit_id"]
                    for _ in range(300):
                        s = httpx.get(f"{api_url}/audits/{aid}", headers=h, timeout=30).json()
                        st.write(f"status: {s['status']}")
                        if s["status"] not in ("queued", "running"):
                            break
                        time.sleep(2)
                    rep = httpx.get(f"{api_url}/audits/{aid}/report", headers=h, timeout=60)
                    rep.raise_for_status(); st.session_state["report"] = rep.json(); st.session_state["files"] = {}
                    status.update(label=f"Audit {aid}: {s['status']}", state="complete")
        except Exception as e:  # noqa: BLE001
            st.error(f"Audit could not run: {type(e).__name__}: {e}")

def show_llm_problems(report):
    log_ = (report or {}).get("metadata", {}).get("extraction_log", [])
    for e in log_:
        if e.get("llm_fallback"):
            st.warning(f"{e['file']}: {e['llm_fallback']}")
    for n in (report or {}).get("metadata", {}).get("llm_notes", []):
        st.warning(n)


rep = st.session_state.get("report")
results = [InvoiceAuditResult.model_validate(i) for i in rep["invoices"]] if rep else []

with tab_up:
    show_llm_problems(st.session_state.get("report"))

with tab_sum:
    if not rep:
        st.info("Run an audit first.")
    else:
        s = rep["summary"]
        c = st.columns(5)
        c[0].metric("Invoices", s["invoices_processed"]); c[1].metric("Passed", s["invoices_passed"]); c[2].metric("Flagged", s["invoices_flagged"])
        c[3].metric("Manual review only", s["invoices_manual_review"]); c[4].metric("Human review pending", s["human_review_pending"])
        c = st.columns(3)
        c[0].metric("Exposure - confirmed (PKR)", f"{float(s['estimated_exposure_confirmed']):,.0f}"); c[1].metric("Exposure - potential (PKR)", f"{float(s['estimated_exposure_potential']):,.0f}")
        c[2].metric("Low-confidence extractions", s["low_confidence_extractions"])
        st.caption(s["exposure_note"])
        st.bar_chart(pd.Series(s["findings_by_code"], name="findings"))
        st.dataframe(invoices_df(results), width="stretch")
        with st.expander("Processing details"):
            st.json({k: v for k, v in rep["metadata"].items() if k != "extraction_log"})
            st.dataframe(pd.DataFrame(rep["metadata"].get("extraction_log", [])).astype(str), width="stretch")

with tab_find:
    if results:
        df = findings_df(results, include_passed=False)
        if df.empty:
            st.success("No findings.")
        else:
            c = st.columns(3)
            sev = c[0].multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            stt = c[1].multiselect("Status", sorted(df.status.unique()), default=sorted(df.status.unique()))
            code = c[2].multiselect("Type", sorted(df.code.unique()))
            f = df[df.severity.isin(sev) & df.status.isin(stt) & (df.code.isin(code) if code else True)]
            st.dataframe(f[["invoice_id", "supplier", "code", "status", "severity", "line_no", "expected", "observed", "difference", "exposure", "needs_human_review", "message"]], width="stretch")
        st.subheader("Human-review queue")
        st.dataframe(pd.DataFrame(rep["review_queue"]).astype(str), width="stretch")
    else:
        st.info("Run an audit first.")

with tab_ev:
    if results:
        rows = [(r, f) for r in results for f in r.findings if f.status != "PASSED"]
        labels = [f"{r.invoice_number} | {f.code} | {f.status}" for r, f in rows]
        if labels:
            i = labels.index(st.selectbox("Finding", labels))
            r, f = rows[i]
            st.write(f.explanation)
            st.caption(f"Explanation source: {f.explanation_source}. Expected: {f.expected} | Observed: {f.observed} | Exposure: {f.exposure_amount}")
            if f.evidence:
                for e in f.evidence:
                    st.markdown(f"**{e.source_file}** - {e.section or ''} (score {e.score})")
                    st.code(e.snippet)
                    p = Path(data_dir) / "raw" / ("contracts" if e.doc_type == "CONTRACT" else "policies") / e.source_file
                    if p.exists():
                        with st.expander("Open the full source document"):
                            st.text(p.read_text(encoding="utf-8", errors="replace")[:6000])
            else:
                st.warning("No supporting passage found in the knowledge base for this finding.")
    else:
        st.info("Run an audit first.")

with tab_prev:
    ups = st.session_state.get("uploads", {})
    if ups:
        name = st.selectbox("Uploaded document", list(ups))
        data = ups[name]
        if name.lower().endswith(".pdf"):
            import pymupdf
            d = pymupdf.open(stream=data, filetype="pdf")
            st.image(d[0].get_pixmap(dpi=90).tobytes("png"), caption=f"{name} (page 1 of {d.page_count})")
        elif name.lower().endswith((".png", ".jpg", ".jpeg")):
            st.image(data, caption=name)
        elif name.lower().endswith((".txt", ".md", ".csv")):
            st.text(data.decode("utf-8", "replace")[:4000])
    else:
        st.info("Upload documents to preview them (previews are not available for the sample-dataset run).")

with tab_dl:
    if rep:
        st.download_button("Report (JSON)", json.dumps(rep, indent=2, default=str), f"{rep['audit_id']}.json", "application/json")
        st.download_button("Report (Markdown)", to_markdown(rep, results), f"{rep['audit_id']}.md", "text/markdown")
        st.download_button("Findings (CSV)", findings_df(results).to_csv(index=False), f"{rep['audit_id']}_findings.csv", "text/csv")
        st.download_button("Report (Excel)", to_excel_bytes(rep, results), f"{rep['audit_id']}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Run an audit first.")
