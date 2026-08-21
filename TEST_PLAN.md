# 🔍 Test Assist — Test Plan

**Version:** 1.3  
**Last updated:** 2026-08-21  
**Status:** In active development

---

## 1. App Overview

Test Assist is a browser-based QA annotation tool. Users capture screenshots or
record video of their screen, then annotate the captured image with highlights,
text comments, circles, arrows, rectangles, and free-hand pen strokes. Annotated
images can be exported as PNG or as JSON (for replay / integration).

---

## 2. Current Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Screen capture (getDisplayMedia) | ✅ Done | Chrome / Edge / Safari 26+ via `ImageCapture`; Firefox via a video-frame fallback |
| Image upload (file picker) | ✅ Done | Any image format |
| Image drag-and-drop upload | ✅ Done | Drop image onto canvas area |
| Video recording (MediaRecorder) | ✅ Done | WebM / MP4 depending on browser |
| Recording timer | ✅ Done | mm:ss counter |
| Stop recording + auto-download | ✅ Done | .webm file saved |
| Select / move annotations | ✅ Done | Drag to reposition. Fixed 2026-08: moved shapes were stretched, pen strokes corrupted — see STABILITY_MATRIX.md |
| Highlight tool | ✅ Done | Semi-transparent fill |
| Text comment | ✅ Done | Multi-line; popup input |
| Circle (ellipse) tool | ✅ Done | Drag to size |
| Arrow tool | ✅ Done | Arrowhead rendered |
| Rectangle tool | ✅ Done | Outline only |
| Free pen tool | ✅ Done | Smooth path |
| Colour picker | ✅ Done | Full spectrum |
| Stroke size slider | ✅ Done | 1–20px |
| Highlight fill opacity slider | ✅ Done | 0–100% |
| Undo | ✅ Done | Covers annotation adds and select-tool moves |
| Session persistence | ✅ Done | IndexedDB; survives a refresh |
| Redo | ✅ Done | Restores redo stack |
| Clear all annotations | ✅ Done | Confirm dialog |
| Export PNG (base + annotations) | ✅ Done | Composited canvas download |
| Export JSON annotations | ✅ Done | Structured annotation data |
| Snapshot gallery | ✅ Done | Thumbnails; click to reload |
| Delete snapshot | ✅ Done | |
| Keyboard shortcuts | ✅ Done | Ctrl+Z, Ctrl+Y, Ctrl+S, h/t/c/a/r/p/s |
| Touch / mobile drawing | ✅ Done | Touch events mapped to mouse |
| Annotation labels (numbering) | ❌ Not started | |
| Cloud save / share | ❌ Not started | |
| PDF export | ❌ Not started | |
| Video annotation (frame-by-frame) | ❌ Not started | |

---

## 3. Test Cases

**Status key:** ✅ covered by an automated Playwright test that passes ·
🚫 blocked from automation.

66 of the 67 cases below are automated, across a smoke suite and a
regression suite. Coverage is not the whole story: several cases substitute a canvas-backed
`MediaStream` for `getDisplayMedia`, because the native screen-share picker is
browser chrome that no automation can drive. `STABILITY_MATRIX.md` records the
classification and the caveat for every case — read it before trusting a ✅.


### 3.1 Image Capture & Upload

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| IC-01 | Click "Capture Screen" | getDisplayMedia prompt shown; screen captured | ✅ |
| IC-02 | User cancels screen capture | No error; placeholder remains | ✅ |
| IC-03 | Upload image via file picker | Image displayed on canvas; annotation tools enabled | ✅ |
| IC-04 | Upload JPEG | Renders correctly on canvas | ✅ |
| IC-05 | Upload PNG with transparency | Transparency shown correctly | ✅ |
| IC-06 | Very large image (> 4000px) | Canvas scales correctly; no crash | ✅ |
| IC-07 | Drag-and-drop image onto canvas | Image loaded and displayed for annotation | ✅ |
| IC-08 | Drag non-image file | Silently ignored | ✅ |
| IC-09 | Browser without `ImageCapture` (Firefox) | Captures via the video-frame fallback | ✅ |
| IC-10 | Browser with no `getDisplayMedia` at all | Told to use Upload Image; no crash | ✅ |

