"""Screen capture overlay and frame recorder for Test Assist."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QRubberBand, QWidget

import debug_log
import paths
from screen_geometry import (
    composite_ratio,
    device_result_size,
    plan_capture,
    to_device_rect,
)


# ─────────────────────────────────────────────────────────────────────────────
# Screenshot overlay
# ─────────────────────────────────────────────────────────────────────────────

def _recordings_dir() -> Path:
    """Recordings live in Documents\\Test Assist, not ~/.test-assist - see
    paths.py for why."""
    return paths.recordings_dir()


# A recording's gallery thumbnail is regenerable cache, not evidence, so it
# lives in history_dir() (AppData) rather than alongside the recording in
# recordings_dir() (Documents) - same split paths.py already draws between
# the two. Named from the recording's own stem with a suffix that never
# matches history's own "*.png" snapshot glob, so
# EditorWindow._prune_unreadable_history() can neither mistake one for a
# snapshot nor delete it.
_THUMBNAIL_WIDTH = 320


def thumbnail_path_for(recording: Path) -> Path:
    """Where `recording`'s cached gallery thumbnail lives, whether or not
    it has been generated yet."""
    return paths.history_dir() / f"{recording.stem}.thumb.jpg"


def _write_thumbnail(image: QImage, destination: Path) -> bool:
    if image.isNull():
        return False
    if image.width() > _THUMBNAIL_WIDTH:
        image = image.scaledToWidth(_THUMBNAIL_WIDTH, Qt.TransformationMode.SmoothTransformation)
    return image.save(str(destination), "JPG", 80)


def ensure_recording_thumbnail(recording: Path, timeout: float = 3.0) -> Path | None:
    """Return the cached gallery thumbnail for `recording`, extracting one
    with the bundled ffmpeg on first use if it is not already cached.

    This is the backfill path for a recording saved before thumbnails
    existed, or one whose frames are already gone - the cheap path (a
    frame already on disk at record time) is FrameRecorder._save(), below.
    Runs synchronously and can take real wall-clock time; callers that must
    not block a UI thread are responsible for calling this off it (see
    editor.py's _RecordingThumb). Never raises: ffmpeg missing, a timeout,
    or a corrupt video all return None so the caller can fall back to a
    generic icon rather than a broken tile.
    """
    destination = thumbnail_path_for(recording)
    if destination.is_file():
        return destination

    try:
        ffmpeg_exe = _resolve_ffmpeg_exe()
    except Exception:
        return None

    import subprocess

    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error", "-nostdin",
        "-i", str(recording),
        "-frames:v", "1",
        "-vf", f"scale={_THUMBNAIL_WIDTH}:-1",
        str(destination),
    ]
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            # Same reasoning as _encode_frames(): console=False build, no
            # window to flash, and a test runner's stdin may not be a real
            # handle subprocess can duplicate.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode == 0 and destination.is_file() and destination.stat().st_size > 0:
        return destination
    return None


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


def overlay_device_coverage(
    screen_geometries: list[QRect], screen_ratios: list[float]
) -> list[QSize]:
    """The device-pixel size a per-screen overlay window ends up covering,
    for each screen, once it is set to that screen's own logical geometry.

    TA-232: a single window spanning every screen can only ever be given
    one devicePixelRatio - Qt assigns a top-level window the DPR of
    whichever screen it considers the window's own (the primary's, for a
    window spanning the whole virtual desktop) - so on any *other* screen
    it under-covers by exactly that screen's ratio: 1536 logical units
    painted 1:1 is 1536 device pixels on a panel that is actually 1920
    wide at 1.25x. Giving each screen its own top-level window, each set to
    that screen's own `.geometry()`, sidesteps the limitation rather than
    working around it: Qt then reports *that* screen's own ratio for *that*
    window, so logical-pixel geometry already implies full device-pixel
    coverage - which is the claim this function exists to make checkable
    against literal numbers (not live QScreen objects), so it can run
    offscreen on single-screen CI.
    """
    return [
        QSize(round(geometry.width() * ratio), round(geometry.height() * ratio))
        for geometry, ratio in zip(screen_geometries, screen_ratios)
    ]


class _OverlayWindow(QWidget):
    """One capture-overlay window, covering exactly one screen.

    Sized to that screen's own `.geometry()` rather than any shared
    virtual-desktop rectangle, so Qt gives it that screen's own DPR (see
    `overlay_device_coverage()`) instead of a borrowed one. Mouse and key
    events are forwarded to the owning `ScreenshotOverlay`, which tracks the
    drag as one shared selection rather than each window running its own -
    a drag that starts on one screen and ends on another must still work,
    and Qt only keeps delivering events to *this* window once the drag has
    grabbed the mouse (see `ScreenshotOverlay.mousePressEvent`).
    """

    def __init__(self, owner: "ScreenshotOverlay", screen_index: int, screen_geometry: QRect) -> None:
        super().__init__()
        self._owner = owner
        self.screen_index = screen_index
        self.screen_geometry = QRect(screen_geometry)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._rubber = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.setGeometry(self.screen_geometry)

    def show_selection(self, global_rect: QRect) -> None:
        """Draw this window's own share of a selection rect given in global
        (virtual-desktop) coordinates - possibly none, if the drag is
        currently entirely on another screen."""
        local = global_rect.translated(-self.screen_geometry.topLeft())
        visible = local.intersected(QRect(QPoint(0, 0), self.screen_geometry.size()))
        if visible.isEmpty():
            self._rubber.hide()
        else:
            self._rubber.setGeometry(visible)
            self._rubber.show()

    def clear_selection(self) -> None:
        self._rubber.hide()

    def mousePressEvent(self, event) -> None:
        self._owner.mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._owner.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._owner.mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        self._owner.keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        # No clipping needed: unlike the old single window spanning the
        # whole virtual desktop, this window's rect *is* one real screen in
        # full, so every pixel of it is real, selectable area. That also
        # removes TA-231's unmapped-region case as a side effect - a gap
        # between mismatched screens is simply not covered by any window at
        # all now, rather than a region this one window had to know to
        # exclude from its own dim (see docs/TA-231.md).
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        painter.end()


class ScreenshotOverlay(QObject):
    """
    Coordinates one semi-transparent `_OverlayWindow` per connected screen.
    The user drags a rectangle, possibly spanning several of them, to
    define the capture region.

    One window per screen rather than one window spanning the virtual
    desktop: see `overlay_device_coverage()` and `_OverlayWindow` for why -
    in short, a single window can only take one screen's DPR, which
    under-covered every other screen by its own ratio (TA-232). The drag
    itself is tracked here, not per-window, because Qt delivers mouse
    events to one widget at a time and a selection spanning two screens
    must still move as one rectangle: whichever window receives
    `mousePressEvent` grabs the mouse for the rest of the drag (see
    `mousePressEvent` below), and every window's own visible share of the
    selection is refreshed from here as it changes.

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
        self._windows: list[_OverlayWindow] = []
        self._origin  = QPoint()
        self._active  = False
        # The window that received mousePressEvent and holds the mouse
        # grab for the rest of the drag - see mousePressEvent().
        self._press_window: _OverlayWindow | None = None

    # ── Public ──────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """Show one overlay window per currently connected screen and ask
        the user to drag a selection.

        Rebuilds the window list from QApplication.screens() every time
        (rather than reusing whatever was there before) since this overlay
        is a single instance shared and reused across captures (see
        launcher.py) and the screen layout can change between them.

        showFullScreen() is fullscreen on *a* screen: it silently discards
        whatever geometry setGeometry() just requested and collapses the
        window onto whichever single screen Qt picks. On real multi-monitor
        hardware that left every screen but one not merely mis-grabbed but
        genuinely uncovered - you could not even click on it. Each window
        here is already frameless and always-on-top, so plain show() after
        setGeometry() covers exactly what it is told to; no fullscreen
        state, and none of its side effects, is needed.

        Each window is set to its own screen's `.geometry()`, not
        `.availableGeometry()`: the available variant excludes taskbars, so
        a taskbar or notification could not be selected at all - wrong for
        an evidence-capture tool.
        """
        self._teardown_windows()
        screens = QApplication.screens()
        self._windows = [
            _OverlayWindow(self, index, screen.geometry())
            for index, screen in enumerate(screens)
        ]
        for window in self._windows:
            window.show()
        for window in self._windows:
            window.raise_()
            if window.geometry() != window.screen_geometry:
                # Should never happen after the fix above - if it does, this
                # window is silently not covering the screen it was asked
                # to, which is exactly this defect. Surfaced rather than
                # assumed away.
                print(
                    f"ScreenshotOverlay: requested geometry {window.screen_geometry} "
                    f"for screen {window.screen_index} but the window reports "
                    f"{window.geometry()} - it is not covering that screen.",
                    file=sys.stderr,
                )
        if self._windows:
            self._windows[0].activateWindow()
            self._windows[0].setFocus()

    def isVisible(self) -> bool:
        return any(window.isVisible() for window in self._windows)

    def hide(self) -> None:
        for window in self._windows:
            window.hide()

    def close(self) -> None:
        self._teardown_windows()

    # ── Private: window bookkeeping ─────────────────────────────────────────

    def _teardown_windows(self) -> None:
        for window in self._windows:
            window.hide()
            window.deleteLater()
        self._windows = []

    def _window_at(self, global_point: QPoint) -> "_OverlayWindow | None":
        for window in self._windows:
            if window.screen_geometry.contains(global_point):
                return window
        # Falls back to the first window rather than None so a press just
        # outside every screen's exact geometry (rounding at an edge) still
        # grabs the mouse and can complete a drag, matching
        # screen_for_rect()'s same fallback-to-index-0 reasoning.
        return self._windows[0] if self._windows else None

    def _update_selection(self, origin: QPoint, current: QPoint) -> None:
        rect = QRect(origin, current).normalized()
        for window in self._windows:
            window.show_selection(rect)

    def _clear_selection(self) -> None:
        for window in self._windows:
            window.clear_selection()

    # ── Mouse events ────────────────────────────────────────────────────────
    #
    # Positions are tracked via event.globalPosition() throughout, not
    # event.position(): the rect this produces is then already in the same
    # space as QScreen.geometry(), so _grab needs no translation step at all
    # and has no dependency on window geometry left to get wrong.

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._active = True
            # grabMouse() on whichever window the drag started on: Qt
            # delivers mouse events per-widget, and a cursor crossing from
            # this screen into another would otherwise stop reaching this
            # window entirely the moment it left. Grabbing keeps every
            # subsequent move/release event coming here regardless of which
            # screen the cursor is physically over, so one shared drag can
            # still span screens now that each screen is its own window.
            self._press_window = self._window_at(self._origin)
            if self._press_window is not None:
                self._press_window.grabMouse()
            self._update_selection(self._origin, self._origin)

    def mouseMoveEvent(self, event) -> None:
        if self._active:
            current = event.globalPosition().toPoint()
            # TA-223: the selection rectangle reportedly jumps/resizes
            # crossing the laptop/external boundary on a mixed-DPI setup
            # (125% laptop, 100% external) - a plausible cause (a Qt
            # logical-pixel rounding discontinuity at the boundary) has no
            # measurement from real hardware to confirm it yet. Logged
            # raw, every move, rather than guessed at - see
            # docs/ta215-225-fix-brief.md. Still fires from here,
            # unconditionally on every move of the (now possibly
            # cross-screen) drag, regardless of which window's grabMouse()
            # is actually receiving the event.
            debug_log.log(
                f"TA-223 drag move: globalPosition=({current.x()}, {current.y()}) "
                f"screens={[s.geometry().getRect() for s in QApplication.screens()]}"
            )
            self._update_selection(self._origin, current)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._active:
            self._active = False
            current = event.globalPosition().toPoint()
            rect = QRect(self._origin, current).normalized()   # already global
            if self._press_window is not None:
                self._press_window.releaseMouse()
            self._press_window = None
            self._clear_selection()
            self.hide()
            if rect.width() > 5 and rect.height() > 5:
                # Small delay so the overlay fully vanishes before grabbing.
                QTimer.singleShot(120, lambda: self._grab(rect))
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._active = False
            if self._press_window is not None:
                self._press_window.releaseMouse()
                self._press_window = None
            self._clear_selection()
            self.hide()
            self.cancelled.emit()

    # ── Private: grab ───────────────────────────────────────────────────────

    def _grab(self, global_rect: QRect) -> None:
        """Grab the selected region from whichever screen(s) it actually falls on.

        `global_rect` already arrives in global desktop coordinates (mouse
        events are read via globalPosition() - see the mouse-event handlers
        above), so no translation from overlay-widget coordinates happens
        here. A selection spanning two screens is composited from every
        intersecting screen rather than clamped to one, so a wide selection
        is never silently truncated to whichever screen holds the most of
        it.
        """
        screens = QApplication.screens()
        geometries = [screen.geometry() for screen in screens]
        pieces = plan_capture(global_rect, geometries)
        # TA-225: capture on the laptop in the secondary-above layout
        # reportedly produces no visible content, despite the drag
        # selection visibly highlighting the right region - unconfirmed
        # whether this is a new edge case or shares TA-223's mechanism.
        # Logs exactly what plan_capture() was asked to divide and what it
        # returned, so a real repro can show which. See
        # docs/ta215-225-fix-brief.md.
        debug_log.log(
            f"TA-225 grab: dragged_rect={global_rect.getRect()} "
            f"screen_geometries={[g.getRect() for g in geometries]} "
            f"plan_capture_result={pieces}"
        )

        if not pieces:
            # The selection touched no known screen - should not happen for a
            # real drag on a real overlay, but emit something rather than
            # nothing.
            pixmap = QApplication.primaryScreen().grabWindow(
                0, global_rect.x(), global_rect.y(), global_rect.width(), global_rect.height()
            )
            # Same normalisation as the composited path below: hand the
            # canvas plain device pixels, not a ratio-tagged pixmap it
            # would then draw at a quarter size.
            pixmap.setDevicePixelRatio(1.0)
            self.capture_ready.emit(pixmap)
            return

        # Sized from the pieces' own bounding box, not global_rect.size():
        # plan_capture() places pieces adjacently along whichever axis the
        # screens are separated on rather than at their true virtual-desktop
        # offset, so a gap between screens is closed rather than reappearing
        # here as unpainted (black) space. max(dest + size) per axis - not
        # e.g. summing widths - is what stays correct regardless of which
        # axis plan_capture chose to close.
        # plan_capture() works in logical (device-independent) pixels,
        # because that is the space a selection is dragged in. A screen
        # with a devicePixelRatio above 1 - every Retina Mac, and every
        # Windows machine at 125% or 150% scaling - holds more real pixels
        # than that, and grabWindow() returns all of them.
        #
        # Compositing into a logical-sized pixmap threw those away: a
        # 400x300 selection on a 2.0-ratio screen grabbed 800x600 real
        # pixels and resampled them down to 400x300, discarding 3/4 of the
        # captured data. For a tool whose output is meant to be evidence
        # that is a correctness problem, not a cosmetic one - 1px borders
        # and antialiased small text are exactly what a tester circles, and
        # exactly what does not survive the downsample.
        #
        # So the result is sized in *device* pixels and left untagged at
        # ratio 1.0, which is what a screenshot has always been elsewhere:
        # macOS `screencapture` writes a 2x file on a Retina display too.
        # Deliberately NOT setDevicePixelRatio() on the result - canvas.py
        # measures annotation coordinates and its own widget size from
        # `_pixmap.width()`, which is device pixels, so a tagged pixmap
        # would render into a quarter of the widget and put every
        # annotation at half its intended position.
        #
        # The highest ratio among the contributing screens wins, so a
        # selection spanning a 2.0 screen and a 1.0 one keeps the sharp
        # half at full detail and scales the other up to meet it, rather
        # than flattening both to the coarser grid.
        # The scaling decision itself lives in screen_geometry, on plain
        # values rather than QScreen objects, so it can be exercised
        # against a mixed-DPI layout with literal ratios - CI has no
        # HiDPI screen, and this is precisely the bug that a 1.0-ratio
        # machine cannot see.
        # TA-246: a 535x418 logical selection on the 125%-laptop screen
        # saved at 535x418 device pixels instead of the expected 669x523 -
        # composite_ratio() trusts whatever devicePixelRatio() reports, so
        # this pins exactly what each screen reported at grab time, per
        # screen, rather than only the composited result downstream.
        debug_log.log(
            f"TA-246 devicePixelRatio at grab: "
            f"{[(i, s.devicePixelRatio()) for i, s in enumerate(screens)]}"
        )
        ratio = composite_ratio(pieces, [screen.devicePixelRatio() for screen in screens])
        size = device_result_size(pieces, ratio)

        # TA-232 HW-1: QPixmap(size) does not reliably carry an alpha
        # channel on every platform/build, so fill(transparent) below
        # silently produced opaque black instead of real transparency -
        # confirmed on hardware as a solid black rectangle exactly where a
        # short piece (e.g. one screen's edge clipping a piece shorter than
        # its neighbour) left the canvas unpainted. QImage in an explicit
        # ARGB format always has a real alpha channel, so build the canvas
        # there and convert once at the end instead of filling a QPixmap
        # directly.
        canvas = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        for piece in pieces:
            screen = screens[piece.screen_index]
            local = piece.screen_local_rect
            grabbed = screen.grabWindow(0, local.x(), local.y(), local.width(), local.height())
            # Source rect is the grabbed pixmap's own device pixels and the
            # destination is the same region scaled by `ratio`, so a piece
            # from a screen already at `ratio` is a 1:1 blit with no
            # resampling at all.
            dest_rect = to_device_rect(piece.dest, local.size(), ratio)
            # TA-239: a spanning capture across mixed-DPI screens showed a
            # ~5px seam at the join in the saved PNG. The coordinate math
            # that produces dest_rect is now covered by an exhaustive
            # synthetic test (test_TA_239_two_piece_join_holds_at_random_non_round_widths
            # in test_screen_geometry.py) and cannot itself explain a seam -
            # the two remaining candidates are (a) grabWindow() not
            # returning exactly local.size()*ratio device pixels on real
            # hardware, and (b) drawPixmap() blending at the destination
            # edge even for nominally-adjacent rects. This logs exactly
            # what each piece actually measures, so a real two-screen drag
            # can show which. See docs/ISSUE-TA-239.md.
            debug_log.log(
                f"TA-239 grab piece: screen_index={piece.screen_index} "
                f"local_rect={local.getRect()} ratio={ratio} "
                f"dest_rect={dest_rect.getRect()} "
                f"expected_grabbed_size=({round(local.width() * ratio)}, {round(local.height() * ratio)}) "
                f"actual_grabbed_size=({grabbed.width()}, {grabbed.height()})"
            )
            painter.drawPixmap(dest_rect, grabbed, grabbed.rect())
        painter.end()
        result = QPixmap.fromImage(canvas)
        result.setDevicePixelRatio(1.0)

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
            # The cheap path: frames[0] is still on disk and already
            # exactly what the gallery needs a preview of, so this costs no
            # extra ffmpeg call and no subprocess - unlike the backfill path
            # for a recording saved before thumbnails existed (see
            # ensure_recording_thumbnail()). A failure here (a corrupt
            # first frame) just leaves no thumbnail; the gallery already
            # falls back to a generic icon for that.
            _write_thumbnail(QImage(str(frames[0])), thumbnail_path_for(output))
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
