--- drawing_editor/ui/main_window.py (原始)
"""
Main window for the CAD drawing editor.

This module provides the CadWindow class which serves as the primary
application window containing all UI elements and coordinating user actions.
"""

from typing import Optional, Dict, Any
import sys
import traceback

from PyQt5.QtWidgets import (
    QMainWindow,
    QGraphicsScene,
    QToolBar,
    QAction,
    QStatusBar,
    QLabel,
    QDockWidget,
    QListWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QApplication,
    QColorDialog,
    QLineEdit,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainter, QTransform
from PyQt5.QtPrintSupport import QPrinter
import ezdxf
from ezdxf.math import Vec3
import json

from drawing_editor.core.models import (
    GraphicObject,
    PointObject,
    LineObject,
    CircleObject,
    RectObject,
    ArcObject,
    TextObject,
    DimensionObject,
)
from drawing_editor.ui.graphics_items import (
    GraphicsPoint,
    GraphicsLine,
    GraphicsCircle,
    GraphicsRect,
    GraphicsArc,
    GraphicsText,
    GraphicsDimension,
)
from drawing_editor.ui.cad_view import CadView
from drawing_editor.ui.dialogs import PropertyDialog


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

        # Формат бумаги (по умолчанию A0)
        self.paper_format = "A0"
        self.paper_sizes = {
            "A0": (1189, 841),   # мм
            "A1": (841, 594),
            "A2": (594, 420),
            "A3": (420, 297),
            "A4": (297, 210),
        }

        self.init_ui()
        self.init_statusbar()
        self.create_empty_document()

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
        export_pdf_action = QAction("Export PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        export_html_action = QAction("Export HTML", self)
        export_html_action.triggered.connect(self.export_html)

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

        # Кнопка убрать толщину линии
        remove_width_action = QAction("Remove Line Width", self)
        remove_width_action.triggered.connect(self.remove_line_width)
        toolbar.addAction(remove_width_action)

        # Кнопка удлинить объект
        extend_action = QAction("Extend", self)
        extend_action.triggered.connect(self.extend_selected)
        toolbar.addAction(extend_action)

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

        # Выбор формата бумаги
        paper_group = QGroupBox("Paper Format")
        paper_layout = QFormLayout()
        self.paper_format_combo = QComboBox()
        self.paper_format_combo.addItems(["A0", "A1", "A2", "A3", "A4"])
        self.paper_format_combo.setCurrentText("A0")
        self.paper_format_combo.currentTextChanged.connect(self.on_paper_format_changed)
        paper_layout.addRow("Format:", self.paper_format_combo)
        paper_group.setLayout(paper_layout)
        layout_right.addWidget(paper_group)

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

    def create_empty_document(self):
        self.dxf_doc = ezdxf.new('R2010')
        self.dxf_modelspace = self.dxf_doc.modelspace()
        self.current_file = None
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()
        self.status_label.setText("New document (unsaved)")
        self.update_scene_rect()
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

    def on_paper_format_changed(self, format_name):
        """Изменение формата бумаги и центрирование объектов."""
        self.paper_format = format_name
        self.update_scene_rect()
        if self.scene.items():
            self.center_objects_in_viewport()

    def get_paper_rect_mm(self):
        """Получить прямоугольник области редактирования в мм."""
        width_mm, height_mm = self.paper_sizes.get(self.paper_format, (1189, 841))
        return QRectF(0, 0, width_mm, height_mm)

    def update_scene_rect(self):
        """Обновить размер сцены согласно формату бумаги."""
        paper_rect = self.get_paper_rect_mm()
        self.scene.setSceneRect(paper_rect)

    def center_objects_in_viewport(self):
        """Центрировать все объекты в центре области редактирования."""
        if not self.scene.items():
            return

        # Получить границы всех объектов
        items_bbox = self.scene.itemsBoundingRect()
        if items_bbox.isEmpty():
            return

        # Получить текущую область редактирования
        paper_rect = self.get_paper_rect_mm()

        # Вычислить центр области редактирования
        paper_center = paper_rect.center()

        # Вычислить центр объектов
        items_center = items_bbox.center()

        # Вычислить смещение для центрирования
        dx = paper_center.x() - items_center.x()
        dy = paper_center.y() - items_center.y()

        # Переместить все объекты
        for item in self.scene.items():
            item.moveBy(dx, dy)

        # Обновить отображение
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

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

    def remove_line_width(self):
        """Убрать толщину линии у выделенных объектов."""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        for item in selected:
            if hasattr(item, 'pen'):
                pen = item.pen()
                pen.setWidthF(0.1)  # Минимальная толщина
                item.setPen(pen)
                # Обновить DXF entity если есть
                for obj in self.obj_map.values():
                    if obj.graphics_item == item and obj.dxf_entity:
                        try:
                            obj.dxf_entity.dxf.lineweight = 0
                        except AttributeError:
                            pass
                        break
        self.update_selected_properties()
        QMessageBox.information(self, "Done", "Line width removed from selected object(s).")

    def extend_selected(self):
        """Удлинить выделенный объект на заданную величину."""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        item = selected[0]
        for obj in self.obj_map.values():
            if obj.graphics_item == item:
                if obj.type == "Line":
                    length_val, ok = QInputDialog.getDouble(self, "Extend", "Enter extension length:", 10.0, 0.1, 1000.0, 2)
                    if ok and length_val > 0:
                        # Удлинить линию в обоих направлениях на половину значения
                        import math
                        dx = obj.x2 - obj.x1
                        dy = obj.y2 - obj.y1
                        length = math.hypot(dx, dy)
                        if length > 0:
                            unit_x = dx / length
                            unit_y = dy / length
                            half_ext = length_val / 2
                            new_x1 = obj.x1 - unit_x * half_ext
                            new_y1 = obj.y1 - unit_y * half_ext
                            new_x2 = obj.x2 + unit_x * half_ext
                            new_y2 = obj.y2 + unit_y * half_ext
                            # Обновить объект
                            obj.x1, obj.y1 = new_x1, new_y1
                            obj.x2, obj.y2 = new_x2, new_y2
                            # Обновить графику
                            if hasattr(item, 'setLine'):
                                from PyQt5.QtCore import QLineF
                                item.setLine(QLineF(new_x1, new_y1, new_x2, new_y2))
                            # Обновить DXF entity если есть
                            if obj.dxf_entity:
                                try:
                                    obj.dxf_entity.dxf.start = (new_x1, new_y1, 0)
                                    obj.dxf_entity.dxf.end = (new_x2, new_y2, 0)
                                except AttributeError:
                                    pass
                            self.update_selected_properties()
                            QMessageBox.information(self, "Done", f"Line extended by {length_val:.2f}.")
                        else:
                            QMessageBox.warning(self, "Error", "Cannot extend zero-length line.")
                    return
                else:
                    QMessageBox.information(self, "Info", "Extend is only available for Line objects.")
                    return

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
            new_msp = new_doc.modelspace()
            for entity in self.dxf_modelspace:
                new_msp.add_entity(entity.copy())
            new_doc.saveas(fname)
            self.current_file = fname
            self.dxf_doc = new_doc
            self.dxf_modelspace = self.dxf_doc.modelspace()
            QMessageBox.information(self, "Saved", f"File saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

    def export_pdf(self):
        """Экспорт текущей сцены в PDF с масштабированием."""
        if not self.scene.items():
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
        if not fname:
            return

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fname)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Landscape)

            bbox = self.scene.itemsBoundingRect()
            if bbox.isEmpty():
                QMessageBox.warning(self, "Warning", "Empty drawing.")
                return

            painter = QPainter(printer)
            painter.setRenderHint(QPainter.Antialiasing)

            page_rect = printer.pageRect(QPrinter.DevicePixel)
            scale_x = page_rect.width() / bbox.width()
            scale_y = page_rect.height() / bbox.height()
            scale = min(scale_x, scale_y) * 0.9

            painter.translate(page_rect.center())
            painter.scale(scale, scale)
            painter.translate(-bbox.center())

            self.scene.render(painter)
            painter.end()

            QMessageBox.information(self, "Exported", f"PDF saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF:\n{str(e)}")
            traceback.print_exc()

    def export_html(self):
        """Экспорт текущей сцены в HTML с границами рабочей области А4."""
        if not self.scene.items():
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export HTML", "", "HTML Files (*.html)")
        if not fname:
            return

        # Размеры А4 в мм (по умолчанию)
        a4_width_mm = 210
        a4_height_mm = 297
        # Преобразуем в пиксели (при 96 DPI)
        mm_to_px = 96 / 25.4
        a4_width_px = a4_width_mm * mm_to_px
        a4_height_px = a4_height_mm * mm_to_px

        bbox = self.scene.itemsBoundingRect()
        if bbox.isEmpty():
            QMessageBox.warning(self, "Warning", "Empty drawing.")
            return

        # Собираем данные объектов для экспорта
        objects_data = []
        for obj in self.obj_map.values():
            item = obj.graphics_item
            pen = item.pen() if hasattr(item, 'pen') else QPen(QColor(0, 0, 0))
            color = pen.color().name() if hasattr(pen, 'color') else "#000000"
            width = pen.widthF() if hasattr(pen, 'widthF') else 0.2

            obj_data = {
                'type': obj.type,
                'color': color,
                'width': width,
            }

            if obj.type == "Line":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
            elif obj.type == "Circle":
                obj_data['cx'] = obj.cx
                obj_data['cy'] = obj.cy
                obj_data['radius'] = obj.radius
            elif obj.type == "Rectangle":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
            elif obj.type == "Arc":
                obj_data['cx'] = obj.cx
                obj_data['cy'] = obj.cy
                obj_data['radius'] = obj.radius
                obj_data['start_angle'] = obj.start_angle
                obj_data['end_angle'] = obj.end_angle
            elif obj.type == "Text":
                obj_data['x'] = obj.x
                obj_data['y'] = obj.y
                obj_data['text'] = obj.text
            elif obj.type == "Dimension":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
                obj_data['dim_type'] = getattr(obj, 'dim_type', 'Linear')

            objects_data.append(obj_data)

        # Генерируем HTML
        html_content = self._generate_html(objects_data, bbox, a4_width_px, a4_height_px)

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(html_content)
            QMessageBox.information(self, "Exported", f"HTML saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def _generate_html(self, objects_data, bbox, a4_width_px, a4_height_px):
        """Генерация HTML содержимого для экспорта."""
        # Вычисляем масштаб для отображения
        margin = 20
        view_width = a4_width_px + margin * 2
        view_height = a4_height_px + margin * 2

        # Определяем масштабирование для fit
        draw_width = bbox.width() if bbox.width() > 0 else 1
        draw_height = bbox.height() if bbox.height() > 0 else 1
        scale = min(a4_width_px / draw_width, a4_height_px / draw_height) * 0.9

        # Центрируем чертеж на странице А4
        offset_x = margin + (a4_width_px - draw_width * scale) / 2
        offset_y = margin + (a4_height_px - draw_height * scale) / 2

        objects_json = json.dumps(objects_data)

        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAD Drawing Export</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
        }}
        svg {{
            display: block;
        }}
        .a4-border {{
            fill: none;
            stroke: #ff0000;
            stroke-width: 2;
            stroke-dasharray: 5,5;
        }}
        .drawing-item {{
            vector-effect: non-scaling-stroke;
        }}
    </style>
