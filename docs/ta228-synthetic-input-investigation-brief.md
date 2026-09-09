# Brief: TA-228 — why checks 2 and 3 don't register synthetic input at all

## Why

TA-228's own "needs a real interactive machine" theory is now disproven, not
confirmed. Re-run twice on Emil's own desktop (fresh state both times, no
stale tray instance): check 1 passes, checks 2 and 3 fail identically both
times — same failure shape as the original cloud/CI-adjacent environment.
With the automated run finished, Emil opened Test Assist and clicked Quick
Capture and Open Editor with his own mouse — both work exactly as expected.
The app is not regressed and the tests are not wrong. What's failing is
narrower and more specific than "no synthetic input reaches the app in this
class of environment": `pywinauto`'s `click_input()` (real OS `SendInput`)
does not register with this specific Qt application even from a real,
logged-in, interactive desktop session.

**Read `TESTASSIST_BACKLOG.md`'s TA-228 entry in full before starting**,
especially its final "re-run on real hardware" paragraph — this brief exists
to act on that paragraph's own stated next step, not to redo the
investigation that already happened.

## What's already ruled out — do not re-investigate these

Confirmed directly, twice (original investigation and the real-hardware
re-run), each via an independent, measured signal, not assumed:

- Process DPI awareness — set explicitly
  (`ctypes.windll.shcore.SetProcessDpiAwareness(2)`) before any UIA/COM use.
- Click coordinates — `WindowFromPoint` at the exact click coordinates
  returns the target window's own real hwnd, not something else intercepting
  it.
- Desktop/session attachment — `OpenInputDesktop` succeeds; the calling
  process's session id matches `WTSGetActiveConsoleSessionId()` (a real,
  attached, interactive session, not a service/disconnected one).
- UIPI integrity mismatch — `whoami /groups` shows Medium integrity for the
  calling process, the normal unelevated level; nothing in this build
  requests elevation.
- UI Automation's `Invoke` pattern, `click_input()` (`SendInput`), and the
  `win32` backend's `PostMessage`-based click were **all** tried in the
  original (non-interactive) investigation and had zero effect — but that
  `win32`-backend attempt has not yet been re-tried specifically on an
  interactive session, where the message pump behaves differently. That
  re-test is in scope below; the other two are not worth repeating as-is.

None of the above depended on the session being non-interactive, so their
being ruled out again on real hardware isn't new information. What's new,
and what this brief is for, is that the "will just work on real hardware"
part of the theory is falsified.

## Three candidates, and the cheap test that tells you which branch to follow

The three candidates named for this investigation: `pywinauto`'s `win32`
backend re-tried on an interactive session, Qt/PySide6 itself filtering
OS-flagged synthetic `SendInput` (Windows marks injected input with
`LLMHF_INJECTED` / `GetMessageExtraInfo()`, and some frameworks' input
handling treats it differently from physically-generated input), and
third-party security software on this machine intercepting synthetic input
to this one process.

**Do this first, before picking a candidate to chase** — it's cheap and it
directly disambiguates candidates 2 and 3:

### Step 0 — control test against a non-Qt target

Run `pywinauto`'s `click_input()` (same mechanism `test_smoke.py` already
uses) against a plain, non-Qt window on this same machine — Notepad's own
window is enough; no new project needed. Two possible outcomes, and each
points somewhere different:

- **It works against Notepad.** The problem is specific to Qt/PySide6 (or to
  this app's own window setup) receiving synthetic input, not a system-wide
  block. Follow the Qt branch (Step 1 below).
- **It fails against Notepad too, the same way.** The problem is system-wide
  on this machine, not Qt-specific — something between `SendInput` and every
  window is intercepting or dropping it. Follow the security-software branch
  (Step 2 below), and re-open the win32-backend retry (Step 3) since a
  system-wide block would explain why that mechanism failed too, both times.

Report this result plainly either way — it's the load-bearing fact for
everything after it, not a throwaway check.

### Step 1 — if Qt-specific: isolate Test Assist's own setup from Qt in general

Build a minimal, throwaway PySide6 script — one `QMainWindow`, one
`QPushButton`, nothing else — and run the same `click_input()` test against
it. This controls for whether the block is Qt/PySide6 in general on this
machine, or something particular to Test Assist's own window: the
`WindowStaysOnTopHint` + frameless flags on `ScreenshotOverlay`, the
`QAbstractNativeEventFilter` installed for global hotkeys (`WM_HOTKEY`)
potentially interfering with other native message delivery, or the
single-instance socket server.

- If the minimal window also fails to receive synthetic input, the cause is
  Qt/PySide6's own Windows input handling on this machine (or this Qt
  build/version) — look at whether Qt's Windows platform plugin
  (`qwindowsmousehandler`/native event handling) checks
  `GetMessageExtraInfo()` or the injected-input flag and treats synthetic
  `SendInput` differently from a physical click. This is a real, documented
  area of Qt/Windows behavior, not a guess to manufacture — search Qt's own
  issue tracker and source for how it classifies injected input before
  writing any workaround code.
