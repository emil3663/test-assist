# Root cause: the capture overlay never spans the virtual desktop

## What was measured

A diagnostic overlay built exactly like `ScreenshotOverlay` printed, on the
reporter-equivalent hardware (laptop 1536×864 @125% at x=−1920, external
1920×1080 @100% at x=0):

    requested overlay geometry : (-1920, 0, 3840, 1032)
    ACTUAL geometry after show : (-1920, 0, 1536, 864)
    window devicePixelRatio    : 1.25

`setGeometry(virt)` followed by `showFullScreen()` **discards the requested
geometry** and makes the window fullscreen on one screen. The overlay covers the
laptop only. The external is not covered at all — you cannot even press on it.

Every drag the probe recorded also reported:

    ERROR : dx=0  dy=0   (agree)

So **the coordinate translation is correct**. `event.position()` plus the window
origin equals `event.globalPosition()` on the screen the window does cover. The
earlier hypothesis that widget-local coordinates break across a DPI boundary was
wrong, and the `screen_geometry.py` functions are not at fault — they were
verified against synthetic layouts including this one.

This single defect is sufficient to explain the reported symptoms — wrong-screen
captures, blank captures, displaced captures — without any other cause.

## The fix

**1. Do not use `showFullScreen()` for a window that must span multiple
screens.** It is defined as fullscreen on *a* screen. Use `show()` after
`setGeometry()`; the window is already frameless and always-on-top, so it needs
no fullscreen state to cover what it is told to cover.

    self.setGeometry(virt)
    self.show()
    self.raise_()
    self.activateWindow()
    self.setFocus()

Then **assert it worked** rather than assuming — this is the whole bug:

    if self.geometry() != virt:
        # log it; the overlay is not covering what it was asked to

**2. Capture the origin once, at activate time.** `_grab` currently reads
`self.geometry().topLeft()` *after* `self.hide()`, and a hidden or restored
window may not report the geometry it had while visible. Store the origin in an
instance attribute when the overlay is shown and use that.

**3. Prefer `event.globalPosition()` anyway.** Not the cause, but it removes the
dependency on window geometry entirely: the rect is then already in the same
space as `QScreen::geometry()` and no translation is needed. Belt and braces, and
it makes the code independent of however Qt decides to place the window.

**4. `availableVirtualGeometry()` excludes taskbars.** Requested height was 1032
against a real 1080. A taskbar or notification cannot be selected. For an
evidence-capture tool that is probably wrong — consider `virtualGeometry()`.

**5. The dead zone.** On this hardware the screens occupy logical x −1920…−384
and 0…1920, leaving **384px of logical space belonging to no screen**. A
selection there has no source pixels and currently yields transparent/black
output with no explanation. Once the overlay genuinely spans the virtual desktop
this becomes reachable, so decide deliberately: either exclude unoccupied
regions from the dimmed area, or clamp the selection to real screen area. Silent
black is the "technically correct" answer that reads as broken.

## Tests

The geometry maths is already covered. What was missing is a test of the
*window*, which is why this got through:

- After `activate()`, assert `overlay.geometry()` equals the requested virtual
  geometry. This fails today and is the regression test for this defect.
- Assert the stored origin used by `_grab` equals the geometry set at activate
  time, and that hiding the overlay does not change it.
- These can run offscreen with a single screen — the assertion is that the
  window keeps the geometry it was given, which does not need two monitors.

## Verification

Automated tests cannot prove the grab returns the right pixels. After the fix,
re-run Block A of `MULTI_DISPLAY_MANUAL_PASS.md` — in particular capturing on
the external, which is currently impossible rather than merely wrong.
