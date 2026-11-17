from decimal import Decimal as D

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from izakami.context import create_context
from izakami.ui.main_window import MainWindow
from izakami.ui.settings_window import SettingsDialog
from izakami.ui.instrument_manager import InstrumentManager


@pytest.fixture
def ctx(tmp_path):
    return create_context(tmp_path / "gui.db", use_platform=False)


@pytest.fixture
def win(qtbot, ctx):
    w = MainWindow(ctx)
    qtbot.addWidget(w)
    w.show()
    return w


def pick(w, symbol):
    w.instrument_combo.setCurrentIndex(w.instrument_combo.findText(symbol))


def test_startup_defaults(win):
    assert win.isVisible() and win.balance.text() == "10000" and win.rr.text() == "2"
    assert win.direction_pill.text() == "—" and "Enter Entry and Stop Loss" in win.status.text.text()
    assert win._always_on_top and win.aot_btn.isChecked()


def test_startup_runs_initial_calculation_once(qtbot, tmp_path):
    ctx = create_context(tmp_path / "startup.db", use_platform=False)
    original = ctx.calc.calculate_from_text
    calls = []

    def counted_calculation(**kwargs):
        calls.append(1)
        return original(**kwargs)

    ctx.calc.calculate_from_text = counted_calculation
    w = MainWindow(ctx)
    qtbot.addWidget(w)
    assert len(calls) == 1


def test_setting_field_to_same_text_does_not_emit_change(win):
    changes = []
    win.entry.edit.textChanged.connect(changes.append)
    win.entry.set_text(win.entry.text())
    assert changes == []


def test_auto_recalculation_and_direction(win):
    pick(win, "BTCUSDT")
    win.balance.set_text("1000")
    win.entry.set_text("95000")
    win.stop.set_text("94500")
    assert win.size_value.text() == "0.020" and "LONG" in win.direction_pill.text()
    assert win.tp.text() == "96,000.00" and win.loss.value.text().startswith("-10.00")
    assert win.profit.value.text().startswith("+20.00")
    win.stop.set_text("95500")  # direction flips automatically
    assert "SHORT" in win.direction_pill.text() and win.direction_pill.property("direction") == "short"
    win.rr.set_text("3")
    assert win.tp.text() == "93,500.00"  # 95000 - 3 x 500


def test_btcusdt_with_forex_prices_shows_visible_calculation_error(win):
    pick(win, "BTCUSDT")
    win.entry.set_text("1.1000")
    win.stop.set_text("1.0950")
    assert win.size_value.text() == "—"
    assert win.status.kind == "error"
    assert win.status.text.property("kind") == "error"
    assert "exceeds the maximum" in win.status.text.text()
    assert "BTCUSDT" in win.status.toolTip() or "BTCUSDT" in win.status.text.text()
    assert win._success_toast.label.text() == "Invalid inputs • BTCUSDT"
    assert win._success_toast.icon_label.text() == "!"
    assert win._success_toast.isVisible()


def test_error_clears_stale_numbers(win):
    pick(win, "EURUSD")
    win.entry.set_text("1.1000")
    win.stop.set_text("1.0950")
    assert win.size_value.text() == "0.20"
    win.stop.set_text("1.1000")
    assert win.size_value.text() == "—" and win.loss.value.text() == "—"
    assert win.status.kind == "error"
    win.stop.set_text("abc")
    assert win.size_value.text() == "—" and win.status.kind == "error"


def test_instrument_selection_changes_result(win):
    win.balance.set_text("10000")
    win.entry.set_text("1.1000")
    win.stop.set_text("1.0950")
    pick(win, "EURUSD")
    assert win.size_value.text() == "0.20" and win.size_unit.text() == "lots"
    pick(win, "XAUUSD")
    # Gold with a 0.005 stop would need 200 lots (> the 50-lot maximum): an error, never a number.
    assert win.size_value.text() == "—" and "exceeds the maximum" in win.status.text.text()
    assert win.ctx.settings.get("selected_instrument") == "XAUUSD"


def test_copy_position_size_copies_only_the_number(win):
    pick(win, "BTCUSDT")
    win.balance.set_text("1000")
    win.entry.set_text("95000")
    win.stop.set_text("94500")
    win.copy_position_size()
    assert QGuiApplication.clipboard().text() == "0.020"
    assert win._success_toast.label.text() == "Lot size copied" and win._success_toast.isVisible()


def test_copy_without_result_reports_error(win):
    QGuiApplication.clipboard().setText("untouched")
    win.copy_position_size()
    assert QGuiApplication.clipboard().text() == "untouched" and win.status.kind == "error"


def test_risk_mode_toggle_and_reset(win):
    win.mode_btn.click()
    assert win.mode_btn.text() == "USD" and win.risk.text() == "100"
    assert win.ctx.settings.get("risk_mode") == "fixed"
    win.entry.set_text("1"); win.stop.set_text("0.9")
    win.reset_prices()
    assert win.entry.text() == "" and win.stop.text() == ""


