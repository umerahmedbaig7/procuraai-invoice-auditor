"""Decimal money helpers. All authoritative financial arithmetic goes through this module.

Rounding rules (documented, configurable via ``RoundingPolicy``):
  * Every monetary quantity is rounded to 2 decimal places with ROUND_HALF_UP.
  * Rounding is applied at each step: gross = round(qty*price); discount = round(gross*disc%/100);
    net = gross - discount; tax = round(net*rate%/100).
  * Header subtotal is the exact sum of rounded line nets; tax total the exact sum of rounded line taxes.
Binary floats are never used for validation: values are parsed from text via ``Decimal(str(x))``.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ZERO = Decimal("0")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class RoundingPolicy:
    places: int = 2
    mode: str = ROUND_HALF_UP

    def q(self, x: Decimal) -> Decimal:
        return x.quantize(Decimal(1).scaleb(-self.places), rounding=self.mode)


DEFAULT_ROUNDING = RoundingPolicy()


def to_decimal(x: Any, default: Decimal | None = None) -> Decimal | None:
    """Parse a number/string such as '12,345.60' or 'PKR 1,200' into a Decimal; default if impossible."""
    if x is None:
        return default
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        return default
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, float):
        return Decimal(str(x))
    s = str(x).strip().replace(",", "")
    for tok in ("PKR", "Rs.", "Rs", "USD", "%"):
        s = s.replace(tok, "")
    s = s.strip()
    if s in ("", "-", "nan", "None", "NaN", "N/A"):
        return default
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return default
    return -d if neg else d


def gross(qty: Decimal, price: Decimal, rp: RoundingPolicy = DEFAULT_ROUNDING) -> Decimal:
    return rp.q(qty * price)


def line_net(qty: Decimal, price: Decimal, disc_pct: Decimal = ZERO, rp: RoundingPolicy = DEFAULT_ROUNDING) -> Decimal:
    g = gross(qty, price, rp)
    disc = rp.q(g * disc_pct / Decimal(100))
    return g - disc


def tax_on(net: Decimal, rate_pct: Decimal, rp: RoundingPolicy = DEFAULT_ROUNDING) -> Decimal:
    return rp.q(net * rate_pct / Decimal(100))


def fmt(x: Decimal | None) -> str:
    return "" if x is None else f"{x:,.2f}"
