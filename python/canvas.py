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
from PySide6.QtWidgets import QInputDialog, QWidget


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
    crop      – crop the canvas to a dragged rectangle
    pen       – freehand stroke

    Signals
    -------
    annotation_changed()  – emitted whenever annotations are modified.
    """

    annotation_changed = Signal()
    text_editing_changed = Signal(bool)

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
        self._selected:      dict | None = None
        self._dragging       = False
        self._drag_moved     = False
        self._drag_started   = False
        self._drag_last_pos  = QPointF()
        self._resize_handle  = None  # For arrows: "start"/"end"; for rect/circle: "tl"/"tr"/"bl"/"br"; for text: "tl"/"tr"/"bl"/"br"

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
            "highlight", "text", "circle", "arrow", "rect", "pen"
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

        if self.tool == "crop":
            self._selected = None
            self._resize_handle = None
            self._drawing = True
            self._start = pos
            self._current = pos
            self.update()
            return

        # You can interact with already-added annotations from any tool.
        hit = self._find_annotation(pos)
        if hit is not None:
            self._selected = hit
            self._resize_handle = self._get_resize_handle(hit, pos)
            self._dragging = True
            self._drag_moved = False
            self._drag_started = False
            self._start = pos
            self._drag_last_pos = pos
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
            self._selected = None
            self._dragging = False
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

        if self._dragging and self._selected is not None:
            dx = pos.x() - self._drag_last_pos.x()
            dy = pos.y() - self._drag_last_pos.y()
            total_dx = pos.x() - self._start.x() if self._start else 0
            total_dy = pos.y() - self._start.y() if self._start else 0
            self._drag_last_pos = pos
            self._drag_moved    = True

            # Require a short real drag before moving/resizing to avoid accidental shifts on click.
            if not self._drag_started:
                if math.hypot(total_dx, total_dy) < 3:
                    return
                self._drag_started = True
            
            anno_type = self._selected.get("type")
            
            # Resizing by dragging handles
            if self._resize_handle:
                if anno_type == "arrow":
                    # Arrow endpoints
                    if self._resize_handle == "start":
                        self._selected["x1"] += dx
                        self._selected["y1"] += dy
                    elif self._resize_handle == "end":
                        self._selected["x2"] += dx
                        self._selected["y2"] += dy
                else:
                    # Corner handles for rect/circle/highlight/text
                    handle = self._resize_handle
                    if anno_type == "text":
                        # For text, modify x/y + width/height with minimum box size.
                        min_w = 48
                        min_h = 24
                        if "tl" in handle:
                            self._selected["x1"] += dx
                            self._selected["y1"] += dy
                            self._selected["width"] -= dx
                            self._selected["height"] -= dy
                        if "tr" in handle:
                            self._selected["width"] += dx
                            self._selected["y1"] += dy
                            self._selected["height"] -= dy
                        if "bl" in handle:
                            self._selected["x1"] += dx
                            self._selected["width"] -= dx
                            self._selected["height"] += dy
                        if "br" in handle:
                            self._selected["width"] += dx
                            self._selected["height"] += dy

                        # Clamp to minimum size and keep anchor behavior stable.
                        if self._selected["width"] < min_w:
                            if "tl" in handle or "bl" in handle:
                                self._selected["x1"] -= (min_w - self._selected["width"])
                            self._selected["width"] = min_w
                        if self._selected["height"] < min_h:
                            if "tl" in handle or "tr" in handle:
                                self._selected["y1"] -= (min_h - self._selected["height"])
                            self._selected["height"] = min_h
                    else:
                        # Robust corner resize for rect/circle/highlight regardless of draw direction.
                        x1, y1 = self._selected["x1"], self._selected["y1"]
                        x2, y2 = self._selected["x2"], self._selected["y2"]

                        left, right = min(x1, x2), max(x1, x2)
                        top, bottom = min(y1, y2), max(y1, y2)

                        if "l" in handle:
                            left += dx
                        if "r" in handle:
                            right += dx
                        if "t" in handle:
                            top += dy
                        if "b" in handle:
                            bottom += dy

                        # Prevent collapsing to zero.
                        if right - left < 2:
                            right = left + 2
                        if bottom - top < 2:
                            bottom = top + 2

                        # Map back to original orientation.
                        if x1 <= x2:
                            self._selected["x1"], self._selected["x2"] = left, right
                        else:
                            self._selected["x1"], self._selected["x2"] = right, left

                        if y1 <= y2:
                            self._selected["y1"], self._selected["y2"] = top, bottom
                        else:
                            self._selected["y1"], self._selected["y2"] = bottom, top
            # Moving the whole annotation
            else:
                if anno_type == "text":
                    self._selected["x1"] += dx
                    self._selected["y1"] += dy
                else:
                    for key in ("x1", "x2"):
                        if key in self._selected:
                            self._selected[key] += dx
                    for key in ("y1", "y2"):
                        if key in self._selected:
                            self._selected[key] += dy
                if "path" in self._selected:
                    self._selected["path"] = [
                        QPointF(p.x() + dx, p.y() + dy)
                        for p in self._selected["path"]
                    ]
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
            self._dragging = False
            self._drag_started = False
            self._resize_handle = None
            # Keep _selected intact so Delete key still works
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
        """Double-click text to edit it in a multiline editor dialog."""
        if not self._pixmap:
            return
        pos = self._to_canvas_pos(event.position())
        hit = self._find_annotation(pos)
        if hit and hit.get("type") == "text":
            current = hit.get("text", "")
            text, ok = QInputDialog.getMultiLineText(
                self,
                "Edit Text",
                "Update annotation text:",
                current,
            )
            if ok:
                new_text = text.rstrip()
                self._undo_stack.append(self._clone_annotations())
                hit["text"] = new_text
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
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        else:
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
                # Draw corner resize handles
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.setPen(QPen(color, 1.5))
                handle_size = 6
                p.drawEllipse(QPointF(x0 - 4, y0 - 4), handle_size, handle_size)
                p.drawEllipse(QPointF(x0 + w + 4, y0 - 4), handle_size, handle_size)
                p.drawEllipse(QPointF(x0 - 4, y0 + h + 4), handle_size, handle_size)
                p.drawEllipse(QPointF(x0 + w + 4, y0 + h + 4), handle_size, handle_size)

        elif t in ("highlight", "rect"):
            rect = QRectF(
                a["x1"], a["y1"],
                a["x2"] - a["x1"], a["y2"] - a["y1"],
            )
            if t == "highlight":
                fill = QColor(a["color"])
                fill.setAlphaF(a.get("opacity", 0.30))
                p.fillRect(rect, QBrush(fill))
            p.drawRect(rect)
            if selected:
                self._draw_selection_rect(p, rect.adjusted(-4, -4, 4, 4))
                # Draw corner resize handles
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.setPen(QPen(color, 1.5))
                handle_size = 6
                p.drawEllipse(QPointF(a["x1"], a["y1"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x2"], a["y1"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x1"], a["y2"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x2"], a["y2"]), handle_size, handle_size)

        elif t == "circle":
            rect = QRectF(
                a["x1"], a["y1"],
                a["x2"] - a["x1"], a["y2"] - a["y1"],
            )
            p.drawEllipse(rect)
            if selected:
                self._draw_selection_rect(p, rect.adjusted(-4, -4, 4, 4))
                # Draw corner resize handles
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.setPen(QPen(color, 1.5))
                handle_size = 6
                p.drawEllipse(QPointF(a["x1"], a["y1"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x2"], a["y1"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x1"], a["y2"]), handle_size, handle_size)
                p.drawEllipse(QPointF(a["x2"], a["y2"]), handle_size, handle_size)

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
                # Draw endpoint handles (small circles you can drag to resize/rotate the arrow)
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.setPen(QPen(color, 1.5))
                p.drawEllipse(QPointF(x1, y1), 6, 6)
                p.drawEllipse(QPointF(x2, y2), 6, 6)

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
        
        # Corner resize handles
        handle_size = 6
        p.setBrush(QBrush(QColor(255, 255, 255, 200)))
        p.setPen(QPen(color, 1.5))
        # Top-left, top-right, bottom-left, bottom-right
        p.drawEllipse(QPointF(x0 - 4, y0 - 4), handle_size, handle_size)
        p.drawEllipse(QPointF(x0 + w + 4, y0 - 4), handle_size, handle_size)
        p.drawEllipse(QPointF(x0 - 4, y0 + h + 4), handle_size, handle_size)
        p.drawEllipse(QPointF(x0 + w + 4, y0 + h + 4), handle_size, handle_size)

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
        handle_radius = 12
        corners = {
            "tl": QPointF(x0 - 4, y0 - 4),
            "tr": QPointF(x0 + w + 4, y0 - 4),
            "bl": QPointF(x0 - 4, y0 + h + 4),
            "br": QPointF(x0 + w + 4, y0 + h + 4),
        }
        for name, corner in corners.items():
            if math.hypot(pos.x() - corner.x(), pos.y() - corner.y()) < handle_radius:
                return name
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

    def _get_resize_handle(self, anno: dict[str, Any], pos: QPointF) -> str | None:
        """Detect which resize handle is being clicked, if any. Returns 'tl', 'tr', 'bl', 'br', 'start', 'end', or None."""
        anno_type = anno.get("type")
        handle_radius = 12
        
        if anno_type == "arrow":
            # Check arrow endpoints
            x1, y1, x2, y2 = anno["x1"], anno["y1"], anno["x2"], anno["y2"]
            if math.hypot(pos.x() - x1, pos.y() - y1) < handle_radius:
                return "start"
            if math.hypot(pos.x() - x2, pos.y() - y2) < handle_radius:
                return "end"
        elif anno_type in ("rect", "highlight", "circle", "text"):
            # Check corner handles for rectangular shapes
            x1 = anno["x1"]
            y1 = anno["y1"]
            
            # For text, compute x2/y2 from width/height; for others use stored values
            if anno_type == "text":
                x1 -= 4
                y1 -= 4
                x2 = anno["x1"] + anno.get("width", 100) + 4
                y2 = anno["y1"] + anno.get("height", 24) + 4
            else:
                x2 = anno["x2"]
                y2 = anno["y2"]
            
            # Normalize coords
            left   = min(x1, x2)
            right  = max(x1, x2)
            top    = min(y1, y2)
            bottom = max(y1, y2)
            
            # Check if near any corner (within handle_radius)
            if math.hypot(pos.x() - left, pos.y() - top) < handle_radius:
                return "tl"
            if math.hypot(pos.x() - right, pos.y() - top) < handle_radius:
                return "tr"
            if math.hypot(pos.x() - left, pos.y() - bottom) < handle_radius:
                return "bl"
            if math.hypot(pos.x() - right, pos.y() - bottom) < handle_radius:
                return "br"
        
        return None

    def _find_annotation(self, pos: QPointF) -> dict | None:
        """Return the topmost annotation under pos, or None."""
        for anno in sorted(self._annotations, key=lambda item: item.get("z", 0), reverse=True):
            t = anno["type"]
            if t == "pen":
                for pt in anno.get("path", []):
                    if math.hypot(pt.x() - pos.x(), pt.y() - pos.y()) < 12:
                        return anno
            elif t == "text":
                x0 = anno.get("x1", 0)
                y0 = anno.get("y1", 0)
                w  = anno.get("width", 100)
                h  = anno.get("height", 24)
                rect = QRectF(x0 - 4, y0 - 4, w + 8, h + 8)
                if rect.contains(pos):
                    return anno
            else:
                min_x = min(anno["x1"], anno["x2"])
                max_x = max(anno["x1"], anno["x2"])
                min_y = min(anno["y1"], anno["y2"])
                max_y = max(anno["y1"], anno["y2"])
                if min_x - 8 <= pos.x() <= max_x + 8 and min_y - 8 <= pos.y() <= max_y + 8:
                    return anno
        return None
