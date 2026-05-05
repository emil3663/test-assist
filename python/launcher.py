"""Floating always-on-top capture launcher for Test Assist (PySide6 edition)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from capture import FrameRecorder, ScreenshotOverlay


# ─────────────────────────────────────────────────────────────────────────────
# Floating launcher
# ─────────────────────────────────────────────────────────────────────────────

class FloatingLauncher(QWidget):
    """
    Small always-on-top overlay window that drives the capture workflow.

    • Photo mode  → drag-select a screen region → editor opens in background.
    • Video mode  → start / stop screen recording → file saved to home folder.

    Drag anywhere on the widget (outside a button) to reposition it.
    Right-click for a context menu with a Quit option.
    """

    def __init__(self, editor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._mode   = "photo"

        # Window chrome
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(280)

        # Screenshot overlay (shared, reused across captures)
        self._overlay = ScreenshotOverlay()
        self._overlay.capture_ready.connect(self._on_capture_ready)
        self._overlay.cancelled.connect(self._on_capture_cancelled)

        # Video recorder
        self._recorder    = FrameRecorder(self)
        self._recorder.finished.connect(self._on_record_finished)
        self._rec_seconds = 0
        self._rec_timer   = QTimer(self)
        self._rec_timer.timeout.connect(self._tick)

        # Drag-to-move state
        self._drag_pos: QPoint | None = None

        self._build_ui()
        self._set_mode("photo")
        self._position_top_right()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Floating panel (full UI) ──────────────────────────────────────────
        self._float_panel = QWidget(self)
        float_layout = QVBoxLayout(self._float_panel)
        float_layout.setContentsMargins(14, 14, 14, 14)
        float_layout.setSpacing(8)

        # Grip handle
        grip = QLabel()
        grip.setFixedHeight(4)
        grip.setStyleSheet(
            "QLabel { background-color: rgba(200,120,60,0.25); border-radius: 2px;"
            " margin: 0px 70px; }"
        )
        float_layout.addWidget(grip, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Header row: title + dock + close
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        title = QLabel("Test Assist")
        title.setStyleSheet(
            "color:#f0d0a0; font-size:14px; font-weight:700;"
            " background:transparent; letter-spacing:1px;"
        )
        header_row.addWidget(title, 1)

        self._btn_dock_right = QPushButton()
        self._btn_dock_right.setFixedSize(26, 26)
        self._btn_dock_right.setIcon(self._make_dock_icon())
        self._btn_dock_right.setIconSize(QSize(14, 14))
        self._btn_dock_right.setToolTip("Dock to right side")
        self._btn_dock_right.setStyleSheet(self._style_icon_btn())

        self._btn_open_editor = QPushButton()
        self._btn_open_editor.setFixedSize(26, 26)
        self._btn_open_editor.setIcon(self._make_ta_icon())
        self._btn_open_editor.setIconSize(QSize(14, 14))
        self._btn_open_editor.setToolTip("Open Editor")
        self._btn_open_editor.setStyleSheet(self._style_icon_btn())
        self._btn_open_editor.setEnabled(True)

        self._btn_close = QPushButton()
        self._btn_close.setFixedSize(26, 26)
        self._btn_close.setIcon(self._make_close_icon())
        self._btn_close.setIconSize(QSize(12, 12))
        self._btn_close.setToolTip("Close Test Assist")
        self._btn_close.setStyleSheet(self._style_icon_btn())

        header_row.addWidget(self._btn_open_editor)
        header_row.addWidget(self._btn_dock_right)
        header_row.addWidget(self._btn_close)
        float_layout.addLayout(header_row)

        # Action row: [Quick Capture] [📷] [🎥]
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self._btn_capture = QPushButton("Quick Capture")
        self._btn_capture.setFixedHeight(36)
        self._btn_capture.setStyleSheet(self._style_primary())

        self._btn_photo = QPushButton()
        self._btn_photo.setFixedSize(36, 36)
        self._btn_photo.setCheckable(True)
        self._btn_photo.setChecked(True)
        self._btn_photo.setToolTip("Photo mode — capture screenshot (Alt+P)")
        self._btn_photo.setStyleSheet(self._style_mode_icon(active=True))

        self._btn_video = QPushButton()
        self._btn_video.setFixedSize(36, 36)
        self._btn_video.setCheckable(True)
        self._btn_video.setToolTip("Video mode — record screen (Alt+V)")
        self._btn_video.setStyleSheet(self._style_mode_icon(active=False))

        self._btn_full_capture = QPushButton()
        self._btn_full_capture.setFixedSize(36, 36)
        self._btn_full_capture.setIcon(self._make_screen_icon("#b88d6f"))
        self._btn_full_capture.setIconSize(QSize(18, 18))
        self._btn_full_capture.setToolTip(
            "Capture full primary screen including taskbar/time (Alt+Shift+P)"
        )
        self._btn_full_capture.setStyleSheet(self._style_mode_icon(active=False))

        self._refresh_mode_icons()

        action_row.addWidget(self._btn_capture, 1)
        action_row.addWidget(self._btn_full_capture)
        action_row.addWidget(self._btn_photo)
        action_row.addWidget(self._btn_video)
        float_layout.addLayout(action_row)

        # Shortcut hint line below action row
        hint = QLabel("Alt+P · capture   ·   Alt+V · record")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:#7a6050; font-size:10px; background:transparent;")
        float_layout.addWidget(hint)

        # Recording timer (hidden until recording starts)
        self._rec_label = QLabel()
        self._rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_label.setStyleSheet(
            "color:#c04040; font-size:12px; font-weight:700; background:transparent;"
        )
        self._rec_label.hide()
        float_layout.addWidget(self._rec_label)

        # Status text
        self._status_lbl = QLabel()
        self._status_lbl.setWordWrap(True)
        self._status_lbl.hide()

        # Wire signals
        self._btn_photo.clicked.connect(lambda: self._set_mode("photo"))
        self._btn_video.clicked.connect(lambda: self._set_mode("video"))
        self._btn_capture.clicked.connect(self._on_action_click)
        self._btn_full_capture.clicked.connect(self._start_full_capture)
        self._btn_open_editor.clicked.connect(self._editor.bring_forward)
        self._btn_dock_right.clicked.connect(self._dock_right)
        self._btn_close.clicked.connect(self._close_launcher)

        outer.addWidget(self._float_panel)

        # ── Docked panel (compact vertical icon strip) ────────────────────────
        self._dock_panel = QWidget(self)
        dock_layout = QVBoxLayout(self._dock_panel)
        dock_layout.setContentsMargins(7, 14, 7, 14)
        dock_layout.setSpacing(10)
        dock_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        _btn_dock_editor = QPushButton()
        _btn_dock_editor.setFixedSize(36, 36)
        _btn_dock_editor.setIcon(self._make_ta_icon())
        _btn_dock_editor.setIconSize(QSize(18, 18))
        _btn_dock_editor.setToolTip("Open Editor")
        _btn_dock_editor.setStyleSheet(self._style_icon_btn())
        _btn_dock_editor.clicked.connect(self._editor.bring_forward)
        dock_layout.addWidget(_btn_dock_editor)

        _btn_dock_capture = QPushButton()
        _btn_dock_capture.setFixedSize(36, 36)
        _btn_dock_capture.setIcon(self._make_camera_icon("#f0d0a0"))
        _btn_dock_capture.setIconSize(QSize(20, 20))
        _btn_dock_capture.setToolTip("Quick Capture")
        _btn_dock_capture.setStyleSheet(self._style_icon_btn())
        _btn_dock_capture.clicked.connect(self._on_action_click)
        dock_layout.addWidget(_btn_dock_capture)

        _btn_undock = QPushButton()
        _btn_undock.setFixedSize(36, 36)
        _btn_undock.setIcon(self._make_undock_icon())
        _btn_undock.setIconSize(QSize(14, 14))
        _btn_undock.setToolTip("Restore floating launcher")
        _btn_undock.setStyleSheet(self._style_icon_btn())
        _btn_undock.clicked.connect(self._undock)
        dock_layout.addWidget(_btn_undock)

        self._dock_panel.hide()
        outer.addWidget(self._dock_panel)

    # ── Action dispatch ───────────────────────────────────────────────────────

    def _on_action_click(self) -> None:
        """Single action button dispatches to photo capture or video toggle."""
        if self._mode == "photo":
            self._start_capture()
        else:
            self._toggle_recording()

    # ── Mode management ───────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        is_photo = mode == "photo"

        self._btn_photo.setChecked(is_photo)
        self._btn_video.setChecked(not is_photo)
        self._btn_photo.setStyleSheet(self._style_mode_icon(active=is_photo))
        self._btn_video.setStyleSheet(self._style_mode_icon(active=not is_photo))
        self._refresh_mode_icons()

        if is_photo:
            self._btn_capture.setText("Quick Capture")
            self._btn_capture.setStyleSheet(self._style_primary())
            self._status_lbl.setText(
                "Drag to select a region after clicking Quick Capture."
            )
        else:
            # Don't overwrite "■ Stop Recording" if recording is in progress
            if not self._rec_timer.isActive():
                self._btn_capture.setText("⏺  Start Recording")
                self._btn_capture.setStyleSheet(self._style_danger())
            self._status_lbl.setText("Click to start a full-screen recording.")

        self.adjustSize()

    # ── Capture flow ─────────────────────────────────────────────────────────

    def _start_capture(self) -> None:
        self.hide()
        # Give the OS time to repaint the screen without this window.
        QTimer.singleShot(220, self._overlay.activate)

    def _start_full_capture(self) -> None:
        """Capture the full primary desktop, including taskbar and clock."""
        self.hide()
        QTimer.singleShot(220, self._grab_full_capture)

    def _grab_full_capture(self) -> None:
        pixmap = QApplication.primaryScreen().grabWindow(0)
        self._on_capture_ready(pixmap)

    def _on_capture_ready(self, pixmap: QPixmap) -> None:
        self.show()
        self._editor.load_pixmap(pixmap, background=True)
        self._btn_open_editor.setEnabled(True)

    def _on_capture_cancelled(self) -> None:
        self.show()
        self._status_lbl.setText("Capture cancelled. Ready for a new capture.")

    # ── Recording flow ────────────────────────────────────────────────────────

    def _toggle_recording(self) -> None:
        if self._rec_timer.isActive():
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        self._recorder.start()
        self._rec_seconds = 0
        self._rec_timer.start(1000)
        self._btn_capture.setText("■  Stop Recording")
        self._btn_capture.setStyleSheet(self._style_danger())
        self._rec_label.setText("⏺  00:00")
        self._rec_label.show()
        self._status_lbl.setText(
            "Recording in progress — click to stop and save."
        )

    def _stop_recording(self) -> None:
        self._rec_timer.stop()
        self._rec_label.hide()
        self._recorder.stop()
        self._btn_capture.setText("⏺  Start Recording")
        self._btn_capture.setStyleSheet(self._style_danger())
        self._status_lbl.setText("Recording stopped. Saving file…")

    def _tick(self) -> None:
        self._rec_seconds += 1
        m, s = divmod(self._rec_seconds, 60)
        self._rec_label.setText(f"⏺  {m:02d}:{s:02d}")

    def _on_record_finished(self, path: str) -> None:
        if path:
            self._status_lbl.setText(f"Saved: {path}")
        else:
            self._status_lbl.setText("Nothing was recorded.")

    def _refresh_mode_icons(self) -> None:
        """Repaint camera/video glyphs with active vs inactive colors."""
        active = "#f0d0a0"
        inactive = "#9b7a64"
        self._btn_photo.setIcon(
            self._make_camera_icon(active if self._mode == "photo" else inactive)
        )
        self._btn_video.setIcon(
            self._make_video_icon(active if self._mode == "video" else inactive)
        )
        self._btn_photo.setIconSize(QSize(18, 18))
        self._btn_video.setIconSize(QSize(18, 18))

    def _close_launcher(self) -> None:
        QApplication.instance().quit()

    # ── Drag-to-move ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ── Context menu (right-click to quit) ────────────────────────────────────

    def contextMenuEvent(self, event) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background:#13132a; border:1px solid #3a3a5e; border-radius:8px; padding:4px;
            }
            QMenu::item { padding:6px 20px; color:#e0e6f0; border-radius:4px; }
            QMenu::item:selected { background:rgba(124,131,253,0.12); color:#7c83fd; }
        """)
        act = menu.addAction("Quit Test Assist")
        act.triggered.connect(QApplication.instance().quit)
        menu.exec(event.globalPos())

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mods = event.modifiers()
        if mods == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_P:
            self._set_mode("photo")
            self._start_capture()
            return
        if (
            mods
            == (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)
            and key == Qt.Key.Key_P
        ):
            self._start_full_capture()
            return
        if mods == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_V:
            self._set_mode("video")
            self._toggle_recording()
            return
        super().keyPressEvent(event)

    # ── Custom background paint ────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(200, 120, 60, 80), 1))
        p.setBrush(QBrush(QColor(18, 12, 8, 242)))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()

    # ── Positioning ──────────────────────────────────────────────────────────

    def _position_top_right(self) -> None:
        geom = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geom.right() - self.width() - 20, geom.top() + 20)

    def _dock_right(self) -> None:
        self._float_panel.hide()
        self._dock_panel.show()
        self.setFixedWidth(50)
        self.adjustSize()
        geom = QApplication.primaryScreen().availableGeometry()
        y = geom.top() + max(20, (geom.height() - self.height()) // 2)
        self.move(geom.right() - self.width(), y)

    def _undock(self) -> None:
        self._dock_panel.hide()
        self._float_panel.show()
        self.setFixedWidth(280)
        self._position_top_right()

    # ── Button stylesheets ────────────────────────────────────────────────────

    @staticmethod
    def _style_primary() -> str:
        return """
            QPushButton {
                background-color: #c8763a;
                color: #fff8f0;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #d88848; }
            QPushButton:pressed { background-color: #a86030; }
        """

    @staticmethod
    def _style_danger() -> str:
        return """
            QPushButton {
                background-color: #c04040;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #d05050; }
            QPushButton:pressed { background-color: #a03030; }
        """

    @staticmethod
    def _style_outline() -> str:
        return """
            QPushButton {
                background-color: transparent;
                color: #b09070;
                border: 1px solid rgba(200,120,60,0.3);
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover    { border-color: #c8763a; color: #f0b880; }
            QPushButton:disabled { color: #5a4030; border-color: rgba(200,120,60,0.1); }
        """

    @staticmethod
    def _style_icon_btn() -> str:
        """Small icon button (dock / close) in muted orange."""
        return """
            QPushButton {
                background-color: rgba(200,120,60,0.08);
                color: #c8906a;
                border: 1px solid rgba(200,120,60,0.25);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(200,120,60,0.18);
                color: #f0b880;
                border-color: rgba(200,120,60,0.5);
            }
            QPushButton:pressed { background-color: rgba(200,120,60,0.30); }
        """

    @staticmethod
    def _style_mode_icon(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: rgba(200,120,60,0.22);
                    border: 1px solid rgba(200,120,60,0.65);
                    border-radius: 8px;
                }
                QPushButton:hover { background-color: rgba(200,120,60,0.32); }
            """
        return """
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(200,120,60,0.18);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(200,120,60,0.10);
            }
        """

    @staticmethod
    def _make_close_icon(color: str = "#f8d3ad") -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.8)
        p.setPen(pen)
        p.drawLine(3, 3, 11, 11)
        p.drawLine(11, 3, 3, 11)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_undock_icon(color: str = "#f8d3ad") -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        # Left-pointing arrow (restore/float)
        p.drawLine(11, 7, 4, 7)
        p.drawLine(4, 7, 7, 4)
        p.drawLine(4, 7, 7, 10)
        # Vertical bar on right (representing the docked edge)
        p.drawLine(12, 2, 12, 12)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_dock_icon(color: str = "#f8d3ad") -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        p.drawLine(2, 2, 2, 12)
        p.drawLine(4, 7, 11, 7)
        p.drawLine(8, 4, 11, 7)
        p.drawLine(8, 10, 11, 7)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_pencil_icon(color: str = "#f8d3ad") -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        p.drawLine(3, 11, 10, 4)
        p.drawLine(9, 3, 11, 5)
        p.drawLine(2, 12, 4, 10)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_ta_icon() -> QIcon:
        """Mini TA badge used for the editor-open toolbar button."""
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#d7873d"), 1))
        p.setBrush(QColor("#d7873d"))
        p.drawRoundedRect(1, 1, 12, 12, 3, 3)
        p.setPen(QColor("#1f1208"))
        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "TA")
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_camera_icon(color: str) -> QIcon:
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(2, 5, 14, 10, 2, 2)
        p.drawEllipse(7, 8, 4, 4)
        p.drawLine(5, 5, 7, 3)
        p.drawLine(7, 3, 11, 3)
        p.drawLine(11, 3, 13, 5)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_video_icon(color: str) -> QIcon:
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(2, 6, 9, 8, 1.5, 1.5)
        tri = QPolygonF([QPoint(11, 8), QPoint(16, 6), QPoint(16, 14), QPoint(11, 12)])
        p.drawPolygon(tri)
        p.end()
        return QIcon(pix)

    @staticmethod
    def _make_screen_icon(color: str) -> QIcon:
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(2, 3, 14, 10, 1.5, 1.5)
        p.drawLine(7, 14, 11, 14)
        p.drawLine(9, 13, 9, 11)
        p.end()
        return QIcon(pix)
