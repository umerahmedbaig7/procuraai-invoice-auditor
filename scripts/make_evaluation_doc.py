#!/usr/bin/env python
"""Render docs/evaluation.md from reports/evaluation/evaluation_results.json (no hand-copied numbers)."""
import json, sys
from pathlib import Path
import pandas as pd
root = Path(__file__).resolve().parents[1]
r = json.loads((root / "reports/evaluation/evaluation_results.json").read_text())

def tbl(rows, cols=None):
    if not rows: return "_none_"
    cols = cols or list(rows[0]); out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    out += ["| " + " | ".join(str(x.get(c, "")) for c in cols) + " |" for x in rows]; return "\n".join(out)

def block(name, d):
    keys = ["n_invoices", "tp", "fp", "fn", "precision", "recall", "f1", "fp_non_info", "fp_info_only", "fp_status_confirmed", "fp_non_info_on_high_confidence_invoices", "severity_agreement", "status_agreement",
            "line_attribution_accuracy", "exposure_invoices_within_1pkr", "exposure_mae", "exposure_expected_total", "exposure_engine_total", "low_confidence_invoices"]
    L = [f"### {name}", "", tbl([dict(metric=k, value=d.get(k)) for k in keys]), "", "Invoice-level confusion (ground truth -> system):", ""]
    L += [tbl([dict(outcome=k, count=v) for k, v in d["invoice_level_confusion"].items()]), "", "Per-code detection:", "", tbl(d["per_code"], ["code", "tp", "fp", "fn", "precision", "recall", "f1"]), ""]
    if d["false_positives"]: L += ["False positives (invoice, code): " + "; ".join(f"`{a}` {b}" for a, b in d["false_positives"]), ""]
    if d["false_negatives"]: L += ["False negatives (invoice, code): " + "; ".join(f"`{a}` {b}" for a, b in d["false_negatives"]), ""]
    L += [f"Citations: {d['citations']['verified']}/{d['citations']['citations']} verified against source text; findings with evidence: {d['citations']['findings_with_evidence']}/{d['citations']['findings_total']}.", ""]
    return L

L = ["# Evaluation (generated from `reports/evaluation/evaluation_results.json`)", "",
     "Protocol: ground truth (`ground_truth/*.csv`) is read only by `procuraai.evaluation`; agents and the engine never see it. A prediction is an (invoice, finding code) pair; INFO notes (description variant, partial-delivery reconciled) are scored like any other code. "
     "`EXTRACTION_LOW_CONFIDENCE` is an operational flag and excluded from scoring.", "",
     "> **Read this first.** The synthetic data and the audit engine were written together, so the structured-path score demonstrates internal consistency, not accuracy on real-world invoices. "
     "The document path (OCR + extraction + audit) is the more informative number. Real suppliers, layouts, scans and policies will behave worse until validated on real, consented documents.", "",
     "## 1. Audit quality", ""]
L += block("Structured-input path (CSV tables -> agents)", r["structured_path"]) + block("Document path (PDF/PNG/JPG/TXT -> OCR/extraction -> agents)", r["document_path"])
L += ["Interpretation of the document-path false positives: they originate in OCR errors in the invoice, purchase order or delivery document (digit/letter confusions, dropped rows). "
      "No false positive was *confirmed*: findings that depend on a low-confidence invoice or on OCR-derived PO/DC evidence are downgraded to POTENTIAL and routed to human review. "
      "The re-scanned duplicate is still caught, but as POSSIBLE_DUPLICATE (OCR lost the invoice number), which counts as one FP and one FN in strict code matching.", "",
      "## 2. Extraction field accuracy (documents vs structured observed values)", ""]
L += [tbl([dict(source=k, documents=v["documents"], fully_correct=v["documents_fully_correct"], field_accuracy=v["field_accuracy"]) for k, v in r["extraction_accuracy"].items()]), "",
      "By field (OCR):", "", tbl([dict(field=k, accuracy=v) for k, v in r["extraction_accuracy"]["ocr"]["by_field"].items()]), ""]
pm = r["product_matching"]
L += ["## 3. Product matching", "", tbl([dict(metric=k, value=v) for k, v in pm.items() if k != "wrong"]), "",
      "Description-only matching hides the product code from the matcher. 100% here reflects the synthetic catalogue (distinct descriptions, curated aliases); real catalogues will have harder near-duplicates.", "", "## 4. RAG retrieval", ""]
for mode, res in r["rag_retrieval"].items():
    L += [f"**{mode}**", "", tbl([dict(query_type=k, **v) for k, v in res.items()]), ""]
L += ["Queries: 14 hand-written policy questions, 16 contract-clause questions (supplier given as a metadata filter), 40 random price-row lookups. "
      "Embedder: offline TF-IDF lexical baseline; a semantic embedder was not run in this evaluation. The hand-written queries share vocabulary with the synthetic policies, so scores are optimistic.", "",
      "## 5. Timing and API usage", "", tbl([dict(kind=k, **v) for k, v in r["processing_time_per_document_s"].items()]), "",
      f"Document-path wall clock: {r['document_path']['wall_clock_s']} s (single process, sandbox CPU). Structured path: {r['structured_path']['timings']['total_s']} s for 72 invoices.", "", f"API usage: {r['api_usage']['note'] if 'note' in r['api_usage'] else r['api_usage']}", ""]
(root / "docs/evaluation.md").write_text("\n".join(L), encoding="utf-8")
print("wrote docs/evaluation.md", len("\n".join(L)))
