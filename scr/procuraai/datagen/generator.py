"""Deterministic generator of related synthetic procurement transactions with labelled anomalies.

Design rules (see docs/architecture.md):
* Every transaction is first built CLEAN (PO -> delivery record(s) -> invoice) with the shared Decimal
  money rules, so clean cases cannot contain accidental anomalies.
* Anomalies are injected one scenario at a time; the injected invoice is kept internally consistent
  except for the specific defect, and ground-truth labels are written at injection time.
* Ground truth lives in its own tables and is never passed to the audit agents.
* A fixed seed makes the whole dataset reproducible.
"""
from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal as D

from .. import taxonomy as T
from ..audit.money import ZERO, line_net, tax_on
from ..schemas import (Charge, DCLine, DeliveryChallanRecord, InvoiceRecord, LineItem, POLine,
                       PriceListEntry, ProductInfo, PurchaseOrderRecord, SupplierAgreement, SupplierInfo)
from .catalog import AgreementSpec, Profile, SupplierSpec


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def contract_price(list_price: D, factor: D, adj: D) -> D:
    v = list_price * factor * adj
    return v.quantize(D("1")) if v >= 100 else v.quantize(D("0.01"))


def recompute(inv: InvoiceRecord, has_tax: bool = True, keep_line_amounts: bool = False) -> None:
    """Make an invoice internally consistent from line quantity/price/discount/tax rate."""
    for l in inv.lines:
        if not keep_line_amounts:
            l.line_amount = line_net(l.quantity, l.unit_price, l.discount_pct or ZERO)
        if has_tax and l.tax_rate is not None:
            l.tax_amount = tax_on(l.line_amount, l.tax_rate)
        elif not has_tax:
            l.tax_rate, l.tax_amount = None, None
    inv.subtotal = sum((l.line_amount for l in inv.lines), ZERO)
    inv.tax_total = sum((l.tax_amount or ZERO for l in inv.lines), ZERO) if has_tax else None
    inv.grand_total = inv.subtotal + (inv.tax_total or ZERO) + sum((c.amount for c in inv.charges), ZERO)


def _net_days(terms: str | None) -> int:
    m = re.search(r"(\d+)", terms or "")
    return int(m.group(1)) if m else 30


@dataclass
class Txn:
    sup: SupplierSpec | None
    sinfo: SupplierInfo
    po: PurchaseOrderRecord
    dcs: list[DeliveryChallanRecord]
    inv: InvoiceRecord
    true_inv: InvoiceRecord
    keep_po: bool = True
    keep_dcs: bool = True
    key: int = 0


@dataclass
class Dataset:
    profile: Profile
    seed: int
    pos: list[PurchaseOrderRecord] = field(default_factory=list)
    dcs: list[DeliveryChallanRecord] = field(default_factory=list)
    invoices: list[InvoiceRecord] = field(default_factory=list)
    gt: list[dict] = field(default_factory=list)
    expected: list[dict] = field(default_factory=list)
    doc_format: dict[str, str] = field(default_factory=dict)       # file name -> render format
    invoice_meta: dict[str, dict] = field(default_factory=dict)    # invoice_id -> {scenario, supplier template...}
    price_list: list[PriceListEntry] = field(default_factory=list)
    agreements: list[SupplierAgreement] = field(default_factory=list)
    registry: list[dict] = field(default_factory=list)
    intentional_dangling: dict[str, str] = field(default_factory=dict)  # file -> reason (for validation)


FORMAT_CYCLE = ["pdf_text", "pdf_text", "pdf_scan", "pdf_text", "png", "pdf_text", "jpg", "txt", "pdf_text", "pdf_text", "png", "pdf_text"]
PO_FORMATS = ["pdf_text"] * 5 + ["pdf_scan"] + ["pdf_text"] * 4 + ["png"] + ["pdf_text"] * 3 + ["jpg"]
DC_FORMATS = ["pdf_text"] * 4 + ["jpg"] + ["pdf_text"] * 3 + ["pdf_scan"] + ["pdf_text"] * 4 + ["png"]


