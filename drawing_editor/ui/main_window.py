"""
Main window for the CAD drawing editor.

This module provides the CadWindow class which serves as the primary
application window containing all UI elements and coordinating user actions.
"""

from typing import Optional, Dict, Any
import sys

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
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainter, QTransform
from PyQt5.QtPrintSupport import QPrinter
import ezdxf
from ezdxf.math import Vec3

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

        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addAction(save_as_action)
        toolbar.addAction(export_pdf_action)
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
                    self.prop_linetype.setText(["Solid", "Dash", "DashDot"][pen.style()])
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
    """Экспорт текущей сцены в PDF с масштабированием."""
    if not self.scene.items():
        QMessageBox.warning(self, "Warning", "Nothing to export.")
        return
    fname, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
    if not fname:
        return

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

    page_rect = printer.pageRect()
    scale_x = page_rect.width() / bbox.width()
    scale_y = page_rect.height() / bbox.height()
    scale = min(scale_x, scale_y) * 0.9

    painter.translate(page_rect.center())
    painter.scale(scale, scale)
    painter.translate(-bbox.center())

    self.scene.render(painter)
    painter.end()

    QMessageBox.information(self, "Exported", f"PDF saved to {fname}")

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
