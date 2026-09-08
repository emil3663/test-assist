"""Diagnostic: does event.position() map linearly to global coordinates
across a mixed-DPI multi-monitor overlay?

Run it, then drag a small box on EACH screen in turn. Press Esc to quit.
For every drag it prints what the two coordinate sources say.
If position()+origin disagrees with globalPosition(), that is the bug.
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QRubberBand
from PySide6.QtCore import QRect, QSize


class Probe(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._origin_local = QPoint()
        self._origin_global = QPoint()

    def activate(self):
        virt = QApplication.primaryScreen().availableVirtualGeometry()
        print(f"\nrequested overlay geometry : {virt.getRect()}")
        self.setGeometry(virt)
        self.showFullScreen()
        print(f"ACTUAL geometry after show : {self.geometry().getRect()}")
        print(f"window devicePixelRatio    : {self.devicePixelRatioF()}")
        print("\nDrag a box on each screen in turn. Esc to quit.\n")

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))
        p.end()

    def mousePressEvent(self, e):
        self._origin_local = e.position().toPoint()
        self._origin_global = e.globalPosition().toPoint()
        self._band.setGeometry(QRect(self._origin_local, QSize()))
        self._band.show()

    def mouseMoveEvent(self, e):
        self._band.setGeometry(
            QRect(self._origin_local, e.position().toPoint()).normalized())

    def mouseReleaseEvent(self, e):
        self._band.hide()
        local_rect = QRect(self._origin_local, e.position().toPoint()).normalized()
        global_rect = QRect(self._origin_global, e.globalPosition().toPoint()).normalized()
        origin = self.geometry().topLeft()
        derived = local_rect.translated(origin)          # what the app computes
        screen = QApplication.screenAt(global_rect.center())

        print("-" * 66)
        print(f"  local  position()          : {local_rect.getRect()}")
        print(f"  derived (local + origin)   : {derived.getRect()}   <-- app uses this")
        print(f"  true    globalPosition()   : {global_rect.getRect()}   <-- truth")
        dx = derived.x() - global_rect.x()
        dy = derived.y() - global_rect.y()
        print(f"  ERROR                      : dx={dx}  dy={dy}"
              f"{'   <<< MISMATCH' if (dx or dy) else '   (agree)'}")
        print(f"  screen under selection     : {screen.name() if screen else 'NONE'}"
              f"  dpr={screen.devicePixelRatio() if screen else '-'}")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            QApplication.quit()


app = QApplication([])
w = Probe()
w.activate()
app.exec()
