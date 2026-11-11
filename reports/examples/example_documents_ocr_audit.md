# ProcuraAI Audit Report `AUD-20261011-170655-7c23c9`

Generated: 2026-10-11T17:11:27+00:00

> Findings are produced by deterministic rules over supplied documents. 'Confirmed' means a rule or arithmetic check failed against the supplied evidence; it is not a legal finding. Nothing here accuses a supplier of fraud. Estimated exposure is the disputed amount implied by the findings, not a confirmed recoverable saving. All payment decisions remain with authorised finance staff.

## Summary

| Metric | Value |
|---|---|
| Invoices processed | 72 |
| Passed (clean / with notes) | 21 / 5 |
| Flagged | 37 |
| Manual review only | 9 |
| Human review pending | 46 |
| Low-confidence extractions | 4 |
| Estimated exposure - confirmed | 687,023.65 |
| Estimated exposure - potential | 1,845,005.45 |
| Estimated exposure - total (no double counting) | 2,532,029.10 |

## Findings by category

- quantity: 29
- arithmetic: 11
- pricing: 8
- documents: 5
- tax: 4
- charges: 4
- duplicate: 4
- product: 4
- references: 3
- supplier: 2
- contract: 2
- currency: 1

## Findings by type

- QTY_EXCEEDS_ORDERED: 10
- PO_DC_QTY_CONFLICT: 10
- QTY_EXCEEDS_RECEIVED: 9
- PRICE_ABOVE_CONTRACT: 5
- UNAUTHORIZED_CHARGE: 4
- GRAND_TOTAL_ERROR: 4
- TAX_CALC_ERROR: 4
- LINE_SUBTOTAL_ERROR: 3
- DISCOUNT_ERROR: 3
- DATE_REFERENCE_INCONSISTENT: 3
- MISSING_PO: 3
- AMBIGUOUS_PRODUCT: 3
- MISSING_TAX_INFO: 2
- POSSIBLE_DUPLICATE: 2
- MISSING_DC: 2
- CONTRACT_NOT_EFFECTIVE: 2
- TAX_RATE_POLICY_MISMATCH: 2
- DUPLICATE_EXACT: 2
- SUPPLIER_DETAILS_INCONSISTENT: 1
- CURRENCY_MISMATCH: 1
- UNKNOWN_SUPPLIER: 1
- UNKNOWN_PRODUCT_CODE: 1

## Invoice results

### PCH-0397 - Peshawar Circuit House - **FLAGGED**
File `INV-001_PCH_PCH-0397.pdf` | PO PO-2025-0035 | delivery DC-2025-0035 | total PKR 130498.50 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 5,120.50 (disputed amount, not a confirmed saving)
- **[MEDIUM] LINE_SUBTOTAL_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 1: amount 97755.00 differs from qty 2500 x price 37.24 less 0% discount = 93100.00. Expected 93100.00, observed 97755.00 (difference 4655.00). No supporting contract/policy passage was found in the knowledge base.
- Recommended actions: Return the invoice to the supplier for correction of the line/subtotal arithmetic.

### IC2025-00111 - Indus Components & Circuits (Pvt) Ltd - **PASSED**
File `INV-002_ICC_IC2025-00111.pdf` | PO PO-2025-0001 | delivery DC-2025-0001 | total PKR 527258.35 | extraction confidence 1.00 | human review: NOT_REQUIRED

### PCH-0383 - Peshawar Circuit House - **PASSED**
File `INV-003_PCH_PCH-0383.pdf` | PO PO-2025-0019 | delivery DC-2025-0019 | total PKR 229398.40 | extraction confidence 0.88 | human review: NOT_REQUIRED

### PPS/0318/25 - Punjab Power Supply Co. - **PASSED**
File `INV-004_PPS_PPS-0318-25.pdf` | PO PO-2025-0008 | delivery GRN-2025-0008 | total PKR 118960.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### 1C2025-00141 - Indus Components and Circuits - **FLAGGED**
File `INV-005_ICC_IC2025-00141.png` | PO PO-2025-0052 | delivery GRN-2025-0052 | total PKR 27236.65 | extraction confidence 0.93 | human review: PENDING
- **[MEDIUM] SUPPLIER_DETAILS_INCONSISTENT** (POTENTIAL) - Potential anomaly: Tax id on invoice (SYN-TAX-0003-9) differs from the supplier master (SYN-TAX-0003-3). Expected SYN-TAX-0003-3, observed SYN-TAX-0003-9. Supporting source: POL-005.txt, Section 5.3.
  - Evidence: `POL-005.txt` / Section 5.3: "[Section 5.3] Supplier tax identification on an invoice must match the supplier master. Differences are queried before payment."
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 2: description 'Electrolytic Capacitor 1000uF SOV' differs from the catalogue but resolves to ELC-3002 (code_exact). Expected Electrolytic Capacitor 1000uF 50V, observed Electrolytic Capacitor 1000uF SOV.
- Unresolved questions: Tax id on invoice (SYN-TAX-0003-9) differs from the supplier master (SYN-TAX-0003-3).
- Recommended actions: Verify the supplier's registration details with the supplier master before payment.

### KET/25/0301 - Karachi Electro Traders (Pvt) Ltd - **PASSED**
File `INV-006_KET_KET-25-0301.pdf` | PO PO-2025-0015 | delivery DC-2025-0015 | total PKR 198024.60 | extraction confidence 1.00 | human review: NOT_REQUIRED

### LL-INV-0197 - Lahore LumenTech Industries - **PASSED_WITH_NOTES**
File `INV-007_LLI_LL-INV-0197.jpg` | PO PO-2025-0057 | delivery DC-2025-0057, DC-2025-0058 | total PKR 33094.70 | extraction confidence 0.92 | human review: NOT_REQUIRED
- **[INFO] PARTIAL_DELIVERY_RECONCILED** (PASSED) - Note: Invoiced quantities reconcile only after aggregating 2 delivery records (DC-2025-0057, DC-2025-0058). Expected 500, observed 500.

### SCW-00180 - Sialkot CableWorks Co. - **PASSED**
File `INV-008_SCW_SCW-00180.txt` | PO PO-2025-0007 | delivery DC-2025-0007 | total PKR 297528.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### SCW-00208 - Sialkot CableWorks Co. - **FLAGGED**
File `INV-009_SCW_SCW-00208.pdf` | PO PO-2025-0056 | delivery GRN-2025-0056 | total PKR 799458.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 14,850.00 (disputed amount, not a confirmed saving)
- **[MEDIUM] DISCOUNT_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 1 CAB-4006: discount 2.00% differs from the contractual 4% (quantity basis 500, threshold 20). Expected 4, observed 2.00 (difference -2.00). Supporting source: CONTRACT_SUP-004.txt, Volume Discount.
  - Evidence: `CONTRACT_SUP-004.txt` / Volume Discount: "[Volume Discount] A volume discount of 4 percent applies to any product line where the ordered quantity is 20 units or more. The discount is determined on the purchase-order quantity and shown on the "
- Recommended actions: Ask the supplier to apply the contractual volume discount.

### KET/25/0324 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-010_KET_KET-25-0324.pdf` | PO PO-2025-0064 | delivery GRN-2025-0066 | total PKR 115488.20 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] DATE_REFERENCE_INCONSISTENT** (POTENTIAL) - Potential anomaly: Invoice cites delivery reference(s) DC-2025-0766 which do not exist, while other delivery records exist for the PO (GRN-2025-0066). Expected GRN-2025-0066, observed DC-2025-0766. Supporting source: POL-005.txt, Section 5.4.
  - Evidence: `POL-005.txt` / Section 5.4: "[Section 5.4] The invoice date should not precede the delivery date of the goods it bills. Inconsistent dates or references are routed to review."
