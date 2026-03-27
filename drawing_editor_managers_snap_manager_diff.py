--- drawing_editor/managers/snap_manager.py (原始)
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

+++ drawing_editor/managers/snap_manager.py (修改后)
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

    Provides snapping to endpoints, centers, vertices, quadrants, and intersection points.
    """

    def __init__(self, scene: Optional[QGraphicsScene] = None) -> None:
        self.scene: Optional[QGraphicsScene] = scene
        self.snap_distance: int = 40
        self.snap_to_endpoints: bool = True
        self.snap_to_center: bool = True
        self.snap_to_quadrants: bool = True  # Quadrant snapping (N, S, E, W on circles)
        self.snap_to_intersections: bool = True  # Intersection points between objects

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

        # Collect all items for intersection calculation
        items = list(self.scene.items())

        for item in items:
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

            # Quadrant snapping for circles (N, S, E, W)
            if self.snap_to_quadrants and isinstance(item, GraphicsCircle):
                circle = item.circle_obj
                quadrants = [
                    (QPointF(circle.cx, circle.cy - circle.radius), "Quad N"),
                    (QPointF(circle.cx, circle.cy + circle.radius), "Quad S"),
                    (QPointF(circle.cx + circle.radius, circle.cy), "Quad E"),
                    (QPointF(circle.cx - circle.radius, circle.cy), "Quad W"),
                ]
                for p, hint in quadrants:
                    pixel_pos = view.mapFromScene(p)
                    dist = (screen_pos - pixel_pos).manhattanLength()
                    if dist < best_dist:
                        best_dist = dist
                        best_point = p
                        best_hint = hint

        # Intersection snapping - check intersections between all pairs of objects
        if self.snap_to_intersections:
            for i, item_a in enumerate(items):
                for item_b in items[i+1:]:
                    intersections = self._find_item_intersections(item_a, item_b)
                    for pt, hint in intersections:
                        pixel_pos = view.mapFromScene(pt)
                        dist = (screen_pos - pixel_pos).manhattanLength()
                        if dist < best_dist:
                            best_dist = dist
                            best_point = pt
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

    def _find_item_intersections(self, item_a, item_b):
        """
        Find intersection points between two graphics items.

        Args:
            item_a: First graphics item
            item_b: Second graphics item

        Returns:
            List of tuples (QPointF, hint_string) for each intersection
        """
        from PyQt5.QtCore import QLineF
        import math

        intersections = []

        # Get line segments from items
        lines_a = self._get_lines_from_item(item_a)
        lines_b = self._get_lines_from_item(item_b)

        # Check all line segment pairs
        for line_a in lines_a:
            for line_b in lines_b:
                intersect_type = line_a.intersect(line_b)
                if intersect_type[0] == QLineF.BoundedIntersection:
                    pt = intersect_type[1]
                    intersections.append((pt, "Intersect"))

        return intersections

    def _get_lines_from_item(self, item):
        """
        Extract line segments from a graphics item.

        Args:
            item: Graphics item (Line, Rect, Circle approximated)

        Returns:
            List of QLineF objects representing the item's edges
        """
        from PyQt5.QtCore import QLineF

        lines = []

        if isinstance(item, GraphicsLine):
            lines.append(item.line())

        elif isinstance(item, GraphicsRect):
            rect = item.rect()
            tl = rect.topLeft()
            tr = rect.topRight()
            br = rect.bottomRight()
            bl = rect.bottomLeft()
            lines = [
                QLineF(tl, tr),  # Top
                QLineF(tr, br),  # Right
                QLineF(br, bl),  # Bottom
                QLineF(bl, tl),  # Left
            ]

        elif isinstance(item, GraphicsCircle):
            # Approximate circle with 8 line segments for intersection detection
            circle = item.circle_obj
            cx, cy, r = circle.cx, circle.cy, circle.radius
            num_segments = 16
            for i in range(num_segments):
                angle1 = 2 * math.pi * i / num_segments
                angle2 = 2 * math.pi * (i + 1) / num_segments
                x1 = cx + r * math.cos(angle1)
                y1 = cy + r * math.sin(angle1)
                x2 = cx + r * math.cos(angle2)
                y2 = cy + r * math.sin(angle2)
                lines.append(QLineF(x1, y1, x2, y2))

        return lines