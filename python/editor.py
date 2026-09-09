"""Annotation editor window for Test Assist (PySide6 edition)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import sys
import json
from pathlib import Path
import time
import webbrowser

from PySide6.QtCore import QObject, Qt, QSize, QSysInfo, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QColorDialog,
    QDialog,
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

import debug_log
import paths
from canvas import AnnotationCanvas
from theme import ACCENT, BG_800, LINE, MUTED, TEXT


# ─────────────────────────────────────────────────────────────────────────────
# Display info for bug reports
# ─────────────────────────────────────────────────────────────────────────────
# Kept as plain-data functions, separate from the QScreen-reading glue in
# _collect_screen_info(), so the formatting can be unit tested without a
# display - the same split used for the multi-display capture fix (issue #1),
# which is exactly the kind of question ("what does their monitor layout look
# like?") this exists to answer without a code read.

def _collect_screen_info() -> list[dict]:
    info = []
    for screen in QApplication.screens():
        geom = screen.geometry()
        info.append({
            "x": geom.x(), "y": geom.y(),
            "width": geom.width(), "height": geom.height(),
            "dpr": screen.devicePixelRatio(),
        })
    return info


def _format_screen_summary(screens: list[dict]) -> str:
    lines = [f"{len(screens)} screen(s):"]
    for index, screen in enumerate(screens):
        lines.append(
            f"  Screen {index}: {screen['width']}x{screen['height']}"
            f" at ({screen['x']}, {screen['y']}), DPR {screen['dpr']}"
        )
    return "\n".join(lines)


def _format_bug_report_details(version: str, os_description: str, screens: list[dict]) -> str:
    return "\n".join([f"Test Assist {version}", os_description, _format_screen_summary(screens)])


# ─────────────────────────────────────────────────────────────────────────────
# Editor window
# ─────────────────────────────────────────────────────────────────────────────

class EditorWindow(QMainWindow):
    """
    Full-screen annotation workspace.

    Opened via load_pixmap(background=True) so it appears behind the launcher
    without stealing focus. Call bring_forward() to raise it.
    """

    def __init__(self, version: str = "0.0.0") -> None:
        super().__init__()
        self._version = version
        # Always visible, shows up in any screenshot a reporter sends - the
        # window title was the only piece of the app that never mentioned the
        # version at all, so a bug report had no easy way to say what build
        # it came from.
        self.setWindowTitle(f"Test Assist {version} — Editor")
        self.setMinimumSize(960, 640)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._canvas = AnnotationCanvas()
        self._fit_mode = True
        # Set via set_show_launcher_callback(), wired from main.py alongside
        # the tray - editor.py takes a plain callable rather than importing
        # FloatingLauncher, which would create an import cycle.
        self._show_launcher_callback: Callable[[], None] | None = None
        # Same reasoning, for Check for Updates (TA-218): it previously
        # existed only on the launcher, so a user working from the Editor
        # had no path to it without switching back. Wired to the
        # launcher's own _check_for_updates() (and its one shared
        # UpdateChecker/QNetworkAccessManager, not a duplicate) rather
        # than the Editor building its own network stack.
        self._check_updates_callback: Callable[[], None] | None = None

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidgetResizable(False)
        self._scroll = scroll

        # Central widget: tool row, settings row, then canvas beside the
        # controls panel. Both top rows are full window width - a real
        # QDockWidget for the controls panel would claim its own 185px
        # ahead of the central widget's own layout, leaving no way for a
        # row inside that central widget to ever reach full window width;
        # a plain QWidget panel placed in the same QHBoxLayout as the
        # canvas does not have that effect. The panel had
        # NoDockWidgetFeatures set anyway (no float/move/close), so this
        # changes nothing behaviourally.
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._build_tools_bar())
        central_layout.addWidget(self._build_settings_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(scroll, 1)
        body.addWidget(self._build_right_panel())
        central_layout.addLayout(body)

        self.setCentralWidget(central)

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

    def record_capture(self, pixmap: QPixmap) -> None:
        """Load a freshly taken capture (region or full-screen) AND
        persist it to History immediately (TA-216).

        Deliberately not folded into load_pixmap() itself: that method is
        also how an existing image gets viewed - a history snapshot
        reloaded, a file opened, a clipboard paste - and none of those
        should create a new History entry every time they're viewed. This
        is the one call a genuinely new capture needs in addition to
        load_pixmap(); the launcher's _on_capture_ready() is the single
        choke point both region and full-screen captures already pass
        through, so it is the one call site that needs to use this
        instead of load_pixmap() directly. Reuses
        _persist_history_snapshot()'s existing "too small to be a real
        capture" guard unchanged.
        """
        self.load_pixmap(pixmap, background=True)
        self._persist_history_snapshot(pixmap)

    def refresh_history(self) -> None:
        """Re-scan History from disk (TA-215).

        A finished recording is saved straight to recordings_dir() by
        FrameRecorder, with nothing routing back through
        _persist_history_snapshot() the way a still capture does - so
        without an explicit call here, it would only show up the next time
        History rebuilds on its own (e.g. editor restart), not live. Public
        because the launcher, which has no editor.py import (avoids an
        import cycle - editor.py doesn't import launcher.py either), needs
        to call this from _on_record_finished() the same way it already
        calls record_capture() and bring_forward().
        """
        self._refresh_history()

    def bring_forward(self) -> None:
        """Raise and activate the editor window - or minimize it if it is
        already the active window (TA-220), so the TA icon (floating and
        docked) and the tray's "Open Editor" all act as a show/hide toggle
        rather than a no-op re-raise when the editor is already what the
        user is looking at.
        """
        active = self.isActiveWindow()
        minimized = self.isMinimized()
        # TA-220: the minimize toggle was reported not to fire reliably
        # (unconfirmed - a plausible cause is isActiveWindow() reading
        # False because the click that triggers this happens on a
        # *different* top-level window, before Windows has reported the
        # Editor as active). No second monitor/interactive session here to
        # reproduce it, so this logs the values instead of guessing at a
        # fix - see docs/ta215-225-fix-brief.md.
        debug_log.log(f"bring_forward: isActiveWindow={active} isMinimized={minimized}")
        if active and not minimized:
            self.showMinimized()
            return
        if minimized:
            # show() alone does not restore from a minimized state. Qt
            # keeps both WindowMinimized and WindowMaximized set together
            # on a window that was maximized before being minimized, so
            # unconditionally calling showNormal() silently dropped a
            # maximized editor to windowed size on restore (TA-220) -
            # check for that combination first.
            if self.windowState() & Qt.WindowState.WindowMaximized:
                self.showMaximized()
            else:
                self.showNormal()
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.show()
        self.activateWindow()
        self.raise_()

    def load_image_path(self, path: str) -> bool:
        """Load an image file into the canvas and bring the editor forward.

        The entry point for both "Open with -> Test Assist" (a file
        argument at first-instance startup) and a second-instance handoff
        (single_instance.py's `open_requested`) - both hand this a raw,
        unvalidated path. A path that does not exist, is not a real image,
        or fails to decode shows a plain warning and returns False rather
        than raising or silently starting the editor on nothing - a caller
        must never mistake a failed open for a working one.
        """
        file = Path(path)
        if not file.is_file():
            QMessageBox.warning(
                self, "Test Assist",
                f"Can't open this file - it doesn't exist:\n{path}",
            )
            return False

        pixmap = QPixmap(str(file))
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Test Assist",
                f"Can't open this file - it isn't a readable image:\n{path}",
            )
            return False

        self.load_pixmap(pixmap, background=False)
        return True

    def set_show_launcher_callback(self, callback: Callable[[], None]) -> None:
        """Wire up the editor's "Show Launcher" button.

        Once the launcher's own X hides it, the tray was the only route
        back - and Windows hides a new tray icon in the overflow by
        default. Takes a plain callable (in practice FloatingLauncher.
        restore) rather than a FloatingLauncher instance, so editor.py
        never has to import launcher.py.
        """
        self._show_launcher_callback = callback

    def set_check_updates_callback(self, callback: Callable[[], None]) -> None:
        """Wire up the editor's "Check for Updates" button (TA-218) -
        Check for Updates existed only on the launcher, so a user working
        from the Editor had no path to it without switching back. Takes a
        plain callable (in practice the launcher's own
        _check_for_updates(), reusing its one UpdateChecker rather than
        building a second network stack) so editor.py never has to
        import launcher.py.
        """
        self._check_updates_callback = callback

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

        # Open Image button — with the editor open and nothing loaded,
        # History (past app-generated exports) and a fresh capture were
        # the only ways to bring an image in; there was no way to pull in
        # an external file (TA-214).
        self._btn_open_image = QPushButton("📂")
        self._btn_open_image.setObjectName("btn_open_image")
        self._btn_open_image.setProperty("smallIconButton", True)
        self._btn_open_image.setFixedSize(28, 28)
        self._btn_open_image.setToolTip("Open Image…")
        self._btn_open_image.clicked.connect(self._open_image_file)
        layout.addWidget(self._btn_open_image, 0, Qt.AlignmentFlag.AlignVCenter)

        # Check for Updates button — previously reachable only from the
        # launcher, so a user working from the Editor had no path to it
        # without switching back (TA-218). No-op until
        # set_check_updates_callback() is wired, same as Show Launcher.
        self._btn_check_updates = QPushButton("🔄")
        self._btn_check_updates.setObjectName("btn_check_updates")
        self._btn_check_updates.setProperty("smallIconButton", True)
        self._btn_check_updates.setFixedSize(28, 28)
        self._btn_check_updates.setToolTip("Check for Updates")
        self._btn_check_updates.clicked.connect(self._on_check_updates_clicked)
        layout.addWidget(self._btn_check_updates, 0, Qt.AlignmentFlag.AlignVCenter)

        # Show Launcher button — beside About and Help, far right of toolbar.
        # Once the launcher is hidden (its own X, or the tray), this is the
        # only route back besides the tray icon, which Windows hides in the
        # overflow by default.
        self._show_launcher_btn = QPushButton("🏠")
        self._show_launcher_btn.setObjectName("btn_show_launcher")
        self._show_launcher_btn.setProperty("smallIconButton", True)
        self._show_launcher_btn.setFixedSize(28, 28)
        self._show_launcher_btn.setToolTip("Show Launcher")
        self._show_launcher_btn.clicked.connect(self._on_show_launcher_clicked)
        layout.addWidget(self._show_launcher_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # About button — beside Help, far right of toolbar
        self._about_btn = QPushButton("ⓘ")
        self._about_btn.setObjectName("btn_about")
        self._about_btn.setProperty("smallIconButton", True)
        self._about_btn.setFixedSize(28, 28)
        self._about_btn.setToolTip("About Test Assist")
        self._about_btn.clicked.connect(self._open_about)
        layout.addWidget(self._about_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Help button — far right of toolbar
        help_btn = QPushButton("?")
        help_btn.setObjectName("btn_help")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Open Help")
        help_btn.clicked.connect(self._open_help)
        layout.addWidget(help_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        return bar

    # ── Settings bar (zoom, style, export) ──────────────────────────────────────

    def _build_settings_bar(self) -> QFrame:
        """Zoom, stroke, arrow style, fill opacity and the export actions.

        Moved here from the right dock: at a fixed 185px, that dock had to
        fit Edit, all of this, and History, which squeezed History in
        particular. This is a full-width row rather than being squeezed
        into the gap between the tool row and the About/Help buttons on the
        row above - that gap is under 400px on a wide window and zero at
        the 960px minimum window width, and these controls need close to
        the full width to lay out horizontally at all.
        """
        bar = QFrame()
        bar.setObjectName("settings_bar")
        bar.setStyleSheet(
            f"QFrame#settings_bar {{ background-color: {BG_800};"
            f" border-bottom: 1px solid {LINE}; }}"
        )
        bar.setFixedHeight(40)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Leading stretch (TA-222): _build_tools_bar() centers its content
        # as one group with a stretch on both sides; this row only had the
        # trailing one, so it packed flush left while the row above it
        # centered - matching that pattern here makes both rows read as
        # the same layout system stacked vertically.
        layout.addStretch()

        # ── Zoom ──────────────────────────────────────────────────────────
        # No text label: at this width, a tooltip on each control carries the
        # meaning that a "Zoom"/"Stroke"/"Arrow"/"Fill" label used to - the
        # same tradeoff the launcher's own icon buttons already make.
        self._btn_zoom_out = QPushButton("-")
        self._btn_zoom_out.setObjectName("btn_zoom_out")
        self._btn_zoom_out.setProperty("smallIconButton", True)
        self._btn_zoom_out.setFixedSize(22, 22)
        self._btn_zoom_out.setToolTip("Zoom out")
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(25, 300)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(60)
        self._zoom_slider.setToolTip("Zoom")
        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.setObjectName("btn_zoom_in")
        self._btn_zoom_in.setProperty("smallIconButton", True)
        self._btn_zoom_in.setFixedSize(22, 22)
        self._btn_zoom_in.setToolTip("Zoom in")
        self._zoom_pct = QLabel("100 %")
        self._zoom_pct.setFixedWidth(38)
        self._btn_fit = QPushButton("Fit")
        self._btn_fit.setObjectName("btn_fit")
        self._btn_fit.setProperty("smallIconButton", True)
        self._btn_fit.setFixedSize(30, 22)
        self._btn_fit.setToolTip("Fit to window")
        layout.addWidget(self._btn_zoom_out)
        layout.addWidget(self._zoom_slider)
        layout.addWidget(self._btn_zoom_in)
        layout.addWidget(self._zoom_pct)
        layout.addWidget(self._btn_fit)

        layout.addWidget(self._vseparator())

        # ── Stroke size ───────────────────────────────────────────────────
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 20)
        self._size_slider.setValue(3)
        self._size_slider.setFixedWidth(55)
        self._size_slider.setToolTip("Stroke size")
        self._size_lbl = QLabel("3 px")
        self._size_lbl.setFixedWidth(32)
        layout.addWidget(self._size_slider)
        layout.addWidget(self._size_lbl)

        layout.addWidget(self._vseparator())

        # ── Arrow style ───────────────────────────────────────────────────
        self._arrow_style_combo = QComboBox()
        self._arrow_style_combo.addItem("Classic", "classic")
        self._arrow_style_combo.addItem("Double", "double")
        self._arrow_style_combo.addItem("Dashed", "dashed")
        self._arrow_style_combo.setCurrentIndex(0)
        self._arrow_style_combo.setFixedWidth(126)  # fits "Classic"/"Dashed" without eliding
        self._arrow_style_combo.setToolTip("Arrow style")
        layout.addWidget(self._arrow_style_combo)

        layout.addWidget(self._vseparator())

        # ── Fill opacity ──────────────────────────────────────────────────
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(30)
        self._opacity_slider.setFixedWidth(55)
        self._opacity_slider.setToolTip("Highlight fill opacity")
        self._opacity_lbl = QLabel("30 %")
        self._opacity_lbl.setFixedWidth(32)
        layout.addWidget(self._opacity_slider)
        layout.addWidget(self._opacity_lbl)

        layout.addStretch(1)

        # ── Export ────────────────────────────────────────────────────────
        # No setFixedHeight() (TA-221): the QSS QPushButton rule's own
        # padding needs more vertical room than 26px left for a 12px font,
        # clipping descenders ("Copy" -> "Copv", "Export" -> "Exoort").
        # Sizing naturally from the stylesheet, like most other buttons in
        # this file already do, can't drift out of sync with it again the
        # way a second hand-tuned pixel height could.
        self._btn_copy = QPushButton("Copy")
        self._btn_copy.setToolTip("Copy annotated image to clipboard")
        layout.addWidget(self._btn_copy)

        self._btn_export_json = QPushButton("Export")
        self._btn_export_json.setToolTip("Export annotations as JSON")
        layout.addWidget(self._btn_export_json)

        # Kept visually primary via the accent-filled btn_primary style and
        # a taller, wider button than the strip around it - this is still
        # the main action of the screen, not just another button in a row.
        self._btn_save_png = QPushButton("💾  Save PNG")
        self._btn_save_png.setObjectName("btn_primary")
        self._btn_save_png.setFixedHeight(28)
        layout.addWidget(self._btn_save_png)

        return bar

    # ── Right controls panel ─────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("right_panel")
        panel.setFixedWidth(185)
        panel.setStyleSheet(f"QWidget#right_panel {{ border-left: 1px solid {LINE}; }}")

        layout = QVBoxLayout(panel)
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

        # ── History / Snapshots ─────────────────────────────────────────
        # Zoom, Stroke, Arrow, Highlight Fill and the export actions moved
        # to a full-width settings bar under the tool row (see
        # _build_settings_bar()) - this dock now holds only Edit and
        # History, which is what lets History take the height freed up.
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

        return panel

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._tool_group.buttonClicked.connect(self._on_tool_changed)
        self._canvas.text_editing_changed.connect(self._set_tool_shortcuts_enabled)
        self._canvas.selection_changed.connect(self._on_selection_changed)

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
        self._on_selection_changed(self._canvas.has_selection())

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Z"), self, self._canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._canvas.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_png)
        QShortcut(QKeySequence("Ctrl+V"), self, self._paste_from_clipboard)
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

    def _on_selection_changed(self, has_selection: bool) -> None:
        """Grey out the buttons that need a selection, so the toolbar says what
        is currently possible instead of offering four no-ops."""
        for button in (
            self._btn_delete, self._btn_front,
            self._btn_back, self._btn_backmost,
        ):
            button.setEnabled(has_selection)

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

    def _on_show_launcher_clicked(self) -> None:
        if self._show_launcher_callback is not None:
            self._show_launcher_callback()

    def _on_check_updates_clicked(self) -> None:
        if self._check_updates_callback is not None:
            self._check_updates_callback()

    def _open_image_file(self) -> None:
        """TA-214: the discoverable control for bringing an external file
        into the editor. Routes through load_image_path() rather than
        loading the chosen path directly, so a bad selection gets exactly
        the same validation and warning as "Open with" and the
        second-instance handoff already do - one behaviour, three entry
        points, not three reimplementations of it.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", str(paths.recordings_dir()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)",
        )
        if path:
            self.load_image_path(path)

    def _paste_from_clipboard(self) -> None:
        """Ctrl+V (TA-214). An empty clipboard - no image on it at all -
        must be a plain no-op with a status message, never a crash and
        never a blank canvas presenting itself as a successful paste.
        Guarded against an in-progress text annotation: that edit is its
        own text-entry surface and must not have an image silently
        dropped over it out from under the user.
        """
        if self._canvas._text_editing:
            return
        image = QApplication.clipboard().image()
        if image.isNull():
            self.statusBar().showMessage("Clipboard has no image to paste.", 4000)
            return
        self.load_pixmap(QPixmap.fromImage(image), background=False)

    def _open_help(self) -> None:
        # resolves both from a source checkout and from a PyInstaller bundle
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        help_file = base / "help.html"
        webbrowser.open(help_file.as_uri())

    def _open_about(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("About Test Assist")
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel(f"Test Assist {self._version}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT};")
        layout.addWidget(title)

        os_line = QLabel(QSysInfo.prettyProductName())
        os_line.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(os_line)

        screens_label = QLabel(_format_screen_summary(_collect_screen_info()))
        screens_label.setWordWrap(True)
        screens_label.setStyleSheet(
            f"color: {MUTED}; font-family: Consolas, 'Cascadia Code', monospace; font-size: 12px;"
        )
        layout.addWidget(screens_label)

        copy_btn = QPushButton("Copy details for a bug report")
        copy_btn.clicked.connect(self._copy_bug_report_details)
        layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        dlg.exec()

    def _copy_bug_report_details(self) -> None:
        """A reporter cannot describe a monitor layout in a bug report as
        well as pasting it can - issue #1 needed a code read to diagnose a
        mixed-DPI question a pasted display list would have answered at once.
        """
        details = _format_bug_report_details(
            self._version, QSysInfo.prettyProductName(), _collect_screen_info(),
        )
        QApplication.clipboard().setText(details)

    def _save_png(self) -> None:
        pixmap = self._canvas.export_pixmap()
        if not pixmap:
            return
        # paths.recordings_dir(), not a bare filename: with no directory
        # hint Qt's dialog falls back to the last-used folder or the
        # current working directory - on Windows, launched via a shortcut,
        # that's the app's own install folder (TA-219). recordings_dir()
        # already creates Documents\Test Assist if it doesn't exist yet.
        default = str(paths.recordings_dir() / f"test-assist-{int(time.time())}.png")
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
        default = str(paths.recordings_dir() / f"annotations-{int(time.time())}.json")
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", default, "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)

    def _load_history(self) -> None:
        # AppLocalDataLocation, not Documents - see paths.py. This folder is
        # auto-pruned below on every launch, which must never happen to a
        # folder the user keeps things in.
        self._history_dir = paths.history_dir()
        self._prune_unreadable_history()
        self._refresh_history()

    def _prune_unreadable_history(self) -> None:
        """Remove snapshots that are not loadable images.

        This used to delete anything under 5 KB, which is a file-size proxy for
        "blank or corrupt". It is a bad proxy: a capture of a dialog or a form
        on a plain background compresses well under 5 KB, so real evidence was
        being deleted on the next launch. Readability is the thing actually
        being tested for, so test for it directly.
        """
        for candidate in self._history_dir.glob("*.png"):
            image = QImage(str(candidate))
            if image.isNull() or image.width() == 0 or image.height() == 0:
                candidate.unlink(missing_ok=True)

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
            if path.suffix == ".png":
                thumb = _SnapshotThumb(path, index)
                thumb.load_requested.connect(self._load_history_snapshot)
            else:
                thumb = _RecordingThumb(path, index)
                thumb.open_requested.connect(self._open_recording)
            self._snap_layout.insertWidget(self._snap_layout.count() - 1, thumb)

    def _recording_entries(self) -> list[Path]:
        """Recordings live in recordings_dir(), never history_dir() - so
        _prune_unreadable_history() (which only ever globs history_dir())
        can never delete one. A finished recording is either a single .mp4,
        or - if encoding fell back - the kept *_frames folder."""
        directory = paths.recordings_dir()
        return list(directory.glob("*.mp4")) + [p for p in directory.glob("*_frames") if p.is_dir()]

    def _history_files_for_mode(self, mode: str | None) -> list[Path]:
        files = self._recording_entries() + list(self._history_dir.glob("*.png"))
        files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
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

    def _open_recording(self, path: Path) -> None:
        """Opens a recording externally - the system video player for an
        mp4, or the containing folder for a kept frame sequence, since there
        is no single file to hand a player. Never decoded, extracted or
        played in-app - discoverability only."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
                    if path.suffix == ".png":
                        thumb = _SnapshotThumb(path, idx, thumb_width=250)
                        thumb.load_requested.connect(self._load_history_snapshot)
                        thumb.load_requested.connect(lambda _p, d=dlg: d.accept())
                    else:
                        thumb = _RecordingThumb(path, idx, thumb_width=250)
                        thumb.open_requested.connect(self._open_recording)
                        thumb.open_requested.connect(lambda _p, d=dlg: d.accept())
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
    def _vseparator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"background-color: {LINE}; border: none; max-width: 1px;")
        line.setFixedWidth(1)
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


class _ThumbnailBackfillWorker(QObject):
    """Runs ensure_recording_thumbnail() off the GUI thread.

    Standard Qt worker-object idiom (moveToThread(), not a QThread
    subclass): ffmpeg extraction can take real wall-clock time, and a
    gallery full of pre-thumbnail recordings must not stall the UI while
    each one is backfilled. `finished` is connected directly to a bound
    method on the requesting widget, never a bare lambda - Qt only
    auto-queues a cross-thread connection back to the GUI thread when it
    can see the receiver's own thread affinity, which a plain callable
    does not carry.
    """

    finished = Signal(object)  # Path | None

    def __init__(self, recording_path: Path) -> None:
        super().__init__()
        self._recording_path = recording_path

    def run(self) -> None:
        import capture
        self.finished.emit(capture.ensure_recording_thumbnail(self._recording_path))


class _RecordingThumb(QFrame):
    """Clickable card representing a recording in the gallery.

    Shows the recording's first frame as a thumbnail once one is available -
    from cache immediately, or backfilled in the background for a recording
    saved before thumbnails existed - with a play badge always overlaid, so
    a recording is never mistakable for a screenshot at a glance the way a
    bare thumbnail would be. Falls back to (and never leaves worse than) the
    original generic icon when no thumbnail can be produced: extraction
    fails, ffmpeg is missing, or the source frames are already gone.

    Deliberately never a decoded frame *for playback*: clicking still opens
    the recording in the system's own player (or its containing folder, for
    a kept frame sequence) rather than attempting any in-app playback -
    discoverability only.
    """

    open_requested = Signal(Path)

    def __init__(
        self,
        recording_path: Path,
        index: int,
        parent: QWidget | None = None,
        thumb_width: int = 168,
    ) -> None:
        super().__init__(parent)
        self._recording_path = recording_path
        self._is_kept_frames = recording_path.is_dir()
        self._thumb_width = thumb_width
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            (f"Click to open the containing folder\n{recording_path.name}")
            if self._is_kept_frames
            else (f"Click to open in your video player\n{recording_path.name}")
        )
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #4a3a2a;
                border-radius: 8px;
                background: rgba(200,120,60,0.06);
            }
            QFrame:hover { border-color: #c8763a; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedHeight(max(60, thumb_width // 2))
        layout.addWidget(self._preview)
        self._show_fallback_icon()

        # A fixed-size badge, always present, on top of whatever _preview
        # is showing - a real thumbnail looks exactly like a screenshot
        # without it. Parented directly to self (a sibling of _preview in
        # the layout, not a child of it) and positioned in resizeEvent,
        # since _preview's own geometry isn't final until layout runs.
        self._badge = QLabel("▶", self)
        self._badge.setStyleSheet(
            "QLabel { color: #ffffff; background: rgba(0,0,0,0.55);"
            " border-radius: 9px; font-size: 11px; padding: 1px 6px 1px 8px; }"
        )
        self._badge.adjustSize()
        self._badge.raise_()

        stamp = datetime.fromtimestamp(recording_path.stat().st_mtime).strftime("%d %b %H:%M")
        kind = "Recording (frames)" if self._is_kept_frames else "Recording"
        label = QLabel(f"{kind} {index} · {stamp}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)

        if not self._is_kept_frames:
            # A kept-frames folder has no video to extract a frame from -
            # the generic icon is the only honest option there.
            self._load_thumbnail()

    def _show_fallback_icon(self) -> None:
        self._preview.setPixmap(QPixmap())
        self._preview.setText("🎞" if self._is_kept_frames else "🎥")
        self._preview.setStyleSheet("font-size: 28px; background: transparent;")

    def _show_thumbnail(self, thumbnail_path: Path) -> None:
        pixmap = QPixmap(str(thumbnail_path))
        if pixmap.isNull():
            return
        self._preview.setStyleSheet("background: transparent;")
        self._preview.setText("")
        self._preview.setPixmap(
            pixmap.scaledToWidth(self._thumb_width, Qt.TransformationMode.SmoothTransformation)
        )

    def _load_thumbnail(self) -> None:
        """A cached thumbnail loads immediately, no subprocess involved. A
        missing one is backfilled off the GUI thread - see
        _ThumbnailBackfillWorker - and swapped in once ready; the fallback
        icon is already showing while that runs, so there is nothing to
        block on.
        """
        import capture

        cached = capture.thumbnail_path_for(self._recording_path)
        if cached.is_file():
            self._show_thumbnail(cached)
            return

        thread = QThread()
        worker = _ThumbnailBackfillWorker(self._recording_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_thumbnail_backfilled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: _forget_thumbnail_thread(thread))
        thread.finished.connect(thread.deleteLater)
        # Both thread and worker, not just thread: moveToThread() does not
        # keep worker alive on its own, and with no Python reference left
        # once this method returns, worker could be garbage-collected while
        # the background thread is still using it - a genuine
        # use-after-free, not a hypothetical one (caught by a crash, not a
        # hang, when this was tried with only `thread` kept).
        _pending_thumbnail_threads.append((thread, worker))
        thread.start()

    def _on_thumbnail_backfilled(self, thumbnail_path) -> None:
        if thumbnail_path is not None:
            self._show_thumbnail(thumbnail_path)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        preview_rect = self._preview.geometry()
        self._badge.move(
            max(preview_rect.left(), preview_rect.right() - self._badge.width() - 6),
            max(preview_rect.top(), preview_rect.bottom() - self._badge.height() - 6),
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self._recording_path)
        super().mousePressEvent(event)


# Kept alive here, not just as an attribute on the (possibly short-lived)
# _RecordingThumb that started them: a QThread (and its worker) with no
# Qt-parent and no remaining Python reference is a premature-collection
# hazard, and parenting the thread to the thumb widget instead would risk
# "QThread: Destroyed while thread is still running" if the gallery dialog
# closes before a backfill finishes. Each (thread, worker) pair removes
# itself once the thread's own `finished` fires - by which point run() has
# genuinely returned, unlike worker.finished (emitted first, while the
# thread is still tearing down).
_pending_thumbnail_threads: list[tuple[QThread, "_ThumbnailBackfillWorker"]] = []


def _forget_thumbnail_thread(thread: QThread) -> None:
    for pair in list(_pending_thumbnail_threads):
        if pair[0] is thread:
            _pending_thumbnail_threads.remove(pair)
