"""Report generation: JSON, Markdown, CSV and Excel. Exposure is de-duplicated per (invoice, exposure_key)."""
from __future__ import annotations

import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .. import taxonomy as T
from ..audit.money import ZERO
from ..schemas import AuditFinding, InvoiceAuditResult

DISCLAIMER = ("Findings are produced by deterministic rules over supplied documents. 'Confirmed' means a rule or arithmetic check failed against the supplied evidence; it is not a legal finding. "
              "Nothing here accuses a supplier of fraud. Estimated exposure is the disputed amount implied by the findings, not a confirmed recoverable saving. "
              "All payment decisions remain with authorised finance staff.")

TEMPLATE_STYLE = {
    T.CONFIRMED: "Confirmed discrepancy",
    T.POTENTIAL: "Potential anomaly",
    T.MANUAL_REVIEW: "Manual review required",
    T.INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    T.PASSED: "Note",
}


def template_explanation(f: AuditFinding) -> str:
    parts = [f"{TEMPLATE_STYLE.get(f.status, f.status)}: {f.message}"]
    if f.expected is not None and f.observed is not None:
        parts.append(f"Expected {f.expected}, observed {f.observed}" + (f" (difference {f.difference})." if f.difference is not None else "."))
    if f.evidence:
        e = f.evidence[0]
        parts.append(f"Supporting source: {e.source_file}" + (f", {e.section}" if e.section else "") + ".")
    else:
        parts.append("No supporting contract/policy passage was found in the knowledge base." if f.status != T.PASSED else "")
    return " ".join(p for p in parts if p)


def exposure_split(results: list[InvoiceAuditResult]) -> tuple[Decimal, Decimal]:
    """(confirmed, potential) exposure with each exposure_key counted once per invoice."""
    conf = pot = ZERO
    for r in results:
        by_key: dict[str, list[AuditFinding]] = defaultdict(list)
        for f in r.findings:
            if f.exposure_key and f.status in (T.CONFIRMED, T.POTENTIAL):
                by_key[f.exposure_key].append(f)
        for fs in by_key.values():
            amt = max(f.exposure_amount for f in fs)
            if any(f.status == T.CONFIRMED for f in fs):
                conf += amt
            else:
                pot += amt
    return conf, pot


def summarize(results: list[InvoiceAuditResult]) -> dict:
    st = Counter(r.overall_status for r in results)
    codes: Counter = Counter()
    cats: Counter = Counter()
    sev: Counter = Counter()
    for r in results:
        for f in r.findings:
            if f.status == T.PASSED or f.code == "EXTRACTION_LOW_CONFIDENCE":
                continue
            codes[f.code] += 1
            cats[T.CODES[f.code].category] += 1
            sev[f.severity] += 1
    conf, pot = exposure_split(results)
    return dict(invoices_processed=len(results), invoices_passed=st["PASSED"] + st["PASSED_WITH_NOTES"], invoices_passed_clean=st["PASSED"], invoices_passed_with_notes=st["PASSED_WITH_NOTES"],
                invoices_flagged=st["FLAGGED"], invoices_manual_review=st["MANUAL_REVIEW"], human_review_pending=sum(1 for r in results if r.human_review_status == "PENDING"),
                low_confidence_extractions=sum(1 for r in results if r.extraction_confidence < 0.75),
                findings_by_code=dict(codes.most_common()), findings_by_category=dict(cats.most_common()), findings_by_severity=dict(sev),
                estimated_exposure_confirmed=str(conf), estimated_exposure_potential=str(pot), estimated_exposure_total=str(conf + pot),
                exposure_note="Each exposure item is counted once per invoice; tax knock-on is included; amounts are disputed amounts, not confirmed recoveries.")


def build_report(audit_id: str, results: list[InvoiceAuditResult], meta: dict | None = None) -> dict:
    meta = meta or {}
    return dict(audit_id=audit_id, generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), disclaimer=DISCLAIMER, metadata=meta, summary=summarize(results),
                review_queue=[dict(invoice_id=r.invoice_id, invoice_number=r.invoice_number, supplier=r.supplier_name, status=r.overall_status, reasons=r.unresolved_questions[:6]) for r in results if r.human_review_status == "PENDING"],
                invoices=[json.loads(r.model_dump_json()) for r in results])


def findings_df(results: list[InvoiceAuditResult], include_passed: bool = True) -> pd.DataFrame:
    rows = []
    for r in results:
        for f in r.findings:
            if not include_passed and f.status == T.PASSED:
                continue
            e = f.evidence[0] if f.evidence else None
            rows.append(dict(audit_id=r.audit_id, invoice_id=r.invoice_id, invoice_number=r.invoice_number, supplier=r.supplier_name, finding_id=f.finding_id, code=f.code, status=f.status, severity=f.severity,
                             line_no=f.line_no, product_code=f.product_code, expected=f.expected, observed=f.observed, difference=f.difference, exposure=str(f.exposure_amount), exposure_key=f.exposure_key,
                             message=f.message, explanation=f.explanation or template_explanation(f), evidence_source=e.source_file if e else None, evidence_section=e.section if e else None,
                             evidence_snippet=e.snippet if e else None, needs_human_review=f.needs_human_review, confidence=f.confidence))
    return pd.DataFrame(rows)


