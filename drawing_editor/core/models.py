"""
Data models for graphic objects in the drawing editor.

This module defines the base classes and specific types for all drawable objects
in the CAD application. Each model class stores geometric data and maintains
a reference to its corresponding DXF entity and graphics item.
"""

from typing import Optional, Dict, Any, List


class GraphicObject:
    """
    Base class for all graphic objects.
    
    Uses __slots__ for 40-50% memory reduction and faster attribute access.
    
    Attributes:
        dxf_entity: Reference to the DXF entity (ezdxf object)
        graphics_item: Reference to the QGraphicsItem for rendering
        type: String identifier for the object type
        params: Dictionary for additional parameters
    """
    __slots__ = ('dxf_entity', 'graphics_item', 'type', 'params')
    
    def __init__(self, dxf_entity: Optional[Any] = None) -> None:
        self.dxf_entity = dxf_entity
        self.graphics_item: Optional[Any] = None
        self.type: str = ""
        self.params: Dict[str, Any] = {}


class PointObject(GraphicObject):
    """
    Represents a point in 2D space.
    
    Attributes:
        x: X coordinate
        y: Y coordinate
    """
    __slots__ = ('x', 'y')
    
    def __init__(self, x: float, y: float, dxf_entity: Optional[Any] = None) -> None:
        super().__init__(dxf_entity)
        self.type = "Point"
        self.x: float = x
        self.y: float = y


class LineObject(GraphicObject):
    """
    Represents a line segment defined by two points.
    
    Attributes:
        x1, y1: Start point coordinates
        x2, y2: End point coordinates
    """
    __slots__ = ('x1', 'y1', 'x2', 'y2')
    
    def __init__(
        self, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Line"
        self.x1: float = x1
        self.y1: float = y1
        self.x2: float = x2
        self.y2: float = y2
    
    @property
    def length(self) -> float:
        """Calculate the length of the line segment."""
        import math
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)
    
    @property
    def midpoint(self) -> tuple[float, float]:
        """Calculate the midpoint of the line segment."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class CircleObject(GraphicObject):
    """
    Represents a circle defined by center and radius.
    
    Attributes:
        cx, cy: Center coordinates
        radius: Circle radius
    """
    __slots__ = ('cx', 'cy', 'radius')
    
    def __init__(
        self, 
        cx: float, 
        cy: float, 
        radius: float, 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Circle"
        self.cx: float = cx
        self.cy: float = cy
        self.radius: float = radius
    
    @property
    def area(self) -> float:
        """Calculate the area of the circle."""
        import math
        return math.pi * self.radius ** 2
    
    @property
    def circumference(self) -> float:
        """Calculate the circumference of the circle."""
        import math
        return 2 * math.pi * self.radius


class RectObject(GraphicObject):
    """
    Represents a rectangle defined by two corner points.
    
    Attributes:
        x1, y1: First corner coordinates
        x2, y2: Second corner coordinates
    """
    __slots__ = ('x1', 'y1', 'x2', 'y2')
    
    def __init__(
        self, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Rectangle"
        self.x1: float = x1
        self.y1: float = y1
        self.x2: float = x2
        self.y2: float = y2
    
    @property
    def width(self) -> float:
        """Calculate the width of the rectangle."""
        return abs(self.x2 - self.x1)
    
    @property
    def height(self) -> float:
        """Calculate the height of the rectangle."""
        return abs(self.y2 - self.y1)
    
    @property
    def area(self) -> float:
        """Calculate the area of the rectangle."""
        return self.width * self.height
    
    @property
    def center(self) -> tuple[float, float]:
        """Calculate the center point of the rectangle."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class ArcObject(GraphicObject):
    """
    Represents an arc defined by center, radius, and angles.
    
    Attributes:
        cx, cy: Center coordinates
        radius: Arc radius
        start_angle: Start angle in degrees
        end_angle: End angle in degrees
    """
    __slots__ = ('cx', 'cy', 'radius', 'start_angle', 'end_angle')
    
    def __init__(
        self, 
        cx: float, 
        cy: float, 
        radius: float, 
        start_angle: float, 
        end_angle: float, 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Arc"
        self.cx: float = cx
        self.cy: float = cy
        self.radius: float = radius
        self.start_angle: float = start_angle
        self.end_angle: float = end_angle
    
    @property
    def span(self) -> float:
        """Calculate the angular span of the arc in degrees."""
        if self.end_angle < self.start_angle:
            return 360 - (self.start_angle - self.end_angle)
        return self.end_angle - self.start_angle
    
    @property
    def arc_length(self) -> float:
        """Calculate the arc length."""
        import math
        return self.radius * math.radians(self.span)


class TextObject(GraphicObject):
    """
    Represents a text annotation at a specific position.
    
    Attributes:
        x, y: Insertion point coordinates
        text: The text content
        height: Text height
    """
    __slots__ = ('x', 'y', 'text', 'height')
    
    def __init__(
        self, 
        x: float, 
        y: float, 
        text: str, 
        height: float = 2.5, 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Text"
        self.x: float = x
        self.y: float = y
        self.text: str = text
        self.height: float = height


class DimensionObject(GraphicObject):
    """
    Represents a dimension annotation (linear, radial, diameter, or angular).
    
    Attributes:
        dim_type: Type of dimension ("Linear", "Radius", "Diameter", "Angular")
        p1: First reference point (QPointF)
        p2: Second reference point (QPointF)
        offset: Offset distance for dimension line
        radius: Radius value (for radius dimensions)
        diameter: Diameter value (for diameter dimensions)
        angle: Angle value (for angular dimensions)
    """
    __slots__ = ('dim_type', 'p1', 'p2', 'offset', 'radius', 'diameter', 'angle')
    
    def __init__(
        self, 
        p1: Any, 
        p2: Any, 
        offset: float = 2, 
        dim_type: str = "Linear", 
        dxf_entity: Optional[Any] = None
    ) -> None:
        super().__init__(dxf_entity)
        self.type = "Dimension"
        self.dim_type: str = dim_type
        self.p1: Any = p1
        self.p2: Any = p2
        self.offset: float = offset
        self.radius: Optional[float] = None
        self.diameter: Optional[float] = None
        self.angle: Optional[float] = None
