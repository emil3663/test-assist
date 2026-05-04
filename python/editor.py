"""Annotation editor window for Test Assist (PySide6 edition)."""

from __future__ import annotations

import json
import time

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from canvas import AnnotationCanvas
from theme import ACCENT, LINE, MUTED


# ─────────────────────────────────────────────────────────────────────────────
# Editor window
# ─────────────────────────────────────────────────────────────────────────────

class EditorWindow(QMainWindow):
    """
    Full-screen annotation workspace.

    Opened via load_pixmap(background=True) so it appears behind the launcher
    without stealing focus. Call bring_forward() to raise it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Test Assist — Editor")
        self.setMinimumSize(960, 640)
        # Opens without stealing focus from the launcher.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._canvas = AnnotationCanvas()

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidgetResizable(False)
        self.setCentralWidget(scroll)

        self._build_tools_dock()
        self._connect_signals()
        self._register_shortcuts()

    # ── Public API ───────────────────────────────────────────────────────────

    def load_pixmap(self, pixmap: QPixmap, background: bool = True) -> None:
        """
        Load a captured image into the canvas.

        background=True  → show without taking focus (launcher stays in front).
        background=False → show and activate (editor comes to the front).
        """
        self._canvas.set_pixmap(pixmap)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, background)
        self.show()
        if not background:
            self.activateWindow()
            self.raise_()

    def bring_forward(self) -> None:
        """Raise and activate the editor window."""
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.show()
        self.activateWindow()
        self.raise_()

    # ── Tools dock ───────────────────────────────────────────────────────────

    def _build_tools_dock(self) -> None:
        dock = QDockWidget("Tools", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(210)

        container = QWidget()
        layout    = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── Tool buttons ──────────────────────────────────────────────────
        self._add_section(layout, "Tools")
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        for tool_id, label in [
            ("select",    "🖱  Select"),
            ("highlight", "🟡 Highlight"),
            ("text",      "📝 Text"),
            ("circle",    "⭕ Circle"),
            ("arrow",     "➡  Arrow"),
            ("rect",      "▭  Rectangle"),
            ("pen",       "✏  Pen"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setProperty("tool_id", tool_id)
            btn.setStyleSheet("text-align: left; padding-left: 10px;")
            self._tool_group.addButton(btn)
            layout.addWidget(btn)
            if tool_id == "select":
                btn.setChecked(True)

        layout.addWidget(self._separator())

        # ── Color ─────────────────────────────────────────────────────────
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color"))
        color_row.addStretch()
        self._color_btn = _ColorButton("#ff3b30")
        color_row.addWidget(self._color_btn)
        layout.addLayout(color_row)

        # ── Stroke size ───────────────────────────────────────────────────
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Stroke Size"))
        self._size_lbl = QLabel("3 px")
        self._size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size_row.addWidget(self._size_lbl)
        layout.addLayout(size_row)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 20)
        self._size_slider.setValue(3)
        layout.addWidget(self._size_slider)

        # ── Fill opacity ──────────────────────────────────────────────────
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Highlight Fill"))
        self._opacity_lbl = QLabel("30 %")
        self._opacity_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opacity_row.addWidget(self._opacity_lbl)
        layout.addLayout(opacity_row)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(30)
        layout.addWidget(self._opacity_slider)

        layout.addWidget(self._separator())

        # ── Undo / Redo / Clear / Delete ─────────────────────────────────
        urc = QHBoxLayout()
        self._btn_undo   = QPushButton("↩ Undo")
        self._btn_redo   = QPushButton("↪ Redo")
        self._btn_clear  = QPushButton("🗑")
        self._btn_clear.setObjectName("btn_danger")
        self._btn_clear.setToolTip("Clear all annotations")
        for btn in (self._btn_undo, self._btn_redo, self._btn_clear):
            btn.setFixedHeight(32)
            urc.addWidget(btn)
        layout.addLayout(urc)

        self._btn_delete = QPushButton("✂  Delete Selected")
        self._btn_delete.setFixedHeight(32)
        self._btn_delete.setToolTip("Delete the selected annotation (or press Delete key)")
        layout.addWidget(self._btn_delete)

        layer_row = QHBoxLayout()
        self._btn_front = QPushButton("⬆ Front")
        self._btn_back  = QPushButton("⬇ Back")
        self._btn_backmost = QPushButton("⤓ Bottom")
        self._btn_front.setToolTip("Bring selected annotation to front")
        self._btn_back.setToolTip("Send selected annotation one layer backward")
        self._btn_backmost.setToolTip("Send selected annotation to back")
        for btn in (self._btn_front, self._btn_back, self._btn_backmost):
            btn.setFixedHeight(32)
            layer_row.addWidget(btn)
        layout.addLayout(layer_row)

        # ── Export ────────────────────────────────────────────────────────
        self._btn_save_png = QPushButton("💾  Save PNG")
        self._btn_save_png.setObjectName("btn_primary")
        self._btn_save_png.setFixedHeight(36)
        layout.addWidget(self._btn_save_png)

        self._btn_export_json = QPushButton("📋  Export JSON")
        self._btn_export_json.setFixedHeight(32)
        layout.addWidget(self._btn_export_json)

        layout.addWidget(self._separator())

        # ── Snapshot gallery ──────────────────────────────────────────────
        self._add_section(layout, "Snapshots")

        snap_scroll = QScrollArea()
        snap_scroll.setWidgetResizable(True)
        snap_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._snap_container = QWidget()
        self._snap_layout    = QVBoxLayout(self._snap_container)
        self._snap_layout.setSpacing(6)
        self._snap_layout.setContentsMargins(0, 0, 0, 0)
        self._snap_layout.addStretch()
        snap_scroll.setWidget(self._snap_container)
        layout.addWidget(snap_scroll, 1)

        dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._tool_group.buttonClicked.connect(self._on_tool_changed)
        self._canvas.text_editing_changed.connect(self._set_tool_shortcuts_enabled)
        self._color_btn.color_changed.connect(
            lambda c: setattr(self._canvas, "color", c)
        )
        self._size_slider.valueChanged.connect(self._on_size_changed)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self._btn_undo.clicked.connect(self._canvas.undo)
        self._btn_redo.clicked.connect(self._canvas.redo)
        self._btn_clear.clicked.connect(self._confirm_clear)
        self._btn_delete.clicked.connect(self._canvas.delete_selected)
        self._btn_front.clicked.connect(self._canvas.bring_selected_to_front)
        self._btn_back.clicked.connect(self._canvas.send_selected_backward)
        self._btn_backmost.clicked.connect(self._canvas.send_selected_to_back)
        self._btn_save_png.clicked.connect(self._save_png)
        self._btn_export_json.clicked.connect(self._export_json)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Z"), self, self._canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._canvas.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_png)
        QShortcut(QKeySequence("Delete"), self, self._canvas.delete_selected)

        self._tool_shortcuts = []
        for key, tool in [
            ("h", "highlight"), ("t", "text"), ("c", "circle"),
            ("a", "arrow"),     ("r", "rect"), ("p", "pen"), ("s", "select"),
        ]:
            _tool = tool  # capture for lambda
            shortcut = QShortcut(
                QKeySequence(key), self,
                lambda checked=False, t=_tool: self._activate_tool(t),
            )
            self._tool_shortcuts.append(shortcut)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tool_changed(self, btn: QPushButton) -> None:
        self._canvas.tool = btn.property("tool_id")

    def _activate_tool(self, tool: str) -> None:
        if self._canvas._text_editing:
            return
        self._canvas.tool = tool
        for btn in self._tool_group.buttons():
            btn.setChecked(btn.property("tool_id") == tool)

    def _set_tool_shortcuts_enabled(self, is_text_editing: bool) -> None:
        for shortcut in getattr(self, "_tool_shortcuts", []):
            shortcut.setEnabled(not is_text_editing)

    def _on_size_changed(self, value: int) -> None:
        self._canvas.stroke_size = value
        self._size_lbl.setText(f"{value} px")

    def _on_opacity_changed(self, value: int) -> None:
        self._canvas.fill_opacity = value / 100.0
        self._opacity_lbl.setText(f"{value} %")

    def _confirm_clear(self) -> None:
        if not self._canvas.has_image():
            return
        reply = QMessageBox.question(
            self,
            "Clear Annotations",
            "Remove all annotations? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._canvas.clear_annotations()

    def _save_png(self) -> None:
        pixmap = self._canvas.export_pixmap()
        if not pixmap:
            return
        default = f"test-assist-{int(time.time())}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save PNG", default, "PNG (*.png)")
        if path:
            pixmap.save(path, "PNG")
            self._add_snapshot(pixmap)

    def _export_json(self) -> None:
        data = {
            "annotations": self._canvas.serialisable_annotations(),
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        default = f"annotations-{int(time.time())}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", default, "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)

    def _add_snapshot(self, pixmap: QPixmap) -> None:
        index = self._snap_layout.count()  # stretch counts as 1
        thumb = _SnapshotThumb(pixmap, index)
        thumb.load_requested.connect(self._canvas.set_pixmap)
        self._snap_layout.insertWidget(0, thumb)

    # ── Window events ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Hide instead of closing so the app keeps running."""
        event.ignore()
        self.hide()

    def keyPressEvent(self, event) -> None:
        """Prevent tool hotkeys from firing when canvas is editing text."""
        if self._canvas._text_editing:
            self._canvas.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {LINE}; border: none; max-height: 1px;")
        return line

    @staticmethod
    def _add_section(layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text.upper())
        lbl.setObjectName("section_title")
        layout.addWidget(lbl)


