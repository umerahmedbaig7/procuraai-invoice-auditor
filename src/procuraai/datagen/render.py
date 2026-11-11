"""Render synthetic documents: selectable-text PDFs (3 invoice layouts, 2 PO, 2 DC), scanned-style
image-only PDFs, PNG/JPG images with degradation, plain-text invoices, contracts and policies.
All documents carry a SYNTHETIC banner."""
from __future__ import annotations

import io
import random
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..schemas import DeliveryChallanRecord, InvoiceRecord, PurchaseOrderRecord
from .catalog import POLICY_DOCS, SYNTHETIC_BANNER, AgreementSpec, Profile, SupplierSpec

W, H = A4

# Header labels per invoice template. The rule-based extractor knows these synonyms.
INV_LABELS = {
    "A": dict(title="TAX INVOICE", inv="Invoice No", date="Invoice Date", po="PO Number", dc="Delivery Ref", cur="Currency", terms="Payment Terms", due="Due Date", tax="Tax Reg No", sid="Supplier Code",
              cols="Code|Description|Qty|UoM|Unit Price|Disc %|Amount|Tax %|Tax Amt", sub="Subtotal", taxt="Total Tax", grand="Grand Total"),
    "B": dict(title="INVOICE", inv="Invoice #", date="Date", po="Purchase Order", dc="DC / GRN Ref", cur="Currency", terms="Terms", due="Payable By", tax="Supplier Tax ID", sid="Vendor Code",
              cols="Item Code|Item Description|Qty|UoM|Rate|Disc|Line Total|GST %|GST Amt", sub="Sub Total", taxt="GST Total", grand="Total Payable"),
    "C": dict(title="BILL / CASH MEMO", inv="Bill No.", date="Dated", po="Your Order No.", dc="Challan No.", cur="Currency", terms="Payment Terms", due="Due On", tax="STRN", sid="Supplier Code",
              cols="S.No|Code|Particulars|Qty|Unit|Rate|Disc %|Net Amt|Tax %|Tax Amt", sub="Net Total", taxt="Sales Tax Total", grand="Invoice Total"),
}


def fdate(d: date | None, style: str) -> str:
    return d.strftime(style) if d else ""


def money(x) -> str:
    return "" if x is None else f"{x:,.2f}"


def num(x) -> str:
    if x is None:
        return "-"
    return f"{x:,.2f}" if x != x.to_integral_value() else f"{int(x):,}"


# ---------------------------------------------------------------------------------------------
# Invoice PDF templates
# ---------------------------------------------------------------------------------------------
def _fit(c: canvas.Canvas, text: str, font: str, size: float, max_w: float) -> float:
    while stringWidth(text, font, size) > max_w and size > 5:
        size -= 0.25
    return size


def _col_layout(names: list[str]) -> list[tuple[str, float, str]]:
    """(canonical name, width, align) for each header, summing to the usable table width."""
    base = {"S.No": 22, "Code": 52, "Item Code": 54, "Description": 190, "Item Description": 190, "Particulars": 184, "Qty": 34, "UoM": 30, "Unit": 30,
            "Unit Price": 50, "Rate": 50, "Disc %": 30, "Disc": 30, "Amount": 56, "Line Total": 56, "Net Amt": 54, "Tax %": 28, "GST %": 28, "Tax Amt": 46, "GST Amt": 46}
    tot = sum(base[n] for n in names)
    scale = 536 / tot
    out = []
    for n in names:
        align = "l" if n in ("Code", "Item Code", "Description", "Item Description", "Particulars", "S.No", "UoM", "Unit") else "r"
        out.append((n, base[n] * scale, align))
    return out


