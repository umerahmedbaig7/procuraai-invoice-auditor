"""Anomaly taxonomy shared by the dataset generator (ground truth), the audit engine and reports.

Every finding code has a default *status* and *severity*. Status distinguishes confirmed rule
violations from potential anomalies, so the system never labels a supplier fraudulent merely
because a discrepancy exists.
"""
from __future__ import annotations

from dataclasses import dataclass

# Finding statuses ------------------------------------------------------------------------
CONFIRMED = "CONFIRMED"                      # deterministic arithmetic / rule violation against supplied evidence
POTENTIAL = "POTENTIAL"                      # suspected anomaly, needs a human to decide
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # a check could not be completed
MANUAL_REVIEW = "MANUAL_REVIEW"              # explicit routing to the human-review queue
PASSED = "PASSED"                            # check passed (INFO notes use this status)
STATUSES = (CONFIRMED, POTENTIAL, INSUFFICIENT_EVIDENCE, MANUAL_REVIEW, PASSED)

SEVERITIES = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class CodeInfo:
    code: str
    category: str
    status: str
    severity: str
    description: str


_ROWS = [
    ("PRICE_ABOVE_CONTRACT", "pricing", CONFIRMED, "HIGH", "Invoiced unit price is above the applicable contract price."),
    ("QTY_EXCEEDS_RECEIVED", "quantity", CONFIRMED, "HIGH", "Invoiced quantity exceeds the cumulative quantity recorded as received."),
    ("QTY_EXCEEDS_ORDERED", "quantity", CONFIRMED, "HIGH", "Invoiced quantity exceeds the purchase-order quantity."),
    ("DUPLICATE_EXACT", "duplicate", CONFIRMED, "CRITICAL", "Same supplier and normalized invoice number already processed."),
    ("POSSIBLE_DUPLICATE", "duplicate", POTENTIAL, "HIGH", "Different invoice number but same supplier, PO and economics as an earlier invoice."),
    ("LINE_SUBTOTAL_ERROR", "arithmetic", CONFIRMED, "MEDIUM", "Line amount differs from quantity x price less discount."),
    ("TAX_CALC_ERROR", "arithmetic", CONFIRMED, "MEDIUM", "Tax amount differs from net amount x stated tax rate."),
    ("GRAND_TOTAL_ERROR", "arithmetic", CONFIRMED, "HIGH", "Grand total differs from subtotal + tax + charges."),
    ("UNAUTHORIZED_CHARGE", "charges", CONFIRMED, "HIGH", "Additional charge is not permitted (or exceeds the cap) under the supplier agreement."),
    ("MISSING_PO", "documents", MANUAL_REVIEW, "HIGH", "No matching purchase order was found."),
    ("MISSING_DC", "documents", MANUAL_REVIEW, "MEDIUM", "No matching delivery challan / goods-received note was found."),
    ("UNKNOWN_PRODUCT_CODE", "product", MANUAL_REVIEW, "MEDIUM", "Product code is not in the product master."),
    ("PRODUCT_DESCRIPTION_VARIANT", "product", PASSED, "INFO", "Description differs from the catalogue but resolves to a single product."),
    ("AMBIGUOUS_PRODUCT", "product", MANUAL_REVIEW, "MEDIUM", "Description matches several catalogue products; human decision required."),
    ("PRODUCT_CODE_DESCRIPTION_MISMATCH", "product", MANUAL_REVIEW, "MEDIUM", "Product code and description refer to different catalogue items."),
    ("UNKNOWN_SUPPLIER", "supplier", MANUAL_REVIEW, "HIGH", "Supplier is not present in the supplier master."),
    ("SUPPLIER_MATCH_UNCERTAIN", "supplier", MANUAL_REVIEW, "LOW", "Supplier name only matched with low confidence."),
    ("SUPPLIER_DETAILS_INCONSISTENT", "supplier", POTENTIAL, "MEDIUM", "Supplier tax id or details differ from the supplier master."),
    ("CONTRACT_NOT_EFFECTIVE", "contract", INSUFFICIENT_EVIDENCE, "MEDIUM", "No supplier agreement was effective on the transaction date; price cannot be validated."),
    ("DISCOUNT_ERROR", "pricing", CONFIRMED, "MEDIUM", "Discount applied differs from the contractual volume discount."),
    ("PARTIAL_DELIVERY_RECONCILED", "quantity", PASSED, "INFO", "Invoice quantity reconciles only after aggregating several delivery records."),
    ("PO_DC_QTY_CONFLICT", "quantity", POTENTIAL, "MEDIUM", "Received quantity exceeds ordered quantity (over-delivery / conflicting records)."),
    ("MISSING_TAX_INFO", "tax", MANUAL_REVIEW, "MEDIUM", "Invoice does not state tax rate/amount; tax cannot be validated."),
    ("TAX_RATE_POLICY_MISMATCH", "tax", CONFIRMED, "MEDIUM", "Tax rate differs from the (synthetic) policy rate for the product category."),
    ("DATE_REFERENCE_INCONSISTENT", "references", POTENTIAL, "MEDIUM", "Invoice dates or document references are inconsistent with the linked documents."),
    ("CURRENCY_MISMATCH", "currency", CONFIRMED, "HIGH", "Invoice currency differs from the PO / agreement currency."),
    # operational codes (not part of the labelled scenarios)
    ("NO_CONTRACT_PRICE", "contract", INSUFFICIENT_EVIDENCE, "LOW", "The effective agreement has no price for this product; price cannot be validated."),
    ("EXTRACTION_LOW_CONFIDENCE", "extraction", MANUAL_REVIEW, "MEDIUM", "Extraction from the source document is unreliable (OCR/integrity); findings need verification against the original."),
]
OPERATIONAL_CODES = {"EXTRACTION_LOW_CONFIDENCE"}

CODES: dict[str, CodeInfo] = {r[0]: CodeInfo(*r) for r in _ROWS}

# Scenario numbers from the project brief (1-25) mapped to the code(s) they exercise.
SCENARIOS = {
    1: "Clean invoice, valid three-way match", 2: "Unit price above contract", 3: "Qty above received",
    4: "Qty above ordered", 5: "Duplicate invoice (identical copy, different filename)",
    6: "Duplicate invoice (re-scan in a different format and filename)", 7: "Incorrect line subtotal",
    8: "Incorrect tax calculation", 9: "Incorrect grand total", 10: "Unauthorized additional charge",
    11: "Missing purchase order", 12: "Missing delivery challan", 13: "Unknown product code",
    14: "Description variant of a known product", 15: "Ambiguous product description", 16: "Unknown supplier",
    17: "Expired / inapplicable pricing agreement", 18: "Incorrect discount", 19: "Partial deliveries reconciled",
    20: "PO and DC quantity conflict", 21: "Missing tax information", 22: "Tax rate inconsistent with policy",
    23: "Inconsistent dates / references", 24: "Currency mismatch", 25: "Multiple simultaneous anomalies",
    26: "Supplier details inconsistent", 27: "Possible duplicate (different invoice number)",
}


def info(code: str) -> CodeInfo:
    return CODES[code]
