"""TA-228: three small, black-box checks against the real packaged exe.

Every other test in this project imports python/'s modules directly into
the test process - real Qt signal/slot wiring, but still one process, one
Qt event loop, Qt's own idea of window state. That is exactly why TA-220's
minimize-toggle gap and TA-217's hotkey-capture gap are still
"instrumented, not fixed": nothing in-process can observe what the real
Windows window manager does with a real separate top-level window under
real focus/Z-order rules. These three checks are deliberately small - a
first slice proving the approach works, not an attempt at broad coverage.
See TESTASSIST_BACKLOG.md's TA-228 and this directory's README.md.
"""
from __future__ import annotations

import time


def test_app_launches_and_shows_its_window(launcher) -> None:
    """Check 1: the app launches and its main window appears within a
    timeout. The launcher fixture's own wait() already had to succeed for
    this test to even start - asserted again here, explicitly, so this is
    a named, reportable claim rather than an implicit side effect of a
    fixture."""
    assert launcher.is_visible()


def test_quick_capture_button_produces_a_real_overlay_window(app, launcher) -> None:
    """Check 2: clicking the real Quick Capture button produces a real,
    visible overlay window - observed from outside the process via the
    OS's own window list (app.windows()), not asserted from inside it.
    Proves the _start_capture() -> 220ms singleShot -> _overlay.activate()
    chain produces a window a real user would actually see, the thing an
    in-process test stubbing _start_capture() (TA-227's own finding)
    structurally cannot prove.
    """
    launcher_rect = launcher.rectangle()
    launcher_area = launcher_rect.width() * launcher_rect.height()

    button = launcher.child_window(title="Quick Capture", control_type="Button")
    button.wait("visible enabled", timeout=5)
    button.click_input()

    # The overlay covers the whole virtual desktop - many times the
    # launcher panel's own area, a generous multiple to avoid a flaky
    # exact-size match against whatever the real screen geometry is.
    deadline = time.time() + 5
    overlay_seen = False
    while time.time() < deadline and not overlay_seen:
        for window in app.windows():
            if not window.is_visible():
                continue
            rect = window.rectangle()
            if rect.width() * rect.height() > launcher_area * 4:
                overlay_seen = True
                break
        if not overlay_seen:
            time.sleep(0.2)

    assert overlay_seen, (
        "no new, visible, desktop-sized overlay window appeared after "
        "clicking Quick Capture - a real user would see nothing happen"
    )


def test_ta_icon_minimizes_and_restores_a_real_os_window(app, launcher) -> None:
    """Check 3: minimize/restore via the TA icon changes the *real* OS
    window state - pywinauto's own is_minimized()/is_normal() (backed by
    UI Automation's WindowVisualState, which Windows derives from actual
    window state), not Qt's internal windowState() flags this suite has
    only ever been able to check in-process. The direct test of TA-220's
    still-unconfirmed hypothesis: the click that triggers this happens on
    a *different* top-level window (the launcher) than the one being
    minimized (the editor), which is exactly the timing this project's
    in-process tests cannot observe.
    """
    open_editor = launcher.child_window(title="Open Editor", control_type="Button")
    open_editor.wait("visible enabled", timeout=5)
    open_editor.click_input()

    editor = app.window(title_re=".*Editor.*")
    editor.wait("visible", timeout=10)
    assert editor.is_normal(), "the editor should open in its normal state, not already minimized"

    open_editor.click_input()  # TA icon again, editor active -> should minimize
    deadline = time.time() + 5
    minimized = False
    while time.time() < deadline:
        if editor.is_minimized():
            minimized = True
            break
        time.sleep(0.2)
    assert minimized, (
        "clicking the TA icon while the editor is the active window must "
        "minimize the real OS window state - Qt's own internal flags "
        "cannot stand in for this"
    )

    open_editor.click_input()  # TA icon again -> should restore
    deadline = time.time() + 5
    restored = False
    while time.time() < deadline:
        if not editor.is_minimized():
            restored = True
            break
        time.sleep(0.2)
    assert restored, "clicking the TA icon again must restore the real OS window"
