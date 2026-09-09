# Brief: implement TA-215, TA-217, TA-220 through TA-225, build, verify, report

## Why

The rc4 manual pass surfaced two kinds of finding: fixes that regressed or
were incomplete (TA-215, TA-217, TA-220 all reopened after rc4 claimed them
done), and new issues found during the first real second-monitor pass
(TA-221 through TA-225). All eight are now locked tickets in
`TESTASSIST_BACKLOG.md` with root cause, scope, deliverables and acceptance
criteria. TA-211's test guard (separate brief) is already done and verified
— commit `7bf77ee` — and is not part of this batch.

**Read each ticket in `TESTASSIST_BACKLOG.md` in full before starting it** —
the summaries below are for sequencing and for the handful of decisions this
brief locks in that the tickets themselves left open; they are not a
substitute for each ticket's own Scope/Deliverables/Acceptance criteria.

## Tickets in scope (all eight)

| ID | Priority | Class | File(s) | One-liner |
|---|---|---|---|---|
| TA-220 | P1 | confirmed fix + investigate | `editor.py` | `showNormal()` always drops a maximized Editor to windowed size on restore; minimize-toggle may not be firing (unconfirmed) |
| TA-217 | P1 | confirmed fix + investigate | `launcher.py` | Quick Capture button never wired to dismiss a blocking modal; hotkey path now dismisses About but the capture that should follow doesn't happen (unconfirmed) |
| TA-215 | P1 | confirmed fix + small addition | `launcher.py` | Finished recordings don't appear in History without reopening the editor; docked icon doesn't show "Video mode selected" before recording starts |
| TA-221 | P2 | confirmed fix | `editor.py` | Copy/Export button text clipped ("Copv"/"Exoort") — `setFixedHeight(26)` too tight for the QSS padding |
| TA-222 | P3 | confirmed fix | `editor.py` | Settings bar is left-packed + right-stretched instead of centered like the tool row above it |
| TA-223 | P1 | investigate first | `capture.py` | Drag-selection rectangle resizes unexpectedly crossing the laptop/external monitor boundary (DSP-03, DSP-07, DSP-08; possibly DSP-01) |
| TA-224 | P2 | scope decision, no code | — | No region-selection before recording (DSP-11) — real feature gap, not a bug |
| TA-225 | P1 | investigate first | `capture.py` / `screen_geometry.py` | Capture on the laptop in the secondary-above layout produces no visible content (DSP-04) — possibly the same mechanism as TA-223 |

## Decisions locked in this brief

Three tickets left an open call the code alone doesn't settle. Deciding them
here so there's no back-and-forth mid-implementation:

- **TA-221 — remove the fixed height, don't bump it.** Delete
  `setFixedHeight(26)` on `_btn_copy` and `_btn_export_json` and let both
  size naturally from the QSS padding, the way most other buttons in the
  file already do. `_btn_save_png`'s `setFixedHeight(28)` happens to clear
  the clipping today, but it's still a hand-tuned pixel value that can drift
  out of sync with the stylesheet again the next time padding or font-size
  changes. Removing the override is the fix that can't regress the same way
  twice.
- **TA-222 — center the whole row as one group**, matching
  `_build_tools_bar()`'s pattern exactly: add a leading `layout.addStretch()`
  before the zoom controls, keep the existing trailing stretch before
  Copy/Export/Save PNG. Not just the button cluster centered on its own —
  the two toolbar rows should read as the same layout system stacked
  vertically.
- **TA-224 — defer past 1.4.0.** This is a net-new capability (region-select
  before recording), not a bug, and 1.4.0's scope has already grown from
  seven tickets to sixteen since the manual pass started. Record the
  deferral on the ticket with this reasoning; no code change. If this
  judgment call is wrong, say so before it's built — it's cheap to reverse
  now and expensive once `TA-223`/`TA-225` work has already touched the same
  overlay code.

## Investigate-first items: instrument, don't guess

TA-220's minimize-toggle gap, TA-217's hotkey-capture gap, TA-223, and TA-225
all share the same problem: there's a plausible mechanism read from the code,
but no measurement from the actual dual-monitor hardware to confirm it. This
environment cannot reproduce any of the four (no second monitor, no
interactive Windows session) — the rc3/rc4 batches already ran into this
exact wall on TA-217's and TA-215's repro-first sub-items. Don't repeat the
guess-a-fix pattern. Instead, ship this build with logging that captures
what's actually happening, so the next manual pass produces a real
measurement instead of another "reportedly doesn't work."

- **TA-220:** log `isActiveWindow()`'s and `isMinimized()`'s values at the
  top of `bring_forward()` on every call.
- **TA-217:** log whether `_dismiss_active_modal_dialog()` found and closed a
  modal, and whether `_overlay.activate()`'s `singleShot` callback actually
  fires, on the hotkey path.
- **TA-223:** log the raw `event.globalPosition()` value from
  `mouseMoveEvent` alongside `QScreen.geometry()` for both screens, on every
  move during a drag.
