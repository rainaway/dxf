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
                             QMenu, QGraphicsSimpleTextItem, QCheckBox, QGroupBox, QHBoxLayout)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, QMarginsF, QSizeF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF, QPainter, QTransform, QPageLayout, QPageSize
import ezdxf
from ezdxf.math import Vec3

# ------------------ Модель данных для графических объектов ------------------
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

# ------------------ Графические элементы PyQt ------------------
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

# ------------------ Привязка ------------------
class SnapManager:
    def __init__(self, scene):
        self.scene = scene
        self.snap_distance = 30
        self.snap_to_endpoints = True
        self.snap_to_center = True

    def snap_point(self, view, screen_pos):
        scene_pos = view.mapToScene(screen_pos)
        if not self.scene:
            return scene_pos
        best_dist = self.snap_distance
        best_point = None
        for item in self.scene.items():
            if self.snap_to_endpoints:
                if isinstance(item, GraphicsLine):
                    line = item.line()
                    for p in [line.p1(), line.p2()]:
                        pixel_pos = view.mapFromScene(p)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = p
                elif isinstance(item, GraphicsRect):
                    rect = item.rect()
                    for p in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                        pixel_pos = view.mapFromScene(p)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = p
                elif isinstance(item, GraphicsPoint):
                    p = item.pos()
                    pixel_pos = view.mapFromScene(p)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = p
            if self.snap_to_center and isinstance(item, GraphicsCircle):
                p = QPointF(item.circle_obj.cx, item.circle_obj.cy)
                pixel_pos = view.mapFromScene(p)
                dist = (screen_pos - pixel_pos).manhattanLength()
                if dist < best_dist:
                    best_dist = dist
                    best_point = p
        return best_point if best_point else scene_pos

