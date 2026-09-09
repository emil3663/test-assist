"""Fixtures for the TA-228 black-box smoke lane.

Drives the actual packaged TestAssist.exe from outside the process via
pywinauto (Windows UI Automation) - not an import of python/'s modules the
way every other test in this project works. This is why it lives in its
own top-level directory rather than tests/: it cannot run from a source
checkout alone, needs a build first, and is not collected by the main
suite (pytest.ini's testpaths / the CI test job only points at tests/).
See this directory's README.md for how to run it and why it is a
local/manual lane rather than a CI one for now.
"""
from __future__ import annotations

import ctypes
import os
import time
from pathlib import Path

import pytest

# Must happen before any pywinauto/COM/UIA usage - Windows process DPI
# awareness is a one-time, early-process setting that has no effect once
# something has already queried it. Without this, click coordinates
# resolved against the target app's own per-monitor-DPI-aware geometry
# land in the wrong place for a caller that Windows treats as DPI-unaware
# (the default for a bare python.exe).
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass

_DEFAULT_EXE = Path(__file__).resolve().parents[1] / "dist" / "TestAssist" / "TestAssist.exe"


def _exe_path() -> Path:
    override = os.environ.get("TESTASSIST_EXE")
    return Path(override) if override else _DEFAULT_EXE


@pytest.fixture
def exe_path() -> Path:
    path = _exe_path()
    if not path.is_file():
        pytest.skip(
            f"no built exe at {path} - run python\\build.ps1 first, or point "
            "TESTASSIST_EXE at an existing build"
        )
    return path


@pytest.fixture
def app(exe_path):
    """A running TestAssist.exe, killed on teardown regardless of the
    test's outcome - a leaked process here would hold the real, shared
    Win32 hotkeys (RegisterHotKey) and go on running invisibly."""
    from pywinauto import Application

    application = Application(backend="uia").start(str(exe_path))
    try:
        yield application
    finally:
        try:
            application.kill()
        except Exception:
            pass
        # kill() is not always instant - a still-exiting process can hold
        # the hotkeys just long enough to fail the *next* thing that
        # needs them (this lane's own next test, or a real launch).
        time.sleep(0.5)


@pytest.fixture
def launcher(app):
    """The launcher's top-level window - main.py never gives it a
    setWindowTitle(), so Qt falls back to reporting the QApplication's
    own applicationName ("Test Assist", set in main.py) as its UIA Name."""
    window = app.window(title="Test Assist")
    window.wait("visible", timeout=15)
    return window
