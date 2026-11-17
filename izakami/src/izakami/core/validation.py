"""Number parsing helpers. Pure Python: no Qt, no I/O."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    """Raised when user-supplied text or values are not acceptable."""


_STRIP = "$€£¥₱₿% \u00a0"
_ALLOWED = re.compile(r"^[+-]?(?:\d[\d.,' \u00a0\u202f]*|[.,]\d+)$")


def normalize_number_text(raw: str) -> str:
    """Turn '95,000.50', '1.234,5', '$ 2 000' ... into a plain Decimal string.

    Ambiguity rule: a lone comma followed by exactly three digits ('1,500') is read as a
    thousands separator; otherwise a lone comma is a decimal comma ('1,5').
    """
    s = raw.strip().strip(_STRIP)
    if not s or not _ALLOWED.match(s):
        raise ValidationError("not a number")
    sign = ""
    if s[0] in "+-":
        sign = "-" if s[0] == "-" else ""
        s = s[1:]
    s = re.sub(r"[ '\u00a0\u202f]", "", s)
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        decimal_sep = "." if s.rfind(".") > s.rfind(",") else ","
        thousands = "," if decimal_sep == "." else "."
        if s.rfind(thousands) > s.rfind(decimal_sep):
            raise ValidationError("not a number")
        s = s.replace(thousands, "").replace(decimal_sep, ".")
    elif has_comma:
        if s.count(",") == 1 and len(s.split(",")[1]) != 3:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot and s.count(".") > 1:
        s = s.replace(".", "")
    return sign + s


def parse_decimal(text: object, field: str = "Value") -> Decimal:
    """Parse user text into a finite Decimal (sign is preserved; callers check ranges)."""
    if text is None or not str(text).strip():
        raise ValidationError(f"{field} is required.")
    try:
        value = Decimal(normalize_number_text(str(text)))
    except (ValidationError, InvalidOperation):
        raise ValidationError(f"{field}: '{text}' is not a valid number.") from None
    if not value.is_finite():
        raise ValidationError(f"{field}: '{text}' is not a valid number.")
    return value


def parse_price_text(raw: object, field: str = "Price") -> Decimal:
    """Strict parser for text captured from another application's clipboard."""
    if raw is None or not str(raw).strip():
        raise ValidationError("The clipboard is empty.")
    text = str(raw).strip()
    if "\n" in text or "\r" in text or len(text) > 32:
        raise ValidationError("The copied text does not look like a single price.")
    value = parse_decimal(text, field)
    if value <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    return value


def format_plain(value: Decimal) -> str:
    """Decimal -> plain string without exponent or trailing zeros ('95000', '0.02')."""
    if value == value.to_integral_value():
        return format(value.quantize(Decimal(1)), "f")
    return format(value.normalize(), "f")
