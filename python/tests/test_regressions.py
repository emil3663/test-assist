from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent

from canvas import AnnotationCanvas
from editor import EditorWindow


@dataclass
class _MouseEventStub:
    x: float
    y: float

    def position(self) -> QPointF:
        return QPointF(self.x, self.y)


def _typed_event(char: str) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, char)


def _canvas_with_image(qapp, blank_pixmap) -> AnnotationCanvas:
    canvas = AnnotationCanvas()
    canvas.set_pixmap(blank_pixmap)
    canvas.show()
    qapp.processEvents()
    return canvas


def test_text_typing_does_not_lose_keyboard_letters(qapp, blank_pixmap) -> None:
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


def test_clicking_empty_space_clears_selection(qapp, blank_pixmap) -> None:
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


def test_text_box_corner_drag_resizes_text_annotation(qapp, blank_pixmap) -> None:
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


def test_existing_annotation_can_be_dragged_without_select_tool(qapp, blank_pixmap) -> None:
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


def test_layer_order_controls_change_topmost_hit_target(qapp, blank_pixmap) -> None:
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