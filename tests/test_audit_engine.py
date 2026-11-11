"""Deterministic audit engine tests (scenarios 1-25 of the brief). Ground truth is used only to pick test inputs."""
import copy
from decimal import Decimal as D

import pytest

from conftest import codes, new_engine


def fnd(res, code):
    return [f for f in res.findings if f.code == code]


def test_01_valid_invoice_passes(results, by_code):
    for iid in by_code["NONE"][:10]:
        r = results[iid]
        assert r.overall_status in ("PASSED", "PASSED_WITH_NOTES"), (iid, [f.code for f in r.findings])
        assert r.total_exposure == 0 and r.human_review_status == "NOT_REQUIRED"


def test_02_price_overcharge_detected(results, by_code):
    r = results[by_code["PRICE_ABOVE_CONTRACT"][0]]
    f = fnd(r, "PRICE_ABOVE_CONTRACT")[0]
    assert f.status == "CONFIRMED" and D(f.observed) > D(f.expected) and D(f.difference) == D(f.observed) - D(f.expected)
    assert r.total_exposure > 0 and f.line_no is not None


def test_03_quantity_overbilling_detected(results, by_code, gt_codes):
    ids = [i for i, c in gt_codes.items() if "QTY_EXCEEDS_RECEIVED" in c]
    assert ids
    for i in ids:
        f = fnd(results[i], "QTY_EXCEEDS_RECEIVED")[0]
        assert f.status == "CONFIRMED" and D(f.observed) > D(f.expected)
    f = fnd(results[[i for i, c in gt_codes.items() if "QTY_EXCEEDS_ORDERED" in c][0]], "QTY_EXCEEDS_ORDERED")[0]
    assert D(f.observed) > D(f.expected)


def test_04_duplicate_invoice_detected(results, gt_codes):
    exact = [i for i, c in gt_codes.items() if "DUPLICATE_EXACT" in c]
    assert len(exact) == 3                                        # identical copy x2 + re-scan in a different format
    for i in exact:
        f = fnd(results[i], "DUPLICATE_EXACT")[0]
        assert f.status == "CONFIRMED" and f.exposure_amount == results[i].grand_total and f.identifiers["original"] != i
    pos = [i for i, c in gt_codes.items() if "POSSIBLE_DUPLICATE" in c][0]
    assert fnd(results[pos], "POSSIBLE_DUPLICATE")[0].status == "POTENTIAL"     # distinguishes possible from exact


def test_05_incorrect_tax_detected(results, by_code):
    f = fnd(results[by_code["TAX_CALC_ERROR"][0]], "TAX_CALC_ERROR")[0]
    assert D(f.observed) > D(f.expected) and f.status == "CONFIRMED"


def test_06_incorrect_grand_total_detected(results, by_code):
    f = fnd(results[by_code["GRAND_TOTAL_ERROR"][0]], "GRAND_TOTAL_ERROR")[0]
    assert D(f.difference) > 0 and f.exposure_amount == D(f.difference)


def test_07_missing_po_is_flagged_for_review_not_confirmed(results, by_code):
    r = results[by_code["MISSING_PO"][0]]
    f = fnd(r, "MISSING_PO")[0]
    assert f.status == "MANUAL_REVIEW" and r.human_review_status == "PENDING"
    assert "QTY_EXCEEDS_ORDERED" not in codes(r)                  # no ordered quantity to compare with: not invented


def test_08_missing_dc_triggers_review_and_is_not_proof(results, by_code):
    r = results[by_code["MISSING_DC"][0]]
    f = fnd(r, "MISSING_DC")[0]
    assert f.status == "MANUAL_REVIEW" and "not proof" in f.reason
    assert "QTY_EXCEEDS_RECEIVED" not in codes(r)


def test_11_expired_contract_handled(results, by_code):
    r = results[by_code["CONTRACT_NOT_EFFECTIVE"][0]]
    f = fnd(r, "CONTRACT_NOT_EFFECTIVE")[0]
    assert f.status == "INSUFFICIENT_EVIDENCE"
    assert "PRICE_ABOVE_CONTRACT" not in codes(r)                 # price is not judged without an effective agreement
    assert next(c for c in r.checks if c.check == "price_validation").status == "SKIPPED"


def test_12_currency_mismatch_detected_and_amounts_not_compared(results, by_code):
    r = results[by_code["CURRENCY_MISMATCH"][0]]
    assert fnd(r, "CURRENCY_MISMATCH")[0].status == "CONFIRMED"
    assert "PRICE_ABOVE_CONTRACT" not in codes(r) and next(c for c in r.checks if c.check == "price_validation").status == "SKIPPED"


