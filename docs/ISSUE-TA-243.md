TA-243 — Stopping a recording sometimes needs two clicks when the launcher isn't OS-focused

## Context

Found alongside `TA-242`, same T2 evaluation session (2026-09-16). If the
floating/docked launcher is not the OS-focused/active window when a
recording is running — even though it's fully visible on screen — the first
click on the Stop button only brings the launcher window to focus; the
click itself doesn't register as a Stop action. A second click is then
needed to actually stop the recording.

Both the undocked Stop button (`_btn_record`) and the docked strip's Stop
button (`_btn_dock_record`) are the same `FloatingLauncher` window in two
layouts, and both route to the same `_toggle_recording()`
(`launcher.py:352-353`, `:439`, handler at `:705-709`). The launcher is a
plain `Qt.WindowType.Tool` window (`launcher.py:88-91`) with no
focus-suppressing attribute set. `WA_ShowWithoutActivating` exists
elsewhere in this codebase (the Editor window, as part of `TA-220`'s
still-unconfirmed focus/minimize fix — `editor.py:100,163,234`), but it is
not applied to the launcher. **Checked and ruled out as a precedent:**
`WindowDoesNotAcceptFocus`, used on `main`'s launcher for a different
button's focus issue, does not appear anywhere in the `ui-polish`
worktree's code — don't assume this button is already covered by that or
any other existing fix. This looks like default OS/window-manager
click-to-focus behavior that nothing in the code currently guards against,
but that's a hypothesis to confirm, not yet a confirmed root cause.

The tester also proposed two UX changes to consider alongside whatever fix
this needs, to make Stop harder to miss even when the "needs a second
click" problem is fixed:

1. Automatically switch the floating widget into its docked/compact form
   the moment a recording starts, rather than leaving it in whatever
   docked/undocked state it was already in.
2. Give the Stop button a pulsing/glowing visual treatment while a
   recording is active, so it reads as unmistakably "recording, click to
   stop" even at a glance.

## Change

**Decided, 2026-09-16 — the two proposed UX additions, locked independently
of the still-open root-cause investigation below:**

- **Auto-dock on record start: yes, implement.** If the launcher is
  floating/undocked when a recording starts, switch it to the docked strip
  automatically (same transition `_dock_right()` already performs on a
  manual click). This isn't just discoverability polish here — docked mode
  has now been confirmed twice (T3, and the tester's follow-up
  confirmation) to exhibit *neither* the double-click symptom *nor* the
  phantom-snapshot side effect, while undocked mode has hit both, twice.
  Forcing docked state during a recording is a real mitigation for this
  ticket's whole mechanism, not just a UX nicety, even before that
  mechanism is fully named.
  **Required alongside it, not optional:** `_btn_dock_right`/`_btn_undock`
  (the manual dock/float toggle) must also be hidden or disabled for the
  duration of a recording, the same way `_refresh_recording_ui()` already
  hides `_btn_dock_capture`/`_btn_dock_full` during recording (same
  method, same pattern) — otherwise a user can re-float mid-recording and
  land right back in the undocked state this mitigation exists to avoid,
  making the auto-dock a one-time gesture instead of an actual guarantee.
- **Pulsing/glowing Stop button: yes, implement.** Reuse whichever
  existing token already renders the recording-state's red
  border/indicator dot (`_refresh_recording_ui()`'s docstring already
  calls this "the convention every recorder uses") rather than
  introducing a new color — this is a treatment of an existing signal, not
  a new one. Subtle enough not to be distracting over a multi-minute
  recording; exact animation mechanism (QTimer-driven stylesheet toggle,
  QPropertyAnimation, etc.) is an implementation choice, not a product one.

**Neither of the above replaces confirming this ticket's actual root
cause** — they reduce how often the bug is *encountered* in normal use,
they don't explain or fix the underlying mechanism, and the acceptance
criteria below (real signal, not assumption) still apply in full,
especially for the phantom-snapshot side effect, which this ticket's own
"why this raises priority" note already flags as worse than a UX
annoyance. Confirm the phantom-snapshot mechanism specifically before
considering this ticket done, even once the mitigations above ship.

