from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QMessageBox, QPushButton, QTabWidget, QWidget

from canvas import AnnotationCanvas
from editor import EditorWindow
from launcher import FloatingLauncher
from update_check import UpdateResult


@dataclass
class _MouseEventStub:
    x: float
    y: float

    def position(self) -> QPointF:
        return QPointF(self.x, self.y)


def _typed_event(char: str) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, char)


def _key_event(key: Qt.Key, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, modifiers)


class _EditorStub:
    def __init__(self) -> None:
        self.bring_forward_calls = 0
        self.loaded = []
        self.recorded = []

    def bring_forward(self) -> None:
        self.bring_forward_calls += 1

    def load_pixmap(self, pixmap, background: bool = True) -> None:
        self.loaded.append((pixmap, background))

    def record_capture(self, pixmap) -> None:
        self.recorded.append(pixmap)


def _canvas_with_image(qapp, blank_pixmap) -> AnnotationCanvas:
    canvas = AnnotationCanvas()
    canvas.set_pixmap(blank_pixmap)
    canvas.show()
    qapp.processEvents()
    return canvas


def test_editor_keyPressEvent_text_typing_preserves_letters(qapp, blank_pixmap) -> None:
    editor = EditorWindow()
    editor.load_pixmap(blank_pixmap, background=False)
    editor._canvas._start_text_edit(QPointF(24, 24))
    qapp.processEvents()

    assert editor._tool_shortcuts
    assert all(not shortcut.isEnabled() for shortcut in editor._tool_shortcuts)

    expected = "qwertyuiopasdfghjklzxcvbnm"
    for char in expected:
        editor.keyPressEvent(_typed_event(char))

    assert editor._canvas._text_buffer == expected

    editor._canvas._commit_text()
    qapp.processEvents()
    assert all(shortcut.isEnabled() for shortcut in editor._tool_shortcuts)
    editor.close()