def test_16_repeated_findings_do_not_double_count_exposure(ds, master):
    """Price AND quantity error on the SAME line: both findings carry one exposure_key, counted once."""
    clean = next(i for i in ds.invoices if i.invoice_number and ds.invoice_meta[i.invoice_id]["scenario_no"] == 1 and len(i.lines) >= 2)
    inv = copy.deepcopy(clean)
    l = inv.lines[0]
    l.unit_price = l.unit_price * D("1.2")
    l.quantity = l.quantity + 10
    from procuraai.datagen.generator import recompute
    recompute(inv)
    eng = new_engine(ds, master)
    r = eng.audit_invoice(inv, "T")
    line_f = [f for f in r.findings if f.exposure_key == "LINE:1" and f.exposure_amount > 0]
    assert {f.code for f in line_f} >= {"PRICE_ABOVE_CONTRACT", "QTY_EXCEEDS_ORDERED"}
    assert len({f.exposure_amount for f in line_f}) == 1          # same amount on every finding of the line
    assert r.total_exposure == line_f[0].exposure_amount          # counted once, not once per finding
    naive = sum(f.exposure_amount for f in r.findings)
    assert r.total_exposure < naive


def test_18_clean_invoices_get_no_false_anomaly_labels(results, by_code):
    for iid in by_code["NONE"]:
        bad = [f.code for f in results[iid].findings if f.severity != "INFO" or f.status != "PASSED"]
        assert not bad, (iid, bad)


def test_19_partial_deliveries_are_aggregated(results, gt_codes):
    ids = [i for i, c in gt_codes.items() if "PARTIAL_DELIVERY_RECONCILED" in c]
    for i in ids:
        r = results[i]
        assert len(r.linked_dcs) == 2 and "QTY_EXCEEDS_RECEIVED" not in codes(r)
        assert fnd(r, "PARTIAL_DELIVERY_RECONCILED")[0].severity == "INFO"


def test_20_po_dc_conflict_is_potential(results, gt_codes):
    i = next(i for i, c in gt_codes.items() if c == {"PO_DC_QTY_CONFLICT"})
    assert fnd(results[i], "PO_DC_QTY_CONFLICT")[0].status == "POTENTIAL" and "QTY_EXCEEDS_ORDERED" not in codes(results[i])


def test_21_22_tax_information_and_policy(results, by_code):
    r = results[by_code["MISSING_TAX_INFO"][0]]
    assert fnd(r, "MISSING_TAX_INFO")[0].status == "MANUAL_REVIEW" and "GRAND_TOTAL_ERROR" not in codes(r)
    r = results[by_code["TAX_RATE_POLICY_MISMATCH"][0]]
    assert fnd(r, "TAX_RATE_POLICY_MISMATCH")[0].status == "CONFIRMED" and "TAX_CALC_ERROR" not in codes(r)


def test_25_multiple_simultaneous_anomalies(results, gt_codes):
    multi = [i for i, c in gt_codes.items() if len(c) >= 3]
    assert len(multi) >= 3
    for i in multi:
        assert codes(results[i]) == gt_codes[i]


def test_unauthorized_charge_and_cap(results, gt_codes):
    ids = [i for i, c in gt_codes.items() if "UNAUTHORIZED_CHARGE" in c]
    assert len(ids) >= 4
    assert all(fnd(results[i], "UNAUTHORIZED_CHARGE")[0].status == "CONFIRMED" for i in ids)


def test_unknown_supplier_skips_contract_checks(results, by_code):
    r = results[by_code["UNKNOWN_SUPPLIER"][0]]
    assert fnd(r, "UNKNOWN_SUPPLIER") and next(c for c in r.checks if c.check == "contract_validity").status == "SKIPPED"


def test_tolerance_is_configurable(ds, master):
    from procuraai.config import AuditConfig
    clean = next(i for i in ds.invoices if ds.invoice_meta[i.invoice_id]["scenario_no"] == 1)
    inv = copy.deepcopy(clean)
    inv.lines[0].unit_price += D("0.50")
    from procuraai.datagen.generator import recompute
    recompute(inv)
    strict = new_engine(ds, master).audit_invoice(copy.deepcopy(inv), "T")
    loose = new_engine(ds, master, cfg=AuditConfig(price_tolerance_abs=D("1.00"))).audit_invoice(copy.deepcopy(inv), "T")
    assert "PRICE_ABOVE_CONTRACT" in codes(strict) and "PRICE_ABOVE_CONTRACT" not in codes(loose)


def test_low_confidence_extraction_downgrades_confirmed_findings(ds, master):
    inv = copy.deepcopy(next(i for i in ds.invoices if ds.invoice_meta[i.invoice_id]["scenario_no"] == 1))
    inv.lines[0].unit_price *= 2
    from procuraai.datagen.generator import recompute
    recompute(inv)
    inv.extraction_confidence = 0.5
    r = new_engine(ds, master).audit_invoice(inv, "T")
    f = fnd(r, "PRICE_ABOVE_CONTRACT")[0]
    assert f.status == "POTENTIAL" and "downgraded" in f.reason and fnd(r, "EXTRACTION_LOW_CONFIDENCE")
