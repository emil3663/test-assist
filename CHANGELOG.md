# Changelog

All notable changes to Test Assist. Dates are the date of the change, not of a
release; only tagged versions appear as releases.

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
