"""
Mathematical utility functions for geometric calculations.

This module provides common mathematical operations used throughout
the drawing editor for geometry processing.
"""

import math
from typing import Tuple


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate Euclidean distance between two points.
    
    Args:
        x1, y1: First point coordinates
        x2, y2: Second point coordinates
        
    Returns:
        Distance between the two points
    """
    return math.hypot(x2 - x1, y2 - y1)


def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    """
    Normalize a 2D vector to unit length.
    
    Args:
        x, y: Vector components
        
    Returns:
        Tuple of (normalized_x, normalized_y)
    """
    magnitude = math.hypot(x, y)
    if magnitude == 0:
        return (0.0, 0.0)
    return (x / magnitude, y / magnitude)


def rotate_point(
    x: float, 
    y: float, 
    angle_degrees: float, 
    origin_x: float = 0.0, 
    origin_y: float = 0.0
) -> Tuple[float, float]:
    """
    Rotate a point around an origin by a given angle.
    
    Args:
        x, y: Point coordinates to rotate
        angle_degrees: Rotation angle in degrees (counter-clockwise)
        origin_x, origin_y: Origin point for rotation
        
    Returns:
        Tuple of (rotated_x, rotated_y)
    """
    angle_rad = math.radians(angle_degrees)
    dx = x - origin_x
    dy = y - origin_y
    
    rotated_x = origin_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
    rotated_y = origin_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
    
    return (rotated_x, rotated_y)


def calculate_angle(
    x1: float, 
    y1: float, 
    x2: float, 
    y2: float
) -> float:
    """
    Calculate the angle between two points in degrees.
    
    Args:
        x1, y1: First point coordinates
        x2, y2: Second point coordinates
        
    Returns:
        Angle in degrees from horizontal (0-360)
    """
    dx = x2 - x1
    dy = y2 - y1
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # Normalize to 0-360 range
    if angle_deg < 0:
        angle_deg += 360
    
    return angle_deg


def midpoint(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint between two points.
    
    Args:
        x1, y1: First point coordinates
        x2, y2: Second point coordinates
        
    Returns:
        Tuple of (midpoint_x, midpoint_y)
    """
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def is_point_on_line(
    px: float, 
    py: float, 
    x1: float, 
    y1: float, 
    x2: float, 
    y2: float, 
    tolerance: float = 0.001
) -> bool:
    """
    Check if a point lies on a line segment.
    
    Args:
        px, py: Point to check
        x1, y1: Line start coordinates
        x2, y2: Line end coordinates
        tolerance: Tolerance for floating-point comparison
        
    Returns:
        True if point is on the line segment
    """
    # Check if point is within bounding box
    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)
    
    if not (min_x - tolerance <= px <= max_x + tolerance and
            min_y - tolerance <= py <= max_y + tolerance):
        return False
    
    # Check collinearity using cross product
    cross = (py - y1) * (x2 - x1) - (px - x1) * (y2 - y1)
    return abs(cross) < tolerance
