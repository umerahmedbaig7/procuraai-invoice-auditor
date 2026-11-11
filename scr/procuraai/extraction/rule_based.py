"""Template/rule-based extraction for the synthetic documents (works offline, no API key).

Table rows are parsed independent of the header text (robust to OCR noise): after an optional serial number
and a product code (or '-'), the description runs until the numeric tail
    qty uom unit_price disc% amount [tax% tax_amt]            (invoice)
    qty uom unit_price amount                                  (purchase order)
    qty uom                                                    (delivery challan)
Unknown values stay None and are listed in ``missing_fields``; nothing is guessed.
"""
from __future__ import annotations

import re
from decimal import Decimal

from ..audit.money import to_decimal
from ..ingestion.loader import ExtractedDocument
from ..normalization import normalize_currency, normalize_uom, parse_date
from ..schemas import (Charge, DCLine, DeliveryChallanRecord, InvoiceRecord, LineItem, POLine, Provenance, PurchaseOrderRecord)

NUM = r"-?[\d,]+(?:\.\d+)?"
CODE = r"(?:[A-Z]{2,4}-\d{3,5}|-)"
_INV_ROW = re.compile(rf"^(?:(?P<sno>\d{{1,3}})\s+)?(?P<code>{CODE})\s+(?P<desc>.+?)\s+(?P<qty>{NUM})\s+(?P<uom>[A-Za-z]{{1,5}})\s+(?P<price>{NUM})\s+(?P<disc>{NUM})\s+(?P<amt>{NUM})(?:\s+(?P<trate>{NUM})\s+(?P<tamt>{NUM}))?\s*$")
_PO_ROW = re.compile(rf"^(?P<sno>\d{{1,3}})\s+(?P<code>{CODE})\s+(?P<desc>.+?)\s+(?P<qty>{NUM})\s+(?P<uom>[A-Za-z]{{1,5}})\s+(?P<price>{NUM})\s+(?P<amt>{NUM})\s*$")
_DC_ROW = re.compile(rf"^(?P<sno>\d{{1,3}})\s+(?P<code>{CODE})\s+(?P<desc>.+?)\s+(?P<qty>{NUM})\s+(?P<uom>[A-Za-z]{{1,5}})\s*$")
_NO_CODE_ROW = re.compile(rf"^(?:(?P<sno>\d{{1,3}})\s+)?(?P<desc>[A-Za-z].+?)\s+(?P<qty>{NUM})\s+(?P<uom>[A-Za-z]{{1,5}})\s+(?P<price>{NUM})\s+(?P<disc>{NUM})\s+(?P<amt>{NUM})(?:\s+(?P<trate>{NUM})\s+(?P<tamt>{NUM}))?\s*$")

LABELS = {
    "invoice_number": r"(?:invoice|bill)[^:]{0,6}?(?:no\.?|#|number)",
    "invoice_date": r"(?:invoice date|date|dated)",
    "po_number": r"(?:po number|purchase order|your order no\.?|po ref(?:erence)?)",
    "dc_reference": r"(?:delivery ref|dc / grn ref|challan no\.?|dc ref|grn ref)",
    "currency": r"currency",
    "payment_terms": r"(?:payment terms|terms)",
    "due_date": r"(?:due date|payable by|due on)",
    "tax_id": r"(?:tax reg no|supplier tax id|strn|ntn)",
    "supplier_code": r"(?:supplier code|vendor code)",
}
TOTALS = {"subtotal": r"(?:subtotal|sub total|net total)", "tax_total": r"(?:total tax|gst total|sales tax total)", "grand_total": r"(?:grand total|total payable|invoice total)"}
CHARGE_KW = re.compile(r"(freight|handling|packing|fuel|service|insurance|loading|surcharge|misc|delivery|courier)", re.I)
TITLES = {"PURCHASE ORDER", "DELIVERY CHALLAN", "GOODS RECEIVED NOTE", "TAX INVOICE", "INVOICE", "BILL / CASH MEMO"}
DATE_RX = re.compile(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}[- ][A-Za-z]{3,9}[- ]\d{4})\b")


