"""Pure geometry for turning a global-coordinate selection into a real capture.

Issue #1: a region capture, a full-screen capture, a recording, and three
launcher-positioning call sites all grabbed or measured `primaryScreen()`
unconditionally, whatever screen the user was actually working on. Fixing the
region-capture site also surfaced a second, more severe defect (see
`ScreenshotOverlay.activate()`): `showFullScreen()` silently discards whatever
geometry `setGeometry()` requested and collapses the window onto one screen,
so a multi-screen selection was never reachable in the first place, on top of
`QScreen.grabWindow(0, x, y, w, h)` taking coordinates relative to *that
screen*, not global ones.

Everything here works on `QRect` values rather than `QScreen` objects, so a
multi-monitor layout - including negative offsets and mixed DPI - can be
exercised with literal geometries and no second monitor.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QSize


def screens_intersecting(global_rect: QRect, screen_geometries: list[QRect]) -> list[int]:
    """Indices of every screen whose geometry overlaps global_rect, in order."""
    return [
        index for index, geometry in enumerate(screen_geometries)
        if geometry.intersects(global_rect)
    ]


def screen_for_rect(global_rect: QRect, screen_geometries: list[QRect]) -> int:
    """Index of the screen holding the largest intersection with global_rect.

    Used where exactly one screen has to be chosen (e.g. positioning a
    widget). Falls back to 0 if global_rect touches no screen at all, so a
    caller never has to guard against an out-of-range index.
    """
    best_index = 0
    best_area = -1
    for index, geometry in enumerate(screen_geometries):
        intersection = geometry.intersected(global_rect)
        area = 0 if intersection.isEmpty() else intersection.width() * intersection.height()
        if area > best_area:
            best_area = area
            best_index = index
    return best_index


def to_screen_local(global_rect: QRect, screen_geometry: QRect) -> QRect:
    """Convert a global rect into coordinates relative to screen_geometry's origin."""
    return global_rect.translated(-screen_geometry.topLeft())


def is_within_dock_band(widget_right: int, pointer: QPoint, screen_geometry: QRect, threshold: int) -> bool:
    """Whether a drag has brought a widget's right edge close enough to
    screen_geometry's own right edge to auto-dock - a narrow band just
    inside the edge, not a half-plane test.

    DSP-12/13/14: "right edge at or past the screen's right edge" is
    satisfied by almost any position reachable by dragging in from a screen
    to the right, so a widget entering a screen from its right side
    auto-docked the instant it arrived rather than only once flush with
    that screen's own edge. Requiring the pointer itself to still be on
    screen_geometry - not just the widget's separately-resolved "current"
    screen - stops a docking decision being made while the two disagree,
    e.g. mid-crossing.
    """
    if not screen_geometry.contains(pointer):
        return False
    distance_from_right_edge = screen_geometry.right() - widget_right
    return 0 <= distance_from_right_edge <= threshold


@dataclass(frozen=True)
class GrabPiece:
    """One screen's contribution to a capture.

    `screen_local_rect` is what to pass to that screen's `grabWindow()`;
    `dest` is where, in device-independent pixels, the grabbed piece belongs
    in the composited result.
    """
    screen_index: int
    screen_local_rect: QRect
    dest: QPoint


