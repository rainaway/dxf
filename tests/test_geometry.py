"""
Tests for geometry engine - intersection and snapping logic.
"""
import unittest
import math
from drawing_editor.core.models import LineObject, CircleObject, RectObject
from drawing_editor.core.geometry import GeometryEngine, GeometryPoint


class TestLineLineIntersection(unittest.TestCase):
    """Test line-line intersection calculations."""
    
    def test_intersecting_lines(self):
        """Test two lines that intersect at a single point."""
        l1 = LineObject(0, 0, 10, 10)
        l2 = LineObject(0, 10, 10, 0)
        
        points = GeometryEngine.line_line_intersection(l1, l2)
        
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0].x, 5.0, places=5)
        self.assertAlmostEqual(points[0].y, 5.0, places=5)
    
    def test_parallel_lines(self):
        """Test parallel lines that don't intersect."""
        l1 = LineObject(0, 0, 10, 0)
        l2 = LineObject(0, 5, 10, 5)
        
        points = GeometryEngine.line_line_intersection(l1, l2)
        
        self.assertEqual(len(points), 0)
    
    def test_non_intersecting_segments(self):
        """Test lines that would intersect if extended but segments don't."""
        l1 = LineObject(0, 0, 5, 5)
        l2 = LineObject(6, 0, 10, 5)
        
        points = GeometryEngine.line_line_intersection(l1, l2)
        
        self.assertEqual(len(points), 0)


class TestLineCircleIntersection(unittest.TestCase):
    """Test line-circle intersection calculations."""
    
    def test_line_through_circle(self):
        """Test a line that passes through a circle (2 intersections)."""
        line = LineObject(-10, 0, 10, 0)
        circle = CircleObject(0, 0, 5)
        
        points = GeometryEngine.line_circle_intersection(line, circle)
        
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[0].x, -5.0, places=5)
        self.assertAlmostEqual(points[1].x, 5.0, places=5)
    
    def test_line_tangent_to_circle(self):
        """Test a line tangent to a circle (1 intersection)."""
        line = LineObject(-10, 5, 10, 5)
        circle = CircleObject(0, 0, 5)
        
        points = GeometryEngine.line_circle_intersection(line, circle)
        
        # Tangent case: discriminant is 0, but floating point may give 2 very close points
        self.assertGreaterEqual(len(points), 1)
        # All points should be at approximately (0, 5)
        for pt in points:
            self.assertAlmostEqual(pt.x, 0.0, places=4)
            self.assertAlmostEqual(pt.y, 5.0, places=4)
    
    def test_line_missing_circle(self):
        """Test a line that doesn't intersect a circle."""
        line = LineObject(-10, 10, 10, 10)
        circle = CircleObject(0, 0, 5)
        
        points = GeometryEngine.line_circle_intersection(line, circle)
        
        self.assertEqual(len(points), 0)


class TestCircleCircleIntersection(unittest.TestCase):
    """Test circle-circle intersection calculations."""
    
    def test_intersecting_circles(self):
        """Test two circles that intersect at two points."""
        c1 = CircleObject(0, 0, 5)
        c2 = CircleObject(6, 0, 5)
        
        points = GeometryEngine.circle_circle_intersection(c1, c2)
        
        self.assertEqual(len(points), 2)
        # Intersection points should be symmetric about x-axis
        self.assertAlmostEqual(points[0].x, 3.0, places=5)
        self.assertAlmostEqual(points[1].x, 3.0, places=5)
    
    def test_separate_circles(self):
        """Test two circles that don't intersect."""
        c1 = CircleObject(0, 0, 2)
        c2 = CircleObject(10, 0, 2)
        
        points = GeometryEngine.circle_circle_intersection(c1, c2)
        
        self.assertEqual(len(points), 0)
    
    def test_concentric_circles(self):
        """Test concentric circles (no intersection)."""
        c1 = CircleObject(0, 0, 5)
        c2 = CircleObject(0, 0, 3)
        
        points = GeometryEngine.circle_circle_intersection(c1, c2)
        
        self.assertEqual(len(points), 0)


