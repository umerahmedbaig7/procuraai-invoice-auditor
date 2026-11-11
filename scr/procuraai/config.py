"""Central configuration. Everything tunable lives here; secrets come only from the environment."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .audit.money import RoundingPolicy


@dataclass
class AuditConfig:
    """Tolerances and thresholds for the deterministic audit engine and matching layer."""
    base_currency: str = "PKR"
    rounding: RoundingPolicy = field(default_factory=RoundingPolicy)
    line_tolerance: Decimal = Decimal("0.01")      # absolute, per line amount / tax amount
    header_tolerance: Decimal = Decimal("0.05")    # absolute, for header subtotal / tax / grand total
    price_tolerance_abs: Decimal = Decimal("0.00")  # absolute unit-price tolerance vs contract
    price_tolerance_pct: Decimal = Decimal("0.00")  # percent unit-price tolerance vs contract
    qty_tolerance: Decimal = Decimal("0")          # absolute quantity tolerance
    discount_tolerance_pct: Decimal = Decimal("0.01")
    tax_rate_tolerance_pct: Decimal = Decimal("0.01")
    # Matching thresholds (rapidfuzz scores 0-100)
    supplier_accept: float = 90.0
    supplier_review: float = 75.0
    product_accept: float = 88.0
    product_review: float = 70.0
    product_margin: float = 6.0
    code_desc_min: float = 55.0       # below this, a known code + description are considered conflicting
    # Severity escalation for pricing findings
    price_high_pct: Decimal = Decimal("10")
    possible_duplicate_days: int = 45


# Synthetic tax policy (NOT real tax law): category -> rate percent. Overridable from policy CSV.
DEFAULT_TAX_RATES = {
    "Electrical Equipment": Decimal("15"), "Lighting": Decimal("15"), "Electronic Components": Decimal("10"),
    "Cables": Decimal("10"), "Connectors": Decimal("10"), "Industrial Supplies": Decimal("15"),
}
DEFAULT_TAX_RATE_UNKNOWN_CATEGORY = Decimal("15")


@dataclass
class Settings:
    """Runtime settings read from environment variables (never hard-coded secrets)."""
    gemini_api_key: str | None = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.environ.get("PROCURAAI_GEMINI_MODEL", "gemini-3.8-flash"))
    embedding_model: str = field(default_factory=lambda: os.environ.get("PROCURAAI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("PROCURAAI_DATA_DIR", "procuraai-data")))
    db_url: str = field(default_factory=lambda: os.environ.get("PROCURAAI_DB_URL", "sqlite:///procuraai.db"))
    upload_dir: Path = field(default_factory=lambda: Path(os.environ.get("PROCURAAI_UPLOAD_DIR", "uploads")))
    api_key: str | None = field(default_factory=lambda: os.environ.get("PROCURAAI_API_KEY") or None)
    max_upload_mb: int = int(os.environ.get("PROCURAAI_MAX_UPLOAD_MB", "25"))
    llm_timeout_s: float = float(os.environ.get("PROCURAAI_LLM_TIMEOUT", "60"))
    llm_max_retries: int = int(os.environ.get("PROCURAAI_LLM_RETRIES", "3"))

    def redacted(self) -> dict:
        d = {k: str(v) for k, v in self.__dict__.items()}
        for k in ("gemini_api_key", "api_key"):
            d[k] = "<set>" if getattr(self, k) else "<not set>"
        return d
