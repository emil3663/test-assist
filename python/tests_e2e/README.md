# Black-box smoke lane (TA-228)

Three small checks that drive the actual packaged `TestAssist.exe` from
outside the process, via [pywinauto](https://pywinauto.readthedocs.io/)
(Windows UI Automation) - the native-desktop equivalent of what a
browser-automation tool does for a web page. Every other test in this
project imports `python/`'s modules directly into the test process; this
is the one lane that instead launches a real subprocess and observes it
the way a real user (or a real Windows window manager) would.

## Why this exists

TA-220's minimize-toggle gap and TA-217's hotkey-capture gap are both
still "instrumented, not fixed" (see `docs/BUILD_LOG.md`'s rc5 entry)
because nothing in-process can observe what the real Windows window
manager does with a real, separate top-level window under real
focus/Z-order rules - exactly where both unconfirmed hypotheses live.
This lane is what could close those for good instead of needing a human
on real hardware every time.

## Decision: local/manual, not CI-wired (for now)

Recorded per `docs/ta227-228-e2e-testing-brief.md`'s instruction to write
the call down rather than default into it.

**Decision: stays a local/manual smoke pass. Not wired into
`.github/workflows/python-tests.yml`.**

Reasoning:

- Building an exe just to run three checks is more CI time than three
  checks are worth today - this is new, unproven infrastructure, not
  something the release has ever depended on.
- **A harder finding while building this lane, not just the ticket's own
  cost argument:** in this development environment, no synthetic input
  mechanism tried actually reached the running app - UI Automation's
  Invoke pattern, `pywinauto`'s `click_input()` (real OS `SendInput`),
  and the `win32` backend's direct `PostMessage`-based click were all
  tried against the real `Quick Capture` button and a real checkbox
  control, each verified via an independent, real signal (a
  `TESTASSIST_DEBUG=1` log line that never appeared; a UI-Automation
  toggle-state read-back that never changed) - all three had zero
  observable effect, despite confirming (also directly, not assumed):
  process DPI awareness set correctly, the click coordinates landing on
  the right window via `WindowFromPoint`, an attached, interactive input
  desktop (`OpenInputDesktop` succeeded) on the session matching the
  active console session, and matching (Medium) process integrity
  levels ruling out a UIPI mismatch. Checks 2 and 3 below are written
  correctly and are the right design, but could not be verified end to
  end in this specific environment as a result - see
  `docs/BUILD_LOG.md`'s TA-228 entry for the full account. **GitHub
  Actions' hosted Windows runners are a similarly non-interactive,
  automated context** - the same class of environment that just failed
  to deliver synthetic input here - so wiring this into CI today risks
  building automation around a false assumption (that a runner can
  deliver real clicks at all) rather than proving anything. This needs
  confirming on a real, interactive Windows machine before CI is even a
  reasonable next step, not just a cost/benefit call.
- Once this lane has actually caught something real on real hardware,
  promoting it to CI (on a self-hosted runner with a real interactive
  session, not a hosted one) is the natural next step - not before.

## Running it

Needs a build first - this cannot run from a source checkout the way
everything else in `tests/` can.

```powershell
cd python
..\.venv\Scripts\Activate.ps1
.\build.ps1                          # or use an existing dist\TestAssist\TestAssist.exe
python -m pip install -r tests_e2e\requirements.txt
python -m pytest tests_e2e           # testpaths in pytest.ini keeps this
                                      # out of a plain `pytest`/`pytest -q`
```

Close any already-running `TestAssist.exe` first (check the tray) - a
second instance hands off to the first and exits immediately, which this
lane's fixtures do not account for.

Point at a different build with `TESTASSIST_EXE`:

```powershell
$env:TESTASSIST_EXE = "C:\TestAssist\TestAssist-1.4.0-rc5(09092026)\TestAssist.exe"
python -m pytest tests_e2e
```

Each test kills its own launched process on teardown (`app.kill()`),
regardless of the test's outcome, so a leaked process is never left
holding the real, shared Win32 hotkeys (`RegisterHotKey`) after a run.

## The three checks

1. **The app launches and its window appears within a timeout.**
2. **Clicking the real Quick Capture button produces a real, visible
   overlay window** - observed via the OS's own window list, not
   asserted from inside the process.
3. **Minimize/restore via the TA icon changes the real OS window
   state** - `pywinauto`'s own `is_minimized()`/`is_normal()`, backed by
   UI Automation's `WindowVisualState` (which Windows derives from
   actual window state), not Qt's internal flags. The direct test of
   TA-220's still-unconfirmed `isActiveWindow()`-timing hypothesis: the
   click happens on a *different* top-level window (the launcher) than
   the one being minimized (the editor).

Deliberately kept to these three and no more for now - a small, sturdy
first slice, not a first attempt at full coverage. Explicitly out of
scope for this same pass: using this lane to actually resolve TA-220's or
TA-217's still-open gaps - that is its own follow-up, once the lane has
been run against real hardware and is trusted.
