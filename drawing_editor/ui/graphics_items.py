"""
PyQt5 graphics items for rendering drawing objects.

This module provides QGraphicsItem subclasses for visualizing all types
of graphic objects in the CAD scene.
"""

import math
from typing import Optional, Dict, Callable

from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
    QGraphicsRectItem,
    QGraphicsItemGroup,
    QGraphicsItem,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath

from drawing_editor.core.models import (
    PointObject,
    LineObject,
    CircleObject,
    RectObject,
    ArcObject,
    TextObject,
    DimensionObject,
)


class GraphicsPoint(QGraphicsEllipseItem):
    """Graphics item for displaying a point."""
    
    def __init__(self, point_obj: PointObject, size: float = 0.2) -> None:
        super().__init__(-size/2, -size/2, size, size)
        self.point_obj = point_obj
        self.setPos(point_obj.x, point_obj.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: QPointF) -> QPointF:
        if change == QGraphicsItem.ItemPositionChange:
            self.point_obj.x = value.x()
            self.point_obj.y = value.y()
            if self.point_obj.dxf_entity:
                from ezdxf.math import Vec3
                self.point_obj.dxf_entity.dxf.location = Vec3(value.x(), value.y(), 0)
        return super().itemChange(change, value)


class GraphicsLine(QGraphicsLineItem):
    """Graphics item for displaying a line segment."""
    
    def __init__(self, line_obj: LineObject) -> None:
        super().__init__(line_obj.x1, line_obj.y1, line_obj.x2, line_obj.y2)
        self.line_obj = line_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self) -> None:
        """Update the graphics item from the model object."""
        self.setLine(
            self.line_obj.x1, 
            self.line_obj.y1, 
            self.line_obj.x2, 
            self.line_obj.y2
        )


class GraphicsCircle(QGraphicsEllipseItem):
    """Graphics item for displaying a circle."""
    
    def __init__(self, circle_obj: CircleObject) -> None:
        super().__init__(
            circle_obj.cx - circle_obj.radius, 
            circle_obj.cy - circle_obj.radius,
            2 * circle_obj.radius, 
            2 * circle_obj.radius
        )
        self.circle_obj = circle_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self) -> None:
        """Update the graphics item from the model object."""
        self.setRect(
            self.circle_obj.cx - self.circle_obj.radius,
            self.circle_obj.cy - self.circle_obj.radius,
            2 * self.circle_obj.radius, 
            2 * self.circle_obj.radius
        )


class GraphicsRect(QGraphicsRectItem):
    """Graphics item for displaying a rectangle."""
    
    def __init__(self, rect_obj: RectObject) -> None:
        x1, y1 = rect_obj.x1, rect_obj.y1
        x2, y2 = rect_obj.x2, rect_obj.y2
        super().__init__(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        self.rect_obj = rect_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self) -> None:
        """Update the graphics item from the model object."""
        x1, y1 = self.rect_obj.x1, self.rect_obj.y1
        x2, y2 = self.rect_obj.x2, self.rect_obj.y2
        self.setRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))


class GraphicsArc(QGraphicsPathItem):
    """Graphics item for displaying an arc."""
    
    def __init__(self, arc_obj: ArcObject) -> None:
        super().__init__()
        self.arc_obj = arc_obj
        self.update_path()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_path(self) -> None:
        """Update the arc path from the model object."""
        cx, cy = self.arc_obj.cx, self.arc_obj.cy
        r = self.arc_obj.radius
        start = self.arc_obj.start_angle
        end = self.arc_obj.end_angle
        
        span = 360 - (start - end) if end < start else end - start
        
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        path = QPainterPath()
        path.arcMoveTo(rect, start)
        path.arcTo(rect, start, span)
        self.setPath(path)


class GraphicsText(QGraphicsTextItem):
    """Graphics item for displaying text annotations."""
    
    def __init__(self, text_obj: TextObject) -> None:
        super().__init__(text_obj.text)
        self.text_obj = text_obj
        self.setPos(text_obj.x, text_obj.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setDefaultTextColor(QColor(0, 0, 0))
        self.setFont(QFont("Arial", int(text_obj.height)))

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: QPointF) -> QPointF:
        if change == QGraphicsItem.ItemPositionChange:
            self.text_obj.x = value.x()
            self.text_obj.y = value.y()
            if self.text_obj.dxf_entity:
                from ezdxf.math import Vec3
                self.text_obj.dxf_entity.dxf.insert = Vec3(value.x(), value.y(), 0)
        return super().itemChange(change, value)


