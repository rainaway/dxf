#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import math
import ezdxf
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QAction, QMenu, QColorDialog, QFileDialog, 
                             QMessageBox, QVBoxLayout, QWidget, QToolBar, QLabel, QComboBox,
                             QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QCursor, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF

# Константы форматов бумаги (в мм)
PAPER_FORMATS = {
    "A4": (210, 297),
    "A3": (297, 420),
    "A2": (420, 594),
    "A1": (594, 841),
    "A0": (841, 1189)
}

class GraphicsTextItem(QGraphicsSimpleTextItem):
    """Текстовый элемент для подсказок, всегда поверх всего."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setFlag(QGraphicsItem.ItemIgnoresParentGeometry)
        self.setZValue(10000)

class CadObject(QGraphicsItem):
    """Базовый класс для объектов чертежа."""
    def __init__(self, color=Qt.black, width=0.5):
        super().__init__()
        self.color = color
        self.width = width
        self.setAcceptHoverEvents(True)
        self._pen = QPen(QColor(color), width)
        self._pen.setCosmetic(False)  # Линии масштабируются вместе с видом

    def set_color(self, color):
        self.color = color
        self._pen.setColor(QColor(color))
        self.update()

    def set_width(self, width):
        self.width = width
        self._pen.setWidthF(width)
        self.update()

    def hoverEnterEvent(self, event):
        if self.scene():
            self.scene().set_hovered_item(self)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self.scene():
            self.scene().set_hovered_item(None)
        super().hoverLeaveEvent(event)

class LineObject(CadObject):
    def __init__(self, start, end, color=Qt.black, width=0.5):
        super().__init__(color, width)
        self.start = start
        self.end = end
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def boundingRect(self):
        return QRectF(self.start, self.end).normalized().adjusted(-self.width, -self.width, self.width, self.width)

    def paint(self, painter, option, widget):
        painter.setPen(self._pen)
        if self.isSelected():
            painter.setPen(QPen(Qt.red, self.width + 0.2, Qt.DashLine))
        painter.drawLine(self.start, self.end)

    def get_start_point(self): return self.start
    def get_end_point(self): return self.end

class CircleObject(CadObject):
    def __init__(self, center, radius, color=Qt.black, width=0.5):
        super().__init__(color, width)
        self.center = center
        self.radius = radius
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def boundingRect(self):
        r = self.radius + self.width
        return QRectF(self.center.x() - r, self.center.y() - r, 2*r, 2*r)

    def paint(self, painter, option, widget):
        painter.setPen(self._pen)
        if self.isSelected():
            painter.setPen(QPen(Qt.red, self.width + 0.2, Qt.DashLine))
        painter.drawEllipse(self.center, self.radius, self.radius)

    def get_center(self): return self.center

class RectObject(CadObject):
    def __init__(self, top_left, bottom_right, color=Qt.black, width=0.5):
        super().__init__(color, width)
        self.rect = QRectF(top_left, bottom_right).normalized()
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def boundingRect(self):
        return self.rect.adjusted(-self.width, -self.width, self.width, self.width)

    def paint(self, painter, option, widget):
        painter.setPen(self._pen)
        if self.isSelected():
            painter.setPen(QPen(Qt.red, self.width + 0.2, Qt.DashLine))
        painter.drawRect(self.rect)

    def get_corners(self):
        return [self.rect.topLeft(), self.rect.topRight(), self.rect.bottomRight(), self.rect.bottomLeft()]

class TextObject(CadObject):
    def __init__(self, pos, text, height=5.0, color=Qt.black):
        super().__init__(color, 0.0) # Текст не имеет толщины линии в обычном смысле
        self.pos = pos
        self.text = text
        self.height = height
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFont(painter.font() if (painter := QPainter()) else QApplication.font())
        self.font().setPointSizeF(height * 5) # Грубая конвертация для примера

    def boundingRect(self):
        # Приблизительная граница
        return QRectF(self.pos.x(), self.pos.y() - self.height*2, len(self.text)*self.height, self.height*2)

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(Qt.red, 0.5, Qt.DashLine))
            painter.drawRect(self.boundingRect())
        painter.setPen(QPen(QColor(self.color), 1))
        painter.setFont(self.font())
        painter.drawText(self.pos, self.text)

class DimensionObject(CadObject):
    def __init__(self, start, end, value, color=Qt.black, width=0.1):
        super().__init__(color, width)
        self.start = start
        self.end = end
        self.value = value
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def boundingRect(self):
        return QRectF(self.start, self.end).normalized().adjusted(-5, -5, 5, 5)

    def paint(self, painter, option, widget):
        painter.setPen(self._pen)
        if self.isSelected():
            painter.setPen(QPen(Qt.red, self.width + 0.2, Qt.DashLine))
        
        # Рисуем линию размера
        painter.drawLine(self.start, self.end)
        
        # Стрелочки (упрощенно)
        angle = math.atan2(self.end.y() - self.start.y(), self.end.x() - self.start.x())
        arr_len = 5
        p1 = QPointF(self.end.x() - arr_len*math.cos(angle - math.pi/6), self.end.y() - arr_len*math.sin(angle - math.pi/6))
        p2 = QPointF(self.end.x() - arr_len*math.cos(angle + math.pi/6), self.end.y() - arr_len*math.sin(angle + math.pi/6))
        painter.drawLine(self.end, p1)
        painter.drawLine(self.end, p2)
        
        p3 = QPointF(self.start.x() + arr_len*math.cos(angle - math.pi/6), self.start.y() + arr_len*math.sin(angle - math.pi/6))
        p4 = QPointF(self.start.x() + arr_len*math.cos(angle + math.pi/6), self.start.y() + arr_len*math.sin(angle + math.pi/6))
        painter.drawLine(self.start, p3)
        painter.drawLine(self.start, p4)

        # Текст
        mid = QPointF((self.start.x() + self.end.x())/2, (self.start.y() + self.end.y())/2)
        painter.drawText(mid, str(self.value))

class BorderItem(QGraphicsRectItem):
    """Элемент рамки формата."""
    def __init__(self, rect):
        super().__init__(rect)
        pen = QPen(Qt.red, 1, Qt.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.NoBrush))
        self.setZValue(-1) # Позади всех объектов
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations) # Рамка не масштабируется визуально как объект, но следует за сценой? Нет, пусть масштабируется.
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

class CadScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setBackgroundBrush(QBrush(QColor(255, 255, 255))) # Белый фон
        self.hovered_item = None
        self.snap_enabled = True
        self.snap_distance = 10.0 # пикселей
        
        # Рамка формата
        self.border_item = None
        self.current_format = "A4"
        self.update_border()

    def set_hovered_item(self, item):
        if self.hovered_item and self.hovered_item != item:
            self.hovered_item.update()
        self.hovered_item = item
        if item:
            item.update()

    def update_border(self):
        if self.border_item:
            self.removeItem(self.border_item)
        
        w_mm, h_mm = PAPER_FORMATS[self.current_format]
        # Конвертируем мм в единицы сцены (предположим 1мм = 1 единица для простоты, или масштаб)
        # Для экрана удобно использовать масштаб, где А4 вписывается.
        # Но логически координаты лучше хранить в мм.
        rect = QRectF(0, 0, w_mm, h_mm)
        # Центрируем рамку относительно (0,0) для удобства, или оставим в 0,0
        # Сделаем центр рамки в (0,0)
        rect.moveCenter(QPointF(0, 0))
        
        self.border_item = BorderItem(rect)
        self.addItem(self.border_item)

    def get_snap_point(self, point):
        if not self.snap_enabled:
            return point, None
        
        min_dist = self.snap_distance
        snap_pt = point
        snap_type = None
        
        # Проверяем привязки к объектам
        for item in self.items():
            if isinstance(item, CadObject):
                pts = []
                s_type = ""
                if isinstance(item, LineObject):
                    pts = [item.get_start_point(), item.get_end_point()]
                    s_type = "End"
                elif isinstance(item, CircleObject):
                    pts = [item.get_center()]
                    s_type = "Center"
                    # Можно добавить квадранты
                elif isinstance(item, RectObject):
                    pts = item.get_corners()
                    s_type = "Vertex"
                
                for p in pts:
                    dist = math.hypot(p.x() - point.x(), p.y() - point.y())
                    # Переводим дистанцию привязки в координаты сцены примерно
                    # Это упрощение, в реальном CAD нужно учитывать трансформацию вида
                    if dist < 5.0: # Жесткая привязка в координатах сцены
                        if dist < min_dist:
                            min_dist = dist
                            snap_pt = p
                            snap_type = s_type
                            
        return snap_pt, snap_type

class CadView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.current_tool = "select" # select, line, circle, rect, arc, text, dim
        self.start_point = None
        self.temp_item = None
        self.tool_tip = None
        self.snap_tip = None
        
        # Инициализация подсказок
        self.tool_tip = GraphicsTextItem("")
        self.scene().addItem(self.tool_tip)
        self.snap_tip = GraphicsTextItem("")
        self.snap_tip.setPen(QPen(Qt.red))
        self.snap_tip.setFont(self.snap_tip.font().bold())
        self.scene().addItem(self.snap_tip)
        
        self.setCursor(Qt.ArrowCursor)

    def set_tool(self, tool):
        self.current_tool = tool
        self.start_point = None
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
            
        if tool == "select":
            self.setCursor(Qt.ArrowCursor)
            self.tool_tip.hide()
        else:
            self.setCursor(Qt.CrossCursor)
            self.tool_tip.show()
            self.tool_tip.setText(tool.capitalize())

    def fit_format_to_view(self):
        """Вписать текущий формат в окно."""
        if self.scene().border_item:
            rect = self.scene().border_item.boundingRect()
            # Добавляем отступ 10%
            margin = max(rect.width(), rect.height()) * 0.1
            view_rect = rect.adjusted(-margin, -margin, margin, margin)
            self.fitInView(view_rect, Qt.KeepAspectRatio)
        else:
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            snap_pos, snap_type = self.scene().get_snap_point(scene_pos)
            
            if self.current_tool != "select":
                if not self.start_point:
                    self.start_point = snap_pos
                    # Создаем временный объект
                    if self.current_tool == "line":
                        self.temp_item = LineObject(snap_pos, snap_pos)
                        self.temp_item.set_pen_style(Qt.DashLine) # Нужен кастомный метод или доступ к пену
                        # Быстрый хак для пунктира
                        p = self.temp_item._pen
                        p.setStyle(Qt.DashLine)
                        self.temp_item._pen = p
                        
                    elif self.current_tool == "circle":
                        self.temp_item = CircleObject(snap_pos, 0)
                        p = self.temp_item._pen; p.setStyle(Qt.DashLine); self.temp_item._pen = p
                    elif self.current_tool == "rect":
                        self.temp_item = RectObject(snap_pos, snap_pos)
                        p = self.temp_item._pen; p.setStyle(Qt.DashLine); self.temp_item._pen = p
                    
                    if self.temp_item:
                        self.temp_item.set_color(Qt.gray)
                        self.scene().addItem(self.temp_item)
                else:
                    # Второй клик - завершение
                    self.finalize_object(snap_pos)
            else:
                # Логика выбора
                super().mousePressEvent(event)
                
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        snap_pos, snap_type = self.scene().get_snap_point(scene_pos)
        
        # Обновление подсказок
        if self.current_tool != "select":
            self.tool_tip.setPos(scene_pos + QPointF(10, -20))
            if snap_type:
                self.snap_tip.setPos(scene_pos + QPointF(10, -35))
                self.snap_tip.setText(f"Snap: {snap_type}")
                self.snap_tip.show()
                scene_pos = snap_pos # Примагничиваем курсор логически
            else:
                self.snap_tip.hide()
        
        if self.temp_item and self.start_point:
            if self.current_tool == "line":
                self.temp_item.end = scene_pos
            elif self.current_tool == "circle":
                self.temp_item.radius = math.hypot(scene_pos.x() - self.start_point.x(), scene_pos.y() - self.start_point.y())
            elif self.current_tool == "rect":
                self.temp_item.rect = QRectF(self.start_point, scene_pos).normalized()
            self.temp_item.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Обработка отпускания для перетаскивания в режиме выбора
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.temp_item:
                self.scene().removeItem(self.temp_item)
                self.temp_item = None
            self.start_point = None
            self.set_tool("select")
        elif event.key() == Qt.Key_Delete:
            for item in self.scene().selectedItems():
                if isinstance(item, CadObject):
                    self.scene().removeItem(item)
        super().keyPressEvent(event)

    def finalize_object(self, end_point):
        if not self.start_point or not self.temp_item:
            return

        # Удаляем временный объект и создаем постоянный с правильными стилями
        self.scene().removeItem(self.temp_item)
        
        obj = None
        if self.current_tool == "line":
            obj = LineObject(self.start_point, end_point)
        elif self.current_tool == "circle":
            r = math.hypot(end_point.x() - self.start_point.x(), end_point.y() - self.start_point.y())
            obj = CircleObject(self.start_point, r)
        elif self.current_tool == "rect":
            obj = RectObject(self.start_point, end_point)
        
        if obj:
            self.scene().addItem(obj)
        
        self.start_point = None
        self.temp_item = None
        # Остаемся в инструменте для продолжения рисования или переключаем? 
        # Обычно в CAD остаются, пока не нажмут Escape или другой инструмент.

    def wheelEvent(self, event):
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1/factor, 1/factor)
        super().wheelEvent(event)

class CadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 DXF Editor - Updated")
        self.setGeometry(100, 100, 1200, 800)
        
        self.scene = CadScene()
        self.view = CadView(self.scene)
        self.setCentralWidget(self.view)
        
        self.create_toolbar()
        self.create_menu()
        self.statusBar().showMessage("Ready")
        
        # Центрирование и вписывание формата при старте
        self.view.fit_format_to_view()

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        actions = {
            "Select": ("select", "M"),
            "Line": ("line", "L"),
            "Circle": ("circle", "C"),
            "Rect": ("rect", "R"),
            "Text": ("text", "T"),
            "Dim": ("dim", "D")
        }
        
        for name, (tool, shortcut) in actions.items():
            action = QAction(name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, t=tool: self.view.set_tool(t))
            toolbar.addAction(action)
        
        toolbar.addSeparator()
        
        # Выбор формата
        self.format_combo = QComboBox()
        self.format_combo.addItems(PAPER_FORMATS.keys())
        self.format_combo.setCurrentText("A4")
        self.format_combo.currentTextChanged.connect(self.change_format)
        toolbar.addWidget(QLabel(" Format: "))
        toolbar.addWidget(self.format_combo)
        
        toolbar.addSeparator()
        
        exp_html = QAction("Export HTML", self)
        exp_html.triggered.connect(self.export_html)
        toolbar.addAction(exp_html)
        
        exp_dxf = QAction("Export DXF", self)
        exp_dxf.triggered.connect(self.export_dxf)
        toolbar.addAction(exp_dxf)

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        new_act = QAction("New", self)
        new_act.triggered.connect(self.new_file)
        file_menu.addAction(new_act)
        
        file_menu.addSeparator()
        
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)
        
        help_menu = menubar.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(lambda: QMessageBox.information(self, "About", "CAD Editor v2.0"))
        help_menu.addAction(about_act)

    def change_format(self, fmt):
        self.scene.current_format = fmt
        self.scene.update_border()
        self.view.fit_format_to_view()

    def new_file(self):
        self.scene.clear()
        # Восстанавливаем рамку после clear
        self.scene.update_border()
        self.view.fit_format_to_view()
        self.statusBar().showMessage("New file created")

    def export_dxf(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save DXF", "", "DXF Files (*.dxf)")
        if fname:
            doc = ezdxf.new()
            msp = doc.modelspace()
            for item in self.scene.items():
                if isinstance(item, LineObject):
                    msp.add_line((item.start.x(), item.start.y()), (item.end.x(), item.end.y()))
                elif isinstance(item, CircleObject):
                    msp.add_circle((item.center.x(), item.center.y()), item.radius)
                elif isinstance(item, RectObject):
                    # Прямоугольник как полилиния
                    pts = [(p.x(), p.y()) for p in item.get_corners()]
                    pts.append(pts[0])
                    msp.add_lwpolyline(pts)
            doc.saveas(fname)
            self.statusBar().showMessage(f"Saved to {fname}")

    def export_html(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export HTML", "", "HTML Files (*.html)")
        if not fname:
            return
        
        # Генерация SVG контента из сцены
        svg_elements = []
        # Получаем границы рамки для viewBox
        if self.scene.border_item:
            r = self.scene.border_item.rect()
            # SVG координаты: Y инвертирован обычно, но для простоты оставим как есть, 
            # либо сдвинем все в положительную зону.
            # Сдвинем все так, чтобы левый нижний угол рамки был (0,0)
            offset_x = -r.left()
            offset_y = -r.top() # В графике Y вниз, в математике вверх. Оставим экранную систему.
            
            # Рамка
            svg_elements.append(f'<rect x="{offset_x}" y="{offset_y}" width="{r.width()}" height="{r.height()}" '
                                f'stroke="red" stroke-width="1" fill="none" stroke-dasharray="5,5" />')
            
            for item in self.scene.items():
                if isinstance(item, BorderItem): continue
                
                if isinstance(item, LineObject):
                    x1, y1 = item.start.x() + offset_x, item.start.y() + offset_y
                    x2, y2 = item.end.x() + offset_x, item.end.y() + offset_y
                    c = item.color.name() if isinstance(item.color, QColor) else QColor(item.color).name()
                    svg_elements.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{item.width}" />')
                
                elif isinstance(item, CircleObject):
                    cx, cy = item.center.x() + offset_x, item.center.y() + offset_y
                    c = item.color.name() if isinstance(item.color, QColor) else QColor(item.color).name()
                    svg_elements.append(f'<circle cx="{cx}" cy="{cy}" r="{item.radius}" stroke="{c}" stroke-width="{item.width}" fill="none" />')
                
                elif isinstance(item, RectObject):
                    x, y = item.rect.left() + offset_x, item.rect.top() + offset_y
                    w, h = item.rect.width(), item.rect.height()
                    c = item.color.name() if isinstance(item.color, QColor) else QColor(item.color).name()
                    svg_elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="{c}" stroke-width="{item.width}" fill="none" />')
                
                elif isinstance(item, TextObject):
                    x, y = item.pos.x() + offset_x, item.pos.y() + offset_y
                    # SVG текст: базовая линия внизу, в QGraphics сверху. Нужно инвертировать Y для текста или сдвигать.
                    # Упрощенно:
                    svg_elements.append(f'<text x="{x}" y="{y}" fill="black" font-size="{item.height*5}">{item.text}</text>')

        svg_content = "\n".join(svg_elements)
        width = r.width()
        height = r.height()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DXF Export</title>
<style>
    body {{ margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f0f0; }}
    .container {{ background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
    svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<div class="container">
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
{svg_content}
</svg>
</div>
</body>
</html>"""
        
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(html)
        self.statusBar().showMessage(f"Exported to {fname}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CadWindow()
    window.show()
    sys.exit(app.exec_())
