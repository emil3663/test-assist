# Review response — the 11 September contribution

**For:** Martin
**Date:** 2026-09-11
**Re:** `docs/SESSION_HANDOVER_2026-09-11.md` and PRs #8, #9, #10, #12, #19

Your §7 briefs a reviewer on how to review this work, and sets the bar for what
comes back: measured evidence rather than impressions, a named failure scenario
per finding, and an explicit statement of what could not be checked. This is
written to that standard. Where something is inferred rather than measured, it
says so.

**Method:** detached read-only worktrees of all five branches, per-branch `git
log` bodies and diffs, exact counts (`wc -l`, `grep -c`, hash-set comparison)
against each branch rather than against the summary. Nothing was run — no test
suite, no application. Full working is in `docs/VERIFICATION_2026-09-11.md`.

---

## What held up

Taking §1 at its word and reading the commit bodies first was the right
instruction — most of what follows was reconstructed from them rather than from
the diffs, and the reasoning was there every time it was needed. Specifically
verified:

- **"Three of the 23 commits are not in the format"** — exactly three, and all
  three are `macos-support` commits predating the convention's own adoption in
  `1aa8a85`. Precisely as §2 explains it.
- **Every §7 measurement is exact.** `canvas.py` is 1,587 lines on `ui-polish`,
  there are 14 `skipif` occurrences, and
  `test_LAUNCH_09_every_launcher_attribute_this_suite_names_exists` is at
  `test_regressions.py:2716`. Not approximations — exact.
- **The `CONTRIBUTING.md` collision was handled exactly as described.** Five
  insertions, zero deletions, inserted cleanly after the `TEST_PLAN.md` §6
  reference. Dropping the duplicate label set rather than merging it was the
  right call for the reason given.
- **Both headline defects are real.** The HiDPI one was confirmed independently
  on `main` before your fix was read: logical-sized destination pixmap at
  `capture.py:331–333`, device-pixel `grabWindow()` result drawn into it at
  `:344`, with the comment at `:340–343` asserting this *was* correct DPR
  handling. Geometrically right, resolution-wrong, and structurally invisible at
  ratio 1.0.
- **The PR #8 approach is the right one.** Extracting `composite_ratio()`,
  `to_device_rect()` and `device_result_size()` as pure functions on plain
  values — so a CI machine with no HiDPI screen can exercise them against
  literal ratios — is what makes this testable at all. `test_HIDPI_02` as an
  explicit "ordinary hardware is byte-for-byte unaffected" guard is the right
  instinct, and making `_StubScreen` actually return the extra pixels rather
  than merely report a ratio is the difference between a real test and a
  decorative one.

---

## Corrections, ranked by consequence

### 1. `ca71881` is not droppable, and the advice to drop it would crash the app

§4 says: *"If you disagree, `ca71881` is the commit to drop. Everything else in
that PR stands without it."*

**Failure scenario:** drop `ca71881`, keep the rest. `5c5e0a1` rewrote
`_apply_hotkey_labels()` to call `self._btn_record.setToolTip(...)`.
`_btn_record` appears 10 times on `ui-polish` and 0 times on `main`. The app
raises `AttributeError` on startup on the `register_global_hotkeys=True` path —
the real application path, and the one the suite avoids. It is the same defect
`5c5e0a1` fixed, in mirror image, invisible to the tests for the identical
reason it was invisible the first time.

The dependency is also written into the suite in places that assert the
*absence* of the old UI — `test_regressions.py:2556`
(`assert not hasattr(launcher, "_btn_photo")`) and `:2736`
(`expected_absent = {"_btn_photo", "_btn_video", "_mode"}`) — plus the TA-211
and TA-215 tests driving `_btn_record` at `:525`, `:552`, `:2580`, `:2594`,
`:2702`. `aca5463` exists solely to repair tests the rebuild broke, and
`1eb6421` redrew every `help.html` diagram for the rebuilt launcher.

