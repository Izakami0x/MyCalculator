"""The floating calculator window."""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap, QGuiApplication
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSizeGrip, QToolButton, QVBoxLayout, QWidget)

from ..context import AppContext
from ..models.account import RiskMode
from ..models.calculation_result import CalculationResult, Direction
from ..models.instrument import Instrument, decimals_of
from ..services.clipboard_service import KIND_ENTRY, KIND_STOP, CaptureOutcome
from ..services.hotkey_service import (ACTION_COPY, ACTION_ENTRY, ACTION_SETTING_KEYS, ACTION_STOP)
from .components import (DragHeader, Field, LogoWidget, Stat, StatusLine, make_rule, repolish)
from .format import fmt_money, fmt_price, fmt_qty, format_plain, qty_text
from .themes import build_stylesheet, palette

log = logging.getLogger("izakami.ui")
from decimal import Decimal  # noqa: E402


class MainWindow(QWidget):
    capture_done = Signal(object)
    hotkey_fired = Signal(str)
    DEFAULT_SIZE = (600, 650)

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._instruments: dict[str, Instrument] = {}
        self._result: Optional[CalculationResult] = None
        self._result_inst: Optional[Instrument] = None
        self._loading = False
        self._last_copy = 0.0
        self._always_on_top = False
        from .success_toast import SuccessToast
        self._success_toast = SuccessToast(self)
        self._currency = "USD"
        self._risk_mode = RiskMode.PERCENT

        self.setObjectName("Root")
        self.setWindowTitle("Izakami Risk Calculator")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(500, 570)

        self._geo_timer = QTimer(self)
        self._geo_timer.setSingleShot(True)
        self._geo_timer.setInterval(500)
        self._geo_timer.timeout.connect(self._save_geometry)

        self._build_ui()
        self.apply_theme(ctx.settings.get("theme"))
        self._load_from_settings()
        self._restore_geometry()
        self.set_always_on_top(ctx.settings.get_bool("always_on_top"))

        self.capture_done.connect(self._on_capture_done)
        self.hotkey_fired.connect(self._on_hotkey)
        ctx.hotkeys.on_trigger = self.hotkey_fired.emit
        if ctx.capture is not None:
            ctx.capture.on_done = self.capture_done.emit
        self.recalculate()

    # ------------------------------------------------------------------ construction
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame()
        self.card.setObjectName("Card")
        outer.addWidget(self.card)
        root = QVBoxLayout(self.card)
        root.setContentsMargins(20, 16, 20, 10)
        root.setSpacing(10)

        # Header ---------------------------------------------------------------
        header = DragHeader()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)
        self.logo = LogoWidget()
        hl.addWidget(self.logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        word = QLabel("IZAKAMI")
        word.setObjectName("Wordmark")
        font = word.font()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 4)
        word.setFont(font)
        sub = QLabel("RISK CALCULATOR")
        sub.setObjectName("Subtitle")
        sfont = sub.font()
        sfont.setLetterSpacing(sfont.SpacingType.AbsoluteSpacing, 2)
        sub.setFont(sfont)
        titles.addWidget(word)
        titles.addWidget(sub)
        title_box = QWidget()
        title_box.setLayout(titles)
        title_box.setMinimumWidth(130)
        hl.addWidget(title_box)
        hl.addStretch(1)
        self.aot_btn = QToolButton()
        self.aot_btn.setIconSize(QPixmap(20, 20).size())
        self.aot_btn.setToolTip("Always on top")
        self.aot_btn.setAccessibleName("Always on top")
        self.aot_btn.setCheckable(True)
        self.aot_btn.setProperty("role", "pin")
        self.aot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aot_btn.toggled.connect(self._on_aot_toggled)
        hl.addWidget(self.aot_btn)
        self.theme_btn = self._tool_button("☀", "Switch theme", self.toggle_theme)
        self.settings_btn = self._tool_button("⚙", "Settings", self.open_settings)
        self.min_btn = self._tool_button("—", "Minimize", self.showMinimized)
        self.close_btn = self._tool_button("✕", "Close", self.close)
        for button in (self.theme_btn, self.settings_btn, self.min_btn, self.close_btn):
            hl.addWidget(button)
        root.addWidget(header)
        root.addWidget(make_rule())

        # Account row ------------------------------------------------------------
        account = QHBoxLayout()
        account.setSpacing(10)
        self.balance = Field("Account Balance", step=Decimal(100))
        self.risk = Field("Risk", step=Decimal("0.25"))
        self.mode_btn = QPushButton("%")
        self.mode_btn.setProperty("role", "mode")
        self.mode_btn.setToolTip("Switch between percentage risk and a fixed amount")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.clicked.connect(self._toggle_risk_mode)
        self.risk.suffix.hide()
        self.risk.row.addWidget(self.mode_btn)
        self.rr = Field("RR", suffix="R", step=Decimal("0.5"))
        account.addWidget(self.balance, 5)
        account.addWidget(self.risk, 3)
        account.addWidget(self.rr, 2)
        root.addLayout(account)
        root.addWidget(make_rule())

        # Instrument + direction ---------------------------------------------------
        inst_row = QHBoxLayout()
        inst_row.setSpacing(14)
        inst_box = QVBoxLayout()
        inst_box.setSpacing(2)
        cap_row = QHBoxLayout()
        cap = QLabel("Instrument")
        cap.setProperty("role", "caption")
        cap_row.addWidget(cap)
        cap_row.addStretch(1)
        self.manage_btn = QPushButton("Manage")
        self.manage_btn.setProperty("role", "link")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.clicked.connect(self.open_instrument_manager)
        cap_row.addWidget(self.manage_btn)
        inst_box.addLayout(cap_row)
        self.instrument_combo = QComboBox()
        self.instrument_combo.setMinimumContentsLength(9)
        self.instrument_combo.currentIndexChanged.connect(self._on_instrument_changed)
        combo_row = QHBoxLayout()
        combo_row.addWidget(self.instrument_combo)
        arrow = QLabel("▾")
        arrow.setProperty("role", "suffix")
        combo_row.addWidget(arrow)
        combo_row.addStretch(1)
        inst_box.addLayout(combo_row)
        inst_row.addLayout(inst_box, 3)
        inst_row.addWidget(make_rule(vertical=True))
        dir_box = QVBoxLayout()
        dir_cap = QLabel("Direction (auto)")
        dir_cap.setProperty("role", "caption")
        self.direction_pill = QLabel("—")
        self.direction_pill.setProperty("role", "pill")
        self.direction_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dir_box.addWidget(dir_cap)
        dir_box.addWidget(self.direction_pill)
        inst_row.addLayout(dir_box, 2)
        root.addLayout(inst_row)
        root.addWidget(make_rule())

        # Prices -------------------------------------------------------------------
        prices = QHBoxLayout()
        prices.setSpacing(10)
        self.entry = Field("Entry Price", hint="Ctrl+Shift+E", placeholder="0.00")
        self.stop = Field("Stop Loss", hint="Ctrl+Shift+S", placeholder="0.00")
        self.tp = Field("Take Profit", readonly=True)
        prices.addWidget(self.entry)
        prices.addWidget(self.stop)
        prices.addWidget(self.tp)
        root.addLayout(prices)
        info = QHBoxLayout()
        self.risk_amount = Stat("Risk Amount")
        self.risk_distance = Stat("Leverage")
        info.addWidget(self.risk_amount)
        info.addWidget(self.risk_distance)
        info.addStretch(1)
        root.addLayout(info)

        # Results ------------------------------------------------------------------
        results = QFrame()
        results.setObjectName("Results")
        rl = QHBoxLayout(results)
        rl.setContentsMargins(8, 10, 16, 10)
        rl.setSpacing(0)
        self.accent = QFrame()
        self.accent.setObjectName("Accent")
        self.accent.setFixedWidth(4)
        rl.addWidget(self.accent)
        left = QVBoxLayout()
        left.setContentsMargins(16, 0, 14, 0)
        left_cap = QLabel("Position Size")
        left_cap.setProperty("role", "caption")
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        self.size_value = QLabel("—")
        self.size_value.setProperty("role", "big")
        self.size_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.size_unit = QLabel("")
        self.size_unit.setProperty("role", "bigunit")
        size_row.addWidget(self.size_value)
        size_row.addWidget(self.size_unit, 0, Qt.AlignmentFlag.AlignBottom)
        size_row.addStretch(1)
        left.addWidget(left_cap)
        left.addLayout(size_row)
        rl.addLayout(left, 5)
        rl.addWidget(make_rule(vertical=True))
        mid = QVBoxLayout()
        mid.setContentsMargins(14, 0, 14, 0)
        self.position_value = Stat("Position Value")
        self.margin = Stat("Est. Required Margin")
        mid.addWidget(self.position_value)
        mid.addWidget(self.margin)
        rl.addLayout(mid, 4)
        rl.addWidget(make_rule(vertical=True))
        right = QVBoxLayout()
        right.setContentsMargins(14, 0, 0, 0)
        self.loss = Stat("Potential Loss")
        self.profit = Stat("Potential Profit")
        right.addWidget(self.loss)
        right.addWidget(self.profit)
        rl.addLayout(right, 4)
        root.addWidget(results)

        # Actions --------------------------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.copy_btn = QPushButton("⧉  Copy Position Size")
        self.copy_btn.setProperty("role", "primary")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_position_size)
        self.copy_hint = QLabel("")
        self.copy_hint.setProperty("role", "hint")
        self.reset_btn = QPushButton("↻  Reset")
        self.reset_btn.setToolTip("Clear Entry and Stop Loss")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_prices)
        actions.addWidget(self.copy_btn)
        actions.addWidget(self.copy_hint)
        actions.addStretch(1)
        actions.addWidget(self.reset_btn)
        root.addLayout(actions)
        root.addWidget(make_rule())

        footer = QHBoxLayout()
        self.status = StatusLine()
        footer.addWidget(self.status, 1)
        grip = QSizeGrip(self)
        footer.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        root.addLayout(footer)

        for field in (self.balance, self.risk, self.rr, self.entry, self.stop):
            field.edit.textChanged.connect(self.recalculate)
        for field in (self.balance, self.risk, self.rr):
            field.edit.editingFinished.connect(self._save_account_fields)

    @staticmethod
    def _tool_button(glyph: str, tip: str, slot) -> QToolButton:
        button = QToolButton()
        button.setText(glyph)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _refresh_pin_icon(self) -> None:
        """Draw a small pin glyph using the active theme's muted/accent color."""
        name = self.ctx.settings.get("theme")
        color = palette(name)["accent"] if self._always_on_top else palette(name)["muted"]
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        pin = QPainterPath()
        pin.moveTo(10, 1)
        pin.cubicTo(5.5, 1, 3, 4.2, 3, 8)
        pin.cubicTo(3, 11, 6.2, 13.5, 8.2, 15.2)
        pin.lineTo(10, 19)
        pin.lineTo(11.8, 15.2)
        pin.cubicTo(13.8, 13.5, 17, 11, 17, 8)
        pin.cubicTo(17, 4.2, 14.5, 1, 10, 1)
        pin.closeSubpath()
        painter.drawPath(pin)
        painter.end()
        self.aot_btn.setIcon(QIcon(pixmap))

    # ------------------------------------------------------------------ settings <-> UI
    def _load_from_settings(self) -> None:
        self._loading = True
        try:
            acc = self.ctx.settings.account()
            self._currency = acc.currency
            self._risk_mode = acc.risk_mode
            self.balance.set_text(format_plain(acc.balance))
            self.balance.set_suffix(acc.currency)
            self.rr.set_text(format_plain(acc.rr))
            self._sync_risk_field()
            self._populate_instruments(self.ctx.settings.get("selected_instrument"))
            self._update_hints()
        finally:
            self._loading = False
        self.recalculate()

    def _sync_risk_field(self) -> None:
        acc = self.ctx.settings.account()
        if self._risk_mode is RiskMode.PERCENT:
            self.risk.caption.setText("Risk (% of balance)")
            self.risk.set_text(format_plain(acc.risk_percent))
            self.mode_btn.setText("%")
        else:
            self.risk.caption.setText(f"Risk (fixed, {self._currency})")
            self.risk.set_text(format_plain(acc.risk_fixed))
            self.mode_btn.setText(self._currency)

    def _update_hints(self) -> None:
        sc = self.ctx.settings.shortcuts()
        self.entry.hint.setText(sc["shortcut_entry"])
        self.stop.hint.setText(sc["shortcut_stop"])
        self.copy_hint.setText(sc["shortcut_copy"])

    def _save_account_fields(self) -> None:
        from ..core.validation import ValidationError, parse_decimal

        s = self.ctx.settings
        try:
            balance = parse_decimal(self.balance.text(), "balance")
            risk = parse_decimal(self.risk.text(), "risk")
            rr = parse_decimal(self.rr.text(), "rr")
        except ValidationError:
            return  # invalid text is reported by recalculate(); never persist it
        if balance > 0:
            s.set("account_balance", balance)
        if risk > 0:
            s.set("risk_percent" if self._risk_mode is RiskMode.PERCENT else "risk_fixed", risk)
        if rr > 0:
            s.set("rr", rr)

    def _toggle_risk_mode(self) -> None:
        self._save_account_fields()
        self._risk_mode = RiskMode.FIXED if self._risk_mode is RiskMode.PERCENT else RiskMode.PERCENT
        self.ctx.settings.set("risk_mode", self._risk_mode.value)
        self._loading = True
        self._sync_risk_field()
        self._loading = False
        self.recalculate()

    # ------------------------------------------------------------------ instruments
    def _populate_instruments(self, select: str = "") -> None:
        items = self.ctx.instruments.list()
        self._instruments = {i.symbol: i for i in items}
        self.instrument_combo.blockSignals(True)
        self.instrument_combo.clear()
        self.instrument_combo.addItems([i.symbol for i in items])
        index = self.instrument_combo.findText(select) if select else -1
        if index < 0 and items:
            index = 0
        self.instrument_combo.setCurrentIndex(index)
        self.instrument_combo.blockSignals(False)
        current = self.current_instrument()
        if current is not None:
            self.ctx.settings.set("selected_instrument", current.symbol)
        self._apply_price_steps()

    def current_instrument(self) -> Optional[Instrument]:
        return self._instruments.get(self.instrument_combo.currentText())

    def _apply_price_steps(self) -> None:
        inst = self.current_instrument()
        if inst is not None:
            step = inst.tick_size * 10
            self.entry.edit.step = step
            self.stop.edit.step = step

    def _on_instrument_changed(self) -> None:
        inst = self.current_instrument()
        if inst is not None:
            self.ctx.settings.set("selected_instrument", inst.symbol)
        self._apply_price_steps()
        self.recalculate()

    # ------------------------------------------------------------------ calculation
    def recalculate(self) -> None:
        if self._loading:
            return
        inst = self.current_instrument()
        if inst is None:
            self._result, self._result_inst = None, None
            self._clear_numbers()
            self._set_direction(None)
            self.status.set_status("error", "No instruments available. Click Manage to add one.")
            return
        result = self.ctx.calc.calculate_from_text(
            balance_text=self.balance.text(), risk_text=self.risk.text(), rr_text=self.rr.text(),
            entry_text=self.entry.text(), stop_text=self.stop.text(), instrument=inst,
            currency=self._currency, risk_mode=self._risk_mode,
            default_leverage=self.ctx.settings.get_decimal("default_leverage"),
        )
        self._result, self._result_inst = result, inst
        self._render(result, inst)

    def _clear_numbers(self) -> None:
        self.size_value.setText("—")
        for stat in (self.position_value, self.margin, self.risk_amount):
            stat.set_value("—")
        self.risk_distance.set_value("—")
        self.loss.set_value("—")
        self.profit.set_value("—")
        self.tp.set_text("")

    def _set_direction(self, direction: Optional[Direction]) -> None:
        tone = {Direction.LONG: "long", Direction.SHORT: "short"}.get(direction, "")
        label = {"long": "▲  LONG", "short": "▼  SHORT"}.get(tone, "—")
        if self.direction_pill.text() != label:
            self.direction_pill.setText(label)
        if self.direction_pill.property("direction") != tone:
            self.direction_pill.setProperty("direction", tone)
            repolish(self.direction_pill)
        if self.accent.property("tone") != tone:
            self.accent.setProperty("tone", tone)
            repolish(self.accent)

    def _render(self, r: Optional[CalculationResult], inst: Instrument) -> None:
        cur = self._currency
        self.size_unit.setText(inst.quantity_unit)
        if r is None:
            self._clear_numbers()
            self._set_direction(None)
            self.status.set_status("info", "Enter Entry and Stop Loss to calculate.")
            return
        self._set_direction(r.direction)
        if not r.ok:
            self._clear_numbers()
            if r.risk_amount is not None:
                self.risk_amount.set_value(f"{fmt_money(r.risk_amount)} {cur}")
            self.status.set_status("error", r.errors[0], "\n".join(r.errors))
            return
        if r.risk_amount is not None:
            self.risk_amount.set_value(f"{fmt_money(r.risk_amount)} {cur}")
        configured_leverage = inst.leverage if inst.leverage is not None else self.ctx.settings.get_decimal("default_leverage")
        self.risk_distance.set_value(f"{format_plain(configured_leverage)}x")
        assert r.quantity is not None and r.notional is not None and r.margin is not None
        assert r.potential_loss is not None and r.potential_profit is not None and r.take_profit is not None
        self.size_value.setText(fmt_qty(r.quantity, inst.quantity_decimals))
        self.position_value.set_value(f"{fmt_money(r.notional)} {cur}")
        self.margin.set_value(f"≈ {fmt_money(r.margin)} {cur}")
        if r.recommended_leverage is not None:
            suggested = r.recommended_leverage.quantize(Decimal("0.01"), rounding="ROUND_CEILING")
            self.risk_distance.set_value(f"{format_plain(suggested)}x suggested")
        self.loss.set_value(f"-{fmt_money(r.potential_loss)} {cur}", "loss")
        self.profit.set_value(f"+{fmt_money(r.potential_profit)} {cur}", "profit")
        self.tp.set_text(fmt_price(r.take_profit, inst.price_decimals))
        rr_text = format_plain(r.rr) if r.rr is not None else "?"
        line = f"Ready • {inst.symbol} • {r.direction.value.title() if r.direction else ''} • 1:{rr_text} RR"
        if r.warnings:
            self.status.set_status("warn", f"{line}  ⚠ {r.warnings[0]}", "\n".join(r.warnings))
        else:
            self.status.set_status("ready", line)

    # ------------------------------------------------------------------ actions
    def reset_prices(self) -> None:
        self._loading = True
        self.entry.set_text("")
        self.stop.set_text("")
        self._loading = False
        self.recalculate()
        self.entry.edit.setFocus()

    def copy_position_size(self) -> None:
        r, inst = self._result, self._result_inst
        if r is None or not r.ok or r.quantity is None or inst is None:
            self.status.set_status("error", "Nothing to copy yet. Fix the inputs first.")
            return
        text = qty_text(r.quantity, inst.quantity_decimals)
        QGuiApplication.clipboard().setText(text)
        self.status.set_status("ready", f"Copied {text} to the clipboard.")
        self._success_toast.show_message("Lot size copied")

    def _on_hotkey(self, action: str) -> None:
        if action == ACTION_COPY:
            now = time.monotonic()
            if now - self._last_copy < 0.25:  # swallow accidental double presses
                return
            self._last_copy = now
            self.copy_position_size()
            return
        kind = KIND_ENTRY if action == ACTION_ENTRY else KIND_STOP if action == ACTION_STOP else None
        if kind is None:
            return
        if self.ctx.capture is None:
            self.status.set_status("error", "Clipboard capture is only available on Windows.")
            return
        if self.ctx.capture.start(kind):
            self.status.set_status("busy", "Capturing from the active application…")

    def _on_capture_done(self, outcome: CaptureOutcome) -> None:
        if not outcome.ok or outcome.value is None:
            self.status.set_status("error", outcome.message)
            return
        field = self.entry if outcome.kind == KIND_ENTRY else self.stop
        field.set_text(format_plain(outcome.value))
        self._success_toast.show_message("Entry price pasted" if outcome.kind == KIND_ENTRY else "Stop Loss pasted")
        if self._result is None or self._result.ok:
            self.status.set_status("ready", outcome.message)

    def apply_hotkeys(self, show_dialog: bool = False) -> None:
        """(Re-)register the global shortcuts and tell the user about any problem."""
        self._update_hints()
        bindings = {action: self.ctx.settings.get(key) for action, key in ACTION_SETTING_KEYS.items()}
        result = self.ctx.hotkeys.apply(bindings)
        if not self.ctx.hotkeys.supported:
            self.status.set_status("info", "Global shortcuts are only available on Windows.")
        elif result.errors:
            message = "\n".join(result.errors.values())
            self.status.set_status("error", next(iter(result.errors.values())), message)
            if show_dialog:
                QMessageBox.warning(self, "Shortcuts", "Some shortcuts are not active:\n\n" + message)

    # ------------------------------------------------------------------ window behaviour
    def apply_theme(self, name: str) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(name))
        self.logo.set_color(palette(name)["text"])
        self.theme_btn.setText("☀" if name == "dark" else "☾")
        self._success_toast.apply_theme(name)
        self._refresh_pin_icon()

    def toggle_theme(self) -> None:
        new = "light" if self.ctx.settings.get("theme") == "dark" else "dark"
        self.ctx.settings.set("theme", new)
        self.apply_theme(new)

    def set_always_on_top(self, on: bool) -> None:
        """Toggle native topmost state without hiding/recreating the Windows window."""
        on = bool(on)
        if on != self._always_on_top:
            try:
                from ..platform.windows.window_effects import set_window_topmost
                applied = set_window_topmost(self, on)
            except (ImportError, OSError, AttributeError):
                applied = False
            if not applied:
                # Non-Windows fallback; native Windows path above avoids Qt's hide/show cycle.
                if self.isVisible():
                    geometry = self.geometry()
                    self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
                    self.show()
                    self.setGeometry(geometry)
                else:
                    self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
            self._always_on_top = on
        self.aot_btn.blockSignals(True)
        self.aot_btn.setChecked(on)
        self.aot_btn.blockSignals(False)
        self.aot_btn.setToolTip("Unpin from top" if on else "Keep on top")
        self._refresh_pin_icon()
        self.aot_btn.setProperty("on", on)
        repolish(self.aot_btn)

    def _on_aot_toggled(self, checked: bool) -> None:
        self.ctx.settings.set("always_on_top", checked)
        self.set_always_on_top(checked)

    def open_settings(self) -> None:
        from .settings_window import SettingsDialog

        dialog = SettingsDialog(self.ctx, self, on_saved=self._after_settings_saved,
                                open_instruments=self.open_instrument_manager)
        dialog.exec()

    def _after_settings_saved(self) -> None:
        self.apply_theme(self.ctx.settings.get("theme"))
        self._load_from_settings()
        self.set_always_on_top(self.ctx.settings.get_bool("always_on_top"))
        self.apply_hotkeys(show_dialog=True)

    def open_instrument_manager(self) -> None:
        from .instrument_manager import InstrumentManager

        dialog = InstrumentManager(self.ctx, self, current_symbol=self.instrument_combo.currentText())
        dialog.exec()
        self._populate_instruments(self.ctx.settings.get("selected_instrument"))
        self.recalculate()

    # -- geometry -------------------------------------------------------------------------
    def _restore_geometry(self) -> None:
        w, h = self.DEFAULT_SIZE
        try:
            x, y, w, h = json.loads(self.ctx.settings.get("window_geometry"))
            rect = QRect(int(x), int(y), max(int(w), 500), max(int(h), 570))
        except (ValueError, TypeError):
            rect = None
        if rect is not None:
            for screen in QGuiApplication.screens():
                overlap = screen.availableGeometry().intersected(rect)
                if overlap.width() >= 80 and overlap.height() >= 40:
                    self.setGeometry(rect)
                    return
        self.resize(w, h)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.center().x() - w // 2, area.center().y() - h // 2)

    def _save_geometry(self) -> None:
        if self.isMinimized() or self.isMaximized():
            return
        g = self.geometry()
        self.ctx.settings.set("window_geometry", json.dumps([g.x(), g.y(), g.width(), g.height()]))

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._geo_timer.start()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._geo_timer.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_account_fields()
        self._save_geometry()
        super().closeEvent(event)
