"""Result of one position-size calculation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class CalculationResult:
    """``ok`` is False whenever the position size cannot be trusted.

    On failure ``quantity`` and every number that depends on it is ``None``; only values that are
    still correct on their own (direction, intended risk, distance) may be filled.
    """

    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    direction: Optional[Direction] = None
    rr: Optional[Decimal] = None
    risk_amount: Optional[Decimal] = None
    risk_distance: Optional[Decimal] = None
    risk_distance_pct: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    raw_quantity: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    notional: Optional[Decimal] = None
    margin: Optional[Decimal] = None
    potential_loss: Optional[Decimal] = None
    potential_profit: Optional[Decimal] = None
    quantity_unit: str = ""
    currency: str = ""
    is_estimate: bool = False
    conversion_note: str = ""

    @classmethod
    def failure(
        cls, errors: Sequence[str], warnings: Sequence[str] = (), **partial: object
    ) -> "CalculationResult":
        return cls(ok=False, errors=tuple(errors), warnings=tuple(warnings), **partial)  # type: ignore[arg-type]
