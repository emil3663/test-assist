TA-247 — Hiding the launcher to the tray gives no in-the-moment confirmation, and is easy to lose track of afterward

## Context

Found during the Launcher Evaluation Pass's written questions (Q3,
2026-09-16). Q3 asked whether the tester read the footer text ("Hides to
the tray · right-click → Quit") and whether it told them something they
didn't know. Their answer: *"i can't see what hides to tray is or if there
is an icon for it."* Follow-up, once asked whether to raise it: *"q3
should be raised as this will become an issue if we merge branches."*

Confirmed by reading the code directly, not just accepting the report:

- The tray icon itself is implemented correctly and works. `main.py`'s
  `_setup_tray()` creates a real `QSystemTrayIcon` with the actual app
  icon (`assets/icon.ico`), a working context menu (Show Launcher / Open
  Editor / Exit), and single-click-to-restore (`_on_activate()`). This is
  not a wiring bug — the icon genuinely exists and works once found.
- `_close_launcher()` (`launcher.py:694-700`), wired to the launcher's `X`
  button (tooltip "Hide to tray"), does exactly one thing: `self.hide()`.
  Nothing else happens — no toast, no balloon, no status message, nothing
  that confirms to the user at the moment of hiding that this occurred or
  where the app went.
- Searched the whole codebase for `showMessage`/`balloon`/`toast`/`notify`:
  the only hit is `editor.py:802`, an unrelated status-bar message about
  an empty clipboard on paste. `QSystemTrayIcon.showMessage()` — the
  actual Windows-native toast API for exactly this situation — is never
  called anywhere.
- The team already knows this is a real gap, twice over, in existing
  comments: `editor.py:271-272` and `editor.py:399-400` both say, near
  identically, that Windows hides a *new* tray icon in the notification
  area's overflow chevron by default, and that this is specifically *why*
  the Editor window carries its own "Show Launcher" 🏠 button — "once the
  launcher's own X hides it, the tray was the only route back."

That fallback only helps if the Editor happens to be open at the time. If
a user hides the launcher (its `X`) without ever having opened the Editor
in that session, the only way back is a tray icon they were never told
exists, sitting whichever wherever Windows chose to hide it — and nothing
in the moment of hiding tells them so. The footer text is the only
documentation of this behavior, and it's easy to not read, or to read once
and forget under Windows' default overflow hiding.

## Change

Not yet decided — candidate directions:

- Call `tray.showMessage("Test Assist", "Still running — right-click the
  tray icon to reopen or exit.", ...)` from `_close_launcher()` so the
  moment of hiding also confirms where the app went and how to get it
  back. Windows renders this as a native toast, which also visually points
  at the tray area.
- Consider showing it only the first time per session (or per install) so
  it doesn't become noise for a user who already knows.
- No API exists to force Windows to keep an icon out of the overflow
  permanently (that's an OS/user setting, not something the app controls)
  — so this fix is about confirmation and one-time education, not forcing
  visibility.

## Acceptance

- [ ] Hiding the launcher gives an immediate, visible confirmation of
      where it went and how to reopen it, without requiring the user to
      have already read the footer or to already have the Editor open.
- [ ] Verified against a fresh/first-run state, not just read from the
      code — the whole point is what a user who has never seen this before
      actually notices.

## Not in this issue

- The tray icon, its menu, and click-to-restore mechanism itself —
  confirmed correct by direct code read (`main.py`'s `_setup_tray()`).
  This is purely a missing-feedback gap at the moment of hiding, not a
  broken tray implementation.
- TA-218 (Check for Updates icon recognizability) — same "is a control
  discoverable" theme, different control, already resolved separately.

## Provenance

- Tester's written answer, Launcher Evaluation Pass Q3, 2026-09-16: "i
  can't see what hides to tray is or if there is an icon for it."
- Tester's explicit request to raise it as a ticket: "q3 should be raised
  as this will become an issue if we merge branches."
- Mechanism confirmed by direct code read: `python/main.py` (`_setup_tray`,
  `_make_tray_icon`), `python/launcher.py` (`_close_launcher`,
  `python/launcher.py:694-700`), `python/editor.py` (comments at
  `:271-272` and `:399-400` documenting the team's existing awareness of
  Windows' overflow-hiding behavior), and a full-codebase search
  confirming no `showMessage()` call is wired to the hide action.
