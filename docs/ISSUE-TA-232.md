TA-232 — The capture overlay under-covers a HiDPI secondary screen by the DPI ratio, making ~36% of it unselectable

## Context

On a mixed-DPI desktop (laptop 1536×864 @125%, external 1920×1080 @100%), the region-capture overlay only covers part of the laptop panel. The uncovered margin cannot be selected at all — no dimming, no drag response — and nothing on screen explains why.

Measured, twice, at identical pixel positions:

| | `docs/TA-232.md` (original) | reproduced 2026-09-13 |
|---|---|---|
| vertical edge | x = 1536, brightness step 27.45 → 39.70 | x = 1536, step 22 → 32 |
| horizontal edge | y = 864, brightness step 27.00 → 39.00 | y = 864, step 27 → 39 |

Both are step functions, not gradients — the covered region ends abruptly at exactly 1536×864, which is the laptop's *logical* resolution. 1536 × 1.25 = 1920 and 864 × 1.25 = 1080: the shortfall is the DPI ratio, exactly. Covered area is 1,327,104 of 2,073,600 device pixels — **64%**. The uncovered ~36% includes the laptop's taskbar, so `CAP-21` and `CAP-22` cannot run on the laptop at all (blocked, not failed — both pass on the external only).

**Mechanism**, read directly out of `python/capture.py`:

```python
# ScreenshotOverlay.activate(), capture.py:187-188
virt = QApplication.primaryScreen().virtualGeometry()
self.setGeometry(virt)
```

`ScreenshotOverlay` is one `QWidget`. Qt gives one top-level window a single `devicePixelRatio` — here, the primary screen's (1.0) — regardless of which screens the requested geometry spans. `virt` is correct (it spans the full virtual desktop in logical units), but the window painting it can only ever render 1 logical unit as 1 device pixel. On the external (DPR 1.0) that's exact. On the laptop (DPR 1.25) the window's actual on-screen extent stops at 1536×864 device pixels — 1536 logical units rendered 1:1 — instead of the panel's real 1920×1080.

**Already ruled out by measurement (`docs/TA-232.md`) — do not re-investigate:**
- Stale geometry: the same seam survives a full app restart with the display arrangement already settled.
- A v1.4.0 regression: v1.3.0 had the same single-window-DPR exposure.
- Position, screen count, or the `availableVirtualGeometry()` → `virtualGeometry()` change: at 100%/100% the overlay correctly reached 3814/3840 virtual-desktop pixels. DPI scaling is the only variable that predicts the failure.

## Change

**Files:** `python/capture.py` (`ScreenshotOverlay`, lines 135–380ish), `python/screen_geometry.py` (pure geometry helpers, unchanged — see Not in this issue), `python/tests/test_screen_geometry.py` and/or a new `test_capture.py`/`test_overlay.py` for the window-level test this defect is missing.

**Shape of the fix — pick one, record which in `docs/TA-232.md`, then implement it:**

