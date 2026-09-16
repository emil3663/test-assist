# Release 1.5.0 Plan (Locked)

Date: 2026-09-16
Scope: Land `fix/ta-232-overlay-hidpi-coverage` and `ui-polish` (minus one commit) onto `main`, resolve their one real code collision deliberately, cut 1.5.0.
Status: Approved — decisions below are locked; sequencing and collision resolution are ready for implementation in Claude Code (VS Code). Not committed anywhere yet; this doc itself is a handover, same pattern as `docs/HANDOVER_TO_CLAUDE_CODE_2026-09-15.md`.

## Goal

Two branches are ready to ship and have each been independently verified, but neither has landed on `main`, and they touch the same function in `python/launcher.py`. This phase merges both, in the right order, with the one real collision between them resolved by hand rather than left to whatever git's auto-merge produces — then bumps the version.

## Scope

- In scope: merging `fix/ta-232-overlay-hidpi-coverage` into `main`; rebasing `ui-polish` onto the updated `main` with `ff0f276` dropped; resolving the `python/launcher.py` collision between TA-241's fix and the launcher rebuild; committing this evening's uncommitted doc work; bumping `__version__` to `1.5.0`.
- Not in scope: `TA-239`'s remaining root-cause work (blocked on a physical two-screen drag with `TESTASSIST_DEBUG=1` against a build that has the instrumentation deployed — code work is already done, only the hardware run is missing); `HW-5`'s Windows Display Settings rearrangement retest (not code — an action item for whoever is at the physical rig); any new feature work.

## Decisions (already locked, from the Launcher Evaluation Pass, 2026-09-16)

