"""Contract calculation models. Each answers: what does one quantity unit risk / weigh?"""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from ..models.instrument import MODEL_LINEAR, MODEL_TICK, Instrument


class SizingModel(Protocol):
    def risk_per_unit(self, inst: Instrument, distance: Decimal, rate: Decimal) -> Decimal:
        """Loss (account currency) for 1 quantity unit if price moves ``distance``."""

    def notional(self, inst: Instrument, quantity: Decimal, price: Decimal) -> Decimal:
        """Position value in the instrument's P&L currency."""


class LinearContractModel:
    """P&L per price unit equals the contract size (forex lots, CFDs, crypto, stocks)."""

    def risk_per_unit(self, inst: Instrument, distance: Decimal, rate: Decimal) -> Decimal:
        return distance * inst.contract_size * rate

    def notional(self, inst: Instrument, quantity: Decimal, price: Decimal) -> Decimal:
        return quantity * inst.contract_size * price


class TickValueModel:
    """P&L = number of ticks moved x tick value (futures and similar)."""

    def risk_per_unit(self, inst: Instrument, distance: Decimal, rate: Decimal) -> Decimal:
        return (distance / inst.tick_size) * inst.tick_value * rate

    def notional(self, inst: Instrument, quantity: Decimal, price: Decimal) -> Decimal:
        return quantity * inst.contract_size * price


_MODELS: dict[str, SizingModel] = {MODEL_LINEAR: LinearContractModel(), MODEL_TICK: TickValueModel()}


def get_model(name: str) -> SizingModel:
    try:
        return _MODELS[name]
    except KeyError:
        raise ValueError(f"Unknown sizing model: {name}") from None