def test_theme_switching_updates_whole_app_and_persists(win, ctx):
    from PySide6.QtWidgets import QApplication
    assert "#13161b" in QApplication.instance().styleSheet()
    win.toggle_theme()
    assert ctx.settings.get("theme") == "light" and "#f6f7f9" in QApplication.instance().styleSheet()
    win.toggle_theme()
    assert ctx.settings.get("theme") == "dark"


def test_always_on_top_toggle(win, ctx):
    win.aot_btn.click()
    assert not win._always_on_top and not win.aot_btn.isChecked()
    assert not ctx.settings.get_bool("always_on_top")
    win.aot_btn.click()
    assert win._always_on_top and win.aot_btn.isChecked()


def test_account_fields_persist_across_restart(qtbot, tmp_path):
    db = tmp_path / "p.db"
    c1 = create_context(db, use_platform=False)
    w1 = MainWindow(c1)
    qtbot.addWidget(w1)
    w1.balance.set_text("2500"); w1.balance.edit.editingFinished.emit()
    w1.rr.set_text("3"); w1.rr.edit.editingFinished.emit()
    pick(w1, "XAUUSD")
    w1.close()
    c1.shutdown()
    c2 = create_context(db, use_platform=False)
    w2 = MainWindow(c2)
    qtbot.addWidget(w2)
    assert w2.balance.text() == "2500" and w2.rr.text() == "3" and w2.instrument_combo.currentText() == "XAUUSD"


def test_invalid_account_text_is_never_persisted(win, ctx):
    win.balance.set_text("garbage")
    win.balance.edit.editingFinished.emit()
    assert ctx.settings.get("account_balance") == "10000" and win.status.kind == "error"


def test_capture_outcome_fills_field_and_failure_keeps_it(win):
    from izakami.services.clipboard_service import CaptureOutcome
    win.entry.set_text("100")
    win._on_capture_done(CaptureOutcome("entry", False, "nope"))
    assert win.entry.text() == "100" and win.status.kind == "error"
    assert not win._success_toast.isVisible()
    win._on_capture_done(CaptureOutcome("entry", True, "Entry captured: 95000.5", D("95000.5")))
    assert win.entry.text() == "95000.5"
    assert win._success_toast.label.text() == "Entry price pasted" and win._success_toast.isVisible()


def test_deleting_selected_instrument_updates_combo(win, ctx):
    pick(win, "BTCUSDT")
    ctx.instruments.delete(ctx.instruments.get("BTCUSDT").id)
    win._populate_instruments(ctx.settings.get("selected_instrument"))
    assert win.instrument_combo.findText("BTCUSDT") == -1 and win.current_instrument() is not None


def test_settings_dialog_saves_and_validates(qtbot, win, ctx):
    saved = []
    dlg = SettingsDialog(ctx, win, on_saved=lambda: saved.append(1))
    qtbot.addWidget(dlg)
    dlg.balance.setText("5000")
    dlg.currency.setCurrentText("EUR")
    dlg.rr.setText("2.5")
    dlg.theme.setCurrentIndex(1)
    dlg._save()
    assert saved and ctx.settings.get("account_balance") == "5000" and ctx.settings.get("account_currency") == "EUR"
    assert ctx.settings.get("theme") == "light" and ctx.settings.get("rr") == "2.5"


def test_settings_dialog_rejects_bad_values(qtbot, win, ctx, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    dlg = SettingsDialog(ctx, win)
    qtbot.addWidget(dlg)
    dlg.balance.setText("-5")
    dlg.risk_percent.setText("150")
    dlg._save()
    assert ctx.settings.get("account_balance") == "10000" and "Account balance" in dlg.general_error.text()


def test_instrument_manager_create_edit_delete(qtbot, win, ctx, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    mgr = InstrumentManager(ctx, win, current_symbol="EURUSD")
    qtbot.addWidget(mgr)
    mgr._new()
    mgr.symbol.setText("MYCFD")
    mgr.pnl_currency.setText("USD")
    mgr.numeric["quantity_step"].setText("0.1")
    mgr.numeric["min_quantity"].setText("0.1")
    mgr.numeric["contract_size"].setText("10")
    mgr._save()
    created = ctx.instruments.get("MYCFD")
    assert created is not None and created.contract_size == D("10") and created.max_quantity is None
    mgr.numeric["contract_size"].setText("20")
    mgr._save()
    assert ctx.instruments.get("MYCFD").contract_size == D("20")
    mgr.numeric["tick_size"].setText("0")
    mgr._save()
    assert "Tick size" in mgr.message.text() and ctx.instruments.get("MYCFD").tick_size != D("0")
    mgr._refresh_list(select="MYCFD")
    mgr._delete()
    assert ctx.instruments.get("MYCFD") is None
