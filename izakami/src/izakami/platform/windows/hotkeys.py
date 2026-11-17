"""Global hotkeys through RegisterHotKey on a dedicated message-loop thread (Windows only)."""
from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes
from typing import Callable, Optional

from ...services.hotkey_service import Shortcut

log = logging.getLogger("izakami.hotkeys.win")

MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_USER = 0x0400
PM_NOREMOVE = 0x0000
ERROR_HOTKEY_ALREADY_REGISTERED = 1409


class WindowsHotkeyBackend:
    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        self._user32.GetMessageW.restype = ctypes.c_int
        self._user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT,
        ]
        self._user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None

    def register(self, bindings: dict[str, Shortcut]) -> dict[str, Optional[str]]:
        self.unregister_all()
        results: dict[str, Optional[str]] = {}
        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, args=(bindings, results, ready), daemon=True, name="izakami-hotkeys"
        )
        self._thread.start()
        if not ready.wait(3.0):
            return {action: "timed out while registering" for action in bindings}
        return results

    def unregister_all(self) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive() and self._thread_id:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None

    def _run(self, bindings: dict[str, Shortcut], results: dict, ready: threading.Event) -> None:
        msg = wintypes.MSG()
        self._thread_id = int(self._kernel32.GetCurrentThreadId())
        self._user32.PeekMessageW(ctypes.byref(msg), None, WM_USER, WM_USER, PM_NOREMOVE)  # create queue
        ids: dict[int, str] = {}
        for index, (action, shortcut) in enumerate(bindings.items(), start=1):
            if self._user32.RegisterHotKey(None, index, shortcut.modifiers | MOD_NOREPEAT, shortcut.vk):
                ids[index] = action
                results[action] = None
            else:
                code = ctypes.get_last_error()
                results[action] = (
                    "already in use by another application"
                    if code == ERROR_HOTKEY_ALREADY_REGISTERED
                    else f"Windows error {code}"
                )
        ready.set()
        try:
            while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    action = ids.get(int(msg.wParam))
                    if action:
                        try:
                            self._callback(action)
                        except Exception:
                            log.exception("Hotkey callback failed")
        finally:
            for index in ids:
                self._user32.UnregisterHotKey(None, index)