- Unresolved questions: Invoice cites delivery reference(s) DC-2025-0766 which do not exist, while other delivery records exist for the PO (GRN-2025-0066).
- Recommended actions: Check dates and cited references with the supplier and receiving.

### 1C2025-00132 - Indus Components & Circuits (Pvt) Ltd - **FLAGGED**
File `INV-011_ICC_IC2025-00132.png` | PO PO-2025-0023 | delivery DC-2025-0023 | total PKR 253918.00 | extraction confidence 0.93 | human review: PENDING
Estimated exposure: 12,408.00 (disputed amount, not a confirmed saving)
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 1: description 'Switch Mode Power Supply 24V SA' differs from the catalogue but resolves to ELC-3008 (code_exact). Expected Switch Mode Power Supply 24V 5A, observed Switch Mode Power Supply 24V SA.
- **[HIGH] PRICE_ABOVE_CONTRACT** (CONFIRMED) - Confirmed discrepancy: Line 1 ELC-3008: billed unit price 3323.00 is 6.0% above contract price 3135 (AG-003). Expected 3135, observed 3323.00 (difference 188.00). Supporting source: CONTRACT_SUP-003.txt, Schedule AG-003 - Price List (2025-01-01 to 2025-12-31).
  - Evidence: `CONTRACT_SUP-003.txt` / Schedule AG-003 - Price List (2025-01-01 to 2025-12-31): "[Schedule AG-003 - Price List (2025-01-01 to 2025-12-31)] ELC-3008 | Switch Mode Power Supply 24V 5A | PCS | PKR 3,135.00"
- Recommended actions: Query the supplier and request a credit note or corrected invoice at the contract price; hold the disputed amount only after a human confirms the agreement.

### FIM-0205 - Faisalabad Industrial Mart - **PASSED**
File `INV-012_FIM_FIM-0205.pdf` | PO PO-2025-0012 | delivery GRN-2025-0012 | total PKR 298826.50 | extraction confidence 1.00 | human review: NOT_REQUIRED

### SCW-00177 - Sialkot Cable Works - **FLAGGED**
File `INV-013_SCW_SCW-00177.pdf` | PO PO-2025-0004 | delivery GRN-2025-0004 | total PKR 488400.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 171,600.00 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: CAB-4004: invoiced quantity 8 exceeds the received quantity 0 across 1 delivery record(s). Expected 0, observed 8 (difference 8). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- Unresolved questions: CAB-4004: invoiced quantity 8 exceeds the received quantity 0 across 1 delivery record(s).
- Recommended actions: Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### LL-INV-0174 - Lahore LumenTech Industries - **FLAGGED**
File `INV-014_LLI_LL-INV-0174.pdf` | PO PO-2025-0026 | delivery GRN-2025-0026 | total PKR 817296.18 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 112,772.22 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_RECEIVED** (CONFIRMED) - Confirmed discrepancy: LGT-2006: invoiced quantity 150 exceeds the received quantity 128 across 1 delivery record(s). Expected 128, observed 150 (difference 22). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- Recommended actions: Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### KET/25/0314 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-015_KET_KET-25-0314.pdf` | PO PO-2025-0040 | delivery GRN-2025-0040 | total PKR 364197.35 | extraction confidence 0.50 | human review: PENDING
Estimated exposure: 326,236.50 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: CAB-4006: invoiced quantity 100 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 100 (difference 100). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: CAB-4006: received quantity 100 exceeds ordered quantity 0. Expected 0, observed 100 (difference 100). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- **[MEDIUM] MISSING_TAX_INFO** (MANUAL_REVIEW) - Manual review required: The invoice does not state tax rate and amount for every line. Expected tax rate and amount per line, observed partially absent. Supporting source: POL-002.txt, Section 2.7.
  - Evidence: `POL-002.txt` / Section 2.7: "[Section 2.7] Every invoice must state the tax rate and tax amount for each line. Invoices without tax information are held for manual review."
- **[MEDIUM] LINE_SUBTOTAL_ERROR** (POTENTIAL) - Potential anomaly: Header subtotal 323736.50 differs from the sum of line amounts 124450.00. Expected 124450.00, observed 323736.50 (difference 199286.50). No supporting contract/policy passage was found in the knowledge base.
- **[HIGH] UNAUTHORIZED_CHARGE** (POTENTIAL) - Potential anomaly: Freight Charges of 2500.00 is not permitted by agreement AG-001-A. Expected 0.00, observed 2500.00 (difference 2500.00). Supporting source: CONTRACT_SUP-001.txt, Freight and Additional Charges.
  - Evidence: `CONTRACT_SUP-001.txt` / Freight and Additional Charges: "[Freight and Additional Charges] Delivery to the Buyer's store is included in the unit prices. No freight, handling, packing, fuel or other additional charge may be invoiced."
- **[MEDIUM] EXTRACTION_LOW_CONFIDENCE** (MANUAL_REVIEW) - Manual review required: Extraction confidence 0.50 (ocr+rule); extraction_integrity: line amounts sum to 124450.00 but subtotal reads 323736.50; ocr_variant=0 integrity_score=12.7. No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: CAB-4006: invoiced quantity 100 exceeds ordered quantity 0 (product is not on the PO). | CAB-4006: received quantity 100 exceeds ordered quantity 0. | The invoice does not state tax rate and amount for every line. | Header subtotal 323736.50 differs from the sum of line amounts 124450.00.
- Recommended actions: Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved. | Request a compliant invoice stating tax rate and amount per line.

### QVS00129 - Quetta Voltage Solutions - **FLAGGED**
File `INV-016_QVS_QVS00129.pdf` | PO PO-2025-0024 | delivery GRN-2025-0024 | total PKR 868392.60 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 55,372.50 (disputed amount, not a confirmed saving)
- **[HIGH] PRICE_ABOVE_CONTRACT** (CONFIRMED) - Confirmed discrepancy: Line 2 ELE-1003: billed unit price 2997.00 is 12.0% above contract price 2676 (AG-007). Expected 2676, observed 2997.00 (difference 321.00). Supporting source: CONTRACT_SUP-007.txt, Schedule AG-007 - Price List (2025-02-01 to 2025-12-31).
  - Evidence: `CONTRACT_SUP-007.txt` / Schedule AG-007 - Price List (2025-02-01 to 2025-12-31): "[Schedule AG-007 - Price List (2025-02-01 to 2025-12-31)] ELE-1003 | Miniature Circuit Breaker 3-Pole 32A | PCS | PKR 2,676.00"
- Recommended actions: Query the supplier and request a credit note or corrected invoice at the contract price; hold the disputed amount only after a human confirms the agreement.

### PPS/0327/25 - Punjab Power Supply Co. - **PASSED**
File `INV-017_PPS_PPS-0327-25.png` | PO PO-2025-0014 | delivery GRN-2025-0014 | total PKR 40128.00 | extraction confidence 0.93 | human review: NOT_REQUIRED

### LL-INV-0165 - Lahore LumenTech Industries - **PASSED**
File `INV-018_LLI_LL-INV-0165.pdf` | PO PO-2025-0010 | delivery GRN-2025-0010 | total PKR 115900.70 | extraction confidence 1.00 | human review: NOT_REQUIRED

### 12025-00119 - Indus Components & Circuits (Pvt) Ltd - **PASSED_WITH_NOTES**
File `INV-019_ICC_IC2025-00119.jpg` | PO PO-2025-0009 | delivery DC-2025-0009 | total PKR 678193.78 | extraction confidence 0.83 | human review: NOT_REQUIRED
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 1: description 'Glass Fuse SA 20mm Box of 100' differs from the catalogue but resolves to ELC-3009 (code_exact). Expected Glass Fuse 5A 20mm Box of 100, observed Glass Fuse SA 20mm Box of 100.

