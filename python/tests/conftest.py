from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def blank_pixmap() -> QPixmap:
    pixmap = QPixmap(480, 320)
    pixmap.fill(QColor("white"))
    return pixmap


@pytest.fixture(autouse=True)
def isolate_home(monkeypatch, tmp_path):
    """Point Path.home() at a temp directory for every test.

    EditorWindow.__init__ calls _load_history(), which creates
    ~/.test-assist/history and deletes any PNG under 5 KB it finds there. Any
    test that constructs an editor would otherwise prune the real capture
    history of whoever ran the suite.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)

    import capture
    import editor

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(capture.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(editor.Path, "home", staticmethod(lambda: home))
    return home
