# Session handover — 2026-09-12

**Scope:** TA-204 multi-display pass against released v1.4.0, on the two-monitor rig.
**Method:** every result below was measured (pixel dimensions, glyph heights, brightness
step positions) rather than judged by eye. Where something was not measured, it says so.
**Status:** pass part-run and paused. Nothing outstanding is time-sensitive.

---

## 1. Rig, confirmed

Test Assist's own About dialog (DSP-17) reports:

```
Screen 0: 1920x1080 at (0, 0),     DPR 1.0    external, primary, 100%
Screen 1: 1536x864  at (-1920, 0), DPR 1.25   laptop, 125%
```

`scripts/preflight.ps1` agrees. Earlier doubt about whether the preflight's layout line
was a DPI-unaware artifact is resolved: Qt reports the same numbers, so the line is safe
to record in `SMOKE_TEST.md`.

Consequence worth carrying forward: the laptop spans x -1920..-384 and the external
starts at 0, so **384 logical units of the virtual desktop belong to no display.** This
is the geometry behind TA-231.

## 2. Measured results

| Case | Result | Evidence |
|---|---|---|
| DSP-03 | PASS | laptop region capture reads LAPTOP |
| DSP-05 | **PASS** | laptop heading 30px vs external 24px = **1.25 exactly** |
| DSP-06 | **PASS** | at matched 100%, 24px vs 24px = **1.00**; both exports 1920x1080 |
| DSP-08b | PASS | spanning capture 3814x232, no seam; 7px offset is content, not misalignment |
| DSP-17 | PASS | geometry block above |
| CAP-21 (external) | PASS | taskbar captured including full clock |

**DSP-05 and DSP-06 corroborate each other.** The external stayed at 24px throughout
while the laptop moved 30 -> 24 as its scale moved 125% -> 100%. One variable changed and
the capture tracked it exactly. That is better evidence for the HiDPI fix than either
case alone, and it is worth citing that way in `SMOKE_TEST.md`.

**The DSP-08b caveat matters for anyone re-running it.** The 7px vertical offset between
halves is present in the two *separately captured* full-screen images too (laptop heading
row 458, external 451). It is where the content sits, not a compositing error. Scoring it
as a failure would be wrong.

## 3. Defects found

- **TA-232** (`docs/TA-232.md`, P1) — the capture overlay covers only 1536x864 of the
  laptop's 1920x1080 panel. ~36% of the screen, including its taskbar, is unselectable.
  Confirmed on a fresh launch; stale geometry and a v1.4.0 regression both ruled out.
- **TA-231** (`docs/TA-231.md`, P2) — a spanning selection across screens of unequal
  height necessarily covers unmapped area, and the resulting fill arrives unexplained.
  **Premise now confirmed** by the geometry in section 1.
- **TA-217** gains detail: with Test Assist's own About dialog open, quick capture *and*
  the global Alt+P / Alt+Shift+P / Alt+V hotkeys are all dead. Qt modals run a nested
  event loop, so the hotkey handler never reaches the launcher. **This also qualifies
  LCH-13**, which assumes the hotkeys always fire. Note the irony for the ticket: the
  About dialog holds exactly the diagnostic block a bug report wants, and the tool cannot
  capture it. Copy details is the workaround.

## 4. Uncommitted work

- `docs/TA-231.md` — written, **not yet committed**. Commit message drafted in chat.
- `docs/TA-232.md` — written, **not yet committed**. Commit message drafted in chat.
- `scripts/preflight.ps1` — untracked. Should be committed; it is now a standing part of
  the pass procedure. **ASCII only, deliberately** — the header comment explains why, and
  that constraint must survive future edits.
- `docs/LAUNCHER_EVALUATION_PASS.md` — untracked.

## 5. Documentation corrections outstanding

