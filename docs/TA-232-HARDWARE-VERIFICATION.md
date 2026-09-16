# TA-232 — hardware verification (post-fix)

Everything automated has passed (`pytest python/tests/` — 339 passed, 3 pre-existing
unrelated `TA-211` failures, confirmed present on `main` too). What's left needs a
human on the actual dual-monitor rig, confirmed build (`C:\TestAssist-1.4.0`, not an
rc build — check Task Manager file location before starting, per today's earlier
mix-up).

| ID | Test | Expected | Status |
|----|------|----------|--------|
| HW-1 | Region covering the laptop's **taskbar** — drag a selection into the reserved band and capture | Selectable and captured in full, not clipped (`CAP-21` on the laptop — previously blocked, never run there) | ✅ PASS (2026-09-13, remote session) |
| HW-2 | Trigger a Windows toast notification on the laptop, capture a region over it | Notification appears in the saved image (`CAP-22` on the laptop — previously blocked, never run there) | ✅ PASS (2026-09-13, user at the rig — see note) |
| HW-3 | Raw Print Screen of the **live overlay** on the laptop (not a Test Assist capture — the overlay itself, mid-drag) | No interior brightness step anywhere on the panel — this is the original measurement method that found the bug, re-run to confirm it's actually gone | ⬜ blocked this pass (see note) |
| HW-4 | Drag a selection starting on one screen, ending on the other | Single composited image, no truncation, no duplication — the cross-screen `grabMouse()` handoff working for real, not just in the stubbed test | ⬜ blocked this pass (see note) |
| HW-5 | Drag slowly across the laptop/external boundary, watching closely | Selection rectangle tracks the cursor smoothly, no visible jump or resize at the crossing (`TA-223` — has never been confirmed on hardware; debug logging is already in place in `capture.py` if this needs a closer look after) | ⬜ |
| HW-6 | Watch the capture cursor/reticle during a normal drag | Tracks the region actually being drawn (`TA-233` — evidence so far was hand-annotated, not measured; check whether this reads as resolved now or still needs its own fix) | ⬜ |
| HW-7 | On the **external** screen only: full quick capture over the taskbar clock, on a fresh launch of the confirmed build, **no restart in between** | Captures the clock in full on the first attempt (2026-09-12 handover §8 — a *different* screen and a *different* symptom shape than TA-232, never re-tested on a build known to be correct) | ✅ PASS (2026-09-15, measured) |

If HW-1 through HW-4 all pass, TA-232's Acceptance section in `docs/ISSUE-TA-232.md`
is fully met — that's the point where the commit trailer becomes `Closes #21`
instead of `Refs #21`. HW-5 through HW-7 are separate tickets (TA-223, TA-233, and
a possible new one for HW-7) and don't block closing TA-232 either way.

## 2026-09-13 pass — HW-1 and HW-2 results, HW-3–4 blockers

HW-1, HW-3 and HW-4 were attempted remotely (Claude driving the physical
rig's mouse/keyboard/screenshots via a computer-use bridge, not a person
at the keyboard); HW-2 was then run by the user directly at the rig after
the remote session flagged what it needed (laptop as primary display).
Full account in `SESSION_HANDOVER_2026-09-13.md` §9. Summary:

- **HW-1: PASS, measured.** Dragged a selection on the laptop screen from
  above the taskbar down to its bottom edge; the exported PNG
  (`Documents\Test Assist\HW1-laptop-taskbar-capture.png`) contains the
  weather widget, Start button and search box in full — not clipped.
  Column/row pixel-sampled with Pillow, not eyeballed.
- **New, unexplained observation (not a HW-1 failure):** that same PNG's
  very last pixel row is solid `(0,0,0)` across its full width — confirmed
  by sampling every 20th pixel of the bottom 3 rows. Rows above it carry
  normal taskbar-gradient color. A same-shape older evidence file
  (`test-assist-1789195366 taskbar capture.png`, pre-dates this session)
  does **not** show this — its bottom row is normal gradient. Not
  diagnosed: could be the capture region touching the literal bottom edge
  of the laptop panel (this drag's end coordinate was the last valid pixel
  row), could be something else. Whoever picks up HW-1's follow-through
  should re-drag a selection that stops a few px short of the physical
  bottom edge and see if the black row disappears — that would confirm
  it's an edge/off-by-one condition rather than a rendering defect.
