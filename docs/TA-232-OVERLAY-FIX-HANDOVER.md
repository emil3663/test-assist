# Handover — fix the overlay DPI under-coverage (TA-232), sequenced with TA-231

**Date:** 2026-09-13
**Priority:** P1
**Confirmed:** twice — original measurement in `docs/TA-232.md`, reproduced independently today (see Evidence). Same seam, same pixel positions, both times.

## Symptom (user-facing)

On a mixed-DPI desktop, quick capture on the laptop panel (1536×864 logical @125%) cannot select roughly the right-most 20% and bottom-most 20% of the *actual physical screen* — including the laptop's own taskbar. The overlay doesn't dim there, doesn't respond to drags there, and nothing on screen explains why. It looks like the app ignored the drag. `CAP-21` and `CAP-22` cannot be run on the laptop at all for this reason — they are blocked, not failed.

## Root cause — measured, not inferred

The overlay is a single top-level window sized to `virtualGeometry()` **in logical units**. Qt gives one window one `devicePixelRatio`, and on a mixed-DPI desktop it takes the *primary* screen's DPR (1.0 here) — not each screen's own. So 1536 logical units render as 1536 **device** pixels on a laptop panel that is actually 1920 device pixels wide (1536 × 1.25 = 1920; 864 × 1.25 = 1080).

Confirmed by brightness measurement, twice:

| | first measurement (`TA-232.md`) | today's reproduction |
|---|---|---|
| vertical edge | x = 1536, step 27.45 → 39.70 | x = 1536, step 22 → 32 |
| horizontal edge | y = 864, step 27.00 → 39.00 | y = 864, step 27 → 39 |

Both are hard step functions, not gradients — the dimmed/selectable region ends abruptly at exactly the laptop's logical resolution. Covered area: 1,327,104 of 2,073,600 device pixels — **64%**. About 36% of the laptop screen, including its taskbar, is outside the overlay entirely.

**Already ruled out by measurement — do not re-investigate these:**
- **Stale geometry.** The same seam survives a full app restart with the display arrangement already settled. This is a permanent, reproducible boundary, not a caching artifact. (There is a *separate*, still-open stale-geometry question — see the dedicated section below — but it is not this.)
- **A v1.4.0 regression.** v1.3.0 had the same single-window-DPR exposure; v1.4.0 likely improved laptop coverage from 0% to 64% rather than breaking anything.
- **Position, screen count, or the `availableVirtualGeometry()` → `virtualGeometry()` change.** With both screens at 100%, the overlay correctly reached 3814 of 3840 virtual-desktop pixels. DPI scaling is the variable, nothing else.

## Fix scope (TA-232 itself)

- Likely shape: **one overlay window per `QScreen`**, so each window takes its own screen's DPR, rather than one window spanning the virtual desktop. Alternative: explicit DPR compensation on a single window. Pick one and record the reasoning in `TA-232.md`.
- Selection must keep working across screens once split — a drag started on one screen and finished on another must still yield one composited capture (no regression to `CAP-13`/`CAP-16`).
- **Out of scope:** how captured pieces are composited or scaled. That path is already correct (`DSP-05` measured 1.25× on the laptop against 1:1 on the external) — this ticket is only about what can be *selected*.

## TA-231 — decide sequencing before touching either

`TA-231` (P2, open): a spanning selection across screens of unequal height produces an unexplained black/unmapped band (measured: a 1536×216 unmapped block on the reference rig, where the L-shaped virtual desktop has no screen at all).

`TA-232.md` is explicit: **decide TA-232's approach before starting TA-231, or the two get solved twice.** If TA-232 is fixed via per-screen overlay windows, each overlay maps 1:1 onto a real display — there is no longer a single rectangle spanning the L-shaped virtual desktop, which removes TA-231's unmapped-region case as a side effect rather than needing its own overlay feedback.

