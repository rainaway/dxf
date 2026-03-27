import sys
import math
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                             QFileDialog, QToolBar, QAction, QStatusBar, QVBoxLayout,
                             QWidget, QDockWidget, QListWidget, QPushButton, QDialog,
                             QFormLayout, QLineEdit, QMessageBox, QLabel, QGraphicsItem,
                             QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPathItem,
                             QGraphicsTextItem, QGraphicsRectItem, QGraphicsPolygonItem,
                             QGraphicsItemGroup, QInputDialog, QColorDialog, QComboBox,
                             QMenu, QGraphicsSimpleTextItem, QCheckBox, QGroupBox, QHBoxLayout,
                             QMenuBar)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, QSizeF, QSettings
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF, QPainter, QTransform
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPageSetupDialog
import ezdxf
from ezdxf.math import Vec3

# Paper sizes in mm (ISO 216)
PAPER_SIZES = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "A2": (420, 594),
    "A3": (297, 420),
    "A4": (210, 297),
}

# Default colors
DEFAULT_BACKGROUND_COLOR = QColor(255, 255, 255)  # White
DEFAULT_OBJECT_COLOR = QColor(0, 0, 0)  # Black

# ------------------ Модель данных ------------------
class GraphicObject:
    def __init__(self, dxf_entity=None):
        self.dxf_entity = dxf_entity
        self.graphics_item = None
        self.type = ""
        self.params = {}

