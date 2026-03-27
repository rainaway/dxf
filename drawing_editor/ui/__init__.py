"""UI module containing all PyQt5 widgets and dialogs."""

from drawing_editor.ui.graphics_items import (
    GraphicsPoint,
    GraphicsLine,
    GraphicsCircle,
    GraphicsRect,
    GraphicsArc,
    GraphicsText,
    GraphicsDimension,
)
from drawing_editor.ui.cad_view import CadView
from drawing_editor.ui.main_window import CadWindow
from drawing_editor.ui.dialogs import PropertyDialog

__all__ = [
    "GraphicsPoint",
    "GraphicsLine",
    "GraphicsCircle",
    "GraphicsRect",
    "GraphicsArc",
    "GraphicsText",
    "GraphicsDimension",
    "CadView",
    "CadWindow",
    "PropertyDialog",
]
