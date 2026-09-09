"""System-wide (global) hotkey registration for Windows.

Qt has no cross-platform global-hotkey API, and QShortcut only fires while
the owning window has focus - useless for a capture tool whose entire
reason to exist is capturing whatever else has focus (issue TA-211: Alt+P,
Alt+Shift+P and Alt+V were advertised in tooltips, a hint label and
help.html, and bound to nothing anywhere). This wraps the Win32
RegisterHotKey/UnregisterHotKey API directly via ctypes - no new dependency
- dispatched through a QAbstractNativeEventFilter that watches for
WM_HOTKEY on the thread's own message queue.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
# Without this, holding the combo down re-fires WM_HOTKEY on every OS
# key-repeat tick - a held Alt+P would queue up many captures instead of one.
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312


class GlobalHotkeyManager(QObject, QAbstractNativeEventFilter):
    """Registers global hotkeys and emits `triggered(id)` for each one that
    fires.

    `register()` must be called after a QApplication exists, from the
    thread whose message queue will receive WM_HOTKEY - Qt's main thread
    satisfies both. A caller picks its own small integer ids (unique
    within this process) to tell fired hotkeys apart in `triggered`.
    """

    triggered = Signal(int)

    def __init__(self, app, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._registered_ids: set[int] = set()
        app.installNativeEventFilter(self)

    def register(self, hotkey_id: int, modifiers: int, virtual_key: int) -> bool:
        """Attempt to claim a hotkey. Returns False - never raises - if
        another application (or another process of this one) already owns
        the combination. Deciding what to do about that (surface it, stop
        advertising the shortcut) is the caller's job, not this class's."""
        ok = bool(
            ctypes.windll.user32.RegisterHotKey(
                None, hotkey_id, modifiers | MOD_NOREPEAT, virtual_key,
            )
        )
        if ok:
            self._registered_ids.add(hotkey_id)
        return ok

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registered_ids):
            ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
        self._registered_ids.clear()

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self.triggered.emit(msg.wParam)
        return False, 0
