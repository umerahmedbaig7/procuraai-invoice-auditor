from decimal import Decimal as D

from procuraai.audit.money import line_net, tax_on, to_decimal
from procuraai.normalization import (ProductMatcher, SupplierMatcher, invoice_key, normalize_code, normalize_desc, normalize_name, normalize_uom, parse_date)
from procuraai.datagen.catalog import ELECTRICAL_PKR as P


def pm():
    return ProductMatcher(P.products)


def test_09_valid_fuzzy_product_match_works():
    m = pm().match(None, "Breaker Miniature Circuit 2-Pole 32A")
    assert m.matched_id == "ELE-1002" and not m.needs_review and m.method == "fuzzy"
    m = pm().match(None, "MCB 2P 32A")
    assert m.matched_id == "ELE-1002" and m.method == "alias"


def test_10_ambiguous_product_match_requires_review():
    m = pm().match(None, "Miniature Circuit Breaker 32A")
    assert m.matched_id is None and m.needs_review and m.method == "ambiguous" and {c.key for c in m.candidates[:2]} == {"ELE-1002", "ELE-1003"}


def test_unknown_code_is_not_auto_accepted():
    m = pm().match("ELE-9901", "Hybrid Solar Inverter 5kW Single Phase")
    assert m.matched_id is None and m.method == "code_unknown"


def test_code_description_conflict_goes_to_review():
    m = pm().match("ELE-1002", "PVC Insulated Cable 4mm Single Core 100m Coil")
    assert m.needs_review and m.method == "code_desc_conflict"


def test_supplier_matching_exact_alias_fuzzy_unknown():
    sm = SupplierMatcher([s.info for s in P.suppliers])
    assert sm.match("Karachi Electro Traders (Pvt) Ltd").method == "exact"
    assert sm.match("KET Karachi").method == "alias"
    assert sm.match("Karachi Electro Trader Pvt Ltd").matched_id == "SUP-001"
    assert sm.match("Gwadar General Traders").matched_id is None
    assert sm.match("Totally Different Name", tax_id="SYN-TAX-0002-2").method == "tax_id"


def test_normalizers():
    assert normalize_name("Indus Components & Circuits (Pvt) Ltd") == "indus components circuits"
    assert normalize_code("ele 1001") == "ELE-1001"
    assert normalize_uom("Mtrs") == "MTR"
    assert normalize_desc("2-Pole 32A") == normalize_desc("2 Pole 32 Amp")
    assert [parse_date(x).isoformat() for x in ("12-Mar-2025", "12/03/2025", "March 12, 2025", "2025-03-12")] == ["2025-03-12"] * 4
    assert invoice_key("IC2025-00141") == invoice_key("1C2025-00141")      # OCR-confusable folding


def test_decimal_money_rules():
    assert line_net(D("3"), D("19.99"), D("10")) == D("53.97")          # 59.97 - 6.00 (half-up)
    assert tax_on(D("100.05"), D("15")) == D("15.01")                    # 15.0075 -> 15.01
    assert to_decimal("1,234.50") == D("1234.50") and to_decimal("n/a") is None and to_decimal("(12.00)") == D("-12.00")
    assert D("0.1") + D("0.2") == D("0.3")                               # no binary-float drift