**Recommendation for this pass:** implement TA-232 as per-screen overlay windows, then check whether TA-231's unmapped-region case still exists at all. If it doesn't, close TA-231 as resolved-by-side-effect (record that in `TA-231.md`, don't just delete it). If it does still exist in some form (e.g. a drag that starts on one per-screen overlay and needs to visually indicate "nothing here" over the gap before crossing to the next), implement TA-231's visual-feedback requirement in the same pass — it is cheap once you're already rebuilding overlay construction, and materially more expensive as a separate pass later. Either way, also make and record the black-vs-transparent decision `TA-231.md` calls for regarding unmapped-region export fill.

## Related cases that likely share this code path — verify explicitly, don't assume fixed

Do not close any of these as "fixed by TA-232" without re-testing. Log the result against each.

- **TA-223** (P1, open) — drag-selection rectangle resizes/jumps unexpectedly crossing a screen boundary (reported independently via DSP-03, DSP-07, DSP-08, possibly DSP-01). Current working hypothesis, not yet confirmed by hardware logging: Windows' per-monitor DPI awareness produces a rounding discontinuity in `event.globalPosition()` right at a mixed-DPI boundary. Since the TA-232 fix touches exactly this per-screen DPR handling, **log raw `event.globalPosition()` values against `QScreen.geometry()` for both screens during a real boundary-crossing drag once the fix lands**, before declaring this fixed too. If it turns out to already be resolved as a side effect of per-screen overlay windows, say so explicitly with the logged evidence — don't infer it.
- **DSP-08** (rescored FAIL, 2026-09-13) — a spanning capture's composite carried the wrong reference-line content instead of the intended rows (evidence: `auto area change.png`). Already flagged as possibly sharing TA-223's mechanism. Re-verify once TA-223/TA-232 are addressed, against the user's clarified intended start/end rows for the drag.
- **TA-233** (P3, open) — capture cursor/reticle doesn't track the region actually being drawn. Evidence so far is hand-annotated, not measured; flagged as a possible shared root cause with TA-223 pending coordinate logging. Same caveat as above.
- **CAP-21 / CAP-22** — currently blocked, not failed, on the laptop, specifically because their target area (taskbar; a toast notification) falls inside the ~36% dead zone this ticket describes. Both have only ever run and passed on the external. **Re-running both on the laptop is TA-232's own stated deliverable**, not a separate ticket — do it as part of this pass, not after.
- **CAP-19 / DSP-09** (full-screen capture on the laptop) — currently passes; output is normalised to DPR 1.0 correctly. TA-232 is explicit that composited/scaled output is out of scope — this is a regression check, not a target of the fix. Re-run anyway since it's cheap and touches adjacent code.

## The "stale geometry" question — separate from TA-232, still genuinely open

TA-232's own measurement rules out staleness as *its* cause. But there is a **different**, still-unresolved stale-geometry question, from the 2026-09-12 session handover (§8): on the **external** screen (DPR 1.0 — not the mixed-DPI mechanism this ticket fixes), CAP-21's taskbar clock was truncated on the first quick-capture attempt and captured in full only after an app restart.

That observation:
- has never been re-tested on a confirmed-correct build — it was confounded earlier this session by an unrelated wrong-build incident (`TA-235`, closed as not-a-bug), whose closing verdict explicitly flagged this as still needing a clean re-test;
- describes a *before/after restart* symptom, not a permanent step-function boundary — a different shape of defect than TA-232's, so **do not assume the TA-232 fix resolves it**;
- should be re-tested once this pass ships: a full quick capture over the external's taskbar clock, on a freshly confirmed v1.4.0 launch, with no restart in between. If it still truncates on the first attempt, that points to geometry being computed once at launch/first-use and cached rather than queried live — a genuinely separate defect, and it should get its own ticket rather than being folded into this one.

## Acceptance criteria

- [ ] Overlay dims and is selectable across the full laptop panel (1920×1080 device px), all four edges — a Print Screen of the live overlay shows no interior brightness step.
- [ ] A region covering the laptop's taskbar can be selected and captured (`CAP-21` re-run and passing on the laptop).
- [ ] A toast notification on the laptop can be captured (`CAP-22` re-run and passing on the laptop).
- [ ] A selection spanning both screens still produces a single composited image (no regression to `CAP-13`/`CAP-16`).
- [ ] Dragging a selection across the laptop/external boundary tracks the cursor smoothly, with no visible jump or resize at the crossing (`TA-223` acceptance criteria — verify on real hardware with logged coordinates, not by reading code).
- [ ] `DSP-08`'s composite carries the correct reference-line content for the intended spanning drag, once the intended rows are clarified.
- [ ] The capture cursor/reticle tracks the region actually being drawn (`TA-233`) — re-check once the above land; record whether it resolved as a side effect or needs its own fix.
- [ ] `TA-231`'s decision is recorded: does the chosen TA-232 approach remove the unmapped-region case entirely, or does the L-shaped-desktop band still need its own visual feedback? Implement whichever is still needed; record the black-vs-transparent export decision either way.
- [ ] Regression: `DSP-05` (1.25× laptop export vs 1:1 external) and `CAP-19`/`DSP-09` (full-screen laptop capture, normalised to DPR 1.0) still pass unchanged — composite/scaling code is explicitly out of scope for this fix.
- [ ] Once shipped, re-test the external-taskbar-clock stale-geometry question (2026-09-12 handover §8) on a confirmed build with no restart. If it still reproduces, file it as its own ticket rather than closing it here.

## Tests to add

- Per-screen covered-area assertion: for each connected screen, the overlay's covered area in device pixels equals that screen's real device resolution — exercised against a faked mixed-DPI layout using the existing `screen_geometry.py` synthetic-layout pattern, so it runs on single-screen CI.
- A drag spanning two screens still yields one composited capture, post-fix.
- If TA-223's boundary-crossing hypothesis is confirmed by hardware logging: a regression test for coordinate tracking across a DPI boundary, synthetic if Qt's DPI reporting can be faked the way the existing tests already do.

## Evidence

- `docs/TA-232.md` — original ticket and measurement.
- `docs/TA-231.md` — dependency note; read before starting either ticket.
- Today's independent reproduction: `raw screen shot of test assists overlay on laptop.png` (`Documents\Test Assist`) — measured boundary at x = 1536 (brightness 22 → 32) and y = 864 (brightness 27 → 39), pixel-exact match to `TA-232.md`'s original seam.
