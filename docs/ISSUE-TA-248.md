TA-248 — The launcher's "Open Editor" control also closes the editor now, but still only says "Open"

## Context

Found while confirming TA-241's hardware repro for 1.5.0 (2026-09-16):
clicking the launcher's editor control minimizes an already-open,
frontmost editor on a second click — `bring_forward()`'s TA-220 toggle,
confirmed working end to end on real hardware against the rebuilt
launcher. But every label on that control still only describes the
"open" half of what it now does:

- The header icon-only button (`_btn_open_editor`, `launcher.py:180-190`):
  tooltip and accessible name both "Open Editor".
- The expanded-panel wide button (`_btn_open_editor_wide`,
  `launcher.py:317-322`): visible text "  Open Editor", same accessible
  name.
- The docked strip's button (`btn_dock_editor`, `launcher.py:435-436`):
  tooltip and accessible name "Open Editor".

All three route to the same `self._editor.bring_forward.connect(...)`
(`launcher.py:367-368,438`). A user who clicks it a second time while the
editor is already frontmost gets a real, correct minimize — but nothing
on the control told them that click would do anything other than "open",
which is the same discoverability shape as `TA-247`'s tray-hide finding:
a real, working mechanism whose own labeling doesn't say what it does.

## Change

Not yet decided — either direction resolves it:

- Rename the label to something that covers both directions ("Editor" on
  its own, letting the icon/state carry the rest) rather than a verb that
  is only ever half true.
- Spell out both directions explicitly ("Open/Close Editor" or similar).

Whichever is chosen should apply to all three call sites above
consistently, not just the one most visible in a screenshot.

## Acceptance

- [ ] A decision is recorded on the exact new label text.
- [ ] All three controls' tooltip/visible text/accessible name are updated
      together, so they stay in agreement with each other and with what
      `bring_forward()` actually does.
- [ ] `test_LAUNCH_09_every_launcher_attribute_this_suite_names_exists`
      (or any other test asserting the current "Open Editor" string) is
      updated to match, not left asserting stale text.

## Not in this issue

- `bring_forward()`'s minimize/restore mechanism itself — confirmed
  correct on real hardware this session, not the gap here.
- `TA-247` — the tray-hide confirmation gap. Same "a real mechanism
  needs better labeling" shape, different control, filed separately.

## Provenance

- User's own observation while running the TA-241 hardware repro this
  session (2026-09-16): the toggle itself works correctly; the button
  text should read "Editor" or "Open/Close Editor" instead of "Open
  Editor". Explicitly called out as cosmetic and not release-blocking for
  1.5.0.
- Call sites confirmed by reading `python/launcher.py` directly, not
  assumed from the one control the report was made against.
