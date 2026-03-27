--- drawing_editor/ui/cad_view.py (原始)
"""
Custom QGraphicsView for CAD drawing operations.

This module provides the CadView class which handles user interaction,
tool management, and drawing operations in the CAD scene.
"""

import math
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QMenu,
    QAction,
    QLabel,
    QInputDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import (
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainter,
    QTransform,
)

from drawing_editor.managers.snap_manager import SnapManager


class CadView(QGraphicsView):
    """
    Custom graphics view for CAD operations.

    Handles mouse interactions, tool switching, snapping, and temporary
    drawing previews.
    """

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # Tool state
        self.tool: str = "Select"
        self.start_point: Optional[QPointF] = None
        self.temp_item: Optional[QGraphicsItem] = None

        # Managers and references
        self.snap_manager: Optional[SnapManager] = None
        self.dim_type: str = "Linear"
        self.parent_window: Optional[Any] = parent

        # UI helpers
        self.tooltip_item: Optional[QGraphicsSimpleTextItem] = None
        self.hovered_item: Optional[QGraphicsItem] = None
        self.original_pen: Optional[QPen] = None
        self.original_color: Optional[QColor] = None
        self.hint_item: Optional[QGraphicsSimpleTextItem] = None

        # Cursor and scrolling
        self.setCursor(Qt.ArrowCursor)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def wheelEvent(self, event: Any) -> None:
        """Handle mouse wheel for zooming."""
        factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)

    def keyPressEvent(self, event: Any) -> None:
        """Handle keyboard shortcuts."""
        try:
            if event.key() == Qt.Key_Escape:
                if self.parent_window:
                    self.parent_window.set_tool("Select")
                if self.temp_item:
                    self.scene().removeItem(self.temp_item)
                    self.temp_item = None
                self.start_point = None
            elif event.key() == Qt.Key_Delete:
                if self.parent_window:
                    self.parent_window.delete_selected()
            elif event.key() in (Qt.Key_L, Qt.Key_l):
                if self.parent_window:
                    self.parent_window.set_tool("Line")
            elif event.key() in (Qt.Key_C, Qt.Key_c):
                if self.parent_window:
                    self.parent_window.set_tool("Circle")
            else:
                # Ignore unsupported key combinations to prevent crashes
                event.ignore()
                return
        except Exception:
            # Silently handle any unexpected errors to prevent application crash
            pass

    def setScene(self, scene: QGraphicsScene) -> None:
        """Set the scene and initialize snap manager."""
        super().setScene(scene)
        if self.snap_manager is None:
            self.snap_manager = SnapManager(scene)
        else:
            self.snap_manager.scene = scene

    def set_tool(self, tool: str) -> None:
        """Switch to a different drawing tool."""
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

        self.setCursor(Qt.ArrowCursor if tool == "Select" else Qt.CrossCursor)

    def set_dim_type(self, dim_type: str) -> None:
        """Set the dimension type for dimension tools."""
        self.dim_type = dim_type

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press events for drawing."""
        if self.tool == "Select":
            super().mousePressEvent(event)
            return
        if self.tool == "Trim":
            # Обработка Trim при клике левой кнопкой мыши
            if event.button() == Qt.LeftButton and self.parent_window:
                pos = self.mapToScene(event.pos())
                item = self.scene().itemAt(pos, QTransform())
                if item and hasattr(item, 'line') and self.parent_window:
                    self.parent_window.trim_object(item)
            return

        pos = self.mapToScene(event.pos())
        if self.snap_manager:
            pos = self.snap_manager.snap_point(self, event.pos())

        if event.button() == Qt.LeftButton:
            if self.start_point is None:
                self.start_point = pos
                self._create_temp_item(pos)
            else:
                self.finish_drawing(pos)
        elif event.button() == Qt.RightButton:
            self._cancel_drawing()
        else:
            super().mousePressEvent(event)

    def _create_temp_item(self, pos: QPointF) -> None:
        """Create a temporary preview item for drawing."""
        if self.tool == "Line":
            self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool == "Circle":
            self.temp_item = QGraphicsEllipseItem()
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool == "Rect":
            self.temp_item = QGraphicsRectItem()
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
            self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))

        if self.temp_item:
            self.scene().addItem(self.temp_item)

    def _cancel_drawing(self) -> None:
        """Cancel the current drawing operation."""
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
        self.start_point = None

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse move for tooltips and previews."""
        self._update_tooltip(event)
        self._update_highlight(event)
        self._update_snap_hint(event)
        self._update_temp_item(event)

    def _update_tooltip(self, event: Any) -> None:
        """Update the tool tooltip."""
        if self.tool != "Select":
            if self.tooltip_item is None:
                self.tooltip_item = QGraphicsSimpleTextItem()
                self.tooltip_item.setBrush(QBrush(QColor(0, 0, 0)))
                self.tooltip_item.setFont(QFont("Arial", 8))
                self.scene().addItem(self.tooltip_item)
            self.tooltip_item.setText(self.tool)
            scene_pos = self.mapToScene(event.pos())
            self.tooltip_item.setPos(scene_pos.x() + 5, scene_pos.y() - 10)
        else:
            if self.tooltip_item:
                self.scene().removeItem(self.tooltip_item)
                self.tooltip_item = None

    def _update_highlight(self, event: Any) -> None:
        """Highlight items under cursor in select mode."""
        if self.tool == "Select":
            pos = self.mapToScene(event.pos())
            item = self.scene().itemAt(pos, QTransform())
            if item != self.hovered_item:
                self._clear_highlight()
                self.hovered_item = item
                if item and item.flags() & QGraphicsItem.ItemIsSelectable:
                    self._highlight_item(item)
        else:
            self._clear_highlight()

    def _update_snap_hint(self, event: Any) -> None:
        """Update snap point hint."""
        if self.snap_manager and self.tool != "Select":
            point, hint = self.snap_manager.get_snap_info(self, event.pos())
            if point and hint:
                if self.hint_item is None:
                    self.hint_item = QGraphicsSimpleTextItem()
                    self.hint_item.setBrush(QBrush(QColor(0, 0, 0)))
                    self.hint_item.setFont(QFont("Arial", 8))
                    self.scene().addItem(self.hint_item)
                self.hint_item.setText(hint)
                # Position hint to the right of the tooltip (which shows primitive name)
                scene_pos = self.mapToScene(event.pos())
                tooltip_offset = len(self.tool) * 6  # Approximate width of tooltip text
                self.hint_item.setPos(scene_pos.x() + 5 + tooltip_offset, scene_pos.y() - 10)
                self.hint_item.show()
            else:
                if self.hint_item:
                    self.hint_item.hide()
        else:
            if self.hint_item:
                self.hint_item.hide()

    def _update_temp_item(self, event: Any) -> None:
        """Update temporary drawing preview."""
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
                rect = QRectF(
                    self.start_point.x() - r,
                    self.start_point.y() - r,
                    2 * r,
                    2 * r
                )
                self.temp_item.setRect(rect)
            elif self.tool == "Rect":
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = pos.x(), pos.y()
                rect = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                self.temp_item.setRect(rect)
            elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
                self.temp_item.setLine(QLineF(self.start_point, pos))
        else:
            super().mouseMoveEvent(event)

    def contextMenuEvent(self, event: Any) -> None:
        """Show context menu for snap settings."""
        if self.tool == "Select":
            super().contextMenuEvent(event)
            return
        if not self.snap_manager:
            return

        menu = QMenu(self)

        snap_end_action = QAction("Snap to endpoints", self)
        snap_end_action.setCheckable(True)
        snap_end_action.setChecked(self.snap_manager.snap_to_endpoints)
        snap_end_action.triggered.connect(
            lambda checked: self.set_snap_endpoints(checked)
        )
        menu.addAction(snap_end_action)

        snap_center_action = QAction("Snap to centers", self)
        snap_center_action.setCheckable(True)
        snap_center_action.setChecked(self.snap_manager.snap_to_center)
        snap_center_action.triggered.connect(
            lambda checked: self.set_snap_center(checked)
        )
        menu.addAction(snap_center_action)

        menu.exec_(event.globalPos())

    def set_snap_endpoints(self, enabled: bool) -> None:
        """Toggle endpoint snapping."""
        self.snap_manager.snap_to_endpoints = enabled
        if self.parent_window:
            self.parent_window.update_snap_settings(
                enabled,
                self.snap_manager.snap_to_center
            )

    def set_snap_center(self, enabled: bool) -> None:
        """Toggle center snapping."""
        self.snap_manager.snap_to_center = enabled
        if self.parent_window:
            self.parent_window.update_snap_settings(
                self.snap_manager.snap_to_endpoints,
                enabled
            )

    def _highlight_item(self, item: QGraphicsItem) -> None:
        """Apply highlight to an item."""
        if hasattr(item, 'pen'):
            self.original_pen = item.pen()
            new_pen = QPen(QColor(255, 0, 0), self.original_pen.widthF() + 0.2)
            new_pen.setStyle(self.original_pen.style())
            item.setPen(new_pen)
        elif isinstance(item, QGraphicsTextItem):
            self.original_color = item.defaultTextColor()
            item.setDefaultTextColor(QColor(255, 0, 0))

    def _clear_highlight(self) -> None:
        """Remove highlight from previously hovered item."""
        if self.hovered_item:
            if hasattr(self.hovered_item, 'pen') and self.original_pen is not None:
                self.hovered_item.setPen(self.original_pen)
            elif (isinstance(self.hovered_item, QGraphicsTextItem) and
                  self.original_color is not None):
                self.hovered_item.setDefaultTextColor(self.original_color)
            self.hovered_item = None
            self.original_pen = None
            self.original_color = None

    def finish_drawing(self, pos: QPointF) -> None:
        """Complete the drawing operation and create the object."""
        if not self.parent_window:
            self._cancel_drawing()
            return

        if self.tool == "Line":
            self.parent_window.add_line(
                self.start_point.x(),
                self.start_point.y(),
                pos.x(),
                pos.y()
            )
        elif self.tool == "Circle":
            r = math.hypot(
                pos.x() - self.start_point.x(),
                pos.y() - self.start_point.y()
            )
            self.parent_window.add_circle(self.start_point.x(), self.start_point.y(), r)
        elif self.tool == "Rect":
            self.parent_window.add_rectangle(
                self.start_point.x(),
                self.start_point.y(),
                pos.x(),
                pos.y()
            )
        elif self.tool == "Arc":
            self._show_arc_dialog()
        elif self.tool == "Text":
            self._show_text_dialog()
        elif self.tool == "Dim":
            self.parent_window.add_dimension(self.start_point, pos, "Linear")
        elif self.tool == "RadiusDim":
            self._show_radius_dialog()
        elif self.tool == "DiameterDim":
            self._show_diameter_dialog()
        elif self.tool == "AngularDim":
            self._show_angular_dialog()

        self._cancel_drawing()

    def _show_arc_dialog(self) -> None:
        """Show dialog for arc parameters."""
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
            self.parent_window.add_arc(
                self.start_point.x(),
                self.start_point.y(),
                r,
                sa,
                ea
            )

    def _show_text_dialog(self) -> None:
        """Show dialog for text input."""
        text, ok = QInputDialog.getText(self.parent_window, "Text", "Enter text:")
        if ok and text:
            self.parent_window.add_text(self.start_point.x(), self.start_point.y(), text)

    def _show_radius_dialog(self) -> None:
        """Show dialog for radius dimension."""
        radius, ok = QInputDialog.getDouble(
            self.parent_window, "Radius", "Enter radius:"
        )
        if ok:
            self.parent_window.add_radius_dim(self.start_point, radius)

    def _show_diameter_dialog(self) -> None:
        """Show dialog for diameter dimension."""
        diam, ok = QInputDialog.getDouble(
            self.parent_window, "Diameter", "Enter diameter:"
        )
        if ok:
            self.parent_window.add_diameter_dim(self.start_point, diam)

    def _show_angular_dialog(self) -> None:
        """Show dialog for angular dimension."""
        angle, ok = QInputDialog.getDouble(
            self.parent_window, "Angle", "Enter angle (degrees):"
        )
        if ok:
            self.parent_window.add_angular_dim(self.start_point, angle)

