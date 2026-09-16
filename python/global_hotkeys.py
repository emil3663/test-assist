"""System-wide (global) hotkey registration.

Qt has no cross-platform global-hotkey API, and QShortcut only fires while
the owning window has focus - useless for a capture tool whose entire
reason to exist is capturing whatever else has focus (issue TA-211: Alt+P,
Alt+Shift+P and Alt+V were advertised in tooltips, a hint label and
help.html, and bound to nothing anywhere).

`GlobalHotkeyManager` is the single interface callers use; the platform
detail sits behind it in one backend per OS:

- Windows: the Win32 RegisterHotKey/UnregisterHotKey API via ctypes,
  dispatched through a QAbstractNativeEventFilter that watches for
  WM_HOTKEY on the thread's own message queue.
- macOS: Carbon's RegisterEventHotKey with an InstallEventHandler
  callback. Carbon is deprecated but is still the only documented way to
  claim a system-wide hotkey without Accessibility permission - a
  CGEventTap would work too, but costs the user a trip to System Settings
  and a TCC prompt for a feature that is meant to be incidental.
- Anywhere else (Linux/X11/Wayland): no backend. `register()` returns
  False rather than raising, which is already the contract for "another
  app owns this combination" - so the launcher's existing handling
  (`_apply_hotkey_labels`, `_report_hotkey_registration_failure`) stops
  advertising a shortcut that does not work, with no new code.

The modifier constants are platform-neutral names with the Win32 values,
kept because that is what callers already pass; each backend translates
them to whatever its own API wants. Virtual keys are likewise passed as
the Windows VK codes the callers already use (`ord("P")`), and translated
per backend - a VK code is ASCII for A-Z and 0-9, which is what makes
that translation a plain lookup rather than a keyboard-layout question.
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
# Without this, holding the combo down re-fires WM_HOTKEY on every OS
# key-repeat tick - a held Alt+P would queue up many captures instead of one.
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312


class _NullBackend:
    """No global-hotkey support on this platform.

    Deliberately not an error: a capture tool without hotkeys is still a
    capture tool, and `register()` returning False is already the signal
    callers handle for a combination they could not claim.
    """

    def register(self, hotkey_id: int, modifiers: int, virtual_key: int) -> bool:
        return False

    def unregister_all(self) -> None:
        pass


class _WindowsBackend(QAbstractNativeEventFilter):
    """Win32 RegisterHotKey, dispatched off the thread's message queue."""

    def __init__(self, app, on_triggered) -> None:
        QAbstractNativeEventFilter.__init__(self)
        self._on_triggered = on_triggered
        self._registered_ids: set[int] = set()
        app.installNativeEventFilter(self)

    def register(self, hotkey_id: int, modifiers: int, virtual_key: int) -> bool:
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
        from ctypes import wintypes
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self._on_triggered(msg.wParam)
        return False, 0


# Carbon's own modifier bits (Events.h). Nothing to do with the MOD_*
# values above, which are Win32's.
_CARBON_CMD = 0x0100
_CARBON_SHIFT = 0x0200
_CARBON_OPTION = 0x0800
_CARBON_CONTROL = 0x1000

# Carbon virtual keycodes are positional, not character codes, so A-Z and
# 0-9 need a real lookup rather than arithmetic (kVK_ANSI_* in Events.h).
_MAC_VK = {
    "A": 0x00, "B": 0x0B, "C": 0x08, "D": 0x02, "E": 0x0E, "F": 0x03,
    "G": 0x05, "H": 0x04, "I": 0x22, "J": 0x26, "K": 0x28, "L": 0x25,
    "M": 0x2E, "N": 0x2D, "O": 0x1F, "P": 0x23, "Q": 0x0C, "R": 0x0F,
    "S": 0x01, "T": 0x11, "U": 0x20, "V": 0x09, "W": 0x0D, "X": 0x07,
    "Y": 0x10, "Z": 0x06,
    "0": 0x1D, "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15,
    "5": 0x17, "6": 0x16, "7": 0x1A, "8": 0x1C, "9": 0x19,
}