### 3.2 Video Recording

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| VR-01 | Click Record | getDisplayMedia prompt; recording badge appears | ✅ |
| VR-02 | Timer increments | mm:ss updates every second | ✅ |
| VR-03 | Stop recording | Badge hides; .webm file downloads | ✅ |
| VR-04 | Cancel screen share mid-recording | Recording stops cleanly; file downloaded | 🚫 |
|  | *Blocked — needs the browser's own "Stop sharing" bar, which the page cannot reach. Manual check.* |  |  |
| VR-05 | User denies permission | No error shown to user | ✅ |
| VR-06 | Record button re-enabled after stop | Can start a new recording | ✅ |

### 3.3 Annotation Tools

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| AT-01 | Highlight drag | Semi-transparent rectangle with border | ✅ |
| AT-02 | Text — click canvas | Popup appears; text placed at click location | ✅ |
| AT-03 | Text — multi-line | Line breaks respected in canvas render | ✅ |
| AT-04 | Text — cancel | Popup closes; nothing added | ✅ |
| AT-05 | Circle drag | Ellipse rendered at correct position and size | ✅ |
| AT-06 | Arrow drag | Arrowhead at end point | ✅ |
| AT-07 | Rectangle drag | Outline rectangle rendered | ✅ |
| AT-08 | Pen draw | Smooth freehand stroke | ✅ |
| AT-09 | Select + drag annotation | Annotation moves to new position | ✅ |
| AT-10 | Colour change | New annotations use new colour | ✅ |
| AT-11 | Stroke size change | New annotations use new size | ✅ |
| AT-12 | Highlight opacity change | Fill transparency updates | ✅ |
| AT-13 | Tiny click (< 3px) | No annotation added | ✅ |
| AT-14 | Touch draw on mobile | Works same as mouse draw | ✅ |
| AT-15 | Select + drag a pen stroke | Whole path moves; no NaN in the export | ✅ |
| AT-16 | Draw with the browser zoomed | Coordinates match the underlying image | ✅ |

### 3.4 Undo / Redo

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| UR-01 | Undo after adding 1 annotation | Canvas returns to empty | ✅ |
| UR-02 | Undo after adding 3 annotations | Each undo removes one | ✅ |
| UR-03 | Undo with empty stack | Nothing happens | ✅ |
| UR-04 | Redo after undo | Annotation restored | ✅ |
| UR-05 | Redo stack cleared on new annotation | Can't redo after new draw | ✅ |
| UR-06 | Ctrl+Z shortcut | Same as Undo button | ✅ |
| UR-07 | Ctrl+Y shortcut | Same as Redo button | ✅ |
| UR-08 | Undo after moving an annotation | Move reversed; a bare click adds no undo step | ✅ |

### 3.5 Export

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| EX-01 | Save PNG | Downloads file with base image + annotations merged | ✅ |
| EX-02 | PNG includes all annotation types | Highlights, text, shapes all visible in PNG | ✅ |
| EX-03 | Save PNG adds to snapshot gallery | Thumbnail appears in sidebar | ✅ |
| EX-04 | Export JSON | Downloads .json with annotation array | ✅ |
| EX-05 | JSON contains all shape properties | type, coords, color, size all present | ✅ |
| EX-06 | Ctrl+S shortcut | Same as Save PNG | ✅ |

### 3.6 Snapshot Gallery

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| SG-01 | Click thumbnail | That snapshot loaded onto canvas | ✅ |
| SG-02 | Delete snapshot | Removed from gallery | ✅ |
| SG-03 | Multiple snapshots | Newest shown first | ✅ |
| SG-04 | Two exports in the same millisecond | Both kept; deleting one leaves the other | ✅ |

