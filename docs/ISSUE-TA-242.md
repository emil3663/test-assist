TA-242 — The floating/docked launcher is not excluded from Test Assist's own screen recordings

## Context

Found during the Launcher Evaluation Pass's T2 task (2026-09-16), testing the
`ui-polish` launcher rebuild's recording flow. The launcher widget stays
100% visible on screen for the entire duration of a recording — by design,
so the Stop button stays reachable — but nothing excludes the widget's own
on-screen area from what actually gets captured. The result: the launcher
itself appears inside the user's own recording, occluding whatever part of
the screen it happens to be sitting over.

Confirmed by reading the code, not just observed: still capture and video
capture share the same underlying primitive, `QScreen.grabWindow(0)` — a
full virtual-desktop grab with no window exclusion (`ScreenshotOverlay._grab()`,
`capture.py:318`/`:339` for stills; `FrameRecorder._capture_frame()`,
`capture.py:449`, called every frame on a `QTimer` from `FrameRecorder.start()`,
`capture.py:410-421`, for video). Neither path filters the launcher's own
window out of the grabbed frame.

Launcher visibility during a recording is controlled by
`FloatingLauncher._start_recording()` (`launcher.py:711-719`) and
`_refresh_recording_ui()` (`launcher.py:582-624`) — both only toggle which
buttons/rows are shown (swap Capture for Stop, show the running timer) and
never call `self.hide()`, `setWindowOpacity()`, or minimize the window. This
is presumably deliberate (an invisible Stop button would be worse), but the
side effect — the widget landing in the recorded footage — doesn't appear to
have been considered as its own problem.

## Change

Not yet investigated or decided. Candidate directions, none confirmed or
ruled out yet:

- Exclude the launcher's own window rectangle from each captured frame
  (crop/mask it out of the composite after the grab, rather than hiding the
  window itself) — keeps Stop clickable and visible to the user while
  keeping it out of the recorded output.
- Temporarily reposition the launcher to a screen corner / off the active
  capture region for the duration of a recording, if a capture region is
  known ahead of time (may not apply to full-screen recording).
- Some OS-level "exclude this window from screen capture" mechanism, if one
  exists that Qt/Windows exposes and that Test Assist could opt into for its
  own window specifically (worth checking before assuming a manual
  crop/mask is the only path).

Whichever direction is taken, do not regress the requirement that Stop
remains visible and clickable throughout the recording.

## Acceptance

- [ ] Root cause confirmed via the frame-capture code path above (or a
      different mechanism, if this investigation finds one).
- [ ] A recording no longer includes the launcher widget's own on-screen
      area in its captured frames — OR an explicit decision is recorded that
      this is acceptable/out of scope, with reasoning, rather than left
      silently unaddressed.
- [ ] Stop stays reachable (visible and clickable) for the whole recording,
      regardless of which direction is taken.
- [ ] Still-capture behavior (region/full-screen screenshots) is unaffected
      — this issue is about the video-recording path specifically.

## Not in this issue

- TA-215's recording feedback (icon swap, running timer) — already working,
  unaffected by this.
- The separate double-click-to-stop finding from the same T2 session — see
  `TA-243`.
- History thumbnail play-badge behavior — already implemented (commit
  `a7a465f`), not part of this finding.

## Provenance

- Tester's live evaluation, Launcher Evaluation Pass task T2, 2026-09-16:
  "the record button did change to a stop recording button but the whole
  floating widget was still 100% visible so i missed a section of my
  screen not sure if this is something we want to discuss."
- Mechanism confirmed by reading `python/capture.py` and `python/launcher.py`
  directly on the `ui-polish` worktree, not inferred from the report alone.
