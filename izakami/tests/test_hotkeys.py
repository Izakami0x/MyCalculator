import threading
import time
from decimal import Decimal as D

import pytest

from izakami.core.validation import ValidationError
from izakami.services.clipboard_service import CaptureController, capture_price
from izakami.services.hotkey_service import (
    ACTION_COPY, ACTION_ENTRY, ACTION_STOP, HotkeyService, parse_shortcut, validate_bindings)


def test_parse_shortcut_normalises():
    sc = parse_shortcut("shift+CTRL+e")
    assert sc.text == "Ctrl+Shift+E" and sc.vk == ord("E") and sc.modifiers == 0x2 | 0x4
    assert parse_shortcut("Ctrl+F5").vk == 0x74 and parse_shortcut("Alt+Del").text == "Alt+Delete"


@pytest.mark.parametrize("text", ["", "E", "Ctrl+", "Ctrl+Shift", "Hyper+E", "Ctrl+Banana"])
def test_parse_shortcut_rejects(text):
    with pytest.raises(ValidationError):
        parse_shortcut(text)


def test_conflicts_and_reserved():
    valid, errors = validate_bindings({ACTION_ENTRY: "Ctrl+Shift+E", ACTION_STOP: "ctrl+shift+e", ACTION_COPY: "Ctrl+C"})
    assert list(valid) == [ACTION_ENTRY]
    assert "already used" in errors[ACTION_STOP] and "reserved" in errors[ACTION_COPY]


class FakeHotkeyBackend:
    def __init__(self, callback, fail=()):
        self.callback, self.fail, self.registered, self.calls = callback, set(fail), {}, 0

    def register(self, bindings):
        self.calls += 1
        self.registered = dict(bindings)
        return {a: ("already in use by another application" if a in self.fail else None) for a in bindings}

    def unregister_all(self):
        self.registered = {}


def test_service_registers_and_reports_failures():
    holder = {}
    def factory(cb):
        holder["b"] = FakeHotkeyBackend(cb, fail={ACTION_STOP})
        return holder["b"]
    svc = HotkeyService(factory)
    res = svc.apply({ACTION_ENTRY: "Ctrl+Shift+E", ACTION_STOP: "Ctrl+Shift+S", ACTION_COPY: "Ctrl+Shift+C"})
    assert res.registered == [ACTION_ENTRY, ACTION_COPY] and "in use" in res.errors[ACTION_STOP]
    got = []
    svc.on_trigger = got.append
    holder["b"].callback(ACTION_ENTRY)
    assert got == [ACTION_ENTRY]
    svc.shutdown()
    assert holder["b"].registered == {}


def test_service_without_backend_still_validates():
    svc = HotkeyService(None)
    assert not svc.supported
    assert ACTION_COPY in svc.apply({ACTION_COPY: "nonsense"}).errors


class FakeClipboard:
    def __init__(self, text="previous", copies="95,000.50", released=True, changes=True):
        self.text, self.seq, self.copies, self.released, self.changes = text, 1, copies, released, changes
        self.sent = 0

    def sequence_number(self): return self.seq
    def read_text(self): return self.text
    def write_text(self, t): self.text, self.seq = t, self.seq + 1; return True
    def wait_modifiers_released(self, timeout): return self.released
    def send_copy(self):
        self.sent += 1
        if self.changes:
            self.text, self.seq = self.copies, self.seq + 1
        return True


FAST = dict(sleep=lambda s: None, clock=iter(range(0, 10**6)).__next__, copy_timeout=3)


def test_capture_success_restores_previous_clipboard():
    cb = FakeClipboard()
    out = capture_price(cb, "entry", **FAST)
    assert out.ok and out.value == D("95000.50") and cb.text == "previous"


def test_capture_invalid_text_does_not_produce_a_value():
    out = capture_price(FakeClipboard(copies="hello world"), "stop", **FAST)
    assert not out.ok and out.value is None and "Stop Loss not changed" in out.message


def test_capture_detects_unchanged_clipboard():
    out = capture_price(FakeClipboard(changes=False), "entry", **FAST)
    assert not out.ok and "nothing was copied" in out.message


def test_capture_same_value_copied_again_still_counts():
    out = capture_price(FakeClipboard(text="1.0850", copies="1.0850"), "entry", **FAST)
    assert out.ok and out.value == D("1.0850")


def test_capture_waits_for_modifiers():
    cb = FakeClipboard(released=False)
    out = capture_price(cb, "entry", **FAST)
    assert not out.ok and cb.sent == 0


def test_controller_ignores_overlapping_presses():
    gate, done = threading.Event(), []

    class Slow(FakeClipboard):
        def wait_modifiers_released(self, timeout):
            gate.wait(2)
            return True

    ctl = CaptureController(Slow())
    ctl.on_done = done.append
    assert ctl.start("entry") is True
    assert ctl.start("entry") is False  # repeated press while busy
    gate.set()
    for _ in range(200):
        if done:
            break
        time.sleep(0.01)
    assert len(done) == 1 and done[0].ok
    assert ctl.start("stop") is True  # free again
