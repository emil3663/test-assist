"""Entry point for Test Assist (PySide6 desktop app)."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from editor import EditorWindow
from launcher import FloatingLauncher
from single_instance import SingleInstanceManager
from theme import EDITOR_STYLE


def _make_tray_icon() -> QIcon:
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


def main() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TestAssist.App")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Test Assist")
    app.setOrganizationName("TestAssist")
    app.setStyle("Fusion")
    app.setStyleSheet(EDITOR_STYLE)

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