</head>
<body>
    <div class="container">
        <svg id="cad-svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">
            <!-- Границы рабочей области А4 -->
            <rect class="a4-border" x="{margin}" y="{margin}" width="{a4_width_px}" height="{a4_height_px}" />
            <!-- Объекты чертежа будут добавлены через JS -->
        </svg>
    </div>
    <script>
        (function() {{
            const objects = {objects_json};
            const svg = document.getElementById('cad-svg');
            const scale = {scale};
            const offsetX = {offset_x};
            const offsetY = {offset_y};
            const bboxX = {bbox.left()};
            const bboxY = {bbox.top()};

            function transformX(x) {{
                return offsetX + (x - bboxX) * scale;
            }}

            function transformY(y) {{
                // SVG Y ось направлена вниз, инвертируем для CAD координат
                return offsetY + (y - bboxY) * scale;
            }}

            objects.forEach(obj => {{
                let element;
                const attrs = {{
                    class: 'drawing-item',
                    stroke: obj.color || '#000000',
                    'stroke-width': obj.width || 0.2,
                    fill: 'none'
                }};

                switch(obj.type) {{
                    case 'Line':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        element.setAttribute('x1', transformX(obj.x1));
                        element.setAttribute('y1', transformY(obj.y1));
                        element.setAttribute('x2', transformX(obj.x2));
                        element.setAttribute('y2', transformY(obj.y2));
                        break;

                    case 'Circle':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                        element.setAttribute('cx', transformX(obj.cx));
                        element.setAttribute('cy', transformY(obj.cy));
                        element.setAttribute('r', obj.radius * scale);
                        break;

                    case 'Rectangle':
                        const rectX = Math.min(obj.x1, obj.x2);
                        const rectY = Math.min(obj.y1, obj.y2);
                        const rectW = Math.abs(obj.x2 - obj.x1);
                        const rectH = Math.abs(obj.y2 - obj.y1);
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        element.setAttribute('x', transformX(rectX));
                        element.setAttribute('y', transformY(rectY));
                        element.setAttribute('width', rectW * scale);
                        element.setAttribute('height', rectH * scale);
                        break;

                    case 'Arc':
                        const startRad = obj.start_angle * Math.PI / 180;
                        const endRad = obj.end_angle * Math.PI / 180;
                        const cx = transformX(obj.cx);
                        const cy = transformY(obj.cy);
                        const r = obj.radius * scale;
                        const x1 = cx + r * Math.cos(startRad);
                        const y1 = cy + r * Math.sin(startRad);
                        const x2 = cx + r * Math.cos(endRad);
                        const y2 = cy + r * Math.sin(endRad);
                        const largeArcFlag = Math.abs(obj.end_angle - obj.start_angle) > 180 ? 1 : 0;
                        const d = `M ${{x1}} ${{y1}} A ${{r}} ${{r}} 0 ${{largeArcFlag}} 1 ${{x2}} ${{y2}}`;
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                        element.setAttribute('d', d);
                        break;

                    case 'Text':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        element.setAttribute('x', transformX(obj.x));
                        element.setAttribute('y', transformY(obj.y));
                        element.setAttribute('fill', obj.color || '#000000');
                        element.setAttribute('font-size', '12');
                        element.setAttribute('font-family', 'Arial');
                        element.textContent = obj.text || '';
                        break;

                    case 'Dimension':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        element.setAttribute('x1', transformX(obj.x1));
                        element.setAttribute('y1', transformY(obj.y1));
                        element.setAttribute('x2', transformX(obj.x2));
                        element.setAttribute('y2', transformY(obj.y2));
                        element.setAttribute('stroke-dasharray', '2,2');
                        break;
                }}

                if (element) {{
                    for (const [key, value] of Object.entries(attrs)) {{
                        if (!element.hasAttribute(key) && key !== 'fill') {{
                            element.setAttribute(key, value);
                        }}
                    }}
                    svg.appendChild(element);
                }}
            }});
        }})();
    </script>
