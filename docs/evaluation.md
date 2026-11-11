# Evaluation (generated from `reports/evaluation/evaluation_results.json`)

Protocol: ground truth (`ground_truth/*.csv`) is read only by `procuraai.evaluation`; agents and the engine never see it. A prediction is an (invoice, finding code) pair; INFO notes (description variant, partial-delivery reconciled) are scored like any other code. `EXTRACTION_LOW_CONFIDENCE` is an operational flag and excluded from scoring.

> **Read this first.** The synthetic data and the audit engine were written together, so the structured-path score demonstrates internal consistency, not accuracy on real-world invoices. The document path (OCR + extraction + audit) is the more informative number. Real suppliers, layouts, scans and policies will behave worse until validated on real, consented documents.

## 1. Audit quality

### Structured-input path (CSV tables -> agents)

| metric | value |
|---|---|
| n_invoices | 72 |
| tp | 54 |
| fp | 0 |
| fn | 0 |
| precision | 1.0 |
| recall | 1.0 |
| f1 | 1.0 |
| fp_non_info | 0 |
| fp_info_only | 0 |
| fp_status_confirmed | 0 |
| fp_non_info_on_high_confidence_invoices | 0 |
| severity_agreement | 1.0 |
| status_agreement | 1.0 |
| line_attribution_accuracy | 1.0 |
| exposure_invoices_within_1pkr | 72 |
| exposure_mae | 0.00 |
| exposure_expected_total | 843027.52 |
| exposure_engine_total | 843027.52 |
| low_confidence_invoices | 0 |

Invoice-level confusion (ground truth -> system):

| outcome | count |
|---|---|
| anomalous->flagged | 42 |
| clean->not_flagged | 30 |

Per-code detection:

| code | tp | fp | fn | precision | recall | f1 |
|---|---|---|---|---|---|---|
| AMBIGUOUS_PRODUCT | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| CONTRACT_NOT_EFFECTIVE | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| CURRENCY_MISMATCH | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DATE_REFERENCE_INCONSISTENT | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DISCOUNT_ERROR | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DUPLICATE_EXACT | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| GRAND_TOTAL_ERROR | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| LINE_SUBTOTAL_ERROR | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| MISSING_DC | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| MISSING_PO | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| MISSING_TAX_INFO | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| PARTIAL_DELIVERY_RECONCILED | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| POSSIBLE_DUPLICATE | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| PO_DC_QTY_CONFLICT | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| PRICE_ABOVE_CONTRACT | 5 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| PRODUCT_DESCRIPTION_VARIANT | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| QTY_EXCEEDS_ORDERED | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| QTY_EXCEEDS_RECEIVED | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| SUPPLIER_DETAILS_INCONSISTENT | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| TAX_CALC_ERROR | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| TAX_RATE_POLICY_MISMATCH | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNAUTHORIZED_CHARGE | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNKNOWN_PRODUCT_CODE | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNKNOWN_SUPPLIER | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |

Citations: 85/85 verified against source text; findings with evidence: 45/50.

### Document path (PDF/PNG/JPG/TXT -> OCR/extraction -> agents)

| metric | value |
|---|---|
| n_invoices | 72 |
| tp | 53 |
| fp | 23 |
| fn | 1 |
| precision | 0.6974 |
| recall | 0.9815 |
| f1 | 0.8154 |
| fp_non_info | 19 |
| fp_info_only | 4 |
| fp_status_confirmed | 0 |
| fp_non_info_on_high_confidence_invoices | 11 |
| severity_agreement | 1.0 |
| status_agreement | 0.9434 |
| line_attribution_accuracy | 1.0 |
| exposure_invoices_within_1pkr | 63 |
| exposure_mae | 23458.36 |
| exposure_expected_total | 843027.52 |
| exposure_engine_total | 2532029.10 |
| low_confidence_invoices | 4 |

Invoice-level confusion (ground truth -> system):

| outcome | count |
|---|---|
| anomalous->flagged | 42 |
| clean->not_flagged | 26 |
| clean->flagged | 4 |

Per-code detection:

