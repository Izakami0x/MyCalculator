"""Global-shortcut parsing, validation and registration (platform backend is injected)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from ..core.validation import ValidationError

log = logging.getLogger("izakami.hotkeys")

ACTION_ENTRY = "capture_entry"
ACTION_STOP = "capture_stop"
ACTION_COPY = "copy_size"

ACTION_LABELS = {
    ACTION_ENTRY: "Capture Entry",
    ACTION_STOP: "Capture Stop Loss",
    ACTION_COPY: "Copy Position Size",
}
ACTION_SETTING_KEYS = {
    ACTION_ENTRY: "shortcut_entry",
    ACTION_STOP: "shortcut_stop",
    ACTION_COPY: "shortcut_copy",
}

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
_MODS = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT,
    "win": MOD_WIN, "meta": MOD_WIN, "windows": MOD_WIN,
}
_NAMED = {
    "space": (0x20, "Space"), "tab": (0x09, "Tab"), "enter": (0x0D, "Enter"), "return": (0x0D, "Enter"),
    "esc": (0x1B, "Esc"), "escape": (0x1B, "Esc"), "backspace": (0x08, "Backspace"),
    "insert": (0x2D, "Insert"), "ins": (0x2D, "Insert"), "delete": (0x2E, "Delete"), "del": (0x2E, "Delete"),
    "home": (0x24, "Home"), "end": (0x23, "End"), "pgup": (0x21, "PgUp"), "pageup": (0x21, "PgUp"),
    "pgdown": (0x22, "PgDown"), "pagedown": (0x22, "PgDown"),
    "left": (0x25, "Left"), "up": (0x26, "Up"), "right": (0x27, "Right"), "down": (0x28, "Down"),
}
_RESERVED = {
    "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+Z", "Ctrl+A", "Ctrl+Y", "Ctrl+Alt+Delete", "Alt+F4", "Alt+Tab",
    "Win+L", "Ctrl+Shift+Esc", "Alt+Esc",
}


@dataclass(frozen=True)
class Shortcut:
    modifiers: int
    vk: int
    text: str  # canonical, e.g. "Ctrl+Shift+E"


def parse_shortcut(text: str) -> Shortcut:
    """Parse 'ctrl+shift+e' into a Shortcut. At least one modifier is required."""
    parts = [p.strip() for p in (text or "").split("+") if p.strip()]
    if not parts:
        raise ValidationError("No shortcut set.")
    *mod_parts, key = parts
    modifiers = 0
    for part in mod_parts:
        flag = _MODS.get(part.lower())
        if flag is None:
            raise ValidationError(f"Unknown modifier '{part}'.")
        modifiers |= flag
    if modifiers == 0:
        raise ValidationError("A shortcut needs at least one modifier (Ctrl, Alt, Shift or Win).")
    lower = key.lower()
    if len(key) == 1 and key.isalnum() and key.isascii():
        vk, name = ord(key.upper()), key.upper()
    elif lower.startswith("f") and lower[1:].isdigit() and 1 <= int(lower[1:]) <= 24:
        vk, name = 0x70 + int(lower[1:]) - 1, f"F{int(lower[1:])}"
    elif lower in _NAMED:
        vk, name = _NAMED[lower]
    else:
        raise ValidationError(f"Unsupported key '{key}'.")
    names = []
    for label, flag in (("Ctrl", MOD_CONTROL), ("Alt", MOD_ALT), ("Shift", MOD_SHIFT), ("Win", MOD_WIN)):
        if modifiers & flag:
            names.append(label)
    return Shortcut(modifiers, vk, "+".join([*names, name]))


def validate_bindings(bindings: dict[str, str]) -> tuple[dict[str, Shortcut], dict[str, str]]:
    """Parse every binding; report bad, reserved and duplicate shortcuts per action."""
    valid: dict[str, Shortcut] = {}
    errors: dict[str, str] = {}
    owner: dict[str, str] = {}
    for action, text in bindings.items():
        try:
            sc = parse_shortcut(text)
        except ValidationError as exc:
            errors[action] = str(exc)
            continue
        if sc.text in _RESERVED:
            errors[action] = f"{sc.text} is reserved by Windows or common editing."
        elif sc.text in owner:
            errors[action] = f"{sc.text} is already used for '{ACTION_LABELS[owner[sc.text]]}'."
        else:
            owner[sc.text] = action
            valid[action] = sc
    return valid, errors


class HotkeyBackend(Protocol):
    def register(self, bindings: dict[str, Shortcut]) -> dict[str, Optional[str]]:
        """Register all bindings; return {action: None | error message}."""

    def unregister_all(self) -> None: ...


@dataclass
class HotkeyApplyResult:
    registered: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


class HotkeyService:
    def __init__(self, backend_factory: Optional[Callable[[Callable[[str], None]], HotkeyBackend]] = None):
        self.on_trigger: Optional[Callable[[str], None]] = None
        self._backend = backend_factory(self._dispatch) if backend_factory else None

    @property
    def supported(self) -> bool:
        return self._backend is not None

    def apply(self, bindings: dict[str, str]) -> HotkeyApplyResult:
        valid, errors = validate_bindings(bindings)
        result = HotkeyApplyResult(errors=dict(errors))
        if self._backend is None:
            return result
        self._backend.unregister_all()
        if valid:
            outcome = self._backend.register(valid)
            for action in valid:
                message = outcome.get(action)
                if message:
                    result.errors[action] = f"{valid[action].text} could not be registered: {message}."
                else:
                    result.registered.append(action)
        return result

    def shutdown(self) -> None:
        if self._backend is not None:
            self._backend.unregister_all()

    def _dispatch(self, action: str) -> None:
        callback = self.on_trigger
        if callback is None:
            return
        try:
            callback(action)
        except Exception:  # never let a callback kill the hotkey thread
            log.exception("Hotkey callback failed for %s", action)
