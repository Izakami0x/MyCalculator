from dataclasses import replace
from decimal import Decimal as D

import pytest

from izakami.core.calculator import CalcInputs, calculate
from izakami.database.presets import starter_presets
from izakami.models.account import RiskMode
from izakami.models.calculation_result import Direction
from izakami.models.instrument import Instrument

P = {i.symbol: i for i in starter_presets()}


def run(symbol="EURUSD", *, entry, stop, balance="10000", risk="1", rr="2", mode=RiskMode.PERCENT,
        ccy="USD", lev="10", inst=None):
    return calculate(CalcInputs(
        balance=D(balance), account_currency=ccy, risk_mode=mode, risk_value=D(risk), rr=D(rr),
        entry=D(entry), stop=D(stop), instrument=inst or P[symbol], default_leverage=D(lev)))


def test_forex_long():
    r = run(entry="1.1000", stop="1.0950", lev="100")
    assert r.ok and r.direction is Direction.LONG
    assert r.quantity == D("0.20") and r.risk_amount == D("100") and r.risk_distance == D("0.0050")
    assert r.notional == D("22000") and r.margin == D("220")
    assert r.potential_loss == D("100") and r.potential_profit == D("200") and r.take_profit == D("1.1100")


def test_forex_short():
    r = run(entry="1.1000", stop="1.1050")
    assert r.direction is Direction.SHORT and r.quantity == D("0.20") and r.take_profit == D("1.0900")
    assert r.potential_profit == D("200")


def test_gold():
    r = run("XAUUSD", entry="2000", stop="1990")
    assert r.quantity == D("0.10") and r.take_profit == D("2020") and r.potential_profit == D("200")


def test_index_cfd():
    r = run("NAS100", entry="20000", stop="19950")
    assert r.quantity == D("2.0") and r.notional == D("40000")


def test_crypto_matches_mockup():
    r = run("BTCUSDT", entry="95000", stop="94500", balance="1000", lev="3")
    assert r.quantity == D("0.020") and r.notional == D("1900") and r.take_profit == D("96000")
    assert r.potential_loss == D("10") and r.potential_profit == D("20")
    assert abs(r.margin - D("633.3333")) < D("0.001")
    assert not r.is_estimate  # USDT ~ USD peg is treated as exact


def test_fixed_risk_and_rr():
    r = run(entry="1.1000", stop="1.0950", mode=RiskMode.FIXED, risk="250", rr="3")
    assert r.quantity == D("0.50") and r.risk_amount == D("250")
    assert r.take_profit == D("1.1150") and r.potential_profit == D("750")


def test_custom_contract_size():
    inst = replace(P["EURUSD"], symbol="MINI", contract_size=D("1000"))
    assert run(entry="1.1", stop="1.095", inst=inst).quantity == D("20.00")


def test_quantity_rounds_down_never_up():
    r = run(entry="1.1000", stop="1.0997")  # raw 3.3333... lots
    assert r.quantity == D("3.33") and r.raw_quantity > r.quantity
    assert r.potential_loss == D("99.90") and r.potential_loss <= r.risk_amount


def test_currency_conversion_marks_estimate():
    inst = replace(P["USDJPY"], conversion_rate=D("0.0067"))
    r = run(entry="150.00", stop="149.50", inst=inst)
    assert r.quantity == D("0.29") and r.is_estimate and r.warnings


def test_account_currency_differs_uses_manual_rate_and_says_so():
    # The preset's stored rate (1) is only a placeholder for a USD account: it must be flagged.
    r = run("EURUSD", entry="1.1", stop="1.095", ccy="EUR")
    assert r.ok and r.is_estimate and "USD->EUR rate 1" in r.warnings[0]
    fixed = replace(P["EURUSD"], conversion_rate=D("0.92"))
    r2 = run(inst=fixed, entry="1.1", stop="1.095", ccy="EUR")
    assert r2.quantity == D("0.21") and r2.is_estimate  # 100 / (0.005 * 100000 * 0.92) = 0.2173 -> 0.21


def test_tick_value_model():
    es = Instrument(symbol="ES", asset_class="futures", model="tick", contract_size=D("50"),
                    tick_size=D("0.25"), tick_value=D("12.5"), quantity_step=D("1"), min_quantity=D("1"),
                    max_quantity=D("100"), quantity_unit="contracts")
    r = run(inst=es, entry="5000", stop="4990", balance="100000")
    assert r.quantity == D("2") and r.notional == D("500000") and r.potential_loss == D("1000")


def test_below_minimum_quantity_is_an_error_without_numbers():
    r = run(entry="1.1000", stop="1.0950", balance="100")
    assert not r.ok and "below the minimum" in r.errors[0]
    assert r.quantity is None and r.potential_loss is None and r.notional is None


def test_above_maximum_quantity():
    r = run(entry="1.1000", stop="1.099995")
    assert not r.ok and "exceeds the maximum" in r.errors[0] and r.quantity is None


def test_min_notional():
    inst = replace(P["EURUSD"], min_notional=D("50000"))
    r = run(entry="1.1000", stop="1.0950", inst=inst)
    assert not r.ok and "minimum notional" in r.errors[0]


@pytest.mark.parametrize("kwargs", [
    dict(entry="1.1", stop="1.1"), dict(entry="-1", stop="1"), dict(entry="1.1", stop="0"),
    dict(entry="1.1", stop="1.09", balance="0"), dict(entry="1.1", stop="1.09", risk="150"),
    dict(entry="1.1", stop="1.09", rr="0"), dict(entry="1.1", stop="1.09", risk="0"),
])
def test_invalid_inputs(kwargs):
    r = run(**kwargs)
    assert not r.ok and r.errors and r.quantity is None


def test_nan_input_rejected():
    r = calculate(CalcInputs(D("NaN"), "USD", RiskMode.PERCENT, D(1), D(2), D("1.1"), D("1.09"), P["EURUSD"]))
    assert not r.ok


def test_zero_tick_size_does_not_divide_by_zero():
    bad = replace(P["EURUSD"], tick_size=D("0"))
    r = run(entry="1.1", stop="1.09", inst=bad)
    assert not r.ok and any("Tick size" in e for e in r.errors)


def test_margin_overrides():
    assert run("EURUSD", entry="1.1", stop="1.095", inst=replace(P["EURUSD"], leverage=D("30"))).margin == D("22000") / 30
    assert run("EURUSD", entry="1.1", stop="1.095", inst=replace(P["EURUSD"], margin_rate=D("0.05"))).margin == D("1100")


def test_take_profit_rounds_toward_entry():
    inst = replace(P["EURUSD"], tick_size=D("0.5"), contract_size=D("1"), quantity_step=D("0.01"), max_quantity=None)
    long_ = run(inst=inst, entry="100", stop="99", rr="1.3")
    short = run(inst=inst, entry="100", stop="101", rr="1.3")
    assert long_.take_profit == D("101.0") and short.take_profit == D("99.0")
    assert long_.potential_profit < long_.potential_loss * D("1.3")


def test_every_preset_is_valid():
    assert all(not p.validate() for p in P.values())
