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

**Decided, 2026-09-16:** use Windows' `SetWindowDisplayAffinity` with
`WDA_EXCLUDEFROMCAPTURE` on the launcher's own HWND, toggled on for the
duration of a recording and back to `WDA_NONE` when it stops. Rejected the
other two candidates:

- Per-frame crop/mask — ruled out. Requires recomputing the launcher's
  screen rectangle every frame (it can move/dock mid-recording) and
  reprocessing every captured frame; `WDA_EXCLUDEFROMCAPTURE` does the same
  job once, at the compositor level, for free.
- Temporary reposition — ruled out per the ticket's own note: doesn't apply
  to full-screen recording, and would make the widget visibly jump on
  screen during recording, which is worse than the current bug.

`WDA_EXCLUDEFROMCAPTURE` (not the older `WDA_MONITOR`, which blacks the
window out in capture instead of showing what's behind it) is built for
exactly this case: the window stays visible and clickable on the physical
display for the user, but is excluded from `BitBlt`/DWM-composited capture
surfaces — which is what `QScreen.grabWindow(0)` reads from — so a
recording shows whatever is behind the launcher instead of the launcher
itself. Still-image capture is untouched, per this ticket's own acceptance
bar: apply the affinity change only around `_start_recording()` /
`_stop_recording()` (`launcher.py:739`/`:750`), never around the
screenshot path.

Implementation notes:
- Get the HWND via `int(self.winId())`; call via `ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` (`WDA_EXCLUDEFROMCAPTURE = 0x11`, `WDA_NONE = 0x0`).
- Requires Windows 10 2004+. Check the call's return value (nonzero on
  success per the Win32 API); if it fails (older Windows, or any other
  reason), log via `debug_log.log(...)` and continue recording normally —
  the launcher being visible in the recording is the pre-existing
  behavior, not a new failure, so this must never block or crash a
  recording.
- Apply/clear only the launcher's own top-level window. If the app has more
  than one top-level widget that could be visible during recording (e.g. a
  docked vs. floating variant is the same window either way per the
  existing dock/float code — confirm this before assuming a single call
  site covers both).
- Set the affinity back to `WDA_NONE` on stop, not left excluded — the
  launcher should behave normally (including being screenshot-able) once a
  recording isn't active.

Whichever direction is taken, do not regress the requirement that Stop
remains visible and clickable throughout the recording.

## Acceptance

- [ ] Root cause confirmed via the frame-capture code path above (already
      done — see Context).
- [ ] `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` is applied to the
      launcher's HWND for the duration of a recording and reverted to
      `WDA_NONE` when it stops, on both the hotkey-triggered and
      button-triggered stop/start paths.
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
