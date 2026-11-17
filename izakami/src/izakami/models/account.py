"""Account-level settings used by the calculator."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class RiskMode(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"


@dataclass(frozen=True)
class AccountSettings:
    balance: Decimal
    currency: str
    risk_mode: RiskMode
    risk_percent: Decimal
    risk_fixed: Decimal
    rr: Decimal
    leverage: Decimal

    @property
    def risk_value(self) -> Decimal:
        return self.risk_percent if self.risk_mode is RiskMode.PERCENT else self.risk_fixed
