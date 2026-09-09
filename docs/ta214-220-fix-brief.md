# Brief: implement TA-214 through TA-220, build, verify, report

## Why

Seven issues were found and confirmed in code during the rc3 manual pass and
are now locked tickets in `TESTASSIST_BACKLOG.md`. Handing this batch over now
— rather than waiting for the full manual pass to finish — so the fixes can be
built while the rest of the manual pass (the items still needing the second
monitor, or a clean machine) continues in parallel.

**Read each ticket in `TESTASSIST_BACKLOG.md` in full before starting it** —
the summaries below are for sequencing, not a substitute for the ticket's own
Scope/Deliverables/Acceptance criteria, which are where the actual
requirements live.

## Tickets in scope (all seven)

| ID | Priority | File(s) | One-liner |
|---|---|---|---|
| TA-214 | P1 | `editor.py` | No way to open a file or paste from clipboard once the editor is open with nothing loaded |
| TA-215 | P1 | `launcher.py` | Docked capture icon never shows recording state; no running-time indicator while docked |
| TA-216 | P1 | `editor.py` | A capture isn't kept anywhere (History) until Save or Copy is explicitly run |
| TA-217 | P1 | `editor.py`, `capture.py` | Quick Capture doesn't reliably work while another window has focus (confirmed: About dialog's Qt modality; unconfirmed: Windows Properties dialog) |
| TA-218 | P2 | `launcher.py` | Check for Updates icon is unrecognizable, and only reachable from the launcher |
| TA-219 | P1 | `editor.py` | Save PNG / Export JSON default to the app's install folder, not `Documents\Test Assist` |
| TA-220 | P1 | `editor.py` | The TA icon doesn't restore the Editor when it's minimized |

## Sequencing

1. **TA-219 and TA-220 first** — both small, isolated, single-function fixes
   with no interaction with anything else in this batch. Good warm-up, fast
   wins.
2. **TA-214 and TA-216 together, same PR** — both tickets are the same
   underlying gap ("how do I get back to an image I'm not currently looking
   at"), and fixing one without the other leaves the workflow still broken:
   TA-216 without TA-214 means captures are in History but you still can't
   pull an *external* file in; TA-214 without TA-216 means you can open a
   file but your own captures still vanish unless saved.
3. **TA-217's confirmed case (About dialog)** — implement per the ticket's
   Scope. **TA-217's Properties-dialog sub-case is repro-first, not
   fix-first**: if a repeatable repro can't be established, say so plainly in
   the report rather than guessing at a fix for an intermittent issue with no
   confirmed mechanism.
4. **TA-215** — the docked-recording feedback fix is a normal implement; the
   PKG-05 sub-item (docked Properties-dialog capture) is also repro-first,
   same rule as above — get a precise repro or report "not reproducible,"
   don't guess.
5. **TA-218 last** — P2, no dependency on anything else here.

## Explicitly out of scope for this brief

Nothing beyond these seven tickets. In particular: the TA-211 tests' missing
`skipif` guard on `ctypes.windll` (flagged separately, no decision made on it
yet) — leave it alone, it isn't part of this batch.

## Build + verify

Same discipline as the rc3 brief — a build isn't proof by itself, verify the
artifact actually changed.

1. **Before starting**, record the current build artifact's identity for
   later comparison:
   ```powershell
   Get-FileHash python\dist\TestAssist\TestAssist.exe -Algorithm MD5
   ```
2. Implement all seven tickets, each with the test(s) its own Deliverables
   section calls for.
3. Run the full suite on Windows (where `ctypes.windll` is real, not stubbed):
   ```powershell
   $env:QT_QPA_PLATFORM = "offscreen"
   pytest -q
   ```
   Must be fully green — no skips, no failures, including the TA-211 hotkey
   tests (they run for real on Windows).
4. Push, confirm the `Python Tests` workflow goes green on the pushed commit
   before building.
5. Build:
   ```powershell
   git status               # must be clean, HEAD at the pushed commit
   cd python
   ..\.venv\Scripts\Activate.ps1
   .\build.ps1 -Zip -Shortcut
   ```
6. **Verify the build actually changed** — the hash from step 5 must differ
   from the one recorded in step 1.
7. Name the zip the next `rc` in sequence (check `docs/BUILD_LOG.md` for the
   last one used — this is rc4 unless something else has shipped since;
   don't reuse rc3).
8. Install it following `MULTI_DISPLAY_MANUAL_PASS.md`'s S-1 through S-4
   (close Test Assist completely first — check the tray; rename the current
   `C:\TestAssist` to keep it for comparison; install fresh).
9. **Report back in `docs/BUILD_LOG.md`, not chat** — one dated entry with:
   - New exe md5 + byte size
   - Installed path and zip path
   - Confirmation of the pushed commit hash and that CI was green on it
   - A one-line status per ticket: fixed + test added, or (for the two
     repro-first items) reproduced-and-fixed / not reproducible with what was
     tried

## What this unblocks vs. what's still blocked

Once rebuilt and installed, these become re-testable manually against the new
build: TA-214 (open/paste), TA-216 (auto-history), TA-219 (save-location
default), TA-220 (minimize/restore), TA-215's docked-recording feedback,
TA-217's About-dialog capture, and TA-218's icon.

Untouched by this batch, exactly as blocked as before: everything in
`MULTI_DISPLAY_MANUAL_PASS.md` that needs the second monitor or a clean
machine (Blocks A–D, PKG-04), and TA-217/TA-215's repro-first sub-items if no
repro is found.