def test_canvas_mousePressEvent_clicking_empty_space_clears_selection(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas._push({
        "type": "rect",
        "x1": 10,
        "y1": 10,
        "x2": 90,
        "y2": 70,
        "color": "#ff3b30",
        "size": 3,
        "opacity": 0.3,
    })

    canvas.tool = "select"
    # Selecting happens on the border. (30, 20) is on the top edge and clear of
    # both the top-left corner handle and the top-edge midpoint handle.
    canvas.mousePressEvent(_MouseEventStub(30, 10))
    assert canvas._selected is not None, "a click on the border should select"

    canvas.mousePressEvent(_MouseEventStub(200, 200))
    assert canvas._selected is None
    canvas.close()


def test_canvas_mouseMoveEvent_text_corner_drag_resizes_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas._push({
        "type": "text",
        "x1": 40,
        "y1": 40,
        "width": 100,
        "height": 30,
        "color": "#000000",
        "size": 3,
        "text": "hello world",
    })
    text = canvas._annotations[0]

    handle_x = text["x1"] + text["width"] + 4
    handle_y = text["y1"] + text["height"] + 4

    # Arm the drag through the real entry point, so the pre-drag snapshot the
    # resize maths works from is taken exactly as a press would take it. Going
    # through mousePressEvent directly would risk the text edit dialog.
    canvas._begin_selection_drag(text, "br", QPointF(handle_x, handle_y))

    canvas.mouseMoveEvent(_MouseEventStub(handle_x + 28, handle_y + 18))
    canvas.mouseReleaseEvent(_MouseEventStub(handle_x + 28, handle_y + 18))

    assert text["width"] > 100
    assert text["height"] > 30
    canvas.close()


def test_canvas_mouseMoveEvent_existing_annotation_drags_without_select_tool(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas._push({
        "type": "rect",
        "x1": 20,
        "y1": 20,
        "x2": 80,
        "y2": 60,
        "color": "#ff3b30",
        "size": 3,
        "opacity": 0.3,
    })
    rect = canvas._annotations[0]
    canvas.tool = "rect"

    before = dict(rect)
    canvas.mousePressEvent(_MouseEventStub(40, 40))
    canvas.mouseMoveEvent(_MouseEventStub(75, 90))
    canvas.mouseReleaseEvent(_MouseEventStub(75, 90))

    assert rect == before
    assert len(canvas._annotations) == 2
    assert canvas._annotations[-1]["type"] == "rect"
    canvas.close()


def test_canvas_send_selected_to_back_changes_topmost_hit_target(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas._push({
        "type": "rect",
        "x1": 20,
        "y1": 20,
        "x2": 100,
        "y2": 100,
        "color": "#111111",
        "size": 3,
        "opacity": 0.3,
    })
    canvas._push({
        "type": "circle",
        "x1": 40,
        "y1": 40,
        "x2": 120,
        "y2": 120,
        "color": "#222222",
        "size": 3,
        "opacity": 0.3,
    })

    # A point where both outlines pass: on the rectangle's right edge and, to
    # within the hit tolerance, on the ellipse too. Selection is border-based, so
    # the probe has to be somewhere both shapes are actually drawn.
    overlap = _MouseEventStub(100, 45)

    canvas.mouseDoubleClickEvent(overlap)
    topmost = canvas._selected
    assert topmost is canvas._annotations[1]

    canvas.send_selected_to_back()
    canvas._selected = None
    canvas.mouseDoubleClickEvent(overlap)

    assert canvas._selected is canvas._annotations[0]
    canvas.close()


def test_editor_tools_bar_has_uniform_cell_and_button_sizes(qapp) -> None:
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    tool_buttons = [
        btn for btn in editor._tool_group.buttons() if isinstance(btn, QPushButton)
    ]
    assert tool_buttons
    assert {btn.size().width() for btn in tool_buttons} == {44}
    assert {btn.size().height() for btn in tool_buttons} == {30}

    cells = {btn.parentWidget() for btn in tool_buttons if btn.parentWidget() is not None}
    assert cells
    for cell in cells:
        assert cell.width() == 64
        assert cell.height() == 74

    editor.close()


def test_editor_tools_bar_row_alignment_top_middle_bottom(qapp) -> None:
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    for btn in editor._tool_group.buttons():
        cell = btn.parentWidget()
        assert cell is not None

        labels = [w for w in cell.findChildren(QLabel) if w.text()]
        assert labels
        name_lbl = labels[0]

        bottom_candidates = [
            w for w in cell.findChildren(QWidget)
            if w is not name_lbl and w is not btn and w.width() == 44 and w.height() == 10
        ]
        assert bottom_candidates
        bottom_row = bottom_candidates[0]

        assert name_lbl.y() < btn.y() < bottom_row.y()

    editor.close()


def test_settings_bar_holds_the_controls_moved_out_of_the_right_panel(qapp) -> None:
    """Zoom, Stroke, Arrow, Highlight Fill, Save PNG, Copy and Export JSON
    moved out of the fixed-width right panel into a full-width row under
    the tool row - the panel had to fit them plus Edit and History, which
    squeezed History in particular."""
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    bar = editor.findChild(QFrame, "settings_bar")
    assert bar is not None, "no settings_bar was built"
    for widget in (
        editor._btn_zoom_out, editor._zoom_slider, editor._btn_zoom_in,
        editor._zoom_pct, editor._btn_fit, editor._size_slider, editor._size_lbl,
        editor._arrow_style_combo, editor._opacity_slider, editor._opacity_lbl,
        editor._btn_copy, editor._btn_export_json, editor._btn_save_png,
    ):
        assert widget.parentWidget() is bar, f"{widget} is not in the settings bar"

    panel = editor.findChild(QWidget, "right_panel")
    assert panel is not None, "no right_panel was built"
    assert editor._btn_zoom_out.parentWidget() is not panel
    assert editor._btn_save_png.parentWidget() is not panel

    editor.close()


def test_settings_bar_spans_the_full_window_width_not_just_the_dock_constrained_central_widget(qapp) -> None:
    """A real QDockWidget for the right panel claims its own width ahead of
    the central widget's layout, so a row placed inside that central widget
    can never reach full window width while the panel is a dock - that is
    exactly why the panel is a plain QWidget beside the canvas now, not a
    QDockWidget."""
    editor = EditorWindow()
    editor.resize(1400, 640)
    editor.show()
    qapp.processEvents()

    bar = editor.findChild(QFrame, "settings_bar")
    assert bar.width() == editor.centralWidget().width(), \
        "the settings bar should span the same width as the central widget, not be narrowed by a docked side panel"
    editor.close()


def test_settings_bar_does_not_clip_at_the_960_minimum_window_width(qapp) -> None:
    """"Do NOT put them between the tool row and the info/help buttons" -
    that gap is zero at the 960px minimum window width. A full-width row is
    what actually fits close to 900px of controls; this pins that it still
    does at the smallest window the app allows, rather than silently
    squeezing something (e.g. Save PNG) narrower than its own content."""
    editor = EditorWindow()
    editor.resize(960, 640)
    editor.show()
    qapp.processEvents()
    qapp.processEvents()

    bar = editor.findChild(QFrame, "settings_bar")
    assert bar.width() == 960
    assert bar.minimumSizeHint().width() <= bar.width(), \
        "the settings bar needs more room than the 960px minimum window provides"

    for widget in bar.findChildren(QWidget):
        if widget.parent() is not bar:
            continue
        natural = widget.minimumWidth() if widget.minimumWidth() > 0 else widget.sizeHint().width()
        assert widget.width() >= natural, \
            f"{widget!r} was squeezed to {widget.width()}px, narrower than its own {natural}px - that is the clipping bug"

    editor.close()


def test_save_png_stays_visually_primary_in_the_settings_bar(qapp) -> None:
    """Moving Save PNG into a strip of other buttons must not demote it to
    just another button in that strip."""
    editor = EditorWindow()

    assert editor._btn_save_png.objectName() == "btn_primary"
    assert editor._btn_save_png.height() > editor._btn_copy.height()
    assert editor._btn_save_png.height() > editor._btn_export_json.height()

    editor.close()


def test_editor_history_header_opens_overlay(qapp, monkeypatch) -> None:
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    called = {"count": 0}

    def _fake_overlay() -> None:
        called["count"] += 1

    monkeypatch.setattr(editor, "_show_history_overlay", _fake_overlay)

    header_buttons = [
        btn for btn in editor.findChildren(QPushButton)
        if btn.objectName() == "section_title" and btn.text().strip().upper() == "HISTORY"
    ]
    assert header_buttons
    header_buttons[0].click()

    assert called["count"] == 1
    editor.close()


def test_editor_show_history_overlay_has_all_categories(qapp, blank_pixmap, monkeypatch) -> None:
    editor = EditorWindow()
    editor.load_pixmap(blank_pixmap, background=False)

    captured: dict[str, QDialog] = {}

    def _fake_exec(dialog: QDialog) -> int:
        captured["dialog"] = dialog
        return 0

    monkeypatch.setattr(QDialog, "exec", _fake_exec)
    editor._show_history_overlay()

    assert "dialog" in captured
    tabs = captured["dialog"].findChild(QTabWidget)
    assert tabs is not None
    assert [tabs.tabText(i) for i in range(tabs.count())] == [
        "Recent", "Today", "This Week", "This Month", "All",
    ]

    editor.close()


def test_editor_history_files_for_mode_all_and_recent(tmp_path: Path, qapp) -> None:
    editor = EditorWindow()
    editor._history_dir = tmp_path

    pixmap = QPixmap(120, 80)
    pixmap.fill(QColor("#dddddd"))
    for idx in range(7):
        assert pixmap.save(str(tmp_path / f"snapshot-{idx}.png"), "PNG")

    all_files = editor._history_files_for_mode("all")
    recent_files = editor._history_files_for_mode("recent")

    assert len(all_files) == 7
    assert len(recent_files) == 5
    editor.close()


def test_editor_persist_history_snapshot_skips_tiny_images(tmp_path: Path, qapp) -> None:
    editor = EditorWindow()
    editor._history_dir = tmp_path

    tiny = QPixmap(20, 20)
    tiny.fill(QColor("#ffffff"))
    editor._persist_history_snapshot(tiny)
    assert list(tmp_path.glob("*.png")) == []

    normal = QPixmap(120, 80)
    normal.fill(QColor("#ffffff"))
    editor._persist_history_snapshot(normal)
    assert len(list(tmp_path.glob("*.png"))) == 1

    editor.close()


def test_canvas_undo_crop_restores_original_canvas_size(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    original_size = canvas.size()

    canvas.tool = "crop"
    canvas.mousePressEvent(_MouseEventStub(10, 10))
    canvas.mouseMoveEvent(_MouseEventStub(120, 90))
    canvas.mouseReleaseEvent(_MouseEventStub(120, 90))

    assert canvas.width() < original_size.width()
    assert canvas.height() < original_size.height()

    canvas.undo()

    assert canvas.size() == original_size
    canvas.close()


def test_canvas_set_zoom_updates_widget_size(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    base_w, base_h = blank_pixmap.width(), blank_pixmap.height()

    canvas.set_zoom(1.5)

    assert canvas.width() == int(round(base_w * 1.5))
    assert canvas.height() == int(round(base_h * 1.5))
    canvas.close()


def test_canvas_fit_to_size_sets_zoom_to_fit(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)

    canvas.fit_to_size(qapp.primaryScreen().availableGeometry().size())

    assert 0.25 <= canvas.zoom() <= 4.0
    canvas.close()


def test_editor_copy_to_clipboard_copies_exported_pixmap(qapp, blank_pixmap) -> None:
    editor = EditorWindow()
    editor.load_pixmap(blank_pixmap, background=False)

    editor._copy_to_clipboard()
    copied = qapp.clipboard().pixmap()

    assert not copied.isNull()
    assert copied.size() == blank_pixmap.size()
    editor.close()


def test_editor_fit_image_reduces_zoom_for_large_image(qapp) -> None:
    editor = EditorWindow()
    large = QPixmap(2600, 1600)
    large.fill(QColor("#202020"))
    editor.resize(1000, 700)
    editor.load_pixmap(large, background=False)

    editor._fit_image()

    assert editor._canvas.zoom() < 1.0
    editor.close()


def test_launcher_build_ui_buttons_include_shortcut_hints(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    # Action button shows "Quick Capture" in photo mode
    assert launcher._btn_capture.text() == "Quick Capture"
    # register_global_hotkeys defaults to False (see TA-211 tests below for
    # why - real, shared OS state that every other launcher-constructing
    # test in this suite would otherwise fight over) - so nothing is
    # actually bound here, and the tooltips must not claim otherwise.
    assert "Alt+P" not in launcher._btn_photo.toolTip()
    assert "Alt+V" not in launcher._btn_video.toolTip()
    assert "Alt+Shift+P" not in launcher._btn_full_capture.toolTip()
    launcher.close()


# ── TA-211: global hotkeys ───────────────────────────────────────────────────
#
# Alt+P, Alt+Shift+P and Alt+V were advertised in these same tooltips, the
# hint label below the action row, and help.html's shortcut table, while
# bound to nothing anywhere - the previous version of the test just above
# this section asserted the tooltip *strings*, which is exactly how a claim
# with nothing behind it shipped and stayed green. Every test below
# exercises the real Win32 RegisterHotKey/UnregisterHotKey API - no
# substitution - since that binding, not a label, is the actual claim.

def test_TA211_global_hotkeys_register_and_are_advertised(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub(), register_global_hotkeys=True)
    try:
        assert launcher._hotkey_registered == {
            "photo": True, "full_capture": True, "video": True,
        }
        assert "(Alt+P)" in launcher._btn_photo.toolTip()
        assert "(Alt+Shift+P)" in launcher._btn_full_capture.toolTip()
        assert "(Alt+V)" in launcher._btn_video.toolTip()
        assert "Alt+P" in launcher._hint_lbl.text()
        assert "Alt+V" in launcher._hint_lbl.text()
    finally:
        launcher.close()


def test_TA211_global_hotkey_dispatch_routes_to_the_right_action(qapp) -> None:
    """The actual binding: a synthetic WM_HOTKEY (not a real OS-delivered
    key event, which this suite has no way to inject) must reach the same
    actions the old window-focused keyPressEvent used to call directly."""
    import ctypes
    from ctypes import wintypes

    from global_hotkeys import WM_HOTKEY

    launcher = FloatingLauncher(_EditorStub(), register_global_hotkeys=True)
    try:
        calls: list[str] = []
        launcher._start_capture = lambda: calls.append("photo")
        launcher._start_full_capture = lambda: calls.append("full_capture")
        launcher._toggle_recording = lambda: calls.append("video")

        for hotkey_id, expected_mode, expected_call in [
            (launcher._HOTKEY_PHOTO, "photo", "photo"),
            (launcher._HOTKEY_FULL_CAPTURE, "photo", "full_capture"),
            (launcher._HOTKEY_VIDEO, "video", "video"),
        ]:
            msg = wintypes.MSG()
            msg.message = WM_HOTKEY
            msg.wParam = hotkey_id
            launcher._hotkeys.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg))
            assert calls[-1] == expected_call
            assert launcher._mode == expected_mode
    finally:
        launcher.close()


def test_TA211_an_unrelated_native_message_is_ignored(qapp) -> None:
    """The event filter must not react to every native message - only
    WM_HOTKEY, and only for a registered id."""
    import ctypes
    from ctypes import wintypes

    launcher = FloatingLauncher(_EditorStub(), register_global_hotkeys=True)
    try:
        calls: list[str] = []
        launcher._start_capture = lambda: calls.append("photo")

        msg = wintypes.MSG()
        msg.message = 0x0010  # WM_CLOSE, not WM_HOTKEY
        msg.wParam = launcher._HOTKEY_PHOTO
        handled, _ = launcher._hotkeys.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg))

        assert calls == []
        assert handled is False
    finally:
        launcher.close()


def test_TA217_global_hotkey_closes_an_open_about_dialog_before_capturing(qapp, monkeypatch) -> None:
    """Confirmed mechanism: EditorWindow._open_about() shows its QDialog
    with setModal(True) (QDialog.exec() is a nested Qt event loop, which
    is why a global hotkey - a native OS message, not routed through
    Qt's own event queue - still reaches _on_global_hotkey() while it
    runs). Qt's own application-modal blocking would otherwise leave the
    freshly-shown capture overlay unable to receive the mouse input
    needed to drag a selection. The hotkey path must close the dialog
    before dispatching, not leave the user with a silently
    non-interactive overlay.
    """
    from PySide6.QtCore import QTimer

    editor = EditorWindow()
    launcher = FloatingLauncher(editor)

    calls: list[str] = []
    launcher._start_capture = lambda: calls.append("start_capture")

    # Spied rather than only checked by end state: without this, a
    # regression would still eventually "pass" once the safety net below
    # force-closes the dialog on its own timeout, masking exactly the
    # failure this test exists to catch.
    dismiss_calls: list[bool] = []
    real_dismiss = FloatingLauncher._dismiss_active_modal_dialog
    def _spy_dismiss():
        dismiss_calls.append(True)
        real_dismiss()
    monkeypatch.setattr(FloatingLauncher, "_dismiss_active_modal_dialog", staticmethod(_spy_dismiss))

    # Fires once the About dialog's nested event loop is actually
    # spinning - scheduling it before dlg.exec() even starts (rather than
    # calling it directly beforehand) is what exercises the real
    # reentrant mechanism, not just the end state.
    QTimer.singleShot(0, lambda: launcher._on_global_hotkey(launcher._HOTKEY_PHOTO))
    # Safety net, not part of the behaviour under test: verified by hand
    # while writing this test that without the fix, nothing ever closes
    # the dialog and _open_about() blocks forever, hanging the whole
    # suite rather than failing this one test. Force it closed well after
    # the hotkey path should have, so a regression fails this test in
    # ~2s instead of hanging indefinitely.
    QTimer.singleShot(2000, lambda: QApplication.activeModalWidget() and QApplication.activeModalWidget().close())
    editor._open_about()  # blocks until the dialog closes

    assert dismiss_calls, "the hotkey path must actually attempt to dismiss an open modal dialog"
    assert calls == ["start_capture"], \
        "the hotkey must still dispatch to a capture while the About dialog is open"
    assert QApplication.activeModalWidget() is None, \
        "the About dialog must be closed, not left open and still input-blocking"
    editor.close()
    launcher.close()


def test_TA211_a_failed_registration_is_surfaced_and_not_advertised(qapp) -> None:
    """RegisterHotKey fails when another application already owns the
    combination - simulated here by claiming Alt+P from the test itself
    before construction. The failure must be visible (not silent) and the
    tooltip/hint must stop claiming that specific shortcut, without
    affecting the other two that still registered fine."""
    import ctypes

    from global_hotkeys import MOD_ALT, MOD_NOREPEAT

    user32 = ctypes.windll.user32
    claim_id = 0xF00D
    assert user32.RegisterHotKey(None, claim_id, MOD_ALT | MOD_NOREPEAT, ord("P")), \
        "test setup: could not claim Alt+P to simulate a conflicting application"

    try:
        launcher = FloatingLauncher(_EditorStub(), register_global_hotkeys=True)
        try:
            assert launcher._hotkey_registered["photo"] is False
            assert launcher._hotkey_registered["full_capture"] is True, \
                "a conflict on one combination must not block the other two"
            assert launcher._hotkey_registered["video"] is True

            assert "Alt+P" not in launcher._btn_photo.toolTip()
            assert "(Alt+Shift+P)" in launcher._btn_full_capture.toolTip()
            assert "Alt+P" not in launcher._hint_lbl.text()

            assert launcher._status_lbl.isVisible()
            assert "Alt+P" in launcher._status_lbl.text()
        finally:
            launcher.close()
    finally:
        user32.UnregisterHotKey(None, claim_id)


def test_TA211_hotkeys_are_released_on_close(qapp) -> None:
    """A hotkey left registered after the launcher is gone would permanently
    deny that combination to every other application until the process
    exits - close() must release it immediately, not just at process exit."""
    import ctypes

    from global_hotkeys import MOD_ALT, MOD_NOREPEAT

    launcher = FloatingLauncher(_EditorStub(), register_global_hotkeys=True)
    assert launcher._hotkey_registered["photo"] is True
    launcher.close()

    user32 = ctypes.windll.user32
    probe_id = 0xF00E
    reclaimed = user32.RegisterHotKey(None, probe_id, MOD_ALT | MOD_NOREPEAT, ord("P"))
    try:
        assert reclaimed, "Alt+P was not released when the launcher closed"
    finally:
        if reclaimed:
            user32.UnregisterHotKey(None, probe_id)


def test_TA211_hotkeys_are_not_touched_without_opting_in(qapp) -> None:
    """register_global_hotkeys defaults to False - the many other tests in
    this suite that construct a launcher for unrelated reasons must never
    reach into real, process-wide OS hotkey state."""
    launcher = FloatingLauncher(_EditorStub())
    try:
        assert launcher._hotkeys is None
        assert not any(launcher._hotkey_registered.values())
        assert "Alt+P" not in launcher._btn_photo.toolTip()
        assert not launcher._hint_lbl.isVisible()
    finally:
        launcher.close()


def test_launcher_dock_right_moves_to_expected_x_position(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    launcher._dock_right()
    qapp.processEvents()

    geom = qapp.primaryScreen().availableGeometry()
    expected_x = geom.right() - launcher.width()
    assert launcher.x() == expected_x
    launcher.close()


def test_LCH_08_dock_right_uses_the_screen_the_widget_is_on(qapp, monkeypatch) -> None:
    """Issue #1: docking measured primaryScreen().availableGeometry()
    unconditionally, so dragging the launcher to a secondary monitor's edge
    docked it against the primary's edge instead."""
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    class _FakeScreen:
        def availableGeometry(self) -> QRect:
            return QRect(2000, 100, 800, 600)

    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: _FakeScreen()))

    launcher._dock_right()
    qapp.processEvents()

    # QRect.right() is x()+width()-1, not x()+width() - match that convention.
    assert launcher.x() == 2000 + 800 - 1 - launcher.width()
    launcher.close()


def test_launcher_position_top_right_uses_the_screen_the_widget_is_on(qapp, monkeypatch) -> None:
    class _FakeScreen:
        def availableGeometry(self) -> QRect:
            return QRect(3000, 200, 1000, 700)

    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: _FakeScreen()))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    # QRect.right() is x()+width()-1, not x()+width() - match that convention.
    assert launcher.x() == 3000 + 1000 - 1 - launcher.width() - 20
    assert launcher.y() == 200 + 20
    launcher.close()


