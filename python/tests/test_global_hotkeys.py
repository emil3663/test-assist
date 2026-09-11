"""Platform dispatch for global hotkeys.

Everything here is deliberately platform-independent: the Win32 and Carbon
APIs themselves are covered by the `skipif`-guarded tests in
`test_regressions.py`, which only ever run on the OS that owns them. The
gap that leaves - and what this file closes - is that a refactor of the
*dispatch* layer can go green on every platform while breaking the one
backend nobody's CI ran.
"""
from __future__ import annotations

import sys

import pytest

import global_hotkeys as gh


class _ExplodingBackend:
    """A backend where every call raises, to prove the manager's contract
    ("returns False, never raises") is the manager's own and does not
    depend on a well-behaved backend."""

    def register(self, hotkey_id, modifiers, virtual_key):
        raise RuntimeError("backend exploded")

    def unregister_all(self):
        raise RuntimeError("backend exploded")


class _RecordingBackend:
    def __init__(self) -> None:
        self.seen: list[tuple] = []

    def register(self, hotkey_id, modifiers, virtual_key):
        return True

    def unregister_all(self):
        pass

    def nativeEventFilter(self, event_type, message):
        self.seen.append((event_type, message))
        return False, 0


def test_null_backend_declines_rather_than_raising() -> None:
    """A platform with no backend must cost the hotkeys, not the app - so
    register() reports failure through the same False the callers already
    handle for "another app owns this combination"."""
    backend = gh._NullBackend()
    assert backend.register(1, gh.MOD_ALT, ord("P")) is False
    backend.unregister_all()


def test_manager_never_raises_even_when_its_backend_does(qapp) -> None:
    manager = gh.GlobalHotkeyManager(qapp)
    manager._backend = _ExplodingBackend()
    assert manager.register(1, gh.MOD_ALT, ord("P")) is False
    manager.unregister_all()


def test_native_event_filter_delegates_to_the_backend(qapp) -> None:
    """TA-211's dispatch tests drive `_hotkeys.nativeEventFilter(...)`, and
    they run on Windows only. This pins the delegation itself everywhere."""
    manager = gh.GlobalHotkeyManager(qapp)
    backend = _RecordingBackend()
    manager._backend = backend

    assert manager.nativeEventFilter(b"windows_generic_MSG", 4242) == (False, 0)
    assert backend.seen == [(b"windows_generic_MSG", 4242)]


def test_native_event_filter_is_qt_shaped_without_a_backend_filter(qapp) -> None:
    """Qt expects a (handled, result) pair from every call. A backend with
    no filter of its own - the null and Carbon ones - must not turn that
    into a None the event loop then has to cope with."""
    manager = gh.GlobalHotkeyManager(qapp)
    manager._backend = gh._NullBackend()
    assert manager.nativeEventFilter(b"anything", 0) == (False, 0)


def test_backend_reports_its_own_name(qapp) -> None:
    """The About dialog's bug-report details name the backend, so a
    "hotkeys do nothing" report says which path actually ran."""
    manager = gh.GlobalHotkeyManager(qapp)
    assert manager.backend_name in {
        "_WindowsBackend", "_MacBackend", "_NullBackend",
    }


def test_macos_keycode_table_covers_every_key_a_caller_can_ask_for() -> None:
    """Carbon keycodes are positional, so A-Z and 0-9 are a lookup rather
    than arithmetic - an incomplete table would fail a specific key only,
    which is exactly the kind of gap a spot check misses."""
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        assert char in gh._MAC_VK, f"{char} missing from the Carbon keycode table"
    assert len(set(gh._MAC_VK.values())) == len(gh._MAC_VK), "duplicate keycodes"


def test_the_three_advertised_shortcuts_are_translatable_on_macos() -> None:
    """TA-211's three combinations are the ones the UI advertises; if any
    one of them cannot be expressed on a Mac, the tooltip lies there too."""
    for key in ("P", "V"):
        assert chr(ord(key)).upper() in gh._MAC_VK


@pytest.mark.skipif(sys.platform != "darwin", reason="Carbon is a macOS API")
def test_macos_selects_the_carbon_backend(qapp) -> None:
    manager = gh.GlobalHotkeyManager(qapp)
    assert manager.backend_name == "_MacBackend"


@pytest.mark.skipif(sys.platform != "darwin", reason="Carbon is a macOS API")
def test_macos_declines_a_key_it_has_no_keycode_for(qapp) -> None:
    """A key outside the table must be declined, not registered wrong -
    silently claiming the wrong key is worse than claiming none."""
    manager = gh.GlobalHotkeyManager(qapp)
    assert manager.register(99, gh.MOD_ALT, ord("[")) is False


@pytest.mark.skipif(sys.platform != "win32", reason="RegisterHotKey is a Win32 API")
def test_windows_selects_the_win32_backend(qapp) -> None:
    manager = gh.GlobalHotkeyManager(qapp)
    assert manager.backend_name == "_WindowsBackend"