class PointObject(GraphicObject):
    def __init__(self, x, y, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Point"
        self.x = x
        self.y = y

class LineObject(GraphicObject):
    def __init__(self, x1, y1, x2, y2, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Line"
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2

class CircleObject(GraphicObject):
    def __init__(self, cx, cy, radius, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Circle"
        self.cx, self.cy = cx, cy
        self.radius = radius

class RectObject(GraphicObject):
    def __init__(self, x1, y1, x2, y2, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Rectangle"
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2

class ArcObject(GraphicObject):
    def __init__(self, cx, cy, radius, start_angle, end_angle, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Arc"
        self.cx, self.cy = cx, cy
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle

class TextObject(GraphicObject):
    def __init__(self, x, y, text, height=2.5, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Text"
        self.x, self.y = x, y
        self.text = text
        self.height = height

class DimensionObject(GraphicObject):
    def __init__(self, p1, p2, offset=2, dim_type="Linear", dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Dimension"
        self.dim_type = dim_type
        self.p1 = p1
        self.p2 = p2
        self.offset = offset
        self.radius = None
        self.diameter = None
        self.angle = None

# ------------------ Графические элементы ------------------
class GraphicsPoint(QGraphicsEllipseItem):
    def __init__(self, point_obj, size=0.2):
        super().__init__(-size/2, -size/2, size, size)
        self.point_obj = point_obj
        self.setPos(point_obj.x, point_obj.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.point_obj.x = value.x()
            self.point_obj.y = value.y()
            if self.point_obj.dxf_entity:
                self.point_obj.dxf_entity.dxf.location = Vec3(value.x(), value.y(), 0)
        return super().itemChange(change, value)

class GraphicsLine(QGraphicsLineItem):
    def __init__(self, line_obj):
        super().__init__(line_obj.x1, line_obj.y1, line_obj.x2, line_obj.y2)
        self.line_obj = line_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self):
        self.setLine(self.line_obj.x1, self.line_obj.y1, self.line_obj.x2, self.line_obj.y2)

class GraphicsCircle(QGraphicsEllipseItem):
    def __init__(self, circle_obj):
        super().__init__(circle_obj.cx - circle_obj.radius, circle_obj.cy - circle_obj.radius,
                         2*circle_obj.radius, 2*circle_obj.radius)
        self.circle_obj = circle_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self):
        self.setRect(self.circle_obj.cx - self.circle_obj.radius,
                     self.circle_obj.cy - self.circle_obj.radius,
                     2*self.circle_obj.radius, 2*self.circle_obj.radius)

class GraphicsRect(QGraphicsRectItem):
    def __init__(self, rect_obj):
        x1, y1 = rect_obj.x1, rect_obj.y1
        x2, y2 = rect_obj.x2, rect_obj.y2
        super().__init__(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1))
        self.rect_obj = rect_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_from_obj(self):
        x1, y1 = self.rect_obj.x1, self.rect_obj.y1
        x2, y2 = self.rect_obj.x2, self.rect_obj.y2
        self.setRect(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1))

class GraphicsArc(QGraphicsPathItem):
    def __init__(self, arc_obj):
        super().__init__()
        self.arc_obj = arc_obj
        self.update_path()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_path(self):
        cx, cy = self.arc_obj.cx, self.arc_obj.cy
        r = self.arc_obj.radius
        start = self.arc_obj.start_angle
        end = self.arc_obj.end_angle
        if end < start:
            span = 360 - (start - end)
        else:
            span = end - start
        rect = QRectF(cx - r, cy - r, 2*r, 2*r)
        path = QPainterPath()
        path.arcMoveTo(rect, start)
        path.arcTo(rect, start, span)
        self.setPath(path)

class GraphicsText(QGraphicsTextItem):
    def __init__(self, text_obj):
        super().__init__(text_obj.text)
        self.text_obj = text_obj
        self.setPos(text_obj.x, text_obj.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setDefaultTextColor(QColor(0,0,0))
        self.setFont(QFont("Arial", int(text_obj.height)))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.text_obj.x = value.x()
            self.text_obj.y = value.y()
            if self.text_obj.dxf_entity:
                self.text_obj.dxf_entity.dxf.insert = Vec3(value.x(), value.y(), 0)
        return super().itemChange(change, value)

class GraphicsDimension(QGraphicsItemGroup):
    def __init__(self, dim_obj):
        super().__init__()
        self.dim_obj = dim_obj
        self.update_graphics()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def update_graphics(self):
        for child in self.childItems():
            self.removeFromGroup(child)
            if child.scene():
                child.scene().removeItem(child)
        if self.dim_obj.dim_type == "Linear":
            self._draw_linear()
        elif self.dim_obj.dim_type == "Radius":
            self._draw_radius()
        elif self.dim_obj.dim_type == "Diameter":
            self._draw_diameter()
        elif self.dim_obj.dim_type == "Angular":
            self._draw_angular()

    def _draw_linear(self):
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
        ext1_end = QPointF(p1.x() + nx*off, p1.y() + ny*off)
        ext2_start = p2
        ext2_end = QPointF(p2.x() + nx*off, p2.y() + ny*off)
        dim_line = QGraphicsLineItem(QLineF(ext1_end, ext2_end))
        ext_line1 = QGraphicsLineItem(QLineF(ext1_start, ext1_end))
        ext_line2 = QGraphicsLineItem(QLineF(ext2_start, ext2_end))
        text = QGraphicsTextItem(f"{length:.2f}")
        mid = (ext1_end + ext2_end) / 2
        text.setPos(mid - text.boundingRect().center())
        pen = QPen(QColor(0,0,0), 0.2)
        dim_line.setPen(pen)
        ext_line1.setPen(pen)
        ext_line2.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(dim_line)
        self.addToGroup(ext_line1)
        self.addToGroup(ext_line2)
        self.addToGroup(text)

    def _draw_radius(self):
        center = self.dim_obj.p1
        radius = self.dim_obj.radius
        arrow_end = QPointF(center.x() + radius, center.y())
        line = QGraphicsLineItem(QLineF(center, arrow_end))
        text = QGraphicsTextItem(f"R{radius:.2f}")
        text.setPos(arrow_end.x() + 1, arrow_end.y())
        pen = QPen(QColor(0,0,0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(line)
        self.addToGroup(text)

    def _draw_diameter(self):
        center = self.dim_obj.p1
        radius = self.dim_obj.diameter / 2
        arrow_end1 = QPointF(center.x() + radius, center.y())
        arrow_end2 = QPointF(center.x() - radius, center.y())
        line = QGraphicsLineItem(QLineF(arrow_end1, arrow_end2))
        text = QGraphicsTextItem(f"Ø{self.dim_obj.diameter:.2f}")
        text.setPos(center.x(), center.y() - 1)
        pen = QPen(QColor(0,0,0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(line)
        self.addToGroup(text)

    def _draw_angular(self):
        vertex = self.dim_obj.p1
        angle = self.dim_obj.angle
        r = 5
        start_angle = 0
        end_angle = angle
        rect = QRectF(vertex.x() - r, vertex.y() - r, 2*r, 2*r)
        path = QPainterPath()
        path.arcMoveTo(rect, start_angle)
        path.arcTo(rect, start_angle, end_angle)
        arc = QGraphicsPathItem(path)
        text = QGraphicsTextItem(f"{angle:.1f}°")
        mid_angle = math.radians(angle/2)
        tx = vertex.x() + r * math.cos(mid_angle)
        ty = vertex.y() - r * math.sin(mid_angle)
        text.setPos(tx, ty)
        pen = QPen(QColor(0,0,0), 0.2)
        arc.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(arc)
        self.addToGroup(text)

# ------------------ Привязка с подсказкой ------------------
class SnapManager:
    def __init__(self, scene):
        self.scene = scene
        self.snap_distance = 40
        self.snap_to_endpoints = True
        self.snap_to_center = True
        self.snap_to_midpoint = True
        self.snap_to_tangent = False
        self.snap_to_perpendicular = False
        self.snap_to_intersection = True

    def get_snap_info(self, view, screen_pos):
        if not self.scene:
            return None, None
        best_dist = self.snap_distance
        best_point = None
        best_hint = None
        
        for item in self.scene.items():
            # Endpoint snaps
            if self.snap_to_endpoints:
                if isinstance(item, GraphicsLine):
                    line = item.line()
                    for p in [line.p1(), line.p2()]:
                        pixel_pos = view.mapFromScene(p)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = p
                            best_hint = "End"
                elif isinstance(item, GraphicsRect):
                    rect = item.rect()
                    for p in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                        pixel_pos = view.mapFromScene(p)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = p
                            best_hint = "Vertex"
                elif isinstance(item, GraphicsPoint):
                    p = item.pos()
                    pixel_pos = view.mapFromScene(p)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = p
                        best_hint = "Point"
                elif isinstance(item, GraphicsArc):
                    # Arc endpoints
                    path = item.path()
                    if not path.isEmpty():
                        start_point = path.pointAtPercent(0)
                        end_point = path.pointAtPercent(1)
                        for p in [start_point, end_point]:
                            pixel_pos = view.mapFromScene(p)
                            dist = (screen_pos - pixel_pos).manhattanLength()
                            if dist < best_dist:
                                best_dist = dist
                                best_point = p
                                best_hint = "End"
            
            # Center snap
            if self.snap_to_center and isinstance(item, GraphicsCircle):
                p = QPointF(item.circle_obj.cx, item.circle_obj.cy)
                pixel_pos = view.mapFromScene(p)
                dist = (screen_pos - pixel_pos).manhattanLength()
                if dist < best_dist:
                    best_dist = dist
                    best_point = p
                    best_hint = "Center"
            
            # Midpoint snaps
            if self.snap_to_midpoint:
                if isinstance(item, GraphicsLine):
                    line = item.line()
                    mid = (line.p1() + line.p2()) / 2
                    pixel_pos = view.mapFromScene(mid)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = mid
                        best_hint = "Mid"
                elif isinstance(item, GraphicsRect):
                    rect = item.rect()
                    # Midpoints of rectangle sides
                    midpoints = [
                        QPointF(rect.center().x(), rect.top()),
                        QPointF(rect.center().x(), rect.bottom()),
                        QPointF(rect.left(), rect.center().y()),
                        QPointF(rect.right(), rect.center().y()),
                    ]
                    for p in midpoints:
                        pixel_pos = view.mapFromScene(p)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = p
                            best_hint = "Mid"
            
            # Tangent snap for circles and arcs
            if self.snap_to_tangent:
                if isinstance(item, (GraphicsCircle, GraphicsArc)):
                    tangent_point = self._find_tangent_point(view, screen_pos, item)
                    if tangent_point:
                        pixel_pos = view.mapFromScene(tangent_point)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = tangent_point
                            best_hint = "Tan"
            
            # Perpendicular snap
            if self.snap_to_perpendicular:
                perp_point = self._find_perpendicular_point(view, screen_pos, item)
                if perp_point:
                    pixel_pos = view.mapFromScene(perp_point)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = perp_point
                        best_hint = "Perp"
            
            # Intersection snap
            if self.snap_to_intersection:
                intersections = self._find_intersections_near(view, screen_pos)
                for p in intersections:
                    pixel_pos = view.mapFromScene(p)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = p
                        best_hint = "Int"
        
        return best_point, best_hint
    
    def _find_tangent_point(self, view, screen_pos, item):
        """Find tangent point on circle/arc from mouse position."""
        scene_pos = view.mapToScene(screen_pos)
        if isinstance(item, GraphicsCircle):
            center = QPointF(item.circle_obj.cx, item.circle_obj.cy)
            radius = item.circle_obj.radius
            dx = scene_pos.x() - center.x()
            dy = scene_pos.y() - center.y()
            dist = math.hypot(dx, dy)
            if dist > radius:
                angle = math.atan2(dy, dx)
                tx = center.x() + radius * math.cos(angle)
                ty = center.y() + radius * math.sin(angle)
                return QPointF(tx, ty)
        elif isinstance(item, GraphicsArc):
            # Simplified tangent for arc - treat as full circle
            center = QPointF(item.arc_obj.cx, item.arc_obj.cy)
            radius = item.arc_obj.radius
            dx = scene_pos.x() - center.x()
            dy = scene_pos.y() - center.y()
            dist = math.hypot(dx, dy)
            if dist > radius:
                angle = math.atan2(dy, dx)
                tx = center.x() + radius * math.cos(angle)
                ty = center.y() + radius * math.sin(angle)
                return QPointF(tx, ty)
        return None
    
    def _find_perpendicular_point(self, view, screen_pos, item):
        """Find perpendicular projection point on line/rectangle edge."""
        scene_pos = view.mapToScene(screen_pos)
        if isinstance(item, GraphicsLine):
            line = item.line()
            p1, p2 = line.p1(), line.p2()
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            if dx == 0 and dy == 0:
                return p1
            t = ((scene_pos.x() - p1.x()) * dx + (scene_pos.y() - p1.y()) * dy) / (dx*dx + dy*dy)
            t = max(0, min(1, t))  # Clamp to segment
            px = p1.x() + t * dx
            py = p1.y() + t * dy
            return QPointF(px, py)
        elif isinstance(item, GraphicsRect):
            rect = item.rect()
            edges = [
                (rect.topLeft(), rect.topRight()),
                (rect.topRight(), rect.bottomRight()),
                (rect.bottomRight(), rect.bottomLeft()),
                (rect.bottomLeft(), rect.topLeft()),
            ]
            best_perp = None
            best_dist = float('inf')
            for p1, p2 in edges:
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                if dx == 0 and dy == 0:
                    continue
                t = ((scene_pos.x() - p1.x()) * dx + (scene_pos.y() - p1.y()) * dy) / (dx*dx + dy*dy)
                t = max(0, min(1, t))
                px = p1.x() + t * dx
                py = p1.y() + t * dy
                dist = math.hypot(scene_pos.x() - px, scene_pos.y() - py)
                if dist < best_dist:
                    best_dist = dist
                    best_perp = QPointF(px, py)
            return best_perp
        return None
    
    def _find_intersections_near(self, view, screen_pos):
        """Find intersection points near the mouse position."""
        scene_pos = view.mapToScene(screen_pos)
        intersections = []
        items = list(self.scene.items())
        
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                pts = self._get_item_intersections(item1, item2)
                for p in pts:
                    if math.hypot(p.x() - scene_pos.x(), p.y() - scene_pos.y()) < 50:
                        intersections.append(p)
        return intersections
    
    def _get_item_intersections(self, item1, item2):
        """Get intersection points between two items."""
        intersections = []
        
        # Line-Line intersection
        if isinstance(item1, GraphicsLine) and isinstance(item2, GraphicsLine):
            l1 = item1.line()
            l2 = item2.line()
            pt = self._line_line_intersection(l1.p1(), l1.p2(), l2.p1(), l2.p2())
            if pt:
                intersections.append(pt)
        
        # Line-Rect intersection (check all edges)
        if isinstance(item1, GraphicsLine) and isinstance(item2, GraphicsRect):
            rect = item2.rect()
            edges = [
                (rect.topLeft(), rect.topRight()),
                (rect.topRight(), rect.bottomRight()),
                (rect.bottomRight(), rect.bottomLeft()),
                (rect.bottomLeft(), rect.topLeft()),
            ]
            line = item1.line()
            for p1, p2 in edges:
                pt = self._line_line_intersection(line.p1(), line.p2(), p1, p2)
                if pt:
                    intersections.append(pt)
        
        if isinstance(item1, GraphicsRect) and isinstance(item2, GraphicsLine):
            rect = item1.rect()
            edges = [
                (rect.topLeft(), rect.topRight()),
                (rect.topRight(), rect.bottomRight()),
                (rect.bottomRight(), rect.bottomLeft()),
                (rect.bottomLeft(), rect.topLeft()),
            ]
            line = item2.line()
            for p1, p2 in edges:
                pt = self._line_line_intersection(p1, p2, line.p1(), line.p2())
                if pt:
                    intersections.append(pt)
        
        return intersections
    
    def _line_line_intersection(self, p1, p2, p3, p4):
        """Calculate intersection point of two line segments."""
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        x3, y3 = p3.x(), p3.y()
        x4, y4 = p4.x(), p4.y()
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return QPointF(x, y)
        return None

    def snap_point(self, view, screen_pos):
        point, _ = self.get_snap_info(view, screen_pos)
        return point if point else view.mapToScene(screen_pos)

# ------------------ Кастомный вид для рисования ------------------
class CadView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.tool = "Select"
        self.start_point = None
        self.temp_item = None
        self.snap_manager = None
        self.dim_type = "Linear"
        self.parent_window = parent
        self.tooltip_item = None
        self.hovered_item = None
        self.original_pen = None
        self.original_color = None
        self.hint_item = None
        self.setCursor(Qt.ArrowCursor)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1/factor, 1/factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.parent_window.set_tool("Select")
            if self.temp_item:
                self.scene().removeItem(self.temp_item)
                self.temp_item = None
            self.start_point = None
        elif event.key() == Qt.Key_Delete:
            self.parent_window.delete_selected()
        elif event.key() == Qt.Key_L or event.key() == Qt.Key_l:
            self.parent_window.set_tool("Line")
        elif event.key() == Qt.Key_C or event.key() == Qt.Key_c:
            self.parent_window.set_tool("Circle")
        else:
            super().keyPressEvent(event)

    def setScene(self, scene):
        super().setScene(scene)
        if self.snap_manager is None:
            self.snap_manager = SnapManager(scene)
        else:
            self.snap_manager.scene = scene

    def set_tool(self, tool):
        self.tool = tool
        self.start_point = None
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
        if self.tooltip_item:
            self.scene().removeItem(self.tooltip_item)
            self.tooltip_item = None
        if self.hint_item:
            self.hint_item.hide()
        if tool == "Select":
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def set_dim_type(self, dim_type):
        self.dim_type = dim_type

    def mousePressEvent(self, event):
        if self.tool == "Select":
            super().mousePressEvent(event)
            return
        if self.tool == "Trim":
            return

        pos = self.mapToScene(event.pos())
        if self.snap_manager:
            pos = self.snap_manager.snap_point(self, event.pos())

        if event.button() == Qt.LeftButton:
            if self.start_point is None:
                self.start_point = pos
                if self.tool == "Line":
                    self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
                    self.temp_item.setPen(QPen(QColor(0,0,255), 0.2, Qt.DashLine))
                    self.scene().addItem(self.temp_item)
                elif self.tool == "Circle":
                    self.temp_item = QGraphicsEllipseItem()
                    self.temp_item.setPen(QPen(QColor(0,0,255), 0.2, Qt.DashLine))
                    self.scene().addItem(self.temp_item)
                elif self.tool == "Rect":
                    self.temp_item = QGraphicsRectItem()
                    self.temp_item.setPen(QPen(QColor(0,0,255), 0.2, Qt.DashLine))
                    self.scene().addItem(self.temp_item)
                elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
                    self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
                    self.temp_item.setPen(QPen(QColor(0,0,255), 0.2, Qt.DashLine))
                    self.scene().addItem(self.temp_item)
            else:
                self.finish_drawing(pos)
        elif event.button() == Qt.RightButton:
            if self.temp_item:
                self.scene().removeItem(self.temp_item)
                self.temp_item = None
            self.start_point = None
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Подсказка инструмента
        if self.tool != "Select":
            if self.tooltip_item is None:
                self.tooltip_item = QGraphicsSimpleTextItem()
                self.tooltip_item.setBrush(QBrush(QColor(0,0,0)))
                self.tooltip_item.setFont(QFont("Arial", 8))
                self.tooltip_item.setZValue(10000)
                self.scene().addItem(self.tooltip_item)
            self.tooltip_item.setText(self.tool)
            scene_pos = self.mapToScene(event.pos())
            self.tooltip_item.setPos(scene_pos.x() + 10, scene_pos.y() - 20)
            self.tooltip_item.show()
        else:
            if self.tooltip_item:
                self.tooltip_item.hide()

        # Подсветка объектов в режиме выбора
        if self.tool == "Select":
            pos = self.mapToScene(event.pos())
            item = self.scene().itemAt(pos, QTransform())
            if item != self.hovered_item:
                self.clear_highlight()
                self.hovered_item = item
                if item and item.flags() & QGraphicsItem.ItemIsSelectable:
                    self.highlight_item(item)
        else:
            self.clear_highlight()

        # Подсказка привязки
        if self.snap_manager and self.tool != "Select":
            point, hint = self.snap_manager.get_snap_info(self, event.pos())
            if point and hint:
                if self.hint_item is None:
                    self.hint_item = QGraphicsSimpleTextItem()
                    self.hint_item.setBrush(QBrush(QColor(255,0,0)))
                    self.hint_item.setFont(QFont("Arial", 8, QFont.Bold))
                    self.hint_item.setZValue(10001)
                    self.scene().addItem(self.hint_item)
                self.hint_item.setText(hint)
                self.hint_item.setPos(point.x() + 10, point.y() - 20)
                self.hint_item.show()
            else:
                if self.hint_item:
                    self.hint_item.hide()
        else:
            if self.hint_item:
                self.hint_item.hide()

        # Временные объекты
        if self.start_point and self.temp_item:
            pos = self.mapToScene(event.pos())
            if self.snap_manager:
                pos = self.snap_manager.snap_point(self, event.pos())
            if self.tool == "Line":
                self.temp_item.setLine(QLineF(self.start_point, pos))
            elif self.tool == "Circle":
                dx = pos.x() - self.start_point.x()
                dy = pos.y() - self.start_point.y()
                r = math.hypot(dx, dy)
                rect = QRectF(self.start_point.x() - r, self.start_point.y() - r, 2*r, 2*r)
                self.temp_item.setRect(rect)
            elif self.tool == "Rect":
                x1 = self.start_point.x()
                y1 = self.start_point.y()
                x2 = pos.x()
                y2 = pos.y()
                rect = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
                self.temp_item.setRect(rect)
            elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
                self.temp_item.setLine(QLineF(self.start_point, pos))
        else:
            super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        if self.tool == "Select":
            super().contextMenuEvent(event)
            return
        if not self.snap_manager:
            return
        menu = QMenu(self)
        snap_end_action = QAction("Snap to endpoints", self)
        snap_end_action.setCheckable(True)
        snap_end_action.setChecked(self.snap_manager.snap_to_endpoints)
        snap_end_action.triggered.connect(lambda checked: self.set_snap_endpoints(checked))
        menu.addAction(snap_end_action)
        snap_center_action = QAction("Snap to centers", self)
        snap_center_action.setCheckable(True)
        snap_center_action.setChecked(self.snap_manager.snap_to_center)
        snap_center_action.triggered.connect(lambda checked: self.set_snap_center(checked))
        menu.addAction(snap_center_action)
        menu.exec_(event.globalPos())

    def set_snap_endpoints(self, enabled):
        self.snap_manager.snap_to_endpoints = enabled
        self.parent_window.update_snap_settings(enabled, self.snap_manager.snap_to_center,
                                                 self.snap_manager.snap_to_midpoint,
                                                 self.snap_manager.snap_to_intersection,
                                                 self.snap_manager.snap_to_tangent,
                                                 self.snap_manager.snap_to_perpendicular)

    def set_snap_center(self, enabled):
        self.snap_manager.snap_to_center = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints, enabled,
                                                 self.snap_manager.snap_to_midpoint,
                                                 self.snap_manager.snap_to_intersection,
                                                 self.snap_manager.snap_to_tangent,
                                                 self.snap_manager.snap_to_perpendicular)

    def set_snap_midpoint(self, enabled):
        self.snap_manager.snap_to_midpoint = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints,
                                                 self.snap_manager.snap_to_center,
                                                 enabled,
                                                 self.snap_manager.snap_to_intersection,
                                                 self.snap_manager.snap_to_tangent,
                                                 self.snap_manager.snap_to_perpendicular)

    def set_snap_intersection(self, enabled):
        self.snap_manager.snap_to_intersection = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints,
                                                 self.snap_manager.snap_to_center,
                                                 self.snap_manager.snap_to_midpoint,
                                                 enabled,
                                                 self.snap_manager.snap_to_tangent,
                                                 self.snap_manager.snap_to_perpendicular)

    def set_snap_tangent(self, enabled):
        self.snap_manager.snap_to_tangent = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints,
                                                 self.snap_manager.snap_to_center,
                                                 self.snap_manager.snap_to_midpoint,
                                                 self.snap_manager.snap_to_intersection,
                                                 enabled,
                                                 self.snap_manager.snap_to_perpendicular)

    def set_snap_perpendicular(self, enabled):
        self.snap_manager.snap_to_perpendicular = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints,
                                                 self.snap_manager.snap_to_center,
                                                 self.snap_manager.snap_to_midpoint,
                                                 self.snap_manager.snap_to_intersection,
                                                 self.snap_manager.snap_to_tangent,
                                                 enabled)

    def highlight_item(self, item):
        if hasattr(item, 'pen'):
            self.original_pen = item.pen()
            new_pen = QPen(QColor(255, 0, 0), self.original_pen.widthF() + 0.2)
            new_pen.setStyle(self.original_pen.style())
            item.setPen(new_pen)
        elif isinstance(item, QGraphicsTextItem):
            self.original_color = item.defaultTextColor()
            item.setDefaultTextColor(QColor(255, 0, 0))

    def clear_highlight(self):
        if self.hovered_item:
            if hasattr(self.hovered_item, 'pen') and self.original_pen is not None:
                self.hovered_item.setPen(self.original_pen)
            elif isinstance(self.hovered_item, QGraphicsTextItem) and self.original_color is not None:
                self.hovered_item.setDefaultTextColor(self.original_color)
            self.hovered_item = None
            self.original_pen = None
            self.original_color = None

    def finish_drawing(self, pos):
        if self.tool == "Line":
            self.parent_window.add_line(self.start_point.x(), self.start_point.y(), pos.x(), pos.y())
        elif self.tool == "Circle":
            r = math.hypot(pos.x() - self.start_point.x(), pos.y() - self.start_point.y())
            self.parent_window.add_circle(self.start_point.x(), self.start_point.y(), r)
        elif self.tool == "Rect":
            self.parent_window.add_rectangle(self.start_point.x(), self.start_point.y(), pos.x(), pos.y())
        elif self.tool == "Arc":
            dlg = QDialog(self.parent_window)
            dlg.setWindowTitle("Arc")
            layout = QFormLayout(dlg)
            r_edit = QLineEdit("10")
            s_edit = QLineEdit("0")
            e_edit = QLineEdit("90")
            layout.addRow("Radius:", r_edit)
            layout.addRow("Start angle:", s_edit)
            layout.addRow("End angle:", e_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                r = float(r_edit.text())
                sa = float(s_edit.text())
                ea = float(e_edit.text())
                self.parent_window.add_arc(self.start_point.x(), self.start_point.y(), r, sa, ea)
        elif self.tool == "Text":
            text, ok = QInputDialog.getText(self.parent_window, "Text", "Enter text:")
            if ok and text:
                self.parent_window.add_text(self.start_point.x(), self.start_point.y(), text)
        elif self.tool == "Dim":
            self.parent_window.add_dimension(self.start_point, pos, "Linear")
        elif self.tool == "RadiusDim":
            radius, ok = QInputDialog.getDouble(self.parent_window, "Radius", "Enter radius:")
            if ok:
                self.parent_window.add_radius_dim(self.start_point, radius)
        elif self.tool == "DiameterDim":
            diam, ok = QInputDialog.getDouble(self.parent_window, "Diameter", "Enter diameter:")
            if ok:
                self.parent_window.add_diameter_dim(self.start_point, diam)
        elif self.tool == "AngularDim":
            angle, ok = QInputDialog.getDouble(self.parent_window, "Angle", "Enter angle (degrees):")
            if ok:
                self.parent_window.add_angular_dim(self.start_point, angle)

        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
        self.start_point = None

# ------------------ Диалог свойств ------------------
class PropertyDialog(QDialog):
    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.setWindowTitle("Object Properties")
        layout = QFormLayout(self)

        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addRow("Color:", self.color_btn)

        pen_width = obj.graphics_item.pen().widthF() if hasattr(obj.graphics_item, 'pen') else 0.2
        self.width_edit = QLineEdit(str(pen_width))
        layout.addRow("Line width:", self.width_edit)

        self.linetype_combo = QComboBox()
        self.linetype_combo.addItems(["Solid", "Dash", "DashDot"])
        layout.addRow("Line type:", self.linetype_combo)

        btn = QPushButton("Apply")
        btn.clicked.connect(self.apply)
        layout.addRow(btn)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.color_btn.color = color

    def apply(self):
        item = self.obj.graphics_item
        if hasattr(item, 'pen'):
            pen = item.pen()
            if hasattr(self.color_btn, 'color'):
                pen.setColor(self.color_btn.color)
            pen.setWidthF(float(self.width_edit.text()))
            linetype = self.linetype_combo.currentText()
            if linetype == "Dash":
                pen.setStyle(Qt.DashLine)
            elif linetype == "DashDot":
                pen.setStyle(Qt.DashDotLine)
            else:
                pen.setStyle(Qt.SolidLine)
            item.setPen(pen)

            if self.obj.dxf_entity:
                color = pen.color()
                try:
                    self.obj.dxf_entity.dxf.rgb = (color.red(), color.green(), color.blue())
                except AttributeError:
                    r, g, b = color.red(), color.green(), color.blue()
                    if (r, g, b) == (255, 0, 0):
                        idx = 1
                    elif (r, g, b) == (255, 255, 0):
                        idx = 2
                    elif (r, g, b) == (0, 255, 0):
                        idx = 3
                    elif (r, g, b) == (0, 255, 255):
                        idx = 4
                    elif (r, g, b) == (0, 0, 255):
                        idx = 5
                    elif (r, g, b) == (255, 0, 255):
                        idx = 6
                    else:
                        idx = 7
                    self.obj.dxf_entity.dxf.color = idx

                if pen.style() == Qt.DashLine:
                    self.obj.dxf_entity.dxf.linetype = "DASHED"
                elif pen.style() == Qt.DashDotLine:
                    self.obj.dxf_entity.dxf.linetype = "DASHDOT"
                else:
                    self.obj.dxf_entity.dxf.linetype = "CONTINUOUS"
        self.accept()

# ------------------ Основное окно ------------------
class CadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DXF Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Paper settings
        self.current_paper = "A4"
        self.paper_landscape = True
        
        # Color settings
        self.background_color = DEFAULT_BACKGROUND_COLOR
        self.object_color = DEFAULT_OBJECT_COLOR
        
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(self.background_color))
        self.view = CadView(self)
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.dxf_doc = None
        self.dxf_modelspace = None
        self.obj_map = {}
        self.current_file = None

        self.init_ui()
        self.init_statusbar()
        self.create_empty_document()
        self.update_paper_bounds()
        self.load_settings()

    def init_ui(self):
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_document)
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.save_as_file)
        export_pdf_action = QAction("Export PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        export_html_action = QAction("Export HTML", self)
        export_html_action.triggered.connect(self.export_html)
        
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(export_pdf_action)
        file_menu.addAction(export_html_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        fit_action = QAction("Fit to Window", self)
        fit_action.triggered.connect(self.fit_content_to_window)
        view_menu.addAction(fit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        colors_action = QAction("Colors...", self)
        colors_action.triggered.connect(self.show_color_settings)
        settings_menu.addAction(colors_action)
        
        toolbar = self.addToolBar("Tools")
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addAction(save_as_action)
        toolbar.addAction(export_pdf_action)
        toolbar.addAction(export_html_action)
        toolbar.addSeparator()

        select_action = QAction("Select", self)
        select_action.triggered.connect(lambda: self.set_tool("Select"))
        line_action = QAction("Line", self)
        line_action.triggered.connect(lambda: self.set_tool("Line"))
        circle_action = QAction("Circle", self)
        circle_action.triggered.connect(lambda: self.set_tool("Circle"))
        rect_action = QAction("Rectangle", self)
        rect_action.triggered.connect(lambda: self.set_tool("Rect"))
        arc_action = QAction("Arc", self)
        arc_action.triggered.connect(lambda: self.set_tool("Arc"))
        text_action = QAction("Text", self)
        text_action.triggered.connect(lambda: self.set_tool("Text"))
        trim_action = QAction("Trim", self)
        trim_action.triggered.connect(lambda: self.set_tool("Trim"))

        toolbar.addAction(select_action)
        toolbar.addAction(line_action)
        toolbar.addAction(circle_action)
        toolbar.addAction(rect_action)
        toolbar.addAction(arc_action)
        toolbar.addAction(text_action)
        toolbar.addAction(trim_action)
        toolbar.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_action)

        self.dim_type_combo = QComboBox()
        self.dim_type_combo.addItems(["Linear", "Radius", "Diameter", "Angular"])
        self.dim_type_combo.currentTextChanged.connect(self.on_dim_type_changed)
        dim_action = QAction("Dimension", self)
        dim_action.triggered.connect(lambda: self.set_tool("Dim"))
        toolbar.addWidget(QLabel("Dim type:"))
        toolbar.addWidget(self.dim_type_combo)
        toolbar.addAction(dim_action)

        # Панель объектов слева
        left_dock = QDockWidget("Objects", self)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_object_selected)
        container_left = QWidget()
        layout_left = QVBoxLayout(container_left)
        layout_left.addWidget(self.list_widget)
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_selected)
        layout_left.addWidget(edit_button)
        left_dock.setWidget(container_left)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)

        # Панель настроек справа
        right_dock = QDockWidget("Settings", self)
        container_right = QWidget()
        layout_right = QVBoxLayout(container_right)

        # Paper settings group
        paper_group = QGroupBox("Paper Settings")
        paper_layout = QFormLayout()
        
        self.paper_size_combo = QComboBox()
        self.paper_size_combo.addItems(["A0", "A1", "A2", "A3", "A4"])
        self.paper_size_combo.setCurrentText("A4")
        self.paper_size_combo.currentTextChanged.connect(self.on_paper_size_changed)
        paper_layout.addRow("Size:", self.paper_size_combo)
        
        self.paper_orientation_combo = QComboBox()
        self.paper_orientation_combo.addItems(["Landscape", "Portrait"])
        self.paper_orientation_combo.setCurrentText("Landscape")
        self.paper_orientation_combo.currentTextChanged.connect(self.on_paper_orientation_changed)
        paper_layout.addRow("Orientation:", self.paper_orientation_combo)
        
        paper_group.setLayout(paper_layout)
        layout_right.addWidget(paper_group)

        snap_group = QGroupBox("Snap Settings")
        snap_layout = QVBoxLayout()
        self.snap_end_check = QCheckBox("Snap to endpoints")
        self.snap_end_check.setChecked(True)
        self.snap_end_check.toggled.connect(self.on_snap_end_toggled)
        self.snap_center_check = QCheckBox("Snap to centers")
        self.snap_center_check.setChecked(True)
        self.snap_center_check.toggled.connect(self.on_snap_center_toggled)
        self.snap_mid_check = QCheckBox("Snap to midpoints")
        self.snap_mid_check.setChecked(True)
        self.snap_mid_check.toggled.connect(self.on_snap_mid_toggled)
        self.snap_int_check = QCheckBox("Snap to intersections")
        self.snap_int_check.setChecked(True)
        self.snap_int_check.toggled.connect(self.on_snap_int_toggled)
        self.snap_tan_check = QCheckBox("Snap to tangent")
        self.snap_tan_check.setChecked(False)
        self.snap_tan_check.toggled.connect(self.on_snap_tan_toggled)
        self.snap_perp_check = QCheckBox("Snap to perpendicular")
        self.snap_perp_check.setChecked(False)
        self.snap_perp_check.toggled.connect(self.on_snap_perp_toggled)
        snap_layout.addWidget(self.snap_end_check)
        snap_layout.addWidget(self.snap_center_check)
        snap_layout.addWidget(self.snap_mid_check)
        snap_layout.addWidget(self.snap_int_check)
        snap_layout.addWidget(self.snap_tan_check)
        snap_layout.addWidget(self.snap_perp_check)
        snap_group.setLayout(snap_layout)
        layout_right.addWidget(snap_group)

        style_group = QGroupBox("Line Style")
        style_layout = QFormLayout()
        self.line_color_btn = QPushButton("Choose Color")
        self.line_color_btn.clicked.connect(self.choose_line_color)
        style_layout.addRow("Color:", self.line_color_btn)
        self.line_width_edit = QLineEdit("0.2")
        style_layout.addRow("Width:", self.line_width_edit)
        self.line_type_combo = QComboBox()
        self.line_type_combo.addItems(["Solid", "Dash", "DashDot"])
        style_layout.addRow("Type:", self.line_type_combo)
        style_group.setLayout(style_layout)
        layout_right.addWidget(style_group)

        apply_style_btn = QPushButton("Apply Style to Selected")
        apply_style_btn.clicked.connect(self.apply_style_to_selected)
        layout_right.addWidget(apply_style_btn)

        prop_group = QGroupBox("Selected Object Properties")
        prop_layout = QFormLayout()
        self.prop_type = QLabel("")
        self.prop_start = QLabel("")
        self.prop_end = QLabel("")
        self.prop_linetype = QLabel("")
        self.prop_color = QLabel("")
        self.prop_width = QLabel("")
        prop_layout.addRow("Type:", self.prop_type)
        prop_layout.addRow("Start:", self.prop_start)
        prop_layout.addRow("End:", self.prop_end)
        prop_layout.addRow("Line type:", self.prop_linetype)
        prop_layout.addRow("Color:", self.prop_color)
        prop_layout.addRow("Width:", self.prop_width)
        prop_group.setLayout(prop_layout)
        layout_right.addWidget(prop_group)

        container_right.setLayout(layout_right)
        right_dock.setWidget(container_right)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

        self.current_line_color = QColor(0,0,0)
        self.current_line_width = 0.2
        self.current_line_type = "Solid"
        self.line_color_btn.setStyleSheet("background-color: black")
        self.line_color_btn.color = self.current_line_color

        self.scene.selectionChanged.connect(self.update_selected_properties)

    def init_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Ready")
        self.status.addWidget(self.status_label)
    
    def load_settings(self):
        """Load user settings from QSettings."""
        settings = QSettings("DXFEditor", "Settings")
        
        # Load color settings
        bg_color = settings.value("background_color", DEFAULT_BACKGROUND_COLOR)
        obj_color = settings.value("object_color", DEFAULT_OBJECT_COLOR)
        
        if isinstance(bg_color, str):
            bg_color = QColor(bg_color)
        if isinstance(obj_color, str):
            obj_color = QColor(obj_color)
            
        self.background_color = bg_color
        self.object_color = obj_color
        self.scene.setBackgroundBrush(QBrush(self.background_color))
        
        # Update button color if it exists
        if hasattr(self, 'line_color_btn'):
            self.line_color_btn.setStyleSheet(f"background-color: {self.object_color.name()}")
            self.line_color_btn.color = self.object_color
    
    def save_settings(self):
        """Save user settings to QSettings."""
        settings = QSettings("DXFEditor", "Settings")
        settings.setValue("background_color", self.background_color.name())
        settings.setValue("object_color", self.object_color.name())
    
    def show_color_settings(self):
        """Show color settings dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Color Settings")
        layout = QFormLayout(dialog)
        
        bg_btn = QPushButton("Background Color")
        bg_btn.setStyleSheet(f"background-color: {self.background_color.name()}")
        bg_btn.clicked.connect(lambda: self.choose_background_color(bg_btn))
        layout.addRow("Background:", bg_btn)
        
        obj_btn = QPushButton("Object Color")
        obj_btn.setStyleSheet(f"background-color: {self.object_color.name()}")
        obj_btn.clicked.connect(lambda: self.choose_object_color(obj_btn))
        layout.addRow("Objects:", obj_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        layout.addRow(ok_btn)
        
        dialog.exec_()
        self.save_settings()
    
    def choose_background_color(self, btn):
        """Choose background color."""
        color = QColorDialog.getColor(self.background_color, self, "Select Background Color")
        if color.isValid():
            self.background_color = color
            self.scene.setBackgroundBrush(QBrush(color))
            btn.setStyleSheet(f"background-color: {color.name()}")
    
    def choose_object_color(self, btn):
        """Choose object color."""
        color = QColorDialog.getColor(self.object_color, self, "Select Object Color")
        if color.isValid():
            self.object_color = color
            btn.setStyleSheet(f"background-color: {color.name()}")
            # Apply to all existing objects
            for item in self.scene.items():
                if hasattr(item, 'setPen') and not hasattr(item, '_is_paper_border'):
                    pen = item.pen()
                    pen.setColor(color)
                    item.setPen(pen)
                elif hasattr(item, 'setDefaultTextColor'):
                    item.setDefaultTextColor(color)
    
    def fit_content_to_window(self):
        """Fit all content to the window with margins."""
        # Get all items except paper border
        drawing_items = [item for item in self.scene.items() 
                        if not (isinstance(item, QGraphicsRectItem) and hasattr(item, '_is_paper_border'))]
        
        if not drawing_items:
            # If no drawing items, fit to paper bounds
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            return
        
        # Calculate bounding box of all drawing items
        bbox = drawing_items[0].sceneBoundingRect()
        for item in drawing_items[1:]:
            bbox = bbox.united(item.sceneBoundingRect())
        
        if bbox.isEmpty():
            return
        
        # Add 10% margin
        margin_x = bbox.width() * 0.1
        margin_y = bbox.height() * 0.1
        bbox.adjust(-margin_x, -margin_y, margin_x, margin_y)
        
        self.view.fitInView(bbox, Qt.KeepAspectRatio)
    
    def update_paper_bounds(self):
        """Update the scene rect to show paper bounds."""
        width_mm, height_mm = PAPER_SIZES.get(self.current_paper, PAPER_SIZES["A4"])
        if self.paper_landscape:
            width_mm, height_mm = height_mm, width_mm
        
        # Convert mm to scene units (1 unit = 1mm)
        scene_rect = QRectF(-width_mm/2, -height_mm/2, width_mm, height_mm)
        self.scene.setSceneRect(scene_rect)
        
        # Draw paper border
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, '_is_paper_border'):
                self.scene.removeItem(item)
        
        border = QGraphicsRectItem(scene_rect)
        border._is_paper_border = True
        border.setPen(QPen(QColor(200, 200, 200), 0.5, Qt.DashLine))
        border.setFlag(QGraphicsItem.ItemIsSelectable, False)
        border.setZValue(-1000)
        self.scene.addItem(border)
        
        self.status_label.setText(f"Paper: {self.current_paper} {'(Landscape)' if self.paper_landscape else '(Portrait)'}")

    def create_empty_document(self):
        self.dxf_doc = ezdxf.new('R2010')
        self.dxf_modelspace = self.dxf_doc.modelspace()
        self.current_file = None
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()
        self.status_label.setText("New document (unsaved)")
        self.update_paper_bounds()
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def set_tool(self, tool):
        self.view.set_tool(tool)
        self.status_label.setText(f"Tool: {tool}")

    def on_dim_type_changed(self, text):
        self.view.dim_type = text

    def on_paper_size_changed(self, text):
        self.current_paper = text
        self.update_paper_bounds()

    def on_paper_orientation_changed(self, text):
        self.paper_landscape = (text == "Landscape")
        self.update_paper_bounds()

    def on_snap_end_toggled(self, checked):
        self.view.set_snap_endpoints(checked)

    def on_snap_center_toggled(self, checked):
        self.view.set_snap_center(checked)

    def on_snap_mid_toggled(self, checked):
        self.view.set_snap_midpoint(checked)

    def on_snap_int_toggled(self, checked):
        self.view.set_snap_intersection(checked)

    def on_snap_tan_toggled(self, checked):
        self.view.set_snap_tangent(checked)

    def on_snap_perp_toggled(self, checked):
        self.view.set_snap_perpendicular(checked)

    def update_snap_settings(self, snap_end, snap_center, snap_mid=None, snap_int=None, snap_tan=None, snap_perp=None):
        self.snap_end_check.blockSignals(True)
        self.snap_center_check.blockSignals(True)
        self.snap_end_check.setChecked(snap_end)
        self.snap_center_check.setChecked(snap_center)
        self.snap_end_check.blockSignals(False)
        self.snap_center_check.blockSignals(False)
        if snap_mid is not None:
            self.snap_mid_check.blockSignals(True)
            self.snap_mid_check.setChecked(snap_mid)
            self.snap_mid_check.blockSignals(False)
        if snap_int is not None:
            self.snap_int_check.blockSignals(True)
            self.snap_int_check.setChecked(snap_int)
            self.snap_int_check.blockSignals(False)
        if snap_tan is not None:
            self.snap_tan_check.blockSignals(True)
            self.snap_tan_check.setChecked(snap_tan)
            self.snap_tan_check.blockSignals(False)
        if snap_perp is not None:
            self.snap_perp_check.blockSignals(True)
            self.snap_perp_check.setChecked(snap_perp)
            self.snap_perp_check.blockSignals(False)

    def choose_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_line_color = color
            self.line_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.line_color_btn.color = color

    def apply_style_to_selected(self):
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        for item in selected:
            for obj in self.obj_map.values():
                if obj.graphics_item == item:
                    if hasattr(item, 'pen'):
                        pen = item.pen()
                        pen.setColor(self.current_line_color)
                        pen.setWidthF(float(self.line_width_edit.text()))
                        lt = self.line_type_combo.currentText()
                        if lt == "Dash":
                            pen.setStyle(Qt.DashLine)
                        elif lt == "DashDot":
                            pen.setStyle(Qt.DashDotLine)
                        else:
                            pen.setStyle(Qt.SolidLine)
                        item.setPen(pen)
                        if obj.dxf_entity:
                            color = pen.color()
                            try:
                                obj.dxf_entity.dxf.rgb = (color.red(), color.green(), color.blue())
                            except AttributeError:
                                r, g, b = color.red(), color.green(), color.blue()
                                if (r, g, b) == (255, 0, 0):
                                    idx = 1
                                elif (r, g, b) == (255, 255, 0):
                                    idx = 2
                                elif (r, g, b) == (0, 255, 0):
                                    idx = 3
                                elif (r, g, b) == (0, 255, 255):
                                    idx = 4
                                elif (r, g, b) == (0, 0, 255):
                                    idx = 5
                                elif (r, g, b) == (255, 0, 255):
                                    idx = 6
                                else:
                                    idx = 7
                                obj.dxf_entity.dxf.color = idx
                            if pen.style() == Qt.DashLine:
                                obj.dxf_entity.dxf.linetype = "DASHED"
                            elif pen.style() == Qt.DashDotLine:
                                obj.dxf_entity.dxf.linetype = "DASHDOT"
                            else:
                                obj.dxf_entity.dxf.linetype = "CONTINUOUS"
                    break
        self.update_selected_properties()
        QMessageBox.information(self, "Done", "Style applied to selected object(s).")

    def delete_selected(self):
        selected = self.scene.selectedItems()
        if not selected:
            return
        for item in selected:
            for obj in list(self.obj_map.keys()):
                if self.obj_map[obj].graphics_item == item:
                    if obj is not None and obj in self.obj_map:
                        del self.obj_map[obj]
                    break
            self.scene.removeItem(item)
        self.update_list()
        self.update_selected_properties()

    def update_selected_properties(self):
        selected = self.scene.selectedItems()
        if not selected:
            self.prop_type.setText("")
            self.prop_start.setText("")
            self.prop_end.setText("")
            self.prop_linetype.setText("")
            self.prop_color.setText("")
            self.prop_width.setText("")
            return
        item = selected[0]
        for obj in self.obj_map.values():
            if obj.graphics_item == item:
                self.prop_type.setText(obj.type)
                if obj.type == "Line":
                    self.prop_start.setText(f"({obj.x1:.2f}, {obj.y1:.2f})")
                    self.prop_end.setText(f"({obj.x2:.2f}, {obj.y2:.2f})")
                elif obj.type == "Circle":
                    self.prop_start.setText(f"Center: ({obj.cx:.2f}, {obj.cy:.2f})")
                    self.prop_end.setText(f"Radius: {obj.radius:.2f}")
                elif obj.type == "Rectangle":
                    self.prop_start.setText(f"({obj.x1:.2f}, {obj.y1:.2f})")
                    self.prop_end.setText(f"({obj.x2:.2f}, {obj.y2:.2f})")
                else:
                    self.prop_start.setText("")
                    self.prop_end.setText("")
                if hasattr(item, 'pen'):
                    pen = item.pen()
                    style_map = {Qt.SolidLine: "Solid", Qt.DashLine: "Dash", Qt.DashDotLine: "DashDot"}
                    self.prop_linetype.setText(style_map.get(pen.style(), "Solid"))
                    self.prop_color.setText(pen.color().name())
                    self.prop_width.setText(f"{pen.widthF():.2f}")
                break

    def new_document(self):
        if self.dxf_doc and self.obj_map:
            reply = QMessageBox.question(self, "Save changes?",
                                         "Do you want to save changes before creating a new document?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        self.create_empty_document()

    def open_file(self):
        if self.dxf_doc and self.obj_map:
            reply = QMessageBox.question(self, "Save changes?",
                                         "Do you want to save changes before opening another file?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        fname, _ = QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF Files (*.dxf)")
        if not fname:
            return
        try:
            self.dxf_doc = ezdxf.readfile(fname)
            self.dxf_modelspace = self.dxf_doc.modelspace()
            self.current_file = fname
            self.load_dxf_entities()
            self.status_label.setText(f"Loaded: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{str(e)}")
            traceback.print_exc()

    def save_file(self):
        if not self.dxf_doc:
            QMessageBox.warning(self, "Warning", "No document opened.")
            return
        if not self.current_file:
            self.save_as_file()
            return
        try:
            self._sync_dxf()
            self.dxf_doc.saveas(self.current_file)
            QMessageBox.information(self, "Saved", f"File saved to {self.current_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

    def save_as_file(self):
        if not self.dxf_doc:
            QMessageBox.warning(self, "Warning", "No document opened.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Save DXF", "", "DXF Files (*.dxf)")
        if not fname:
            return
        versions = ["R12", "R2000", "R2004", "R2007", "R2010"]
        version, ok = QInputDialog.getItem(self, "DXF Version", "Select DXF version:", versions, 4, False)
        if not ok:
            return
        try:
            new_doc = ezdxf.new(version)
            new_doc.modelspace().add_entities(list(self.dxf_modelspace))
            new_doc.saveas(fname)
            self.current_file = fname
            self.dxf_doc = new_doc
            self.dxf_modelspace = self.dxf_doc.modelspace()
            QMessageBox.information(self, "Saved", f"File saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

    def export_pdf(self):
        """Export current scene to PDF with paper size settings."""
        # First fit content to window to ensure proper scaling
        self.fit_content_to_window()
        
        # Get all items except paper border
        drawing_items = [item for item in self.scene.items() 
                        if not (isinstance(item, QGraphicsRectItem) and hasattr(item, '_is_paper_border'))]
        
        if not drawing_items:
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
        if not fname:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(fname)
        
        # Set paper size based on current selection
        width_mm, height_mm = PAPER_SIZES.get(self.current_paper, PAPER_SIZES["A4"])
        if self.paper_landscape:
            width_mm, height_mm = height_mm, width_mm
            printer.setOrientation(QPrinter.Landscape)
        else:
            printer.setOrientation(QPrinter.Portrait)
        
        # Set page size in millimeters
        printer.setPageSizeMM(QSizeF(width_mm, height_mm))
        
        # Calculate bounding box of drawing items
        bbox = drawing_items[0].sceneBoundingRect()
        for item in drawing_items[1:]:
            bbox = bbox.united(item.sceneBoundingRect())
        
        if bbox.isEmpty():
            QMessageBox.warning(self, "Warning", "Empty drawing.")
            return

        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Get the page rectangle in points
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        
        # Calculate scale to fit drawing on page with margins
        margin = 20  # mm margin
        available_width = width_mm - 2 * margin
        available_height = height_mm - 2 * margin
        
        draw_width = bbox.width()
        draw_height = bbox.height()
        
        if draw_width > 0 and draw_height > 0:
            scale_x = available_width / draw_width
            scale_y = available_height / draw_height
            scale = min(scale_x, scale_y)
        else:
            scale = 1.0

        # Apply transformations
        painter.translate(page_rect.center())
        painter.scale(scale, scale)
        painter.translate(-bbox.center())

        # Render all drawing items using the view's render method
        for item in drawing_items:
            item.paint(painter, None, None)
        
        painter.end()

        QMessageBox.information(self, "Exported", f"PDF saved to {fname}")

    def export_html(self):
        """Export current scene to HTML file that works offline on any device."""
        # Get all items except paper border
        drawing_items = [item for item in self.scene.items() 
                        if not (isinstance(item, QGraphicsRectItem) and hasattr(item, '_is_paper_border'))]
        
        if not drawing_items:
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export HTML", "", "HTML Files (*.html)")
        if not fname:
            return
        
        # Get paper size for bounds display
        width_mm, height_mm = PAPER_SIZES.get(self.current_paper, PAPER_SIZES["A4"])
        if self.paper_landscape:
            width_mm, height_mm = height_mm, width_mm
        
        # Generate SVG paths for all drawing items
        svg_elements = []
        for item in drawing_items:
            svg = self._item_to_svg(item)
            if svg:
                svg_elements.append(svg)
        
        svg_content = "\n".join(svg_elements)
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drawing Export</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            background-color: white; 
            font-family: Arial, sans-serif;
            overflow: auto;
        }}
        .container {{
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .drawing-container {{
            position: relative;
            border: 2px dashed red;
            background-color: white;
        }}
        svg {{
            display: block;
            max-width: 100%;
            height: auto;
        }}
        .info {{
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="info">
        Paper: {self.current_paper} ({width_mm}x{height_mm} mm)<br>
        Items: {len(drawing_items)}
    </div>
    <div class="container">
        <div class="drawing-container" style="width: {width_mm}px; height: {height_mm}px;">
            <svg viewBox="-{width_mm/2} -{height_mm/2} {width_mm} {height_mm}" 
                 width="{width_mm}" height="{height_mm}"
                 xmlns="http://www.w3.org/2000/svg">
                {svg_content}
            </svg>
        </div>
    </div>
</body>
</html>'''
        
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(html_content)
            QMessageBox.information(self, "Exported", f"HTML saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
    
    def _item_to_svg(self, item):
        """Convert a QGraphicsItem to SVG element."""
        if isinstance(item, GraphicsLine):
            line = item.line()
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<line x1="{line.x1()}" y1="{line.y1()}" x2="{line.x2()}" y2="{line.y2()}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, GraphicsCircle):
            rect = item.rect()
            cx = rect.center().x()
            cy = rect.center().y()
            r = rect.width() / 2
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, GraphicsRect):
            rect = item.rect()
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<rect x="{rect.x()}" y="{rect.y()}" width="{rect.width()}" height="{rect.height()}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, GraphicsArc):
            path = item.path()
            if path.isEmpty():
                return ''
            # Convert QPainterPath to SVG path
            svg_path = self._path_to_svg(path)
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<path d="{svg_path}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, GraphicsText):
            text = item.toPlainText()
            pos = item.pos()
            font = item.font()
            # Escape special XML characters
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'<text x="{pos.x()}" y="{pos.y()}" font-family="Arial" font-size="{font.pointSizeF() * 1.5}" fill="black">{text}</text>'
        
        elif isinstance(item, GraphicsDimension):
            # Render dimension as group of elements
            elements = []
            for child in item.childItems():
                child_svg = self._item_to_svg(child)
                if child_svg:
                    elements.append(child_svg)
            return '\n'.join(elements)
        
        elif isinstance(item, (QGraphicsLineItem)):
            line = item.line()
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<line x1="{line.x1()}" y1="{line.y1()}" x2="{line.x2()}" y2="{line.y2()}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, (QGraphicsEllipseItem)):
            rect = item.rect()
            cx = rect.center().x()
            cy = rect.center().y()
            rx = rect.width() / 2
            ry = rect.height() / 2
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            if abs(rx - ry) < 0.01:  # Circle
                return f'<circle cx="{cx}" cy="{cy}" r="{rx}" stroke="{color}" stroke-width="{width}" fill="none"/>'
            else:  # Ellipse
                return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, (QGraphicsRectItem)):
            rect = item.rect()
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<rect x="{rect.x()}" y="{rect.y()}" width="{rect.width()}" height="{rect.height()}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        elif isinstance(item, (QGraphicsTextItem)):
            text = item.toPlainText()
            pos = item.pos()
            font = item.font()
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'<text x="{pos.x()}" y="{pos.y()}" font-family="Arial" font-size="{font.pointSizeF() * 1.5}" fill="black">{text}</text>'
        
        elif isinstance(item, (QGraphicsPathItem)):
            path = item.path()
            if path.isEmpty():
                return ''
            svg_path = self._path_to_svg(path)
            pen = item.pen()
            color = pen.color().name()
            width = max(0.1, pen.widthF())
            return f'<path d="{svg_path}" stroke="{color}" stroke-width="{width}" fill="none"/>'
        
        return ''
    
    def _path_to_svg(self, path):
        """Convert QPainterPath to SVG path data."""
        if path.isEmpty():
            return ''
        
        elements = []
        i = 0
        while i < path.elementCount():
            elem = path.elementAt(i)
            if elem.type == QPainterPath.MoveToElement:
                elements.append(f'M {elem.x} {elem.y}')
            elif elem.type == QPainterPath.LineToElement:
                elements.append(f'L {elem.x} {elem.y}')
            elif elem.type == QPainterPath.CurveToElement:
                cp1x, cp1y = elem.x, elem.y
                i += 1
                if i < path.elementCount():
                    elem2 = path.elementAt(i)
                    cp2x, cp2y = elem2.x, elem2.y
                    i += 1
                    if i < path.elementCount():
                        elem3 = path.elementAt(i)
                        ex, ey = elem3.x, elem3.y
                        elements.append(f'C {cp1x} {cp1y} {cp2x} {cp2y} {ex} {ey}')
            i += 1
        
        return ' '.join(elements)

    def _sync_dxf(self):
        for obj in self.obj_map.values():
            if obj.dxf_entity:
                if obj.type == "Point":
                    obj.dxf_entity.dxf.location = Vec3(obj.x, obj.y, 0)
                elif obj.type == "Line":
                    obj.dxf_entity.dxf.start = Vec3(obj.x1, obj.y1, 0)
                    obj.dxf_entity.dxf.end = Vec3(obj.x2, obj.y2, 0)
                elif obj.type == "Circle":
                    obj.dxf_entity.dxf.center = Vec3(obj.cx, obj.cy, 0)
                    obj.dxf_entity.dxf.radius = obj.radius
                elif obj.type == "Arc":
                    obj.dxf_entity.dxf.center = Vec3(obj.cx, obj.cy, 0)
                    obj.dxf_entity.dxf.radius = obj.radius
                    obj.dxf_entity.dxf.start_angle = obj.start_angle
                    obj.dxf_entity.dxf.end_angle = obj.end_angle
                elif obj.type == "Text":
                    obj.dxf_entity.dxf.insert = Vec3(obj.x, obj.y, 0)
                    obj.dxf_entity.dxf.text = obj.text
                    obj.dxf_entity.dxf.height = obj.height

    def load_dxf_entities(self):
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()

        for entity in self.dxf_modelspace:
            self.add_entity_to_scene(entity)

        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def add_entity_to_scene(self, entity):
        try:
            # Get color from entity or use default object color
            color = self.object_color
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'color') and entity.dxf.color:
                # Convert ACI color to QColor
                aci_color = entity.dxf.color
                if isinstance(aci_color, int) and aci_color > 0:
                    # Simple ACI color mapping (basic colors)
                    color_map = {
                        1: QColor(255, 0, 0),    # Red
                        2: QColor(255, 255, 0),  # Yellow
                        3: QColor(0, 255, 0),    # Green
                        4: QColor(0, 255, 255),  # Cyan
                        5: QColor(0, 0, 255),    # Blue
                        6: QColor(255, 0, 255),  # Magenta
                        7: QColor(255, 255, 255),# White
                    }
                    color = color_map.get(aci_color, self.object_color)
            
            pen = QPen(color, 0.2)
            
            if entity.dxftype() == 'POINT':
                x, y, z = entity.dxf.location
                obj = PointObject(x, y, entity)
                item = GraphicsPoint(obj, 0.2)
                item.setBrush(QBrush(color))
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Point ({x:.2f},{y:.2f})")
            elif entity.dxftype() == 'LINE':
                x1, y1, z1 = entity.dxf.start
                x2, y2, z2 = entity.dxf.end
                obj = LineObject(x1, y1, x2, y2, entity)
                item = GraphicsLine(obj)
                item.setPen(pen)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Line ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
            elif entity.dxftype() == 'CIRCLE':
                cx, cy, cz = entity.dxf.center
                r = entity.dxf.radius
                obj = CircleObject(cx, cy, r, entity)
                item = GraphicsCircle(obj)
                item.setPen(pen)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Circle (r={r:.2f})")
            elif entity.dxftype() == 'ARC':
                cx, cy, cz = entity.dxf.center
                r = entity.dxf.radius
                start = entity.dxf.start_angle
                end = entity.dxf.end_angle
                obj = ArcObject(cx, cy, r, start, end, entity)
                item = GraphicsArc(obj)
                item.setPen(pen)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Arc")
            elif entity.dxftype() == 'TEXT':
                insert = entity.dxf.insert
                text = entity.dxf.text
                height = entity.dxf.height
                obj = TextObject(insert.x, insert.y, text, height, entity)
                item = GraphicsText(obj)
                item.setDefaultTextColor(color)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Text: {text[:20]}")
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.vertices())
                if len(points) > 1:
                    for i in range(len(points)-1):
                        p1 = points[i]
                        p2 = points[i+1]
                        line_obj = LineObject(p1[0], p1[1], p2[0], p2[1], None)
                        item = GraphicsLine(line_obj)
                        item.setPen(pen)
                        self.scene.addItem(item)
                        self.list_widget.addItem(f"Polyline segment")
        except Exception as e:
            print(f"Error adding entity {entity.dxftype()}: {e}")

    def on_object_selected(self, item):
        text = item.text()
        for obj in self.obj_map.values():
            desc = self.object_description(obj)
            if desc == text:
                if obj.graphics_item:
                    self.scene.clearSelection()
                    obj.graphics_item.setSelected(True)
                    self.view.centerOn(obj.graphics_item)
                break

    def object_description(self, obj):
        if obj.type == "Point":
            return f"Point ({obj.x:.2f},{obj.y:.2f})"
        elif obj.type == "Line":
            return f"Line ({obj.x1:.2f},{obj.y1:.2f})-({obj.x2:.2f},{obj.y2:.2f})"
        elif obj.type == "Circle":
            return f"Circle (r={obj.radius:.2f})"
        elif obj.type == "Arc":
            return "Arc"
        elif obj.type == "Text":
            return f"Text: {obj.text[:20]}"
        return ""

    def edit_selected(self):
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Edit", "No object selected.")
            return
        item = selected[0]
        for obj in self.obj_map.values():
            if obj.graphics_item == item:
                dlg = PropertyDialog(obj, self)
                if dlg.exec_():
                    self.update_selected_properties()
                break

    def update_list(self):
        self.list_widget.clear()
        for obj in self.obj_map.values():
            self.list_widget.addItem(self.object_description(obj))

    # ------------------ Добавление примитивов ------------------
    def add_line(self, x1, y1, x2, y2):
        entity = self.dxf_modelspace.add_line((x1, y1), (x2, y2))
        obj = LineObject(x1, y1, x2, y2, entity)
        item = GraphicsLine(obj)
        pen = item.pen()
        pen.setColor(self.current_line_color)
        pen.setWidthF(float(self.line_width_edit.text()))
        lt = self.line_type_combo.currentText()
        if lt == "Dash":
            pen.setStyle(Qt.DashLine)
        elif lt == "DashDot":
            pen.setStyle(Qt.DashDotLine)
        else:
            pen.setStyle(Qt.SolidLine)
        item.setPen(pen)
        try:
            entity.dxf.rgb = (self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue())
        except AttributeError:
            r,g,b = self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue()
            if (r,g,b) == (255,0,0): idx=1
            elif (r,g,b) == (255,255,0): idx=2
            elif (r,g,b) == (0,255,0): idx=3
            elif (r,g,b) == (0,255,255): idx=4
            elif (r,g,b) == (0,0,255): idx=5
            elif (r,g,b) == (255,0,255): idx=6
            else: idx=7
            entity.dxf.color = idx
        if lt == "Dash":
            entity.dxf.linetype = "DASHED"
        elif lt == "DashDot":
            entity.dxf.linetype = "DASHDOT"
        else:
            entity.dxf.linetype = "CONTINUOUS"
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Line ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
        return item

    def add_circle(self, cx, cy, r):
        entity = self.dxf_modelspace.add_circle((cx, cy), r)
        obj = CircleObject(cx, cy, r, entity)
        item = GraphicsCircle(obj)
        pen = item.pen()
        pen.setColor(self.current_line_color)
        pen.setWidthF(float(self.line_width_edit.text()))
        lt = self.line_type_combo.currentText()
        if lt == "Dash":
            pen.setStyle(Qt.DashLine)
        elif lt == "DashDot":
            pen.setStyle(Qt.DashDotLine)
        else:
            pen.setStyle(Qt.SolidLine)
        item.setPen(pen)
        try:
            entity.dxf.rgb = (self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue())
        except AttributeError:
            r,g,b = self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue()
            if (r,g,b) == (255,0,0): idx=1
            elif (r,g,b) == (255,255,0): idx=2
            elif (r,g,b) == (0,255,0): idx=3
            elif (r,g,b) == (0,255,255): idx=4
            elif (r,g,b) == (0,0,255): idx=5
            elif (r,g,b) == (255,0,255): idx=6
            else: idx=7
            entity.dxf.color = idx
        if lt == "Dash":
            entity.dxf.linetype = "DASHED"
        elif lt == "DashDot":
            entity.dxf.linetype = "DASHDOT"
        else:
            entity.dxf.linetype = "CONTINUOUS"
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Circle (r={r:.2f})")
        return item

    def add_rectangle(self, x1, y1, x2, y2):
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        entity = self.dxf_modelspace.add_lwpolyline(points, close=True)
        obj = RectObject(x1, y1, x2, y2, entity)
        item = GraphicsRect(obj)
        pen = item.pen()
        pen.setColor(self.current_line_color)
        pen.setWidthF(float(self.line_width_edit.text()))
        lt = self.line_type_combo.currentText()
        if lt == "Dash":
            pen.setStyle(Qt.DashLine)
        elif lt == "DashDot":
            pen.setStyle(Qt.DashDotLine)
        else:
            pen.setStyle(Qt.SolidLine)
        item.setPen(pen)
        try:
            entity.dxf.rgb = (self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue())
        except AttributeError:
            r,g,b = self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue()
            if (r,g,b) == (255,0,0): idx=1
            elif (r,g,b) == (255,255,0): idx=2
            elif (r,g,b) == (0,255,0): idx=3
            elif (r,g,b) == (0,255,255): idx=4
            elif (r,g,b) == (0,0,255): idx=5
            elif (r,g,b) == (255,0,255): idx=6
            else: idx=7
            entity.dxf.color = idx
        if lt == "Dash":
            entity.dxf.linetype = "DASHED"
        elif lt == "DashDot":
            entity.dxf.linetype = "DASHDOT"
        else:
            entity.dxf.linetype = "CONTINUOUS"
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Rectangle")
        return item

    def add_arc(self, cx, cy, r, start_angle, end_angle):
        entity = self.dxf_modelspace.add_arc((cx, cy), r, start_angle, end_angle)
        obj = ArcObject(cx, cy, r, start_angle, end_angle, entity)
        item = GraphicsArc(obj)
        pen = item.pen()
        pen.setColor(self.current_line_color)
        pen.setWidthF(float(self.line_width_edit.text()))
        lt = self.line_type_combo.currentText()
        if lt == "Dash":
            pen.setStyle(Qt.DashLine)
        elif lt == "DashDot":
            pen.setStyle(Qt.DashDotLine)
        else:
            pen.setStyle(Qt.SolidLine)
        item.setPen(pen)
        try:
            entity.dxf.rgb = (self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue())
        except AttributeError:
            r,g,b = self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue()
            if (r,g,b) == (255,0,0): idx=1
            elif (r,g,b) == (255,255,0): idx=2
            elif (r,g,b) == (0,255,0): idx=3
            elif (r,g,b) == (0,255,255): idx=4
            elif (r,g,b) == (0,0,255): idx=5
            elif (r,g,b) == (255,0,255): idx=6
            else: idx=7
            entity.dxf.color = idx
        if lt == "Dash":
            entity.dxf.linetype = "DASHED"
        elif lt == "DashDot":
            entity.dxf.linetype = "DASHDOT"
        else:
            entity.dxf.linetype = "CONTINUOUS"
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Arc")
        return item

    def add_text(self, x, y, text, height=2.5):
        entity = self.dxf_modelspace.add_text(text, dxfattribs={'height': height})
        entity.dxf.insert = (x, y, 0)
        obj = TextObject(x, y, text, height, entity)
        item = GraphicsText(obj)
        item.setDefaultTextColor(self.current_line_color)
        try:
            entity.dxf.rgb = (self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue())
        except AttributeError:
            r,g,b = self.current_line_color.red(), self.current_line_color.green(), self.current_line_color.blue()
            if (r,g,b) == (255,0,0): idx=1
            elif (r,g,b) == (255,255,0): idx=2
            elif (r,g,b) == (0,255,0): idx=3
            elif (r,g,b) == (0,255,255): idx=4
            elif (r,g,b) == (0,0,255): idx=5
            elif (r,g,b) == (255,0,255): idx=6
            else: idx=7
            entity.dxf.color = idx
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Text: {text[:20]}")
        return item

    def add_dimension(self, p1, p2, dim_type="Linear", offset=2):
        obj = DimensionObject(p1, p2, offset, dim_type, None)
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Dimension ({dim_type})")
        return item

    def add_radius_dim(self, center, radius):
        obj = DimensionObject(center, center, 0, "Radius", None)
        obj.radius = radius
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Radius Dimension R{radius:.2f}")
        return item

    def add_diameter_dim(self, center, diameter):
        obj = DimensionObject(center, center, 0, "Diameter", None)
        obj.diameter = diameter
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Diameter Dimension Ø{diameter:.2f}")
        return item

    def add_angular_dim(self, vertex, angle):
        obj = DimensionObject(vertex, vertex, 0, "Angular", None)
        obj.angle = angle
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Angular Dimension {angle:.1f}°")
        return item

def main():
    app = QApplication(sys.argv)
    window = CadWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()