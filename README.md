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
python drawing_editor.py
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
├── drawing_editor.py    # Main application code
├── run_editor.bat       # Windows batch launcher
└── README.md            # This file
```

## Code Architecture

The application follows an MVC-like architecture:

### Data Models (`drawing_editor.py`)
- `GraphicObject`: Base class for all graphic objects
- `PointObject`, `LineObject`, `CircleObject`, etc.: Specific shape models
- `DimensionObject`: Dimension annotation model

### Graphics Items (PyQt5 Visual Layer)
- `GraphicsPoint`, `GraphicsLine`, `GraphicsCircle`, etc.: Qt graphics items
- `GraphicsDimension`: Complex dimension rendering
- All items support selection, movement, and style updates

### Managers
- `SnapManager`: Handles object snapping logic
- `CadView`: Custom QGraphicsView with drawing tools

### Main Window
- `CadWindow`: Main application window with:
  - Toolbar with drawing/editing tools
  - Graphics view canvas
  - Object list panel
  - Properties editor
  - Snap settings panel

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
