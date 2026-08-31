"""Entry point for Test Assist (PySide6 desktop app)."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

__version__ = "1.2.0"

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from editor import EditorWindow
from launcher import FloatingLauncher
from single_instance import SingleInstanceManager
from theme import EDITOR_STYLE


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
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("Test Assist")

    menu = QMenu()
    show_launcher = QAction("Show Launcher", menu)
    open_editor = QAction("Open Editor", menu)
    quit_app = QAction("Exit", menu)

    show_launcher.triggered.connect(launcher.show)
    show_launcher.triggered.connect(launcher.raise_)
    open_editor.triggered.connect(editor.bring_forward)
    quit_app.triggered.connect(app.quit)

    menu.addAction(show_launcher)
    menu.addAction(open_editor)
    menu.addSeparator()
    menu.addAction(quit_app)

    tray.setContextMenu(menu)

    def _on_activate(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            launcher.show()
            launcher.raise_()

    tray.activated.connect(_on_activate)
    tray.show()
    return tray


def _run_selftest() -> None:
    """Headless proof that the packaged build can actually find and run its
    bundled ffmpeg - not just that collect_data_files() dropped the exe
    somewhere under dist/. capture._resolve_ffmpeg_exe() locates the binary
    via imageio_ffmpeg.__file__, which only resolves to a real path inside
    the frozen bundle if PyInstaller rewrote it correctly; a file existing on
    disk does not by itself prove the frozen import resolves the same way.

    Same file-probe pattern as --version: a windowed build has no usable
    stdout, so the result is written to TESTASSIST_VERSION_FILE as two lines
    - the resolved path, then the first line of `ffmpeg -version` - and the
    path is left empty on any failure rather than raising.
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

    text = f"{path}\n{version_line}"
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
    app.setApplicationName("Test Assist")
    app.setOrganizationName("TestAssist")
    app.setStyle("Fusion")
    app.setStyleSheet(EDITOR_STYLE)
    app.setWindowIcon(_make_tray_icon())

    # Keep the process alive even when all windows are hidden
    # (launcher is the "last" visible window and must not trigger quit).
    app.setQuitOnLastWindowClosed(False)

    single = SingleInstanceManager()
    if not single.acquire():
        # Another instance could not be replaced cleanly.
        sys.exit(1)

    single.quit_requested.connect(app.quit)

    editor   = EditorWindow()
    launcher = FloatingLauncher(editor)
    tray = _setup_tray(app, launcher, editor)
    app.setProperty("trayIcon", tray)
    launcher.show()

    exit_code = app.exec()
    single.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