class Generator:
    def __init__(self, profile: Profile, seed: int = 20250101, n_clean: int = 22):
        self.p = profile
        self.seed = seed
        self.rng = random.Random(seed)
        self.n_clean = n_clean
        self.sups = {s.info.supplier_id: s for s in profile.suppliers}
        self.products = {x.product_code: x for x in profile.products}
        self.by_cat: dict[str, list[ProductInfo]] = {}
        for x in profile.products:
            self.by_cat.setdefault(x.category, []).append(x)
        self.ag_by_sup: dict[str, list[AgreementSpec]] = {}
        for a in profile.agreements:
            self.ag_by_sup.setdefault(a.agreement.supplier_id, []).append(a)
        self.po_n = 0
        self.dc_n = 0
        self.sup_inv_n = {sid: self.rng.randint(100, 400) for sid in self.sups}
        self.txns: list[Txn] = []
        self.pending: list[dict] = []     # emitted invoices awaiting final id assignment
        self.key_n = 0

    # ------------------------------------------------------------------ lookups
    def agreement_at(self, sid: str, d: date) -> AgreementSpec | None:
        for a in self.ag_by_sup.get(sid, []):
            if a.agreement.effective_from <= d <= a.agreement.effective_to:
                return a
        return None

    def price_at(self, sid: str, code: str, d: date) -> D | None:
        a = self.agreement_at(sid, d)
        if a is None:
            return None
        return contract_price(self.products[code].list_price, self.sups[sid].price_factor, a.price_adj)

    def _qty(self, prod: ProductInfo) -> D:
        r, u = self.rng, prod.uom
        if u == "PCS":
            pool = [200, 500, 600, 1000, 2500] if prod.list_price < 100 else ([5, 10, 12, 20, 24, 30, 40, 60, 75, 120, 150, 200] if prod.list_price < 5000 else [2, 4, 6, 8, 10, 12])
        else:
            pool = {"MTR": [100, 200, 250, 500, 1000, 1500], "ROLL": [2, 5, 8, 10, 15, 25, 30], "BOX": [1, 2, 3, 5, 10],
                    "SET": [5, 10, 20, 25], "PKT": [10, 20, 50, 100]}.get(u, [5, 10, 20])
        return D(r.choice(pool))

    def _rand_date(self, sid: str, lo: date | None = None, hi: date | None = None) -> date:
        ags = self.ag_by_sup[sid]
        start = max(self.p.start, min(a.agreement.effective_from for a in ags))
        end = min(self.p.end, max(a.agreement.effective_to for a in ags) - timedelta(days=25))
        if lo:
            start = max(start, lo)
        if hi:
            end = min(end, hi)
        return start + timedelta(days=self.rng.randint(0, (end - start).days))

    # ------------------------------------------------------------------ clean transaction
    def new_txn(self, sid: str | None = None, n_lines: int | None = None, po_date: date | None = None,
                min_qty_line: bool = False, products: list[str] | None = None, alias_name: bool | None = None,
                charge: bool | None = None, unknown_supplier: bool = False, allow_no_agreement: bool = False) -> Txn:
        r = self.rng
        self.key_n += 1
        if unknown_supplier:
            sup = None
            sinfo = self.p.unknown_supplier
            sid = sinfo.supplier_id
            cats = list(self.by_cat)
            po_date = po_date or self.p.start + timedelta(days=r.randint(20, 150))
        else:
            sid = sid or r.choice(list(self.sups))
            sup = self.sups[sid]
            sinfo = sup.info
            cats = sup.categories
            po_date = po_date or self._rand_date(sid)
        pool = [x for c in cats for x in self.by_cat[c]]
        if products:
            chosen = [self.products[c] for c in products]
        else:
            n = n_lines or r.choice([2, 2, 3, 3, 4, 5])
            chosen = r.sample(pool, n)
        self.po_n += 1
        po_no = f"PO-2025-{self.po_n:04d}"
        dc_date = po_date + timedelta(days=r.randint(6, 14))
        inv_date = dc_date + timedelta(days=r.randint(1, 6))
        terms = sinfo.payment_terms or "Net 30"

        po_lines, dc_lines, inv_lines = [], [], []
        for i, prod in enumerate(chosen, 1):
            qty = self._qty(prod)
            if min_qty_line and i == 1 and sup and sup.info.volume_discount_min_qty > 0:
                qty = max(qty, sup.info.volume_discount_min_qty + D(r.choice([0, 5, 10, 20])))
            price = self.price_at(sid, prod.product_code, po_date) if sup else (prod.list_price * D("1.02")).quantize(D("0.01"))
            if price is None and allow_no_agreement and sup:
                price = contract_price(prod.list_price, sup.price_factor, D("1"))   # last known price; no agreement in force
            if price is None:
                raise ValueError(f"no agreement for {sid} on {po_date}")
            disc = sup.info.volume_discount_pct if (sup and sup.info.volume_discount_min_qty > 0 and qty >= sup.info.volume_discount_min_qty) else D("0")
            rate = self.p.tax_rates[prod.category]
            net = line_net(qty, price, disc)
            po_lines.append(POLine(line_no=i, product_code=prod.product_code, description=prod.description, quantity=qty,
                                   uom=prod.uom, unit_price=price, line_amount=line_net(qty, price)))
            dc_lines.append(DCLine(line_no=i, product_code=prod.product_code, description=prod.description, quantity_received=qty, uom=prod.uom))
            inv_lines.append(LineItem(line_no=i, product_code=prod.product_code, description=prod.description, quantity=qty, uom=prod.uom,
                                      unit_price=price, discount_pct=disc, line_amount=net, tax_rate=rate, tax_amount=tax_on(net, rate)))
        po = PurchaseOrderRecord(po_number=po_no, po_date=po_date, supplier_id=sid, supplier_name=sinfo.name, currency=self.p.currency,
                                 payment_terms=terms, expected_delivery_date=po_date + timedelta(days=10), lines=po_lines,
                                 total=sum((l.line_amount for l in po_lines), ZERO))
        self.dc_n += 1
        dc_no = (f"DC-2025-{self.dc_n:04d}" if self.dc_n % 2 else f"GRN-2025-{self.dc_n:04d}")
        dc = DeliveryChallanRecord(dc_number=dc_no, dc_date=dc_date, po_number=po_no, supplier_id=sid, supplier_name=sinfo.name,
                                   lines=dc_lines, remarks=r.choice(["Received in good condition", "Delivered to main store", "Received by store keeper", ""]))
        # invoice header
        if sup:
            self.sup_inv_n[sid] += r.randint(1, 9)
            number = sup.inv_format.format(n=self.sup_inv_n[sid])
            name = r.choice(sinfo.aliases) if (alias_name if alias_name is not None else r.random() < 0.15) else sinfo.name
        else:
            number = f"GGT-{r.randint(1000, 9999)}"
            name = sinfo.name
        inv = InvoiceRecord(invoice_number=number, invoice_date=inv_date, due_date=inv_date + timedelta(days=_net_days(terms)),
                            supplier_id=sid if (sup and sup.template == "B") else None, supplier_name=name, supplier_tax_id=sinfo.tax_id,
                            po_number=po_no, dc_reference=dc_no, currency=self.p.currency, payment_terms=terms, lines=inv_lines)
        # optional allowed freight within cap
        if sup and sup.charges_allowed and sup.freight_cap > 0 and (charge if charge is not None else r.random() < 0.45):
            amt = D(r.randrange(int(sup.freight_cap * D("0.4")) // 50, int(sup.freight_cap) // 50 + 1) * 50)
            inv.charges.append(Charge(charge_type="FREIGHT", description="Freight Charges", amount=amt))
        recompute(inv)
        t = Txn(sup=sup, sinfo=sinfo, po=po, dcs=[dc], inv=inv, true_inv=copy.deepcopy(inv), key=self.key_n)
        return t

    def set_qty(self, t: Txn, i: int, qty: D) -> None:
        """Set the quantity of line i consistently on PO, every DC (first DC only) and invoice; recompute the invoice."""
        t.po.lines[i].quantity = qty
        t.po.lines[i].line_amount = line_net(qty, t.po.lines[i].unit_price)
        t.po.total = sum((x.line_amount for x in t.po.lines), ZERO)
        t.dcs[0].lines[i].quantity_received = qty
        l = t.inv.lines[i]
        l.quantity = qty
        sup = t.sup
        l.discount_pct = sup.info.volume_discount_pct if (sup and sup.info.volume_discount_min_qty > 0 and qty >= sup.info.volume_discount_min_qty) else D("0")
        recompute(t.inv)
        t.true_inv = copy.deepcopy(t.inv)

    def pick_line_with_min_qty(self, t: Txn, minimum: int = 10, exclude: tuple[int, ...] = ()) -> int:
        cands = [i for i, l in enumerate(t.inv.lines) if i not in exclude and l.quantity >= minimum]
        i = self.rng.choice(cands) if cands else next(j for j in range(len(t.inv.lines)) if j not in exclude)
        if t.inv.lines[i].quantity < minimum:
            self.set_qty(t, i, D(minimum * 2))
        return i

    # ------------------------------------------------------------------ emission
    def _lab(self, rows: list, code: str, line: int | None = None, product: str | None = None, expected=None, observed=None,
             scenario: int = 0, notes: str = ""):
        ci = T.info(code)
        rows.append(dict(anomaly_code=code, line_no=line, product_code=product, severity=ci.severity, expected_status=ci.status,
                         expected_value=None if expected is None else str(expected), observed_value=None if observed is None else str(observed),
                         scenario_no=scenario, scenario_name=T.SCENARIOS.get(scenario, ""), description=ci.description, notes=notes))

    def emit(self, t: Txn, labels: list[dict], fmt: str | None = None, scenario: int = 1, exposure: D | None = None,
             received_offset_days: int = 0, extra_po: bool = True, tag: str = "") -> dict:
        """Register a transaction's documents and its labels (final ids are assigned in finalize())."""
        if not labels:
            labels.append(dict(anomaly_code="NONE", line_no=None, product_code=None, severity="INFO", expected_status="PASSED",
                               expected_value=None, observed_value=None, scenario_no=1, scenario_name=T.SCENARIOS[1],
                               description="Clean invoice: valid three-way match and arithmetic.", notes=""))
        rec = dict(txn=t, labels=labels, fmt=fmt, scenario=scenario, exposure=exposure,
                   received=datetime.combine(t.inv.invoice_date, datetime.min.time()) + timedelta(hours=9 + self.rng.randint(0, 7), minutes=self.rng.randint(0, 59),
                                                                                                    days=received_offset_days),
                   tag=tag)
        self.pending.append(rec)
        if extra_po and t not in self.txns:
            self.txns.append(t)
        return rec

    # ------------------------------------------------------------------ scenarios
    def clean(self, n: int):
        for i in range(n):
            t = self.new_txn(min_qty_line=(i % 5 == 0), alias_name=(i % 7 == 3), charge=(True if i % 3 == 0 else None))
            self.emit(t, [], scenario=1)

    def sc_price_above(self):
        for k in range(3):
            t = self.new_txn(sid=["SUP-003", "SUP-007", "SUP-001"][k])
            l = t.inv.lines[self.rng.randrange(len(t.inv.lines))]
            exp = l.unit_price
            l.unit_price = (exp * D(str(self.rng.choice([1.06, 1.12, 1.18])))).quantize(D("1") if exp >= 100 else D("0.01"))
            recompute(t.inv)
            labels = []
            self._lab(labels, "PRICE_ABOVE_CONTRACT", l.line_no, l.product_code, exp, l.unit_price, 2)
            self.emit(t, labels, scenario=2)

    def sc_qty_received(self):
        # A: DC short-delivers one line; B: partial delivery, only the first DC exists (second never arrived)
        for k in range(2):
            t = self.new_txn(sid=["SUP-002", "SUP-005"][k], n_lines=3)
            i = self.pick_line_with_min_qty(t)
            po_q = t.po.lines[i].quantity
            recv = (po_q * D("0.85")).quantize(D("1")) if k == 0 else (po_q * D("0.6")).quantize(D("1"))
            t.dcs[0].lines[i].quantity_received = recv
            t.dcs[0].remarks = "Partial delivery - balance to follow" if k == 1 else "Short delivered"
            # true supportable invoice: bills only what was received (discount basis stays the PO quantity)
            t.true_inv = copy.deepcopy(t.inv)
            t.true_inv.lines[i].quantity = recv
            recompute(t.true_inv, keep_line_amounts=False)
            labels = []
            self._lab(labels, "QTY_EXCEEDS_RECEIVED", t.inv.lines[i].line_no, t.inv.lines[i].product_code, recv, po_q, 3,
                      "partial delivery; balance never received" if k == 1 else "DC shows short delivery")
            self.emit(t, labels, scenario=3)

    def sc_qty_ordered(self):
        for k in range(2):
            t = self.new_txn(sid=["SUP-001", "SUP-004"][k], n_lines=3)
            i = self.pick_line_with_min_qty(t)
            l = t.inv.lines[i]
            po_q = l.quantity
            over = (po_q * D("1.10")).quantize(D("1"))
            if over == po_q:
                over = po_q + 1
            l.quantity = over
            recompute(t.inv)
            labels = []
            self._lab(labels, "QTY_EXCEEDS_ORDERED", l.line_no, l.product_code, po_q, over, 4)
            if k == 0:     # DC matches PO -> invoice also exceeds received
                self._lab(labels, "QTY_EXCEEDS_RECEIVED", l.line_no, l.product_code, po_q, over, 4, "DC quantity equals PO quantity")
            else:          # supplier over-delivered and the DC records it -> PO/DC conflict
                t.dcs[0].lines[i].quantity_received = over
                self._lab(labels, "PO_DC_QTY_CONFLICT", l.line_no, l.product_code, po_q, over, 4, "DC records over-delivery")
            self.emit(t, labels, scenario=4)

    def sc_duplicates(self):
        for k in range(2):      # scenario 5: identical copy, different filename, same format
            t = self.new_txn(sid=["SUP-003", "SUP-008"][k])
            orig = self.emit(t, [], scenario=1, fmt="pdf_text", tag=f"dup_orig_{k}")
            t2 = Txn(sup=t.sup, sinfo=t.sinfo, po=t.po, dcs=t.dcs, inv=copy.deepcopy(t.inv), true_inv=copy.deepcopy(t.inv), key=-1)
            labels = []
            self._lab(labels, "DUPLICATE_EXACT", expected="first submission only", observed="resubmitted copy", scenario=5, notes="identical content, different filename")
            self.emit(t2, labels, scenario=5, fmt="pdf_text", exposure=t.inv.grand_total, received_offset_days=2, extra_po=False, tag=f"dup_copy_{k}")
        # scenario 6: a re-scan of the same invoice delivered as an image
        t = self.new_txn(sid="SUP-002")
        self.emit(t, [], scenario=1, fmt="pdf_text", tag="rescan_orig")
        t2 = Txn(sup=t.sup, sinfo=t.sinfo, po=t.po, dcs=t.dcs, inv=copy.deepcopy(t.inv), true_inv=copy.deepcopy(t.inv), key=-1)
        labels = []
        self._lab(labels, "DUPLICATE_EXACT", expected="first submission only", observed="re-scanned copy (image)", scenario=6, notes="same invoice number re-sent as degraded image")
        self.emit(t2, labels, scenario=6, fmt="png", exposure=t.inv.grand_total, received_offset_days=3, extra_po=False, tag="rescan_copy")
        # scenario 27: different invoice number, identical economics, same PO
        t = self.new_txn(sid="SUP-005")
        self.emit(t, [], scenario=1, fmt="pdf_text", tag="posdup_orig")
        inv2 = copy.deepcopy(t.inv)
        n = inv2.invoice_number
        m = re.search(r"(\d)(\d)(?!.*\d)", n)
        if m and m.group(1) != m.group(2):
            inv2.invoice_number = n[:m.start()] + m.group(2) + m.group(1) + n[m.end():]
        else:
            inv2.invoice_number = n + "-A"
        inv2.invoice_date = t.inv.invoice_date + timedelta(days=1)
        inv2.due_date = t.inv.due_date + timedelta(days=1)
        t2 = Txn(sup=t.sup, sinfo=t.sinfo, po=t.po, dcs=t.dcs, inv=inv2, true_inv=copy.deepcopy(t.inv), key=-1)
        labels = []
        self._lab(labels, "POSSIBLE_DUPLICATE", expected="single invoice for this PO", observed=inv2.invoice_number, scenario=27, notes=f"original number {n}")
        self.emit(t2, labels, scenario=27, fmt="pdf_text", exposure=t.inv.grand_total, received_offset_days=4, extra_po=False, tag="posdup_copy")

    def sc_arithmetic(self):
        for k in range(2):      # 7: line subtotal
            t = self.new_txn(sid=["SUP-001", "SUP-008"][k], n_lines=3)
            l = t.inv.lines[0]
            exp = l.line_amount
            l.line_amount = (exp * D("1.05")).quantize(D("0.01"))
            recompute(t.inv, keep_line_amounts=True)
            labels = []
            self._lab(labels, "LINE_SUBTOTAL_ERROR", l.line_no, l.product_code, exp, l.line_amount, 7)
            self.emit(t, labels, scenario=7)
        for k in range(2):      # 8: tax calculation
            t = self.new_txn(sid=["SUP-004", "SUP-005"][k], n_lines=3)
            l = t.inv.lines[-1]
            exp = l.tax_amount
            l.tax_amount = (exp * D("1.30")).quantize(D("0.01"))
            recompute_tax_total(t.inv)
            labels = []
            self._lab(labels, "TAX_CALC_ERROR", l.line_no, l.product_code, exp, l.tax_amount, 8)
            self.emit(t, labels, scenario=8)
        for k in range(2):      # 9: grand total
            t = self.new_txn(sid=["SUP-007", "SUP-002"][k], n_lines=2)
            exp = t.inv.grand_total
            t.inv.grand_total = exp + D(["1250.00", "3880.50"][k])
            labels = []
            self._lab(labels, "GRAND_TOTAL_ERROR", None, None, exp, t.inv.grand_total, 9)
            self.emit(t, labels, scenario=9)

    def sc_charges(self):
        # A: freight on an INCLUDED-freight agreement; B: unnamed fuel surcharge; C: freight above the cap
        specs = [("SUP-001", "FREIGHT", "Freight Charges", D("2500"), None), ("SUP-002", "FUEL", "Fuel Surcharge", D("1200"), None),
                 ("SUP-005", "FREIGHT", "Freight Charges", D("7800"), D("5000"))]
        for sid, ctype, desc, amt, cap in specs:
            t = self.new_txn(sid=sid, charge=False)
            t.true_inv = copy.deepcopy(t.inv)
            if cap is not None:
                t.true_inv.charges = [Charge(charge_type="FREIGHT", description="Freight Charges", amount=cap)]
                recompute(t.true_inv)
            t.inv.charges = [Charge(charge_type=ctype, description=desc, amount=amt)]
            recompute(t.inv)
            labels = []
            self._lab(labels, "UNAUTHORIZED_CHARGE", None, None, f"<= {cap}" if cap else "0.00", amt, 10,
                      "freight above agreement cap" if cap else "charge not permitted by agreement")
            self.emit(t, labels, scenario=10)

    def sc_documents(self):
        for k in range(2):      # 11 missing PO
            t = self.new_txn(sid=["SUP-003", "SUP-007"][k], n_lines=2)
            t.keep_po = False
            labels = []
            self._lab(labels, "MISSING_PO", expected=t.po.po_number, observed="not on file", scenario=11, notes="PO number cited by invoice and DC but PO document absent")
            self.emit(t, labels, scenario=11)
        for k in range(2):      # 12 missing DC
            t = self.new_txn(sid=["SUP-008", "SUP-004"][k], n_lines=2)
            t.keep_dcs = False
            labels = []
            self._lab(labels, "MISSING_DC", expected=t.inv.dc_reference, observed="not on file", scenario=12, notes="DC cited by invoice but no delivery record on file")
            self.emit(t, labels, scenario=12)

    def sc_products(self):
        # 13 unknown product code (item present on PO/DC/invoice but not in the catalogue)
        t = self.new_txn(sid="SUP-005", n_lines=2)
        code, desc, price, qty = "ELE-9901", "Hybrid Solar Inverter 5kW Single Phase", D("185000"), D("2")
        for coll, mk in ((t.po.lines, lambda i: POLine(line_no=i, product_code=code, description=desc, quantity=qty, uom="PCS", unit_price=price, line_amount=line_net(qty, price))),
                         (t.dcs[0].lines, lambda i: DCLine(line_no=i, product_code=code, description=desc, quantity_received=qty, uom="PCS"))):
            coll.append(mk(len(coll) + 1))
        t.po.total = sum((x.line_amount for x in t.po.lines), ZERO)
        t.inv.lines.append(LineItem(line_no=len(t.inv.lines) + 1, product_code=code, description=desc, quantity=qty, uom="PCS", unit_price=price,
                                    discount_pct=D("0"), line_amount=line_net(qty, price), tax_rate=D("15"), tax_amount=ZERO))
        recompute(t.inv)
        t.true_inv = copy.deepcopy(t.inv)
        labels = []
        self._lab(labels, "UNKNOWN_PRODUCT_CODE", t.inv.lines[-1].line_no, code, "code in product master", code, 13)
        self.emit(t, labels, scenario=13)
        # 14 description variants (informational, no financial effect)
        for k in range(2):
            t = self.new_txn(sid=["SUP-001", "SUP-007"][k], products=[["ELE-1002", "CAB-4002"], ["ELE-1005", "LGT-2005"]][k])
            l = t.inv.lines[0]
            prod = self.products[l.product_code]
            if k == 0:
                l.description = prod.aliases[0]
                note = "alias description with correct code"
            else:
                words = prod.description.split()
                l.description = " ".join([words[1], words[0]] + words[2:]) if len(words) > 2 else prod.description
                l.product_code = None
                note = "reordered description, code omitted"
            labels = []
            self._lab(labels, "PRODUCT_DESCRIPTION_VARIANT", l.line_no, prod.product_code, prod.description, l.description, 14, note)
            self.emit(t, labels, scenario=14)
        # 15 ambiguous description
        t = self.new_txn(sid="SUP-007", products=["ELE-1002", "LGT-2006"])
        l = t.inv.lines[0]
        l.description, l.product_code = "Miniature Circuit Breaker 32A", None
        labels = []
        self._lab(labels, "AMBIGUOUS_PRODUCT", l.line_no, None, "ELE-1002 or ELE-1003", l.description, 15, "2-pole vs 3-pole not stated")
        self.emit(t, labels, scenario=15)

    def sc_supplier(self):
        t = self.new_txn(unknown_supplier=True, n_lines=3)       # 16
        labels = []
        self._lab(labels, "UNKNOWN_SUPPLIER", None, None, "supplier in master", t.inv.supplier_name, 16)
        self.emit(t, labels, scenario=16)
        t = self.new_txn(sid="SUP-003", n_lines=2)                # 26
        exp = t.inv.supplier_tax_id
        t.inv.supplier_tax_id = "SYN-TAX-0003-9"
        labels = []
        self._lab(labels, "SUPPLIER_DETAILS_INCONSISTENT", None, None, exp, t.inv.supplier_tax_id, 26, "tax id differs from master")
        self.emit(t, labels, scenario=26)

    def sc_contract_expired(self):
        for k in range(2):
            t = self.new_txn(sid="SUP-006", po_date=date(2025, 5, 14) + timedelta(days=k * 31), n_lines=3, allow_no_agreement=True)
            labels = []
            self._lab(labels, "CONTRACT_NOT_EFFECTIVE", None, None, "agreement effective on PO date", f"PO {t.po.po_date}; AG-006 ended 2025-04-30", 17)
            self.emit(t, labels, scenario=17)

    def sc_discount(self):
        for k in range(2):
            sid = ["SUP-001", "SUP-004"][k]
            t = self.new_txn(sid=sid, n_lines=3, min_qty_line=True)
            l = t.inv.lines[0]
            exp = l.discount_pct
            if exp == 0:      # make sure line qualifies
                l.quantity = t.po.lines[0].quantity = t.dcs[0].lines[0].quantity_received = self.sups[sid].info.volume_discount_min_qty + D("10")
                l.discount_pct = exp = self.sups[sid].info.volume_discount_pct
                t.po.lines[0].line_amount = line_net(l.quantity, l.unit_price)
                t.po.total = sum((x.line_amount for x in t.po.lines), ZERO)
            l.discount_pct = D("0") if k == 0 else D("2")
            recompute(t.inv)
            t.true_inv = copy.deepcopy(t.inv)
            t.true_inv.lines[0].discount_pct = exp
            recompute(t.true_inv)
            labels = []
            self._lab(labels, "DISCOUNT_ERROR", l.line_no, l.product_code, exp, l.discount_pct, 18, "volume discount missing" if k == 0 else "wrong discount rate")
            self.emit(t, labels, scenario=18)

    def sc_partial_reconciled(self):
        for k in range(2):
            t = self.new_txn(sid=["SUP-002", "SUP-005"][k], n_lines=2)
            for j in range(len(t.inv.lines)):
                if t.inv.lines[j].quantity < 5:
                    self.set_qty(t, j, D(10))
            first = t.dcs[0]
            second = copy.deepcopy(first)
            self.dc_n += 1
            second.dc_number = f"DC-2025-{self.dc_n:04d}"
            second.dc_date = first.dc_date + timedelta(days=self.rng.randint(5, 9))
            for a, b, pl in zip(first.lines, second.lines, t.po.lines):
                a.quantity_received = (pl.quantity * D("0.6")).quantize(D("1"))
                b.quantity_received = pl.quantity - a.quantity_received
            first.remarks, second.remarks = "Part delivery 1 of 2", "Part delivery 2 of 2 (balance)"
            t.dcs = [first, second]
            inv = t.inv
            inv.invoice_date = second.dc_date + timedelta(days=2)
            inv.due_date = inv.invoice_date + timedelta(days=_net_days(inv.payment_terms))
            inv.dc_reference = f"{first.dc_number}, {second.dc_number}"
            t.true_inv = copy.deepcopy(inv)
            labels = []
            self._lab(labels, "PARTIAL_DELIVERY_RECONCILED", None, None, "ordered = sum(received)", "2 delivery records", 19, "invoice qty equals aggregated deliveries")
            self.emit(t, labels, scenario=19)

    def sc_po_dc_conflict(self):
        t = self.new_txn(sid="SUP-008", n_lines=3)
        i = self.pick_line_with_min_qty(t)
        over = (t.po.lines[i].quantity * D("1.20")).quantize(D("1"))
        t.dcs[0].lines[i].quantity_received = over
        labels = []
        self._lab(labels, "PO_DC_QTY_CONFLICT", t.inv.lines[i].line_no, t.inv.lines[i].product_code, t.po.lines[i].quantity, over, 20, "invoice bills PO quantity; DC shows more")
        self.emit(t, labels, scenario=20)

    def sc_tax(self):
        t = self.new_txn(sid="SUP-003", n_lines=3)       # 21 missing tax info
        recompute(t.inv, has_tax=False)
        labels = []
        self._lab(labels, "MISSING_TAX_INFO", None, None, "tax rate and amount per line", "absent", 21)
        self.emit(t, labels, scenario=21)
        for k in range(2):                                # 22 wrong rate for category (arithmetically consistent)
            t = self.new_txn(sid=["SUP-004", "SUP-007"][k], n_lines=3)
            l = t.inv.lines[0]
            exp = l.tax_rate
            l.tax_rate = exp + D("2") if k == 0 else exp - D("5")
            recompute(t.inv)
            labels = []
            self._lab(labels, "TAX_RATE_POLICY_MISMATCH", l.line_no, l.product_code, exp, l.tax_rate, 22)
            self.emit(t, labels, scenario=22)

    def sc_dates_refs(self):
        t = self.new_txn(sid="SUP-005", n_lines=2)       # 23A invoice dated before the delivery
        t.inv.invoice_date = t.dcs[0].dc_date - timedelta(days=4)
        t.inv.due_date = t.inv.invoice_date + timedelta(days=_net_days(t.inv.payment_terms))
        labels = []
        self._lab(labels, "DATE_REFERENCE_INCONSISTENT", None, None, f">= {t.dcs[0].dc_date}", str(t.inv.invoice_date), 23, "invoice precedes delivery")
        self.emit(t, labels, scenario=23)
        t = self.new_txn(sid="SUP-001", n_lines=2)       # 23B invoice cites a DC reference that does not match the PO's delivery
        wrong = f"DC-2025-{self.dc_n + 700:04d}"
        labels = []
        self._lab(labels, "DATE_REFERENCE_INCONSISTENT", None, None, t.dcs[0].dc_number, wrong, 23, "invoice cites a different delivery reference")
        t.inv.dc_reference = wrong
        self.emit(t, labels, scenario=23)

    def sc_currency(self):
        t = self.new_txn(sid="SUP-002", n_lines=2)
        t.inv.currency = "USD"
        labels = []
        self._lab(labels, "CURRENCY_MISMATCH", None, None, "PKR", "USD", 24)
        self.emit(t, labels, scenario=24)

    def sc_multi(self):
        # M1: price above contract + qty above received + wrong grand total
        t = self.new_txn(sid="SUP-005", n_lines=3)
        ib = self.pick_line_with_min_qty(t, 10, exclude=(0,))
        a, b = t.inv.lines[0], t.inv.lines[ib]
        exp_p = a.unit_price
        a.unit_price = (exp_p * D("1.15")).quantize(D("1") if exp_p >= 100 else D("0.01"))
        po_q = b.quantity
        recv = (po_q * D("0.8")).quantize(D("1"))
        t.dcs[0].lines[ib].quantity_received = recv
        t.true_inv = copy.deepcopy(t.inv)
        t.true_inv.lines[0].unit_price = exp_p
        t.true_inv.lines[ib].quantity = recv
        recompute(t.true_inv)
        recompute(t.inv)
        exp_gt = t.inv.grand_total
        t.inv.grand_total = exp_gt + D("2000")
        labels = []
        self._lab(labels, "PRICE_ABOVE_CONTRACT", a.line_no, a.product_code, exp_p, a.unit_price, 25)
        self._lab(labels, "QTY_EXCEEDS_RECEIVED", b.line_no, b.product_code, recv, po_q, 25)
        self._lab(labels, "GRAND_TOTAL_ERROR", None, None, exp_gt, t.inv.grand_total, 25)
        self.emit(t, labels, scenario=25)
        # M2: wrong/missing discount + unauthorized surcharge + tax calc error
        t = self.new_txn(sid="SUP-001", n_lines=3, min_qty_line=True, charge=False)
        l = t.inv.lines[0]
        if l.discount_pct == 0:
            l.quantity = t.po.lines[0].quantity = t.dcs[0].lines[0].quantity_received = D("60")
            l.discount_pct = D("5")
            t.po.lines[0].line_amount = line_net(l.quantity, l.unit_price)
            t.po.total = sum((x.line_amount for x in t.po.lines), ZERO)
            recompute(t.inv)
        exp_d = l.discount_pct
        t.true_inv = copy.deepcopy(t.inv)
        l.discount_pct = D("0")
        t.inv.charges = [Charge(charge_type="SERVICE", description="Service Surcharge", amount=D("1800"))]
        recompute(t.inv)
        t.true_inv.charges = []
        recompute(t.true_inv)
        c = t.inv.lines[-1]
        exp_tax = c.tax_amount
        c.tax_amount = (exp_tax * D("1.4")).quantize(D("0.01"))
        recompute_tax_total(t.inv)
        labels = []
        self._lab(labels, "DISCOUNT_ERROR", l.line_no, l.product_code, exp_d, l.discount_pct, 25)
        self._lab(labels, "UNAUTHORIZED_CHARGE", None, None, "0.00", D("1800"), 25)
        self._lab(labels, "TAX_CALC_ERROR", c.line_no, c.product_code, exp_tax, c.tax_amount, 25)
        self.emit(t, labels, scenario=25)
        # M3: missing PO + invoice price above contract + invoice dated before delivery
        t = self.new_txn(sid="SUP-003", n_lines=2)
        t.keep_po = False
        a = t.inv.lines[0]
        exp_p = a.unit_price
        a.unit_price = (exp_p * D("1.10")).quantize(D("1") if exp_p >= 100 else D("0.01"))
        t.true_inv = copy.deepcopy(t.inv)
        t.true_inv.lines[0].unit_price = exp_p
        recompute(t.true_inv)
        recompute(t.inv)
        t.inv.invoice_date = t.dcs[0].dc_date - timedelta(days=3)
        t.inv.due_date = t.inv.invoice_date + timedelta(days=_net_days(t.inv.payment_terms))
        labels = []
        self._lab(labels, "MISSING_PO", expected=t.po.po_number, observed="not on file", scenario=25)
        self._lab(labels, "PRICE_ABOVE_CONTRACT", a.line_no, a.product_code, exp_p, a.unit_price, 25)
        self._lab(labels, "DATE_REFERENCE_INCONSISTENT", None, None, f">= {t.dcs[0].dc_date}", str(t.inv.invoice_date), 25)
        self.emit(t, labels, scenario=25)

    # ------------------------------------------------------------------ build + finalize
    def build(self) -> Dataset:
        self.clean(self.n_clean)
        self.sc_price_above(); self.sc_qty_received(); self.sc_qty_ordered(); self.sc_duplicates()
        self.sc_arithmetic(); self.sc_charges(); self.sc_documents(); self.sc_products(); self.sc_supplier()
        self.sc_contract_expired(); self.sc_discount(); self.sc_partial_reconciled(); self.sc_po_dc_conflict()
        self.sc_tax(); self.sc_dates_refs(); self.sc_currency(); self.sc_multi()
        return self.finalize()

    def finalize(self) -> Dataset:
        ds = Dataset(profile=self.p, seed=self.seed)
        rng = random.Random(self.seed + 7)
        # price list + agreements
        for a in self.p.agreements:
            ds.agreements.append(a.agreement)
            sup = self.sups[a.agreement.supplier_id]
            for cat in sup.categories:
                for prod in self.by_cat[cat]:
                    ds.price_list.append(PriceListEntry(
                        agreement_id=a.agreement.agreement_id, supplier_id=sup.info.supplier_id, product_code=prod.product_code,
                        contract_price=contract_price(prod.list_price, sup.price_factor, a.price_adj), currency=self.p.currency,
                        effective_from=a.agreement.effective_from, effective_to=a.agreement.effective_to))
        # order invoices by arrival and assign ids / file names
        recs = sorted(self.pending, key=lambda r: (r["received"], r["txn"].key if r["txn"].key > 0 else 10**6))
        ext = {"pdf_text": "pdf", "pdf_scan": "pdf", "png": "png", "jpg": "jpg", "txt": "txt"}
        seen_docs: set[int] = set()
        po_idx = dc_idx = 0
        for idx, r in enumerate(recs, 1):
            t: Txn = r["txn"]
            fmt = r["fmt"] or FORMAT_CYCLE[(idx - 1) % len(FORMAT_CYCLE)]
            inv = t.inv
            scode = t.sup.code if t.sup else "UNK"
            safe = re.sub(r"[^A-Za-z0-9]+", "-", inv.invoice_number).strip("-")
            inv_id = f"INV-{idx:03d}_{scode}_{safe}"
            inv.invoice_id = inv_id
            inv.source_file = f"{inv_id}.{ext[fmt]}"
            inv.received_at = r["received"]
            ds.doc_format[inv.source_file] = fmt
            ds.invoices.append(inv)
            ds.invoice_meta[inv_id] = dict(scenario_no=r["scenario"], template=(t.sup.template if t.sup else "A"), fmt=fmt, tag=r["tag"],
                                           supplier_id=t.sinfo.supplier_id)
            ds.registry.append(dict(source_file=inv.source_file, doc_type="INVOICE", received_at=r["received"].isoformat(timespec="minutes"),
                                    channel=rng.choice(["email", "supplier_portal", "scan_inbox"]) if fmt in ("pdf_scan", "png", "jpg") else rng.choice(["email", "supplier_portal"])))
            # GT rows
            for lab in r["labels"]:
                ds.gt.append(dict(invoice_id=inv_id, source_file=inv.source_file, supplier_id=t.sinfo.supplier_id, invoice_number=inv.invoice_number, **lab))
            # expected values
            ti = t.true_inv
            if r["exposure"] is not None:
                expo = r["exposure"]
            else:
                expo = max(ZERO, (inv.grand_total or ZERO) - (ti.grand_total or ZERO))
            ds.expected.append(dict(invoice_id=inv_id, source_file=inv.source_file, expected_subtotal=ti.subtotal, expected_tax_total=ti.tax_total,
                                    expected_grand_total=ti.grand_total, observed_subtotal=inv.subtotal, observed_tax_total=inv.tax_total,
                                    observed_grand_total=inv.grand_total, expected_exposure=expo))
            # PO / DC documents (once per transaction)
            if r["txn"].key > 0 and id(t) not in seen_docs:
                seen_docs.add(id(t))
                if t.keep_po:
                    po_idx += 1
                    f = PO_FORMATS[(po_idx - 1) % len(PO_FORMATS)]
                    t.po.source_file = f"{t.po.po_number}.{ext[f]}"
                    ds.doc_format[t.po.source_file] = f
                    ds.pos.append(t.po)
                    ds.registry.append(dict(source_file=t.po.source_file, doc_type="PURCHASE_ORDER", received_at=datetime.combine(t.po.po_date, datetime.min.time()).isoformat(timespec="minutes"), channel="erp_export"))
                else:
                    ds.intentional_dangling[inv.source_file + ":po"] = "MISSING_PO"
                if t.keep_dcs:
                    for dc in t.dcs:
                        dc_idx += 1
                        f = DC_FORMATS[(dc_idx - 1) % len(DC_FORMATS)]
                        dc.source_file = f"{dc.dc_number}.{ext[f]}"
                        ds.doc_format[dc.source_file] = f
                        ds.dcs.append(dc)
                        ds.registry.append(dict(source_file=dc.source_file, doc_type="DELIVERY_CHALLAN", received_at=datetime.combine(dc.dc_date, datetime.min.time()).isoformat(timespec="minutes"), channel="warehouse"))
                else:
                    ds.intentional_dangling[inv.source_file + ":dc"] = "MISSING_DC"
        # sort pos/dcs by number for tidy outputs
        ds.pos.sort(key=lambda x: x.po_number)
        ds.dcs.sort(key=lambda x: x.dc_number)
        return ds


def recompute_tax_total(inv: InvoiceRecord) -> None:
    """Re-sum tax and grand total from the (possibly deliberately wrong) per-line tax amounts."""
    inv.tax_total = sum((l.tax_amount or ZERO for l in inv.lines), ZERO)
    inv.grand_total = (inv.subtotal or ZERO) + inv.tax_total + sum((c.amount for c in inv.charges), ZERO)


def generate(profile: Profile, seed: int = 20250101, n_clean: int = 22) -> Dataset:
    return Generator(profile, seed, n_clean).build()