def test_launcher_current_screen_falls_back_to_the_only_screen_when_off_every_screen(qapp, monkeypatch) -> None:
    """screenAt() returns None for a point off every screen - a real case,
    not a hypothetical one, e.g. mid-drag before layout settles. With only
    one real screen the largest-overlap fallback and "the primary" happen to
    be the same screen; test_DSP_13_current_screen_resolves_a_gap_to_the_
    overlapping_screen below is what actually distinguishes them."""
    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    assert launcher._current_screen() is QApplication.primaryScreen()
    launcher.close()


class _FakeScreenGeometry:
    """A minimal QScreen substitute. availableGeometry() is what
    positioning/docking actually use; geometry() is what the gap-resolution
    fallback and screenAt() substitutes use - kept equal here since none of
    these tests are about taskbar exclusion."""

    def __init__(self, geometry: QRect) -> None:
        self._geometry = geometry

    def geometry(self) -> QRect:
        return self._geometry

    def availableGeometry(self) -> QRect:
        return self._geometry


def test_DSP_13_current_screen_resolves_a_gap_to_the_overlapping_screen(qapp, monkeypatch) -> None:
    """The reported hardware: laptop -1920..-384, external 0..1920, leaving a
    384px gap belonging to no screen. screenAt() returns None there, and
    falling back to the primary (the external) is exactly why undocking sent
    the launcher back to the external instead of the laptop it was on."""
    laptop = _FakeScreenGeometry(QRect(-1920, 0, 1536, 864))
    external = _FakeScreenGeometry(QRect(0, 0, 1920, 1080))
    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [laptop, external]))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    # Frame's centre lands in the gap, but it mostly overlaps the laptop.
    launcher.move(-450, 100)
    qapp.processEvents()
    frame_centre_x = launcher.frameGeometry().center().x()
    assert -384 <= frame_centre_x <= 0, "test setup: the centre must actually be in the gap"

    assert launcher._current_screen() is laptop
    launcher.close()


