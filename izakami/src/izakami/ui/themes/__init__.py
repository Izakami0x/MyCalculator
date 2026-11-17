"""Dark and light themes as Qt style sheets."""
from __future__ import annotations

from string import Template

PALETTES = {
    "dark": dict(
        bg="#13161b", panel="#191d24", border="#272d37", border_strong="#323a47", text="#e8ebf0",
        muted="#8991a1", green="#2ecc8f", green_bg="rgba(46,204,143,0.12)", red="#ef5266",
        red_bg="rgba(239,82,102,0.12)", amber="#e8b04a", accent="#2ecc8f", on_accent="#08130e",
        button="#222730", button_hover="#2b313c", selection="#25604f",
    ),
    "light": dict(
        bg="#f6f7f9", panel="#ffffff", border="#dfe2e8", border_strong="#cfd3db", text="#14171c",
        muted="#6a7282", green="#0b9a69", green_bg="rgba(11,154,105,0.10)", red="#d3334a",
        red_bg="rgba(211,51,74,0.09)", amber="#b9801c", accent="#0b9a69", on_accent="#ffffff",
        button="#eceef2", button_hover="#e1e4ea", selection="#bfe9d9",
    ),
}


def palette(name: str) -> dict[str, str]:
    return PALETTES.get(name, PALETTES["dark"])


_QSS = Template("""
* { font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif; }
QWidget { color: $text; font-size: 10pt; }
QWidget#Root { background: transparent; }
QFrame#Card { background: $bg; border: 1px solid $border_strong; border-radius: 20px; }
QFrame#Header, QFrame#Footer { background: transparent; border: none; }
QFrame[role="rule"], QFrame[role="vrule"] { background: $border; border: none; }

QFrame[role="field"] { background: $panel; border: 1px solid $border; border-radius: 12px; }
QFrame[role="field"][focused="true"] { border: 1px solid $accent; }
QFrame[role="field"][readonly="true"] { background: transparent; }
QFrame#Results { background: $panel; border: 1px solid $border; border-radius: 12px; }
QFrame#Accent { background: $muted; border: none; border-radius: 2px; }
QFrame#Accent[tone="long"] { background: $green; }
QFrame#Accent[tone="short"] { background: $red; }

QLabel { background: transparent; border: none; }
QLabel[role="caption"] { color: $muted; font-size: 9pt; }
QLabel[role="hint"] { color: $muted; font-size: 8pt; }
QLabel[role="suffix"] { color: $muted; font-size: 10pt; }
QLabel#Wordmark { font-size: 17pt; font-weight: 600; }
QLabel#Subtitle { color: $muted; font-size: 8pt; }
QLabel[role="stat"] { font-size: 12pt; font-weight: 500; }
QLabel[role="stat"][tone="loss"] { color: $red; }
QLabel[role="stat"][tone="profit"] { color: $green; }
QLabel[role="big"] { font-size: 34pt; font-weight: 600; }
QLabel[role="bigunit"] { color: $muted; font-size: 15pt; }
QLabel[role="pill"] { border: 1px solid $border; border-radius: 15px; padding: 6px 20px; color: $muted; font-weight: 600; }
QLabel[role="pill"][direction="long"] { color: $green; border-color: $green; background: $green_bg; }
QLabel[role="pill"][direction="short"] { color: $red; border-color: $red; background: $red_bg; }
QLabel[role="dot"] { font-size: 8pt; color: $muted; }
QLabel[role="dot"][kind="ready"] { color: $green; }
QLabel[role="dot"][kind="warn"] { color: $amber; }
QLabel[role="dot"][kind="busy"] { color: $amber; }
QLabel[role="dot"][kind="error"] { color: $red; }
QLabel[role="note"] { color: $muted; }
QLabel[role="error"] { color: $red; }

QLineEdit { background: $panel; border: 1px solid $border; border-radius: 6px; padding: 5px 8px; selection-background-color: $selection; }
QLineEdit:focus { border: 1px solid $accent; }
QLineEdit[role="fieldedit"] { background: transparent; border: none; padding: 0; font-size: 16pt; }
QLineEdit[role="fieldedit"][readOnly="true"] { color: $muted; }

QPushButton { background: $button; border: 1px solid $border; border-radius: 10px; padding: 8px 16px; font-weight: 500; }
QPushButton:hover { background: $button_hover; }
QPushButton:disabled { color: $muted; }
QPushButton[role="primary"] { background: $accent; color: $on_accent; border: none; }
QPushButton[role="primary"]:hover { background: $accent; }
QPushButton[role="toggle"] { background: transparent; border: none; color: $muted; padding: 4px 8px; }
QPushButton[role="toggle"][on="true"] { color: $text; }
QToolButton[role="pin"] { min-width: 28px; min-height: 28px; padding: 3px; border-radius: 8px; }
QToolButton[role="pin"][on="true"] { color: $accent; background: $button; }
QPushButton[role="mode"] { background: transparent; border: 1px solid $border; border-radius: 8px; padding: 2px 8px; color: $muted; font-size: 10pt; }
QPushButton[role="mode"]:hover { color: $text; border-color: $muted; }
QPushButton[role="link"] { background: transparent; border: none; color: $muted; padding: 2px 6px; font-size: 9pt; }
QPushButton[role="link"]:hover { color: $text; }
QToolButton { background: transparent; border: none; border-radius: 8px; padding: 6px 8px; font-size: 13pt; color: $muted; }
QToolButton:hover { background: $button_hover; color: $text; }

QComboBox { background: transparent; border: none; font-size: 16pt; font-weight: 600; padding: 2px 4px; }
QComboBox::drop-down { border: none; width: 0px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView { background: $panel; border: 1px solid $border; selection-background-color: $selection; selection-color: $text; outline: none; font-size: 11pt; font-weight: normal; }

QDialog { background: $bg; }
QDialog QComboBox { background: $panel; border: 1px solid $border; border-radius: 6px; padding: 5px 8px; font-size: 10pt; font-weight: normal; }
QDialog QComboBox::drop-down { width: 18px; }
QDialog QPushButton[role="mode"] { padding: 4px 10px; }
QTabWidget::pane { border: 1px solid $border; border-radius: 8px; top: -1px; }
QTabBar::tab { padding: 8px 16px; color: $muted; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: $text; border-bottom: 2px solid $accent; }
QListWidget { background: $panel; border: 1px solid $border; border-radius: 8px; padding: 4px; outline: none; }
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:selected { background: $selection; color: $text; }
QCheckBox { spacing: 8px; }
QKeySequenceEdit { background: $panel; border: 1px solid $border; border-radius: 6px; }
QToolTip { background: $panel; color: $text; border: 1px solid $border; padding: 4px 6px; }
""")


def build_stylesheet(name: str) -> str:
    return _QSS.substitute(palette(name))
