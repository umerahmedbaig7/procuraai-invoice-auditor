"""Build schema records from the structured CSV/XLSX tables (the 'structured' input path)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..audit.money import to_decimal
from ..normalization import normalize_currency, normalize_uom, parse_date
from ..schemas import (Charge, DCLine, DeliveryChallanRecord, InvoiceRecord, LineItem, POLine, PolicyRule, PriceListEntry,
                       ProductInfo, PurchaseOrderRecord, SupplierAgreement, SupplierInfo)


def _n(x):
    return None if x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() in ("", "nan", "None") else str(x).strip()


def invoices_from_df(df: pd.DataFrame) -> list[InvoiceRecord]:
    out = []
    for iid, g in df.groupby("invoice_id", sort=False):
        h = g.iloc[0]
        inv = InvoiceRecord(source_file=_n(h.get("source_file")) or "", invoice_id=iid, invoice_number=_n(h["invoice_number"]), invoice_date=parse_date(_n(h["invoice_date"])),
                            due_date=parse_date(_n(h.get("due_date"))), supplier_name=_n(h["supplier_name"]), supplier_id=_n(h.get("supplier_id_printed")),
                            supplier_tax_id=_n(h.get("supplier_tax_id")), po_number=_n(h.get("po_number")), dc_reference=_n(h.get("dc_reference")),
                            currency=normalize_currency(_n(h.get("currency"))), payment_terms=_n(h.get("payment_terms")), subtotal=to_decimal(_n(h.get("subtotal"))),
                            tax_total=to_decimal(_n(h.get("tax_total"))), grand_total=to_decimal(_n(h.get("grand_total"))), extraction_method="csv")
        for _, r in g.iterrows():
            if r["line_type"] == "CHARGE":
                inv.charges.append(Charge(charge_type=_n(r["charge_type"]) or "OTHER", description=_n(r["description"]) or "", amount=to_decimal(_n(r["line_amount"]))))
            else:
                inv.lines.append(LineItem(line_no=int(r["line_no"]), product_code=_n(r["product_code"]), description=_n(r["description"]) or "", quantity=to_decimal(_n(r["quantity"])),
                                          uom=normalize_uom(_n(r["uom"])), unit_price=to_decimal(_n(r["unit_price"])), discount_pct=to_decimal(_n(r["discount_pct"])),
                                          line_amount=to_decimal(_n(r["line_amount"])), tax_rate=to_decimal(_n(r["tax_rate"])), tax_amount=to_decimal(_n(r["tax_amount"]))))
        out.append(inv)
    return out


def pos_from_df(df: pd.DataFrame) -> list[PurchaseOrderRecord]:
    out = []
    for pn, g in df.groupby("po_number", sort=False):
        h = g.iloc[0]
        out.append(PurchaseOrderRecord(source_file=_n(h.get("source_file")) or "", po_number=pn, po_date=parse_date(_n(h["po_date"])), supplier_id=_n(h["supplier_id"]),
                                       supplier_name=_n(h["supplier_name"]), currency=normalize_currency(_n(h["currency"])), payment_terms=_n(h["payment_terms"]),
                                       expected_delivery_date=parse_date(_n(h["expected_delivery_date"])), total=to_decimal(_n(h["total"])), extraction_method="csv",
                                       lines=[POLine(line_no=int(r["line_no"]), product_code=_n(r["product_code"]), description=_n(r["description"]) or "", quantity=to_decimal(_n(r["quantity"])),
                                                     uom=normalize_uom(_n(r["uom"])), unit_price=to_decimal(_n(r["unit_price"])), line_amount=to_decimal(_n(r["line_amount"]))) for _, r in g.iterrows()]))
    return out


def dcs_from_df(df: pd.DataFrame) -> list[DeliveryChallanRecord]:
    out = []
    for dn, g in df.groupby("dc_number", sort=False):
        h = g.iloc[0]
        out.append(DeliveryChallanRecord(source_file=_n(h.get("source_file")) or "", dc_number=dn, dc_date=parse_date(_n(h["dc_date"])), po_number=_n(h["po_number"]),
                                         supplier_id=_n(h["supplier_id"]), supplier_name=_n(h["supplier_name"]), remarks=_n(h.get("remarks")), extraction_method="csv",
                                         lines=[DCLine(line_no=int(r["line_no"]), product_code=_n(r["product_code"]), description=_n(r["description"]) or "",
                                                       quantity_received=to_decimal(_n(r["quantity_received"])), uom=normalize_uom(_n(r["uom"]))) for _, r in g.iterrows()]))
    return out


def suppliers_from_df(df: pd.DataFrame) -> list[SupplierInfo]:
    return [SupplierInfo(supplier_id=r["supplier_id"], name=r["name"], tax_id=_n(r["tax_id"]), address=_n(r["address"]), city=_n(r["city"]), payment_terms=_n(r["payment_terms"]),
                         aliases=[a for a in str(r["aliases"]).split("|") if a], categories=[a for a in str(r["categories"]).split("|") if a],
                         volume_discount_min_qty=to_decimal(r["volume_discount_min_qty"]) or 0, volume_discount_pct=to_decimal(r["volume_discount_pct"]) or 0,
                         status=_n(r.get("status")) or "ACTIVE") for _, r in df.iterrows()]


def products_from_df(df: pd.DataFrame) -> list[ProductInfo]:
    return [ProductInfo(product_code=r["product_code"], description=r["description"], category=r["category"], uom=r["uom"], list_price=to_decimal(r["list_price"]),
                        aliases=[a for a in str(r["aliases"]).split("|") if a]) for _, r in df.iterrows()]


def agreements_from_df(df: pd.DataFrame) -> list[SupplierAgreement]:
    return [SupplierAgreement(agreement_id=r["agreement_id"], supplier_id=r["supplier_id"], effective_from=parse_date(r["effective_from"]), effective_to=parse_date(r["effective_to"]),
                              currency=r["currency"], payment_terms=_n(r["payment_terms"]), volume_discount_min_qty=to_decimal(r["volume_discount_min_qty"]) or 0,
                              volume_discount_pct=to_decimal(r["volume_discount_pct"]) or 0, freight_policy=r["freight_policy"], freight_cap=to_decimal(r["freight_cap"]) or 0,
                              allowed_charge_types=[a for a in str(r["allowed_charge_types"]).split("|") if a and a != "nan"]) for _, r in df.iterrows()]


def price_list_from_df(df: pd.DataFrame) -> list[PriceListEntry]:
    return [PriceListEntry(agreement_id=r["agreement_id"], supplier_id=r["supplier_id"], product_code=r["product_code"], contract_price=to_decimal(r["contract_price"]),
                           currency=r["currency"], effective_from=parse_date(r["effective_from"]), effective_to=parse_date(r["effective_to"])) for _, r in df.iterrows()]


def policies_from_df(df: pd.DataFrame) -> list[PolicyRule]:
    return [PolicyRule(policy_id=r["policy_id"], rule_key=r["rule_key"], rule_value=str(r["rule_value"]), text=r["text"], source_file=f"{r['policy_id']}.txt") for _, r in df.iterrows()]


def load_structured_dir(d: str | Path) -> dict:
    d = Path(d)
    rd = lambda n: pd.read_csv(d / f"{n}.csv", dtype=str, keep_default_na=False)
    return dict(invoices=invoices_from_df(rd("invoices")), purchase_orders=pos_from_df(rd("purchase_orders")), delivery_challans=dcs_from_df(rd("delivery_challans")),
                suppliers=suppliers_from_df(rd("supplier_master")), products=products_from_df(rd("product_master")), agreements=agreements_from_df(rd("supplier_agreements")),
                price_list=price_list_from_df(rd("supplier_price_list")), policies=policies_from_df(rd("procurement_policies")))
