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

from PySide6.QtCore import QPoint, QRect


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
    """
    pieces = []
    for index in screens_intersecting(global_rect, screen_geometries):
        geometry = screen_geometries[index]
        intersection = geometry.intersected(global_rect)
        if intersection.isEmpty():
            continue
        local = to_screen_local(intersection, geometry)
        dest = intersection.topLeft() - global_rect.topLeft()
        pieces.append(GrabPiece(index, local, dest))
    return pieces
