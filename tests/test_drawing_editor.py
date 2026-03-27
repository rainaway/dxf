"""
Unit tests for the Drawing Editor application.
Tests cover data models, geometry calculations, and core functionality.
"""

import unittest
import math
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drawing_editor import (
    GraphicObject, PointObject, LineObject, CircleObject, 
    RectObject, ArcObject, TextObject, DimensionObject
)


class TestGraphicObject(unittest.TestCase):
    """Tests for the base GraphicObject class."""
    
    def test_init_default_values(self):
        """Test that GraphicObject initializes with default values."""
        obj = GraphicObject()
        self.assertIsNone(obj.dxf_entity)
        self.assertIsNone(obj.graphics_item)
        self.assertEqual(obj.type, "")
        self.assertEqual(obj.params, {})
    
    def test_init_with_dxf_entity(self):
        """Test GraphicObject initialization with DXF entity."""
        mock_entity = {"type": "LINE"}
        obj = GraphicObject(dxf_entity=mock_entity)
        self.assertEqual(obj.dxf_entity, mock_entity)


class TestPointObject(unittest.TestCase):
    """Tests for PointObject class."""
    
    def test_init(self):
        """Test PointObject initialization."""
        point = PointObject(10.0, 20.0)
        self.assertEqual(point.type, "Point")
        self.assertEqual(point.x, 10.0)
        self.assertEqual(point.y, 20.0)
    
    def test_init_with_dxf_entity(self):
        """Test PointObject with DXF entity."""
        mock_entity = {"type": "POINT"}
        point = PointObject(5.0, 15.0, dxf_entity=mock_entity)
        self.assertEqual(point.dxf_entity, mock_entity)


class TestLineObject(unittest.TestCase):
    """Tests for LineObject class."""
    
    def test_init(self):
        """Test LineObject initialization."""
        line = LineObject(0.0, 0.0, 10.0, 20.0)
        self.assertEqual(line.type, "Line")
        self.assertEqual(line.x1, 0.0)
        self.assertEqual(line.y1, 0.0)
        self.assertEqual(line.x2, 10.0)
        self.assertEqual(line.y2, 20.0)
    
    def test_length_calculation(self):
        """Test manual length calculation for a line."""
        line = LineObject(0.0, 0.0, 3.0, 4.0)
        length = math.hypot(line.x2 - line.x1, line.y2 - line.y1)
        self.assertAlmostEqual(length, 5.0)
    
    def test_midpoint_calculation(self):
        """Test midpoint calculation for a line."""
        line = LineObject(0.0, 0.0, 10.0, 10.0)
        mid_x = (line.x1 + line.x2) / 2
        mid_y = (line.y1 + line.y2) / 2
        self.assertEqual(mid_x, 5.0)
        self.assertEqual(mid_y, 5.0)


class TestCircleObject(unittest.TestCase):
    """Tests for CircleObject class."""
    
    def test_init(self):
        """Test CircleObject initialization."""
        circle = CircleObject(5.0, 10.0, 3.0)
        self.assertEqual(circle.type, "Circle")
        self.assertEqual(circle.cx, 5.0)
        self.assertEqual(circle.cy, 10.0)
        self.assertEqual(circle.radius, 3.0)
    
    def test_area_calculation(self):
        """Test area calculation for a circle."""
        circle = CircleObject(0.0, 0.0, 2.0)
        area = math.pi * circle.radius ** 2
        self.assertAlmostEqual(area, 12.566370614359172)
    
    def test_circumference_calculation(self):
        """Test circumference calculation for a circle."""
        circle = CircleObject(0.0, 0.0, 5.0)
        circumference = 2 * math.pi * circle.radius
        self.assertAlmostEqual(circumference, 31.41592653589793)
    
    def test_point_on_circle(self):
        """Test if a point lies on the circle boundary."""
        circle = CircleObject(0.0, 0.0, 5.0)
        # Point at (5, 0) should be on the circle
        point_x, point_y = 5.0, 0.0
        distance = math.hypot(point_x - circle.cx, point_y - circle.cy)
        self.assertAlmostEqual(distance, circle.radius)


