"""Visual regression tests that run against real font rendering (TA-226).

Deliberately excluded from the main suite by pytest.ini's default
`-m "not visual"` - the offscreen Qt platform plugin every other test in
this project runs under does not rasterize real glyphs, so a screenshot
taken under it is tofu boxes, not text. Nothing here can prove a
rendering/clipping/layout claim while offscreen; these tests need the
real "windows" Qt platform plugin, which only a real Windows machine can
give. CI runs these in a dedicated step that does not set
QT_QPA_PLATFORM=offscreen (conftest.py's `os.environ.setdefault` only
applies its own default when nothing has already set the variable, so
that step's real "windows" plugin wins).

Run explicitly: `pytest -m visual` with QT_QPA_PLATFORM set to "windows"
(not left unset - conftest.py's setdefault would fill in "offscreen"
otherwise). Running the whole suite with plain `pytest -q` skips this file
by design - see DESKTOP_STABILITY_MATRIX.md's note on this lane.
"""
from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPushButton

from editor import EditorWindow, _RecordingThumb, _SnapshotThumb
import theme
from theme import ACCENT, BG_700, LINE

pytestmark = pytest.mark.visual

# A per-test skipif, not a module-level pytest.skip(): the latter fires
# during collection/import, before pytest.ini's `-m "not visual"` ever gets
# a chance to deselect this module in the main lane's plain `pytest -q` -
# which would show up as an unwanted "1 skipped" there instead of a clean
# deselection. A skipif on the test itself is only evaluated for an item
# that already survived marker-based deselection, so the main lane (which
# never selects anything marked visual) never sees it at all; only an
# explicit `-m visual` run that forgot to set QT_QPA_PLATFORM=windows hits
# this, with a clear reason instead of a confusing tofu-box failure.
_offscreen = pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="needs the real 'windows' Qt platform plugin, not offscreen",
)


def _ink_row_bounds(image, background: QColor, threshold: int = 160) -> tuple[int, int] | None:
    """The topmost and bottommost row containing a pixel of real text ink,
    or None if none was found - i.e. nothing was actually drawn.

    Bounding-box/ink-extent, not a pixel-diff against a checked-in golden
    image (TA-226's own tradeoff, decided here): a golden image is brittle
    to font-hinting/ClearType/DPI drift whenever the CI runner's Windows or
    font-package version changes underneath it, and would need
    re-capturing for reasons that have nothing to do with a real
    regression. Measuring where the ink actually falls relative to the
    widget's own rendered rect is closer to what "not clipped" literally
    means, and keeps working across a font-rendering change that isn't a
    bug.

    threshold is a summed per-channel distance, not a per-channel one: the
    button's own `border: 1px solid` (theme.LINE_STRONG) runs the full
    height on both edges and differs from the background enough to trip a
    per-channel check (measured ~95-104 combined distance on a real
    render), which would wrongly read as text on every row. Real text
    (theme.MUTED) measured ~271-340 on the same render - comfortably above
    a threshold that sits below the border's and above real ink's.
    """
    top = None
    bottom = None
    for y in range(image.height()):
        for x in range(image.width()):
            px = image.pixelColor(x, y)
            distance = (
                abs(px.red() - background.red())
                + abs(px.green() - background.green())
                + abs(px.blue() - background.blue())
            )
            if distance > threshold:
                if top is None:
                    top = y
                bottom = y
                break
    if top is None:
        return None
    return top, bottom


@_offscreen
def test_TA221_copy_and_export_render_full_text_with_no_clipped_descenders(qapp) -> None:
    """Retrofits TA-221's own acceptance criterion, which rc5 shipped
    without: a screenshot proving "Copy"/"Export" render in full, not
    clipped ("Copv"/"Exoort"). The offscreen suite could only prove the
    natural height now matches _btn_save_png's (a measurement-based proxy,
    per rc5's BUILD_LOG entry) - this is the real thing, run against real
    ClearType/font-hinting on the actual machine.

    Honest limitation, found while writing this (see docs/BUILD_LOG.md's
    TA-226 entry for the full measurement): reverting to the pre-fix
    `setFixedHeight(26)` on this specific machine's font rendering does
    NOT reproduce visible clipping - measured at 12 ink rows out of a
    14-row unclipped maximum, identical to `_btn_save_png`'s own
    untouched `setFixedHeight(28)`, which the ticket already treats as
    fine. Font-metric drift across machines/ClearType settings is exactly
    the risk TA-226 exists to surface, not hide - this test still checks
    the real, literal acceptance criterion for the code as shipped;
    test_ink_extent_detection_actually_catches_a_clipped_button below
    proves the detection mechanism itself catches real clipping when it
    is actually present, independent of whether that specific historical
    height reproduces it on any given machine.
    """
    app = QApplication.instance()
    app.setStyle("Fusion")
    app.setStyleSheet(theme.editor_style())

    editor = EditorWindow()
    editor.show()
    qapp.processEvents()

    background = QColor(BG_700)  # the button's own QSS background-color

    for button in (editor._btn_copy, editor._btn_export_json):
        image = button.grab().toImage()
        bounds = _ink_row_bounds(image, background)
        assert bounds is not None, (
            f"{button.text()!r} rendered no visible ink at all against its "
            "own background - real font rendering did not happen, or the "
            "button is blank"
        )
        top, bottom = bounds
        assert top > 0, (
            f"{button.text()!r} text touches the very top row (0 of "
            f"{image.height()}) - this is what clipping looks like"
        )
        assert bottom < image.height() - 1, (
            f"{button.text()!r} text touches the very bottom row "
            f"({image.height() - 1} of {image.height()}) - a descender is "
            "being cut off"
        )

    editor.close()


