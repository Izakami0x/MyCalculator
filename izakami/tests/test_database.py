import sqlite3
from decimal import Decimal as D

import pytest

from izakami.context import create_context
from izakami.database.connection import connect
from izakami.database.migrations import LATEST_VERSION, MigrationError, current_version, migrate
from izakami.database.repositories import InstrumentRepository, SettingsRepository
from izakami.models.instrument import Instrument


def test_settings_persist_across_restart(tmp_path):
    db = tmp_path / "t.db"
    ctx = create_context(db, use_platform=False)
    ctx.settings.set("account_balance", D("2500.50"))
    ctx.settings.set("theme", "light")
    ctx.settings.set("always_on_top", False)
    ctx.shutdown()
    again = create_context(db, use_platform=False)
    assert again.settings.get_decimal("account_balance") == D("2500.50")
    assert again.settings.get("theme") == "light" and not again.settings.get_bool("always_on_top")
    assert again.settings.get("shortcut_entry") == "Ctrl+Shift+E"  # untouched defaults


def test_corrupt_setting_falls_back_to_default(tmp_path):
    ctx = create_context(tmp_path / "t.db", use_platform=False)
    ctx.settings.set("rr", "not-a-number")
    assert ctx.settings.get_decimal("rr") == D("2")


def test_migrations_stepwise_and_data_preserved():
    conn = connect(":memory:")
    assert migrate(conn, target=1) == 1 and current_version(conn) == 1
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='broker_profiles'").fetchone() is None
    InstrumentRepository(conn).add(Instrument(symbol="KEEPME"))
    assert migrate(conn) == LATEST_VERSION
    assert InstrumentRepository(conn).get_by_symbol("KEEPME") is not None
    assert conn.execute("SELECT id FROM broker_profiles").fetchone()["id"] == "default"
    assert migrate(conn) == LATEST_VERSION  # idempotent


def test_failed_migration_rolls_back():
    conn = connect(":memory:")

    def good(c): c.execute("CREATE TABLE a (x)")
    def bad(c):
        c.execute("CREATE TABLE b (x)")
        raise RuntimeError("boom")

    with pytest.raises(MigrationError):
        migrate(conn, [(1, good), (2, bad)])
    assert current_version(conn) == 1
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='b'").fetchone() is None


def test_newer_database_is_refused():
    conn = connect(":memory:")
    conn.execute("PRAGMA user_version = 99")
    with pytest.raises(MigrationError):
        migrate(conn)


def test_settings_repository_upsert():
    conn = connect(":memory:")
    migrate(conn)
    repo = SettingsRepository(conn)
    repo.set("k", "1"); repo.set("k", "2")
    assert repo.get_all() == {"k": "2"}
