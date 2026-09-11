"""Colour tokens, fonts and Qt stylesheet for Test Assist (PySide6 edition)."""

import sys

from PySide6.QtGui import QFont

# A fallback chain, not a change of font: whichever platform you are on,
# its own UI face is asked for first and the rest follow as backstops.
#
# This exists because seven call sites constructed `QFont("Segoe UI", ...)`
# with no alternative at all, and Qt answers an unknown family by
# substituting a default whose metrics are its own business. Five of those
# sites are in canvas.py, where QFontMetricsF drives annotation text
# wrapping and badge sizing - so on any machine without Segoe UI installed
# the *exported evidence* laid out differently, not merely the UI chrome.
#
# Ordering by platform rather than hardcoding Segoe UI first is not
# cosmetic: naming a missing family first makes Qt populate its font-family
# alias table to go looking for it, which measured at ~195 ms of startup
# cost on macOS and emits a qt.qpa.fonts warning on every launch. Windows
# still asks for Segoe UI first and so renders exactly as it always has.
#
# ".AppleSystemUIFont" is the always-present macOS system face (SF) and
# is what a Mac actually resolves to. "SF Pro Text" is deliberately NOT
# listed ahead of it: that name ships with Xcode rather than with macOS,
# so on a stock Mac it is missing and naming it first reintroduces the
# very alias-table cost this ordering exists to avoid. Helvetica Neue
# sits behind as the documented public name, in case the dot-prefixed
# private one ever stops resolving.
_WINDOWS_UI = ["Segoe UI"]
_MACOS_UI = [".AppleSystemUIFont", "Helvetica Neue"]
_LINUX_UI = ["Cantarell", "Noto Sans", "DejaVu Sans"]
_GENERIC_UI = ["Arial", "sans-serif"]

if sys.platform == "win32":
    UI_FONT_FAMILIES = _WINDOWS_UI + _MACOS_UI + _LINUX_UI + _GENERIC_UI
elif sys.platform == "darwin":
    UI_FONT_FAMILIES = _MACOS_UI + _WINDOWS_UI + _LINUX_UI + _GENERIC_UI
else:
    UI_FONT_FAMILIES = _LINUX_UI + _WINDOWS_UI + _MACOS_UI + _GENERIC_UI


# The same chain as a CSS font-family value, so the stylesheet and the
# QFont call sites can never name a different font from each other - and
# so the stylesheet inherits the platform ordering rather than pinning a
# missing family first and paying the alias-table cost anyway.
UI_FONT_CSS = ", ".join(
    family if family == "sans-serif" else f"'{family}'"
    for family in UI_FONT_FAMILIES
)

MONO_FONT_FAMILIES = [
    "Consolas", "Cascadia Code", "SF Mono", "Menlo", "DejaVu Sans Mono", "monospace",
]


