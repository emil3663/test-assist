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

# Colour tokens
ACCENT      = "#7c83fd"
DANGER      = "#e94560"
BG_900      = "#0d0d1a"
BG_800      = "#13132a"
BG_700      = "#1a1b35"
LINE        = "#2a2a4e"
LINE_STRONG = "#3a3a5e"
TEXT        = "#e0e6f0"
MUTED       = "#8892a4"

# Applied to the editor QApplication so all Qt widgets inherit the dark look.
EDITOR_STYLE = f"""
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
    background-color: #7f86fd;
    border-color: #7f86fd;
    color: #ffffff;
}}
QPushButton#btn_danger {{
    background-color: {DANGER};
    color: #ffffff;
    border-color: {DANGER};
}}
QPushButton#btn_danger:hover {{
    background-color: #ef6070;
    border-color: #ef6070;
    color: #ffffff;
}}
QPushButton#btn_help {{
    background-color: #1a6fc4;
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
    background-color: #2585e0;
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
