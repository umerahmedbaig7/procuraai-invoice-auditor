"""Normalization and entity matching.

Original extracted values are always kept next to normalized ones (see ``MatchResult``) so an auditor
can trace each transformation. Low-confidence fuzzy matches are never auto-accepted: they set
``needs_review=True`` and are routed to the human-review queue.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Iterable

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from .config import AuditConfig
from .schemas import ProductInfo, SupplierInfo

# ---------------------------------------------------------------------------------------------
# Scalar normalizers
# ---------------------------------------------------------------------------------------------
_LEGAL = {"pvt", "private", "ltd", "limited", "co", "company", "corp", "inc", "llc", "smc", "the", "and"}
_UOM = {
    "pcs": "PCS", "pc": "PCS", "nos": "PCS", "no": "PCS", "each": "PCS", "ea": "PCS", "unit": "PCS", "units": "PCS",
    "mtr": "MTR", "mtrs": "MTR", "m": "MTR", "meter": "MTR", "metre": "MTR", "meters": "MTR", "metres": "MTR",
    "box": "BOX", "boxes": "BOX", "bx": "BOX", "roll": "ROLL", "rolls": "ROLL", "rl": "ROLL",
    "set": "SET", "sets": "SET", "kg": "KG", "kgs": "KG", "pkt": "PKT", "pack": "PKT", "packs": "PKT",
}
_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%B %d, %Y", "%b %d, %Y", "%d.%m.%Y", "%Y/%m/%d", "%d-%b-%y"]


def normalize_name(s: str | None) -> str:
    """Lowercase, strip punctuation and legal suffixes: 'Karachi Electro Traders (Pvt.) Ltd.' -> 'karachi electro traders'."""
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9& ]+", " ", s.lower().replace("&", " and "))
    toks = [t for t in s.split() if t not in _LEGAL]
    return " ".join(toks)


def normalize_code(s: str | None) -> str:
    """'ele 1001', 'ELE_1001', 'ele–1001' -> 'ELE-1001'. Non-matching strings are only upper-cased/stripped."""
    if not s:
        return ""
    t = re.sub(r"[\u2010-\u2015_\s]+", "-", s.strip().upper())
    m = re.fullmatch(r"([A-Z]{2,4})-*(\d{3,5})", t)
    return f"{m.group(1)}-{m.group(2)}" if m else t


def normalize_invoice_number(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


_CONFUSABLE = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "Q": "0"})


def invoice_key(s: str | None) -> str:
    """Duplicate-detection key: upper-case alphanumerics with OCR-confusable characters folded (I/L->1, O/Q->0, S->5, B->8, Z->2).
    Folding is applied to both sides of every comparison, so a re-scan with 'IC2025-0014' read as '1C2025-0014' still matches."""
    return normalize_invoice_number(s).translate(_CONFUSABLE)


def normalize_uom(s: str | None) -> str | None:
    if not s:
        return None
    return _UOM.get(s.strip().lower().rstrip("."), s.strip().upper())


def normalize_currency(s: str | None) -> str | None:
    if not s:
        return None
    t = s.strip().upper().replace("RS.", "PKR").replace("RS", "PKR")
    return {"PKR": "PKR", "USD": "USD", "$": "USD", "EUR": "EUR", "RUPEES": "PKR"}.get(t, t)


def parse_date(s: str | date | None) -> date | None:
    """Parse the date formats seen in the dataset. Ambiguous day/month values are read day-first (documented)."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    t = str(s).strip().rstrip(".,")
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    for f in _DATE_FORMATS:
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            continue
    return None


_SYN = {"amp": "a", "amps": "a", "ampere": "a", "amperes": "a", "pole": "p", "poles": "p", "way": "w", "ways": "w",
        "watt": "w", "watts": "w", "volt": "v", "volts": "v", "metre": "m", "meter": "m", "mtr": "m",
        "core": "c", "cores": "c", "pair": "pr", "pcs": "", "inch": "in"}


