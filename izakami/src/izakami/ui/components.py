"""Small reusable widgets for the calculator window."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPolygonF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..core.validation import ValidationError, parse_decimal
from .format import format_plain


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def make_rule(vertical: bool = False) -> QFrame:
    rule = QFrame()
    rule.setProperty("role", "vrule" if vertical else "rule")
    if vertical:
        rule.setFixedWidth(1)
    else:
        rule.setFixedHeight(1)
    return rule


class StepLineEdit(QLineEdit):
    """Line edit whose Up/Down keys step the numeric value."""

    def __init__(self, step: Optional[Decimal] = None) -> None:
        super().__init__()
        self.step = step
        self.setProperty("role", "fieldedit")

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self.step and not self.isReadOnly() and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            try:
                current = parse_decimal(self.text() or "0")
            except ValidationError:
                return
            new = current + self.step if event.key() == Qt.Key.Key_Up else current - self.step
            if new > 0:
                self.setText(format_plain(new))
            return
        super().keyPressEvent(event)


class Field(QFrame):
    """Captioned input box: caption + hint on top, big editable value below."""

    def __init__(self, caption: str, *, suffix: str = "", readonly: bool = False,
                 step: Optional[Decimal] = None, hint: str = "", placeholder: str = "") -> None:
        super().__init__()
        self.setProperty("role", "field")
        self.setProperty("readonly", readonly)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 9, 14, 10)
        outer.setSpacing(1)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.caption = QLabel(caption)
        self.caption.setProperty("role", "caption")
        top.addWidget(self.caption)
        top.addStretch(1)
        self.hint = QLabel(hint)
        self.hint.setProperty("role", "hint")
        top.addWidget(self.hint)
        outer.addLayout(top)
        self.row = QHBoxLayout()
        self.row.setSpacing(6)
        self.edit = StepLineEdit(step)
        self.edit.setReadOnly(readonly)
        self.edit.setPlaceholderText(placeholder)
        self.row.addWidget(self.edit, 1)
        self.suffix = QLabel(suffix)
        self.suffix.setProperty("role", "suffix")
        self.row.addWidget(self.suffix)
        outer.addLayout(self.row)
        self.edit.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.edit and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            repolish(self)
        return False

    def text(self) -> str:
        return self.edit.text()

    def set_text(self, text: str) -> None:
        self.edit.setText(text)

    def set_suffix(self, text: str) -> None:
        self.suffix.setText(text)


class Stat(QWidget):
    """Caption above a value; the value's colour follows ``tone`` (loss / profit / '')."""

    def __init__(self, caption: str, role: str = "stat") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.caption = QLabel(caption)
        self.caption.setProperty("role", "caption")
        self.value = QLabel("—")
        self.value.setProperty("role", role)
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.caption)
        layout.addWidget(self.value)

    def set_value(self, text: str, tone: str = "") -> None:
        if self.value.text() != text:
            self.value.setText(text)
        if self.value.property("tone") != tone:
            self.value.setProperty("tone", tone)
            repolish(self.value)


class StatusLine(QWidget):
    """Coloured dot + message. kind: ready | busy | warn | error | info."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setProperty("role", "dot")
        self.text = QLabel("")
        self.text.setProperty("role", "hint")
        self.text.setWordWrap(False)
        layout.addWidget(self.dot)
        layout.addWidget(self.text, 1)
        self.kind = "info"

    def set_status(self, kind: str, text: str, tooltip: str = "") -> None:
        if self.kind != kind:
            self.kind = kind
            self.dot.setProperty("kind", kind)
            repolish(self.dot)
        if self.text.text() != text:
            self.text.setText(text)
        self.setToolTip(tooltip or text)


class DragHeader(QFrame):
    """Header strip that moves the frameless window."""

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)


class LogoWidget(QWidget):
    """Geometric placeholder logo (two chevrons)."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(46, 32)
        self._color = QColor("#ffffff")

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawPolygon(QPolygonF([QPointF(0, 30), QPointF(17, 2), QPointF(34, 30),
                                       QPointF(26, 30), QPointF(17, 14), QPointF(8, 30)]))
        painter.drawPolygon(QPolygonF([QPointF(22, 30), QPointF(31, 16), QPointF(40, 30)]))
