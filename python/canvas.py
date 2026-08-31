"""Annotation canvas widget for Test Assist (PySide6 edition)."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QInputDialog, QWidget


# ─────────────────────────────────────────────────────────────────────────────
# AnnotationCanvas
# ─────────────────────────────────────────────────────────────────────────────

class AnnotationCanvas(QWidget):
    """
    Renders a base QPixmap with annotation overlays drawn by the user.

    Supported tools
    ---------------
    select    – click to pick an annotation, drag to reposition it
    highlight – semi-transparent filled rectangle
    text      – inline text label placed at click position
    circle    – ellipse
    arrow     – line with arrowhead
    rect      – outline rectangle
    blur      – blur (pixelate) a rectangular region
    crop      – crop the canvas to a dragged rectangle
    pen       – freehand stroke

    Signals
    -------
    annotation_changed()  – emitted whenever annotations are modified.
    """

    annotation_changed = Signal()
    text_editing_changed = Signal(bool)
    selection_changed = Signal(bool)

    # Handle sizes are expressed in SCREEN pixels and divided by the zoom when
    # used, so a handle stays the same size to the hand at any zoom level.
    _HANDLE_SCREEN_RADIUS = 5.0     # what gets drawn
    _GRAB_SCREEN_RADIUS   = 8.0     # what can be grabbed
    _DRAG_SCREEN_THRESHOLD = 4.0    # movement before a press becomes a drag
    _DBLCLICK_SCREEN_SLOP  = 10.0   # a "drag" this small before a double-click
                                    # is hand wobble, not an intended move

    _CURSOR_FOR_HANDLE = {
        "tl": Qt.CursorShape.SizeFDiagCursor,
        "br": Qt.CursorShape.SizeFDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor,
        "bl": Qt.CursorShape.SizeBDiagCursor,
        "l":  Qt.CursorShape.SizeHorCursor,
        "r":  Qt.CursorShape.SizeHorCursor,
        "t":  Qt.CursorShape.SizeVerCursor,
        "b":  Qt.CursorShape.SizeVerCursor,
        "start": Qt.CursorShape.SizeAllCursor,
        "end":   Qt.CursorShape.SizeAllCursor,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._pixmap:      QPixmap | None        = None
        self._annotations: list[dict[str, Any]]  = []
        self._undo_stack:  list[list]            = []
        self._redo_stack:  list[list]            = []
        self._next_z:      int                   = 0
        self._next_text_id: int                  = 1
        self._zoom:        float                 = 1.0

        # Active tool settings
        self.tool:         str   = "select"
        self.color:        str   = "#ff3b30"
        self.stroke_size:  int   = 3
        self.fill_opacity: float = 0.30
        self.arrow_style:  str   = "classic"

        # Drawing state
        self._drawing     = False
        self._start       = QPointF()
        self._current     = QPointF()
        self._pen_path:   list[QPointF] = []

        # Select / drag state  (selection persists after mouse release)
        self.__selected: dict | None = None
        self._dragging       = False
        self._drag_moved     = False
        self._drag_started   = False
        self._drag_last_pos  = QPointF()
        self._drag_origin: dict[str, Any] | None = None   # pre-drag geometry
        self._last_drag: dict[str, Any] | None = None     # for double-click undo
        self._resize_handle  = None  # arrows: "start"/"end"; boxes: tl/t/tr/l/r/bl/b/br
        self._hover_cursor   = Qt.CursorShape.ArrowCursor

        # Inline text editing state
        self._text_editing   = False
        self._text_pos       = QPointF()
        self._text_buffer    = ""
        self._text_width     = 100  # Width of the text box
        self._text_height    = 24   # Height of the text box
        self._text_resize_handle: str | None = None
        self._text_resize_start = QPointF()
        self._text_box_start = (0.0, 0.0, 100.0, 24.0)  # x, y, width, height
        self._cursor_visible = True
        self._cursor_timer   = QTimer(self)
        self._cursor_timer.setInterval(530)
        self._cursor_timer.timeout.connect(self._blink_cursor)

        self.setMouseTracking(True)
        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    # ── Public API ───────────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QPixmap) -> None:
        """Load a new base image and discard any existing annotations."""
        self._pixmap = pixmap
        self._sync_widget_size()
        self.clear_annotations(push_undo=False)
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.25, min(4.0, float(zoom)))
        self._sync_widget_size()
        self.update()

    def fit_to_size(self, viewport_size: QSize) -> None:
        """Set zoom so the image fits inside the provided viewport size."""
        if not self._pixmap or viewport_size.width() <= 0 or viewport_size.height() <= 0:
            return
        scale_x = viewport_size.width() / max(1, self._pixmap.width())
        scale_y = viewport_size.height() / max(1, self._pixmap.height())
        self.set_zoom(min(scale_x, scale_y))

    # ── Selection state ──────────────────────────────────────────────────────
    # A property rather than a plain attribute so that every assignment, from
    # anywhere, reports the change. The editor uses it to enable and disable the
    # Delete Selected and layer buttons.

    @property
    def _selected(self) -> dict | None:
        return self.__selected

    @_selected.setter
    def _selected(self, value: dict | None) -> None:
        if value is self.__selected:
            return
        self.__selected = value
        self.selection_changed.emit(value is not None)

    def has_selection(self) -> bool:
        return self.__selected is not None

    # ── Zoom-independent handle geometry ─────────────────────────────────────

    def _handle_radius(self) -> float:
        """Drawn handle radius in image space, so it is constant on screen."""
        return self._HANDLE_SCREEN_RADIUS / max(self._zoom, 0.05)

    def _grab_radius(self) -> float:
        """Grab radius in image space, so it is constant on screen."""
        return self._GRAB_SCREEN_RADIUS / max(self._zoom, 0.05)

    def _hit_tolerance(self) -> float:
        """How close a click must be to a shape's outline to count as on it."""
        return max(4.0, self._grab_radius())

    def _handle_points(self, anno: dict[str, Any]) -> dict[str, QPointF]:
        """Every grabbable handle for an annotation, keyed by name.

        Corners resize both axes; edge midpoints resize one. Arrows have two
        endpoints instead, and pen strokes have none — a freehand path has no
        meaningful box to stretch.
        """
        t = anno.get("type")
        if t == "arrow":
            return {
                "start": QPointF(anno["x1"], anno["y1"]),
                "end":   QPointF(anno["x2"], anno["y2"]),
            }
        if t == "text":
            left   = anno["x1"] - 4
            top    = anno["y1"] - 4
            right  = anno["x1"] + anno.get("width", 100) + 4
            bottom = anno["y1"] + anno.get("height", 24) + 4
        elif t in ("rect", "highlight", "circle", "blur"):
            left, right = sorted((anno["x1"], anno["x2"]))
            top, bottom = sorted((anno["y1"], anno["y2"]))
        else:
            return {}

        return self._box_handle_points(left, top, right, bottom)

    @staticmethod
    def _box_handle_points(left, top, right, bottom) -> dict[str, QPointF]:
        mid_x = (left + right) / 2
        mid_y = (top + bottom) / 2
        return {
            "tl": QPointF(left,  top),    "t": QPointF(mid_x, top),
            "tr": QPointF(right, top),    "l": QPointF(left,  mid_y),
            "r":  QPointF(right, mid_y),  "bl": QPointF(left, bottom),
            "b":  QPointF(mid_x, bottom), "br": QPointF(right, bottom),
        }

    def has_image(self) -> bool:
        return self._pixmap is not None

    def clear_annotations(self, push_undo: bool = True) -> None:
        if push_undo and self._annotations:
            self._undo_stack.append(self._clone_annotations())
        self._annotations = []
        self._redo_stack  = []
        self._selected    = None
        self._next_z      = 0
        self._next_text_id = 1
        self._cancel_text()
        self.update()
        self.annotation_changed.emit()

    def undo(self) -> None:
        self._commit_text()
        if self._undo_stack:
            self._redo_stack.append(self._capture_document_state())
            state = self._undo_stack.pop()
            if self._is_document_state(state):
                self._restore_document_state(state)
            else:
                self._annotations = state
                self._selected = None
                self._recalculate_next_z()
                self._recalculate_next_text_id()
            self.update()
            self.annotation_changed.emit()

    def redo(self) -> None:
        self._commit_text()
        if self._redo_stack:
            self._undo_stack.append(self._capture_document_state())
            state = self._redo_stack.pop()
            if self._is_document_state(state):
                self._restore_document_state(state)
            else:
                self._annotations = state
                self._selected = None
                self._recalculate_next_z()
                self._recalculate_next_text_id()
            self.update()
            self.annotation_changed.emit()

    def delete_selected(self) -> None:
        """Remove the currently selected annotation. Also triggered by Delete key."""
        if self._selected is not None and self._selected in self._annotations:
            self._undo_stack.append(self._clone_annotations())
            self._annotations.remove(self._selected)
            self._selected   = None
            self._redo_stack = []
            self.update()
            self.annotation_changed.emit()

    def bring_selected_to_front(self) -> None:
        """Move the selected annotation above all others."""
        if self._selected is None or self._selected not in self._annotations:
            return
        current_top = max((anno.get("z", 0) for anno in self._annotations), default=0)
        if self._selected.get("z", 0) == current_top:
            return
        self._undo_stack.append(self._clone_annotations())
        self._selected["z"] = current_top + 1
        self._redo_stack = []
        self._normalise_z_order()
        self.update()
        self.annotation_changed.emit()

    def send_selected_backward(self) -> None:
        """Move the selected annotation one layer backward."""
        if self._selected is None or self._selected not in self._annotations:
            return
        ordered = sorted(self._annotations, key=lambda item: item.get("z", 0))
        index = ordered.index(self._selected)
        if index == 0:
            return
        self._undo_stack.append(self._clone_annotations())
        previous = ordered[index - 1]
        self._selected["z"], previous["z"] = previous.get("z", 0), self._selected.get("z", 0)
        self._redo_stack = []
        self._normalise_z_order()
        self.update()
        self.annotation_changed.emit()

    def send_selected_to_back(self) -> None:
        """Move the selected annotation behind all others."""
        if self._selected is None or self._selected not in self._annotations:
            return
        current_bottom = min((anno.get("z", 0) for anno in self._annotations), default=0)
        if self._selected.get("z", 0) == current_bottom:
            return
        self._undo_stack.append(self._clone_annotations())
        self._selected["z"] = current_bottom - 1
        self._redo_stack = []
        self._normalise_z_order()
        self.update()
        self.annotation_changed.emit()

    def update_selected_style(
        self,
        color: str | None = None,
        size: int | None = None,
        opacity: float | None = None,
        arrow_style: str | None = None,
    ) -> None:
        """Apply style updates to the currently selected annotation, if any."""
        if self._selected is None or self._selected not in self._annotations:
            return

        changed = False
        anno = self._selected

        if color is not None and anno.get("type") in {
            "highlight", "text", "circle", "arrow", "rect", "pen"
        }:
            anno["color"] = color
            changed = True

        if size is not None and anno.get("type") in {
            "highlight", "text", "circle", "arrow", "rect", "pen", "blur"
        }:
            anno["size"] = max(1, int(size))
            changed = True

        if opacity is not None and anno.get("type") == "highlight":
            anno["opacity"] = max(0.0, min(1.0, float(opacity)))
            changed = True

        if arrow_style is not None and anno.get("type") == "arrow":
            anno["arrow_style"] = arrow_style
            changed = True

        if changed:
            self.update()
            self.annotation_changed.emit()

    def export_pixmap(self) -> QPixmap | None:
        """Composite the base image and all annotations into a single QPixmap."""
        if not self._pixmap:
            return None
        result  = QPixmap(self._pixmap.size())
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self._pixmap)
        self._paint_annotations(painter, export=True)
        painter.end()
        return result

    def serialisable_annotations(self) -> list[dict]:
        """Return a JSON-serialisable copy of the annotation list."""
        out = []
        for anno in self._annotations:
            a = {k: v for k, v in anno.items() if k != "path"}
            if "path" in anno:
                a["path"] = [{"x": p.x(), "y": p.y()} for p in anno["path"]]
            out.append(a)
        return out

    # ── Mouse events ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if not self._pixmap:
            return
        pos = self._to_canvas_pos(event.position())
        self.setFocus()

        if self._text_editing:
            handle = self._get_live_text_resize_handle(pos)
            if handle:
                self._text_resize_handle = handle
                self._text_resize_start = pos
                self._text_box_start = (
                    self._text_pos.x(),
                    self._text_pos.y(),
                    float(self._text_width),
                    float(self._text_height),
                )
                return
            self._commit_text()

        previous = self._selected

        if self.tool == "crop":
            self._selected = None
            self._resize_handle = None
            self._drawing = True
            self._start = pos
            self._current = pos
            self.update()
            return

        self._selected = None
        self._resize_handle = None
        self.update()

        if self.tool == "text":
            # Commit any in-progress text, then start a new one at clicked position
            self._commit_text()
            self._start_text_edit(pos)
            return

        if self.tool == "select":
            self._dragging = False

            # 1. A resize handle on the annotation that is already selected wins.
            #    Handles sit on the outline and reach outside the shape, so
            #    hit-testing first would either miss them or grab whatever sits
            #    underneath the corner.
            if previous is not None and previous in self._annotations:
                handle = self._get_resize_handle(previous, pos)
                if handle:
                    self._begin_selection_drag(previous, handle, pos)
                    self.update()
                    return

            # 2. A border under the cursor selects and arms a move or resize.
            hit = self._find_annotation(pos)
            if hit is not None:
                self._begin_selection_drag(hit, self._get_resize_handle(hit, pos), pos)
                self.update()
                return

            # 3. Inside a text box, a single click edits the words. The border is
            #    how you move or resize it; the inside is how you change it.
            text = self._find_text_at(pos)
            if text is not None:
                self._selected = text
                self.update()
                self._edit_text_annotation(text)
                return

            self.update()
            return

        self._drawing = True
        self._start   = pos
        self._current = pos
        if self.tool == "pen":
            self._pen_path = [pos]

    def mouseMoveEvent(self, event) -> None:
        pos = self._to_canvas_pos(event.position())

        if self._text_editing and self._text_resize_handle:
            dx = pos.x() - self._text_resize_start.x()
            dy = pos.y() - self._text_resize_start.y()
            x0, y0, w0, h0 = self._text_box_start
            min_w = 48.0
            min_h = 24.0
            handle = self._text_resize_handle

            new_x = x0
            new_y = y0
            new_w = w0
            new_h = h0

            if "l" in handle:
                new_x = x0 + dx
                new_w = w0 - dx
            if "r" in handle:
                new_w = w0 + dx
            if "t" in handle:
                new_y = y0 + dy
                new_h = h0 - dy
            if "b" in handle:
                new_h = h0 + dy

            if new_w < min_w:
                if "l" in handle:
                    new_x -= (min_w - new_w)
                new_w = min_w
            if new_h < min_h:
                if "t" in handle:
                    new_y -= (min_h - new_h)
                new_h = min_h

            self._text_pos = QPointF(new_x, new_y)
            self._text_width = int(round(new_w))
            self._text_height = int(round(new_h))
            self.update()
            return

        if not self._dragging and not self._drawing:
            self._update_hover_cursor(pos)

        if self._dragging and self._selected is not None:
            total_dx = pos.x() - self._start.x()
            total_dy = pos.y() - self._start.y()
            self._drag_last_pos = pos
            self._drag_moved    = True

            # Require a real drag before moving or resizing, so a click that
            # selects cannot also nudge. Measured in screen pixels so the
            # threshold feels the same at every zoom level.
            if not self._drag_started:
                threshold = self._DRAG_SCREEN_THRESHOLD / max(self._zoom, 0.05)
                if math.hypot(total_dx, total_dy) < threshold:
                    return
                # Past the threshold, so this is a real move or resize. Nothing
                # has been mutated yet, so snapshot the pre-drag geometry here.
                self._undo_stack.append(self._clone_annotations())
                self._redo_stack = []
                self._drag_started = True

            self._apply_drag(total_dx, total_dy, self._event_shift(event))
            self.update()
            return

        if self._drawing:
            self._current = pos
            if self.tool == "pen":
                self._pen_path.append(pos)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._text_editing and self._text_resize_handle:
            self._text_resize_handle = None
            return

        if self._dragging:
            changed = self._drag_started
            # Remember what this gesture did. If a double-click follows, the
            # press that started it was the first half of that double-click, and
            # any movement was hand wobble rather than an intended move.
            self._last_drag = {
                "anno":     self._selected,
                "origin":   self._drag_origin,
                "distance": math.hypot(
                    self._drag_last_pos.x() - self._start.x(),
                    self._drag_last_pos.y() - self._start.y(),
                ),
                "pushed":   changed,
            } if changed else None
            self._dragging = False
            self._drag_started = False
            self._resize_handle = None
            self._drag_origin = None
            # Keep _selected intact so Delete key still works
            if changed:
                self.update()
                self.annotation_changed.emit()
            return

        if not self._drawing:
            return
        self._drawing = False
        pos = self._to_canvas_pos(event.position())

        if self.tool == "pen":
            if len(self._pen_path) > 1:
                self._push({
                    "type":  "pen",
                    "path":  list(self._pen_path),
                    "color": self.color,
                    "size":  self.stroke_size,
                })
            return

        if self.tool == "crop":
            rect = QRectF(self._start, pos).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self._apply_crop(rect)
            return

        dx = pos.x() - self._start.x()
        dy = pos.y() - self._start.y()
        if abs(dx) < 3 and abs(dy) < 3:
            return  # ignore tiny accidental clicks

        self._push({
            "type":    self.tool,
            "x1":      self._start.x(),
            "y1":      self._start.y(),
            "x2":      pos.x(),
            "y2":      pos.y(),
            "color":   self.color,
            "size":    self.stroke_size,
            "opacity": self.fill_opacity,
            "arrow_style": self.arrow_style if self.tool == "arrow" else None,
        })

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click to select an annotation, or edit text annotations."""
        if not self._pixmap:
            return
        pos = self._to_canvas_pos(event.position())
        self._undo_double_click_wobble()
        hit = self._find_annotation(pos)

        # Select the hit annotation (works with any tool)
        if hit is not None:
            self._begin_selection_drag(hit, self._get_resize_handle(hit, pos), pos)
            self.update()

        if hit is None:
            hit = self._find_text_at(pos)
            if hit is not None:
                self._selected = hit
                self.update()

        if hit and hit.get("type") == "text":
            self._edit_text_annotation(hit)

    def _edit_text_annotation(self, anno: dict[str, Any]) -> None:
        """Open the editor for an existing text annotation."""
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Edit Text",
            "Update annotation text:",
            anno.get("text", ""),
        )
        if not ok:
            return
        new_text = text.rstrip()
        if new_text == anno.get("text", ""):
            return
        self._undo_stack.append(self._clone_annotations())
        anno["text"] = new_text
        self._redo_stack = []
        self.update()
        self.annotation_changed.emit()

    def keyPressEvent(self, event) -> None:
        key  = event.key()
        mods = event.modifiers()

        # ── Text editing mode ──────────────────────────────────────────────
        if self._text_editing:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if mods & Qt.KeyboardModifier.ControlModifier:
                    self._commit_text()          # Ctrl+Enter = commit
                else:
                    self._text_buffer += "\n"   # Enter = newline
            elif key == Qt.Key.Key_Escape:
                self._cancel_text()
            elif key == Qt.Key.Key_Backspace:
                self._text_buffer = self._text_buffer[:-1]
            else:
                text = event.text()
                if text and text.isprintable():
                    self._text_buffer += text
            self.update()
            return

        # ── Normal mode ────────────────────────────────────────────────────
        if key == Qt.Key.Key_Escape and self._cancel_drag():
            return

        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            return

        nudges = {
            Qt.Key.Key_Left:  (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up:    (0, -1),
            Qt.Key.Key_Down:  (0, 1),
        }
        if key in nudges and self._selected is not None:
            # Shift for a coarse step, matching the drawing tools people are
            # used to; the fine step is a single image pixel.
            step = 10 if mods & Qt.KeyboardModifier.ShiftModifier else 1
            dx, dy = nudges[key]
            if self.nudge_selected(dx * step, dy * step):
                return

        super().keyPressEvent(event)

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.save()
        p.scale(self._zoom, self._zoom)

        if self._pixmap:
            p.drawPixmap(0, 0, self._pixmap)
        else:
            p.fillRect(self.rect(), QColor("#0d0d1a"))

        self._paint_annotations(p)

        # Live preview while dragging a new shape
        if self._drawing and self.tool not in ("select", "text", "pen"):
            if self.tool == "crop":
                self._draw_crop_preview(p)
            else:
                self._draw_one(p, {
                    "type":    self.tool,
                    "x1":      self._start.x(),
                    "y1":      self._start.y(),
                    "x2":      self._current.x(),
                    "y2":      self._current.y(),
                    "color":   self.color,
                    "size":    self.stroke_size,
                    "opacity": self.fill_opacity,
                }, preview=True)
        elif self._drawing and self.tool == "pen" and len(self._pen_path) > 1:
            self._draw_one(p, {
                "type":  "pen",
                "path":  self._pen_path,
                "color": self.color,
                "size":  self.stroke_size,
            })

        # Inline text input preview
        if self._text_editing:
            self._draw_inline_text(p)

        p.restore()

        p.end()

    # ── Drawing primitives ───────────────────────────────────────────────────

    def _paint_annotations(self, painter: QPainter, export: bool = False) -> None:
        for anno in sorted(self._annotations, key=lambda item: item.get("z", 0)):
            is_sel = (not export) and (anno is self._selected)
            self._draw_one(painter, anno, selected=is_sel)

    def _draw_one(
        self,
        p: QPainter,
        a: dict[str, Any],
        preview: bool = False,
        selected: bool = False,
    ) -> None:
        p.save()
        color = QColor(a["color"])
        pen   = QPen(color, a.get("size", 3))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if preview:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)

        t = a["type"]

        if t == "pen":
            pts = a.get("path", [])
            if len(pts) >= 2:
                path = QPainterPath()
                path.moveTo(pts[0])
                for pt in pts[1:]:
                    path.lineTo(pt)
                p.drawPath(path)
            if selected:
                self._draw_pen_selection(p, pts)

        elif t == "text":
            font_size = max(14, a.get("size", 3) * 4)
            f = QFont("Segoe UI", font_size, QFont.Weight.Bold)
            p.setFont(f)
            p.setPen(QPen(color))
            
            x0 = a.get("x1", 0)
            y0 = a.get("y1", 0)
            w  = a.get("width", 100)
            h  = a.get("height", 24)
            text = a.get("text", "")
            line_h = font_size + 2

            fm = QFontMetricsF(f)
            lines = self._wrap_text_lines(text, fm, w - 8)
            
            # Draw a light grey text box border so the annotation remains visible as a layer.
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(198, 198, 198, 210), 1.2))
            p.drawRect(QRectF(x0 - 2, y0 - 2, w + 4, h))

            p.setPen(QPen(color))
            # Draw wrapped text
            for i, line in enumerate(lines):
                p.drawText(QPointF(x0 + 2, y0 + line_h * (i + 1)), line)

            # Superscript-like text id marker in the top-right corner.
            text_id = a.get("text_id")
            if text_id is not None:
                badge_font = QFont("Segoe UI", max(9, int(font_size * 0.55)), QFont.Weight.DemiBold)
                p.setFont(badge_font)
                p.setPen(QPen(QColor(215, 215, 215, 220)))
                p.drawText(QPointF(x0 + w - 10, y0 - 6), str(text_id))

                # Restore drawing font/pen for any subsequent text operations.
                p.setFont(f)
                p.setPen(QPen(color))
            
            if selected:
                rect = QRectF(x0 - 4, y0 - 4, w + 8, h + 8)
                self._draw_selection_rect(p, rect)
                self._draw_handles(p, a, color)

        elif t in ("highlight", "rect", "blur"):
            rect = QRectF(
                a["x1"], a["y1"],
                a["x2"] - a["x1"], a["y2"] - a["y1"],
            )
            if t == "highlight":
                fill = QColor(a["color"])
                fill.setAlphaF(a.get("opacity", 0.30))
                p.fillRect(rect, QBrush(fill))
                p.drawRect(rect)
            elif t == "rect":
                p.drawRect(rect)
            else:
                self._draw_blur_rect(p, rect, a.get("size", 3), selected)
            if selected:
                self._draw_selection_rect(p, rect.adjusted(-4, -4, 4, 4))
                self._draw_handles(p, a, color)

        elif t == "circle":
            rect = QRectF(
                a["x1"], a["y1"],
                a["x2"] - a["x1"], a["y2"] - a["y1"],
            )
            p.drawEllipse(rect)
            if selected:
                self._draw_selection_rect(p, rect.adjusted(-4, -4, 4, 4))
                self._draw_handles(p, a, color)

        elif t == "arrow":
            x1, y1, x2, y2 = a["x1"], a["y1"], a["x2"], a["y2"]
            arrow_style = a.get("arrow_style") or "classic"
            if arrow_style == "dashed":
                pen.setStyle(Qt.PenStyle.DashLine)
                p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            head  = max(14, a.get("size", 3) * 3)
            angle = math.atan2(y2 - y1, x2 - x1)
            for sign in (+1, -1):
                tip = QPointF(
                    x2 - head * math.cos(angle - sign * math.pi / 6),
                    y2 - head * math.sin(angle - sign * math.pi / 6),
                )
                p.drawLine(QPointF(x2, y2), tip)

            if arrow_style == "double":
                angle2 = math.atan2(y1 - y2, x1 - x2)
                for sign in (+1, -1):
                    tail = QPointF(
                        x1 - head * math.cos(angle2 - sign * math.pi / 6),
                        y1 - head * math.sin(angle2 - sign * math.pi / 6),
                    )
                    p.drawLine(QPointF(x1, y1), tail)
            if selected:
                bx = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                self._draw_selection_rect(
                    p, QRectF(bx[0] - 4, bx[1] - 4, bx[2] - bx[0] + 8, bx[3] - bx[1] + 8)
                )
                self._draw_handles(p, a, color)

        p.restore()

    def _draw_handles(self, p: QPainter, anno: dict[str, Any], color: QColor) -> None:
        """Draw every grabbable handle at a constant on-screen size.

        The radius is divided by the zoom because the painter is already scaled
        by it. Without that, handles shrink to nothing when you zoom out to see
        a whole screenshot — exactly when you most need to grab one.
        """
        radius = self._handle_radius()
        p.save()
        p.setBrush(QBrush(QColor(255, 255, 255, 230)))
        p.setPen(QPen(color, max(1.0, 1.5 / max(self._zoom, 0.05))))
        for name, point in self._handle_points(anno).items():
            # Edge handles are drawn slightly smaller so a corner still reads as
            # the primary grip.
            scale = 1.0 if name in ("tl", "tr", "bl", "br", "start", "end") else 0.8
            p.drawEllipse(point, radius * scale, radius * scale)
        p.restore()

    def _draw_selection_rect(self, p: QPainter, rect: QRectF) -> None:
        """Dashed white + dark outline around the selected annotation."""
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        # dark shadow (drawn slightly larger for contrast)
        p.setPen(QPen(QColor(0, 0, 0, 140), 2.5, Qt.PenStyle.DashLine))
        p.drawRect(rect.adjusted(-1, -1, 1, 1))
        # bright white dash on top
        p.setPen(QPen(QColor(255, 255, 255, 220), 1.5, Qt.PenStyle.DashLine))
        p.drawRect(rect)
        p.restore()

    def _draw_crop_preview(self, p: QPainter) -> None:
        """Visual guide for crop selection rectangle while dragging."""
        rect = QRectF(self._start, self._current).normalized()
        if rect.width() <= 0 or rect.height() <= 0:
            return
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 210, 170, 220), 1.6, Qt.PenStyle.DashLine))
        p.drawRect(rect)
        p.restore()

    def _draw_blur_rect(self, p: QPainter, rect: QRectF, strength: int, selected: bool) -> None:
        """Draw a semi-opaque redaction overlay over the rectangle region."""
        # strength 1-10 maps to alpha 160-255
        alpha = min(255, 160 + (strength - 1) * 10)
        fill = QColor(0, 0, 0, alpha)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawRect(rect)
        p.restore()

    def _apply_crop(self, rect: QRectF) -> None:
        """Crop current canvas content (base image + annotations) to rect."""
        if not self._pixmap:
            return
        composed = self.export_pixmap()
        if composed is None:
            return

        self._undo_stack.append(self._capture_document_state())
        self._redo_stack = []

        x = max(0, int(rect.x()))
        y = max(0, int(rect.y()))
        w = int(rect.width())
        h = int(rect.height())

        max_w = composed.width() - x
        max_h = composed.height() - y
        w = max(1, min(w, max_w))
        h = max(1, min(h, max_h))

        cropped = composed.copy(x, y, w, h)
        self.set_pixmap(cropped)
        self.annotation_changed.emit()

    def _draw_pen_selection(self, p: QPainter, pts: list[QPointF]) -> None:
        if not pts:
            return
        xs   = [pt.x() for pt in pts]
        ys   = [pt.y() for pt in pts]
        rect = QRectF(min(xs) - 4, min(ys) - 4, max(xs) - min(xs) + 8, max(ys) - min(ys) + 8)
        self._draw_selection_rect(p, rect)

    def _draw_inline_text(self, p: QPainter) -> None:
        """Render the text buffer on a resizable box while the user is typing."""
        font_size = max(14, self.stroke_size * 4)
        f  = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        fm = QFontMetricsF(f)
        p.setFont(f)

        x0     = self._text_pos.x()
        y0     = self._text_pos.y()
        w      = self._text_width
        h      = self._text_height
        line_h = font_size + 2

        # Wrap text to fit within box width
        lines = self._wrap_text_lines(self._text_buffer, fm, w - 8)
        
        # Update height based on number of lines
        needed_height = line_h * max(1, len(lines)) + 6
        if needed_height > h:
            h = self._text_height = needed_height

        # Semi-transparent dark background
        bg = QColor(0, 0, 0, 120)
        p.fillRect(QRectF(x0 - 4, y0 - 4, w + 8, h + 4), bg)

        # Draw text lines
        color = QColor(self.color)
        p.setPen(QPen(color))
        for i, line in enumerate(lines):
            p.drawText(QPointF(x0 + 2, y0 + line_h * (i + 1)), line)

        # Blinking cursor
        if self._cursor_visible and lines:
            last_line = lines[-1]
            cx        = x0 + 2 + fm.horizontalAdvance(last_line)
            cy_top    = y0 + line_h * (len(lines) - 1) + 4
            cy_bot    = cy_top + font_size
            p.setPen(QPen(color, 2.0))
            p.drawLine(QPointF(cx, cy_top), QPointF(cx, cy_bot))

        # Border with corner handles
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(198, 198, 198, 220), 1.2))
        p.drawRect(QRectF(x0 - 4, y0 - 4, w + 8, h + 4))
        
        # Resize handles, at a constant on-screen size
        radius = self._handle_radius()
        p.setBrush(QBrush(QColor(255, 255, 255, 230)))
        p.setPen(QPen(color, max(1.0, 1.5 / max(self._zoom, 0.05))))
        points = self._box_handle_points(x0 - 4, y0 - 4, x0 + w + 4, y0 + h + 4)
        for name, point in points.items():
            scale = 1.0 if name in ("tl", "tr", "bl", "br") else 0.8
            p.drawEllipse(point, radius * scale, radius * scale)

    # ── Text editing helpers ──────────────────────────────────────────────────

    def _start_text_edit(self, pos: QPointF) -> None:
        """Start inline text editing at the given position with initial width for ~10 chars."""
        font_size = max(14, self.stroke_size * 4)
        f  = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        fm = QFontMetricsF(f)
        # Initial width for approximately 10 characters
        char_width = fm.horizontalAdvance("M")  # Average char width
        initial_width = char_width * 10
        
        self._text_pos       = pos
        self._text_buffer    = ""
        self._text_width     = initial_width
        self._text_height    = font_size + 6  # Height of one line
        self._text_editing   = True
        self._cursor_visible = True
        self._cursor_timer.start()
        self.text_editing_changed.emit(True)
        self.update()

    @staticmethod
    def _wrap_text_lines(text: str, fm: QFontMetricsF, max_width: float) -> list[str]:
        """Wrap text while preserving explicit newlines and blank lines."""
        max_width = max(12.0, max_width)
        if not text:
            return [""]

        lines: list[str] = []
        for paragraph in text.split("\n"):
            if paragraph == "":
                lines.append("")
                continue

            words = paragraph.split(" ")
            current = ""
            for word in words:
                token = word if current == "" else f" {word}"
                candidate = f"{current}{token}" if current else word
                if current and fm.horizontalAdvance(candidate) > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        return lines if lines else [""]

    def _get_live_text_resize_handle(self, pos: QPointF) -> str | None:
        """Detect resize-handle hit while editing inline text."""
        x0 = self._text_pos.x()
        y0 = self._text_pos.y()
        w = self._text_width
        h = self._text_height
        radius = self._grab_radius()
        points = self._box_handle_points(x0 - 4, y0 - 4, x0 + w + 4, y0 + h + 4)
        for group in (("tl", "tr", "bl", "br"), ("t", "b", "l", "r")):
            best, best_distance = None, radius
            for name in group:
                point = points[name]
                distance = math.hypot(pos.x() - point.x(), pos.y() - point.y())
                if distance < best_distance:
                    best, best_distance = name, distance
            if best is not None:
                return best
        return None

    def _commit_text(self) -> None:
        if not self._text_editing:
            return
        text = self._text_buffer.strip()
        self._text_editing = False
        self._cursor_timer.stop()
        self.text_editing_changed.emit(False)
        self._text_buffer  = ""
        if text:
            text_id = self._next_text_id
            self._next_text_id += 1
            self._push({
                "type":  "text",
                "x1":    self._text_pos.x(),
                "y1":    self._text_pos.y(),
                "color": self.color,
                "size":  self.stroke_size,
                "text":  text,
                "width": self._text_width,
                "height": self._text_height,
                "text_id": text_id,
            })
        else:
            self.update()

    def _cancel_text(self) -> None:
        self._text_editing = False
        self._text_buffer  = ""
        self._cursor_timer.stop()
        self.text_editing_changed.emit(False)
        self.update()

    def _blink_cursor(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self.update()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _push(self, anno: dict[str, Any]) -> None:
        anno.setdefault("z", self._next_z)
        self._next_z = max(self._next_z, anno["z"] + 1)
        self._undo_stack.append(self._clone_annotations())
        self._annotations.append(anno)
        self._redo_stack = []
        self.update()
        self.annotation_changed.emit()

    def _clone_annotations(self) -> list[dict[str, Any]]:
        return deepcopy(self._annotations)

    def _capture_document_state(self) -> dict[str, Any]:
        return {
            "pixmap": self._pixmap.copy() if self._pixmap is not None else None,
            "annotations": self._clone_annotations(),
            "next_z": self._next_z,
            "next_text_id": self._next_text_id,
        }

    @staticmethod
    def _is_document_state(state: Any) -> bool:
        return isinstance(state, dict) and "pixmap" in state and "annotations" in state

    def _restore_document_state(self, state: dict[str, Any]) -> None:
        pixmap = state.get("pixmap")
        self._pixmap = pixmap.copy() if pixmap is not None else None
        self._sync_widget_size()
        self._annotations = deepcopy(state.get("annotations", []))
        self._selected = None
        self._next_z = state.get("next_z", 0)
        self._next_text_id = state.get("next_text_id", 1)
        self._cancel_text()

    def _sync_widget_size(self) -> None:
        if self._pixmap is None:
            return
        w = max(1, int(round(self._pixmap.width() * self._zoom)))
        h = max(1, int(round(self._pixmap.height() * self._zoom)))
        self.setFixedSize(w, h)

    def _to_canvas_pos(self, pos: QPointF) -> QPointF:
        return QPointF(pos.x() / self._zoom, pos.y() / self._zoom)

    def _normalise_z_order(self) -> None:
        for index, anno in enumerate(sorted(self._annotations, key=lambda item: item.get("z", 0))):
            anno["z"] = index
        self._recalculate_next_z()

    def _recalculate_next_z(self) -> None:
        self._next_z = max((anno.get("z", 0) for anno in self._annotations), default=-1) + 1

    def _recalculate_next_text_id(self) -> None:
        self._next_text_id = max(
            (anno.get("text_id", 0) for anno in self._annotations if anno.get("type") == "text"),
            default=0,
        ) + 1

    def _undo_double_click_wobble(self) -> None:
        """Reverse the tiny move made by the first press of a double-click.

        Selecting on a single press means the opening press of a double-click
        arms a drag. A hand that wanders a few pixels between the two clicks
        would otherwise nudge the annotation and leave an undo entry behind,
        which is not what anyone doing a double-click meant to happen.
        """
        last = self._last_drag
        self._last_drag = None
        if not last or not last.get("pushed"):
            return
        slop = self._DBLCLICK_SCREEN_SLOP / max(self._zoom, 0.05)
        if last["distance"] > slop:
            return                       # a deliberate drag, leave it alone
        anno, origin = last["anno"], last["origin"]
        if anno is None or origin is None or anno not in self._annotations:
            return
        anno.clear()
        anno.update(deepcopy(origin))
        if self._undo_stack:
            self._undo_stack.pop()
        self.update()

    # ── Hover feedback ───────────────────────────────────────────────────────

    def _update_hover_cursor(self, pos: QPointF) -> None:
        """Say what a press would do, before it is pressed.

        Without this the cursor is a plain arrow everywhere and there is no way
        to tell a shape from empty canvas, or the body of a shape from one of its
        resize handles, except by clicking and finding out.
        """
        shape = Qt.CursorShape.ArrowCursor

        if self._pixmap is None:
            pass
        elif self._text_editing:
            handle = self._get_live_text_resize_handle(pos)
            shape = self._CURSOR_FOR_HANDLE.get(handle, Qt.CursorShape.IBeamCursor)
        elif self.tool == "select":
            handle = None
            # The current selection is asked first, matching how a press
            # resolves: its handles win over whatever sits beneath them.
            if self._selected is not None and self._selected in self._annotations:
                handle = self._get_resize_handle(self._selected, pos)
            if handle:
                shape = self._CURSOR_FOR_HANDLE[handle]
            else:
                hit = self._find_annotation(pos)
                if hit is not None:
                    handle = self._get_resize_handle(hit, pos)
                    shape = (
                        self._CURSOR_FOR_HANDLE[handle] if handle
                        else Qt.CursorShape.SizeAllCursor
                    )
                elif self._find_text_at(pos) is not None:
                    shape = Qt.CursorShape.IBeamCursor
        elif self.tool == "text":
            shape = Qt.CursorShape.IBeamCursor
        else:
            shape = Qt.CursorShape.CrossCursor

        if shape != self._hover_cursor:
            self._hover_cursor = shape
            self.setCursor(shape)

    # ── Drag engine ──────────────────────────────────────────────────────────
    # Every drag is computed from a snapshot of the annotation taken when the
    # press landed, not by accumulating per-event deltas. That is what makes
    # Shift-constrain and Escape-to-cancel possible, and it cannot drift.

    @staticmethod
    def _event_shift(event) -> bool:
        """Shift held? Tolerant of the position-only stubs used in tests."""
        mods = getattr(event, "modifiers", None)
        if mods is None:
            return False
        try:
            return bool(mods() & Qt.KeyboardModifier.ShiftModifier)
        except Exception:
            return False

    def _apply_drag(self, tdx: float, tdy: float, shift: bool) -> None:
        origin = self._drag_origin
        anno   = self._selected
        if origin is None or anno is None:
            return
        handle = self._resize_handle
        if handle:
            self._apply_resize(anno, origin, handle, tdx, tdy, shift)
        else:
            self._apply_move(anno, origin, tdx, tdy, shift)

    def _apply_move(self, anno, origin, tdx, tdy, shift) -> None:
        if shift:
            # Lock to the axis the hand has travelled furthest along.
            if abs(tdx) >= abs(tdy):
                tdy = 0.0
            else:
                tdx = 0.0
        for key in ("x1", "x2"):
            if key in origin:
                anno[key] = origin[key] + tdx
        for key in ("y1", "y2"):
            if key in origin:
                anno[key] = origin[key] + tdy
        if "path" in origin:
            anno["path"] = [QPointF(pt.x() + tdx, pt.y() + tdy) for pt in origin["path"]]

    def _apply_resize(self, anno, origin, handle, tdx, tdy, shift) -> None:
        anno_type = origin.get("type")

        if anno_type == "arrow":
            if handle == "start":
                anno["x1"] = origin["x1"] + tdx
                anno["y1"] = origin["y1"] + tdy
            elif handle == "end":
                anno["x2"] = origin["x2"] + tdx
                anno["y2"] = origin["y2"] + tdy
            return

        if anno_type == "text":
            left   = origin["x1"]
            top    = origin["y1"]
            right  = left + origin.get("width", 100)
            bottom = top + origin.get("height", 24)
            min_w, min_h = 48.0, 24.0
        else:
            left, right = sorted((origin["x1"], origin["x2"]))
            top, bottom = sorted((origin["y1"], origin["y2"]))
            min_w = min_h = 4.0

        start_w = right - left
        start_h = bottom - top

        if "l" in handle:
            left += tdx
        if "r" in handle:
            right += tdx
        if "t" in handle:
            top += tdy
        if "b" in handle:
            bottom += tdy

        # Shift keeps the original proportions, but only for a corner —
        # constraining a single-axis handle would defeat the point of having one.
        if shift and handle in ("tl", "tr", "bl", "br") and start_w > 0 and start_h > 0:
            ratio  = start_h / start_w
            new_h  = abs(right - left) * ratio
            if "t" in handle:
                top = bottom - new_h
            else:
                bottom = top + new_h

        if right - left < min_w:
            if "l" in handle:
                left = right - min_w
            else:
                right = left + min_w
        if bottom - top < min_h:
            if "t" in handle:
                top = bottom - min_h
            else:
                bottom = top + min_h

        if anno_type == "text":
            anno["x1"], anno["y1"] = left, top
            anno["width"]  = right - left
            anno["height"] = bottom - top
            return

        # Write back in the orientation the shape was drawn in, so a rectangle
        # dragged right-to-left does not silently flip on its first resize.
        if origin["x1"] <= origin["x2"]:
            anno["x1"], anno["x2"] = left, right
        else:
            anno["x1"], anno["x2"] = right, left
        if origin["y1"] <= origin["y2"]:
            anno["y1"], anno["y2"] = top, bottom
        else:
            anno["y1"], anno["y2"] = bottom, top

    def _cancel_drag(self) -> bool:
        """Abort an in-progress drag, restoring the pre-drag geometry."""
        if not self._dragging or self._drag_origin is None or self._selected is None:
            return False
        if self._drag_started:
            self._selected.clear()
            self._selected.update(deepcopy(self._drag_origin))
            if self._undo_stack:
                self._undo_stack.pop()      # the snapshot taken when the drag began
        self._dragging = False
        self._drag_started = False
        self._resize_handle = None
        self._drag_origin = None
        self.update()
        return True

    def nudge_selected(self, dx: float, dy: float) -> bool:
        """Move the selection by a fixed step. Used by the arrow keys."""
        if self._selected is None or self._selected not in self._annotations:
            return False
        self._undo_stack.append(self._clone_annotations())
        self._redo_stack = []
        origin = deepcopy(self._selected)
        self._apply_move(self._selected, origin, dx, dy, False)
        self.update()
        self.annotation_changed.emit()
        return True

    def _begin_selection_drag(
        self, anno: dict[str, Any], handle: str | None, pos: QPointF
    ) -> None:
        """Select `anno` and arm a move/resize drag starting at `pos`.

        Shared by single-click selection (Select tool) and double-click
        selection (any tool) so the two paths arm the drag identically.
        """
        self._selected      = anno
        self._resize_handle = handle
        self._dragging      = True
        self._drag_moved    = False
        self._drag_started  = False
        self._start         = pos
        self._drag_last_pos = pos
        self._drag_origin   = deepcopy(anno)

    def _get_resize_handle(self, anno: dict[str, Any], pos: QPointF) -> str | None:
        """Which handle is under pos, or None.

        Corners are tested before edges so that the corner wins where their grab
        zones overlap — a corner does what both edges do, so it is never the
        more surprising answer.
        """
        radius = self._grab_radius()
        points = self._handle_points(anno)
        for group in (("tl", "tr", "bl", "br", "start", "end"), ("t", "b", "l", "r")):
            best, best_distance = None, radius
            for name in group:
                point = points.get(name)
                if point is None:
                    continue
                distance = math.hypot(pos.x() - point.x(), pos.y() - point.y())
                if distance < best_distance:
                    best, best_distance = name, distance
            if best is not None:
                return best
        return None

    def _find_annotation(self, pos: QPointF) -> dict | None:
        """Return the topmost annotation whose OUTLINE is under pos, or None.

        Selecting and dragging happen on a shape's border — the pixels actually
        drawn at that point. Interiors are deliberately click-through, so a
        rectangle drawn around a defect never blocks access to anything inside
        it, and a tester can work through a densely marked-up screenshot without
        having to reorder layers.

        Text is the exception, and it is handled separately: the border of a text
        box moves it, while clicking inside it edits the words. See
        `_find_text_at`.
        """
        tol = self._hit_tolerance()
        for anno in sorted(self._annotations, key=lambda item: item.get("z", 0), reverse=True):
            if self._is_on_outline(anno, pos, tol):
                return anno
        return None

    def _find_text_at(self, pos: QPointF) -> dict | None:
        """Topmost text annotation whose interior contains pos.

        Only used to decide whether a click means "edit these words".
        """
        tol = self._hit_tolerance()
        for anno in sorted(self._annotations, key=lambda item: item.get("z", 0), reverse=True):
            if anno.get("type") == "text" and self._contains_point(anno, pos, tol):
                return anno
        return None

    def _is_on_outline(self, anno: dict[str, Any], pos: QPointF, tol: float) -> bool:
        """Is pos on the annotation's stroke — the pixels actually drawn there?"""
        t = anno["type"]

        if t == "pen":
            return any(
                math.hypot(pt.x() - pos.x(), pt.y() - pos.y()) < tol
                for pt in anno.get("path", [])
            )

        if t == "arrow":
            # Distance to the shaft, not to the bounding box — a diagonal arrow's
            # box is mostly empty space nowhere near the arrow.
            return self._distance_to_segment(
                pos, anno["x1"], anno["y1"], anno["x2"], anno["y2"]
            ) <= tol

        if t == "text":
            left   = anno.get("x1", 0)
            top    = anno.get("y1", 0)
            right  = left + anno.get("width", 100)
            bottom = top + anno.get("height", 24)
        else:
            left, right = sorted((anno["x1"], anno["x2"]))
            top, bottom = sorted((anno["y1"], anno["y2"]))

        if t == "circle":
            rx = (right - left) / 2
            ry = (bottom - top) / 2
            if rx <= 0 or ry <= 0:
                return False
            cx, cy = left + rx, top + ry
            # Normalised radius: 1.0 is exactly on the outline.
            radius = math.hypot((pos.x() - cx) / rx, (pos.y() - cy) / ry)
            return abs(radius - 1.0) <= tol / min(rx, ry)

        outer = QRectF(
            left - tol, top - tol,
            (right - left) + 2 * tol, (bottom - top) + 2 * tol,
        )
        if not outer.contains(pos):
            return False
        inner_w = (right - left) - 2 * tol
        inner_h = (bottom - top) - 2 * tol
        if inner_w <= 0 or inner_h <= 0:
            return True          # too small to have an interior
        return not QRectF(left + tol, top + tol, inner_w, inner_h).contains(pos)

    def _contains_point(self, anno: dict[str, Any], pos: QPointF, tol: float) -> bool:
        """Is pos inside the annotation's area? Pen strokes have none."""
        t = anno["type"]
        if t in ("pen", "arrow"):
            return False

        if t == "text":
            left   = anno.get("x1", 0)
            top    = anno.get("y1", 0)
            right  = left + anno.get("width", 100)
            bottom = top + anno.get("height", 24)
        else:
            left, right = sorted((anno["x1"], anno["x2"]))
            top, bottom = sorted((anno["y1"], anno["y2"]))

        if t == "circle":
            rx = (right - left) / 2
            ry = (bottom - top) / 2
            if rx <= 0 or ry <= 0:
                return False
            cx, cy = left + rx, top + ry
            return math.hypot((pos.x() - cx) / rx, (pos.y() - cy) / ry) <= 1.0

        return QRectF(
            left - tol, top - tol,
            (right - left) + 2 * tol, (bottom - top) + 2 * tol,
        ).contains(pos)

    @staticmethod
    def _distance_to_segment(pos: QPointF, x1, y1, x2, y2) -> float:
        vx, vy = x2 - x1, y2 - y1
        length_squared = vx * vx + vy * vy
        if length_squared == 0:
            return math.hypot(pos.x() - x1, pos.y() - y1)
        t = ((pos.x() - x1) * vx + (pos.y() - y1) * vy) / length_squared
        t = max(0.0, min(1.0, t))
        return math.hypot(pos.x() - (x1 + t * vx), pos.y() - (y1 + t * vy))
