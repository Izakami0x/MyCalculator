"""Instrument manager: add, edit, delete, search and select instruments."""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget)

from ..context import AppContext
from ..core.validation import ValidationError, parse_decimal
from ..models.instrument import ASSET_CLASSES, SIZING_MODELS, Instrument
from ..services.instrument_service import InstrumentError
from .format import format_plain

# (attribute, caption, tooltip, optional?)
DECIMAL_FIELDS = [
    ("contract_size", "Contract size", "Units of the instrument per 1 quantity unit (e.g. 100000 for a forex lot).", False),
    ("tick_size", "Tick size", "Smallest price movement. Also used to round the take-profit price.", False),
    ("tick_value", "Tick value", "Value of one tick per 1 quantity unit in the P&L currency (tick model only).", False),
    ("quantity_step", "Quantity step", "Smallest size increment. Position size is always rounded DOWN to this step.", False),
    ("min_quantity", "Minimum quantity", "Smallest tradable size.", False),
    ("max_quantity", "Maximum quantity", "Leave blank for no maximum.", True),
    ("min_notional", "Minimum notional", "Minimum position value in the P&L currency. Blank = none.", True),
    ("conversion_rate", "Conversion rate", "1 unit of the P&L currency in your ACCOUNT currency. Ignored when they match.", False),
    ("leverage", "Leverage", "Blank = use the default leverage from Settings.", True),
    ("margin_rate", "Margin rate", "Optional fraction (0.05 = 5%) that overrides leverage-based margin.", True),
]