| code | tp | fp | fn | precision | recall | f1 |
|---|---|---|---|---|---|---|
| AMBIGUOUS_PRODUCT | 1 | 1 | 0 | 0.5 | 1.0 | 0.6667 |
| CONTRACT_NOT_EFFECTIVE | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| CURRENCY_MISMATCH | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DATE_REFERENCE_INCONSISTENT | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DISCOUNT_ERROR | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DUPLICATE_EXACT | 2 | 0 | 1 | 1.0 | 0.6667 | 0.8 |
| GRAND_TOTAL_ERROR | 3 | 1 | 0 | 0.75 | 1.0 | 0.8571 |
| LINE_SUBTOTAL_ERROR | 2 | 1 | 0 | 0.6667 | 1.0 | 0.8 |
| MISSING_DC | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| MISSING_PO | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| MISSING_TAX_INFO | 1 | 1 | 0 | 0.5 | 1.0 | 0.6667 |
| PARTIAL_DELIVERY_RECONCILED | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| POSSIBLE_DUPLICATE | 1 | 1 | 0 | 0.5 | 1.0 | 0.6667 |
| PO_DC_QTY_CONFLICT | 2 | 5 | 0 | 0.2857 | 1.0 | 0.4444 |
| PRICE_ABOVE_CONTRACT | 5 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| PRODUCT_DESCRIPTION_VARIANT | 2 | 4 | 0 | 0.3333 | 1.0 | 0.5 |
| QTY_EXCEEDS_ORDERED | 2 | 5 | 0 | 0.2857 | 1.0 | 0.4444 |
| QTY_EXCEEDS_RECEIVED | 4 | 3 | 0 | 0.5714 | 1.0 | 0.7273 |
| SUPPLIER_DETAILS_INCONSISTENT | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| TAX_CALC_ERROR | 3 | 1 | 0 | 0.75 | 1.0 | 0.8571 |
| TAX_RATE_POLICY_MISMATCH | 2 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNAUTHORIZED_CHARGE | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNKNOWN_PRODUCT_CODE | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNKNOWN_SUPPLIER | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |

False positives (invoice, code): `INV-005_ICC_IC2025-00141` PRODUCT_DESCRIPTION_VARIANT; `INV-011_ICC_IC2025-00132` PRODUCT_DESCRIPTION_VARIANT; `INV-013_SCW_SCW-00177` QTY_EXCEEDS_RECEIVED; `INV-015_KET_KET-25-0314` LINE_SUBTOTAL_ERROR; `INV-015_KET_KET-25-0314` MISSING_TAX_INFO; `INV-015_KET_KET-25-0314` PO_DC_QTY_CONFLICT; `INV-015_KET_KET-25-0314` QTY_EXCEEDS_ORDERED; `INV-019_ICC_IC2025-00119` PRODUCT_DESCRIPTION_VARIANT; `INV-022_LLI_LL-INV-0183` POSSIBLE_DUPLICATE; `INV-027_PPS_PPS-0344-25` PO_DC_QTY_CONFLICT; `INV-027_PPS_PPS-0344-25` QTY_EXCEEDS_ORDERED; `INV-029_PPS_PPS-0344-52` PO_DC_QTY_CONFLICT; `INV-029_PPS_PPS-0344-52` QTY_EXCEEDS_ORDERED; `INV-032_FIM_FIM-0209` PO_DC_QTY_CONFLICT; `INV-032_FIM_FIM-0209` QTY_EXCEEDS_ORDERED; `INV-035_ICC_IC2025-00154` QTY_EXCEEDS_RECEIVED; `INV-035_ICC_IC2025-00154` PRODUCT_DESCRIPTION_VARIANT; `INV-055_KET_KET-25-0297` AMBIGUOUS_PRODUCT; `INV-055_KET_KET-25-0297` TAX_CALC_ERROR; `INV-055_KET_KET-25-0297` GRAND_TOTAL_ERROR; `INV-064_QVS_QVS00122` QTY_EXCEEDS_RECEIVED; `INV-066_QVS_QVS00132` PO_DC_QTY_CONFLICT; `INV-066_QVS_QVS00132` QTY_EXCEEDS_ORDERED

False negatives (invoice, code): `INV-022_LLI_LL-INV-0183` DUPLICATE_EXACT

Citations: 135/135 verified against source text; findings with evidence: 70/81.