Not yet investigated (unchanged from before): first step is confirming the
actual mechanism behind
the double-click, not assuming it's the same "activation swallows the
first click" pattern found elsewhere in this codebase for a different
window/button — that needs its own check here, on this button, on this
window class. As part of that: check whether Capture and Full-screen (the
launcher's other two buttons) show the same first-click-just-focuses
symptom when the launcher isn't focused, or whether this is specific to
Stop/the recording state — that result decides whether the fix belongs on
the whole window or just the recording-state button handling.

Once the mechanism is confirmed, the two UX proposals above are a separate
decision (implement, defer, or reject each, with reasoning) — they would
reduce how often the double-click problem is even encountered, but don't
fix it on their own if the underlying activation issue isn't addressed.

## Acceptance

- [ ] Root cause confirmed: is this activation/focus swallowing the first
      click (as hypothesized), or a different mechanism? Confirmed via a
      real signal (e.g. logging which handler actually fires on each of
      the two clicks), not assumed from the symptom alone.
- [ ] Whether Capture/Full-screen share this symptom when unfocused is
      checked and recorded, even if the fix ends up scoped to Stop only.
- [ ] A single click on Stop reliably stops the recording regardless of
      the launcher's current OS focus state.
- [ ] A decision is recorded on both proposed UX additions (auto-dock on
      record start; pulsing/glowing Stop button) — implement, defer, or
      reject, with reasoning either way, not left silently unaddressed.

## Not in this issue

- `TA-242` — the launcher appearing inside the recorded footage itself.
  Related (same testing session, same button), but a different mechanism
  and a different fix.
- Whether the Editor window's own `WA_ShowWithoutActivating` /`TA-220` fix
  is itself confirmed working — that's `TA-220`'s own open item, not this
  one's to re-verify.

## Provenance

- Tester's live evaluation, Launcher Evaluation Pass task T2, 2026-09-16:
  "i had to click the stop record a few times as even though the ta
  floating widget was not in focus it was visible and the first click was
  to put focus on it and the second to actually stop it... if we handle
  that the floating widget changes into the docked version when recording
  and we can [have] the stop button glow or pulse so people can see it
  clearly it would be great."
- Code mechanism (click handlers, window flags, and the absence of any
  matching focus-suppression precedent in this worktree) confirmed by
  reading `python/launcher.py` directly, not inferred from the report
  alone.

## 2026-09-16 (later) — new evidence: an unintended snapshot is saved right after each recording

The tester's ordering question — "the video was added below a snapshot i
didn't take, shouldn't it be the top one as it was the last thing done" —
led to checking `_history_files_for_mode()`'s sort
(`editor.py:956`, `files.sort(key=lambda item: item.stat().st_mtime,
reverse=True)`), which is correctly newest-first by file modification
time. That rules out a sort-order bug. But it also means the snapshot
genuinely does have a *later* mtime than the recording sitting below it —
which sent this back to "why does an untaken snapshot exist with a
timestamp right after the recording," not "why is the list ordered wrong."

Checked directly against the AppData history folder's actual file
timestamps for both of today's recording attempts:

| file | unix mtime | gap |
|---|---|---|
| `test-recording-1789515826.thumb.jpg` | 1789515840.72 | — |
| `snapshot-20260916-014401-388082.png` | 1789515842.08 | **+1.36s** |
| `test-recording-1789515938.thumb.jpg` | 1789515952.02 | — |
| `snapshot-20260916-014552-541733.png` | 1789515953.20 | **+1.18s** |

Both of today's recordings produced an untaken snapshot roughly 1.2-1.4
seconds after that recording's thumbnail was generated. This is not a
coincidence pattern worth dismissing — it happened both times, at nearly
identical offsets.

Traced (not yet confirmed) where a `snapshot-*.png` can come from: only one
code path writes that filename shape — `EditorWindow._persist_history_snapshot()`
(`editor.py:911`), and the only route into it from a *new* capture (as
opposed to re-viewing an existing history item) is `record_capture()`
(`editor.py:168`), which is called exactly once, from the launcher's still-
capture-ready path (`launcher.py:530`). Nothing about stopping a recording
is supposed to reach that path. The most plausible mechanism, given this
ticket's own root topic: whatever produces the "first click only focuses,
second click actually stops" symptom above might also explain a
misdirected click — e.g. if the docked capture/record button's mode state
is briefly stale during the recording-to-idle transition, a click landing
in that window could dispatch through `_on_action_click()`'s photo branch
(`_start_capture()`) instead of the recording-stop branch. **This is a
hypothesis from timing correlation and a code-path trace, not yet
confirmed with instrumentation** — whoever picks this up should log which
handler actually fires on each click of the stop sequence, the same
measured-not-argued bar this project holds everywhere else, rather than
assume the mechanism above is exactly right.

**Why this raises this ticket's priority:** if confirmed, this isn't just
an extra click — every recording in this session's testing silently added
an untaken, meaningless snapshot into the evidence history, one which a
real user would have no way to distinguish from an intentional capture
without checking timestamps the way this investigation just did. That's
worse than a UX annoyance.

## Acceptance (addendum)

- [ ] Confirm or rule out the phantom-snapshot mechanism above, with a
      real signal (logged handler dispatch), not argument from timing
      alone.
- [ ] If confirmed: no unintended snapshot is saved as a side effect of
      stopping a recording, however many clicks it takes.

## 2026-09-16 (later still) — narrowed: docked-mode stop does not reproduce the phantom snapshot

T3's clean 10s recording (`test-recording-1789517866.mp4`, 9.47s) was
started and stopped via the **docked** strip's record button, not the
undocked/floating one used for both of T2's recordings. Checked directly
against `history/`'s file timestamps: `test-recording-1789517866.thumb.jpg`
(mtime 1789517880.73) is the newest file in the folder — no
`snapshot-*.png` appears after it, unlike both T2 runs, which each produced
one ~1.2-1.4s after their own thumbnail.

This narrows the phantom-snapshot mechanism to the **undocked/floating**
record button's stop path specifically, not the recording-stop flow in
general — the docked strip's `_btn_dock_record` reaching the same
`_toggle_recording()` does not (so far, n=1) trigger it. Still needs the
tester's confirmation on whether docked-mode stop also avoided needing a
second click (asked, not yet answered) — that determines whether docked
mode sidesteps this ticket's whole mechanism or just the snapshot side
effect specifically, which changes where a fix should be scoped: at
`_toggle_recording()` itself (shared) vs. something specific to the
undocked button/window's click or focus handling (not shared with the
docked strip).

