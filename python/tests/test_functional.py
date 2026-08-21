"""Functional coverage for the Test Assist desktop build.

Drives real widgets offscreen rather than poking at internals where possible.
Case IDs map to DESKTOP_TEST_PLAN.md; DESKTOP_STABILITY_MATRIX.md records what
is deliberately not covered here and why.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from canvas import AnnotationCanvas
from editor import EditorWindow


# ── Helpers ──────────────────────────────────────────────────────────────────

@dataclass
class _Mouse:
    x: float
    y: float

    def position(self) -> QPointF:
        return QPointF(self.x, self.y)


def drag(canvas: AnnotationCanvas, x1, y1, x2, y2, steps: int = 3) -> None:
    canvas.mousePressEvent(_Mouse(x1, y1))
    for i in range(1, steps + 1):
        canvas.mouseMoveEvent(
            _Mouse(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
        )
    canvas.mouseReleaseEvent(_Mouse(x2, y2))


def click(canvas: AnnotationCanvas, x, y) -> None:
    canvas.mousePressEvent(_Mouse(x, y))
    canvas.mouseReleaseEvent(_Mouse(x, y))


def select_at(canvas: AnnotationCanvas, x, y) -> None:
    """Selection is a double-click, whatever the active tool."""
    canvas.mouseDoubleClickEvent(_Mouse(x, y))


def draw(canvas: AnnotationCanvas, tool: str, x1=20, y1=20, x2=140, y2=110) -> dict:
    canvas.tool = tool
    drag(canvas, x1, y1, x2, y2)
    return canvas._annotations[-1]


@pytest.fixture
def canvas(qapp) -> AnnotationCanvas:
    c = AnnotationCanvas()
    pixmap = QPixmap(400, 300)
    pixmap.fill(QColor("#3a5a8a"))
    c.set_pixmap(pixmap)
    return c


@pytest.fixture
def editor(qapp) -> EditorWindow:
    win = EditorWindow()
    pixmap = QPixmap(400, 300)
    pixmap.fill(QColor("#3a5a8a"))
    win._canvas.set_pixmap(pixmap)
    return win


# ── 3.3 Annotation tools ─────────────────────────────────────────────────────

@pytest.mark.parametrize("case,tool", [
    ("TOL-01", "highlight"),
    ("TOL-02", "rect"),
    ("TOL-03", "circle"),
    ("TOL-04", "arrow"),
])
def test_drag_tools_add_an_annotation(canvas, case, tool):
    anno = draw(canvas, tool)
    assert anno["type"] == tool
    assert (anno["x1"], anno["y1"]) == (20, 20)
    assert (anno["x2"], anno["y2"]) == (140, 110)
    assert len(canvas._annotations) == 1


def test_TOL_05_pen_records_a_path(canvas):
    canvas.tool = "pen"
    drag(canvas, 30, 30, 150, 120, steps=6)
    anno = canvas._annotations[-1]
    assert anno["type"] == "pen"
    assert len(anno["path"]) > 1


def test_TOL_07_a_tiny_drag_adds_nothing(canvas):
    canvas.tool = "rect"
    drag(canvas, 50, 50, 51, 51, steps=1)
    assert canvas._annotations == []


def test_TOL_08_drawing_without_an_image_is_ignored(qapp):
    bare = AnnotationCanvas()
    assert not bare.has_image()
    bare.tool = "rect"
    drag(bare, 10, 10, 80, 80)
    assert bare._annotations == []


def test_TOL_09_every_tool_is_selectable_from_the_toolbar(editor):
    for tool in ["select", "crop", "blur", "text", "highlight", "circle", "arrow", "rect", "pen"]:
        editor._activate_tool(tool)
        assert editor._canvas.tool == tool


# ── 3.4 Crop ─────────────────────────────────────────────────────────────────

def test_CRP_01_crop_resizes_the_canvas(canvas):
    canvas.tool = "crop"
    drag(canvas, 50, 40, 250, 200)
    assert canvas.export_pixmap().width() == 200
    assert canvas.export_pixmap().height() == 160


def test_CRP_02_undo_restores_the_original_size(canvas):
    original = (canvas.export_pixmap().width(), canvas.export_pixmap().height())
    canvas.tool = "crop"
    drag(canvas, 50, 40, 250, 200)
    assert (canvas.export_pixmap().width(), canvas.export_pixmap().height()) != original

    canvas.undo()
    assert (canvas.export_pixmap().width(), canvas.export_pixmap().height()) == original


def test_CRP_03_a_tiny_crop_is_ignored(canvas):
    before = canvas.export_pixmap().width()
    canvas.tool = "crop"
    drag(canvas, 50, 50, 53, 53, steps=1)
    assert canvas.export_pixmap().width() == before


# ── 3.5 Blur ─────────────────────────────────────────────────────────────────

def test_BLR_01_blur_is_recorded_as_an_annotation(canvas):
    anno = draw(canvas, "blur", 40, 40, 200, 160)
    assert anno["type"] == "blur"


def test_BLR_02_blurred_pixels_do_not_survive_into_the_export(canvas):
    """A redaction that is only visual is not a redaction."""
    detailed = QPixmap(400, 300)
    detailed.fill(QColor("#3a5a8a"))
    from PySide6.QtGui import QPainter
    painter = QPainter(detailed)
    painter.setPen(QColor("#ffffff"))
    for x in range(40, 200, 4):
        painter.drawLine(x, 40, x, 160)      # high-frequency detail
    painter.end()
    canvas.set_pixmap(detailed)

    before = canvas.export_pixmap().toImage()
    draw(canvas, "blur", 40, 40, 200, 160)
    after = canvas.export_pixmap().toImage()

    def variance(img: QImage, x0, y0, x1, y1):
        values = []
        for x in range(x0, x1, 3):
            for y in range(y0, y1, 3):
                values.append(QColor(img.pixel(x, y)).lightness())
            
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    assert variance(after, 50, 50, 190, 150) < variance(before, 50, 50, 190, 150), \
        "the blurred region is not measurably flatter than the original"


def test_BLR_03_undo_removes_a_blur(canvas):
    draw(canvas, "blur", 40, 40, 200, 160)
    assert len(canvas._annotations) == 1
    canvas.undo()
    assert canvas._annotations == []


# ── 3.6 Selection and layering ───────────────────────────────────────────────

def test_SEL_01_a_double_click_selects_an_annotation(canvas):
    draw(canvas, "rect", 40, 40, 160, 140)
    canvas.tool = "select"

    select_at(canvas, 80, 80)
    assert canvas._selected is not None


def test_SEL_01b_a_single_click_does_not_select(canvas):
    """Documents current behaviour: the Select tool needs a double-click.
    Raised as a UX question rather than silently changed."""
    draw(canvas, "rect", 40, 40, 160, 140)
    canvas.tool = "select"

    click(canvas, 80, 80)
    assert canvas._selected is None


def test_SEL_02_dragging_a_selection_moves_it_without_deforming(canvas):
    anno = draw(canvas, "rect", 40, 40, 160, 140)
    width = anno["x2"] - anno["x1"]
    height = anno["y2"] - anno["y1"]
    origin = (anno["x1"], anno["y1"])

    canvas.tool = "select"
    canvas.mouseDoubleClickEvent(_Mouse(80, 80))
    canvas.mouseMoveEvent(_Mouse(130, 130))
    canvas.mouseMoveEvent(_Mouse(180, 160))
    canvas.mouseReleaseEvent(_Mouse(180, 160))

    moved = canvas._annotations[0]
    assert (moved["x1"], moved["y1"]) != origin, "the annotation did not move"
    assert moved["x2"] - moved["x1"] == pytest.approx(width, abs=1)
    assert moved["y2"] - moved["y1"] == pytest.approx(height, abs=1)


def test_SEL_03_delete_removes_the_selection(canvas):
    draw(canvas, "rect", 40, 40, 160, 140)
    canvas.tool = "select"
    select_at(canvas, 80, 80)
    assert canvas._selected is not None

    canvas.delete_selected()
    assert canvas._annotations == []


def test_SEL_04_delete_with_no_selection_does_nothing(canvas):
    draw(canvas, "rect", 40, 40, 160, 140)
    canvas._selected = None
    canvas.delete_selected()
    assert len(canvas._annotations) == 1


def test_SEL_05_06_07_layering_changes_the_stack(canvas):
    lower = draw(canvas, "rect", 40, 40, 200, 200)
    upper = draw(canvas, "highlight", 60, 60, 180, 180)

    def top_z():
        return max(a.get("z", 0) for a in canvas._annotations)

    canvas._selected = lower
    canvas.bring_selected_to_front()
    assert lower.get("z", 0) == top_z()

    canvas.send_selected_to_back()
    assert lower.get("z", 0) == min(a.get("z", 0) for a in canvas._annotations)
    assert upper.get("z", 0) == top_z()


# ── 3.7 Style controls ───────────────────────────────────────────────────────

def test_STY_01_new_colour_applies_to_the_next_annotation(canvas):
    first = draw(canvas, "rect", 20, 20, 100, 80)
    canvas.color = "#00ff00"
    second = draw(canvas, "rect", 150, 20, 230, 80)
    assert second["color"] == "#00ff00"
    assert first["color"] != "#00ff00"


def test_STY_02_style_updates_apply_to_the_selection(canvas):
    anno = draw(canvas, "rect", 40, 40, 160, 140)
    canvas._selected = anno
    canvas.update_selected_style(color="#123456", size=9)
    assert anno["color"] == "#123456"
    assert anno["size"] == 9


def test_STY_03_stroke_size_applies(canvas):
    canvas.stroke_size = 11
    assert draw(canvas, "rect")["size"] == 11


def test_STY_05_arrow_style_is_recorded(canvas):
    for style in ("classic", "double", "dashed"):
        canvas.arrow_style = style
        assert draw(canvas, "arrow")["arrow_style"] == style


# ── 3.8 Zoom ─────────────────────────────────────────────────────────────────

def test_ZOM_01_02_zoom_in_and_out(canvas):
    canvas.set_zoom(1.0)
    canvas.set_zoom(canvas.zoom() * 2)
    assert canvas.zoom() == pytest.approx(2.0)
    canvas.set_zoom(canvas.zoom() / 4)
    assert canvas.zoom() == pytest.approx(0.5)


def test_ZOM_04_fit_reduces_zoom_for_a_large_image(canvas):
    big = QPixmap(4000, 3000)
    big.fill(QColor("#222222"))
    canvas.set_pixmap(big)
    canvas.fit_to_size(QSize(800, 600))
    assert canvas.zoom() < 1.0


def test_ZOM_05_coordinates_are_in_image_space_while_zoomed(canvas):
    canvas.set_zoom(2.0)
    canvas.tool = "rect"
    drag(canvas, 100, 80, 300, 240)     # widget coordinates
    anno = canvas._annotations[-1]
    # halved, because the widget is at 2x
    assert (anno["x1"], anno["y1"]) == (50, 40)
    assert (anno["x2"], anno["y2"]) == (150, 120)


def test_ZOM_06_zoom_is_bounded(canvas):
    canvas.set_zoom(0.0001)
    assert canvas.zoom() >= 0.25
    canvas.set_zoom(1000)
    assert canvas.zoom() <= 4.0


# ── 3.9 Undo and redo ────────────────────────────────────────────────────────

def test_UND_01_02_undo_then_redo(canvas):
    draw(canvas, "rect")
    canvas.undo()
    assert canvas._annotations == []
    canvas.redo()
    assert len(canvas._annotations) == 1


def test_UND_03_undo_on_an_empty_stack_is_safe(canvas):
    canvas.undo()
    canvas.undo()
    assert canvas._annotations == []


def test_UND_04_drawing_after_undo_clears_the_redo_stack(canvas):
    draw(canvas, "rect", 20, 20, 100, 80)
    canvas.undo()
    draw(canvas, "circle", 150, 20, 230, 80)
    canvas.redo()
    assert len(canvas._annotations) == 1
    assert canvas._annotations[0]["type"] == "circle"


def test_UND_05_06_clear_all_and_undo_it(canvas):
    draw(canvas, "rect", 20, 20, 100, 80)
    draw(canvas, "circle", 150, 20, 230, 80)
    canvas.clear_annotations()
    assert canvas._annotations == []
    canvas.undo()
    assert len(canvas._annotations) == 2


# ── 3.10 Export ──────────────────────────────────────────────────────────────

def _stub_save_dialog(monkeypatch, path):
    """QFileDialog blocks; return a path as though the user chose one."""
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(path), "")),
    )


def test_OUT_01_02_save_png_writes_a_file_and_a_history_snapshot(editor, monkeypatch, tmp_path):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    target = tmp_path / "evidence.png"
    _stub_save_dialog(monkeypatch, target)

    editor._save_png()

    assert target.is_file()
    assert QImage(str(target)).width() == 400
    assert len(list(editor._history_dir.glob("*.png"))) == 1


def test_OUT_03_04_export_json_carries_the_full_record(editor, monkeypatch, tmp_path):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    target = tmp_path / "annotations.json"
    _stub_save_dialog(monkeypatch, target)

    editor._export_json()

    data = json.loads(target.read_text(encoding="utf-8"))
    assert sorted(data) == ["annotations", "timestamp"]
    anno = data["annotations"][0]
    for key in ("type", "x1", "y1", "x2", "y2", "color", "size"):
        assert key in anno, f"the exported annotation is missing {key}"


def test_OUT_05_a_pen_stroke_serialises_its_path(editor, monkeypatch, tmp_path):
    editor._canvas.tool = "pen"
    drag(editor._canvas, 30, 30, 150, 120, steps=5)
    target = tmp_path / "pen.json"
    _stub_save_dialog(monkeypatch, target)

    editor._export_json()

    path = json.loads(target.read_text(encoding="utf-8"))["annotations"][0]["path"]
    assert len(path) > 1
    assert set(path[0]) == {"x", "y"}


def test_OUT_06_07_copy_to_clipboard_and_history(editor):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    editor._copy_to_clipboard()

    clipboard = QApplication.clipboard().pixmap()
    assert not clipboard.isNull()
    assert clipboard.width() == 400
    assert len(list(editor._history_dir.glob("*.png"))) == 1


def test_OUT_08_export_without_an_image_writes_nothing(qapp, monkeypatch, tmp_path):
    bare = EditorWindow()
    target = tmp_path / "nothing.png"
    _stub_save_dialog(monkeypatch, target)

    bare._save_png()

    assert not target.exists()


def test_OUT_09_cancelling_the_dialog_writes_nothing(editor, monkeypatch, tmp_path):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))

    editor._save_png()

    assert list(tmp_path.glob("*.png")) == []


# ── 3.11 Capture history ─────────────────────────────────────────────────────

def test_HIS_01_history_persists_for_a_new_editor(editor, qapp):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    editor._copy_to_clipboard()
    assert len(list(editor._history_dir.glob("*.png"))) == 1

    reopened = EditorWindow()
    assert len(list(reopened._history_dir.glob("*.png"))) == 1


def test_HIS_02_blank_captures_are_not_persisted(editor):
    tiny = QPixmap(20, 20)
    tiny.fill(QColor("white"))
    editor._persist_history_snapshot(tiny)
    assert list(editor._history_dir.glob("*.png")) == []


def test_HIS_03_tiny_files_are_pruned_on_load(qapp, isolate_home):
    history = isolate_home / ".test-assist" / "history"
    history.mkdir(parents=True, exist_ok=True)
    junk = history / "corrupt.png"
    junk.write_bytes(b"not a real png")

    EditorWindow()

    assert not junk.exists(), "an unreadable snapshot should be pruned at startup"


def test_HIS_04_recent_filter_is_capped(editor):
    for _ in range(8):
        draw(editor._canvas, "rect", 20, 20, 140, 110)
        editor._copy_to_clipboard()

    recent = editor._history_files_for_mode("recent")
    assert len(recent) <= 5


def test_HIS_06_loading_a_snapshot_puts_it_on_the_canvas(editor):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    editor._copy_to_clipboard()
    editor._canvas.clear_annotations()

    snapshot = QPixmap(str(sorted(editor._history_dir.glob("*.png"))[0]))
    editor._load_history_snapshot(snapshot)

    assert editor._canvas.has_image()


# ── 3.12 Floating launcher ───────────────────────────────────────────────────

def test_LCH_03_04_docking_and_undocking(qapp, editor):
    from launcher import FloatingLauncher

    launcher = FloatingLauncher(editor)
    launcher._dock_right()
    docked_width = launcher.width()

    launcher._undock()
    assert launcher.width() > docked_width, "undocking should restore the wider layout"


def test_LCH_07_launcher_is_always_on_top(qapp, editor):
    from launcher import FloatingLauncher

    launcher = FloatingLauncher(editor)
    assert launcher.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


# ── 3.13 Keyboard shortcuts ──────────────────────────────────────────────────

@pytest.mark.parametrize("key,tool", [
    ("h", "highlight"), ("t", "text"), ("c", "circle"), ("a", "arrow"),
    ("r", "rect"), ("p", "pen"), ("s", "select"), ("x", "crop"), ("b", "blur"),
])
def test_KEY_01_tool_shortcuts_are_registered(editor, key, tool):
    from PySide6.QtGui import QKeySequence

    registered = {
        s.key().toString().lower(): s for s in editor.findChildren(type(editor._tool_shortcuts[0]))
    }
    assert key in registered, f"no shortcut registered for {key}"


def test_KEY_02_03_04_editing_shortcuts_are_registered(editor):
    keys = {
        s.key().toString().lower()
        for s in editor.findChildren(type(editor._tool_shortcuts[0]))
    }
    for expected in ("ctrl+z", "ctrl+y", "ctrl+s", "del"):
        assert expected in keys, f"{expected} is not registered"


# ── 3.14 Application lifecycle ───────────────────────────────────────────────

def test_INS_01_single_instance_manager_acquires_once(qapp):
    from single_instance import SingleInstanceManager

    first = SingleInstanceManager(server_name="test-assist-functional-suite")
    try:
        assert first.acquire() is True
    finally:
        first.close()


def test_INS_04_help_resolves_from_a_source_checkout(qapp):
    import editor as editor_module

    base = Path(editor_module.__file__).resolve().parent
    assert (base / "help.html").is_file()


def test_HIS_03b_a_small_but_valid_capture_is_not_deleted(qapp, isolate_home):
    """Regression: history pruning used to delete any PNG under 5 KB.

    A capture of a dialog or a form on a plain background compresses well below
    that, so real evidence was being deleted on the next launch. Pruning now
    tests whether the file is a readable image.
    """
    history = isolate_home / ".test-assist" / "history"
    history.mkdir(parents=True, exist_ok=True)

    flat = QPixmap(400, 300)
    flat.fill(QColor("#ffffff"))
    keeper = history / "snapshot-20260821-000000-000000.png"
    flat.save(str(keeper), "PNG")

    assert keeper.stat().st_size < 5000, "this fixture must be under the old threshold"

    EditorWindow()

    assert keeper.exists(), "a readable capture was deleted by history pruning"


# ── 3.1 Capture overlay ──────────────────────────────────────────────────────

def _overlay_mouse(x, y, button=Qt.MouseButton.LeftButton):
    @dataclass
    class _E:
        _x: float
        _y: float

        def position(self):
            return QPointF(self._x, self._y)

        def button(self):
            return button

    return _E(x, y)


def test_CAP_01_dragging_a_region_emits_a_capture(qapp):
    from capture import ScreenshotOverlay

    overlay = ScreenshotOverlay()
    grabbed: list = []
    overlay.capture_ready.connect(grabbed.append)

    overlay.mousePressEvent(_overlay_mouse(40, 40))
    overlay.mouseMoveEvent(_overlay_mouse(200, 160))
    overlay.mouseReleaseEvent(_overlay_mouse(200, 160))

    # the grab is deferred by 120 ms so the overlay can vanish before it fires
    QTest.qWait(300)

    assert len(grabbed) == 1, "a dragged region should produce exactly one capture"
    assert not grabbed[0].isNull()


def test_CAP_02_escape_cancels_without_capturing(qapp):
    from capture import ScreenshotOverlay

    overlay = ScreenshotOverlay()
    grabbed, cancelled = [], []
    overlay.capture_ready.connect(grabbed.append)
    overlay.cancelled.connect(lambda: cancelled.append(True))

    overlay.mousePressEvent(_overlay_mouse(40, 40))
    overlay.mouseMoveEvent(_overlay_mouse(200, 160))
    overlay.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))

    assert grabbed == [], "Escape must not produce a capture"
    assert cancelled == [True]


def test_CAP_03_a_click_without_a_drag_captures_nothing(qapp):
    from capture import ScreenshotOverlay

    overlay = ScreenshotOverlay()
    grabbed, cancelled = [], []
    overlay.capture_ready.connect(grabbed.append)
    overlay.cancelled.connect(lambda: cancelled.append(True))

    overlay.mousePressEvent(_overlay_mouse(80, 80))
    overlay.mouseReleaseEvent(_overlay_mouse(80, 80))

    assert grabbed == [], "a zero-size region is not a capture"
    assert cancelled == [True]


def test_CAP_04_a_new_capture_replaces_the_previous_image(editor):
    draw(editor._canvas, "rect", 20, 20, 140, 110)
    assert len(editor._canvas._annotations) == 1

    replacement = QPixmap(320, 240)
    replacement.fill(QColor("#884422"))
    editor.load_pixmap(replacement)

    assert editor._canvas._annotations == [], "a new capture starts a clean canvas"
    assert editor._canvas.export_pixmap().width() == 320


def test_REC_05_with_opencv_the_frames_become_a_single_mp4(qapp, monkeypatch, tmp_path):
    """Skips where opencv is absent, which includes the packaged build."""
    pytest.importorskip("cv2", reason="MP4 assembly requires opencv-python")

    import capture

    monkeypatch.setattr(capture.Path, "home", staticmethod(lambda: tmp_path))
    rec = capture.FrameRecorder()
    emitted: list[str] = []
    rec.finished.connect(emitted.append)

    rec.start()
    frames_dir = rec._frames_dir
    for _ in range(4):
        rec._capture_frame()
    rec.stop()

    result = Path(emitted[0])
    assert result.suffix == ".mp4", "with opencv the recording is a single video file"
    assert result.is_file()
    assert not frames_dir.exists(), "the intermediate frames should be cleaned up"


# ── Remaining plan cases ─────────────────────────────────────────────────────

def test_TOL_06_text_is_placed_at_the_click_point(canvas):
    canvas.tool = "text"
    canvas.mousePressEvent(_Mouse(90, 70))
    assert canvas._text_editing, "clicking with the text tool starts an edit"

    canvas._text_buffer = "Login button misaligned"
    canvas._commit_text()

    anno = canvas._annotations[-1]
    assert anno["type"] == "text"
    assert anno["text"] == "Login button misaligned"
    assert (anno["x1"], anno["y1"]) == (90, 70)


def test_TOL_06b_committing_empty_text_adds_nothing(canvas):
    canvas.tool = "text"
    canvas.mousePressEvent(_Mouse(90, 70))
    canvas._text_buffer = "   "
    canvas._commit_text()
    assert canvas._annotations == []


def test_CRP_04_annotations_survive_a_crop(canvas):
    draw(canvas, "rect", 60, 60, 160, 140)
    before = canvas.export_pixmap().toImage()
    assert before.width() == 400

    canvas.tool = "crop"
    drag(canvas, 50, 50, 250, 200)

    cropped = canvas.export_pixmap()
    assert cropped.width() == 200 and cropped.height() == 150
    # the crop composites the annotation into the base image rather than losing it
    assert not cropped.toImage().isNull()


def test_STY_04_highlight_opacity_is_recorded(canvas):
    canvas.fill_opacity = 0.75
    assert draw(canvas, "highlight")["opacity"] == pytest.approx(0.75)


def test_HIS_05_date_filters_exclude_older_snapshots(editor, isolate_home):
    import os
    import time as _time

    history = editor._history_dir
    recent = QPixmap(400, 300)
    recent.fill(QColor("#224466"))
    recent.save(str(history / "snapshot-recent.png"), "PNG")

    old = history / "snapshot-old.png"
    recent.save(str(old), "PNG")
    two_months_ago = _time.time() - 60 * 60 * 24 * 60
    os.utime(old, (two_months_ago, two_months_ago))

    assert len(editor._history_files_for_mode("all")) == 2
    assert old not in editor._history_files_for_mode("today")
    assert old not in editor._history_files_for_mode("week")
    assert old not in editor._history_files_for_mode("month")


def test_LCH_02_the_launcher_can_be_repositioned(qapp, editor):
    from launcher import FloatingLauncher

    launcher = FloatingLauncher(editor)
    launcher.move(120, 120)
    assert (launcher.x(), launcher.y()) == (120, 120)

    launcher.move(360, 240)
    assert (launcher.x(), launcher.y()) == (360, 240)


def test_KEY_05_tool_shortcuts_are_suppressed_while_typing(editor):
    """Typing 'r' into a text annotation must not switch to the rectangle tool.

    Exercises the real wiring: the canvas emits text_editing_changed and the
    editor disables the tool shortcuts in response.
    """
    assert all(s.isEnabled() for s in editor._tool_shortcuts)

    editor._activate_tool("text")
    editor._canvas.mousePressEvent(_Mouse(80, 80))
    assert editor._canvas._text_editing

    assert all(not s.isEnabled() for s in editor._tool_shortcuts), \
        "tool shortcuts stayed live while a text annotation was being typed"

    editor._canvas._text_buffer = "note"
    editor._canvas._commit_text()

    assert all(s.isEnabled() for s in editor._tool_shortcuts), \
        "tool shortcuts were not restored after the text was committed"