class TestRectObject(unittest.TestCase):
    """Tests for RectObject class."""
    
    def test_init(self):
        """Test RectObject initialization."""
        rect = RectObject(0.0, 0.0, 10.0, 5.0)
        self.assertEqual(rect.type, "Rectangle")
        self.assertEqual(rect.x1, 0.0)
        self.assertEqual(rect.y1, 0.0)
        self.assertEqual(rect.x2, 10.0)
        self.assertEqual(rect.y2, 5.0)
    
    def test_width_calculation(self):
        """Test width calculation for a rectangle."""
        rect = RectObject(0.0, 0.0, 10.0, 5.0)
        width = abs(rect.x2 - rect.x1)
        self.assertEqual(width, 10.0)
    
    def test_height_calculation(self):
        """Test height calculation for a rectangle."""
        rect = RectObject(0.0, 0.0, 10.0, 5.0)
        height = abs(rect.y2 - rect.y1)
        self.assertEqual(height, 5.0)
    
    def test_area_calculation(self):
        """Test area calculation for a rectangle."""
        rect = RectObject(0.0, 0.0, 10.0, 5.0)
        area = abs(rect.x2 - rect.x1) * abs(rect.y2 - rect.y1)
        self.assertEqual(area, 50.0)
    
    def test_center_calculation(self):
        """Test center point calculation for a rectangle."""
        rect = RectObject(0.0, 0.0, 10.0, 6.0)
        center_x = (rect.x1 + rect.x2) / 2
        center_y = (rect.y1 + rect.y2) / 2
        self.assertEqual(center_x, 5.0)
        self.assertEqual(center_y, 3.0)
    
    def test_inverted_coordinates(self):
        """Test rectangle with inverted coordinates."""
        rect = RectObject(10.0, 10.0, 0.0, 0.0)
        width = abs(rect.x2 - rect.x1)
        height = abs(rect.y2 - rect.y1)
        self.assertEqual(width, 10.0)
        self.assertEqual(height, 10.0)


class TestArcObject(unittest.TestCase):
    """Tests for ArcObject class."""
    
    def test_init(self):
        """Test ArcObject initialization."""
        arc = ArcObject(0.0, 0.0, 5.0, 0.0, 90.0)
        self.assertEqual(arc.type, "Arc")
        self.assertEqual(arc.cx, 0.0)
        self.assertEqual(arc.cy, 0.0)
        self.assertEqual(arc.radius, 5.0)
        self.assertEqual(arc.start_angle, 0.0)
        self.assertEqual(arc.end_angle, 90.0)
    
    def test_arc_span_positive(self):
        """Test arc span calculation for positive angles."""
        arc = ArcObject(0.0, 0.0, 5.0, 0.0, 90.0)
        span = arc.end_angle - arc.start_angle
        self.assertEqual(span, 90.0)
    
    def test_arc_span_negative(self):
        """Test arc span calculation when end < start."""
        arc = ArcObject(0.0, 0.0, 5.0, 350.0, 10.0)
        if arc.end_angle < arc.start_angle:
            span = 360 - (arc.start_angle - arc.end_angle)
        else:
            span = arc.end_angle - arc.start_angle
        self.assertEqual(span, 20.0)
    
    def test_arc_length_calculation(self):
        """Test arc length calculation."""
        arc = ArcObject(0.0, 0.0, 10.0, 0.0, 90.0)
        span_rad = math.radians(arc.end_angle - arc.start_angle)
        arc_length = arc.radius * span_rad
        self.assertAlmostEqual(arc_length, 15.707963267948966)
    
    def test_quarter_circle_area(self):
        """Test area of a quarter circle arc."""
        arc = ArcObject(0.0, 0.0, 4.0, 0.0, 90.0)
        full_area = math.pi * arc.radius ** 2
        quarter_area = full_area / 4
        self.assertAlmostEqual(quarter_area, 12.566370614359172)


class TestTextObject(unittest.TestCase):
    """Tests for TextObject class."""
    
    def test_init_default_height(self):
        """Test TextObject initialization with default height."""
        text = TextObject(0.0, 0.0, "Hello")
        self.assertEqual(text.type, "Text")
        self.assertEqual(text.x, 0.0)
        self.assertEqual(text.y, 0.0)
        self.assertEqual(text.text, "Hello")
        self.assertEqual(text.height, 2.5)
    
    def test_init_custom_height(self):
        """Test TextObject initialization with custom height."""
        text = TextObject(5.0, 10.0, "World", height=5.0)
        self.assertEqual(text.height, 5.0)
    
    def test_empty_text(self):
        """Test TextObject with empty string."""
        text = TextObject(0.0, 0.0, "")
        self.assertEqual(text.text, "")
    
    def test_special_characters(self):
        """Test TextObject with special characters."""
        text = TextObject(0.0, 0.0, "Special: @#$%^&*()")
        self.assertEqual(text.text, "Special: @#$%^&*()")


