"""Floating always-on-top capture launcher for Test Assist (PySide6 edition)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import debug_log
from capture import FrameRecorder, ScreenshotOverlay
from global_hotkeys import MOD_ALT, MOD_SHIFT, GlobalHotkeyManager
from screen_geometry import is_within_dock_band, screen_for_rect
from update_check import UpdateChecker


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

    # Ids this process picks for its own hotkeys - arbitrary, but must be
    # distinct from each other within this process.
    _HOTKEY_PHOTO = 1
    _HOTKEY_FULL_CAPTURE = 2
    _HOTKEY_VIDEO = 3

    def __init__(
        self,
        editor,
        version: str = "0.0.0",
        parent: QWidget | None = None,
        register_global_hotkeys: bool = False,
    ) -> None:
        super().__init__(parent)
        self._editor  = editor
        self._mode    = "photo"
        self._version = version
        # Off by default: real Win32 RegisterHotKey calls are shared,
        # global OS state - every test in this suite that just needs *a*
        # launcher would otherwise fight over the literal same Alt+P/
        # Alt+Shift+P/Alt+V combinations. main.py's real launcher passes
        # True; the handful of tests in test_regressions.py that exercise
        # the hotkey mechanism itself do too, deliberately.
        self._register_global_hotkeys = register_global_hotkeys
        self._hotkeys: GlobalHotkeyManager | None = None
        self._hotkey_registered: dict[str, bool] = {
            "photo": False, "full_capture": False, "video": False,
        }

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

        # Update check - one manager for the process, not one per click.
        self._network_manager = QNetworkAccessManager(self)
        self._update_checker  = UpdateChecker(self._network_manager, self._version, self)

        # Drag-to-move state
        self._drag_pos: QPoint | None = None

        self._build_ui()
        self._set_mode("photo")
        self._position_top_right()
        self._register_hotkeys()

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
        # setAccessibleName(), not just the tooltip (TA-228): this is an
        # icon-only button, indistinguishable from its unlabeled siblings
        # to UI Automation without one - the black-box e2e lane needs a
        # reliable way to find it from outside the process, and a real
        # accessible name is also what a screen reader would announce.
        self._btn_open_editor.setAccessibleName("Open Editor")
        self._btn_open_editor.setStyleSheet(self._style_icon_btn())
        self._btn_open_editor.setEnabled(True)

        self._btn_check_updates = QPushButton()
        self._btn_check_updates.setFixedSize(26, 26)
        self._btn_check_updates.setIcon(self._make_update_icon())
        self._btn_check_updates.setIconSize(QSize(14, 14))
        self._btn_check_updates.setToolTip("Check for Updates")
        self._btn_check_updates.setStyleSheet(self._style_icon_btn())

        self._btn_close = QPushButton()
        self._btn_close.setFixedSize(26, 26)
        self._btn_close.setIcon(self._make_close_icon())
        self._btn_close.setIconSize(QSize(12, 12))
        self._btn_close.setToolTip("Hide to tray")
        self._btn_close.setStyleSheet(self._style_icon_btn())

        header_row.addWidget(self._btn_open_editor)
        header_row.addWidget(self._btn_check_updates)
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
        # The "(Alt+P)" suffix is appended only once _register_hotkeys()
        # knows whether that combination actually registered - see
        # _apply_hotkey_labels(). Advertising a shortcut that did not bind
        # is exactly the bug (TA-211) this exists to not repeat.
        self._btn_photo.setToolTip("Photo mode — capture screenshot")
        self._btn_photo.setStyleSheet(self._style_mode_icon(active=True))

        self._btn_video = QPushButton()
        self._btn_video.setFixedSize(36, 36)
        self._btn_video.setCheckable(True)
        self._btn_video.setToolTip("Video mode — record screen")
        self._btn_video.setStyleSheet(self._style_mode_icon(active=False))

        self._btn_full_capture = QPushButton()
        self._btn_full_capture.setFixedSize(36, 36)
        self._btn_full_capture.setIcon(self._make_screen_icon("#b88d6f"))
        self._btn_full_capture.setIconSize(QSize(18, 18))
        self._btn_full_capture.setToolTip(
            "Capture full primary screen including taskbar/time"
        )
        self._btn_full_capture.setStyleSheet(self._style_mode_icon(active=False))

        self._refresh_mode_icons()

        action_row.addWidget(self._btn_capture, 1)
        action_row.addWidget(self._btn_full_capture)
        action_row.addWidget(self._btn_photo)
        action_row.addWidget(self._btn_video)
        float_layout.addLayout(action_row)

        # Shortcut hint line below action row - text filled in by
        # _apply_hotkey_labels() once registration outcomes are known;
        # starts empty and hidden rather than claiming anything upfront.
        self._hint_lbl = QLabel("")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_lbl.setStyleSheet("color:#7a6050; font-size:10px; background:transparent;")
        self._hint_lbl.hide()
        float_layout.addWidget(self._hint_lbl)

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

        # "Where did it go" gets a one-click answer instead of a folder name
        # in a status line the user has to go and find themselves.
        self._btn_open_folder = QPushButton("Open folder")
        self._btn_open_folder.setFixedHeight(26)
        self._btn_open_folder.setStyleSheet(self._style_outline())
        self._btn_open_folder.hide()
        float_layout.addWidget(self._btn_open_folder)
        self._last_recording_path: Path | None = None

        # Wire signals
        self._btn_photo.clicked.connect(lambda: self._set_mode("photo"))
        self._btn_video.clicked.connect(lambda: self._set_mode("video"))
        self._btn_capture.clicked.connect(self._on_action_click)
        self._btn_full_capture.clicked.connect(self._start_full_capture)
        self._btn_open_editor.clicked.connect(self._editor.bring_forward)
        self._btn_check_updates.clicked.connect(self._check_for_updates)
        self._btn_open_folder.clicked.connect(self._open_last_recording_folder)
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

        self._btn_dock_capture = QPushButton()
        self._btn_dock_capture.setFixedSize(36, 36)
        self._btn_dock_capture.setIcon(self._make_camera_icon("#f0d0a0"))
        self._btn_dock_capture.setIconSize(QSize(20, 20))
        self._btn_dock_capture.setToolTip("Quick Capture")
        self._btn_dock_capture.setStyleSheet(self._style_icon_btn())
        self._btn_dock_capture.clicked.connect(self._on_action_click)
        dock_layout.addWidget(self._btn_dock_capture)

        # Minimal running-time readout, docked-strip width - TA-215: the
        # icon swap alone is easy to miss at 20x20px, and the compact dock
        # is exactly the mode this needs to be visible in, since it's the
        # one place recording state previously had zero feedback at all.
        self._dock_rec_label = QLabel()
        self._dock_rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dock_rec_label.setStyleSheet(
            "color:#c04040; font-size:9px; font-weight:700; background:transparent;"
        )
        self._dock_rec_label.hide()
        dock_layout.addWidget(self._dock_rec_label)

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

    # ── Global hotkeys ───────────────────────────────────────────────────────
    #
    # TA-211: Alt+P, Alt+Shift+P and Alt+V used to be advertised in these
    # same tooltips and this hint label, and in help.html, while being bound
    # to nothing anywhere - not even a QShortcut, which would have been the
    # wrong tool anyway: the entire point of an always-on-top capture widget
    # is capturing whatever else has focus, so a shortcut that only fires
    # while Test Assist itself is focused does not satisfy that claim.

    def _register_hotkeys(self) -> None:
        if not self._register_global_hotkeys:
            self._apply_hotkey_labels()
            return

        self._hotkeys = GlobalHotkeyManager(QApplication.instance(), self)
        self._hotkeys.triggered.connect(self._on_global_hotkey)
        QApplication.instance().aboutToQuit.connect(self._hotkeys.unregister_all)

        attempts = [
            ("photo", self._HOTKEY_PHOTO, MOD_ALT, ord("P"), "Alt+P"),
            ("full_capture", self._HOTKEY_FULL_CAPTURE, MOD_ALT | MOD_SHIFT, ord("P"), "Alt+Shift+P"),
            ("video", self._HOTKEY_VIDEO, MOD_ALT, ord("V"), "Alt+V"),
        ]
        failed_labels = []
        for name, hotkey_id, modifiers, virtual_key, label in attempts:
            ok = self._hotkeys.register(hotkey_id, modifiers, virtual_key)
            self._hotkey_registered[name] = ok
            if not ok:
                failed_labels.append(label)

        self._apply_hotkey_labels()
        if failed_labels:
            self._report_hotkey_registration_failure(failed_labels)

    def _apply_hotkey_labels(self) -> None:
        """Append "(Alt+P)" etc. to a tooltip only for a combination that
        actually registered - never advertise one that did not, whether
        because registration failed or was never attempted at all (most
        test-constructed launchers skip it entirely; see
        register_global_hotkeys)."""
        if self._hotkey_registered["photo"]:
            self._btn_photo.setToolTip(self._btn_photo.toolTip() + " (Alt+P)")
        if self._hotkey_registered["full_capture"]:
            self._btn_full_capture.setToolTip(self._btn_full_capture.toolTip() + " (Alt+Shift+P)")
        if self._hotkey_registered["video"]:
            self._btn_video.setToolTip(self._btn_video.toolTip() + " (Alt+V)")

        hints = []
        if self._hotkey_registered["photo"]:
            hints.append("Alt+P · capture")
        if self._hotkey_registered["video"]:
            hints.append("Alt+V · record")
        self._hint_lbl.setText("   ·   ".join(hints))
        self._hint_lbl.setVisible(bool(hints))

    def _report_hotkey_registration_failure(self, failed_labels: list[str]) -> None:
        """Surfaced in the status line rather than a modal dialog - this
        runs at construction time, before the window is necessarily even
        shown, and a conflict with another application is not urgent
        enough to interrupt every launch with a dialog to dismiss."""
        combos = ", ".join(failed_labels)
        plural = "s" if len(failed_labels) > 1 else ""
        self._status_lbl.setText(
            f"Global shortcut{plural} {combos} could not be registered - "
            f"probably already used by another application. "
            f"Test Assist still works from its own window."
        )
        self._status_lbl.show()

    def _on_global_hotkey(self, hotkey_id: int) -> None:
        # TA-217: a global hotkey is a native OS message, not routed
        # through Qt's own event queue, so it still fires (and the overlay
        # still shows) while one of Test Assist's own dialogs - About, the
        # History gallery, Clear Annotations - is exec()'d application-
        # modal. Qt's modal blocking then keeps the freshly-shown overlay
        # from ever receiving the mouse input needed to drag a selection.
        # Pressing a capture hotkey clearly means "capture now" - closing
        # whatever dialog is in the way matches that intent better than
        # leaving the user with a silently non-interactive overlay.
        self._dismiss_active_modal_dialog()
        if hotkey_id == self._HOTKEY_PHOTO:
            self._set_mode("photo")
            self._start_capture()
        elif hotkey_id == self._HOTKEY_FULL_CAPTURE:
            self._start_full_capture()
        elif hotkey_id == self._HOTKEY_VIDEO:
            self._set_mode("video")
            self._toggle_recording()

    def closeEvent(self, event) -> None:
        if self._hotkeys is not None:
            self._hotkeys.unregister_all()
        super().closeEvent(event)

    @staticmethod
    def _dismiss_active_modal_dialog() -> None:
        """Close whichever of Test Assist's own dialogs currently owns
        Qt's application-modal input block, if any - not hardcoded to
        About specifically, so any future modal dialog is covered the
        same way without needing its own fix (TA-217)."""
        modal = QApplication.activeModalWidget()
        # TA-217: rc4's fix covered the hotkey path but not this one - the
        # Quick Capture *button* silently swallowed its click the same way
        # while a modal was up. Logged here (shared by both paths) rather
        # than only at the hotkey call site, since whichever path called
        # in is equally worth knowing about.
        debug_log.log(f"_dismiss_active_modal_dialog: activeModalWidget={modal!r}")
        if modal is not None:
            modal.close()

    # ── Action dispatch ───────────────────────────────────────────────────────

    def _on_action_click(self) -> None:
        """Single action button dispatches to photo capture or video toggle.

        _dismiss_active_modal_dialog() first (TA-217): the hotkey path
        already closes a blocking modal before dispatching - the button
        click handler never did, so clicking Quick Capture while e.g. the
        About dialog was open was silently swallowed by Qt's
        application-modal block exactly as if the fix had never shipped.
        """
        self._dismiss_active_modal_dialog()
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
        self._refresh_dock_recording_indicator()

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
        # TA-217: reported that pressing Alt+P while About was open closed
        # the dialog but took no snapshot - unconfirmed from the code
        # alone whether this singleShot callback ever fires on that path.
        # Logged rather than guessed at; see docs/ta215-225-fix-brief.md.
        def _activate_overlay() -> None:
            debug_log.log("_start_capture: singleShot fired, calling _overlay.activate()")
            self._overlay.activate()
        QTimer.singleShot(220, _activate_overlay)

    def _start_full_capture(self) -> None:
        """Capture the full primary desktop, including taskbar and clock."""
        self.hide()
        QTimer.singleShot(220, self._grab_full_capture)

    def _grab_full_capture(self) -> None:
        pixmap = self._current_screen().grabWindow(0)
        # Same normalisation capture.py applies to both of its own results:
        # canvas.py measures its own geometry and every annotation's
        # coordinates from _pixmap.width(), which is device pixels, so a
        # ratio-tagged pixmap is painted at its device-independent size
        # inside a device-sized surface - on a 125% screen, 1536x864 of
        # picture inside a 1920x1080 file, black filling the rest.
        pixmap.setDevicePixelRatio(1.0)
        self._on_capture_ready(pixmap)

    def _on_capture_ready(self, pixmap: QPixmap) -> None:
        # record_capture(), not load_pixmap() directly: this is the single
        # choke point both region and full-screen captures pass through,
        # so it is also the one place that must persist to History
        # automatically (TA-216) rather than requiring a completed Save
        # dialog first.
        self.show()
        self._editor.record_capture(pixmap)
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
        self._recorder.start(self._current_screen())
        self._rec_seconds = 0
        self._rec_timer.start(1000)
        self._btn_capture.setText("■  Stop Recording")
        self._btn_capture.setStyleSheet(self._style_danger())
        self._rec_label.setText("⏺  00:00")
        self._rec_label.show()
        self._status_lbl.setText(
            "Recording in progress — click to stop and save."
        )
        self._refresh_dock_recording_indicator()

    def _stop_recording(self) -> None:
        self._rec_timer.stop()
        self._rec_label.hide()
        self._recorder.stop()
        self._btn_capture.setText("⏺  Start Recording")
        self._btn_capture.setStyleSheet(self._style_danger())
        self._status_lbl.setText("Recording stopped. Saving file…")
        self._refresh_dock_recording_indicator()

    def _tick(self) -> None:
        self._rec_seconds += 1
        m, s = divmod(self._rec_seconds, 60)
        self._rec_label.setText(f"⏺  {m:02d}:{s:02d}")
        self._dock_rec_label.setText(f"{m:02d}:{s:02d}")

    def _refresh_dock_recording_indicator(self) -> None:
        """TA-215: the docked strip's single capture icon was set once at
        construction and never updated, unlike the undocked action button
        (whose text/style do change) - so a user working from the compact
        dock got no visual confirmation a recording was running, and the
        one control available to stop it gave no cue that clicking it
        again would. The underlying toggle was already correctly wired
        either way - clicking the docked icon a second time does call
        _stop_recording() - this is a state-feedback gap, not a broken
        stop mechanism.

        Also gives the docked icon a distinct "video mode selected"
        appearance before recording starts (re-tested on rc4: recording
        feedback itself works, but Photo vs Video mode was indistinguishable
        on the docked icon until a recording was actually running) - reuses
        _make_video_icon(), the same glyph the undocked mode buttons already
        use for exactly this distinction, rather than inventing a new one.
        """
        recording = self._rec_timer.isActive()
        if recording:
            icon = self._make_stop_icon()
            icon_size = QSize(16, 16)
        elif self._mode == "video":
            icon = self._make_video_icon("#f0d0a0")
            icon_size = QSize(20, 20)
        else:
            icon = self._make_camera_icon("#f0d0a0")
            icon_size = QSize(20, 20)
        self._btn_dock_capture.setIcon(icon)
        self._btn_dock_capture.setIconSize(icon_size)
        self._btn_dock_capture.setToolTip("Stop Recording" if recording else "Quick Capture")
        self._dock_rec_label.setText("00:00" if recording else "")
        self._dock_rec_label.setVisible(recording)

    def _on_record_finished(self, path: str) -> None:
        if not path:
            self._status_lbl.setText("Nothing was recorded.")
            self._last_recording_path = None
            self._btn_open_folder.hide()
            return

        result = Path(path)
        if result.suffix == ".mp4":
            self._status_lbl.setText(f"Saved video: {path}")
        else:
            n = len(list(result.glob("frame_*.jpg"))) if result.is_dir() else 0
            self._status_lbl.setText(
                f"Saved {n} frames (video encoding unavailable): {path}"
            )
        self._last_recording_path = result
        self._btn_open_folder.show()
        # TA-215: a finished recording is saved straight to disk, but
        # nothing told the editor's History panel to look again - it would
        # only show up the next time History rebuilds on its own (e.g. an
        # editor restart), unlike a still capture which persists live via
        # record_capture(). refresh_history() re-scans the same directory
        # _persist_history_snapshot() already refreshes from.
        self._editor.refresh_history()

    def _open_last_recording_folder(self) -> None:
        """"Where did it go" gets a one-click answer, whatever the path is -
        Documents\\Test Assist by default, or the frame-sequence folder if
        encoding fell back."""
        path = self._last_recording_path
        if path is None:
            return
        folder = path if path.is_dir() else path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # ── Update check ─────────────────────────────────────────────────────────

    def _check_for_updates(self) -> None:
        self._btn_check_updates.setEnabled(False)
        self._update_checker.check(self._on_update_result)

    def _on_update_result(self, result) -> None:
        self._btn_check_updates.setEnabled(True)

        if not result.ok:
            QMessageBox.information(
                self,
                "Check for Updates",
                "Couldn't reach GitHub to check. Try again later.",
            )
            return

        if not result.is_newer:
            QMessageBox.information(
                self,
                "Check for Updates",
                f"You're on {self._version} — this is the latest version.",
            )
            return

        box = QMessageBox(self)
        box.setWindowTitle("Update available")
        box.setText(
            f"Version {result.latest_version} is available — you're on {self._version}.\n\n"
            "To update: close Test Assist, download the zip, and replace the "
            "contents of the folder you run it from."
        )
        open_btn = None
        if result.html_url:
            open_btn = box.addButton("Open Download Page", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if open_btn is not None and box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl(result.html_url))

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
        """Hides to the tray rather than quitting.

        This used to call QApplication.instance().quit(), which took the
        tray icon down with it - Show Launcher became unreachable, and
        nothing short of relaunching the exe brought the app back (INS-02).
        Exit in the tray menu is the only full quit now.
        """
        self.hide()

    def restore(self) -> None:
        """Bring the launcher back from the tray - Show Launcher, and a
        single click on the tray icon, both go through this rather than
        show()/raise_() directly.

        If the screen it was on is no longer there (hidden while docked to
        a monitor since unplugged - DSP-15), reappearing at the stale
        position would leave it genuinely unreachable, not just off the
        visible edge of a screen that still exists. Reposition first in
        that case, docked or floating according to how it was left.
        """
        if QApplication.screenAt(self.frameGeometry().center()) is None:
            # isVisible() also reflects the (hidden) launcher's own
            # visibility; isVisibleTo(self) checks _dock_panel's own state
            # without that, which is what "docked or floating" needs here.
            if self._dock_panel.isVisibleTo(self):
                self._dock_right()
            else:
                self._position_top_right()
        self.show()
        self.raise_()

    # ── Drag-to-move ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    _AUTO_DOCK_THRESHOLD_PX = 12

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            # Docked strip is anchored — never allow dragging while docked
            if self._dock_panel.isVisible():
                super().mouseMoveEvent(event)
                return
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self._maybe_auto_dock(event.globalPosition().toPoint())
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

    # Alt+P/Alt+Shift+P/Alt+V used to be handled here via keyPressEvent -
    # removed (TA-211): a window-focused key handler cannot satisfy "capture
    # whatever else has focus", which is the entire premise of these
    # shortcuts, and once a combination is claimed via RegisterHotKey the
    # OS delivers it as WM_HOTKEY instead of a normal key event to whichever
    # window has focus anyway - this would never have fired for a
    # successfully-registered hotkey even while Test Assist itself was
    # focused. See _on_global_hotkey().

    # ── Custom background paint ────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(200, 120, 60, 80), 1))
        p.setBrush(QBrush(QColor(18, 12, 8, 242)))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()

    def _maybe_auto_dock(self, pointer: QPoint) -> None:
        """Dock only within a narrow band of the current screen's own right
        edge - see is_within_dock_band() for why a half-plane test (the old
        "x() + width() >= geom.right()") auto-docked the instant a drag
        arrived from a screen to the right (DSP-12/13/14)."""
        geom = self._current_screen().availableGeometry()
        if is_within_dock_band(self.x() + self.width(), pointer, geom, self._AUTO_DOCK_THRESHOLD_PX):
            self._dock_right()

    # ── Positioning ──────────────────────────────────────────────────────────

    def _current_screen(self):
        """The screen this widget is actually on, not always the primary.

        screenAt() returns None when the widget's centre falls in a
        virtual-desktop gap belonging to no screen - mismatched monitor
        heights leave exactly this kind of band, and a drag reaches it, not
        just a hypothetical edge case (DSP-13/14). Falling back to the
        primary there silently snapped the widget back to the wrong screen.
        Falling back instead to whichever screen the widget's frame mostly
        overlaps - screen_for_rect(), already covered for the capture
        overlay - answers correctly even when the anchor point itself is in
        the gap.
        """
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is not None:
            return screen
        screens = QApplication.screens()
        if not screens:
            return QApplication.primaryScreen()
        geometries = [candidate.geometry() for candidate in screens]
        return screens[screen_for_rect(self.frameGeometry(), geometries)]

    def _position_top_right(self, screen=None) -> None:
        if screen is None:
            screen = self._current_screen()
        geom = screen.availableGeometry()
        self.adjustSize()
        self.move(geom.right() - self.width() - 20, geom.top() + 20)

    def _dock_right(self) -> None:
        # Resolved once, before anything below changes the frame that
        # _current_screen() would otherwise re-read mid-call.
        screen = self._current_screen()
        self._float_panel.hide()
        self._dock_panel.show()
        self.setFixedWidth(50)
        self.adjustSize()
        geom = screen.availableGeometry()
        y = geom.top() + max(20, (geom.height() - self.height()) // 2)
        self.move(geom.right() - self.width(), y)

    def _undock(self) -> None:
        # Resolved while still correctly docked, before widening the frame
        # back to the floating width changes what _current_screen() would
        # see - so undocking cannot disagree with the screen it docked on.
        screen = self._current_screen()
        self._dock_panel.hide()
        self._float_panel.show()
        self.setFixedWidth(280)
        self._position_top_right(screen)

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
    def _make_update_icon(color: str = "#f8d3ad") -> QIcon:
        """A circular refresh arrow - the standard visual convention for
        "check for updates". The previous icon (a plain arrow into a
        tray) was a generic download shape with no such convention behind
        it, indistinguishable from its neighbours at 14x14 (TA-218)."""
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(2, 2, 10, 10), 20 * 16, 280 * 16)
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPoint(12, 1), QPoint(14, 6), QPoint(9, 5)]))
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
    def _make_stop_icon(color: str = "#ff5050") -> QIcon:
        """Filled red square - the docked capture icon's recording state
        (TA-215), mirroring the "■" the undocked action button already
        shows in its text while recording."""
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(3, 3, 12, 12, 2, 2)
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
