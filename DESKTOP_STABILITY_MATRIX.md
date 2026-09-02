# 🔍 Test Assist — Desktop stability matrix

**Version:** 1.2
**Last updated:** 2026-09-03
**Applies to:** the PySide6 desktop build. The browser build has its own matrix
in `STABILITY_MATRIX.md`.

---

## Why this document exists

`DESKTOP_TEST_PLAN.md` says 129 of 134 cases are automated. That number is only
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
| Cases in `DESKTOP_TEST_PLAN.md` v1.7 | 151 |
| Automated and passing | 145 |
| Blocked, documented as manual | 6 |
| Automated tests | 229 collected — 229 pass everywhere, no skips |
| Wall clock | about 2-3 seconds warm; the first run is slower while the bundled ffmpeg loads |

**A green run is `229 passed, 0 skipped`, everywhere.** MP4 assembly used to
depend on `opencv-python`, an optional dependency the product deliberately
shipped without, which made REC-05 skip itself on CI, the packaged build, and
any clean checkout. It now shells out to a bundled `ffmpeg` binary via
`imageio-ffmpeg`, a real entry in `requirements.txt` — so REC-05 runs and
passes in every environment, and there is no longer a skip to explain away.

**The update check's network round-trip is not in that number.** UPD-01
through UPD-11 test the pure parsing and comparison functions, and the
launcher's dialog logic with a substituted result — none of it touches the
network. Whether `https://api.github.com/...` actually answers is UPD-12,
listed as Blocked below. Be honest with yourself about the difference: this
suite proves the update check's *logic* is correct, not that it will
successfully reach GitHub from a real machine.

