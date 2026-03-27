"""
Drawing Editor - A PyQt5-based DXF drawing application.

This package provides a comprehensive 2D CAD-like drawing editor with support for:
- Basic shapes (points, lines, circles, rectangles, arcs)
- Text annotations
- Dimensions (linear, radius, diameter, angular)
- DXF file import/export
- Object snapping
- Interactive editing
"""

__version__ = "1.0.0"
__author__ = "Drawing Editor Team"

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

__all__ = [
    "GraphicObject",
    "PointObject",
    "LineObject",
    "CircleObject",
    "RectObject",
    "ArcObject",
    "TextObject",
    "DimensionObject",
]
