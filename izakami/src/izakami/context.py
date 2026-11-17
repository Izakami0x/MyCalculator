"""Application wiring: builds every service from a database path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

import sqlite3

from . import platform as platform_adapters
from .database.connection import connect
from .database.migrations import migrate
from .database.repositories import InstrumentRepository, SettingsRepository
from .services.calculation_service import CalculationService
from .services.clipboard_service import CaptureController, ClipboardBackend
from .services.hotkey_service import HotkeyBackend, HotkeyService
from .services.instrument_service import InstrumentService
from .services.settings_service import SettingsService


@dataclass
class AppContext:
    conn: sqlite3.Connection
    settings: SettingsService
    instruments: InstrumentService
    calc: CalculationService
    hotkeys: HotkeyService
    capture: Optional[CaptureController]

    def shutdown(self) -> None:
        self.hotkeys.shutdown()
        try:
            self.conn.close()
        except sqlite3.Error:
            pass


def create_context(
    db_path: Union[str, Path],
    *,
    use_platform: bool = True,
    hotkey_backend_factory: Optional[Callable[[Callable[[str], None]], HotkeyBackend]] = None,
    clipboard_backend: Optional[ClipboardBackend] = None,
) -> AppContext:
    conn = connect(db_path)
    migrate(conn)
    settings = SettingsService(SettingsRepository(conn))
    instruments = InstrumentService(InstrumentRepository(conn), settings)
    instruments.seed_presets_if_needed()
    if use_platform:
        hotkey_backend_factory = hotkey_backend_factory or platform_adapters.create_hotkey_backend
        clipboard_backend = clipboard_backend or platform_adapters.create_clipboard_backend()
    capture = (
        CaptureController(clipboard_backend, lambda: settings.get_bool("restore_clipboard"))
        if clipboard_backend is not None
        else None
    )
    return AppContext(
        conn=conn, settings=settings, instruments=instruments, calc=CalculationService(),
        hotkeys=HotkeyService(hotkey_backend_factory), capture=capture,
    )