### LL-INV-0183 - Lahore LumenTech Industries - **PASSED**
File `INV-020_LLI_LL-INV-0183.pdf` | PO PO-2025-0032 | delivery GRN-2025-0032 | total PKR 111493.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### LL-INV-0204 - Lahore LumenTech Industries - **FLAGGED**
File `INV-021_LLI_LL-INV-0204.pdf` | PO PO-2025-0065 | delivery DC-2025-0067 | total USD 25844.50 | extraction confidence 1.00 | human review: PENDING
- **[HIGH] CURRENCY_MISMATCH** (CONFIRMED) - Confirmed discrepancy: Invoice currency USD differs from the PO currency PKR; amounts are not compared. Expected PKR, observed USD. Supporting source: POL-003.txt, Section 3.4.
  - Evidence: `POL-003.txt` / Section 3.4: "[Section 3.4] All invoices must be issued in Pakistani Rupees (PKR) unless the agreement states another currency."
- Recommended actions: Confirm the invoicing currency with the supplier; do not compare amounts across currencies.

### INV-022_LLI_LL-INV-0183 - Fe - **FLAGGED**
File `INV-022_LLI_LL-INV-0183.png` | PO PO-2025-0032 | delivery GRN-2025-0032 | total PKR 111493.00 | extraction confidence 0.60 | human review: PENDING
Estimated exposure: 111,493.00 (disputed amount, not a confirmed saving)
- **[HIGH] POSSIBLE_DUPLICATE** (POTENTIAL) - Potential anomaly: Invoice None has a different number but the same supplier, PO and economic content as INV-020_LLI_LL-INV-0183. Expected a single invoice for this PO, observed similar to INV-020_LLI_LL-INV-0183. Supporting source: POL-004.txt, Section 4.2.
  - Evidence: `POL-004.txt` / Section 4.2: "[Section 4.2] An invoice with a different number but the same supplier, purchase order and economic content as an earlier invoice is a possible duplicate and requires review."
- **[MEDIUM] EXTRACTION_LOW_CONFIDENCE** (MANUAL_REVIEW) - Manual review required: Extraction confidence 0.60 (ocr+rule); ocr_variant=1 integrity_score=14.9. No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: Invoice None has a different number but the same supplier, PO and economic content as INV-020_LLI_LL-INV-0183. | Extraction confidence 0.60 (ocr+rule); ocr_variant=1 integrity_score=14.9.
- Recommended actions: Compare with the earlier invoice for the same PO and confirm with the supplier before any payment. | Verify extracted values against the original document image/PDF.

### PCH-0407 - PCH Peshawar - **FLAGGED**
File `INV-023_PCH_PCH-0407.png` | PO PO-2025-0059 | delivery DC-2025-0061 | total PKR 143429.00 | extraction confidence 0.93 | human review: PENDING
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: ELC-3004: received quantity 240 exceeds ordered quantity 200. Expected 200, observed 240 (difference 40). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- Unresolved questions: ELC-3004: received quantity 240 exceeds ordered quantity 200.
- Recommended actions: Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.

### SCW-00207 - Sialkot Cable Works - **MANUAL_REVIEW**
File `INV-024_SCW_SCW-00207.pdf` | PO PO-2025-0046 | delivery n/a | total PKR 37675.00 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] MISSING_DC** (MANUAL_REVIEW) - Manual review required: No delivery challan / goods-received note was found for this invoice. Expected GRN-2025-0046, observed not on file. Supporting source: POL-001.txt, Section 1.4.
  - Evidence: `POL-001.txt` / Section 1.4: "[Section 1.4] A missing delivery record is not proof of non-delivery. The invoice is routed to manual review so that receiving staff can confirm delivery."
- Unresolved questions: No delivery challan / goods-received note was found for this invoice.
- Recommended actions: Ask receiving staff to confirm delivery and locate the delivery record. Absence of the record is not proof of non-delivery.

### PPS/0317/25 - Punjab Power Supply Co. - **PASSED**
File `INV-025_PPS_PPS-0317-25.pdf` | PO PO-2025-0002 | delivery GRN-2025-0002 | total PKR 379640.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### IC2025-00146 - Indus Components & Circuits (Pvt) Ltd - **MANUAL_REVIEW**
File `INV-026_ICC_IC2025-00146.pdf` | PO PO-2025-0060 | delivery GRN-2025-0062 | total PKR 402841.80 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] MISSING_TAX_INFO** (MANUAL_REVIEW) - Manual review required: The invoice states no tax rate or tax amount. Expected tax rate and amount per line, observed absent. Supporting source: POL-002.txt, Section 2.7.
  - Evidence: `POL-002.txt` / Section 2.7: "[Section 2.7] Every invoice must state the tax rate and tax amount for each line. Invoices without tax information are held for manual review."
- Unresolved questions: The invoice states no tax rate or tax amount.
- Recommended actions: Request a compliant invoice stating tax rate and amount per line.

### PPS/0344/25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-027_PPS_PPS-0344-25.pdf` | PO PO-2025-0033 | delivery DC-2025-0033 | total PKR 42552.70 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 37,315.20 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: ELE-1008: invoiced quantity 4 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 4 (difference 4). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: ELE-1008: received quantity 4 exceeds ordered quantity 0. Expected 0, observed 4 (difference 4). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- Unresolved questions: ELE-1008: invoiced quantity 4 exceeds ordered quantity 0 (product is not on the PO). | ELE-1008: received quantity 4 exceeds ordered quantity 0.
- Recommended actions: Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.

### PPS/0338/25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-028_PPS_PPS-0338-25.pdf` | PO PO-2025-0027 | delivery DC-2025-0027 | total PKR 52253.60 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 7,774.00 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_RECEIVED** (CONFIRMED) - Confirmed discrepancy: ELE-1001: invoiced quantity 24 exceeds the received quantity 14 across 1 delivery record(s). Expected 14, observed 24 (difference 10). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- Recommended actions: Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### PPS/0344/52 - Punjab Power Supply Co. - **FLAGGED**
File `INV-029_PPS_PPS-0344-52.pdf` | PO PO-2025-0033 | delivery DC-2025-0033 | total PKR 42552.70 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 79,867.90 (disputed amount, not a confirmed saving)
- **[HIGH] POSSIBLE_DUPLICATE** (POTENTIAL) - Potential anomaly: Invoice PPS/0344/52 has a different number but the same supplier, PO and economic content as INV-027_PPS_PPS-0344-25. Expected a single invoice for this PO, observed similar to INV-027_PPS_PPS-0344-25. Supporting source: POL-004.txt, Section 4.2.
  - Evidence: `POL-004.txt` / Section 4.2: "[Section 4.2] An invoice with a different number but the same supplier, purchase order and economic content as an earlier invoice is a possible duplicate and requires review."
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: ELE-1008: invoiced quantity 4 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 4 (difference 4). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: ELE-1008: received quantity 4 exceeds ordered quantity 0. Expected 0, observed 4 (difference 4). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- Unresolved questions: Invoice PPS/0344/52 has a different number but the same supplier, PO and economic content as INV-027_PPS_PPS-0344-25. | ELE-1008: invoiced quantity 4 exceeds ordered quantity 0 (product is not on the PO). | ELE-1008: received quantity 4 exceeds ordered quantity 0.
- Recommended actions: Compare with the earlier invoice for the same PO and confirm with the supplier before any payment. | Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.

### PPS/0372/25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-030_PPS_PPS-0372-25.pdf` | PO PO-2025-0066 | delivery GRN-2025-0068 | total PKR 115272.35 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 12,990.55 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: ELE-1001: invoiced quantity 60 exceeds the received quantity 48 across 1 delivery record(s). Expected 48, observed 60 (difference 12). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[HIGH] PRICE_ABOVE_CONTRACT** (CONFIRMED) - Confirmed discrepancy: Line 1 ELE-1002: billed unit price 2213.00 is 15.0% above contract price 1924 (AG-005). Expected 1924, observed 2213.00 (difference 289.00). Supporting source: CONTRACT_SUP-005.txt, Schedule AG-005 - Price List (2025-01-01 to 2025-12-31).
  - Evidence: `CONTRACT_SUP-005.txt` / Schedule AG-005 - Price List (2025-01-01 to 2025-12-31): "[Schedule AG-005 - Price List (2025-01-01 to 2025-12-31)] ELE-1002 | Miniature Circuit Breaker 2-Pole 32A | PCS | PKR 1,924.00"
