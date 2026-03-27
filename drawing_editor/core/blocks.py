"""
Blocks/Components system for reusable drawing elements.

This module provides functionality to create, store, and insert
reusable blocks (components) similar to CAD block references.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from PyQt5.QtCore import QPointF, QRectF


@dataclass
class BlockDefinition:
    """
    Defines a reusable block/component.

    Attributes:
        name: Unique block name
        objects: List of graphic objects that make up the block
        base_point: Insertion base point (QPointF)
        description: Optional description
        metadata: Additional metadata dictionary
    """

    name: str
    objects: List[Any] = field(default_factory=list)
    base_point: QPointF = field(default_factory=lambda: QPointF(0, 0))
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate block definition."""
        if not self.name or not self.name.strip():
            raise ValueError("Block name cannot be empty")

    @property
    def bounding_box(self) -> Optional[QRectF]:
        """Calculate the bounding box of all objects in the block."""
        if not self.objects:
            return None

        # Collect all points from objects
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for obj in self.objects:
            # Handle different object types
            if hasattr(obj, "x1") and hasattr(obj, "y1"):
                min_x = min(min_x, obj.x1)
                min_y = min(min_y, obj.y1)
                max_x = max(max_x, obj.x1)
                max_y = max(max_y, obj.y1)

            if hasattr(obj, "x2") and hasattr(obj, "y2"):
                min_x = min(min_x, obj.x2)
                min_y = min(min_y, obj.y2)
                max_x = max(max_x, obj.x2)
                max_y = max(max_y, obj.y2)

            if hasattr(obj, "cx") and hasattr(obj, "cy") and hasattr(obj, "radius"):
                min_x = min(min_x, obj.cx - obj.radius)
                min_y = min(min_y, obj.cy - obj.radius)
                max_x = max(max_x, obj.cx + obj.radius)
                max_y = max(max_y, obj.cy + obj.radius)

        if min_x == float("inf"):
            return None

        return QRectF(QPointF(min_x, min_y), QPointF(max_x, max_y))


@dataclass
class BlockReference:
    """
    A reference/instance of a block in the drawing.

    Attributes:
        block_def: Reference to the block definition
        position: Insert position (QPointF)
        scale_x: X scale factor
        scale_y: Y scale factor
        rotation: Rotation angle in degrees
        layer: Layer name for this reference
        attributes: Attribute overrides for this instance
    """

    block_def: BlockDefinition
    position: QPointF = field(default_factory=lambda: QPointF(0, 0))
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    layer: str = "0"
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def transformed_position(self) -> QPointF:
        """Get position after applying transformations."""
        return QPointF(
            self.position.x() * self.scale_x, self.position.y() * self.scale_y
        )


