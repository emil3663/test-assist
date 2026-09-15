TA-240 — Clicking the annotation window's taskbar icon or its floating-toolbar icon does not bring it to the front

## Context

Reported directly by the user during TA-204 hardware verification (2026-09-15), not yet reproduced against source: after a capture, clicking either the Windows taskbar icon for the annotation/canvas window, or the corresponding icon in Test Assist's own floating capture toolbar, fails to bring that window to the foreground. It stays behind other windows and has to be found by minimizing unrelated apps one at a time.

**Possibly related, not yet confirmed as the same root cause:** `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-13 section already logged a related observation on the same floating toolbar — its camera icon "was inconsistently clickable this pass after other windows (Task Manager, File Explorer) had been interacted with... sometimes didn't register a click at all." That is a click-registration failure; this ticket's symptom is a click that registers but doesn't raise the window. They may share a root cause in the toolbar/canvas window's activation or z-order handling, or may not — treat as two symptoms to investigate together, not one confirmed bug, until the code is read.

No measurement beyond the user's direct report exists yet — this brief is filed to hold the report and a starting point, not a diagnosis.

## Change

Not yet investigated. Likely relevant: wherever the annotation/canvas window and the floating toolbar's icon click handlers raise or activate a window. Windows-specific foreground-window APIs are a common culprit here — `SetForegroundWindow` has well-known OS restrictions when the calling process isn't already the foreground process, which would explain "registers as a click, does nothing visible" rather than "click ignored entirely."

Starting points to grep for: the floating toolbar's click handler (likely near `FloatingLauncher` / `python/launcher.py` or similar, given TA-211's `_apply_hotkey_labels()` and hotkey-release code lives there) and whatever the canvas/annotation window uses to raise itself (`raise_()`, `activateWindow()`, or a Win32 call) — see `python/canvas.py`.

## Acceptance

- [ ] Root cause identified: which call is supposed to raise the window, and why it doesn't on this hardware/OS state.
- [ ] Clicking the annotation window's Windows taskbar icon brings it to the foreground, focused, from any window state (minimized, behind other windows).
- [ ] Clicking the floating toolbar's corresponding icon does the same.
- [ ] A decision recorded on whether this shares a root cause with the floating-toolbar click-registration issue logged in `docs/TA-232-HARDWARE-VERIFICATION.md` (2026-09-13) — either confirmed and fixed together, or confirmed separate and this ticket scoped to the raise-to-front behavior only.

## Not in this issue

- The floating toolbar's click-registration failure itself (clicks not registering at all) — logged in `docs/TA-232-HARDWARE-VERIFICATION.md`, not reproduced or diagnosed yet. Fold in only once the investigation above confirms a shared cause.
- HW-6 (cursor/reticle tracking, TA-233) and HW-7 (external taskbar full capture on fresh launch) — unrelated, still untested, tracked in `docs/TA-232-HARDWARE-VERIFICATION.md`'s punch list.

## Provenance

- User report, live hardware-verification session, 2026-09-15: "clicking on the edit screen in the task bar or in the floating widget don't bring the editing screen to the front...I had to minimise apps until I found it."
- Cross-referenced against `docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-13 floating-toolbar click-registration note (possible shared cause, not confirmed).