1. Accept the `ui-polish` launcher rebuild.
2. Drop `ff0f276` (`refactor(launcher): route the floating panel through the theme tokens` — the light/indigo palette change). Keep the current dark/amber palette; the amber is distinct and visible against whatever app is under test. Every other `ui-polish` commit ships.
3. `TA-247` (hiding to the tray gives no confirmation, raised from the pass's Q3) is filed as a new backlog item, not a release blocker.

## Branch inventory

| Branch | Commits ahead of `main` | What it contains |
|---|---|---|
| `fix/ta-232-overlay-hidpi-coverage` | 15 (pushed to origin) | `TA-231` pixmap-alpha fix (`3a6e4a6`), `TA-241` launcher focus-toggle fix (`d8b67b1`), `TA-232` per-screen overlay fix (`dfbb679`), `TA-239` debug instrumentation (`7d52ac1`), `TA-233`/`TA-223` bug-framing correction (`4bcb4bd`), the Launcher Evaluation Pass checklist (`ba00fac`), 2026-09-12/13/15 session-handover docs. Working tree also currently holds this evening's uncommitted doc work (below) — not yet a commit on this branch. |
| `origin/ui-polish` | 20 (from merge-base `2152cb6`) | Full launcher rebuild (`ca71881` + supporting commits), Material Icons theme, OS light/dark following, macOS build support, editor menu bar, `ff0f276`'s palette change (to be dropped). |

Uncommitted in the working tree right now (all doc-only, written from chat/Cowork per the standing agreement — Claude Code commits them, Cowork does not): `TESTASSIST_BACKLOG.md`'s TA-217 re-verification update, edits to `docs/TA-232-HARDWARE-VERIFICATION.md` and `docs/ta215-225-fix-brief.md`, and six new files `docs/ISSUE-TA-242.md` through `docs/ISSUE-TA-247.md`.

## The collision — confirmed, not assumed

Both branches rewrite the same `setWindowFlags(...)` block in `FloatingLauncher.__init__` (`python/launcher.py`):

- `fix/ta-232-overlay-hidpi-coverage`'s `d8b67b1` (closes `TA-241`) adds `| Qt.WindowType.WindowDoesNotAcceptFocus` to that block, with a comment explaining why: without it, clicking the floating toolbar's TA icon briefly makes the launcher itself the OS-active window, so `bring_forward()`'s `isActiveWindow()` check (the TA-220 minimize toggle) reads stale and fails to minimize an already-open editor.
- `ui-polish`'s `ca71881` rebuilds the entire `FloatingLauncher` class, including that exact block — diffed directly against `origin/ui-polish`, its version of the block does **not** include `WindowDoesNotAcceptFocus`, because the rebuild predates the TA-241 fix.

Confirmed by direct diff comparison (not inferred): `fix/ta-232-overlay-hidpi-coverage`'s single hunk on this file (lines 79–101 against `main`) falls inside `ui-polish`'s much larger hunk covering the same constructor region. A textual merge conflict here is expected, and even if git's merge machinery resolved it without flagging one, the rebuilt class would silently ship without the flag — reintroducing `TA-241`. `python/canvas.py` and `python/tests/test_functional.py` are the only other files both branches touch; diffed the same way, their changed regions don't overlap and are expected to merge cleanly.

## Procedure

1. On `fix/ta-232-overlay-hidpi-coverage`: commit the currently-uncommitted working-tree changes (the TA-217 backlog update, the two doc edits, and `docs/ISSUE-TA-242.md`–`TA-247.md`) as their own commit(s), following the house Conventional Commits format.
2. Merge `fix/ta-232-overlay-hidpi-coverage` into `main`. It has no dependency on `ui-polish` and has already been independently verified on hardware (per `docs/SESSION_HANDOVER_2026-09-15.md` and this evening's re-verification pass).
3. Create a new branch off `origin/ui-polish` (e.g. `ui-polish-rebased`) rather than rewriting `ui-polish` in place — see Rollback below for why. On the new branch, interactive-rebase onto the updated `main`, dropping `ff0f276`.
4. At the `python/launcher.py` conflict in `FloatingLauncher.__init__`: keep `ui-polish`'s rebuilt `setWindowFlags(...)` block, but add `| Qt.WindowType.WindowDoesNotAcceptFocus` to it, carrying forward `d8b67b1`'s explanatory comment. Do not resolve this by taking either side wholesale.
5. Port or re-verify `d8b67b1`'s regression test (`test_TA241_launcher_does_not_accept_focus`) against the rebuilt `FloatingLauncher` — confirm it still exists and still passes after the rebase, not just that the file merged without conflict markers.
6. Run the full suite. Expect only the 3 pre-existing `RegisterHotKey` Win32-conflict failures already known and excluded elsewhere (per `d8b67b1`'s own commit message: "343 passed, only the 3 pre-existing... failures"). Any other failure is a real regression from the rebase and blocks the merge.
7. Bump `python/main.py`'s `__version__` to `"1.5.0"`; regenerate `version_info.txt` via `python/generate_version_info.py` and confirm `help.html`'s stamped version follows.
8. Update `TESTASSIST_BACKLOG.md`: close out `TA-241`, `TA-231`, and this build's `TA-232`; leave `TA-217` open (reopened per this evening's re-verification — the button path is still a no-op); carry `TA-239` and `HW-5` forward as explicitly open, not blockers.
9. Merge `ui-polish-rebased` into `main`.

## Rollback procedure

1. Step 2 (`fix/ta-232-overlay-hidpi-coverage` → `main`) merges an already independently-verified branch — if something is later found wrong with it, `git revert` the merge commit (or `git reset` if not yet pushed).
2. Doing the rebase on a new branch (`ui-polish-rebased`) rather than in place means the original `ui-polish` ref is never touched. If the rebase or the collision resolution goes wrong, delete `ui-polish-rebased` and start over from `origin/ui-polish` at no cost.
3. Before merging `ui-polish-rebased` into `main`, tag `main`'s tip (e.g. `git tag pre-1.5.0-merge`). If a problem is caught before pushing further, `git reset --hard pre-1.5.0-merge`; if already pushed, `git revert -m 1 <merge-commit>`.
4. Do not attempt a partial unpick of individual commits from either branch after they've merged — the two branches are now interdependent at the `launcher.py` collision point, and the evaluation pass's own rejected "Reject the rebuild" option already documented exactly this risk (`5c5e0a1`'s dangling `_btn_record` reference raising `AttributeError` on startup if unpicked without its dependents). A bad merge is undone wholesale, not piece by piece.

## Acceptance / Exit Criteria

- `git log main` contains both branches' work, `ff0f276` absent, and a clean, deliberate resolution of the `launcher.py` collision with `WindowDoesNotAcceptFocus` present in the rebuilt `FloatingLauncher`.
- Full test suite passes except the 3 known pre-existing `RegisterHotKey` failures — no others.
- Manual repro on real hardware: clicking the floating toolbar's TA icon a second time, while the editor is already open and frontmost, minimizes it (TA-241's original repro, re-run against the rebuilt launcher specifically).
- The built app reports version `1.5.0` in its window title and About dialog.
- `TESTASSIST_BACKLOG.md` reflects final status for `TA-241`, `TA-231`, `TA-232` (closed), `TA-217` (open/reopened), and explicitly carries `TA-239` and `HW-5` forward as open, not blocking this release.
- `docs/ISSUE-TA-242.md` through `TA-247.md` and the current Launcher Evaluation Pass content are committed, not just present in the working tree.