def render_invoice_pdf(inv: InvoiceRecord, sup: SupplierSpec | None, sinfo, template: str, profile: Profile, path: Path, date_style: str) -> None:
    L = INV_LABELS[template]
    has_tax = inv.has_tax_info
    cols = L["cols"].split("|")
    if not has_tax:
        cols = [c for c in cols if not (c.startswith("Tax") or c.startswith("GST"))]
    font = "Times-Roman" if template == "C" else "Helvetica"
    bold = "Times-Bold" if template == "C" else "Helvetica-Bold"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"Invoice {inv.invoice_number}")
    c.setAuthor("ProcuraAI synthetic data generator")
    left, y = 30, H - 36
    # --- supplier block (first text line = supplier name)
    if template == "A":
        c.setFillColor(colors.HexColor("#1f3a5f")); c.rect(0, H - 8, W, 8, fill=1, stroke=0); c.setFillColor(colors.black)
    if template == "B":
        c.setFillColor(colors.HexColor("#0b7285")); c.rect(0, H - 14, W, 14, fill=1, stroke=0); c.setFillColor(colors.black)
    name = inv.supplier_name or ""
    c.setFont(bold, 15 if template != "C" else 14)
    c.drawString(left, y - (6 if template == "B" else 0), name if template != "C" else name)
    c.setFont(font, 8.5)
    y -= 14 + (6 if template == "B" else 0)
    c.drawString(left, y, f"{sinfo.address}, {sinfo.city}")
    y -= 11
    c.drawString(left, y, f"{L['tax']}: {inv.supplier_tax_id or ''}")
    if inv.supplier_id:
        y -= 11
        c.drawString(left, y, f"{L['sid']}: {inv.supplier_id}")
    # --- title + fields
    ty = H - 100
    if template == "A":
        c.setFont(bold, 18); c.drawRightString(W - 30, H - 42, L["title"])
        fields_x, fy = 330, H - 62
    elif template == "B":
        c.setFont(bold, 16); c.drawRightString(W - 30, H - 44, L["title"])
        fields_x, fy = 330, H - 64
    else:
        c.setFont(bold, 13); c.drawRightString(W - 30, H - 36, L["title"])
        fields_x, fy = 330, H - 56
    pairs = [(L["inv"], inv.invoice_number), (L["date"], fdate(inv.invoice_date, date_style)), (L["po"], inv.po_number),
             (L["dc"], inv.dc_reference), (L["cur"], inv.currency), (L["terms"], inv.payment_terms), (L["due"], fdate(inv.due_date, date_style))]
    c.setFont(font, 8.5)
    for lab, val in pairs:
        if val:
            c.setFont(bold, 8.5); c.drawString(fields_x, fy, f"{lab}:")
            c.setFont(font, 8.5); c.drawString(fields_x + 78, fy, str(val))
            fy -= 11
    # bill-to
    by = min(y, fy) - 12
    c.setFont(bold, 8.5); c.drawString(left, by, "Bill To:")
    c.setFont(font, 8.5)
    c.drawString(left + 38, by, profile.customer_name)
    c.drawString(left + 38, by - 10, profile.customer_address)
    ty = by - 30
    # --- table
    cl = _col_layout(cols)
    x0 = left
    if template == "A":
        c.setFillColor(colors.HexColor("#1f3a5f")); c.rect(x0 - 2, ty - 4, 540, 15, fill=1, stroke=0); c.setFillColor(colors.white)
    elif template == "B":
        c.setStrokeColor(colors.HexColor("#0b7285")); c.line(x0 - 2, ty - 5, x0 + 538, ty - 5); c.setFillColor(colors.HexColor("#0b7285"))
    else:
        c.setStrokeColor(colors.black); c.rect(x0 - 2, ty - 5, 540, 16, fill=0, stroke=1)
    xs, x = [], x0
    c.setFont(bold, 7.6)
    for n, w, al in cl:
        xs.append((x, w, al))
        (c.drawString(x + 1, ty, n) if al == "l" else c.drawRightString(x + w - 2, ty, n))
        x += w
    c.setFillColor(colors.black)
    ry = ty - 17
    n_by_col = {n: i for i, (n, _, _) in enumerate(cl)}
    for i, l in enumerate(inv.lines, 1):
        tax_pct = f"{l.tax_rate:.2f}" if l.tax_rate is not None else ""
        vals = {"S.No": str(i), "Code": l.product_code or "-", "Item Code": l.product_code or "-", "Description": l.description, "Item Description": l.description,
                "Particulars": l.description, "Qty": num(l.quantity), "UoM": l.uom or "", "Unit": l.uom or "", "Unit Price": money(l.unit_price), "Rate": money(l.unit_price),
                "Disc %": f"{l.discount_pct or 0:.2f}", "Disc": f"{l.discount_pct or 0:.2f}", "Amount": money(l.line_amount), "Line Total": money(l.line_amount), "Net Amt": money(l.line_amount),
                "Tax %": tax_pct, "GST %": tax_pct, "Tax Amt": money(l.tax_amount), "GST Amt": money(l.tax_amount)}
        if template == "A" and i % 2 == 0:
            c.setFillColor(colors.HexColor("#eef2f7")); c.rect(x0 - 2, ry - 3, 540, 12, fill=1, stroke=0); c.setFillColor(colors.black)
        for (n, w, al), (xx, ww, _) in zip(cl, xs):
            t = vals[n]
            size = _fit(c, t, font, 7.8, ww - 3)
            c.setFont(font, size)
            (c.drawString(xx + 1, ry, t) if al == "l" else c.drawRightString(xx + ww - 2, ry, t))
        if template == "C":
            c.setStrokeColor(colors.grey); c.line(x0 - 2, ry - 3, x0 + 538, ry - 3)
        ry -= 13
    if template in ("A", "B"):
        c.setStrokeColor(colors.grey); c.line(x0 - 2, ry + 6, x0 + 538, ry + 6)
    # --- totals
    ry -= 14
    rx = W - 32
    def trow(label, val, b=False):
        nonlocal ry
        c.setFont(bold if b else font, 9)
        c.drawString(330, ry, f"{label}:")
        c.drawRightString(rx, ry, money(val))
        ry -= 12
    trow(L["sub"], inv.subtotal)
    if has_tax and inv.tax_total is not None:
        trow(L["taxt"], inv.tax_total)
    for ch in inv.charges:
        trow(ch.description or ch.charge_type.title(), ch.amount)
    c.setStrokeColor(colors.black); c.line(330, ry + 9, rx, ry + 9)
    trow(L["grand"], inv.grand_total, b=True)
    ry -= 6
    c.setFont(font, 7.5)
    if inv.payment_terms:
        c.drawString(left, ry, f"Payment terms: {inv.payment_terms}. Goods once sold are subject to the supplier's standard terms.")
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.HexColor("#b00020"))
    c.drawString(left, 24, SYNTHETIC_BANNER)
    c.showPage(); c.save()


