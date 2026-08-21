# 🔍 Test Assist — Desktop Test Plan

**Version:** 1.1
**Last updated:** 2026-08-21
**Status:** In active development
**Applies to:** the PySide6 desktop build under `python/`. The browser build has
its own plan in `TEST_PLAN.md`.

---

## 1. App Overview

Test Assist Desktop is a QA evidence tool that lives in the system tray. A
floating launcher stays above the application under test; capturing a region
opens the captured image in an editor with nine annotation tools, zoom,
layering, and export to PNG, JSON or the clipboard. Captures are kept in a
history that survives restarts.

---

## 2. Current Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Region screenshot overlay | ✅ Done | Drag to select; Esc cancels |
| Screen recording | ✅ Done | Frames written as captured; 3-minute cap |
| MP4 assembly | ✅ Done | Only when `opencv-python` is installed |
| Select tool | ✅ Done | Click to select, drag to move |
| Crop | ✅ Done | Undoable; restores original canvas size |
| Blur / redact | ✅ Done | For masking sensitive content before sharing |
| Text, Highlight, Circle, Arrow, Rectangle, Pen | ✅ Done | |
| Arrow styles | ✅ Done | Classic, double-headed, dashed |
| Colour / stroke size / highlight opacity | ✅ Done | |
| Layering | ✅ Done | Bring to front, send backward, send to back |
| Zoom in / out / fit | ✅ Done | Slider plus buttons |
| Undo / redo | ✅ Done | Covers annotations, crop and moves |
| Delete selected | ✅ Done | Delete key |
| Export PNG | ✅ Done | Also written to history |
| Export JSON | ✅ Done | Annotation list plus timestamp |
| Copy to clipboard | ✅ Done | Also written to history |
| Capture history | ✅ Done | Persists in `~/.test-assist/history` |
| History filters | ✅ Done | Recent 5 / Today / This Week / This Month |
| Floating launcher | ✅ Done | Always on top; drag to reposition |
| Edge docking | ✅ Done | Compact vertical strip |
| System tray icon and menu | ✅ Done | Show launcher, open editor, exit |
| Single-instance enforcement | ✅ Done | Second launch focuses the running app |
| Packaged Windows executable | ✅ Done | Built by the tagged-release workflow |
| Annotation numbering | ❌ Not done | Numbered callouts not supported |
| PDF export | ❌ Not done | PNG and JSON only |
| Frame-by-frame video annotation | ❌ Not done | |

---

## 3. Test Cases

**Status key:** ✅ covered by an automated test that passes · 🚫 blocked from
automation, manual only.

Every case that can be automated is. The four blocked ones need a built
executable on real Windows and are listed as manual rather than quietly
dropped.

`DESKTOP_STABILITY_MATRIX.md` records which cases are automated, which are not,
and why — read it before treating a ✅ as proof of more than it is.

### 3.1 Capture

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| CAP-01 | Drag a region on the capture overlay | Selected region is grabbed and opens in the editor | ✅ |
| CAP-02 | Press Esc during region select | Overlay closes; no capture; editor unchanged | ✅ |
| CAP-03 | Click without dragging | No zero-size capture is produced | ✅ |
| CAP-04 | Capture while the editor already holds an image | Previous image is replaced, annotations cleared | ✅ |

### 3.2 Screen Recording

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| REC-01 | Record for a few seconds and stop | Frames are written to `~/.test-assist/recordings` as captured | ✅ |
| REC-02 | Memory during a recording | Memory stays flat; frames are not held in a list | ✅ |
| REC-03 | Recording reaches the duration cap | Recording stops itself at 3 minutes | ✅ |
| REC-04 | Frame width | Frames are scaled to at most 1280px wide | ✅ |
| REC-05 | Stop with `opencv-python` installed | A single `.mp4` is produced and the frames are removed | ✅ |
| REC-06 | Stop without `opencv-python` | The frame folder is kept and returned as the recording | ✅ |
| REC-07 | Stop having captured nothing | Empty result, no crash, no stray folder | ✅ |
| REC-08 | Frame files missing when saving | Finishes cleanly rather than raising | ✅ |

### 3.3 Annotation Tools

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| TOL-01 | Highlight drag | Semi-transparent filled rectangle added | ✅ |
| TOL-02 | Rectangle drag | Outlined rectangle added | ✅ |
| TOL-03 | Circle drag | Ellipse added at the dragged bounds | ✅ |
| TOL-04 | Arrow drag | Arrow added with an arrowhead at the end point | ✅ |
| TOL-05 | Pen draw | Freehand path recorded with multiple points | ✅ |
| TOL-06 | Text placement | Text annotation added at the click point | ✅ |
| TOL-07 | Tiny drag below the threshold | No annotation is added | ✅ |
| TOL-08 | Drawing with no image loaded | Ignored; no annotation, no crash | ✅ |
| TOL-09 | Each tool is selectable from the toolbar | Active tool changes and the button shows as active | ✅ |