# ------------------ Кастомный вид для рисования ------------------
class CadView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)  # Отключаем стандартный RubberBandDrag
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
        self.setCursor(Qt.ArrowCursor)
        # Масштабирование
        self._zoom_factor = 1.2
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        # Перемещение области (панорамирование)
        self._panning = False
        self._last_pan_pos = None

    def wheelEvent(self, event):
        """Масштабирование колесом мыши"""
        delta = event.angleDelta().y()
        if delta > 0:
            factor = self._zoom_factor
        else:
            factor = 1 / self._zoom_factor
        
        current_zoom = self.transform().m11()
        new_zoom = current_zoom * factor
        
        if self._min_zoom <= new_zoom <= self._max_zoom:
            # Масштабирование относительно позиции курсора
            pos = event.pos()
            before_pos = self.mapToScene(pos)
            self.scale(factor, factor)
            after_pos = self.mapToScene(pos)
            # Корректировка позиции, чтобы точка под курсором осталась на месте
            self.translate(after_pos.x() - before_pos.x(), after_pos.y() - before_pos.y())
        event.accept()

    def mousePressEvent(self, event):
        # Обработка нажатия колеса мыши для панорамирования
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        
        # Команда _m (перемещение) - обрабатывается через клавиатуру, но здесь поддержка через флаг
        if hasattr(self, '_move_mode') and self._move_mode:
            self._panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            
        if self.tool == "Select":
            super().mousePressEvent(event)
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
        # Обработка панорамирования (перемещения области) при зажатом колесе мыши
        if self._panning and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            # Прокрутка сцены в противоположном направлении движения мыши
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            return
        
        scene_pos = self.mapToScene(event.pos())
        snapped_pos = scene_pos
        snap_name = ""
        
        # Проверка привязок
        if self.snap_manager and self.tool != "Select":
            snapped_pos = self.snap_manager.snap_point(self, event.pos())
            # Определяем имя привязки
            if snapped_pos != scene_pos:
                # Проверяем тип привязки
                for obj in self.parent_window.obj_map.values():
                    if obj.type == "Line":
                        if math.hypot(snapped_pos.x() - obj.x1, snapped_pos.y() - obj.y1) < 0.5:
                            snap_name = "Endpoint"
                            break
                        elif math.hypot(snapped_pos.x() - obj.x2, snapped_pos.y() - obj.y2) < 0.5:
                            snap_name = "Endpoint"
                            break
                    elif obj.type == "Circle":
                        if math.hypot(snapped_pos.x() - obj.cx, snapped_pos.y() - obj.cy) < 0.5:
                            snap_name = "Center"
                            break
        
        # Подсказка для инструментов рисования (следует за курсором)
        if self.tool != "Select":
            if self.tooltip_item is None:
                self.tooltip_item = QGraphicsSimpleTextItem()
                self.tooltip_item.setBrush(QBrush(QColor(0,0,0)))
                self.tooltip_item.setFont(QFont("Arial", 8))
                self.scene().addItem(self.tooltip_item)
            
            # Отображение названия инструмента и координат
            if snap_name:
                tooltip_text = f"{self.tool}: ({snapped_pos.x():.2f}, {snapped_pos.y():.2f}) [{snap_name}]"
            else:
                tooltip_text = f"{self.tool}: ({snapped_pos.x():.2f}, {snapped_pos.y():.2f})"
            
            self.tooltip_item.setText(tooltip_text)
            self.tooltip_item.setPos(snapped_pos.x() + 5, snapped_pos.y() - 10)
        else:
            if self.tooltip_item:
                self.scene().removeItem(self.tooltip_item)
                self.tooltip_item = None
            
            # В режиме выбора показываем имя объекта под курсором
            pos = scene_pos
            item = self.scene().itemAt(pos, QTransform())
            if item and item.flags() & QGraphicsItem.ItemIsSelectable:
                # Находим соответствующий объект
                for obj in self.parent_window.obj_map.values():
                    if obj.graphics_item == item:
                        if self.tooltip_item is None:
                            self.tooltip_item = QGraphicsSimpleTextItem()
                            self.tooltip_item.setBrush(QBrush(QColor(0,0,255)))
                            self.tooltip_item.setFont(QFont("Arial", 9, QFont.Bold))
                            self.scene().addItem(self.tooltip_item)
                        
                        obj_name = self.parent_window.object_description(obj)
                        self.tooltip_item.setText(f"{obj_name}")
                        self.tooltip_item.setPos(pos.x() + 10, pos.y() + 10)
                        break

        # Подсветка объектов в режиме выбора
        if self.tool == "Select":
            pos = scene_pos
            item = self.scene().itemAt(pos, QTransform())
            if item != self.hovered_item:
                self.clear_highlight()
                self.hovered_item = item
                if item and item.flags() & QGraphicsItem.ItemIsSelectable:
                    self.highlight_item(item)
        else:
            self.clear_highlight()

        # Обработка перемещения для временных объектов
        if self.start_point and self.temp_item:
            pos = snapped_pos if self.snap_manager else scene_pos
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
        self.parent_window.update_snap_settings(enabled, self.snap_manager.snap_to_center)

    def set_snap_center(self, enabled):
        self.snap_manager.snap_to_center = enabled
        self.parent_window.update_snap_settings(self.snap_manager.snap_to_endpoints, enabled)

    def highlight_item(self, item):
        """Подсветка объекта изменением пера или цвета текста."""
        if hasattr(item, 'pen'):
            self.original_pen = item.pen()
            new_pen = QPen(QColor(255, 0, 0), self.original_pen.widthF() + 0.2)
            new_pen.setStyle(self.original_pen.style())
            item.setPen(new_pen)
        elif isinstance(item, QGraphicsTextItem):
            self.original_color = item.defaultTextColor()
            item.setDefaultTextColor(QColor(255, 0, 0))

    def clear_highlight(self):
        """Восстановление исходного вида объекта."""
        if self.hovered_item:
            if hasattr(self.hovered_item, 'pen') and self.original_pen is not None:
                self.hovered_item.setPen(self.original_pen)
            elif isinstance(self.hovered_item, QGraphicsTextItem) and self.original_color is not None:
                self.hovered_item.setDefaultTextColor(self.original_color)
            self.hovered_item = None
            self.original_pen = None
            self.original_color = None

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши для завершения панорамирования"""
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self._last_pan_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Обработка клавиши ESC для отмены текущей команды, Delete для удаления и _m для перемещения"""
        if event.key() == Qt.Key_Escape:
            # Сброс режима панорамирования если активен
            if self._panning:
                self._panning = False
                self._last_pan_pos = None
                self.setCursor(Qt.ArrowCursor)
            elif self.tool != "Select":
                # Отмена текущей операции рисования
                if self.temp_item:
                    self.scene().removeItem(self.temp_item)
                    self.temp_item = None
                self.start_point = None
                # Переключение в режим выбора
                self.parent_window.set_tool("Select")
            event.accept()
        elif event.key() == Qt.Key_Delete:
            # Удаление выделенных объектов
            if self.tool == "Select":
                self.parent_window.delete_selected()
            event.accept()
        elif event.key() == Qt.Key_M:
            # Команда _m - переход в режим перемещения (панорамирования)
            if self.tool == "Select":
                self._move_mode = True
                self.setCursor(Qt.OpenHandCursor)
                self.parent_window.status_label.setText("Move mode: Click and drag to pan. Press ESC to exit.")
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Обработка отпускания клавиш"""
        if event.key() == Qt.Key_M:
            self._move_mode = False
        super().keyReleaseEvent(event)

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
        # Сброс режима перемещения при смене инструмента
        self._move_mode = False
        if tool == "Select":
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def set_dim_type(self, dim_type):
        self.dim_type = dim_type

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

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(255,255,255)))
        self.view = CadView(self)
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.dxf_doc = None
        self.dxf_modelspace = None
        self.obj_map = {}
        self.current_file = None
        self._unsaved_changes = False

        # Инициализируем statusbar ДО вызова init_ui, т.к. setup_paper_format использует status_label
        self.init_statusbar()
        self.init_ui()
        self.create_empty_document()   # создаём пустой документ без запроса пути

    def init_ui(self):
        toolbar = self.addToolBar("Tools")
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_document)
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.save_as_file)
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addAction(save_as_action)
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

        toolbar.addAction(select_action)
        toolbar.addAction(line_action)
        toolbar.addAction(circle_action)
        toolbar.addAction(rect_action)
        toolbar.addAction(arc_action)
        toolbar.addAction(text_action)
        toolbar.addSeparator()

        self.dim_type_combo = QComboBox()
        self.dim_type_combo.addItems(["Linear", "Radius", "Diameter", "Angular"])
        self.dim_type_combo.currentTextChanged.connect(self.on_dim_type_changed)
        dim_action = QAction("Dimension", self)
        dim_action.triggered.connect(lambda: self.set_tool("Dim"))
        toolbar.addWidget(QLabel("Dim type:"))
        toolbar.addWidget(self.dim_type_combo)
        toolbar.addAction(dim_action)
        toolbar.addSeparator()
        
        # Выбор формата бумаги
        self.paper_format_combo = QComboBox()
        self.paper_format_combo.addItems(["A0", "A1", "A2", "A3", "A4"])
        self.paper_format_combo.setCurrentText("A3")
        self.paper_format_combo.currentTextChanged.connect(self.on_paper_format_changed)
        toolbar.addWidget(QLabel("Paper:"))
        toolbar.addWidget(self.paper_format_combo)
        toolbar.addSeparator()
        
        # Кнопка печати/экспорта в PDF
        print_action = QAction("Print / Export PDF", self)
        print_action.triggered.connect(self.print_to_pdf)
        toolbar.addAction(print_action)

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
        delete_button = QPushButton("Delete Selected")
        delete_button.setShortcut("Delete")
        delete_button.clicked.connect(self.delete_selected)
        layout_left.addWidget(delete_button)
        left_dock.setWidget(container_left)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)

        # Панель настроек справа
        right_dock = QDockWidget("Settings", self)
        container_right = QWidget()
        layout_right = QVBoxLayout(container_right)

        # Группа привязок
        snap_group = QGroupBox("Snap Settings")
        snap_layout = QVBoxLayout()
        self.snap_end_check = QCheckBox("Snap to endpoints")
        self.snap_end_check.setChecked(True)
        self.snap_end_check.toggled.connect(self.on_snap_end_toggled)
        self.snap_center_check = QCheckBox("Snap to centers")
        self.snap_center_check.setChecked(True)
        self.snap_center_check.toggled.connect(self.on_snap_center_toggled)
        snap_layout.addWidget(self.snap_end_check)
        snap_layout.addWidget(self.snap_center_check)
        snap_group.setLayout(snap_layout)
        layout_right.addWidget(snap_group)

        # Группа стилей линии
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

        # Кнопка применить стиль к выделенному объекту
        apply_style_btn = QPushButton("Apply Style to Selected")
        apply_style_btn.clicked.connect(self.apply_style_to_selected)
        layout_right.addWidget(apply_style_btn)

        container_right.setLayout(layout_right)
        right_dock.setWidget(container_right)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

        # Сохраняем текущие настройки стиля
        self.current_line_color = QColor(0,0,0)
        self.current_line_width = 0.2
        self.current_line_type = "Solid"
        
        # Формат бумаги (по умолчанию A3)
        self.paper_format = "A3"
        self.paper_sizes = {
            "A0": (841, 1189),  # мм
            "A1": (594, 841),
            "A2": (420, 594),
            "A3": (297, 420),
            "A4": (210, 297)
        }
        self.setup_paper_format("A3")

    def init_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Ready")
        self.status.addWidget(self.status_label)

    def create_empty_document(self):
        """Создаёт новый пустой документ в памяти без запроса имени файла."""
        self.dxf_doc = ezdxf.new('R2010')
        self.dxf_modelspace = self.dxf_doc.modelspace()
        self.current_file = None
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()
        self.status_label.setText("New document (unsaved)")
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def set_tool(self, tool):
        self.view.set_tool(tool)
        self.status_label.setText(f"Tool: {tool}")

    def on_dim_type_changed(self, text):
        self.view.dim_type = text

    def on_snap_end_toggled(self, checked):
        self.view.set_snap_endpoints(checked)

    def on_snap_center_toggled(self, checked):
        self.view.set_snap_center(checked)

    def update_snap_settings(self, snap_end, snap_center):
        self.snap_end_check.blockSignals(True)
        self.snap_center_check.blockSignals(True)
        self.snap_end_check.setChecked(snap_end)
        self.snap_center_check.setChecked(snap_center)
        self.snap_end_check.blockSignals(False)
        self.snap_center_check.blockSignals(False)

    def choose_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_line_color = color
            self.line_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.line_color_btn.color = color

    def apply_style_to_selected(self):
        """Применить текущие настройки стиля к выделенному объекту."""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        for item in selected:
            # Находим соответствующий GraphicObject
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
                            # Сохранить в DXF
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
        QMessageBox.information(self, "Done", "Style applied to selected object(s).")

    def new_document(self):
        # Запрашиваем имя файла, если пользователь хочет сохранить текущий
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
        try:
            self._sync_dxf()
            self.dxf_doc.saveas(fname)
            self.current_file = fname
            QMessageBox.information(self, "Saved", f"File saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

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
            if entity.dxftype() == 'POINT':
                x, y, z = entity.dxf.location
                obj = PointObject(x, y, entity)
                item = GraphicsPoint(obj, 0.2)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Point ({x:.2f},{y:.2f})")
            elif entity.dxftype() == 'LINE':
                x1, y1, z1 = entity.dxf.start
                x2, y2, z2 = entity.dxf.end
                obj = LineObject(x1, y1, x2, y2, entity)
                item = GraphicsLine(obj)
                self.scene.addItem(item)
                obj.graphics_item = item
                self.obj_map[entity] = obj
                self.list_widget.addItem(f"Line ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
            elif entity.dxftype() == 'CIRCLE':
                cx, cy, cz = entity.dxf.center
                r = entity.dxf.radius
                obj = CircleObject(cx, cy, r, entity)
                item = GraphicsCircle(obj)
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
                    pass
                break

    def delete_selected(self):
        """Удаление выделенных объектов"""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Delete", "No object selected.")
            return
        
        for item in selected:
            # Находим соответствующий GraphicObject и удаляем из DXF
            obj_to_remove = None
            for entity, obj in list(self.obj_map.items()):
                if obj.graphics_item == item:
                    obj_to_remove = obj
                    # Удаляем из DXF документа
                    if obj.dxf_entity and self.dxf_modelspace:
                        try:
                            self.dxf_modelspace.delete_entity(obj.dxf_entity)
                        except Exception:
                            pass
                    break
            
            # Удаляем графический элемент из сцены
            self.scene.removeItem(item)
            
            # Удаляем из списка объектов
            if obj_to_remove:
                # Обновляем список в левой панели
                for i in range(self.list_widget.count()):
                    list_item = self.list_widget.item(i)
                    if list_item and list_item.text() == self.object_description(obj_to_remove):
                        self.list_widget.takeItem(i)
                        break
                
                # Удаляем из obj_map
                for entity, obj in list(self.obj_map.items()):
                    if obj == obj_to_remove:
                        del self.obj_map[entity]
                        break
        
        self.status_label.setText("Object(s) deleted")

    # ------------------ Добавление новых примитивов ------------------
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
        # Сохранить в DXF
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

    def add_dimension(self, p1, p2, dim_type="Linear", offset=2):
        obj = DimensionObject(p1, p2, offset, dim_type, None)
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Dimension ({dim_type})")

    def add_radius_dim(self, center, radius):
        obj = DimensionObject(center, center, 0, "Radius", None)
        obj.radius = radius
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Radius Dimension R{radius:.2f}")

    def add_diameter_dim(self, center, diameter):
        obj = DimensionObject(center, center, 0, "Diameter", None)
        obj.diameter = diameter
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Diameter Dimension Ø{diameter:.2f}")

    def add_angular_dim(self, vertex, angle):
        obj = DimensionObject(vertex, vertex, 0, "Angular", None)
        obj.angle = angle
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.list_widget.addItem(f"Angular Dimension {angle:.1f}°")

    # ------------------ Формат бумаги и печать ------------------
    def setup_paper_format(self, format_name):
        """Настройка формата бумаги для рабочей области"""
        if format_name not in self.paper_sizes:
            return
        
        width_mm, height_mm = self.paper_sizes[format_name]
        # Конвертируем мм в единицы сцены (предполагаем 1 мм = 1 единица)
        width = width_mm
        height = height_mm
        
        # Очищаем сцену и устанавливаем новый размер
        rect = QRectF(0, 0, width, height)
        self.scene.setSceneRect(rect)
        
        # Рисуем рамку бумаги
        self._draw_paper_border(width, height)
        
        self.paper_format = format_name
        self.status_label.setText(f"Paper format: {format_name} ({width}x{height} mm)")
    
    def _draw_paper_border(self, width, height):
        """Рисует рамку бумаги на сцене"""
        # Удаляем существующую рамку если есть
        for item in self.scene.items():
            if hasattr(item, 'is_paper_border') and item.is_paper_border:
                self.scene.removeItem(item)
        
        # Рисуем новую рамку
        border_rect = QGraphicsRectItem(0, 0, width, height)
        border_rect.setPen(QPen(QColor(200, 200, 200), 0.5, Qt.DashLine))
        border_rect.is_paper_border = True
        border_rect.setFlag(QGraphicsItem.ItemIsSelectable, False)
        border_rect.setZValue(-1000)  # Помещаем на задний план
        self.scene.addItem(border_rect)
    
    def on_paper_format_changed(self, format_name):
        """Обработчик изменения формата бумаги"""
        self.setup_paper_format(format_name)
    
    def print_to_pdf(self):
        """Печать или экспорт в PDF"""
        # Диалог выбора файла для сохранения PDF
        fname, _ = QFileDialog.getSaveFileName(
            self, 
            "Export to PDF", 
            "", 
            "PDF Files (*.pdf)"
        )
        if not fname:
            return
        
        try:
            # Создаем принтер для PDF
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fname)
            
            # Устанавливаем размер страницы согласно выбранному формату
            width_mm, height_mm = self.paper_sizes[self.paper_format]
            page_layout = QPageLayout()
            page_size = QPageSize(QSizeF(width_mm, height_mm), QPageSize.Millimeter)
            page_layout.setPageSize(page_size)
            page_layout.setMargins(QMarginsF(5, 5, 5, 5))  # Небольшие поля
            printer.setPageLayout(page_layout)
            
            # Создаем painter для рендеринга
            painter = QPainter(printer)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Получаем границы содержимого сцены
            scene_rect = self.scene.itemsBoundingRect()
            if scene_rect.isEmpty():
                QMessageBox.warning(self, "Warning", "No content to print.")
                painter.end()
                return
            
            # Масштабируем для размещения на странице
            # Учитываем поля
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            
            # Рассчитываем масштаб для fit-in-page
            scale_x = page_rect.width() / scene_rect.width()
            scale_y = page_rect.height() / scene_rect.height()
            scale = min(scale_x, scale_y) * 0.95  # 95% для запасa
            
            painter.scale(scale, scale)
            
            # Центрируем содержимое на странице
            translate_x = -scene_rect.left() + (page_rect.width() / scale - scene_rect.width()) / 2
            translate_y = -scene_rect.top() + (page_rect.height() / scale - scene_rect.height()) / 2
            painter.translate(translate_x, translate_y)
            
            # Рендерим сцену
            self.scene.render(painter)
            
            painter.end()
            
            QMessageBox.information(self, "Success", f"PDF exported to:\n{fname}")
            self.status_label.setText(f"Exported to PDF: {fname}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF:\n{str(e)}")
            traceback.print_exc()

def main():
    app = QApplication(sys.argv)
    window = CadWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()