class GraphicsDimension(QGraphicsItemGroup):
    """
    Graphics item for displaying dimension annotations.
    
    Supports linear, radius, diameter, and angular dimensions.
    """
    
    DIMENSION_HANDLERS: Dict[str, str] = {
        "Linear": "_draw_linear",
        "Radius": "_draw_radius",
        "Diameter": "_draw_diameter",
        "Angular": "_draw_angular",
    }
    
    def __init__(self, dim_obj: DimensionObject) -> None:
        super().__init__()
        self.dim_obj = dim_obj
        self.update_graphics()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_graphics(self) -> None:
        """Clear and redraw the dimension graphics."""
        for child in self.childItems():
            self.removeFromGroup(child)
            if child.scene():
                child.scene().removeItem(child)
        
        handler_name = self.DIMENSION_HANDLERS.get(self.dim_obj.dim_type)
        if handler_name:
            getattr(self, handler_name)()

    def _draw_linear(self) -> None:
        """Draw a linear dimension."""
        p1 = self.dim_obj.p1
        p2 = self.dim_obj.p2
        
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        
        if length == 0:
            return
        
        nx = -dy / length
        ny = dx / length
        off = self.dim_obj.offset
        
        ext1_start = p1
        ext1_end = QPointF(p1.x() + nx * off, p1.y() + ny * off)
        ext2_start = p2
        ext2_end = QPointF(p2.x() + nx * off, p2.y() + ny * off)
        
        dim_line = QGraphicsLineItem(QLineF(ext1_end, ext2_end))
        ext_line1 = QGraphicsLineItem(QLineF(ext1_start, ext1_end))
        ext_line2 = QGraphicsLineItem(QLineF(ext2_start, ext2_end))
        
        text = QGraphicsTextItem(f"{length:.2f}")
        mid = (ext1_end + ext2_end) / 2
        text.setPos(mid - text.boundingRect().center())
        
        pen = QPen(QColor(0, 0, 0), 0.2)
        dim_line.setPen(pen)
        ext_line1.setPen(pen)
        ext_line2.setPen(pen)
        text.setDefaultTextColor(QColor(0, 0, 0))
        
        self.addToGroup(dim_line)
        self.addToGroup(ext_line1)
        self.addToGroup(ext_line2)
        self.addToGroup(text)

    def _draw_radius(self) -> None:
        """Draw a radius dimension."""
        center = self.dim_obj.p1
        radius = self.dim_obj.radius
        
        arrow_end = QPointF(center.x() + radius, center.y())
        line = QGraphicsLineItem(QLineF(center, arrow_end))
        
        text = QGraphicsTextItem(f"R{radius:.2f}")
        text.setPos(arrow_end.x() + 1, arrow_end.y())
        
        pen = QPen(QColor(0, 0, 0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0, 0, 0))
        
        self.addToGroup(line)
        self.addToGroup(text)

    def _draw_diameter(self) -> None:
        """Draw a diameter dimension."""
        center = self.dim_obj.p1
        radius = self.dim_obj.diameter / 2
        
        arrow_end1 = QPointF(center.x() + radius, center.y())
        arrow_end2 = QPointF(center.x() - radius, center.y())
        line = QGraphicsLineItem(QLineF(arrow_end1, arrow_end2))
        
        text = QGraphicsTextItem(f"Ø{self.dim_obj.diameter:.2f}")
        text.setPos(center.x(), center.y() - 1)
        
        pen = QPen(QColor(0, 0, 0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0, 0, 0))
        
        self.addToGroup(line)
        self.addToGroup(text)

    def _draw_angular(self) -> None:
        """Draw an angular dimension."""
        vertex = self.dim_obj.p1
        angle = self.dim_obj.angle
        r = 5
        
        rect = QRectF(vertex.x() - r, vertex.y() - r, 2 * r, 2 * r)
        path = QPainterPath()
        path.arcMoveTo(rect, 0)
        path.arcTo(rect, 0, angle)
        arc = QGraphicsPathItem(path)
        
        text = QGraphicsTextItem(f"{angle:.1f}°")
        mid_angle = math.radians(angle / 2)
        tx = vertex.x() + r * math.cos(mid_angle)
        ty = vertex.y() - r * math.sin(mid_angle)
        text.setPos(tx, ty)
        
        pen = QPen(QColor(0, 0, 0), 0.2)
        arc.setPen(pen)
        text.setDefaultTextColor(QColor(0, 0, 0))
        
        self.addToGroup(arc)
        self.addToGroup(text)
