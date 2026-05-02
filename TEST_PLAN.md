# 🔍 Test Assist — Test Plan

**Version:** 1.0  
**Last updated:** 2026-05-02  
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
| Screen capture (getDisplayMedia) | ✅ Done | Chrome / Edge / Firefox |
| Image upload (file picker) | ✅ Done | Any image format |
| Image drag-and-drop upload | ✅ Done | Drop image onto canvas area |
| Video recording (MediaRecorder) | ✅ Done | WebM / MP4 depending on browser |
| Recording timer | ✅ Done | mm:ss counter |
| Stop recording + auto-download | ✅ Done | .webm file saved |
| Select / move annotations | ✅ Done | Drag to reposition |
| Highlight tool | ✅ Done | Semi-transparent fill |
| Text comment | ✅ Done | Multi-line; popup input |
| Circle (ellipse) tool | ✅ Done | Drag to size |
| Arrow tool | ✅ Done | Arrowhead rendered |
| Rectangle tool | ✅ Done | Outline only |
| Free pen tool | ✅ Done | Smooth path |
| Colour picker | ✅ Done | Full spectrum |
| Stroke size slider | ✅ Done | 1–20px |
| Highlight fill opacity slider | ✅ Done | 0–100% |
| Undo | ✅ Done | Fixed: saves state before add |
| Redo | ✅ Done | Restores redo stack |
| Clear all annotations | ✅ Done | Confirm dialog |
| Export PNG (base + annotations) | ✅ Done | Composited canvas download |
| Export JSON annotations | ✅ Done | Structured annotation data |
| Snapshot gallery | ✅ Done | Thumbnails; click to reload |
| Delete snapshot | ✅ Done | |
| Keyboard shortcuts | ✅ Done | Ctrl+Z, Ctrl+Y, Ctrl+S, h/t/c/a/r/p/s |
| Touch / mobile drawing | ✅ Done | Touch events mapped to mouse |
| Drag-and-drop image upload | ❌ Not wired | Drop zone UI exists but handler missing |
| Annotation labels (numbering) | ❌ Not started | |
| Cloud save / share | ❌ Not started | |
| PDF export | ❌ Not started | |
| Video annotation (frame-by-frame) | ❌ Not started | |

---

## 3. Test Cases

### 3.1 Image Capture & Upload

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| IC-01 | Click "Capture Screen" | getDisplayMedia prompt shown; screen captured | ⬜ |
| IC-02 | User cancels screen capture | No error; placeholder remains | ⬜ |
| IC-03 | Upload image via file picker | Image displayed on canvas; annotation tools enabled | ⬜ |
| IC-04 | Upload JPEG | Renders correctly on canvas | ⬜ |
| IC-05 | Upload PNG with transparency | Transparency shown correctly | ⬜ |
| IC-06 | Very large image (> 4000px) | Canvas scales correctly; no crash | ⬜ |
| IC-07 | Drag-and-drop image onto canvas | Image loaded and displayed for annotation | ⬜ |
| IC-08 | Drag non-image file | Silently ignored | ⬜ |

### 3.2 Video Recording

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| VR-01 | Click Record | getDisplayMedia prompt; recording badge appears | ⬜ |
| VR-02 | Timer increments | mm:ss updates every second | ⬜ |
| VR-03 | Stop recording | Badge hides; .webm file downloads | ⬜ |
| VR-04 | Cancel screen share mid-recording | Recording stops cleanly; file downloaded | ⬜ |
| VR-05 | User denies permission | No error shown to user | ⬜ |
| VR-06 | Record button re-enabled after stop | Can start a new recording | ⬜ |

