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
    """Redirect every location the app writes to, for every test.

    Recordings and history used to live under Path.home()/".test-assist",
    which is what made patching Path.home() sufficient. TA-202 moved both
    onto QStandardPaths via paths.py, so that seam disappeared - patching
    paths.QStandardPaths.writableLocation is the new one, and it is the only
    one, since capture.py and editor.py no longer call Path.home() directly
    at all (paths.legacy_dir() still does, for migration, which is why
    Path.home() is still patched here too).

    The two asserts are not decoration. EditorWindow.__init__ calls
    _load_history(), which deletes any unreadable file it finds in the
    history folder - so a patch that silently stopped taking effect (a
    renamed target, a missed import order) would have this suite pruning the
    real ~/Documents and %LOCALAPPDATA% of whoever ran it, while still
    reporting green. Isolation that is patched but never verified is not
    verified.
    """
    home = tmp_path / "home"
    documents = tmp_path / "documents"
    app_local = tmp_path / "app_local"
    for directory in (home, documents, app_local):
        directory.mkdir(parents=True, exist_ok=True)

    import paths
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    def _fake_writable_location(location):
        if location == QStandardPaths.StandardLocation.DocumentsLocation:
            return str(documents)
        if location == QStandardPaths.StandardLocation.AppLocalDataLocation:
            return str(app_local)
        raise AssertionError(f"unexpected QStandardPaths location requested in tests: {location}")

    monkeypatch.setattr(paths.QStandardPaths, "writableLocation", staticmethod(_fake_writable_location))

    assert str(paths.recordings_dir()).startswith(str(tmp_path)), \
        "recordings_dir() did not redirect under tmp_path - test isolation is not verified"
    assert str(paths.history_dir()).startswith(str(tmp_path)), \
        "history_dir() did not redirect under tmp_path - test isolation is not verified"

    return home
