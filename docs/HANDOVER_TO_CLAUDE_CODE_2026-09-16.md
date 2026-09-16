# Handover to Claude Code — land 1.5.0 (fix branch + ui-polish rebuild)

**Repo:** `C:\Users\MSI workstation\source\repos\test-assist`
**Current branch:** `fix/ta-232-overlay-hidpi-coverage`, HEAD `61d2607`, up to date with origin.
**Also relevant:** `origin/ui-polish` (20 commits ahead of the merge-base, not checked out locally).

**Working agreement:** this handover and everything it references were written from chat/Cowork, not committed. Claude Code in VS Code is the sole git driver for this repo — all commits, merges, rebases and the version bump below go through Claude Code, not Cowork.

**Read first:** `docs/RELEASE_1.5.0_PLAN.md`. It has the full branch inventory, the confirmed `python/launcher.py` collision (diffed directly, not assumed), the merge order, and the rollback procedure. This handover is just the ordered task list — the plan doc is the source of truth for *why*; don't re-derive it.

## Do these, in order

### 1. Commit tonight's uncommitted doc work on `fix/ta-232-overlay-hidpi-coverage`

Currently sitting in the working tree, not yet a commit:
- Modified: `TESTASSIST_BACKLOG.md` (TA-217 re-verification — button path still broken, hotkey path now confirmed to dismiss+capture but never able to capture the About dialog itself), `docs/TA-232-HARDWARE-VERIFICATION.md`, `docs/ta215-225-fix-brief.md`.
- New: `docs/ISSUE-TA-242.md` through `docs/ISSUE-TA-247.md`, `docs/RELEASE_1.5.0_PLAN.md`.

Commit these (doc-only, Conventional Commits, one or more commits as makes sense grouped by topic) before doing anything else, so they land as part of this branch's history rather than getting lost in the merge.

### 2. Merge `fix/ta-232-overlay-hidpi-coverage` into `main`

No dependency on `ui-polish`; already independently verified on hardware. Straightforward merge.

### 3. Rebase `ui-polish` onto the updated `main`, on a new branch

Per the plan doc: create `ui-polish-rebased` off `origin/ui-polish` rather than rewriting `ui-polish` in place (cheap rollback if the rebase goes wrong — see the plan's Rollback section). Interactive-rebase onto the post-merge `main`, dropping `ff0f276` (the palette commit — evaluation pass decision was accept-the-rebuild-drop-the-palette).

### 4. Resolve the `python/launcher.py` collision by hand

At the `setWindowFlags(...)` conflict in `FloatingLauncher.__init__`: keep `ui-polish`'s rebuilt block, add back `| Qt.WindowType.WindowDoesNotAcceptFocus`, and carry forward `d8b67b1`'s explanatory comment (TA-241 — without this flag, clicking the TA icon steals OS activation from the editor and `bring_forward()`'s minimize toggle reads stale). Do not resolve by taking either side wholesale — confirmed by direct diff that `ui-polish`'s version doesn't have the flag because the rebuild predates the fix.

### 5. Confirm the TA-241 regression test survived

`test_TA241_launcher_does_not_accept_focus` (added in `d8b67b1`) needs to exist and pass against the rebuilt `FloatingLauncher`, not just merge without conflict markers.

### 6. Run the full suite

Expect only the 3 pre-existing `RegisterHotKey` Win32-conflict failures already known and excluded elsewhere. Anything else is a real regression from the rebase — stop and investigate before continuing.

### 7. Bump the version

`python/main.py`'s `__version__` → `"1.5.0"`. Regenerate `version_info.txt` via `python/generate_version_info.py`; confirm `help.html`'s stamped version follows.

### 8. Update `TESTASSIST_BACKLOG.md`

Close `TA-241`, `TA-231`, and this build's `TA-232`. Leave `TA-217` open (reopened this evening — button path still a no-op). Carry `TA-239` and `HW-5` forward explicitly as open, not blockers for this release.

### 9. Merge `ui-polish-rebased` into `main`

Tag `main`'s pre-merge tip first (`pre-1.5.0-merge`) per the plan's rollback procedure.

## Still open, not blocked on this release

- **`TA-239`** — instrumentation is in place (`capture.py::_grab()`, gated by `TESTASSIST_DEBUG=1`) but not yet exercised: needs a real cross-screen drag on hardware once a build with this code is deployed.
- **`HW-5`** — not code. Whoever's at the physical rig needs to close the 384px gap in Windows Display Settings between the two screens, then retest.

## After this

Once `main` has both branches merged, the collision resolved, tests green, and `__version__` at `1.5.0`, this release is done. `TA-239` and `HW-5` carry forward to whatever comes after 1.5.0.
