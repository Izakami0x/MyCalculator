"""Editable starter instruments.

These are STARTING POINTS only. Contract sizes, steps, limits and especially the manual
currency-conversion rates differ between brokers and change over time - verify and edit them.
"""
from __future__ import annotations

from decimal import Decimal as D

from ..models.instrument import Instrument


def _p(symbol: str, asset_class: str, *, contract: str, tick: str, step: str, minq: str, maxq: str,
       unit: str, ccy: str = "USD", rate: str = "1", min_notional: str = "0") -> Instrument:
    return Instrument(
        symbol=symbol, asset_class=asset_class, model="linear",
        contract_size=D(contract), tick_size=D(tick), tick_value=D(contract) * D(tick),
        quantity_step=D(step), min_quantity=D(minq), max_quantity=D(maxq),
        min_notional=D(min_notional), pnl_currency=ccy, conversion_rate=D(rate),
        quantity_unit=unit, is_preset=True,
    )


def starter_presets() -> list[Instrument]:
    fx = dict(contract="100000", step="0.01", minq="0.01", maxq="100", unit="lots")
    return [
        _p("EURUSD", "forex", tick="0.00001", **fx),
        _p("GBPUSD", "forex", tick="0.00001", **fx),
        _p("USDJPY", "forex", tick="0.001", ccy="JPY", rate="0.0065", **fx),
        _p("AUDUSD", "forex", tick="0.00001", **fx),
        _p("USDCAD", "forex", tick="0.00001", ccy="CAD", rate="0.72", **fx),
        _p("USDCHF", "forex", tick="0.00001", ccy="CHF", rate="1.25", **fx),
        _p("NZDUSD", "forex", tick="0.00001", **fx),
        _p("XAUUSD", "metals", contract="100", tick="0.01", step="0.01", minq="0.01", maxq="50", unit="lots"),
        _p("XAGUSD", "metals", contract="5000", tick="0.001", step="0.01", minq="0.01", maxq="50", unit="lots"),
        _p("NAS100", "indices", contract="1", tick="0.01", step="0.1", minq="0.1", maxq="100", unit="contracts"),
        _p("US30", "indices", contract="1", tick="0.01", step="0.1", minq="0.1", maxq="100", unit="contracts"),
        _p("SPX500", "indices", contract="1", tick="0.01", step="0.1", minq="0.1", maxq="100", unit="contracts"),
        _p("GER40", "indices", contract="1", tick="0.01", step="0.1", minq="0.1", maxq="100",
           unit="contracts", ccy="EUR", rate="1.10"),
        _p("UK100", "indices", contract="1", tick="0.01", step="0.1", minq="0.1", maxq="100",
           unit="contracts", ccy="GBP", rate="1.30"),
        _p("BTCUSDT", "crypto", contract="1", tick="0.01", step="0.001", minq="0.001", maxq="100",
           unit="BTC", ccy="USDT", min_notional="5"),
        _p("ETHUSDT", "crypto", contract="1", tick="0.01", step="0.001", minq="0.001", maxq="1000",
           unit="ETH", ccy="USDT", min_notional="5"),
        _p("SOLUSDT", "crypto", contract="1", tick="0.001", step="0.01", minq="0.01", maxq="10000",
           unit="SOL", ccy="USDT", min_notional="5"),
    ]