- **HW-2: PASS, measured — completed by the user directly, not remotely.**
  Made the laptop primary, extended the notification-dismiss timeout to
  5 minutes (Settings → Accessibility → Visual effects) to remove the
  timing pressure, triggered a real toast (Win+Shift+S → any throwaway
  snip → the "Screenshot copied to clipboard" Snipping Tool toast), then
  ran a normal TestAssist region capture over it. Saved output
  (`Documents\Test Assist\test-assist-1789325114 windows toast
  captured.png`, 529×486) contains the toast's bell icon, app label,
  both body lines and the "Mark-up and share" button in full — not
  clipped. Edges/corners of this PNG sampled with Pillow and are all
  normal dark chrome, no black-line artifact like HW-1's (see above) —
  one more point toward that being an edge/off-by-one condition specific
  to dragging to the literal screen boundary, not a general defect.
  **Incidental observation, not a defect:** a raw Print Screen taken
  while TestAssist's blue selection tint was active under the toast
  shows the toast drawn fully opaque *on top of* the tint, i.e. the
  selection highlight doesn't visually show through the notification.
  This is expected — Windows toasts render in an always-on-top shell
  layer above ordinary application windows, including TestAssist's own
  overlay — and it doesn't affect the actual capture output, which reads
  real screen content rather than TestAssist's own composited overlay.
- **HW-3: blocked.** Tried to hold a drag (mouse down, mid-drag, selection
  rectangle visibly active) and fire a raw Print Screen while still held,
  twice. Both times, sending the key through the remote bridge caused
  TestAssist to finalize the drag as a completed capture instead of the
  key reaching Windows as a screen-grab — the two inputs don't compose
  through this bridge. A person with a physical keyboard and mouse doesn't
  have this problem.
- **HW-4: blocked.** The cross-screen `grabMouse()` handoff needs genuinely
  continuous mouse motion across the physical screen boundary. The
  remote bridge validates/clamps coordinates to whichever single monitor
  is currently addressed, so a drag has to be stitched from a press on
  monitor A + a teleport-style move to monitor B — tried twice, and both
  times TestAssist treated the jump as the drag ending, not crossing. Needs
  a physical mouse doing one continuous motion across the bezel.
- Also worth knowing for whoever picks this up remotely again: TestAssist's
  floating capture toolbar (the small always-on-top TA/camera/history
  strip) was inconsistently clickable this pass after other windows (Task
  Manager, File Explorer) had been interacted with — the camera icon
  sometimes didn't register a click at all, with no visible error. Clicking
  the TA icon first, then the camera icon, in the same short burst (no
  other clicks in between) was the only sequence that worked reliably.

## 2026-09-15 pass — HW-7 result, and a focus/z-order observation that may reframe TA-240

**HW-7: PASS, measured.** Test Assist was fully closed (confirmed absent from
Task Manager's process list, sub-processes included) and relaunched fresh —
no prior captures, no restart in between launch and capture. On the very
first quick-capture, the user dragged a selection over the external screen's
taskbar clock and saved it (`Documents\Test Assist\test-assist-1789503144.png`,
199×90). Pillow bounding-box of the clock/date text's bright pixels: (127,54)
to (187,79) — 11px clear margin to the right edge, 10px clear margin to the
bottom edge, nothing touching any border. The clock ("22:12") and date
("2026/09/15") are both captured in full, not clipped. This does not
reproduce the 2026-09-12 handover §8 theory (stale display geometry from
before the external was connected persisting until restart) on this build.

**Why this one had to be done by the user, not remotely:** the remote
computer-use bridge's permission model gives Windows shell apps (File
Explorer, and by extension the taskbar it owns) a permanently click-only
tier — no drag gestures — as a deliberate restriction, not a bug. Since the
capture region has to end on the taskbar, the drag itself can't be issued
through the bridge. Noted here in case a future remote pass hits the same
wall.

**Observation, not yet a confirmed diagnosis — logged for whoever picks up
`TA-240`:** during this same session, the remote bridge also could not get
**Task Manager** (an unrelated Windows shell app, not part of Test Assist)
to respond to *any* interaction — row selection, column-header sort,
End Task, minimize, or close all silently no-opped across roughly a dozen
attempts, while live data in the window kept refreshing normally. Switching
to Test Assist's own window on the external monitor and clicking inside it
did not transfer OS focus either: a subsequent keystroke was still rejected
with "Taskmgr is granted at tier click" as if it were still the foreground
window. Separately, the user reported firsthand (this session, not
reproduced by Claude) that neither Test Assist's floating-toolbar icon nor
its taskbar icon, **nor Notepad's taskbar icon**, would bring their window
to the front on the same screen. Notepad is not part of this codebase, which
points at something at the session/OS level — possibly the Claude desktop
app's own window holding foreground/focus during a bridged session — rather
than a defect in Test Assist's own window-raise code. `TA-240` was filed
assuming a Test Assist-specific cause (`activateWindow()` / `raise_()` /
`SetForegroundWindow` in the canvas or floating-toolbar code); this
observation doesn't rule that out, but the Notepad data point means it
shouldn't be assumed either until someone reproduces TA-240's symptom
**without** a Claude-driven session in the picture at all (person at the
keyboard, Claude Desktop not running or not bridged). Left as evidence, not
acted on — no code touched here per the working agreement.