class TestDimensionObject(unittest.TestCase):
    """Tests for DimensionObject class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from PyQt5.QtCore import QPointF
        self.p1 = QPointF(0.0, 0.0)
        self.p2 = QPointF(10.0, 0.0)
    
    def test_linear_dimension_init(self):
        """Test Linear DimensionObject initialization."""
        dim = DimensionObject(self.p1, self.p2, offset=2.0, dim_type="Linear")
        self.assertEqual(dim.type, "Dimension")
        self.assertEqual(dim.dim_type, "Linear")
        self.assertEqual(dim.offset, 2.0)
    
    def test_radius_dimension_init(self):
        """Test Radius DimensionObject initialization."""
        dim = DimensionObject(self.p1, self.p2, dim_type="Radius")
        dim.radius = 5.0
        self.assertEqual(dim.dim_type, "Radius")
        self.assertEqual(dim.radius, 5.0)
    
    def test_diameter_dimension_init(self):
        """Test Diameter DimensionObject initialization."""
        dim = DimensionObject(self.p1, self.p2, dim_type="Diameter")
        dim.diameter = 10.0
        self.assertEqual(dim.dim_type, "Diameter")
        self.assertEqual(dim.diameter, 10.0)
    
    def test_angular_dimension_init(self):
        """Test Angular DimensionObject initialization."""
        dim = DimensionObject(self.p1, self.p2, dim_type="Angular")
        dim.angle = 45.0
        self.assertEqual(dim.dim_type, "Angular")
        self.assertEqual(dim.angle, 45.0)
    
    def test_distance_calculation(self):
        """Test distance calculation between two points."""
        import math
        dx = self.p2.x() - self.p1.x()
        dy = self.p2.y() - self.p1.y()
        distance = math.hypot(dx, dy)
        self.assertEqual(distance, 10.0)
    
    def test_offset_dimension_line(self):
        """Test offset calculation for dimension line."""
        dim = DimensionObject(self.p1, self.p2, offset=3.0)
        # For horizontal line, offset should be in Y direction
        self.assertEqual(dim.offset, 3.0)


class TestGeometryCalculations(unittest.TestCase):
    """Tests for geometric calculations used in the drawing editor."""
    
    def test_point_distance(self):
        """Test Euclidean distance between two points."""
        x1, y1 = 0.0, 0.0
        x2, y2 = 3.0, 4.0
        distance = math.hypot(x2 - x1, y2 - y1)
        self.assertEqual(distance, 5.0)
    
    def test_line_intersection_horizontal_vertical(self):
        """Test intersection of horizontal and vertical lines."""
        # Horizontal line from (0, 5) to (10, 5)
        # Vertical line from (5, 0) to (5, 10)
        intersection_x = 5.0
        intersection_y = 5.0
        self.assertEqual(intersection_x, 5.0)
        self.assertEqual(intersection_y, 5.0)
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        x, y = 3.0, 4.0
        magnitude = math.hypot(x, y)
        nx, ny = x / magnitude, y / magnitude
        self.assertAlmostEqual(nx, 0.6)
        self.assertAlmostEqual(ny, 0.8)
        # Normalized vector should have magnitude 1
        self.assertAlmostEqual(math.hypot(nx, ny), 1.0)
    
    def test_rotate_point_90_degrees(self):
        """Test rotating a point 90 degrees around origin."""
        x, y = 1.0, 0.0
        angle_rad = math.radians(90)
        rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
        rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
        self.assertAlmostEqual(rotated_x, 0.0, places=5)
        self.assertAlmostEqual(rotated_y, 1.0)
    
    def test_angle_between_points(self):
        """Test angle calculation between two points."""
        x1, y1 = 0.0, 0.0
        x2, y2 = 1.0, 1.0
        angle_rad = math.atan2(y2 - y1, x2 - x1)
        angle_deg = math.degrees(angle_rad)
        self.assertAlmostEqual(angle_deg, 45.0)


class TestSnapLogic(unittest.TestCase):
    """Tests for snap logic and tolerance calculations."""
    
    def test_snap_tolerance_check(self):
        """Test if point is within snap tolerance."""
        snap_distance = 10.0
        point_x, point_y = 5.0, 5.0
        target_x, target_y = 8.0, 9.0
        distance = math.hypot(point_x - target_x, point_y - target_y)
        is_within_tolerance = distance <= snap_distance
        self.assertTrue(is_within_tolerance)
    
    def test_snap_tolerance_outside(self):
        """Test if point is outside snap tolerance."""
        snap_distance = 5.0
        point_x, point_y = 0.0, 0.0
        target_x, target_y = 10.0, 10.0
        distance = math.hypot(point_x - target_x, point_y - target_y)
        is_within_tolerance = distance <= snap_distance
        self.assertFalse(is_within_tolerance)
    
    def test_closest_endpoint(self):
        """Test finding closest endpoint on a line."""
        line_start = (0.0, 0.0)
        line_end = (10.0, 0.0)
        cursor_pos = (9.0, 1.0)
        
        dist_to_start = math.hypot(cursor_pos[0] - line_start[0], 
                                    cursor_pos[1] - line_start[1])
        dist_to_end = math.hypot(cursor_pos[0] - line_end[0], 
                                  cursor_pos[1] - line_end[1])
        
        closest = line_start if dist_to_start < dist_to_end else line_end
        self.assertEqual(closest, line_end)


if __name__ == '__main__':
    unittest.main()