# ---------------------------------------------------------------------------------------------
# PO / DC templates
# ---------------------------------------------------------------------------------------------
def render_po_pdf(po: PurchaseOrderRecord, sinfo, profile: Profile, path: Path, variant: int = 0) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    font, bold = ("Helvetica", "Helvetica-Bold") if variant == 0 else ("Times-Roman", "Times-Bold")
    c.setTitle(f"Purchase Order {po.po_number}")
    y = H - 40
    c.setFont(bold, 15); c.drawString(30, y, profile.customer_name)
    c.setFont(font, 8.5); c.drawString(30, y - 12, profile.customer_address)
    c.setFont(bold, 17); c.drawRightString(W - 30, y, "PURCHASE ORDER")
    y -= 38
    rows = [("PO Number", po.po_number), ("PO Date", po.po_date.strftime("%d-%b-%Y" if variant == 0 else "%Y-%m-%d")),
            ("Supplier", po.supplier_name), ("Supplier Code", po.supplier_id), ("Currency", po.currency), ("Payment Terms", po.payment_terms),
            ("Delivery Date", po.expected_delivery_date.strftime("%d-%b-%Y" if variant == 0 else "%Y-%m-%d") if po.expected_delivery_date else "")]
    for lab, val in rows:
        c.setFont(bold, 9); c.drawString(30, y, f"{lab}:")
        c.setFont(font, 9); c.drawString(120, y, str(val or ""))
        y -= 12
    y -= 10
    cols = [("#", 22, "l"), ("Code", 62, "l"), ("Description", 230, "l"), ("Qty", 44, "r"), ("UoM", 36, "l"), ("Unit Price", 62, "r"), ("Amount", 80, "r")]
    x = 30
    if variant == 0:
        c.setFillColor(colors.HexColor("#444444")); c.rect(28, y - 4, 540, 15, fill=1, stroke=0); c.setFillColor(colors.white)
    else:
        c.rect(28, y - 4, 540, 15, fill=0, stroke=1)
    c.setFont(bold, 8)
    xs = []
    for n, w, al in cols:
        xs.append((x, w, al)); (c.drawString(x, y, n) if al == "l" else c.drawRightString(x + w - 2, y, n)); x += w
    c.setFillColor(colors.black)
    y -= 17
    for i, l in enumerate(po.lines, 1):
        vals = [str(i), l.product_code or "-", l.description, num(l.quantity), l.uom or "", money(l.unit_price), money(l.line_amount)]
        for (n, w, al), (xx, ww, _), v in zip(cols, xs, vals):
            c.setFont(font, _fit(c, v, font, 8.3, ww - 3))
            (c.drawString(xx, y, v) if al == "l" else c.drawRightString(xx + ww - 2, y, v))
        y -= 13
    y -= 8
    c.setFont(bold, 9.5); c.drawString(380, y, "Order Total:"); c.drawRightString(W - 32, y, money(po.total))
    y -= 22
    c.setFont(font, 8); c.drawString(30, y, "Prices as per agreed supplier price list. Delivery to main store. Invoice must quote the PO number.")
    c.setFont("Helvetica-Oblique", 7); c.setFillColor(colors.HexColor("#b00020")); c.drawString(30, 24, SYNTHETIC_BANNER)
    c.showPage(); c.save()


