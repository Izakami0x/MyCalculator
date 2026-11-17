"""Small Windows-only native window helpers."""
from __future__ import annotations

import ctypes
import sys


def set_window_topmost(widget, enabled: bool) -> bool:
    """Set HWND_TOPMOST/HWND_NOTOPMOST without toggling Qt window flags."""
    if sys.platform != "win32":
        return False
    hwnd = int(widget.winId())
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.SetWindowPos.restype = ctypes.c_bool
    insert_after = ctypes.c_void_p(-1 if enabled else -2)
    flags = 0x0001 | 0x0002 | 0x0010  # NOMOVE | NOSIZE | NOACTIVATE
    if not user32.SetWindowPos(ctypes.c_void_p(hwnd), insert_after, 0, 0, 0, 0, flags):
        raise ctypes.WinError(ctypes.get_last_error())
    return True


def apply_titlebar_theme(widget, theme: str) -> None:
    """Ask DWM to use a dark native title bar when the application theme is dark."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        dwmapi = ctypes.WinDLL("dwmapi")
        value = ctypes.c_int(1 if theme == "dark" else 0)
        result = dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 20, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result != 0:
            # Older Windows 10 builds used attribute 19.
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), 19, ctypes.byref(value), ctypes.sizeof(value)
            )
    except (OSError, AttributeError):
        pass
