"""Platform adapters. Only Windows is implemented; other systems degrade gracefully."""
from __future__ import annotations

import sys
from typing import Callable, Optional


def is_windows() -> bool:
    return sys.platform == "win32"


def create_hotkey_backend(callback: Callable[[str], None]):
    if not is_windows():
        return None
    from .windows.hotkeys import WindowsHotkeyBackend

    return WindowsHotkeyBackend(callback)


def create_clipboard_backend():
    if not is_windows():
        return None
    from .windows.clipboard import WindowsClipboardBackend

    return WindowsClipboardBackend()


def set_launch_at_login(enabled: bool) -> Optional[str]:
    """Returns an error message, or None on success."""
    if not is_windows():
        return "Launching at login is only supported on Windows."
    from .windows.startup import set_launch_at_login as _set

    return _set(enabled)
