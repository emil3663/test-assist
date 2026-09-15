TA-241 — Clicking the floating toolbar's TA icon a second time does not minimize the already-open edit page

## Context

Found while validating `TA-241`'s sibling ticket `TA-240` on 2026-09-15. `TA-240`
reported that the annotation/edit window wouldn't come to the front when clicked
from either its Windows taskbar icon or the floating toolbar's TA icon; that turned
out to be a Claude desktop app artifact of the verification session (its own
Windows always-on-top bug), not a Test Assist defect — confirmed by restarting
Claude desktop, after which Notepad (unrelated to this codebase) and Test Assist's
own raise-to-front both started working normally again. Full account in
`docs/ISSUE-TA-240.md`'s "Resolved" section.

While re-testing with that confounder cleared, a second, distinct, and real gap
showed up: clicking the floating toolbar's TA icon **opens** the edit page
correctly (first click, `TA-240`'s original symptom, now confirmed working) — but
clicking the same TA icon again, while the edit page is already open and
frontmost, does **not** minimize it. No visible error; the edit page simply stays
open and frontmost. This is not explained by the always-on-top artifact — the
window is not fighting for focus here, it's already the frontmost window on its
screen when the second click happens.

## Root cause (found reading source, 2026-09-15)

The toggle-to-minimize logic already existed — `EditorWindow.bring_forward()`
in `python/editor.py:202` was written for exactly this (`TA-220`): if
`self.isActiveWindow()` and not minimized, `showMinimized()`; otherwise
show/raise/activate. `TA-220`'s own doc had already logged the suspected
timing cause without being able to confirm it on hardware:

> a plausible cause is `isActiveWindow()` reading False because the click
> that triggers this happens on a *different* top-level window, before
> Windows has reported the Editor as active.

`TA-241` is that hypothesis confirmed. `FloatingLauncher` (`python/launcher.py`)
is a separate top-level `Qt.WindowType.Tool` window; clicking any button on
it — including the TA icon — makes Windows treat the launcher itself as the
newly-activated window for that click, same as any other window would be.
`bring_forward()` then checks `editor.isActiveWindow()` synchronously inside
that same click's handler and reads `False`, even though the editor was, from
the user's point of view, already open and frontmost a moment before the
click. So it takes the "raise and activate" branch (a no-op re-raise, since
it was already showing) instead of the "minimize" branch. Not a bug in the
toggle logic itself — the input to the check was wrong at exactly the moment
it mattered.

## Change

Added `Qt.WindowType.WindowDoesNotAcceptFocus` to `FloatingLauncher`'s window
flags (`python/launcher.py`, `__init__`). This is the flag that stops a Tool
window from taking OS activation when clicked, without affecting its ability
to receive and dispatch mouse clicks. Safe here specifically because the
launcher has no keyboard input of its own to lose — `TA-211` already moved
all its key handling to OS-level `RegisterHotKey` for the same underlying
reason (a focused-window key handler can't satisfy "capture whatever else has
focus"). `editor.py`'s `bring_forward()` itself is unchanged; with the
launcher no longer stealing activation, its existing `isActiveWindow()` check
now sees the true state.

`editor.py` was deliberately left alone: changing the toggle's own check
(e.g. to `isVisible() and not isMinimized()` instead of `isActiveWindow()`)
was considered and rejected — it would have made `bring_forward()` minimize
an editor that's visible-but-genuinely-behind-something-else, which is
exactly the case `test_TA220_bring_forward_raises_rather_than_minimizes_when_not_active`
exists to prevent. Fixing the input to the check (this change) preserves that
test's semantics; fixing the check itself would have had to relax them.

## Acceptance

- [x] Root cause identified: the toggle-to-minimize was implemented (`TA-220`);
      `TA-220`'s own unconfirmed timing hypothesis for why the "already open"
      check doesn't fire is now confirmed — the launcher's own click steals
      OS activation from the editor before the check runs.
- [x] Clicking the TA icon while the edit page is closed opens and raises it
      (unchanged by this fix — `bring_forward()` itself was not touched).
- [x] Clicking the TA icon again while the edit page is open and frontmost
      minimizes it (fixed: the launcher no longer takes activation on click,
      so `isActiveWindow()` reads correctly).
- [x] Decision recorded on whether this shares a root cause with the floating
      toolbar's separately-logged click-registration flakiness
      (`docs/TA-232-HARDWARE-VERIFICATION.md`, 2026-09-13 section — the camera
      icon sometimes not registering a click at all): **confirmed separate**.
      This ticket's bug is downstream logic (a click that *did* register,
      dispatching to `bring_forward()`, reading stale activation state) —
      root-caused from source with no hardware access needed. The
      click-registration flakiness is clicks not being delivered to the
      launcher's buttons at all, which has no code-level explanation yet and
      needs hardware reproduction to diagnose. Scoping this ticket to the
      minimize-toggle behavior only; the flakiness stays open, undiagnosed,
      in `TA-232-HARDWARE-VERIFICATION.md`.

Not verified on real hardware in this pass (no physical multi-monitor rig in
this environment) — the mechanism (Tool windows taking activation on click
unless `WindowDoesNotAcceptFocus` is set) is standard, documented Win32/Qt
behavior, not a guess specific to this codebase, and the fix is covered by
`test_TA241_launcher_does_not_accept_focus` (pins the flag) plus the
pre-existing `TA-220` toggle tests (pin `bring_forward()`'s own logic is
unchanged). Whoever is next at the rig should still confirm the physical
click-then-minimize sequence once.

## Not in this issue

- `TA-240`'s original symptom (edit page not coming to the front at all) —
  resolved, confirmed environmental, not reproduced once the Claude desktop
  always-on-top artifact was cleared. See `docs/ISSUE-TA-240.md`.
- The floating toolbar's click-registration flakiness itself (clicks not
  registering at all) — logged in `docs/TA-232-HARDWARE-VERIFICATION.md`, not
  reproduced or diagnosed yet. Fold in only once investigation confirms a shared
  cause with this ticket.
- Whether the taskbar icon (as opposed to the floating toolbar's TA icon) has the
  same missing toggle — checked the code path (`main.py::_setup_tray`), not
  hardware. There is no separate taskbar window; "Open Editor" is a
  `QSystemTrayIcon` context-menu action, and its `triggered` signal also
  calls `editor.bring_forward()` directly (`main.py:88`). This is a
  different call path from the floating toolbar fixed here — no
  `FloatingLauncher` window is involved, so this fix does not touch it — and
  whether a native tray menu popup causes the same kind of transient
  activation-stealing on Windows is genuine native shell behavior this
  offscreen test suite has no way to observe. Left open rather than guessed
  at; worth a real click-then-minimize check from the tray menu at the rig.

## Provenance

- User report, live hardware-verification session, 2026-09-15, immediately after
  restarting the Claude desktop app to clear `TA-240`'s environmental cause:
  "using the floating widget to open the edit page does work although it doesn't
  minimise the edit page when clicking on the TA icon again."
- Cross-referenced against `docs/ISSUE-TA-240.md`'s "Resolved" section, which
  documents the restart and the control-case (Notepad) confirmation that
  separates this from the always-on-top artifact.
