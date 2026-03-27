"""
Command pattern implementation for undo/redo functionality.

This module provides the command pattern infrastructure for supporting
undoable and redoable operations in the drawing editor.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal


class ICommand(Protocol):
    """Protocol defining the interface for all commands."""

    def execute(self) -> None:
        """Execute the command."""
        ...

    def undo(self) -> None:
        """Undo the command."""
        ...

    def redo(self) -> None:
        """Redo the command (typically same as execute)."""
        ...


class Command(QObject):
    """
    Abstract base class for all commands in the editor.

    Each command encapsulates an operation that can be executed, undone,
    and redone. Commands should store all necessary state to perform
    these operations.

    Signals:
        executed: Emitted when command is successfully executed
        undone: Emitted when command is successfully undone
    """

    executed = pyqtSignal(object)  # Emits command instance
    undone = pyqtSignal(object)  # Emits command instance

    def __init__(self, name: str = "Command") -> None:
        """
        Initialize the command.

        Args:
            name: Human-readable name for the command (for UI display)
        """
        super().__init__()
        self._name = name
        self._executed = False

    @property
    def name(self) -> str:
        """Return the command name."""
        return self._name

    @abstractmethod
    def execute(self) -> None:
        """
        Execute the command.

        This method should perform the actual operation and store any
        state needed for undo/redo.
        """
        pass

    @abstractmethod
    def undo(self) -> None:
        """
        Undo the command.

        This method should reverse the effect of execute(), restoring
        the application state to before the command was executed.
        """
        pass

    def redo(self) -> None:
        """
        Redo the command.

        By default, this calls execute(). Subclasses can override if
        different behavior is needed for redo vs execute.
        """
        self.execute()

    @property
    def is_executed(self) -> bool:
        """Check if the command has been executed."""
        return self._executed

    def _mark_executed(self) -> None:
        """Mark the command as executed and emit signal."""
        self._executed = True
        self.executed.emit(self)

    def _mark_undone(self) -> None:
        """Mark the command as undone and emit signal."""
        self._executed = False
        self.undone.emit(self)


class AddObjectCommand(Command):
    """
    Command to add a graphic object to the scene.

    Attributes:
        scene: The graphics scene to add the object to
        obj: The graphic object to add
        graphics_item: The associated graphics item
    """

    def __init__(
        self, scene: Any, obj: Any, graphics_item: Any, name: str = "Add Object"
    ) -> None:
        """
        Initialize the add object command.

        Args:
            scene: The QGraphicsScene to add the object to
            obj: The GraphicObject model instance
            graphics_item: The QGraphicsItem for rendering
            name: Command name for UI
        """
        super().__init__(name)
        self._scene = scene
        self._obj = obj
        self._graphics_item = graphics_item
        self._obj_map: Optional[Dict] = None

    def execute(self) -> None:
        """Add the object to the scene."""
        if self._obj_map is not None:
            self._obj_map[self._obj] = type(
                "ObjRef", (), {"graphics_item": self._graphics_item}
            )()
        self._scene.addItem(self._graphics_item)
        self._mark_executed()

    def undo(self) -> None:
        """Remove the object from the scene."""
        self._scene.removeItem(self._graphics_item)
        if self._obj_map is not None and self._obj in self._obj_map:
            del self._obj_map[self._obj]
        self._mark_undone()


class RemoveObjectCommand(Command):
    """
    Command to remove a graphic object from the scene.

    Stores the object's state so it can be restored on undo.
    """

    def __init__(
        self,
        scene: Any,
        obj: Any,
        graphics_item: Any,
        obj_map: Optional[Dict] = None,
        name: str = "Remove Object",
    ) -> None:
        """
        Initialize the remove object command.

        Args:
            scene: The QGraphicsScene
            obj: The GraphicObject model instance
            graphics_item: The QGraphicsItem to remove
            obj_map: Optional reference to object mapping dictionary
            name: Command name for UI
        """
        super().__init__(name)
        self._scene = scene
        self._obj = obj
        self._graphics_item = graphics_item
        self._obj_map = obj_map
        self._was_selected = graphics_item.isSelected() if graphics_item else False

    def execute(self) -> None:
        """Remove the object from the scene."""
        self._scene.removeItem(self._graphics_item)
        if self._obj_map is not None and self._obj in self._obj_map:
            del self._obj_map[self._obj]
        self._mark_executed()

    def undo(self) -> None:
        """Restore the object to the scene."""
        self._scene.addItem(self._graphics_item)
        if self._obj_map is not None:
            self._obj_map[self._obj] = type(
                "ObjRef", (), {"graphics_item": self._graphics_item}
            )()
        if self._was_selected:
            self._graphics_item.setSelected(True)
        self._mark_undone()


class MoveObjectCommand(Command):
    """
    Command to move a graphic object by a delta.

    Stores the original position for undo functionality.
    """

    def __init__(
        self,
        graphics_item: Any,
        delta_x: float,
        delta_y: float,
        name: str = "Move Object",
    ) -> None:
        """
        Initialize the move object command.

        Args:
            graphics_item: The QGraphicsItem to move
            delta_x: Horizontal displacement
            delta_y: Vertical displacement
            name: Command name for UI
        """
        super().__init__(name)
        self._graphics_item = graphics_item
        self._delta_x = delta_x
        self._delta_y = delta_y
        self._original_pos: Optional[Any] = None

    def execute(self) -> None:
        """Move the object by the delta."""
        if self._original_pos is None:
            self._original_pos = self._graphics_item.pos()
        self._graphics_item.moveBy(self._delta_x, self._delta_y)
        self._mark_executed()

    def undo(self) -> None:
        """Move the object back to its original position."""
        if self._original_pos is not None:
            self._graphics_item.setPos(self._original_pos)
        self._mark_undone()


class ModifyPropertyCommand(Command):
    """
    Command to modify a property of a graphic object.

    Supports modifying any named property with old/new value tracking.
    """

    def __init__(
        self,
        obj: Any,
        property_name: str,
        old_value: Any,
        new_value: Any,
        name: str = "Modify Property",
    ) -> None:
        """
        Initialize the modify property command.

        Args:
            obj: The object whose property will be modified
            property_name: Name of the property to change
            old_value: The current/old value
            new_value: The new value to set
            name: Command name for UI
        """
        super().__init__(name)
        self._obj = obj
        self._property_name = property_name
        self._old_value = old_value
        self._new_value = new_value

    def execute(self) -> None:
        """Set the property to the new value."""
        setattr(self._obj, self._property_name, self._new_value)
        self._mark_executed()

    def undo(self) -> None:
        """Restore the property to its old value."""
        setattr(self._obj, self._property_name, self._old_value)
        self._mark_undone()


class CommandManager:
    """
    Manages command execution, undo, and redo operations.

    Maintains two stacks: one for executed commands (undo stack)
    and one for undone commands (redo stack). Provides methods
    to execute commands and navigate the history.

    Attributes:
        max_history: Maximum number of commands to keep in history
        undo_stack: Stack of executed commands
        redo_stack: Stack of undone commands
    """

    def __init__(self, max_history: int = 100) -> None:
        """
        Initialize the command manager.

        Args:
            max_history: Maximum commands to retain in undo history
        """
        self._max_history = max_history
        self._undo_stack: deque[Command] = deque(maxlen=max_history)
        self._redo_stack: deque[Command] = deque(maxlen=max_history)
        self._is_undoing = False

    @property
    def can_undo(self) -> bool:
        """Check if there are commands that can be undone."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Check if there are commands that can be redone."""
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        """Return the number of commands in the undo stack."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Return the number of commands in the redo stack."""
        return len(self._redo_stack)

    def execute(self, command: Command) -> None:
        """
        Execute a command and add it to the undo stack.

        Executing a new command clears the redo stack, as the
        redo history is no longer valid after a new action.

        Args:
            command: The command to execute
        """
        # Clear redo stack when new command is executed
        self._redo_stack.clear()

        command.execute()
        self._undo_stack.append(command)

    def undo(self) -> Optional[Command]:
        """
        Undo the last executed command.

        Returns:
            The command that was undone, or None if no commands to undo
        """
        if not self.can_undo:
            return None

        command = self._undo_stack.pop()
        self._is_undoing = True
        try:
            command.undo()
        finally:
            self._is_undoing = False

        self._redo_stack.append(command)
        return command

    def redo(self) -> Optional[Command]:
        """
        Redo the last undone command.

        Returns:
            The command that was redone, or None if no commands to redo
        """
        if not self.can_redo:
            return None

        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        return command

    def clear_history(self) -> None:
        """Clear both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_undo_command_name(self, index: int = 0) -> Optional[str]:
        """
        Get the name of a command in the undo stack.

        Args:
            index: Index from the top of the stack (0 = most recent)

        Returns:
            Command name or None if index is out of range
        """
        if index < 0 or index >= len(self._undo_stack):
            return None
        # Convert to list to access by index (deque doesn't support negative indexing well)
        undo_list = list(self._undo_stack)
        return undo_list[-(index + 1)].name

    def get_redo_command_name(self, index: int = 0) -> Optional[str]:
        """
        Get the name of a command in the redo stack.

        Args:
            index: Index from the top of the stack (0 = most recent)

        Returns:
            Command name or None if index is out of range
        """
        if index < 0 or index >= len(self._redo_stack):
            return None
        redo_list = list(self._redo_stack)
        return redo_list[-(index + 1)].name
