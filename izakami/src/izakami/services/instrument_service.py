"""Business rules around instruments: validation, presets, safe deletion."""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ..database.presets import starter_presets
from ..database.repositories import DuplicateInstrumentError, InstrumentRepository
from ..models.instrument import Instrument
from .settings_service import SettingsService


class InstrumentError(Exception):
    """One or more problems with an instrument; ``messages`` are user-friendly."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages


class InstrumentService:
    def __init__(self, repo: InstrumentRepository, settings: SettingsService) -> None:
        self._repo = repo
        self._settings = settings

    # -- presets -------------------------------------------------------------------------
    def seed_presets_if_needed(self) -> None:
        """Seed once. Presets a user deleted are not resurrected on the next start."""
        if self._settings.get_bool("presets_seeded"):
            return
        self.restore_presets()
        self._settings.set("presets_seeded", True)

    def restore_presets(self) -> int:
        added = 0
        for preset in starter_presets():
            if self._repo.get_by_symbol(preset.symbol) is None:
                self._repo.add(preset)
                added += 1
        return added

    # -- queries ---------------------------------------------------------------------------
    def list(self, search: str = "") -> list[Instrument]:
        return self._repo.list(search)

    def get(self, symbol: str) -> Optional[Instrument]:
        return self._repo.get_by_symbol(symbol)

    def selected(self) -> Optional[Instrument]:
        """The selected instrument; falls back to the first available one if it was deleted."""
        chosen = self._repo.get_by_symbol(self._settings.get("selected_instrument"))
        if chosen is not None:
            return chosen
        items = self._repo.list()
        if not items:
            return None
        self._settings.set("selected_instrument", items[0].symbol)
        return items[0]

    # -- mutations -------------------------------------------------------------------------
    def save(self, inst: Instrument) -> Instrument:
        inst = replace(inst, symbol=inst.symbol.strip().upper())
        problems = inst.validate()
        if problems:
            raise InstrumentError(problems)
        try:
            return self._repo.update(inst) if inst.id is not None else self._repo.add(inst)
        except DuplicateInstrumentError:
            raise InstrumentError([f"An instrument named {inst.symbol} already exists."]) from None

    def duplicate(self, inst: Instrument) -> Instrument:
        base = f"{inst.symbol}_COPY"
        symbol, n = base, 2
        while self._repo.get_by_symbol(symbol) is not None:
            symbol, n = f"{base}{n}", n + 1
        return self.save(replace(inst, id=None, symbol=symbol, is_preset=False))

    def delete(self, instrument_id: int) -> bool:
        removed = self._repo.delete(instrument_id)
        self.selected()  # repairs the stored selection if it pointed at the deleted instrument
        return removed
