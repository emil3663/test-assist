TA-239 — A spanning capture across mixed-DPI screens leaves a ~5px seam line at the join, cutting into content on both sides

## Context

A drag spanning the laptop (1536×864 @125%) and external (1920×1080 @100%) screens produces a single composited image, as required — but the join between the two pieces isn't clean. Measured on `test-assist-1789320131 laptop to external.png` (`Documents\Test Assist`, captured against the TA-232-fix build, 2026-09-13):

- The reference text on the laptop side reads `...9LAPTOP LAP` — cut off mid-word right at the boundary.
- Immediately after it, a vertical band sits before `1EXTERNAL` begins.

Pixel measurement, not a visual impression: scanning column brightness across the full 52px height, columns **x=1895–1899** (5px wide) are **uniform top-to-bottom** — e.g. column 1897 is a flat 157 at every row — where every neighboring column (background or text) varies between ~39 (background) and ~255 (text stroke) depending on row. A letter glyph or a plain background gap both vary by row; a solid, full-height, single-brightness column across 5px does not occur naturally in either. This is a real inserted seam, not a rendering artifact of viewing the image at the wrong scale.

**What this issue is not:**

- **Not** the reference-row content question DSP-08 was blocked on. That question is resolved as of this same test run: the image's content was confirmed to be exactly what was selected across both screens, for the first time. This issue is about the join itself, on top of that.
- **Not** the "auto adjust" behavior reported while dragging *across* the seam mid-drag (the selection rectangle changing as the cursor crosses the screen boundary). That's `TA-223`'s territory — already instrumented, still needs on-hardware confirmation — and is about drag-time behavior, not the exported image. Do not conflate the two; this issue is scoped to the static artifact left in the saved file after the drag ends.

**Mechanism — traced, not yet nailed down.** The composite path is `screen_geometry.py`'s `plan_capture()` / `composite_ratio()` / `to_device_rect()`, called from `capture.py::_grab()` (all explicitly untouched by TA-232 — that issue was scoped to what could be *selected*, not the grab/composite path).

```python
# screen_geometry.py, plan_capture() — horizontal-packing branch
raw.sort(key=lambda item: item[2].left())
...
for index, geometry, intersection in raw:
    local = to_screen_local(intersection, geometry)
    dest = QPoint(x_cursor, intersection.top() - top_of_bounding_box)
    pieces.append(GrabPiece(index, local, dest))
    x_cursor += intersection.width()          # logical pixels
```

```python
# screen_geometry.py
def to_device_rect(dest, local_size, ratio):
    return QRect(round(dest.x() * ratio), round(dest.y() * ratio),
                 round(local_size.width() * ratio), round(local_size.height() * ratio))
```

For a two-piece horizontal case, the second piece's device-pixel `dest.x` is `round(x_cursor * ratio)` where `x_cursor` equals the first piece's own logical `intersection.width()` — the exact same value, multiplied by the exact same shared `ratio` (`composite_ratio()`'s max of the two screens' DPRs), that produces the first piece's own device *width* in `to_device_rect()`. On paper these should land edge-to-edge with no gap regardless of rounding, because both sides of the join go through the identical `round(width * ratio)` computation.

That the math traces clean and a seam still shows up on hardware means the cause is somewhere this trace doesn't reach — candidates:
- ~~The laptop's real DPR isn't exactly `1.25`~~ **Ruled out, 2026-09-15.** The `round(width * ratio)` identity that makes piece0's device width equal piece1's device x-offset holds for *any* ratio value, not just clean ones — both sides call the exact same expression with the exact same operands, so they cannot diverge regardless of what the real hardware DPR turns out to be. See below.
- ~~The coordinate math (`plan_capture`/`to_device_rect`) has a rounding bug~~ **Ruled out, 2026-09-15.** See below — both by an existing test and a new, more adversarial one.
- `screen.grabWindow()`'s returned pixmap doesn't measure exactly `local.size() * ratio` device pixels on this hardware — `to_device_rect()` assumes it does but nothing asserts it. **Still open** — needs a real hardware run (instrumentation now in place, see below).
- `QPainter.drawPixmap()` blends or antialiases at the destination rect's edge even when two dest rects are nominally adjacent. **Still open** — could not be exercised in this pass (no root/display access to run an offscreen Qt paint test); needs either a real hardware run or a properly provisioned Qt CI environment.

