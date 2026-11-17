"""Thin data-access layer. Decimals are stored as TEXT so no precision is ever lost."""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from typing import Optional

from ..models.instrument import DEFAULT_BROKER, Instrument


class DuplicateInstrumentError(Exception):
    """An instrument with the same symbol already exists for that broker profile."""


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_all(self) -> dict[str, str]:
        return {r["key"]: r["value"] for r in self._conn.execute("SELECT key, value FROM settings")}

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


_COLUMNS = (
    "broker_id", "symbol", "asset_class", "model", "contract_size", "tick_size", "tick_value",
    "quantity_step", "min_quantity", "max_quantity", "min_notional", "pnl_currency",
    "conversion_rate", "quantity_unit", "leverage", "margin_rate", "is_preset",
)


def _opt(value: Optional[str]) -> Optional[Decimal]:
    return None if value is None else Decimal(value)


def _to_instrument(row: sqlite3.Row) -> Instrument:
    return Instrument(
        id=row["id"],
        broker_id=row["broker_id"],
        symbol=row["symbol"],
        asset_class=row["asset_class"],
        model=row["model"],
        contract_size=Decimal(row["contract_size"]),
        tick_size=Decimal(row["tick_size"]),
        tick_value=Decimal(row["tick_value"]),
        quantity_step=Decimal(row["quantity_step"]),
        min_quantity=Decimal(row["min_quantity"]),
        max_quantity=_opt(row["max_quantity"]),
        min_notional=Decimal(row["min_notional"]),
        pnl_currency=row["pnl_currency"],
        conversion_rate=Decimal(row["conversion_rate"]),
        quantity_unit=row["quantity_unit"],
        leverage=_opt(row["leverage"]),
        margin_rate=_opt(row["margin_rate"]),
        is_preset=bool(row["is_preset"]),
    )


def _values(i: Instrument) -> tuple:
    def opt(v: Optional[Decimal]) -> Optional[str]:
        return None if v is None else str(v)

    return (
        i.broker_id, i.symbol, i.asset_class, i.model, str(i.contract_size), str(i.tick_size),
        str(i.tick_value), str(i.quantity_step), str(i.min_quantity), opt(i.max_quantity),
        str(i.min_notional), i.pnl_currency, str(i.conversion_rate), i.quantity_unit,
        opt(i.leverage), opt(i.margin_rate), 1 if i.is_preset else 0,
    )


class InstrumentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list(self, search: str = "", broker_id: str = DEFAULT_BROKER) -> list[Instrument]:
        sql = "SELECT * FROM instruments WHERE broker_id = ?"
        args: list[object] = [broker_id]
        if search.strip():
            sql += " AND (instr(upper(symbol), upper(?)) > 0 OR instr(upper(asset_class), upper(?)) > 0)"
            args += [search.strip(), search.strip()]
        sql += " ORDER BY id"
        return [_to_instrument(r) for r in self._conn.execute(sql, args)]

    def get(self, instrument_id: int) -> Optional[Instrument]:
        row = self._conn.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
        return _to_instrument(row) if row else None

    def get_by_symbol(self, symbol: str, broker_id: str = DEFAULT_BROKER) -> Optional[Instrument]:
        row = self._conn.execute(
            "SELECT * FROM instruments WHERE broker_id = ? AND symbol = ?", (broker_id, symbol)
        ).fetchone()
        return _to_instrument(row) if row else None

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0])

    def add(self, inst: Instrument) -> Instrument:
        placeholders = ", ".join("?" for _ in _COLUMNS)
        try:
            cur = self._conn.execute(
                f"INSERT INTO instruments ({', '.join(_COLUMNS)}) VALUES ({placeholders})", _values(inst)
            )
        except sqlite3.IntegrityError:
            raise DuplicateInstrumentError(inst.symbol) from None
        created = self.get(int(cur.lastrowid))
        assert created is not None
        return created

    def update(self, inst: Instrument) -> Instrument:
        if inst.id is None:
            raise ValueError("Cannot update an instrument without an id.")
        assignments = ", ".join(f"{c} = ?" for c in _COLUMNS)
        try:
            self._conn.execute(
                f"UPDATE instruments SET {assignments} WHERE id = ?", (*_values(inst), inst.id)
            )
        except sqlite3.IntegrityError:
            raise DuplicateInstrumentError(inst.symbol) from None
        updated = self.get(inst.id)
        assert updated is not None
        return updated

    def delete(self, instrument_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM instruments WHERE id = ?", (instrument_id,))
        return cur.rowcount > 0