class TestSnappingPoints(unittest.TestCase):
    """Test snapping point generation for different shapes."""
    
    def test_line_snapping_points(self):
        """Test snapping points for a line."""
        line = LineObject(0, 0, 10, 10)
        
        points = GeometryEngine.get_snapping_points(line)
        
        self.assertEqual(len(points), 3)  # Start, end, midpoint
        # Check start
        self.assertAlmostEqual(points[0].x, 0.0)
        self.assertAlmostEqual(points[0].y, 0.0)
        # Check end
        self.assertAlmostEqual(points[1].x, 10.0)
        self.assertAlmostEqual(points[1].y, 10.0)
        # Check midpoint
        self.assertAlmostEqual(points[2].x, 5.0)
        self.assertAlmostEqual(points[2].y, 5.0)
    
    def test_circle_snapping_points(self):
        """Test snapping points for a circle - includes center!"""
        circle = CircleObject(5, 5, 10)
        
        points = GeometryEngine.get_snapping_points(circle)
        
        self.assertEqual(len(points), 5)  # Center + 4 cardinal points
        
        # Check center (CRUCIAL for circles)
        center = points[0]
        self.assertAlmostEqual(center.x, 5.0)
        self.assertAlmostEqual(center.y, 5.0)
        
        # Check cardinal points
        north = points[1]
        south = points[2]
        east = points[3]
        west = points[4]
        
        self.assertAlmostEqual(north.x, 5.0)
        self.assertAlmostEqual(north.y, -5.0)  # 5 - 10
        
        self.assertAlmostEqual(south.x, 5.0)
        self.assertAlmostEqual(south.y, 15.0)  # 5 + 10
        
        self.assertAlmostEqual(east.x, 15.0)  # 5 + 10
        self.assertAlmostEqual(east.y, 5.0)
        
        self.assertAlmostEqual(west.x, -5.0)  # 5 - 10
        self.assertAlmostEqual(west.y, 5.0)
    
    def test_rect_snapping_points(self):
        """Test snapping points for a rectangle."""
        rect = RectObject(0, 0, 10, 8)
        
        points = GeometryEngine.get_snapping_points(rect)
        
        # 4 corners + 1 center + 4 edge midpoints = 9 points
        self.assertEqual(len(points), 9)


class TestFindSnapPoint(unittest.TestCase):
    """Test the main snapping function."""
    
    def test_snap_to_line_endpoint(self):
        """Test snapping to a line endpoint."""
        line = LineObject(0, 0, 10, 10)
        shapes = [line]
        
        # Query point near the start (within threshold)
        snapped = GeometryEngine.find_snap_point(1.0, 1.0, shapes)
        
        self.assertIsNotNone(snapped)
        self.assertAlmostEqual(snapped.x, 0.0, places=5)
        self.assertAlmostEqual(snapped.y, 0.0, places=5)
    
    def test_snap_to_circle_center(self):
        """Test snapping to circle center - KEY FEATURE."""
        circle = CircleObject(5, 5, 10)
        shapes = [circle]
        
        # Query point near the center
        snapped = GeometryEngine.find_snap_point(5.5, 4.5, shapes)
        
        self.assertIsNotNone(snapped)
        self.assertAlmostEqual(snapped.x, 5.0, places=5)
        self.assertAlmostEqual(snapped.y, 5.0, places=5)
    
    def test_no_snap_when_far(self):
        """Test that no snapping occurs when far from any point."""
        line = LineObject(0, 0, 10, 10)
        shapes = [line]
        
        # Query point far away (threshold is 10 pixels)
        snapped = GeometryEngine.find_snap_point(50.0, 50.0, shapes)
        
        self.assertIsNone(snapped)
    
    def test_exclude_shape(self):
        """Test that excluded shape is ignored."""
        line1 = LineObject(0, 0, 10, 10)
        line2 = LineObject(20, 20, 30, 30)
        shapes = [line1, line2]
        
        # Query near line1 but exclude it
        snapped = GeometryEngine.find_snap_point(1.0, 1.0, shapes, exclude_shape=line1)
        
        # Should not snap to line1, and line2 is too far
        self.assertIsNone(snapped)


class TestIntersectionResults(unittest.TestCase):
    """Test the find_intersections method."""
    
    def test_line_rect_intersection(self):
        """Test intersection between line and rectangle."""
        line = LineObject(-5, 5, 15, 5)
        rect = RectObject(0, 0, 10, 10)
        
        results = GeometryEngine.find_intersections(line, rect)
        
        # Line should intersect top and bottom edges
        self.assertEqual(len(results), 2)
    
    def test_circle_rect_intersection(self):
        """Test intersection between circle and rectangle."""
        # Circle centered at origin with radius 5
        # Rectangle from (-4,-4) to (4,4) - circle extends outside on all sides
        # Intersections occur where x^2+y^2=25 meets the rectangle edges
        circle = CircleObject(0, 0, 5)
        rect = RectObject(-4, -4, 4, 4)
        
        results = GeometryEngine.find_intersections(circle, rect)
        
        # Circle should intersect all 4 edges (2 points per edge = 8 total)
        self.assertGreaterEqual(len(results), 4)


if __name__ == '__main__':
    unittest.main()
