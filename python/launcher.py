"""Floating always-on-top capture launcher for Test Assist (PySide6 edition)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
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
        self.setFixedWidth(310)

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
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # Grip handle
        grip = QLabel()
        grip.setFixedHeight(5)
        grip.setStyleSheet("""
            QLabel {
                background-color: rgba(255,255,255,0.12);
                border-radius: 3px;
                margin: 0px 90px;
            }
        """)
        outer.addWidget(grip, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Header
        kicker = QLabel("Floating Control")
        kicker.setStyleSheet(
            "color:#9aa3ff; font-size:10px; letter-spacing:2px;"
            " font-weight:700; background:transparent;"
        )
        title = QLabel("Quick Capture")
        title.setStyleSheet(
            "color:#e0e6f0; font-size:16px; font-weight:700; background:transparent;"
        )
        outer.addWidget(kicker)
        outer.addWidget(title)

        # Mode toggle
        toggle_frame = QFrame()
        toggle_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.04);
                border-radius: 12px;
                border: none;
            }
        """)
        toggle_row = QHBoxLayout(toggle_frame)
        toggle_row.setContentsMargins(6, 6, 6, 6)
        toggle_row.setSpacing(6)

        self._btn_photo = QPushButton("📷  Photo")
        self._btn_video = QPushButton("🎥  Video")
        for btn in (self._btn_photo, self._btn_video):
            btn.setFixedHeight(34)
        toggle_row.addWidget(self._btn_photo)
        toggle_row.addWidget(self._btn_video)
        outer.addWidget(toggle_frame)

        # Primary action row
        self._btn_capture = QPushButton("📷  Quick Capture")
        self._btn_capture.setFixedHeight(38)
        self._btn_capture.setStyleSheet(self._style_primary())

        self._btn_record = QPushButton("⏺  Start Recording")
        self._btn_record.setFixedHeight(38)
        self._btn_record.setStyleSheet(self._style_danger())

        self._btn_open_editor = QPushButton("Open Editor")
        self._btn_open_editor.setFixedHeight(38)
        self._btn_open_editor.setStyleSheet(self._style_outline())
        self._btn_open_editor.setEnabled(False)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addWidget(self._btn_capture,     6)
        action_row.addWidget(self._btn_record,      6)
        action_row.addWidget(self._btn_open_editor, 4)
        outer.addLayout(action_row)

        # Recording timer (hidden until recording starts)
        self._rec_label = QLabel()
        self._rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_label.setStyleSheet(
            "color:#e94560; font-size:12px; font-weight:700; background:transparent;"
        )
        self._rec_label.hide()
        outer.addWidget(self._rec_label)

        # Status text
        self._status_lbl = QLabel()
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet(
            "color:#aab0c2; font-size:11px; background:transparent; line-height:1.5;"
        )
        outer.addWidget(self._status_lbl)

        # Wire signals
        self._btn_photo.clicked.connect(lambda: self._set_mode("photo"))
        self._btn_video.clicked.connect(lambda: self._set_mode("video"))
        self._btn_capture.clicked.connect(self._start_capture)
        self._btn_record.clicked.connect(self._toggle_recording)
        self._btn_open_editor.clicked.connect(self._editor.bring_forward)

    # ── Mode management ───────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        is_photo   = mode == "photo"

        self._btn_photo.setStyleSheet(self._style_mode_btn(active=is_photo))
        self._btn_video.setStyleSheet(self._style_mode_btn(active=not is_photo))
        self._btn_capture.setVisible(is_photo)
        self._btn_record.setVisible(not is_photo)

        if is_photo:
            self._status_lbl.setText(
                "Drag to select a region after clicking Quick Capture. "
                "The editor opens in the background after capture."
            )
        else:
            self._status_lbl.setText(
                "Start a full-screen recording. "
                "Stop when done — the file is saved to your home folder."
            )

        self.adjustSize()

    # ── Capture flow ─────────────────────────────────────────────────────────

    def _start_capture(self) -> None:
        self.hide()
        # Give the OS time to repaint the screen without this window.
        QTimer.singleShot(220, self._overlay.activate)

    def _on_capture_ready(self, pixmap: QPixmap) -> None:
        self.show()
        self._editor.load_pixmap(pixmap, background=True)
        self._btn_open_editor.setEnabled(True)
        self._status_lbl.setText(
            "Screenshot captured. Editor opened in the background — "
            "click 'Open Editor' whenever you're ready to annotate."
        )

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
        self._btn_record.setText("■  Stop Recording")
        self._rec_label.setText("⏺  00:00")
        self._rec_label.show()
        self._status_lbl.setText(
            "Recording in progress — click 'Stop Recording' to finish and save."
        )

    def _stop_recording(self) -> None:
        self._rec_timer.stop()
        self._rec_label.hide()
        self._recorder.stop()
        self._btn_record.setText("⏺  Start Recording")
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

    # ── Custom background paint ────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(124, 131, 253, 75), 1))
        p.setBrush(QBrush(QColor(16, 17, 35, 238)))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()

    # ── Positioning ──────────────────────────────────────────────────────────

    def _position_top_right(self) -> None:
        geom = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geom.right() - self.width() - 20, geom.top() + 20)

    # ── Button stylesheets ────────────────────────────────────────────────────

    @staticmethod
    def _style_primary() -> str:
        return """
            QPushButton {
                background-color: #7c83fd;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #9098fe; }
            QPushButton:pressed { background-color: #6870e8; }
        """

    @staticmethod
    def _style_danger() -> str:
        return """
            QPushButton {
                background-color: #e94560;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #f0607a; }
            QPushButton:pressed { background-color: #d03050; }
        """

    @staticmethod
    def _style_outline() -> str:
        return """
            QPushButton {
                background-color: transparent;
                color: #a0a8d8;
                border: 1px solid #3a3a5e;
                border-radius: 10px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover    { border-color: #7c83fd; color: #7c83fd; }
            QPushButton:disabled { color: #3a3a5e; border-color: #2a2a4e; }
        """

    @staticmethod
    def _style_mode_btn(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: rgba(124,131,253,0.16);
                    color: #eef0ff;
                    border: 1px solid rgba(124,131,253,0.5);
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 12px;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                color: #8892a4;
                border: 1px solid transparent;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ccd0f0;
                background-color: rgba(255,255,255,0.06);
            }
        """
