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
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import debug_log
import paths
from capture import FrameRecorder, ScreenshotOverlay
from global_hotkeys import MOD_ALT, MOD_SHIFT, GlobalHotkeyManager
from screen_geometry import is_within_dock_band, screen_for_rect
from update_check import UpdateChecker
import theme
from theme import ui_font


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
        self._position_top_right()
        self._register_hotkeys()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Floating panel ────────────────────────────────────────────────────
        self._float_panel = QWidget(self)
        # Transparent so the rounded panel painted in paintEvent shows
        # through, border included. Without this the global stylesheet's
        # QWidget background paints an opaque rectangle over it - which was
        # invisible while the two colours matched, and would have hidden the
        # red recording border entirely.
        self._float_panel.setStyleSheet("background: transparent;")
        float_layout = QVBoxLayout(self._float_panel)
        float_layout.setContentsMargins(14, 10, 14, 12)
        float_layout.setSpacing(9)

        # Header: identity on the left, window controls on the right.
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        badge = QLabel("TA")
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background:{theme.ACCENT}; color:#ffffff; border-radius:6px;"
            f" font-size:10px; font-weight:800;"
        )
        header_row.addWidget(badge)

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        title_lbl = QLabel("Test Assist")
        title_lbl.setStyleSheet(
            f"color:{theme.TEXT}; font-size:13px; font-weight:700; background:transparent;"
        )
        version_lbl = QLabel(f"v{self._version}" if self._version else "")
        version_lbl.setStyleSheet(
            f"color:{theme.MUTED}; font-size:9px; background:transparent;"
        )
        name_col.addWidget(title_lbl)
        name_col.addWidget(version_lbl)
        header_row.addLayout(name_col)
        header_row.addStretch(1)

        self._btn_open_editor = QPushButton()
        self._btn_open_editor.setFixedSize(22, 22)
        self._btn_open_editor.setIcon(theme.icon_pixmap("pen", 13, theme.MUTED))
        self._btn_open_editor.setToolTip("Open Editor")
        # setAccessibleName(), not just the tooltip (TA-228): this is an
        # icon-only button, indistinguishable from its unlabeled siblings
        # to UI Automation without one - the black-box e2e lane needs a
        # reliable way to find it from outside the process, and a real
        # accessible name is also what a screen reader would announce.
        self._btn_open_editor.setAccessibleName("Open Editor")
        self._btn_open_editor.setStyleSheet(self._style_ghost())

        self._btn_check_updates = QPushButton()
        self._btn_check_updates.setFixedSize(22, 22)
        self._btn_check_updates.setIcon(theme.icon_pixmap("updates", 13, theme.MUTED))
        self._btn_check_updates.setToolTip("Check for Updates")
        self._btn_check_updates.setAccessibleName("Check for Updates")
        self._btn_check_updates.setStyleSheet(self._style_ghost())

        # One reduced form, not two: this shrinks to the docked strip, which
        # is the compact mode. Named _btn_dock_right still because that is
        # what it does and what the suite already calls it.
        self._btn_dock_right = QPushButton()
        self._btn_dock_right.setFixedSize(22, 22)
        self._btn_dock_right.setIcon(theme.icon_pixmap("minimise", 13, theme.MUTED))
        self._btn_dock_right.setToolTip("Shrink to the compact strip")
        self._btn_dock_right.setAccessibleName("Shrink to strip")
        self._btn_dock_right.setStyleSheet(self._style_ghost())

        self._btn_close = QPushButton()
        self._btn_close.setFixedSize(22, 22)
        self._btn_close.setIcon(theme.icon_pixmap("close", 13, theme.MUTED))
        self._btn_close.setToolTip("Hide to the tray - click the tray icon to bring it back")
        self._btn_close.setAccessibleName("Hide to tray")
        self._btn_close.setStyleSheet(self._style_ghost())

        for button in (
            self._btn_open_editor, self._btn_check_updates,
            self._btn_dock_right, self._btn_close,
        ):
            header_row.addWidget(button)
        float_layout.addLayout(header_row)
        float_layout.addWidget(self._rule())

        # ── Capture: three direct actions, no mode to set first ───────────
        #
        # There was a Photo/Video toggle beside the capture button, so what
        # "Quick Capture" did depended on an unlabeled control next to it.
        # Each action is now its own button: click the thing you want.
        self._btn_capture = QPushButton("  Capture Region")
        self._btn_capture.setIcon(theme.icon_pixmap("region", 16, "#ffffff"))
        self._btn_capture.setFixedHeight(38)
        self._btn_capture.setStyleSheet(self._style_primary())
        self._btn_capture.setAccessibleName("Capture Region")
        float_layout.addWidget(self._btn_capture)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._btn_full_capture = QPushButton("  Full Screen")
        self._btn_full_capture.setIcon(theme.icon_pixmap("fullscreen", 14, theme.MUTED))
        self._btn_full_capture.setFixedHeight(32)
        self._btn_full_capture.setToolTip("Capture the whole screen, including the taskbar and clock")
        self._btn_full_capture.setAccessibleName("Full Screen")
        self._btn_full_capture.setStyleSheet(self._style_outline())
        action_row.addWidget(self._btn_full_capture, 1)

        # Round and red, the convention every recorder uses, and the one
        # control here that is not a still. It becomes stop in place rather
        # than moving or handing off to something elsewhere, so the thing
        # you pressed to start is the thing you press to finish.
        self._btn_record = QPushButton()
        self._btn_record.setFixedSize(32, 32)
        self._btn_record.setStyleSheet(self._style_record())
        self._btn_record.setAccessibleName("Record")
        action_row.addWidget(self._btn_record)
        float_layout.addLayout(action_row)

        # Recording status: a dot, the word, and a running clock.
        self._rec_row = QWidget()
        rec_row = QHBoxLayout(self._rec_row)
        rec_row.setContentsMargins(0, 0, 0, 0)
        rec_row.setSpacing(6)
        self._rec_dot = QLabel("\u25cf")
        self._rec_dot.setStyleSheet(
            f"color:{theme.DANGER}; font-size:15px; background:transparent;"
        )
        rec_word = QLabel("Recording")
        rec_word.setStyleSheet(
            f"color:{theme.DANGER}; font-size:12px; font-weight:700; background:transparent;"
        )
        self._rec_label = QLabel("00:00")
        self._rec_label.setStyleSheet(
            f"color:{theme.TEXT}; font-size:15px; font-weight:700; background:transparent;"
        )
        rec_row.addWidget(self._rec_dot)
        rec_row.addWidget(rec_word)
        rec_row.addStretch(1)
        rec_row.addWidget(self._rec_label)
        self._rec_row.hide()
        float_layout.addWidget(self._rec_row)

        self._btn_stop = QPushButton("  Stop Recording")
        self._btn_stop.setIcon(theme.icon_pixmap("stop", 18, "#ffffff"))
        self._btn_stop.setFixedHeight(44)
        self._btn_stop.setStyleSheet(self._style_danger())
        self._btn_stop.setAccessibleName("Stop Recording")
        self._btn_stop.hide()
        float_layout.addWidget(self._btn_stop)

        # ── Recent captures ───────────────────────────────────────────────
        self._recent_hdr = QLabel("RECENT")
        self._recent_hdr.setStyleSheet(
            f"color:{theme.MUTED}; font-size:9px; font-weight:700;"
            f" letter-spacing:1.2px; background:transparent;"
        )
        float_layout.addWidget(self._recent_hdr)

        recent_row = QHBoxLayout()
        recent_row.setSpacing(6)
        self._recent_slots: list[QLabel] = []
        for _ in range(3):
            slot = QLabel()
            slot.setFixedSize(76, 50)
            slot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.setScaledContents(False)
            slot.setStyleSheet(
                f"background:{theme.BG_700}; border:1px solid {theme.LINE};"
                f" border-radius:6px;"
            )
            self._recent_slots.append(slot)
            recent_row.addWidget(slot)
        float_layout.addLayout(recent_row)

        self._btn_open_editor_wide = QPushButton("  Open Editor")
        self._btn_open_editor_wide.setIcon(theme.icon_pixmap("pen", 14, theme.MUTED))
        self._btn_open_editor_wide.setFixedHeight(30)
        self._btn_open_editor_wide.setStyleSheet(self._style_outline())
        self._btn_open_editor_wide.setAccessibleName("Open Editor")
        float_layout.addWidget(self._btn_open_editor_wide)

        float_layout.addWidget(self._rule())

        # Shortcut hint line - text filled in by _apply_hotkey_labels() once
        # registration outcomes are known; starts empty and hidden rather
        # than claiming anything upfront.
        self._hint_lbl = QLabel("")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_lbl.setStyleSheet(
            f"color:{theme.MUTED}; font-size:9px; background:transparent;"
        )
        self._hint_lbl.hide()
        float_layout.addWidget(self._hint_lbl)

        # How to get it back, and how to quit. Both were undiscoverable:
        # the close button hides to the tray with no on-screen sign that is
        # what happened, and quitting is a context menu nothing announced.
        self._exit_hint = QLabel("Hides to the tray  \u00b7  right-click  \u2192  Quit")
        self._exit_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._exit_hint.setStyleSheet(
            f"color:{theme.MUTED}; font-size:9px; background:transparent;"
        )
        float_layout.addWidget(self._exit_hint)

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
        self._btn_capture.clicked.connect(self._on_capture_click)
        self._btn_full_capture.clicked.connect(self._start_full_capture)
        self._btn_record.clicked.connect(self._toggle_recording)
        self._btn_stop.clicked.connect(self._toggle_recording)
        self._btn_open_editor.clicked.connect(self._editor.bring_forward)
        self._btn_open_editor_wide.clicked.connect(self._editor.bring_forward)
        self._btn_check_updates.clicked.connect(self._check_for_updates)
        self._btn_open_folder.clicked.connect(self._open_last_recording_folder)
        self._btn_dock_right.clicked.connect(self._dock_right)
        self._btn_close.clicked.connect(self._close_launcher)

        outer.addWidget(self._float_panel)

        # ── Docked strip: the one reduced form ────────────────────────────
        self._dock_panel = QWidget(self)
        self._dock_panel.setStyleSheet("background: transparent;")
        dock_layout = QVBoxLayout(self._dock_panel)
        dock_layout.setContentsMargins(8, 10, 8, 10)
        dock_layout.setSpacing(7)
        dock_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        dock_badge = QLabel("TA")
        dock_badge.setFixedSize(28, 28)
        dock_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dock_badge.setStyleSheet(
            f"background:{theme.ACCENT}; color:#ffffff; border-radius:7px;"
            f" font-size:10px; font-weight:800;"
        )
        dock_layout.addWidget(dock_badge, 0, Qt.AlignmentFlag.AlignHCenter)
        dock_layout.addWidget(self._rule())

        # Same three actions as the panel, same order, so the strip is the
        # panel with the labels removed rather than a different tool.
        self._btn_dock_capture = QPushButton()
        self._btn_dock_capture.setFixedSize(40, 36)
        self._btn_dock_capture.setIcon(theme.icon_pixmap("region", 18, theme.TEXT))
        self._btn_dock_capture.setToolTip("Capture region")
        self._btn_dock_capture.setAccessibleName("Capture Region")
        self._btn_dock_capture.setStyleSheet(self._style_icon_btn())
        dock_layout.addWidget(self._btn_dock_capture, 0, Qt.AlignmentFlag.AlignHCenter)

        self._btn_dock_full = QPushButton()
        self._btn_dock_full.setFixedSize(40, 36)
        self._btn_dock_full.setIcon(theme.icon_pixmap("fullscreen", 18, theme.TEXT))
        self._btn_dock_full.setToolTip("Capture full screen")
        self._btn_dock_full.setAccessibleName("Full Screen")
        self._btn_dock_full.setStyleSheet(self._style_icon_btn())
        dock_layout.addWidget(self._btn_dock_full, 0, Qt.AlignmentFlag.AlignHCenter)

        self._btn_dock_record = QPushButton()
        self._btn_dock_record.setFixedSize(40, 40)
        self._btn_dock_record.setStyleSheet(self._style_record(radius=20))
        self._btn_dock_record.setAccessibleName("Record")
        dock_layout.addWidget(self._btn_dock_record, 0, Qt.AlignmentFlag.AlignHCenter)

        # TA-215: the strip is the mode a tester actually leaves on screen
        # for a long session, so it is the one that most needs to say a
        # recording is running - and to be one click from stopping it.
        self._dock_rec_label = QLabel()
        self._dock_rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dock_rec_label.setFixedHeight(13)
        self._dock_rec_label.setStyleSheet(
            f"color:{theme.DANGER}; font-size:10px; font-weight:700; background:transparent;"
        )
        self._dock_rec_label.hide()
        dock_layout.addWidget(self._dock_rec_label)

        dock_layout.addWidget(self._rule())

        btn_dock_editor = QPushButton()
        btn_dock_editor.setFixedSize(40, 30)
        btn_dock_editor.setIcon(theme.icon_pixmap("pen", 15, theme.MUTED))
        btn_dock_editor.setToolTip("Open Editor")
        btn_dock_editor.setAccessibleName("Open Editor")
        btn_dock_editor.setStyleSheet(self._style_ghost())
        btn_dock_editor.clicked.connect(self._editor.bring_forward)
        dock_layout.addWidget(btn_dock_editor, 0, Qt.AlignmentFlag.AlignHCenter)

        self._btn_undock = QPushButton()
        self._btn_undock.setFixedSize(40, 30)
        self._btn_undock.setIcon(theme.icon_pixmap("expand", 15, theme.MUTED))
        self._btn_undock.setToolTip("Expand to the full panel")
        self._btn_undock.setAccessibleName("Expand")
        self._btn_undock.setStyleSheet(self._style_ghost())
        self._btn_undock.clicked.connect(self._undock)
        dock_layout.addWidget(self._btn_undock, 0, Qt.AlignmentFlag.AlignHCenter)

        self._btn_dock_capture.clicked.connect(self._on_capture_click)
        self._btn_dock_full.clicked.connect(self._start_full_capture)
        self._btn_dock_record.clicked.connect(self._toggle_recording)

        self._dock_panel.hide()
        outer.addWidget(self._dock_panel)

        self._refresh_recording_ui()
        self.refresh_recent()

    def _rule(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{theme.LINE}; border:none;")
        return line

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
            self._btn_capture.setToolTip("Capture a region (Alt+P)")
        if self._hotkey_registered["full_capture"]:
            self._btn_full_capture.setToolTip(
                self._btn_full_capture.toolTip() + " (Alt+Shift+P)"
            )
        if self._hotkey_registered["video"]:
            self._btn_record.setToolTip("Start recording (Alt+V)")

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
            self._start_capture()
        elif hotkey_id == self._HOTKEY_FULL_CAPTURE:
            self._start_full_capture()
        elif hotkey_id == self._HOTKEY_VIDEO:
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

    def _on_capture_click(self) -> None:
        """Region capture, from either panel.

        _dismiss_active_modal_dialog() first (TA-217): the hotkey path
        already closes a blocking modal before dispatching - the button
        click handler never did, so clicking capture while e.g. the About
        dialog was open was silently swallowed by Qt's application-modal
        block exactly as if the fix had never shipped.
        """
        self._dismiss_active_modal_dialog()
        self._start_capture()

    # ── Recording state ───────────────────────────────────────────────────────

    def is_recording(self) -> bool:
        return self._rec_timer.isActive()

    def _refresh_recording_ui(self) -> None:
        """Put both panels into the recording state, or out of it.

        Stopping used to be the same button that started, relabelled - and
        in the strip, an icon swap on a 20px control with nothing else to
        signal it. A tester who has been recording for two minutes should
        not have to work out which control stops it; that is the specific
        thing QuickTime gets wrong by hiding stop in the menu bar, and the
        thing this is meant to beat.

        So while recording: the panel's capture actions give way to one
        full-width Stop, a dot and a running clock appear, the strip's
        round record button becomes a square stop in place - same position,
        same colour, so the control never moves - and both panels take a
        red border, which is what makes the state readable peripherally
        rather than only on inspection.
        """
        recording = self._rec_timer.isActive()

        for widget in (self._btn_capture, self._btn_full_capture, self._btn_record):
            widget.setVisible(not recording)
        self._rec_row.setVisible(recording)
        self._btn_stop.setVisible(recording)

        self._btn_record.setIcon(
            theme.icon_pixmap("stop" if recording else "record", 16, "#ffffff")
        )
        self._btn_record.setToolTip("Stop recording" if recording else "Start recording")

        self._btn_dock_record.setIcon(
            theme.icon_pixmap("stop" if recording else "record", 18, "#ffffff")
        )
        self._btn_dock_record.setToolTip("Stop recording" if recording else "Start recording")
        self._btn_dock_record.setAccessibleName("Stop Recording" if recording else "Record")
        self._dock_rec_label.setVisible(recording)
        if not recording:
            self._dock_rec_label.setText("")

        # Stills are meaningless mid-recording and would only compete for
        # the click that stops it.
        self._btn_dock_capture.setVisible(not recording)
        self._btn_dock_full.setVisible(not recording)

        self.update()

    def refresh_recent(self) -> None:
        """Fill the three RECENT slots from the capture history.

        Read from paths.history_dir() rather than asked of the editor: the
        panel should say whether a capture worked without the editor having
        been opened at all, which is the confirmation it previously gave
        nowhere. Never raises - a launcher that will not build because a
        thumbnail would not load is a worse failure than an empty slot.
        """
        slots = getattr(self, "_recent_slots", [])
        if not slots:
            return
        try:
            files = sorted(
                (f for f in paths.history_dir().iterdir()
                 if f.suffix.lower() in {".png", ".jpg", ".jpeg"}),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )[:len(slots)]
        except Exception:
            files = []

        for index, slot in enumerate(slots):
            newest = index == 0 and bool(files)
            slot.setStyleSheet(
                f"background:{theme.BG_700}; border:1px solid "
                f"{theme.ACCENT if newest else theme.LINE}; border-radius:6px;"
            )
            if index < len(files):
                pixmap = QPixmap(str(files[index]))
                if not pixmap.isNull():
                    slot.setPixmap(pixmap.scaled(
                        slot.width() - 2, slot.height() - 2,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                    slot.setToolTip(files[index].name)
                    continue
            slot.setPixmap(QPixmap())
            slot.setToolTip("")

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
        self._rec_label.setText("00:00")
        self._dock_rec_label.setText("00:00")
        self._status_lbl.setText(
            "Recording in progress — click Stop to finish and save."
        )
        self._refresh_recording_ui()

    def _stop_recording(self) -> None:
        self._rec_timer.stop()
        self._recorder.stop()
        self._status_lbl.setText("Recording stopped. Saving file…")
        self._refresh_recording_ui()

    def _tick(self) -> None:
        self._rec_seconds += 1
        m, s = divmod(self._rec_seconds, 60)
        self._rec_label.setText(f"{m:02d}:{s:02d}")
        self._dock_rec_label.setText(f"{m:02d}:{s:02d}")

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
        # A red border while recording. The state is then readable from the
        # shape of the thing at the edge of vision, rather than only by
        # reading a label - which is the difference between noticing a
        # recording is still running and not.
        if self._rec_timer.isActive():
            border = QColor(theme.DANGER)
            border.setAlpha(220)
            p.setPen(QPen(border, 2))
        else:
            p.setPen(QPen(QColor(*theme.PANEL_BORDER), 1))
        p.setBrush(QBrush(QColor(*theme.PANEL_BG)))
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
        # 40px controls inside 8px margins need 56, not 50: at 50 the strip
        # was 6px narrower than its own contents, so every button in it was
        # pushed off-centre rather than centred with AlignHCenter.
        self.setFixedWidth(56)
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
        return f"""
            QPushButton {{
                background-color: {theme.ACCENT};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover   {{ background-color: {theme.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {theme.ACCENT_PRESSED}; }}
        """

    @staticmethod
    def _style_danger() -> str:
        return f"""
            QPushButton {{
                background-color: {theme.DANGER};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover   {{ background-color: {theme.DANGER_HOVER}; }}
            QPushButton:pressed {{ background-color: {theme.DANGER_PRESSED}; }}
        """

    @staticmethod
    def _style_outline() -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.MUTED};
                border: 1px solid rgba(124,131,253,0.30);
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover    {{ border-color: {theme.ACCENT}; color: {theme.ACCENT}; }}
            QPushButton:disabled {{ color: #4a4f63; border-color: rgba(124,131,253,0.10); }}
        """

    @staticmethod
    def _style_ghost() -> str:
        """A header control: no chrome until hovered. These sit beside the
        app's own name, so a visible border on each would make the header
        busier than the actions below it."""
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {theme.BG_700}; }}
        """

    @staticmethod
    def _style_record(radius: int = 16) -> str:
        """The record control: round and red in both panels, so it reads as
        a different class of thing from the stills beside it - and so the
        square it becomes while recording is recognisably the same button."""
        return f"""
            QPushButton {{
                background-color: {theme.DANGER};
                border: none;
                border-radius: {radius}px;
            }}
            QPushButton:hover {{ background-color: {theme.DANGER_HOVER}; }}
            QPushButton:pressed {{ background-color: {theme.DANGER_PRESSED}; }}
        """

    @staticmethod
    def _style_icon_btn() -> str:
        """Small icon button (dock / close), muted against the panel."""
        return f"""
            QPushButton {{
                background-color: rgba(124,131,253,0.08);
                color: {theme.MUTED};
                border: 1px solid rgba(124,131,253,0.25);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(124,131,253,0.18);
                color: {theme.ACCENT};
                border-color: rgba(124,131,253,0.50);
            }}
            QPushButton:pressed {{ background-color: rgba(124,131,253,0.30); }}
        """
