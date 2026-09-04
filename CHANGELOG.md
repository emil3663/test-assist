# Changelog

All notable changes to Test Assist. Dates are the date of the change, not of a
release; only tagged versions appear as releases.

## [Unreleased]

### Fixed

- **Region capture, full-screen capture, recording and the launcher's own
  positioning all read `primaryScreen()` unconditionally** (GitHub issue #1).
  On a laptop with an external monitor, dragging a selection on the secondary
  display returned the matching area on the *primary* instead — the overlay
  is placed at the virtual desktop's origin, so its widget coordinates are
  not global coordinates whenever a screen sits left of or above the primary,
  which is negative on Windows and was being treated as global (0, 0).
  Recording had the identical bug and was not in the original report: a
  tester recording a repro on a secondary monitor got footage of the primary
  with nothing to hint at it until playback. Docking and positioning the
  launcher measured the primary's edge even when the launcher was on another
  screen. All six sites now resolve the actual screen(s) involved; a
  selection spanning two screens is composited from every intersecting
  screen rather than clamped to one, since silently returning less than the
  user selected is the class of bug this removes. The underlying geometry is
  pure functions over `QRect` values (`screen_geometry.py`), so negative-
  coordinate and mixed-size layouts are covered without a second monitor —
  the one thing that still needs real mixed-DPI hardware is whether the
  grabbed pixels come out the right *size*, tracked as Blocked (CAP-12).
  - **That fix was necessary but not sufficient.** Real two-monitor hardware
    proved the region-capture overlay never covered a second screen at all:
    `activate()` called `showFullScreen()` after `setGeometry()`, and
    `showFullScreen()` silently discards the requested geometry and sizes
    the window to fullscreen on *a* screen instead — a second screen was
    physically uncovered, not merely mis-grabbed once shown. The same
    diagnostic run confirmed the coordinate translation above was already
    correct. Fixed with plain `show()` (the window needs no fullscreen state
    to cover what it's told to), mouse positions read via `globalPosition()`
    throughout so the capture rect no longer depends on window geometry at
    all, `virtualGeometry()` instead of `availableVirtualGeometry()` so a
    taskbar can be selected, and any gap between mismatched screens excluded
    from the dimmed selection area rather than silently yielding nothing
    there. CAP-14 is the regression test.

### Added

- **The version now shows up without opening a dialog.** The editor's
  window title reads `Test Assist <version> — Editor`, and `help.html`'s
  header and footer show the version too — both taken from `__version__` at
  build time (`generate_version_info.py` now stamps `help.html` alongside
  `version_info.txt`), so there is no third place for the number to drift.
- **An About dialog**, reachable from the toolbar beside Help, with a "Copy
  details for a bug report" button that copies the version, OS name/version,
  and the full display layout — every screen's geometry and device pixel
  ratio. Issue #1 took a code read to diagnose because the report could not
  describe the reporter's monitor layout; pasting this would have answered
  the mixed-DPI question immediately.

### Changed

- **Recordings and capture history moved out of `~/.test-assist`.**
  `~/.test-assist/recordings` was undiscoverable on Windows — a dot-prefixed
  folder is a Unix convention Windows users do not look in — and moving it
  into the install folder instead, which looked like the obvious fix, would
  have made every recording get deleted by the documented update procedure
  ("close the app, download the zip, replace the folder's contents"). Split
  instead by what the files are: recordings and saved exports now live in
  `Documents\Test Assist\` (discoverable, backed up, untouched by an update),
  and capture history — an app-managed cache the app auto-prunes on every
  launch — lives in `%LOCALAPPDATA%\Test Assist\history` instead, since an
  auto-deleting folder must never sit where a user keeps things they'd miss.
  Both resolve through one new module, `paths.py`, rather than being built
  by hand in two places. A recording now offers an "Open folder" button once
  it finishes, so "where did it go" has a one-click answer regardless of
  which of the two outcomes (a finished mp4, or a kept frame sequence if
  encoding fell back) produced it.
  - `setOrganizationName("TestAssist")` is removed. Nothing in the app read
    it (`single_instance.py` already used its own hardcoded server name),
    and `QStandardPaths.AppLocalDataLocation` folds the organisation name in
    ahead of the application name, which would otherwise have produced
    `AppData\Local\TestAssist\Test Assist\history` for no reason.
  - A populated `~/.test-assist` from an earlier install migrates into the
    new locations once, automatically, the first time a build with this
    change runs. Best-effort and never fatal: v1.0.0, v1.1.0 and v1.3.0 are
    public downloads, at least one person outside this repo has real
    recordings sitting in the old location, and a broken migration must
    never be the reason the app fails to start. The old folder is left in
    place rather than risking a delete of anything that failed to copy.
  - The test isolation this depends on moved with it: `conftest.py` used to
    redirect `Path.home()`, which is what capture.py and editor.py built
    paths from directly; both now go through `paths.py`, so the fixture
    patches `paths.QStandardPaths.writableLocation` instead and asserts the
    redirect actually took effect, rather than assuming a patched seam still
    does anything.

## [1.3.0] — 2026-08-31

### Added

- **A manual "Check for Updates" button** on the floating launcher. Compares
  the running version against the latest GitHub release tag and, if newer,
  links to its release page — nothing is downloaded or installed
  automatically. Manual only, by design: no on-launch poll, no telemetry, and
  a short (~5s) timeout so a slow or absent network can never freeze the UI.
  Since the app is installed by unzipping, the result dialog says how to
  actually update: close Test Assist, download the zip, replace the folder's
  contents.
  - Comparison is now trustworthy by construction, not by having been
    corrected once: the version-tag fix above means `__version__` is exactly
    what CI already enforces the built binary reports.
  - Extends the `--selftest` mechanism (see below) to also report whether TLS
    is available, since Qt does not link it in — HTTPS depends on a separate
    plugin PyInstaller must bundle alongside it, and if that plugin is
    missing the update check would fail forever, indistinguishable from being
    offline. `build.ps1` and the release workflow now fail the build if TLS
    is unsupported in the frozen app; verified clean against a real
    PyInstaller build (backend: `schannel`).

### Changed

- **MP4 recording works in the packaged build now.** Assembly moved from an
  optional, lazily-imported `opencv-python` — never included in the packaged
  build, so a released copy of the app could only ever produce a JPEG frame
  sequence — to `imageio-ffmpeg`, a real dependency that bundles a standalone
  `ffmpeg` binary and is shipped with every build, source or packaged. The
  download grows by about 29 MB compressed to carry it. Recordings still fall
  back to the frame sequence rather than being lost if encoding ever fails —
  the dependency is missing, ffmpeg exits non-zero, or it times out.
- **The editor was rebuilt for volume use.** It was correct but slow to drive:
  no cursor feedback at all, handles that shrank to nothing when zoomed out, and
  a grab radius four times the size of the visible handle. Marking up one
  screenshot was fine; marking up forty was a fight.
  - **A shape's border is its grip.** One click on the border selects it and
    shows eight handles; dragging the border moves it. Interiors are
    click-through, so a rectangle drawn around a defect no longer blocks the
    marks inside it. A circle selects from its arc rather than its empty
    bounding-box corners, and an arrow from its shaft rather than the large empty
    box around a diagonal line.
  - **A text box works the other way round, deliberately.** Its border moves it;
    a single click inside it edits the words.
  - **Handles hold their size on screen.** The drawn and grab radii are divided
    by the zoom, so they are the same to the hand at 40% as at 250%.
  - **Edge handles.** Corners resize both axes; the four edge midpoints resize
    one, so width and height can be changed independently.
  - **The cursor says what a press will do** — move over a border, the matching
    diagonal or axis arrow over each handle, an I-beam inside a text box, a
    crosshair while a drawing tool is active.
  - **Shift** keeps the proportions on a corner resize, or locks a move to one
    axis. **Arrow keys** nudge by a pixel, Shift+arrow by ten. **Escape**
    abandons a drag in progress and restores the geometry.
  - Delete Selected and the three layer buttons are greyed out when nothing is
    selected, instead of offering four no-ops.
- Every drag is now computed from a snapshot taken when the press landed rather
  than by accumulating per-event deltas — which is what makes Shift-constrain and
  Escape possible, and removes any chance of drift over a long drag.

### Fixed

- **v1.1.0 shipped reporting itself as 1.0.0.** `__version__` in `main.py` was
  bumped for the release but `version_info.txt` — a second, hand-maintained
  copy that drives the Windows file properties on the built exe — was not, so
  `TestAssist-1.1.0-win64.zip` contained a binary whose file properties and
  `--version` output both said 1.0.0. The release verify step only checked
  that the output matched a version-shaped pattern, so it could not have
  caught this. `version_info.txt` is now generated from `__version__` at build
  time (`generate_version_info.py`, run from `build.ps1`) instead of hand-kept
  in step with it, the release workflow now asserts the built binary's
  self-reported version equals the git tag on an actual tag push, and a test
  pins the checked-in `version_info.txt` to `__version__` so the two cannot
  drift between releases again. Bumped to **1.2.0**.
- **MP4 encoding could fail in the packaged build even with ffmpeg bundled and
  working.** `imageio_ffmpeg.get_ffmpeg_exe()` validates the binary it finds by
  running `ffmpeg -version` as a subprocess without redirecting stdin; a
  process with no real stdin handle — which describes this app, built with
  `console=False` — can make that validation subprocess fail to start even
  though ffmpeg itself is perfectly runnable, so recording would silently and
  unpredictably fall back to a frame sequence. `capture.py` now locates the
  bundled binary directly instead of going through that check.
- **Moving or resizing an annotation was not undoable.** The drag path mutated
  the annotation in place without ever pushing an undo snapshot, so a misplaced or
  mis-sized shape could not be taken back — the only recovery was to delete it and
  draw it again. A snapshot is now taken once a drag passes the threshold, so
  a move or a resize undoes and redoes like any other edit.
- **Drags did not emit `annotation_changed`,** unlike every other mutating
  operation. Now emitted on release when the drag actually moved something.
  Nothing in the app connects to that signal yet, so this removes a trap rather
  than changing behaviour.
- **A wobbly double-click nudged the annotation.** Selecting on a single press
  means the opening press of a double-click arms a drag; a hand that wandered a
  few pixels between the two clicks left the annotation moved and an undo entry
  behind. Movement below a double-click slop threshold is now reversed when the
  second click arrives.
- **The in-app help described history pruning by file size.** It still said blank
  or corrupt snapshots under 5 KB are removed on startup; that proxy was replaced
  in 1.1.0 with a readability test, and small valid captures are kept.

### Removed

- The "selection is bound to double-click" known limitation, and the
  "not usable at volume" limitation that replaced it. Both are now false.

## [1.1.0] — 2026-08-21

### Fixed

- **The recorder held every frame in memory.** Measured at 7.92 MB per frame, so
  a one-minute recording held roughly 7 GB and would exhaust memory before you
  pressed stop. Frames are now scaled, encoded and written to disk as they are
  captured; the same 90 frames cost 4 MB instead of 711 MB. Added a three-minute
  cap and a dropped-frame counter.
- **History pruning deleted real captures.** Any history PNG under 5 KB was
  removed on launch, as a proxy for "blank or corrupt". A capture of a dialog or
  a form on a plain background compresses well below that, so genuine evidence
  was being deleted. Pruning now tests whether the file is a readable image.
- **The recorder crashed** when its frame counter and the files on disk
  disagreed, raising `IndexError` instead of finishing cleanly.
- **The test suite could destroy your capture history.** Constructing an editor
  triggers history pruning against the real `~/.test-assist`, so running the
  tests operated on your own captures. Every test now runs against a temporary
  home directory.

### Added

- **Browser sessions survive a refresh.** Image, annotations, undo/redo history
  and snapshots are stored in IndexedDB and restored on load, behind a versioned
  schema, with a restore notice and a control to clear it. IndexedDB rather than
  localStorage because one screenshot as a data URL is comparable to
  localStorage's entire budget.
- **`DESKTOP_TEST_PLAN.md`** — 91 ID-coded cases covering every desktop feature.
- **`DESKTOP_STABILITY_MATRIX.md`** — triage for all of them: 87 automated, 4
  blocked, and a plain statement of what offscreen testing does not prove.
- **`python/tests/test_functional.py`** — the automation for that plan. 108
  pytest tests in total, running in under two seconds.
- Six browser tests for session persistence, including a session written under
  an unrecognised schema and storage being unavailable entirely.

### Known limitations

- Recordings are capped at three minutes and scaled to 1280px wide; full
  resolution frames cannot be encoded inside the frame budget.
- Selection is bound to double-click for every tool, including Select. Recorded
  as an open question in `DESKTOP_TEST_PLAN.md` rather than changed silently.

## [1.0.0] — 2026-08-20

First tagged release. Both builds are feature-complete for the workflow they
claim: capture the screen, mark it up, export the evidence.

### Added

- **Packaged Windows desktop app.** `TestAssist.exe` with its own icon, built by
  a tagged-release workflow on a clean Windows runner and attached to the
  GitHub Release. No Python installation needed; pin it to the taskbar.
- **49 Playwright tests** for the browser build — an 8-test smoke suite that
  runs in CI on every push, and a 41-test regression suite run on demand.
- `STABILITY_MATRIX.md` — every test-plan case triaged Stable / Moderate /
  Blocked, with the reason and the caveats that a coverage count hides.
- Firefox screen capture, via a video-frame fallback for browsers without
  `ImageCapture`.
- Undoable annotation moves, and three tests covering packaging and file
  locations in the desktop suite.
- `--version` on the desktop build, so a build pipeline can prove the
  executable runs rather than assume it.

### Changed

- The published page is the working browser application. It previously served a
  launcher concept mock that labelled itself as one, which misrepresented a tool
  that worked the whole time.
- Recordings are written to `~/.test-assist/recordings/` instead of loose in the
  home directory.
- `TEST_PLAN.md` is at v1.2: 61 cases, 60 automated, 1 honestly marked blocked.

### Fixed

- Dragging a shape moved one corner and left the other, stretching it instead of
  moving it.
- Dragging a pen stroke wrote `NaN` coordinates into the annotation, which then
  reached the exported JSON.
- Snapshot ids were `Date.now()` alone, so two exports in the same millisecond
  collided and deleting one removed both.
- The Photo/Video toggle appeared to do nothing: a CSS rule overrode the
  `hidden` attribute, so both mode buttons rendered at once.
- Below 960px the floating launcher covered the whole toolbar.
- The published page returned 404 for `/favicon.ico` on every visit.

### Corrected documentation

Four claims in the docs were false and are now checked rather than asserted:
screen capture was listed as working in Firefox, the exported JSON `type` was
documented as `ellipse` when the code emits `circle`, drag-and-drop upload was
listed as unwired when it had worked for some time, and a browser-zoom
coordinate misalignment was listed as a known limitation when `getPos()` already
compensates for it.

### Known limitations

- The packaged desktop build records to a PNG frame sequence rather than MP4.
  MP4 needs `opencv-python`, which would add roughly 250 MB to the download; run
  from source with it installed if you want MP4.
- Browser build: annotations and snapshots do not survive a page refresh.
- No annotation numbering, PDF export, cloud save, or frame-by-frame video
  annotation in either build.
