"""Animated, theme-aware success toast for completed clipboard actions."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
)


class SuccessToast(QFrame):
    """A non-intrusive toast anchored to the active screen's bottom-right corner."""

    def __init__(self, parent):
        super().__init__(
            parent,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setObjectName("SuccessToast")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.icon_label = QLabel("✓", self)
        self.icon_label.setObjectName("ToastIcon")
        self.label = QLabel(self)
        self.label.setObjectName("ToastLabel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(17, 13, 22, 13)
        layout.setSpacing(12)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        self._shadow = shadow
        self._fade_animation: QPropertyAnimation | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._animate_out)
        self._animation: QPropertyAnimation | None = None
        self._hiding = False
        self.apply_theme("dark")

    def apply_theme(self, name: str) -> None:
        self._theme = name
        self._apply_palette("success")

    def _apply_palette(self, kind: str) -> None:
        if kind == "error":
            if self._theme == "light":
                bg, border, text, accent, accent_bg = ("#fff0f1", "#dc3545", "#541820", "#ffffff", "#cf2638")
            else:
                bg, border, text, accent, accent_bg = ("#3d252b", "#ff5266", "#fff0f2", "#2b1117", "#ff5266")
        elif self._theme == "light":
            bg, border, text, accent, accent_bg = (
                "#eaf8f1", "#19a873", "#12382b", "#ffffff", "#12a36d",
            )
        else:
            bg, border, text, accent, accent_bg = (
                "#20372f", "#2ecc8f", "#e9fff4", "#10251c", "#2ecc8f",
            )
        self.setStyleSheet(
            "QFrame#SuccessToast {"
            f" background:{bg}; border:1.5px solid {border}; border-radius:16px;"
            " }"
            "QLabel#ToastIcon {"
            f" color:{accent}; background:{accent_bg};"
            " border-radius:14px; min-width:28px; max-width:28px;"
            " min-height:28px; max-height:28px; font-size:16px;"
            " font-weight:800; qproperty-alignment: AlignCenter;"
            " }"
            "QLabel#ToastLabel {"
            f" color:{text}; font-size:10.5pt; font-weight:700;"
            " background:transparent; border:none;"
            " }"
        )
        self._shadow.setColor(QColor("#0b9a69" if name == "light" else "#2ecc8f"))
        self._shadow.setBlurRadius(30)

    def _screen_geometry(self):
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None and self.parentWidget() is not None:
            screen = self.parentWidget().screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _stop_animation(self) -> None:
        for animation in (self._animation, self._fade_animation):
            if animation is not None:
                animation.stop()
                animation.deleteLater()
        self._animation = None
        self._fade_animation = None

    def show_message(self, message: str) -> None:
        self._show(message, "success")

    def show_error_message(self, message: str) -> None:
        self._show(message, "error")

    def _show(self, message: str, kind: str) -> None:
        self._timer.stop()
        self._stop_animation()
        self._hiding = False
        self.icon_label.setText("!" if kind == "error" else "✓")
        self._apply_palette(kind)
        self.label.setText(message)
        self.adjustSize()

        area = self._screen_geometry()
        if area is None:
            self.setWindowOpacity(1.0)
            self.show()
            self.raise_()
            self._timer.start(2200)
            return

        margin = 24
        end_pos = QPoint(
            area.x() + (area.width() - self.width()) // 2,
            area.y() + (area.height() // 4) - (self.height() // 2),
        )
        start_pos = end_pos + QPoint(34, 0)
        self.move(start_pos)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        # Animate position and opacity together for a soft, floating entrance.
        self._animation = QPropertyAnimation(self, b"pos", self)
        self._animation.setDuration(320)
        self._animation.setStartValue(start_pos)
        self._animation.setEndValue(end_pos)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(260)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade.start()
        self._fade_animation = fade
        self._timer.start(2300)

    def _animate_out(self) -> None:
        if not self.isVisible() or self._hiding:
            return
        self._hiding = True
        self._stop_animation()
        start_pos = self.pos()
        end_pos = start_pos + QPoint(22, 0)
        self._animation = QPropertyAnimation(self, b"pos", self)
        self._animation.setDuration(220)
        self._animation.setStartValue(start_pos)
        self._animation.setEndValue(end_pos)
        self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._animation.finished.connect(self.hide)
        self._animation.start()
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(200)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        fade.start()
        self._fade_animation = fade
