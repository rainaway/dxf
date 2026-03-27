"""
Logging configuration for the drawing editor.

This module provides centralized logging setup and utilities for consistent
logging across the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format with timestamp, level, logger name, and message
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Format for file logs (more detailed)
FILE_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    Get or create a logger with the specified configuration.

    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (default: INFO)
        log_file: Optional path to log file
        console_output: Whether to output to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create formatter
    console_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_formatter = logging.Formatter(FILE_LOG_FORMAT)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def setup_global_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
) -> None:
    """
    Set up global logging configuration for the entire application.

    This configures the root logger which affects all loggers that
    don't have their own configuration.

    Args:
        level: Global logging level
        log_file: Optional path to log file
        log_format: Log format string
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(FILE_LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


class LoggingContext:
    """
    Context manager for temporary logging configuration.

    Useful for test scenarios or specific operations that need
    different logging settings.

    Example:
        with LoggingContext(level=logging.DEBUG, log_file='temp.log'):
            # Operations with debug logging
            pass
    """

    def __init__(
        self,
        level: int = logging.DEBUG,
        log_file: Optional[str] = None,
        console_output: bool = True,
    ) -> None:
        """
        Initialize logging context.

        Args:
            level: Temporary logging level
            log_file: Temporary log file path
            console_output: Whether to output to console
        """
        self._level = level
        self._log_file = log_file
        self._console_output = console_output
        self._old_handlers: list = []
        self._old_level: int = logging.INFO

    def __enter__(self) -> "LoggingContext":
        """Enter context and apply temporary logging configuration."""
        root_logger = logging.getLogger()

        # Save current state
        self._old_level = root_logger.level
        self._old_handlers = root_logger.handlers.copy()

        # Clear and reconfigure
        root_logger.handlers.clear()
        root_logger.setLevel(self._level)

        # Console handler
        if self._console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._level)
            console_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
            root_logger.addHandler(console_handler)

        # File handler
        if self._log_file:
            log_path = Path(self._log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self._log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
            root_logger.addHandler(file_handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore previous logging configuration."""
        root_logger = logging.getLogger()

        # Restore previous state
        root_logger.handlers.clear()
        for handler in self._old_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(self._old_level)


def log_method_call(logger: Optional[logging.Logger] = None):
    """
    Decorator to log method calls and execution time.

    Args:
        logger: Logger to use (if None, creates one based on module)

    Returns:
        Decorated function
    """
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            func_name = f"{func.__qualname__}"
            logger.debug(f"Calling {func_name}")

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.debug(f"{func_name} completed in {elapsed:.4f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{func_name} failed after {elapsed:.4f}s: {e}")
                raise

        return wrapper

    return decorator


# Common exception types for the drawing editor
class DrawingEditorError(Exception):
    """Base exception for drawing editor errors."""

    pass


class LayerError(DrawingEditorError):
    """Exception raised for layer-related errors."""

    pass


class CommandError(DrawingEditorError):
    """Exception raised for command-related errors."""

    pass


class SnapError(DrawingEditorError):
    """Exception raised for snapping-related errors."""

    pass


class FileIOError(DrawingEditorError):
    """Exception raised for file I/O errors."""

    pass


class ValidationError(DrawingEditorError):
    """Exception raised for validation errors."""

    pass


def handle_exception(
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
    default_return: Optional[any] = None,
):
    """
    Decorator to handle exceptions in methods with logging.

    Args:
        logger: Logger to use (if None, creates one based on module)
        reraise: Whether to re-raise the exception after logging
        default_return: Value to return if exception is caught and not re-raised

    Returns:
        Decorated function
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in {func.__qualname__}: {e}")
                if reraise:
                    raise
                return default_return

        return wrapper

    return decorator
