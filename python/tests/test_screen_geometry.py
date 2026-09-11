"""Unit tests for the multi-display capture geometry (issue #1).

These take literal QRect layouts, not QScreen objects, so a second monitor -
including a negative-coordinate or mixed-DPI layout - is not needed to prove
the maths. What cannot be proven here is the actual pixel grab on real
hardware; see DESKTOP_STABILITY_MATRIX.md for what stays manual (CAP-12).
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize

from screen_geometry import (
    composite_ratio,
    device_result_size,
    is_within_dock_band,
    plan_capture,
    screen_for_rect,
    screens_intersecting,
    to_device_rect,
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


# ── plan_capture: closing the gap (PRE_BUILD_HANDOVER item 8) ───────────────
#
# DSP-08 (real hardware): a selection spanning laptop and external produced
# a correct composite either side, but a solid black band ~384px wide sat
# between them - virtual-desktop coordinate space belonging to no screen,
# left unpainted. Decision: composite pieces adjacently (no gap), keeping
# vertical offsets true, since screens at different heights are a real
# relationship rather than an artefact to collapse.

def test_DSP_08_a_gap_between_screens_is_closed_not_left_as_a_band():
    primary = QRect(0, 0, 1000, 800)
    secondary = QRect(1200, 0, 1000, 800)      # a 200px gap: 1000..1200 belongs to no screen
    selection = QRect(800, 100, 600, 200)      # x: 800..1400, spans the gap

    pieces = plan_capture(selection, [primary, secondary])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}
    left, right = by_screen[0], by_screen[1]

    assert left.screen_local_rect == QRect(800, 100, 200, 200)
    assert left.dest == QPoint(0, 0)

    # The second piece butts against the first - its own width, not the true
    # 400px virtual-desktop offset that would leave the 200px gap unpainted.
    assert right.screen_local_rect == QRect(0, 100, 200, 200)
    assert right.dest == QPoint(left.screen_local_rect.width(), 0)
    assert right.dest.x() == 200


def test_plan_capture_abutting_screens_are_unaffected_by_the_gap_fix():
    """Two screens with zero gap must produce the same result the true-offset
    approach already gave - the gap-closing logic changes nothing when there
    is no gap to close."""
    primary = QRect(0, 0, 1000, 800)
    secondary = QRect(1000, 0, 1000, 800)      # abuts exactly, no gap
    selection = QRect(800, 100, 400, 200)

    pieces = plan_capture(selection, [primary, secondary])

    by_screen = {p.screen_index: p for p in pieces}
    assert by_screen[0].dest == QPoint(0, 0)
    assert by_screen[1].dest == QPoint(200, 0)


def test_plan_capture_single_screen_is_unaffected_by_the_gap_fix():
    geometries = [QRect(0, 0, 1920, 1080)]
    selection = QRect(100, 100, 300, 200)

    pieces = plan_capture(selection, geometries)

    assert len(pieces) == 1
    assert pieces[0].dest == QPoint(0, 0)


def test_plan_capture_gap_fix_preserves_true_vertical_offset():
    """These two screens are separated in x (side by side, no shared
    x-range) - the gap-closing axis - so y keeps its true relative
    position: screens at different heights are a real relationship, not a
    gap to collapse."""
    upper = QRect(0, 0, 1000, 600)            # shorter screen, top-aligned
    lower = QRect(1000, 200, 1000, 800)       # taller screen, starts 200px lower
    selection = QRect(800, 0, 400, 900)       # spans both, well past either's bottom

    pieces = plan_capture(selection, [upper, lower])

    by_screen = {p.screen_index: p for p in pieces}
    # The lower screen's piece starts 200px further down than the upper's,
    # matching their true geometry - not reset to a shared y=0.
    assert by_screen[1].dest.y() - by_screen[0].dest.y() == 200


# ── plan_capture: packing along whichever axis screens are separated on ─────
#
# DSP-04 (secondary above), reported after e201cdb: two screens stacked
# vertically (same x-range, separated in y) were still packed side by side,
# because plan_capture always accumulated x regardless of which axis the
# screens were actually separated on. That reintroduces the exact black band
# the commit exists to remove, just on the other axis.

def test_DSP_04_secondary_directly_above_with_a_gap_stacks_vertically():
    """The exact reported repro: same x-range, secondary above with a gap."""
    upper = QRect(0, -1080, 1920, 1080)
    lower = QRect(0, 0, 1920, 1080)
    selection = QRect(200, -500, 800, 1000)   # spans the boundary at y=0

    pieces = plan_capture(selection, [upper, lower])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}
    assert by_screen[0].dest == QPoint(0, 0)
    # Stacked directly beneath the first piece - its own height, not a
    # virtual-desktop offset that would leave a gap between them.
    assert by_screen[1].dest == QPoint(0, by_screen[0].screen_local_rect.height())
    assert by_screen[1].dest == QPoint(0, 500)


def test_DSP_04b_secondary_directly_below_with_a_gap_stacks_vertically():
    upper = QRect(0, 0, 1920, 1080)
    lower = QRect(0, 1200, 1920, 1080)        # 120px gap: 1080..1200
    selection = QRect(100, 900, 500, 500)     # x: 900..1399, spans the gap

    pieces = plan_capture(selection, [upper, lower])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}
    assert by_screen[0].dest == QPoint(0, 0)
    assert by_screen[1].dest == QPoint(0, by_screen[0].screen_local_rect.height())


def test_plan_capture_result_bounding_box_is_fully_painted_when_stacked():
    """The failure mode DSP-04 actually looked like: capture.py sizes the
    result from max(dest + size) per axis, so a vertically-packed result
    must not be wider than a single piece - that width would be unpainted
    space either side, invisible in a geometry-only assertion but visible
    as a black margin in the real output."""
    upper = QRect(0, -1080, 1920, 1080)
    lower = QRect(0, 0, 1920, 1080)
    selection = QRect(200, -500, 800, 1000)

    pieces = plan_capture(selection, [upper, lower])

    result_width = max(p.dest.x() + p.screen_local_rect.width() for p in pieces)
    result_height = max(p.dest.y() + p.screen_local_rect.height() for p in pieces)
    assert (result_width, result_height) == (800, 1000)


def test_plan_capture_diagonal_layout_is_pinned_not_incidental():
    """Screens separated on both axes have no single gap-free answer.
    Decision: pack horizontally (as for the plain side-by-side case) rather
    than leave the choice to sort-order incidence - a real relationship
    (the vertical offset) is preserved on top, exactly as the purely
    horizontal case already does."""
    primary = QRect(0, 0, 1000, 800)
    secondary = QRect(1200, 900, 1000, 800)   # gap in x (1000..1200) and y (800..900)
    selection = QRect(800, 700, 600, 400)     # x: 800..1399, y: 700..1099 - spans both gaps

    pieces = plan_capture(selection, [primary, secondary])

    assert len(pieces) == 2
    by_screen = {p.screen_index: p for p in pieces}
    assert by_screen[0].screen_local_rect == QRect(800, 700, 200, 100)
    assert by_screen[0].dest == QPoint(0, 0)
    assert by_screen[1].screen_local_rect == QRect(0, 0, 200, 200)
    assert by_screen[1].dest == QPoint(200, 200)


# ── is_within_dock_band (DSP-12/13/14) ──────────────────────────────────────
#
# Reported-hardware layout: laptop -1920..-384, external 0..1920. Dragging the
# launcher from the external onto the laptop, which sits to its LEFT, used to
# auto-dock the instant it arrived and undocking sent it back to the external.

_LAPTOP = QRect(-1920, 0, 1536, 864)     # right() = -385
_EXTERNAL = QRect(0, 0, 1920, 1080)      # right() = 1919


def test_DSP_12_a_widget_entering_a_screen_from_the_right_does_not_auto_dock():
    """The old half-plane test ("right edge at or past the screen's right
    edge") was satisfied by almost any position reachable by dragging in
    from a screen to the right - reproducing exactly this."""
    widget_right = -500                        # comfortably inside the laptop,
    pointer = QPoint(-500, 100)                 # nowhere near ITS OWN right edge
    assert not is_within_dock_band(widget_right, pointer, _LAPTOP, threshold=12)


def test_DSP_widget_genuinely_flush_with_the_right_edge_does_auto_dock():
    widget_right = _LAPTOP.right() - 5          # 5px inside the edge
    pointer = QPoint(-500, 100)
    assert is_within_dock_band(widget_right, pointer, _LAPTOP, threshold=12)


def test_DSP_the_band_has_a_far_boundary_too():
    just_outside = _LAPTOP.right() - 13         # 1px past the threshold
    pointer = QPoint(-500, 100)
    assert not is_within_dock_band(just_outside, pointer, _LAPTOP, threshold=12)


def test_DSP_a_widget_past_the_right_edge_does_not_auto_dock():
    """The band only opens *inside* the edge - a widget already past it
    (distance negative) is not "flush", it has overshot."""
    past_the_edge = _LAPTOP.right() + 5
    pointer = QPoint(-500, 100)
    assert not is_within_dock_band(past_the_edge, pointer, _LAPTOP, threshold=12)


def test_DSP_13_dock_band_requires_the_pointer_on_the_same_screen():
    """A widget's frame can be flush with one screen's edge while the
    pointer driving the drag is still over a different screen - docking
    must not fire on the geometry alone."""
    widget_right = _LAPTOP.right() - 5
    pointer_on_external = QPoint(500, 100)
    assert not is_within_dock_band(widget_right, pointer_on_external, _LAPTOP, threshold=12)


# ── Device-pixel scaling ─────────────────────────────────────────────────────
#
# A selection is dragged in logical pixels, but a screen with a
# devicePixelRatio above 1 holds more real pixels than that and
# grabWindow() returns all of them. Compositing into a logically-sized
# pixmap threw them away - a 400x300 selection on a 2.0 screen grabbed
# 800x600 and resampled down to 400x300, discarding 3/4 of the capture.
#
# CI runs on 1.0-ratio hardware, where every one of these cases is a
# no-op. That is exactly why they are here as literal ratios rather than
# left to a real HiDPI machine nobody's CI has.


def test_composite_ratio_is_one_for_ordinary_screens() -> None:
    """The overwhelmingly common case must be untouched: on 1.0 hardware
    the result is the same size it always was, byte for byte."""
    screens = [QRect(0, 0, 1920, 1080)]
    pieces = plan_capture(QRect(100, 100, 400, 300), screens)
    assert composite_ratio(pieces, [1.0]) == 1.0
    assert device_result_size(pieces, 1.0) == QSize(400, 300)


def test_composite_ratio_follows_a_hidpi_screen() -> None:
    screens = [QRect(0, 0, 1512, 982)]
    pieces = plan_capture(QRect(200, 200, 400, 300), screens)
    ratio = composite_ratio(pieces, [2.0])
    assert ratio == 2.0
    assert device_result_size(pieces, ratio) == QSize(800, 600)


def test_a_span_takes_the_sharpest_screen_not_the_coarsest() -> None:
    """Taking the lowest ratio would discard real pixels from the sharper
    screen permanently. Scaling the coarser piece up cannot invent detail,
    but it does not destroy any either - and it keeps one consistent grid."""
    retina = QRect(0, 0, 1512, 982)
    external = QRect(1512, 0, 1920, 1080)
    pieces = plan_capture(QRect(1000, 100, 1000, 400), [retina, external])

    assert len(pieces) == 2, "selection must span both screens for this to mean anything"
    assert composite_ratio(pieces, [2.0, 1.0]) == 2.0
    assert composite_ratio(pieces, [1.0, 2.0]) == 2.0


def test_a_span_that_misses_the_hidpi_screen_stays_at_one() -> None:
    """The ratio comes from the screens actually contributing, not from
    the sharpest screen attached to the machine."""
    retina = QRect(0, 0, 1512, 982)
    left = QRect(-1920, 0, 1920, 1080)
    right = QRect(1512, 0, 1920, 1080)
    # entirely on the two 1.0 externals, nowhere near the retina panel
    pieces = plan_capture(QRect(-500, 100, 400, 300), [retina, left, right])

    assert composite_ratio(pieces, [2.0, 1.0, 1.0]) == 1.0


def test_to_device_rect_scales_placement_and_size_together() -> None:
    assert to_device_rect(QPoint(0, 0), QSize(400, 300), 1.0) == QRect(0, 0, 400, 300)
    assert to_device_rect(QPoint(0, 0), QSize(400, 300), 2.0) == QRect(0, 0, 800, 600)
    assert to_device_rect(QPoint(512, 0), QSize(488, 400), 2.0) == QRect(1024, 0, 976, 800)


def test_device_pieces_tile_the_result_without_gap_or_overlap() -> None:
    """The property that actually matters: scaled up, the pieces must still
    exactly cover the result. An off-by-one in the rounding shows up as a
    1px unpainted seam, which every viewer renders as a black line down the
    middle of the evidence."""
    retina = QRect(0, 0, 1512, 982)
    external = QRect(1512, 0, 1920, 1080)
    for ratio in (1.0, 2.0, 3.0):
        pieces = plan_capture(QRect(1000, 100, 1000, 400), [retina, external])
        size = device_result_size(pieces, ratio)
        rects = [to_device_rect(p.dest, p.screen_local_rect.size(), ratio) for p in pieces]

        covered = sum(r.width() * r.height() for r in rects)
        assert covered == size.width() * size.height(), f"gap or overlap at ratio {ratio}"
        for a, b in zip(rects, rects[1:]):
            assert not a.intersects(b), f"pieces overlap at ratio {ratio}"


def test_an_empty_plan_yields_a_usable_ratio_and_size() -> None:
    """A selection touching no screen should not make a caller divide by a
    meaningless ratio or build a negative-sized pixmap."""
    assert composite_ratio([], [2.0]) == 1.0
    assert device_result_size([], 1.0) == QSize(0, 0)
