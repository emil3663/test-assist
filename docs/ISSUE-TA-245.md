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

**Decided, 2026-09-16: both directions, not a choice between them** — this
ticket's own framing ("for an evidence-capture tool, silently not
representing the wall-clock time it claims to is a real correctness
problem") rules out picking speed over accuracy, or accuracy without
telling the user when it was compromised.

- **Frame-duplication to backfill missed ticks, not a full timestamp/VFR
  re-encode.** Keep `_FPS = 15` and `_encode_frames()`'s fixed
  `-framerate 15` ffmpeg call exactly as they are — don't switch to a
  concat-demuxer/variable-duration encode, which is a bigger change to a
  working code path and has its own player-compatibility footguns. Instead
  fix it earlier, in the capture loop itself: track wall-clock elapsed
  time against how many nominal 66.7ms ticks *should* have produced a
  frame by now; whenever `_capture_frame()` falls behind (a tick's own
  grab+scale+encode+write took longer than the interval), duplicate the
  last successfully captured frame under the next sequential filename(s)
  to catch back up, rather than just letting the tick silently not fire.
  The saved video's duration then always matches `frame_count / 15`
  exactly, and `frame_count / 15` now always matches real elapsed time —
  both true at once, with no change to the encode step at all.
- **Surface it to the user when duplication had to compensate
  meaningfully.** Extend the existing `dropped_frames`-style tracking
  (currently only counts a failed `image.save()`, per this ticket's own
  Context section) to also count duplicated-due-to-lag frames. If that
  count exceeds a small threshold for the recording as a whole (exact
  number is an implementation choice — something that only fires for a
  real, sustained throttle, not one slow frame), surface it via the
  existing `_status_lbl` mechanism already used for
  "Recording stopped. Saving file…" — e.g. noting the capture rate
  dropped during the recording — rather than the saved file's timing
  accuracy being invisible the way it is today.

This fixes the duration mismatch itself (the bug as reported) and keeps
the existing "was anything actually wrong with this evidence" signal
honest, without touching `_MAX_SECONDS` or the encode pipeline's output
format/compatibility.

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

## 2026-09-16 (later) — implemented and measured

`_capture_frame()` now tracks wall-clock elapsed time
(`time.monotonic() - self._started_at`) against `frame_count`, and
backfills by copying the just-captured frame under sequential filenames
whenever a real tick fell behind — `_encode_frames()`'s fixed
`-framerate 15` call is untouched. `duplicated_frames` (a new property,
alongside the existing `dropped_frames`) counts them; `launcher.py`'s
`_on_record_finished()` appends a warning to `_status_lbl` when that
count reaches 15 (roughly a second's worth at 15fps — "a real, sustained
throttle, not one slow frame," per this doc's own Change section).

**Measured, not just accepted from the arithmetic** — a deliberately-
loaded scenario, `time.monotonic()` mocked so the numbers are exact
rather than machine-dependent: 3 ticks arrive on schedule, then one tick
is deliberately delayed a full simulated second (the same class of
stall this ticket's own Context section describes: a single capture
taking far longer than its 66.7ms budget).

| | frame_count | duplicated_frames | saved duration | real elapsed |
|---|---|---|---|---|
| **Before this fix** (naive tick count) | 4 | — | 4/15 = **0.267s** | 1.067s |
| **After this fix** | 16 | 12 | 16/15 = **1.067s** | 1.067s |

Saved duration matches real elapsed time within one frame interval
(`1/15s`), confirming the fix directly rather than by re-deriving the
arithmetic. `debug_log` now carries a `TA-245 backfilled N frame(s)`
line at the moment a backfill happens and a `TA-245 recording summary`
line on save (elapsed, frame_count, duplicated, dropped, achieved fps),
so a real hardware repro can read back exactly what happened, the same
standard this ticket's own Context section (an `ffprobe` measurement,
not a guess) already set.

Two new tests in `test_functional.py` cover the backfill logic directly
(and that a recording which never falls behind gets no padding at all),
two in `test_regressions.py` cover the `_status_lbl` warning crossing
and staying under the threshold, one covers the instrumentation log
lines existing and carrying real numbers. 391 tests pass.
