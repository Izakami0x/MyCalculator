"""Locations of application data (kept outside the installation folder)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Izakami"


def data_dir() -> Path:
    """Return (and create) the per-user data directory."""
    override = os.environ.get("IZAKAMI_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        base = Path(root) / APP_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        base = Path(root) / APP_NAME.lower()
    base.mkdir(parents=True, exist_ok=True)
    return base


def database_path() -> Path:
    return data_dir() / "izakami.db"


def log_path() -> Path:
    return data_dir() / "izakami.log"
