# TA-204 Multi-Display Verification — Handover (2026-09-15, end of session)

**Update, later still (same day):** the "how was the original capture driven" lead
below (HW-1) is resolved — it was a red herring, not remote-vs-local. Root cause
found: `Canvas.export_pixmap()` in `python/canvas.py` has an independent, unfixed
copy of the exact same bug `1df02f9` fixed in `capture.py::_grab()` — a bare
`QPixmap(size)` composited onto with no alpha fill. `_grab()`'s output is correctly
transparent in memory; `export_pixmap()` (which every real Save PNG / clipboard copy /
history snapshot goes through) silently reintroduces the opaque-black corner one step
later, regardless of how the capture was driven. Full writeup, with the file that
proves it, in `docs/TA-231.md`'s final section. Not fixed here — code work, goes
through Claude Code in VS Code per the working agreement below.

Repo: `C:\Users\MSI workstation\source\repos\test-assist`
Branch: `fix/ta-232-overlay-hidpi-coverage` — 9 commits ahead of `origin`, nothing pushed.
Deployed build under test: `C:\TestAssist\TestAssist.exe`, commit `b77ce50a` (predates all 9 new commits).

**Working agreement:** doc writing/updates (handover docs, issue docs) are fine to do
directly from chat/Cowork. Code changes and commits specifically go through Claude Code
in VS Code — Cowork shouldn't be a second git driver on the same repo. Earlier this
session two tools *did* drive git on the same working tree concurrently (see "Git
history note" below) — resolved, nothing lost, and going forward Claude Code in VS Code
is the sole git driver for this repo.

## What's committed (local only, on the branch above)

- `60aec84` docs(ta231): soften HW-1 root-cause claim, add on-hardware falsification
- `01469f9` test(tests): document TA232_HW1 test's platform-dependent coverage
- `7e6b60e` docs(ta240): file annotation-window focus-raise bug
- `1df02f9` fix(capture): give composite canvas a real alpha channel
- `7d52ac1` test(screen-geometry): rule out coordinate-math rounding for TA-239 seam
- `608eed5` chore(scripts): add TA-204 preflight check script
- `ba00fac` docs: add launcher evaluation pass checklist (PR #19)
- `2baab32` docs(backlog): file TA-233–238 from the 2026-09-13 review pass
- `7ef8b40` docs: record 2026-09-12/13 TA-204 session handovers and TA-232 fix docs

## HW-1 fix — status as of tonight: kept, but the mystery deepened rather than resolved

Original hardware evidence is solid: two exported PNGs from the deployed build showed a
genuinely opaque-black (no alpha) rectangle exactly where a short composite piece left
the canvas unpainted. The fix (`1df02f9`, building the composite canvas as a `QImage` in
an explicit ARGB format instead of a bare `QPixmap(size)` + `fill(transparent)`) is
correct and strictly safer regardless — but Claude Code in VS Code has now ruled out the
two most likely explanations for why the *original* bug doesn't reproduce on the dev
machine:

- **Qt/PySide6 version mismatch — ruled out.** Bundled version in the deployed build
  (`6.11.0`) matches the dev venv exactly.
- **Packaging (PyInstaller/frozen-build) difference — ruled out.** A frozen PyInstaller
  probe on this machine still gets real alpha from `fill(transparent)`.
- **Ran the actual pre-fix `capture.py`** (confirmed byte-identical to the deployed
  build via `git log`) **against the real physical rig** — the same laptop+external
  setup (1536×864@1.25, 1920×1080@1.0) the original evidence came from — reproducing the
  exact drag from the `TA-225` debug-log entry. Output matched the evidence file's size
  (579×305) exactly, but the corner came back as real transparency, not opaque black.

So: same source, same Qt version, same physical hardware, same capture call, same
drag — and the defect still doesn't reproduce. This is committed in `docs/TA-231.md`
(`60aec84`), which now reads "plausible mechanism, fixed defensively" rather than
"root cause identified," and frames the fix as worth keeping on its own merits (an
explicit `QImage` alpha format is strictly safer regardless of whether this was the
actual trigger).

**Open lead, not yet investigated:** something about how the *original* capture session
was being driven may matter — e.g. remote vs. local input (much of TA-204's earlier
hardware work this cycle was done via a remote computer-use bridge before shifting to
the user driving the rig physically), which could plausibly affect which code path,
process, or Qt backend actually issues the grab. Worth checking whether the two
black-rectangle evidence files correlate with remote-driven captures specifically.

## Punch list status

| Item | Status |
|---|---|
| HW-1 (taskbar drag, no clip) | Fix committed and kept as defensive hardening. The opaque-black corner mystery is now explained, not just falsified: a second, unfixed instance of the same bug lives in `canvas.py::export_pixmap()`, downstream of `_grab()` — see `docs/TA-231.md`'s final section. Not remote-vs-local; deterministic and reproduces locally too. |
| HW-4 (cross-screen, no truncation) | Original PASS stands. A later file where "external taskbar wasn't covered" was a drag-placement issue (confirmed via `TA-225` debug log: the drag simply didn't reach the taskbar), not a new regression. |
| HW-5 (TA-223 "jump" at boundary) | Root cause found, not a code bug: the laptop screen ends at logical x=1536, external starts at x=1920 — a 384px gap in the Windows virtual-desktop layout. `debug.log` shows the OS cursor teleporting across that gap 3 times in one drag. Recommend checking Windows Display Settings → Rearrange your displays to close the gap, then re-test. |
| HW-6 (cursor/reticle tracking) | ✅ Measured, reclassified: not a bug. The reticle-vs-rectangle "mismatch" is expected DPI-aware per-screen rendering of one logical rectangle. See `docs/TA-233.md`'s 2026-09-15 section — recommends a regression test + a `TESTASSIST_BACKLOG.md` correction, not a runtime fix. |
| HW-7 (external taskbar, fresh launch) | ✅ PASS, measured (2026-09-15). Clock captured in full on the first quick-capture after a clean relaunch, no clipping. See `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-15 section. |
| TA-239 (~5px composite seam) | Coordinate-math rounding ruled out (new synthetic test, 200×2 trials, exact edge match). Debug-log instrumentation added to `capture.py` for the two remaining candidates (`grabWindow()` actual size, `QPainter.drawPixmap()` blend behavior) but not in the deployed build yet — no on-hardware data. |
| TA-240 (edit window doesn't raise on click) | ✅ RESOLVED, confirmed 2026-09-15: not a Test Assist defect. Was the Claude desktop app's own Windows always-on-top bug, active only during this bridged session — restarting Claude desktop fixed it (control case: Notepad, unrelated to this codebase, also started working again). See `docs/ISSUE-TA-240.md`'s "Resolved" section. No code fix needed for the original symptom. |
| TA-241 (new: TA icon doesn't minimize an already-open edit page) | Filed as `docs/ISSUE-TA-241.md`, found while validating TA-240 above — real, distinct, not explained by the always-on-top artifact. Not yet investigated against source. |
| TA-231 (unmapped region between screens) | Reopened, then re-softened per the falsification above — see `docs/TA-231.md`. |

## Key facts worth not re-deriving

- **Screen geometry on the rig:** laptop `(0, 0, 1536, 864)` @1.25 DPR, external
  `(1920, 0, 1920, 1080)` @1.0 DPR. The gap between x=1536 and x=1920 is the root of
  the HW-5 jump.
- **Debug log location:** `C:\Users\MSI workstation\AppData\Local\Test
  Assist\history\debug.log` (gated by `TESTASSIST_DEBUG=1`). Has real `TA-223`/`TA-225`
  entries from physical drags this session; no `TA-239` entries yet since that
  instrumentation isn't in the deployed build.
- **`git commit`s in this repo use `emil3663 <emil3663@gmail.com>`** — already
  configured, nothing to set up.

## Ready for next build — everything validated, 2026-09-15 (later still)

All open items from this hardware-verification pass are now either measured and
closed, or measured and confirmed as real, scoped defects. Nothing below still
needs re-testing or re-diagnosing before code work starts — this is the complete
punch list for the next build, before picking up backlog items.

**Needs an actual code fix:**

1. **`Canvas.export_pixmap()` in `python/canvas.py`** (`TA-231`) — bare `QPixmap`
   with no alpha fill, the second unfixed instance of the bug `1df02f9` already
   fixed once in `capture.py::_grab()`. Root-caused, not just suspected — see
   `docs/TA-231.md`'s final section for the code excerpt and reasoning. Mirror
   `_grab()`'s `QImage(Format_ARGB32_Premultiplied)` + `fill(transparent)` pattern,
   add a test mirroring
   `test_TA232_HW1_unpainted_corner_between_unequal_height_pieces_stays_transparent`
   against `export_pixmap()` itself, and re-run the drag that produced
   `test-assist-1789493362.png` to confirm the *saved file* is transparent this
   time.
2. **`TA-241` — floating toolbar's TA icon doesn't minimize an already-open edit
   page** (new, `docs/ISSUE-TA-241.md`). Opening works; the toggle-to-minimize on
   a second click doesn't. Not yet root-caused — starting points are in the
   ticket (`python/launcher.py`'s click handler, `python/canvas.py`'s window).

**Needs doc/test correction only, no runtime behavior change:**

3. **`TA-233` / HW-6** — the reticle-vs-rectangle "mismatch" is correct DPI-aware
   rendering, not a bug (measured, `docs/TA-233.md`). Recommended: a regression
   test asserting the DPR-ratio relationship between the two screens' rendered
   pieces, and a correction to `TESTASSIST_BACKLOG.md`'s TA-223 entry (and
   `TA-233.md`'s own Problem/Scope text) so it stops reading as an open bug.

**Still open, needs on-hardware data (not blocked on a decision, just data):**

4. **`TA-239`** — coordinate math is conclusively cleared (proven for any DPR, not
   hardware-dependent); the remaining two candidates
   (`grabWindow()`'s actual returned size, `QPainter.drawPixmap()`'s blend
   behavior at adjacent dest rects) need the debug-log instrumentation already
   added to `capture.py::_grab()` to actually ship in a build and get exercised
   by a real cross-screen drag.

**Confirmed not a code issue — no fix needed:**

5. **`HW-5` / `TA-223`'s "jump" at the screen boundary** — root-caused as a 384px
   gap in the Windows virtual-desktop layout between the two screens, not a Test
   Assist bug. Action item is for whoever's at the rig: Windows Display Settings →
   Rearrange your displays, then a retest (not yet done).
6. **`TA-240`** — resolved, confirmed environmental (Claude desktop's own
   Windows always-on-top bug during this bridged session), not a Test Assist
   defect. Nothing to fix. See `docs/ISSUE-TA-240.md`'s "Resolved" section.

**Already closed:**

7. **`HW-1`**, **`HW-2`**, **`HW-4`**, **`HW-7`** — all measured PASS, see the
   punch list above.

Also still pending: deciding whether to push the local branch (9 commits ahead of
`origin`, nothing pushed yet).

## Immediate next actions

1. Fix `Canvas.export_pixmap()` (item 1 above) — the highest-priority code fix,
   a real user-facing defect on every Save PNG / clipboard copy / history
   snapshot.
2. `TA-241` — root-cause and fix the minimize-toggle gap (item 2 above).
3. `TA-233` — add the regression test and correct the two docs (item 3 above).
4. Decide whether to push the branch.
5. HW-5: ask whoever's at the rig to check/fix the monitor arrangement in Windows
   Display Settings, then retest.
6. `TA-239`: get the existing instrumentation into a deployed build and run a
   real cross-screen drag to collect the missing hardware data.
7. Once the above lands, move on to `TESTASSIST_BACKLOG.md` items.