Interpretation of the document-path false positives: they originate in OCR errors in the invoice, purchase order or delivery document (digit/letter confusions, dropped rows). No false positive was *confirmed*: findings that depend on a low-confidence invoice or on OCR-derived PO/DC evidence are downgraded to POTENTIAL and routed to human review. The re-scanned duplicate is still caught, but as POSSIBLE_DUPLICATE (OCR lost the invoice number), which counts as one FP and one FN in strict code matching.

## 2. Extraction field accuracy (documents vs structured observed values)

| source | documents | fully_correct | field_accuracy |
|---|---|---|---|
| ocr | 22 | 10 | 0.9371 |
| text-layer/plain | 50 | 50 | 1.0 |

By field (OCR):

| field | accuracy |
|---|---|
| invoice_number | 0.6364 |
| invoice_date | 0.9545 |
| supplier_name | 0.9091 |
| po_number | 1.0 |
| dc_reference | 1.0 |
| currency | 1.0 |
| subtotal | 0.9545 |
| tax_total | 1.0 |
| grand_total | 1.0 |
| supplier_tax_id | 0.9545 |
| due_date | 1.0 |
| payment_terms | 1.0 |
| line.product_code | 0.9 |
| line.quantity | 0.9333 |
| line.unit_price | 0.9333 |
| line.discount_pct | 0.9333 |
| line.line_amount | 0.9333 |
| line.tax_rate | 0.9333 |
| line.tax_amount | 0.9333 |

## 3. Product matching

| metric | value |
|---|---|
| lines | 196 |
| description_only_correct | 196 |
| description_only_routed_to_review | 0 |
| description_only_wrong_auto_match | 0 |
| description_only_accuracy | 1.0 |
| auto_match_precision | 1.0 |
| code_plus_description_accuracy | 1.0 |

Description-only matching hides the product code from the matcher. 100% here reflects the synthetic catalogue (distinct descriptions, curated aliases); real catalogues will have harder near-duplicates.

## 4. RAG retrieval

**dense**

| query_type | recall@1 | recall@3 | recall@5 | mrr | n |
|---|---|---|---|---|---|
| contract_clause | 0.75 | 1.0 | 1.0 | 0.875 | 16 |
| policy | 0.8571 | 1.0 | 1.0 | 0.9167 | 14 |
| price_row | 1.0 | 1.0 | 1.0 | 1.0 | 40 |
| ALL | 0.9143 | 1.0 | 1.0 | 0.9548 | 70 |

**keyword**

| query_type | recall@1 | recall@3 | recall@5 | mrr | n |
|---|---|---|---|---|---|
| contract_clause | 1.0 | 1.0 | 1.0 | 1.0 | 16 |
| policy | 0.9286 | 1.0 | 1.0 | 0.9643 | 14 |
| price_row | 1.0 | 1.0 | 1.0 | 1.0 | 40 |
| ALL | 0.9857 | 1.0 | 1.0 | 0.9929 | 70 |

**hybrid**

| query_type | recall@1 | recall@3 | recall@5 | mrr | n |
|---|---|---|---|---|---|
| contract_clause | 1.0 | 1.0 | 1.0 | 1.0 | 16 |
| policy | 0.9286 | 1.0 | 1.0 | 0.9643 | 14 |
| price_row | 1.0 | 1.0 | 1.0 | 1.0 | 40 |
| ALL | 0.9857 | 1.0 | 1.0 | 0.9929 | 70 |

Queries: 14 hand-written policy questions, 16 contract-clause questions (supplier given as a metadata filter), 40 random price-row lookups. Embedder: offline TF-IDF lexical baseline; a semantic embedder was not run in this evaluation. The hand-written queries share vocabulary with the synthetic policies, so scores are optimistic.

## 5. Timing and API usage

| kind | mean | max | n |
|---|---|---|---|
| ocr | 5.665 | 11.324 | 48 |
| text-layer/plain | 0.004 | 0.015 | 157 |

Document-path wall clock: 272.8 s (single process, sandbox CPU). Structured path: 0.651 s for 72 invoices.

API usage: No Gemini API key was configured in this run, so no LLM calls were made and no API cost was incurred.
