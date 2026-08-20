# Changelog

All notable changes to Test Assist. Dates are the date of the change, not of a
release; only tagged versions appear as releases.

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