- If the minimal window receives the click correctly, the cause is something
  particular to Test Assist's own window setup, not Qt generally. Narrow it
  by disabling one candidate mechanism at a time in a throwaway build (the
  native event filter, then `WindowStaysOnTopHint`) and re-running the
  control test after each, rather than guessing which one from reading code
  alone.

### Step 2 — if system-wide: security software

Identify what's actually running on this machine (Windows Security /
Defender status at minimum, plus anything else with real-time protection or
an input-monitoring/anti-cheat-style driver). Check Windows Event Viewer for
anything logged at the time of a failed synthetic click. If a low-level
mouse hook is suspected, a hook-enumeration tool can confirm whether
something is installed at `WH_MOUSE_LL`.

**Do not disable or reconfigure any security software as part of this
investigation without asking first.** Confirming the hypothesis by turning
real-time protection off and re-testing is a reasonable diagnostic step, but
it's a security-posture decision, not a test-writing one — flag it and get
an explicit go-ahead before doing it, the same way TA-228's own CI-vs-manual
call was recorded rather than defaulted into.

### Step 3 — win32 backend, re-tried on this interactive session

Independent of which branch above applies, this is worth re-trying on its
own: `pywinauto`'s `win32` backend (`Application(backend="win32")`) sends
clicks via `PostMessage` (`WM_LBUTTONDOWN`/`WM_LBUTTONUP`) rather than
`SendInput`, and was only tried once, in the original non-interactive
environment, where the message pump behaves differently. Re-test it here
specifically, verified the same way this project verifies everything else in
this lane — an independent real signal (the existing `TESTASSIST_DEBUG=1`
log line, or a UI-Automation toggle-state read-back), not just "no exception
was raised."

## Sequencing

1. **Step 0** — the control test. Everything else depends on its result.
2. **Step 3** (win32 backend retry) can run in parallel with Step 0 — it's a
   different click mechanism entirely and doesn't need the branch decision
   first.
3. Follow **Step 1 or Step 2** based on what Step 0 showed.

## Explicitly out of scope for this brief

- Actually closing TA-220's or TA-217's still-open gaps. Those stay blocked
  on checks 2 and 3 actually passing — get the checks working first.
- Wiring `tests_e2e/` into CI. That decision already stands (local/manual)
  and isn't reopened by this investigation.
- Broadening the three checks beyond their current scope.
- Any change to security software configuration without asking first (see
  Step 2).
- Inventing a workaround before the cause is confirmed. If a fix is obvious
  once the cause is known (e.g., Test Assist needs to explicitly accept
  injected input, or a specific window flag needs to change), write that up
  as a new, separate ticket rather than folding an untested fix into this
  investigation's own report.

## Build + verify

No production code change is expected to come out of this brief — it's
root-cause work, same shape as `overlay-geometry-fix-brief.md`'s
measurement-first approach. If Step 1 or Step 2 turns up a concrete fix
worth making, propose it as a new ticket rather than building it silently
inside this investigation.

Every candidate ruled out or confirmed needs its own independent, measured
signal — a log line that did or didn't appear, a toggle-state read-back, an
Event Viewer entry, a control test's pass/fail — not "seems related" or "this
would explain it." That's this project's own standing bar, applied to every
other ticket in `TESTASSIST_BACKLOG.md`.

**Report back in `docs/BUILD_LOG.md`, not chat** — a new dated sub-entry
under the existing TA-228 story (not a fresh top-level heading), covering:
the Step 0 control-test result, which branch it led to, what was found there
with its independent signal, and the win32-backend retry's result. State
plainly if the cause is still unconfirmed after all three steps — an honest
"still open, here's what's now ruled out" is a valid outcome, consistent
with how TA-228's own entry has been reported so far.

**Update `TESTASSIST_BACKLOG.md`'s TA-228 entry** with the outcome once
done. Per this session's own stash-loss precaution (`docs/BUILD_LOG.md`'s
"Investigation: what has been silently reverting `TESTASSIST_BACKLOG.md`"
entry), **commit that file by itself, immediately after editing it** —
never batched with a code/test commit, and avoid any `git stash` operation
that touches it.
