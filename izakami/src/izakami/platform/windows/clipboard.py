"""Win32 clipboard access and key simulation (Windows only)."""
from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from typing import Optional

log = logging.getLogger("izakami.clipboard.win")

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_C = 0x10, 0x11, 0x12, 0x5B, 0x5C, 0x43

ULONG_PTR = wintypes.WPARAM


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class WindowsClipboardBackend:
    def __init__(self) -> None:
        u, k = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)
        self._u, self._k = u, k
        u.OpenClipboard.argtypes = [wintypes.HWND]
        u.OpenClipboard.restype = wintypes.BOOL
        u.CloseClipboard.restype = wintypes.BOOL
        u.EmptyClipboard.restype = wintypes.BOOL
        u.GetClipboardData.argtypes = [wintypes.UINT]
        u.GetClipboardData.restype = wintypes.HANDLE
        u.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        u.SetClipboardData.restype = wintypes.HANDLE
        u.GetClipboardSequenceNumber.restype = wintypes.DWORD
        u.GetAsyncKeyState.argtypes = [ctypes.c_int]
        u.GetAsyncKeyState.restype = ctypes.c_short
        u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        u.SendInput.restype = wintypes.UINT
        k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        k.GlobalAlloc.restype = wintypes.HGLOBAL
        k.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k.GlobalLock.restype = wintypes.LPVOID
        k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        k.GlobalFree.argtypes = [wintypes.HGLOBAL]

    def sequence_number(self) -> int:
        return int(self._u.GetClipboardSequenceNumber())

    def _open(self) -> bool:
        for _ in range(15):
            if self._u.OpenClipboard(None):
                return True
            time.sleep(0.01)
        return False

    def read_text(self) -> Optional[str]:
        if not self._open():
            return None
        try:
            handle = self._u.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            pointer = self._k.GlobalLock(handle)
            if not pointer:
                return None
            try:
                return ctypes.wstring_at(pointer)
            finally:
                self._k.GlobalUnlock(handle)
        finally:
            self._u.CloseClipboard()

    def write_text(self, text: str) -> bool:
        data = (text + "\0").encode("utf-16-le")
        if not self._open():
            return False
        try:
            self._u.EmptyClipboard()
            handle = self._k.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not handle:
                return False
            pointer = self._k.GlobalLock(handle)
            if not pointer:
                self._k.GlobalFree(handle)
                return False
            ctypes.memmove(pointer, data, len(data))
            self._k.GlobalUnlock(handle)
            if not self._u.SetClipboardData(CF_UNICODETEXT, handle):
                self._k.GlobalFree(handle)
                return False
            return True  # the system owns the memory now
        finally:
            self._u.CloseClipboard()

    def _held(self, vk: int) -> bool:
        return bool(self._u.GetAsyncKeyState(vk) & 0x8000)

    def wait_modifiers_released(self, timeout: float) -> bool:
        """Wait until Shift/Alt/Win (and Ctrl) from the hotkey are physically released."""
        deadline = time.monotonic() + timeout
        keys = (VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN, VK_CONTROL)
        while time.monotonic() < deadline:
            if not any(self._held(vk) for vk in keys):
                return True
            time.sleep(0.01)
        return False

    def send_copy(self) -> bool:
        def key(vk: int, up: bool = False) -> INPUT:
            return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP if up else 0, 0, 0))

        events = (INPUT * 4)(key(VK_CONTROL), key(VK_C), key(VK_C, True), key(VK_CONTROL, True))
        return int(self._u.SendInput(4, events, ctypes.sizeof(INPUT))) == 4