1. **`docs/VERIFICATION_2026-09-09.md` section 4 carries a false finding** about browser
   test counts. It claims a discrepancy between README and the suite. There is none: the
   runner reports 47 regression tests and the README is right. The error came from
   counting `test()` calls by grep, which misses parametrised tests —
   `regression.spec.ts:487:9` is one `test()` in a loop yielding 7. **This retraction has
   been outstanding the longest of anything here.** Add alongside it the convention that
   caused it: *test counts are measured with the runner, never by grepping.*
2. **v1.4.0 GitHub release notes** do not mention the taskbar behaviour change
   (`availableVirtualGeometry()` -> `virtualGeometry()`). The CHANGELOG does. Users read
   the release page, so in practice a user-visible change shipped unannounced. Decide:
   add it openly with an "added after publication" note, or fold it into 1.5.0's notes.
3. **`docs/coord_probe.py`** still calls `availableVirtualGeometry()` and
   `showFullScreen()`. It is a *diagnostic* script, so it now reports geometry computed
   with superseded APIs — wrong answers about the exact subsystem it exists to
   investigate. Needs a ticket.
4. **Known Limitations item 1** ("live display changes are untested") should be revisited
   once section 8's observation is settled.

## 6. Waiting on Code

**The packing question, and it gates TA-231.** Code described `DESKTOP_TEST_PLAN.md`
CAP-16/17 as covering "a gap between screens, which packing closes to zero". If the
v1.4.0 capture path really does reposition pieces to eliminate inter-screen gaps, that is
precisely what TA-231 argues must never happen, and it already ships. Then TA-231's
premise is wrong and the ticket needs rewriting — the question becomes whether packing is
correct, not whether to add feedback. **Answer this before anyone starts TA-231.**

## 7. Decisions waiting

- **TA-232's approach must be chosen before TA-231 is started.** If the fix is one overlay
  window per `QScreen`, each overlay maps 1:1 onto a real display, no single rectangle
  spans the L-shaped desktop, and TA-231's case disappears as a side effect. Solve the
  geometry once.
- **`FrameRecorder.start(screen=None)`** defaults to `primaryScreen()` — the original
  defect, waiting for a second caller. Make `screen` required.
  `test_recorder_start_defaults_to_the_primary_screen_when_none_is_given` must be
  **deleted**, not adapted; it asserts the behaviour being removed. **Keep `test_REC_09`**,
  which is a genuine regression guard.
- **TA-230 (A)/(B)** — cherry-pick the hotkey mitigations to `main`, or let them arrive
  with PR #19 in 1.5.0. Decide it rather than letting it default by inaction.
- **PR #19** — run `docs/LAUNCHER_EVALUATION_PASS.md` and record the verdict.
- **PR #9 macOS** — supported, or "runs from source".
- **1.5.0 decision record** — does not exist yet; write it once #19 and #9 are called.

## 8. One thing not explained

CAP-21's first attempt on the external truncated the taskbar clock; after an app restart
the same action captured it in full. The external is DPR 1.0, so TA-232's mechanism does
not account for it. Two possibilities, not separated: the app was holding geometry cached
from before the external was connected, or the first drag simply fell short.

If it is the former, **there is a second defect** — a display change not taking effect
until restart — and it would be the most user-facing thing found tonight, since nobody
restarts their capture tool after plugging in a monitor. Worth a deliberate test: with the
app running, connect or rescale a display, then check whether the overlay picks it up.

## 9. Pass state

**Blocked, not failed:** CAP-21 and CAP-22 on the laptop. They are unrunnable there until
TA-232 is fixed; recording them as failures would hide that the taskbar change works.

**Still to run:** CAP-22 against a real Windows toast on the external; DSP-08 at 125%;
DSP-09's "after" shot to close the issue #1 before/after pair; the remainder of Block A;
and Blocks C, D, E.

**Issue #1 evidence already in hand:** two 1.3.0 full-screen captures a minute apart, one
with the widget on the external (correct) and one with it on the laptop (wrong, still
returns EXTERNAL). The pair contains its own control, which is what makes it worth
posting — one variable changed, the output did not move.
