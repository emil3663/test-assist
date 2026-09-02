"""Screen capture overlay and frame recorder for Test Assist."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QRubberBand, QWidget

from screen_geometry import overlay_local_to_global, plan_capture


# ─────────────────────────────────────────────────────────────────────────────
# Screenshot overlay
# ─────────────────────────────────────────────────────────────────────────────

def _recordings_dir() -> Path:
    """Recordings live beside the capture history, not loose in the home folder."""
    path = Path.home() / ".test-assist" / "recordings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_ffmpeg_exe() -> str:
    """Locate the ffmpeg binary bundled with imageio_ffmpeg.

    Deliberately does not call imageio_ffmpeg.get_ffmpeg_exe() directly: it
    validates whatever it finds by running `ffmpeg -version` as a subprocess
    without redirecting stdin, and a process with no real stdin handle - this
    app is built with console=False, and a test runner's captured stdin has
    the same shape - can make that validation subprocess fail to start even
    though the binary itself is perfectly runnable. Finding the bundled binary
    by path sidesteps that check entirely.
    """
    import imageio_ffmpeg

    override = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if override:
        return override

    binaries_dir = Path(imageio_ffmpeg.__file__).resolve().parent / "binaries"
    matches = sorted(binaries_dir.glob("ffmpeg-*"))
    if matches:
        return str(matches[0])

    # No bundled binary found - fall back to the library's own resolution
    # (e.g. a system or conda ffmpeg), validity check and all.
    return imageio_ffmpeg.get_ffmpeg_exe()


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
        """Grab the selected region from whichever screen(s) it actually falls on.

        `rect` is in overlay-widget coordinates; the overlay is placed at the
        virtual desktop's origin (see activate()), so this has to be
        translated to global coordinates - and then back to screen-local
        coordinates for grabWindow() - before it means anything. A selection
        spanning two screens is composited from every intersecting screen
        rather than clamped to one, so a wide selection is never silently
        truncated to whichever screen holds the most of it.
        """
        screens = QApplication.screens()
        geometries = [screen.geometry() for screen in screens]
        virtual_origin = self.geometry().topLeft()
        global_rect = overlay_local_to_global(rect, virtual_origin)
        pieces = plan_capture(global_rect, geometries)

        if not pieces:
            # The selection touched no known screen - should not happen for a
            # real drag on a real overlay, but emit something rather than
            # nothing.
            pixmap = QApplication.primaryScreen().grabWindow(
                0, rect.x(), rect.y(), rect.width(), rect.height()
            )
            self.capture_ready.emit(pixmap)
            return

        result = QPixmap(global_rect.size())
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        for piece in pieces:
            screen = screens[piece.screen_index]
            local = piece.screen_local_rect
            grabbed = screen.grabWindow(0, local.x(), local.y(), local.width(), local.height())
            # Drawing into a fixed logical-pixel destination rect - rather
            # than at the grabbed pixmap's own size - is what accounts for
            # that screen's devicePixelRatio: grabWindow() already tags the
            # returned pixmap with it, and QPainter scales accordingly.
            painter.drawPixmap(QRect(piece.dest, local.size()), grabbed, grabbed.rect())
        painter.end()

        self.capture_ready.emit(result)


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
        self._screen = None

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

    def start(self, screen=None) -> None:
        """Begin recording `screen`, or the primary display if none is given.

        Previously always recorded QApplication.primaryScreen(), so a tester
        recording a repro on their secondary monitor silently got footage of
        the primary instead - with nothing to hint at it until playback.
        Recording pins the screen once at start rather than re-querying it
        every frame, so a window dragged between screens mid-recording does
        not make the recording jump displays underneath the user.
        """
        self._screen = screen if screen is not None else QApplication.primaryScreen()
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

        screen = self._screen
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

        if self._encode_frames(frames_dir, output):
            # The frames were only ever an intermediate step to the video.
            for frame_path in frames:
                frame_path.unlink(missing_ok=True)
            frames_dir.rmdir()
            self.finished.emit(str(output))
        else:
            # ffmpeg missing, failed, or timed out - the frame sequence on
            # disk is the recording. A recording is never lost to an encoding
            # failure.
            self.finished.emit(str(frames_dir))

    def _encode_frames(self, frames_dir: Path, output: Path) -> bool:
        """Assemble the frame sequence into an mp4 via ffmpeg.

        Returns False - never raises - on any failure: imageio_ffmpeg not
        installed, a non-zero exit, a timeout, or no output file, so the
        caller can fall back to keeping the frames.
        """
        try:
            ffmpeg_exe = _resolve_ffmpeg_exe()
        except Exception:
            return False

        import subprocess

        cmd = [
            ffmpeg_exe, "-y", "-loglevel", "error", "-nostdin",
            "-framerate", str(self._FPS),
            "-i", str(frames_dir / "frame_%05d.jpg"),
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output),
        ]
        try:
            result = subprocess.run(
                cmd,
                timeout=300,
                # The app is built with console=False; without this a
                # console window flashes on every save.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                capture_output=True,
                # Never inherit the caller's stdin - under a test runner it
                # may be a fake object subprocess cannot duplicate a handle
                # for, which raises before ffmpeg even starts.
                stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        return (
            result.returncode == 0
            and output.is_file()
            and output.stat().st_size > 0
        )
