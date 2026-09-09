# 🔍 Test Assist — Desktop stability matrix

**Version:** 1.13
**Last updated:** 2026-09-09
**Applies to:** the PySide6 desktop build. The browser build has its own matrix
in `STABILITY_MATRIX.md`.

---

## Why this document exists

`DESKTOP_TEST_PLAN.md` says most of its cases are automated. That number is
only worth anything if you can check what it covers and what it quietly does
not. This document is that check.

| Stability | Meaning |
|---|---|
| **Stable** | Deterministic. No timing dependency, no environment dependency. |
| **Moderate** | Deterministic in behaviour but depends on timing or a substituted API. |
| **Blocked** | Cannot be automated here; needs a built executable on real Windows. |

---

## Coverage

| | Count |
|---|---|
| Cases in `DESKTOP_TEST_PLAN.md` v1.17 | 175 |
| Automated and passing | 170 |
| Blocked, documented as manual | 5 |
| Automated tests | 270 collected — 270 pass everywhere, no skips |
| Wall clock | about 2-3 seconds warm; the first run is slower while the bundled ffmpeg loads |

**A green run is `270 passed, 0 skipped`, everywhere.** MP4 assembly used to
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
removes. Real mixed-DPI hardware later confirmed the pixels come out the
right size (CAP-12, exercised 2026-09-07 - see **Defects found** below for
what it actually turned up).

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

**The first multi-display fix was necessary but not sufficient.** Real
two-monitor hardware proved `ScreenshotOverlay.activate()` called
`showFullScreen()` after `setGeometry()`, and `showFullScreen()` silently
discards the requested geometry and sizes the window to fullscreen on *a*
screen instead - the overlay never covered a second screen at all, rather
than merely mis-grabbing it once shown. The same diagnostic run confirmed the
coordinate translation `screen_geometry.py` provides was already correct
(every drag reported zero disagreement), so that work was not wasted, just
incomplete on its own. Fixed by using plain `show()` (the window is already
frameless and always-on-top, so it needs no fullscreen state to cover what
it is told to), reading mouse positions via `globalPosition()` throughout so
the capture rect has no dependency on window geometry left to get wrong, and
excluding any gap between mismatched screens from the dimmed selection area
rather than letting it silently yield nothing. CAP-14 is the regression test,
reproducible with the one real screen the offscreen platform provides by
mocking `virtualGeometry()` to look like the reported hardware while the
real platform integration sizes `showFullScreen()` to the real screen
regardless; verified to fail against the old code and pass against the fix.

Twelve defects have been found so far: six by writing these tests, two
following a user bug report, and four following real-hardware verification
that went beyond what these tests alone could prove — see **Defects found**
below.

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

## The blocked five

| ID | Case | Why it cannot be automated here |
|----|------|--------------------------------|
| INS-02 | The app stays alive in the tray when the last window closes | Needs a real tray and a running event loop with a window manager. `QSystemTrayIcon` availability varies by desktop environment and is absent in the offscreen platform. **Exercised manually 2026-09-07 and FAILED** — see defect 11 below. The tray itself stays Blocked; what the close button is wired to is now covered separately by INS-05/INS-06. |
| PKG-03 | The pinned taskbar icon matches the tray icon | A property of the Windows shell, not of the process. |
| PKG-04 | First launch on a machine without Python | Needs a clean Windows machine. The release workflow proves the exe runs on a runner, which is close but not the same as a machine that never had Python. |
| PKG-05 | Windows file properties show product name and version | Readable only from a Windows build; the version resource is ignored on Linux, where the validation build runs. |
| UPD-12 | A real round-trip to the GitHub API | Would make the suite depend on the network and GitHub's rate limits - "a suite that reaches the internet is a suite that fails on a train." `build.ps1` and the release workflow separately prove the packaged build *can* do TLS at all (PKG-07); nothing proves the request itself succeeds. |

CAP-12 (a capture spanning or landing on a real high-DPI secondary monitor)
was on this list until 2026-09-07: exercised on real hardware, it turned up
one defect, the gap between screens (defect 10), not a DPI-scaling problem -
the pixels and screen ordering were already correct. Fixed by compositing
adjacently (CAP-16/17/18, items 8 and its follow-up - see defect 12), which
turned the remaining risk into pure geometry the suite can actually reach,
so CAP-12 moved off this list rather than staying Blocked for a risk that no
longer exists.

These five are the manual pass to run against a release before trusting it.

---

## Stability by area

