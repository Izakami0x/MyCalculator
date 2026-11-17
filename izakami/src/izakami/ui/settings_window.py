"""Settings dialog: General, Shortcuts, Instruments, Connectivity."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QKeySequenceEdit, QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget,
                               QVBoxLayout, QWidget)

from .. import platform as platform_adapters
from ..context import AppContext
from ..core.validation import ValidationError, parse_decimal
from ..services.hotkey_service import ACTION_LABELS, ACTION_SETTING_KEYS, validate_bindings
from ..services.settings_service import DEFAULT_SHORTCUTS
from .format import format_plain

CURRENCIES = ["USD", "USDT", "USDC", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "PHP"]


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("role", "note")
    return label


class SettingsDialog(QDialog):
    def __init__(self, ctx: AppContext, parent: Optional[QWidget] = None, *,
                 on_saved: Optional[Callable[[], None]] = None,
                 open_instruments: Optional[Callable[[], None]] = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._on_saved = on_saved
        self._open_instruments = open_instruments
        self.setWindowTitle("Izakami Settings")
        self.setModal(True)
        self.setMinimumWidth(460)

        tabs = QTabWidget()
        tabs.addTab(self._general_tab(), "General")
        tabs.addTab(self._shortcuts_tab(), "Shortcuts")
        tabs.addTab(self._instruments_tab(), "Instruments")
        tabs.addTab(self._connectivity_tab(), "Connectivity")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    # -- tabs ---------------------------------------------------------------------------
    def _general_tab(self) -> QWidget:
        s = self.ctx.settings
        acc = s.account()
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setVerticalSpacing(10)
        self.balance = QLineEdit(format_plain(acc.balance))
        self.currency = QComboBox()
        self.currency.setEditable(True)
        self.currency.addItems(CURRENCIES)
        self.currency.setCurrentText(acc.currency)
        self.risk_mode = QComboBox()
        self.risk_mode.addItem("Percentage of balance", "percent")
        self.risk_mode.addItem("Fixed amount", "fixed")
        self.risk_mode.setCurrentIndex(0 if acc.risk_mode.value == "percent" else 1)
        self.risk_percent = QLineEdit(format_plain(acc.risk_percent))
        self.risk_fixed = QLineEdit(format_plain(acc.risk_fixed))
        self.rr = QLineEdit(format_plain(acc.rr))
        self.leverage = QLineEdit(format_plain(acc.leverage))
        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.theme.setCurrentIndex(0 if s.get("theme") == "dark" else 1)
        self.always_on_top = QCheckBox("Keep the calculator above other windows")
        self.always_on_top.setChecked(s.get_bool("always_on_top"))
        self.start_minimized = QCheckBox("Start minimized")
        self.start_minimized.setChecked(s.get_bool("start_minimized"))
        self.launch_at_login = QCheckBox("Launch when I sign in to Windows")
        self.launch_at_login.setChecked(s.get_bool("launch_at_login"))
        self.restore_clipboard = QCheckBox("Restore my previous clipboard text after capturing a price")
        self.restore_clipboard.setChecked(s.get_bool("restore_clipboard"))
        form.addRow("Account balance", self.balance)
        form.addRow("Account currency", self.currency)
        form.addRow("Risk mode", self.risk_mode)
        form.addRow("Default risk (%)", self.risk_percent)
        form.addRow("Fixed risk amount", self.risk_fixed)
        form.addRow("Reward-to-risk (R)", self.rr)
        form.addRow("Default leverage (x)", self.leverage)
        form.addRow("Theme", self.theme)
        form.addRow("", self.always_on_top)
        form.addRow("", self.start_minimized)
        form.addRow("", self.launch_at_login)
        form.addRow("", self.restore_clipboard)
        self.general_error = QLabel("")
        self.general_error.setProperty("role", "error")
        self.general_error.setWordWrap(True)
        form.addRow("", self.general_error)
        return page

    def _shortcuts_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        self.shortcut_edits: dict[str, QKeySequenceEdit] = {}
        current = self.ctx.settings.shortcuts()
        for action, key in ACTION_SETTING_KEYS.items():
            edit = QKeySequenceEdit(QKeySequence(current[key]))
            if hasattr(edit, "setMaximumSequenceLength"):
                edit.setMaximumSequenceLength(1)
            self.shortcut_edits[action] = edit
            form.addRow(ACTION_LABELS[action], edit)
        layout.addLayout(form)
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset_shortcuts)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addStretch(1)
        layout.addLayout(row)
        self.shortcut_error = QLabel("")
        self.shortcut_error.setProperty("role", "error")
        self.shortcut_error.setWordWrap(True)
        layout.addWidget(self.shortcut_error)
        layout.addWidget(_note(
            "Shortcuts are global and need at least one modifier. A shortcut another program already "
            "owns cannot be registered; Izakami will tell you. Note that a global shortcut takes the "
            "combination away from other applications (for example Ctrl+Shift+C opens browser developer tools)."))
        layout.addStretch(1)
        return page

    def _instruments_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        button = QPushButton("Manage instruments…")
        button.clicked.connect(self._manage_instruments)
        row = QHBoxLayout()
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(_note(
            "Add, edit or delete instruments and their contract specifications. The built-in list is a set "
            "of editable starter presets, not verified broker data."))
        layout.addWidget(_note(
            "Broker profiles: the database already separates instruments by broker profile, but only the "
            "'Default' profile is available in this version."))
        layout.addStretch(1)
        return page

    def _connectivity_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        offline = QCheckBox("Offline-first mode (always on)")
        offline.setChecked(True)
        offline.setEnabled(False)
        self.api_enabled = QCheckBox("Enable optional API integrations")
        self.api_enabled.setChecked(self.ctx.settings.get_bool("api_enabled"))
        layout.addWidget(offline)
        layout.addWidget(self.api_enabled)
        layout.addWidget(_note(
            "Izakami never needs the internet, an account or an API key. No data providers are included in "
            "this version, so enabling this does not contact anything yet. When providers are added they "
            "will stay off by default, show how fresh their data is and never overwrite your specifications."))
        layout.addStretch(1)
        return page

    # -- actions ----------------------------------------------------------------------
    def _manage_instruments(self) -> None:
        if self._open_instruments:
            self._open_instruments()

    def _reset_shortcuts(self) -> None:
        for action, key in ACTION_SETTING_KEYS.items():
            self.shortcut_edits[action].setKeySequence(QKeySequence(DEFAULT_SHORTCUTS[key]))

    def _shortcut_text(self, action: str) -> str:
        return self.shortcut_edits[action].keySequence().toString(QKeySequence.SequenceFormat.PortableText)

    def _save(self) -> None:
        errors: list[str] = []

        def number(edit: QLineEdit, label: str, maximum: Optional[int] = None):
            try:
                value = parse_decimal(edit.text(), label)
            except ValidationError as exc:
                errors.append(str(exc))
                return None
            if value <= 0 or (maximum is not None and value > maximum):
                errors.append(f"{label} must be greater than zero" + (f" and at most {maximum}." if maximum else "."))
                return None
            return value

        balance = number(self.balance, "Account balance")
        percent = number(self.risk_percent, "Default risk (%)", 100)
        fixed = number(self.risk_fixed, "Fixed risk amount")
        rr = number(self.rr, "Reward-to-risk")
        leverage = number(self.leverage, "Default leverage")
        currency = self.currency.currentText().strip().upper()
        if not (2 <= len(currency) <= 6 and currency.isalnum()):
            errors.append("Account currency must be a short code such as USD or EUR.")
        self.general_error.setText("\n".join(errors))

        _, shortcut_errors = validate_bindings({a: self._shortcut_text(a) for a in self.shortcut_edits})
        self.shortcut_error.setText(
            "\n".join(f"{ACTION_LABELS[a]}: {m}" for a, m in shortcut_errors.items()))
        if errors or shortcut_errors:
            QMessageBox.warning(self, "Settings", "Please fix the highlighted problems before saving.")
            return

        s = self.ctx.settings
        launch = self.launch_at_login.isChecked()
        if launch != s.get_bool("launch_at_login"):
            problem = platform_adapters.set_launch_at_login(launch)
            if problem:
                QMessageBox.warning(self, "Startup", problem)
                launch = s.get_bool("launch_at_login")
        s.set("account_balance", balance)
        s.set("account_currency", currency)
        s.set("risk_mode", self.risk_mode.currentData())
        s.set("risk_percent", percent)
        s.set("risk_fixed", fixed)
        s.set("rr", rr)
        s.set("default_leverage", leverage)
        s.set("theme", self.theme.currentData())
        s.set("always_on_top", self.always_on_top.isChecked())
        s.set("start_minimized", self.start_minimized.isChecked())
        s.set("launch_at_login", launch)
        s.set("restore_clipboard", self.restore_clipboard.isChecked())
        s.set("api_enabled", self.api_enabled.isChecked())
        valid, _ = validate_bindings({a: self._shortcut_text(a) for a in self.shortcut_edits})
        for action, shortcut in valid.items():
            s.set(ACTION_SETTING_KEYS[action], shortcut.text)
        self.accept()
        if self._on_saved:
            self._on_saved()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        try:
            from ..platform.windows.window_effects import apply_titlebar_theme
            apply_titlebar_theme(self, self.ctx.settings.get("theme"))
        except (ImportError, OSError, AttributeError):
            pass
