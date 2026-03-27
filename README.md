# DXF Drawing Editor

A PyQt5-based CAD application for viewing and editing DXF (Drawing Exchange Format) files. This tool provides a graphical interface for creating, editing, and saving technical drawings with support for various geometric primitives and dimensioning tools.

## Features

### Drawing Tools
- **Line**: Create straight line segments
- **Circle**: Draw circles by center and radius
- **Rectangle**: Create rectangular shapes
- **Arc**: Draw arcs with specified angles
- **Text**: Add text annotations to drawings

### Dimensioning Tools
- **Linear Dimension**: Measure distance between two points
- **Radius Dimension**: Display radius of circles/arcs
- **Diameter Dimension**: Show diameter measurements
- **Angular Dimension**: Measure angles between vectors

### Object Snapping
Precision drawing with snap-to-point functionality:
- **Endpoint Snap**: Snap to line/segment endpoints
- **Midpoint Snap**: Snap to line midpoints
- **Center Snap**: Snap to circle/arc centers
- Configurable snap tolerance

### File Operations
- Open existing DXF files
- Create new drawings
- Save drawings in DXF R2010 format
- Support for multiple DXF entity types (LINE, CIRCLE, ARC, TEXT, POINT, LWPOLYLINE)

### Line Styling
- Multiple line types (Continuous, Dashed, Dotted, DashDot, DashDotDot)
- Adjustable line weights
- Color support (simplified)

## Requirements

- Python 3.7+
- PyQt5
- ezdxf

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install PyQt5 ezdxf
```

## Usage

### Running the Application

On Windows:
```bash
run_editor.bat
```

Or directly with Python:
```bash
python drawing_editor/main.py
```

### Basic Workflow

1. **Create New Drawing**: Click "New" toolbar button or start fresh
2. **Select Tool**: Choose a drawing tool from the toolbar (Line, Circle, etc.)
3. **Draw**: Click on canvas to place points; right-click to cancel
4. **Edit Objects**: Select objects and use "Edit Selected" or "Properties" buttons
5. **Save**: Click "Save" to export as DXF file

### Keyboard/Mouse Controls

- **Left Click**: Place point / select object
- **Right Click**: Cancel current operation
- **Mouse Drag** (Select mode): Pan view
- **Rubber Band**: Selection box in Select mode

## Project Structure

```
/workspace/
├── drawing_editor/           # Refactored package (modular architecture)
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   └── models.py         # Data models (GraphicObject, LineObject, etc.)
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py    # Main application window (CadWindow)
│   │   ├── cad_view.py       # Custom QGraphicsView (CadView)
│   │   ├── graphics_items.py # PyQt5 graphics items
│   │   └── dialogs.py        # Property and input dialogs
│   ├── managers/
│   │   ├── __init__.py
│   │   └── snap_manager.py   # Object snapping manager
│   └── utils/
│       ├── __init__.py
│       └── math_utils.py     # Mathematical utility functions
├── drawing_editor.py         # Legacy monolithic file (for reference)
├── cad_editor.py             # Alternative editor version
├── run_editor.bat            # Windows batch launcher
├── README.md                 # This file
├── IMPROVEMENTS.md           # Detailed improvement suggestions
└── tests/
    ├── __init__.py
    └── test_drawing_editor.py  # Unit tests (40 tests)
```

## Code Architecture

The application follows an MVC-like architecture with a modular package structure:

### Data Models (`drawing_editor/core/models.py`)
- `GraphicObject`: Base class for all graphic objects
- `PointObject`, `LineObject`, `CircleObject`, etc.: Specific shape models
- `DimensionObject`: Dimension annotation model
- Properties like `length`, `area`, `midpoint` for geometric calculations

### Graphics Items (`drawing_editor/ui/graphics_items.py`)
- `GraphicsPoint`, `GraphicsLine`, `GraphicsCircle`, etc.: Qt graphics items
- `GraphicsDimension`: Complex dimension rendering
- All items support selection, movement, and style updates
- `update_from_obj()` methods for synchronizing with data models

### Managers (`drawing_editor/managers/`)
- `SnapManager`: Handles object snapping logic (endpoints, centers, midpoints)
- Configurable snap tolerance and snap types

### UI Components (`drawing_editor/ui/`)
- `CadView`: Custom QGraphicsView with drawing tools and mouse interaction
- `CadWindow`: Main application window with toolbar, docks, and menus
- `PropertyDialog`: Dialog for editing object properties
- `dialogs`: Additional input dialogs for arc, text, and dimension parameters

### Utilities (`drawing_editor/utils/math_utils.py`)
- Geometric calculation functions (distance, angle, rotation, midpoint)
- Vector operations (normalization)
- Point-on-line detection

### Entry Point (`drawing_editor/main.py`)
- Application bootstrap and PyQt5 event loop

## Supported DXF Entities

| Entity Type | Read | Write | Edit |
|-------------|------|-------|------|
| LINE        | ✓    | ✓     | ✓    |
| CIRCLE      | ✓    | ✓     | ✓    |
| ARC         | ✓    | ✓     | ✓    |
| TEXT        | ✓    | ✓     | ✓    |
| POINT       | ✓    | ✓     | ✓    |
| LWPOLYLINE  | ✓    | ✓     | Partial |

## Limitations

- Color mapping is simplified (primarily black)
- Dimension entities are visual-only (not saved to DXF)
- Polyline editing creates separate line segments
- Angular dimension uses dialog input for third point

## Future Improvements

Potential enhancements for future versions:
- Full color palette support
- Layer management
- Block/reference support
- More dimension styles
- Undo/redo functionality
- Export to other formats (SVG, PDF)
- Grid display and coordinate input

## Testing

The project includes a comprehensive unit test suite covering data models and geometry calculations.

### Running Tests

```bash
# Run all tests
python tests/test_drawing_editor.py

# Run with verbose output
python tests/test_drawing_editor.py -v
```

### Test Coverage

- **GraphicObject**: Base class initialization
- **PointObject**: Point creation and properties
- **LineObject**: Length, midpoint, and angle calculations
- **CircleObject**: Area, circumference, and point containment
- **RectObject**: Width, height, area, and center calculations
- **ArcObject**: Span, length, and area calculations
- **TextObject**: Text properties and special characters
- **DimensionObject**: All dimension types (Linear, Radius, Diameter, Angular)
- **Geometry Calculations**: Distance, normalization, rotation, angles
- **Snap Logic**: Tolerance checking and closest point detection

**Total**: 40 tests covering core functionality

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Areas for improvement include:
- Bug fixes
- New features
- Documentation improvements
- Code refactoring

## Troubleshooting

### Common Issues

**Application won't start:**
- Ensure PyQt5 and ezdxf are installed: `pip install PyQt5 ezdxf`
- Check Python version (3.7+ required)

**DXF file won't open:**
- Verify file is valid DXF format
- Check file permissions
- Some complex DXF features may not be supported

**Snapping not working:**
- Ensure snap is enabled in the Snap Settings panel
- Adjust snap tolerance if needed
- Try zooming in for better precision

## Author

DXF Drawing Editor - A PyQt5 CAD Application
