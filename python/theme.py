"""Colour tokens and Qt stylesheet for Test Assist (PySide6 edition)."""

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
    font-family: 'Segoe UI', Arial, sans-serif;
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
    color: {LINE_STRONG};
    border-color: {LINE};
    background-color: {BG_900};
}}
QPushButton#btn_primary {{
    background-color: {ACCENT};
    color: #ffffff;
    border-color: {ACCENT};
}}
QPushButton#btn_primary:hover {{
    background-color: #9098fe;
    border-color: #9098fe;
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
