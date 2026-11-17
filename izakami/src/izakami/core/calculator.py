"""Position sizing engine. Independent of the GUI, the database and the network."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Optional

from ..models.account import RiskMode
from ..models.calculation_result import CalculationResult, Direction
from ..models.instrument import Instrument
from .currency_conversion import ConversionError, ExternalRate, resolve_conversion
from .sizing_models import get_model


@dataclass(frozen=True)
class CalcInputs:
    balance: Decimal
    account_currency: str
    risk_mode: RiskMode
    risk_value: Decimal  # percent (0-100) or fixed amount, depending on risk_mode
    rr: Decimal
    entry: Decimal
    stop: Decimal
    instrument: Instrument
    default_leverage: Decimal = Decimal(10)


def _bad(value: Optional[Decimal]) -> bool:
    return value is None or not value.is_finite() or value <= 0


def _short(value: Decimal) -> str:
    try:
        return format(value.quantize(Decimal("0.0001")), "f")
    except Exception:  # extremely large values
        return str(value)


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Round DOWN to a multiple of ``step`` - sizes are never rounded up (risk must not grow)."""
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def calculate(inp: CalcInputs, external_rate: Optional[ExternalRate] = None) -> CalculationResult:
    inst = inp.instrument
    errors: list[str] = []

    if _bad(inp.balance):
        errors.append("Account balance must be greater than zero.")
    if _bad(inp.rr):
        errors.append("Reward-to-risk (RR) must be greater than zero.")
    if _bad(inp.entry):
        errors.append("Entry price must be greater than zero.")
    if _bad(inp.stop):
        errors.append("Stop Loss must be greater than zero.")
    if _bad(inp.risk_value):
        errors.append("Risk must be greater than zero.")
    elif inp.risk_mode is RiskMode.PERCENT and inp.risk_value > 100:
        errors.append("Risk percentage cannot exceed 100%.")
    if _bad(inp.default_leverage):
        errors.append("Default leverage must be greater than zero.")
    errors.extend(inst.validate())
    if errors:
        return CalculationResult.failure(errors)

    if inp.entry == inp.stop:
        return CalculationResult.failure(["Entry and Stop Loss must be different."])

    direction = Direction.LONG if inp.stop < inp.entry else Direction.SHORT
    distance = abs(inp.entry - inp.stop)
    if inp.risk_mode is RiskMode.PERCENT:
        risk_amount = inp.balance * inp.risk_value / Decimal(100)
    else:
        risk_amount = inp.risk_value

    partial = dict(
        direction=direction,
        rr=inp.rr,
        risk_amount=risk_amount,
        risk_distance=distance,
        risk_distance_pct=distance / inp.entry * Decimal(100),
    )
    unit = inst.quantity_unit
    ccy = inp.account_currency

    try:
        conv = resolve_conversion(
            inst.pnl_currency, inp.account_currency, inst.conversion_rate, external_rate
        )
    except ConversionError as exc:
        return CalculationResult.failure([str(exc)], quantity_unit=unit, currency=ccy, **partial)

    model = get_model(inst.model)
    risk_per_unit = model.risk_per_unit(inst, distance, conv.rate)
    if risk_per_unit <= 0:
        return CalculationResult.failure(
            ["Risk per unit is zero; check the instrument specification."],
            quantity_unit=unit, currency=ccy, **partial,
        )

    raw_qty = risk_amount / risk_per_unit
    qty = floor_to_step(raw_qty, inst.quantity_step)

    if qty < inst.min_quantity:
        return CalculationResult.failure(
            [
                f"Calculated size {_short(raw_qty)} {unit} is below the minimum "
                f"{_plain(inst.min_quantity)} {unit}. Increase the risk or widen the stop."
            ],
            raw_quantity=raw_qty, quantity_unit=unit, currency=ccy, **partial,
        )
    if inst.max_quantity is not None and qty > inst.max_quantity:
        return CalculationResult.failure(
            [
                f"Calculated size {_plain(qty)} {unit} exceeds the maximum "
                f"{_plain(inst.max_quantity)} {unit}. Reduce the risk or widen the stop."
            ],
            raw_quantity=raw_qty, quantity_unit=unit, currency=ccy, **partial,
        )

    notional_pnl = model.notional(inst, qty, inp.entry)
    if inst.min_notional > 0 and notional_pnl < inst.min_notional:
        return CalculationResult.failure(
            [
                f"Position value {_short(notional_pnl)} {inst.pnl_currency} is below the minimum "
                f"notional {_plain(inst.min_notional)} {inst.pnl_currency}."
            ],
            raw_quantity=raw_qty, quantity_unit=unit, currency=ccy, **partial,
        )
    notional = notional_pnl * conv.rate

    if inst.margin_rate is not None:
        margin = notional * inst.margin_rate
    else:
        margin = notional / (inst.leverage if inst.leverage is not None else inp.default_leverage)

    # Take-profit: rounded to the tick grid *toward entry* so the target is never overstated.
    if direction is Direction.LONG:
        tp_raw, rounding = inp.entry + distance * inp.rr, ROUND_FLOOR
    else:
        tp_raw, rounding = inp.entry - distance * inp.rr, ROUND_CEILING
    take_profit = (tp_raw / inst.tick_size).to_integral_value(rounding=rounding) * inst.tick_size
    tp_distance = abs(take_profit - inp.entry)

    potential_loss = qty * risk_per_unit
    potential_profit = qty * model.risk_per_unit(inst, tp_distance, conv.rate)

    warnings: list[str] = []
    if not conv.exact:
        warnings.append(conv.note or "Currency conversion is an estimate.")
    if take_profit <= 0:
        warnings.append("Take-profit price is at or below zero; that target is not reachable.")
    if margin > inp.balance:
        warnings.append("Estimated margin exceeds the account balance.")
    if inp.risk_mode is RiskMode.FIXED and risk_amount > inp.balance:
        warnings.append("Fixed risk is larger than the account balance.")

    return CalculationResult(
        ok=True,
        warnings=tuple(warnings),
        take_profit=take_profit,
        raw_quantity=raw_qty,
        quantity=qty,
        notional=notional,
        margin=margin,
        potential_loss=potential_loss,
        potential_profit=potential_profit,
        quantity_unit=unit,
        currency=ccy,
        is_estimate=not conv.exact,
        conversion_note=conv.note,
        **partial,  # type: ignore[arg-type]
    )
