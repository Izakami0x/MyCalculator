"""Small, theme-aware success toast for completed clipboard actions."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class SuccessToast(QFrame):
    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("SuccessToast")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label = QLabel(self)
        self.label.setObjectName("ToastLabel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.addWidget(self.label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.apply_theme("dark")

    def apply_theme(self, name: str) -> None:
        if name == "light":
            self.setStyleSheet("QFrame#SuccessToast { background:#ffffff; border:1px solid #cfd3db; border-radius:9px; } QLabel#ToastLabel { color:#14171c; font-weight:600; }")
        else:
            self.setStyleSheet("QFrame#SuccessToast { background:#222730; border:1px solid #323a47; border-radius:9px; } QLabel#ToastLabel { color:#e8ebf0; font-weight:600; }")

    def show_message(self, message: str) -> None:
        self.label.setText(message)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            self.move(parent.mapToGlobal(parent.rect().topLeft()).x() + 12,
                      parent.mapToGlobal(parent.rect().topLeft()).y() + 12)
        self.show()
        self.raise_()
        self._timer.start(1800)