class InstrumentManager(QDialog):
    def __init__(self, ctx: AppContext, parent: Optional[QWidget] = None, current_symbol: str = "") -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._current: Optional[Instrument] = None
        self._dirty = False
        self._loading = False
        self.setWindowTitle("Instrument Manager")
        self.setMinimumSize(700, 500)

        # left: search + list
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search symbol or asset class…")
        self.search.textChanged.connect(lambda: self._refresh_list())
        self.listing = QListWidget()
        self.listing.currentItemChanged.connect(self._on_item_changed)
        new_btn = QPushButton("New instrument")
        new_btn.clicked.connect(self._new)
        restore_btn = QPushButton("Restore starter presets")
        restore_btn.setToolTip("Re-adds any deleted starter preset. Existing instruments are not touched.")
        restore_btn.clicked.connect(self._restore_presets)
        left.addWidget(self.search)
        left.addWidget(self.listing, 1)
        left.addWidget(new_btn)
        left.addWidget(restore_btn)

        # right: form
        right = QVBoxLayout()
        form = QFormLayout()
        form.setVerticalSpacing(6)
        self.symbol = QLineEdit()
        self.asset_class = QComboBox()
        self.asset_class.addItems(ASSET_CLASSES)
        self.model = QComboBox()
        self.model.addItem("Linear (contract multiplier)", "linear")
        self.model.addItem("Tick value (futures)", "tick")
        self.pnl_currency = QLineEdit()
        self.quantity_unit = QLineEdit()
        form.addRow("Symbol", self.symbol)
        form.addRow("Asset class", self.asset_class)
        form.addRow("Calculation model", self.model)
        form.addRow("P&L currency", self.pnl_currency)
        form.addRow("Quantity unit", self.quantity_unit)
        self.numeric: dict[str, QLineEdit] = {}
        for attr, caption, tip, _optional in DECIMAL_FIELDS:
            edit = QLineEdit()
            edit.setToolTip(tip)
            self.numeric[attr] = edit
            form.addRow(caption, edit)
        right.addLayout(form)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setProperty("role", "error")
        right.addWidget(self.message)
        right.addStretch(1)
        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setProperty("role", "primary")
        self.save_btn.clicked.connect(self._save)
        self.dup_btn = QPushButton("Duplicate")
        self.dup_btn.clicked.connect(self._duplicate)
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._delete)
        self.use_btn = QPushButton("Use this instrument")
        self.use_btn.clicked.connect(self._use)
        for b in (self.save_btn, self.dup_btn, self.del_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(self.use_btn)
        right.addLayout(buttons)

        root = QHBoxLayout(self)
        root.addLayout(left, 2)
        root.addLayout(right, 3)

        for edit in (self.symbol, self.pnl_currency, self.quantity_unit, *self.numeric.values()):
            edit.textEdited.connect(self._mark_dirty)
        self.asset_class.currentIndexChanged.connect(self._mark_dirty)
        self.model.currentIndexChanged.connect(self._mark_dirty)

        self._refresh_list(select=current_symbol)

    # -- list handling -------------------------------------------------------------------
    def _refresh_list(self, select: str = "") -> None:
        keep = select or (self._current.symbol if self._current else "")
        self.listing.blockSignals(True)
        self.listing.clear()
        for inst in self.ctx.instruments.list(self.search.text()):
            item = QListWidgetItem(f"{inst.symbol}    ·  {inst.asset_class}")
            item.setData(Qt.ItemDataRole.UserRole, inst.symbol)
            self.listing.addItem(item)
            if inst.symbol == keep:
                self.listing.setCurrentItem(item)
        self.listing.blockSignals(False)
        item = self.listing.currentItem()
        if item is None and self.listing.count():
            self.listing.setCurrentRow(0)
            item = self.listing.currentItem()
        symbol = item.data(Qt.ItemDataRole.UserRole) if item else None
        inst = self.ctx.instruments.get(symbol) if symbol else None
        if inst is not None:
            self._load(inst)
        elif self.listing.count() == 0:
            self._load(None)

    def _on_item_changed(self, item: Optional[QListWidgetItem], _previous) -> None:
        if item is None or self._loading:
            return
        if self._dirty and not self._confirm_discard():
            self._refresh_list()  # snap back to the instrument being edited
            return
        inst = self.ctx.instruments.get(item.data(Qt.ItemDataRole.UserRole))
        if inst is not None:
            self._load(inst)

    def _confirm_discard(self) -> bool:
        answer = QMessageBox.question(
            self, "Unsaved changes", "Discard your unsaved changes?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard

    # -- form <-> instrument ----------------------------------------------------------------
    def _load(self, inst: Optional[Instrument]) -> None:
        self._loading = True
        self._current = inst
        base = inst or Instrument(symbol="")
        self.symbol.setText(base.symbol)
        self.asset_class.setCurrentText(base.asset_class)
        self.model.setCurrentIndex(max(0, SIZING_MODELS.index(base.model)))
        self.pnl_currency.setText(base.pnl_currency)
        self.quantity_unit.setText(base.quantity_unit)
        for attr, _c, _t, _o in DECIMAL_FIELDS:
            value = getattr(base, attr)
            self.numeric[attr].setText("" if value is None else format_plain(value))
        self.message.setText("")
        has = inst is not None and inst.id is not None
        self.dup_btn.setEnabled(has)
        self.del_btn.setEnabled(has)
        self.use_btn.setEnabled(has)
        self._dirty = False
        self._loading = False

    def _mark_dirty(self) -> None:
        if not self._loading:
            self._dirty = True

    def _collect(self) -> tuple[Optional[Instrument], list[str]]:
        errors: list[str] = []
        values: dict[str, object] = {}
        for attr, caption, _tip, optional in DECIMAL_FIELDS:
            text = self.numeric[attr].text().strip()
            if not text:
                if optional:
                    values[attr] = None if attr != "min_notional" else parse_decimal("0")
                else:
                    errors.append(f"{caption} is required.")
                continue
            try:
                values[attr] = parse_decimal(text, caption)
            except ValidationError as exc:
                errors.append(str(exc))
        if errors:
            return None, errors
        base = self._current or Instrument(symbol="")
        inst = replace(
            base, symbol=self.symbol.text().strip(), asset_class=self.asset_class.currentText(),
            model=self.model.currentData(), pnl_currency=self.pnl_currency.text().strip().upper(),
            quantity_unit=self.quantity_unit.text().strip() or "units", **values)  # type: ignore[arg-type]
        return inst, []

    # -- actions ----------------------------------------------------------------------------
    def _new(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self.listing.blockSignals(True)
        self.listing.clearSelection()
        self.listing.setCurrentItem(None)
        self.listing.blockSignals(False)
        self._load(None)
        self.symbol.setFocus()

    def _save(self) -> None:
        inst, errors = self._collect()
        if inst is not None:
            try:
                saved = self.ctx.instruments.save(inst)
            except InstrumentError as exc:
                errors = exc.messages
            else:
                self._dirty = False
                self._current = saved
                self._refresh_list(select=saved.symbol)
                self.message.setText("")
                return
        self.message.setText("\n".join(errors))

    def _duplicate(self) -> None:
        if self._current is None or self._current.id is None:
            return
        try:
            copy = self.ctx.instruments.duplicate(self._current)
        except InstrumentError as exc:
            self.message.setText("\n".join(exc.messages))
            return
        self._dirty = False
        self._refresh_list(select=copy.symbol)

    def _delete(self) -> None:
        inst = self._current
        if inst is None or inst.id is None:
            return
        answer = QMessageBox.question(
            self, "Delete instrument", f"Delete {inst.symbol}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.ctx.instruments.delete(inst.id)
        self._dirty = False
        self._current = None
        self._refresh_list()

    def _restore_presets(self) -> None:
        added = self.ctx.instruments.restore_presets()
        self._refresh_list()
        self.message.setText(f"Restored {added} starter preset(s)." if added else "All starter presets already exist.")

    def _use(self) -> None:
        if self._current is None or self._current.id is None:
            return
        if self._dirty:
            self._save()
            if self._dirty or self.message.text():
                return
        self.ctx.settings.set("selected_instrument", self._current.symbol)
        self.accept()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        try:
            from ..platform.windows.window_effects import apply_titlebar_theme
            apply_titlebar_theme(self, self.ctx.settings.get("theme"))
        except (ImportError, OSError, AttributeError):
            pass