**Measured, not just argued.** `git revert --no-commit ca71881` on a detached
`origin/ui-polish` worktree:

```
CONFLICT (content): Merge conflict in python/launcher.py
CONFLICT (content): Merge conflict in python/tests/test_regressions.py
error: could not revert ca71881... feat(launcher): rebuild the floating panel and docked strip
```

Three conflicting hunks in `launcher.py` — the capture-button row, the
full-screen button, and the whole recording-status/Stop/RECENT block — and one
in `test_regressions.py` spanning lines 2525–2734, which is the "Launcher
redesign" section `ca71881` added and `5c5e0a1` and `aca5463` then extended.
`theme.py` auto-merges cleanly; its 12 added tokens have no later edits to
collide with.

Rejecting the rebuild is a five-commit unpick, not a one-commit revert. It is
still a legitimate choice — it just isn't the cheap one the handover offers.
Worth stating that cost accurately, because the offer as written invites exactly
the change that breaks it.

**The conflicts are not the dangerous part.** Inspected on the mid-revert tree,
`_apply_hotkey_labels()` sits entirely *outside* every conflict hunk and merges
silently — still calling `self._btn_record.setToolTip(...)` — while `grep` finds
zero `_btn_record = ` creation lines, those having reverted cleanly with no
marker. Checked against `ui-polish`'s own positions: the widget is created at
`launcher.py:240`, between the 216–229 and 265–340 hunks; `_apply_hotkey_labels()`
is at `:487` with the surviving call at `:500`. `ca71881`'s own references revert
away with it — the one that survives is the reference `5c5e0a1` added, because
that is a separate commit the revert never touches.

So a fully hand-resolved unpick yields a tree that still raises `AttributeError`
on `register_global_hotkeys=True`, with nothing to flag it. **The conflict-free
resolution is the worse outcome**, which is the opposite of the usual intuition
and the reason this is worth stating explicitly rather than leaving to whoever
attempts it.

### 2. PR #8's seam test never exercises the ratios the fix exists for

`test_device_pieces_tile_the_result_without_gap_or_overlap` iterates
`for ratio in (1.0, 2.0, 3.0)` over a layout producing two pieces.

**Failure scenario:** `to_device_rect()` rounds x, y, w and h independently. For
three or more pieces at a fractional ratio, `round(w₁·r) + round(w₂·r)` is not
guaranteed to equal `round((w₁+w₂)·r)`. The result is a 1px unpainted seam —
which every viewer renders as a black line through the middle of the evidence,
and which is precisely what that test was written to catch. The commit body
names *"every Windows machine at 125% or 150% scaling"* as the motivating case,
and 1.25 and 1.5 are the two ratios never tested. Three-screen layouts aren't
hypothetical: TA-209 documents the L-shaped case.

For two pieces the seam is safe by construction — piece 2's `dest.x` equals
piece 1's width, so both sides round the same expression. It is the third piece
that breaks the property.

**Ask:** add `1.25, 1.5` to that loop and a three-piece layout, and report
whether it still passes. This is cheap and it is the case the fix is for.

### 3. §7's numbers are exact, but never say which tree they describe

All three check out perfectly against `ui-polish`, and all three are wrong
against `main`: `canvas.py` is 1,542 there, there are 5 `skipif`s not 14, and
`test_LAUNCH_09...` does not exist — nor does any `test_LAUNCH_*`.

Since §7 is explicitly the briefing for an agent reviewing the code, and an
agent will most likely start from `main`, it will find all three wrong and
start discounting the brief. One line naming the ref fixes it.

### 4. The document is stale about itself by exactly one commit