+++ drawing_editor/ui/cad_view.py (修改后)
"""
Custom QGraphicsView for CAD drawing operations.

This module provides the CadView class which handles user interaction,
tool management, and drawing operations in the CAD scene.
"""

import math
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QMenu,
    QAction,
    QLabel,
    QInputDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import (
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainter,
    QTransform,
)

from drawing_editor.managers.snap_manager import SnapManager


class CadView(QGraphicsView):
    """
    Custom graphics view for CAD operations.

    Handles mouse interactions, tool switching, snapping, and temporary
    drawing previews.
    """

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # Tool state
        self.tool: str = "Select"
        self.start_point: Optional[QPointF] = None
        self.temp_item: Optional[QGraphicsItem] = None

        # Managers and references
        self.snap_manager: Optional[SnapManager] = None
        self.dim_type: str = "Linear"
        self.parent_window: Optional[Any] = parent

        # UI helpers
        self.tooltip_item: Optional[QGraphicsSimpleTextItem] = None
        self.hovered_item: Optional[QGraphicsItem] = None
        self.original_pen: Optional[QPen] = None
        self.original_color: Optional[QColor] = None
        self.hint_item: Optional[QGraphicsSimpleTextItem] = None

        # Cursor and scrolling
        self.setCursor(Qt.ArrowCursor)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def wheelEvent(self, event: Any) -> None:
        """Handle mouse wheel for zooming."""
        factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)

    def keyPressEvent(self, event: Any) -> None:
        """Handle keyboard shortcuts."""
        try:
            if event.key() == Qt.Key_Escape:
                if self.parent_window:
                    self.parent_window.set_tool("Select")
                if self.temp_item:
                    self.scene().removeItem(self.temp_item)
                    self.temp_item = None
                self.start_point = None
            elif event.key() == Qt.Key_Delete:
                if self.parent_window:
                    self.parent_window.delete_selected()
            elif event.key() in (Qt.Key_L, Qt.Key_l):
                if self.parent_window:
                    self.parent_window.set_tool("Line")
            elif event.key() in (Qt.Key_C, Qt.Key_c):
                if self.parent_window:
                    self.parent_window.set_tool("Circle")
            else:
                # Ignore unsupported key combinations to prevent crashes
                event.ignore()
                return
        except Exception:
            # Silently handle any unexpected errors to prevent application crash
            pass

    def setScene(self, scene: QGraphicsScene) -> None:
        """Set the scene and initialize snap manager."""
        super().setScene(scene)
        if self.snap_manager is None:
            self.snap_manager = SnapManager(scene)
        else:
            self.snap_manager.scene = scene

    def set_tool(self, tool: str) -> None:
        """Switch to a different drawing tool."""
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

        self.setCursor(Qt.ArrowCursor if tool == "Select" else Qt.CrossCursor)

    def set_dim_type(self, dim_type: str) -> None:
        """Set the dimension type for dimension tools."""
        self.dim_type = dim_type

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press events for drawing."""
        if self.tool == "Select":
            super().mousePressEvent(event)
            return
        if self.tool == "Trim":
            # Trim command: click on object to trim at intersection point
            if event.button() == Qt.LeftButton and self.parent_window:
                pos = self.mapToScene(event.pos())
                item = self.scene().itemAt(pos, QTransform())
                if item and self.parent_window:
                    # Pass click position for segment determination
                    self.parent_window.trim_object(item, click_pos=pos)
            return

        pos = self.mapToScene(event.pos())
        if self.snap_manager:
            pos = self.snap_manager.snap_point(self, event.pos())

        if event.button() == Qt.LeftButton:
            if self.start_point is None:
                self.start_point = pos
                self._create_temp_item(pos)
            else:
                self.finish_drawing(pos)
        elif event.button() == Qt.RightButton:
            self._cancel_drawing()
        else:
            super().mousePressEvent(event)

    def _create_temp_item(self, pos: QPointF) -> None:
        """Create a temporary preview item for drawing."""
        if self.tool == "Line":
            self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool == "Circle":
            self.temp_item = QGraphicsEllipseItem()
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool == "Rect":
            self.temp_item = QGraphicsRectItem()
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))
        elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
            self.temp_item = QGraphicsLineItem(QLineF(pos, pos))
            self.temp_item.setPen(QPen(QColor(0, 0, 255), 0.2, Qt.DashLine))

        if self.temp_item:
            self.scene().addItem(self.temp_item)

    def _cancel_drawing(self) -> None:
        """Cancel the current drawing operation."""
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None
        self.start_point = None

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse move for tooltips and previews."""
        self._update_tooltip(event)
        self._update_highlight(event)
        self._update_snap_hint(event)
        self._update_temp_item(event)

    def _update_tooltip(self, event: Any) -> None:
        """Update the tool tooltip."""
        if self.tool != "Select":
            if self.tooltip_item is None:
                self.tooltip_item = QGraphicsSimpleTextItem()
                self.tooltip_item.setBrush(QBrush(QColor(0, 0, 0)))
                self.tooltip_item.setFont(QFont("Arial", 8))
                self.scene().addItem(self.tooltip_item)
            self.tooltip_item.setText(self.tool)
            scene_pos = self.mapToScene(event.pos())
            self.tooltip_item.setPos(scene_pos.x() + 5, scene_pos.y() - 10)
        else:
            if self.tooltip_item:
                self.scene().removeItem(self.tooltip_item)
                self.tooltip_item = None

    def _update_highlight(self, event: Any) -> None:
        """Highlight items under cursor in select mode."""
        if self.tool == "Select":
            pos = self.mapToScene(event.pos())
            item = self.scene().itemAt(pos, QTransform())
            if item != self.hovered_item:
                self._clear_highlight()
                self.hovered_item = item
                if item and item.flags() & QGraphicsItem.ItemIsSelectable:
                    self._highlight_item(item)
        else:
            self._clear_highlight()

    def _update_snap_hint(self, event: Any) -> None:
        """Update snap point hint."""
        if self.snap_manager and self.tool != "Select":
            point, hint = self.snap_manager.get_snap_info(self, event.pos())
            if point and hint:
                if self.hint_item is None:
                    self.hint_item = QGraphicsSimpleTextItem()
                    self.hint_item.setBrush(QBrush(QColor(0, 0, 0)))
                    self.hint_item.setFont(QFont("Arial", 8))
                    self.scene().addItem(self.hint_item)
                self.hint_item.setText(hint)
                # Position hint to the right of the tooltip (which shows primitive name)
                scene_pos = self.mapToScene(event.pos())
                tooltip_offset = len(self.tool) * 6  # Approximate width of tooltip text
                self.hint_item.setPos(scene_pos.x() + 5 + tooltip_offset, scene_pos.y() - 10)
                self.hint_item.show()
            else:
                if self.hint_item:
                    self.hint_item.hide()
        else:
            if self.hint_item:
                self.hint_item.hide()

    def _update_temp_item(self, event: Any) -> None:
        """Update temporary drawing preview."""
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
                rect = QRectF(
                    self.start_point.x() - r,
                    self.start_point.y() - r,
                    2 * r,
                    2 * r
                )
                self.temp_item.setRect(rect)
            elif self.tool == "Rect":
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = pos.x(), pos.y()
                rect = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                self.temp_item.setRect(rect)
            elif self.tool in ("Dim", "RadiusDim", "DiameterDim", "AngularDim"):
                self.temp_item.setLine(QLineF(self.start_point, pos))
        else:
            super().mouseMoveEvent(event)

    def contextMenuEvent(self, event: Any) -> None:
        """Show context menu for snap settings."""
        if self.tool == "Select":
            super().contextMenuEvent(event)
            return
        if not self.snap_manager:
            return

        menu = QMenu(self)

        snap_end_action = QAction("Snap to endpoints", self)
        snap_end_action.setCheckable(True)
        snap_end_action.setChecked(self.snap_manager.snap_to_endpoints)
        snap_end_action.triggered.connect(
            lambda checked: self.set_snap_endpoints(checked)
        )
        menu.addAction(snap_end_action)

        snap_center_action = QAction("Snap to centers", self)
        snap_center_action.setCheckable(True)
        snap_center_action.setChecked(self.snap_manager.snap_to_center)
        snap_center_action.triggered.connect(
            lambda checked: self.set_snap_center(checked)
        )
        menu.addAction(snap_center_action)

        menu.exec_(event.globalPos())

    def set_snap_endpoints(self, enabled: bool) -> None:
        """Toggle endpoint snapping."""
        self.snap_manager.snap_to_endpoints = enabled
        if self.parent_window:
            self.parent_window.update_snap_settings(
                enabled,
                self.snap_manager.snap_to_center
            )

    def set_snap_center(self, enabled: bool) -> None:
        """Toggle center snapping."""
        self.snap_manager.snap_to_center = enabled
        if self.parent_window:
            self.parent_window.update_snap_settings(
                self.snap_manager.snap_to_endpoints,
                enabled
            )

    def _highlight_item(self, item: QGraphicsItem) -> None:
        """Apply highlight to an item."""
        if hasattr(item, 'pen'):
            self.original_pen = item.pen()
            new_pen = QPen(QColor(255, 0, 0), self.original_pen.widthF() + 0.2)
            new_pen.setStyle(self.original_pen.style())
            item.setPen(new_pen)
        elif isinstance(item, QGraphicsTextItem):
            self.original_color = item.defaultTextColor()
            item.setDefaultTextColor(QColor(255, 0, 0))

    def _clear_highlight(self) -> None:
        """Remove highlight from previously hovered item."""
        if self.hovered_item:
            if hasattr(self.hovered_item, 'pen') and self.original_pen is not None:
                self.hovered_item.setPen(self.original_pen)
            elif (isinstance(self.hovered_item, QGraphicsTextItem) and
                  self.original_color is not None):
                self.hovered_item.setDefaultTextColor(self.original_color)
            self.hovered_item = None
            self.original_pen = None
            self.original_color = None

    def finish_drawing(self, pos: QPointF) -> None:
        """Complete the drawing operation and create the object."""
        if not self.parent_window:
            self._cancel_drawing()
            return

        if self.tool == "Line":
            self.parent_window.add_line(
                self.start_point.x(),
                self.start_point.y(),
                pos.x(),
                pos.y()
            )
        elif self.tool == "Circle":
            r = math.hypot(
                pos.x() - self.start_point.x(),
                pos.y() - self.start_point.y()
            )
            self.parent_window.add_circle(self.start_point.x(), self.start_point.y(), r)
        elif self.tool == "Rect":
            self.parent_window.add_rectangle(
                self.start_point.x(),
                self.start_point.y(),
                pos.x(),
                pos.y()
            )
        elif self.tool == "Arc":
            self._show_arc_dialog()
        elif self.tool == "Text":
            self._show_text_dialog()
        elif self.tool == "Dim":
            self.parent_window.add_dimension(self.start_point, pos, "Linear")
        elif self.tool == "RadiusDim":
            self._show_radius_dialog()
        elif self.tool == "DiameterDim":
            self._show_diameter_dialog()
        elif self.tool == "AngularDim":
            self._show_angular_dialog()

        self._cancel_drawing()

    def _show_arc_dialog(self) -> None:
        """Show dialog for arc parameters."""
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
            self.parent_window.add_arc(
                self.start_point.x(),
                self.start_point.y(),
                r,
                sa,
                ea
            )

    def _show_text_dialog(self) -> None:
        """Show dialog for text input."""
        text, ok = QInputDialog.getText(self.parent_window, "Text", "Enter text:")
        if ok and text:
            self.parent_window.add_text(self.start_point.x(), self.start_point.y(), text)

    def _show_radius_dialog(self) -> None:
        """Show dialog for radius dimension."""
        radius, ok = QInputDialog.getDouble(
            self.parent_window, "Radius", "Enter radius:"
        )
        if ok:
            self.parent_window.add_radius_dim(self.start_point, radius)

    def _show_diameter_dialog(self) -> None:
        """Show dialog for diameter dimension."""
        diam, ok = QInputDialog.getDouble(
            self.parent_window, "Diameter", "Enter diameter:"
        )
        if ok:
            self.parent_window.add_diameter_dim(self.start_point, diam)

    def _show_angular_dialog(self) -> None:
        """Show dialog for angular dimension."""
        angle, ok = QInputDialog.getDouble(
            self.parent_window, "Angle", "Enter angle (degrees):"
        )
        if ok:
            self.parent_window.add_angular_dim(self.start_point, angle)