</body>
</html>'''
        return html

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
            # Обновить область сцены согласно формату бумаги
            self.update_scene_rect()
            # Центрировать объекты в области редактирования
            self.center_objects_in_viewport()

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
                    self.update_selected_properties()
                break

    def update_list(self):
        self.list_widget.clear()
        for obj in self.obj_map.values():
            self.list_widget.addItem(self.object_description(obj))
        # Auto-fit view to show all content after list update
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def trim_object(self, item):
        """Удалить часть объекта (линии) при пересечении с другим объектом."""
        if not hasattr(item, 'line'):
            return

        # Найти все другие линии для поиска пересечений
        from PyQt5.QtCore import QLineF
        line_obj = item.line()

        # Найти ближайшую линию для обрезки
        cutting_line = None
        intersection_point = None

        for other_item in self.scene().items():
            if other_item == item or not hasattr(other_item, 'line'):
                continue
            other_line = other_item.line()

            # Проверить пересечение
            intersect_type, pt = line_obj.intersect(other_line)
            if intersect_type == QLineF.BoundedIntersection:
                cutting_line = other_line
                intersection_point = pt
                break

        if intersection_point and cutting_line:
            # Определить, какую часть удалить (ближайшую к клику)
            # Для простоты удаляем весь объект если есть пересечение
            # В будущем можно улучшить логику для удаления только части
            for obj_key, obj in list(self.obj_map.items()):
                if obj.graphics_item == item:
                    if obj in self.obj_map:
                        del self.obj_map[obj_key]
                    break
            self.scene().removeItem(item)
            self.update_list()
            self.update_selected_properties()

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
        # Auto-fit view to show all content
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
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
        # Auto-fit view to show all content
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
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

+++ drawing_editor/ui/main_window.py (修改后)
"""
Main window for the CAD drawing editor.

This module provides the CadWindow class which serves as the primary
application window containing all UI elements and coordinating user actions.
"""

from typing import Optional, Dict, Any
import sys
import traceback

from PyQt5.QtWidgets import (
    QMainWindow,
    QGraphicsScene,
    QToolBar,
    QAction,
    QStatusBar,
    QLabel,
    QDockWidget,
    QListWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QApplication,
    QColorDialog,
    QLineEdit,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainter, QTransform
from PyQt5.QtPrintSupport import QPrinter
import ezdxf
from ezdxf.math import Vec3
import json

from drawing_editor.core.models import (
    GraphicObject,
    PointObject,
    LineObject,
    CircleObject,
    RectObject,
    ArcObject,
    TextObject,
    DimensionObject,
)
from drawing_editor.ui.graphics_items import (
    GraphicsPoint,
    GraphicsLine,
    GraphicsCircle,
    GraphicsRect,
    GraphicsArc,
    GraphicsText,
    GraphicsDimension,
)
from drawing_editor.ui.cad_view import CadView
from drawing_editor.ui.dialogs import PropertyDialog
from drawing_editor.core.geometry import GeometryEngine


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

        # Формат бумаги (по умолчанию A0)
        self.paper_format = "A0"
        self.paper_sizes = {
            "A0": (1189, 841),   # мм
            "A1": (841, 594),
            "A2": (594, 420),
            "A3": (420, 297),
            "A4": (297, 210),
        }

        self.init_ui()
        self.init_statusbar()
        self.create_empty_document()

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
        export_pdf_action = QAction("Export PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        export_html_action = QAction("Export HTML", self)
        export_html_action.triggered.connect(self.export_html)

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

        # Кнопка убрать толщину линии
        remove_width_action = QAction("Remove Line Width", self)
        remove_width_action.triggered.connect(self.remove_line_width)
        toolbar.addAction(remove_width_action)

        # Кнопка удлинить объект
        extend_action = QAction("Extend", self)
        extend_action.triggered.connect(self.extend_selected)
        toolbar.addAction(extend_action)

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

        # Выбор формата бумаги
        paper_group = QGroupBox("Paper Format")
        paper_layout = QFormLayout()
        self.paper_format_combo = QComboBox()
        self.paper_format_combo.addItems(["A0", "A1", "A2", "A3", "A4"])
        self.paper_format_combo.setCurrentText("A0")
        self.paper_format_combo.currentTextChanged.connect(self.on_paper_format_changed)
        paper_layout.addRow("Format:", self.paper_format_combo)
        paper_group.setLayout(paper_layout)
        layout_right.addWidget(paper_group)

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

    def create_empty_document(self):
        self.dxf_doc = ezdxf.new('R2010')
        self.dxf_modelspace = self.dxf_doc.modelspace()
        self.current_file = None
        self.scene.clear()
        self.list_widget.clear()
        self.obj_map.clear()
        self.status_label.setText("New document (unsaved)")
        self.update_scene_rect()
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

    def on_paper_format_changed(self, format_name):
        """Изменение формата бумаги и центрирование объектов."""
        self.paper_format = format_name
        self.update_scene_rect()
        if self.scene.items():
            self.center_objects_in_viewport()

    def get_paper_rect_mm(self):
        """Получить прямоугольник области редактирования в мм."""
        width_mm, height_mm = self.paper_sizes.get(self.paper_format, (1189, 841))
        return QRectF(0, 0, width_mm, height_mm)

    def update_scene_rect(self):
        """Обновить размер сцены согласно формату бумаги."""
        paper_rect = self.get_paper_rect_mm()
        self.scene.setSceneRect(paper_rect)

    def center_objects_in_viewport(self):
        """Центрировать все объекты в центре области редактирования."""
        if not self.scene.items():
            return

        # Получить границы всех объектов
        items_bbox = self.scene.itemsBoundingRect()
        if items_bbox.isEmpty():
            return

        # Получить текущую область редактирования
        paper_rect = self.get_paper_rect_mm()

        # Вычислить центр области редактирования
        paper_center = paper_rect.center()

        # Вычислить центр объектов
        items_center = items_bbox.center()

        # Вычислить смещение для центрирования
        dx = paper_center.x() - items_center.x()
        dy = paper_center.y() - items_center.y()

        # Переместить все объекты
        for item in self.scene.items():
            item.moveBy(dx, dy)

        # Обновить отображение
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

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

    def remove_line_width(self):
        """Убрать толщину линии у выделенных объектов."""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        for item in selected:
            if hasattr(item, 'pen'):
                pen = item.pen()
                pen.setWidthF(0.1)  # Минимальная толщина
                item.setPen(pen)
                # Обновить DXF entity если есть
                for obj in self.obj_map.values():
                    if obj.graphics_item == item and obj.dxf_entity:
                        try:
                            obj.dxf_entity.dxf.lineweight = 0
                        except AttributeError:
                            pass
                        break
        self.update_selected_properties()
        QMessageBox.information(self, "Done", "Line width removed from selected object(s).")

    def extend_selected(self):
        """Удлинить выделенный объект на заданную величину."""
        selected = self.scene.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "No object selected.")
            return
        item = selected[0]
        for obj in self.obj_map.values():
            if obj.graphics_item == item:
                if obj.type == "Line":
                    length_val, ok = QInputDialog.getDouble(self, "Extend", "Enter extension length:", 10.0, 0.1, 1000.0, 2)
                    if ok and length_val > 0:
                        # Удлинить линию в обоих направлениях на половину значения
                        import math
                        dx = obj.x2 - obj.x1
                        dy = obj.y2 - obj.y1
                        length = math.hypot(dx, dy)
                        if length > 0:
                            unit_x = dx / length
                            unit_y = dy / length
                            half_ext = length_val / 2
                            new_x1 = obj.x1 - unit_x * half_ext
                            new_y1 = obj.y1 - unit_y * half_ext
                            new_x2 = obj.x2 + unit_x * half_ext
                            new_y2 = obj.y2 + unit_y * half_ext
                            # Обновить объект
                            obj.x1, obj.y1 = new_x1, new_y1
                            obj.x2, obj.y2 = new_x2, new_y2
                            # Обновить графику
                            if hasattr(item, 'setLine'):
                                from PyQt5.QtCore import QLineF
                                item.setLine(QLineF(new_x1, new_y1, new_x2, new_y2))
                            # Обновить DXF entity если есть
                            if obj.dxf_entity:
                                try:
                                    obj.dxf_entity.dxf.start = (new_x1, new_y1, 0)
                                    obj.dxf_entity.dxf.end = (new_x2, new_y2, 0)
                                except AttributeError:
                                    pass
                            self.update_selected_properties()
                            QMessageBox.information(self, "Done", f"Line extended by {length_val:.2f}.")
                        else:
                            QMessageBox.warning(self, "Error", "Cannot extend zero-length line.")
                    return
                else:
                    QMessageBox.information(self, "Info", "Extend is only available for Line objects.")
                    return

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
            new_msp = new_doc.modelspace()
            for entity in self.dxf_modelspace:
                new_msp.add_entity(entity.copy())
            new_doc.saveas(fname)
            self.current_file = fname
            self.dxf_doc = new_doc
            self.dxf_modelspace = self.dxf_doc.modelspace()
            QMessageBox.information(self, "Saved", f"File saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")

    def export_pdf(self):
        """Экспорт текущей сцены в PDF с масштабированием."""
        if not self.scene.items():
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
        if not fname:
            return

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fname)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Landscape)

            bbox = self.scene.itemsBoundingRect()
            if bbox.isEmpty():
                QMessageBox.warning(self, "Warning", "Empty drawing.")
                return

            painter = QPainter(printer)
            painter.setRenderHint(QPainter.Antialiasing)

            page_rect = printer.pageRect(QPrinter.DevicePixel)
            scale_x = page_rect.width() / bbox.width()
            scale_y = page_rect.height() / bbox.height()
            scale = min(scale_x, scale_y) * 0.9

            painter.translate(page_rect.center())
            painter.scale(scale, scale)
            painter.translate(-bbox.center())

            self.scene.render(painter)
            painter.end()

            QMessageBox.information(self, "Exported", f"PDF saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF:\n{str(e)}")
            traceback.print_exc()

    def export_html(self):
        """Экспорт текущей сцены в HTML с границами рабочей области А4."""
        if not self.scene.items():
            QMessageBox.warning(self, "Warning", "Nothing to export.")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export HTML", "", "HTML Files (*.html)")
        if not fname:
            return

        # Размеры А4 в мм (по умолчанию)
        a4_width_mm = 210
        a4_height_mm = 297
        # Преобразуем в пиксели (при 96 DPI)
        mm_to_px = 96 / 25.4
        a4_width_px = a4_width_mm * mm_to_px
        a4_height_px = a4_height_mm * mm_to_px

        bbox = self.scene.itemsBoundingRect()
        if bbox.isEmpty():
            QMessageBox.warning(self, "Warning", "Empty drawing.")
            return

        # Собираем данные объектов для экспорта
        objects_data = []
        for obj in self.obj_map.values():
            item = obj.graphics_item
            pen = item.pen() if hasattr(item, 'pen') else QPen(QColor(0, 0, 0))
            color = pen.color().name() if hasattr(pen, 'color') else "#000000"
            width = pen.widthF() if hasattr(pen, 'widthF') else 0.2

            obj_data = {
                'type': obj.type,
                'color': color,
                'width': width,
            }

            if obj.type == "Line":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
            elif obj.type == "Circle":
                obj_data['cx'] = obj.cx
                obj_data['cy'] = obj.cy
                obj_data['radius'] = obj.radius
            elif obj.type == "Rectangle":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
            elif obj.type == "Arc":
                obj_data['cx'] = obj.cx
                obj_data['cy'] = obj.cy
                obj_data['radius'] = obj.radius
                obj_data['start_angle'] = obj.start_angle
                obj_data['end_angle'] = obj.end_angle
            elif obj.type == "Text":
                obj_data['x'] = obj.x
                obj_data['y'] = obj.y
                obj_data['text'] = obj.text
            elif obj.type == "Dimension":
                obj_data['x1'] = obj.x1
                obj_data['y1'] = obj.y1
                obj_data['x2'] = obj.x2
                obj_data['y2'] = obj.y2
                obj_data['dim_type'] = getattr(obj, 'dim_type', 'Linear')

            objects_data.append(obj_data)

        # Генерируем HTML
        html_content = self._generate_html(objects_data, bbox, a4_width_px, a4_height_px)

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(html_content)
            QMessageBox.information(self, "Exported", f"HTML saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def _generate_html(self, objects_data, bbox, a4_width_px, a4_height_px):
        """Генерация HTML содержимого для экспорта."""
        # Вычисляем масштаб для отображения
        margin = 20
        view_width = a4_width_px + margin * 2
        view_height = a4_height_px + margin * 2

        # Определяем масштабирование для fit
        draw_width = bbox.width() if bbox.width() > 0 else 1
        draw_height = bbox.height() if bbox.height() > 0 else 1
        scale = min(a4_width_px / draw_width, a4_height_px / draw_height) * 0.9

        # Центрируем чертеж на странице А4
        offset_x = margin + (a4_width_px - draw_width * scale) / 2
        offset_y = margin + (a4_height_px - draw_height * scale) / 2

        objects_json = json.dumps(objects_data)

        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAD Drawing Export</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
        }}
        svg {{
            display: block;
        }}
        .a4-border {{
            fill: none;
            stroke: #ff0000;
            stroke-width: 2;
            stroke-dasharray: 5,5;
        }}
        .drawing-item {{
            vector-effect: non-scaling-stroke;
        }}
    </style>
</head>
<body>
    <div class="container">
        <svg id="cad-svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">
            <!-- Границы рабочей области А4 -->
            <rect class="a4-border" x="{margin}" y="{margin}" width="{a4_width_px}" height="{a4_height_px}" />
            <!-- Объекты чертежа будут добавлены через JS -->
        </svg>
    </div>
    <script>
        (function() {{
            const objects = {objects_json};
            const svg = document.getElementById('cad-svg');
            const scale = {scale};
            const offsetX = {offset_x};
            const offsetY = {offset_y};
            const bboxX = {bbox.left()};
            const bboxY = {bbox.top()};

            function transformX(x) {{
                return offsetX + (x - bboxX) * scale;
            }}

            function transformY(y) {{
                // SVG Y ось направлена вниз, инвертируем для CAD координат
                return offsetY + (y - bboxY) * scale;
            }}

            objects.forEach(obj => {{
                let element;
                const attrs = {{
                    class: 'drawing-item',
                    stroke: obj.color || '#000000',
                    'stroke-width': obj.width || 0.2,
                    fill: 'none'
                }};

                switch(obj.type) {{
                    case 'Line':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        element.setAttribute('x1', transformX(obj.x1));
                        element.setAttribute('y1', transformY(obj.y1));
                        element.setAttribute('x2', transformX(obj.x2));
                        element.setAttribute('y2', transformY(obj.y2));
                        break;

                    case 'Circle':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                        element.setAttribute('cx', transformX(obj.cx));
                        element.setAttribute('cy', transformY(obj.cy));
                        element.setAttribute('r', obj.radius * scale);
                        break;

                    case 'Rectangle':
                        const rectX = Math.min(obj.x1, obj.x2);
                        const rectY = Math.min(obj.y1, obj.y2);
                        const rectW = Math.abs(obj.x2 - obj.x1);
                        const rectH = Math.abs(obj.y2 - obj.y1);
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        element.setAttribute('x', transformX(rectX));
                        element.setAttribute('y', transformY(rectY));
                        element.setAttribute('width', rectW * scale);
                        element.setAttribute('height', rectH * scale);
                        break;

                    case 'Arc':
                        const startRad = obj.start_angle * Math.PI / 180;
                        const endRad = obj.end_angle * Math.PI / 180;
                        const cx = transformX(obj.cx);
                        const cy = transformY(obj.cy);
                        const r = obj.radius * scale;
                        const x1 = cx + r * Math.cos(startRad);
                        const y1 = cy + r * Math.sin(startRad);
                        const x2 = cx + r * Math.cos(endRad);
                        const y2 = cy + r * Math.sin(endRad);
                        const largeArcFlag = Math.abs(obj.end_angle - obj.start_angle) > 180 ? 1 : 0;
                        const d = `M ${{x1}} ${{y1}} A ${{r}} ${{r}} 0 ${{largeArcFlag}} 1 ${{x2}} ${{y2}}`;
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                        element.setAttribute('d', d);
                        break;

                    case 'Text':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        element.setAttribute('x', transformX(obj.x));
                        element.setAttribute('y', transformY(obj.y));
                        element.setAttribute('fill', obj.color || '#000000');
                        element.setAttribute('font-size', '12');
                        element.setAttribute('font-family', 'Arial');
                        element.textContent = obj.text || '';
                        break;

                    case 'Dimension':
                        element = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        element.setAttribute('x1', transformX(obj.x1));
                        element.setAttribute('y1', transformY(obj.y1));
                        element.setAttribute('x2', transformX(obj.x2));
                        element.setAttribute('y2', transformY(obj.y2));
                        element.setAttribute('stroke-dasharray', '2,2');
                        break;
                }}

                if (element) {{
                    for (const [key, value] of Object.entries(attrs)) {{
                        if (!element.hasAttribute(key) && key !== 'fill') {{
                            element.setAttribute(key, value);
                        }}
                    }}
                    svg.appendChild(element);
                }}
            }});
        }})();
    </script>
</body>
</html>'''
        return html

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
            # Обновить область сцены согласно формату бумаги
            self.update_scene_rect()
            # Центрировать объекты в области редактирования
            self.center_objects_in_viewport()

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
                    self.update_selected_properties()
                break

    def update_list(self):
        self.list_widget.clear()
        for obj in self.obj_map.values():
            self.list_widget.addItem(self.object_description(obj))
        # Auto-fit view to show all content after list update
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def trim_object(self, item, click_pos: Optional[QPointF] = None):
        """
        Trim (cut) an object at intersection points with other objects.

        The command requires:
        1. Cutting edges (objects that act as "knives")
        2. Objects to trim and click points to determine which segment to remove

        Args:
            item: The graphics item clicked for trimming
            click_pos: The position where user clicked (determines which segment to delete)
        """
        from PyQt5.QtCore import QLineF

        # Get all scene items
        all_items = list(self.scene().items())

        # Find the object corresponding to the clicked item
        target_obj = None
        for obj_key, obj in self.obj_map.items():
            if obj.graphics_item == item:
                target_obj = obj
                break

        if not target_obj:
            return

        # Find all intersection points between target and other objects
        intersections = []

        for other_item in all_items:
            if other_item == item:
                continue

            # Get other object from map
            other_obj = None
            for obj_key, obj in self.obj_map.items():
                if obj.graphics_item == other_item:
                    other_obj = obj
                    break

            if not other_obj:
                continue

            # Use GeometryEngine to find intersections
            try:
                results = GeometryEngine.find_intersections(target_obj, other_obj)
                for res in results:
                    intersections.append((QPointF(res.point.x, res.point.y), other_item))
            except Exception:
                # Fallback to simple line-line intersection for GraphicsLine items
                if hasattr(item, 'line') and hasattr(other_item, 'line'):
                    line_obj = item.line()
                    other_line = other_item.line()
                    intersect_type, pt = line_obj.intersect(other_line)
                    if intersect_type == QLineF.BoundedIntersection:
                        intersections.append((pt, other_item))

        if not intersections:
            # No intersections found - cannot trim
            return

        # If click position is provided, determine which segment to remove
        if click_pos:
            # For lines: split at intersection point closest to click, remove segment containing click
            if isinstance(target_obj, LineObject):
                self._trim_line_at_intersections(item, target_obj, intersections, click_pos)
        else:
            # Default behavior: remove the entire object if it has intersections
            # This is a fallback for simple cases
            if item in self.scene().items():
                for obj_key, obj in list(self.obj_map.items()):
                    if obj.graphics_item == item:
                        del self.obj_map[obj_key]
                        break
                self.scene().removeItem(item)
                self.update_list()
                self.update_selected_properties()

    def _trim_line_at_intersections(self, item, line_obj, intersections, click_pos):
        """
        Trim a line object at intersection points, removing the segment containing click_pos.

        Args:
            item: Graphics item to trim
            line_obj: LineObject model
            intersections: List of (QPointF, other_item) tuples
            click_pos: Click position to determine which segment to remove
        """
        from PyQt5.QtCore import QLineF

        # Sort intersection points by distance from line start
        line_start = QPointF(line_obj.x1, line_obj.y1)
        line_end = QPointF(line_obj.x2, line_obj.y2)
        line_vec = line_end - line_start
        line_length = line_obj.length

        # Get unique intersection points sorted along the line
        t_values = []
        for pt, _ in intersections:
            # Calculate parameter t (0..1) along the line
            if line_length > 0:
                t = QPointF.dotProduct(pt - line_start, line_vec) / (line_length * line_length)
                if 0 < t < 1:  # Only interior intersections
                    t_values.append((t, pt))

        if not t_values:
            return

        # Sort by t value
        t_values.sort(key=lambda x: x[0])

        # Find which segment contains the click point
        # Segments are: [0, t1], [t1, t2], ..., [tn, 1]
        click_t = None
        if line_length > 0:
            click_vec = click_pos - line_start
            click_t = QPointF.dotProduct(click_vec, line_vec) / (line_length * line_length)

        # Determine segment to remove
        remove_start_t = 0.0
        remove_end_t = 1.0

        if click_t is not None:
            # Find the segment containing click_t
            prev_t = 0.0
            for t, pt in t_values:
                if prev_t <= click_t <= t:
                    # Click is in segment [prev_t, t]
                    remove_start_t = prev_t
                    remove_end_t = t
                    break
                prev_t = t
            else:
                # Click is in last segment [last_t, 1]
                remove_start_t = t_values[-1][0]
                remove_end_t = 1.0

        # Calculate new endpoints (keep the parts outside the removed segment)
        # We need to keep [0, remove_start_t] and [remove_end_t, 1]
        # For simplicity, we'll keep the longer segment

        seg1_length = remove_start_t * line_length
        seg2_length = (1.0 - remove_end_t) * line_length

        if seg1_length >= seg2_length:
            # Keep first segment
            new_x2 = line_obj.x1 + remove_start_t * (line_obj.x2 - line_obj.x1)
            new_y2 = line_obj.y1 + remove_start_t * (line_obj.y2 - line_obj.y1)
        else:
            # Keep second segment
            new_x1 = line_obj.x1 + remove_end_t * (line_obj.x2 - line_obj.x1)
            new_y1 = line_obj.y1 + remove_end_t * (line_obj.y2 - line_obj.y1)
            new_x2 = line_obj.x2
            new_y2 = line_obj.y2

        # Update the graphics item
        if seg1_length >= seg2_length:
            new_line = QLineF(line_obj.x1, line_obj.y1, new_x2, new_y2)
        else:
            new_line = QLineF(new_x1, new_y1, line_obj.x2, line_obj.y2)

        item.setLine(new_line)

        # Update the model
        if seg1_length >= seg2_length:
            line_obj.x2 = new_x2
            line_obj.y2 = new_y2
        else:
            line_obj.x1 = new_x1
            line_obj.y1 = new_y1

        self.update_list()
        self.update_selected_properties()

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
        # Auto-fit view to show all content
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
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
        # Auto-fit view to show all content
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
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