def render_dc_pdf(dc: DeliveryChallanRecord, sinfo, profile: Profile, path: Path, variant: int = 0) -> None:
    grn = dc.dc_number.startswith("GRN")
    title = "GOODS RECEIVED NOTE" if grn else "DELIVERY CHALLAN"
    font, bold = ("Helvetica", "Helvetica-Bold") if variant == 0 else ("Courier", "Courier-Bold")
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{title} {dc.dc_number}")
    y = H - 40
    c.setFont(bold, 15); c.drawString(30, y, profile.customer_name if grn else (dc.supplier_name or ""))
    c.setFont(font, 8.5); c.drawString(30, y - 12, profile.customer_address if grn else f"{sinfo.address}, {sinfo.city}")
    c.setFont(bold, 16); c.drawRightString(W - 30, y, title)
    y -= 38
    rows = [("GRN No" if grn else "DC No", dc.dc_number), ("Date", dc.dc_date.strftime("%d/%m/%Y")), ("PO Reference", dc.po_number),
            ("Supplier", dc.supplier_name), ("Supplier Code", dc.supplier_id)]
    for lab, val in rows:
        c.setFont(bold, 9); c.drawString(30, y, f"{lab}:")
        c.setFont(font, 9); c.drawString(120, y, str(val or ""))
        y -= 12
    y -= 10
    cols = [("#", 22, "l"), ("Code", 62, "l"), ("Description", 270, "l"), ("Qty Received", 80, "r"), ("UoM", 60, "l")]
    x = 30
    c.rect(28, y - 4, 520, 15, fill=0, stroke=1)
    c.setFont(bold, 8)
    xs = []
    for n, w, al in cols:
        xs.append((x, w, al)); (c.drawString(x + 2, y, n) if al == "l" else c.drawRightString(x + w - 2, y, n)); x += w
    y -= 17
    for i, l in enumerate(dc.lines, 1):
        vals = [str(i), l.product_code or "-", l.description, num(l.quantity_received), l.uom or ""]
        for (n, w, al), (xx, ww, _), v in zip(cols, xs, vals):
            c.setFont(font, _fit(c, v, font, 8.3, ww - 3))
            (c.drawString(xx + 2, y, v) if al == "l" else c.drawRightString(xx + ww - 2, y, v))
        y -= 13
    y -= 10
    if dc.remarks:
        c.setFont(bold, 9); c.drawString(30, y, "Remarks:"); c.setFont(font, 9); c.drawString(90, y, dc.remarks)
    c.setFont("Helvetica-Oblique", 7); c.setFillColor(colors.HexColor("#b00020")); c.drawString(30, 24, SYNTHETIC_BANNER)
    c.showPage(); c.save()