# ─────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ─────────────────────────────────────────────────────────────────────────────

class _ColorButton(QPushButton):
    """A coloured square button that opens QColorDialog on click."""

    color_changed = Signal(str)

    def __init__(self, color: str = "#ff3b30", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(36, 36)
        self.setToolTip("Click to change annotation colour")
        self._refresh()
        self.clicked.connect(self._pick)

    @property
    def color(self) -> str:
        return self._color

    def _pick(self) -> None:
        c = QColorDialog.getColor(QColor(self._color), self, "Annotation Colour")
        if c.isValid():
            self._color = c.name()
            self._refresh()
            self.color_changed.emit(self._color)

    def _refresh(self) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border-radius: 8px;
                border: 2px solid #3a3a5e;
            }}
            QPushButton:hover {{ border-color: #7c83fd; }}
        """)


class _SnapshotThumb(QFrame):
    """Clickable thumbnail shown in the snapshot gallery."""

    load_requested = Signal(object)  # QPixmap

    def __init__(
        self, pixmap: QPixmap, index: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._pixmap = pixmap
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to reload this snapshot")
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #2a2a4e;
                border-radius: 8px;
            }
            QFrame:hover { border-color: #7c83fd; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        thumb = pixmap.scaledToWidth(168, Qt.TransformationMode.SmoothTransformation)
        img   = QLabel()
        img.setPixmap(thumb)
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img)

        lbl = QLabel(f"Snap {index}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.load_requested.emit(self._pixmap)
        super().mousePressEvent(event)
