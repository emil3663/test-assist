from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPixmap

from canvas import AnnotationCanvas
from editor import EditorWindow
from launcher import FloatingLauncher


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

    def bring_forward(self) -> None:
        self.bring_forward_calls += 1

    def load_pixmap(self, pixmap, background: bool = True) -> None:
        self.loaded.append((pixmap, background))


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
    canvas.mousePressEvent(_MouseEventStub(30, 30))
    assert canvas._selected is canvas._annotations[0]

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

    canvas.mousePressEvent(_MouseEventStub(handle_x, handle_y))
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

    canvas.mousePressEvent(_MouseEventStub(40, 40))
    canvas.mouseMoveEvent(_MouseEventStub(75, 90))
    canvas.mouseReleaseEvent(_MouseEventStub(75, 90))

    assert rect["x1"] == 55
    assert rect["y1"] == 70
    assert rect["x2"] == 115
    assert rect["y2"] == 110
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

    canvas.mousePressEvent(_MouseEventStub(60, 60))
    topmost = canvas._selected
    assert topmost is canvas._annotations[1]

    canvas.send_selected_to_back()
    canvas.mousePressEvent(_MouseEventStub(60, 60))

    assert canvas._selected is canvas._annotations[0]
    canvas.close()


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
    # Mode icon buttons carry Alt shortcut hints in their tooltips
    assert "Alt+P" in launcher._btn_photo.toolTip()
    assert "Alt+V" in launcher._btn_video.toolTip()
    assert "Alt+Shift+P" in launcher._btn_full_capture.toolTip()
    launcher.close()


def test_launcher_dock_right_moves_to_expected_x_position(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    launcher._dock_right()
    qapp.processEvents()

    geom = qapp.primaryScreen().availableGeometry()
    expected_x = geom.right() - launcher.width() - 20
    assert launcher.x() == expected_x
    launcher.close()


def test_launcher_keyPressEvent_alt_v_toggles_recording_mode(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    launcher.keyPressEvent(_key_event(Qt.Key.Key_V, Qt.KeyboardModifier.AltModifier))

    assert launcher._mode == "video"
    assert launcher._rec_timer.isActive()
    # Action button text changes to stop indicator while recording
    assert "Stop" in launcher._btn_capture.text()

    launcher.keyPressEvent(_key_event(Qt.Key.Key_V, Qt.KeyboardModifier.AltModifier))
    assert not launcher._rec_timer.isActive()
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
    assert launcher._btn_dock_right.toolTip() == "Dock to right side"
    assert launcher._btn_close.toolTip() == "Close Test Assist"
    launcher.close()


def test_launcher_keyPressEvent_alt_shift_p_triggers_full_capture(qapp) -> None:
    launcher = FloatingLauncher(_EditorStub())
    launcher.show()
    qapp.processEvents()

    called = {"count": 0}

    def _fake_full_capture() -> None:
        called["count"] += 1

    launcher._start_full_capture = _fake_full_capture  # type: ignore[method-assign]
    launcher.keyPressEvent(
        _key_event(
            Qt.Key.Key_P,
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
        )
    )

    assert called["count"] == 1
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