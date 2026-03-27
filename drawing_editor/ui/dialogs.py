"""
Dialog windows for property editing and user input.

This module provides dialog classes for editing object properties
and other user interactions.
"""

from typing import Optional, Any

from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QComboBox,
    QColorDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from drawing_editor.core.models import GraphicObject


class PropertyDialog(QDialog):
    """
    Dialog for editing graphic object properties.
    
    Allows users to modify color, line width, and line type.
    """
    
    def __init__(self, obj: GraphicObject, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.obj = obj
        self.setWindowTitle("Object Properties")
        
        layout = QFormLayout(self)
        
        # Color button
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addRow("Color:", self.color_btn)
        
        # Line width
        pen_width = 0.2
        if hasattr(obj.graphics_item, 'pen'):
            pen_width = obj.graphics_item.pen().widthF()
        self.width_edit = QLineEdit(str(pen_width))
        layout.addRow("Line width:", self.width_edit)
        
        # Line type
        self.linetype_combo = QComboBox()
        self.linetype_combo.addItems(["Solid", "Dash", "DashDot"])
        layout.addRow("Line type:", self.linetype_combo)
        
        # Apply button
        btn = QPushButton("Apply")
        btn.clicked.connect(self.apply)
        layout.addRow(btn)

    def choose_color(self) -> None:
        """Open color picker dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.color_btn.color = color

    def apply(self) -> None:
        """Apply property changes to the object."""
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
            
            # Update DXF entity if present
            if self.obj.dxf_entity:
                self._update_dxf_entity(pen)
        
        self.accept()

    def _update_dxf_entity(self, pen: QPen) -> None:
        """Update the DXF entity with new properties."""
        color = pen.color()
        
        try:
            self.obj.dxf_entity.dxf.rgb = (color.red(), color.green(), color.blue())
        except AttributeError:
            # Fallback to indexed color
            r, g, b = color.red(), color.green(), color.blue()
            color_map = {
                (255, 0, 0): 1,
                (255, 255, 0): 2,
                (0, 255, 0): 3,
                (0, 255, 255): 4,
                (0, 0, 255): 5,
                (255, 0, 255): 6,
            }
            idx = color_map.get((r, g, b), 7)
            self.obj.dxf_entity.dxf.color = idx
        
        # Update linetype
        linetype_map = {
            Qt.DashLine: "DASHED",
            Qt.DashDotLine: "DASHDOT",
            Qt.SolidLine: "CONTINUOUS",
        }
        self.obj.dxf_entity.dxf.linetype = linetype_map.get(pen.style(), "CONTINUOUS")