- **[HIGH] GRAND_TOTAL_ERROR** (CONFIRMED) - Confirmed discrepancy: Grand total 115272.35 differs from subtotal 94889.00 + tax 14233.35 + charges 4150.00 = 113272.35. Expected 113272.35, observed 115272.35 (difference 2000.00). No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: ELE-1001: invoiced quantity 60 exceeds the received quantity 48 across 1 delivery record(s).
- Recommended actions: Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced. | Query the supplier and request a credit note or corrected invoice at the contract price; hold the disputed amount only after a human confirms the agreement. | Return the invoice for correction; the stated total does not foot.

### KET/25/0306 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-031_KET_KET-25-0306.jpg` | PO PO-2025-0028 | delivery GRN-2025-0028 | total PKR 37633.68 | extraction confidence 0.91 | human review: PENDING
Estimated exposure: 1,216.38 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_ORDERED** (CONFIRMED) - Confirmed discrepancy: CAB-4007: invoiced quantity 275 exceeds ordered quantity 250. Expected 250, observed 275 (difference 25). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[HIGH] QTY_EXCEEDS_RECEIVED** (CONFIRMED) - Confirmed discrepancy: CAB-4007: invoiced quantity 275 exceeds the received quantity 250 across 1 delivery record(s). Expected 250, observed 275 (difference 25). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- Recommended actions: Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### FIM-0209 - Faisalabad Industrial Mart - **FLAGGED**
File `INV-032_FIM_FIM-0209.txt` | PO PO-2025-0053 | delivery DC-2025-0053 | total PKR 27629.85 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 27,629.85 (disputed amount, not a confirmed saving)
- **[MEDIUM] CONTRACT_NOT_EFFECTIVE** (INSUFFICIENT_EVIDENCE) - Insufficient evidence: No supplier agreement for SUP-006 was effective on 2025-05-14 (PO date). The latest agreement AG-006 ran 2025-01-01 to 2025-04-30. Expected agreement effective on PO date, observed 2025-05-14. Supporting source: POL-005.txt, Section 5.2.
  - Evidence: `POL-005.txt` / Section 5.2: "[Section 5.2] The applicable supplier agreement is the one effective on the purchase order date. If no agreement is effective, contract prices cannot be validated and the invoice is held for review."
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: CON-5006: invoiced quantity 120 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 120 (difference 120). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: CON-5006: received quantity 120 exceeds ordered quantity 0. Expected 0, observed 120 (difference 120). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: IND-6005: invoiced quantity 60 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 60 (difference 60). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: IND-6005: received quantity 60 exceeds ordered quantity 0. Expected 0, observed 60 (difference 60). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: IND-6001: invoiced quantity 30 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 30 (difference 30). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: IND-6001: received quantity 30 exceeds ordered quantity 0. Expected 0, observed 30 (difference 30). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- Unresolved questions: No supplier agreement for SUP-006 was effective on 2025-05-14 (PO date). The latest agreement AG-006 ran 2025-01-01 to 2025-04-30. | CON-5006: invoiced quantity 120 exceeds ordered quantity 0 (product is not on the PO). | CON-5006: received quantity 120 exceeds ordered quantity 0. | IND-6005: invoiced quantity 60 exceeds ordered quantity 0 (product is not on the PO).
- Recommended actions: Confirm which price agreement applies (renewal/extension) before validating prices. | Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.

### KET/25/0302 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-033_KET_KET-25-0302.pdf` | PO PO-2025-0025 | delivery DC-2025-0025 | total PKR 737522.60 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 20,592.00 (disputed amount, not a confirmed saving)
- **[HIGH] PRICE_ABOVE_CONTRACT** (CONFIRMED) - Confirmed discrepancy: Line 2 CAB-4003: billed unit price 15338.00 is 18.0% above contract price 12998 (AG-001-A). Expected 12998, observed 15338.00 (difference 2340.00). Supporting source: CONTRACT_SUP-001.txt, Schedule AG-001-A - Price List (2025-01-01 to 2025-05-31).
  - Evidence: `CONTRACT_SUP-001.txt` / Schedule AG-001-A - Price List (2025-01-01 to 2025-05-31): "[Schedule AG-001-A - Price List (2025-01-01 to 2025-05-31)] CAB-4003 | PVC Insulated Cable 4mm Single Core 100m Coil | ROLL | PKR 12,998.00"
- Recommended actions: Query the supplier and request a credit note or corrected invoice at the contract price; hold the disputed amount only after a human confirms the agreement.

### SCW-00188 - Sialkot CableWorks Co. - **PASSED**
File `INV-034_SCW_SCW-00188.pdf` | PO PO-2025-0016 | delivery GRN-2025-0016 | total PKR 275308.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### 1C2025-00154 - Indus Components & Circuits (Pvt) Ltd - **FLAGGED**
File `INV-035_ICC_IC2025-00154.png` | PO PO-2025-0068 | delivery GRN-2025-0070 | total PKR 221995.02 | extraction confidence 0.93 | human review: PENDING
Estimated exposure: 220,845.02 (disputed amount, not a confirmed saving)
- **[HIGH] MISSING_PO** (MANUAL_REVIEW) - Manual review required: Purchase order PO-2025-0068 was not found among the supplied documents. Expected PO-2025-0068, observed not on file. Supporting source: POL-001.txt, Section 1.1.
  - Evidence: `POL-001.txt` / Section 1.1: "[Section 1.1] Every supplier invoice must be matched to its purchase order and to the goods-received or delivery record before payment is considered."
- **[MEDIUM] DATE_REFERENCE_INCONSISTENT** (POTENTIAL) - Potential anomaly: Invoice dated 2025-06-03 precedes the delivery dated 2025-06-06. Expected >= 2025-06-06, observed 2025-06-03. Supporting source: POL-005.txt, Section 5.4.
  - Evidence: `POL-005.txt` / Section 5.4: "[Section 5.4] The invoice date should not precede the delivery date of the goods it bills. Inconsistent dates or references are routed to review."
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 2: description 'Switch Mode Power Supply 24V SA' differs from the catalogue but resolves to ELC-3008 (code_exact). Expected Switch Mode Power Supply 24V 5A, observed Switch Mode Power Supply 24V SA.
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: ELC-3006: invoiced quantity 500 exceeds the received quantity 0 across 1 delivery record(s). Expected 0, observed 500 (difference 500). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: ELC-3008: invoiced quantity 60 exceeds the received quantity 0 across 1 delivery record(s). Expected 0, observed 60 (difference 60). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[HIGH] PRICE_ABOVE_CONTRACT** (CONFIRMED) - Confirmed discrepancy: Line 1 ELC-3006: billed unit price 26.12 is 10.0% above contract price 23.75 (AG-003). Expected 23.75, observed 26.12 (difference 2.37). Supporting source: CONTRACT_SUP-003.txt, Schedule AG-003 - Price List (2025-01-01 to 2025-12-31).
  - Evidence: `CONTRACT_SUP-003.txt` / Schedule AG-003 - Price List (2025-01-01 to 2025-12-31): "[Schedule AG-003 - Price List (2025-01-01 to 2025-12-31)] ELC-3006 | Voltage Regulator IC 7805 | PCS | PKR 23.75"