def _edge_color(image, x: int, y: int) -> QColor:
    x = max(0, min(image.width() - 1, x))
    y = max(0, min(image.height() - 1, y))
    return image.pixelColor(x, y)


def _channel_distance(a: QColor, b: QColor) -> int:
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())


@_offscreen
def test_TA244_a_recording_tile_is_visually_distinct_from_a_snapshot_at_rest(qapp, tmp_path) -> None:
    """This ticket's own acceptance bar: verified against a real rendered
    screenshot, not argued from the CSS alone, and _SnapshotThumb checked
    explicitly rather than assumed untouched. Neither tile is hovered -
    "at rest, not just on hover" is the whole point of this ticket's fix,
    since a static theme.LINE_STRONG border only read as "this is a
    recording" once the pointer happened to land on the tile."""
    app = QApplication.instance()
    app.setStyle("Fusion")
    app.setStyleSheet(theme.editor_style())

    video_path = tmp_path / "ta244-recording.mp4"
    video_path.write_bytes(b"fake mp4")
    image_path = tmp_path / "ta244-snapshot.png"
    from PySide6.QtGui import QPixmap
    QPixmap(64, 48).save(str(image_path))

    recording_thumb = _RecordingThumb(video_path, 1)
    snapshot_thumb = _SnapshotThumb(image_path, 1)
    recording_thumb.show()
    snapshot_thumb.show()
    qapp.processEvents()

    try:
        rec_image = recording_thumb.grab().toImage()
        snap_image = snapshot_thumb.grab().toImage()

        # Sample the left edge, mid-height - a QFrame's border is drawn
        # right at the widget's own edge.
        rec_mid_y = rec_image.height() // 2
        snap_mid_y = snap_image.height() // 2
        rec_border = _edge_color(rec_image, 0, rec_mid_y)
        snap_border = _edge_color(snap_image, 0, snap_mid_y)

        accent = QColor(ACCENT)
        line = QColor(LINE)

        assert _channel_distance(rec_border, accent) < _channel_distance(rec_border, line), (
            f"the recording tile's rest-state border {rec_border.getRgb()} reads "
            f"closer to theme.LINE {line.getRgb()} than theme.ACCENT "
            f"{accent.getRgb()} - it should be noticeably accented without hovering"
        )
        assert _channel_distance(snap_border, line) <= _channel_distance(snap_border, accent), (
            f"_SnapshotThumb's own border {snap_border.getRgb()} moved toward "
            f"theme.ACCENT {accent.getRgb()} - it must stay theme.LINE "
            f"{line.getRgb()}, untouched by this ticket"
        )

        # The two tiles' borders must actually differ from each other -
        # the real "identifiable at a glance" claim, not just each one
        # individually matching its own expected token.
        assert _channel_distance(rec_border, snap_border) > 30, (
            "a recording tile and a snapshot tile render with "
            "indistinguishable borders at rest"
        )
    finally:
        recording_thumb.close()
        snapshot_thumb.close()


@_offscreen
def test_ink_extent_detection_actually_catches_a_clipped_button(qapp) -> None:
    """Proves _ink_row_bounds() genuinely discriminates clipped from
    unclipped real rendering, rather than trusting the mechanism on the
    strength of the arithmetic alone.

    A plain QPushButton("Copy") with the same real stylesheet applied,
    swept by fixed height on this exact machine while writing this test:
    0 ink rows at height <= 16 (Qt omits the label entirely rather than
    drawing a partial glyph below some minimum), a growing partial glyph
    from height 18 up, plateauing at the full 14-row glyph only from
    height 30 - so height 18 is a real, measured, reproducibly-clipped
    case on this hardware, unlike the historical height 26 (see the test
    above). Compares against a naturally-sized control button from the
    same run, not a hardcoded row count, so this does not itself become
    the kind of DPI/font-version-brittle fixture TA-226 exists to avoid.
    """
    app = QApplication.instance()
    app.setStyle("Fusion")
    app.setStyleSheet(theme.editor_style())
    background = QColor(BG_700)

    control = QPushButton("Copy")
    control.show()
    clipped = QPushButton("Copy")
    clipped.setFixedHeight(18)
    clipped.show()
    qapp.processEvents()

    try:
        control_bounds = _ink_row_bounds(control.grab().toImage(), background)
        clipped_bounds = _ink_row_bounds(clipped.grab().toImage(), background)

        assert control_bounds is not None, "control button rendered no ink at all"
        control_rows = control_bounds[1] - control_bounds[0] + 1

        if clipped_bounds is None:
            clipped_rows = 0
        else:
            clipped_rows = clipped_bounds[1] - clipped_bounds[0] + 1

        assert clipped_rows < control_rows, (
            f"a button fixed to 18px tall rendered {clipped_rows} ink rows, "
            f"not fewer than the naturally-sized control's {control_rows} - "
            "the detection mechanism did not catch a real, deliberately "
            "undersized button"
        )
    finally:
        control.close()
        clipped.close()
