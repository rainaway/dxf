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
                             QDoubleSpinBox, QCheckBox, QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF, QPainter
import ezdxf
from ezdxf.math import Vec3

# ------------------ Утилиты для работы с DXF стилями линий ------------------
# Сопоставление типов линий ezdxf с Qt
LINE_STYLES = {
    "Continuous": Qt.SolidLine,
    "Dashed": Qt.DashLine,
    "Dotted": Qt.DotLine,
    "DashDot": Qt.DashDotLine,
    "DashDotDot": Qt.DashDotDotLine,
}

def get_qt_pen_from_dxf(entity, default_width=0.2):
    """Получить QPen из DXF сущности."""
    # Определяем цвет (если есть)
    color = QColor(0, 0, 0)  # черный по умолчанию
    if hasattr(entity.dxf, 'color'):
        # DXF цвет 0-256, простой черный 7
        col = entity.dxf.color
        if col == 7:
            color = QColor(0,0,0)
        else:
            # упрощенно: используем стандартную палитру, но для простоты черный
            pass
    # Тип линии
    linetype = "Continuous"
    if hasattr(entity.dxf, 'linetype'):
        linetype = entity.dxf.linetype
    # Толщина
    width = default_width
    if hasattr(entity.dxf, 'lineweight'):
        # lineweight в сотых мм, 0 = default
        lw = entity.dxf.lineweight
        if lw > 0:
            width = lw / 100.0
    # Создаем перо
    pen = QPen(color, width)
    pen.setStyle(LINE_STYLES.get(linetype, Qt.SolidLine))
    return pen

# ------------------ Модель данных для графических объектов (расширена) ------------------
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
    def __init__(self, dim_type, points, offset=2, dxf_entity=None):
        super().__init__(dxf_entity)
        self.type = "Dimension"
        self.dim_type = dim_type  # "linear", "radius", "diameter", "angular"
        self.points = points      # список QPointF в зависимости от типа
        self.offset = offset

# ------------------ Графические элементы PyQt (с учетом стилей) ------------------
class GraphicsPoint(QGraphicsEllipseItem):
    def __init__(self, point_obj, size=0.2):
        super().__init__(-size/2, -size/2, size, size)
        self.point_obj = point_obj
        self.setPos(point_obj.x, point_obj.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setPen(QPen(QColor(0,0,0), 0.1))

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
        self.update_pen()

    def update_pen(self):
        if self.line_obj.dxf_entity:
            pen = get_qt_pen_from_dxf(self.line_obj.dxf_entity)
            self.setPen(pen)
        else:
            self.setPen(QPen(QColor(0,0,0), 0.2))

    def update_from_obj(self):
        self.setLine(self.line_obj.x1, self.line_obj.y1, self.line_obj.x2, self.line_obj.y2)
        self.update_pen()

class GraphicsCircle(QGraphicsEllipseItem):
    def __init__(self, circle_obj):
        super().__init__(circle_obj.cx - circle_obj.radius, circle_obj.cy - circle_obj.radius,
                         2*circle_obj.radius, 2*circle_obj.radius)
        self.circle_obj = circle_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.update_pen()

    def update_pen(self):
        if self.circle_obj.dxf_entity:
            pen = get_qt_pen_from_dxf(self.circle_obj.dxf_entity)
            self.setPen(pen)
        else:
            self.setPen(QPen(QColor(0,0,0), 0.2))

    def update_from_obj(self):
        self.setRect(self.circle_obj.cx - self.circle_obj.radius,
                     self.circle_obj.cy - self.circle_obj.radius,
                     2*self.circle_obj.radius, 2*self.circle_obj.radius)
        self.update_pen()

class GraphicsRect(QGraphicsRectItem):
    def __init__(self, rect_obj):
        x1, y1 = rect_obj.x1, rect_obj.y1
        x2, y2 = rect_obj.x2, rect_obj.y2
        super().__init__(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1))
        self.rect_obj = rect_obj
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.update_pen()

    def update_pen(self):
        if self.rect_obj.dxf_entity:
            pen = get_qt_pen_from_dxf(self.rect_obj.dxf_entity)
            self.setPen(pen)
        else:
            self.setPen(QPen(QColor(0,0,0), 0.2))

    def update_from_obj(self):
        x1, y1 = self.rect_obj.x1, self.rect_obj.y1
        x2, y2 = self.rect_obj.x2, self.rect_obj.y2
        self.setRect(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1))
        self.update_pen()