- Unresolved questions: Purchase order PO-2025-0068 was not found among the supplied documents. | Invoice dated 2025-06-03 precedes the delivery dated 2025-06-06. | ELC-3006: invoiced quantity 500 exceeds the received quantity 0 across 1 delivery record(s). | ELC-3008: invoiced quantity 60 exceeds the received quantity 0 across 1 delivery record(s).
- Recommended actions: Locate the purchase order (or confirm an authorised exception) before paying. | Check dates and cited references with the supplier and receiving. | Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### GGT-4056 - Gwadar General Traders - **MANUAL_REVIEW**
File `INV-036_UNK_GGT-4056.pdf` | PO PO-2025-0051 | delivery DC-2025-0051 | total PKR 154907.40 | extraction confidence 1.00 | human review: PENDING
- **[HIGH] UNKNOWN_SUPPLIER** (MANUAL_REVIEW) - Manual review required: Supplier 'Gwadar General Traders' is not in the supplier master. Expected supplier in master, observed Gwadar General Traders. Supporting source: POL-005.txt, Section 5.1.
  - Evidence: `POL-005.txt` / Section 5.1: "[Section 5.1] Invoices may only be accepted from suppliers listed in the approved supplier master. Invoices from unlisted suppliers are routed to procurement for onboarding review."
- Unresolved questions: Supplier 'Gwadar General Traders' is not in the supplier master.
- Recommended actions: Route to procurement for supplier onboarding/verification before any payment.

### SCW-00196 - Sialkot CableWorks Co. - **FLAGGED**
File `INV-037_SCW_SCW-00196.pdf` | PO PO-2025-0029 | delivery DC-2025-0029 | total PKR 396396.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 14,256.00 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_ORDERED** (CONFIRMED) - Confirmed discrepancy: CAB-4006: invoiced quantity 110 exceeds ordered quantity 100. Expected 100, observed 110 (difference 10). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: CAB-4006: received quantity 110 exceeds ordered quantity 100. Expected 100, observed 110 (difference 10). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- Unresolved questions: CAB-4006: received quantity 110 exceeds ordered quantity 100.
- Recommended actions: Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved.

### SCW-00211 - Sialkot CableWorks Co. - **FLAGGED**
File `INV-038_SCW_SCW-00211.pdf` | PO PO-2025-0061 | delivery DC-2025-0063 | total PKR 159107.60 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 729.60 (disputed amount, not a confirmed saving)
- **[MEDIUM] TAX_RATE_POLICY_MISMATCH** (CONFIRMED) - Confirmed discrepancy: Line 1 CON-5001 (Connectors): tax rate 12.00% differs from the synthetic policy rate 10%. Expected 10, observed 12.00 (difference 2.00). Supporting source: POL-002.txt, Section 2.5.
  - Evidence: `POL-002.txt` / Section 2.5: "[Section 2.5] Synthetic policy tax rate for Connectors is 10 percent."
- Recommended actions: Check the applicable rate under the (synthetic) policy and ask the supplier to correct if confirmed.

### KET/25/0293 - Karachi Electro Traders (Pvt) Ltd - **PASSED**
File `INV-039_KET_KET-25-0293.pdf` | PO PO-2025-0005 | delivery DC-2025-0005 | total PKR 813448.95 | extraction confidence 0.91 | human review: NOT_REQUIRED

### KET/25/0322 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-040_KET_KET-25-0322.pdf` | PO PO-2025-0055 | delivery DC-2025-0055 | total PKR 721160.40 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 29,932.20 (disputed amount, not a confirmed saving)
- **[MEDIUM] DISCOUNT_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 1 ELE-1009: discount 0% differs from the contractual 5% (quantity basis 120, threshold 50). Expected 5, observed 0 (difference -5). Supporting source: CONTRACT_SUP-001.txt, Volume Discount.
  - Evidence: `CONTRACT_SUP-001.txt` / Volume Discount: "[Volume Discount] A volume discount of 5 percent applies to any product line where the ordered quantity is 50 units or more. The discount is determined on the purchase-order quantity and shown on the "
- Recommended actions: Ask the supplier to apply the contractual volume discount.

### 1C2025-00116 - Indus Components & Circuits (Pvt) Ltd - **PASSED**
File `INV-041_ICC_IC2025-00116.png` | PO PO-2025-0003 | delivery DC-2025-0003 | total PKR 712474.25 | extraction confidence 0.93 | human review: NOT_REQUIRED

### PPS/0358/25 - Punjab Power Supply Co. - **PASSED_WITH_NOTES**
File `INV-042_PPS_PPS-0358-25.pdf` | PO PO-2025-0058 | delivery DC-2025-0059, DC-2025-0060 | total PKR 825240.00 | extraction confidence 1.00 | human review: NOT_REQUIRED
- **[INFO] PARTIAL_DELIVERY_RECONCILED** (PASSED) - Note: Invoiced quantities reconcile only after aggregating 2 delivery records (DC-2025-0059, DC-2025-0060). Expected 75, observed 75.

### INV-043_PPS_PPS-0355-25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-043_PPS_PPS-0355-25.jpg` | PO PO-2025-0042 | delivery GRN-2025-0042 | total PKR 1378416.00 | extraction confidence 0.60 | human review: PENDING
Estimated exposure: 2,800.00 (disputed amount, not a confirmed saving)
- **[HIGH] UNAUTHORIZED_CHARGE** (POTENTIAL) - Potential anomaly: Freight 7800.00 exceeds the agreed cap of 5000 (AG-005). Expected <= 5000, observed 7800.00 (difference 2800.00). Supporting source: CONTRACT_SUP-005.txt, Freight and Additional Charges.
  - Evidence: `CONTRACT_SUP-005.txt` / Freight and Additional Charges: "[Freight and Additional Charges] The Supplier may invoice the following additional charges: freight, handling. Freight must not exceed PKR 5,000 per invoice. No other surcharge (including fuel or serv"
- **[MEDIUM] EXTRACTION_LOW_CONFIDENCE** (MANUAL_REVIEW) - Manual review required: Extraction confidence 0.60 (ocr+rule); invoice_date recovered from neighbouring text (low confidence); ocr_variant=0 integrity_score=15.3. No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: Freight 7800.00 exceeds the agreed cap of 5000 (AG-005). | Extraction confidence 0.60 (ocr+rule); invoice_date recovered from neighbouring text (low confidence); ocr_variant=0 integrity_score=15.3.
- Recommended actions: Query the charge against the supplier agreement; request removal or written authorisation from procurement. | Verify extracted values against the original document image/PDF.

### FIM-0212 - Faisalabad Industrial Mart - **MANUAL_REVIEW**
File `INV-044_FIM_FIM-0212.txt` | PO PO-2025-0054 | delivery GRN-2025-0054 | total PKR 194318.00 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] CONTRACT_NOT_EFFECTIVE** (INSUFFICIENT_EVIDENCE) - Insufficient evidence: No supplier agreement for SUP-006 was effective on 2025-06-14 (PO date). The latest agreement AG-006 ran 2025-01-01 to 2025-04-30. Expected agreement effective on PO date, observed 2025-06-14. Supporting source: POL-005.txt, Section 5.2.
  - Evidence: `POL-005.txt` / Section 5.2: "[Section 5.2] The applicable supplier agreement is the one effective on the purchase order date. If no agreement is effective, contract prices cannot be validated and the invoice is held for review."
- Unresolved questions: No supplier agreement for SUP-006 was effective on 2025-06-14 (PO date). The latest agreement AG-006 ran 2025-01-01 to 2025-04-30.
- Recommended actions: Confirm which price agreement applies (renewal/extension) before validating prices.

### QVS00124 - Quetta Voltage Solutions - **PASSED**
File `INV-045_QVS_QVS00124.pdf` | PO PO-2025-0021 | delivery DC-2025-0021 | total PKR 100688.25 | extraction confidence 1.00 | human review: NOT_REQUIRED

