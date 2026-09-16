TA-246 — Quick Capture's saved image is sized in raw logical pixels, not the screen's real (DPI-scaled) resolution, so it doesn't match what was actually selected on screen

## Context

Found during T4 of the Launcher Evaluation Pass (2026-09-16): the tester
did a Quick Capture on the laptop display (their current primary/main
monitor), dragging and resizing a selection rectangle. Their report: the
pointer ended at the bottom-right corner of the selection rectangle, but
the captured image that came back was of a smaller, centered sub-region —
not what the on-screen rubber band appeared to cover.

This looked at first like it could be TA-223/TA-225's already-tracked
mixed-DPI coordinate problem, but TA-223/225 are both `unconfirmed —
plausible mechanism, no hardware measurement` (see
`docs/ta215-225-fix-brief.md`). Rather than guess again, the tester
re-ran the repro with `TESTASSIST_DEBUG=1` set (the opt-in logging
`python/debug_log.py` already ships specifically for this class of bug),
producing a real measurement instead of another "reportedly doesn't
work":

```
[2026-09-16 03:02:41] _start_capture: singleShot fired, calling _overlay.activate()
[2026-09-16 03:02:43] TA-223 drag move: globalPosition=(610, 189) screens=[(0, 0, 1536, 864), (1920, 0, 1920, 1080)]
...
[2026-09-16 03:02:44] TA-223 drag move: globalPosition=(1143, 604) screens=[(0, 0, 1536, 864), (1920, 0, 1920, 1080)]
[2026-09-16 03:02:45] TA-225 grab: dragged_rect=(609, 187, 535, 418) screen_geometries=[(0, 0, 1536, 864), (1920, 0, 1920, 1080)] plan_capture_result=[GrabPiece(screen_index=0, screen_local_rect=PySide6.QtCore.QRect(609, 187, 535, 418), dest=PySide6.QtCore.QPoint(0, 0))]
```

The drag itself is correct: origin (610, 189) to release (1143, 604)
matches the logged `dragged_rect` of `(609, 187, 535, 418)` almost
exactly, entirely on screen 0 (the laptop), and `plan_capture()` assigned
the whole thing to that one screen with no cross-screen split. So the
selection *math* — the part TA-223 and TA-225 both suspected — is not the
bug here.

The saved file is: `test-assist-1789520570.png`, measured directly
(`PIL Image.size`) at **535 x 418** — i.e. exactly the *logical*-pixel
drag rectangle, pixel for pixel.

That is the bug. The laptop screen's logical geometry, `(0, 0, 1536,
864)`, is almost certainly a scaled-down representation of a 1920x1080
physical panel at 125% OS scaling (1536 x 1.25 = 1920, 864 x 1.25 = 1080
exactly) — this matches the "125% laptop, 100% external" setup already
recorded in `docs/ta215-225-fix-brief.md` for this same machine. A
correctly DPI-scaled capture of a 535x418 *logical*-pixel selection on a
1.25-ratio screen should be **669 x 523** device pixels (535 x 1.25 =
668.75, 418 x 1.25 = 522.5). It came back at 535x418 instead — meaning
`_grab()`'s composite ratio was computed as 1.0, not 1.25, for this
capture.

Reading `python/screen_geometry.py` confirms exactly where that ratio
comes from:

```python
def composite_ratio(pieces: list[GrabPiece], screen_ratios: list[float]) -> float:
    ...
    return max(screen_ratios[piece.screen_index] for piece in pieces)
