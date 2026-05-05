"""Annotation editor window for Test Assist (PySide6 edition)."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import time
import webbrowser

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QColorDialog,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from canvas import AnnotationCanvas
from theme import ACCENT, BG_800, LINE, MUTED, TEXT


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
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._canvas = AnnotationCanvas()
        self._fit_mode = True

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidgetResizable(False)
        self._scroll = scroll

        # Central widget: tools bar at top + canvas below
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._build_tools_bar())
        central_layout.addWidget(scroll, 1)
        self.setCentralWidget(central)

        self._build_right_dock()
        self._connect_signals()
        self._register_shortcuts()
        self._load_history()

    # ── Public API ───────────────────────────────────────────────────────────

    def load_pixmap(self, pixmap: QPixmap, background: bool = True) -> None:
        """
        Load a captured image into the canvas.

        background=True  → show without taking focus (launcher stays in front).
        background=False → show and activate (editor comes to the front).
        """
        self._canvas.set_pixmap(pixmap)
        if self._fit_mode:
            self._fit_image()
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

    # ── Top tools bar ─────────────────────────────────────────────────────────

    def _build_tools_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("tools_bar")
        bar.setStyleSheet(
            f"QFrame#tools_bar {{ background-color: {BG_800};"
            f" border-bottom: 1px solid {LINE}; }}"
        )
        bar.setFixedHeight(92)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_color_btns: dict[str, _ColorButton] = {}
        self._tool_colors: dict[str, str] = {
            "text":      "#ffffff",
            "highlight": "#ffcc00",
            "circle":    "#ff3b30",
            "arrow":     "#ff3b30",
            "rect":      "#ff3b30",
            "pen":       "#ff3b30",
        }

        _TOOLS = [
            ("select",    "🖱",  "Select (S)",       False),
            ("crop",      "✂",  "Crop (X)",          False),
            ("blur",      "▒",  "Blur (B)",          False),
            ("text",      "T",   "Text (T)",          True),
            ("highlight", "🟡", "Highlight (H)",      True),
            ("circle",    "⭕", "Circle (C)",         True),
            ("arrow",     "→",  "Arrow (A)",          True),
            ("rect",      "▭",  "Rectangle (R)",      True),
            ("pen",       "✏", "Pen (P)",             True),
        ]

        layout.addStretch()

        for tool_id, icon, tip, has_color in _TOOLS:
            short_name = tip.split(" (")[0]
            cell = QWidget()
            cell.setFixedSize(64, 74)
            vl = QVBoxLayout(cell)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(2)

            name_lbl = QLabel(short_name)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setFixedHeight(14)
            name_lbl.setStyleSheet("font-size: 9px; color: #b0b0c8; background: transparent;")
            vl.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

            vl.addStretch(1)

            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.setFixedSize(44, 30)
            btn.setToolTip(tip)
            btn.setProperty("tool_id", tool_id)
            self._tool_group.addButton(btn)
            vl.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

            vl.addStretch(1)

            if has_color:
                cbtn = _ColorButton(self._tool_colors[tool_id], size=(44, 10))
                cbtn.setToolTip(f"Colour for {short_name}")
                self._tool_color_btns[tool_id] = cbtn
                vl.addWidget(cbtn, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            else:
                spacer = QWidget()
                spacer.setFixedSize(44, 10)
                vl.addWidget(spacer, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

            if tool_id == "select":
                btn.setChecked(True)

            layout.addWidget(cell)

        layout.addStretch()

        # Help button — far right of toolbar
        help_btn = QPushButton("?")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Open Help")
        help_btn.setStyleSheet(
            "QPushButton { background: rgba(200,120,60,0.10); color: #c8906a;"
            " border: 1px solid rgba(200,120,60,0.30); border-radius: 14px;"
            " font-size: 13px; font-weight: 700; }"
            " QPushButton:hover { background: rgba(200,120,60,0.22); color: #f0b880; }"
        )
        help_btn.clicked.connect(self._open_help)
        layout.addWidget(help_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        return bar

    # ── Right controls dock ───────────────────────────────────────────────────

    def _build_right_dock(self) -> None:
        dock = QDockWidget("Controls", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(185)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── Edit controls stacked vertically ─────────────────────────────
        self._add_section(layout, "Edit")

        self._btn_undo     = QPushButton("↩  Undo")
        self._btn_redo     = QPushButton("↪  Redo")
        self._btn_delete   = QPushButton("✂  Delete Selected")
        self._btn_front    = QPushButton("⬆  Bring to Front")
        self._btn_back     = QPushButton("⬇  Send Backward")
        self._btn_backmost = QPushButton("⤓  Send to Back")
        self._btn_clear    = QPushButton("🗑  Clear All")
        self._btn_clear.setObjectName("btn_danger")

        self._btn_undo.setToolTip("Undo (Ctrl+Z)")
        self._btn_redo.setToolTip("Redo (Ctrl+Y)")
        self._btn_delete.setToolTip("Delete selected annotation (Del)")
        self._btn_front.setToolTip("Bring selected annotation to front")
        self._btn_back.setToolTip("Send selected annotation one layer back")
        self._btn_backmost.setToolTip("Send selected annotation to back")
        self._btn_clear.setToolTip("Clear all annotations")

        for btn in (
            self._btn_undo, self._btn_redo, self._btn_delete,
            self._btn_front, self._btn_back, self._btn_backmost, self._btn_clear,
        ):
            btn.setFixedHeight(30)
            layout.addWidget(btn)

        layout.addWidget(self._separator())

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom"))
        self._btn_zoom_out = QPushButton("-")
        self._btn_zoom_out.setFixedSize(24, 24)
        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.setFixedSize(24, 24)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(25, 300)
        self._zoom_slider.setValue(100)
        self._zoom_pct = QLabel("100 %")
        self._zoom_pct.setFixedWidth(48)
        self._btn_fit = QPushButton("Fit")
        self._btn_fit.setFixedHeight(24)
        zoom_row.addWidget(self._btn_zoom_out)
        zoom_row.addWidget(self._zoom_slider, 1)
        zoom_row.addWidget(self._btn_zoom_in)
        zoom_row.addWidget(self._zoom_pct)
        zoom_row.addWidget(self._btn_fit)
        layout.addLayout(zoom_row)

        layout.addWidget(self._separator())

        # ── Stroke size ───────────────────────────────────────────────────
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Stroke"))
        self._size_lbl = QLabel("3 px")
        self._size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size_row.addWidget(self._size_lbl)
        layout.addLayout(size_row)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 20)
        self._size_slider.setValue(3)
        layout.addWidget(self._size_slider)

        # ── Arrow style ───────────────────────────────────────────────────
        arrow_row = QHBoxLayout()
        arrow_row.addWidget(QLabel("Arrow"))
        self._arrow_style_combo = QComboBox()
        self._arrow_style_combo.addItem("Classic", "classic")
        self._arrow_style_combo.addItem("Double", "double")
        self._arrow_style_combo.addItem("Dashed", "dashed")
        self._arrow_style_combo.setCurrentIndex(0)
        arrow_row.addWidget(self._arrow_style_combo, 1)
        layout.addLayout(arrow_row)

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

        # ── Export ────────────────────────────────────────────────────────
        self._btn_save_png = QPushButton("💾  Save PNG")
        self._btn_save_png.setObjectName("btn_primary")
        self._btn_save_png.setFixedHeight(34)
        layout.addWidget(self._btn_save_png)

        self._btn_copy = QPushButton("⧉  Copy")
        self._btn_copy.setFixedHeight(30)
        self._btn_copy.setToolTip("Copy annotated image to clipboard")
        layout.addWidget(self._btn_copy)

        self._btn_export_json = QPushButton("📋  Export JSON")
        self._btn_export_json.setFixedHeight(30)
        layout.addWidget(self._btn_export_json)

        layout.addWidget(self._separator())

        # ── History / Snapshots ───────────────────────────────────────────
        history_header = self._add_section(layout, "History", clickable=True)
        history_header.clicked.connect(self._show_history_overlay)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show"))
        self._history_filter = QComboBox()
        self._history_filter.addItem("Recent 5", "recent")
        self._history_filter.addItem("Today", "today")
        self._history_filter.addItem("This Week", "week")
        self._history_filter.addItem("This Month", "month")
        filter_row.addWidget(self._history_filter, 1)
        layout.addLayout(filter_row)

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
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._tool_group.buttonClicked.connect(self._on_tool_changed)
        self._canvas.text_editing_changed.connect(self._set_tool_shortcuts_enabled)

        # Per-tool colour wiring
        for tool_id, cbtn in self._tool_color_btns.items():
            cbtn.color_changed.connect(
                lambda c, t=tool_id: self._on_tool_color_changed(t, c)
            )

        self._history_filter.currentIndexChanged.connect(self._refresh_history)
        self._btn_zoom_out.clicked.connect(lambda: self._set_zoom_percent(self._zoom_slider.value() - 10))
        self._btn_zoom_in.clicked.connect(lambda: self._set_zoom_percent(self._zoom_slider.value() + 10))
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        self._btn_fit.clicked.connect(self._fit_image)
        self._size_slider.valueChanged.connect(self._on_size_changed)
        self._arrow_style_combo.currentIndexChanged.connect(self._on_arrow_style_changed)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self._btn_undo.clicked.connect(self._canvas.undo)
        self._btn_redo.clicked.connect(self._canvas.redo)
        self._btn_clear.clicked.connect(self._confirm_clear)
        self._btn_delete.clicked.connect(self._canvas.delete_selected)
        self._btn_front.clicked.connect(self._canvas.bring_selected_to_front)
        self._btn_back.clicked.connect(self._canvas.send_selected_backward)
        self._btn_backmost.clicked.connect(self._canvas.send_selected_to_back)
        self._btn_save_png.clicked.connect(self._save_png)
        self._btn_copy.clicked.connect(self._copy_to_clipboard)
        self._btn_export_json.clicked.connect(self._export_json)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Z"), self, self._canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._canvas.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_png)
        QShortcut(QKeySequence("Delete"), self, self._canvas.delete_selected)

        self._tool_shortcuts = []
        for key, tool in [
            ("h", "highlight"), ("t", "text"), ("c", "circle"),
            ("a", "arrow"),     ("r", "rect"), ("p", "pen"),
            ("s", "select"),    ("x", "crop"), ("b", "blur"),
        ]:
            _tool = tool  # capture for lambda
            shortcut = QShortcut(
                QKeySequence(key), self,
                lambda checked=False, t=_tool: self._activate_tool(t),
            )
            self._tool_shortcuts.append(shortcut)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tool_changed(self, btn: QPushButton) -> None:
        tool_id = btn.property("tool_id")
        self._canvas.tool = tool_id
        # Apply this tool's colour to the canvas
        if tool_id in self._tool_colors:
            self._canvas.color = self._tool_colors[tool_id]

    def _on_tool_color_changed(self, tool_id: str, color: str) -> None:
        self._tool_colors[tool_id] = color
        if self._canvas.tool == tool_id:
            self._canvas.color = color
        selected = self._canvas._selected
        if selected is not None and selected.get("type") == tool_id:
            self._canvas.update_selected_style(color=color)

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
        self._canvas.update_selected_style(size=value)

    def _on_zoom_slider_changed(self, value: int) -> None:
        self._fit_mode = False
        self._canvas.set_zoom(value / 100.0)
        self._zoom_pct.setText(f"{value} %")

    def _set_zoom_percent(self, value: int) -> None:
        self._zoom_slider.setValue(max(25, min(300, value)))

    def _fit_image(self) -> None:
        self._fit_mode = True
        self._canvas.fit_to_size(self._scroll.viewport().size())
        pct = int(round(self._canvas.zoom() * 100))
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(max(25, min(300, pct)))
        self._zoom_slider.blockSignals(False)
        self._zoom_pct.setText(f"{self._zoom_slider.value()} %")

    def _on_arrow_style_changed(self, _index: int) -> None:
        style = self._arrow_style_combo.currentData()
        if not style:
            return
        self._canvas.arrow_style = style
        self._canvas.update_selected_style(arrow_style=style)

    def _on_opacity_changed(self, value: int) -> None:
        self._canvas.fill_opacity = value / 100.0
        self._opacity_lbl.setText(f"{value} %")
        self._canvas.update_selected_style(opacity=self._canvas.fill_opacity)

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

    def _open_help(self) -> None:
        help_file = Path(__file__).parent / "help.html"
        webbrowser.open(help_file.as_uri())

    def _save_png(self) -> None:
        pixmap = self._canvas.export_pixmap()
        if not pixmap:
            return
        default = f"test-assist-{int(time.time())}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save PNG", default, "PNG (*.png)")
        if path:
            pixmap.save(path, "PNG")
            self._persist_history_snapshot(pixmap)

    def _copy_to_clipboard(self) -> None:
        pixmap = self._canvas.export_pixmap()
        if not pixmap:
            return
        QApplication.clipboard().setPixmap(pixmap)
        self._persist_history_snapshot(pixmap)

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

    def _load_history(self) -> None:
        self._history_dir = Path.home() / ".test-assist" / "history"
        self._history_dir.mkdir(parents=True, exist_ok=True)
        # Remove blank/corrupt snapshots saved from blank canvas states (< 5 KB).
        for stale in self._history_dir.glob("*.png"):
            if stale.stat().st_size < 5000:
                stale.unlink(missing_ok=True)
        self._refresh_history()

    def _persist_history_snapshot(self, pixmap: QPixmap) -> None:
        # Skip saving if the image is too small to be a real capture (blank canvas states).
        if pixmap.width() < 50 or pixmap.height() < 50:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = self._history_dir / f"snapshot-{stamp}.png"
        pixmap.save(str(path), "PNG")
        self._refresh_history()

    def _refresh_history(self, _index: int | None = None) -> None:
        while self._snap_layout.count() > 1:
            item = self._snap_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        mode = self._history_filter.currentData()
        files = self._history_files_for_mode(mode)

        if not files:
            empty = QLabel("No snapshots in this range")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {MUTED}; padding: 8px;")
            self._snap_layout.insertWidget(0, empty)
            return

        for index, path in enumerate(files, start=1):
            thumb = _SnapshotThumb(path, index)
            thumb.load_requested.connect(self._load_history_snapshot)
            self._snap_layout.insertWidget(self._snap_layout.count() - 1, thumb)

    def _history_files_for_mode(self, mode: str | None) -> list[Path]:
        files = sorted(self._history_dir.glob("*.png"), key=lambda item: item.stat().st_mtime, reverse=True)
        now = datetime.now()

        if mode == "all":
            return files
        if mode == "today":
            return [item for item in files if datetime.fromtimestamp(item.stat().st_mtime).date() == now.date()]
        if mode == "week":
            cutoff = now - timedelta(days=7)
            return [item for item in files if datetime.fromtimestamp(item.stat().st_mtime) >= cutoff]
        if mode == "month":
            cutoff = now - timedelta(days=30)
            return [item for item in files if datetime.fromtimestamp(item.stat().st_mtime) >= cutoff]
        return files[:5]

    def _load_history_snapshot(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self._canvas.set_pixmap(pixmap)
        if self._fit_mode:
            self._fit_image()

    def _show_history_overlay(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("History Gallery")
        dlg.setModal(True)
        dlg.resize(920, 620)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        subtitle = QLabel("Browse snapshots by category and click a thumbnail to load it in the editor.")
        subtitle.setStyleSheet(f"color: {MUTED};")
        root.addWidget(subtitle)

        tabs = QTabWidget()
        categories = [
            ("Recent", "recent"),
            ("Today", "today"),
            ("This Week", "week"),
            ("This Month", "month"),
            ("All", "all"),
        ]

        for tab_name, mode in categories:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(0, 0, 0, 0)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            grid = QGridLayout(content)
            grid.setContentsMargins(4, 4, 4, 4)
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(8)

            files = self._history_files_for_mode(mode)
            if not files:
                empty = QLabel("No snapshots in this category")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty.setStyleSheet(f"color: {MUTED}; padding: 20px;")
                grid.addWidget(empty, 0, 0)
            else:
                for idx, path in enumerate(files, start=1):
                    thumb = _SnapshotThumb(path, idx, thumb_width=250)
                    thumb.load_requested.connect(self._load_history_snapshot)
                    thumb.load_requested.connect(lambda _p, d=dlg: d.accept())
                    row = (idx - 1) // 3
                    col = (idx - 1) % 3
                    grid.addWidget(thumb, row, col)

            scroll.setWidget(content)
            tab_layout.addWidget(scroll)
            tabs.addTab(tab, tab_name)

        root.addWidget(tabs)
        dlg.exec()

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_mode:
            self._fit_image()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {LINE}; border: none; max-height: 1px;")
        return line

    @staticmethod
    def _add_section(layout: QVBoxLayout, text: str, clickable: bool = False) -> QLabel | QPushButton:
        if clickable:
            btn = QPushButton(text.upper())
            btn.setObjectName("section_title")
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"text-align: left; color: {TEXT};")
            layout.addWidget(btn)
            return btn
        lbl = QLabel(text.upper())
        lbl.setObjectName("section_title")
        layout.addWidget(lbl)
        return lbl


# ─────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ─────────────────────────────────────────────────────────────────────────────

class _ColorButton(QPushButton):
    """A coloured swatch button that opens QColorDialog on click."""

    color_changed = Signal(str)

    def __init__(
        self,
        color: str = "#ff3b30",
        size: tuple = (36, 36),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(*size)
        self.setToolTip("Click to change colour")
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
        radius = min(8, min(self.width(), self.height()) // 2)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border-radius: {radius}px;
                border: 2px solid #3a3a5e;
            }}
            QPushButton:hover {{ border-color: #7c83fd; }}
        """)


class _SnapshotThumb(QFrame):
    """Clickable thumbnail shown in the snapshot gallery."""

    load_requested = Signal(object)  # QPixmap

    def __init__(
        self,
        image_path: Path,
        index: int,
        parent: QWidget | None = None,
        thumb_width: int = 168,
    ) -> None:
        super().__init__(parent)
        self._image_path = image_path
        self._pixmap = QPixmap(str(image_path))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click to reload this snapshot\n{image_path.name}")
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

        img   = QLabel()
        if self._pixmap.isNull():
            img.setText("Preview unavailable")
        else:
            thumb = self._pixmap.scaledToWidth(thumb_width, Qt.TransformationMode.SmoothTransformation)
            img.setPixmap(thumb)
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img)

        stamp = datetime.fromtimestamp(image_path.stat().st_mtime).strftime("%d %b %H:%M")
        lbl = QLabel(f"Snap {index} · {stamp}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.load_requested.emit(self._pixmap)
        super().mousePressEvent(event)