def test_DSP_14_auto_dock_does_not_fire_when_dragged_in_from_the_right(qapp, monkeypatch) -> None:
    """End-to-end reproduction of the reported regression: dragging the
    launcher from the external onto the laptop, which sits to its left,
    must not auto-dock the instant it arrives."""
    laptop = _FakeScreenGeometry(QRect(-1920, 0, 1536, 864))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()
    monkeypatch.setattr(launcher, "_current_screen", lambda: laptop)

    # Comfortably inside the laptop, nowhere near ITS OWN right edge -
    # exactly what "just arrived from the screen to the right" looks like.
    pointer = QPoint(-500, 100)
    launcher.move(pointer.x() - 10, pointer.y() - 10)
    launcher._maybe_auto_dock(pointer)

    assert not launcher._dock_panel.isVisible(), "auto-dock fired on arrival, not proximity to the edge"
    launcher.close()


def test_DSP_auto_dock_fires_once_genuinely_flush_with_the_edge(qapp, monkeypatch) -> None:
    laptop = _FakeScreenGeometry(QRect(-1920, 0, 1536, 864))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()
    monkeypatch.setattr(launcher, "_current_screen", lambda: laptop)

    target_x = laptop.geometry().right() - launcher.width() - 5   # 5px inside the edge
    pointer = QPoint(target_x, 100)
    launcher.move(target_x, 100)
    launcher._maybe_auto_dock(pointer)

    assert launcher._dock_panel.isVisible(), "did not auto-dock once flush with the screen's own edge"
    launcher.close()


def test_DSP_dock_then_undock_returns_to_the_screen_it_docked_on(qapp, monkeypatch) -> None:
    """Docking and undocking must not disagree about which display they are
    on. _undock() used to widen the frame back to its floating width
    *before* re-resolving the current screen; if that widened-but-not-yet-
    repositioned frame reaches into a neighbouring screen, the widget snaps
    there instead of back to the screen it was actually docked on.

    The geometries below are deliberately small, not representative of real
    monitors: they exist to make the widened frame's centre of overlap cross
    into "external" if (and only if) the screen is re-resolved after
    widening rather than before - the numeric proof that the ordering in
    _undock() matters, not a hardware simulation.
    """
    laptop = _FakeScreenGeometry(QRect(-200, 0, 100, 864))     # right() = -101
    external = _FakeScreenGeometry(QRect(0, 0, 1920, 1080))
    screens = [laptop, external]
    monkeypatch.setattr(
        QApplication, "screenAt",
        staticmethod(lambda point: next((s for s in screens if s.geometry().contains(point)), None)),
    )
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: screens))

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    # Floating (width 280), centred well inside the laptop.
    launcher.move(-290, 100)
    qapp.processEvents()
    assert launcher._current_screen() is laptop, "test setup: must start out resolved to the laptop"

    launcher._dock_right()
    qapp.processEvents()
    assert launcher.x() == laptop.geometry().right() - launcher.width()

    launcher._undock()
    qapp.processEvents()

    expected = laptop.geometry()
    assert launcher.x() == expected.right() - launcher.width() - 20, \
        "undocking landed on a different screen than the one it docked on"
    launcher.close()


def test_TA216_on_capture_ready_routes_through_record_capture_not_load_pixmap(qapp) -> None:
    """A completed region or full-screen capture must reach History
    immediately (TA-216) - record_capture() is what does that;
    load_pixmap() alone (also used to view an existing image) does not."""
    editor = _EditorStub()
    launcher = FloatingLauncher(editor)

    launcher._on_capture_ready(QPixmap(64, 48))

    assert editor.recorded, "on_capture_ready must call record_capture()"
    assert editor.loaded == [], "on_capture_ready must not also call load_pixmap() directly"
    launcher.close()


def test_launcher_full_capture_uses_the_screen_the_widget_is_on(qapp, monkeypatch) -> None:
    """launcher.py:312 - full-screen capture only ever grabbed the primary."""
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    calls = []

    class _FakeScreen:
        def grabWindow(self, _wid):
            calls.append(True)
            return QPixmap(10, 10)

    monkeypatch.setattr(launcher, "_current_screen", lambda: _FakeScreen())

    launcher._grab_full_capture()

    assert calls == [True]
    launcher.close()


def test_open_folder_button_appears_after_a_recording_and_opens_its_folder(qapp, monkeypatch) -> None:
    """Fixes the discoverability complaint properly, per the data-locations
    brief: "where did it go" gets a one-click answer instead of a folder name
    buried in a status line."""
    import launcher as launcher_module

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()
    assert launcher._btn_open_folder.isHidden()

    import paths
    video_path = paths.recordings_dir() / "test-recording-1.mp4"
    video_path.write_bytes(b"fake mp4")

    launcher._on_record_finished(str(video_path))
    assert not launcher._btn_open_folder.isHidden()

    opened = []
    monkeypatch.setattr(
        launcher_module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toLocalFile())),
    )

    launcher._btn_open_folder.click()

    # QUrl normalises separators, so compare as paths rather than raw strings.
    assert [Path(p) for p in opened] == [video_path.parent]
    launcher.close()


def test_open_folder_button_hides_again_when_nothing_was_recorded(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    launcher._on_record_finished("")

    assert launcher._btn_open_folder.isHidden()
    launcher.close()


def test_open_folder_opens_the_frame_folder_itself_when_encoding_fell_back(qapp, monkeypatch, tmp_path) -> None:
    """When ffmpeg is unavailable, the "recording" is the frame folder itself,
    not a file inside one - the folder to open is that directory, not its
    parent."""
    import launcher as launcher_module

    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    frames_dir = tmp_path / "test-recording-1_frames"
    frames_dir.mkdir()

    launcher._on_record_finished(str(frames_dir))

    opened = []
    monkeypatch.setattr(
        launcher_module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toLocalFile())),
    )
    launcher._btn_open_folder.click()

    assert [Path(p) for p in opened] == [frames_dir]
    launcher.close()


def test_launcher_keyPressEvent_plain_letters_do_not_trigger_actions(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    launcher.keyPressEvent(_key_event(Qt.Key.Key_P))
    assert launcher._mode == "photo"
    assert not launcher.isHidden()

    launcher.keyPressEvent(_key_event(Qt.Key.Key_V))
    assert launcher._mode == "photo"
    assert not launcher._rec_timer.isActive()
    launcher.close()


def test_launcher_build_ui_header_controls_have_expected_tooltips(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    assert launcher._btn_open_editor.toolTip() == "Open Editor"
    assert launcher._btn_check_updates.toolTip() == "Check for Updates"
    assert launcher._btn_dock_right.toolTip() == "Dock to right side"
    assert launcher._btn_close.toolTip() == "Hide to tray"
    launcher.close()


def test_INS_02_close_button_hides_instead_of_quitting(qapp, monkeypatch) -> None:
    """PRE_BUILD_HANDOVER item 9, the most serious of this batch: the X used
    to call QApplication.instance().quit(), taking the tray icon down with
    it - Show Launcher became unreachable and nothing short of relaunching
    the exe brought the app back. quit() is monkeypatched at the class level
    (the pattern already used for QApplication.screenAt/screens elsewhere in
    this file) rather than called for real, since this test shares the
    session's one real QApplication with everything else."""
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    quit_calls = []
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: quit_calls.append(True)))

    launcher._btn_close.click()
    qapp.processEvents()

    assert quit_calls == [], "closing the launcher must not quit the application"
    assert launcher.isHidden()