# ---------------------------------------------------------------------------------------------
# Plain-text invoice
# ---------------------------------------------------------------------------------------------
def render_invoice_txt(inv: InvoiceRecord, sinfo, template: str, profile: Profile, date_style: str) -> str:
    L = INV_LABELS[template]
    has_tax = inv.has_tax_info
    cols = L["cols"].split("|")
    if not has_tax:
        cols = [c for c in cols if not (c.startswith("Tax") or c.startswith("GST"))]
    out = [inv.supplier_name or "", f"{sinfo.address}, {sinfo.city}", f"{L['tax']}: {inv.supplier_tax_id or ''}"]
    if inv.supplier_id:
        out.append(f"{L['sid']}: {inv.supplier_id}")
    out += ["", L["title"], f"{L['inv']}: {inv.invoice_number}", f"{L['date']}: {fdate(inv.invoice_date, date_style)}", f"{L['po']}: {inv.po_number or ''}"]
    if inv.dc_reference:
        out.append(f"{L['dc']}: {inv.dc_reference}")
    out += [f"{L['cur']}: {inv.currency}", f"{L['terms']}: {inv.payment_terms}", f"{L['due']}: {fdate(inv.due_date, date_style)}", "", f"Bill To: {profile.customer_name}", ""]
    out.append("  ".join(cols))
    for i, l in enumerate(inv.lines, 1):
        vals = {"S.No": str(i), "Code": l.product_code or "-", "Item Code": l.product_code or "-", "Description": l.description, "Item Description": l.description,
                "Particulars": l.description, "Qty": num(l.quantity), "UoM": l.uom or "", "Unit": l.uom or "", "Unit Price": money(l.unit_price), "Rate": money(l.unit_price),
                "Disc %": f"{l.discount_pct or 0:.2f}", "Disc": f"{l.discount_pct or 0:.2f}", "Amount": money(l.line_amount), "Line Total": money(l.line_amount), "Net Amt": money(l.line_amount),
                "Tax %": f"{l.tax_rate:.2f}" if l.tax_rate is not None else "", "GST %": f"{l.tax_rate:.2f}" if l.tax_rate is not None else "",
                "Tax Amt": money(l.tax_amount), "GST Amt": money(l.tax_amount)}
        out.append("  ".join(vals[c] for c in cols))
    out.append("")
    out.append(f"{L['sub']}: {money(inv.subtotal)}")
    if has_tax and inv.tax_total is not None:
        out.append(f"{L['taxt']}: {money(inv.tax_total)}")
    for ch in inv.charges:
        out.append(f"{ch.description or ch.charge_type.title()}: {money(ch.amount)}")
    out.append(f"{L['grand']}: {money(inv.grand_total)}")
    out += ["", SYNTHETIC_BANNER]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------------------------
# Rasterisation and degradation
# ---------------------------------------------------------------------------------------------
def rasterize(pdf_path: Path, dpi: int = 200) -> Image.Image:
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def degrade(img: Image.Image, level: str, rng: random.Random) -> Image.Image:
    """level: 'clean' | 'scan' | 'photo'. Mild rotation, noise, blur, uneven background, low contrast."""
    if level == "clean":
        return img
    seed = rng.randint(0, 2**31 - 1)
    nrng = np.random.default_rng(seed)
    angle = rng.uniform(-0.8, 0.8) if level == "scan" else rng.uniform(-1.6, 1.6)
    bg = (246, 244, 238) if level == "scan" else (236, 232, 222)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=bg)
    arr = np.asarray(img).astype(np.float32)
    h, w, _ = arr.shape
    # uneven illumination gradient
    gx = np.linspace(rng.uniform(-10, 4), rng.uniform(-14, 2), w)[None, :, None]
    gy = np.linspace(rng.uniform(-6, 2), rng.uniform(-10, 0), h)[:, None, None]
    arr = arr + gx + gy
    # low contrast
    k = 0.93 if level == "scan" else 0.86
    arr = 128 + (arr - 128) * k + (0 if level == "scan" else 8)
    arr += nrng.normal(0, 3.0 if level == "scan" else 5.5, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(0.45 if level == "scan" else 0.65))
    return img


def save_image_doc(img: Image.Image, path: Path, fmt: str) -> None:
    if fmt == "png":
        img.save(path, format="PNG", optimize=True)
    else:
        img.save(path, format="JPEG", quality=62, optimize=True)