```

called from `capture.py` `_grab()` as:

```python
ratio = composite_ratio(pieces, [screen.devicePixelRatio() for screen in screens])
```

A ratio of 1.0 coming out of that means `QScreen.devicePixelRatio()`
returned `1.0` for the laptop screen at the moment of this capture —
despite its own logical geometry implying a real 1.25 scale factor. The
grab, scale and composite arithmetic downstream of that (`to_device_rect`,
`device_result_size`) all trusted that reported ratio and are not
themselves in question here — they did exactly what a 1.0 ratio tells
them to do.

**This also explains the tester's original visual complaint without
needing to invoke a coordinate/position bug at all:** a capture that is
genuinely 535x418 when the user's drag visually covered a 669x523-pixel
area on their actual (physical-pixel) screen will necessarily look like a
smaller, "centered" sub-region of what was selected once displayed back —
without a single coordinate anywhere being wrong. The drag tracking, the
rect math, and the screen assignment are all correct; only the DPR used
to size the final grab is not.

## 2026-09-16 (later) — rounding-policy hypothesis tested, does not reproduce here

A specific hypothesis was proposed: nothing in this codebase calls
`QGuiApplication.setHighDpiScaleFactorRoundingPolicy(...)` before
`QApplication(sys.argv)` (`main.py:210`, confirmed by grep — no hits), and
Qt's default rounding policy on Windows can round a non-integer scale
factor to the nearest supported step, which would turn a real 1.25 into a
flat 1.0 — exactly this ticket's symptom.

Tested directly against the real `ScreenshotOverlay.activate()` → `_grab()`
→ `composite_ratio()` code path (not a simulated click — a direct method
call with a hardcoded rect, since synthetic input is unreliable in this
class of environment, per `TA-228`'s own finding), on real Windows with
the real `windows` Qt platform (not offscreen), confirmed via
`SetProcessDpiAwareness` that the physical display is genuinely 1920x1080
at 125% (reported 1536x864 logical) — the same scale factor this ticket's
own repro measured, but **only one screen currently connected, no
external monitor**, so this does not reproduce the original two-screen
mixed-DPI hardware exactly.

The new `TA-246 devicePixelRatio at grab` log line (added at the
`composite_ratio()` call site in `capture.py`) read:

```
[2026-09-16 07:42:16] TA-246 devicePixelRatio at grab: [(0, 1.25)]
[2026-09-16 07:42:16] TA-239 grab piece: screen_index=0 local_rect=(100, 100, 400, 300) ratio=1.25 dest_rect=(0, 0, 500, 375) expected_grabbed_size=(500, 375) actual_grabbed_size=(500, 375)
```

`devicePixelRatio()` read `1.25` correctly — **without** the proposed fix.
Applying `setHighDpiScaleFactorRoundingPolicy(PassThrough)` and repeating
the identical repro produced an identical result (`1.25`, same saved
size). **The bug does not reproduce on this hardware at all, with or
without the fix** — not "the fix doesn't help," the misread was never
present to begin with here.

This neither confirms nor rules out the rounding-policy hypothesis. The
most likely explanation: the original report's hardware had *two* screens
at *different* scale factors connected simultaneously (125% laptop + 100%
external), and Qt's DPI-rounding defaults are known to behave differently
specifically under mixed-DPI multi-monitor configurations — a single
125% screen, which is all that was available for this pass, may simply
not trigger whatever the real mechanism is. **Needs re-testing on the
actual two-monitor mixed-DPI rig** before either confirming this fix or
moving on to the timing/race candidates below. The rounding-policy fix
itself was *not* applied to the codebase, since it could not be verified
to do anything on the hardware available — only the diagnostic log line
was kept.

## Change

Not yet decided — needs one of:

- Find why `QScreen.devicePixelRatio()` reports `1.0` for this screen at
  capture time when its own `geometry()` (1536x864 against an almost
  certain 1920x1080 physical panel) implies 1.25. Candidates worth
  checking: timing (is the overlay window's screen affinity/DPR settled
  by the time `_grab()` reads it, given `_start_capture()`'s existing
  `singleShot(220, ...)` delay before `activate()` — is there a
  similar race on the *read* side?), the app's DPI-awareness manifest ordering
  vs. window/screen creation, or a Qt/Windows quirk specific to a
  secondary/tool-flagged window (`_OverlayWindow` sets
  `Qt.WindowType.Tool`) not inheriting the primary display's DPR the same
  way a normal top-level window does.
- Once the real cause is found, decide whether the fix is at the
  `devicePixelRatio()` read itself, or whether `_grab()` needs a more
  reliable DPR source (e.g. reading it from the screen at `activate()`
  time instead of at `_grab()` time, or cross-checking against
  `geometry()` vs a known/expected physical resolution).

## Acceptance

- [ ] Root cause of the `devicePixelRatio() == 1.0` reading confirmed,
      not just worked around.
- [ ] A Quick Capture drag on the laptop screen produces a saved image
      sized at the real physical-pixel dimensions of the dragged
      selection (535x418 logical -> 669x523 device pixels for this
      screen's 1.25 ratio), verified by measuring the actual saved file,
      not just by reading the code.
- [ ] Re-run with `TESTASSIST_DEBUG=1` after the fix and confirm the
      `TA-225 grab` log line's `dragged_rect` and the saved file's actual
      pixel dimensions agree once the ratio is applied.
- [ ] Check whether this also affects the external monitor piece in a
      cross-screen selection (screen 1 here reports ratio via the same
      code path) — this repro happened to land entirely on screen 0, so
      the external monitor's ratio handling is untested by this evidence
      alone.

## Not in this issue

- TA-223 (selection rectangle jumping/resizing at a screen boundary
  during the drag itself) and TA-225 (capture producing no visible
  content in the laptop-as-secondary-above layout) — both still open,
  both about the *drag/assignment* math, which this evidence shows is
  working correctly in this repro. This ticket is about the *sizing* of
  the final grabbed image, a separate stage in the same pipeline. Worth
  revisiting whether TA-225's "no visible content" report shares this same
  `devicePixelRatio()` misread as its actual mechanism once that's
  understood, but not assumed here.
- TA-239 (seam at the join in a spanning two-screen capture) — unrelated,
  this capture didn't span screens.

## Provenance

- Tester's live evaluation, Launcher Evaluation Pass task T4, 2026-09-16:
  "you can clearly see that the capture area is not below the pointer...
  this occurs for both the floating and docked versions." Follow-up
  clarification: "i did a physical click and drag...i changed the size of
  the rectangle but tried to show how the pointer was not at right
  place. pointer ended in the bottom right of the capture region while
  the section captured was centered."
- Re-repro with `TESTASSIST_DEBUG=1` enabled per tester's request,
  2026-09-16 03:02: `history/debug.log` entries quoted above, and the
  resulting `test-assist-1789520570.png` measured directly at 535x418 via
  PIL.
- Mechanism (the ratio computation in `screen_geometry.py` and its call
  site in `capture.py`) confirmed by direct code read, not inferred from
  the log alone.
