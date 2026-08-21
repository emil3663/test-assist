# 🔍 Test Assist — Desktop stability matrix

**Version:** 1.0
**Last updated:** 2026-08-21
**Applies to:** the PySide6 desktop build. The browser build has its own matrix
in `STABILITY_MATRIX.md`.

---

## Why this document exists

`DESKTOP_TEST_PLAN.md` says 87 of 91 cases are automated. That number is only
worth anything if you can check what it covers and what it quietly does not.
This document is that check.

| Stability | Meaning |
|---|---|
| **Stable** | Deterministic. No timing dependency, no environment dependency. |
| **Moderate** | Deterministic in behaviour but depends on timing or a substituted API. |
| **Blocked** | Cannot be automated here; needs a built executable on real Windows. |

---

## Coverage

| | Count |
|---|---|
| Cases in `DESKTOP_TEST_PLAN.md` v1.1 | 91 |
| Automated and passing | 87 |
| Blocked, documented as manual | 4 |
| Automated tests | 108 (`test_regressions.py` + `test_functional.py`) |
| Wall clock | under 2 seconds |

Three defects were found by writing these tests. All are fixed and all have a
regression test — see **Defects found** below.

---

## What the tests run against

`QT_QPA_PLATFORM=offscreen`, so real widgets are constructed and real event
handlers run, but nothing is drawn to a display. Mouse interaction is driven by
calling the widget's own `mousePressEvent` / `mouseMoveEvent` /
`mouseReleaseEvent` with position stubs, which is the same path a real click
takes once Qt has dispatched it.

What that does **not** prove: that Qt dispatches those events to the right
widget in a real window, that the layout is usable, or that anything is legible.
Those are properties of a running desktop and remain manual.

---

## The blocked four

| ID | Case | Why it cannot be automated here |
|----|------|--------------------------------|
| INS-02 | The app stays alive in the tray when the last window closes | Needs a real tray and a running event loop with a window manager. `QSystemTrayIcon` availability varies by desktop environment and is absent in the offscreen platform. |
| PKG-03 | The pinned taskbar icon matches the tray icon | A property of the Windows shell, not of the process. |
| PKG-04 | First launch on a machine without Python | Needs a clean Windows machine. The release workflow proves the exe runs on a runner, which is close but not the same as a machine that never had Python. |
| PKG-05 | Windows file properties show product name and version | Readable only from a Windows build; the version resource is ignored on Linux, where the validation build runs. |

These four are the manual pass to run against a release before trusting it.

---

## Stability by area

| Area | Cases | Stability | Notes |
|---|---|---|---|
| 3.1 Capture | 4 | Moderate | The grab is deferred by a 120 ms timer so the overlay can vanish first; the test waits for it rather than assuming. Offscreen grabs return a blank pixmap, so these prove the mechanism, not the pixels. |
| 3.2 Recording | 8 | Moderate | REC-05 skips where `opencv-python` is absent, which includes the packaged build. The rest are deterministic. |
| 3.3 Tools | 10 | Stable | Direct assertions on the annotation model. |
| 3.4 Crop | 4 | Stable | |
| 3.5 Blur | 3 | Stable | BLR-02 measures pixel variance in the exported image rather than trusting that a blur annotation exists. |
| 3.6 Selection & layering | 8 | Stable | |
| 3.7 Style | 5 | Stable | |
| 3.8 Zoom | 6 | Stable | ZOM-05 asserts that coordinates are in image space, not widget space. |
| 3.9 Undo/redo | 6 | Stable | |
| 3.10 Export | 9 | Stable | `QFileDialog` is substituted, so these prove what is written, not that the dialog appears. |
| 3.11 History | 8 | Stable | HIS-05 back-dates a file's mtime rather than waiting. |
| 3.12 Launcher | 7 | Stable | LCH-07 asserts the always-on-top flag is set, not that the window is actually on top. |
| 3.13 Shortcuts | 5 | Stable | KEY-05 exercises the real signal path rather than calling the setter directly. |
| 3.14 Lifecycle | 4 | Moderate | INS-01 binds a uniquely named local server so it cannot collide with a running app. |
| 3.15 Packaging | 5 | Blocked (3) | PKG-01 and PKG-02 are automated. |

---

## A safety fix the suite needed

`EditorWindow.__init__` calls `_load_history()`, which touches
`~/.test-assist/history` — and used to delete files there. Any test that
constructs an editor was therefore operating on the real capture history of
whoever ran the suite.

`conftest.py` now redirects `Path.home()` to a temporary directory for **every**
test. A test suite that can destroy the user's data is worse than no test suite.

---

## Defects found by writing these tests

**1. History pruning deleted real captures.** `_load_history` removed any PNG
under 5 KB, as a proxy for "blank or corrupt". It is a bad proxy: a capture of a
dialog or a form on a plain background compresses well below 5 KB, so genuine
evidence was deleted on the next launch. Pruning now tests whether the file is a
readable image, which is the thing actually meant. Caught by HIS-01, pinned by
HIS-03b.

**2. The recorder crashed when the frame count and the disk disagreed.** `_save`
guarded on the frame counter but not on the frames being present, so a failed
write or a removed folder raised `IndexError` instead of finishing cleanly.
Caught by REC-03 while testing the duration cap.

**3. The recorder held every frame in memory.** Measured at 7.92 MB per frame,
so a one-minute recording held roughly 7 GB. Fixed before this suite was
written; REC-01 and REC-02 now hold the line.

---

## An open question, not a defect

**Selection is bound to double-click**, for every tool including Select. A
single click with the Select tool active selects nothing. SEL-01b documents the
current behaviour rather than asserting the intended one, because a tool named
Select that does not select on click is surprising enough to be worth a decision
rather than a silent fix.

---

## Running them

```bash
cd python
pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen pytest -q      # 108 tests, under 2 seconds
```

On Windows the platform variable is unnecessary; `conftest.py` sets it.