class BlockManager:
    """
    Manages block definitions and references in the drawing.

    Provides functionality to create, modify, delete, and insert blocks.
    Similar to the BLOCK command in traditional CAD software.

    Attributes:
        definitions: Dictionary of block name to BlockDefinition
        references: List of all BlockReference instances
    """

    def __init__(self) -> None:
        """Initialize the block manager."""
        self._definitions: Dict[str, BlockDefinition] = {}
        self._references: List[BlockReference] = []
        self._next_ref_id = 0

    @property
    def definitions(self) -> Dict[str, BlockDefinition]:
        """Get all block definitions."""
        return self._definitions.copy()

    @property
    def definition_names(self) -> List[str]:
        """Get list of all block definition names."""
        return list(self._definitions.keys())

    @property
    def references(self) -> List[BlockReference]:
        """Get all block references."""
        return self._references.copy()

    def add_definition(
        self,
        name: str,
        objects: List[Any],
        base_point: Optional[QPointF] = None,
        description: str = "",
    ) -> BlockDefinition:
        """
        Add a new block definition.

        Args:
            name: Unique name for the block
            objects: List of graphic objects in the block
            base_point: Base point for insertion (default: origin)
            description: Optional description

        Returns:
            The created BlockDefinition

        Raises:
            ValueError: If block with this name already exists
        """
        if name in self._definitions:
            raise ValueError(f"Block '{name}' already exists")

        definition = BlockDefinition(
            name=name,
            objects=objects,
            base_point=base_point if base_point else QPointF(0, 0),
            description=description,
        )
        self._definitions[name] = definition
        return definition

    def remove_definition(self, name: str, force: bool = False) -> bool:
        """
        Remove a block definition.

        Args:
            name: Name of the block to remove
            force: If True, also remove all references

        Returns:
            True if removed, False otherwise

        Raises:
            ValueError: If block has references and force=False
        """
        if name not in self._definitions:
            return False

        # Check for references
        refs_with_block = [r for r in self._references if r.block_def.name == name]

        if refs_with_block and not force:
            raise ValueError(
                f"Cannot remove block '{name}': {len(refs_with_block)} references exist. "
                "Use force=True to remove with references."
            )

        # Remove references if force
        if force:
            self._references = [r for r in self._references if r.block_def.name != name]

        del self._definitions[name]
        return True

    def get_definition(self, name: str) -> Optional[BlockDefinition]:
        """
        Get a block definition by name.

        Args:
            name: Block name

        Returns:
            BlockDefinition or None if not found
        """
        return self._definitions.get(name)

    def insert_reference(
        self,
        block_name: str,
        position: QPointF,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        rotation: float = 0.0,
        layer: str = "0",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[BlockReference]:
        """
        Insert a reference to a block at the specified position.

        Args:
            block_name: Name of the block to insert
            position: Insertion point
            scale_x: X scale factor
            scale_y: Y scale factor
            rotation: Rotation angle in degrees
            layer: Target layer
            attributes: Attribute overrides

        Returns:
            Created BlockReference or None if block not found
        """
        definition = self._definitions.get(block_name)
        if definition is None:
            return None

        reference = BlockReference(
            block_def=definition,
            position=position,
            scale_x=scale_x,
            scale_y=scale_y,
            rotation=rotation,
            layer=layer,
            attributes=attributes or {},
        )

        self._references.append(reference)
        self._next_ref_id += 1
        return reference

    def remove_reference(self, reference: BlockReference) -> bool:
        """
        Remove a block reference.

        Args:
            reference: The BlockReference to remove

        Returns:
            True if removed, False if not found
        """
        if reference in self._references:
            self._references.remove(reference)
            return True
        return False

    def update_reference(
        self,
        reference: BlockReference,
        position: Optional[QPointF] = None,
        scale_x: Optional[float] = None,
        scale_y: Optional[float] = None,
        rotation: Optional[float] = None,
        layer: Optional[str] = None,
    ) -> None:
        """
        Update properties of a block reference.

        Args:
            reference: The reference to update
            position: New position (if provided)
            scale_x: New X scale (if provided)
            scale_y: New Y scale (if provided)
            rotation: New rotation (if provided)
            layer: New layer (if provided)
        """
        if position is not None:
            reference.position = position
        if scale_x is not None:
            reference.scale_x = scale_x
        if scale_y is not None:
            reference.scale_y = scale_y
        if rotation is not None:
            reference.rotation = rotation
        if layer is not None:
            reference.layer = layer

    def explode_reference(
        self, reference: BlockReference, transform_objects: bool = True
    ) -> List[Any]:
        """
        Explode a block reference into its constituent objects.

        Args:
            reference: The BlockReference to explode
            transform_objects: If True, apply position/scale/rotation transforms

        Returns:
            List of objects from the exploded block

        Note:
            This removes the reference after exploding.
        """
        objects = []

        for obj in reference.block_def.objects:
            if transform_objects:
                # Create transformed copy of object
                transformed = self._transform_object(obj, reference)
                objects.append(transformed)
            else:
                objects.append(obj)

        # Remove the reference
        self.remove_reference(reference)

        return objects

    def _transform_object(self, obj: Any, reference: BlockReference) -> Any:
        """
        Apply transformations to an object based on reference properties.

        Args:
            obj: Object to transform
            reference: BlockReference with transformation data

        Returns:
            Transformed copy of the object
        """
        import math

        # Create a copy with transformed coordinates
        # This is simplified - actual implementation would need
        # to handle each object type specifically

        if hasattr(obj, "__class__"):
            # Get class and create new instance with transformed coords
            obj_type = obj.__class__.__name__

            # For now, just return original (full implementation would
            # properly transform each coordinate)
            return obj

        return obj

    def get_references_by_block(self, block_name: str) -> List[BlockReference]:
        """
        Get all references to a specific block.

        Args:
            block_name: Name of the block

        Returns:
            List of BlockReferences
        """
        return [r for r in self._references if r.block_def.name == block_name]

    def count_references(self, block_name: str) -> int:
        """
        Count how many times a block is referenced.

        Args:
            block_name: Name of the block

        Returns:
            Number of references
        """
        return len(self.get_references_by_block(block_name))

    def rename_definition(self, old_name: str, new_name: str) -> bool:
        """
        Rename a block definition.

        Args:
            old_name: Current name
            new_name: New name

        Returns:
            True if renamed, False if failed

        Raises:
            KeyError: If old name doesn't exist
            ValueError: If new name already exists
        """
        if old_name not in self._definitions:
            raise KeyError(f"Block '{old_name}' does not exist")

        if new_name in self._definitions:
            raise ValueError(f"Block '{new_name}' already exists")

        # Get and update definition
        definition = self._definitions[old_name]
        definition.name = new_name

        # Update dictionary
        self._definitions[new_name] = definition
        del self._definitions[old_name]

        # Update all references
        for ref in self._references:
            if ref.block_def.name == old_name:
                ref.block_def = definition

        return True

    def export_blocks(self) -> Dict[str, Any]:
        """
        Export block definitions to a dictionary for serialization.

        Returns:
            Dictionary containing block data
        """
        return {
            "definitions": {
                name: {
                    "name": defn.name,
                    "base_point": {"x": defn.base_point.x(), "y": defn.base_point.y()},
                    "description": defn.description,
                    "metadata": defn.metadata,
                    # Note: objects would need special serialization
                    "object_count": len(defn.objects),
                }
                for name, defn in self._definitions.items()
            },
            "references": [
                {
                    "block_name": ref.block_def.name,
                    "position": {"x": ref.position.x(), "y": ref.position.y()},
                    "scale_x": ref.scale_x,
                    "scale_y": ref.scale_y,
                    "rotation": ref.rotation,
                    "layer": ref.layer,
                    "attributes": ref.attributes,
                }
                for ref in self._references
            ],
        }

    def clear_all(self) -> None:
        """Remove all block definitions and references."""
        self._definitions.clear()
        self._references.clear()
        self._next_ref_id = 0
