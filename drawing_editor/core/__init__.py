"""Core module containing data models and business logic."""

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
from drawing_editor.core.commands import (
    Command,
    CommandManager,
    AddObjectCommand,
    RemoveObjectCommand,
    MoveObjectCommand,
    ModifyPropertyCommand,
)
from drawing_editor.core.layers import (
    Layer,
    LayerManager,
)
from drawing_editor.core.di_container import (
    ServiceContainer,
    Lazy,
    inject,
)
from drawing_editor.core.blocks import (
    BlockDefinition,
    BlockReference,
    BlockManager,
)

__all__ = [
    # Models
    "GraphicObject",
    "PointObject",
    "LineObject",
    "CircleObject",
    "RectObject",
    "ArcObject",
    "TextObject",
    "DimensionObject",
    # Commands
    "Command",
    "CommandManager",
    "AddObjectCommand",
    "RemoveObjectCommand",
    "MoveObjectCommand",
    "ModifyPropertyCommand",
    # Layers
    "Layer",
    "LayerManager",
    # DI
    "ServiceContainer",
    "Lazy",
    "inject",
    # Blocks
    "BlockDefinition",
    "BlockReference",
    "BlockManager",
]
