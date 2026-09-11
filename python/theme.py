"""Colour tokens, fonts and Qt stylesheet for Test Assist (PySide6 edition)."""

import sys

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QIcon

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
/* A button carrying both an icon and a label. Qt centres the icon+text
   pair as one group, so in a column of buttons whose labels differ in
   length - Undo, Delete Selected, Bring to Front - every icon lands at a
   different x and the column reads as ragged. Left-aligning pins the
   icons to one edge, and since they are all the same size the labels line
   up behind them too.

   Qt has no selector for "has an icon", so this is opted into with a
   dynamic property rather than applied to every QPushButton: a short
   text-only button like Copy or Fit still looks right centred. */
QPushButton[iconLabel="true"] {{
    text-align: left;
    padding-left: 12px;
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

# ── Icons ────────────────────────────────────────────────────────────────────
#
# Material Icons (Apache-2.0, see assets/MaterialIcons-LICENSE.txt) as a font
# rather than image assets.
#
# The editor previously used emoji characters as button labels. Emoji render
# through the platform's colour-emoji font, which is a *bitmap* face: it
# pixelates at any size the bitmaps were not cut for, and - the reason this
# mattered once there were two palettes - it ignores the stylesheet `color`
# entirely, because each glyph carries its own. Light mode therefore turned
# the chrome pale while the icons stayed exactly as they were, which is the
# "light on light" everyone could see and nobody could fix by editing a
# colour.
#
# A font fixes both at once: glyphs are outlines, so they are crisp at every
# size, and they take the colour of the text they are, so they follow the
# palette for free and will keep doing so for any palette added later.
# Codepoints rather than the font's ligature names ("home"), which depend on
# ligature shaping being on and fail silently to tofu when it is not.

ICON_FONT_FAMILY = ""

ICONS = {
    "open":        "\ue2c8",  # folder_open
    "updates":     "\ue5d5",  # refresh
    "home":        "\ue88a",  # home
    "about":       "\ue88e",  # info
    "help":        "\ue887",  # help
    "save":        "\ue161",  # save
    "copy":        "\ue14d",  # content_copy
    "export":      "\ue2c4",  # file_download
    "undo":        "\ue166",  # undo
    "redo":        "\ue15a",  # redo
    "delete":      "\ue872",  # delete
    "to_front":    "\ue883",  # flip_to_front
    "backward":    "\ue5db",  # arrow_downward
    "to_back":     "\ue882",  # flip_to_back
    "clear":       "\ue872",  # delete
    "zoom_in":     "\ue145",  # add
    "zoom_out":    "\ue15b",  # remove
    "select":      "\ue323",  # mouse
    "crop":        "\ue3be",  # crop
    "blur":        "\ue3a5",  # blur_on
    "text":        "\ue262",  # text_fields
    "highlight":   "\ue3ae",  # brush
    "circle":      "\ue836",  # radio_button_unchecked
    "arrow":       "\ue5c8",  # arrow_forward
    "rect":        "\ue835",  # check_box_outline_blank
    "pen":         "\ue3c9",  # edit
    # Launcher chrome
    "close":       "\ue5cd",  # close
    "minimise":    "\ue931",  # minimize
    "fullscreen":  "\ue30c",  # desktop_windows
    "expand":      "\ue5d0",  # fullscreen
    "region":      "\ue3be",  # crop
    "record":      "\ue061",  # fiber_manual_record
    "camera":      "\ue412",  # photo_camera
    "video":       "\ue04b",  # videocam
    "history":     "\ue889",  # history
    "dock":        "\uef6f",  # push_pin
    "stop":        "\ue047",  # stop
}


def load_icon_font(path) -> str:
    """Register the icon font and return its family name.

    Needs a live QApplication, so it is called at startup rather than on
    import. Returns "" if the font cannot be loaded - callers then fall back
    to a text label, because an icon-only button showing tofu is worse than
    a word.
    """
    global ICON_FONT_FAMILY
    from PySide6.QtGui import QFontDatabase

    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:
        return ""
    families = QFontDatabase.applicationFontFamilies(font_id)
    ICON_FONT_FAMILY = families[0] if families else ""
    return ICON_FONT_FAMILY


def icon_font(pixel_size: int) -> QFont:
    """The icon face at a given size, in pixels rather than points: these are
    glyphs sized to a box, not text sized to a reading measure."""
    font = QFont(ICON_FONT_FAMILY)
    font.setPixelSize(pixel_size)
    return font


def icon(name: str) -> str:
    """The character for an icon, or "" when the font is unavailable."""
    return ICONS.get(name, "") if ICON_FONT_FAMILY else ""


def icon_pixmap(name: str, pixel_size: int = 18, colour: str | None = None) -> QIcon:
    """One icon glyph rendered into a QIcon, tinted.

    setIcon() rather than putting the glyph in the button's text, because a
    button like "Save PNG" needs the label in the UI face and the mark in
    the icon face, and a widget has only one font. Rendering also makes the
    colour explicit: passing the palette's TEXT is what keeps these
    following light and dark, which is the whole reason for moving off
    emoji.

    Rendered at exactly the device resolution and tagged with the ratio, so
    Qt blits it 1:1. Both halves of that matter and a previous version got
    both wrong: it drew the glyph at 3x and then scaled the pixmap down,
    which is a resample - the softness everyone could see - and it produced
    an untagged pixmap sized in logical pixels, which a HiDPI screen then
    had to scale *up* again to fill the same button. Two resamples for a
    glyph that is an outline and could simply have been drawn at the size
    actually needed.

    Returns an empty QIcon when the font is unavailable, which QPushButton
    draws as no icon at all - so a button falls back to its text label
    rather than to tofu.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap

    glyph = icon(name)
    if not glyph:
        return QIcon()

    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0

    pixmap = QPixmap(round(pixel_size * ratio), round(pixel_size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(ratio)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    # Font size in logical pixels: the painter is already scaled by the
    # pixmap's ratio, so asking for the device size here would draw the
    # glyph at ratio-squared.
    painter.setFont(icon_font(pixel_size))
    painter.setPen(QColor(colour or TEXT))
    painter.drawText(
        QRectF(0, 0, pixel_size, pixel_size),
        Qt.AlignmentFlag.AlignCenter,
        glyph,
    )
    painter.end()
    return QIcon(pixmap)