### 2026-09-15 — coordinate math conclusively cleared

Two independent things, done before touching the deployed build:

1. **`test_device_pieces_tile_the_result_without_gap_or_overlap` (already in the suite, pre-dates this issue)** already proves the two-piece case is gap-free by construction, with the exact identity reasoning used above in its own docstring. It just hadn't been connected to this issue explicitly — it uses one drag position, at intersection widths (512/488) that happen to divide cleanly by 1.25.
2. **New test added: `test_TA_239_two_piece_join_holds_at_random_non_round_widths`** (`python/tests/test_screen_geometry.py`) — 200 random left/right splits across the laptop/external boundary, at both 125% and 150%, including 1px slivers at either end. Every trial: exact edge match, 0px gap, 0px overlap. Verified by direct execution (`python3 -c "...test function..."`) in this session — `pytest` itself could not be run here (see below), but the test's own logic executes cleanly against the same `screen_geometry.py` code the deployed build uses.

This satisfies Acceptance criterion 2 below and rules out the coordinate math entirely, for any DPR value — not just the reference rig's `1.25`. The remaining two candidates (`grabWindow()`'s actual returned size, `QPainter.drawPixmap()`'s compositing behavior) are about real Qt rendering, not pure arithmetic, and cannot be settled without either real hardware or a full Qt display environment.

**Instrumentation added:** `capture.py::_grab()` now logs, per piece, `local_rect`, `ratio`, the computed `dest_rect`, the *expected* grabbed size (`round(local.size() * ratio)`), and the *actual* `grabbed.width()`/`grabbed.height()` Qt returns — tagged `TA-239 grab piece`, gated the same way as the existing `TA-223`/`TA-225` logging (`TESTASSIST_DEBUG=1`). This directly answers Acceptance criterion 1, but only once exercised on hardware: **not yet in the deployed build** (`b77ce50a`) — needs a rebuild + redeploy before a real two-screen drag will produce this log line.

**Environment note:** this session's shell (a sandboxed Linux VM with the repo mounted, no root) can run `screen_geometry.py`'s pure logic directly (it only imports `PySide6.QtCore`), which is how the new test was verified — but cannot run the actual `pytest` suite (`conftest.py` imports `QtGui`, which needs `libEGL.so.1`, not installed and not installable without root) or any real Qt rendering/paint test. Whoever next has a real dev machine or CI with Qt fully available should run `pytest python/tests/test_screen_geometry.py -k TA_239` to confirm in the normal way.

## Change