| Area | Cases | Stability | Notes |
|---|---|---|---|
| 3.1 Capture | 14 | Moderate | The grab is deferred by a 120 ms timer so the overlay can vanish first; the test waits for it rather than assuming. Offscreen grabs return a blank pixmap, so these prove the mechanism, not the pixels. CAP-10/11/13 substitute stub `QScreen` objects to prove `_grab()` picks the right screen(s) and composites correctly. CAP-12 was exercised once on real mixed-DPI hardware (2026-09-07) rather than automated directly; what it found (the gap, not a DPI defect) is now covered by CAP-16/17/18's literal-layout tests. CAP-14 mocks `virtualGeometry()` and requires an explicit `processEvents()` call to observe the platform-level effect of `showFullScreen()` at all - asserting immediately after `activate()` would pass against the buggy code too, for the wrong reason. CAP-16/17 were each verified to fail against the pre-fix arithmetic they superseded, both at the pure-geometry level and end-to-end through `_grab()`; CAP-18 (diagonal) is a pinning test, not a regression test - the old code produced the same output for that layout by incidence, not by design. |
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
| 3.11 History | 18 | Moderate | HIS-05 back-dates a file's mtime rather than waiting. HIS-08 through HIS-12 (item 4) prove recordings appear in the gallery, get their own widget rather than being fed through `_SnapshotThumb`'s `QPixmap(path)` call, open externally rather than loading into the canvas, and are never touched by history pruning. HIS-13 through HIS-17 (recording thumbnails) shell out to the real bundled ffmpeg the same way REC-05 does, and HIS-14/HIS-15 poll for a background-thread result with a timeout rather than a fixed sleep - see the note on `QTest.qWait()` below. All five were verified to fail against the pre-fix code; HIS-17 (pruning vs. a thumbnail file) is a pinning test, not a regression test - the pruning glob already only ever matched `*.png`, thumbnail or not. |
| 3.12 Launcher | 11 | Stable | LCH-07 asserts the always-on-top flag is set, not that the window is actually on top. LCH-08 substitutes `QApplication.screenAt()` to prove docking and positioning measure the screen the widget is actually on. DSP-12/13/14 were each verified to genuinely fail against the pre-fix code (reverted locally, run, restored) rather than trusted to discriminate on the strength of the arithmetic alone. |
| 3.13 Shortcuts | 6 | Stable | KEY-05 exercises the real signal path rather than calling the setter directly. KEY-06 (the `help.html` pin, PRE_BUILD_HANDOVER item 5) is a deliberately partial mechanical check: the 9 tool-letter and 4 editing rows are compared against the real `QShortcut` objects `EditorWindow` registers, but the 3 launcher-only rows (Alt+P, Alt+Shift+P, Alt+V) are not pinned the same way. Those are inline `keyPressEvent` conditionals in `launcher.py`, not `QShortcut` objects - there is no non-hardcoded source of truth to check them against without either regex-parsing source (brittle to any refactor) or a second hardcoded list (which just moves the manual-sync burden rather than removing it). Their behaviour, not their documentation, is what `test_launcher_keyPressEvent_*` covers instead. |
| 3.14 Lifecycle | 6 | Moderate | INS-01 binds a uniquely named local server so it cannot collide with a running app. INS-05 monkeypatches `QApplication.quit` at the class level (this suite shares one real `QApplication`) rather than calling it for real, verified to fail against the pre-fix code. INS-06 covers `restore()`'s off-screen repositioning, also verified to fail without it. |
| 3.15 Packaging | 7 | Blocked (3) | PKG-01, PKG-02, PKG-06 and PKG-07 are automated. PKG-07's "True" assertion is also exercised for real, once, against an actual PyInstaller build - see below. |
| 3.16 Update check | 12 | Stable (11) / Blocked (1) | UPD-01 through UPD-11 are pure-function and substituted-result tests, no network. UPD-12 (the real round-trip) is blocked. |
| 3.17 Diagnostics | 4 | Stable | ABT-02's clipboard assertion is the same shape as issue #1's own diagnosis - proving a reporter's monitor layout is now visible without a code read. |
| 3.18 Data Locations | 7 | Stable | `QStandardPaths.writableLocation` is substituted, not the real Windows API, so these prove the resolution and migration logic; they do not prove `Documents\Test Assist\` looks right in actual Windows Explorer. |
| 3.19 Editor Chrome | 2 | Stable | UI-01/UI-02 (items 2-3) check the stylesheet's own text, not rendered pixels - they prove no rule sets a sub-3:1-contrast colour or omits the shared small-icon-button rule, not that a button looks right on screen. |

---

## A `QTest.qWait()` gap found while testing recording thumbnails

The recording-thumbnail backfill (`editor._RecordingThumb`) runs off the GUI
thread via the standard `moveToThread()` worker idiom, and delivers its result
back via a normal cross-thread signal-slot connection - the kind Qt is
supposed to auto-queue onto the receiver's own thread. `QTest.qWait()`, this
suite's usual tool for "wait for something async" (used elsewhere for
timer-driven UI), was tried first to pump the event loop while waiting for
that delivery. Under this suite's offscreen QPA platform it did not reliably
deliver the queued signal - not flaky, consistently absent, confirmed over
repeated runs of an isolated reproduction outside pytest entirely. A plain
loop calling `QApplication.processEvents()` directly, with a short sleep
between calls, delivered it every time, also confirmed over repeated runs.
HIS-14 and HIS-15 use that pattern (`_wait_until()` / `_pump_events()` in
`test_functional.py`) instead of `qWait()`, with a comment pointing at this
section so it is not silently reintroduced.

The same isolated reproduction also caught a real bug before it reached the
test suite at all: the worker object passed to `moveToThread()` was kept
alive only via `_pending_thumbnail_threads` holding the `QThread`, not the
worker itself. `moveToThread()` does not extend an object's Python lifetime,
so with no other reference the worker could be garbage-collected while the
background thread was still using it - a genuine use-after-free (an access
violation, not a hang, in the reproduction), not a hypothetical one. Fixed by
keeping `(thread, worker)` pairs together.

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

**8. The overlay never covered a second screen at all - defect 7 was
necessary but not sufficient.** `ScreenshotOverlay.activate()` called
`showFullScreen()` after `setGeometry()`; `showFullScreen()` is defined as
fullscreen on *a* screen, so it silently discarded the requested virtual-
desktop geometry and sized the window to one screen only. A second screen
was not merely mis-grabbed, as defect 7's fix assumed - it was physically
uncovered, unreachable to a click. Found by running a diagnostic overlay on
real two-monitor hardware, which also confirmed the coordinate translation
itself was already correct (every drag reported zero disagreement), so
defect 7's fix was not wasted. Fixed by using plain `show()` instead - the
window is already frameless and always-on-top, so no fullscreen state is
needed to cover what it's told to - reading mouse positions via
`globalPosition()` throughout so the capture rect no longer depends on
window geometry at all, using `virtualGeometry()` rather than
`availableVirtualGeometry()` so a taskbar can be selected, and excluding any
gap between mismatched screens from the dimmed area rather than letting a
selection there silently yield nothing. CAP-14 is the regression test,
verified to fail against the old code and pass against the fix using only
the one real screen the offscreen platform provides.

**9. Fixing LCH-08 correctly exposed a fresh bug in the launcher's auto-dock
and undock (DSP-12/13/14).** Found by a manual pass on real two-monitor
hardware, not by these tests - the opposite direction from defects 1-6.
Auto-dock used a half-plane test ("right edge at or past the screen's right
edge"); it never fired incorrectly before because the launcher's screen was
always (wrongly) measured as the primary, so making `_current_screen()`
correct is what exposed it - a widget entering a screen from its right side
satisfies a half-plane the instant it arrives, so dragging the launcher onto
the laptop (to the left of the external) auto-docked on arrival. Separately,
the same 384px gap between the two monitors that motivated CAP-12 made
`screenAt()` return `None` mid-drag; falling back to the primary there is
why undocking sent the launcher back to the external instead of the laptop
it had been docked on. Fixed with a narrow proximity band instead of a
half-plane (`is_within_dock_band()`, requiring the pointer to also be on the
resolved screen), a largest-overlap fallback reusing `screen_for_rect()`
instead of defaulting to the primary, and resolving the screen once in
`_dock_right()`/`_undock()` before either mutates the frame a second
resolution would otherwise re-read mid-call. All three fixes were verified
to genuinely fail against the pre-fix code (reverted locally, run, restored)
rather than trusted to discriminate on the strength of the arithmetic alone,
the same lesson learned while building CAP-14.

**10. CAP-12 was finally exercised on real mixed-DPI hardware, and the
compositing is correct — but the gap between the screens is not.** A
selection dragged from the 125% laptop across to the 100% external produced
both screens' content, in the right order, at the right sizes. Between them
sat a solid black band. It is not wrong content: the layout is laptop
`-1920..-384` and external `0..1920`, so `-384..0` is virtual-desktop
coordinate space belonging to no screen. `_grab()` allocates the result at
`global_rect.size()` and fills it transparent, `plan_capture()` correctly
emits no piece for the dead zone, and every viewer renders transparent as
black. The math is right and the output is unusable — the failure mode
predicted when the dead zone was excluded from the dimmed region rather than
clamped. Fixed by compositing the pieces adjacently instead of at their true
virtual-desktop offset (`plan_capture()`, `docs/PRE_BUILD_HANDOVER.md` item
8) - pieces are sorted left-to-right and their x offsets accumulated, so a
gap of any width collapses to zero rather than reappearing as unpainted
space. Vertical offsets keep their true relative position, on the
(mistaken, see defect 12) assumption that screens separated in y were
always laid out side by side in x. This also means CAP-12 no longer needs
to stay Blocked: the `dest` arithmetic is now pure geometry, covered by
literal-layout tests (CAP-16, `test_screen_geometry.py`) like the rest of
the module, verified to fail against the old true-offset code both at the
pure-geometry level and end-to-end through `_grab()`.

**11. INS-02 was exercised and failed: the launcher's X quits the whole
application.** `_close_launcher()` calls `QApplication.instance().quit()`, so
closing the floating widget takes the tray icon with it and `Show Launcher`
is unreachable — nothing short of relaunching the exe brings the app back.
This is the reason the same manual pass could not take a full-screen capture
("unable to get the floating widget to display"): the app was not hidden, it
was gone. Worth noting what the suite could and could not have caught here.
The tray itself is genuinely Blocked — `QSystemTrayIcon` needs a real desktop
environment. But *what the X button is wired to* is not: nothing prevented a
test asserting that activating `_btn_close` leaves the application running.
Blocked-ness of the surrounding feature was allowed to excuse leaving the
adjacent, testable half uncovered, which is its own lesson.

Fixed: `_close_launcher()` now hides rather than quitting, so the tray icon
and `Show Launcher` survive it; `Exit` in the tray menu is the only full
quit (INS-05). While in there, `Show Launcher` and a tray-icon click were
also changed to go through a new `restore()` rather than `show()`/`raise_()`
directly, which repositions the launcher - docked or floating, matching how
it was left - if the screen it was on is no longer there, e.g. hidden while
docked to a monitor since unplugged (DSP-15, INS-06). Both fixes were
verified to fail against the pre-fix code: `test_INS_02_close_button_hides_
instead_of_quitting` monkeypatches `QApplication.quit` at the class level
(this suite shares one real `QApplication`) rather than calling it for real.

**12. Defect 10's fix (item 8, e201cdb) was itself incomplete: it only closed
gaps along x.** `plan_capture()` sorted every intersecting piece by
`intersection.left()` and accumulated x offsets unconditionally, which is
correct when screens are arranged side by side but wrong when they are
stacked - two screens sharing the same x-range (`(0,-1080,1920,1080)` above
`(0,0,1920,1080)`) have the same `left()` for any centered selection, so
sorting by it left their relative order to Python's stable-sort incidence
rather than their actual vertical relationship, and packing them along x
anyway reintroduced the exact black-band failure defect 10 exists to
remove, just rotated onto the other axis. Reported by the user with an
exact repro: selecting `(200,-500,800,1000)` across that pair produced dest
`(0,0)`/`(800,500)` and a 1600×1000 result pixmap, half of it unpainted,
where `(0,0)`/`(0,500)` and a fully-painted 800×1000 pixmap was expected -
found by inspection of the arithmetic, not by the suite, since e201cdb's
own tests only ever exercised horizontally-separated layouts.

Fixed by making the axis choice explicit rather than assumed:
`plan_capture()` now checks whether every piece's x-range overlaps every
other's (`max(lefts) <= min(rights)`); if so the screens are stacked
relative to each other, so it sorts by `top()` and accumulates y instead,
preserving x. Otherwise - separated in x, or genuinely diagonal - it packs
along x exactly as e201cdb did, unchanged. `_grab()`'s result-pixmap sizing
was generalized to match: a uniform `max(dest + size)` bounding box per
axis replaces the old x-specific `sum(widths)` formula, since summing is
only correct for the axis actually being packed and the packed axis can
now be either one. Verified against defect 10's regression by hand-tracing
e201cdb's exact code against the vertical-stack repro (confirming it does
produce `(0,0)`/`(800,500)`) before writing the fix, then confirming the
new tests (`test_DSP_04_secondary_directly_above_with_a_gap_stacks_
vertically`, `..._directly_below_...`) fail the same way against a reverted
copy; the four tests e201cdb added for the horizontal case were re-run
unchanged to confirm the fix does not disturb that branch. A diagonal
layout (screens separated on both axes) has no gap-free answer either way,
so `test_plan_capture_diagonal_layout_is_pinned_not_incidental` exists to
pin the horizontal-default choice as deliberate rather than leave it to
sort-order incidence, the same trap defect 12 itself was.

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
QT_QPA_PLATFORM=offscreen pytest -q      # 270 passed, about 2-3 seconds warm;
                                          # slower on the first run while the
                                          # bundled ffmpeg loads
```

On Windows the platform variable is unnecessary; `conftest.py` sets it.
