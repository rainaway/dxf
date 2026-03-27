"""
Layer management system for the drawing editor.

This module provides layer functionality similar to professional CAD applications,
allowing users to organize objects into named layers with visibility and lock controls.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from PyQt5.QtGui import QColor, QPen


@dataclass
class Layer:
    """
    Represents a drawing layer with properties.

    Attributes:
        name: Unique layer name
        visible: Whether objects on this layer are visible
        locked: Whether objects on this layer can be edited
        color: Default color for objects on this layer
        line_weight: Default line weight for objects on this layer
        line_type: Default line type for objects on this layer
        frozen: Whether the layer is frozen (not displayed/regenerated)
        printable: Whether objects on this layer print
    """

    name: str
    visible: bool = True
    locked: bool = False
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    line_weight: float = 0.25
    line_type: str = "Continuous"
    frozen: bool = False
    printable: bool = True

    def __post_init__(self) -> None:
        """Validate layer properties after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Layer name cannot be empty")

    @property
    def is_editable(self) -> bool:
        """Check if the layer allows editing."""
        return self.visible and not self.locked and not self.frozen


class LayerManager:
    """
    Manages layers in the drawing editor.

    Provides functionality to create, delete, modify, and query layers.
    Also tracks which objects belong to which layers.

    Attributes:
        layers: Dictionary of layer name to Layer objects
        current_layer: Name of the currently active layer
        object_layers: Mapping of object IDs to layer names
    """

    DEFAULT_LAYER_NAME = "0"

    def __init__(self) -> None:
        """Initialize the layer manager with a default layer."""
        self._layers: Dict[str, Layer] = {}
        self._current_layer: str = self.DEFAULT_LAYER_NAME
        self._object_layers: Dict[int, str] = {}  # object id -> layer name
        self._layer_order: List[str] = []  # Maintain layer order

        # Create default layer
        self.add_layer(self.DEFAULT_LAYER_NAME)

    @property
    def layers(self) -> Dict[str, Layer]:
        """Get all layers."""
        return self._layers.copy()

    @property
    def layer_names(self) -> List[str]:
        """Get list of all layer names in order."""
        return self._layer_order.copy()

    @property
    def current_layer(self) -> str:
        """Get the current active layer name."""
        return self._current_layer

    @current_layer.setter
    def current_layer(self, name: str) -> None:
        """
        Set the current active layer.

        Args:
            name: Name of the layer to make current

        Raises:
            KeyError: If the layer doesn't exist
        """
        if name not in self._layers:
            raise KeyError(f"Layer '{name}' does not exist")
        self._current_layer = name

    @property
    def current_layer_obj(self) -> Layer:
        """Get the current active layer object."""
        return self._layers[self._current_layer]

    def add_layer(
        self,
        name: str,
        color: Optional[QColor] = None,
        line_weight: float = 0.25,
        line_type: str = "Continuous",
    ) -> Layer:
        """
        Add a new layer.

        Args:
            name: Unique name for the layer
            color: Default color (default: black)
            line_weight: Default line weight (default: 0.25mm)
            line_type: Default line type (default: Continuous)

        Returns:
            The created Layer object

        Raises:
            ValueError: If a layer with this name already exists
        """
        if name in self._layers:
            raise ValueError(f"Layer '{name}' already exists")

        layer = Layer(
            name=name,
            color=color if color else QColor(0, 0, 0),
            line_weight=line_weight,
            line_type=line_type,
        )
        self._layers[name] = layer
        self._layer_order.append(name)
        return layer

    def remove_layer(self, name: str, force: bool = False) -> bool:
        """
        Remove a layer.

        Args:
            name: Name of the layer to remove
            force: If True, reassign objects to default layer instead of failing

        Returns:
            True if layer was removed, False otherwise

        Raises:
            ValueError: If trying to remove the default layer or layer has objects
        """
        if name == self.DEFAULT_LAYER_NAME:
            raise ValueError("Cannot remove the default layer")

        if name not in self._layers:
            return False

        # Check for objects on this layer
        objects_on_layer = [
            obj_id for obj_id, layer in self._object_layers.items() if layer == name
        ]

        if objects_on_layer and not force:
            raise ValueError(
                f"Cannot remove layer '{name}': {len(objects_on_layer)} objects on this layer. "
                "Use force=True to reassign objects to default layer."
            )

        # Reassign objects to default layer if force
        if force:
            for obj_id in objects_on_layer:
                self._object_layers[obj_id] = self.DEFAULT_LAYER_NAME

        # Remove layer
        del self._layers[name]
        self._layer_order.remove(name)

        # Update current layer if needed
        if self._current_layer == name:
            self._current_layer = self.DEFAULT_LAYER_NAME

        return True

    def get_layer(self, name: str) -> Optional[Layer]:
        """
        Get a layer by name.

        Args:
            name: Layer name

        Returns:
            Layer object or None if not found
        """
        return self._layers.get(name)

    def set_layer_property(self, name: str, property_name: str, value: Any) -> bool:
        """
        Set a property on a layer.

        Args:
            name: Layer name
            property_name: Property to set (visible, locked, color, etc.)
            value: New value for the property

        Returns:
            True if property was set, False if layer not found
        """
        layer = self._layers.get(name)
        if layer is None:
            return False

        if not hasattr(layer, property_name):
            raise AttributeError(f"Layer has no property '{property_name}'")

        setattr(layer, property_name, value)
        return True

    def assign_object_to_layer(self, obj_id: int, layer_name: str) -> bool:
        """
        Assign an object to a layer.

        Args:
            obj_id: Unique identifier of the object (use id(obj))
            layer_name: Name of the layer to assign to

        Returns:
            True if assignment succeeded, False if layer not found
        """
        if layer_name not in self._layers:
            return False

        self._object_layers[obj_id] = layer_name
        return True

    def get_object_layer(self, obj_id: int) -> Optional[str]:
        """
        Get the layer name for an object.

        Args:
            obj_id: Object identifier

        Returns:
            Layer name or None if object not assigned
        """
        return self._object_layers.get(obj_id)

    def get_objects_on_layer(self, layer_name: str) -> List[int]:
        """
        Get all object IDs on a specific layer.

        Args:
            layer_name: Layer name to query

        Returns:
            List of object IDs on the layer
        """
        return [
            obj_id
            for obj_id, layer in self._object_layers.items()
            if layer == layer_name
        ]

    def move_object_to_layer(
        self,
        obj_id: int,
        target_layer: str,
        update_graphics_item: Optional[callable] = None,
    ) -> bool:
        """
        Move an object from one layer to another.

        Args:
            obj_id: Object identifier
            target_layer: Target layer name
            update_graphics_item: Optional callback to update graphics item appearance

        Returns:
            True if move succeeded, False otherwise
        """
        if target_layer not in self._layers:
            return False

        old_layer = self._object_layers.get(obj_id, self.DEFAULT_LAYER_NAME)
        if old_layer == target_layer:
            return True  # Already on target layer

        self._object_layers[obj_id] = target_layer

        # Update graphics item if callback provided
        if update_graphics_item:
            target_layer_obj = self._layers[target_layer]
            update_graphics_item(obj_id, target_layer_obj)

        return True

    def toggle_layer_visibility(self, name: str) -> Optional[bool]:
        """
        Toggle visibility of a layer.

        Args:
            name: Layer name

        Returns:
            New visibility state or None if layer not found
        """
        layer = self._layers.get(name)
        if layer is None:
            return None

        layer.visible = not layer.visible
        return layer.visible

    def toggle_layer_lock(self, name: str) -> Optional[bool]:
        """
        Toggle lock state of a layer.

        Args:
            name: Layer name

        Returns:
            New lock state or None if layer not found
        """
        layer = self._layers.get(name)
        if layer is None:
            return None

        layer.locked = not layer.locked
        return layer.locked

    def freeze_layer(self, name: str) -> bool:
        """Freeze a layer."""
        return self.set_layer_property(name, "frozen", True)

    def thaw_layer(self, name: str) -> bool:
        """Thaw (unfreeze) a layer."""
        return self.set_layer_property(name, "frozen", False)

    def get_visible_layers(self) -> List[str]:
        """Get list of all visible, non-frozen layers."""
        return [
            name
            for name, layer in self._layers.items()
            if layer.visible and not layer.frozen
        ]

    def get_editable_layers(self) -> List[str]:
        """Get list of all editable layers (visible, not locked, not frozen)."""
        return [name for name, layer in self._layers.items() if layer.is_editable]

    def rename_layer(self, old_name: str, new_name: str) -> bool:
        """
        Rename a layer.

        Args:
            old_name: Current layer name
            new_name: New layer name

        Returns:
            True if renamed, False if failed

        Raises:
            ValueError: If new name already exists or is invalid
            KeyError: If old name doesn't exist
        """
        if old_name not in self._layers:
            raise KeyError(f"Layer '{old_name}' does not exist")

        if new_name in self._layers:
            raise ValueError(f"Layer '{new_name}' already exists")

        if not new_name or not new_name.strip():
            raise ValueError("Layer name cannot be empty")

        # Get layer and update name
        layer = self._layers[old_name]
        layer.name = new_name

        # Update dictionary
        self._layers[new_name] = layer
        del self._layers[old_name]

        # Update order list
        idx = self._layer_order.index(old_name)
        self._layer_order[idx] = new_name

        # Update current layer reference
        if self._current_layer == old_name:
            self._current_layer = new_name

        # Update object layer assignments
        for obj_id, layer_name in self._object_layers.items():
            if layer_name == old_name:
                self._object_layers[obj_id] = new_name

        return True

    def clear_all_layers(self) -> None:
        """Remove all custom layers, keeping only the default layer."""
        self._layers.clear()
        self._object_layers.clear()
        self._layer_order.clear()
        self._current_layer = self.DEFAULT_LAYER_NAME
        self.add_layer(self.DEFAULT_LAYER_NAME)

    def export_layers(self) -> Dict[str, Any]:
        """
        Export layer configuration to a dictionary.

        Returns:
            Dictionary containing layer data for serialization
        """
        return {
            "layers": {
                name: {
                    "visible": layer.visible,
                    "locked": layer.locked,
                    "color": layer.color.name(),
                    "line_weight": layer.line_weight,
                    "line_type": layer.line_type,
                    "frozen": layer.frozen,
                    "printable": layer.printable,
                }
                for name, layer in self._layers.items()
            },
            "current_layer": self._current_layer,
            "object_layers": self._object_layers.copy(),
            "layer_order": self._layer_order.copy(),
        }

    def import_layers(self, data: Dict[str, Any]) -> None:
        """
        Import layer configuration from a dictionary.

        Args:
            data: Dictionary containing layer data from export_layers()
        """
        self.clear_all_layers()

        # Recreate layers
        layers_data = data.get("layers", {})
        for name, props in layers_data.items():
            color = QColor(props.get("color", "#000000"))
            self.add_layer(
                name=name,
                color=color,
                line_weight=props.get("line_weight", 0.25),
                line_type=props.get("line_type", "Continuous"),
            )
            # Set additional properties
            if name in self._layers:
                layer = self._layers[name]
                layer.visible = props.get("visible", True)
                layer.locked = props.get("locked", False)
                layer.frozen = props.get("frozen", False)
                layer.printable = props.get("printable", True)

        # Restore state
        self._current_layer = data.get("current_layer", self.DEFAULT_LAYER_NAME)
        self._object_layers = data.get("object_layers", {}).copy()
        self._layer_order = data.get("layer_order", [self.DEFAULT_LAYER_NAME])