## 2026-09-16 — TA-222 regression found (settings bar centering)

**Status: TA-222 reopened.** Believed fixed and shipped in `v1.4.0`; confirmed
during this session's QA work that the fix does not actually achieve the
centering it claims.

**What was observed:** a QA tester's screenshot of the Editor window (title
bar "Test Assist 1.4.0 — Editor") shows row 2 of the Editor toolbar (zoom
controls, stroke-width slider, the "Classic" arrow-style dropdown, opacity
slider, then Copy / Export / Save PNG) **not** centered under the tool-icon
row above it. Instead: the left cluster (zoom…opacity) sits flush against the
window's left edge, Copy/Export/Save PNG sit flush against the right edge,
and there is a large empty gap in between — visually indistinguishable from
the original pre-fix bug report.

**Root cause — confirmed by reading `python/editor.py`'s
`_build_settings_bar()`:** the row is a single `QHBoxLayout`, built in this
order:

1. `layout.addStretch()` — leading, **stretch factor 0** — added by the
   TA-222 fix commit `5783f8d` (line 459 on current `main`).
2. zoom controls → separator → stroke-width slider → separator →
   arrow-style combo → separator → opacity slider.
3. `layout.addStretch(1)` — mid-row, **stretch factor 1** — this stretch
   pre-dates the TA-222 fix commit and was never touched by it (line 531 on
   current `main`).
4. Copy, Export, Save PNG buttons, with **no trailing stretch** after them
   (`return bar` at line 556 on current `main`).

Qt's `QBoxLayout` gives *all* extra horizontal space to whichever stretch
item has the highest stretch factor; when factors differ, the lower-factor
stretch does not share in the extra space at all. Here the leading stretch
(factor 0) gets none of the extra width and collapses to ~0px, while the
mid-row stretch (factor 1) absorbs the *entire* leftover gap between the
opacity slider and the Copy button. The result is exactly the "hard left,
huge gap, hard right" layout in the screenshot — the leading stretch added
by the fix is present in the code but structurally inert.

This is unlike `_build_tools_bar()` (line ~292), which centers its icon
group correctly: it uses `addStretch()` (factor 0, no argument) on **both**
ends, so the two stretches have matching factors and Qt splits the leftover
space evenly between them, producing true centering.

**The TA-222 fix commit's premise was wrong on two counts**, not one:

- It added a factor-0 stretch to match a factor-1 stretch, so the two ends
  never compete for space on equal terms (the one-line bug).
- `_build_tools_bar()` has no mid-row stretch and no right-anchored
  subgroup at all — it is *just* an icon group between two matching
  stretches. `_build_settings_bar()` has a third element the tools bar
  doesn't: the Copy/Export/Save PNG cluster anchored to the right by the
  mid-row stretch. The fix commit's message claimed to match
  `_build_tools_bar()`'s pattern, but the two layouts aren't structurally
  analogous, so "add a leading `addStretch()`" alone can't reproduce that
  pattern regardless of stretch factor.

**Confirmed present in — this is not a stale-build artifact:**

- `v1.4.0` as tagged and shipped (tag `v1.4.0`, commit `23f1f51`, dated
  Sep 12) — contains the original "fix" commit `5783f8d`.
- Current `main` tip (commit `2e49940`).
- The `ui-polish` review worktree HEAD (commit `90fcf92`) — the pending
  launcher-rebuild branch under evaluation.

All three read identical code at `_build_settings_bar()` (lines ~431–575).
Every current build — shipped, mainline, and the branch being evaluated for
the next release — has this bug.

**Why this needs a decision, not just a one-line tweak:** because of the
second structural difference above, simply changing `addStretch(1)` to
`addStretch()` would center the *entire* row (zoom through Save PNG) as one
block, pulling Copy/Export/Save PNG in from the right edge toward the
middle — a materially different visual result than "the left cluster is
centered and the export buttons stay right-anchored," which is also a
plausible reading of the original bug report and the backlog's acceptance
wording. Two real options exist:

- **(a)** Remove the mid-row stretch entirely and treat the whole row —
  zoom through Save PNG — as one centered group, matching
  `_build_tools_bar()`'s pattern exactly (`addStretch()`, factor 0, on both
  true ends, nothing else on the row).
- **(b)** Keep Copy/Export/Save PNG deliberately right-anchored as a
  separate design intent, in which case only the left cluster should be
  centered within the remaining space to its left of that right-anchored
  group, and the ticket's acceptance criteria ("centered below the editing
  icons") should be read as referring to the left cluster only, not the
  full row.

This is a product/design call, not something the code alone settles — the
same open question the original TA-222 ticket text flagged and that was
not actually resolved by commit `5783f8d`. TA-222 should not be considered
closed until that decision is made explicit and a corresponding code fix
(not the current one) lands. No code was changed as part of this finding,
per the working agreement — this is a documentation-only pass.
