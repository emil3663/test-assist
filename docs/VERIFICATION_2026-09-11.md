# Verification report — the 11 September contribution

**Date:** 2026-09-11
**Scope:** independent verification of `docs/SESSION_HANDOVER_2026-09-11.md` and the five open PRs behind it (#8, #9, #10, #12, #19).
**Method:** read-only detached worktrees of all five PR branches, plus per-branch `git log` bodies and diffs dumped to `artifacts/review/`. Every number below is measured against the branch it actually describes — `wc -l`, `grep -c`, hash-set comparison, word counts over real commit bodies — not re-read from the handover's own account of itself. Commit timestamps compared directly rather than inferred from prose.

---

## 1. The handover is stale about itself — by exactly one commit

Same class of finding as `VERIFICATION_2026-09-09.md` §1, but much narrower and entirely benign. The document was committed at **15:06:42**. One further commit landed on `ui-polish` **2h18m later**, and every numeric drift in the document traces to that single commit.

| Time | Commit | What |
|---|---|---|
| 15:06:42 | `6595e6e` | `docs: session handover for the 11 September contribution` — the document itself, on `main` |
| 17:24:49 | `90fcf92` | `docs: bring the README's desktop claims up to date` — tip of `ui-polish`, written after the handover and not reflected in it |

**What drifted, and by how much:**

| §1 claim | As written | Now |
|---|---|---|
| Commits carrying rationale | 23 | **24** |
| Total words of rationale | 6,397 | **6,503** (body only) |
| Median words per commit | 256 | **252** |
| `ui-polish` commits | 15 | **16** unique (20 via the command §1 gives — see §3) |
| Open issues (§7) | 13 | **15** |

`90fcf92`'s own body is ~106 words, and 6,503 − 6,397 = **106**. The arithmetic closes exactly. **The statistics were correct at the moment they were written** and have drifted by precisely one commit's worth — this is a documentation-hygiene problem, not a credibility one.

The issue count moves the same way and for a related reason: the new issue **#20, "The two builds have diverged, and the browser one is the shop window,"** is literally the issue `90fcf92`'s commit body says it was deliberately deferring rather than fixing with a quiet edit. (Creation timestamps weren't captured — `gh` was queried without `createdAt` — so this is strong inference, not proof.)

**One worry raised and cleared.** `90fcf92`'s subject — *"bring the README's desktop claims up to date"* — looked like it might have quietly actioned the #15 JSON-export decision before it was put to you. It did not. It corrects the test count (229 → 351) and adds the menu bar and OS-following light/dark to the desktop-only feature list, and its body explicitly records what it left alone and why. **#15 remains genuinely open and undecided.**

---

## 2. Every §7 measurement is exact — against a tree the document never names

§7 is the section that briefs a reviewing agent, so its numbers matter more than most. All three checkable ones are **precisely correct for `ui-polish`** and wrong for `main`:

| §7 claim | On `main` | On `ui-polish` |
|---|---|---|
| `canvas.py` (1,587 lines) | 1,542 | **1,587** ✅ exact |
| "14 tests run on one OS only" | 5 | **14** `skipif` occurrences ✅ |
| `test_LAUNCH_09_every_launcher_attribute_this_suite_names_exists` | absent (no `test_LAUNCH_*` exists at all) | **`test_regressions.py:2716`** ✅ |

These are exact measurements of a specific tree, not approximations — which is a point in the document's favour, not against it. The defect is only that §7 never states which tree it measured, and a reviewer starting from `main` will find all three wrong and start distrusting the brief.

**One genuine imprecision inside the right tree:** on `ui-polish` there are 14 `skipif` occurrences, but only **8** are `sys.platform` conditions (6 × `win32`, 2 × `darwin`). The remaining 6 guard on the Qt platform plugin (`test_visual.py`'s offscreen guard), not the OS. "14 tests run on one OS only" should read "8 tests are OS-gated; 14 carry a `skipif` of some kind."

---

## 3. Claim audit — the handover against the repository

| Claim | Where | Reality |
|---|---|---|
| "three of the 23 commits here are not in the format" | §2 | **True, exactly.** Three subjects fail the Conventional Commits grammar: `Add run.sh...`, `Give global hotkeys a backend per platform...`, `Give the UI font a real fallback chain...`. All three are `macos-support` commits predating the convention's own adoption (`1aa8a85`, 11:10:53), exactly as §2 explains. |
| `git log origin/main..ui-polish` → "the UI work, 15 commits" | §1 | **The number is right; the command is not.** `ui-polish` is stacked on `macos-support`, so that command returns **20** (16 unique + `macos-support`'s 4). The 4 are a strict subset, confirmed by hash comparison. §1's command therefore double-counts #9's work for anyone who runs it. |
| "#19 is based on #9 and retargets to `main` when that merges" | §5 | **True.** Confirmed by the same subset check and by `gh`'s `baseRefName`. |
| §1's three `git log` commands cover the work | §1 | **Incomplete.** They cover 3 of 5 branches. `issue-workflow` (2 commits) and `gitignore-fix` (1) get no command and no branch name anywhere in the document — yet §5 tells you to review **#12 and #8 first**. |
| "**Nothing here is merged.** Five PRs are open." | header | **True.** `origin/main` is at `6595e6e`, the handover commit itself. Five open PRs confirmed. |
| Your `CONTRIBUTING.md` "kept as-is… a four-line pointer added… nothing else touched" | §4 | **True, precisely.** `CONTRIBUTING.md \| 5 +` — five insertions, **zero deletions**, inserted cleanly after the `TEST_PLAN.md` §6 reference. The process content genuinely went to the new `docs/WORKING_AGREEMENTS.md` (148 lines) and `docs/CONVENTIONAL_COMMITS.md` (237 lines). |
| The four §6 findings are real | §6 | **Three have filed issues** — #2 (HiDPI), #3 (hotkeys down at startup), #4 (hardcoded Segoe UI). The fourth (text plate lost on commit) has no issue; it was fixed directly in `9f62f55`. |
| "the desktop build has three [dependencies], on purpose" | §7 | **Three lines, but two runtime deps.** `requirements.txt` is `PySide6`, `pytest`, `imageio-ffmpeg` — `pytest` is a test dependency sitting in the shipped app's install list. The point being made (don't add dependencies casually) stands. |
| "315 of 320 tests passed unmodified on a Mac" | §4 | **Unverifiable here** — needs a Mac. |
| "351 tests, ~12s" | §8 | **Not run.** Not contradicted by anything measured. |

---

## 4. PR #8 (HiDPI) — the fix is sound; its own property test has a gap

The defect is real and I confirmed it independently on `main` before reading the fix. In `capture.py`, the result pixmap is allocated from **logical** pixel sizes (lines 331–333) and `grabWindow()`'s **device**-pixel return is drawn down into it (line 344). At ratio 2.0 an 800×600 grab lands in a 400×300 export. The comment at lines 340–343 asserts this *is* correct DPR handling — it is geometrically correct and resolution-wrong, which is exactly why a 1.0-ratio machine can never reveal it, and why this has been quietly degrading exported evidence on any machine at 125% or above.

The fix is careful work. Extracting `composite_ratio()`, `to_device_rect()` and `device_result_size()` as pure functions on plain values — so a CI machine with no HiDPI screen can exercise them against literal ratios — is the right instinct and is explicitly reasoned in the commit body. `test_HIDPI_02` is a proper regression guard proving 1.0 hardware is byte-for-byte unaffected. The `_StubScreen` change actually models a HiDPI screen (returns the extra pixels *and* tags the ratio) rather than merely reporting a number.

**The gap.** The seam-safety property test reads:

```python
for ratio in (1.0, 2.0, 3.0):
```

All three are integers, and the layout it exercises produces exactly **two** pieces. The fix's own commit body names *"every Windows machine at 125% or 150% scaling"* as the motivating case — **1.25 and 1.5 are never exercised.** `to_device_rect()` rounds x, y, w and h independently, and for three or more pieces at a fractional ratio, `round(w₁·r) + round(w₂·r)` is not guaranteed to equal `round((w₁+w₂)·r)`. The failure mode is a 1px unpainted seam, which is precisely what that test exists to catch and which every viewer renders as a black line through the middle of the evidence.

For two pieces the seam is safe by construction (piece 2's `dest.x` equals piece 1's width, so both sides round the same expression). Three-piece layouts are not hypothetical: `TA-209` already documents the L-shaped three-screen case.

**Ask before merging:** add `1.25, 1.5` to that loop and a three-piece layout, and report whether it still passes. This machine's own laptop runs at 125%.

### The fix is incomplete — the full-screen path has the same defect and #8 does not touch it

Found by building both branches and taking a real capture on the 125% laptop, not by reading.

Two full-screen captures, one per build, measured: **a 1920×1080 file containing only 1536×864 of content in the top-left, black elsewhere.** Those are exactly the device and logical dimensions of a 1080p panel at 125%. The two builds' output differs by 49 pixels — the same capture path in both.

Each link verified:

1. `_grab_full_capture()` lives in **`launcher.py`**, not `capture.py`, and reads `pixmap = self._current_screen().grabWindow(0)` — byte-identical on `main` and `ui-polish`, with **no `setDevicePixelRatio` call anywhere in either file**.
2. **PR #8's diff touches `capture.py`, `screen_geometry.py` and two test files — zero lines of `launcher.py`.**
3. On a 1.25 screen, `grabWindow(0)` returns a 1920×1080 pixmap *tagged* DPR 1.25.
4. The fix's own commit body names this hazard exactly: *"canvas.py measures annotation coordinates and its own widget size from `_pixmap.width()`, which is device pixels, so a tagged pixmap would render into a quarter of the widget and put every annotation at half its intended position."*
5. That is precisely why it calls `setDevicePixelRatio(1.0)` on **both** results inside `capture.py`, the no-pieces fallback included.
6. The full-screen path never enters `capture.py`. It hands a DPR-tagged pixmap straight into the code the fix's own author documented as unable to accept one.

**Remedy — the same line, in the place the fix did not reach:**

```python
def _grab_full_capture(self) -> None:
    pixmap = self._current_screen().grabWindow(0)
    pixmap.setDevicePixelRatio(1.0)          # matches capture.py's normalisation
    self._on_capture_ready(pixmap)
```

**This is not a regression from this contribution.** It is pre-existing on `main` and ships in v1.4.0-rc5 today: every user on a scaled display — 125% and 150% being the ordinary Windows laptop — gets full-screen captures that are black-padded and carry logical-resolution content inside a device-sized file. For a tool whose output is evidence, that is a correctness defect, and it is single-monitor reproducible.

**It should fold into #8 rather than become a separate PR.** Same defect class, same one-line remedy; merging #8 without it would close the issue while leaving half the capture surface broken — worse than not closing it, because the ticket would then read as done.

**Not yet done:** diagnosed from the artefact plus the code, not by running the patched line. Confirmation is that one line plus a re-capture — if the black padding goes and content fills 1920×1080, it is proven.

**On TA-225 and TA-223.** The handover's reasoning that TA-225 (blank capture) is probably unrelated holds — this fix changes result *sizing*, and can make a capture softer or sharper but never blank. TA-223 (selection rectangle jumping at a mixed-DPI boundary) is untouched by this PR for a good reason: it lives in `mouseMoveEvent`'s `globalPosition()` tracking during the drag, not in the grab path. Neither should be closed on the back of this fix.

---

## 5. Three things about this repository, independent of the PRs

1. **`README.md` understates `main`'s own test count by ~91.** It claims "229 pytest tests"; `BUILD_LOG.md`'s rc5 entry records `320 passed, 0 skipped (2 deselected)`. This was already stale before any of this work arrived — the same pattern `VERIFICATION_2026-09-09.md` §4 flagged and which was only partly corrected. `90fcf92` fixes it to 351, but only on an unmerged branch.

2. **`.gitignore` line 5 was ignoring neither path.** `.venv/.claude/` is two patterns merged onto one line, so **`.claude/` was not ignored** — the directory Claude Code writes session artifacts into, in a public repo, against a standing preference to keep agent session artifacts out of public repos. PR #12 splits it correctly and is a one-line change. Worth merging on its own merits regardless of what happens to the other four.

3. **The JSON export claim (#15) is confirmed false, and it is the most consequential item in the document.** The exported payload on `main` is exactly `{ annotations, timestamp: new Date().toISOString() }` — no image reference, no dimensions, no importer anywhere in the repo. `README.md` promises the layer can be *"re-rendered at a different resolution"* and *"re-rendered against a later build of the same screen."* Neither is possible without the source dimensions. This sits on the page linked from a CV and an already-sent cover letter, and it is the specific claim the README uses to distinguish this tool from a screenshot tool. Either add the fields or soften the sentence — but it should not stay as it is.

---

## 6. `ca71881` reviewed properly — and it is **not** droppable

§4 of the handover says of the launcher rebuild: *"If you disagree, `ca71881` is the commit to drop. Everything else in that PR stands without it."*

**That is false, and the cost of acting on it is a startup crash.**

`5c5e0a1` (two minutes later) rewrote `_apply_hotkey_labels()` to address the rebuilt controls. On `ui-polish` that method calls `self._btn_record.setToolTip(...)`. `_btn_record` appears **10 times on `ui-polish` and 0 times on `main`**. Drop `ca71881` while keeping `5c5e0a1` and the app raises `AttributeError` on startup, on the `register_global_hotkeys=True` path — which is the real application path and the one the suite structurally avoids, exactly as §7.2 of the handover warns. It is the same defect `5c5e0a1` was written to fix, reintroduced in mirror image, and invisible to the tests for the same reason it was invisible the first time.

The dependency is also written into the test suite, in places that assert the rebuild's *absence* of the old UI:

| Location | Assertion |
|---|---|
| `test_regressions.py:2556` | `assert not hasattr(launcher, "_btn_photo"), "the mode toggle is back"` |
| `test_regressions.py:2736` | `expected_absent = {"_btn_photo", "_btn_video", "_mode"}` — the allowlist inside `test_LAUNCH_09` |
| `:525, :552, :2702` | TA-211 hotkey tests reading `launcher._btn_record.toolTip()` |
| `:2580, :2594` | TA-215 tests driving `_btn_record` directly |

And `aca5463` exists *solely* to repair the Windows-only TA-211 tests the rebuild broke, while `1eb6421` redrew every `help.html` diagram to show the rebuilt launcher — so dropping `ca71881` alone would leave the help page documenting a UI that does not exist, which is the precise defect class TA-203 and TA-211 were raised for.

**Real cost of rejecting the rebuild:** unpick `ca71881` + `5c5e0a1` + `aca5463` + the docstring and thumbnail-fallback work in `cc5d893` + the launcher and strip diagrams in `1eb6421`. That is a considered decision, not a one-commit revert, and it should be made knowing that.

**Measured afterwards, confirming the above.** `git revert --no-commit ca71881` on a detached `origin/ui-polish` worktree (full transcript in `BUILD_LOG.md`, 2026-09-11):

```
CONFLICT (content): Merge conflict in python/launcher.py
CONFLICT (content): Merge conflict in python/tests/test_regressions.py
error: could not revert ca71881... feat(launcher): rebuild the floating panel and docked strip
```

Three conflicting hunks in `launcher.py` (the capture-button row, the full-screen button, and the whole recording-status/Stop/RECENT block) and one in `test_regressions.py` spanning lines 2525–2734 — recorded as *"the whole 'Launcher redesign' test section added by `ca71881` and extended by later commits (`5c5e0a1`, `aca5463`)"*, which is the dependency chain above, independently observed. `theme.py` auto-merged cleanly, its 12 added tokens having no later edits to collide with.

**And the conflicts are not the dangerous part.** Inspected on the mid-revert tree: `_apply_hotkey_labels()` sits entirely **outside** every conflict hunk and merges silently, still calling `self._btn_record.setToolTip(...)` — while `grep` found **zero** `_btn_record = ` creation lines, those having been removed cleanly with no conflict at all.

Confirmed against `ui-polish`'s own line positions: `_btn_record` is created at `launcher.py:240`, which falls between the 216–229 and 265–340 conflict hunks and so is untouched by any marker; `_apply_hotkey_labels()` is at `:487` with its surviving call at `:500`, far outside all three. `ca71881`'s own references to the widget revert away with it; the one that survives is the reference `5c5e0a1` introduced, because that is a different commit and reverting `ca71881` does not touch it.

So a fully hand-resolved revert produces a tree that **still crashes** on `register_global_hotkeys=True` — the real startup path, and precisely the one the suite structurally avoids. **A conflict-free resolution is the worse outcome here**, because the four conflicts at least demand attention, while the dangling reference announces itself to nothing.

**What the commit actually does, measured:**

| | `main` | `ui-polish` |
|---|---|---|
| `_mode` / `_set_mode` / `_on_action_click` | 21 / 6 / 3 | **0 / 0 / 0** |
| `_btn_photo` / `_btn_video` | 13 / 12 | **0 / 0** |
| `_btn_record` / `_btn_stop` | 0 / 0 | **10 / 10** |
| `_make_*icon` factories, `_style_mode_icon` | 10 / present | **0 / gone** |
| `launcher.py` | 1,074 lines | 1,069 lines |

The mode concept is genuinely gone, not softened — confirmed by attribute count, not by reading the summary. Stop is a real separate full-width control (`launcher.py:271–278`), hidden by default and shown on `_set_recording_state` (`:604`), styled `DANGER` with a red frame border (`:901`) — matching the commit body's description exactly. `refresh_recent()` does read `paths.history_dir()` directly (`:630`, `:641`) rather than asking the editor, as claimed, and guards with `getattr(self, "_recent_slots", [])`.

**Two imprecisions in the commit body, both now isolated and confirmed** (`git show ca71881 --stat/--numstat`, transcript in `BUILD_LOG.md`):

| Commit body says | Measured for `ca71881` alone |
|---|---|
| "launcher.py loses ~150 lines" | `392 409 python/launcher.py` — net **−17**, an overstatement of roughly 9× |
| "Eleven hand-drawn icon factories and `_style_mode_icon`" | **Ten** `_make_*icon` functions, listed by line at `ca71881^`, plus `_style_mode_icon` — eleven *functions*, ten *factories* |

The whole commit is 596 insertions / 446 deletions across three files; `launcher.py` is churn rather than reduction — 801 of its lines changed for a net of −17. Neither imprecision affects the change's substance, but "loses ~150 lines" is the kind of claim a reviewer uses to size a diff before reading it.

*(`BUILD_LOG.md`'s own entry states the overstatement as "roughly 30×" — that figure is 150 ÷ −5, the whole-branch net, rather than 150 ÷ −17, this commit's. The correct factor is ~9×.)*

**A new coupling worth knowing about.** RECENT now reads `paths.history_dir()` — the same directory `_prune_unreadable_history()` deletes from on every launch. The panel's "confirm a capture worked without opening the editor" affordance is therefore coupled to history retention policy: prune aggressively and RECENT goes blank. Not a defect, but a dependency that did not exist before and is not documented.

**A fifth deviation the handover does not list.** §4 names four places the work departed from your direction. There is a fifth: `ff0f276` replaces the launcher's amber palette with `theme.py`'s indigo tokens, and its own commit body flags it for you — *"the amber may have been deliberate, to keep an always-on-top overlay visually distinct from the application under test… worth disagreeing with."* That is a separate decision from the rebuild, it is independently droppable (`ff0f276` is the earliest launcher commit on the branch), and someone reading only the handover would never know to make it. It is a good illustration of §1's own point that the reasoning lives in the commit bodies — and of the cost when the summary does not carry it forward.

**On the design itself:** the argument is strong. Making one button both start and stop a recording, then distinguishing the states by a 20px icon swap, is a real usability failure for an evidence tool, and the QuickTime comparison is apt. Roughly three times the height is a genuine cost, but the defence holds — the docked strip exists to be the compact mode, so the panel does not also have to be. The judgement call is yours; the reasoning behind it is not thin.

---

## 7. Suggested review order

Revised from §5's, on the basis of the above:

1. **#12** (`gitignore-fix`) — one line, fixes a real ignore gap with a privacy dimension. No reason to wait.
2. **#8** (`hidpi-capture`) — genuine defect, sound fix, but put the fractional-ratio question in §4 to Martin before merging.
3. **#9** (`macos-support`) — unblocks #19.
4. **#10** (`issue-workflow`) — scope verified clean; independent of everything else.
5. **#19** (`ui-polish`) — last, since it is the only real judgement call (the launcher rebuild, `ca71881`) and is stacked on #9 anyway. Decide it as **accept-or-reject the whole rebuild**, not as a droppable commit — see §6.

---

## What I didn't do

I did not run the test suite on any branch — the "351 tests, ~12s" and "315 of 320 on a Mac" figures are unverified, though nothing measured contradicts them. I did not run the app or capture anything on real hardware, so the HiDPI fix is verified by reading and by its tests, not by a measured before/after on a HiDPI display — that measurement is still owed. `ca71881` was subsequently isolated — `git show --stat/--numstat` and a trial `git revert --no-commit` on a detached worktree, both transcribed in `BUILD_LOG.md` — so §6's line-count, factory-count and unpick-cost findings are now measured rather than inferred. What that revert could *not* establish is whether a hand-resolved unpick yields a running application; the conflicts stop it before a tree exists. I did not judge the rebuilt launcher visually — nobody has; it has not been run on Windows, and three-times-the-height is a claim about a screen, not a diff. Issue creation timestamps were not captured, so the explanation for 13 → 15 open issues is inference. And no PR was merged, rebased, modified or pushed in the course of this — the five worktrees under `artifacts/review/` are detached and read-only.
