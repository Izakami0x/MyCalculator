"""Optional data-provider interface. No providers ship with this version.

Providers are adapters that live OUTSIDE the calculation engine: the engine only ever sees plain
values (an instrument specification or an ExternalRate), never a network client. Providers must be
disabled by default, must never block the calculator, and must never silently overwrite
user-defined specifications.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..core.currency_conversion import ExternalRate
from ..models.instrument import Instrument


class DataProvider(ABC):
    name: str = "provider"

    @abstractmethod
    def fetch_conversion_rate(self, from_currency: str, to_currency: str) -> Optional[ExternalRate]:
        """Return a timestamped rate, or None when unavailable."""

    def fetch_instrument(self, symbol: str) -> Optional[Instrument]:
        """Return suggested specifications for review (never applied automatically)."""
        return None
