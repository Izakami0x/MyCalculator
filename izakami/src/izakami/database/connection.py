"""SQLite connection factory."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


def connect(path: Union[str, Path]) -> sqlite3.Connection:
    """Open a connection in autocommit mode (transactions are explicit where needed)."""
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
