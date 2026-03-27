# Improvements Made to DXF Drawing Editor

## 1. Fixed PDF Export (Empty Page Issue)

**Problem**: The PDF export was producing blank pages.

**Solution**: 
- Modified  method to properly calculate the bounding box excluding the paper border
- Added proper scaling calculation with margins (20mm on each side)
- Changed rendering to draw individual items instead of using 
- The export now respects the selected paper size and orientation

## 2. Added Paper Size Support (A0-A4)

**New Features**:
- Added  dictionary with ISO 216 standard paper sizes:
  - A0: 841×1189 mm
  - A1: 594×841 mm
  - A2: 420×594 mm
  - A3: 297×420 mm
  - A4: 210×297 mm

- Added paper settings UI in the right dock panel:
  - Paper size dropdown (A0-A4)
  - Orientation dropdown (Landscape/Portrait)

- Added  method that:
  - Sets the scene rectangle to match the selected paper size
  - Draws a dashed border showing the paper boundaries
  - Updates the status bar with current paper settings

- Paper border is automatically excluded from export

## 3. Enhanced Object Snaps (AutoCAD-style)

**Added New Snap Types**:

1. **Midpoint Snap** ():
   - Snaps to the middle of lines
   - Snaps to the middle of rectangle edges (all 4 sides)

2. **Intersection Snap** ():
   - Detects line-line intersections
   - Detects line-rectangle edge intersections
   - Only shows intersections near the cursor (< 50 units)

3. **Tangent Snap** ():
   - Snaps to tangent points on circles
   - Snaps to tangent points on arcs
   - Calculates tangent point from mouse position to circle/arc center

4. **Perpendicular Snap** ():
   - Projects perpendicular point onto lines
   - Projects perpendicular point onto rectangle edges
   - Clamps to segment bounds

**Enhanced Existing Snaps**:
- **Endpoint Snap**: Now also works with Arc objects (start and end points)

**UI Changes**:
- Added checkboxes for all snap types in the Settings panel:
  - Snap to endpoints
  - Snap to centers
  - Snap to midpoints
  - Snap to intersections
  - Snap to tangent
  - Snap to perpendicular

**Implementation Details**:
- Added helper methods to :
  - : Calculate tangent point on circle/arc
  - : Project point perpendicular to line/edge
  - : Find nearby intersection points
  - : Get intersections between two items
  - : Calculate line segment intersection

## 4. Code Structure Improvements

- Added  import for future use
- Added  import (available for future page setup features)
- Improved separation of concerns in export functionality
- Better organization of snap-related code

## Usage

### Changing Paper Size
1. Open the Settings panel (right dock)
2. In "Paper Settings" group:
   - Select paper size (A0-A4) from dropdown
   - Select orientation (Landscape/Portrait)
3. The drawing area will update to show the new paper boundaries

### Using Object Snaps
1. Open the Settings panel (right dock)
2. In "Snap Settings" group, enable desired snaps:
   - Endpoints: Snap to line/arc endpoints and rectangle vertices
   - Centers: Snap to circle centers
   - Midpoints: Snap to line and rectangle edge midpoints
   - Intersections: Snap to where lines cross
   - Tangent: Snap to tangent points on circles/arcs
   - Perpendicular: Snap perpendicular to lines/edges
3. When drawing, the cursor will automatically snap to these points with a hint label

### Exporting to PDF
1. Create your drawing within the paper boundaries
2. Click "Export PDF" from the toolbar
3. Select file location
4. The PDF will be generated with:
   - The selected paper size (A0-A4)
   - The selected orientation
   - Proper scaling to fit the drawing with margins
   - Only drawing objects (paper border excluded)
