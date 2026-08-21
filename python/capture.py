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

def _recordings_dir() -> Path:
    """Recordings live beside the capture history, not loose in the home folder."""
    path = Path.home() / ".test-assist" / "recordings"
    path.mkdir(parents=True, exist_ok=True)
    return path


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

    Frames are scaled, encoded and written to disk as they are captured, never
    accumulated in memory. The previous implementation appended a full
    resolution QPixmap per frame: measured at 1920x1080 that is 7.9 MB every
    1/15th of a second, so a one minute recording held about 7 GB and would
    exhaust memory long before the user pressed stop.

    Signals
    -------
    finished(str)   emitted with the output path when the recording is saved,
                    or an empty string if nothing was captured.
    progress(int)   emitted with the elapsed whole seconds, so the UI can show
                    how close the recording is to the cap.
    """

    finished = Signal(str)
    progress = Signal(int)

    _FPS = 15
    # Evidence for a defect report does not need native resolution, and full
    # size frames cannot be encoded inside the frame budget. 1280 wide costs
    # roughly half a frame interval to encode and stays legible.
    _MAX_WIDTH = 1280
    _JPEG_QUALITY = 75
    # A hard stop, so an unattended recording cannot fill the disk.
    _MAX_SECONDS = 180

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._capture_frame)
        self._frames_dir: Path | None = None
        self._count = 0
        self._dropped = 0
        self._stamp = 0

    # ── Public ──────────────────────────────────────────────────────────────

    @property
    def frame_count(self) -> int:
        return self._count

    @property
    def dropped_frames(self) -> int:
        """Frames the disk could not keep up with. Surfaced so a slow machine
        degrades visibly rather than silently."""
        return self._dropped

    @property
    def seconds_recorded(self) -> float:
        return self._count / self._FPS

    def start(self) -> None:
        self._stamp = int(time.time())
        self._frames_dir = _recordings_dir() / f"test-recording-{self._stamp}_frames"
        self._frames_dir.mkdir(parents=True, exist_ok=True)
        self._count = 0
        self._dropped = 0
        self._timer.start(1000 // self._FPS)

    def stop(self) -> None:
        self._timer.stop()
        self._save()

    def is_recording(self) -> bool:
        return self._timer.isActive()

    # ── Private ─────────────────────────────────────────────────────────────

    def _capture_frame(self) -> None:
        if self._frames_dir is None:
            return

        if self._count >= self._MAX_SECONDS * self._FPS:
            self.stop()
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        image = screen.grabWindow(0).toImage()
        if image.width() > self._MAX_WIDTH:
            image = image.scaledToWidth(
                self._MAX_WIDTH, Qt.TransformationMode.SmoothTransformation
            )

        path = self._frames_dir / f"frame_{self._count:05d}.jpg"
        if image.save(str(path), "JPG", self._JPEG_QUALITY):
            self._count += 1
            if self._count % self._FPS == 0:
                self.progress.emit(self._count // self._FPS)
        else:
            self._dropped += 1

    def _save(self) -> None:
        frames_dir = self._frames_dir
        self._frames_dir = None

        if frames_dir is None or self._count == 0:
            self.finished.emit("")
            return

        frames = sorted(frames_dir.glob("frame_*.jpg"))
        if not frames:
            # The counter and the disk disagree - a failed write, or the folder
            # was removed underneath us. Better an empty result than a crash.
            self.finished.emit("")
            return

        output = _recordings_dir() / f"test-recording-{self._stamp}.mp4"

        try:
            import cv2          # type: ignore[import]

            first = cv2.imread(str(frames[0]))
            if first is None:
                raise ImportError("unreadable frame")
            h, w = first.shape[:2]

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output), fourcc, self._FPS, (w, h))
            for frame_path in frames:
                frame = cv2.imread(str(frame_path))
                if frame is not None:
                    writer.write(frame)
            writer.release()

            # The frames were only ever an intermediate step to the video.
            for frame_path in frames:
                frame_path.unlink(missing_ok=True)
            frames_dir.rmdir()

            self.finished.emit(str(output))

        except ImportError:
            # No cv2 - the frame sequence on disk is the recording.
            self.finished.emit(str(frames_dir))
