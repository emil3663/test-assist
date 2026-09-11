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

---

## TA-211 test guard — 2026-09-09

Built per `docs/ta211-test-guard-brief.md`, executed in full. Test-only —
no build/install step, nothing in `python\dist\` changes.

Added `@pytest.mark.skipif(sys.platform != "win32", reason="RegisterHotKey
is a Win32 API")` to exactly the five tests that call
`ctypes.windll.user32.RegisterHotKey`/`UnregisterHotKey` directly:
`test_TA211_global_hotkeys_register_and_are_advertised`,
`test_TA211_global_hotkey_dispatch_routes_to_the_right_action`,
`test_TA211_an_unrelated_native_message_is_ignored`,
`test_TA211_a_failed_registration_is_surfaced_and_not_advertised`,
`test_TA211_hotkeys_are_released_on_close`. Left
`test_TA211_hotkeys_are_not_touched_without_opting_in` and the TA-217
hotkey test unguarded, per the brief — both use
`register_global_hotkeys=False` and never touch the real API.

**Windows suite, guard in place:** 307 passed, 0 skipped — identical to
rc4's count; the guard is inert here, exactly as expected.

**Off-Windows skip verified for real, not just asserted by reasoning:** no
non-Windows shell was available in this environment (no WSL Linux distro
installed — only the `docker-desktop` internal one — and the Docker
daemon itself was not running, so a container run wasn't possible either).
Instead of asserting the `sys.platform` check "would work," the exact
failure mode was reproduced directly: a standalone pytest file used
`monkeypatch.delattr(ctypes, "windll")` (removing the real attribute that
Linux/macOS lack, not a mock) to prove two things under real
`pytest.mark.skipif` machinery in the same run — (1) without the guard,
the test body hits a genuine `AttributeError` exactly as the brief
describes, and (2) with the guard's condition forced `True` (simulating
`sys.platform != "win32"`), pytest reports the test as **skipped** and the
crashing line never executes at all (a trailing `assert False` placed
after it was never reached). 1 passed (the crash case), 1 skipped (the
guarded case) — confirms the mechanism, not just the syntax.

**Commit:** `7bf77ee` (test-only change, on top of `8aed866`).

---

## rc5 — 2026-09-09

Built per `docs/ta215-225-fix-brief.md`, executed in full (TA-215, TA-217,
TA-220 through TA-225 — eight tickets, three confirmed fixes reopened from
rc4, two small layout fixes, four investigate-first items instrumented
with logging, one deferred).

**Source:** `origin/main` at `5783f8dc2e32390fa778307d2cfc3d37c428ef1d`
(`5783f8d`) — pushed this session (`77029f2..5783f8d`). `git rev-parse HEAD`
matches `5783f8d` exactly, working tree clean. CI (`Python Tests`,
`.github/workflows/python-tests.yml`) confirmed **green** on this exact
commit before building —
[run 34337047970](https://github.com/emil3663/test-assist/actions/runs/34337047970),
conclusion `success`, `headSha` `5783f8dc2e32390fa778307d2cfc3d37c428ef1d`.

**Build command:** `.\build.ps1 -Zip -Shortcut` from `python\`, venv active.
The build's own self-check passed (`Built and verified: Test Assist 1.3.0`,
ffmpeg resolved, SSL backend `schannel`).

**Hash verification — this build genuinely differs from rc4:**

| | rc4 (stale, predates this batch) | rc5 (this entry) |
|---|---|---|
| md5 | `3f040048c6fdd3a466f1359d9678cfb5` | `94124e37bdc2eed2444b3b83ae3ea88e` |
| size (bytes) | 2,281,414 | 2,284,303 |
| exe mtime | 2026-09-09 08:12 | 2026-09-09 11:53 |

Not taken on faith: `python\build\TestAssist\xref-TestAssist.html` (this
build's own module cross-reference) was grepped directly and lists
`debug_log` — proof the new logging module was actually analyzed into
this exe, not just that the hash happened to differ.

**Artifacts:**
- Built folder: `python\dist\TestAssist\` (exe md5 `94124e37bdc2eed2444b3b83ae3ea88e`, 2,284,303 bytes)
- Zip: `python\dist\TestAssist-1.4.0-rc5-win64.zip` (renamed from the
  `TestAssist-1.3.0-win64.zip` `build.ps1` produced — `__version__` is
  still `1.3.0`, deliberately, until the manual pass is green)
- Desktop shortcut: `C:\Users\MSI workstation\Desktop\Test Assist.lnk` (from `-Shortcut`)

**Installed at:** `C:\TestAssist\TestAssist-1.4.0-rc5(09092026)\TestAssist.exe`
— a new dated subfolder, same convention as rc3/rc4. Nothing existing was
renamed or moved. No `TestAssist` process was running at install time
(checked via `tasklist` before copying), so there was nothing to close per
S-1. Installed copy's md5 checked directly against the build output:
**identical** (`94124e37bdc2eed2444b3b83ae3ea88e`).

**Per-ticket status:**
- **TA-220** — confirmed part fixed: `bring_forward()` now checks
  `Qt.WindowState.WindowMaximized` before restoring, calling
  `showMaximized()` instead of unconditionally `showNormal()`; a maximized
  Editor minimized then restored now comes back maximized. Test added,
  verified to fail pre-fix. Minimize-toggle-not-firing gap:
  **instrumented, not fixed** — `bring_forward()` logs
  `isActiveWindow()`/`isMinimized()` on every call when `TESTASSIST_DEBUG=1`,
  writing to `paths.history_dir()/debug.log` (`%LOCALAPPDATA%\Test
  Assist\history\debug.log` on a real install). No second monitor/
  interactive session here to confirm the `isActiveWindow()` timing
  hypothesis — needs a real click on the actual hardware.
- **TA-221** — fixed: removed `_btn_copy`/`_btn_export_json`'s
  `setFixedHeight(26)` rather than bumping it; both now size naturally at
  28px, matching `_btn_save_png`'s already-proven-clear height. Test added
  (checks `maximumHeight()` is uncapped), verified to fail pre-fix. Could
  **not** get the ticket's own asked-for rendered-screenshot confirmation
  in this environment — the offscreen Qt platform used for headless tests
  has no real font rendering available (glyphs render as tofu boxes, not
  usable to confirm clipping is gone); the measurement-based proxy
  (natural height now exactly matches Save PNG's already-unclipped 28px)
  is strong but not the literal visual check the ticket asks for — needs
  a real screenshot from the installed build.
- **TA-222** — fixed: added the settings bar's missing leading
  `layout.addStretch()`, matching the tools bar's centering pattern. Test
  added, verified to fail pre-fix.
- **TA-217** — confirmed part fixed: `_dismiss_active_modal_dialog()` is
  now also called from the Quick Capture button's own click handler, not
  just the hotkey path. Test added, verified to fail pre-fix.
  Hotkey-path-doesn't-capture gap: **instrumented, not fixed** —
  `_dismiss_active_modal_dialog()` logs whether it found a modal;
  `_start_capture()` logs when its overlay-activation `singleShot`
  actually fires. Same `TESTASSIST_DEBUG=1` / `debug.log` location as
  above.
- **TA-215** — confirmed parts fixed: `_on_record_finished()` now calls
  the editor's new public `refresh_history()`, so a finished recording
  appears in History live instead of only after a restart; the docked
  capture icon now shows a distinct appearance when Video mode is
  selected but not yet recording (reuses the existing `_make_video_icon()`
  glyph). Tests added for both, verified to fail pre-fix.
- **TA-223** — **instrumented, not fixed** (P1, but genuinely needs the
  real dual-monitor hardware to measure, not another guess): `capture.py`'s
  `mouseMoveEvent()` now logs the raw `event.globalPosition()` value
  alongside both screens' `QScreen.geometry()` on every drag move, gated
  behind `TESTASSIST_DEBUG=1`, written to `paths.history_dir()/debug.log`.
  The next manual pass dragging across the laptop/external boundary with
  this build will produce the coordinate log needed to confirm or rule out
  the DPI-rounding hypothesis.
- **TA-224** — **deferred past 1.4.0**, decision recorded on the ticket in
  `TESTASSIST_BACKLOG.md` (net-new capability, not a bug; 1.4.0's scope has
  already grown from 7 to 16 tickets). No code change.
- **TA-225** — **instrumented, not fixed**, same reasoning as TA-223:
  `capture.py`'s `_grab()` now logs the dragged rect and what
  `plan_capture()` received/returned for it, same env var and log file.
  Possibly the same mechanism as TA-223 — the next manual pass's log
  output for both will show whether they share a cause.

**Debug logging convention used:** a new `debug_log.py` module (no
existing app-wide logging module existed to reuse) — `debug_log.log(msg)`,
gated on `os.environ.get("TESTASSIST_DEBUG") == "1"` (checked per call,
not cached, so it can be toggled without restarting), appends a
timestamped plain-text line to `paths.history_dir() / "debug.log"` — the
same app-managed-cache location `paths.py` already designates for
non-Documents data. On a real install this resolves to
`%LOCALAPPDATA%\Test Assist\history\debug.log`. To capture the next
manual pass's measurements: set `TESTASSIST_DEBUG=1` before launching
`TestAssist.exe`, reproduce TA-220/TA-217/TA-223/TA-225's cases, then read
that file.

**Full suite:** 320 passed, 0 skipped, 0 failed. Every new/changed test
verified to genuinely fail against the pre-fix code first (production
files reverted to HEAD, confirmed real failures, then restored) — 12
new/changed tests failed pre-fix as expected; a 13th
(`test_TA215_a_recording_with_nothing_captured_does_not_refresh_history`)
is a pinning test for an already-correct early-return path and correctly
passed both before and after.

**What this unblocks:** TA-220's maximize-restore, TA-221's button text,
TA-222's row alignment, TA-217's button-path dismiss, and TA-215's
History-refresh-on-finish and video-mode icon are all re-testable manually
against `C:\TestAssist\TestAssist-1.4.0-rc5(09092026)\TestAssist.exe`
(single monitor is enough for all five). Still blocked on the second
monitor: TA-220's minimize-toggle gap, TA-217's hotkey-capture gap,
TA-223, and TA-225 — this batch instruments them but doesn't fix them; the
actual fix is a follow-up ticket once the `debug.log` output from the next
manual pass is in hand. TA-224 stays deferred past 1.4.0 per the decision
above unless overridden.

---

## TA-226 — real-font-rendering visual test lane — 2026-09-09

Built per `docs/ta226-visual-test-lane-brief.md`, executed in full.
Test/CI infrastructure only — no app code changed, nothing in
`python\dist\` differs, no new `rc` build.

**Source:** `origin/main` at `41bd84437dd3437be29e4c3a3a5725651fd920f4`
(`41bd844`) — pushed this session (`7ff53f3..41bd844`). CI confirmed
**green** on this exact commit —
[run 34341689925](https://github.com/emil3663/test-assist/actions/runs/34341689925),
conclusion `success`, both jobs reported by CI itself (not asserted from
the workflow file alone):
[`test`](https://github.com/emil3663/test-assist/actions/runs/34341689925/job/102433712117)
succeeded in 1m1s, and the new
[`visual`](https://github.com/emil3663/test-assist/actions/runs/34341689925/job/102433711803)
job succeeded in 46s.

**Assertion mechanism chosen: bounding-box/ink-extent against a real
`QWidget.grab()` screenshot, not a pixel-diff golden image.** A golden
image is brittle to font-hinting/ClearType/DPI drift whenever the CI
runner's Windows or font-package version changes underneath it, needing
re-capture for reasons that have nothing to do with a real regression;
measuring where the ink actually falls relative to the widget's own
rendered rect is closer to what "not clipped" literally means and keeps
working across a font-rendering change that isn't a bug.

**CI wiring:** a new `visual` job in
`.github/workflows/python-tests.yml`, separate from the existing `test`
job (not a step inside it), `runs-on: windows-latest` with
`QT_QPA_PLATFORM: windows` (not left unset — `conftest.py`'s
`os.environ.setdefault` fills in `offscreen` otherwise) and
`continue-on-error: true`, so a failure here can never block anything
gating on the workflow's overall conclusion; only the `test` job's own
status does that. Runs `python -m pytest -q -m visual`.

**Main suite confirmed unaffected:** `320 passed, 0 skipped (2
deselected)` — identical to rc5's count. A new `python/pytest.ini` sets
`addopts = -m "not visual"` so the new marker is excluded from the
default run everywhere (local dev and the `test` job) without needing an
environment-based skip, which would have shown up as an unwanted
"skipped" instead of a clean deselection (tried first, corrected after
measuring the actual summary line).

**Real font rendering confirmed, not just claimed — with real measured
values:** the CI log for the `visual` job's "Run visual regression
tests" step shows `env: QT_QPA_PLATFORM: windows` and
`2 passed, 320 deselected in 4.15s`, i.e. actually running on the
runner's real Windows font stack, not offscreen. Local measurement while
writing the test (`tests/test_visual.py`'s real `QWidget.grab()`
screenshots, same machine class as CI):
- `_btn_copy`/`_btn_export_json` (current/shipped code): ink spans rows
  14–27 of a 38px-tall real render, 10–14px of clear background margin
  above and below — not touching either edge.
- The button's own `border: 1px solid` (theme.LINE_STRONG) measured a
  combined RGB distance of ~95–104 from the background on every row (it
  runs the full height on both edges) — real text (theme.MUTED) measured
  ~271–340 on the same render, which is what the ink-extent threshold
  (160) is tuned to sit between.

**Honest gap found while verifying, not hidden:** Task item 3 asked to
verify the retrofitted test fails against the old `setFixedHeight(26)`
code and passes against current code. Reverting to `setFixedHeight(26)`
on this machine's real font rendering does **not** reproduce visible
clipping — measured at 12 ink rows out of a 14-row unclipped maximum,
**identical** to `_btn_save_png`'s own untouched `setFixedHeight(28)`
(already treated as fine by the original ticket). A height sweep from 14
to 34px on a plain `QPushButton("Copy")` with the real stylesheet applied
found: 0 ink rows at height ≤16 (Qt omits the label rather than drawing
a partial glyph), a genuinely partial glyph from height 18 up, plateauing
at the full 14-row glyph only from height 30. So height 26 sits in a
region that is measurably tighter than the natural size but not tight
enough to visibly clip *on this specific machine's font metrics* — this
is exactly the font-hinting/DPI-drift risk TA-226's own problem
statement named, encountered directly while building the fix for it, not
a flaw in the new test. Reported here rather than silently forcing a
pass/fail narrative that the real pixels didn't support.

Handled by not overstating what the retrofitted test proves: it checks
the real, literal acceptance criterion against the **code as shipped**
(passes, for real, against real rendering — the actual thing rc5 could
not do). A second test in the same file,
`test_ink_extent_detection_actually_catches_a_clipped_button`, separately
proves the detection mechanism itself catches a real, deliberately
undersized button (height 18) on this same hardware, by comparing its
ink-row count against a naturally-sized control from the same run rather
than a hardcoded number — independent of whether the specific historical
height reproduces clipping on any given machine.

**Per-test timing (`--durations=0`, warm run):** `test_TA221_...`: 0.23s.
`test_ink_extent_detection_...`: 0.13s. Noticeably slower per test than
the main suite's ~30-40ms average (real font rasterization and window
creation cost, vs. offscreen), though the absolute cost is small at two
tests — worth knowing as this lane grows, not a surprise on a later run.

**Testing-conventions note added:** `DESKTOP_STABILITY_MATRIX.md` now
documents which class of future ticket belongs in this lane
(rendering/layout — clipping, contrast, icon legibility at real size)
versus the main offscreen suite (everything else: logic, state, wiring,
geometry math).

**Commit:** `41bd844` (includes `TESTASSIST_BACKLOG.md`'s TA-226 status
update in the same commit as the test/CI changes, per the brief).

---

## TA-227 — retrofit TA-217's two dispatch tests — 2026-09-09

Built per `docs/ta227-228-e2e-testing-brief.md`, executed in full.
Test-only — no app code changes, nothing in `python\dist\` differs, no
new `rc` build.

**Source:** `origin/main` at `c0bf19741e29a9f8ae560fccb953d8bfda5f4262`
(`c0bf197`) — pushed this session. CI confirmed **green** —
[run 34344108333](https://github.com/emil3663/test-assist/actions/runs/34344108333),
both `test` (59s) and `visual` (41s) jobs succeeded.
`TESTASSIST_BACKLOG.md`'s status update committed separately and
immediately (`45792b9`, pushed ahead of the code commit) — see the note
on why at the end of this entry.

**What was wrong:** both
`test_TA217_global_hotkey_closes_an_open_about_dialog_before_capturing`
and `test_TA217_quick_capture_button_closes_an_open_about_dialog_before_capturing`
replaced `launcher._start_capture` with a call-recording lambda, then
asserted only `calls == ["start_capture"]` — proving the function ran,
not that a real, interactive capture overlay ever resulted, exactly the
gap TA-217's own ticket had already flagged about these two tests by
name.

**Retrofit:** `_start_capture` is no longer stubbed in either test. Both
let the real `220ms singleShot -> _overlay.activate()` chain run
(`QTest.qWait`, the same mechanism `test_functional.py` already uses for
this), then assert the real end state: `launcher._overlay.isVisible()`,
followed by a real press/move/release drag through the overlay confirmed
via a real `capture_ready` signal emission carrying a non-null pixmap.
The button-path test also now triggers `launcher._btn_capture.click()`
instead of calling `_on_action_click` directly, exercising Qt's real
signal/slot wiring.

**Verified to fail two independent ways, each restored after:**
1. Reverting `_dismiss_active_modal_dialog()`'s call in `_on_global_hotkey()`
   reproduces the original rc4 regression — fails on the pre-existing
   dismiss assertion (`AssertionError: the hotkey path must actually
   attempt to dismiss an open modal dialog`).
2. Keeping that call but removing `_start_capture()` itself (both the
   hotkey path's `if hotkey_id == self._HOTKEY_PHOTO:` branch and the
   button path's `_on_action_click`) fails **specifically on the new
   `isVisible()` assertion** in both cases — confirming the retrofit adds
   real, independent detection power, not just riding on the older
   dismiss check.

**Grep for the same shape, repo-wide:** searched both test files for
`lambda: ...append(...)` and every real-signal `.connect(lambda: ...)`.
Found no other instance of the flawed shape. Checked and cleared,
specifically:
- `test_TA211_global_hotkey_dispatch_routes_to_the_right_action` stubs
  `_start_capture`/`_start_full_capture`/`_toggle_recording`, but its own
  claim is narrowly "routes to the right handler" — the broader "capture
  actually works" claim is now independently covered by this retrofit.
- The two DSP-15 restore-repositioning tests stub `_position_top_right`/
  `_dock_right`, but each of those has its own real, unstubbed
  correctness test elsewhere
  (`test_launcher_position_top_right_uses_the_screen_the_widget_is_on`,
  `test_launcher_dock_right_moves_to_expected_x_position`).
- The TA-218 Editor-button test stubs `_check_for_updates`, but its own
  claim is narrowly "reaches the launcher's checker" — the checker's own
  logic is covered by UPD-01 through UPD-11.
- `QApplication.quit`/`primaryScreen` stubs are system-API-boundary
  substitutions (calling the real API would either kill the shared test
  `QApplication` or defeat the point of pinning a screen), not app-logic
  shortcuts.
- Every remaining `signal.connect(lambda: ...)` (canvas
  `annotation_changed`, `SingleInstanceManager`'s `quit_requested`/
  `show_requested`, `ScreenshotOverlay.cancelled`) is a spy on a real
  signal a real operation actually emits, not a stand-in for a mechanism.

Convention recorded in `DESKTOP_STABILITY_MATRIX.md` (new paragraph under
"What the tests run against"): a dispatch/wiring test may stub what's
downstream of the action under test, or a method whose own correctness
is independently verified elsewhere unstubbed, or observe a real signal —
never the action's own immediate, in-process effect.

**Full suite:** `320 passed, 0 skipped` (2 deselected), unaffected.

**Commit:** `c0bf197` (code/tests + convention note).
`TESTASSIST_BACKLOG.md`'s TA-227 status committed separately,
immediately, as `45792b9` — see the investigation note below.

---

## TA-228 — pywinauto black-box smoke lane — 2026-09-09

Built per `docs/ta227-228-e2e-testing-brief.md`, executed in full, with
one honest, partial result reported rather than hidden.

**Source:** `origin/main` at `1873e0b90cd22978877c34fe68db7584f7ef1b92`
(`1873e0b`) — pushed this session. CI confirmed **green** —
[run 34345914619](https://github.com/emil3663/test-assist/actions/runs/34345914619),
both `test` (54s) and `visual` (1m45s) jobs succeeded; `tests_e2e/`
correctly did not run in either (that is the point of `pytest.ini`'s new
`testpaths = tests`).

**What shipped:** `pywinauto` as a new Windows-only, dev/test-only
dependency (`python/tests_e2e/requirements.txt`, deliberately kept out of
`python/requirements.txt`). New `python/tests_e2e/` — its own
`conftest.py` (launches the exe, kills it on teardown regardless of
outcome) and `test_smoke.py` with the three scoped checks: app launches
and its window appears; Quick Capture produces a real, visible overlay
window observed via the OS's own window list; TA-icon minimize/restore
changes the real OS window state via `pywinauto`'s
`is_minimized()`/`is_normal()` (backed by UI Automation's
`WindowVisualState`), not Qt's internal flags.

**CI-vs-manual decision, recorded explicitly (`python/tests_e2e/README.md`):
stays local/manual, not wired into CI.** The ticket's own cost argument
(building an exe for three checks is more CI time than they're worth
today) held up, but a harder, measured finding surfaced while building
this made the call firmer — see below.

**Ran the three checks for real against the current build
(`python/dist/TestAssist/TestAssist.exe`, rebuilt once — see the
production-change note below, not a new numbered `rc`):**

- **Check 1 (launch, window appears): genuinely verified both ways.**
  Passes against the real build. Errors against a deliberately corrupted
  one (`python -m pytest tests_e2e -k launches` with `TESTASSIST_EXE`
  pointed at a 1000-byte-truncated copy of the real exe) —
  `pywinauto.application.AppStartError: ... CreateProcess: (193,
  'CreateProcess', '%1 is not a valid Win32 application.')` — a real,
  meaningful failure. Separately confirmed a *missing* exe correctly
  **skips** instead (the `exe_path` fixture), a different and correct
  case from a broken one.
- **Checks 2 and 3: could not be verified to pass in this environment.**
  Both fail cleanly within their own timeouts (5s / 10s) rather than
  hang — the deadline-polling loops did their job — but the reason they
  fail is not the app; it's that **no synthetic input mechanism reached
  the running app at all** while writing this lane. Tried, in order, each
  checked against a real, independent signal, not assumed:
  1. UI Automation's `Invoke` pattern on the real Quick Capture button —
     `launcher.hide()` never happened (the launcher stayed
     `is_visible() == True`).
  2. `pywinauto`'s `click_input()` (real OS `SendInput`) at the button's
     own screen coordinates, with `ctypes.windll.shcore.SetProcessDpiAwareness(2)`
     set before any UIA/COM usage — no effect.
  3. The `win32` backend's direct `PostMessage`-based click, and a raw
     `pywinauto.mouse.click()` at a checkbox control's coordinates,
     verified via the checkbox's own UI-Automation toggle-state
     (`get_toggle_state()`) read back unchanged (0 before, 0 after) — no
     effect.
  Each candidate cause checked and ruled out directly, not assumed away:
  `TESTASSIST_DEBUG=1` set on the launched process's environment (Win32
  `CreateProcess` with `lpEnvironment=NULL` inherits the caller's block —
  confirmed by reading `pywinauto.application.Application.start`'s own
  source) never produced a `debug.log` line from
  `_dismiss_active_modal_dialog()`, which logs unconditionally on every
  call; `WindowFromPoint` at the button's exact screen coordinates
  returned the launcher's own real hwnd (no unrelated window intercepting
  the click); `OpenInputDesktop` succeeded and the calling process's
  session id matched `WTSGetActiveConsoleSessionId()` (a real, attached,
  interactive desktop, not a disconnected/service session);
  `whoami /groups` showed `Mandatory Label\Medium Mandatory Level` (the
  normal, unelevated integrity level — rules out a UIPI mismatch against
  an elevated target, since nothing in this project's build requests
  elevation).
  This is the same class of environment gap as TA-220/TA-217/TA-223/
  TA-225 — not a flaw in the two tests, which are the correct design and
  will run properly once tried on a real, interactively-used Windows
  machine. Recorded here rather than claimed as passing.

**Why this sharpened the CI-vs-manual decision beyond the ticket's own
reasoning:** GitHub Actions' hosted Windows runners are themselves a
non-interactive, automated context — the same class of environment that
just failed to deliver synthetic input here. Wiring this lane into CI
today would risk automating around the assumption that a runner can
deliver real clicks at all, which is exactly what needs confirming first,
not assumed by building CI plumbing around it.

**One small production change, in service of this lane, not a UX
change:** `launcher.py`'s `_btn_open_editor` (icon-only, otherwise
indistinguishable from its unlabeled sibling buttons to UI Automation)
now has `setAccessibleName("Open Editor")`, needed for check 3 to find it
reliably from outside the process — also a genuine accessibility
improvement (a screen reader now announces it), not solely a test hook.
Required one rebuild to include (`.\build.ps1`, no `-Zip -Shortcut` —
this is a local dev build for testing this lane, not a release
candidate); full suite re-confirmed `320 passed, 0 skipped` (2
deselected) afterward.

**How to run it:** `python/tests_e2e/README.md` — needs a build first
(`python\build.ps1`), then `python -m pip install -r
tests_e2e\requirements.txt` and `python -m pytest tests_e2e` from
`python\`. Point at a specific build with `$env:TESTASSIST_EXE`.

**Commit:** `1873e0b` (code/tests/docs). `TESTASSIST_BACKLOG.md`'s TA-228
status committed separately, immediately, as `3074602` — see the
investigation note below.

### Follow-up — root cause found: a mouse-hook utility, not the environment — 2026-09-09

Per `docs/ta228-synthetic-input-investigation-brief.md`, written after a
first re-run on Emil's own real, interactive desktop reproduced the exact
same checks-2/3 failure as the original non-interactive environment — the
"needs real hardware" theory from the entry above was falsified by that
re-run (recorded on `TESTASSIST_BACKLOG.md`'s TA-228 entry, commit
`bfe1ee7`). This entry reports what the brief's three-step investigation
actually found.

**Step 0 — control test.** Notepad turned out to be the wrong control
target: modern Windows 11 Notepad is single-instance/tabbed, exactly like
TestAssist itself — a fresh launch hands off to the existing window rather
than opening a clean one, which very nearly caused a real problem: the
first attempt (`subprocess.Popen(["notepad.exe"])`) silently added a tab to
the user's own already-open Notepad window (which had real, unsaved tabs —
`Laptop.md`, `External.md`) rather than starting anything new. Caught
before any damage (only the newly-spawned orphan helper processes were
closed, by exact PID, never the user's own window), then abandoned Notepad
entirely in favor of a minimal, purpose-built Tkinter window — genuinely
separate, non-Qt, non-single-instance, a real native Win32 window
underneath, with a button whose click handler sets the window's real title
via `root.title()` (a real `SetWindowText`), read back independently of
pywinauto.

**Result: `click_input()` also failed against this plain, non-Qt window.**
Verified the click wasn't simply mistargeted first — `WindowFromPoint` at
the button's exact center returned the button's own real hwnd, and
`GetForegroundWindow()` confirmed the Tk window was genuinely focused at
click time — before concluding the click itself had no effect. Per the
brief's own branching logic, this result means the cause is **system-wide,
not Qt-specific.**

**Step 3 — win32 backend retry (run in parallel, per the brief's
sequencing).** Connected to the real, already-running TestAssist.exe
(the user's own instance from the earlier manual re-run) rather than
starting a second one — a second launch just hands off to the first and
exits (`python/tests_e2e/README.md` already documents this). The win32
backend's `child_window()` couldn't even locate Quick Capture — Qt paints
its own widgets rather than creating native child HWNDs, so there was
nothing for PostMessage-based control lookup to find, a structural fact
about Qt on Windows rather than evidence either way. Retried with a
coordinate-based click instead (the button's real screen center, read via
the UIA backend, converted to the win32 top-level window's client
coordinates, clicked via `top.click(coords=...)`): **still no effect** —
consistent with Step 0's system-wide finding.

**One level lower still, bypassing pywinauto entirely.** A raw
`SendInput` mouse *move* to an absolute screen point, verified via
`GetCursorPos` before/after: **the cursor genuinely moved to the exact
target coordinates.** The same raw `SendInput` sequence but for a button
down+up at that same point, against the Tk button, verified via the same
window-title read-back as Step 0: **zero effect.** This pinned the block
down precisely — synthetic input reaches the OS input stream and moves the
real cursor; specifically the button-press portion of it doesn't register
against a target window. That is a very different (and much narrower)
claim than "no synthetic input reaches this environment," which is what
every prior pass of this investigation had, reasonably, concluded.

**Step 2 — chasing the system-wide cause.** `Get-MpComputerStatus` showed
only Windows Defender, real-time protection on, no third-party AV/EDR
product registered in `root/SecurityCenter2`; a scan of Defender's
operational log and the Application log for the ~20 minutes around the
test runs turned up nothing relevant. A full process listing of the
interactive session, filtered down to real user-session processes,
surfaced `XMouseButtonControl.exe` — X-Mouse Button Control 2.20.5
(`C:\Program Files\Highresolution Enterprises\X-Mouse Button Control\`), a
third-party mouse-button remapper. Its entire mechanism is a system-wide
low-level mouse hook intercepting button press/release events
specifically — not movement — which is exactly the split just measured.

**Confirmed directly, with the user's explicit go-ahead before touching
anything running on their machine** (it isn't security software, but it's
real software they actively rely on, so this wasn't defaulted into): the
process was running elevated and this session's own `taskkill` came back
`Access is denied`, so the user exited it themselves. With it stopped, the
exact same raw `SendInput` click test that had just failed **now
succeeded** (`TK_TARGET_CLICKED`); pywinauto's own `click_input()` against
the same Tk window also now succeeded. Re-ran the real `pytest tests_e2e`
suite (against a freshly closed-and-relaunched `TestAssist.exe`, per its
own documented prerequisite) with XMBC still stopped:

- **Check 1 (launch): PASSED.**
- **Check 2 (Quick Capture → real overlay window): PASSED** — genuinely,
  for the first time, against the real build with no environment caveat.
- **Check 3 (TA-icon minimize/restore): FAILED — consistently, re-run
  once more to rule out a one-off flake, same failure both times.** This
  is a *different* failure than before: input now reaches the app (check 2
  proves that), so this is no longer the "nothing can click anything"
  environment gap. It is either a genuine reproduction of TA-220's own
  still-unconfirmed hypothesis (the editor's real OS window never entered
  `is_minimized()` within the 5s deadline after the TA-icon click), or an
  artifact of this specific test's own timing/focus assumptions — brief
  says explicitly not to chase TA-220's or TA-217's gaps in this pass, so
  this is reported as a real, live finding for a future ticket, not
  investigated further here.

The user relaunched X-Mouse Button Control immediately afterward (I could
only relaunch it via a normal, non-elevated `Start-Process` — since the
original instance ran elevated and I have no way to know if that was
load-bearing for it, **it's worth a quick check that its button mappings
still behave as expected**, in case it needs restarting a second time,
elevated, to fully match its prior state).

**Conclusion: root cause found and confirmed, not just ruled-out-around.**
The "no synthetic input reaches the app" finding across every earlier pass
of this investigation (original non-interactive environment, and the first
real-hardware re-run) was real, but its cause was never the
environment being non-interactive, Qt-specific, or this project's own
code — it was a third-party mouse-button remapper's system-wide low-level
mouse hook on this specific development machine, intercepting synthetic
button-press events before they reached any target window, Qt or not.
Checks 2 and 3 are, and always were, written correctly; check 2 is now
genuinely verified passing. Check 3 surfaced what looks like a real,
separate finding (TA-220's own hypothesis) worth its own follow-up ticket,
not folded into this one per the brief's explicit scope boundary.

**No change to the CI-vs-manual decision** — that call isn't reopened by
this finding (a hosted CI runner without this specific machine's
XMouseButtonControl install was never going to hit this same cause either
way, but the decision itself stands as recorded).

**No production code change.** Root-cause investigation only, per the
brief.

---

## Investigation: what has been silently reverting `TESTASSIST_BACKLOG.md` — 2026-09-09

Requested before starting the TA-227/228 work above, after this file's
uncommitted content was reported lost four times this project, including
a verification note from the TA-226 session. Reporting the honest
result: **the exact mechanism on any single occasion could not be proven
— it leaves no trace by design — but a concrete, evidence-backed leading
cause was found, and the "still don't know" list is narrower than before.**

**Ruled out, directly, not assumed:**
- `git stash list` — empty. No stash currently holding (or having
  dropped, per its own reflog) an edit to this file.
- `git reflog show stash` — errors with "unknown revision," meaning no
  stash ref has existed recently enough to leave that trail either.
- `.gitattributes`, custom `.git/hooks/*` (only the default `.sample`
  files are present), a second `git worktree` (`git worktree list` shows
  only this one checkout), and a `.vscode/settings.json` auto-save/
  format-on-save setting (it contains one unrelated Python-env-manager
  key) — none exist.
- OneDrive/known-folder redirection of the repo path — `$env:OneDrive`
  is configured on this machine, but `fsutil reparsepoint query` on the
  repo's parent (`...\source`) confirms it is a plain directory, not a
  reparse point; this folder is not inside OneDrive's sync tree.
- The specific claim "your TA-226 verification note vanished": checked
  directly — it is present, complete, in both the commit that added it
  (`5783f8d`... actually `41bd844`'s TA-226 note lands via that session's
  own commits) and the current working tree. Whatever happened
  previously, it is not currently missing.

**The leading, evidence-backed candidate:** `git fsck --unreachable
--no-reflogs` found **16 dangling stash-related commit objects** (8
`stash push`/pop or drop cycles, each leaving a `WIP on main: ...` +
paired `index on main: ...` pair behind since the reflog that would
normally reference them has expired or was cleared) — timestamped
throughout today, several landing within seconds of this project's own
batch commits (`19bbf0c`, `734dfe7`, `aa93bb3` — itself a backlog-content
commit, `009798b`, `fe7e801`). This is direct, concrete proof that
`git stash push -- <files>` was used heavily and repeatedly today (this
project's own revert-test-restore verification methodology, used in
every batch this session), not a one-off. None of those 16 dangling
commits' own diffs touch `TESTASSIST_BACKLOG.md` — ruling out "a stash
captured a backlog edit and then lost it" specifically — but that
sharpens rather than clears the real suspect: a stash that never
contained this file is exactly the setup for the mistake already caught
once this session by hand (documented earlier: `git stash push --
launcher.py` followed by a mistaken `git checkout stash@{0} --
tests/test_regressions.py`, which silently resolved to the **parent
commit's** version of that unrelated file, discarding an uncommitted
test addition with zero trace in reflog or `fsck`, since a single-file
`git checkout` never moves a ref). Given `TESTASSIST_BACKLOG.md` is
almost always being hand-edited in the *same* working session as a
code-file stash-based revert cycle for whatever ticket is in progress,
it is the single most exposed file in this repository to exactly that
mistake — and it is structurally invisible to every git forensic tool
available (reflog, `fsck`, stash list all track ref and object history,
not plain working-tree `checkout`/`restore` operations).

**Honestly still open:** this cannot be proven for any specific past
incident — by the time content is gone, there is nothing left to
inspect. An editor-level cause (a stale open buffer autosaving over
newer disk content) was considered and could not be ruled out or
confirmed from this side either, since it depends on the user's own
editor state, not anything visible here.

**What changes as a result:** every stash/checkout-from-stash operation
performed for the rest of this session avoided `TESTASSIST_BACKLOG.md`
entirely (confirmed by design, not just intention — no stash touching it
was created). Per instruction, this file is now committed **by itself,
immediately** after each edit (`45792b9` for TA-227, `3074602` for
TA-228), rather than batched with the corresponding code/test commit —
shrinking the window a loss could happen in, independent of whether the
root cause above is the true one.

## `ca71881` isolated — §6's two imprecisions confirmed, revert cost measured — 2026-09-11

`docs/VERIFICATION_2026-09-11.md` §6 audited the launcher rebuild
(`ca71881`) against branch-wide diffs and commit-body claims, but could
not isolate the commit itself. Two commands settle what that comparison
could only infer.

**`git show ca71881 --stat`:**

```
commit ca718819e15fb29f5018976a486534445f867b94
Author: Martin Hugo <m.hugo@guardian360.nl>
Date:   Fri Sep 11 12:56:53 2026 +0200

    feat(launcher): rebuild the floating panel and docked strip
    [...]

 python/launcher.py               | 801 +++++++++++++++++++--------------------
 python/tests/test_regressions.py | 229 +++++++++--
 python/theme.py                  |  12 +
 3 files changed, 596 insertions(+), 446 deletions(-)
```

`--numstat` for the per-file split:

```
392	409	python/launcher.py
192	37	python/tests/test_regressions.py
12	0	python/theme.py
```

**"launcher.py loses ~150 lines" is not true of this commit alone.**
392 insertions, 409 deletions — net **−17** for `ca71881` by itself. The
whole-branch net of −5 (already noted in §6) was the closer number; the
commit's own body overstates its own contribution by roughly 30x.

**"Eleven hand-drawn icon factories" — confirmed as ten, not eleven.**
Functions matching `_make_*icon` present in `python/launcher.py` at
`ca71881^` (i.e. immediately before the commit):

```
900:    def _style_mode_icon(active: bool) -> str:
922:    def _make_close_icon(color: str = theme.TEXT) -> QIcon:
935:    def _make_undock_icon(color: str = theme.TEXT) -> QIcon:
952:    def _make_dock_icon(color: str = theme.TEXT) -> QIcon:
967:    def _make_pencil_icon(color: str = theme.TEXT) -> QIcon:
981:    def _make_ta_icon() -> QIcon:
997:    def _make_update_icon(color: str = theme.TEXT) -> QIcon:
1018:    def _make_camera_icon(color: str) -> QIcon:
1035:    def _make_stop_icon(color: str = "#ff5050") -> QIcon:
1050:    def _make_video_icon(color: str) -> QIcon:
1065:    def _make_screen_icon(color: str) -> QIcon:
```

Ten `_make_*icon` functions, plus `_style_mode_icon` (a helper, not a
factory) — eleven functions total removed, zero remaining in
`ca71881`'s own tree. The commit body's "eleven hand-drawn icon
factories and `_style_mode_icon`" reads as eleven factories *plus* the
helper; it is ten factories plus the helper.

**The revert experiment.** `git worktree add --detach
artifacts/review/drop-test origin/ui-polish` followed by `git revert
--no-commit ca71881`:

```
Auto-merging python/launcher.py
CONFLICT (content): Merge conflict in python/launcher.py
Auto-merging python/tests/test_regressions.py
CONFLICT (content): Merge conflict in python/tests/test_regressions.py
error: could not revert ca71881... feat(launcher): rebuild the floating panel and docked strip
```

`python/theme.py` auto-merged cleanly (the 12 added theme tokens have
no later edits to conflict with). Two files do not:

- **`python/launcher.py`** — three separate conflicting hunks: lines
  194–210 (the old single "Capture Region" button vs. the new
  three-action row), 216–229 (the old "Quick Capture" button vs. the
  rebuilt full-screen button), and 265–340 (the entire recording-status
  row, Stop button, and Recent-captures block the rebuild added, colliding
  with the old mode-icon buttons and hint-line comment it replaced).
- **`python/tests/test_regressions.py`** — one conflicting hunk, lines
  2525–2734: the whole "Launcher redesign" test section added by
  `ca71881` and extended by later commits (`5c5e0a1`, `aca5463`) fails to
  reverse-apply as a block, since the file has moved on from what
  `ca71881` originally touched.

This is the concrete unpick cost §6 described from dependency analysis:
not a clean one-commit revert, but conflicts in the two files every
later launcher commit continued to build on. `git revert --abort` was
run immediately after inspecting the conflict markers; nothing was
committed. The worktree (`artifacts/review/drop-test`) has been removed
and `git worktree prune` run — `git worktree list` shows only the five
per-PR review worktrees.

## `ca71881` re-isolated — arithmetic correction, and a conflict-free revert would still crash — 2026-09-11

Re-run of the two commands above, this time checking the one thing the
prior entry did not: whether a *hand-resolved* revert produces a tree
that actually runs, not just one that reverts without conflict markers.

**`git show ca71881 --stat` (verbatim, unchanged from the prior run):**

```
commit ca718819e15fb29f5018976a486534445f867b94
Author: Martin Hugo <m.hugo@guardian360.nl>
Date:   Fri Sep 11 12:56:53 2026 +0200

    feat(launcher): rebuild the floating panel and docked strip
    [...]

 python/launcher.py               | 801 +++++++++++++++++++--------------------
 python/tests/test_regressions.py | 229 +++++++++--
 python/theme.py                  |  12 +
 3 files changed, 596 insertions(+), 446 deletions(-)
```

**Correcting an arithmetic slip in the prior entry.** That entry called
the "~150 lines" overstatement "roughly 30x" — that number is
150 ÷ 5 (the whole-branch net, from §6's own table), not 150 ÷ 17 (this
commit's own net, from `--numstat`: `392 409 python/launcher.py`, net
−17). The correct factor for the claim as written — about *this commit*
— is **~9x**, not 30x. The −5 whole-branch net and the −17 single-commit
net are both real, measured numbers; they just answer different
questions, and the prior entry compared the claim to the wrong one.

**`git worktree add --detach artifacts/review/drop-test origin/ui-polish`
then `git revert --no-commit ca71881`** reproduces exactly the prior
result — same two files, same three hunks in `launcher.py` (lines
194–210, 216–229, 265–340 in the marked-up file), same single hunk in
`test_regressions.py` (2525–2734), `theme.py` auto-merging cleanly:

```
Auto-merging python/launcher.py
CONFLICT (content): Merge conflict in python/launcher.py
Auto-merging python/tests/test_regressions.py
CONFLICT (content): Merge conflict in python/tests/test_regressions.py
Auto-merging python/theme.py
error: could not revert ca71881... feat(launcher): rebuild the floating panel and docked strip
```

**The more important question: does the tree left behind actually run?**
`_apply_hotkey_labels()` — added by `5c5e0a1`, two commits after
`ca71881`, and not touched by reverting `ca71881` alone — calls
`self._btn_record.setToolTip("Start recording (Alt+V)")` at
`launcher.py:479` in the mid-revert tree. That call site sits *outside*
all three conflict hunks (479 falls between the 265–340 hunk and nothing
else follows it), so it merges silently, unchanged, on both sides of the
conflict — there is no marker to alert a reviewer to it.

Checked directly, on the mid-revert file, before aborting:

```
$ grep -n "_btn_record" python/launcher.py
479:            self._btn_record.setToolTip("Start recording (Alt+V)")

$ grep -n "_btn_record\s*=" python/launcher.py
(no output)
```

Every `self._btn_record = ...` creation line (`launcher.py:240–244` on
clean `ui-polish` — the button's construction, its `clicked.connect`,
and its later `setIcon`/`setToolTip` calls in `_set_recording_state`)
was removed by the revert **without a conflict** — that part of
`ca71881`'s patch applied cleanly, since nothing later touches those
exact lines. The one survivor, `_apply_hotkey_labels()`'s reference, is
untouched because it belongs to a different commit (`5c5e0a1`) that
this revert does not target.

**Conclusion: a fully hand-resolved revert of `ca71881` — with both
conflicting hunks in `launcher.py` and the one in `test_regressions.py`
resolved in the "drop the rebuild" direction — leaves `_btn_record`
uncreated while `_apply_hotkey_labels()` still calls a method on it.**
That path runs whenever `register_global_hotkeys=True`, which is the
real application's startup path and the one the test suite structurally
avoids (documented precedent: this is the same class of failure
`5c5e0a1` itself was written to fix, and the same class `aca5463`
patched again after the rebuild). A conflict-free, carefully
hand-resolved revert is therefore a **worse** outcome than the conflict
git already reports: the conflict at least stops a reviewer before a
broken tree exists, where a quiet hand-resolution would not.

`git revert --abort` was run immediately after this check; nothing was
committed or left staged. The worktree
(`artifacts/review/drop-test`) has been removed (`git worktree remove`
hit the same Windows file-lock `Permission denied` as before —
resolved with `rm -rf` once the shell's working directory had moved off
it, followed by `git worktree prune`). `git worktree list` again shows
only the five per-PR review worktrees.