def test_restore_repositions_a_floating_launcher_left_on_a_since_removed_screen(qapp, monkeypatch) -> None:
    """DSP-15: hidden while on a screen that is since gone (e.g. an external
    monitor unplugged), Show Launcher must not just re-show it at a position
    that is no longer reachable."""
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    launcher.hide()

    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))
    calls = []
    monkeypatch.setattr(launcher, "_position_top_right", lambda: calls.append("float"))

    launcher.restore()

    assert calls == ["float"]
    assert not launcher.isHidden()
    launcher.close()


def test_restore_repositions_a_docked_launcher_left_on_a_since_removed_screen(qapp, monkeypatch) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    launcher._dock_right()
    launcher.hide()

    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))
    calls = []
    monkeypatch.setattr(launcher, "_dock_right", lambda: calls.append("dock"))

    launcher.restore()

    assert calls == ["dock"]
    launcher.close()


def test_restore_does_not_reposition_a_launcher_still_on_a_real_screen(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    launcher.move(120, 130)
    launcher.hide()

    launcher.restore()

    assert (launcher.x(), launcher.y()) == (120, 130), \
        "restore() must not move a launcher that is still on a real screen"
    assert not launcher.isHidden()
    launcher.close()


def test_show_launcher_button_uses_the_shared_small_icon_button_style(qapp) -> None:
    """No new one-off rule - it opts into the same dynamic property as
    About, zoom out/in and Fit."""
    editor = EditorWindow()
    assert editor._show_launcher_btn.property("smallIconButton") is True
    editor.close()


def test_show_launcher_button_is_a_noop_without_a_wired_callback(qapp) -> None:
    """A standalone EditorWindow (as most tests construct one) has nothing
    wired yet - clicking must not raise."""
    editor = EditorWindow()
    editor._show_launcher_btn.click()
    editor.close()


def test_show_launcher_button_makes_a_hidden_launcher_visible(qapp) -> None:
    """editor.py holds no reference to the launcher at all, so once the
    launcher's own X hides it, the tray was the only route back - and
    Windows hides a new tray icon in the overflow by default."""
    from launcher import FloatingLauncher

    editor = EditorWindow()
    launcher = FloatingLauncher(editor)
    launcher.show()
    qapp.processEvents()
    launcher.hide()
    assert launcher.isHidden()

    editor.set_show_launcher_callback(launcher.restore)
    editor._show_launcher_btn.click()
    qapp.processEvents()

    assert not launcher.isHidden()
    editor.close()
    launcher.close()


def test_show_launcher_button_routes_through_restore_not_show(qapp, monkeypatch) -> None:
    """It must go through restore(), not show()/raise_() directly, so
    DSP-15's off-screen repositioning still applies here the same way it
    does for the tray menu and tray-icon click."""
    from launcher import FloatingLauncher

    editor = EditorWindow()
    launcher = FloatingLauncher(editor)

    calls: list[str] = []
    monkeypatch.setattr(FloatingLauncher, "restore", lambda self: calls.append("restore"))
    monkeypatch.setattr(FloatingLauncher, "show", lambda self: calls.append("show"))

    editor.set_show_launcher_callback(launcher.restore)
    editor._show_launcher_btn.click()

    assert calls == ["restore"]
    editor.close()


def test_TA220_bring_forward_toggles_minimize_when_already_active(qapp) -> None:
    """Clicking the TA icon while the Editor is already open and focused
    used to be a no-op re-raise; it must minimize instead, and a further
    click must restore and focus it again - a genuine show/hide toggle."""
    editor = EditorWindow()

    editor.bring_forward()
    qapp.processEvents()
    assert editor.isActiveWindow()
    assert not editor.isMinimized()

    editor.bring_forward()
    qapp.processEvents()
    assert editor.isMinimized(), "a second bring_forward() while active must minimize, not re-raise"

    editor.bring_forward()
    qapp.processEvents()
    assert not editor.isMinimized()
    assert editor.isActiveWindow()
    editor.close()


def test_TA220_bring_forward_raises_rather_than_minimizes_when_not_active(qapp) -> None:
    """The toggle only applies when the editor is already the active
    window - bring_forward() while something else has focus must still
    just raise and activate it, not minimize an editor nobody was
    looking at."""
    from PySide6.QtWidgets import QWidget

    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    other = QWidget()
    other.show()
    other.activateWindow()
    qapp.processEvents()
    assert not editor.isActiveWindow()

    editor.bring_forward()
    qapp.processEvents()

    assert not editor.isMinimized()
    assert editor.isActiveWindow()
    editor.close()
    other.close()


def test_INS_08_load_image_path_loads_a_valid_image_and_brings_the_editor_forward(qapp, tmp_path, blank_pixmap) -> None:
    """The "Open with -> Test Assist" / second-instance-handoff entry
    point: both hand load_image_path() a raw path string, never a
    QPixmap directly."""
    image_path = tmp_path / "photo.png"
    blank_pixmap.save(str(image_path), "PNG")

    editor = EditorWindow()
    assert editor.load_image_path(str(image_path)) is True

    assert editor._canvas.has_image()
    assert editor._canvas._pixmap.size() == blank_pixmap.size()
    assert not editor.isHidden(), "the editor must come to the front, not load silently in the background"
    editor.close()


def test_INS_09_load_image_path_degrades_cleanly_on_a_missing_file(qapp, tmp_path, monkeypatch) -> None:
    """A path that does not exist must warn and return False - never raise,
    and never start the editor pretending an open that didn't happen did."""
    missing = tmp_path / "does-not-exist.png"

    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: warnings.append(a[-1]) or QMessageBox.StandardButton.Ok),
    )

    editor = EditorWindow()
    before = editor._canvas.has_image()

    assert editor.load_image_path(str(missing)) is False

    assert warnings, "no warning was shown for a missing file"
    assert editor._canvas.has_image() == before, "a failed open must not change canvas state"
    editor.close()


def test_INS_09b_load_image_path_degrades_cleanly_on_a_non_image_file(qapp, tmp_path, monkeypatch) -> None:
    """A path that exists but is not a real image (a corrupt or unrelated
    file) must degrade the same way a missing one does - QPixmap loading it
    returns a null pixmap rather than raising, and that must be treated as
    a failure, not loaded as a blank canvas pretending to be the image."""
    not_an_image = tmp_path / "notes.txt"
    not_an_image.write_text("this is not an image")

    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: warnings.append(a[-1]) or QMessageBox.StandardButton.Ok),
    )

    editor = EditorWindow()
    before = editor._canvas.has_image()

    assert editor.load_image_path(str(not_an_image)) is False

    assert warnings, "no warning was shown for an unreadable image"
    assert editor._canvas.has_image() == before
    editor.close()


def test_launcher_open_editor_button_is_available_without_capture(qapp) -> None:
    editor = _EditorStub()
    launcher = FloatingLauncher(editor)
    launcher.show()
    qapp.processEvents()

    assert launcher._btn_open_editor.isEnabled()
    launcher._btn_open_editor.click()
    assert editor.bring_forward_calls == 1
    launcher.close()


def test_update_check_failure_shows_a_calm_message_not_a_traceback(qapp, monkeypatch):
    """No test may touch the network - the reply is substituted with a literal
    UpdateResult, exactly at the seam UpdateChecker.interpret() produces."""
    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    seen = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: seen.append(a[-1])))

    launcher._on_update_result(UpdateResult(ok=False))

    assert seen == ["Couldn't reach GitHub to check. Try again later."]
    assert launcher._btn_check_updates.isEnabled(), "the button must re-enable after the check finishes"
    launcher.close()


def test_update_check_reports_up_to_date(qapp, monkeypatch):
    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    seen = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: seen.append(a[-1])))

    launcher._on_update_result(UpdateResult(ok=True, is_newer=False))

    assert seen == ["You're on 1.2.0 — this is the latest version."]
    launcher.close()


def test_update_check_offers_to_open_the_release_page(qapp, monkeypatch):
    """Clicking "Open Download Page" must open html_url; the dialog text must
    say how to update, since unzip-install users cannot just click "Update"."""
    import launcher as launcher_module

    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    opened = []
    monkeypatch.setattr(launcher_module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toString())))

    def _click_the_action_button(self):
        # QMessageBox.buttons() is not insertion order, so find our custom
        # button by role rather than by position - simulating the user
        # clicking "Open Download Page" without blocking on a real modal loop.
        button = next(b for b in self.buttons() if self.buttonRole(b) == QMessageBox.ButtonRole.ActionRole)
        button.click()

    monkeypatch.setattr(QMessageBox, "exec", _click_the_action_button)

    launcher._on_update_result(
        UpdateResult(ok=True, is_newer=True, latest_version="1.3.0", html_url="https://example.test/releases/v1.3.0")
    )

    assert opened == ["https://example.test/releases/v1.3.0"]
    launcher.close()