### PPS/0335/25 - Punjab Power Supply Co. - **PASSED**
File `INV-046_PPS_PPS-0335-25.pdf` | PO PO-2025-0020 | delivery GRN-2025-0020 | total PKR 606284.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### QVS00145 - eS - **MANUAL_REVIEW**
File `INV-047_QVS_QVS00145.png` | PO PO-2025-0050 | delivery GRN-2025-0050 | total PKR 228207.00 | extraction confidence 0.94 | human review: PENDING
- **[MEDIUM] AMBIGUOUS_PRODUCT** (MANUAL_REVIEW) - Manual review required: Line 1: description 'Miniature Circuit Breaker 32A' could refer to several products (ELE-1002, ELE-1003, ELE-1001). Expected a single catalogue product, observed Miniature Circuit Breaker 32A. Supporting source: POL-005.txt, Section 5.5.
  - Evidence: `POL-005.txt` / Section 5.5: "[Section 5.5] Where an invoice line cannot be resolved to a single catalogue product, it is routed to manual review."
- Unresolved questions: Line 1: description 'Miniature Circuit Breaker 32A' could refer to several products (ELE-1002, ELE-1003, ELE-1001).
- Recommended actions: Have a buyer decide which catalogue product this line refers to.

### PPS/0367/25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-048_PPS_PPS-0367-25.pdf` | PO PO-2025-0063 | delivery DC-2025-0065 | total PKR 31395.00 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] DATE_REFERENCE_INCONSISTENT** (POTENTIAL) - Potential anomaly: Invoice dated 2025-07-07 precedes the delivery dated 2025-07-11. Expected >= 2025-07-11, observed 2025-07-07. Supporting source: POL-005.txt, Section 5.4.
  - Evidence: `POL-005.txt` / Section 5.4: "[Section 5.4] The invoice date should not precede the delivery date of the goods it bills. Inconsistent dates or references are routed to review."
- Unresolved questions: Invoice dated 2025-07-07 precedes the delivery dated 2025-07-11.
- Recommended actions: Check dates and cited references with the supplier and receiving.

### QVS00138 - Quetta Voltage Solutions - **MANUAL_REVIEW**
File `INV-049_QVS_QVS00138.pdf` | PO PO-2025-0044 | delivery GRN-2025-0044 | total PKR 350080.00 | extraction confidence 1.00 | human review: PENDING
- **[HIGH] MISSING_PO** (MANUAL_REVIEW) - Manual review required: Purchase order PO-2025-0044 was not found among the supplied documents. Expected PO-2025-0044, observed not on file. Supporting source: POL-001.txt, Section 1.1.
  - Evidence: `POL-001.txt` / Section 1.1: "[Section 1.1] Every supplier invoice must be matched to its purchase order and to the goods-received or delivery record before payment is considered."
- Unresolved questions: Purchase order PO-2025-0044 was not found among the supplied documents.
- Recommended actions: Locate the purchase order (or confirm an authorised exception) before paying.

### IC2025-00138 - Indus Components & Circuits (Pvt) Ltd - **MANUAL_REVIEW**
File `INV-050_ICC_IC2025-00138.pdf` | PO PO-2025-0043 | delivery DC-2025-0043 | total PKR 6638.50 | extraction confidence 1.00 | human review: PENDING
- **[HIGH] MISSING_PO** (MANUAL_REVIEW) - Manual review required: Purchase order PO-2025-0043 was not found among the supplied documents. Expected PO-2025-0043, observed not on file. Supporting source: POL-001.txt, Section 1.1.
  - Evidence: `POL-001.txt` / Section 1.1: "[Section 1.1] Every supplier invoice must be matched to its purchase order and to the goods-received or delivery record before payment is considered."
- Unresolved questions: Purchase order PO-2025-0043 was not found among the supplied documents.
- Recommended actions: Locate the purchase order (or confirm an authorised exception) before paying.

### SCW-00183 - Sialkot CableWorks Co. - **PASSED**
File `INV-051_SCW_SCW-00183.pdf` | PO PO-2025-0013 | delivery DC-2025-0013 | total PKR 167382.60 | extraction confidence 0.87 | human review: NOT_REQUIRED

### LL-INV-0169 - Lahore LumenTech Industries - **PASSED**
File `INV-052_LLI_LL-INV-0169.pdf` | PO PO-2025-0017 | delivery DC-2025-0017 | total PKR 198327.70 | extraction confidence 1.00 | human review: NOT_REQUIRED

### PCH-0405 - Peshawar Circuit House - **MANUAL_REVIEW**
File `INV-053_PCH_PCH-0405.png` | PO PO-2025-0045 | delivery n/a | total PKR 78155.00 | extraction confidence 0.94 | human review: PENDING
- **[MEDIUM] MISSING_DC** (MANUAL_REVIEW) - Manual review required: No delivery challan / goods-received note was found for this invoice. Expected DC-2025-0045, observed not on file. Supporting source: POL-001.txt, Section 1.4.
  - Evidence: `POL-001.txt` / Section 1.4: "[Section 1.4] A missing delivery record is not proof of non-delivery. The invoice is routed to manual review so that receiving staff can confirm delivery."
- Unresolved questions: No delivery challan / goods-received note was found for this invoice.
- Recommended actions: Ask receiving staff to confirm delivery and locate the delivery record. Absence of the record is not proof of non-delivery.

### QVS00144 - Quetta Voltage Solutions - **PASSED_WITH_NOTES**
File `INV-054_QVS_QVS00144.pdf` | PO PO-2025-0049 | delivery DC-2025-0049 | total PKR 147742.80 | extraction confidence 1.00 | human review: NOT_REQUIRED
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 1: description 'Current Residual Breaker 2-Pole 40A' differs from the catalogue but resolves to ELE-1005 (fuzzy). Expected Residual Current Breaker 2-Pole 40A, observed Current Residual Breaker 2-Pole 40A.

### KET/25/0297 - Karachi Electro Traders - **FLAGGED**
File `INV-055_KET_KET-25-0297.jpg` | PO PO-2025-0011 | delivery DC-2025-0011 | total PKR 1325290.40 | extraction confidence 0.60 | human review: PENDING
Estimated exposure: 149,661.00 (disputed amount, not a confirmed saving)
- **[MEDIUM] AMBIGUOUS_PRODUCT** (MANUAL_REVIEW) - Manual review required: Line 1: description 'Core 100m Coil' could refer to several products (CAB-4001, CAB-4002, CAB-4003). Expected a single catalogue product, observed Core 100m Coil. Supporting source: POL-005.txt, Section 5.5.
  - Evidence: `POL-005.txt` / Section 5.5: "[Section 5.5] Where an invoice line cannot be resolved to a single catalogue product, it is routed to manual review."
- **[MEDIUM] AMBIGUOUS_PRODUCT** (MANUAL_REVIEW) - Manual review required: Line 2: description 'Core 100m Coil' could refer to several products (CAB-4001, CAB-4002, CAB-4003). Expected a single catalogue product, observed Core 100m Coil. Supporting source: POL-005.txt, Section 5.5.
  - Evidence: `POL-005.txt` / Section 5.5: "[Section 5.5] Where an invoice line cannot be resolved to a single catalogue product, it is routed to manual review."
- **[MEDIUM] TAX_CALC_ERROR** (POTENTIAL) - Potential anomaly: Header tax total 126396.40 differs from the sum of line taxes 106875.40. Expected 106875.40, observed 126396.40 (difference 19521.00). Supporting source: POL-002.txt, Section 2.8.
  - Evidence: `POL-002.txt` / Section 2.8: "[Section 2.8] Tax is calculated on the line amount after discount. Additional charges are not taxable under this synthetic policy."