**Files:** `python/screen_geometry.py` (`plan_capture`, `to_device_rect`, `composite_ratio` — read, unmodified: the math is proven correct, so it doesn't need changing), `python/tests/test_screen_geometry.py` (new test added, 2026-09-15), `python/capture.py` (`_grab`, ~line 505 — instrumentation added, 2026-09-15).

**Investigate before fixing — this is not yet a diagnosed bug, only a measured symptom:**

1. Add a temporary instrumentation path (mirror the existing `TA-225` pattern already in `_grab()` — `debug_log.log(f"TA-225 grab: ...")`) that logs each piece's `local.size()`, the `ratio` used, and the resulting `to_device_rect()` output for a real two-screen drag. Compare the logged right edge of piece 0 against the logged left edge of piece 1 directly, on hardware, rather than by hand-tracing the formula as above.
2. Check what `screen.devicePixelRatio()` actually reports on the reference rig at the moment of grab — confirm it's exactly `1.25` and not an approximate value Qt rounds for display purposes elsewhere.
3. If the dest rects log as adjacent but the saved PNG still shows a seam, the gap is being introduced by the paint step itself (`drawPixmap`/`QPainter` compositing mode), not the arithmetic — that points at a different fix entirely (e.g. an explicit `CompositionMode` or drawing pieces back-to-front with a 1px overlap).

**Once the actual mechanism is confirmed, fix it there** — this brief deliberately stops short of prescribing the fix, since the arithmetic trace above didn't find one and guessing at a patch without reproducing the exact failing case first risks the same "should be fine because..." gap this project's own verification discipline exists to catch.

## Acceptance

- [x] A logged (or test-asserted) two-piece mixed-DPI grab shows the first piece's device-pixel right edge and the second piece's device-pixel left edge are the same value, or the investigation identifies exactly where they diverge. — **Test-asserted, 2026-09-15**: the coordinate math is proven to always match (see above); the instrumentation for the *rendering* side (`grabWindow`/`drawPixmap`) is now in place but not yet run against a rebuilt deployed binary.
- [x] A new test in `python/tests/test_screen_geometry.py` or `test_capture.py`, using synthetic (non-round) intersection widths — not just the reference rig's convenient exact numbers — asserts adjacent pieces' device rects share an exact edge. Convenient round numbers (1536×1.25=1920 exactly) can hide a rounding bug that a partial-screen drag would expose. — **Done, 2026-09-15**: `test_TA_239_two_piece_join_holds_at_random_non_round_widths`, 200 random trials × 2 ratios, all exact.
- [ ] On real hardware: a spanning capture across the laptop/external boundary, saved and opened at full zoom, shows no full-height single-color column at the join. — still open; needs a rebuild with the new instrumentation, redeploy, and a fresh hardware drag.
- [ ] Whatever the root cause turns out to be, it's written down in this file's own resolution section — including if it turns out to be a `QPainter` compositing detail rather than the coordinate math, since that changes where future mixed-DPI compositing work should look first. — narrowed to two candidates (see above), not yet down to one.

## Not in this issue

- **TA-223** (drag rectangle behavior *while crossing* the screen boundary, mid-drag) — separate, already-tracked, still needs on-hardware confirmation. This issue is about the static output file, not drag-time behavior.
- **DSP-08's reference-row content** — confirmed correct in the same test run this issue's evidence comes from. Nothing to re-open there.
- **TA-231** (unmapped region between screens of unequal height, filled transparent) — a different geometry entirely (an L-shaped virtual desktop gap), already resolved as a side effect of TA-232. This issue is a side-by-side join on the axis `plan_capture()` actually packs, not an unmapped region.
- **TA-229** (three-or-more-piece composite seam/gap at a fractional DPR) — already its own ticket, same code (`to_device_rect`), but a different N-piece scenario. Worth revisiting together once either is diagnosed, but don't merge the tickets pre-emptively.
- **TA-232's overlay-window geometry** — already fixed, unrelated code path (selection, not compositing).

## Provenance

- `test-assist-1789320131 laptop to external.png` (`Documents\Test Assist`, `desktop-jinunnr`) — the source evidence, captured against the TA-232-fix build.
- Measured via a per-column brightness scan (Python/PIL) across the image's full height: uniform-brightness columns at x=1895–1899, distinct from both background (39) and text-stroke (255) variation in every neighboring column.
- `python/screen_geometry.py` and `python/capture.py::_grab()` read directly to trace the compositing math above; the trace did not find a rounding explanation, which is itself the finding motivating the "investigate before fixing" framing of this brief.
- 2026-09-15: `test_TA_239_two_piece_join_holds_at_random_non_round_widths` added and executed directly (200 trials × 2 ratios, all exact) — confirms the hand-trace above holds under adversarial input, not just the one convenient example. `capture.py::_grab()` instrumented with a `TA-239 grab piece` debug-log line for the still-open rendering-side question. Neither change is in the currently deployed build (`b77ce50a`) yet.

---

**Process, per `docs/WORKING_AGREEMENTS.md`:** file as a GitHub issue carrying the `TA-239` identifier, work on a branch, open a PR, merge closes the issue. Commit subjects follow `docs/CONVENTIONAL_COMMITS.md`. Since this brief's own Change section is an investigation plan rather than a prescribed fix, expect at least one commit that only adds instrumentation/tests and records findings before any behavior changes — `Refs #N` on that one, `Closes #N` only once the Acceptance section is actually met.
