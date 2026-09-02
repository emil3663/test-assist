"""Where Test Assist writes its data.

The single seam every caller goes through. `capture.py` and `editor.py` used
to build `Path.home() / ".test-assist" / ...` by hand in two separate places,
which is exactly what made the old test isolation (patching `Path.home`)
fragile, and exactly what a new one scattered the same way would repeat.

`~/.test-assist` was undiscoverable on Windows - a dot-prefixed folder is a
Unix convention Windows users do not look in - and the install folder is not
a fix: the documented update procedure is "close the app, download the zip,
replace the contents of the folder you run it from", so anything written
there is deleted by every update.

Split by what the files *are*:

- Recordings and saved exports are user evidence: Documents, so they are
  discoverable, covered by whatever backs up Documents, per-user, and
  untouched by the update procedure above.
- Capture history is an app-managed cache that gets auto-pruned on every
  launch (see editor.py's `_prune_unreadable_history`). That must never live
  under Documents - an auto-deleting folder there would be alarming, not
  just annoying - so it goes to AppLocalDataLocation instead.

QStandardPaths needs a live QCoreApplication to resolve app-name-derived
locations, so every path here is resolved lazily inside a function, never at
import time or as a module-level constant.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def recordings_dir() -> Path:
    """User evidence: screen recordings and saved exports."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    path = Path(base) / "Test Assist"
    path.mkdir(parents=True, exist_ok=True)
    return path


def history_dir() -> Path:
    """App-managed capture-history cache, auto-pruned on every launch.

    Deliberately not under recordings_dir() / Documents - see the module
    docstring for why an auto-pruned folder must not live there.
    """
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    path = Path(base) / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_dir() -> Path:
    """Where everything lived before this module existed."""
    return Path.home() / ".test-assist"


def migrate_legacy_data() -> None:
    """One-time, best-effort move from the pre-1.4 `~/.test-assist` layout.

    This is not for a fresh dev checkout - v1.0.0, v1.1.0 and v1.3.0 are
    public downloads, and at least one person outside this repo has real
    recordings and history sitting in the old location. Never allowed to
    fail or block startup: any problem here is swallowed. The old folder is
    left in place (possibly empty) rather than risking a delete of evidence
    that failed to copy across.
    """
    try:
        legacy = legacy_dir()
        if not legacy.is_dir():
            return
        _migrate_contents(legacy / "recordings", recordings_dir())
        _migrate_contents(legacy / "history", history_dir())
    except Exception:
        pass


def _migrate_contents(source: Path, destination: Path) -> None:
    if not source.is_dir():
        return
    for item in source.iterdir():
        target = destination / item.name
        if target.exists():
            # Already migrated, or a name collision - leave both alone
            # rather than overwrite something that might be a different file.
            continue
        try:
            item.rename(target)
        except OSError:
            # One unreadable or locked item must not stop the rest of the
            # migration, and must not prevent startup.
            continue
