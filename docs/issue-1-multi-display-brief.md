# Issue #1 — multi-display capture and pinning

## The bug, confirmed in code

`capture.py` line 136, the whole of `_grab`:

    pixmap = QApplication.primaryScreen().grabWindow(
        0, rect.x(), rect.y(), rect.width(), rect.height()
    )

Three errors compound here:

1. **It always grabs `primaryScreen()`**, whatever the user selected.
2. **`rect` is in overlay-widget coordinates.** `activate()` places the overlay at
   `availableVirtualGeometry()`, so widget (0,0) is the virtual desktop's
   top-left — which is *not* global (0,0) when a monitor sits left of or above
   the primary. On Windows those layouts give negative coordinates, and this is
   the common case for a laptop with an external monitor.
3. **`QScreen::grabWindow(0, x, y, w, h)` takes coordinates relative to *that
   screen*,** not global ones. Even with the right screen picked, the screen's
   origin has to be subtracted.

Together these produce exactly the reported symptom: the returned image is the
area with matching coordinates *on the main display*.

## The same defect in four more places

The reporter found two of these. The others are the same root cause and are
worth fixing in one pass:

| Where | Code | Effect |
|---|---|---|
| `capture.py:136` | `primaryScreen().grabWindow(0, …)` | **Reported.** Region capture returns the wrong screen |
| `launcher.py:312` | `primaryScreen().grabWindow(0)` | Full-screen capture only ever captures the primary |
| `capture.py:226` | `primaryScreen()` in `_capture_frame` | **Recording only ever records the primary display** |
| `launcher.py:444` | `primaryScreen().availableGeometry()` | Auto-dock measures the wrong screen's edge |
| `launcher.py:502` | `primaryScreen().availableGeometry()` | `_position_top_right` sends the widget to the primary |
| `launcher.py:511` | `primaryScreen().availableGeometry()` | `_dock_right` docks to the primary's edge |

The last three are the "widget pinning also exhibits coordinate mapping issues"
half of the report. The recording one is **not** in the report and is arguably
worse than the reported bug: a tester records a repro on their external monitor
and gets a video of the wrong screen, with nothing to hint at it until playback.

## Two further problems any fix must handle

**Mixed DPI — likely a second, independent bug.** The reporter's machine is a
ThinkPad P14s Gen 5: a high-DPI laptop panel, almost certainly alongside a 100%
external monitor. `grabWindow` returns device pixels at *that screen's*
`devicePixelRatio`, while widget coordinates are logical. A fix that picks the
right screen but ignores per-screen DPR will still return a wrongly sized or
offset image on the secondary. This is the part most likely to be missed,
because it looks fixed on a matched-DPI setup.

**Selections spanning two screens** cannot come from one `grabWindow`. Decide
deliberately: composite from every intersecting screen onto one pixmap
(correct, more code), or clamp to the screen holding most of the selection and
say so. Do not leave it undefined.

Also: `activate()` uses `availableVirtualGeometry()`, which excludes taskbars,
so the overlay cannot cover them and a taskbar or notification cannot be
selected. For a QA evidence tool that is probably wrong — consider
`virtualGeometry()`.

## How to make this testable without two monitors

This is the important part. Do **not** write a fix that can only be checked by
plugging in a second display.

Extract the geometry as pure functions that take **rectangles, not `QScreen`
objects**, so they can be tested with synthetic layouts:

- `overlay_local_to_global(local_rect, virtual_origin) -> QRect`
- `screen_for_rect(global_rect, screen_geometries) -> int` — index of the screen
  holding the largest intersection
- `to_screen_local(global_rect, screen_geometry) -> QRect`

Then `_grab` becomes: translate to global, choose the screen, convert to
screen-local, grab, and scale by that screen's `devicePixelRatio`.

Cover with unit tests using literal geometries — no real monitors needed:

- secondary to the right (positive offsets)
- **secondary to the left (negative x)** and above (negative y)
- vertically stacked
- mixed DPI (1.0 primary, 1.5 secondary, and the reverse)
- a selection wholly inside the secondary
- a selection spanning both, asserting whatever behaviour you chose
- a single-screen layout, asserting nothing changed

Do the same for the launcher: positioning should use the screen the widget is
currently on (`QApplication.screenAt(self.frameGeometry().center())`, falling
back to the primary when it returns None — it does when the point is off any
screen).

## What cannot be verified here

Nothing in this repo's test environment has more than one screen, and the
offscreen Qt platform provides a single display. The pure functions above are
fully testable; **the actual grab on a real secondary monitor is not.** It needs
a manual pass on hardware with two displays, ideally at different scaling
factors. Add it to the plan as a Blocked case rather than implying coverage.

## Suggested case IDs

`CAP-10` secondary capture, `CAP-11` negative-coordinate layout, `CAP-12` mixed
DPI, `CAP-13` spanning selection, `REC-09` recording follows the active screen,
`LCH-08` widget docks to the screen it is on.
