"""
Object snapping manager for precision drawing.

This module provides the SnapManager class which handles snapping to
geometric features like endpoints, centers, and vertices.
"""

from typing import Optional, Tuple, List, Any
from functools import lru_cache

from PyQt5.QtCore import QPointF, QRectF
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
    Uses spatial optimization to reduce unnecessary distance calculations.
    """
    
    __slots__ = ('scene', 'snap_distance', 'snap_to_endpoints', 'snap_to_center',
                 '_cached_points', '_cache_valid')
    
    def __init__(self, scene: Optional[QGraphicsScene] = None) -> None:
        self.scene: Optional[QGraphicsScene] = scene
        self.snap_distance: int = 40
        self.snap_to_endpoints: bool = True
        self.snap_to_center: bool = True
        self._cached_points: List[Tuple[QPointF, str]] = []
        self._cache_valid: bool = False

    def invalidate_cache(self) -> None:
        """Invalidate the snap point cache when scene changes."""
        self._cache_valid = False
        self._cached_points.clear()

    def add_item_snap_points(self, item: Any) -> None:
        """Incrementally add snap points for a new item (optimization)."""
        if not self.snap_to_endpoints and not self.snap_to_center:
            return
            
        if self.snap_to_endpoints:
            if isinstance(item, GraphicsLine):
                line = item.line()
                self._cached_points.append((line.p1(), "End"))
                self._cached_points.append((line.p2(), "End"))
                
            elif isinstance(item, GraphicsRect):
                rect = item.rect()
                self._cached_points.append((rect.topLeft(), "Vertex"))
                self._cached_points.append((rect.topRight(), "Vertex"))
                self._cached_points.append((rect.bottomLeft(), "Vertex"))
                self._cached_points.append((rect.bottomRight(), "Vertex"))
                
            elif isinstance(item, GraphicsPoint):
                self._cached_points.append((item.pos(), "Point"))
        
        if self.snap_to_center and isinstance(item, GraphicsCircle):
            p = QPointF(item.circle_obj.cx, item.circle_obj.cy)
            self._cached_points.append((p, "Center"))

    def remove_item_snap_points(self, item: Any) -> None:
        """Incrementally remove snap points for a removed item (optimization)."""
        if not self._cached_points:
            return
        
        # Filter out points belonging to this item
        if isinstance(item, GraphicsLine):
            line = item.line()
            line_points = {line.p1(), line.p2()}
            self._cached_points = [(p, h) for p, h in self._cached_points 
                                   if p not in line_points]
        elif isinstance(item, GraphicsRect):
            rect = item.rect()
            rect_points = {rect.topLeft(), rect.topRight(), 
                          rect.bottomLeft(), rect.bottomRight()}
            self._cached_points = [(p, h) for p, h in self._cached_points 
                                   if p not in rect_points]
        elif isinstance(item, GraphicsPoint):
            point_pos = item.pos()
            self._cached_points = [(p, h) for p, h in self._cached_points 
                                   if p != point_pos]
        elif isinstance(item, GraphicsCircle):
            circle_center = QPointF(item.circle_obj.cx, item.circle_obj.cy)
            self._cached_points = [(p, h) for p, h in self._cached_points 
                                   if p != circle_center]

    def _build_snap_cache(self) -> None:
        """Pre-compute all snap points for efficient lookup."""
        if not self.scene:
            return
        
        self._cached_points.clear()
        
        for item in self.scene.items():
            self.add_item_snap_points(item)
        
        self._cache_valid = True

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
        
        # Build cache if needed
        if not self._cache_valid:
            self._build_snap_cache()
        
        if not self._cached_points:
            return None, None
        
        best_dist = self.snap_distance
        best_point: Optional[QPointF] = None
        best_hint: Optional[str] = None
        
        # Optimized: single pass through pre-computed points
        mapFromScene = view.mapFromScene
        manhattanLength = QPointF.manhattanLength
        
        for point, hint in self._cached_points:
            pixel_pos = mapFromScene(point)
            dist = manhattanLength(screen_pos - pixel_pos)
            if dist < best_dist:
                best_dist = dist
                best_point = point
                best_hint = hint
        
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
