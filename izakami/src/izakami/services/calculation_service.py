"""Glue between raw field text and the calculation engine."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from ..core.calculator import CalcInputs, calculate
from ..core.currency_conversion import ExternalRate
from ..core.validation import ValidationError, parse_decimal
from ..models.account import RiskMode
from ..models.calculation_result import CalculationResult
from ..models.instrument import Instrument


class CalculationService:
    def calculate_from_text(
        self,
        *,
        balance_text: str,
        risk_text: str,
        rr_text: str,
        entry_text: str,
        stop_text: str,
        instrument: Instrument,
        currency: str,
        risk_mode: RiskMode,
        default_leverage: Decimal,
        external_rate: Optional[ExternalRate] = None,
    ) -> Optional[CalculationResult]:
        """Return a result, or ``None`` while Entry / Stop Loss are not both filled in yet."""
        errors: list[str] = []

        def parse(text: str, label: str) -> Optional[Decimal]:
            try:
                return parse_decimal(text, label)
            except ValidationError as exc:
                errors.append(str(exc))
                return None

        balance = parse(balance_text, "Account balance")
        risk = parse(risk_text, "Risk")
        rr = parse(rr_text, "RR")
        entry = parse(entry_text, "Entry price") if entry_text.strip() else None
        stop = parse(stop_text, "Stop Loss") if stop_text.strip() else None
        if errors:
            return CalculationResult.failure(errors)
        if entry is None or stop is None:
            return None
        assert balance is not None and risk is not None and rr is not None
        return calculate(
            CalcInputs(
                balance=balance, account_currency=currency, risk_mode=risk_mode, risk_value=risk,
                rr=rr, entry=entry, stop=stop, instrument=instrument, default_leverage=default_leverage,
            ),
            external_rate,
        )