def _segments(line: str) -> list[str]:
    return [s.strip() for s in re.split(r"\s{2,}", line.strip()) if s.strip()]


def _kv_pairs(lines: list[str]) -> list[tuple[str, str, int]]:
    """Collect (label, value, line index) from 'Label: value' and 'Label:  value' constructs."""
    out = []
    for i, ln in enumerate(lines):
        segs = _segments(ln)
        j = 0
        while j < len(segs):
            sg = segs[j]
            if ":" in sg:
                lab, _, val = sg.partition(":")
                lab, val = lab.strip(), val.strip()
                if not val and j + 1 < len(segs) and ":" not in segs[j + 1][:40]:
                    val = segs[j + 1]
                    j += 1
                out.append((lab.lower(), val, i))
            j += 1
    return out


def _find(pairs, rx: str):
    r = re.compile(rf"^{rx}$", re.I)
    for lab, val, i in pairs:
        if r.match(lab):
            return val, i
    return None, None


def _clean_ocr_token(s: str | None) -> str | None:
    return s.strip(" .,;") if s else s


class _Builder:
    def __init__(self, doc: ExtractedDocument):
        self.doc = doc
        self.lines = [l for l in doc.text.splitlines() if l.strip()]
        self.prov: dict[str, Provenance] = {}
        self.missing: list[str] = []
        self.warnings: list[str] = []
        self.method = "ocr+rule" if "ocr" in doc.method else "rule"

    def note(self, field: str, line: str | None, conf: float = 1.0):
        self.prov[field] = Provenance(source_file=self.doc.source_file, page=1, excerpt=(line or "")[:160], method=self.method, confidence=min(conf, self.doc.confidence))

    def get(self, pairs, field: str, rx: str, as_date=False):
        val, i = _find(pairs, rx)
        if val in (None, ""):
            self.missing.append(field)
            return None
        self.note(field, self.lines[i] if i is not None and i < len(self.lines) else None)
        if as_date:
            d = parse_date(val)
            if d is None:
                self.warnings.append(f"{field}: unparseable date {val!r}")
                self.missing.append(field)
            return d
        return _clean_ocr_token(val)


def _supplier_name(lines: list[str]) -> tuple[str | None, str | None]:
    for ln in lines[:4]:
        for seg in _segments(ln):
            if seg.upper() in TITLES or ":" in seg:
                continue
            seg = re.sub(r"^M/s\.?\s*", "", seg)
            return seg, ln
    return None, None


def _split_table_and_totals(lines: list[str]):
    start = None
    for i, ln in enumerate(lines):
        if _INV_ROW.match(ln) or _NO_CODE_ROW.match(ln):
            start = i
            break
    return start