### 3.3 Annotation Tools

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| AT-01 | Highlight drag | Semi-transparent rectangle with border | ⬜ |
| AT-02 | Text — click canvas | Popup appears; text placed at click location | ⬜ |
| AT-03 | Text — multi-line | Line breaks respected in canvas render | ⬜ |
| AT-04 | Text — cancel | Popup closes; nothing added | ⬜ |
| AT-05 | Circle drag | Ellipse rendered at correct position and size | ⬜ |
| AT-06 | Arrow drag | Arrowhead at end point | ⬜ |
| AT-07 | Rectangle drag | Outline rectangle rendered | ⬜ |
| AT-08 | Pen draw | Smooth freehand stroke | ⬜ |
| AT-09 | Select + drag annotation | Annotation moves to new position | ⬜ |
| AT-10 | Colour change | New annotations use new colour | ⬜ |
| AT-11 | Stroke size change | New annotations use new size | ⬜ |
| AT-12 | Highlight opacity change | Fill transparency updates | ⬜ |
| AT-13 | Tiny click (< 3px) | No annotation added | ⬜ |
| AT-14 | Touch draw on mobile | Works same as mouse draw | ⬜ |

### 3.4 Undo / Redo

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| UR-01 | Undo after adding 1 annotation | Canvas returns to empty | ⬜ |
| UR-02 | Undo after adding 3 annotations | Each undo removes one | ⬜ |
| UR-03 | Undo with empty stack | Nothing happens | ⬜ |
| UR-04 | Redo after undo | Annotation restored | ⬜ |
| UR-05 | Redo stack cleared on new annotation | Can't redo after new draw | ⬜ |
| UR-06 | Ctrl+Z shortcut | Same as Undo button | ⬜ |
| UR-07 | Ctrl+Y shortcut | Same as Redo button | ⬜ |

### 3.5 Export

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| EX-01 | Save PNG | Downloads file with base image + annotations merged | ⬜ |
| EX-02 | PNG includes all annotation types | Highlights, text, shapes all visible in PNG | ⬜ |
| EX-03 | Save PNG adds to snapshot gallery | Thumbnail appears in sidebar | ⬜ |
| EX-04 | Export JSON | Downloads .json with annotation array | ⬜ |
| EX-05 | JSON contains all shape properties | type, coords, color, size all present | ⬜ |
| EX-06 | Ctrl+S shortcut | Same as Save PNG | ⬜ |

### 3.6 Snapshot Gallery

| ID | Test | Expected Result | Status |
|----|------|-----------------|--------|
| SG-01 | Click thumbnail | That snapshot loaded onto canvas | ⬜ |
| SG-02 | Delete snapshot | Removed from gallery | ⬜ |
| SG-03 | Multiple snapshots | Newest shown first | ⬜ |

### 3.7 Keyboard Shortcuts

| ID | Key | Expected Tool / Action | Status |
|----|-----|------------------------|--------|
| KS-01 | `h` | Highlight tool selected | ⬜ |
| KS-02 | `t` | Text tool selected | ⬜ |
| KS-03 | `c` | Circle tool selected | ⬜ |
| KS-04 | `a` | Arrow tool selected | ⬜ |
| KS-05 | `r` | Rectangle tool selected | ⬜ |
| KS-06 | `p` | Pen tool selected | ⬜ |
| KS-07 | `s` | Select tool selected | ⬜ |
| KS-08 | Ctrl+Z | Undo | ⬜ |
| KS-09 | Ctrl+Y | Redo | ⬜ |
| KS-10 | Ctrl+S | Save PNG | ⬜ |

---

## 4. Known Limitations & Gaps

1. **Drag-and-drop upload not wired** — The drop zone UI exists but the
   `dragover` / `drop` event handlers on the main canvas area are not connected.
2. **Annotations not persisted** — Refreshing the page loses all annotations
   (snapshots gallery is in-memory only).
3. **No annotation labels** — Numbered callouts (① ② ③) are not yet supported.
4. **No PDF export** — Only PNG export currently available.
5. **Video annotation** — Recorded videos cannot be annotated frame-by-frame.
6. **Screen capture API** — Not available in Safari on iOS; mobile users must
   upload an image manually.
7. **Canvas scales on zoom** — If the browser is zoomed in/out, the annotation
   coordinates may be slightly misaligned with the underlying image.

---

## 5. Roadmap / Next Steps

### Sprint 1 (Bug fixes & completeness)
- [ ] Fix canvas coordinate scaling when browser is zoomed
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
