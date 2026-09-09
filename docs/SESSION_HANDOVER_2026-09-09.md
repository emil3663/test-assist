# Session handover — 2026-09-09

Written so a new conversation can pick this up without re-deriving anything.
Read this first, then the documents it points at. Where this file and a
conversation disagree, this file and the repository win.

---

## 1. Current state

- **HEAD:** `734dfe7`, pushed. `origin/main` level with local.
- **`__version__`:** still `1.3.0`, deliberately. Not bumped, not tagged.
- **Latest build:** `python\dist\TestAssist\` — exe md5 `9c2ecf4d`.
  Zipped as `python\dist\TestAssist-1.4.0-rc2-win64.zip`.
- **Installed for testing:** `C:\TestAssist\TestAssist-1.4.0-rc(08092026)\`
  (rc1, md5 `85e1556d`). rc2 has not been installed yet.
- **Uncommitted:** the `MULTI_DISPLAY_MANUAL_PASS.md` INS-02 result, and
  `docs\PHASE_4_DECISION_RECORD.md`.

### Build identity — read this before testing anything

Every build since 1.3.0 still reports **1.3.0**, so the version string cannot
tell you which binary you are running. This has already cost one wasted test
cycle: a zip named `TestAssist-1.3.0-win64.zip` sitting in `C:\TestAssist` was
the real 2 September release, and unzipping it produced a failing INS-02 run
against three-week-old code.

Identify a build by these instead:

| Check | Old (2 Sep, md5 `12fade5b`) | Current |
|---|---|---|
| exe size | 1,804,298 bytes | 2,260,596+ |
| About button (ⓘ) in the editor | invisible | visible |
| Tooltip on the launcher's X | "Close Test Assist" | "Hide to tray" |

Release-candidate zips are named `-rc<n>-` for this reason. Do not produce a
zip named for a version it is not.

---

## 2. Decisions locked this session

1. **A spanning capture closes the gap between screens.** Pieces composite
   adjacently, not at their true virtual-desktop offset. A tester dragging
   across two monitors wants both screens side by side, not a coordinate-
   accurate map of a desktop with a hole in it. Vertical offsets are kept
   where screens are genuinely stacked. See `CHANGELOG.md` and `TA-209` for
   the residual case.
2. **The launcher's X hides to the tray.** `Exit` in the tray menu is the
   only full quit.
3. **Recordings show their first frame with a play badge** in the history
   gallery. Thumbnails are regenerable cache in `history_dir()`, never in the
   user's evidence folder.
4. **Settings and export controls live in a full-width second toolbar row**,
   not the right panel, so History gets the height. Save PNG stays visually
   primary.
5. **A second launch hands off to the running instance** rather than quitting
   it — in progress, see section 4.
6. **Phase 4 (image viewer) is locked** in `docs\PHASE_4_DECISION_RECORD.md`:
   install to `%LOCALAPPDATA%\Programs\Test Assist`, register as a candidate
   handler only, saving an opened file never overwrites the original, editor
   dirty-state tracking is in scope, folder navigation on arrow keys.

---

## 3. Work completed this session

| Commit | What |
|---|---|
| `5bb6185` | Launcher auto-dock/undock disagreeing about the current screen (DSP-12/13/14) |
| `7744fc7` | Four small toolbar buttons rendering as empty shapes |
| `909baaa` | Unreadable disabled-button text, plus a contrast regression test |
| `738ac52` | Recordings listed in the history gallery |
| `d9b8f54` | help.html content pass (TA-203) |
| `e201cdb` | Closed the black band in spanning captures; resolved CAP-12 |
| `f2b8e27` | Launcher's X hides to tray instead of quitting |
| `571cb7a` | `build.ps1 -Zip` PowerShell variable-name collision |
| `71a8f1b` | Gap-closing fixed to work on whichever axis screens are separated on |
| `4cd26b9` | Planning and manual-test docs tracked in git |
| `a7a465f` | Recording thumbnails with a play badge |
| `19bbf0c` | Settings/export controls moved to a full-width row |
| `734dfe7` | "Show Launcher" button in the editor toolbar |

Suite: **278 passed, 0 skipped**, verified on a clean clone from GitHub.

---

## 4. Outstanding, in order

### 4.1 In progress
- **argv hand-off and single-instance.** `main.py` reads `sys.argv` only for
  `--version` and `--selftest`, so "Open with → Test Assist" is ignored.
  Worse: `SingleInstanceManager.acquire()` unconditionally sends `QUIT` to any
  running instance, so a second launch silently kills the running app — and
  nothing tracks the editor as modified, so unsaved annotation work is lost
  with no prompt. **This is the only outstanding item that can destroy the
  user's work.** A second launch must hand the file path to the running
  instance over the existing local socket and exit; QUIT-and-replace survives
  only as a fallback when the handshake fails, so a hung instance is still
  recoverable.

### 4.2 Then
- Commit the two uncommitted files above.
- Rebuild, install rc3, and run the manual pass.
- **26 manual checks remain unrun** — see `MULTI_DISPLAY_MANUAL_PASS.md`.
  Most need the second monitor, which was disconnected at the end of this
  session. The single-screen ones that can be done now: DSP-18, PKG-03,
  PKG-05, UPD-12, REC-console.
- DSP-04 (secondary **above**) deserves particular attention: it is the
  configuration that nearly shipped broken, caught only by an independent
  layout probe rather than by the test suite.
- Only when the pass is green: bump `__version__` to 1.4.0, regenerate,
  tag, release, and reply on GitHub issue #1.

### 4.3 Backlog, not now
- `TA-209` — `plan_capture()` still leaves unpainted regions for layouts
  separated on both axes (a corner-touching diagonal pair, or three screens
  in an L). Single-axis packing cannot close both gaps; a real fix needs
  row/column packing.
- Region-selected video recording; canvas padding around the image.
- Phase 4, the image viewer.

---

## 5. How this session worked

Worth keeping, because it caught things the test suite did not.

- **Reports from the implementing agent were verified, not accepted.** Every
  "done" was checked by cloning from GitHub, running the suite independently,
  and reverting the fix to confirm its test genuinely fails. This caught a
  fix that only worked on one axis, and confirmed several that did hold.
- **Claims were measured, not reasoned about.** Template matching to locate a
  capture inside a known screenshot; extracting video frames to prove which
  screen was recorded; hashing binaries to prove which build was installed;
  laying the window out at its minimum size to measure real button geometry.
  Every time a hypothesis was argued instead of measured this session, it was
  wrong — including a confident and entirely incorrect root-cause analysis of
  the displaced captures.
- **Work was handed to Claude Code as written briefs**, committed into the
  repo rather than pasted into chat, because briefs delivered only into a
  conversation do not reach disk and cannot be found later.

---

## 6. Document map

| File | What it holds |
|---|---|
| `CHANGELOG.md` | Every fix, with why it was wrong and how it was verified |
| `DESKTOP_TEST_PLAN.md` | Case definitions, IDs, expected results |
| `DESKTOP_STABILITY_MATRIX.md` | What is automatable, what is Blocked, and twelve numbered defect narratives |
| `MULTI_DISPLAY_MANUAL_PASS.md` | The manual pass, grouped by monitor configuration; 26 checks outstanding |
| `TESTASSIST_BACKLOG.md` | TA-201 … TA-209 |
| `docs/PHASE_4_DECISION_RECORD.md` | Image-viewer phase, locked |
| `docs/PRE_BUILD_HANDOVER.md` | Superseded by this file |
| `docs/screens.py`, `docs/coord_probe.py` | Diagnostic scripts for multi-display geometry |