def test_update_check_hides_the_open_button_when_there_is_no_url(qapp, monkeypatch):
    """parse_latest_release() returns an empty html_url when the GitHub
    payload omits it. The button must not appear at all in that case - a
    button that does nothing when clicked is worse than no button."""
    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    captured = {}
    monkeypatch.setattr(QMessageBox, "exec", lambda self: captured.setdefault("box", self))

    launcher._on_update_result(
        UpdateResult(ok=True, is_newer=True, latest_version="1.3.0", html_url="")
    )

    box = captured["box"]
    action_buttons = [b for b in box.buttons() if box.buttonRole(b) == QMessageBox.ButtonRole.ActionRole]
    assert action_buttons == [], "no 'Open Download Page' button when there is no URL to open"
    launcher.close()


def test_update_check_dialog_names_the_new_version_and_how_to_update(qapp, monkeypatch):
    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    captured = {}

    def _fake_exec(self):
        captured["text"] = self.text()

    monkeypatch.setattr(QMessageBox, "exec", _fake_exec)

    launcher._on_update_result(
        UpdateResult(ok=True, is_newer=True, latest_version="1.3.0", html_url="https://example.test")
    )

    assert "1.3.0" in captured["text"]
    assert "1.2.0" in captured["text"]
    assert "close test assist" in captured["text"].lower()
    assert "replace the" in captured["text"].lower()
    launcher.close()


def test_update_check_button_click_disables_it_until_the_result_arrives(qapp, monkeypatch):
    launcher = FloatingLauncher(_EditorStub(), version="1.2.0")

    calls = []
    monkeypatch.setattr(launcher._update_checker, "check", lambda cb: calls.append(cb))

    launcher._btn_check_updates.click()

    assert not launcher._btn_check_updates.isEnabled(), "must disable immediately, before any result arrives"
    assert len(calls) == 1
    launcher.close()


def test_canvas_mouseReleaseEvent_highlight_tool_creates_highlight_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "highlight"

    canvas.mousePressEvent(_MouseEventStub(20, 20))
    canvas.mouseMoveEvent(_MouseEventStub(140, 100))
    canvas.mouseReleaseEvent(_MouseEventStub(140, 100))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "highlight"
    canvas.close()


def test_canvas_mouseReleaseEvent_rect_tool_creates_rect_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "rect"

    canvas.mousePressEvent(_MouseEventStub(25, 30))
    canvas.mouseMoveEvent(_MouseEventStub(160, 120))
    canvas.mouseReleaseEvent(_MouseEventStub(160, 120))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "rect"
    canvas.close()


def test_canvas_mouseReleaseEvent_circle_tool_creates_circle_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "circle"

    canvas.mousePressEvent(_MouseEventStub(30, 30))
    canvas.mouseMoveEvent(_MouseEventStub(170, 130))
    canvas.mouseReleaseEvent(_MouseEventStub(170, 130))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "circle"
    canvas.close()


def test_canvas_mouseReleaseEvent_arrow_tool_creates_arrow_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "arrow"

    canvas.mousePressEvent(_MouseEventStub(40, 40))
    canvas.mouseMoveEvent(_MouseEventStub(220, 140))
    canvas.mouseReleaseEvent(_MouseEventStub(220, 140))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "arrow"
    canvas.close()


def test_canvas_mouseReleaseEvent_blur_tool_creates_blur_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "blur"

    canvas.mousePressEvent(_MouseEventStub(60, 50))
    canvas.mouseMoveEvent(_MouseEventStub(220, 140))
    canvas.mouseReleaseEvent(_MouseEventStub(220, 140))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "blur"
    canvas.close()


def test_canvas_mouseReleaseEvent_pen_tool_creates_pen_annotation(qapp, blank_pixmap) -> None:
    canvas = _canvas_with_image(qapp, blank_pixmap)
    canvas.tool = "pen"

    canvas.mousePressEvent(_MouseEventStub(50, 50))
    canvas.mouseMoveEvent(_MouseEventStub(80, 70))
    canvas.mouseMoveEvent(_MouseEventStub(110, 90))
    canvas.mouseReleaseEvent(_MouseEventStub(110, 90))

    assert canvas._annotations
    assert canvas._annotations[-1]["type"] == "pen"
    assert len(canvas._annotations[-1]["path"]) >= 2
    canvas.close()


# ─────────────────────────────────────────────────────────────────────────────
# Packaging / file locations
# ─────────────────────────────────────────────────────────────────────────────

def test_recordings_dir_resolves_through_the_paths_module(isolate_home):
    """Recordings used to land under ~/.test-assist, a dot-prefixed folder
    Windows users do not look in. TA-202 moved resolution to paths.py -
    capture.py's own helper must delegate rather than build the path itself,
    or the two could drift the way version_info.txt once did."""
    import capture
    import paths

    target = capture._recordings_dir()

    assert target == paths.recordings_dir()
    assert target.is_dir()


def test_version_flag_reports_a_semantic_version(capsys):
    """The release pipeline asserts on this output to prove the build runs."""
    import re
    import sys as _sys

    import main

    monkey = list(_sys.argv)
    try:
        _sys.argv = ["TestAssist.exe", "--version"]
        main.main()
    finally:
        _sys.argv = monkey

    out = capsys.readouterr().out.strip()
    assert re.fullmatch(r"Test Assist \d+\.\d+\.\d+", out), out
    assert out.endswith(main.__version__)


def test_version_flag_writes_a_file_when_asked(monkeypatch, tmp_path):
    """A windowed build has no usable stdout, so the release pipeline reads this
    file instead. If this contract breaks, the release cannot be verified."""
    import sys as _sys

    import main

    target = tmp_path / "version-probe.txt"
    monkeypatch.setenv("TESTASSIST_VERSION_FILE", str(target))
    monkeypatch.setattr(_sys, "argv", ["TestAssist.exe", "--version"])

    main.main()

    assert target.is_file(), "no version file was written"
    assert target.read_text(encoding="utf-8").strip() == f"Test Assist {main.__version__}"


def test_selftest_flag_resolves_and_runs_the_bundled_ffmpeg(monkeypatch, tmp_path):
    """--selftest proves the packaged build can actually find its ffmpeg, not
    just that the binary exists somewhere in the dist folder - collect_data_
    files() landing the file on disk does not prove the frozen import resolves
    the same way. build.ps1 and the release workflow run exactly this."""
    import sys as _sys

    import main

    target = tmp_path / "selftest-probe.txt"
    monkeypatch.setenv("TESTASSIST_VERSION_FILE", str(target))
    monkeypatch.setattr(_sys, "argv", ["TestAssist.exe", "--selftest"])

    main.main()

    assert target.is_file(), "no selftest file was written"
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    path, version_line, ssl_supported, ssl_backend = lines
    assert Path(path).is_file(), f"resolved ffmpeg path does not exist: {path}"
    assert "version" in version_line.lower()
    assert ssl_supported == "True", "TLS must be supported for the update check to ever work once frozen"
    assert ssl_backend


def test_selftest_flag_leaves_the_path_empty_on_resolution_failure(monkeypatch, tmp_path):
    """A resolution failure must be visible as an empty path, not a crash or a
    stale/misleading value - it is exactly what build.ps1 checks for."""
    import sys as _sys

    import capture
    import main

    monkeypatch.setattr(
        capture,
        "_resolve_ffmpeg_exe",
        lambda: (_ for _ in ()).throw(RuntimeError("simulated: not found")),
    )

    target = tmp_path / "selftest-probe.txt"
    monkeypatch.setenv("TESTASSIST_VERSION_FILE", str(target))
    monkeypatch.setattr(_sys, "argv", ["TestAssist.exe", "--selftest"])

    main.main()

    assert target.is_file()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "", "the path must be empty when resolution fails"


def test_selftest_flag_reports_ssl_unsupported_rather_than_crashing(monkeypatch, tmp_path):
    """A frozen build missing the TLS plugin must show up as a plain
    'False' in the probe file - not an exception, and not a value that could
    be mistaken for a working backend."""
    import sys as _sys

    import main
    from PySide6.QtNetwork import QSslSocket

    monkeypatch.setattr(QSslSocket, "supportsSsl", staticmethod(lambda: False))
    monkeypatch.setattr(QSslSocket, "activeBackend", staticmethod(lambda: ""))

    target = tmp_path / "selftest-probe.txt"
    monkeypatch.setenv("TESTASSIST_VERSION_FILE", str(target))
    monkeypatch.setattr(_sys, "argv", ["TestAssist.exe", "--selftest"])

    main.main()

    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "False"
    assert lines[3] == ""