def plan_capture(global_rect: QRect, screen_geometries: list[QRect]) -> list[GrabPiece]:
    """Decide which screen(s) to grab from and where each piece lands.

    A selection spanning two screens is composited from every intersecting
    screen rather than clamped to one - silently returning less than the
    user selected is exactly the class of bug this exists to remove. A
    single-screen selection produces exactly one piece covering the whole
    rect, so nothing changes for the common case.

    Pieces are placed adjacently along whichever axis the screens are
    actually separated on, not at their true virtual-desktop offset. A gap
    between screens (e.g. mismatched monitor heights, or one stacked above
    another) would otherwise show up in the result as an unpainted region,
    which every viewer renders as a solid black band - the "math is right,
    output is unusable" failure predicted when that gap was excluded from
    the overlay's dimmed region rather than clamped (see
    ScreenshotOverlay._covered_region()). A tester dragging a selection
    across two monitors is asking for both screens side by side (or
    stacked, if that is how they are arranged), not a coordinate-accurate
    map of a desktop with a hole in it.

    The axis choice: if every piece's x-range overlaps every other's, the
    screens are stacked vertically relative to each other (or there is only
    one), so the gap is closed in y and x keeps its true relative position.
    Otherwise - separated in x, or separated on both axes (a genuinely
    diagonal layout, where no single choice removes every gap) - the gap is
    closed in x and y keeps its true relative position, as before. A single
    piece is unaffected either way: both axes reduce to (0, 0) for it.
    """
    raw = []
    for index in screens_intersecting(global_rect, screen_geometries):
        geometry = screen_geometries[index]
        intersection = geometry.intersected(global_rect)
        if not intersection.isEmpty():
            raw.append((index, geometry, intersection))

    if not raw:
        return []

    stack_vertically = max(i.left() for _, _, i in raw) <= min(i.right() for _, _, i in raw)

    if stack_vertically:
        raw.sort(key=lambda item: item[2].top())
        left_of_bounding_box = min(intersection.left() for _, _, intersection in raw)
        pieces = []
        y_cursor = 0
        for index, geometry, intersection in raw:
            local = to_screen_local(intersection, geometry)
            dest = QPoint(intersection.left() - left_of_bounding_box, y_cursor)
            pieces.append(GrabPiece(index, local, dest))
            y_cursor += intersection.height()
        return pieces

    raw.sort(key=lambda item: item[2].left())
    top_of_bounding_box = min(intersection.top() for _, _, intersection in raw)

    pieces = []
    x_cursor = 0
    for index, geometry, intersection in raw:
        local = to_screen_local(intersection, geometry)
        dest = QPoint(x_cursor, intersection.top() - top_of_bounding_box)
        pieces.append(GrabPiece(index, local, dest))
        x_cursor += intersection.width()
    return pieces


def composite_ratio(pieces: list[GrabPiece], screen_ratios: list[float]) -> float:
    """The device-pixel ratio a composited capture should be rendered at.

    The highest ratio among the contributing screens, so a selection
    spanning a 2.0 screen and a 1.0 one keeps the sharp half at full
    detail and scales the coarser half up to meet it. Taking the lowest
    (or assuming 1.0, which is what sizing the result in logical pixels
    amounted to) discards real captured pixels permanently: grabWindow()
    returns every device pixel the screen holds, and a tool whose output
    is evidence should not be the thing that throws them away.

    Falls back to 1.0 for an empty plan so a caller never divides by or
    multiplies with a meaningless ratio.
    """
    if not pieces:
        return 1.0
    return max(screen_ratios[piece.screen_index] for piece in pieces)


def to_device_rect(dest: QPoint, local_size: QSize, ratio: float) -> QRect:
    """Where one piece lands in a result measured in device pixels.

    `plan_capture()` places pieces in logical pixels, because that is the
    space a selection is dragged in; this is the same placement scaled
    onto the device-pixel grid the result is actually stored on.
    """
    return QRect(
        round(dest.x() * ratio),
        round(dest.y() * ratio),
        round(local_size.width() * ratio),
        round(local_size.height() * ratio),
    )


def device_result_size(pieces: list[GrabPiece], ratio: float) -> QSize:
    """The size, in device pixels, of the pixmap the pieces composite into.

    max(dest + size) per axis rather than summing, for the same reason
    plan_capture() places pieces the way it does: which axis was packed
    is that function's decision, and this must stay correct either way.
    """
    if not pieces:
        return QSize(0, 0)
    width = max(piece.dest.x() + piece.screen_local_rect.width() for piece in pieces)
    height = max(piece.dest.y() + piece.screen_local_rect.height() for piece in pieces)
    return QSize(round(width * ratio), round(height * ratio))
