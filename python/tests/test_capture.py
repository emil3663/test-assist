"""Window-level and pure-function coverage for TA-232: the capture overlay
under-covering a HiDPI secondary screen by exactly its DPI ratio.

screen_geometry.py is deliberately untouched by this fix (see
docs/ISSUE-TA-232.md) - the defect and its fix live entirely in how many
windows ScreenshotOverlay makes and what geometry each one gets, not in the
grab/composite maths screen_geometry.py already covers. These tests live
here, separate from test_screen_geometry.py, for that reason.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from capture import ScreenshotOverlay, overlay_device_coverage


# ── overlay_device_coverage: the pure claim the fix depends on ──────────────
#
# Numbers are the reference rig from docs/TA-232.md / docs/ISSUE-TA-232.md:
# laptop 1536x864 logical @1.25 (really 1920x1080 device px), external
# 1920x1080 logical @1.0. A single window spanning both can only take one
# DPR (the primary's), so it rendered the laptop's 1536 logical units as
# 1536 device pixels - 64% of the real 1920x1080. One window per screen,
# each set to that screen's own geometry, is what this function's return
# value has to prove: it must equal each screen's real device-pixel area,
# not a fraction of it.

def test_overlay_device_coverage_matches_each_screens_real_device_pixels():
    laptop = QRect(0, 0, 1536, 864)
    external = QRect(1536, 0, 1920, 1080)

    coverage = overlay_device_coverage([laptop, external], [1.25, 1.0])

    assert coverage == [QSize(1920, 1080), QSize(1920, 1080)], (
        "each per-screen window must cover its screen's full device-pixel "
        "area, not the 1536x864 (64%) a single shared-DPR window produced"
    )


def test_overlay_device_coverage_is_unaffected_at_100_percent():
    """The common case - every screen at 1.0 - must be unchanged: logical
    and device pixels already coincide, so coverage is just the geometry."""
    screens = [QRect(0, 0, 1920, 1080), QRect(-1920, 0, 1920, 1080)]
    assert overlay_device_coverage(screens, [1.0, 1.0]) == [
        QSize(1920, 1080), QSize(1920, 1080),
    ]


def test_overlay_device_coverage_handles_three_mixed_ratio_screens():
    screens = [QRect(0, 0, 1536, 864), QRect(1536, 0, 1920, 1080), QRect(0, 864, 1280, 800)]
    ratios = [1.25, 1.0, 1.5]
    assert overlay_device_coverage(screens, ratios) == [
        QSize(1920, 1080), QSize(1920, 1080), QSize(1920, 1200),
    ]


def test_overlay_device_coverage_matches_an_empty_layout():
    assert overlay_device_coverage([], []) == []


# ── Window-level: activate() actually builds one window per screen ──────────

class _StubScreen:
    """Minimal QScreen substitute - geometry and ratio only, plus
    grabWindow() for the one test here that drives a capture to
    completion. Deliberately does not implement virtualGeometry() or
    availableGeometry(): activate() must not call either any more (see
    ScreenshotOverlay.activate()'s docstring) - a stub missing them would
    raise AttributeError if it did."""

    def __init__(self, geometry: QRect, ratio: float = 1.0) -> None:
        self._geometry = geometry
        self._ratio = ratio

    def geometry(self) -> QRect:
        return self._geometry

    def devicePixelRatio(self) -> float:
        return self._ratio

    def grabWindow(self, _wid, x=0, y=0, w=-1, h=-1) -> QPixmap:
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("red"))
        return pixmap


def test_activate_creates_one_window_per_screen_at_its_own_geometry(qapp, monkeypatch):
    """TA-232's actual mechanism, exercised end to end: activate() must not
    size one window to a shared virtualGeometry() (which is what forced a
    single, borrowed DPR) - it must build one window per screen, each set
    to that screen's own geometry, so each inherits that screen's own DPR."""
    laptop = _StubScreen(QRect(-1920, 0, 1536, 864), ratio=1.25)
    external = _StubScreen(QRect(0, 0, 1920, 1080), ratio=1.0)
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [laptop, external]))

    overlay = ScreenshotOverlay()
    overlay.activate()

    assert len(overlay._windows) == 2, "one overlay window per connected screen"
    assert overlay._windows[0].geometry() == laptop.geometry()
    assert overlay._windows[1].geometry() == external.geometry()
    assert overlay.isVisible()

    overlay.close()


def test_activate_rebuilds_windows_for_the_current_screen_layout(qapp, monkeypatch):
    """The overlay is a single instance shared and reused across captures
    (see launcher.py), so a second activate() must reflect the screen
    layout at that time, not the one left over from the previous capture."""
    single = [_StubScreen(QRect(0, 0, 1920, 1080))]
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: single))

    overlay = ScreenshotOverlay()
    overlay.activate()
    assert len(overlay._windows) == 1

    two = [_StubScreen(QRect(0, 0, 1920, 1080)), _StubScreen(QRect(1920, 0, 1280, 800))]
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: two))
    overlay.activate()

    assert len(overlay._windows) == 2
    overlay.close()


def test_window_screen_geometry_survives_hide(qapp, monkeypatch):
    """CAP-14b's original concern, ported to the new architecture: _grab's
    correctness must not depend on geometry read back from a hidden or
    restored widget. Each window's screen_geometry is now a plain
    attribute captured once at construction rather than re-read from Qt,
    so this holds structurally - pinned here so a future change that
    re-derives it from self.geometry() instead would fail loudly."""
    laptop = _StubScreen(QRect(-1920, 0, 1536, 864))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [laptop]))

    overlay = ScreenshotOverlay()
    overlay.activate()
    window = overlay._windows[0]
    assert window.screen_geometry == laptop.geometry()

    window.hide()

    assert window.screen_geometry == laptop.geometry(), \
        "hiding a window must not change the geometry the capture pipeline relies on"
    overlay.close()


# ── TA-231 side effect: an unmapped region is covered by no window at all ───

def test_the_gap_between_mismatched_screens_is_covered_by_no_window(qapp, monkeypatch):
    """TA-231: a virtual-desktop rectangle can include a region that belongs
    to no screen at all - e.g. a laptop panel and an external monitor of
    different logical heights, top-aligned. Under the old single-window
    design that region had to be explicitly excluded from the dim
    (the removed _covered_region()). Under one-window-per-screen there is
    nothing to exclude: no window's geometry reaches that region in the
    first place, so it is simply never dimmed or drawn - see
    docs/TA-231.md for the recorded decision that this removes TA-231's
    case as a side effect of this fix."""
    laptop = _StubScreen(QRect(-1920, 0, 1536, 864))     # logical x: -1920..-384
    external = _StubScreen(QRect(0, 0, 1920, 1080))      # logical x: 0..1920
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [laptop, external]))

    overlay = ScreenshotOverlay()
    overlay.activate()

    dead_zone = QPoint(-300, 900)    # -384 < -300 < 0, and below the laptop's own y=864 bottom edge
    on_laptop = QPoint(-1000, 100)
    on_external = QPoint(500, 100)

    covering = [w for w in overlay._windows if w.screen_geometry.contains(dead_zone)]
    assert covering == [], "no per-screen window should reach a region no real screen occupies"
    assert any(w.screen_geometry.contains(on_laptop) for w in overlay._windows)
    assert any(w.screen_geometry.contains(on_external) for w in overlay._windows)

    overlay.close()


# ── A drag spanning two screens, driven through the real per-window path ────

def _global_mouse(x: float, y: float, button=Qt.MouseButton.LeftButton):
    @dataclass
    class _E:
        _x: float
        _y: float

        def globalPosition(self):
            return QPointF(self._x, self._y)

        def button(self):
            return button

    return _E(x, y)


def test_a_drag_crossing_screens_updates_both_windows_and_yields_one_capture(qapp, monkeypatch):
    """The hard part of the per-screen-window port: a drag that starts on
    one screen's window and ends on another must still work, and the
    other window must show its own share of the growing selection - even
    though it never itself receives a mouse event (see
    ScreenshotOverlay.mousePressEvent's grabMouse() reasoning)."""
    left = _StubScreen(QRect(0, 0, 1000, 800))
    right = _StubScreen(QRect(1000, 0, 1000, 800))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [left, right]))

    overlay = ScreenshotOverlay()
    overlay.activate()
    left_window, right_window = overlay._windows

    captured: list[QPixmap] = []
    overlay.capture_ready.connect(captured.append)

    # Press on the left window, drag across the boundary at x=1000 onto
    # the right - real Qt delivery would move to the right window's own
    # widget once the cursor crosses, but grabMouse() keeps it here.
    left_window.mousePressEvent(_global_mouse(800, 100))
    left_window.mouseMoveEvent(_global_mouse(1200, 300))

    assert left_window._rubber.isVisible()
    assert right_window._rubber.isVisible(), (
        "the right window must show its own share of the selection without "
        "ever receiving a mouse event of its own"
    )

    left_window.mouseReleaseEvent(_global_mouse(1200, 300))
    QTest.qWait(300)   # _grab is deferred 120ms so the overlay can vanish first

    assert len(captured) == 1, "a drag spanning two screens must still yield one composited capture"
    result = captured[0]
    # QRect(point, point) is Qt's inclusive-corner constructor: 401x201, not 400x200.
    assert (result.width(), result.height()) == (401, 201)
    assert not left_window._rubber.isVisible(), "the rubber band must be cleared once the drag completes"
    assert not right_window._rubber.isVisible()
    overlay.close()


def test_escape_hides_every_window_and_cancels(qapp, monkeypatch):
    left = _StubScreen(QRect(0, 0, 1000, 800))
    right = _StubScreen(QRect(1000, 0, 1000, 800))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [left, right]))

    overlay = ScreenshotOverlay()
    overlay.activate()
    left_window, _right_window = overlay._windows

    grabbed: list[QPixmap] = []
    cancelled: list[bool] = []
    overlay.capture_ready.connect(grabbed.append)
    overlay.cancelled.connect(lambda: cancelled.append(True))

    left_window.mousePressEvent(_global_mouse(40, 40))
    left_window.mouseMoveEvent(_global_mouse(200, 160))

    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    overlay.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))

    assert grabbed == [], "Escape must not produce a capture"
    assert cancelled == [True]
    assert not overlay.isVisible(), "Escape must hide every overlay window, not just the one that had focus"
    overlay.close()
