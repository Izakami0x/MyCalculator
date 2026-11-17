"""Display formatting for numbers (Decimal in, text out)."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..core.validation import format_plain

__all__ = ["format_plain", "fmt_money", "fmt_price", "fmt_qty", "qty_text"]


def _quantize(value: Decimal, places: int) -> Decimal:
    try:
        return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    except Exception:
        return value


def fmt_money(value: Decimal) -> str:
    return f"{_quantize(value, 2):,.2f}"


def fmt_price(value: Decimal, decimals: int) -> str:
    return f"{_quantize(value, decimals):,.{decimals}f}"


def fmt_qty(value: Decimal, decimals: int) -> str:
    return f"{_quantize(value, decimals):,.{decimals}f}"


def qty_text(value: Decimal, decimals: int) -> str:
    """Ungrouped quantity for the clipboard, e.g. '0.020'."""
    return f"{_quantize(value, decimals):.{decimals}f}"