- **[HIGH] GRAND_TOTAL_ERROR** (POTENTIAL) - Potential anomaly: Grand total 1325290.40 differs from subtotal 1068754.00 + tax 126396.40 + charges 0 = 1195150.40. Expected 1195150.40, observed 1325290.40 (difference 130140.00). No supporting contract/policy passage was found in the knowledge base.
- **[MEDIUM] EXTRACTION_LOW_CONFIDENCE** (MANUAL_REVIEW) - Manual review required: Extraction confidence 0.60 (ocr+rule); ocr_variant=0 integrity_score=10.4. No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: Line 1: description 'Core 100m Coil' could refer to several products (CAB-4001, CAB-4002, CAB-4003). | Line 2: description 'Core 100m Coil' could refer to several products (CAB-4001, CAB-4002, CAB-4003). | Header tax total 126396.40 differs from the sum of line taxes 106875.40. | Grand total 1325290.40 differs from subtotal 1068754.00 + tax 126396.40 + charges 0 = 1195150.40.
- Recommended actions: Have a buyer decide which catalogue product this line refers to. | Ask the supplier to correct the tax calculation. | Return the invoice for correction; the stated total does not foot.

### KET/25/0317 - Karachi Electro Traders - **PASSED_WITH_NOTES**
File `INV-056_KET_KET-25-0317.txt` | PO PO-2025-0048 | delivery GRN-2025-0048 | total PKR 229244.18 | extraction confidence 1.00 | human review: NOT_REQUIRED
- **[INFO] PRODUCT_DESCRIPTION_VARIANT** (PASSED) - Note: Line 1: description 'MCB 2P 32A' differs from the catalogue but resolves to ELE-1002 (code_exact). Expected Miniature Circuit Breaker 2-Pole 32A, observed MCB 2P 32A.

### KET/25/0333 - Karachi Electro Traders (Pvt) Ltd - **FLAGGED**
File `INV-057_KET_KET-25-0333.pdf` | PO PO-2025-0067 | delivery DC-2025-0069 | total PKR 610976.50 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 27,717.00 (disputed amount, not a confirmed saving)
- **[MEDIUM] DISCOUNT_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 1 CAB-4002: discount 0% differs from the contractual 5% (quantity basis 50, threshold 50). Expected 5, observed 0 (difference -5). Supporting source: CONTRACT_SUP-001.txt, Volume Discount.
  - Evidence: `CONTRACT_SUP-001.txt` / Volume Discount: "[Volume Discount] A volume discount of 5 percent applies to any product line where the ordered quantity is 50 units or more. The discount is determined on the purchase-order quantity and shown on the "
- **[MEDIUM] TAX_CALC_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 3: tax 7203.00 differs from 15.00% of 34300.00 = 5145.00. Expected 5145.00, observed 7203.00 (difference 2058.00). Supporting source: POL-002.txt, Section 2.8.
  - Evidence: `POL-002.txt` / Section 2.8: "[Section 2.8] Tax is calculated on the line amount after discount. Additional charges are not taxable under this synthetic policy."
- **[HIGH] UNAUTHORIZED_CHARGE** (CONFIRMED) - Confirmed discrepancy: Service Surcharge of 1800.00 is not permitted by agreement AG-001-B. Expected 0.00, observed 1800.00 (difference 1800.00). Supporting source: CONTRACT_SUP-001.txt, Freight and Additional Charges.
  - Evidence: `CONTRACT_SUP-001.txt` / Freight and Additional Charges: "[Freight and Additional Charges] Delivery to the Buyer's store is included in the unit prices. No freight, handling, packing, fuel or other additional charge may be invoiced."
- Recommended actions: Ask the supplier to apply the contractual volume discount. | Ask the supplier to correct the tax calculation. | Query the charge against the supplier agreement; request removal or written authorisation from procurement.

### IC2025-00125 - Indus Components & Circuits (Pvt) Ltd - **PASSED**
File `INV-058_ICC_IC2025-00125.pdf` | PO PO-2025-0022 | delivery GRN-2025-0022 | total PKR 66082.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### IC2025-00137 - Indus Components & Circuits (Pvt) Ltd - **PASSED**
File `INV-059_ICC_IC2025-00137.pdf` | PO PO-2025-0030 | delivery GRN-2025-0030 | total PKR 83673.25 | extraction confidence 1.00 | human review: NOT_REQUIRED

### IC2025-00137 - Indus Components & Circuits (Pvt) Ltd - **FLAGGED**
File `INV-060_ICC_IC2025-00137.pdf` | PO PO-2025-0030 | delivery GRN-2025-0030 | total PKR 83673.25 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 83,673.25 (disputed amount, not a confirmed saving)
- **[CRITICAL] DUPLICATE_EXACT** (CONFIRMED) - Confirmed discrepancy: Invoice IC2025-00137 from this supplier was already processed as INV-059_ICC_IC2025-00137 (INV-059_ICC_IC2025-00137.pdf). Expected first submission only, observed duplicate of INV-059_ICC_IC2025-00137. Supporting source: POL-004.txt, Section 4.1.
  - Evidence: `POL-004.txt` / Section 4.1: "[Section 4.1] An invoice is an exact duplicate when the supplier and the normalized invoice number match an invoice already processed, regardless of file name or document format."
- Recommended actions: Do not process for payment; confirm with accounts payable that the earlier invoice is the one being paid.

### LL-INV-0185 - Lahore LumenTech Industries - **FLAGGED**
File `INV-061_LLI_LL-INV-0185.pdf` | PO PO-2025-0039 | delivery DC-2025-0039 | total PKR 26792.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 3,880.50 (disputed amount, not a confirmed saving)
- **[HIGH] GRAND_TOTAL_ERROR** (CONFIRMED) - Confirmed discrepancy: Grand total 26792.00 differs from subtotal 20555.00 + tax 2356.50 + charges 0 = 22911.50. Expected 22911.50, observed 26792.00 (difference 3880.50). No supporting contract/policy passage was found in the knowledge base.
- Recommended actions: Return the invoice for correction; the stated total does not foot.

### KET/25/0313 - Karachi Electro Traders - **FLAGGED**
File `INV-062_KET_KET-25-0313.pdf` | PO PO-2025-0034 | delivery GRN-2025-0034 | total PKR 206713.25 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 1,438.65 (disputed amount, not a confirmed saving)
- **[MEDIUM] LINE_SUBTOTAL_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 1: amount 26271.00 differs from qty 4 x price 6255.00 less 0% discount = 25020.00. Expected 25020.00, observed 26271.00 (difference 1251.00). No supporting contract/policy passage was found in the knowledge base.
- Recommended actions: Return the invoice to the supplier for correction of the line/subtotal arithmetic.

### LL-INV-0192 - Lahore LumenTech Industries - **FLAGGED**
File `INV-063_LLI_LL-INV-0192.pdf` | PO PO-2025-0041 | delivery DC-2025-0041 | total PKR 120412.50 | extraction confidence 0.92 | human review: PENDING
Estimated exposure: 1,200.00 (disputed amount, not a confirmed saving)
- **[HIGH] UNAUTHORIZED_CHARGE** (CONFIRMED) - Confirmed discrepancy: Fuel Surcharge of 1200.00 is not permitted by agreement AG-002. Expected 0.00, observed 1200.00 (difference 1200.00). Supporting source: CONTRACT_SUP-002.txt, Freight and Additional Charges.
  - Evidence: `CONTRACT_SUP-002.txt` / Freight and Additional Charges: "[Freight and Additional Charges] The Supplier may invoice the following additional charges: freight. Freight must not exceed PKR 3,500 per invoice. No other surcharge (including fuel or service surcha"
- Recommended actions: Query the charge against the supplier agreement; request removal or written authorisation from procurement.

