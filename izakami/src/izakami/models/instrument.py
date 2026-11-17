"""Instrument model. Identity (symbol) is separate from contract specifications."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

ASSET_CLASSES = ("forex", "metals", "indices", "crypto", "stocks", "futures", "custom")
MODEL_LINEAR = "linear"
MODEL_TICK = "tick"
SIZING_MODELS = (MODEL_LINEAR, MODEL_TICK)
DEFAULT_BROKER = "default"


def decimals_of(value: Decimal) -> int:
    """Number of decimal places needed to represent ``value`` (0.001 -> 3, 5 -> 0)."""
    exp = value.normalize().as_tuple().exponent
    return max(0, -exp) if isinstance(exp, int) else 0


def _bad(value: Optional[Decimal]) -> bool:
    return value is None or not value.is_finite() or value <= 0


@dataclass(frozen=True)
class Instrument:
    """Contract specification of one tradable instrument.

    ``model`` selects how risk per quantity unit is derived:

    * ``linear`` - P&L per price unit = ``contract_size`` (forex, CFDs, crypto, stocks).
    * ``tick``   - P&L = ticks moved x ``tick_value`` (futures). ``contract_size`` is then
      only used for notional / margin estimates.
    """

    symbol: str
    asset_class: str = "custom"
    model: str = MODEL_LINEAR
    contract_size: Decimal = Decimal(1)
    tick_size: Decimal = Decimal("0.01")
    tick_value: Decimal = Decimal("0.01")
    quantity_step: Decimal = Decimal("0.01")
    min_quantity: Decimal = Decimal("0.01")
    max_quantity: Optional[Decimal] = None
    min_notional: Decimal = Decimal(0)
    pnl_currency: str = "USD"
    conversion_rate: Decimal = Decimal(1)
    quantity_unit: str = "units"
    leverage: Optional[Decimal] = None
    margin_rate: Optional[Decimal] = None
    broker_id: str = DEFAULT_BROKER
    id: Optional[int] = None
    is_preset: bool = False

    @property
    def price_decimals(self) -> int:
        return decimals_of(self.tick_size)

    @property
    def quantity_decimals(self) -> int:
        return decimals_of(self.quantity_step)

    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty list = valid)."""
        errors: list[str] = []
        if not self.symbol or not self.symbol.strip():
            errors.append("Symbol is required.")
        elif any(ch.isspace() for ch in self.symbol):
            errors.append("Symbol must not contain spaces.")
        if self.asset_class not in ASSET_CLASSES:
            errors.append("Unknown asset class.")
        if self.model not in SIZING_MODELS:
            errors.append("Unknown calculation model.")

        def positive(label: str, value: Optional[Decimal]) -> None:
            if _bad(value):
                errors.append(f"{label} must be greater than zero.")

        positive("Contract size", self.contract_size)
        positive("Tick size", self.tick_size)
        positive("Quantity step", self.quantity_step)
        positive("Minimum quantity", self.min_quantity)
        positive("Conversion rate", self.conversion_rate)
        if self.model == MODEL_TICK:
            positive("Tick value", self.tick_value)
        if self.max_quantity is not None:
            if _bad(self.max_quantity):
                errors.append("Maximum quantity must be greater than zero (or blank).")
            elif not _bad(self.min_quantity) and self.max_quantity < self.min_quantity:
                errors.append("Maximum quantity cannot be below the minimum quantity.")
        if self.min_notional is None or not self.min_notional.is_finite() or self.min_notional < 0:
            errors.append("Minimum notional cannot be negative.")
        if not self.pnl_currency or not self.pnl_currency.strip():
            errors.append("P&L currency is required.")
        if self.leverage is not None and _bad(self.leverage):
            errors.append("Leverage must be greater than zero (or blank).")
        if self.margin_rate is not None and (
            not self.margin_rate.is_finite() or not (0 < self.margin_rate <= 1)
        ):
            errors.append("Margin rate must be between 0 and 1 (or blank).")
        return errors
