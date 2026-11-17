"""Conversion of instrument P&L currency into the account currency."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

# Dollar-pegged units are treated as interchangeable. Everything else needs an explicit rate.
PEGGED_USD = frozenset({"USD", "USDT", "USDC"})


class ConversionError(ValueError):
    """No trustworthy conversion rate is available."""


@dataclass(frozen=True)
class ExternalRate:
    """A rate supplied by an optional data provider (never required)."""

    rate: Decimal
    fetched_at: datetime
    source: str = "external"


@dataclass(frozen=True)
class ConversionRate:
    rate: Decimal
    exact: bool  # False -> monetary figures are estimates
    note: str = ""


def _valid(rate: Optional[Decimal]) -> bool:
    return rate is not None and rate.is_finite() and rate > 0


def resolve_conversion(
    pnl_currency: str,
    account_currency: str,
    manual_rate: Optional[Decimal],
    external: Optional[ExternalRate] = None,
    *,
    now: Optional[datetime] = None,
    max_age: timedelta = timedelta(hours=24),
) -> ConversionRate:
    """Return the rate that converts 1 unit of ``pnl_currency`` into ``account_currency``."""
    pnl = (pnl_currency or "").strip().upper()
    acct = (account_currency or "").strip().upper()
    if not pnl or not acct:
        raise ConversionError("Currency code is missing.")
    if pnl == acct:
        return ConversionRate(Decimal(1), True)
    if pnl in PEGGED_USD and acct in PEGGED_USD:
        return ConversionRate(Decimal(1), True, f"{pnl} is treated as equal to {acct}.")
    if external is not None and _valid(external.rate):
        current = now or datetime.now(timezone.utc)
        age = current - external.fetched_at
        stamp = external.fetched_at.strftime("%Y-%m-%d %H:%M UTC")
        if age > max_age:
            return ConversionRate(
                external.rate, False,
                f"{pnl}->{acct} rate from {external.source} is stale (fetched {stamp}); risk is an estimate.",
            )
        return ConversionRate(external.rate, True, f"{pnl}->{acct} rate from {external.source} ({stamp}).")
    if not _valid(manual_rate):
        raise ConversionError(
            f"No valid {pnl}->{acct} conversion rate. Set one in the instrument's specifications."
        )
    return ConversionRate(
        manual_rate, False,  # type: ignore[arg-type]
        f"Uses manual {pnl}->{acct} rate {manual_rate:f}; monetary risk is an estimate.",
    )