def normalize_desc(s: str | None) -> str:
    """Normalize a product description for comparison: '2-Pole 32A' and '2 Pole 32 Amp' both give '2 p 32 a'."""
    if not s:
        return ""
    t = s.lower().replace("-", " ").replace("/", " ").replace("x", "x")
    t = re.sub(r"[^a-z0-9. ]+", " ", t)
    t = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", t)
    toks = [_SYN.get(w, w) for w in t.split()]
    return " ".join(w for w in toks if w)


def numeric_tokens(norm_desc: str) -> set[str]:
    return {t for t in norm_desc.split() if re.fullmatch(r"\d+(\.\d+)?", t)}


# ---------------------------------------------------------------------------------------------
# Match results
# ---------------------------------------------------------------------------------------------
class Candidate(BaseModel):
    key: str
    label: str
    score: float


class MatchResult(BaseModel):
    original: str | None
    normalized: str | None
    matched_id: str | None = None
    method: str = "none"          # exact | alias | tax_id | fuzzy | semantic | ambiguous | none | code_exact | code_unknown
    score: float = 0.0
    needs_review: bool = False
    note: str = ""
    candidates: list[Candidate] = Field(default_factory=list)
    original_code: str | None = None
    description_variant: bool = False


class SupplierMatcher:
    def __init__(self, suppliers: Iterable[SupplierInfo], cfg: AuditConfig | None = None):
        self.cfg = cfg or AuditConfig()
        self.suppliers = {s.supplier_id: s for s in suppliers}
        self._names: dict[str, str] = {}
        self._alias: dict[str, str] = {}
        self._tax: dict[str, str] = {}
        for s in self.suppliers.values():
            self._names[normalize_name(s.name)] = s.supplier_id
            for a in s.aliases:
                self._alias[normalize_name(a)] = s.supplier_id
            if s.tax_id:
                self._tax[re.sub(r"[^A-Z0-9]", "", s.tax_id.upper())] = s.supplier_id

    def match(self, name: str | None, tax_id: str | None = None, supplier_id: str | None = None) -> MatchResult:
        norm = normalize_name(name)
        res = MatchResult(original=name, normalized=norm)
        if supplier_id and supplier_id in self.suppliers:
            res.matched_id, res.method, res.score = supplier_id, "exact", 100.0
            return res
        if norm in self._names:
            res.matched_id, res.method, res.score = self._names[norm], "exact", 100.0
            return res
        if norm in self._alias:
            res.matched_id, res.method, res.score = self._alias[norm], "alias", 100.0
            return res
        if tax_id:
            k = re.sub(r"[^A-Z0-9]", "", tax_id.upper())
            if k in self._tax:
                res.matched_id, res.method, res.score = self._tax[k], "tax_id", 95.0
                res.note = "matched on tax id; name differs"
                return res
        if not norm:
            res.note = "no supplier name"
            return res
        pool = {**self._names, **self._alias}
        scored = sorted(((fuzz.token_sort_ratio(norm, k), k) for k in pool), reverse=True)[:3]
        res.candidates = [Candidate(key=pool[k], label=k, score=float(sc)) for sc, k in scored]
        best, bk = scored[0]
        if best >= self.cfg.supplier_accept:
            res.matched_id, res.method, res.score = pool[bk], "fuzzy", float(best)
        elif best >= self.cfg.supplier_review:
            res.matched_id, res.method, res.score = pool[bk], "fuzzy", float(best)
            res.needs_review = True
            res.note = f"low-confidence fuzzy supplier match ({best:.0f})"
        else:
            res.score = float(best)
            res.note = "no supplier above review threshold"
        return res


