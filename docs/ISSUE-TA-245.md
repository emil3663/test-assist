TA-245 — A recording's saved video is shorter than the on-screen timer showed, with no indication to the user

## Context

Found during T3 of the Launcher Evaluation Pass (2026-09-16): the tester
ran a recording, watched the docked timer count up to 11 seconds, stopped
it — and the saved `test-recording-1789517866.mp4` plays back at 9.47
seconds, not 11. The on-screen timer and the actual saved evidence
disagree about how long the recording was.

Confirmed mechanism, reading `python/capture.py`'s `FrameRecorder`
directly: frames are captured on a `QTimer` set to fire every
`1000 // _FPS` ms (`_FPS = 15`, so ~66.7ms), each tick calling
`_capture_frame()` (screen grab, scale, JPEG-encode, disk write — all
synchronous on the same timer callback). The final video is assembled by
`_encode_frames()` with a **fixed** `-framerate 15` passed to ffmpeg
regardless of how long the recording actually ran — so the output
duration is always exactly `frame_count / 15`, never `frame_count /
(actual average capture rate)`.

The numbers here confirm the mechanism exactly: `9.4667s x 15fps = 142.0`
frames — an exact match, so the video was encoded from precisely 142
captured frames. If the recording genuinely ran 11 real seconds (per the
on-screen timer, which is a separate, independent `QTimer` ticking once a
second — `_tick()`, `launcher.py`), then only 142 of the ~165 frames a
true 15fps capture over 11 seconds would need were actually captured — an
effective throughput of about 12.9 fps, roughly 86% of the nominal rate.
`FrameRecorder.dropped_frames` only counts frames whose `image.save()`
call itself failed (`capture.py` `_capture_frame()`'s `else` branch) — it
does **not** count a `QTimer` tick that simply never fires because the
previous `_capture_frame()` call (grab + scale + JPEG-encode + write) took
longer than the 66.7ms interval, which is a normal, silent way for a
single-threaded, non-reentrant Qt timer to fall behind under load. Nothing
surfaces that gap to the user or into the saved file's own duration
accounting.

**Net effect:** whenever screen-grab-and-encode can't keep up with 15fps —
plausible on this rig, given it's mid-testing with a multi-monitor HiDPI
overlay, several other apps open, and Test Assist's own overlay/editor
machinery running — the saved recording plays back *faster than real
time* and is *shorter* than what the user watched happen, with zero
indication anywhere (no dropped-frame warning, no duration mismatch
notice) that this occurred. For an evidence-capture tool, a recording
silently not representing the wall-clock time it claims to is a real
correctness problem, not just a cosmetic one.

## Change

Not yet decided — several independent directions exist and this needs a
choice, not just a bug fix:

- **Timestamp-based encoding instead of a fixed assumed fps.** Record a
  real timestamp per captured frame and pass a variable frame-rate /
  per-frame duration to ffmpeg (or duplicate frames to fill real gaps) so
  the *encoded* video's duration matches wall-clock time even when capture
  throughput dips, rather than silently compressing time.
- **Surface a dropped/throttled indicator to the user** (analogous to the
  existing `dropped_frames` property, which is already tracked but not
  shown anywhere) — at minimum, a warning if actual elapsed time and
  `frame_count / _FPS` diverge by more than some threshold when the
  recording is saved.
- **Both** — fixing playback-speed accuracy doesn't remove the value of
  telling the user their machine couldn't sustain the capture rate during
  that specific recording.

## Acceptance

- [ ] Root cause confirmed with instrumentation (log actual per-frame
      capture timestamps during a deliberately-loaded test recording,
      compare achieved fps against `_FPS`), not just accepted from this
      ticket's arithmetic alone.
- [ ] A decision is recorded on which direction(s) above are taken.
- [ ] After the fix, a saved recording's duration matches the wall-clock
      time the on-screen timer showed for that same recording, within a
      small, stated tolerance — verified by a real recording, not just a
      unit test of the encoding math.
- [ ] If full timestamp-accurate encoding is out of scope for now, at
      minimum the user is told when a recording's actual capture rate
      fell meaningfully short of `_FPS`, rather than the discrepancy being
      silent.

## Not in this issue

- `_MAX_SECONDS` (180s hard cap) and its own accounting — unaffected,
  unrelated to this.
- `TA-242`/`TA-243`/`TA-244` — same testing session, different mechanisms
  (launcher visibility during capture, click/focus handling, thumbnail
  badge visibility).

## Provenance

- Tester's live evaluation, Launcher Evaluation Pass task T3, 2026-09-16:
  "9.5 isn't good enough as you can see in the recording that the timer
  ran to 11s we have a mismatch in time here now."
- Mechanism and the exact frame-count arithmetic confirmed by reading
  `FrameRecorder` in `python/capture.py` directly and checking the actual
  saved file's duration (`ffprobe`, 9.4667s), not inferred from the report
  alone.
