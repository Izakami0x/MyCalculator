from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from izakami.core.currency_conversion import ConversionError, ExternalRate, resolve_conversion


def test_same_currency_is_exact():
    r = resolve_conversion("USD", "usd", None)
    assert r.rate == 1 and r.exact


def test_dollar_pegs_are_equal():
    assert resolve_conversion("USDT", "USD", None).exact


def test_manual_rate_is_an_estimate():
    r = resolve_conversion("JPY", "USD", D("0.0067"))
    assert r.rate == D("0.0067") and not r.exact and "estimate" in r.note


@pytest.mark.parametrize("rate", [None, D("0"), D("-1"), D("NaN")])
def test_missing_or_invalid_rate_is_rejected(rate):
    with pytest.raises(ConversionError):
        resolve_conversion("JPY", "USD", rate)


def test_external_fresh_and_stale():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    fresh = ExternalRate(D("0.007"), now - timedelta(hours=1), "demo")
    stale = ExternalRate(D("0.007"), now - timedelta(days=3), "demo")
    assert resolve_conversion("JPY", "USD", D("0.0067"), fresh, now=now).exact
    s = resolve_conversion("JPY", "USD", D("0.0067"), stale, now=now)
    assert not s.exact and "stale" in s.note
