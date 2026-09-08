# Before the next build — outstanding work

**Date:** 2026-09-07
**HEAD:** `136be0d` (overlay geometry fix) — pushed
**Uncommitted:** the docking fix, the help.html pass, plus untracked reference docs

## State

Committed and pushed: the multi-display capture fix, the data-location move, and
the overlay geometry fix. `origin/main` is level with local.

Uncommitted in the working tree: the DSP-12/13/14 docking fix (verified, awaiting
its commit) and the partially-done `help.html` content pass.

Everything below is what Claude Code still has to do **before I pull a build**.

---

## 1. Commit the docking fix — DONE, needs committing only

Verified independently: 239 pass; reverting the dock band fails 4 tests,
reverting the gap fallback fails `test_DSP_13`. Commit message already supplied.

## 2. Small fixed-size buttons render empty — NOT STARTED

The global `QPushButton` rule sets `padding: 7px 14px`. The About button is
28×28, so 14px each side consumes the whole width and the glyph has nowhere to
draw. Zoom `−` and `+` are 24×24 against 28px of horizontal padding; `Fit` is
24px tall against 14px vertical padding plus a 12px font. Four buttons draw as
empty shapes. `#btn_help` is the only one that renders — because its rule sets
`padding: 0`, which is an accidental workaround rather than a special case.

Fix as one systemic problem: a shared objectName/class for small icon buttons
with `padding: 0` and a suitable font-size, applied to About, zoom out, zoom in
and Fit. Not four separate rules.

**Blocks DSP-17** — the About dialog cannot be manually tested while its button
is invisible.

## 3. Disabled button text is unreadable — NOT STARTED

`QPushButton:disabled` uses `color: LINE_STRONG #3a3a5e` on `BG_900 #0d0d1a`.
Measured contrast: **1.79:1**. WCAG AA wants 4.5:1 for body text, 3:1 for large.
It is a border token used as a text colour. `MUTED #8892a4` gives 6.14:1.

Became visible because the layer buttons now disable when nothing is selected —
correct behaviour that exposed a pre-existing style bug.

Add a test asserting no stylesheet rule sets a text colour below 3:1 against its
own background. A contrast function is a dozen lines and catches the whole class.

## 4. Recordings are invisible in the app — NOT STARTED

The editor's history gallery globs `*.png` from the history folder and has no
concept of video, so a recording appears nowhere in the UI. Not a regression —
frame-by-frame video annotation is already ❌ Not done — but "the app makes a
file and never mentions it again" is poor regardless.

Discoverability only: list recordings in the gallery, visually distinguished,
click opens the system player. **No** in-app playback, frame extraction or
annotation. Two traps: the gallery assumes every entry is a loadable QPixmap, and
recordings must be read from `recordings_dir()` so the history pruning can never
touch them.

## 5. Finish TA-203 — the help.html content pass — PARTIALLY DONE

Video mode card done. Still pending: Check for Updates, About/diagnostics,
multi-display behaviour, and the keyboard-shortcuts pin decision.

## 6. Backlog tickets only — DO NOT IMPLEMENT

- **Region-selected video recording.** Recording is whole-screen by design and
  always has been. Odd asymmetry for an evidence tool; route is to reuse the
  existing selection overlay for a crop rect plus ffmpeg `-vf crop`.
- **Canvas padding around the image**, so annotations can extend past the image
  edge. The decision that matters: does the exported PNG include the margin or
  crop back to the image?

## 7. "Show in folder opened `docs\`" — RESOLVED, NOT A BUG

Retested on real hardware: the button opens `Documents\Test Assist`, which is
correct. The earlier sighting was a misread of the Explorer breadcrumb. No work.

## 8. Spanning capture leaves a black band — NOT STARTED (new, DSP-08 FAILED)

DSP-08 was run and failed. A selection dragged from the laptop across to the
external produced a correct composite — laptop content left, external content
right, right order, right pixels — with a solid black band roughly 384px wide
between them.

The band is **not wrong content, it is unpainted content.** The layout is laptop
`-1920..-384` (1536 logical px at DPR 1.25) and external `0..1920`, so
`-384..0` is virtual-desktop coordinate space that belongs to no screen at all.
`capture.py:226` allocates the result at `global_rect.size()` and fills it
transparent; `plan_capture()` correctly emits no piece for the dead zone, so
those columns are never painted and every viewer renders transparent as black.

