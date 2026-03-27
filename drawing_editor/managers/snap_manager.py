"""
Object snapping manager for precision drawing.

This module provides the SnapManager class which handles snapping to
geometric features like endpoints, centers, and vertices.
"""

from typing import Optional, Tuple

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

from drawing_editor.ui.graphics_items import (
    GraphicsLine,
    GraphicsRect,
    GraphicsPoint,
    GraphicsCircle,
)


class SnapManager:
    """
    Manages object snapping behavior for CAD view.
    
    Provides snapping to endpoints, centers, and vertices with visual hints.
    """
    
    def __init__(self, scene: Optional[QGraphicsScene] = None) -> None:
        self.scene: Optional[QGraphicsScene] = scene
        self.snap_distance: int = 40
        self.snap_to_endpoints: bool = True
        self.snap_to_center: bool = True

    def get_snap_info(
        self, 
        view: QGraphicsView, 
        screen_pos: QPointF
    ) -> Tuple[Optional[QPointF], Optional[str]]:
        """
        Find the nearest snap point and return it with a hint.
        
        Args:
            view: The graphics view for coordinate mapping
            screen_pos: Mouse position in screen coordinates
            
        Returns:
            Tuple of (snap_point, hint_string) or (None, None) if no snap found
        """
        if not self.scene:
            return None, None
        
        best_dist = self.snap_distance
        best_point: Optional[QPointF] = None
        best_hint: Optional[str] = None
        
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
                            best_hint = "End"
                            
                elif isinstance(item, GraphicsRect):
                    rect = item.rect()
                    for p in [rect.topLeft(), rect.topRight(), 
                              rect.bottomLeft(), rect.bottomRight()]:
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
            
            if self.snap_to_center and isinstance(item, GraphicsCircle):
                p = QPointF(item.circle_obj.cx, item.circle_obj.cy)
                pixel_pos = view.mapFromScene(p)
                dist = (screen_pos - pixel_pos).manhattanLength()
                if dist < best_dist:
                    best_dist = dist
                    best_point = p
                    best_hint = "Center"
        
        return best_point, best_hint

    def snap_point(
        self, 
        view: QGraphicsView, 
        screen_pos: QPointF
    ) -> QPointF:
        """
        Snap a screen position to the nearest geometric feature.
        
        Args:
            view: The graphics view for coordinate mapping
            screen_pos: Mouse position in screen coordinates
            
        Returns:
            Snapped scene position, or original mapped position if no snap
        """
        point, _ = self.get_snap_info(view, screen_pos)
        return point if point else view.mapToScene(screen_pos)
