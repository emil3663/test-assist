"""Screen capture overlay and frame recorder for Test Assist."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QRubberBand, QWidget


# ─────────────────────────────────────────────────────────────────────────────
# Screenshot overlay
# ─────────────────────────────────────────────────────────────────────────────

class ScreenshotOverlay(QWidget):
    """
    Fullscreen semi-transparent overlay.
    The user drags a rectangle to define the capture region.

    Signals
    -------
    capture_ready(QPixmap)  – emitted after the selected region is grabbed.
    cancelled()             – emitted when the user presses Escape or clicks
                              without dragging a meaningful region.
    """

    capture_ready = Signal(QPixmap)
    cancelled     = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._rubber  = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._origin  = QPoint()
        self._active  = False

    # ── Public ──────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """Cover all screens and ask the user to drag a selection."""
        virt = QApplication.primaryScreen().availableVirtualGeometry()
        self.setGeometry(virt)
        self.showFullScreen()
        self.activateWindow()
        self.raise_()

    # ── Mouse events ────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._rubber.setGeometry(QRect(self._origin, QSize()))
            self._rubber.show()
            self._active = True

    def mouseMoveEvent(self, event) -> None:
        if self._active:
            self._rubber.setGeometry(
                QRect(self._origin, event.position().toPoint()).normalized()
            )

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._active:
            self._active = False
            rect = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber.hide()
            self.hide()
            if rect.width() > 5 and rect.height() > 5:
                # Small delay so the overlay fully vanishes before grabbing.
                QTimer.singleShot(120, lambda: self._grab(rect))
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._rubber.hide()
            self.hide()
            self.cancelled.emit()

    # ── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        p.end()

    # ── Private ─────────────────────────────────────────────────────────────

    def _grab(self, rect: QRect) -> None:
        pixmap = QApplication.primaryScreen().grabWindow(
            0, rect.x(), rect.y(), rect.width(), rect.height()
        )
        self.capture_ready.emit(pixmap)


# ─────────────────────────────────────────────────────────────────────────────
# Frame-based screen recorder
# ─────────────────────────────────────────────────────────────────────────────

class FrameRecorder(QObject):
    """
    Captures the primary screen at ~15 fps using QScreen.

    Signals
    -------
    finished(str)  – emitted with the output path when the recording is saved.
    """

    finished = Signal(str)

    _FPS = 15

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._frames: list[QPixmap] = []
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)

    def start(self) -> None:
        self._frames = []
        self._timer.start(1000 // self._FPS)

    def stop(self) -> None:
        self._timer.stop()
        self._save()

    # ── Private ─────────────────────────────────────────────────────────────

    def _capture_frame(self) -> None:
        pixmap = QApplication.primaryScreen().grabWindow(0)
        self._frames.append(pixmap)

    def _save(self) -> None:
        if not self._frames:
            self.finished.emit("")
            return

        ts = int(time.time())
        output = str(Path.home() / f"test-recording-{ts}.mp4")

        try:
            import cv2      # type: ignore[import]
            import numpy as np  # type: ignore[import]

            h = self._frames[0].height()
            w = self._frames[0].width()
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output, fourcc, self._FPS, (w, h))

            for pixmap in self._frames:
                img = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
                ptr = img.bits()
                arr = np.frombuffer(ptr, dtype=np.uint8).reshape(h, w, 3).copy()
                writer.write(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

            writer.release()
            self.finished.emit(output)

        except ImportError:
            # No cv2 – fall back to a PNG frame sequence.
            frames_dir = Path.home() / f"test-recording-{ts}_frames"
            frames_dir.mkdir(exist_ok=True)
            for i, pixmap in enumerate(self._frames):
                pixmap.save(str(frames_dir / f"frame_{i:04d}.png"))
            self.finished.emit(str(frames_dir))

        finally:
            self._frames = []