_EVENT_CLASS_KEYBOARD = 0x6B657962   # 'keyb'
_EVENT_HOTKEY_PRESSED = 5
_PARAM_DIRECT_OBJECT = 0x2D2D2D2D    # '----'
_TYPE_EVENT_HOTKEY_ID = 0x686B6964   # 'hkid'
_SIGNATURE = 0x54534153              # 'TSAS' - Test ASSist


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _MacBackend:
    """Carbon RegisterEventHotKey.

    The handler is installed on the application event target, so it fires
    off the same CFRunLoop Qt already drives on macOS - no extra thread
    and no polling. The callback trampoline is kept alive on the instance
    on purpose: ctypes callbacks are garbage-collected like any other
    object, and letting one be collected while Carbon still holds the
    pointer is a crash, not a missed keystroke.
    """

    def __init__(self, app, on_triggered) -> None:
        self._on_triggered = on_triggered
        self._refs: dict[int, ctypes.c_void_p] = {}
        self._carbon = ctypes.CDLL(
            "/System/Library/Frameworks/Carbon.framework/Carbon"
        )
        self._carbon.GetApplicationEventTarget.restype = ctypes.c_void_p

        proto = ctypes.CFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )
        self._trampoline = proto(self._handle_event)

        spec = _EventTypeSpec(_EVENT_CLASS_KEYBOARD, _EVENT_HOTKEY_PRESSED)
        handler_ref = ctypes.c_void_p()
        self._carbon.InstallEventHandler(
            ctypes.c_void_p(self._carbon.GetApplicationEventTarget()),
            self._trampoline,
            1,
            ctypes.byref(spec),
            None,
            ctypes.byref(handler_ref),
        )
        self._handler_ref = handler_ref

    def _handle_event(self, next_handler, event, user_data):
        hotkey_id = _EventHotKeyID()
        status = self._carbon.GetEventParameter(
            ctypes.c_void_p(event),
            ctypes.c_uint32(_PARAM_DIRECT_OBJECT),
            ctypes.c_uint32(_TYPE_EVENT_HOTKEY_ID),
            None,
            ctypes.c_uint32(ctypes.sizeof(_EventHotKeyID)),
            None,
            ctypes.byref(hotkey_id),
        )
        if status == 0:
            self._on_triggered(int(hotkey_id.id))
        return 0

    def register(self, hotkey_id: int, modifiers: int, virtual_key: int) -> bool:
        try:
            key_char = chr(virtual_key).upper()
        except ValueError:
            return False
        keycode = _MAC_VK.get(key_char)
        if keycode is None:
            return False

        carbon_modifiers = 0
        # Alt is the Option key on a Mac keyboard; Win32's MOD_WIN is the
        # nearest thing to Command, which is what a Mac user reaches for.
        if modifiers & MOD_ALT:
            carbon_modifiers |= _CARBON_OPTION
        if modifiers & MOD_SHIFT:
            carbon_modifiers |= _CARBON_SHIFT
        if modifiers & MOD_CONTROL:
            carbon_modifiers |= _CARBON_CONTROL
        if modifiers & MOD_WIN:
            carbon_modifiers |= _CARBON_CMD

        ref = ctypes.c_void_p()
        status = self._carbon.RegisterEventHotKey(
            ctypes.c_uint32(keycode),
            ctypes.c_uint32(carbon_modifiers),
            _EventHotKeyID(_SIGNATURE, hotkey_id),
            ctypes.c_void_p(self._carbon.GetApplicationEventTarget()),
            0,
            ctypes.byref(ref),
        )
        if status != 0:
            return False
        self._refs[hotkey_id] = ref
        return True

    def unregister_all(self) -> None:
        for ref in self._refs.values():
            self._carbon.UnregisterEventHotKey(ref)
        self._refs.clear()


def _make_backend(app, on_triggered):
    """Pick a backend for this platform, degrading to none rather than
    raising: an unsupported platform must cost the hotkeys, not the app."""
    try:
        if sys.platform == "win32":
            return _WindowsBackend(app, on_triggered)
        if sys.platform == "darwin":
            return _MacBackend(app, on_triggered)
    except Exception:
        return _NullBackend()
    return _NullBackend()


class GlobalHotkeyManager(QObject):
    """Registers global hotkeys and emits `triggered(id)` for each one that
    fires.

    `register()` must be called after a QApplication exists, from the
    thread whose event loop will receive the OS notification - Qt's main
    thread satisfies both on every supported platform. A caller picks its
    own small integer ids (unique within this process) to tell fired
    hotkeys apart in `triggered`.
    """

    triggered = Signal(int)

    def __init__(self, app, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        self._backend = _make_backend(app, self.triggered.emit)

    @property
    def backend_name(self) -> str:
        """Which backend is in play - for the About dialog's bug-report
        details, so "the hotkeys do nothing" reports say which path ran."""
        return type(self._backend).__name__

    def register(self, hotkey_id: int, modifiers: int, virtual_key: int) -> bool:
        """Attempt to claim a hotkey. Returns False - never raises - if
        another application (or another process of this one) already owns
        the combination, or if this platform has no backend. Deciding what
        to do about that (surface it, stop advertising the shortcut) is the
        caller's job, not this class's."""
        try:
            return self._backend.register(hotkey_id, modifiers, virtual_key)
        except Exception:
            return False

    def nativeEventFilter(self, event_type, message):
        """Delegate to the backend's own filter.

        Kept on the manager rather than left to the backend alone because
        that is the surface TA-211's dispatch tests already drive
        (`launcher._hotkeys.nativeEventFilter(...)`), and those tests run
        only on Windows - so a refactor that quietly moved the method
        would go green on every other platform and break the one that
        actually exercises it. Returns the same (handled, result) pair Qt
        expects, and a plain "not handled" when the backend has no filter
        of its own.
        """
        handler = getattr(self._backend, "nativeEventFilter", None)
        if handler is None:
            return False, 0
        return handler(event_type, message)

    def unregister_all(self) -> None:
        try:
            self._backend.unregister_all()
        except Exception:
            pass