def test_version_info_matches_main_version():
    """v1.1.0 shipped reporting itself as 1.0.0 because version_info.txt was a
    second place to remember and nobody updated it alongside __version__.
    generate_version_info.py derives it from __version__ at build time, but
    version_info.txt is also checked into the repo so a plain `pyinstaller
    TestAssist.spec` still works - this pins the two together so the checked
    in copy cannot silently drift from source between releases."""
    import re

    import main

    here = Path(main.__file__).resolve().parent
    text = (here / "version_info.txt").read_text(encoding="utf-8")

    file_version = re.search(r"StringStruct\('FileVersion', '([^']+)'\)", text)
    product_version = re.search(r"StringStruct\('ProductVersion', '([^']+)'\)", text)
    assert file_version and file_version.group(1) == main.__version__
    assert product_version and product_version.group(1) == main.__version__

    parts = tuple(int(p) for p in main.__version__.split("."))
    filevers = re.search(r"filevers=\(([^)]+)\)", text)
    assert filevers
    assert tuple(int(p.strip()) for p in filevers.group(1).split(",")) == (*parts, 0)


def test_help_html_matches_main_version():
    """help.html is opened as a static file:// URI via webbrowser.open(), so
    nothing can stamp its version at runtime the way a server-rendered page
    could. generate_version_info.py stamps it at build time from
    __version__; this pins the checked-in copy so it cannot silently drift
    the way version_info.txt once did for v1.1.0."""
    import re

    import main

    here = Path(main.__file__).resolve().parent
    text = (here / "help.html").read_text(encoding="utf-8")

    header_version = re.search(r'id="app-version">([^<]*)<', text)
    footer_version = re.search(r'id="app-version-footer">([^<]*)<', text)
    assert header_version and header_version.group(1) == main.__version__
    assert footer_version and footer_version.group(1) == main.__version__


def test_help_html_shortcuts_table_matches_the_editor_registered_shortcuts(qapp) -> None:
    """PRE_BUILD_HANDOVER item 5's shortcuts-table judgement call.

    The 9 tool-letter and 4 editing shortcuts are pinned mechanically against
    the QShortcut objects EditorWindow actually registers - the same
    introspection test_KEY_01/test_KEY_02_03_04 already rely on, extended to
    also check help.html's documented set matches. Deliberately NOT pinned:
    the 3 launcher-only rows (Alt+P, Alt+Shift+P, Alt+V). Those are inline
    keyPressEvent conditionals, not QShortcut objects, so there is no
    non-hardcoded source of truth to check them against here - a test that
    regex-parsed launcher.py's source would be brittle to any refactor of
    that method's shape, and a second hardcoded expectation would just move
    the manual-sync burden rather than remove it. Their *behaviour* is
    already covered separately by test_launcher_keyPressEvent_* below.
    """
    import re

    from PySide6.QtGui import QShortcut

    editor = EditorWindow()
    registered = {s.key().toString().lower() for s in editor.findChildren(QShortcut)}
    editor.close()

    html = (Path(__file__).resolve().parents[1] / "help.html").read_text(encoding="utf-8")
    table = re.search(r'<table class="shortcut-table">.*?</table>', html, re.DOTALL).group(0)
    documented = {key.lower() for key in re.findall(r"<code>([^<]+)</code></td>", table)}

    # QKeySequence("Delete").toString() is "Del" - the same key, a different
    # spelling. Aliased here rather than changing what the table says to a
    # user, since "Delete" is the name printed on the actual keyboard key.
    documented_normalised = {("del" if key == "delete" else key) for key in documented}

    launcher_only = {"alt+p", "alt+shift+p", "alt+v"}
    documented_editor_rows = documented_normalised - launcher_only

    assert documented_editor_rows == registered, (
        "help.html's shortcut table has drifted from what EditorWindow actually registers.\n"
        f"Documented (editor-scope): {sorted(documented_editor_rows)}\n"
        f"Registered:                {sorted(registered)}"
    )
    assert launcher_only <= documented, "the launcher-only shortcuts should still be documented, just not pinned here"


def test_WIN_01_editor_window_title_includes_the_running_version(qapp) -> None:
    """Zero new UI, always visible, and it shows up in any screenshot a
    reporter sends - the only way to learn the version in-app used to be
    pressing Check for Updates."""
    editor = EditorWindow(version="1.3.0")
    assert editor.windowTitle() == "Test Assist 1.3.0 — Editor"
    editor.close()


def test_editor_window_title_never_hardcodes_a_version(qapp) -> None:
    editor = EditorWindow(version="9.9.9")
    assert "9.9.9" in editor.windowTitle()
    editor.close()


def test_format_bug_report_details_includes_version_os_and_every_screen():
    """Pure formatting, no QScreen involved - issue #1 took a code read to
    diagnose because the report could not describe the monitor layout; this
    is the text a reporter would paste instead."""
    from editor import _format_bug_report_details

    screens = [
        {"x": 0, "y": 0, "width": 1920, "height": 1080, "dpr": 1.0},
        {"x": 1920, "y": 0, "width": 1280, "height": 800, "dpr": 1.5},
    ]
    details = _format_bug_report_details("1.3.0", "Windows 11 Version 24H2", screens)

    assert "Test Assist 1.3.0" in details
    assert "Windows 11 Version 24H2" in details
    assert "2 screen(s)" in details
    assert "1920x1080 at (0, 0), DPR 1.0" in details
    assert "1280x800 at (1920, 0), DPR 1.5" in details


def test_format_bug_report_details_with_no_screens_does_not_crash():
    from editor import _format_bug_report_details

    details = _format_bug_report_details("1.3.0", "Some OS", [])
    assert "0 screen(s)" in details


def test_ABT_01_about_dialog_shows_the_running_version_and_os(qapp, monkeypatch) -> None:
    editor = EditorWindow(version="1.3.0")
    editor.show()
    qapp.processEvents()

    captured = {}
    monkeypatch.setattr(QDialog, "exec", lambda self: captured.setdefault("dialog", self) and 0)

    editor._open_about()

    labels = [w.text() for w in captured["dialog"].findChildren(QLabel)]
    assert any("1.3.0" in text for text in labels), "the dialog does not show the running version"
    editor.close()


def test_ABT_02_copy_details_button_copies_version_os_and_display_layout(qapp, monkeypatch) -> None:
    """The point of the About dialog: a reporter can paste this instead of
    describing their monitor layout in prose."""
    editor = EditorWindow(version="1.3.0")

    monkeypatch.setattr(
        "editor.QSysInfo.prettyProductName", staticmethod(lambda: "Windows 11 Version 24H2"),
    )

    editor._copy_bug_report_details()
    copied = qapp.clipboard().text()

    assert "Test Assist 1.3.0" in copied
    assert "Windows 11 Version 24H2" in copied
    assert "screen(s):" in copied
    editor.close()


def test_ABT_03_about_button_is_reachable_from_the_toolbar(qapp) -> None:
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    about_buttons = [
        btn for btn in editor.findChildren(QPushButton)
        if btn.objectName() == "btn_about"
    ]
    assert about_buttons
    assert about_buttons[0].toolTip() == "About Test Assist"
    editor.close()


