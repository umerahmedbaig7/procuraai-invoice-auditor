"""Write the generated dataset to disk (documents, structured CSV/XLSX, ground truth, manifest, ZIP) and
validate cross-document integrity BEFORE anything is saved."""
from __future__ import annotations

import json
import random
import re
import shutil
import tempfile
import zipfile
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

import pandas as pd

from .. import taxonomy as T
from ..audit.money import ZERO, line_net, tax_on
from . import render as R
from .catalog import POLICY_DOCS, SYNTHETIC_BANNER
from .generator import Dataset, contract_price

DIRS = ["raw/invoices/pdf", "raw/invoices/images", "raw/invoices/text", "raw/purchase_orders/pdf", "raw/purchase_orders/images",
        "raw/delivery_challans/pdf", "raw/delivery_challans/images", "raw/contracts", "raw/policies", "structured", "ground_truth",
        "processed", "reports", "manifest"]


class DatasetIntegrityError(RuntimeError):
    pass


# ---------------------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------------------
def validate_dataset(ds: Dataset) -> dict:
    """Return summary stats or raise DatasetIntegrityError listing every problem found."""
    errs: list[str] = []
    p = ds.profile
    prods = {x.product_code: x for x in p.products}
    sups = {s.info.supplier_id: s for s in p.suppliers}
    pos = {x.po_number: x for x in ds.pos}
    dcs = {x.dc_number: x for x in ds.dcs}
    labels_by_inv: dict[str, list[dict]] = defaultdict(list)
    for g in ds.gt:
        labels_by_inv[g["invoice_id"]].append(g)
        if g["anomaly_code"] != "NONE" and g["anomaly_code"] not in T.CODES:
            errs.append(f"GT {g['invoice_id']}: unknown anomaly code {g['anomaly_code']}")
    inv_ids = {i.invoice_id for i in ds.invoices}
    if len(inv_ids) != len(ds.invoices):
        errs.append("duplicate invoice ids")
    names = list(ds.doc_format)
    if len(set(names)) != len(names):
        errs.append("duplicate file names")
    for iid in labels_by_inv:
        if iid not in inv_ids:
            errs.append(f"GT references unknown invoice {iid}")
    for inv in ds.invoices:
        labs = labels_by_inv.get(inv.invoice_id)
        if not labs:
            errs.append(f"{inv.invoice_id}: no ground-truth rows")
            continue
        codes = {g["anomaly_code"] for g in labs}
        for g in labs:
            if g["line_no"] is not None and not any(l.line_no == int(g["line_no"]) for l in inv.lines):
                errs.append(f"{inv.invoice_id}: GT line_no {g['line_no']} not on invoice")
        if "UNKNOWN_SUPPLIER" not in codes and inv.supplier_id is None and inv.supplier_name:
            pass
        # reference integrity
        sup_id = ds.invoice_meta[inv.invoice_id]["supplier_id"]
        if sup_id not in sups and "UNKNOWN_SUPPLIER" not in codes:
            errs.append(f"{inv.invoice_id}: supplier {sup_id} not in master and not labelled")
        if inv.po_number not in pos and "MISSING_PO" not in codes:
            errs.append(f"{inv.invoice_id}: PO {inv.po_number} missing but not labelled MISSING_PO")
        if inv.po_number in pos and "MISSING_PO" in codes:
            errs.append(f"{inv.invoice_id}: labelled MISSING_PO but PO exists")
        refs = [r.strip() for r in (inv.dc_reference or "").split(",") if r.strip()]
        for r in refs:
            if r not in dcs and not ({"MISSING_DC", "DATE_REFERENCE_INCONSISTENT"} & codes):
                errs.append(f"{inv.invoice_id}: DC ref {r} missing but not labelled")
        po_dcs = [d for d in ds.dcs if d.po_number == inv.po_number]
        if "MISSING_DC" in codes and po_dcs:
            errs.append(f"{inv.invoice_id}: labelled MISSING_DC but DCs exist for PO")
        for l in inv.lines:
            if l.product_code and l.product_code not in prods and "UNKNOWN_PRODUCT_CODE" not in codes:
                errs.append(f"{inv.invoice_id}: unknown product {l.product_code} not labelled")
        # clean-invoice arithmetic/consistency (independent re-derivation)
        if codes == {"NONE"} or codes <= {"NONE"}:
            po = pos.get(inv.po_number)
            if po is None:
                errs.append(f"{inv.invoice_id}: clean but PO missing")
                continue
            sup = sups[sup_id]
            for l in inv.lines:
                pl = next((x for x in po.lines if x.product_code == l.product_code), None)
                if pl is None:
                    errs.append(f"{inv.invoice_id}: clean line {l.product_code} not on PO"); continue
                recv = sum((dl.quantity_received for d in po_dcs for dl in d.lines if dl.product_code == l.product_code), ZERO)
                if not (l.quantity <= pl.quantity and l.quantity <= recv):
                    errs.append(f"{inv.invoice_id}: clean line {l.product_code} qty {l.quantity} vs PO {pl.quantity} / recv {recv}")
                price = contract_price(prods[l.product_code].list_price, sup.price_factor,
                                       next(a.price_adj for a in p.agreements if a.agreement.supplier_id == sup_id and a.agreement.effective_from <= po.po_date <= a.agreement.effective_to))
                if l.unit_price != price or pl.unit_price != price:
                    errs.append(f"{inv.invoice_id}: clean price mismatch {l.product_code}")
                dpc = sup.info.volume_discount_pct if (sup.info.volume_discount_min_qty > 0 and pl.quantity >= sup.info.volume_discount_min_qty) else D("0")
                if (l.discount_pct or D("0")) != dpc:
                    errs.append(f"{inv.invoice_id}: clean discount mismatch {l.product_code}")
                net = line_net(l.quantity, l.unit_price, l.discount_pct or ZERO)
                if l.line_amount != net or l.tax_amount != tax_on(net, l.tax_rate) or l.tax_rate != p.tax_rates[prods[l.product_code].category]:
                    errs.append(f"{inv.invoice_id}: clean arithmetic/tax mismatch {l.product_code}")
            sub = sum((l.line_amount for l in inv.lines), ZERO)
            tax = sum((l.tax_amount for l in inv.lines), ZERO)
            ch = sum((c.amount for c in inv.charges), ZERO)
            if inv.subtotal != sub or inv.tax_total != tax or inv.grand_total != sub + tax + ch:
                errs.append(f"{inv.invoice_id}: clean totals mismatch")
            for c in inv.charges:
                if c.charge_type not in sup.charges_allowed or c.amount > sup.freight_cap:
                    errs.append(f"{inv.invoice_id}: clean charge not permitted")
            last_dc = max(d.dc_date for d in po_dcs)
            if not (po.po_date <= last_dc <= inv.invoice_date):
                errs.append(f"{inv.invoice_id}: clean date order violated")
            if inv.currency != p.currency:
                errs.append(f"{inv.invoice_id}: clean currency")
    for d in ds.dcs:
        if d.po_number not in pos and not any(("MISSING_PO" in {g["anomaly_code"] for g in labels_by_inv[i.invoice_id]}) and i.po_number == d.po_number for i in ds.invoices):
            errs.append(f"{d.dc_number}: references PO {d.po_number} that does not exist")
        for l in d.lines:
            if l.product_code not in prods and l.product_code != "ELE-9901":
                errs.append(f"{d.dc_number}: unknown product {l.product_code}")
    for po in ds.pos:
        for l in po.lines:
            if l.product_code not in prods and l.product_code != "ELE-9901":
                errs.append(f"{po.po_number}: unknown product {l.product_code}")
    fm = defaultdict(int)
    for fn, f in ds.doc_format.items():
        fm[(fn.split("_")[0].split("-")[0], f)] += 1
    n_clean = sum(1 for i in ds.invoices if {g["anomaly_code"] for g in labels_by_inv[i.invoice_id]} == {"NONE"})
    n_anom = sum(1 for i in ds.invoices if any(T.CODES.get(g["anomaly_code"]) and T.CODES[g["anomaly_code"]].severity != "INFO" for g in labels_by_inv[i.invoice_id]))
    inv_pdf = sum(1 for i in ds.invoices if i.source_file.endswith(".pdf"))
    po_pdf = sum(1 for x in ds.pos if x.source_file.endswith(".pdf"))
    dc_pdf = sum(1 for x in ds.dcs if x.source_file.endswith(".pdf"))
    images = sum(1 for fn in ds.doc_format if fn.endswith((".png", ".jpg")))
    mins = [("suppliers", len(p.suppliers), 8), ("purchase_orders", len(ds.pos), 40), ("delivery_challans", len(ds.dcs), 40), ("invoices", len(ds.invoices), 60),
            ("products", len(p.products), 40), ("clean_invoices", n_clean, 20), ("anomalous_invoices", n_anom, 20), ("pdf_invoices", inv_pdf, 10),
            ("pdf_pos", po_pdf, 8), ("pdf_dcs", dc_pdf, 8), ("image_documents", images, 8)]
    for name, have, need in mins:
        if have < need:
            errs.append(f"requirement not met: {name} = {have} < {need}")
    if errs:
        raise DatasetIntegrityError("Dataset integrity check failed:\n - " + "\n - ".join(errs[:60]) + (f"\n ... and {len(errs) - 60} more" if len(errs) > 60 else ""))
    return {k: v for k, v, _ in mins} | {"checks": "all passed"}


