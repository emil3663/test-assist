# Test Assist

**A QA engineer's defect-evidence tool.** Capture the screen, annotate what is
wrong clearly enough that a developer needs no further explanation, and export
both a composited image and the annotation data as structured JSON.

It exists because attaching a raw screenshot to a defect is not evidence — it is
a starting point for an argument. A good defect report makes the finding
reproducible from the record alone, and the tooling for that is usually either
heavyweight, cloud-bound, or not built for testers.

Built twice, desktop-first in intent. The PySide6 application is the one designed
to be lived in — a native overlay with a tray launcher that stays above whatever
you are testing. The browser build was written from the same specification so the
tool can be used without an install, which is also what makes it demonstrable
from a link.

Both are real. The browser build runs the whole capture → annotate → export loop
on its own; it is not a preview of the desktop one. What the desktop build adds
is the set of things a browser is not permitted to do.

**Try it in your browser, nothing to install:** https://emil3663.github.io/test-assist/

---

## The two builds

| | Browser | Desktop |
|---|---|---|
| **Stack** | Vanilla JavaScript, Canvas API | Python, PySide6 (Qt) |
| **Install** | None — open `index.html` | `pip install -r python/requirements.txt` |
| **Capture** | `getDisplayMedia`, `MediaRecorder` | Native screenshot overlay, frame recorder |
| **Best for** | Trying the full capture → annotate → export loop in ten seconds, with nothing to install | Long test sessions — a tray launcher that stays above the application under test |
| **Tests** | Manual only — ID-coded cases in `TEST_PLAN.md`, no automated coverage | 29 pytest regression tests, 74 assertions, in CI |

Both produce the same two outputs: a composited PNG for attaching to a defect,
and a structured JSON annotation layer.

### Only in the desktop build

The browser is sandboxed, so these exist only in the PySide6 version:

- A tray launcher that stays above the application under test, and docks to a
  screen edge as a compact vertical strip
- Zoom, and a capture history that persists across restarts
- Single-instance enforcement — a second launch focuses the running window
- MP4 recording where `opencv-python` is installed; the browser writes `.webm`

Everything under **What it does** below is the browser build.

---

## What it does

**Capture**

- Screen capture via `getDisplayMedia` (Chrome, Edge, Safari 26+ — Firefox has
  no `ImageCapture`, so still capture is unavailable there; use Upload Image)
- Screen recording via `MediaRecorder` with an mm:ss timer; stop writes a `.webm`
- Image upload by file picker or drag-and-drop onto the canvas

**Annotate**

- Highlight (semi-transparent fill), text comment (multi-line), circle, arrow,
  rectangle, freehand pen
- Colour picker, stroke width 1–20px, highlight fill opacity 0–100%
- Select and drag any annotation to reposition it
- Undo and redo, and clear-all behind a confirmation
- Keyboard shortcuts: `Ctrl+Z`, `Ctrl+Y`, `Ctrl+S`, and `h` `t` `c` `a` `r` `p` `s`
  for the tools
- Touch support, so it works on a tablet

**Export**

- **PNG** — base image and annotation layer composited into one file
- **JSON** — the annotation layer as data, for replay or downstream integration
- Snapshot gallery: every export is kept as a thumbnail you can click to reload

---

## The JSON export

This is the part that distinguishes it from a screenshot tool. Annotations are
exported as data, not baked into pixels, so they can be replayed, diffed,
re-rendered at a different resolution, or consumed by another system.

```json
{
  "annotations": [
    {
      "type": "rect",
      "x": 412, "y": 208, "x2": 690, "y2": 344,
      "color": "#ff3b30",
      "size": 3,
      "fillOpacity": 0
    },
    {
      "type": "text",
      "x": 700, "y": 214,
      "color": "#ff3b30",
      "size": 16,
      "text": "Total ignores the discount applied above"
    }
  ],
  "timestamp": "2026-05-04T09:21:44.301Z"
}
```

`type` is one of `highlight`, `text`, `circle`, `arrow`, `rect` or `pen`. Shape
annotations carry a start and end point; `pen` carries its path; `text` carries
its string. `timestamp` is ISO-8601 at the moment of export.

Because the geometry is preserved, a defect's evidence can be re-rendered against
a later build of the same screen — which is the direction the tool is heading.

---

## Running it

**Browser** — nothing to install; open the live version above, or:

```
Open index.html in Chrome, Edge or Firefox.
```

Screen capture and recording require a secure context, so if you are serving it
rather than opening the file directly, use `localhost` or HTTPS. Declining the
screen-capture permission is handled — you can still upload an image and annotate.

**Desktop**:

```bash
cd python
pip install -r requirements.txt
python main.py          # or: ./run.ps1 on Windows
```

`opencv-python` and `numpy` are optional. With them, recordings export as MP4;
without, they are saved as a PNG frame sequence.

---

## Testing

The desktop build carries the automated coverage:

- **29 pytest regression tests, 74 assertions**, in `python/tests/test_regressions.py`
- Run with `pytest` from the `python/` directory
- Executed on every push by `.github/workflows/python-tests.yml`

The browser build is covered by `TEST_PLAN.md` — a per-feature status matrix and
ID-coded manual test cases. Not-yet-implemented features are listed there as such
rather than omitted.

---

## Status

Active development. The full annotation and capture feature set is delivered and
in use. Known gaps, all listed in `TEST_PLAN.md`: annotation numbering, PDF
export, cloud save and share, and frame-by-frame video annotation.

---

## How this was built

Specification first. Every ticket carries scope, deliverables, observable
acceptance criteria and explicit dependencies before any implementation begins;
AI coding agents do the implementation; the output is reviewed against that
specification rather than accepted on trust. `TEST_PLAN.md` is the record of what
was verified and what was not.

That method is the point of this portfolio — see
[github.com/emil3663](https://github.com/emil3663).

---

## Licence

MIT. See `LICENSE`.