### 3.4 Crop

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| CRP-01 | Crop to a dragged region | Canvas resizes to the region | ✅ |
| CRP-02 | Undo a crop | Original canvas size and content restored | ✅ |
| CRP-03 | Crop smaller than the minimum | Ignored; canvas unchanged | ✅ |
| CRP-04 | Crop with annotations present | Annotations remain positioned correctly relative to the image | ✅ |

### 3.5 Blur / Redact

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| BLR-01 | Blur a dragged region | Region is obscured in the exported image | ✅ |
| BLR-02 | Blur is destructive to the export | The original pixels are not recoverable from the exported PNG | ✅ |
| BLR-03 | Undo a blur | Previous state restored | ✅ |

### 3.6 Selection & Layering

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| SEL-01 | Double-click an annotation | That annotation becomes selected | ✅ |
| SEL-01b | Single-click an annotation with the Select tool | Nothing is selected — see the UX note in section 4 | ✅ |
| SEL-02 | Drag a selected annotation | It moves without deforming | ✅ |
| SEL-03 | Delete key with a selection | Selected annotation is removed | ✅ |
| SEL-04 | Delete key with nothing selected | Nothing happens; no crash | ✅ |
| SEL-05 | Bring to front | Selected annotation becomes the topmost hit target | ✅ |
| SEL-06 | Send to back | Selected annotation is no longer the topmost hit target | ✅ |
| SEL-07 | Send backward | Annotation moves one step down the stack | ✅ |

### 3.7 Style Controls

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| STY-01 | Change colour, then draw | New annotation uses the new colour | ✅ |
| STY-02 | Change colour with an annotation selected | The selected annotation's colour updates | ✅ |
| STY-03 | Change stroke size, then draw | New annotation uses the new size | ✅ |
| STY-04 | Change highlight opacity | New highlight uses the new fill opacity | ✅ |
| STY-05 | Arrow style: classic / double / dashed | The style is recorded on the annotation | ✅ |

### 3.8 Zoom

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| ZOM-01 | Zoom in | Zoom factor increases; widget grows | ✅ |
| ZOM-02 | Zoom out | Zoom factor decreases | ✅ |
| ZOM-03 | Fit to window | Zoom is set so the image fits the viewport | ✅ |
| ZOM-04 | Fit a very large image | Zoom is reduced below 100% | ✅ |
| ZOM-05 | Draw while zoomed | Annotation coordinates match the image, not the screen | ✅ |
| ZOM-06 | Zoom bounds | Zoom cannot be driven to zero or beyond the maximum | ✅ |

### 3.9 Undo / Redo

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| UND-01 | Undo after adding an annotation | Annotation removed | ✅ |
| UND-02 | Redo after undo | Annotation restored | ✅ |
| UND-03 | Undo with an empty stack | Nothing happens; no crash | ✅ |
| UND-04 | New annotation after an undo | Redo stack is cleared | ✅ |
| UND-05 | Clear all annotations | Canvas empties | ✅ |
| UND-06 | Undo a clear-all | Annotations restored | ✅ |

### 3.10 Export

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| OUT-01 | Save PNG | File written, containing base image and annotations | ✅ |
| OUT-02 | Save PNG adds to history | A snapshot appears in the history folder | ✅ |
| OUT-03 | Export JSON | File contains `annotations` and `timestamp` | ✅ |
| OUT-04 | JSON contains every annotation field | Type, coordinates, colour and size all present | ✅ |
| OUT-05 | JSON for a pen stroke | Path serialised as a list of x/y objects | ✅ |
| OUT-06 | Copy to clipboard | Clipboard holds the composited image | ✅ |
| OUT-07 | Copy to clipboard adds to history | A snapshot appears in the history folder | ✅ |
| OUT-08 | Export with no image loaded | No file written; no crash | ✅ |
| OUT-09 | Cancel the save dialog | No file written; no crash | ✅ |

