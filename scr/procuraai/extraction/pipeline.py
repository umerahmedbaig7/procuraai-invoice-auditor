"""File -> record extraction with OCR retry (choose the most self-consistent OCR pass)."""
from __future__ import annotations

from pathlib import Path

from ..ingestion.loader import OCR_VARIANTS, ExtractedDocument, load_file
from .rule_based import check_integrity, extract_document, integrity_score

MAX_SCORE = {"INVOICE": 14.0, "PURCHASE_ORDER": 25.0, "DELIVERY_CHALLAN": 25.0}


def extract_file(path: str | Path, ocr: bool = True, max_variants: int = len(OCR_VARIANTS)):
    """Returns (ExtractedDocument, record|None). Re-runs OCR with other settings only when the result is not self-consistent."""
    p = Path(path)
    doc = load_file(p, ocr=ocr, ocr_variant=0)
    rec = extract_document(doc)
    if rec is None or "ocr" not in doc.method or not ocr:
        if rec is not None and rec.doc_type == "INVOICE":
            check_integrity(rec, ocr=False)
        return doc, rec
    best, best_doc, best_sc = rec, doc, integrity_score(rec)
    for v in range(1, max_variants):
        if best_sc >= MAX_SCORE.get(rec.doc_type, 99):
            break
        d2 = load_file(p, ocr=True, ocr_variant=v)
        r2 = extract_document(d2)
        if r2 is None:
            continue
        sc = integrity_score(r2)
        if sc > best_sc:
            best, best_doc, best_sc = r2, d2, sc
    if best.doc_type == "INVOICE":
        check_integrity(best, ocr=True)
    best.warnings.append(f"ocr_variant={best_doc.ocr_variant} integrity_score={best_sc:.1f}")
    return best_doc, best
