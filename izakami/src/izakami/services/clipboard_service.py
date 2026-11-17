"""Capture a highlighted price from another application via a simulated Ctrl+C."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional, Protocol

from ..core.validation import ValidationError, parse_price_text

log = logging.getLogger("izakami.clipboard")

KIND_ENTRY = "entry"
KIND_STOP = "stop"


class ClipboardBackend(Protocol):
    def sequence_number(self) -> int: ...
    def read_text(self) -> Optional[str]: ...
    def write_text(self, text: str) -> bool: ...
    def send_copy(self) -> bool: ...
    def wait_modifiers_released(self, timeout: float) -> bool: ...


@dataclass
class CaptureOutcome:
    kind: str
    ok: bool
    message: str
    value: Optional[Decimal] = None
    raw_text: Optional[str] = None


def capture_price(
    backend: ClipboardBackend,
    kind: str,
    *,
    restore_clipboard: bool = True,
    release_timeout: float = 1.5,
    copy_timeout: float = 0.8,
    poll: float = 0.015,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> CaptureOutcome:
    """Send Ctrl+C to the focused application and read the result.

    The clipboard *sequence number* decides whether anything was copied, so re-copying an
    identical value still counts. The previous text clipboard is put back afterwards.
    """
    label = "Entry" if kind == KIND_ENTRY else "Stop Loss"
    previous = backend.read_text() if restore_clipboard else None
    before = backend.sequence_number()

    # The user is still holding the shortcut's modifiers; wait so the target app sees a clean Ctrl+C.
    if not backend.wait_modifiers_released(release_timeout):
        return CaptureOutcome(kind, False, "Release the shortcut keys and try again.")
    if not backend.send_copy():
        return CaptureOutcome(kind, False, "Could not send Ctrl+C to the active application.")

    deadline = clock() + copy_timeout
    while backend.sequence_number() == before and clock() < deadline:
        sleep(poll)
    if backend.sequence_number() == before:
        return CaptureOutcome(
            kind, False,
            f"{label} not captured: nothing was copied. The selected text may not be copyable "
            "(chart-drawn labels often aren't).",
        )

    text: Optional[str] = None
    for _ in range(5):  # some applications fill the clipboard a moment after announcing it
        text = backend.read_text()
        if text:
            break
        sleep(poll)

    try:
        value = parse_price_text(text, label)
        outcome = CaptureOutcome(kind, True, f"{label} captured: {value.normalize():f}", value, text)
    except ValidationError as exc:
        outcome = CaptureOutcome(kind, False, f"{label} not changed. {exc}", None, text)

    if restore_clipboard and previous is not None:
        backend.write_text(previous)
    return outcome


class CaptureController:
    """Runs captures on a worker thread (never blocks the GUI) and ignores overlapping presses."""

    def __init__(
        self,
        backend: ClipboardBackend,
        restore_provider: Callable[[], bool] = lambda: True,
    ) -> None:
        self._backend = backend
        self._restore = restore_provider
        self._lock = threading.Lock()
        self.on_done: Optional[Callable[[CaptureOutcome], None]] = None

    def start(self, kind: str) -> bool:
        """Begin a capture. Returns False if one is already running."""
        if not self._lock.acquire(blocking=False):
            return False
        threading.Thread(target=self._run, args=(kind,), daemon=True, name="izakami-capture").start()
        return True

    def _run(self, kind: str) -> None:
        try:
            outcome = capture_price(self._backend, kind, restore_clipboard=self._restore())
        except Exception:
            log.exception("Clipboard capture failed")
            outcome = CaptureOutcome(kind, False, "Clipboard capture failed. See the log for details.")
        finally:
            self._lock.release()
        callback = self.on_done
        if callback is not None:
            try:
                callback(outcome)
            except Exception:
                log.exception("Capture callback failed")
