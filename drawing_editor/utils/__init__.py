"""Utils module containing utility functions and helpers."""

from drawing_editor.utils.math_utils import (
    calculate_distance,
    normalize_vector,
    rotate_point,
    calculate_angle,
)
from drawing_editor.utils.logger import (
    get_logger,
    setup_global_logging,
    LoggingContext,
    log_method_call,
    handle_exception,
    DrawingEditorError,
    LayerError,
    CommandError,
    SnapError,
    FileIOError,
    ValidationError,
)

__all__ = [
    # Math utilities
    "calculate_distance",
    "normalize_vector",
    "rotate_point",
    "calculate_angle",
    # Logging utilities
    "get_logger",
    "setup_global_logging",
    "LoggingContext",
    "log_method_call",
    "handle_exception",
    # Exceptions
    "DrawingEditorError",
    "LayerError",
    "CommandError",
    "SnapError",
    "FileIOError",
    "ValidationError",
]
