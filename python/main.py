"""Entry point for Test Assist (PySide6 desktop app)."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

__version__ = "1.3.0"

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import paths
from editor import EditorWindow
from launcher import FloatingLauncher
from single_instance import AcquireOutcome, SingleInstanceManager
from theme import EDITOR_STYLE


_FLAGS = ("--version", "--selftest")


def _extract_open_path(argv: list[str]) -> str | None:
    """The file path Windows "Open with" passes on the command line, if
    any - the first argument after the program name that isn't one of the
    flags handled separately below."""
    for arg in argv[1:]:
        if arg in _FLAGS:
            continue
        return arg
    return None


def _asset_path(name: str) -> Path:
    """Locate a bundled asset, whether running from source or from a build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name


def _make_tray_icon() -> QIcon:
    # Prefer the real icon file, which is what Windows shows on the taskbar;
    # fall back to the drawn one when running from a source checkout without it.
    icon_file = _asset_path("icon.ico")
    if icon_file.exists():
        return QIcon(str(icon_file))

    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#d7873d"), 2))
    p.setBrush(QColor("#d7873d"))
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setPen(QColor("#1f1208"))
    p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "TA")
    p.end()
    return QIcon(pix)


def _setup_tray(app: QApplication, launcher: FloatingLauncher, editor: EditorWindow) -> QSystemTrayIcon:
    # The editor's own "Show Launcher" toolbar button goes through the same
    # restore() as the tray menu and tray-icon click below - editor.py takes
    # a plain callable rather than importing FloatingLauncher, which would
    # create an import cycle (launcher.py already takes an EditorWindow
    # instance without importing editor.py for it).
    editor.set_show_launcher_callback(launcher.restore)
    # Same reasoning (TA-218): reuses the launcher's own _check_for_updates()
    # and its one UpdateChecker/QNetworkAccessManager rather than the editor
    # building a second network stack.
    editor.set_check_updates_callback(launcher._check_for_updates)

    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("Test Assist")

    menu = QMenu()
    show_launcher = QAction("Show Launcher", menu)
    open_editor = QAction("Open Editor", menu)
    quit_app = QAction("Exit", menu)

    # restore(), not show()/raise_() directly: it repositions first if the
    # launcher would otherwise reappear on a screen that is no longer there
    # (hidden while docked, then that monitor unplugged - DSP-15).
    show_launcher.triggered.connect(launcher.restore)
    open_editor.triggered.connect(editor.bring_forward)
    quit_app.triggered.connect(app.quit)

    menu.addAction(show_launcher)
    menu.addAction(open_editor)
    menu.addSeparator()
    menu.addAction(quit_app)

    tray.setContextMenu(menu)

    def _on_activate(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            launcher.restore()

    tray.activated.connect(_on_activate)
    tray.show()
    return tray


def _run_selftest() -> None:
    """Headless proof of two things a frozen build can silently get wrong:

    1. Can it actually find and run its bundled ffmpeg - not just that
       collect_data_files() dropped the exe somewhere under dist/.
       capture._resolve_ffmpeg_exe() locates the binary via
       imageio_ffmpeg.__file__, which only resolves to a real path inside the
       frozen bundle if PyInstaller rewrote it correctly; a file existing on
       disk does not by itself prove the frozen import resolves the same way.

    2. Can it do TLS. Qt does not link TLS in - HTTPS depends on a separate
       plugin (qschannelbackend.dll on Windows) that PyInstaller must bundle
       alongside the modules its hooks already know about. If that plugin is
       missing, QSslSocket.supportsSsl() is False and every https:// request
       (the update check) fails, indistinguishable from being offline.

    Same file-probe pattern as --version: a windowed build has no usable
    stdout, so the result is written to TESTASSIST_VERSION_FILE as four lines
    - the resolved ffmpeg path, the first line of `ffmpeg -version`, whether
    SSL is supported, and the active SSL backend name - and each value is
    left empty/False on its own failure rather than raising.
    """
    import subprocess

    import capture

    path = ""
    version_line = ""
    try:
        path = capture._resolve_ffmpeg_exe()
    except Exception:
        path = ""

    if path:
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                stdin=subprocess.DEVNULL,
            )
            if result.stdout:
                version_line = result.stdout.decode(errors="replace").splitlines()[0]
        except Exception:
            version_line = ""

    ssl_supported = False
    ssl_backend = ""
    try:
        from PySide6.QtNetwork import QSslSocket

        ssl_supported = bool(QSslSocket.supportsSsl())
        ssl_backend = QSslSocket.activeBackend() or ""
    except Exception:
        ssl_supported = False
        ssl_backend = ""

    # A trailing newline is required, not cosmetic: when ssl_backend is empty
    # (SSL unsupported), a line-splitter that treats a final "\n" as a plain
    # terminator - which both Python's splitlines() and PowerShell's
    # Get-Content do - silently drops that last, empty line instead of
    # reporting it, leaving only 3 fields where 4 were written.
    text = "\n".join([path, version_line, str(ssl_supported), ssl_backend]) + "\n"
    target = os.environ.get("TESTASSIST_VERSION_FILE")
    if target:
        Path(target).write_text(text, encoding="utf-8")
    try:
        print(text)
    except Exception:
        pass


def main() -> None:
    if "--version" in sys.argv:
        # Headless: lets a build pipeline prove the executable actually runs
        # without needing a display.
        #
        # A windowed build has no usable stdout on Windows - PyInstaller sets
        # sys.stdout to None in --noconsole mode - so a pipeline cannot capture
        # what is printed here. Writing to the path in TESTASSIST_VERSION_FILE
        # gives it something it can actually read back.
        text = f"Test Assist {__version__}"
        target = os.environ.get("TESTASSIST_VERSION_FILE")
        if target:
            Path(target).write_text(text, encoding="utf-8")
        try:
            print(text)
        except Exception:
            pass
        return

    if "--selftest" in sys.argv:
        _run_selftest()
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TestAssist.App")
    except Exception:
        pass

    app = QApplication(sys.argv)
    # No setOrganizationName(): QStandardPaths' AppLocalDataLocation folds it
    # in ahead of the application name, which would give
    # AppData\Local\TestAssist\Test Assist\ for no reason - nothing else in
    # the app reads organizationName (single_instance.py uses its own
    # hardcoded server name), so there is nothing to preserve by keeping it.
    app.setApplicationName("Test Assist")
    app.setStyle("Fusion")
    app.setStyleSheet(EDITOR_STYLE)
    app.setWindowIcon(_make_tray_icon())

    # Keep the process alive even when all windows are hidden
    # (launcher is the "last" visible window and must not trigger quit).
    app.setQuitOnLastWindowClosed(False)

    paths.migrate_legacy_data()

    open_path = _extract_open_path(sys.argv)

    single = SingleInstanceManager()
    outcome = single.acquire(open_path)
    if outcome is AcquireOutcome.HANDED_OFF:
        # A running instance took the request (opened the file, or came to
        # the front) - nothing to start here.
        return
    if outcome is AcquireOutcome.FAILED:
        sys.exit(1)

    single.quit_requested.connect(app.quit)

    editor   = EditorWindow(version=__version__)
    launcher = FloatingLauncher(editor, version=__version__, register_global_hotkeys=True)
    tray = _setup_tray(app, launcher, editor)
    app.setProperty("trayIcon", tray)

    # A second launch's handoff lands here too, once this instance is the
    # one running - same destinations either way.
    single.show_requested.connect(launcher.restore)
    single.open_requested.connect(editor.load_image_path)

    if not open_path or not editor.load_image_path(open_path):
        launcher.show()

    exit_code = app.exec()
    single.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