### 3.7 Keyboard Shortcuts

| ID | Key | Expected Tool / Action | Status |
|----|-----|------------------------|--------|
| KS-01 | `h` | Highlight tool selected | ✅ |
| KS-02 | `t` | Text tool selected | ✅ |
| KS-03 | `c` | Circle tool selected | ✅ |
| KS-04 | `a` | Arrow tool selected | ✅ |
| KS-05 | `r` | Rectangle tool selected | ✅ |
| KS-06 | `p` | Pen tool selected | ✅ |
| KS-07 | `s` | Select tool selected | ✅ |
| KS-08 | Ctrl+Z | Undo | ✅ |
| KS-09 | Ctrl+Y | Redo | ✅ |
| KS-10 | Ctrl+S | Save PNG | ✅ |
| KS-11 | Typing in the text popup | Tool shortcuts stay inert | ✅ |

### 3.8 Session Persistence

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| SP-01 | Reload after annotating | Image and annotations are restored | ✅ |
| SP-02 | Undo on a restored session | Undo history came back with it | ✅ |
| SP-03 | Reload with snapshots taken | Snapshot gallery is restored | ✅ |
| SP-04 | Clear the saved session | Canvas empties and the session does not return on reload | ✅ |
| SP-05 | Session saved under an old schema | Discarded rather than half-read; no error | ✅ |
| SP-06 | Storage unavailable (private window) | App works normally; nothing is remembered | ✅ |

---

## 4. Known Limitations & Gaps

1. **Session storage is per-browser** — a restored session belongs to the
   browser it was made in; it does not follow you to another machine.
2. **No annotation labels** — Numbered callouts (① ② ③) are not yet supported.
3. **No PDF export** — Only PNG export currently available.
4. **Video annotation** — Recorded videos cannot be annotated frame-by-frame.
5. **Screen capture API** — Not available in Safari on iOS; mobile users must
   upload an image manually.

*Removed in v1.2, having been checked rather than assumed:* browser zoom
misalignment (AT-16 shows `getPos()` already compensates via the bounding-rect
ratio), Firefox capture (now works through the video-frame fallback, IC-09),
and un-undoable moves (fixed, UR-08).

---

## 5. Roadmap / Next Steps

### Sprint 1 (Bug fixes & completeness)
- [ ] Persist snapshots in localStorage (as data URLs)
- [ ] Add numbered callout / label annotation type

### Sprint 2 (Richer annotations)
- [ ] Blur / pixelate tool (for redacting sensitive info in screenshots)
- [ ] Measurement ruler tool
- [ ] Stamp / emoji overlay
- [ ] Annotation list panel (click to select / edit / delete by name)

### Sprint 3 (Collaboration)
- [ ] Share annotated image via unique URL (Supabase Storage or Cloudinary)
- [ ] Comments linked to annotations (discussion thread per annotation)
- [ ] Export as annotated PDF

### Sprint 4 (Video)
- [ ] Frame-by-frame video scrubbing
- [ ] Overlay annotations on video frames
- [ ] Export annotated video as GIF or MP4

---

## 6. GitHub Project Board Structure

| Column | Description |
|--------|-------------|
| 🧊 Backlog | Ideas and future features |
| 🐛 Bug | Confirmed bugs to fix |
| 🚧 In Progress | Actively being worked on |
| 👀 In Review | PR open, awaiting review |
| ✅ Done | Merged and released |

### Suggested Labels

| Label | Colour | Use |
|-------|--------|-----|
| `bug` | red | Something isn't working |
| `enhancement` | blue | New feature or request |
| `annotation` | yellow | Drawing / annotation tools |
| `export` | green | PNG / JSON / PDF export |
| `video` | purple | Video recording / annotation |
| `mobile` | teal | Mobile / touch support |
| `good first issue` | light-green | Easy entry point |
| `accessibility` | orange | A11y improvements |
