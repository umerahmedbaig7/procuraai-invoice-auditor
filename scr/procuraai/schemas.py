"""Pydantic schemas shared by ingestion, extraction, the audit engine, the API and the dashboard.

Percentages (discount, tax) are stored as percent numbers (15 means 15%). Money and quantities use Decimal.
Unknown values are ``None`` and listed in ``missing_fields``; nothing is invented.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

DocType = Literal["INVOICE", "PURCHASE_ORDER", "DELIVERY_CHALLAN", "CONTRACT", "POLICY", "UNKNOWN"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)


class Provenance(_Base):
    """Where an extracted value came from."""
    source_file: str
    page: int | None = None
    excerpt: str | None = None
    method: str = "rule"          # rule | llm | csv | ocr+rule
    confidence: float = 1.0


class SupplierInfo(_Base):
    supplier_id: str
    name: str
    tax_id: str | None = None
    address: str | None = None
    city: str | None = None
    payment_terms: str | None = None
    aliases: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    volume_discount_min_qty: Decimal = Decimal("0")
    volume_discount_pct: Decimal = Decimal("0")
    status: str = "ACTIVE"


class ProductInfo(_Base):
    product_code: str
    description: str
    category: str
    uom: str
    list_price: Decimal
    aliases: list[str] = Field(default_factory=list)


class LineItem(_Base):
    line_no: int
    product_code: str | None = None
    description: str = ""
    quantity: Decimal | None = None
    uom: str | None = None
    unit_price: Decimal | None = None
    discount_pct: Decimal | None = None
    line_amount: Decimal | None = None        # net of discount, before tax
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    confidence: float = 1.0
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("quantity", "unit_price", "discount_pct", "line_amount", "tax_rate", "tax_amount")
    def _ser(self, v):  # JSON-friendly
        return None if v is None else str(v)


class Charge(_Base):
    charge_type: str                      # FREIGHT | HANDLING | FUEL | PACKING | INSURANCE | SERVICE | OTHER
    description: str = ""
    amount: Decimal

    @field_serializer("amount")
    def _ser(self, v):
        return str(v)


class DocumentBase(_Base):
    doc_type: DocType = "UNKNOWN"
    source_file: str = ""
    page_count: int | None = None
    extraction_method: str = "rule"
    extraction_confidence: float = 1.0
    missing_fields: list[str] = Field(default_factory=list)
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    received_at: datetime | None = None


class InvoiceRecord(DocumentBase):
    doc_type: Literal["INVOICE"] = "INVOICE"
    invoice_id: str = ""                  # stable internal id (file stem or generated)
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    supplier_id: str | None = None        # only if printed on the document
    supplier_name: str | None = None
    supplier_tax_id: str | None = None
    po_number: str | None = None
    dc_reference: str | None = None
    currency: str | None = None
    payment_terms: str | None = None
    lines: list[LineItem] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    subtotal: Decimal | None = None
    tax_total: Decimal | None = None
    grand_total: Decimal | None = None

    @property
    def has_tax_info(self) -> bool:
        return any(l.tax_rate is not None or l.tax_amount is not None for l in self.lines) or self.tax_total is not None

    @field_serializer("subtotal", "tax_total", "grand_total")
    def _ser(self, v):
        return None if v is None else str(v)


class POLine(_Base):
    line_no: int
    product_code: str | None = None
    description: str = ""
    quantity: Decimal | None = None
    uom: str | None = None
    unit_price: Decimal | None = None
    line_amount: Decimal | None = None

    @field_serializer("quantity", "unit_price", "line_amount")
    def _ser(self, v):
        return None if v is None else str(v)


class PurchaseOrderRecord(DocumentBase):
    doc_type: Literal["PURCHASE_ORDER"] = "PURCHASE_ORDER"
    po_number: str | None = None
    po_date: date | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    currency: str | None = None
    payment_terms: str | None = None
    expected_delivery_date: date | None = None
    lines: list[POLine] = Field(default_factory=list)
    total: Decimal | None = None

    @field_serializer("total")
    def _ser(self, v):
        return None if v is None else str(v)


class DCLine(_Base):
    line_no: int
    product_code: str | None = None
    description: str = ""
    quantity_received: Decimal | None = None
    uom: str | None = None

    @field_serializer("quantity_received")
    def _ser(self, v):
        return None if v is None else str(v)


class DeliveryChallanRecord(DocumentBase):
    doc_type: Literal["DELIVERY_CHALLAN"] = "DELIVERY_CHALLAN"
    dc_number: str | None = None
    dc_date: date | None = None
    po_number: str | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    lines: list[DCLine] = Field(default_factory=list)
    remarks: str | None = None


class SupplierAgreement(_Base):
    """Supplier pricing agreement header (contract / price list)."""
    agreement_id: str
    supplier_id: str
    effective_from: date
    effective_to: date
    currency: str = "PKR"
    payment_terms: str | None = None
    volume_discount_min_qty: Decimal = Decimal("0")
    volume_discount_pct: Decimal = Decimal("0")
    freight_policy: str = "INCLUDED"                  # INCLUDED | CAPPED
    freight_cap: Decimal = Decimal("0")
    allowed_charge_types: list[str] = Field(default_factory=list)
    source_file: str | None = None


class PriceListEntry(_Base):
    agreement_id: str
    supplier_id: str
    product_code: str
    contract_price: Decimal
    currency: str = "PKR"
    effective_from: date
    effective_to: date


class PolicyRule(_Base):
    policy_id: str
    rule_key: str
    rule_value: str
    text: str
    source_file: str | None = None


class EvidenceRef(_Base):
    """A retrieved passage supporting a finding. Never fabricated: always from an indexed source."""
    source_file: str
    doc_type: str = ""
    supplier_id: str | None = None
    section: str | None = None
    page: int | None = None
    snippet: str
    score: float | None = None
    chunk_id: str | None = None


class AuditFinding(_Base):
    finding_id: str
    invoice_id: str
    code: str
    check: str
    status: Literal["CONFIRMED", "POTENTIAL", "INSUFFICIENT_EVIDENCE", "MANUAL_REVIEW", "PASSED"]
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    line_no: int | None = None
    product_code: str | None = None
    expected: str | None = None
    observed: str | None = None
    difference: str | None = None
    message: str
    reason: str = ""
    identifiers: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    exposure_amount: Decimal = Decimal("0")
    exposure_key: str | None = None
    confidence: float = 1.0
    needs_human_review: bool = False
    explanation: str | None = None            # optional LLM-written narrative about an already-computed finding
    explanation_source: str | None = None     # "llm" | "template"

    @field_serializer("exposure_amount")
    def _ser(self, v):
        return str(v)


class CheckResult(_Base):
    check: str
    status: Literal["PASSED", "FAILED", "SKIPPED", "INSUFFICIENT_EVIDENCE"]
    detail: str = ""


class InvoiceAuditResult(_Base):
    audit_id: str
    invoice_id: str
    invoice_number: str | None = None
    invoice_date: date | None = None
    supplier_id: str | None = None
    supplier_name: str | None = None
    supplier_match: dict[str, Any] = Field(default_factory=dict)
    po_number: str | None = None
    linked_po: str | None = None
    linked_dcs: list[str] = Field(default_factory=list)
    currency: str | None = None
    grand_total: Decimal | None = None
    source_file: str | None = None
    overall_status: Literal["PASSED", "PASSED_WITH_NOTES", "FLAGGED", "MANUAL_REVIEW"] = "PASSED"
    findings: list[AuditFinding] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    total_exposure: Decimal = Decimal("0")
    extraction_confidence: float = 1.0
    unresolved_questions: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    human_review_status: Literal["NOT_REQUIRED", "PENDING"] = "NOT_REQUIRED"
    product_matches: list[dict[str, Any]] = Field(default_factory=list)

    @field_serializer("grand_total", "total_exposure")
    def _ser(self, v):
        return None if v is None else str(v)


def dump_json(model: BaseModel, **kw) -> str:
    return model.model_dump_json(indent=2, **kw)
