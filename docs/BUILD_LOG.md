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