def ui_font(point_size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """The UI face at a given size, with a real fallback chain.

    `setFamilies` rather than the `QFont(family, ...)` constructor: the
    constructor takes a single family and silently substitutes when it is
    missing, which is the behaviour this exists to remove.
    """
    font = QFont()
    font.setFamilies(UI_FONT_FAMILIES)
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font

# ── Colour tokens ────────────────────────────────────────────────────────────
#
# Two palettes, chosen once at startup from whatever the OS is set to (see
# use_scheme()). Deliberately a binary: light or dark, no in-app toggle and
# nothing persisted, because a third state is a preference to store, migrate
# and keep in step with the OS, and this does not need one.
#
# SCOPE, and the line that keeps this small: these tokens style the
# application's own chrome only - the launcher panel, the editor's toolbars
# and docks. They do NOT reach canvas.py. Annotations are painted on top of
# the user's screenshot, not on app background, so their colours must not
# depend on the tester's OS setting: the same defect marked up on two
# machines has to export the same evidence. canvas.py solves "unknown
# background" its own way already - see the black dashed line drawn under
# the white one for the selection marquee, which is legible over anything.
#
# The launcher is a frameless panel painted by hand, so it needs PANEL_* as
# RGBA values rather than stylesheet rules.

_DARK = {
    "ACCENT":         "#7c83fd",
    # Deepens on hover rather than lightening, which is the less obvious
    # direction on a dark UI and the one the contrast test forces: these
    # buttons carry white labels, and the lighter #8f95ff measured 2.65:1
    # against white - under the 3:1 floor. ACCENT -> HOVER -> PRESSED is
    # therefore one consistent darkening ramp.
    "ACCENT_HOVER":   "#6f77f2",
    "ACCENT_PRESSED": "#666dd4",
    "DANGER":         "#e94560",
    "DANGER_HOVER":   "#f25a73",
    "DANGER_PRESSED": "#c9364e",
    "BG_900":         "#0d0d1a",
    "BG_800":         "#13132a",
    "BG_700":         "#1a1b35",
    "LINE":           "#2a2a4e",
    "LINE_STRONG":    "#3a3a5e",
    "TEXT":           "#e0e6f0",
    "MUTED":          "#8892a4",
    "PANEL_BG":       (13, 13, 26, 242),
    "PANEL_BORDER":   (124, 131, 253, 80),
}

# Amber rather than a lightened indigo: the launcher was originally amber,
# and it reads better against a light ground than the indigo does. Darker
# than that original #c8763a on purpose - white label text on the lighter
# shade falls below 4.5:1, which is fine on near-black and not on white.
_LIGHT = {
    "ACCENT":         "#b0591f",
    "ACCENT_HOVER":   "#c76a2b",
    "ACCENT_PRESSED": "#8f4718",
    "DANGER":         "#c0392b",
    "DANGER_HOVER":   "#d4503f",
    "DANGER_PRESSED": "#9c2b1f",
    "BG_900":         "#f7f7fa",
    "BG_800":         "#eeeef4",
    "BG_700":         "#e4e4ec",
    "LINE":           "#d8d8e2",
    "LINE_STRONG":    "#c2c2d0",
    "TEXT":           "#1a1a24",
    "MUTED":          "#5f6676",
    "PANEL_BG":       (247, 247, 250, 242),
    "PANEL_BORDER":   (176, 89, 31, 90),
}

# Dark is the default so that importing this module never depends on a live
# QApplication - use_scheme() replaces these once one exists.
ACCENT = ACCENT_HOVER = ACCENT_PRESSED = ""
DANGER = DANGER_HOVER = DANGER_PRESSED = ""
BG_900 = BG_800 = BG_700 = LINE = LINE_STRONG = TEXT = MUTED = ""
PANEL_BG = PANEL_BORDER = ()
is_light = False


def use_scheme(light: bool) -> None:
    """Swap the module's tokens to one palette or the other.

    Must be called before any widget is constructed: consumers read these
    through the module (`theme.ACCENT`) rather than binding them at import,
    but a widget already built has its stylesheet string baked in. That is
    also why there is no live switching when the OS theme changes mid-run -
    restyling every existing widget is a different and much larger job than
    picking a palette at startup, and the failure mode of getting it wrong
    is a half-recoloured window.
    """
    global ACCENT, ACCENT_HOVER, ACCENT_PRESSED
    global DANGER, DANGER_HOVER, DANGER_PRESSED
    global BG_900, BG_800, BG_700, LINE, LINE_STRONG, TEXT, MUTED
    global PANEL_BG, PANEL_BORDER, is_light

    palette = _LIGHT if light else _DARK
    globals().update(palette)
    is_light = light


use_scheme(light=False)


def editor_style() -> str:
    """The application stylesheet, built from whichever palette is active.

    A function rather than a module constant because the palette is not
    known until a QApplication exists to be asked what the OS is set to.
    """
    return f"""
QMainWindow, QDialog {{
    background-color: {BG_900};
}}
QWidget {{
    background-color: {BG_900};
    color: {TEXT};
    font-family: {UI_FONT_CSS};
    font-size: 13px;
}}
QDockWidget::title {{
    background-color: {BG_800};
    color: {ACCENT};
    padding: 8px 12px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.2px;
    border-bottom: 1px solid {LINE};
}}
QDockWidget {{
    border: 1px solid {LINE};
}}
QPushButton {{
    background-color: {BG_700};
    color: {MUTED};
    border: 1px solid {LINE_STRONG};
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
    background-color: rgba(124, 131, 253, 0.08);
}}
QPushButton:pressed {{
    background-color: rgba(124, 131, 253, 0.18);
}}
QPushButton:checked {{
    border-color: {ACCENT};
    color: {ACCENT};
    background-color: rgba(124, 131, 253, 0.12);
}}
QPushButton:disabled {{
    /* LINE_STRONG is a border token, not a text colour - against BG_900 it
    measured 1.79:1, well under WCAG's 3:1 floor for large text/icons.
    MUTED is the token already used for regular body text and gives 6.14:1. */
    color: {MUTED};
    border-color: {LINE};
    background-color: {BG_900};
}}
QPushButton#btn_primary {{
    background-color: {ACCENT};
    color: #ffffff;
    border-color: {ACCENT};
}}
QPushButton#btn_primary:hover {{
    /* #9098fe (a bigger lighten) dropped white text to 2.59:1, below the
    3:1 floor - found by the contrast test added for item 3, not reported
    separately. This lighten is smaller specifically to stay above it. */
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
    color: #ffffff;
}}
QPushButton#btn_danger {{
    background-color: {DANGER};
    color: #ffffff;
    border-color: {DANGER};
}}
QPushButton#btn_danger:hover {{
    background-color: {DANGER_HOVER};
    border-color: {DANGER_HOVER};
    color: #ffffff;
}}
QPushButton#btn_help {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 14px;
    padding: 0;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton[smallIconButton="true"] {{
    /* The global QPushButton rule's 7px/14px padding leaves nowhere for a
    glyph to draw once a button is fixed-size and small - e.g. 24-28px
    square. #btn_help worked only because its own rule happens to set
    padding: 0, which was an accident, not a pattern; every small icon
    button now opts into this one shared rule via a dynamic property
    instead of needing its own #id override. */
    padding: 0;
    font-size: 12px;
}}
QPushButton#btn_help:hover {{
    background-color: {ACCENT_HOVER};
    color: #ffffff;
    border: none;
}}
QSlider::groove:horizontal {{
    background: {LINE};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    border: none;
    border-radius: 7px;
    width: 14px;
    height: 14px;
    margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QLabel {{
    color: {MUTED};
    font-size: 11px;
    background: transparent;
}}
QLabel#section_title {{
    color: {ACCENT};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.2px;
}}
QScrollBar:vertical {{
    background: {BG_900};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {LINE};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {LINE_STRONG};
}}
QScrollBar:horizontal {{
    background: {BG_900};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {LINE};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QSplitter::handle {{
    background: {LINE};
    width: 1px;
    height: 1px;
}}
QInputDialog QTextEdit,
QInputDialog QLineEdit,
QInputDialog QPlainTextEdit {{
    background: {BG_900};
    border: 1px solid {LINE_STRONG};
    border-radius: 6px;
    color: {TEXT};
    padding: 6px;
}}
QInputDialog QLabel {{
    color: {TEXT};
    font-size: 13px;
}}
QInputDialog QPushButton {{
    min-width: 80px;
}}
QMenu {{
    background: {BG_800};
    border: 1px solid {LINE_STRONG};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
    color: {TEXT};
}}
QMenu::item:selected {{
    background-color: rgba(124, 131, 253, 0.12);
    color: {ACCENT};
}}
QToolTip {{
    background: {BG_800};
    color: {TEXT};
    border: 1px solid {LINE_STRONG};
    border-radius: 6px;
    padding: 4px 8px;
}}
QMessageBox {{
    background: {BG_800};
}}
QMessageBox QLabel {{
    color: {TEXT};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}
"""