**Multi-display capture (issue #1) is now fixed and covered the same way.**
Region capture, full-screen capture, recording, and all three launcher
pinning sites read `primaryScreen()` unconditionally, so anything on a
secondary monitor was silently wrong - a selection returned the matching area
on the *primary* instead, and a recording started on a secondary monitor
captured the primary with nothing to hint at it until playback. The geometry
fix is pure functions taking `QRect` values rather than `QScreen` objects
(`screen_geometry.py`), so negative-coordinate and mixed-DPI layouts are
covered by literal test geometries without a second monitor. A selection
spanning two screens is composited from both rather than clamped to one -
returning less than the user selected is exactly the class of bug this
removes. What is not provable here: the actual grabbed pixels coming out the
right size from a real high-DPI secondary. That is CAP-12, listed below.

**Data now lives somewhere update-safe, and the isolation moved with it
(TA-202).** `~/.test-assist` was undiscoverable on Windows and, worse, the
install folder it was tempting to move data *into* instead is wiped by every
update. Recordings now go to `Documents\Test Assist\`, capture history to
`%LOCALAPPDATA%\Test Assist\history` (deliberately not under Documents, since
it is auto-pruned on every launch), resolved through a single seam
(`paths.py`) rather than built by hand in two places. A populated
`~/.test-assist` from an earlier version migrates once, best-effort, and can
never block startup. The test isolation this suite depends on moved onto the
same seam — see **A safety fix the suite needed** below for what that means
and why it is asserted rather than assumed.

Six defects were found by writing these tests, and a seventh was fixed
following a user bug report rather than an internal test — see
**Defects found** below.

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

## The blocked six

| ID | Case | Why it cannot be automated here |
|----|------|--------------------------------|
| INS-02 | The app stays alive in the tray when the last window closes | Needs a real tray and a running event loop with a window manager. `QSystemTrayIcon` availability varies by desktop environment and is absent in the offscreen platform. |
| PKG-03 | The pinned taskbar icon matches the tray icon | A property of the Windows shell, not of the process. |
| PKG-04 | First launch on a machine without Python | Needs a clean Windows machine. The release workflow proves the exe runs on a runner, which is close but not the same as a machine that never had Python. |
| PKG-05 | Windows file properties show product name and version | Readable only from a Windows build; the version resource is ignored on Linux, where the validation build runs. |
| CAP-12 | A capture spanning or landing on a real high-DPI secondary monitor comes out the right size | Needs actual mixed-DPI hardware. The pure geometry functions are fully covered with literal mixed-size layouts (`test_screen_geometry.py`); what is not provable here is that `QScreen.grabWindow()`'s returned pixmap and the compositing `QPainter` produce correct pixels on a real scaled display, not just correct math on paper. |
| UPD-12 | A real round-trip to the GitHub API | Would make the suite depend on the network and GitHub's rate limits - "a suite that reaches the internet is a suite that fails on a train." `build.ps1` and the release workflow separately prove the packaged build *can* do TLS at all (PKG-07); nothing proves the request itself succeeds. |

These six are the manual pass to run against a release before trusting it.

---

## Stability by area

| Area | Cases | Stability | Notes |
|---|---|---|---|
| 3.1 Capture | 8 | Moderate | The grab is deferred by a 120 ms timer so the overlay can vanish first; the test waits for it rather than assuming. Offscreen grabs return a blank pixmap, so these prove the mechanism, not the pixels. CAP-10/11/13 substitute stub `QScreen` objects to prove `_grab()` picks the right screen(s) and composites correctly; CAP-12 (real mixed-DPI pixels) is Blocked. |
| 3.2 Recording | 9 | Moderate | REC-05 shells out to a real bundled `ffmpeg` binary to assemble an mp4; REC-09 substitutes a stub screen to prove the recorder uses the screen pinned at `start()`, not `primaryScreen()`; the rest are deterministic. |
| 3.3 Tools | 9 | Stable | Direct assertions on the annotation model. |
| 3.4 Crop | 4 | Stable | |
| 3.5 Blur | 3 | Stable | BLR-02 measures pixel variance in the exported image rather than trusting that a blur annotation exists. |
| 3.6 Selection & layering | 33 | Stable | SEL-01f pins the ordering between grabbing a resize handle and hit-testing for a new selection. |
| 3.6b Placed text | 4 | Stable | The edit dialog is substituted, so these prove the routing — border vs interior — not the dialog. |
| 3.7 Style | 5 | Stable | |
| 3.8 Zoom | 6 | Stable | ZOM-05 asserts that coordinates are in image space, not widget space. |
| 3.9 Undo/redo | 6 | Stable | |
| 3.10 Export | 9 | Stable | `QFileDialog` is substituted, so these prove what is written, not that the dialog appears. |
| 3.11 History | 8 | Stable | HIS-05 back-dates a file's mtime rather than waiting. |
| 3.12 Launcher | 8 | Stable | LCH-07 asserts the always-on-top flag is set, not that the window is actually on top. LCH-08 substitutes `QApplication.screenAt()` to prove docking and positioning measure the screen the widget is actually on. |
| 3.13 Shortcuts | 5 | Stable | KEY-05 exercises the real signal path rather than calling the setter directly. |
| 3.14 Lifecycle | 4 | Moderate | INS-01 binds a uniquely named local server so it cannot collide with a running app. |
| 3.15 Packaging | 7 | Blocked (3) | PKG-01, PKG-02, PKG-06 and PKG-07 are automated. PKG-07's "True" assertion is also exercised for real, once, against an actual PyInstaller build - see below. |
| 3.16 Update check | 12 | Stable (11) / Blocked (1) | UPD-01 through UPD-11 are pure-function and substituted-result tests, no network. UPD-12 (the real round-trip) is blocked. |
| 3.17 Diagnostics | 4 | Stable | ABT-02's clipboard assertion is the same shape as issue #1's own diagnosis - proving a reporter's monitor layout is now visible without a code read. |
| 3.18 Data Locations | 7 | Stable | `QStandardPaths.writableLocation` is substituted, not the real Windows API, so these prove the resolution and migration logic; they do not prove `Documents\Test Assist\` looks right in actual Windows Explorer. |

---

## Verified against a real PyInstaller build

The pytest suite runs `--selftest` through `main.main()` directly - real
logic, but never actually frozen. Two things it asserts only make sense once
frozen, so both were separately checked against an actual `build.ps1` run
(PyInstaller 6.22.2) rather than trusted on the strength of the source-level
tests alone:

- **ffmpeg resolution.** `_resolve_ffmpeg_exe()` locates the binary via
  `imageio_ffmpeg.__file__`, which only points inside the bundle if
  PyInstaller rewrote it correctly. The real build resolved it to
  `dist\TestAssist\_internal\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
  - genuinely inside `dist\`, not merely present somewhere on disk.
- **TLS.** Qt does not link TLS in; it depends on a separate plugin PyInstaller
  must also bundle. The real build reported `supportsSsl() -> True`, backend
  `schannel` - so `TestAssist.spec`'s aggressive `excludes` list does not
  catch it by accident, but that was verified, not assumed.

Both came back clean; no defect was found in either mechanism. That is a
different, weaker claim than "this is tested" - it means these two specific,
previously-uninspected risks turned out fine on this machine, this PyInstaller
version, this once. `build.ps1` and the release workflow re-run both checks
on every build, which is what makes the claim durable rather than a one-time
observation.

---

## A safety fix the suite needed

`EditorWindow.__init__` calls `_load_history()`, which touches the capture
history folder and deletes unreadable files there. Any test that constructs
an editor was therefore operating on the real capture history of whoever ran
the suite.

`conftest.py` redirects every location the app writes to, for **every** test.
Originally that meant patching `Path.home()`, back when history and recordings
were both built from it by hand; TA-202 moved resolution onto `paths.py` and
`QStandardPaths`, so `conftest.py`'s `isolate_home` fixture now patches
`paths.QStandardPaths.writableLocation` instead (`Path.home()` is still
patched too, since `paths.legacy_dir()` - migration only - still uses it), and
**asserts the redirect actually took effect** rather than trusting the patch:
a path returned by `paths.recordings_dir()` / `paths.history_dir()` must
resolve under `tmp_path`, checked on every single test via the fixture
itself. A test suite that can destroy the user's data is worse than no test
suite, and one where the isolation seam silently stopped working while still
reporting green would be worse still.

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

**4. Moving or resizing an annotation was not undoable.** The drag path mutated
the annotation in place without ever pushing an undo snapshot, so a misplaced or
mis-sized shape could not be taken back — the only recovery was to delete it and
draw it again. Found while implementing single-click selection, which makes an
accidental nudge easier to trigger. SEL-02b and SEL-02c hold the line, SEL-02d
covers redo.

The same path also skipped `annotation_changed`, which every other mutating
operation emits. That is now emitted too, and SEL-02e pins it — but be clear
about what it is worth: **nothing in the app currently connects to that signal.**
There is no dirty-state indicator, no unsaved-changes prompt and no autosave, so
the missing emit had no user-visible effect. It is fixed for consistency, so that
anything wired to the signal later sees drags as well.

**5. v1.1.0 shipped reporting itself as 1.0.0.** `version_info.txt` was a second,
hand-maintained copy of the version number, and it was not updated when
`__version__` was bumped for that release. Nothing caught it because the release
verify step only checked that the output was version-*shaped*, not that it was
the *right* version. Found by inspecting the actual v1.1.0 release artefact
while adding PKG-06, not by a failing test — there was no test to catch it.
There is now: PKG-06 pins `version_info.txt` to `__version__`, and the release
workflow asserts the built binary's self-reported version equals the git tag.

**6. MP4 encoding could silently fail even with ffmpeg correctly bundled.**
`imageio_ffmpeg.get_ffmpeg_exe()` validates the binary it finds by running
`ffmpeg -version` as a subprocess without redirecting stdin. A process with no
real stdin handle — this app, built with `console=False` — can make that
validation subprocess fail to start even though ffmpeg itself runs fine, so
recording would unpredictably fall back to a frame sequence for reasons that
had nothing to do with ffmpeg. Caught as intermittent (roughly 1-in-3) failures
of REC-05 while verifying this suite is actually deterministic, not by a single
failing run — flaky is easy to mistake for fine. `capture.py` now locates the
bundled binary by path instead of going through that check.

**7. Region capture, full-screen capture, recording and three launcher
positioning sites all read `primaryScreen()` unconditionally.** Reported as
GitHub issue #1, not found by writing these tests - the opposite direction
from defects 1-6. On a laptop with an external monitor, a region selected on
the secondary returned the matching area on the *primary* instead; the
overlay is placed at the virtual desktop's origin, so widget coordinates are
not global coordinates whenever a screen sits left of or above the primary,
which is negative on Windows and was being treated as if it were (0, 0).
Recording had the identical bug and was not in the original report — a
tester recording a repro on a secondary monitor got footage of the primary
with nothing to hint at it until playback. Fixed with pure geometry functions
in `screen_geometry.py` that take `QRect` values instead of `QScreen`
objects, so the fix is covered by literal negative-coordinate and mixed-size
layouts without a second monitor (`test_screen_geometry.py`, CAP-10/11/13,
REC-09, LCH-08). Decision made explicitly rather than left implicit: a
selection spanning two screens is composited from every intersecting screen
rather than clamped to the one holding the most of it, because silently
returning less than the user selected is exactly the class of bug this
removes. What is not covered: the actual pixel-level correctness of a grab on
real mixed-DPI hardware - CAP-12, listed as Blocked above.

---

## The selection model

Selecting, moving and resizing were rebuilt for volume use. The model is now:

- **A shape's border is its grip.** One click on the border selects it and shows
  eight handles; dragging the border moves it. Interiors are click-through, so a
  rectangle drawn around a defect never blocks the marks inside it, and nothing
  has to be reordered to reach them. A circle selects from its arc, not its empty
  bounding-box corners; an arrow from its shaft, not the large empty box around a
  diagonal line.
- **A text box is the exception, deliberately.** Its border moves it; clicking
  inside it edits the words.
- **Handles are in screen pixels.** Both the drawn radius and the grab radius are
  divided by the zoom, so they are the same size to the hand at 40% as at 250%.
  Previously they lived in image space and shrank to nothing when zoomed out —
  precisely when you are repositioning things.
- **Corners resize both axes, edge midpoints one.** Shift keeps the proportions
  on a corner, or locks a move to an axis. Arrow keys nudge, Escape abandons a
  drag, and everything is undoable.
- **The cursor states the outcome before the click.** SEL-15a–g assert the exact
  shape at seven positions, which is the only way this stays true.

The riskiest part is border-based hit-testing, because it changes how every
existing shape selects. It is the piece to check first if anything about
selection feels wrong.

### What automation still cannot tell you

These tests drive the widget's own handlers offscreen. They prove the geometry,
the state machine and the cursor *shape*. They cannot tell you whether the
handles are comfortable to hit with a real mouse on a real screen, whether the
grab radius is right for the hand, or whether the cursor changes feel
responsive. That is a sitting-down-with-it judgement and it has not been made
yet on the packaged build.

---
---

## Running them

```bash
cd python
pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen pytest -q      # 229 passed, about 2-3 seconds warm;
                                          # slower on the first run while the
                                          # bundled ffmpeg loads
```

On Windows the platform variable is unnecessary; `conftest.py` sets it.
