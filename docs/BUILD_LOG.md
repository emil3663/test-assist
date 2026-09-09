# Build log

Dated entries recording exactly what was built, its real hash, and where it
was installed — so "which binary is this" never again has to be inferred
from a version string that hasn't changed since 1.3.0 (see
`docs/SESSION_HANDOVER_2026-09-09.md`'s "Build identity" section for why
that string alone cannot tell you).

---

## rc3 — 2026-09-09

Built per `docs/rc3-build-and-install-brief.md`, executed in full.

**Source:** `origin/main` at `3fbe4c287cc7838b0cf4a69c7f4cd2cfaed84fb6` (`3fbe4c2`)
— pushed this session (`aa93bb3..3fbe4c2`). `git log -1` on the pushed ref
matches `3fbe4c2` exactly. CI (`Python Tests`, `.github/workflows/python-tests.yml`,
`windows-latest`) confirmed **green** on this exact commit before building —
[run 34305421541](https://github.com/emil3663/test-assist/actions/runs/34305421541),
conclusion `success`, `headSha` `3fbe4c287cc7838b0cf4a69c7f4cd2cfaed84fb6`.

Contains both commits that predate every prior build: `6468591`
(single-instance handoff) and `3fbe4c2` (TA-211 global hotkeys).

**Build command:** `.\build.ps1 -Zip -Shortcut` from `python\`, venv active.
The build's own self-check passed (`Built and verified: Test Assist 1.3.0`,
ffmpeg resolved, SSL backend `schannel`).

**Hash verification — this build genuinely differs from the stale rc2:**

| | rc2 (stale, built before `6468591`/`3fbe4c2`) | rc3 (this entry) |
|---|---|---|
| md5 | `9c2ecf4dd35356af2c8062bff9a9d762` | `481ffa8d588ed8b15ee7455e119ac136` |
| size (bytes) | 2,266,091 | 2,277,554 |
| exe mtime | 2026-09-09 00:58 | 2026-09-09 05:04:46 |

Not taken on faith: `python\build\TestAssist\xref-TestAssist.html` (PyInstaller's
own module cross-reference for *this* build) was grepped directly and lists
`global_hotkeys` / `global_hotkeys.py` — proof the TA-211 module was actually
analyzed into this exe, not just that the hash happened to differ.

**Artifacts:**
- Built folder: `python\dist\TestAssist\` (exe md5 `481ffa8d588ed8b15ee7455e119ac136`, 2,277,554 bytes)
- Zip: `python\dist\TestAssist-1.4.0-rc3-win64.zip` (renamed from the `TestAssist-1.3.0-win64.zip` `build.ps1` produced — `__version__` is still `1.3.0`, deliberately, until the manual pass is green)
- Desktop shortcut: `C:\Users\MSI workstation\Desktop\Test Assist.lnk` (from `-Shortcut`)

**Installed at:** `C:\TestAssist\TestAssist-1.4.0-rc3(09092026)\TestAssist.exe`
— a new dated subfolder, matching the naming convention already used by the
other builds already sitting in `C:\TestAssist\` (`TestAssist-1.4.0-rc(08092026)`,
`TestAssist-1.3.0(09092026)`, etc.). Nothing existing was renamed or moved;
`C:\TestAssist` is a container of dated builds plus manual-pass reference
files, not itself a flat install, so the brief's literal
`Rename-Item "C:\TestAssist" ...` step did not apply as written — confirmed
with the user before installing. Installed copy's md5 checked directly
against the build output: **identical** (`481ffa8d588ed8b15ee7455e119ac136`).

No `TestAssist` process was running at install time (checked via `tasklist`
before copying), so there was nothing to close per S-1.

**Unblocks** (per the brief): DSP-18, PKG-03, PKG-05, UPD-12, REC-console,
DSP-15, DSP-16, LCH-13 — none of these run results are recorded here; running
them is a manual step for whoever performs the pass, against
`C:\TestAssist\TestAssist-1.4.0-rc3(09092026)\TestAssist.exe` specifically
(not rc1, not rc2), same as `MULTI_DISPLAY_MANUAL_PASS.md` already records
INS-02's outcome.

---

## rc4 — 2026-09-09

Built per `docs/ta214-220-fix-brief.md`, executed in full (all seven tickets:
TA-214, TA-215, TA-216, TA-217, TA-218, TA-219, TA-220).

**Source:** `origin/main` at `a795b6f2c3abf0a0723206801adbaf33dcb6b519` (`a795b6f`)
— pushed this session (`fe7e801..a795b6f`, five new commits: `12c5385`,
`009798b`, `c7d1ee3`, `7408ecc`, `a795b6f`). `git rev-parse HEAD` matches
`a795b6f` exactly, working tree clean. CI (`Python Tests`,
`.github/workflows/python-tests.yml`) confirmed **green** on this exact
commit before building —
[run 34317885494](https://github.com/emil3663/test-assist/actions/runs/34317885494),
conclusion `success`, `headSha` `a795b6f2c3abf0a0723206801adbaf33dcb6b519`.

**Build command:** `.\build.ps1 -Zip -Shortcut` from `python\`, venv active.
The build's own self-check passed (`Built and verified: Test Assist 1.3.0`,
ffmpeg resolved, SSL backend `schannel`).

**Hash verification — this build genuinely differs from rc3:**

| | rc3 (stale, predates this batch) | rc4 (this entry) |
|---|---|---|
| md5 | `481ffa8d588ed8b15ee7455e119ac136` | `3f040048c6fdd3a466f1359d9678cfb5` |
| size (bytes) | 2,277,554 | 2,281,414 |
| exe mtime | 2026-09-09 05:04:46 | 2026-09-09 08:12 |

**Artifacts:**
- Built folder: `python\dist\TestAssist\` (exe md5 `3f040048c6fdd3a466f1359d9678cfb5`, 2,281,414 bytes)
- Zip: `python\dist\TestAssist-1.4.0-rc4-win64.zip` (renamed from the
  `TestAssist-1.3.0-win64.zip` `build.ps1` produced — `__version__` is still
  `1.3.0`, deliberately, until the manual pass is green)
- Desktop shortcut: `C:\Users\MSI workstation\Desktop\Test Assist.lnk` (from `-Shortcut`)

**Installed at:** `C:\TestAssist\TestAssist-1.4.0-rc4(09092026)\TestAssist.exe`
— a new dated subfolder, same convention as rc3. Nothing existing was
renamed or moved. No `TestAssist` process was running at install time
(checked via `tasklist` before copying), so there was nothing to close per
S-1. Installed copy's md5 checked directly against the build output:
**identical** (`3f040048c6fdd3a466f1359d9678cfb5`).

**Per-ticket status:**
- **TA-219** (save dialogs defaulted to the install folder) — fixed:
  `_save_png()`/`_export_json()` now default to `paths.recordings_dir()`.
  Tests added, verified to fail pre-fix.
- **TA-220** (TA taskbar icon did not toggle minimize) — fixed:
  `bring_forward()` now checks `isActiveWindow()`/`isMinimized()` and calls
  `showNormal()` before re-showing. Tests added, verified to fail pre-fix.
- **TA-214** (no way to open or paste an image into the Editor) — fixed:
  new 📂 Open Image toolbar button (reuses `load_image_path()`) and a
  `Ctrl+V` paste shortcut, guarded against empty clipboard and in-progress
  text annotation. Tests added, verified to fail pre-fix.
- **TA-216** (captures not auto-persisted to History) — fixed: new
  `EditorWindow.record_capture()`, wired from the launcher's
  `_on_capture_ready()`, kept separate from `load_pixmap()` so merely
  viewing an existing image does not create duplicate History entries.
  Tests added, verified to fail pre-fix.
- **TA-217, confirmed case** (About dialog blocks global-hotkey capture) —
  fixed: a global hotkey now calls `_dismiss_active_modal_dialog()`
  (`QApplication.activeModalWidget()` + `.close()`) before dispatching.
  Test added (with a spy + a 2s force-close safety net so a regression
  fails fast instead of hanging), verified to fail pre-fix.
- **TA-217, Properties-dialog sub-case** — **not attempted**: repro-first
  per the brief; no repeatable repro could be established in this
  environment (needs real interactive input this environment does not
  have). Left unfixed, reported plainly rather than guessed at.
- **TA-215, docked-recording feedback** — fixed: the docked capture button
  now swaps to a stop icon and shows a live `mm:ss` label while recording.
  Tests added, verified to fail pre-fix.
- **TA-215, PKG-05 sub-item** (docked Properties-dialog capture) — **not
  attempted**: same repro-first reasoning as TA-217's sub-case, no
  repeatable repro established.
- **TA-218** (unrecognizable update icon, launcher-only reachability) —
  fixed: redesigned `_make_update_icon()` to a circular refresh-arrow glyph
  (visually verified via a rendered PNG), and added a Check for Updates
  toolbar button on the Editor that reuses the launcher's own
  `_check_for_updates()`/`UpdateChecker`. Tests added, verified to fail
  pre-fix.

**Full suite:** 307 passed, 0 skipped, 0 failed — includes the TA-211
hotkey tests running for real (a leftover running `TestAssist.exe`, PID
3292, was found holding the global hotkeys during this session and closed
before the final run).

**What this unblocks:** TA-214, TA-216, TA-219, TA-220, TA-215's
docked-recording feedback, TA-217's About-dialog capture, and TA-218's icon
are re-testable manually against
`C:\TestAssist\TestAssist-1.4.0-rc4(09092026)\TestAssist.exe`. Everything
needing the second monitor or a clean machine stays blocked, as do
TA-217's and TA-215's repro-first sub-items (no repro found with what was
tried).
