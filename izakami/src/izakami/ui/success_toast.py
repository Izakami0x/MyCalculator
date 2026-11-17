"""Animated, theme-aware success toast for completed clipboard actions."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
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
        layout.setContentsMargins(15, 11, 19, 11)
        layout.setSpacing(11)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 6)
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
        if name == "light":
            bg, border, text, accent, accent_bg = (
                "rgba(250,252,255,0.90)",
                "rgba(255,255,255,0.72)",
                "#14171c",
                "#0b9a69",
                "rgba(11,154,105,0.12)",
            )
        else:
            bg, border, text, accent, accent_bg = (
                "rgba(29,36,47,0.91)",
                "rgba(255,255,255,0.14)",
                "#e8ebf0",
                "#2ecc8f",
                "rgba(46,204,143,0.15)",
            )
        self.setStyleSheet(
            "QFrame#SuccessToast {"
            f" background:{bg}; border:1px solid {border}; border-radius:14px;"
            " }"
            "QLabel#ToastIcon {"
            f" color:{accent}; background:{accent_bg};"
            " border-radius:12px; min-width:24px; max-width:24px;"
            " min-height:24px; max-height:24px; font-size:14px;"
            " font-weight:800; qproperty-alignment: AlignCenter;"
            " }"
            "QLabel#ToastLabel {"
            f" color:{text}; font-size:10pt; font-weight:600;"
            " background:transparent; border:none;"
            " }"
        )
        self._shadow.setColor(Qt.GlobalColor.black)
        self._shadow.setBlurRadius(24)

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
        self._timer.stop()
        self._stop_animation()
        self._hiding = False
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
            area.y() + margin,
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
