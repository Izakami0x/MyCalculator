"""Schema versioning via PRAGMA user_version. Every migration runs in one transaction."""
from __future__ import annotations

import sqlite3
from typing import Callable, Optional, Sequence

Migration = Callable[[sqlite3.Connection], None]


class MigrationError(RuntimeError):
    """The database could not be brought to the required schema version."""


def _v1_initial(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute(
        """CREATE TABLE instruments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broker_id TEXT NOT NULL DEFAULT 'default',
            symbol TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            model TEXT NOT NULL,
            contract_size TEXT NOT NULL,
            tick_size TEXT NOT NULL,
            tick_value TEXT NOT NULL,
            quantity_step TEXT NOT NULL,
            min_quantity TEXT NOT NULL,
            max_quantity TEXT,
            min_notional TEXT NOT NULL DEFAULT '0',
            pnl_currency TEXT NOT NULL,
            conversion_rate TEXT NOT NULL,
            quantity_unit TEXT NOT NULL,
            leverage TEXT,
            margin_rate TEXT,
            is_preset INTEGER NOT NULL DEFAULT 0,
            UNIQUE (broker_id, symbol)
        )"""
    )


def _v2_broker_profiles(conn: sqlite3.Connection) -> None:
    """Prepares for multiple broker profiles; only 'default' is used in this version."""
    conn.execute("CREATE TABLE broker_profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
    conn.execute("INSERT INTO broker_profiles (id, name) VALUES ('default', 'Default')")


MIGRATIONS: list[tuple[int, Migration]] = [(1, _v1_initial), (2, _v2_broker_profiles)]
LATEST_VERSION = MIGRATIONS[-1][0]


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(
    conn: sqlite3.Connection,
    migrations: Sequence[tuple[int, Migration]] = tuple(MIGRATIONS),
    target: Optional[int] = None,
) -> int:
    """Apply pending migrations in order and return the resulting schema version."""
    version = current_version(conn)
    latest = max(v for v, _ in migrations)
    if version > latest:
        raise MigrationError(
            f"The database (schema v{version}) was created by a newer version of Izakami."
        )
    for number, step in sorted(migrations, key=lambda m: m[0]):
        if number <= version:
            continue
        if target is not None and number > target:
            break
        try:
            conn.execute("BEGIN")
            step(conn)
            conn.execute(f"PRAGMA user_version = {int(number)}")
            conn.execute("COMMIT")
        except Exception as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise MigrationError(f"Migration to schema v{number} failed: {exc}") from exc
        version = number
    return version
