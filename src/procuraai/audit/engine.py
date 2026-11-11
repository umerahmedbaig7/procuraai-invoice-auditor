"""Deterministic reconciliation and audit engine.

* All financial arithmetic uses ``Decimal`` and the rounding policy in ``audit.money``.
* No LLM is involved in any decision here. An LLM may later *explain* findings; it never creates or changes them.
* Findings are typed (see taxonomy): CONFIRMED, POTENTIAL, INSUFFICIENT_EVIDENCE, MANUAL_REVIEW, PASSED.
* A missing delivery record or missing policy passage is never treated as proof of a violation.
* Exposure estimates are de-duplicated: all findings that concern the same underlying line/header item share an
  ``exposure_key`` and the report counts each key once.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable

from .. import taxonomy as T
from ..config import DEFAULT_TAX_RATES, AuditConfig
from ..normalization import (MatchResult, ProductMatcher, SupplierMatcher, invoice_key, normalize_code, normalize_currency, normalize_name)
from ..schemas import (AuditFinding, CheckResult, DeliveryChallanRecord, EvidenceRef, InvoiceAuditResult, InvoiceRecord, LineItem,
                       PolicyRule, PriceListEntry, ProductInfo, PurchaseOrderRecord, SupplierAgreement, SupplierInfo)
from .money import ZERO, line_net, tax_on

EvidenceFn = Callable[[str, str | None, str | None, dict], list[EvidenceRef]]   # (code, supplier_id, product_code, context)


# ---------------------------------------------------------------------------------------------
@dataclass
class MasterData:
    suppliers: list[SupplierInfo]
    products: list[ProductInfo]
    agreements: list[SupplierAgreement]
    price_list: list[PriceListEntry]
    policies: list[PolicyRule] = field(default_factory=list)

    def __post_init__(self):
        self.supplier_by_id = {s.supplier_id: s for s in self.suppliers}
        self.product_by_code = {p.product_code: p for p in self.products}
        self._prices = {(e.agreement_id, e.product_code): e for e in self.price_list}
        self.tax_rates: dict[str, Decimal] = dict(DEFAULT_TAX_RATES)
        for r in self.policies:
            if r.rule_key.startswith("tax_rate:"):
                try:
                    self.tax_rates[r.rule_key.split(":", 1)[1]] = Decimal(r.rule_value)
                except Exception:  # noqa: BLE001
                    pass

    def agreement_for(self, supplier_id: str, on: date) -> SupplierAgreement | None:
        for a in self.agreements:
            if a.supplier_id == supplier_id and a.effective_from <= on <= a.effective_to:
                return a
        return None

    def last_agreement(self, supplier_id: str) -> SupplierAgreement | None:
        c = [a for a in self.agreements if a.supplier_id == supplier_id]
        return max(c, key=lambda a: a.effective_to) if c else None

    def price(self, agreement_id: str, code: str) -> PriceListEntry | None:
        return self._prices.get((agreement_id, code))


@dataclass
class DocumentStore:
    pos: dict[str, PurchaseOrderRecord] = field(default_factory=dict)
    dcs: dict[str, DeliveryChallanRecord] = field(default_factory=dict)

    @classmethod
    def from_lists(cls, pos, dcs):
        return cls({normalize_code_ref(p.po_number): p for p in pos if p.po_number}, {normalize_code_ref(d.dc_number): d for d in dcs if d.dc_number})

    def dcs_for_po(self, po_number: str) -> list[DeliveryChallanRecord]:
        k = normalize_code_ref(po_number)
        return [d for d in self.dcs.values() if d.po_number and normalize_code_ref(d.po_number) == k]


def normalize_code_ref(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def split_refs(s: str | None) -> list[str]:
    return [x.strip() for x in re.split(r"[,;&]|\band\b", s or "") if x.strip()]


@dataclass
class LedgerEntry:
    invoice_id: str
    supplier_key: str
    number_key: str
    po_key: str
    grand_total: Decimal | None
    signature: frozenset
    qty_by_product: dict[str, Decimal]
    source_file: str
    is_duplicate: bool = False


# ---------------------------------------------------------------------------------------------
RECOMMENDED = {
    "PRICE_ABOVE_CONTRACT": "Query the supplier and request a credit note or corrected invoice at the contract price; hold the disputed amount only after a human confirms the agreement.",
    "QTY_EXCEEDS_RECEIVED": "Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.",
    "QTY_EXCEEDS_ORDERED": "Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice.",
    "DUPLICATE_EXACT": "Do not process for payment; confirm with accounts payable that the earlier invoice is the one being paid.",
    "POSSIBLE_DUPLICATE": "Compare with the earlier invoice for the same PO and confirm with the supplier before any payment.",
    "LINE_SUBTOTAL_ERROR": "Return the invoice to the supplier for correction of the line/subtotal arithmetic.",
    "TAX_CALC_ERROR": "Ask the supplier to correct the tax calculation.",
    "GRAND_TOTAL_ERROR": "Return the invoice for correction; the stated total does not foot.",
    "UNAUTHORIZED_CHARGE": "Query the charge against the supplier agreement; request removal or written authorisation from procurement.",
    "MISSING_PO": "Locate the purchase order (or confirm an authorised exception) before paying.",
    "MISSING_DC": "Ask receiving staff to confirm delivery and locate the delivery record. Absence of the record is not proof of non-delivery.",
    "UNKNOWN_PRODUCT_CODE": "Have procurement identify the item and update the product master or reject the line.",
    "AMBIGUOUS_PRODUCT": "Have a buyer decide which catalogue product this line refers to.",
    "PRODUCT_CODE_DESCRIPTION_MISMATCH": "Verify which product was actually supplied.",
    "UNKNOWN_SUPPLIER": "Route to procurement for supplier onboarding/verification before any payment.",
    "SUPPLIER_MATCH_UNCERTAIN": "Confirm the supplier identity against the master.",
    "SUPPLIER_DETAILS_INCONSISTENT": "Verify the supplier's registration details with the supplier master before payment.",
    "CONTRACT_NOT_EFFECTIVE": "Confirm which price agreement applies (renewal/extension) before validating prices.",
    "NO_CONTRACT_PRICE": "Confirm the agreed price for this product with procurement.",
    "DISCOUNT_ERROR": "Ask the supplier to apply the contractual volume discount.",
    "PO_DC_QTY_CONFLICT": "Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.",
    "MISSING_TAX_INFO": "Request a compliant invoice stating tax rate and amount per line.",
    "TAX_RATE_POLICY_MISMATCH": "Check the applicable rate under the (synthetic) policy and ask the supplier to correct if confirmed.",
    "DATE_REFERENCE_INCONSISTENT": "Check dates and cited references with the supplier and receiving.",
    "CURRENCY_MISMATCH": "Confirm the invoicing currency with the supplier; do not compare amounts across currencies.",
    "EXTRACTION_LOW_CONFIDENCE": "Verify extracted values against the original document image/PDF.",
}


class AuditEngine:
    def __init__(self, master: MasterData, docs: DocumentStore, cfg: AuditConfig | None = None, evidence_fn: EvidenceFn | None = None,
                 low_confidence_threshold: float = 0.75):
        self.m, self.docs, self.cfg = master, docs, cfg or AuditConfig()
        self.rp = self.cfg.rounding
        self.sm = SupplierMatcher(master.suppliers, self.cfg)
        self.pm = ProductMatcher(master.products, self.cfg)
        self.ledger: list[LedgerEntry] = []
        self.evidence_fn = evidence_fn
        self.low_conf = low_confidence_threshold

    # ------------------------------------------------------------------ batch
    def audit_batch(self, invoices: list[InvoiceRecord], audit_id: str) -> list[InvoiceAuditResult]:
        order = sorted(invoices, key=lambda i: (i.received_at or __import__("datetime").datetime.min, i.invoice_date or date.min, i.source_file))
        return [self.audit_invoice(inv, audit_id) for inv in order]

    # ------------------------------------------------------------------ helpers
    def _q(self, x: Decimal) -> Decimal:
        return self.rp.q(x)

    def _fid(self, ctx: dict) -> str:
        ctx["n"] += 1
        return f"{ctx['audit']}:{ctx['inv'].invoice_id}:{ctx['n']:03d}"

    def _add(self, ctx: dict, code: str, check: str, message: str, *, line: LineItem | None = None, product: str | None = None, expected=None, observed=None,
             difference=None, status: str | None = None, severity: str | None = None, reason: str = "", exposure: Decimal = ZERO, exposure_key: str | None = None,
             identifiers: dict | None = None, confidence: float = 1.0) -> AuditFinding:
        ci = T.info(code)
        f = AuditFinding(finding_id=self._fid(ctx), invoice_id=ctx["inv"].invoice_id, code=code, check=check, status=status or ci.status, severity=severity or ci.severity,
                         line_no=line.line_no if line else None, product_code=product or (line.product_code if line else None),
                         expected=None if expected is None else str(expected), observed=None if observed is None else str(observed),
                         difference=None if difference is None else str(difference), message=message, reason=reason or ci.description,
                         identifiers=identifiers or {}, exposure_amount=exposure, exposure_key=exposure_key, confidence=confidence,
                         needs_human_review=(status or ci.status) in (T.POTENTIAL, T.MANUAL_REVIEW, T.INSUFFICIENT_EVIDENCE))
        ctx["findings"].append(f)
        return f

    def _check(self, ctx: dict, name: str, status: str, detail: str = ""):
        ctx["checks"].append(CheckResult(check=name, status=status, detail=detail))

    # ------------------------------------------------------------------ main
    def audit_invoice(self, inv: InvoiceRecord, audit_id: str) -> InvoiceAuditResult:
        ctx = dict(inv=inv, audit=audit_id, findings=[], checks=[], n=0, identifiers={})
        res = InvoiceAuditResult(audit_id=audit_id, invoice_id=inv.invoice_id, invoice_number=inv.invoice_number, invoice_date=inv.invoice_date, supplier_name=inv.supplier_name,
                                 po_number=inv.po_number, currency=inv.currency, grand_total=inv.grand_total, source_file=inv.source_file, extraction_confidence=inv.extraction_confidence)
        # 1 supplier ------------------------------------------------------------------
        sup = self._check_supplier(ctx)
        res.supplier_id = sup.supplier_id if sup else None
        res.supplier_match = ctx["supplier_match"].model_dump()
        # 2 linking -------------------------------------------------------------------
        po, dcs = self._link(ctx, sup)
        res.linked_po = po.po_number if po else None
        res.linked_dcs = [d.dc_number for d in dcs]
        # 3 currency ------------------------------------------------------------------
        comparable = self._check_currency(ctx, po)
        # 4 dates ---------------------------------------------------------------------
        self._check_dates(ctx, po, dcs)
        # 5 products ------------------------------------------------------------------
        resolved = self._resolve_products(ctx)
        res.product_matches = [dict(line_no=l.line_no, **m.model_dump()) for l, m in zip(inv.lines, ctx["matches"])]
        # 6 duplicates (before quantities so possible duplicates are excluded from cumulative sums)
        dup_ids = self._check_duplicates(ctx, sup, po)
        # 7 agreement / contract ------------------------------------------------------
        agr = self._agreement(ctx, sup, po)
        # 8 quantities ----------------------------------------------------------------
        supportable = self._check_quantities(ctx, po, dcs, resolved, dup_ids)
        # 9 pricing + discount --------------------------------------------------------
        contract_prices = self._check_prices(ctx, sup, agr, po, resolved, comparable)
        # 10 arithmetic + tax ---------------------------------------------------------
        self._check_arithmetic(ctx, resolved)
        # 11 charges ------------------------------------------------------------------
        self._check_charges(ctx, sup, agr, comparable)
        # 12 line exposure (deduplicated per line) -------------------------------------
        self._line_exposures(ctx, resolved, supportable, contract_prices, agr, po)
        self._finalise(ctx, res)
        self._record_ledger(ctx, sup, po, resolved, dup_ids)
        return res

    # ------------------------------------------------------------------ 1 supplier
    def _check_supplier(self, ctx) -> SupplierInfo | None:
        inv = ctx["inv"]
        m = self.sm.match(inv.supplier_name, inv.supplier_tax_id, None)
        ctx["supplier_match"] = m
        if not m.matched_id:
            self._add(ctx, "UNKNOWN_SUPPLIER", "supplier_validation", f"Supplier '{inv.supplier_name}' is not in the supplier master.", expected="supplier in master", observed=inv.supplier_name,
                      identifiers=dict(supplier_name=inv.supplier_name, tax_id=inv.supplier_tax_id))
            self._check(ctx, "supplier_validation", "FAILED", "unknown supplier")
            return None
        sup = self.m.supplier_by_id[m.matched_id]
        if m.needs_review:
            self._add(ctx, "SUPPLIER_MATCH_UNCERTAIN", "supplier_validation", f"Supplier name '{inv.supplier_name}' matched {sup.name} only with score {m.score:.0f}.", observed=inv.supplier_name,
                      expected=sup.name, identifiers=dict(matched=sup.supplier_id, score=m.score))
        if inv.supplier_tax_id and sup.tax_id:
            if re.sub(r"[^A-Z0-9]", "", inv.supplier_tax_id.upper()) != re.sub(r"[^A-Z0-9]", "", sup.tax_id.upper()):
                self._add(ctx, "SUPPLIER_DETAILS_INCONSISTENT", "supplier_validation", f"Tax id on invoice ({inv.supplier_tax_id}) differs from the supplier master ({sup.tax_id}).",
                          expected=sup.tax_id, observed=inv.supplier_tax_id, identifiers=dict(supplier_id=sup.supplier_id))
        elif not inv.supplier_tax_id:
            self._check(ctx, "supplier_tax_id", "INSUFFICIENT_EVIDENCE", "tax id not read from invoice")
        if inv.supplier_id and inv.supplier_id != sup.supplier_id:
            self._add(ctx, "SUPPLIER_DETAILS_INCONSISTENT", "supplier_validation", f"Supplier code on invoice ({inv.supplier_id}) differs from the matched supplier ({sup.supplier_id}).",
                      expected=sup.supplier_id, observed=inv.supplier_id)
        if not any(f.code in ("SUPPLIER_DETAILS_INCONSISTENT", "SUPPLIER_MATCH_UNCERTAIN") for f in ctx["findings"]):
            self._check(ctx, "supplier_validation", "PASSED", f"matched {sup.supplier_id} by {m.method}")
        return sup

    # ------------------------------------------------------------------ 2 linking
    def _link(self, ctx, sup):
        inv = ctx["inv"]
        po = self.docs.pos.get(normalize_code_ref(inv.po_number)) if inv.po_number else None
        refs = split_refs(inv.dc_reference)
        found: dict[str, DeliveryChallanRecord] = {}
        missing_refs = []
        for r in refs:
            d = self.docs.dcs.get(normalize_code_ref(r))
            (found.__setitem__(d.dc_number, d) if d else missing_refs.append(r))
        if po is None and found:                      # try to recover the PO through a cited delivery record
            po_ref = next((d.po_number for d in found.values() if d.po_number), None)
            po = self.docs.pos.get(normalize_code_ref(po_ref)) if po_ref else None
        po_key = inv.po_number or (next(iter(found.values())).po_number if found else None)
        by_po = self.docs.dcs_for_po(po_key) if po_key else []
        for d in by_po:
            found.setdefault(d.dc_number, d)
        ctx["po_key"] = po_key
        if po is None:
            self._add(ctx, "MISSING_PO", "document_matching", f"Purchase order {inv.po_number or '(none cited)'} was not found among the supplied documents.", expected=inv.po_number or "a purchase order reference",
                      observed="not on file", reason="A missing PO is not proof of an unauthorised purchase; it requires manual confirmation.", identifiers=dict(po_number=inv.po_number))
            self._check(ctx, "po_match", "FAILED")
        else:
            self._check(ctx, "po_match", "PASSED", po.po_number)
            if sup and po.supplier_id and po.supplier_id != sup.supplier_id:
                self._add(ctx, "SUPPLIER_DETAILS_INCONSISTENT", "document_matching", f"PO {po.po_number} was issued to {po.supplier_id} but the invoice supplier matches {sup.supplier_id}.",
                          expected=po.supplier_id, observed=sup.supplier_id)
        dcs = list(found.values())
        linked = ([po] if po else []) + dcs
        ctx["weak_sources"] = [d.source_file for d in linked if "ocr" in (d.extraction_method or "") or d.extraction_confidence < self.low_conf]
        ctx["linked_conf"] = min([d.extraction_confidence for d in linked], default=1.0)
        if not dcs:
            self._add(ctx, "MISSING_DC", "document_matching", "No delivery challan / goods-received note was found for this invoice.", expected=inv.dc_reference or "a delivery record", observed="not on file",
                      reason="A missing delivery record is not proof that goods were not delivered; receiving staff must confirm.", identifiers=dict(dc_reference=inv.dc_reference))
            self._check(ctx, "dc_match", "FAILED")
        else:
            self._check(ctx, "dc_match", "PASSED", ", ".join(d.dc_number for d in dcs))
            if missing_refs:
                self._add(ctx, "DATE_REFERENCE_INCONSISTENT", "reference_consistency", f"Invoice cites delivery reference(s) {', '.join(missing_refs)} which do not exist, while other delivery records exist for the PO ({', '.join(d.dc_number for d in dcs)}).",
                          expected=", ".join(d.dc_number for d in dcs), observed=", ".join(missing_refs), identifiers=dict(cited=missing_refs))
        return po, dcs

    # ------------------------------------------------------------------ 3 currency
    def _check_currency(self, ctx, po) -> bool:
        inv = ctx["inv"]
        cur = normalize_currency(inv.currency)
        ref = normalize_currency(po.currency) if po and po.currency else self.cfg.base_currency
        if cur is None:
            self._check(ctx, "currency", "INSUFFICIENT_EVIDENCE", "currency not stated")
            return True
        if cur != ref:
            self._add(ctx, "CURRENCY_MISMATCH", "currency_consistency", f"Invoice currency {cur} differs from the {'PO' if po else 'policy'} currency {ref}; amounts are not compared.", expected=ref, observed=cur)
            self._check(ctx, "currency", "FAILED")
            return False
        self._check(ctx, "currency", "PASSED", cur)
        return True

    # ------------------------------------------------------------------ 4 dates
    def _check_dates(self, ctx, po, dcs):
        inv = ctx["inv"]
        if not inv.invoice_date:
            self._check(ctx, "dates", "INSUFFICIENT_EVIDENCE", "invoice date missing")
            return
        last_dc = max((d.dc_date for d in dcs if d.dc_date), default=None)
        problems = []
        if last_dc and inv.invoice_date < last_dc:
            problems.append((f">= {last_dc}", str(inv.invoice_date), f"Invoice dated {inv.invoice_date} precedes the delivery dated {last_dc}."))
        if po and po.po_date and inv.invoice_date < po.po_date:
            problems.append((f">= {po.po_date}", str(inv.invoice_date), f"Invoice dated {inv.invoice_date} precedes the purchase order dated {po.po_date}."))
        for exp, obs, msg in problems[:1]:
            self._add(ctx, "DATE_REFERENCE_INCONSISTENT", "date_consistency", msg, expected=exp, observed=obs)
        self._check(ctx, "dates", "FAILED" if problems else "PASSED")

    # ------------------------------------------------------------------ 5 products
    def _resolve_products(self, ctx) -> dict[int, str]:
        inv = ctx["inv"]
        ctx["matches"] = []
        resolved: dict[int, str] = {}
        for l in inv.lines:
            m = self.pm.match(l.product_code, l.description)
            ctx["matches"].append(m)
            if m.matched_id and not m.needs_review:
                resolved[l.line_no] = m.matched_id
                if m.description_variant:
                    self._add(ctx, "PRODUCT_DESCRIPTION_VARIANT", "product_identity", f"Line {l.line_no}: description '{l.description}' differs from the catalogue but resolves to {m.matched_id} ({m.method}).",
                              line=l, product=m.matched_id, expected=self.m.product_by_code[m.matched_id].description, observed=l.description, status=T.PASSED, severity="INFO", identifiers=dict(match=m.model_dump()))
            elif m.method == "code_desc_conflict":
                self._add(ctx, "PRODUCT_CODE_DESCRIPTION_MISMATCH", "product_identity", f"Line {l.line_no}: code {m.matched_id} does not fit the description '{l.description}' ({m.note}).", line=l,
                          expected=self.m.product_by_code[m.matched_id].description, observed=l.description, identifiers=dict(candidates=[c.model_dump() for c in m.candidates]))
            elif m.method == "ambiguous" and not m.original_code:
                names = ", ".join(c.key for c in m.candidates[:3])
                self._add(ctx, "AMBIGUOUS_PRODUCT", "product_identity", f"Line {l.line_no}: description '{l.description}' could refer to several products ({names}).", line=l,
                          expected="a single catalogue product", observed=l.description, identifiers=dict(candidates=[c.model_dump() for c in m.candidates]))
            else:
                hint = f" Closest catalogue items: {', '.join(c.key for c in m.candidates[:2])}." if m.candidates else ""
                self._add(ctx, "UNKNOWN_PRODUCT_CODE", "product_identity", f"Line {l.line_no}: product '{l.product_code or l.description}' is not in the product master.{hint}", line=l,
                          expected="code in product master", observed=l.product_code or l.description, identifiers=dict(candidates=[c.model_dump() for c in m.candidates]))
        if not any(f.check == "product_identity" and f.status != T.PASSED for f in ctx["findings"]):
            self._check(ctx, "product_identity", "PASSED")
        else:
            self._check(ctx, "product_identity", "FAILED")
        return resolved

    # ------------------------------------------------------------------ 6 duplicates
    @staticmethod
    def _signature(inv: InvoiceRecord, resolved: dict[int, str] | None = None) -> frozenset:
        return frozenset((normalize_code(l.product_code) or normalize_name(l.description), str(l.quantity), str(l.unit_price)) for l in inv.lines)

    def _check_duplicates(self, ctx, sup, po) -> set[str]:
        inv = ctx["inv"]
        sk = sup.supplier_id if sup else normalize_name(inv.supplier_name)
        nk = invoice_key(inv.invoice_number)
        pk = normalize_code_ref(ctx.get("po_key"))
        sig = self._signature(inv)
        ctx["dupkeys"] = (sk, nk, pk, sig)
        exact, possible = None, None
        for e in self.ledger:
            if e.supplier_key != sk:
                continue
            if nk and e.number_key == nk:
                exact = exact or e
            elif pk and e.po_key == pk and ((e.grand_total is not None and inv.grand_total is not None and abs(e.grand_total - inv.grand_total) <= self.cfg.header_tolerance) or e.signature == sig):
                possible = possible or e
        dup_ids: set[str] = set()
        if exact:
            dup_ids.add(exact.invoice_id)
            self._add(ctx, "DUPLICATE_EXACT", "duplicate_detection", f"Invoice {inv.invoice_number} from this supplier was already processed as {exact.invoice_id} ({exact.source_file}).", expected="first submission only",
                      observed=f"duplicate of {exact.invoice_id}", exposure=inv.grand_total or ZERO, exposure_key="INVOICE:DUP", identifiers=dict(original=exact.invoice_id, original_file=exact.source_file))
            self._check(ctx, "duplicate_detection", "FAILED", "exact")
        elif possible:
            dup_ids.add(possible.invoice_id)
            self._add(ctx, "POSSIBLE_DUPLICATE", "duplicate_detection", f"Invoice {inv.invoice_number} has a different number but the same supplier, PO and economic content as {possible.invoice_id}.", expected="a single invoice for this PO",
                      observed=f"similar to {possible.invoice_id}", exposure=inv.grand_total or ZERO, exposure_key="INVOICE:DUP", identifiers=dict(similar_to=possible.invoice_id))
            self._check(ctx, "duplicate_detection", "FAILED", "possible")
        else:
            self._check(ctx, "duplicate_detection", "PASSED")
        ctx["dup_ids"] = dup_ids
        return dup_ids

    # ------------------------------------------------------------------ 7 agreement
    def _agreement(self, ctx, sup, po) -> SupplierAgreement | None:
        inv = ctx["inv"]
        if not sup:
            self._check(ctx, "contract_validity", "SKIPPED", "supplier unknown")
            return None
        ref = po.po_date if (po and po.po_date) else inv.invoice_date
        if ref is None:
            self._check(ctx, "contract_validity", "INSUFFICIENT_EVIDENCE", "no reference date")
            return None
        a = self.m.agreement_for(sup.supplier_id, ref)
        if a is None:
            last = self.m.last_agreement(sup.supplier_id)
            msg = f"No supplier agreement for {sup.supplier_id} was effective on {ref} ({'PO date' if po else 'invoice date'})."
            if last:
                msg += f" The latest agreement {last.agreement_id} ran {last.effective_from} to {last.effective_to}."
            self._add(ctx, "CONTRACT_NOT_EFFECTIVE", "contract_validity", msg, expected="agreement effective on PO date", observed=str(ref), reason="Prices cannot be validated without an effective agreement; this is not proof of overcharging.",
                      identifiers=dict(reference_date=str(ref), supplier_id=sup.supplier_id, latest_agreement=last.agreement_id if last else None))
            self._check(ctx, "contract_validity", "INSUFFICIENT_EVIDENCE")
            return None
        ctx["agreement"] = a
        self._check(ctx, "contract_validity", "PASSED", a.agreement_id)
        return a

    # ------------------------------------------------------------------ 8 quantities
    def _po_qty(self, po) -> dict[str, Decimal]:
        out: dict[str, Decimal] = defaultdict(lambda: ZERO)
        if po:
            for l in po.lines:
                m = self.pm.match(l.product_code, l.description)
                code = m.matched_id or normalize_code(l.product_code)
                if code and l.quantity is not None:
                    out[code] += l.quantity
        return out

    def _dc_qty(self, dcs) -> dict[str, Decimal]:
        out: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for d in dcs:
            for l in d.lines:
                m = self.pm.match(l.product_code, l.description)
                code = m.matched_id or normalize_code(l.product_code)
                if code and l.quantity_received is not None:
                    out[code] += l.quantity_received
        return out

    def _check_quantities(self, ctx, po, dcs, resolved, dup_ids) -> dict[int, Decimal | None]:
        inv = ctx["inv"]
        ordered = self._po_qty(po) if po else None
        received = self._dc_qty(dcs) if dcs else None
        tol = self.cfg.qty_tolerance
        prior: dict[str, Decimal] = defaultdict(lambda: ZERO)
        pk = normalize_code_ref(ctx.get("po_key"))
        sk = ctx["dupkeys"][0]
        nk = ctx["dupkeys"][1]
        if pk:
            for e in self.ledger:
                if e.po_key == pk and e.supplier_key == sk and not e.is_duplicate and e.number_key != nk and e.invoice_id not in dup_ids:
                    for c, q in e.qty_by_product.items():
                        prior[c] += q
        # aggregate invoice qty by product, keep first line for attribution
        agg: dict[str, Decimal] = defaultdict(lambda: ZERO)
        first_line: dict[str, LineItem] = {}
        for l in inv.lines:
            c = resolved.get(l.line_no)
            if c and l.quantity is not None:
                agg[c] += l.quantity
                first_line.setdefault(c, l)
        bounds_cache: dict[str, Decimal | None] = {}
        for c, q in agg.items():
            cum = prior[c] + q
            o = ordered.get(c, ZERO) if ordered is not None else None
            r = received.get(c, ZERO) if received is not None else None
            if o is not None and cum > o + tol:
                self._add(ctx, "QTY_EXCEEDS_ORDERED", "three_way_match", f"{c}: invoiced quantity {cum} exceeds ordered quantity {o}" + (" (product is not on the PO)" if o == 0 else "") + ".", line=first_line[c], product=c,
                          expected=o, observed=cum, difference=cum - o, exposure_key=f"LINE:{first_line[c].line_no}", identifiers=dict(po=po.po_number if po else None, prior_invoiced=str(prior[c])))
            if r is not None and cum > r + tol:
                self._add(ctx, "QTY_EXCEEDS_RECEIVED", "three_way_match", f"{c}: invoiced quantity {cum} exceeds the received quantity {r} across {len(dcs)} delivery record(s).", line=first_line[c], product=c,
                          expected=r, observed=cum, difference=cum - r, exposure_key=f"LINE:{first_line[c].line_no}", identifiers=dict(delivery_records=[d.dc_number for d in dcs], prior_invoiced=str(prior[c])))
            if o is not None and r is not None and r > o + tol:
                self._add(ctx, "PO_DC_QTY_CONFLICT", "three_way_match", f"{c}: received quantity {r} exceeds ordered quantity {o}.", line=first_line[c], product=c, expected=o, observed=r, difference=r - o,
                          identifiers=dict(po=po.po_number, delivery_records=[d.dc_number for d in dcs]))
            if r is not None and len(dcs) > 1:
                per_dc = [sum((x.quantity_received or ZERO) for x in d.lines if (normalize_code(x.product_code) == c)) for d in dcs]
                if per_dc and cum > max(per_dc) and cum <= r + tol and (o is None or cum <= o + tol):
                    if not any(f.code == "PARTIAL_DELIVERY_RECONCILED" for f in ctx["findings"]):
                        self._add(ctx, "PARTIAL_DELIVERY_RECONCILED", "three_way_match", f"Invoiced quantities reconcile only after aggregating {len(dcs)} delivery records ({', '.join(d.dc_number for d in dcs)}).",
                                  status=T.PASSED, severity="INFO", expected=r, observed=cum, identifiers=dict(delivery_records=[d.dc_number for d in dcs]))
            bounds = [x for x in (o, r) if x is not None]
            bounds_cache[c] = min(bounds) if bounds else None
            bounds_cache[c] = (max(ZERO, bounds_cache[c] - prior[c]) if bounds_cache[c] is not None else None)
        if po is None:
            self._check(ctx, "three_way_match", "INSUFFICIENT_EVIDENCE", "no PO: ordered quantities unavailable")
        elif not dcs:
            self._check(ctx, "three_way_match", "INSUFFICIENT_EVIDENCE", "no delivery record: received quantities unavailable")
        else:
            self._check(ctx, "three_way_match", "FAILED" if any(f.check == "three_way_match" and f.status in (T.CONFIRMED, T.POTENTIAL) for f in ctx["findings"]) else "PASSED")
        # supportable qty per line (allocate sequentially across lines of the same product)
        remaining = dict(bounds_cache)
        support: dict[int, Decimal | None] = {}
        for l in inv.lines:
            c = resolved.get(l.line_no)
            if not c or l.quantity is None:
                support[l.line_no] = None
                continue
            b = remaining.get(c)
            if b is None:
                support[l.line_no] = l.quantity
            else:
                take = min(l.quantity, b)
                support[l.line_no] = take
                remaining[c] = b - take
        ctx["ordered"] = ordered
        return support

    # ------------------------------------------------------------------ 9 prices & discounts
    def _check_prices(self, ctx, sup, agr, po, resolved, comparable) -> dict[int, Decimal | None]:
        inv = ctx["inv"]
        out: dict[int, Decimal | None] = {}
        ctx["disc_expected"] = {}
        if not (sup and agr and comparable):
            self._check(ctx, "price_validation", "SKIPPED", "no supplier/agreement or currency not comparable")
            self._check(ctx, "discount_validation", "SKIPPED")
            return out
        ordered = ctx.get("ordered")
        any_price_fail = any_disc_fail = False
        for l in inv.lines:
            c = resolved.get(l.line_no)
            if not c or l.unit_price is None:
                continue
            entry = self.m.price(agr.agreement_id, c)
            if entry is None:
                self._add(ctx, "NO_CONTRACT_PRICE", "price_validation", f"Line {l.line_no}: agreement {agr.agreement_id} has no price for {c}.", line=l, product=c, identifiers=dict(agreement=agr.agreement_id))
                continue
            cp = entry.contract_price
            out[l.line_no] = cp
            tol = max(self.cfg.price_tolerance_abs, cp * self.cfg.price_tolerance_pct / Decimal(100))
            if l.unit_price > cp + tol:
                pct = (l.unit_price - cp) / cp * Decimal(100)
                sev = "HIGH" if pct >= Decimal("5") else "MEDIUM"
                any_price_fail = True
                self._add(ctx, "PRICE_ABOVE_CONTRACT", "price_validation", f"Line {l.line_no} {c}: billed unit price {l.unit_price} is {pct:.1f}% above contract price {cp} ({agr.agreement_id}).", line=l, product=c, expected=cp, observed=l.unit_price,
                          difference=l.unit_price - cp, severity=sev, exposure_key=f"LINE:{l.line_no}", identifiers=dict(agreement=agr.agreement_id, effective=f"{agr.effective_from}..{agr.effective_to}"))
            # volume discount on ordered quantity (PO) when known, otherwise on invoiced quantity
            basis = ordered.get(c) if (ordered is not None and ordered.get(c)) else l.quantity
            exp_d = agr.volume_discount_pct if (agr.volume_discount_min_qty > 0 and basis is not None and basis >= agr.volume_discount_min_qty) else ZERO
            ctx["disc_expected"][l.line_no] = exp_d
            obs_d = l.discount_pct or ZERO
            if abs(obs_d - exp_d) > self.cfg.discount_tolerance_pct:
                any_disc_fail = True
                self._add(ctx, "DISCOUNT_ERROR", "discount_validation", f"Line {l.line_no} {c}: discount {obs_d}% differs from the contractual {exp_d}% (quantity basis {basis}, threshold {agr.volume_discount_min_qty}).", line=l, product=c,
                          expected=exp_d, observed=obs_d, difference=obs_d - exp_d, exposure_key=f"LINE:{l.line_no}", identifiers=dict(agreement=agr.agreement_id))
        self._check(ctx, "price_validation", "FAILED" if any_price_fail else "PASSED")
        self._check(ctx, "discount_validation", "FAILED" if any_disc_fail else "PASSED")
        return out

    # ------------------------------------------------------------------ 10 arithmetic and tax
    def _check_arithmetic(self, ctx, resolved):
        inv = ctx["inv"]
        lt, ht = self.cfg.line_tolerance, self.cfg.header_tolerance
        bad_line = bad_tax = False
        ctx["policy_rate"] = {}
        for l in inv.lines:
            if None in (l.quantity, l.unit_price, l.line_amount):
                self._check(ctx, f"line_{l.line_no}_arithmetic", "INSUFFICIENT_EVIDENCE", "missing quantity/price/amount")
                continue
            exp = line_net(l.quantity, l.unit_price, l.discount_pct or ZERO, self.rp)
            if abs(l.line_amount - exp) > lt:
                bad_line = True
                self._add(ctx, "LINE_SUBTOTAL_ERROR", "line_arithmetic", f"Line {l.line_no}: amount {l.line_amount} differs from qty {l.quantity} x price {l.unit_price} less {l.discount_pct or 0}% discount = {exp}.", line=l,
                          expected=exp, observed=l.line_amount, difference=l.line_amount - exp, exposure_key=f"LINE:{l.line_no}")
            if l.tax_rate is not None and l.tax_amount is not None:
                texp = tax_on(l.line_amount, l.tax_rate, self.rp)
                if abs(l.tax_amount - texp) > lt:
                    bad_tax = True
                    self._add(ctx, "TAX_CALC_ERROR", "tax_arithmetic", f"Line {l.line_no}: tax {l.tax_amount} differs from {l.tax_rate}% of {l.line_amount} = {texp}.", line=l, expected=texp, observed=l.tax_amount, difference=l.tax_amount - texp,
                              exposure_key=f"LINE:{l.line_no}")
            c = resolved.get(l.line_no)
            if c and l.tax_rate is not None:
                cat = self.m.product_by_code[c].category
                pr = self.m.tax_rates.get(cat)
                if pr is not None:
                    ctx["policy_rate"][l.line_no] = pr
                    if abs(l.tax_rate - pr) > self.cfg.tax_rate_tolerance_pct:
                        bad_tax = True
                        self._add(ctx, "TAX_RATE_POLICY_MISMATCH", "tax_policy", f"Line {l.line_no} {c} ({cat}): tax rate {l.tax_rate}% differs from the synthetic policy rate {pr}%.", line=l, product=c, expected=pr, observed=l.tax_rate,
                                  difference=l.tax_rate - pr, exposure_key=f"LINE:{l.line_no}", identifiers=dict(category=cat))
        # tax presence
        with_tax = [l for l in inv.lines if l.tax_rate is not None and l.tax_amount is not None]
        if not inv.has_tax_info or (inv.lines and len(with_tax) < len(inv.lines)):
            self._add(ctx, "MISSING_TAX_INFO", "tax_information", "The invoice does not state tax rate and amount for every line." if inv.has_tax_info else "The invoice states no tax rate or tax amount.",
                      expected="tax rate and amount per line", observed="absent" if not inv.has_tax_info else "partially absent")
        # header totals
        lines_sum = sum((l.line_amount for l in inv.lines if l.line_amount is not None), ZERO)
        tax_sum = sum((l.tax_amount for l in inv.lines if l.tax_amount is not None), ZERO)
        charges = sum((c.amount for c in inv.charges), ZERO)
        if inv.subtotal is not None and inv.lines and abs(inv.subtotal - lines_sum) > ht:
            self._add(ctx, "LINE_SUBTOTAL_ERROR", "header_arithmetic", f"Header subtotal {inv.subtotal} differs from the sum of line amounts {lines_sum}.", expected=lines_sum, observed=inv.subtotal, difference=inv.subtotal - lines_sum,
                      exposure=max(ZERO, inv.subtotal - lines_sum), exposure_key="HEADER:SUB")
        if inv.tax_total is not None and with_tax and abs(inv.tax_total - tax_sum) > ht:
            self._add(ctx, "TAX_CALC_ERROR", "header_arithmetic", f"Header tax total {inv.tax_total} differs from the sum of line taxes {tax_sum}.", expected=tax_sum, observed=inv.tax_total, difference=inv.tax_total - tax_sum,
                      exposure=max(ZERO, inv.tax_total - tax_sum), exposure_key="HEADER:TAX")
        sub = inv.subtotal if inv.subtotal is not None else lines_sum
        if inv.grand_total is None:
            self._check(ctx, "grand_total", "INSUFFICIENT_EVIDENCE", "grand total missing")
        elif inv.has_tax_info:
            exp = sub + (inv.tax_total if inv.tax_total is not None else tax_sum) + charges
            if abs(inv.grand_total - exp) > ht:
                self._add(ctx, "GRAND_TOTAL_ERROR", "header_arithmetic", f"Grand total {inv.grand_total} differs from subtotal {sub} + tax {inv.tax_total if inv.tax_total is not None else tax_sum} + charges {charges} = {exp}.", expected=exp, observed=inv.grand_total,
                          difference=inv.grand_total - exp, exposure=max(ZERO, inv.grand_total - exp), exposure_key="HEADER:GRAND")
        else:
            policy_tax = sum((tax_on(l.line_amount, ctx["policy_rate"][l.line_no], self.rp) for l in inv.lines if l.line_amount is not None and l.line_no in ctx["policy_rate"]), ZERO)
            if abs(inv.grand_total - (sub + charges)) > ht and abs(inv.grand_total - (sub + charges + policy_tax)) > ht:
                self._add(ctx, "GRAND_TOTAL_ERROR", "header_arithmetic", f"Grand total {inv.grand_total} matches neither subtotal + charges ({sub + charges}) nor subtotal + charges + policy tax ({sub + charges + policy_tax}).", expected=sub + charges,
                          observed=inv.grand_total, difference=inv.grand_total - sub - charges, exposure=ZERO, exposure_key="HEADER:GRAND")
        self._check(ctx, "line_arithmetic", "FAILED" if bad_line else "PASSED")
        self._check(ctx, "tax_validation", "FAILED" if bad_tax else ("INSUFFICIENT_EVIDENCE" if not inv.has_tax_info else "PASSED"))

    # ------------------------------------------------------------------ 11 charges
    def _check_charges(self, ctx, sup, agr, comparable):
        inv = ctx["inv"]
        if not inv.charges:
            self._check(ctx, "additional_charges", "PASSED", "no additional charges")
            return
        if not (sup and agr and comparable):
            self._check(ctx, "additional_charges", "INSUFFICIENT_EVIDENCE", "no applicable agreement to validate charges")
            return
        bad = False
        for i, ch in enumerate(inv.charges):
            allowed = ch.charge_type in agr.allowed_charge_types
            if not allowed:
                bad = True
                self._add(ctx, "UNAUTHORIZED_CHARGE", "charge_validation", f"{ch.description or ch.charge_type} of {ch.amount} is not permitted by agreement {agr.agreement_id}.", expected="0.00", observed=ch.amount, difference=ch.amount,
                          exposure=ch.amount, exposure_key=f"CHARGE:{i}", identifiers=dict(agreement=agr.agreement_id, allowed=agr.allowed_charge_types))
            elif ch.charge_type == "FREIGHT" and agr.freight_cap > 0 and ch.amount > agr.freight_cap:
                bad = True
                self._add(ctx, "UNAUTHORIZED_CHARGE", "charge_validation", f"Freight {ch.amount} exceeds the agreed cap of {agr.freight_cap} ({agr.agreement_id}).", expected=f"<= {agr.freight_cap}", observed=ch.amount,
                          difference=ch.amount - agr.freight_cap, exposure=ch.amount - agr.freight_cap, exposure_key=f"CHARGE:{i}", identifiers=dict(agreement=agr.agreement_id, cap=str(agr.freight_cap)))
        self._check(ctx, "additional_charges", "FAILED" if bad else "PASSED")

    # ------------------------------------------------------------------ 12 exposure per line
    def _line_exposures(self, ctx, resolved, supportable, contract_prices, agr, po):
        inv = ctx["inv"]
        money_codes = {"PRICE_ABOVE_CONTRACT", "QTY_EXCEEDS_ORDERED", "QTY_EXCEEDS_RECEIVED", "DISCOUNT_ERROR", "LINE_SUBTOTAL_ERROR", "TAX_CALC_ERROR", "TAX_RATE_POLICY_MISMATCH"}
        by_line: dict[int, list[AuditFinding]] = defaultdict(list)
        for f in ctx["findings"]:
            if f.code in money_codes and f.exposure_key and f.exposure_key.startswith("LINE:"):
                by_line[int(f.exposure_key.split(":")[1])].append(f)
        for l in inv.lines:
            fs = by_line.get(l.line_no)
            if not fs or None in (l.quantity, l.unit_price, l.line_amount):
                continue
            qty = supportable.get(l.line_no)
            qty = l.quantity if qty is None else qty
            price = contract_prices.get(l.line_no)
            price = l.unit_price if price is None else min(price, l.unit_price)
            disc = ctx["disc_expected"].get(l.line_no, l.discount_pct or ZERO)
            sup_net = line_net(qty, price, disc, self.rp)
            rate = ctx["policy_rate"].get(l.line_no, l.tax_rate)
            sup_tax = tax_on(sup_net, rate, self.rp) if rate is not None else ZERO
            obs_tax = l.tax_amount if l.tax_amount is not None else ZERO
            exposure = max(ZERO, (l.line_amount + obs_tax) - (sup_net + sup_tax))
            for f in fs:
                f.exposure_amount = self._q(exposure)

    # ------------------------------------------------------------------ finalise
    def _finalise(self, ctx, res: InvoiceAuditResult):
        inv = ctx["inv"]
        findings: list[AuditFinding] = ctx["findings"]
        low = inv.extraction_confidence < self.low_conf
        if low:
            findings.append(AuditFinding(finding_id=self._fid(ctx), invoice_id=inv.invoice_id, code="EXTRACTION_LOW_CONFIDENCE", check="extraction_quality", status=T.MANUAL_REVIEW, severity="MEDIUM",
                                         message=f"Extraction confidence {inv.extraction_confidence:.2f} ({inv.extraction_method}); {'; '.join(w for w in inv.warnings if 'integrity' in w or 'recovered' in w) or 'verify against the source document'}.",
                                         reason=T.info("EXTRACTION_LOW_CONFIDENCE").description, needs_human_review=True, confidence=inv.extraction_confidence))
            for f in findings:
                if f.status == T.CONFIRMED:
                    f.status, f.needs_human_review = T.POTENTIAL, True
                    f.reason += " [downgraded: low-confidence extraction, verify against the original document]"
        weak = ctx.get("weak_sources") or []
        if weak:
            for f in findings:
                if f.check in ("three_way_match", "discount_validation") and f.status == T.CONFIRMED:
                    f.status, f.needs_human_review = T.POTENTIAL, True
                    f.reason += f" [downgraded: relies on OCR-derived linked document(s) {', '.join(weak)}; verify against the originals]"
        for f in findings:
            f.confidence = round(min(f.confidence, inv.extraction_confidence, ctx.get("linked_conf", 1.0) if f.check in ("three_way_match", "discount_validation") else 1.0), 3)
            if self.evidence_fn and f.status != T.PASSED:
                try:
                    cat = self.m.product_by_code[f.product_code].category if f.product_code in self.m.product_by_code else None
                    desc = self.m.product_by_code[f.product_code].description if f.product_code in self.m.product_by_code else None
                    agr = ctx.get("agreement")
                    f.evidence = self.evidence_fn(f.code, res.supplier_id, f.product_code, dict(agreement_id=agr.agreement_id if agr else None, category=cat, product_desc=desc))
                except Exception as e:  # noqa: BLE001 - evidence is supplementary
                    f.identifiers["evidence_error"] = f"{type(e).__name__}: {e}"
        res.findings = findings
        res.checks = ctx["checks"]
        # exposure without double counting: one amount per (invoice, exposure_key)
        keyed: dict[str, Decimal] = {}
        for f in findings:
            if f.exposure_key and f.status in (T.CONFIRMED, T.POTENTIAL):
                keyed[f.exposure_key] = max(keyed.get(f.exposure_key, ZERO), f.exposure_amount)
        res.total_exposure = self._q(sum(keyed.values(), ZERO))
        real = [f for f in findings if f.status != T.PASSED and f.code != "EXTRACTION_LOW_CONFIDENCE"]
        if any(f.status in (T.CONFIRMED, T.POTENTIAL) for f in real):
            res.overall_status = "FLAGGED"
        elif any(f.status in (T.MANUAL_REVIEW, T.INSUFFICIENT_EVIDENCE) for f in findings):
            res.overall_status = "MANUAL_REVIEW"
        elif findings:
            res.overall_status = "PASSED_WITH_NOTES"
        else:
            res.overall_status = "PASSED"
        res.human_review_status = "PENDING" if any(f.status != T.PASSED for f in findings) else "NOT_REQUIRED"
        res.unresolved_questions = [f.message for f in findings if f.status in (T.POTENTIAL, T.MANUAL_REVIEW, T.INSUFFICIENT_EVIDENCE)]
        seen, actions = set(), []
        for f in findings:
            if f.status != T.PASSED and f.code not in seen and f.code in RECOMMENDED:
                seen.add(f.code)
                actions.append(RECOMMENDED[f.code])
        res.recommended_actions = actions

    def _record_ledger(self, ctx, sup, po, resolved, dup_ids):
        inv = ctx["inv"]
        sk, nk, pk, sig = ctx["dupkeys"]
        qty: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for l in inv.lines:
            c = resolved.get(l.line_no)
            if c and l.quantity is not None:
                qty[c] += l.quantity
        self.ledger.append(LedgerEntry(invoice_id=inv.invoice_id, supplier_key=sk, number_key=nk, po_key=pk, grand_total=inv.grand_total, signature=sig, qty_by_product=dict(qty), source_file=inv.source_file,
                                       is_duplicate=bool(dup_ids)))
