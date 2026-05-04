"""Entry point for Test Assist (PySide6 desktop app)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from editor import EditorWindow
from launcher import FloatingLauncher
from theme import EDITOR_STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Test Assist")
    app.setOrganizationName("TestAssist")
    app.setStyle("Fusion")
    app.setStyleSheet(EDITOR_STYLE)

    # Keep the process alive even when all windows are hidden
    # (launcher is the "last" visible window and must not trigger quit).
    app.setQuitOnLastWindowClosed(False)

    editor   = EditorWindow()
    launcher = FloatingLauncher(editor)
    launcher.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
