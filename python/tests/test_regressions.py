from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QTabWidget, QWidget

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
    expected_x = geom.right() - launcher.width()
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


def test_launcher_open_editor_button_is_available_without_capture(qapp) -> None:
    editor = _EditorStub()
    launcher = FloatingLauncher(editor)
    launcher.show()
    qapp.processEvents()

    assert launcher._btn_open_editor.isEnabled()
    launcher._btn_open_editor.click()
    assert editor.bring_forward_calls == 1
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

def test_recordings_are_written_beside_the_history_not_loose_in_home(monkeypatch, tmp_path):
    """Recordings used to land directly in the user's home folder."""
    import capture

    monkeypatch.setattr(capture.Path, "home", staticmethod(lambda: tmp_path))
    target = capture._recordings_dir()

    assert target == tmp_path / ".test-assist" / "recordings"
    assert target.is_dir()
    assert not list(tmp_path.glob("test-recording-*"))


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


def test_packaged_icon_exists_and_is_a_real_ico():
    """The taskbar icon ships with the build; a missing file falls back silently."""
    icon = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
    assert icon.is_file(), "assets/icon.ico is missing"
    assert icon.read_bytes()[:4] == b"\x00\x00\x01\x00", "not an ICO file"


# ─────────────────────────────────────────────────────────────────────────────
# Screen recording
# ─────────────────────────────────────────────────────────────────────────────

def _recorder(monkeypatch, tmp_path):
    import capture

    monkeypatch.setattr(capture.Path, "home", staticmethod(lambda: tmp_path))
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


def test_recorder_with_nothing_captured_emits_empty(qapp, monkeypatch, tmp_path):
    capture, rec = _recorder(monkeypatch, tmp_path)
    emitted: list[str] = []
    rec.finished.connect(emitted.append)

    rec.start()
    rec.stop()

    assert emitted == [""]
