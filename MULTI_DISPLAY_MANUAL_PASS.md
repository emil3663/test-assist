# Manual Pass — multi-display fix and packaging

**Version:** 2.0 (ordered by configuration)
**Last updated:** 2026-09-04
**Status:** Not yet run
**Hardware:** external E241Y 1920×1080 @100% (main) · laptop panel 1536×864 logical @125%, positioned LEFT

Run against a **built executable**, not `python main.py`. Half of what this pass
exists to catch — the console flash, ffmpeg resolving inside the bundle — only
happens once frozen.

Cases are ordered so you change Windows display settings as few times as
possible. Work top to bottom.

---

## Setup (once)

- [ ] **S-1** Close Test Assist completely — check the tray, not just the window.
      The single-instance guard will silently hand a new launch to an old
      running copy, and you would be testing 1.3.0 while believing otherwise.
- [ ] **S-2** Keep the old build: `Rename-Item "C:\TestAssist" "C:\TestAssist-1.3.0"`
- [ ] **S-3** Build: `cd ...\python; ..\.venv\Scripts\Activate.ps1; .\build.ps1`
- [ ] **S-4** Copy `python\dist\TestAssist\*` into a fresh `C:\TestAssist\`
- [ ] **S-5** Open a maximised window on each screen with unmistakable text —
      `LAPTOP LAPTOP LAPTOP` on the laptop panel, `EXTERNAL EXTERNAL EXTERNAL`
      on the external, large font. Every capture then answers its own question.
- [ ] **S-6** First launch: confirm `~/.test-assist` contents migrated into
      `Documents\Test Assist\` and `%LOCALAPPDATA%\Test Assist\`.

> The new build still reports **1.3.0** — the version bump happens at release.
> Tell the builds apart by folder, never by the title bar.

---

## Block A — your current layout (no settings changes)

Laptop LEFT @125% · external main @100%. This is the hardest configuration and
you already have it: negative coordinates *and* mixed DPI at once.

| ID | Test | Expected | Status |
|----|------|----------|--------|
| DSP-03 | Capture a region on the **laptop** | Image says LAPTOP | ⬜ |
| DSP-07 | Capture a region on the **external** | Image says EXTERNAL, not blank | ⬜ |
| DSP-05 | Compare both exports | Laptop export is ~1.25× the pixel size of the same-sized external selection, or consistently scaled — and consistent between them | ⬜ |
| DSP-05b | Annotate on the laptop panel | Shapes land under the cursor; no drift on the 125% screen | ⬜ |
| DSP-08 | Drag a selection **spanning both** screens | One image, LAPTOP and EXTERNAL joined, no gap, no doubling, no vertical offset | ⬜ |
| DSP-09 | Full-screen capture, launcher on the **laptop** | Captures the laptop | ⬜ |
| DSP-10 | Record a few seconds, launcher on the laptop, then **play it back** | Video shows the laptop. Only visible on playback | ⬜ |
| DSP-11 | Same recording | Right dimensions, not distorted | ⬜ |
| DSP-12 | Drag the launcher to the laptop, dock right | Docks to the **laptop's** right edge | ⬜ |
| DSP-13 | Undock on the laptop | Returns to the laptop's top-right | ⬜ |
| DSP-14 | Drag flush to the laptop's right edge | Auto-docks against that screen | ⬜ |
| DSP-17 | About → Copy details for a bug report | Clipboard has version, OS, both screens with geometry and DPR | ⬜ |
| DSP-18 | Help page header and footer | Version shown, matches the window title | ⬜ |
| INS-02 | Close the last window | App stays alive in the tray | ✅ 2026-09-08 — X hides the launcher, tray survives, Show Launcher restores it. Run against build md5 `85e1556d`; an earlier run against `12fade5b` (the 2 Sep binary, unzipped by mistake) failed and does not count. |
| PKG-03 | Pin to taskbar | Pinned icon matches the tray icon | ⬜ |
| PKG-05 | Right-click exe → Properties → Details | Product name and version populated | ⬜ |
| UPD-12 | Check for Updates | Reaches GitHub and reports correctly | ⬜ |
| REC-console | Watch closely as a recording saves | **No console window flashes** | ⬜ |
| LCH-13 | Focus a browser (or any other window), then press Alt+P / Alt+Shift+P / Alt+V | Each captures or toggles recording exactly as its launcher button would, with Test Assist not the focused window | ⬜ |

**Before/after evidence:** repeat DSP-03 once from `C:\TestAssist-1.3.0`. It
should return EXTERNAL — the bug. Keep both images for the issue thread.

---

## Block B — matched DPI

Settings → Display → select the laptop → Scale **100%**. Positions unchanged.
**Restart the app.**

| ID | Test | Expected | Status |
|----|------|----------|--------|
| DSP-03b | Capture on the laptop | Says LAPTOP | ⬜ |
| DSP-06 | Compare exports again | Both 1:1 now | ⬜ |
| DSP-08b | Spanning selection | Joined cleanly | ⬜ |

*If Block A failed and Block B passes, the fault is DPI handling, not screen
selection. That distinction is the most useful thing this pass can produce.*

---

## Block C — secondary on the right

Drag the laptop thumbnail to the **right** of the external. Laptop back to
**125%**. **Restart the app.**

| ID | Test | Expected | Status |
|----|------|----------|--------|
| DSP-01 | Capture on the laptop | Says LAPTOP | ⬜ |
| DSP-02 | Capture on the external | Says EXTERNAL | ⬜ |

*This is closest to the reporter's layout — positive offsets rather than
negative.*

---

## Block D — secondary above

Drag the laptop thumbnail **above** the external. **Restart the app.**

| ID | Test | Expected | Status |
|----|------|----------|--------|
| DSP-04 | Capture on the laptop | Says LAPTOP — negative-Y path | ⬜ |

---

## Block E — single monitor

Unplug the external. **Restart the app.**

| ID | Test | Expected | Status |
|----|------|----------|--------|
| DSP-15 | Launcher was on the unplugged screen | App still reachable, not off-screen | ⬜ |
| DSP-16 | Capture, full capture, record, dock, undock | All behave as before the fix — no regression for single-screen users | ⬜ |

---

## Block F — deferred

| ID | Test | Expected | Status |
|----|------|----------|--------|
| PKG-04 | First launch on a machine without Python | Starts from the unzipped folder | ⬜ |

*Needs a clean Windows machine. Defer with the reason rather than guessing.*

---

## Known Limitations & Gaps

1. **Live display changes are untested** — this pass restarts the app between
   configurations. Hot-plugging while running is not covered.
2. **Three or more monitors are not covered.**
3. **Only Windows.**
4. **The overlay cannot cover taskbars** — it uses `availableVirtualGeometry`,
   so a taskbar or notification cannot be selected. Pre-existing, not part of
   this fix.

## Next Steps

- [ ] Record the outcome in `SMOKE_TEST.md` with the date and configurations used
- [ ] File any failure as its own ticket rather than fixing it silently
- [ ] Reply on issue #1 with the result
- [ ] Only then TA-207: bump to 1.4.0, regenerate, tag