## 2026-09-16 — confirmed: docked-mode stop is a single click, whole mechanism avoided

Tester confirmation: stopping the docked-strip recording (T3's clean 10s
clip) took exactly one click — no focus-then-stop double click, matching
the earlier finding that it also produced no phantom snapshot. Both
symptoms are absent together in docked mode, present together in undocked
mode (both T2 runs) — strengthens that this is one shared root cause tied
to the undocked/floating window's state specifically (most likely something
about its focus/activation as a moveable, non-anchored top-level window),
not two coincidentally-correlated bugs. Still needs instrumentation to name
the exact mechanism (see acceptance criteria above) — the docked-vs-
undocked split is a strong, now twice-confirmed clue for whoever
investigates, not itself the fix.

## 2026-09-16 (later) — phantom-snapshot mechanism confirmed: geometric overlap, not stale mode state

The doc's own hypothesis ("the docked capture/record button's mode state
is briefly stale during the recording-to-idle transition, a click landing
in that window could dispatch through `_on_action_click()`'s photo
branch") **no longer applies to the current code.** The launcher rebuild
that shipped with 1.5.0 (`ca71881`) removed mode-based dispatch entirely —
`_on_action_click()` is gone; `_btn_capture`/`_btn_dock_capture`,
`_btn_full_capture`/`_btn_dock_full` and `_btn_record`/`_btn_dock_record`
each connect to their own independent handler
(`_on_capture_click`/`_start_full_capture`/`_toggle_recording`) with no
shared mode state left to go stale. Confirmed by `grep`, not assumed.

**The actual mechanism, measured directly** (constructing a real
`FloatingLauncher`, reading real `QWidget.geometry()` values, not argued
from the layout code alone):

```
idle:      _btn_capture      geometry=(14, 53, 252, 38)
recording: _btn_stop         geometry=(14, 77, 252, 44)
overlap:   (14, 77, 252, 14)  — confirmed via QRect.intersects()
```

In the **floating panel only**, Stop is not the same widget relabelled —
`_refresh_recording_ui()` hides `_btn_capture`/`_btn_full_capture`/
`_btn_record` and shows a *separate* widget, `_btn_stop`, in their place.
Because `_btn_capture` sits above the row `_btn_stop` ends up occupying
once the others collapse, their rects genuinely overlap by 14px of
height. A real `QTest.mouseClick` sequence confirms the consequence
directly: click #1 inside that overlap region correctly resolves to
`_btn_stop` and stops the recording; the *same screen point*, re-hit-
tested immediately afterward (`parent.childAt(point)`, Qt's own hit-test,
not assumed), now resolves to `_btn_capture`. A second real click there
dispatches `_on_capture_click()` — the exact call chain
(`_start_capture()` → overlay → `record_capture()` →
`_persist_history_snapshot()`) that produces an unrequested
`snapshot-*.png`.

This is a **different but adjacent** mechanism from the doc's original
guess — a same-frame widget swap creating a landing trap for a rapid
second click, not stale mode state — but explains the identical observed
symptom, and explains why **only** the undocked/floating panel reproduces
it: the docked strip's Stop control (`_btn_dock_record`) is the *same
widget* throughout a recording, just re-iconed, so there is no second
widget for a second click to fall into. This also fits the earlier
docked-vs-undocked split (confirmed twice on hardware) without needing a
second, independent explanation.

**Still not confirmed from this environment:** whether the reported
"first click only focuses the window" step is real OS-level click-to-
focus behaviour swallowing the very first click, before either the
overlap mechanism above or a normal click ever gets a chance to run. That
is an OS window-manager phenomenon no in-process or offscreen Qt test can
observe (the same limitation this project's `tests_e2e` black-box lane
exists for, per `TA-228`) — needs a person clicking a real, unfocused
launcher on real hardware. Whether Capture/Full-screen share that same
first-click-swallowed symptom (this ticket's own acceptance bar) is
likewise unconfirmed for the same reason; both buttons now log
`_on_capture_click: dispatched` / `_start_full_capture: dispatched` via
`debug_log`, alongside `_toggle_recording`'s own dispatch log, so a real
hardware pass with `TESTASSIST_DEBUG=1` can read back exactly which
handler fired on which click, the same standard this ticket's own
acceptance criteria ask for.

**What ships regardless:** auto-dock on record start plus locking
`_btn_dock_right`/`_btn_undock` for the duration (already the locked
decision above) structurally eliminates the vulnerable code path — once
docked, the floating panel's `_btn_stop` is never shown at all during a
recording, so the overlap this section measured cannot be reached by a
real click. This eliminates the confirmed geometric-overlap mechanism
even though it does not (and was never claimed to) address the separate,
still-unconfirmed OS-focus question.