class ProductMatcher:
    """Resolve an invoice/PO/DC line to a catalogue product.

    Order: code lookup -> alias -> fuzzy (with numeric-token guard and margin test) -> optional semantic hook.
    """

    def __init__(self, products: Iterable[ProductInfo], cfg: AuditConfig | None = None,
                 semantic_fn: Callable[[str, int], list[tuple[str, float]]] | None = None):
        self.cfg = cfg or AuditConfig()
        self.products = {p.product_code: p for p in products}
        self._norm = {c: normalize_desc(p.description) for c, p in self.products.items()}
        self._alias: dict[str, str] = {}
        for c, p in self.products.items():
            for a in p.aliases:
                self._alias[normalize_desc(a)] = c
        self.semantic_fn = semantic_fn

    def _fuzzy(self, q: str) -> list[Candidate]:
        qn = numeric_tokens(q)
        out = []
        for c, nd in self._norm.items():
            score = fuzz.token_set_ratio(q, nd)
            # Penalize candidates whose numeric specification differs from the query's.
            cn = numeric_tokens(nd)
            if qn and not qn.issubset(cn):
                score *= 0.6
            elif qn != cn:
                score = min(score, self.cfg.product_accept - 1)   # incomplete spec: never auto-accept
            out.append(Candidate(key=c, label=self.products[c].description, score=float(score)))
        return sorted(out, key=lambda x: -x.score)[:4]

    def description_similarity(self, code: str, description: str) -> float:
        q = normalize_desc(description)
        if not q:
            return 100.0
        if q == self._norm[code]:
            return 100.0
        if self._alias.get(q) == code:
            return 99.0          # known alias: acceptable, but reported as a description variant
        return float(fuzz.token_set_ratio(q, self._norm[code]))

    def match(self, code: str | None, description: str | None) -> MatchResult:
        ncode = normalize_code(code) if code and code.strip() not in ("-", "N/A", "") else ""
        q = normalize_desc(description)
        res = MatchResult(original=description, normalized=q, original_code=code)
        if ncode and ncode in self.products:
            res.matched_id, res.method, res.score = ncode, "code_exact", 100.0
            if q:
                sim = self.description_similarity(ncode, description or "")
                if sim < self.cfg.code_desc_min:
                    # Code is valid but the text describes something else: do not trust either blindly.
                    res.needs_review, res.method = True, "code_desc_conflict"
                    res.note = f"description similarity to {ncode} is only {sim:.0f}"
                    res.candidates = self._fuzzy(q)[:3]
                elif sim < 100.0:
                    res.description_variant = True
                    res.note = f"description variant (similarity {sim:.0f})"
            return res
        if ncode:
            res.method = "code_unknown"
            res.note = f"code {ncode} not in product master"
        if not q:
            return res
        if q in self._alias:
            res.matched_id, res.method, res.score = self._alias[q], "alias", 100.0
            res.description_variant = True
            res.needs_review = bool(ncode)       # unknown code + alias description: a human must confirm
            return res
        for c, nd in self._norm.items():
            if nd == q:
                res.matched_id, res.method, res.score = c, "exact", 100.0
                res.needs_review = bool(ncode)
                return res
        cands = self._fuzzy(q)
        res.candidates = cands[:3]
        best = cands[0]
        second = cands[1].score if len(cands) > 1 else 0.0
        if best.score >= self.cfg.product_accept and best.score - second >= self.cfg.product_margin and not ncode:
            res.matched_id, res.method, res.score = best.key, "fuzzy", best.score
            res.description_variant = True
            res.note = f"fuzzy match {best.score:.0f}"
        elif best.score >= self.cfg.product_review:
            res.matched_id, res.method, res.score = None, "ambiguous", best.score
            res.needs_review = True
            res.note = "several plausible products or incomplete specification" if not ncode else "unknown code; description resembles catalogue product"
        else:
            if self.semantic_fn is not None:
                sem = self.semantic_fn(description or "", 3)
                if sem:
                    res.candidates = [Candidate(key=c, label=self.products[c].description, score=float(s) * 100) for c, s in sem if c in self.products]
                    res.method, res.needs_review, res.note = "semantic", True, "semantic candidates only; never auto-accepted"
                    return res
            res.score = best.score
            res.note = res.note or "no catalogue product above review threshold"
        return res