### QVS00122 - QVS Quetta - **FLAGGED**
File `INV-064_QVS_QVS00122.pdf` | PO PO-2025-0018 | delivery GRN-2025-0018 | total PKR 129821.20 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 126,371.20 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: ELE-1010: invoiced quantity 10 exceeds the received quantity 0 across 1 delivery record(s). Expected 0, observed 10 (difference 10). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[HIGH] QTY_EXCEEDS_RECEIVED** (POTENTIAL) - Potential anomaly: ELE-1008: invoiced quantity 6 exceeds the received quantity 0 across 1 delivery record(s). Expected 0, observed 6 (difference 6). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- Unresolved questions: ELE-1010: invoiced quantity 10 exceeds the received quantity 0 across 1 delivery record(s). | ELE-1008: invoiced quantity 6 exceeds the received quantity 0 across 1 delivery record(s).
- Recommended actions: Ask receiving/stores to confirm quantities received; pay only for confirmed receipts until the balance is delivered or evidenced.

### LL-INV-0160 - Lahore LumenTech Industries - **PASSED**
File `INV-065_LLI_LL-INV-0160.png` | PO PO-2025-0006 | delivery GRN-2025-0006 | total PKR 274258.33 | extraction confidence 0.93 | human review: NOT_REQUIRED

### QVS00132 - Quetta Voltage Solutions - **FLAGGED**
File `INV-066_QVS_QVS00132.pdf` | PO PO-2025-0038 | delivery GRN-2025-0038 | total PKR 599692.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 597,042.00 (disputed amount, not a confirmed saving)
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: ELE-1006: invoiced quantity 150 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 150 (difference 150). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: ELE-1006: received quantity 150 exceeds ordered quantity 0. Expected 0, observed 150 (difference 150). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- **[HIGH] QTY_EXCEEDS_ORDERED** (POTENTIAL) - Potential anomaly: LGT-2003: invoiced quantity 5 exceeds ordered quantity 0 (product is not on the PO). Expected 0, observed 5 (difference 5). Supporting source: POL-001.txt, Section 1.2.
  - Evidence: `POL-001.txt` / Section 1.2: "[Section 1.2] The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing "
- **[MEDIUM] PO_DC_QTY_CONFLICT** (POTENTIAL) - Potential anomaly: LGT-2003: received quantity 5 exceeds ordered quantity 0. Expected 0, observed 5 (difference 5). Supporting source: POL-001.txt, Section 1.5.
  - Evidence: `POL-001.txt` / Section 1.5: "[Section 1.5] Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."
- **[HIGH] GRAND_TOTAL_ERROR** (CONFIRMED) - Confirmed discrepancy: Grand total 599692.00 differs from subtotal 518080.00 + tax 77712.00 + charges 2650.00 = 598442.00. Expected 598442.00, observed 599692.00 (difference 1250.00). No supporting contract/policy passage was found in the knowledge base.
- Unresolved questions: ELE-1006: invoiced quantity 150 exceeds ordered quantity 0 (product is not on the PO). | ELE-1006: received quantity 150 exceeds ordered quantity 0. | LGT-2003: invoiced quantity 5 exceeds ordered quantity 0 (product is not on the PO). | LGT-2003: received quantity 5 exceeds ordered quantity 0.
- Recommended actions: Pay only up to the ordered quantity unless the purchasing manager approves an amendment; request a corrected invoice. | Purchasing manager to resolve the over-delivery; pay only up to the ordered quantity until approved. | Return the invoice for correction; the stated total does not foot.

### QVvs00149 - Quetta Voltage Solutions - **FLAGGED**
File `INV-067_QVS_QVS00149.jpg` | PO PO-2025-0062 | delivery GRN-2025-0064 | total PKR 82394.00 | extraction confidence 0.88 | human review: PENDING
- **[MEDIUM] TAX_RATE_POLICY_MISMATCH** (CONFIRMED) - Confirmed discrepancy: Line 1 LGT-2001 (Lighting): tax rate 10.00% differs from the synthetic policy rate 15%. Expected 15, observed 10.00 (difference -5.00). Supporting source: POL-002.txt, Section 2.2.
  - Evidence: `POL-002.txt` / Section 2.2: "[Section 2.2] Synthetic policy tax rate for Lighting products is 15 percent."
- Recommended actions: Check the applicable rate under the (synthetic) policy and ask the supplier to correct if confirmed.

### SCW-00203 - Sialkot CableWorks Co. - **FLAGGED**
File `INV-068_SCW_SCW-00203.txt` | PO PO-2025-0036 | delivery GRN-2025-0036 | total PKR 254550.08 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 531.48 (disputed amount, not a confirmed saving)
- **[MEDIUM] TAX_CALC_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 3: tax 2303.08 differs from 10.00% of 17716.00 = 1771.60. Expected 1771.60, observed 2303.08 (difference 531.48). Supporting source: POL-002.txt, Section 2.8.
  - Evidence: `POL-002.txt` / Section 2.8: "[Section 2.8] Tax is calculated on the line amount after discount. Additional charges are not taxable under this synthetic policy."
- Recommended actions: Ask the supplier to correct the tax calculation.

### PCH-0392 - Peshawar Circuit House - **PASSED**
File `INV-069_PCH_PCH-0392.pdf` | PO PO-2025-0031 | delivery DC-2025-0031 | total PKR 265727.00 | extraction confidence 1.00 | human review: NOT_REQUIRED

### PCH-0392 - Peshawar Circuit House - **FLAGGED**
File `INV-070_PCH_PCH-0392.pdf` | PO PO-2025-0031 | delivery DC-2025-0031 | total PKR 265727.00 | extraction confidence 1.00 | human review: PENDING
Estimated exposure: 265,727.00 (disputed amount, not a confirmed saving)
- **[CRITICAL] DUPLICATE_EXACT** (CONFIRMED) - Confirmed discrepancy: Invoice PCH-0392 from this supplier was already processed as INV-069_PCH_PCH-0392 (INV-069_PCH_PCH-0392.pdf). Expected first submission only, observed duplicate of INV-069_PCH_PCH-0392. Supporting source: POL-004.txt, Section 4.1.
  - Evidence: `POL-004.txt` / Section 4.1: "[Section 4.1] An invoice is an exact duplicate when the supplier and the normalized invoice number match an invoice already processed, regardless of file name or document format."
- Recommended actions: Do not process for payment; confirm with accounts payable that the earlier invoice is the one being paid.

### PPS/0347/25 - Punjab Power Supply Co. - **FLAGGED**
File `INV-071_PPS_PPS-0347-25.png` | PO PO-2025-0037 | delivery DC-2025-0037 | total PKR 605789.60 | extraction confidence 0.93 | human review: PENDING
Estimated exposure: 8,985.60 (disputed amount, not a confirmed saving)
- **[MEDIUM] TAX_CALC_ERROR** (CONFIRMED) - Confirmed discrepancy: Line 3: tax 38937.60 differs from 15.00% of 199680.00 = 29952.00. Expected 29952.00, observed 38937.60 (difference 8985.60). Supporting source: POL-002.txt, Section 2.8.
  - Evidence: `POL-002.txt` / Section 2.8: "[Section 2.8] Tax is calculated on the line amount after discount. Additional charges are not taxable under this synthetic policy."
- Recommended actions: Ask the supplier to correct the tax calculation.

### PPS/0357/25 - Punjab Power Supply Co. - **MANUAL_REVIEW**
File `INV-072_PPS_PPS-0357-25.pdf` | PO PO-2025-0047 | delivery DC-2025-0047 | total PKR 500967.60 | extraction confidence 1.00 | human review: PENDING
- **[MEDIUM] UNKNOWN_PRODUCT_CODE** (MANUAL_REVIEW) - Manual review required: Line 3: product 'ELE-9901' is not in the product master. Closest catalogue items: ELE-1010, ELC-3009. Expected code in product master, observed ELE-9901. Supporting source: POL-005.txt, Section 5.5.
  - Evidence: `POL-005.txt` / Section 5.5: "[Section 5.5] Where an invoice line cannot be resolved to a single catalogue product, it is routed to manual review."
- Unresolved questions: Line 3: product 'ELE-9901' is not in the product master. Closest catalogue items: ELE-1010, ELC-3009.
- Recommended actions: Have procurement identify the item and update the product master or reject the line.