def test_small_fixed_size_buttons_opt_into_the_shared_zero_padding_rule(qapp) -> None:
    """PRE_BUILD_HANDOVER item 2: the global QPushButton rule's 7px/14px
    padding leaves nowhere for a glyph to draw on a small fixed-size button -
    About (28x28), zoom out/in (24x24 each) and Fit (24px tall) all drew as
    empty shapes. Fixed as one systemic rule via a dynamic property, not four
    separate #id overrides."""
    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    for button in (editor._about_btn, editor._btn_zoom_out, editor._btn_zoom_in, editor._btn_fit):
        assert button.property("smallIconButton") is True, \
            f"{button.objectName() or button.text()!r} does not opt into the shared small-icon-button rule"
    editor.close()


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def linearise(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = linearise(r), linearise(g), linearise(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.x contrast ratio between two colours, 1:1 (none) to 21:1 (max)."""
    lighter, darker = sorted((_relative_luminance(hex_a), _relative_luminance(hex_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _color_background_pairs(stylesheet: str) -> list[tuple[str, str, str]]:
    """Every {...} rule block that sets both `color` and `background-color`
    as literal hex values in the same block - the pairs a contrast check can
    verify without a full CSS cascade resolver.

    Declarations are matched by their exact property name (split on `;`),
    not by a `color:` substring search - `border-color:` and
    `background-color:` both contain that substring too.
    """
    import re

    pairs = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", stylesheet):
        color = background = None
        for declaration in body.split(";"):
            declaration = declaration.strip()
            match = re.match(r"(color|background-color):\s*(#[0-9a-fA-F]{6})", declaration)
            if not match:
                continue
            if match.group(1) == "color":
                color = match.group(2)
            else:
                background = match.group(2)
        if color and background:
            pairs.append((selector.strip(), color, background))
    return pairs


def test_no_stylesheet_rule_sets_text_below_minimum_contrast() -> None:
    """PRE_BUILD_HANDOVER item 3: QPushButton:disabled used a border token
    (LINE_STRONG) as a text colour - measured 1.79:1 against its own
    background, well under WCAG's 3:1 floor for large text/icons. A contrast
    function catches the whole class of this mistake, not just the one rule
    that happened to be reported."""
    from theme import EDITOR_STYLE

    pairs = _color_background_pairs(EDITOR_STYLE)
    assert pairs, "test setup: expected at least one rule with both color and background-color"

    failures = [
        f"{selector}: {color} on {background} = {_contrast_ratio(color, background):.2f}:1"
        for selector, color, background in pairs
        if _contrast_ratio(color, background) < 3.0
    ]
    assert not failures, "contrast below the 3:1 minimum:\n" + "\n".join(failures)


def test_theme_has_exactly_one_shared_rule_for_small_icon_buttons() -> None:
    import re

    from theme import EDITOR_STYLE

    matches = re.findall(r'QPushButton\[smallIconButton="true"\]\s*\{([^}]*)\}', EDITOR_STYLE)
    assert len(matches) == 1, "expected one shared rule, not one per button"
    assert "padding: 0" in matches[0]


def test_packaged_icon_exists_and_is_a_real_ico():
    """The taskbar icon ships with the build; a missing file falls back silently."""
    icon = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
    assert icon.is_file(), "assets/icon.ico is missing"
    assert icon.read_bytes()[:4] == b"\x00\x00\x01\x00", "not an ICO file"


# ─────────────────────────────────────────────────────────────────────────────
# Screen recording
# ─────────────────────────────────────────────────────────────────────────────

def _recorder(monkeypatch, tmp_path):
    """isolate_home (autouse) already redirects paths.recordings_dir() under
    tmp_path; monkeypatch/tmp_path are kept as parameters so every call site
    doesn't need editing, even though this helper no longer patches anything
    itself."""
    import capture

    return capture, capture.FrameRecorder()


def test_recorder_writes_frames_to_disk_instead_of_holding_them(qapp, monkeypatch, tmp_path):
    """The recorder used to append a full resolution QPixmap per frame - about
    7.9 MB every 1/15th of a second, so a one minute recording held roughly
    7 GB. Frames must reach disk as they are captured."""
    capture, rec = _recorder(monkeypatch, tmp_path)

    rec.start()
    for _ in range(6):
        rec._capture_frame()

    assert rec.frame_count == 6
    written = sorted(rec._frames_dir.glob("frame_*.jpg"))
    assert len(written) == 6, "frames were not written as they were captured"
    assert not hasattr(rec, "_frames"), "the in-memory frame list is gone"


def test_recorder_stops_itself_at_the_duration_cap(qapp, monkeypatch, tmp_path):
    """An unattended recording must not fill the disk."""
    capture, rec = _recorder(monkeypatch, tmp_path)

    rec.start()
    rec._count = rec._MAX_SECONDS * rec._FPS
    rec._capture_frame()

    assert not rec.is_recording(), "the cap did not stop the recording"


def test_recorder_scales_frames_below_the_capture_width(qapp, monkeypatch, tmp_path):
    """Full resolution frames cannot be encoded inside the frame budget."""
    from PySide6.QtGui import QImage

    capture, rec = _recorder(monkeypatch, tmp_path)
    rec.start()
    rec._capture_frame()

    frame = sorted(rec._frames_dir.glob("frame_*.jpg"))[0]
    assert QImage(str(frame)).width() <= rec._MAX_WIDTH


def test_recorder_without_imageio_ffmpeg_keeps_the_frame_sequence(qapp, monkeypatch, tmp_path):
    """Without imageio_ffmpeg the frames on disk are the recording, and must survive."""
    import builtins

    capture, rec = _recorder(monkeypatch, tmp_path)
    real_import = builtins.__import__

    def no_ffmpeg(name, *args, **kwargs):
        if name == "imageio_ffmpeg":
            raise ImportError("simulated: imageio_ffmpeg not installed")
        return real_import(name, *args, **kwargs)

    emitted: list[str] = []
    rec.finished.connect(emitted.append)

    rec.start()
    for _ in range(4):
        rec._capture_frame()

    monkeypatch.setattr(builtins, "__import__", no_ffmpeg)
    rec.stop()

    result = Path(emitted[0])
    assert result.is_dir(), "the frame folder is the recording when ffmpeg is unavailable"
    assert len(list(result.glob("frame_*.jpg"))) == 4


def test_recorder_a_nonzero_ffmpeg_exit_keeps_the_frame_sequence(qapp, monkeypatch, tmp_path):
    """A crashing or misconfigured ffmpeg must not lose the recording."""
    import subprocess

    capture, rec = _recorder(monkeypatch, tmp_path)

    class _FailedRun:
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FailedRun())

    emitted: list[str] = []
    rec.finished.connect(emitted.append)

    rec.start()
    for _ in range(4):
        rec._capture_frame()
    rec.stop()

    result = Path(emitted[0])
    assert result.is_dir(), "a non-zero ffmpeg exit must fall back to the frame folder"
    assert len(list(result.glob("frame_*.jpg"))) == 4


def test_recorder_encodes_odd_height_frames_without_error(qapp, monkeypatch, tmp_path):
    """yuv420p rejects odd dimensions; the scale filter must compensate."""
    from PySide6.QtGui import QColor, QImage

    capture, rec = _recorder(monkeypatch, tmp_path)
    rec.start()
    frames_dir = rec._frames_dir

    for i in range(3):
        image = QImage(101, 63, QImage.Format.Format_RGB32)
        image.fill(QColor("blue"))
        image.save(str(frames_dir / f"frame_{i:05d}.jpg"), "JPG", rec._JPEG_QUALITY)
    rec._count = 3

    emitted: list[str] = []
    rec.finished.connect(emitted.append)
    rec.stop()

    result = Path(emitted[0])
    assert result.suffix == ".mp4", "odd-height frames must still encode successfully"
    assert result.is_file()
    assert result.stat().st_size > 0


def test_REC_09_recording_uses_the_screen_passed_to_start_not_always_primary(qapp, monkeypatch, tmp_path):
    """Issue #1, the site not in the original bug report: capture.py:226 read
    QApplication.primaryScreen() on every frame, so a tester recording a
    repro on their secondary monitor got footage of the primary instead, with
    nothing to hint at it until playback."""
    capture, rec = _recorder(monkeypatch, tmp_path)

    class _FakeScreen:
        def __init__(self) -> None:
            self.grab_calls = 0

        def grabWindow(self, _wid):
            self.grab_calls += 1
            pixmap = QPixmap(64, 48)
            pixmap.fill(QColor("blue"))
            return pixmap

    fake_screen = _FakeScreen()
    real_primary_calls = []
    monkeypatch.setattr(
        capture.QApplication, "primaryScreen",
        staticmethod(lambda: real_primary_calls.append(1) or fake_screen),
    )

    rec.start(screen=fake_screen)
    real_primary_calls.clear()   # start() itself may or may not consult it; only frame capture matters here
    rec._capture_frame()

    assert fake_screen.grab_calls == 1
    assert real_primary_calls == [], "a frame was captured from primaryScreen() instead of the pinned screen"


def test_recorder_start_defaults_to_the_primary_screen_when_none_is_given(qapp, monkeypatch, tmp_path):
    capture, rec = _recorder(monkeypatch, tmp_path)
    rec.start()
    assert rec._screen is capture.QApplication.primaryScreen()


def test_recorder_with_nothing_captured_emits_empty(qapp, monkeypatch, tmp_path):
    capture, rec = _recorder(monkeypatch, tmp_path)
    emitted: list[str] = []
    rec.finished.connect(emitted.append)

    rec.start()
    rec.stop()

    assert emitted == [""]