def extract_invoice(doc: ExtractedDocument) -> InvoiceRecord:
    b = _Builder(doc)
    pairs = _kv_pairs(b.lines)
    inv = InvoiceRecord(source_file=doc.source_file, invoice_id=doc.source_file.rsplit(".", 1)[0], page_count=len(doc.pages), extraction_method=b.method)
    name, nl = _supplier_name(b.lines)
    inv.supplier_name = name
    if name:
        b.note("supplier_name", nl)
    else:
        b.missing.append("supplier_name")
    inv.invoice_number = b.get(pairs, "invoice_number", LABELS["invoice_number"])
    if inv.invoice_number is None:
        m = re.search(r"(?:Invoice|Bill)[^:\n]{0,8}?(?:No\.?|#)\s*:\s*([A-Z0-9][A-Z0-9/\-_.]+)", re.sub(r"[ \t]+", " ", doc.text))
        if m:
            inv.invoice_number = m.group(1)
            b.missing.remove("invoice_number")
            b.warnings.append("invoice_number recovered with fallback pattern (noisy label)")
            b.note("invoice_number", m.group(0), 0.7)
    inv.invoice_date = b.get(pairs, "invoice_date", LABELS["invoice_date"], as_date=True)
    if inv.invoice_date is None and "invoice_date" in b.missing:
        # OCR may displace the value to a neighbouring line: use the first header date not claimed by the due date
        due_val, _ = _find(pairs, LABELS["due_date"])
        header = "\n".join(b.lines[:14])
        cands = [m for m in DATE_RX.findall(header) if m != due_val]
        if cands:
            inv.invoice_date = parse_date(cands[0])
            if inv.invoice_date:
                b.missing.remove("invoice_date")
                b.warnings.append("invoice_date recovered from neighbouring text (low confidence)")
                b.note("invoice_date", cands[0], 0.6)
    inv.due_date = b.get(pairs, "due_date", LABELS["due_date"], as_date=True)
    inv.po_number = b.get(pairs, "po_number", LABELS["po_number"])
    inv.dc_reference = b.get(pairs, "dc_reference", LABELS["dc_reference"])
    if "dc_reference" in b.missing:
        b.missing.remove("dc_reference")             # optional field: absence is not an extraction failure
    cur = b.get(pairs, "currency", LABELS["currency"])
    inv.currency = normalize_currency(cur)
    inv.payment_terms = b.get(pairs, "payment_terms", LABELS["payment_terms"])
    inv.supplier_tax_id = b.get(pairs, "supplier_tax_id", LABELS["tax_id"])
    sid = b.get(pairs, "supplier_id", LABELS["supplier_code"])
    inv.supplier_id = sid
    if "supplier_id" in b.missing:
        b.missing.remove("supplier_id")
    # table rows
    start = _split_table_and_totals(b.lines)
    rows = b.lines[start:] if start is not None else []
    n = 0
    for ln in rows:
        m = _INV_ROW.match(ln)
        code = None
        if m:
            code = None if m.group("code") == "-" else m.group("code")
        else:
            m = _NO_CODE_ROW.match(ln) if not re.match(r"^\s*(?:[A-Za-z ]+):", ln) else None
        if not m:
            continue
        n += 1
        d = m.groupdict()
        li = LineItem(line_no=n, product_code=code if "code" in d and d.get("code") else None, description=d["desc"].strip(), quantity=to_decimal(d["qty"]),
                      uom=normalize_uom(d["uom"]), unit_price=to_decimal(d["price"]), discount_pct=to_decimal(d["disc"]), line_amount=to_decimal(d["amt"]),
                      tax_rate=to_decimal(d.get("trate")), tax_amount=to_decimal(d.get("tamt")), confidence=doc.confidence)
        if li.quantity is None or li.unit_price is None or li.line_amount is None:
            li.warnings.append("numeric field unreadable")
        inv.lines.append(li)
        b.prov[f"line{n}"] = Provenance(source_file=doc.source_file, page=1, excerpt=ln[:160], method=b.method, confidence=doc.confidence)
    if not inv.lines:
        b.missing.append("lines")
        b.warnings.append("no line items recognised")
    # totals + charges (after the last table row)
    tail_start = 0
    for i, ln in enumerate(b.lines):
        if ln in rows and (_INV_ROW.match(ln) or _NO_CODE_ROW.match(ln)):
            tail_start = i + 1
    tail = b.lines[tail_start:]
    tpairs = _kv_pairs(tail)
    for fld, rx in TOTALS.items():
        v, i = _find(tpairs, rx)
        dv = to_decimal(v)
        if dv is not None:
            setattr(inv, fld, dv)
            b.note(fld, tail[i] if i is not None else None)
    for lab, val, i in tpairs:
        if any(re.match(f"^{rx}$", lab, re.I) for rx in TOTALS.values()):
            continue
        amt = to_decimal(val)
        if amt is not None and CHARGE_KW.search(lab) and "terms" not in lab:
            ctype = CHARGE_KW.search(lab).group(1).upper()
            ctype = {"FREIGHT": "FREIGHT", "HANDLING": "HANDLING", "PACKING": "PACKING", "FUEL": "FUEL", "SERVICE": "SERVICE", "INSURANCE": "INSURANCE", "LOADING": "HANDLING"}.get(ctype, "OTHER")
            inv.charges.append(Charge(charge_type=ctype, description=lab.title(), amount=amt))
            b.note(f"charge:{lab}", tail[i])
    for f_, v in (("subtotal", inv.subtotal), ("grand_total", inv.grand_total)):
        if v is None:
            b.missing.append(f_)
    inv.missing_fields = sorted(set(b.missing))
    inv.provenance = b.prov
    inv.warnings = b.warnings
    expected = 11
    found = expected - len([m for m in inv.missing_fields if m in ("supplier_name", "invoice_number", "invoice_date", "po_number", "currency", "payment_terms", "subtotal", "grand_total", "lines", "due_date", "supplier_tax_id")])
    inv.extraction_confidence = round(doc.confidence * max(0.0, found / expected) * (0.9 if any(l.warnings for l in inv.lines) else 1.0), 3)
    return inv