class GraphicsArc(QGraphicsPathItem):
    def __init__(self, arc_obj):
        super().__init__()
        self.arc_obj = arc_obj
        self.update_path()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.update_pen()

    def update_pen(self):
        if self.arc_obj.dxf_entity:
            pen = get_qt_pen_from_dxf(self.arc_obj.dxf_entity)
            self.setPen(pen)
        else:
            self.setPen(QPen(QColor(0,0,0), 0.2))

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

    def update_pen(self):
        # Текст использует цвет из DXF? Пока оставим черный
        pass

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
        if self.dim_obj.dim_type == "linear":
            p1 = self.dim_obj.points[0]
            p2 = self.dim_obj.points[1]
            self._add_linear_dimension(p1, p2)
        elif self.dim_obj.dim_type == "radius":
            center = self.dim_obj.points[0]
            point_on = self.dim_obj.points[1]
            self._add_radius_dimension(center, point_on)
        elif self.dim_obj.dim_type == "diameter":
            center = self.dim_obj.points[0]
            point_on = self.dim_obj.points[1]
            self._add_diameter_dimension(center, point_on)
        elif self.dim_obj.dim_type == "angular":
            # Угловой размер: три точки: вершина, точка на первом луче, точка на втором
            vertex = self.dim_obj.points[0]
            p1 = self.dim_obj.points[1]
            p2 = self.dim_obj.points[2]
            self._add_angular_dimension(vertex, p1, p2)

    def _add_linear_dimension(self, p1, p2):
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

    def _add_radius_dimension(self, center, point_on):
        # Проводим линию от центра до точки, затем выносную линию
        r = math.hypot(point_on.x() - center.x(), point_on.y() - center.y())
        # Рисуем линию от центра до точки на радиусе
        line = QGraphicsLineItem(QLineF(center, point_on))
        # Добавляем текст
        text = QGraphicsTextItem(f"R{r:.2f}")
        # Размещаем текст на середине линии, чуть выше
        mid = (center + point_on) / 2
        text.setPos(mid - text.boundingRect().center())
        pen = QPen(QColor(0,0,0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(line)
        self.addToGroup(text)

    def _add_diameter_dimension(self, center, point_on):
        r = math.hypot(point_on.x() - center.x(), point_on.y() - center.y())
        # Противоположная точка
        opposite = QPointF(center.x()*2 - point_on.x(), center.y()*2 - point_on.y())
        line = QGraphicsLineItem(QLineF(point_on, opposite))
        text = QGraphicsTextItem(f"Ø{r*2:.2f}")
        mid = (point_on + opposite) / 2
        text.setPos(mid - text.boundingRect().center())
        pen = QPen(QColor(0,0,0), 0.2)
        line.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(line)
        self.addToGroup(text)

    def _add_angular_dimension(self, vertex, p1, p2):
        # Вычисляем угол между векторами vertex->p1 и vertex->p2
        v1 = p1 - vertex
        v2 = p2 - vertex
        angle = math.degrees(math.atan2(v1.x()*v2.y() - v1.y()*v2.x(), v1.x()*v2.x() + v1.y()*v2.y()))
        angle = abs(angle)
        # Рисуем дугу на расстоянии R от вершины
        r = 5  # радиус дуги, фиксированный для простоты
        start_angle = math.degrees(math.atan2(v1.y(), v1.x()))
        end_angle = math.degrees(math.atan2(v2.y(), v2.x()))
        # Создаем дугу
        rect = QRectF(vertex.x() - r, vertex.y() - r, 2*r, 2*r)
        path = QPainterPath()
        path.arcMoveTo(rect, start_angle)
        path.arcTo(rect, start_angle, angle)
        arc_item = QGraphicsPathItem(path)
        # Текст
        text = QGraphicsTextItem(f"{angle:.1f}°")
        # Размещаем текст на средней точке дуги
        mid_angle = start_angle + angle/2
        rad = math.radians(mid_angle)
        text_pos = QPointF(vertex.x() + r*1.2*math.cos(rad), vertex.y() + r*1.2*math.sin(rad))
        text.setPos(text_pos - text.boundingRect().center())
        pen = QPen(QColor(0,0,0), 0.2)
        arc_item.setPen(pen)
        text.setDefaultTextColor(QColor(0,0,0))
        self.addToGroup(arc_item)
        self.addToGroup(text)

# ------------------ Менеджер привязок ------------------
class SnapManager:
    def __init__(self, scene):
        self.scene = scene
        self.enabled = True
        self.snap_endpoint = True
        self.snap_midpoint = True
        self.snap_center = True
        self.snap_intersection = True
        self.snap_nearest = False
        self.snap_tolerance = 10  # пикселей

    def snap_point(self, view, screen_point):
        """Находит точку привязки в мировых координатах."""
        if not self.enabled:
            return None
        # Преобразуем экранные координаты в мировые
        scene_pos = view.mapToScene(screen_point)
        # Проверяем все объекты на сцене
        best_dist = float('inf')
        best_point = None
        for item in self.scene.items():
            if isinstance(item, (GraphicsPoint, GraphicsLine, GraphicsCircle, GraphicsArc, GraphicsRect)):
                # Получаем возможные точки привязки
                points = self._get_snap_points(item)
                for p in points:
                    # Переводим в экранные координаты для сравнения расстояния
                    screen_p = view.mapFromScene(p)
                    dist = (screen_p.x() - screen_point.x())**2 + (screen_p.y() - screen_point.y())**2
                    if dist < best_dist and dist < self.snap_tolerance**2:
                        best_dist = dist
                        best_point = p
        return best_point

    def _get_snap_points(self, item):
        points = []
        if isinstance(item, GraphicsPoint):
            points.append(item.pos())
        elif isinstance(item, GraphicsLine):
            if self.snap_endpoint:
                points.append(item.line().p1())
                points.append(item.line().p2())
            if self.snap_midpoint:
                p1 = item.line().p1()
                p2 = item.line().p2()
                points.append((p1 + p2)/2)
        elif isinstance(item, GraphicsCircle):
            if self.snap_center:
                points.append(item.rect().center())
        elif isinstance(item, GraphicsArc):
            if self.snap_center:
                path = item.path()
                # Приблизительно центр дуги – это центр bounding rect
                points.append(item.boundingRect().center())
        return points

# ------------------ Кастомный вид для рисования ------------------
class CadView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.tool = "Select"
        self.start_point = None
        self.temp_item = None
        self.parent_window = parent
        self.snap_manager = SnapManager(self.scene())

    def set_tool(self, tool):
        self.tool = tool
        self.start_point = None
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None

    def mousePressEvent(self, event):
        if self.tool == "Select":
            super().mousePressEvent(event)
            return

        # Получаем точку с привязкой
        snapped = self.snap_manager.snap_point(self, event.pos())
        if snapped is not None:
            pos = snapped
        else:
            pos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            if self.start_point is None:
                self.start_point = pos
                # Временная отрисовка
                if self.tool in ("Line", "DimLinear", "DimRadius", "DimDiameter", "DimAngular"):
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
                elif self.tool == "Text":
                    # Текст создается сразу
                    self.finish_drawing(pos)
            else:
                # Завершение рисования
                self.finish_drawing(pos)
        elif event.button() == Qt.RightButton:
            if self.temp_item:
                self.scene().removeItem(self.temp_item)
                self.temp_item = None
            self.start_point = None
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Привязка к объектам
        if self.tool != "Select":
            # Для временной линии используем привязанную точку
            if self.start_point and self.temp_item:
                snapped = self.snap_manager.snap_point(self, event.pos())
                if snapped is not None:
                    pos = snapped
                else:
                    pos = self.mapToScene(event.pos())
                if self.tool in ("Line", "DimLinear", "DimRadius", "DimDiameter", "DimAngular"):
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
        else:
            super().mouseMoveEvent(event)

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
        elif self.tool == "DimLinear":
            self.parent_window.add_dimension("linear", [self.start_point, pos])
        elif self.tool == "DimRadius":
            # Для радиуса нужно указать окружность, но упрощенно: первая точка - центр, вторая - на окружности
            self.parent_window.add_dimension("radius", [self.start_point, pos])
        elif self.tool == "DimDiameter":
            self.parent_window.add_dimension("diameter", [self.start_point, pos])
        elif self.tool == "DimAngular":
            # Для угла нужно три точки: вершина, две точки на лучах. Пока реализуем как два клика: первый - вершина, второй - точка на первом луче, третий - на втором
            # Для простоты сделаем через диалог? Или накапливать точки. Пока используем временно два клика: первый - вершина, второй - конец первого луча, третий - конец второго.
            # В реальности нужно накопление точек, но для демо используем диалог.
            dlg = QDialog(self.parent_window)
            dlg.setWindowTitle("Angular Dimension")
            layout = QFormLayout(dlg)
            layout.addRow(QLabel("Click on vertex, then on two points on arms"))
            # Упростим: после двух точек будет диалог для третьей? Неудобно.
            # Вместо этого предложим ввести угол.
            angle_edit = QLineEdit("45")
            layout.addRow("Angle (degrees):", angle_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                angle = float(angle_edit.text())
                # Создаем угловой размер с заданным углом
                vertex = self.start_point
                p1 = QPointF(vertex.x() + 5, vertex.y())  # условно
                p2 = QPointF(vertex.x() + 5*math.cos(math.radians(angle)), vertex.y() + 5*math.sin(math.radians(angle)))
                self.parent_window.add_dimension("angular", [vertex, p1, p2])

        # Очистка
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
        self.start_point = None

# ------------------ Диалог редактирования свойств объекта ------------------
class EditPropertiesDialog(QDialog):
    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.setWindowTitle("Edit Properties")
        layout = QFormLayout(self)

        # Цвет
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addRow("Color:", self.color_btn)

        # Толщина линии
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.01, 10.0)
        self.width_spin.setSingleStep(0.1)
        layout.addRow("Line width:", self.width_spin)

        # Тип линии
        self.linetype_combo = QComboBox()
        self.linetype_combo.addItems(["Continuous", "Dashed", "Dotted", "DashDot", "DashDotDot"])
        layout.addRow("Line type:", self.linetype_combo)

        # Загружаем текущие значения, если есть DXF сущность
        if obj.dxf_entity:
            # Цвет (упрощенно: берем из DXF)
            # Толщина
            if hasattr(obj.dxf_entity.dxf, 'lineweight'):
                lw = obj.dxf_entity.dxf.lineweight
                if lw > 0:
                    self.width_spin.setValue(lw/100.0)
                else:
                    self.width_spin.setValue(0.2)
            # Тип линии
            if hasattr(obj.dxf_entity.dxf, 'linetype'):
                lt = obj.dxf_entity.dxf.linetype
                idx = self.linetype_combo.findText(lt)
                if idx >= 0:
                    self.linetype_combo.setCurrentIndex(idx)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addRow(ok_btn)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # Сохраняем цвет в атрибуты DXF
            # В DXF цвет задается индексом 0-256, для простоты установим 7 (черный)
            # В реальном приложении нужно преобразование
            pass

    def get_values(self):
        return {
            'linewidth': self.width_spin.value(),
            'linetype': self.linetype_combo.currentText()
        }

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
        self.obj_map = {}          # DXF entity -> GraphicObject
        self.next_id = 1

        self.init_ui()
        self.init_statusbar()
        self.new_document()

    def init_ui(self):
        toolbar = self.addToolBar("Tools")
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_document)
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
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
        dim_linear_action = QAction("Dim Linear", self)
        dim_linear_action.triggered.connect(lambda: self.set_tool("DimLinear"))
        dim_radius_action = QAction("Dim Radius", self)
        dim_radius_action.triggered.connect(lambda: self.set_tool("DimRadius"))
        dim_diameter_action = QAction("Dim Diameter", self)
        dim_diameter_action.triggered.connect(lambda: self.set_tool("DimDiameter"))
        dim_angular_action = QAction("Dim Angular", self)
        dim_angular_action.triggered.connect(lambda: self.set_tool("DimAngular"))

        toolbar.addAction(select_action)
        toolbar.addAction(line_action)
        toolbar.addAction(circle_action)
        toolbar.addAction(rect_action)
        toolbar.addAction(arc_action)
        toolbar.addAction(text_action)
        toolbar.addSeparator()
        toolbar.addAction(dim_linear_action)
        toolbar.addAction(dim_radius_action)
        toolbar.addAction(dim_diameter_action)
        toolbar.addAction(dim_angular_action)

        dock = QDockWidget("Objects", self)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_object_selected)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.list_widget)
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_selected)
        layout.addWidget(edit_button)
        props_button = QPushButton("Properties")
        props_button.clicked.connect(self.edit_properties)
        layout.addWidget(props_button)
        dock.setWidget(container)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # Панель привязок
        snap_dock = QDockWidget("Snap Settings", self)
        snap_widget = QWidget()
        snap_layout = QVBoxLayout(snap_widget)
        self.snap_enable = QCheckBox("Enable Snap")
        self.snap_enable.setChecked(True)
        self.snap_enable.toggled.connect(self.toggle_snap)
        snap_layout.addWidget(self.snap_enable)
        self.snap_endpoint = QCheckBox("Endpoint")
        self.snap_endpoint.setChecked(True)
        self.snap_endpoint.toggled.connect(self.update_snap)
        snap_layout.addWidget(self.snap_endpoint)
        self.snap_midpoint = QCheckBox("Midpoint")
        self.snap_midpoint.setChecked(True)
        self.snap_midpoint.toggled.connect(self.update_snap)
        snap_layout.addWidget(self.snap_midpoint)
        self.snap_center = QCheckBox("Center")
        self.snap_center.setChecked(True)
        self.snap_center.toggled.connect(self.update_snap)
        snap_layout.addWidget(self.snap_center)
        snap_dock.setWidget(snap_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, snap_dock)

    def toggle_snap(self, enabled):
        self.view.snap_manager.enabled = enabled

    def update_snap(self):
        self.view.snap_manager.snap_endpoint = self.snap_endpoint.isChecked()
        self.view.snap_manager.snap_midpoint = self.snap_midpoint.isChecked()
        self.view.snap_manager.snap_center = self.snap_center.isChecked()

    def init_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Ready")
        self.status.addWidget(self.status_label)

    def set_tool(self, tool):
        self.view.set_tool(tool)
        self.status_label.setText(f"Tool: {tool}")

    def new_document(self):
        self.dxf_doc = ezdxf.new('R2010')
        self.dxf_modelspace = self.dxf_doc.modelspace()
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()
        self.status_label.setText("New document")
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def open_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF Files (*.dxf)")
        if not fname:
            return
        try:
            self.dxf_doc = ezdxf.readfile(fname)
            self.dxf_modelspace = self.dxf_doc.modelspace()
            self.load_dxf_entities()
            self.status_label.setText(f"Loaded: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{str(e)}")
            traceback.print_exc()

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

    def save_file(self):
        if not self.dxf_doc:
            QMessageBox.warning(self, "Warning", "No document opened.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Save DXF", "", "DXF Files (*.dxf)")
        if not fname:
            return
        try:
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
            self.dxf_doc.saveas(fname)
            QMessageBox.information(self, "Saved", f"File saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

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
                self.edit_object(obj)
                break

    def edit_properties(self):
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Properties", "No object selected.")
            return
        item = selected[0]
        for obj in self.obj_map.values():
            if obj.graphics_item == item:
                dlg = EditPropertiesDialog(obj, self)
                if dlg.exec_():
                    values = dlg.get_values()
                    # Применяем к DXF сущности
                    if obj.dxf_entity:
                        obj.dxf_entity.dxf.lineweight = int(values['linewidth']*100)
                        obj.dxf_entity.dxf.linetype = values['linetype']
                    # Обновляем отображение
                    if hasattr(obj.graphics_item, 'update_pen'):
                        obj.graphics_item.update_pen()
                break

    def edit_object(self, obj):
        if obj.type == "Point":
            dlg = QDialog(self)
            dlg.setWindowTitle("Edit Point")
            layout = QFormLayout(dlg)
            x_edit = QLineEdit(str(obj.x))
            y_edit = QLineEdit(str(obj.y))
            layout.addRow("X:", x_edit)
            layout.addRow("Y:", y_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                obj.x = float(x_edit.text())
                obj.y = float(y_edit.text())
                obj.graphics_item.setPos(obj.x, obj.y)
                if obj.dxf_entity:
                    obj.dxf_entity.dxf.location = Vec3(obj.x, obj.y, 0)
        elif obj.type == "Line":
            dlg = QDialog(self)
            dlg.setWindowTitle("Edit Line")
            layout = QFormLayout(dlg)
            x1_edit = QLineEdit(str(obj.x1))
            y1_edit = QLineEdit(str(obj.y1))
            x2_edit = QLineEdit(str(obj.x2))
            y2_edit = QLineEdit(str(obj.y2))
            layout.addRow("X1:", x1_edit)
            layout.addRow("Y1:", y1_edit)
            layout.addRow("X2:", x2_edit)
            layout.addRow("Y2:", y2_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                obj.x1 = float(x1_edit.text())
                obj.y1 = float(y1_edit.text())
                obj.x2 = float(x2_edit.text())
                obj.y2 = float(y2_edit.text())
                obj.graphics_item.update_from_obj()
                if obj.dxf_entity:
                    obj.dxf_entity.dxf.start = Vec3(obj.x1, obj.y1, 0)
                    obj.dxf_entity.dxf.end = Vec3(obj.x2, obj.y2, 0)
        elif obj.type == "Circle":
            dlg = QDialog(self)
            dlg.setWindowTitle("Edit Circle")
            layout = QFormLayout(dlg)
            cx_edit = QLineEdit(str(obj.cx))
            cy_edit = QLineEdit(str(obj.cy))
            r_edit = QLineEdit(str(obj.radius))
            layout.addRow("Center X:", cx_edit)
            layout.addRow("Center Y:", cy_edit)
            layout.addRow("Radius:", r_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                obj.cx = float(cx_edit.text())
                obj.cy = float(cy_edit.text())
                obj.radius = float(r_edit.text())
                obj.graphics_item.update_from_obj()
                if obj.dxf_entity:
                    obj.dxf_entity.dxf.center = Vec3(obj.cx, obj.cy, 0)
                    obj.dxf_entity.dxf.radius = obj.radius
        elif obj.type == "Text":
            dlg = QDialog(self)
            dlg.setWindowTitle("Edit Text")
            layout = QFormLayout(dlg)
            text_edit = QLineEdit(obj.text)
            x_edit = QLineEdit(str(obj.x))
            y_edit = QLineEdit(str(obj.y))
            h_edit = QLineEdit(str(obj.height))
            layout.addRow("Text:", text_edit)
            layout.addRow("X:", x_edit)
            layout.addRow("Y:", y_edit)
            layout.addRow("Height:", h_edit)
            btn = QPushButton("OK")
            btn.clicked.connect(dlg.accept)
            layout.addRow(btn)
            if dlg.exec_():
                obj.text = text_edit.text()
                obj.x = float(x_edit.text())
                obj.y = float(y_edit.text())
                obj.height = float(h_edit.text())
                obj.graphics_item.setPlainText(obj.text)
                obj.graphics_item.setPos(obj.x, obj.y)
                obj.graphics_item.setFont(QFont("Arial", int(obj.height)))
                if obj.dxf_entity:
                    obj.dxf_entity.dxf.insert = Vec3(obj.x, obj.y, 0)
                    obj.dxf_entity.dxf.text = obj.text
                    obj.dxf_entity.dxf.height = obj.height

    # ------------------ Добавление новых примитивов ------------------
    def add_line(self, x1, y1, x2, y2):
        entity = self.dxf_modelspace.add_line((x1, y1), (x2, y2))
        obj = LineObject(x1, y1, x2, y2, entity)
        item = GraphicsLine(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Line ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")

    def add_circle(self, cx, cy, r):
        entity = self.dxf_modelspace.add_circle((cx, cy), r)
        obj = CircleObject(cx, cy, r, entity)
        item = GraphicsCircle(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Circle (r={r:.2f})")

    def add_rectangle(self, x1, y1, x2, y2):
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        entity = self.dxf_modelspace.add_lwpolyline(points, close=True)
        obj = RectObject(x1, y1, x2, y2, entity)
        item = GraphicsRect(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Rectangle")

    def add_arc(self, cx, cy, r, start_angle, end_angle):
        entity = self.dxf_modelspace.add_arc((cx, cy), r, start_angle, end_angle)
        obj = ArcObject(cx, cy, r, start_angle, end_angle, entity)
        item = GraphicsArc(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Arc")

    def add_text(self, x, y, text, height=2.5):
        entity = self.dxf_modelspace.add_text(text, dxfattribs={'height': height})
        entity.dxf.insert = (x, y, 0)
        obj = TextObject(x, y, text, height, entity)
        item = GraphicsText(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        self.obj_map[entity] = obj
        self.list_widget.addItem(f"Text: {text[:20]}")

    def add_dimension(self, dim_type, points, offset=2):
        obj = DimensionObject(dim_type, points, offset, None)
        item = GraphicsDimension(obj)
        self.scene.addItem(item)
        obj.graphics_item = item
        # Не сохраняем в DXF для простоты
        self.list_widget.addItem(f"Dimension ({dim_type})")

def main():
    app = QApplication(sys.argv)
    window = CadWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()