- **TA-225:** log the selected rectangle as dragged and what
  `plan_capture()` receives and returns for it.

Gate all of it behind an environment variable (e.g. `TESTASSIST_DEBUG=1`) so
normal runs are unaffected, and write to a plain-text log file under
`paths.history_dir()` (or wherever fits the existing logging/debug
conventions in this codebase — use what's already there rather than
inventing a second mechanism if one exists). Confirm in the report which
convention was used.

None of these four get a blind fix in this batch. Ship the logging, install
the build, and the next manual pass on the actual hardware — laptop as
secondary, both left and above — will produce the log output needed to scope
the real fix as a follow-up ticket.

## Sequencing

1. **TA-220's confirmed part first** — small, isolated: check
   `Qt.WindowState.WindowMaximized` in the `isMinimized()` branch and call
   `showMaximized()` instead of `showNormal()` when it's set.
2. **TA-221 and TA-222** — both small, isolated, single-widget layout fixes,
   decisions already made above.
3. **TA-217's confirmed part** — wire `_dismiss_active_modal_dialog()` into
   the Quick Capture button's own click handler, not just the hotkey path.
4. **TA-215's confirmed part** — have `_on_record_finished()` trigger the
   same History refresh `_persist_history_snapshot()` already does. Then the
   video-mode-selected icon state as a second, smaller deliverable on the
   same ticket — reuse whatever icon-swap mechanism the rc4 recording
   indicator already established.
5. **The four investigate-first items together** (TA-220's remaining gap,
   TA-217's remaining gap, TA-223, TA-225) — same shape of work, same
   environment-variable logging convention, worth doing in one pass so the
   convention is only invented once.
6. **TA-224** — record the deferral decision on the ticket. No build
   dependency on anything else here; can happen any time in this batch.

## Explicitly out of scope for this brief

TA-211 (done, verified, commit `7bf77ee` — leave alone). Any actual fix for
TA-220's minimize-toggle gap, TA-217's hotkey-capture gap, TA-223, or TA-225
beyond the logging described above — those wait for real measurements from
the next manual pass, not this build.

## Build + verify

Same discipline as the rc3 and rc4 briefs — a build isn't proof by itself,
verify the artifact actually changed.

1. **Before starting**, record the current build artifact's identity for
   later comparison:
   ```powershell
   Get-FileHash python\dist\TestAssist\TestAssist.exe -Algorithm MD5
   ```
2. Implement all seven code items (TA-220, TA-221, TA-222, TA-217, TA-215,
   plus the logging for TA-220/TA-217/TA-223/TA-225), each with the test(s)
   its own ticket's Deliverables section calls for. Record TA-224's
   deferral on its ticket — no code.
3. Run the full suite on Windows:
   ```powershell
   $env:QT_QPA_PLATFORM = "offscreen"
   pytest -q
   ```
   Must be fully green — no skips beyond the existing TA-211 platform guard,
   no failures.
4. Push, confirm the `Python Tests` workflow goes green on the pushed commit
   before building.
5. Build:
   ```powershell
   git status               # must be clean, HEAD at the pushed commit
   cd python
   ..\.venv\Scripts\Activate.ps1
   .\build.ps1 -Zip -Shortcut
   ```
6. **Verify the build actually changed** — the hash from step 1 must differ
   from the new one.
7. Name the zip **rc5** (check `docs/BUILD_LOG.md` first in case something
   else has shipped since rc4 — don't reuse a number).
8. Install it following `MULTI_DISPLAY_MANUAL_PASS.md`'s S-1 through S-4
   (close Test Assist completely first — check the tray; rename the current
   `C:\TestAssist` install to keep it for comparison; install fresh).
9. **Report back in `docs/BUILD_LOG.md`, not chat** — one dated entry with:
   - New exe md5 + byte size
   - Installed path and zip path
   - Confirmation of the pushed commit hash and that CI was green on it
   - A one-line status per ticket: fixed + test added, deferred (TA-224,
     with the reasoning), or instrumented-not-fixed (the four
     investigate-first items) — and for those four, the exact env var name
     and log file location so the next manual pass knows where to look.

## What this unblocks vs. what's still blocked

Once rebuilt and installed: TA-220's maximize-restore, TA-221's button text,
TA-222's row alignment, TA-217's button-path dismiss, and TA-215's
History-refresh-on-finish all become re-testable manually against the new
build (single monitor is enough for all five).

Still blocked on the second monitor, same as before: TA-220's minimize-toggle
gap, TA-217's hotkey-capture gap, TA-223, and TA-225 — this batch instruments
them but doesn't fix them; the actual fix is a follow-up ticket once the log
output from the next manual pass is in hand. TA-224 stays deferred past
1.4.0 per the decision above unless overridden.

**Once TESTASSIST_BACKLOG.md is edited, commit it in the same commit as the
code changes** (`git add TESTASSIST_BACKLOG.md`) rather than leaving it as an
uncommitted working-copy edit — an uncommitted edit to this file has been
silently lost to a git operation twice already this project (see
`docs/BUILD_LOG.md`'s history and the note on this in the current session).