def extract_po(doc: ExtractedDocument) -> PurchaseOrderRecord:
    b = _Builder(doc)
    pairs = _kv_pairs(b.lines)
    po = PurchaseOrderRecord(source_file=doc.source_file, page_count=len(doc.pages), extraction_method=b.method)
    po.po_number = b.get(pairs, "po_number", r"po number")
    po.po_date = b.get(pairs, "po_date", r"po date", as_date=True)
    po.supplier_name = b.get(pairs, "supplier_name", r"supplier")
    po.supplier_id = b.get(pairs, "supplier_id", r"supplier code")
    po.currency = normalize_currency(b.get(pairs, "currency", r"currency"))
    po.payment_terms = b.get(pairs, "payment_terms", r"payment terms")
    po.expected_delivery_date = b.get(pairs, "expected_delivery_date", r"delivery date", as_date=True)
    n = 0
    for ln in b.lines:
        m = _PO_ROW.match(ln)
        if not m:
            continue
        n += 1
        d = m.groupdict()
        po.lines.append(POLine(line_no=n, product_code=None if d["code"] == "-" else d["code"], description=d["desc"].strip(), quantity=to_decimal(d["qty"]),
                               uom=normalize_uom(d["uom"]), unit_price=to_decimal(d["price"]), line_amount=to_decimal(d["amt"])))
    tp = _kv_pairs(b.lines)
    v, _ = _find(tp, r"order total")
    po.total = to_decimal(v)
    if not po.lines:
        b.missing.append("lines")
    po.missing_fields, po.provenance, po.warnings = sorted(set(b.missing)), b.prov, b.warnings
    po.extraction_confidence = round(doc.confidence * (1 - 0.12 * len(po.missing_fields)), 3)
    return po


def extract_dc(doc: ExtractedDocument) -> DeliveryChallanRecord:
    b = _Builder(doc)
    pairs = _kv_pairs(b.lines)
    dc = DeliveryChallanRecord(source_file=doc.source_file, page_count=len(doc.pages), extraction_method=b.method)
    dc.dc_number = b.get(pairs, "dc_number", r"(?:dc no|grn no)")
    dc.dc_date = b.get(pairs, "dc_date", r"date", as_date=True)
    dc.po_number = b.get(pairs, "po_number", r"po reference")
    dc.supplier_name = b.get(pairs, "supplier_name", r"supplier")
    dc.supplier_id = b.get(pairs, "supplier_id", r"supplier code")
    rem, _ = _find(pairs, r"remarks")
    dc.remarks = rem
    n = 0
    for ln in b.lines:
        m = _DC_ROW.match(ln)
        if not m:
            continue
        n += 1
        d = m.groupdict()
        dc.lines.append(DCLine(line_no=n, product_code=None if d["code"] == "-" else d["code"], description=d["desc"].strip(), quantity_received=to_decimal(d["qty"]), uom=normalize_uom(d["uom"])))
    if not dc.lines:
        b.missing.append("lines")
    dc.missing_fields, dc.provenance, dc.warnings = sorted(set(b.missing), key=str), b.prov, b.warnings
    dc.extraction_confidence = round(doc.confidence * (1 - 0.12 * len(dc.missing_fields)), 3)
    return dc


