from dataclasses import replace
from decimal import Decimal as D

import pytest

from izakami.context import create_context
from izakami.models.instrument import Instrument
from izakami.services.instrument_service import InstrumentError


@pytest.fixture
def ctx(tmp_path):
    return create_context(tmp_path / "t.db", use_platform=False)


def test_presets_seeded_once(tmp_path):
    db = tmp_path / "t.db"
    c = create_context(db, use_platform=False)
    n = len(c.instruments.list())
    assert n >= 15
    c.instruments.delete(c.instruments.get("EURUSD").id)
    c.shutdown()
    c2 = create_context(db, use_platform=False)
    assert c2.instruments.get("EURUSD") is None and len(c2.instruments.list()) == n - 1
    assert c2.instruments.restore_presets() == 1 and c2.instruments.get("EURUSD")


def test_add_edit_search(ctx):
    created = ctx.instruments.save(Instrument(symbol="my pair".replace(" ", "x"), quantity_unit="lots"))
    assert created.id and created.symbol == "MYXPAIR"
    edited = ctx.instruments.save(replace(created, contract_size=D("250"), max_quantity=D("9")))
    assert ctx.instruments.get("MYXPAIR").contract_size == D("250") and edited.max_quantity == D("9")
    assert [i.symbol for i in ctx.instruments.list("myx")] == ["MYXPAIR"]
    assert any(i.symbol == "BTCUSDT" for i in ctx.instruments.list("crypto"))


def test_validation_and_duplicates(ctx):
    with pytest.raises(InstrumentError):
        ctx.instruments.save(Instrument(symbol="BAD", quantity_step=D("0")))
    with pytest.raises(InstrumentError):
        ctx.instruments.save(Instrument(symbol="has space"))
    with pytest.raises(InstrumentError) as exc:
        ctx.instruments.save(Instrument(symbol="eurusd"))
    assert "already exists" in exc.value.messages[0]
    with pytest.raises(InstrumentError):
        ctx.instruments.save(Instrument(symbol="TKM", model="tick", tick_value=D("0")))


def test_deleting_selected_instrument_selects_another(ctx):
    ctx.settings.set("selected_instrument", "BTCUSDT")
    ctx.instruments.delete(ctx.instruments.get("BTCUSDT").id)
    sel = ctx.instruments.selected()
    assert sel is not None and sel.symbol != "BTCUSDT"
    assert ctx.settings.get("selected_instrument") == sel.symbol


def test_deleting_everything_is_safe(ctx):
    for inst in ctx.instruments.list():
        ctx.instruments.delete(inst.id)
    assert ctx.instruments.selected() is None


def test_duplicate_instrument(ctx):
    copy = ctx.instruments.duplicate(ctx.instruments.get("XAUUSD"))
    again = ctx.instruments.duplicate(ctx.instruments.get("XAUUSD"))
    assert copy.symbol == "XAUUSD_COPY" and again.symbol == "XAUUSD_COPY2" and not copy.is_preset


def test_decimal_precision_survives_storage(ctx):
    saved = ctx.instruments.save(Instrument(symbol="PREC", tick_size=D("0.00001"), conversion_rate=D("0.0067123")))
    assert ctx.instruments.get("PREC").conversion_rate == D("0.0067123") and saved.tick_size == D("0.00001")