1. **One `ScreenshotOverlay` window per `QScreen`**, each `setGeometry()`'d to that screen's own `.geometry()` (so each window inherits *that* screen's DPR rather than the primary's), shown together when `activate()` is called. This is the shape `docs/TA-232.md` already recommends.
2. Explicit DPR compensation on the current single window (scale the requested geometry by each region's own ratio before laying it out). More surgical, but keeps a subtlety: a single window still has one DPR, so this likely means manually drawing device-pixel-correct content rather than trusting Qt's logical-pixel model — probably more code, not less.

**If you take option 1 (recommended), the hard part is not window construction — it's `activate()`'s current assumptions elsewhere in the same class, all built around there being exactly one overlay window and one drag:**

- `_virtual_origin` (capture.py:167, set at capture.py:208) and `_to_local()` (capture.py:219–220) currently translate against one origin. Per-screen windows need this per-window, or a rethink of how local (rubber-band) coordinates are derived from the global drag rect.
- `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` (capture.py:222–258) assume the same window receives the whole drag. **A drag that starts on one screen and ends on another must still work** (this is explicitly required by TA-232's own acceptance criteria) — but Qt delivers mouse events per-widget, and a mouse crossing from window A's screen into window B's screen will not naturally keep delivering events to window A. The straightforward fix is `self.grabMouse()` on whichever window receives `mousePressEvent`, so that window keeps receiving move/release events regardless of cursor position; the other windows then need to redraw their own rubber-band feedback (or dimmed/selected region) in response to a shared, updated selection rect rather than from their own mouse events. Design this explicitly — don't discover it midway through the port.
- `_covered_region()` (capture.py:268–282) sums every screen's logical geometry into one region to exclude gaps from the dimmed area. Under a per-screen-window model this mostly collapses (each window *is* one screen, so the whole window is covered) — but see TA-231 below for what that does to the L-shaped-desktop case.
- `mouseMoveEvent`'s existing TA-223 debug logging (capture.py:239–242, using `debug_log.log`) must keep working per-window — don't drop it in the port, it's the only instrumentation TA-223 currently has for its own on-hardware repro.
- **Not in scope for this refactor:** the actual pixel grab and composite path (`_grab`, capture.py:292 onward, and all of `screen_geometry.py` — `plan_capture`, `composite_ratio`, `to_device_rect`). That output is already correct (`DSP-05` measured 1.25× on the laptop against 1:1 on the external) — this issue is only about what can be *selected*, not what happens after release.

**Test to add — this is the one that's currently missing, per `docs/TA-232.md`:** a window-level assertion, not just geometry math. `screen_geometry.py`'s existing functions are pure (`QRect`/`float` in, `QRect`/`float` out) and already have synthetic-layout coverage — mirror that pattern rather than inventing a new one. Concretely: extract whatever decides "what rect should the overlay for screen N occupy, in device pixels" into a pure function taking a list of screen geometries + DPRs (not live `QScreen` objects), so it can run offscreen on single-screen CI, and assert its output equals each screen's full device-pixel area for a faked mixed-DPI layout (e.g. the exact reference-rig numbers above: 1536×864 @1.25 and 1920×1080 @1.0).

## Acceptance

- [ ] `pytest python/tests/test_screen_geometry.py` and any new overlay/window test pass, including a synthetic mixed-DPI case (1536×864 @1.25 next to 1920×1080 @1.0) asserting full device-pixel coverage per screen.
- [ ] `python/tests/test_regressions.py` and `python/tests/test_functional.py` still pass unchanged (no regression to `CAP-13`/`CAP-16`/`DSP-05`/`CAP-19`).
- [ ] On real hardware (manual — cannot be scripted, no installed-app automation available for this tool, see `TA-238`): a region covering the laptop's taskbar can be selected and captured (`CAP-21` on laptop). A toast notification on the laptop can be captured (`CAP-22` on laptop). A Print Screen of the live overlay on the laptop shows no interior brightness step.
- [ ] On real hardware: a selection started on one screen and finished on the other still produces a single composited image.
- [ ] `docs/TA-232.md` updated with which fix shape was taken and why.
- [ ] `docs/TA-231.md` updated with a recorded decision: does this fix remove the L-shaped-desktop unmapped-region case entirely (per-screen windows leave no single rectangle to span it), or does it still need its own visual feedback? If it still needs it, implement TA-231's overlay-feedback requirement (`_covered_region()`-equivalent dimming distinction) in this same PR rather than a follow-up — it's cheap here, expensive later. Either way, make and record the black-vs-transparent decision for unmapped-region export fill that `docs/TA-232.md` and `docs/TA-231.md` both defer.
- [ ] `MULTI_DISPLAY_MANUAL_PASS.md` and `DESKTOP_TEST_PLAN.md`'s DSP-08 expected result is corrected per `docs/TA-231.md`'s note (name the unequal-height case explicitly rather than folding it into "no gap").

## Not in this issue

- **TA-223** (drag rectangle jumps/resizes crossing a screen boundary) — already instrumented (capture.py:239–242 logs raw `globalPosition()` + all screen geometries on every move) but not yet confirmed by an actual on-hardware boundary-crossing drag. That confirmation is a manual step for whoever has the hardware, not something this issue's code change should attempt to close. Do not remove or weaken this logging while refactoring; if the per-screen-window port changes how moves are delivered (see `grabMouse()` note above), keep the same log line firing from wherever the drag is actually tracked afterward.
- **DSP-08's rescore** (spanning composite carried the wrong reference-line content) — re-verify only after TA-223 is confirmed or ruled out; needs the user's intended start/end rows clarified first regardless.
- **TA-233** (capture cursor/reticle doesn't track the drawn region) — evidence is hand-annotated, not measured; possible shared root cause with TA-223, unconfirmed. Re-check after this lands; don't assume it's fixed.
- **The external-screen stale-geometry question** (2026-09-12 handover §8: CAP-21's taskbar clock truncated on first capture, full only after restart) — this is the *external* screen (DPR 1.0), not the mixed-DPI mechanism this issue fixes, and it's a before/after-restart symptom, not a permanent boundary. Never confirmed on a build known to be correct. Re-test after this ships; if it still reproduces, it's a separate issue (geometry cached at launch rather than queried live), not a TA-232 symptom.
- **CAP-20** (three-or-more-piece composite at a fractional DPR can leave a 1px gap/overlap) — already tracked separately as `TA-229`. Unrelated code path (`to_device_rect`), don't touch it here.

## Provenance

- `docs/TA-232.md` — original ticket, first measurement.
- `docs/TA-231.md` — dependency; its "decide TA-232's approach before starting TA-231" instruction is why this issue includes TA-231's decision in its own acceptance criteria rather than treating it as fully separate.
- 2026-09-13 reproduction: `raw screen shot of test assists overlay on laptop.png` (`Documents\Test Assist` on `desktop-jinunnr`), measured boundary at x=1536 (22→32) and y=864 (27→39) — pixel-exact match to the original ticket's seam, on a separately-confirmed build.
- `python/capture.py` read directly (lines 135–380-ish) to ground the mechanism and line references above, rather than relying on the original brief's older description (`docs/overlay-geometry-fix-brief.md` describes a now-fixed, different defect — `showFullScreen()` discarding geometry entirely — not this one).

---

**Process, per `docs/WORKING_AGREEMENTS.md`:** file this as a GitHub issue (title as above, carrying the `TA-232` identifier), work it on a branch, open a PR, and let the merge close the issue. Commit subjects follow `docs/CONVENTIONAL_COMMITS.md` — Conventional Commits with a body giving the why, the alternatives rejected (state which overlay-fix shape you chose and why the other wasn't taken), and what the change deliberately does not do (the grab/composite path, TA-223's confirmation, TA-233, TA-235's separate stale-geometry question). End the commit(s) with `Refs #N` while work is in progress and `Closes #N` on the one that satisfies the Acceptance section above.