def invoices_df(results: list[InvoiceAuditResult]) -> pd.DataFrame:
    return pd.DataFrame([dict(invoice_id=r.invoice_id, invoice_number=r.invoice_number, invoice_date=r.invoice_date, supplier_id=r.supplier_id, supplier=r.supplier_name, po=r.linked_po or r.po_number,
                              delivery_records="|".join(r.linked_dcs), currency=r.currency, grand_total=r.grand_total, status=r.overall_status, n_findings=sum(1 for f in r.findings if f.status != T.PASSED),
                              exposure=r.total_exposure, extraction_confidence=r.extraction_confidence, human_review=r.human_review_status, source_file=r.source_file) for r in results])


def to_markdown(report: dict, results: list[InvoiceAuditResult], max_findings: int = 400) -> str:
    s = report["summary"]
    L = [f"# ProcuraAI Audit Report `{report['audit_id']}`", "", f"Generated: {report['generated_at']}", "", f"> {report['disclaimer']}", "", "## Summary", "",
         f"| Metric | Value |", "|---|---|", f"| Invoices processed | {s['invoices_processed']} |", f"| Passed (clean / with notes) | {s['invoices_passed_clean']} / {s['invoices_passed_with_notes']} |",
         f"| Flagged | {s['invoices_flagged']} |", f"| Manual review only | {s['invoices_manual_review']} |", f"| Human review pending | {s['human_review_pending']} |",
         f"| Low-confidence extractions | {s['low_confidence_extractions']} |", f"| Estimated exposure - confirmed | {Decimal(s['estimated_exposure_confirmed']):,.2f} |",
         f"| Estimated exposure - potential | {Decimal(s['estimated_exposure_potential']):,.2f} |", f"| Estimated exposure - total (no double counting) | {Decimal(s['estimated_exposure_total']):,.2f} |", "",
         "## Findings by category", ""]
    L += [f"- {k}: {v}" for k, v in s["findings_by_category"].items()] or ["- none"]
    L += ["", "## Findings by type", ""] + ([f"- {k}: {v}" for k, v in s["findings_by_code"].items()] or ["- none"]) + ["", "## Invoice results", ""]
    n = 0
    for r in results:
        L.append(f"### {r.invoice_number or r.invoice_id} - {r.supplier_name or 'unknown supplier'} - **{r.overall_status}**")
        L.append(f"File `{r.source_file}` | PO {r.linked_po or r.po_number or 'n/a'} | delivery {', '.join(r.linked_dcs) or 'n/a'} | total {r.currency or ''} {r.grand_total} | extraction confidence {r.extraction_confidence:.2f} | human review: {r.human_review_status}")
        if r.total_exposure:
            L.append(f"Estimated exposure: {r.total_exposure:,.2f} (disputed amount, not a confirmed saving)")
        for f in r.findings:
            if n >= max_findings:
                break
            n += 1
            L.append(f"- **[{f.severity}] {f.code}** ({f.status}) - {f.explanation or template_explanation(f)}")
            for e in f.evidence[:1]:
                L.append(f"  - Evidence: `{e.source_file}`{' / ' + e.section if e.section else ''}: \"{e.snippet[:200].replace(chr(10), ' ')}\"")
        if r.unresolved_questions:
            L.append("- Unresolved questions: " + " | ".join(r.unresolved_questions[:4]))
        if r.recommended_actions:
            L.append("- Recommended actions: " + " | ".join(r.recommended_actions[:3]))
        L.append("")
    return "\n".join(L)


def to_excel_bytes(report: dict, results: list[InvoiceAuditResult]) -> bytes:
    from openpyxl.styles import Font, PatternFill
    buf = io.BytesIO()
    s = report["summary"]
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame([(k, json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in s.items()] + [("audit_id", report["audit_id"]), ("generated_at", report["generated_at"]), ("disclaimer", report["disclaimer"])],
                     columns=["metric", "value"]).to_excel(xw, sheet_name="Summary", index=False)
        invoices_df(results).to_excel(xw, sheet_name="Invoices", index=False)
        fd = findings_df(results)
        (fd if not fd.empty else pd.DataFrame(columns=["code"])).to_excel(xw, sheet_name="Findings", index=False)
        pd.DataFrame(report["review_queue"]).assign(reasons=lambda d: d["reasons"].map(lambda x: " | ".join(x)) if "reasons" in d else None).to_excel(xw, sheet_name="ReviewQueue", index=False) if report["review_queue"] else pd.DataFrame(columns=["invoice_id"]).to_excel(xw, sheet_name="ReviewQueue", index=False)
        for ws in xw.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3A5F")
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col[:80]) + 2))
    return buf.getvalue()


def write_reports(outdir: str | Path, report: dict, results: list[InvoiceAuditResult]) -> dict[str, str]:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    aid = report["audit_id"]
    paths = {}
    paths["json"] = out / f"audit_{aid}.json"; paths["json"].write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    paths["markdown"] = out / f"audit_{aid}.md"; paths["markdown"].write_text(to_markdown(report, results), encoding="utf-8")
    paths["findings_csv"] = out / f"audit_{aid}_findings.csv"; findings_df(results).to_csv(paths["findings_csv"], index=False)
    paths["invoices_csv"] = out / f"audit_{aid}_invoices.csv"; invoices_df(results).to_csv(paths["invoices_csv"], index=False)
    paths["excel"] = out / f"audit_{aid}.xlsx"; paths["excel"].write_bytes(to_excel_bytes(report, results))
    return {k: str(v) for k, v in paths.items()}
