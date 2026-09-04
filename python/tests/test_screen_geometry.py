"""Unit tests for the multi-display capture geometry (issue #1).

These take literal QRect layouts, not QScreen objects, so a second monitor -
including a negative-coordinate or mixed-DPI layout - is not needed to prove
the maths. What cannot be proven here is the actual pixel grab on real
hardware; see DESKTOP_STABILITY_MATRIX.md for what stays manual (CAP-12).
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect

from screen_geometry import (
    plan_capture,
    screen_for_rect,
    screens_intersecting,
    to_screen_local,
)


# ── screens_intersecting ─────────────────────────────────────────────────────

def test_CAP_11_screens_intersecting_finds_a_screen_at_negative_coordinates():
    """Secondary to the left of the primary - the common laptop + external
    monitor layout - reports negative x for anything on the secondary."""
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(-1920, 0, 1920, 1080)
    geometries = [primary, secondary]

    on_secondary = QRect(-500, 100, 200, 150)
    assert screens_intersecting(on_secondary, geometries) == [1]


def test_screens_intersecting_returns_empty_for_a_rect_off_every_screen():
    geometries = [QRect(0, 0, 1920, 1080)]
    assert screens_intersecting(QRect(5000, 5000, 100, 100), geometries) == []


def test_CAP_13_screens_intersecting_finds_both_for_a_spanning_selection():
    primary = QRect(0, 0, 1000, 800)
    secondary = QRect(1000, 0, 1000, 800)
    spanning = QRect(800, 100, 400, 200)
    assert screens_intersecting(spanning, [primary, secondary]) == [0, 1]


# ── screen_for_rect ───────────────────────────────────────────────────────────

def test_CAP_10_screen_for_rect_secondary_to_the_right():
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(1920, 0, 1920, 1080)
    selection = QRect(2000, 100, 200, 150)
    assert screen_for_rect(selection, [primary, secondary]) == 1


def test_screen_for_rect_secondary_above_the_primary_negative_y():
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(0, -1080, 1920, 1080)
    selection = QRect(100, -900, 200, 150)
    assert screen_for_rect(selection, [primary, secondary]) == 1


def test_screen_for_rect_vertically_stacked_layout():
    top = QRect(0, -1080, 1920, 1080)
    bottom = QRect(0, 0, 1920, 1080)
    assert screen_for_rect(QRect(100, -500, 50, 50), [top, bottom]) == 0
    assert screen_for_rect(QRect(100, 500, 50, 50), [top, bottom]) == 1


def test_screen_for_rect_selection_wholly_inside_the_secondary():
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(1920, 0, 1280, 800)
    selection = QRect(2200, 200, 100, 100)
    assert screen_for_rect(selection, [primary, secondary]) == 1


def test_screen_for_rect_mixed_dpi_primary_larger():
    """Primary at 1.0 scale (1920x1080 logical), secondary at 1.5 scale
    (reports a smaller logical geometry, e.g. 1280x800). The selection logic
    only ever sees logical geometries, so a size mismatch between screens
    must not confuse it.

    This proves the screen-selection *geometry* is unaffected by mixed DPI.
    It does not prove the grabbed pixels come out the right size on a real
    high-DPI secondary - that needs actual hardware and is CAP-12, tracked as
    Blocked in DESKTOP_STABILITY_MATRIX.md.
    """
    primary = QRect(0, 0, 1920, 1080)
    secondary_hidpi = QRect(1920, 0, 1280, 800)
    mostly_on_secondary = QRect(1950, 50, 300, 200)
    assert screen_for_rect(mostly_on_secondary, [primary, secondary_hidpi]) == 1


def test_screen_for_rect_mixed_dpi_reversed():
    """Same layout, but the high-DPI screen is now the primary. See the note
    on test_screen_for_rect_mixed_dpi_primary_larger about what this does
    and does not prove."""
    primary_hidpi = QRect(0, 0, 1280, 800)
    secondary = QRect(1280, 0, 1920, 1080)
    mostly_on_secondary = QRect(1310, 50, 300, 200)
    assert screen_for_rect(mostly_on_secondary, [primary_hidpi, secondary]) == 1


def test_screen_for_rect_falls_back_to_index_zero_off_every_screen():
    geometries = [QRect(0, 0, 1920, 1080)]
    assert screen_for_rect(QRect(5000, 5000, 10, 10), geometries) == 0


def test_screen_for_rect_single_screen_layout_is_unaffected():
    geometries = [QRect(0, 0, 1920, 1080)]
    assert screen_for_rect(QRect(100, 100, 200, 200), geometries) == 0


# ── to_screen_local ───────────────────────────────────────────────────────────

def test_to_screen_local_subtracts_the_screen_origin():
    global_rect = QRect(2000, 100, 200, 150)
    screen = QRect(1920, 0, 1920, 1080)
    assert to_screen_local(global_rect, screen) == QRect(80, 100, 200, 150)


def test_to_screen_local_on_a_screen_with_negative_origin():
    global_rect = QRect(-500, 100, 200, 150)
    screen = QRect(-1920, 0, 1920, 1080)
    assert to_screen_local(global_rect, screen) == QRect(1420, 100, 200, 150)


def test_to_screen_local_with_zero_origin_is_unchanged():
    global_rect = QRect(10, 20, 100, 80)
    screen = QRect(0, 0, 1920, 1080)
    assert to_screen_local(global_rect, screen) == global_rect


# ── plan_capture ───────────────────────────────────────────────────────────────

def test_plan_capture_single_screen_layout_produces_one_unmodified_piece():
    """A single-screen layout must behave exactly as before the fix."""
    geometries = [QRect(0, 0, 1920, 1080)]
    selection = QRect(100, 100, 300, 200)

    pieces = plan_capture(selection, geometries)

    assert len(pieces) == 1
    assert pieces[0].screen_index == 0
    assert pieces[0].screen_local_rect == selection
    assert pieces[0].dest == QPoint(0, 0)


def test_plan_capture_selection_wholly_inside_the_secondary():
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(1920, 0, 1920, 1080)
    selection = QRect(2200, 200, 100, 80)

    pieces = plan_capture(selection, [primary, secondary])

    assert len(pieces) == 1
    assert pieces[0].screen_index == 1
    assert pieces[0].screen_local_rect == QRect(280, 200, 100, 80)
    assert pieces[0].dest == QPoint(0, 0)


def test_CAP_13_plan_capture_spanning_selection_composites_both_screens():
    """Decision: composite from every intersecting screen rather than clamp -
    returning less than the user selected is exactly the bug being removed."""
    primary = QRect(0, 0, 1000, 800)
    secondary = QRect(1000, 0, 1000, 800)
    selection = QRect(800, 100, 400, 200)   # x: 800-1200, spans the boundary at 1000

    pieces = plan_capture(selection, [primary, secondary])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}

    left = by_screen[0]
    assert left.screen_local_rect == QRect(800, 100, 200, 200)
    assert left.dest == QPoint(0, 0)

    right = by_screen[1]
    assert right.screen_local_rect == QRect(0, 100, 200, 200)
    assert right.dest == QPoint(200, 0)

    # The two pieces cover the full selection width with no gap or overlap.
    total_width = left.screen_local_rect.width() + right.screen_local_rect.width()
    assert total_width == selection.width()


def test_plan_capture_spanning_a_vertically_stacked_boundary():
    top = QRect(0, -1080, 1920, 1080)
    bottom = QRect(0, 0, 1920, 1080)
    selection = QRect(100, -50, 200, 100)   # straddles y = 0

    pieces = plan_capture(selection, [top, bottom])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}
    assert by_screen[0].screen_local_rect.height() == 50   # 50px on the top screen
    assert by_screen[1].screen_local_rect.height() == 50   # 50px on the bottom screen


def test_plan_capture_negative_coordinate_layout_secondary_to_the_left():
    primary = QRect(0, 0, 1920, 1080)
    secondary = QRect(-1920, 0, 1920, 1080)
    selection = QRect(-500, 100, 200, 150)

    pieces = plan_capture(selection, [primary, secondary])

    assert len(pieces) == 1
    assert pieces[0].screen_index == 1
    assert pieces[0].screen_local_rect == QRect(1420, 100, 200, 150)


def test_plan_capture_ignores_a_selection_touching_no_screen():
    geometries = [QRect(0, 0, 1920, 1080)]
    assert plan_capture(QRect(5000, 5000, 100, 100), geometries) == []