### 3.11 Capture History

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| HIS-01 | History persists across restarts | Snapshots written previously are listed on next launch | ✅ |
| HIS-02 | Blank captures are not persisted | Images below the size threshold are skipped | ✅ |
| HIS-03 | Unreadable files are pruned on load | Files that are not loadable images are removed at startup | ✅ |
| HIS-03b | A small but valid capture on load | Kept — a flat capture under 5 KB is still real evidence | ✅ |
| HIS-04 | Filter: Recent 5 | At most five most recent snapshots listed | ✅ |
| HIS-05 | Filter: Today / This Week / This Month | Only snapshots within the window are listed | ✅ |
| HIS-06 | Click a history thumbnail | That snapshot loads onto the canvas | ✅ |
| HIS-07 | History overlay opens | Gallery shows all categories | ✅ |

### 3.12 Floating Launcher

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| LCH-01 | Launcher buttons are present | Capture, record, editor and help controls exist with tooltips | ✅ |
| LCH-02 | Drag the launcher | It moves to the dragged position | ✅ |
| LCH-03 | Drag to the right edge | It docks as a compact vertical strip | ✅ |
| LCH-04 | Undock | It returns to the expanded layout | ✅ |
| LCH-05 | Keyboard shortcuts on the launcher | Documented keys trigger their actions | ✅ |
| LCH-06 | Open the editor with no capture taken | Editor opens without an image and does not crash | ✅ |
| LCH-07 | Launcher stays above other windows | Always-on-top flag is set | ✅ |

### 3.13 Keyboard Shortcuts

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| KEY-01 | `h` `t` `c` `a` `r` `p` `s` `x` `b` | Each selects its tool | ✅ |
| KEY-02 | Ctrl+Z / Ctrl+Y | Undo / redo | ✅ |
| KEY-03 | Ctrl+S | Save PNG | ✅ |
| KEY-04 | Delete | Delete the selected annotation | ✅ |
| KEY-05 | Shortcuts while typing a text annotation | Tool shortcuts are suppressed | ✅ |

### 3.14 Application Lifecycle

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| INS-01 | Launch a second instance | The running instance is focused; the second exits | ✅ |
| INS-02 | Close the last window | The app stays alive in the tray | 🚫 |
| INS-03 | `--version` | Prints the version and exits without a UI | ✅ |
| INS-04 | Help | `help.html` resolves from both a source checkout and a build | ✅ |

### 3.15 Packaging (built executable only)

These need a built artefact rather than a source checkout.

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| PKG-01 | The icon ships | `assets/icon.ico` is present and a valid ICO | ✅ |
| PKG-02 | Built exe reports its version | `--version` writes the expected string | ✅ |
| PKG-03 | Taskbar icon | Pinned icon matches the tray icon | 🚫 |
| PKG-04 | First launch on a machine without Python | App starts from the unzipped folder | 🚫 |
| PKG-05 | Windows file properties | Product name and version are populated | 🚫 |

---

## 4. Known Limitations & Gaps

1. **MP4 needs opencv** — the packaged build excludes `opencv-python`, which
   would add roughly 250 MB. Recordings are saved as a JPEG frame sequence
   unless the app is run from source with opencv installed.
2. **Recording is capped at three minutes** — deliberate, so an unattended
   recording cannot fill the disk.
3. **Recording frames are scaled to 1280px wide** — full-resolution frames
   cannot be encoded inside the frame budget.
4. **Selection needs a double-click** — with the Select tool active, a single
   click does not select anything; selection is bound to double-click for every
   tool. SEL-01b documents the current behaviour rather than asserting the
   intended one. Worth a decision: a tool called Select that does not select on
   click is surprising.
5. **No annotation numbering, PDF export, or frame-by-frame video annotation.**

---

## 5. Roadmap / Next Steps

### Sprint 1 (Confidence)
- [ ] Automate the cases in this plan and record what cannot be automated
- [ ] Run a manual pass of the 🚫 cases against a built executable

### Sprint 2 (Evidence workflow)
- [ ] Annotation numbering (① ② ③) for step-by-step defect reports
- [ ] Ticket-shaped default filenames instead of timestamps

### Sprint 3 (Output)
- [ ] PDF export combining several captures into one document
- [ ] Frame-by-frame annotation of recordings

---

## 6. GitHub Project Board Structure

| Column | Description |
|--------|-------------|
| 🧊 Backlog | Ideas and future features |
| 🔍 Needs Investigation | Bugs and edge cases to research |
| 🚧 In Progress | Actively being worked on |
| 👀 In Review | PR open, awaiting review |
| ✅ Done | Merged and released |

### Suggested Labels

| Label | Colour | Use |
|-------|--------|-----|
| `bug` | red | Something isn't working |
| `enhancement` | blue | New feature or request |
| `desktop` | purple | PySide6 build only |
| `annotation` | orange | Drawing, tools and the canvas |
| `packaging` | grey | Build, release and distribution |
| `good first issue` | light-green | Easy entry point |