def extract_document(doc: ExtractedDocument):
    if doc.doc_type == "INVOICE":
        return extract_invoice(doc)
    if doc.doc_type == "PURCHASE_ORDER":
        return extract_po(doc)
    if doc.doc_type == "DELIVERY_CHALLAN":
        return extract_dc(doc)
    return None


def integrity_score(rec) -> float:
    """Self-consistency score used to choose between OCR passes (higher is better; max for invoices = 15)."""
    if isinstance(rec, InvoiceRecord):
        sc = sum(1 for v in (rec.invoice_number, rec.invoice_date, rec.supplier_name, rec.po_number, rec.currency, rec.subtotal, rec.grand_total, rec.due_date, rec.supplier_tax_id) if v)
        sc += min(len(rec.lines), 5) * 0.2
        if rec.lines and rec.subtotal is not None and sum((l.line_amount or 0) for l in rec.lines) == rec.subtotal:
            sc += 3
        if rec.lines:
            ok = sum(1 for l in rec.lines if None not in (l.quantity, l.unit_price, l.line_amount)
                     and abs(l.quantity * l.unit_price * (1 - (l.discount_pct or Decimal(0)) / 100) - l.line_amount) <= Decimal("0.02") * max(Decimal(1), l.line_amount / 1000))
            sc += 2 * ok / len(rec.lines)
        if None not in (rec.subtotal, rec.grand_total) and rec.subtotal + (rec.tax_total or 0) + sum((c.amount for c in rec.charges), Decimal(0)) == rec.grand_total:
            sc += 1.5
        return sc
    fields = [getattr(rec, f, None) for f in ("po_number", "dc_number", "po_date", "dc_date", "supplier_name")]
    sc = sum(1 for v in fields if v) + min(len(rec.lines), 6) * 0.5
    if isinstance(rec, PurchaseOrderRecord) and rec.lines:
        ok = sum(1 for l in rec.lines if None not in (l.quantity, l.unit_price, l.line_amount) and abs(l.quantity * l.unit_price - l.line_amount) <= Decimal("0.02"))
        sc += 3 * ok / len(rec.lines)
        if rec.total is not None and sum((l.line_amount or Decimal(0)) for l in rec.lines) == rec.total:
            sc += 2
    elif isinstance(rec, DeliveryChallanRecord) and rec.lines:
        sc += 2 * sum(1 for l in rec.lines if l.quantity_received is not None and l.product_code) / len(rec.lines)
    return sc


def check_integrity(rec: InvoiceRecord, ocr: bool) -> None:
    """Attach extraction-integrity warnings; for OCR output cap confidence so downstream findings go to review."""
    if rec.lines and rec.subtotal is not None:
        total = sum((l.line_amount or Decimal(0)) for l in rec.lines)
        if total != rec.subtotal:
            rec.warnings.append(f"extraction_integrity: line amounts sum to {total} but subtotal reads {rec.subtotal}")
            if ocr:
                rec.extraction_confidence = min(rec.extraction_confidence, 0.5)
    if ocr and (rec.missing_fields and any(m in rec.missing_fields for m in ("invoice_number", "invoice_date", "lines", "subtotal", "grand_total"))):
        rec.extraction_confidence = min(rec.extraction_confidence, 0.6)