Committed at 15:06:42; `90fcf92` landed on `ui-polish` at 17:24:49. Every
numeric drift traces to that one commit — 23 → 24 commits, 6,397 → 6,503 words
(that commit's body is ~106 words, and 6,503 − 6,397 = 106), median 256 → 252,
and 13 → 15 open issues, one of which (#20) is the divergence issue `90fcf92`'s
own body says it was deferring.

The statistics were correct when written. Flagging it because §1 makes those
numbers load-bearing for how the whole review is conducted, so they are the
numbers most worth a final pass before the document is committed.

### 5. A fifth deviation didn't make it into §4

`ff0f276` replaces the launcher's amber palette with `theme.py`'s indigo
tokens, and its own body flags it properly: *"the amber may have been
deliberate, to keep an always-on-top overlay visually distinct from the
application under test… worth disagreeing with."*

That is exactly the right note to write. It just didn't reach §4's list of four
deviations, so someone reading only the handover would never know to make the
call — and unlike the rebuild, this one *is* independently droppable, since
`ff0f276` is the earliest launcher commit on the branch. A good illustration of
§1's own point, and of what it costs when the summary doesn't carry the commit
body's reasoning forward.

### 6. Small imprecisions

- *"14 tests run on one OS only"* — 14 is the `skipif` count; only **8** are
  `sys.platform` conditions (6 × `win32`, 2 × `darwin`). The other 6 guard on
  the Qt platform plugin in `test_visual.py`, not the OS.
- *"Eleven hand-drawn icon factories and `_style_mode_icon`"* (`ca71881`) —
  **ten** factories, listed by line at `ca71881^`. Eleven *functions* were
  removed, of which ten match `_make_*icon`; `_style_mode_icon` is a style
  helper, not a factory. The wording reads as eleven factories plus the helper.
- *"launcher.py loses ~150 lines"* (`ca71881`) — `git show --numstat` gives
  `392 409 python/launcher.py`: net **−17** for this commit alone, an
  overstatement of roughly 9×. 801 of the file's lines changed, so it is churn
  rather than reduction. Substance unaffected, but line-count is what a reviewer
  uses to size a diff before opening it.
- *"the desktop build has three dependencies"* — three lines, but `pytest` is a
  test dependency sitting in the shipped app's install list. The point stands.

---

## Two things that were already true before you arrived

Neither is yours; both are worth knowing you found real problems rather than
introduced them.

- **`README.md` understated `main`'s own test count by ~91** — it claims 229;
  `BUILD_LOG.md`'s rc5 entry records 320 passed. `90fcf92` corrects it to 351.
- **`.gitignore` line 5 was ignoring neither path.** `.venv/.claude/` is two
  patterns merged, so `.claude/` — where agent session artifacts land, in a
  public repo — was never ignored. PR #12 is a one-line fix and is the first
  thing being merged.

---

## On your §5 decision table, where it can be answered now

- **#15 (JSON export)** — confirmed, and it is the most consequential item you
  raised. The payload on `main` is exactly
  `{ annotations, timestamp: new Date().toISOString() }`. The README promises
  the layer can be *"re-rendered at a different resolution"* and *"re-rendered
  against a later build of the same screen"*; neither is possible without
  source dimensions. This sits on a page linked from a CV and an already-sent
  cover letter, and it is the specific claim used to distinguish this from a
  screenshot tool. It is being fixed rather than softened.
- **#2 (is TA-225 the same bug)** — your reasoning holds. The fix changes result
  sizing, so it can make a capture softer or sharper but never blank. Worth
  adding that TA-223 is also untouched by it for a different reason: that one
  lives in `mouseMoveEvent`'s `globalPosition()` tracking during the drag, not
  in the grab path. Neither should be closed on the back of #8.

---

## What was not checked

No test suite was run, on any branch — "351 tests, ~12s" and "315 of 320 on a
Mac" are unverified, though nothing measured contradicts either. The HiDPI fix
was verified by reading and by its own tests, not by a measured before/after on
a HiDPI display; that measurement is still owed and can only be done on
hardware. Issue creation
timestamps weren't captured, so the 13 → 15 explanation is inference. And nobody
has *looked* at the rebuilt launcher on Windows — "roughly three times the
height" is a claim about a screen, and no screen has seen it yet.
