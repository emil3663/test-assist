"""Opt-in plain-text logging for hard-to-reproduce, hardware-dependent bugs.

Exists for TA-220's minimize-toggle gap, TA-217's hotkey-capture gap,
TA-223 and TA-225 (see TESTASSIST_BACKLOG.md) - four issues this dev
environment cannot reproduce (no second monitor, no interactive Windows
session), where reading the code has run out of answers and only a real
measurement on the reporter's own hardware can move them forward. Gated
behind TESTASSIST_DEBUG=1 so a normal run pays nothing and writes nothing.

The env var is read on every call, not cached at import time, so a test
(or a user) can toggle it without needing to reimport this module.
"""
from __future__ import annotations

import os
import time

import paths


def log(message: str) -> None:
    if os.environ.get("TESTASSIST_DEBUG") != "1":
        return
    try:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        with open(paths.history_dir() / "debug.log", "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        # Never let opt-in diagnostic logging take down the app it's
        # meant to be helping debug.
        pass