**Decision: close the gap.** Composite the pieces adjacently instead of at their
virtual-desktop offsets — laptop content butting straight against external
content, result width = sum of the piece widths, no band. A tester who drags a
selection across two monitors is asking for "both screens side by side", not a
coordinate-accurate map of a desktop that has a hole in it.

Implementation note: the substance is a change to `dest` in `plan_capture()` —
walk the pieces in order of `intersection.left()` and accumulate x rather than
using `intersection.topLeft() - global_rect.topLeft()`. `capture.py` then needs
one consequent change: size the result pixmap from the pieces' bounding box, not
from `global_rect.size()`, or the gap simply reappears as trailing black.
Vertical
offsets keep their true relative positions — screens at different heights are a
real relationship, not a gap. A single-screen selection must still produce
exactly one piece at `(0,0)` covering the whole rect: pin that with a test so the
common path cannot drift.

Tests: two screens with a gap → two pieces, second `dest.x()` equal to the first
piece's width; two screens that abut → identical output to today; one screen →
unchanged.

**This unblocks CAP-12**, currently recorded Blocked in the stability matrix.

## 9. The launcher's X kills the app — NOT STARTED (new, INS-02 FAILED)

`launcher.py:449` — `_close_launcher()` calls `QApplication.instance().quit()`.
The X on the floating widget is a full application exit, so the tray icon goes
with it and `Show Launcher` in the tray menu is unreachable. Nothing is
recoverable without relaunching the exe.

This is also why the widget "would not display" during the manual pass and why a
full-screen capture could not be taken at all — the app was gone, not hidden.

**Decision: X hides to tray.** `_close_launcher()` should `self.hide()`. The tray
icon stays up, `Show Launcher` and single-click activation bring it back, and
`Exit` in the tray menu becomes the only full quit. Update the tooltip from
"Close Test Assist" to "Hide to tray" so the control is honest about what it
does. Standard tray-app behaviour, and it is what INS-02 has always asserted.

Check while in there that `Show Launcher` restores a launcher hidden this way —
`launcher.show()` after `hide()` is fine, but if the widget was docked when
hidden it must come back in a reachable position, not off-screen.

---

## Outstanding manual checks

Nothing here can be automated — all need a built exe and two monitors.

### Re-test after the fixes land
| ID | Check |
|----|-------|
| DSP-12/13/14 | Drag the launcher between screens **in both directions**, dock, undock |
| DSP-17 | About → Copy details for a bug report (blocked until item 2) |
| DSP-08 | Selection spanning both screens — no band, content adjacent (blocked until item 8) |
| INS-02 | X on the launcher hides it; tray survives; Show Launcher restores it (blocked until item 9) |

### Not yet run
| ID | Check |
|----|-------|
| DSP-05 | Compare export pixel sizes, laptop vs external, same visual size |
| DSP-05b | Annotate on the 125% panel — shapes must land under the cursor |
| DSP-01/02 | Secondary dragged to the **right** in Settings |
| DSP-04 | Secondary **above** |
| DSP-16 | Unplug the external — no regression for single-screen users |
| DSP-15 | Launcher on the unplugged screen stays reachable |
| DSP-18 | Help header and footer version match the window title |
| PKG-03 | Pinned taskbar icon matches the tray icon |
| PKG-05 | File properties show the version |
| UPD-12 | Check for Updates reaches GitHub |
| — | No console window flashes when a recording saves |
| PKG-04 | First launch on a machine without Python — deferred, needs a clean machine |

### Passed already
DSP-07 (capture on the external — verified by template match, 1.0000),
DSP-11 (recording valid: h264, 1280×720, 15fps, clean decode),
DSP-10 (recorded on each screen; frame extraction confirms each recording shows
its own display),
plus the data-location move confirmed working on real hardware.

## Sequence

1. Claude Code: items 1–5 and 8–9, each its own commit, suite green between
2. Push
3. Build with `build.ps1`, confirm the four self-checks
4. Close Test Assist **from the tray → Exit**, install, relaunch
5. Work the manual list, recording actual rects in `SMOKE_TEST.md`
6. Only then: bump to 1.4.0, regenerate, tag