# ---------------------------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------------------------
def _s(x):
    return None if x is None else str(x)


def tables(ds: Dataset) -> dict[str, pd.DataFrame]:
    p = ds.profile
    inv_rows = []
    for inv in ds.invoices:
        head = dict(invoice_id=inv.invoice_id, source_file=inv.source_file, invoice_number=inv.invoice_number, invoice_date=_s(inv.invoice_date),
                    due_date=_s(inv.due_date), supplier_name=inv.supplier_name, supplier_id_printed=inv.supplier_id, supplier_tax_id=inv.supplier_tax_id,
                    po_number=inv.po_number, dc_reference=inv.dc_reference, currency=inv.currency, payment_terms=inv.payment_terms,
                    subtotal=_s(inv.subtotal), tax_total=_s(inv.tax_total), grand_total=_s(inv.grand_total))
        for l in inv.lines:
            inv_rows.append(head | dict(line_type="ITEM", line_no=l.line_no, product_code=l.product_code, description=l.description, quantity=_s(l.quantity), uom=l.uom,
                                        unit_price=_s(l.unit_price), discount_pct=_s(l.discount_pct), line_amount=_s(l.line_amount), tax_rate=_s(l.tax_rate),
                                        tax_amount=_s(l.tax_amount), charge_type=None))
        for k, c in enumerate(inv.charges, 1):
            inv_rows.append(head | dict(line_type="CHARGE", line_no=100 + k, product_code=None, description=c.description, quantity=None, uom=None, unit_price=None,
                                        discount_pct=None, line_amount=_s(c.amount), tax_rate=None, tax_amount=None, charge_type=c.charge_type))
    po_rows = [dict(po_number=po.po_number, po_date=_s(po.po_date), supplier_id=po.supplier_id, supplier_name=po.supplier_name, currency=po.currency,
                    payment_terms=po.payment_terms, expected_delivery_date=_s(po.expected_delivery_date), total=_s(po.total), source_file=po.source_file,
                    line_no=l.line_no, product_code=l.product_code, description=l.description, quantity=_s(l.quantity), uom=l.uom, unit_price=_s(l.unit_price),
                    line_amount=_s(l.line_amount)) for po in ds.pos for l in po.lines]
    dc_rows = [dict(dc_number=d.dc_number, dc_date=_s(d.dc_date), po_number=d.po_number, supplier_id=d.supplier_id, supplier_name=d.supplier_name, remarks=d.remarks,
                    source_file=d.source_file, line_no=l.line_no, product_code=l.product_code, description=l.description, quantity_received=_s(l.quantity_received),
                    uom=l.uom) for d in ds.dcs for l in d.lines]
    sup_rows = [dict(supplier_id=s.info.supplier_id, name=s.info.name, tax_id=s.info.tax_id, address=s.info.address, city=s.info.city,
                     payment_terms=s.info.payment_terms, aliases="|".join(s.info.aliases), categories="|".join(s.info.categories),
                     volume_discount_min_qty=_s(s.info.volume_discount_min_qty), volume_discount_pct=_s(s.info.volume_discount_pct), status="ACTIVE") for s in p.suppliers]
    prod_rows = [dict(product_code=x.product_code, description=x.description, category=x.category, uom=x.uom, list_price=_s(x.list_price), aliases="|".join(x.aliases)) for x in p.products]
    ag_rows = [dict(agreement_id=a.agreement_id, supplier_id=a.supplier_id, effective_from=_s(a.effective_from), effective_to=_s(a.effective_to), currency=a.currency,
                    payment_terms=a.payment_terms, volume_discount_min_qty=_s(a.volume_discount_min_qty), volume_discount_pct=_s(a.volume_discount_pct),
                    freight_policy=a.freight_policy, freight_cap=_s(a.freight_cap), allowed_charge_types="|".join(a.allowed_charge_types)) for a in ds.agreements]
    pl_rows = [dict(agreement_id=e.agreement_id, supplier_id=e.supplier_id, product_code=e.product_code, contract_price=_s(e.contract_price), currency=e.currency,
                    effective_from=_s(e.effective_from), effective_to=_s(e.effective_to)) for e in ds.price_list]
    pol_rows = [dict(policy_id=pid, policy_title=title, section=sec, rule_key=k, rule_value=v, text=text) for pid, (title, rows) in POLICY_DOCS.items() for sec, k, v, text in rows]
    return dict(invoices=pd.DataFrame(inv_rows), purchase_orders=pd.DataFrame(po_rows), delivery_challans=pd.DataFrame(dc_rows), supplier_master=pd.DataFrame(sup_rows),
                product_master=pd.DataFrame(prod_rows), supplier_agreements=pd.DataFrame(ag_rows), supplier_price_list=pd.DataFrame(pl_rows),
                procurement_policies=pd.DataFrame(pol_rows))


