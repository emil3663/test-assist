TA-240 — Clicking the annotation window's taskbar icon or its floating-toolbar icon does not bring it to the front

**Status: RESOLVED, not a Test Assist defect — confirmed 2026-09-15 as a Claude desktop app artifact of this verification session. See "Resolved" section near the end. A distinct, real gap found while confirming this is filed separately as `TA-241`.**

## Context

Reported directly by the user during TA-204 hardware verification (2026-09-15), not yet reproduced against source: after a capture, clicking either the Windows taskbar icon for the annotation/canvas window, or the corresponding icon in Test Assist's own floating capture toolbar, fails to bring that window to the foreground. It stays behind other windows and has to be found by minimizing unrelated apps one at a time.

**Possibly related, not yet confirmed as the same root cause:** `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-13 section already logged a related observation on the same floating toolbar — its camera icon "was inconsistently clickable this pass after other windows (Task Manager, File Explorer) had been interacted with... sometimes didn't register a click at all." That is a click-registration failure; this ticket's symptom is a click that registers but doesn't raise the window. They may share a root cause in the toolbar/canvas window's activation or z-order handling, or may not — treat as two symptoms to investigate together, not one confirmed bug, until the code is read.

No measurement beyond the user's direct report exists yet — this brief is filed to hold the report and a starting point, not a diagnosis.

## Change

Not yet investigated. Likely relevant: wherever the annotation/canvas window and the floating toolbar's icon click handlers raise or activate a window. Windows-specific foreground-window APIs are a common culprit here — `SetForegroundWindow` has well-known OS restrictions when the calling process isn't already the foreground process, which would explain "registers as a click, does nothing visible" rather than "click ignored entirely."

Starting points to grep for: the floating toolbar's click handler (likely near `FloatingLauncher` / `python/launcher.py` or similar, given TA-211's `_apply_hotkey_labels()` and hotkey-release code lives there) and whatever the canvas/annotation window uses to raise itself (`raise_()`, `activateWindow()`, or a Win32 call) — see `python/canvas.py`.

## Acceptance

- [x] Root cause identified: **not a Test Assist defect.** Confirmed 2026-09-15 (see "Resolved" section below) — the cause was the Claude desktop app's own always-on-top bug on Windows, active only during this bridged verification session, not anything in this codebase.
- [x] Clicking the annotation window's Windows taskbar icon brings it to the foreground — confirmed working once the environmental cause was cleared.
- [x] Clicking the floating toolbar's corresponding icon does the same — confirmed working once the environmental cause was cleared.
- [x] Decision recorded: **not** the same root cause as the floating-toolbar click-registration flakiness logged in `docs/TA-232-HARDWARE-VERIFICATION.md` (2026-09-13) — that remains a separate, still-open observation. A newly found, distinct, confirmed Test Assist behavior gap (the TA icon doesn't toggle-minimize an already-open edit page) is tracked separately as `TA-241` — see `docs/ISSUE-TA-241.md`.

## Not in this issue

- The floating toolbar's click-registration failure itself (clicks not registering at all) — logged in `docs/TA-232-HARDWARE-VERIFICATION.md`, not reproduced or diagnosed yet. Fold in only once the investigation above confirms a shared cause.
- HW-6 (cursor/reticle tracking, TA-233) and HW-7 (external taskbar full capture on fresh launch) — unrelated, still untested, tracked in `docs/TA-232-HARDWARE-VERIFICATION.md`'s punch list.

## Provenance

- User report, live hardware-verification session, 2026-09-15: "clicking on the edit screen in the task bar or in the floating widget don't bring the editing screen to the front...I had to minimise apps until I found it."
- Cross-referenced against `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-13 floating-toolbar click-registration note (possible shared cause, not confirmed).

## New evidence, 2026-09-15 — a data point against a Test Assist-specific cause

During unrelated HW-7 work in the same session, the user separately observed
that **Notepad's** taskbar icon also failed to bring its window to the front
— Notepad has no connection to this codebase. In parallel, the remote
computer-use bridge driving this session could not get **Task Manager**
(also unrelated to Test Assist) to respond to any interaction at all, and a
subsequent keystroke aimed at Test Assist's own window was rejected as still
belonging to Task Manager, as if OS focus never actually moved. Full account
in `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-15 section.

This doesn't clear the code path named in this ticket's **Change** section —
Test Assist's own `activateWindow()` / `raise_()` calls may still be broken
— but a Notepad-level failure of the same shape suggests the cause may sit
at the session/OS level (candidate: the Claude desktop app holding
foreground focus during a bridged remote-control session) rather than being
specific to Test Assist. Recommend whoever picks this up first reproduces
the original symptom (floating toolbar / taskbar icon not raising the
Test Assist window) with a person physically at the keyboard and no
Claude-driven session bridged to the machine at all — if it doesn't
reproduce that way, this ticket's root cause is elsewhere and it should be
re-scoped or closed as a session artifact rather than a Test Assist defect.
Not acted on further here — evidence only, no code touched, per the working
agreement.

## Resolved, 2026-09-15 (later) — confirmed environmental, not a Test Assist defect

Following on from the "New evidence" section above: the user restarted the
Claude desktop app (the always-on-top bug it has on Windows is not
persisted and clears on relaunch — see the GitHub issues cited in this
session's chat, `anthropics/claude-code#89467` and related). After the
restart, with the same Test Assist build, same verification session
otherwise unchanged:

- **Notepad's taskbar icon now brings it to the front normally.** This is
  the control case — Notepad has zero connection to this codebase, so its
  recovery confirms the "won't come to front" symptom really was the Claude
  desktop always-on-top artifact, not something wrong with any particular
  app's window-raise code.
- **Test Assist: using the floating widget's TA icon to open the edit
  page now works.** Same confirmation for the symptom this ticket was
  originally filed for.

This ticket's original report is therefore resolved as a session artifact,
not a Test Assist code defect. Nothing in `python/canvas.py` or the
floating-toolbar launcher needs changing for the symptom as originally
described.

**However, while confirming this, a distinct, real, still-present gap was
found and is *not* explained by the always-on-top artifact:** clicking the
TA icon a second time, while the edit page is already open and frontmost,
does not minimize it. This is a toggle-show/hide behavior that's either
missing or broken in the floating toolbar's click handler — a genuine Test
Assist behavior gap, unrelated to any focus-stealing by another app. Filed
separately as `TA-241` (`docs/ISSUE-TA-241.md`) so it can go into the next
build's fix list. Not fixed here — code work, goes through Claude Code in
VS Code per the working agreement.

The floating toolbar's earlier-logged click-registration flakiness
(`docs/TA-232-HARDWARE-VERIFICATION.md`, 2026-09-13 section — the camera
icon sometimes not registering a click at all) remains open and unexplained
by any of the above; it may or may not share a cause with `TA-241` and
should be looked at together with it, not assumed identical.
