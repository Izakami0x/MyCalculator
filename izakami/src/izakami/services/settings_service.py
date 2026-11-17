"""Typed access to persisted settings with safe defaults."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Union

from ..core.validation import ValidationError, format_plain, parse_decimal
from ..database.repositories import SettingsRepository
from ..models.account import AccountSettings, RiskMode

log = logging.getLogger("izakami.settings")

DEFAULT_SHORTCUTS = {
    "shortcut_entry": "Ctrl+Shift+E",
    "shortcut_stop": "Ctrl+Shift+S",
    "shortcut_copy": "Ctrl+Shift+C",
}

DEFAULTS: dict[str, str] = {
    "account_balance": "10000",
    "account_currency": "USD",
    "risk_mode": "percent",
    "risk_percent": "1",
    "risk_fixed": "100",
    "rr": "2",
    "default_leverage": "10",
    "theme": "dark",
    "always_on_top": "1",
    "selected_instrument": "BTCUSDT",
    "window_geometry": "",
    "start_minimized": "0",
    "launch_at_login": "0",
    "restore_clipboard": "1",
    "api_enabled": "0",
    "presets_seeded": "0",
    **DEFAULT_SHORTCUTS,
}


class SettingsService:
    def __init__(self, repo: SettingsRepository) -> None:
        self._repo = repo
        self._cache: dict[str, str] = {**DEFAULTS, **repo.get_all()}

    def get(self, key: str) -> str:
        return self._cache.get(key, DEFAULTS.get(key, ""))

    def set(self, key: str, value: Union[str, bool, int, Decimal]) -> None:
        if isinstance(value, bool):
            text = "1" if value else "0"
        elif isinstance(value, Decimal):
            text = format_plain(value)
        else:
            text = str(value)
        self._repo.set(key, text)
        self._cache[key] = text

    def get_bool(self, key: str) -> bool:
        return self.get(key) in ("1", "true", "True")

    def get_decimal(self, key: str) -> Decimal:
        try:
            value = parse_decimal(self.get(key), key)
            if value > 0:
                return value
        except ValidationError:
            pass
        log.warning("Setting %s is invalid (%r); using default.", key, self.get(key))
        return Decimal(DEFAULTS[key])

    def account(self) -> AccountSettings:
        try:
            mode = RiskMode(self.get("risk_mode"))
        except ValueError:
            mode = RiskMode.PERCENT
        return AccountSettings(
            balance=self.get_decimal("account_balance"),
            currency=(self.get("account_currency") or "USD").strip().upper(),
            risk_mode=mode,
            risk_percent=self.get_decimal("risk_percent"),
            risk_fixed=self.get_decimal("risk_fixed"),
            rr=self.get_decimal("rr"),
            leverage=self.get_decimal("default_leverage"),
        )

    def shortcuts(self) -> dict[str, str]:
        return {k: self.get(k) for k in DEFAULT_SHORTCUTS}