def image_to_pdf(img: Image.Image, path: Path) -> None:
    """Image-only PDF (no text layer) to test the OCR fallback."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    page.insert_image(fitz.Rect(0, 0, W, H), stream=buf.getvalue())
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------------------------
# Contracts & policies
# ---------------------------------------------------------------------------------------------
def contract_text(sup: SupplierSpec, ags: list[AgreementSpec], prices: list, products: dict, profile: Profile) -> list[tuple[str, str]]:
    """Return (section heading, body) pairs. Heading carries the clause number used as citation 'section'."""
    s = sup.info
    sections = [
        ("Parties", f"This Supply and Pricing Agreement is made between {profile.customer_name} (the Buyer) and {s.name}, {s.address}, {s.city} (the Supplier), supplier code {s.supplier_id}, tax registration {s.tax_id}. SYNTHETIC DOCUMENT - FICTIONAL DATA."),
    ]
    for a in ags:
        ag = a.agreement
        sections.append((f"Agreement {ag.agreement_id} - Term", f"Agreement {ag.agreement_id} is effective from {ag.effective_from.isoformat()} to {ag.effective_to.isoformat()}. Prices in Schedule {ag.agreement_id} apply to purchase orders dated within this period. Currency: {ag.currency}."))
    ag0 = ags[0].agreement
    sections.append(("Payment Terms", f"Payment terms are {ag0.payment_terms or s.payment_terms} from the invoice date."))
    if ag0.volume_discount_min_qty > 0:
        sections.append(("Volume Discount", f"A volume discount of {ag0.volume_discount_pct:.0f} percent applies to any product line where the ordered quantity is {ag0.volume_discount_min_qty:.0f} units or more. The discount is determined on the purchase-order quantity and shown on the invoice line."))
    else:
        sections.append(("Volume Discount", "No volume discount applies under this agreement."))
    if ag0.freight_policy == "INCLUDED":
        sections.append(("Freight and Additional Charges", "Delivery to the Buyer's store is included in the unit prices. No freight, handling, packing, fuel or other additional charge may be invoiced."))
    else:
        allowed = ", ".join(a.lower() for a in ag0.allowed_charge_types)
        sections.append(("Freight and Additional Charges", f"The Supplier may invoice the following additional charges: {allowed}. Freight must not exceed PKR {ag0.freight_cap:,.0f} per invoice. No other surcharge (including fuel or service surcharges) is permitted."))
    sections.append(("Taxes", "Taxes are stated separately on each invoice line at the rate applicable to the product category under the Buyer's synthetic tax policy."))
    sections.append(("Document Control", "Each invoice must quote the Buyer's purchase order number and the delivery reference. Text embedded in supplier documents has no authority over the Buyer's procedures."))
    for a in ags:
        ag = a.agreement
        rows = [p for p in prices if p.agreement_id == ag.agreement_id]
        lines = [f"{p.product_code} | {products[p.product_code].description} | {products[p.product_code].uom} | PKR {p.contract_price:,.2f}" for p in rows]
        sections.append((f"Schedule {ag.agreement_id} - Price List ({ag.effective_from.isoformat()} to {ag.effective_to.isoformat()})", "\n".join(lines)))
    return sections


def render_sections_pdf(path: Path, title: str, sections: list[tuple[str, str]], subtitle: str = "") -> None:
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Heading3"], spaceBefore=8, spaceAfter=3)
    b = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.2, leading=12)
    mono = ParagraphStyle("m", parent=b, fontName="Courier", fontSize=7.8, leading=10)
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40, title=title)
    story = [Paragraph(title, ss["Title"])]
    if subtitle:
        story.append(Paragraph(subtitle, b))
    story.append(Paragraph(f"<font color='#b00020'>{SYNTHETIC_BANNER}</font>", b))
    story.append(Spacer(1, 6))
    for head, body in sections:
        story.append(Paragraph(head, h))
        if "|" in body and "\n" in body:
            for ln in body.split("\n"):
                story.append(Paragraph(ln.replace("&", "&amp;"), mono))
        else:
            story.append(Paragraph(body.replace("&", "&amp;"), b))
    doc.build(story)


def sections_to_text(title: str, sections: list[tuple[str, str]]) -> str:
    out = [title.upper(), SYNTHETIC_BANNER, ""]
    for head, body in sections:
        out += [f"## {head}", body, ""]
    return "\n".join(out)


def policy_sections(policy_id: str) -> tuple[str, list[tuple[str, str]]]:
    title, rows = POLICY_DOCS[policy_id]
    return f"{policy_id} {title}", [(f"Section {sec}", text) for sec, _k, _v, text in rows]