def _subdir(kind: str, fmt_ext: str) -> str:
    base = {"INVOICE": "raw/invoices", "PURCHASE_ORDER": "raw/purchase_orders", "DELIVERY_CHALLAN": "raw/delivery_challans"}[kind]
    if fmt_ext in ("png", "jpg"):
        return f"{base}/images"
    if fmt_ext == "txt":
        return f"{base}/text"
    return f"{base}/pdf"


# ---------------------------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------------------------
def write_dataset(ds: Dataset, root: str | Path, make_zip: bool = True) -> dict:
    root = Path(root)
    stats = validate_dataset(ds)          # stop before writing anything if references are inconsistent
    if root.exists():
        shutil.rmtree(root)
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    rng = random.Random(ds.seed + 99)
    p = ds.profile
    sups = {s.info.supplier_id: s for s in p.suppliers}
    all_sinfo = {**{k: v.info for k, v in sups.items()}, p.unknown_supplier.supplier_id: p.unknown_supplier}
    paths: dict[str, str] = {}
    tmp = Path(tempfile.mkdtemp())

    def emit_doc(kind: str, fname: str, fmt: str, pdf_maker, txt_maker=None, level_png="scan"):
        ext = fname.rsplit(".", 1)[1]
        sub = _subdir(kind, ext)
        out = root / sub / fname
        if fmt == "pdf_text":
            pdf_maker(out)
        elif fmt == "txt":
            out.write_text(txt_maker(), encoding="utf-8")
        else:
            tp = tmp / (fname + ".tmp.pdf")
            pdf_maker(tp)
            img = R.rasterize(tp, dpi=200 if fmt != "pdf_scan" else 170)
            if fmt == "pdf_scan":
                R.image_to_pdf(R.degrade(img, "scan", rng), out)
            elif fmt == "png":
                R.save_image_doc(R.degrade(img, level_png, rng), out, "png")
            else:
                R.save_image_doc(R.degrade(img, "photo", rng), out, "jpg")
        paths[fname] = f"{sub}/{fname}"

    for inv in ds.invoices:
        meta = ds.invoice_meta[inv.invoice_id]
        sid = meta["supplier_id"]
        sup = sups.get(sid)
        style = sup.date_style if sup else "%d-%b-%Y"
        sinfo = all_sinfo[sid]
        tpl = meta["template"]
        fmt = ds.doc_format[inv.source_file]
        emit_doc("INVOICE", inv.source_file, fmt,
                 lambda out, inv=inv, sup=sup, sinfo=sinfo, tpl=tpl, style=style: R.render_invoice_pdf(inv, sup, sinfo, tpl, p, out, style),
                 lambda inv=inv, sinfo=sinfo, tpl=tpl, style=style: R.render_invoice_txt(inv, sinfo, tpl, p, style),
                 level_png="scan" if meta.get("tag") == "rescan_copy" else "clean")
    for i, po in enumerate(ds.pos):
        emit_doc("PURCHASE_ORDER", po.source_file, ds.doc_format[po.source_file],
                 lambda out, po=po, i=i: R.render_po_pdf(po, all_sinfo[po.supplier_id], p, out, variant=i % 2), level_png="scan")
    for i, dc in enumerate(ds.dcs):
        emit_doc("DELIVERY_CHALLAN", dc.source_file, ds.doc_format[dc.source_file],
                 lambda out, dc=dc, i=i: R.render_dc_pdf(dc, all_sinfo[dc.supplier_id], p, out, variant=i % 2), level_png="scan")

    # contracts (PDF + TXT) and policies (PDF + TXT + combined markdown)
    prods = {x.product_code: x for x in p.products}
    for s in p.suppliers:
        ags = [a for a in p.agreements if a.agreement.supplier_id == s.info.supplier_id]
        pr = [e for e in ds.price_list if e.supplier_id == s.info.supplier_id]
        secs = R.contract_text(s, ags, pr, prods, p)
        title = f"Supply and Pricing Agreement - {s.info.name}"
        R.render_sections_pdf(root / "raw/contracts" / f"CONTRACT_{s.info.supplier_id}.pdf", title, secs, f"Supplier code {s.info.supplier_id}")
        (root / "raw/contracts" / f"CONTRACT_{s.info.supplier_id}.txt").write_text(R.sections_to_text(title, secs), encoding="utf-8")
    md = ["# Procurement Policies (Synthetic)", "", f"> {SYNTHETIC_BANNER}", ""]
    for pid in POLICY_DOCS:
        title, secs = R.policy_sections(pid)
        R.render_sections_pdf(root / "raw/policies" / f"{pid}.pdf", title, secs)
        (root / "raw/policies" / f"{pid}.txt").write_text(R.sections_to_text(title, secs), encoding="utf-8")
        md += [f"## {title}", ""] + [f"- **{h}**: {b}" for h, b in secs] + [""]
    (root / "raw/policies" / "procurement_policies_summary.md").write_text("\n".join(md), encoding="utf-8")

    # structured data
    t = tables(ds)
    for name in ("invoices", "purchase_orders", "delivery_challans", "supplier_master", "product_master", "supplier_price_list", "procurement_policies", "supplier_agreements"):
        t[name].to_csv(root / "structured" / f"{name}.csv", index=False)
    pd.DataFrame(ds.registry).to_csv(root / "structured/document_registry.csv", index=False)
    gt = pd.DataFrame(ds.gt)
    gt.insert(0, "gt_id", [f"GT-{i:04d}" for i in range(1, len(gt) + 1)])
    gt.to_csv(root / "ground_truth/ground_truth.csv", index=False)
    pd.DataFrame(ds.expected).to_csv(root / "ground_truth/expected_values.csv", index=False)
    (root / "ground_truth/README.txt").write_text("EVALUATION ONLY. These files must never be given to the audit agents during inference.\n", encoding="utf-8")
    with pd.ExcelWriter(root / "structured/procurement_master_data.xlsx", engine="openpyxl") as xw:
        pd.DataFrame({"note": ["SYNTHETIC DATA - fictional companies, products and transactions.", "Tax rates are synthetic configuration, not Pakistani tax law.",
                               "Ground truth is intentionally NOT in this workbook."]}).to_excel(xw, sheet_name="README", index=False)
        sheet = {"supplier_master": "Suppliers", "product_master": "Products", "supplier_agreements": "Agreements", "supplier_price_list": "PriceList",
                 "procurement_policies": "Policies", "purchase_orders": "PO_Lines", "delivery_challans": "DC_Lines", "invoices": "Invoice_Lines"}
        for k, name in sheet.items():
            t[k].to_excel(xw, sheet_name=name, index=False)
        hdr = t["invoices"].drop_duplicates("invoice_id")[["invoice_id", "source_file", "invoice_number", "invoice_date", "supplier_name", "po_number", "dc_reference", "currency", "subtotal", "tax_total", "grand_total"]]
        hdr.to_excel(xw, sheet_name="Invoice_Headers", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(45, max(10, max(len(str(c.value or "")) for c in col[:60]) + 2))

    # manifest (contains ground-truth labels: evaluation only)
    labs = defaultdict(list)
    for g in ds.gt:
        labs[g["invoice_id"]].append(g)
    man = []
    dcs_by_po = defaultdict(list)
    for d in ds.dcs:
        dcs_by_po[d.po_number].append(d.dc_number)
    for inv in ds.invoices:
        L = labs[inv.invoice_id]
        codes = sorted({g["anomaly_code"] for g in L if g["anomaly_code"] != "NONE"})
        man.append(dict(filename=inv.source_file, relative_path=paths[inv.source_file], document_type="INVOICE", format=ds.doc_format[inv.source_file],
                        supplier_id=ds.invoice_meta[inv.invoice_id]["supplier_id"], document_id=inv.invoice_number, related_po=inv.po_number,
                        related_dc="|".join(dcs_by_po.get(inv.po_number, [])), expected_anomalies="|".join(codes) or "NONE",
                        scenario_nos="|".join(str(s) for s in sorted({g["scenario_no"] for g in L})), ground_truth_label="CLEAN" if not codes else ("INFO_ONLY" if all(T.CODES[c].severity == "INFO" for c in codes) else "ANOMALOUS")))
    for po in ds.pos:
        man.append(dict(filename=po.source_file, relative_path=paths[po.source_file], document_type="PURCHASE_ORDER", format=ds.doc_format[po.source_file], supplier_id=po.supplier_id,
                        document_id=po.po_number, related_po=po.po_number, related_dc="|".join(dcs_by_po.get(po.po_number, [])), expected_anomalies="", scenario_nos="", ground_truth_label=""))
    for d in ds.dcs:
        man.append(dict(filename=d.source_file, relative_path=paths[d.source_file], document_type="DELIVERY_CHALLAN", format=ds.doc_format[d.source_file], supplier_id=d.supplier_id,
                        document_id=d.dc_number, related_po=d.po_number, related_dc=d.dc_number, expected_anomalies="", scenario_nos="", ground_truth_label=""))
    for s in p.suppliers:
        for ext in ("pdf", "txt"):
            fn = f"CONTRACT_{s.info.supplier_id}.{ext}"
            man.append(dict(filename=fn, relative_path=f"raw/contracts/{fn}", document_type="CONTRACT", format=ext, supplier_id=s.info.supplier_id, document_id=fn.split(".")[0],
                            related_po="", related_dc="", expected_anomalies="", scenario_nos="", ground_truth_label=""))
    for pid in POLICY_DOCS:
        for ext in ("pdf", "txt"):
            fn = f"{pid}.{ext}"
            man.append(dict(filename=fn, relative_path=f"raw/policies/{fn}", document_type="POLICY", format=ext, supplier_id="", document_id=pid, related_po="", related_dc="",
                            expected_anomalies="", scenario_nos="", ground_truth_label=""))
    mdf = pd.DataFrame(man)
    mdf.to_csv(root / "manifest/dataset_manifest.csv", index=False)
    (root / "manifest/dataset_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    (root / "manifest/README.txt").write_text("The manifest contains ground-truth labels (expected_anomalies). EVALUATION ONLY.\n", encoding="utf-8")
    (root / "README.txt").write_text(
        f"ProcuraAI synthetic procurement dataset (seed {ds.seed}).\n{SYNTHETIC_BANNER}\n\n"
        "raw/            documents (PDF, PNG/JPG, TXT) - the only thing an audit run may read, plus structured/\n"
        "structured/     CSV/XLSX master data and transaction tables (observed values, no labels)\n"
        "ground_truth/   labels and expected values - EVALUATION ONLY\nmanifest/       file inventory with labels - EVALUATION ONLY\n"
        "processed/ reports/   outputs written by the pipeline\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    out = dict(stats=stats, root=str(root), files=len(paths) + 16 + len(man))
    if make_zip:
        zp = root.parent / "procuraai_synthetic_dataset.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in sorted(root.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(root.parent))
        out["zip"] = str(zp)
        out["zip_mb"] = round(zp.stat().st_size / 1e6, 2)
    return out
