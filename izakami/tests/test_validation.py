from decimal import Decimal as D

import pytest

from izakami.core.validation import ValidationError, format_plain, parse_decimal, parse_price_text


@pytest.mark.parametrize("text,expected", [
    ("95,000.50", D("95000.50")), ("1.0850", D("1.0850")), ("1,5", D("1.5")), ("1.234.567", D("1234567")),
    ("1,234", D("1234")), ("$ 2 000.5", D("2000.5")), ("1.234,5", D("1234.5")), ("0.02", D("0.02")), ("-5", D("-5")),
])
def test_parse_decimal(text, expected):
    assert parse_decimal(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "abc", "NaN", "Infinity", "1e5", "1,2.3,4", "--1", ".", "12abc"])
def test_parse_decimal_rejects(text):
    with pytest.raises(ValidationError):
        parse_decimal(text, "Entry")


def test_parse_price_text_rules():
    assert parse_price_text(" 95,000.50 ") == D("95000.50")
    for bad in ["-5", "0", "BTC 95000", "1\n2", None, "", "1" * 40]:
        with pytest.raises(ValidationError):
            parse_price_text(bad)


def test_format_plain():
    assert format_plain(D("100")) == "100"
    assert format_plain(D("1E+2")) == "100"
    assert format_plain(D("0.0200")) == "0.02"
