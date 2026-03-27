"""
Geometry Engine module for intersection calculations and snapping logic.
Implements simple intersection logic for Lines, Rectangles, and Circles.
"""
import math
from typing import List, Optional, Tuple, Any

from drawing_editor.core.models import (
    GraphicObject, LineObject, CircleObject, 
    RectObject, PointObject
)


class GeometryPoint:
    """Simple point structure for geometry calculations."""
    __slots__ = ('x', 'y')
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class IntersectionResult:
    """Represents a point of intersection between two shapes."""
    __slots__ = ('point', 'shape_a', 'shape_b')
    
    def __init__(self, point: GeometryPoint, shape_a: GraphicObject, shape_b: GraphicObject):
        self.point = point
        self.shape_a = shape_a
        self.shape_b = shape_b


class GeometryEngine:
    """
    Static utility class for geometric calculations.
    Handles intersections and snapping logic.
    """

    EPSILON = 1e-6  # Tolerance for floating point comparisons
    SNAP_THRESHOLD = 10.0  # Pixels threshold for snapping in UI coordinates

    @staticmethod
    def to_geometry_point(obj: Any) -> GeometryPoint:
        """Convert various point representations to GeometryPoint."""
        if isinstance(obj, GeometryPoint):
            return obj
        # Handle QPointF from Qt
        if hasattr(obj, 'x') and hasattr(obj, 'y'):
            return GeometryPoint(float(obj.x()), float(obj.y())) if callable(obj.x) else GeometryPoint(float(obj.x), float(obj.y))
        # Handle tuple
        if isinstance(obj, (tuple, list)) and len(obj) >= 2:
            return GeometryPoint(float(obj[0]), float(obj[1]))
        raise ValueError(f"Cannot convert {type(obj)} to GeometryPoint")

    @staticmethod
    def get_shape_bounds(shape: GraphicObject) -> Tuple[float, float, float, float]:
        """Returns (min_x, min_y, max_x, max_y) for a shape."""
        if isinstance(shape, RectObject):
            return (min(shape.x1, shape.x2), min(shape.y1, shape.y2),
                    max(shape.x1, shape.x2), max(shape.y1, shape.y2))
        elif isinstance(shape, CircleObject):
            return (shape.cx - shape.radius, shape.cy - shape.radius,
                    shape.cx + shape.radius, shape.cy + shape.radius)
        elif isinstance(shape, LineObject):
            return (min(shape.x1, shape.x2), min(shape.y1, shape.y2),
                    max(shape.x1, shape.x2), max(shape.y1, shape.y2))
        # Fallback for generic shapes
        return 0, 0, 0, 0

    @staticmethod
    def line_line_intersection(l1: LineObject, l2: LineObject) -> List[GeometryPoint]:
        """Calculates intersection points between two line segments."""
        x1, y1 = l1.x1, l1.y1
        x2, y2 = l1.x2, l1.y2
        x3, y3 = l2.x1, l2.y1
        x4, y4 = l2.x2, l2.y2

        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if abs(denom) < GeometryEngine.EPSILON:
            return []  # Parallel or collinear

        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

        if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return [GeometryPoint(x, y)]
        return []

    @staticmethod
    def line_circle_intersection(line: LineObject, circle: CircleObject) -> List[GeometryPoint]:
        """Calculates intersection points between a line segment and a circle."""
        dx = line.x2 - line.x1
        dy = line.y2 - line.y1
        
        fx = line.x1 - circle.cx
        fy = line.y1 - circle.cy

        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = (fx * fx + fy * fy) - (circle.radius * circle.radius)

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return []

        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)

        points = []
        for t in [t1, t2]:
            if 0.0 <= t <= 1.0:
                x = line.x1 + t * dx
                y = line.y1 + t * dy
                points.append(GeometryPoint(x, y))
        return points

    @staticmethod
    def line_rect_intersection(line: LineObject, rect: RectObject) -> List[GeometryPoint]:
        """Calculates intersection points between a line and a rectangle."""
        # Convert rectangle to 4 lines
        min_x, min_y, max_x, max_y = GeometryEngine.get_shape_bounds(rect)
        
        r_lines = [
            LineObject(min_x, min_y, max_x, min_y),  # Top
            LineObject(max_x, min_y, max_x, max_y),  # Right
            LineObject(max_x, max_y, min_x, max_y),  # Bottom
            LineObject(min_x, max_y, min_x, min_y)   # Left
        ]
        
        points = []
        for r_line in r_lines:
            pts = GeometryEngine.line_line_intersection(line, r_line)
            points.extend(pts)
        return points

    @staticmethod
    def circle_circle_intersection(c1: CircleObject, c2: CircleObject) -> List[GeometryPoint]:
        """Calculates intersection points between two circles."""
        d2 = (c1.cx - c2.cx)**2 + (c1.cy - c2.cy)**2
        d = math.sqrt(d2)
        
        if d > c1.radius + c2.radius or d < abs(c1.radius - c2.radius) or d == 0:
            return []

        a = (c1.radius**2 - c2.radius**2 + d2) / (2 * d)
        h = math.sqrt(max(0, c1.radius**2 - a**2))

        x2 = c1.cx + a * (c2.cx - c1.cx) / d
        y2 = c1.cy + a * (c2.cy - c1.cy) / d

        x3_1 = x2 + h * (c2.cy - c1.cy) / d
        y3_1 = y2 - h * (c2.cx - c1.cx) / d
        x3_2 = x2 - h * (c2.cy - c1.cy) / d
        y3_2 = y2 + h * (c2.cx - c1.cx) / d

        return [GeometryPoint(x3_1, y3_1), GeometryPoint(x3_2, y3_2)]

    @classmethod
    def find_intersections(cls, shape_a: GraphicObject, shape_b: GraphicObject) -> List[IntersectionResult]:
        """Finds all intersection points between two shapes."""
        points = []
        
        # Dispatch based on types
        if isinstance(shape_a, LineObject):
            if isinstance(shape_b, LineObject):
                pts = cls.line_line_intersection(shape_a, shape_b)
            elif isinstance(shape_b, CircleObject):
                pts = cls.line_circle_intersection(shape_a, shape_b)
            elif isinstance(shape_b, RectObject):
                pts = cls.line_rect_intersection(shape_a, shape_b)
            else:
                pts = []
        elif isinstance(shape_a, CircleObject):
            if isinstance(shape_b, LineObject):
                pts = cls.line_circle_intersection(shape_b, shape_a)  # Symmetric
            elif isinstance(shape_b, CircleObject):
                pts = cls.circle_circle_intersection(shape_a, shape_b)
            elif isinstance(shape_b, RectObject):
                # Approximate rect as 4 lines for circle intersection
                pts = []
                min_x, min_y, max_x, max_y = cls.get_shape_bounds(shape_b)
                r_lines = [
                    LineObject(min_x, min_y, max_x, min_y),
                    LineObject(max_x, min_y, max_x, max_y),
                    LineObject(max_x, max_y, min_x, max_y),
                    LineObject(min_x, max_y, min_x, min_y)
                ]
                for r_line in r_lines:
                    sub_pts = cls.line_circle_intersection(r_line, shape_a)
                    pts.extend(sub_pts)
            else:
                pts = []
        elif isinstance(shape_a, RectObject):
            if isinstance(shape_b, LineObject):
                pts = cls.line_rect_intersection(shape_b, shape_a)
            elif isinstance(shape_b, CircleObject):
                # Symmetric to Circle-Rect
                pts = []
                min_x, min_y, max_x, max_y = cls.get_shape_bounds(shape_a)
                r_lines = [
                    LineObject(min_x, min_y, max_x, min_y),
                    LineObject(max_x, min_y, max_x, max_y),
                    LineObject(max_x, max_y, min_x, max_y),
                    LineObject(min_x, max_y, min_x, min_y)
                ]
                for r_line in r_lines:
                    sub_pts = cls.line_circle_intersection(r_line, shape_b)
                    pts.extend(sub_pts)
            elif isinstance(shape_b, RectObject):
                # Rect-Rect: intersect edges
                pts = []
                # Simplified: just check edge intersections for now
                min_x_a, min_y_a, max_x_a, max_y_a = cls.get_shape_bounds(shape_a)
                min_x_b, min_y_b, max_x_b, max_y_b = cls.get_shape_bounds(shape_b)
                
                edges_a = [
                    LineObject(min_x_a, min_y_a, max_x_a, min_y_a),
                    LineObject(max_x_a, min_y_a, max_x_a, max_y_a),
                    LineObject(max_x_a, max_y_a, min_x_a, max_y_a),
                    LineObject(min_x_a, max_y_a, min_x_a, min_y_a)
                ]
                edges_b = [
                    LineObject(min_x_b, min_y_b, max_x_b, min_y_b),
                    LineObject(max_x_b, min_y_b, max_x_b, max_y_b),
                    LineObject(max_x_b, max_y_b, min_x_b, max_y_b),
                    LineObject(min_x_b, max_y_b, min_x_b, min_y_b)
                ]
                
                for ea in edges_a:
                    for eb in edges_b:
                        sub_pts = cls.line_line_intersection(ea, eb)
                        pts.extend(sub_pts)
            else:
                pts = []
        else:
            pts = []
        
        return [IntersectionResult(point=p, shape_a=shape_a, shape_b=shape_b) for p in pts]

    @staticmethod
    def get_snapping_points(shape: GraphicObject) -> List[GeometryPoint]:
        """
        Returns significant points for a shape that can be snapped to.
        Includes endpoints, centers, and control points.
        """
        points = []
        if isinstance(shape, LineObject):
            points.append(GeometryPoint(shape.x1, shape.y1))
            points.append(GeometryPoint(shape.x2, shape.y2))
            # Midpoint
            points.append(GeometryPoint((shape.x1 + shape.x2)/2, (shape.y1 + shape.y2)/2))
        
        elif isinstance(shape, RectObject):
            # Corners
            min_x, min_y, max_x, max_y = GeometryEngine.get_shape_bounds(shape)
            points.append(GeometryPoint(min_x, min_y))
            points.append(GeometryPoint(max_x, min_y))
            points.append(GeometryPoint(max_x, max_y))
            points.append(GeometryPoint(min_x, max_y))
            # Center
            points.append(GeometryPoint((min_x + max_x)/2, (min_y + max_y)/2))
            # Midpoints of edges
            points.append(GeometryPoint((min_x + max_x)/2, min_y))
            points.append(GeometryPoint(max_x, (min_y + max_y)/2))
            points.append(GeometryPoint((min_x + max_x)/2, max_y))
            points.append(GeometryPoint(min_x, (min_y + max_y)/2))

        elif isinstance(shape, CircleObject):
            # Center (Crucial for Circle)
            points.append(GeometryPoint(shape.cx, shape.cy))
            # Cardinal points (N, S, E, W)
            points.append(GeometryPoint(shape.cx, shape.cy - shape.radius))  # North
            points.append(GeometryPoint(shape.cx, shape.cy + shape.radius))  # South
            points.append(GeometryPoint(shape.cx + shape.radius, shape.cy))  # East
            points.append(GeometryPoint(shape.cx - shape.radius, shape.cy))  # West
            
        return points

    @classmethod
    def find_snap_point(cls, query_x: float, query_y: float, shapes: List[GraphicObject], 
                        exclude_shape: Optional[GraphicObject] = None) -> Optional[GeometryPoint]:
        """
        Finds the nearest snap point among all provided shapes.
        Checks standard shape points AND intersection points between shapes.
        
        Args:
            query_x, query_y: The mouse cursor position.
            shapes: List of all shapes in the scene.
            exclude_shape: Shape to ignore (e.g., the one currently being drawn/moved).
            
        Returns:
            The snapped GeometryPoint if within threshold, otherwise None.
        """
        candidates: List[Tuple[GeometryPoint, float]] = []
        threshold_sq = cls.SNAP_THRESHOLD ** 2

        # 1. Check standard anchor points (endpoints, centers, etc.)
        for shape in shapes:
            if shape == exclude_shape:
                continue
            for pt in cls.get_snapping_points(shape):
                dist_sq = (pt.x - query_x)**2 + (pt.y - query_y)**2
                if dist_sq <= threshold_sq:
                    candidates.append((pt, dist_sq))

        # 2. Check intersection points between pairs of shapes
        # This is computationally heavier (O(N^2)), so we do it carefully
        n = len(shapes)
        for i in range(n):
            if shapes[i] == exclude_shape:
                continue
            for j in range(i + 1, n):
                if shapes[j] == exclude_shape:
                    continue
                
                intersections = cls.find_intersections(shapes[i], shapes[j])
                for res in intersections:
                    dist_sq = (res.point.x - query_x)**2 + (res.point.y - query_y)**2
                    if dist_sq <= threshold_sq:
                        candidates.append((res.point, dist_sq))

        if not candidates:
            return None

        # Return the closest candidate
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
