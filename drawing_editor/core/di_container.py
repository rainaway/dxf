"""
Dependency Injection container for the drawing editor.

This module provides a simple DI container for managing dependencies
and promoting loose coupling between components.
"""

from typing import Any, Dict, Optional, Type, TypeVar, Callable, Generic
from contextlib import contextmanager

T = TypeVar("T")


class ServiceContainer:
    """
    A simple dependency injection container.

    Provides registration and resolution of services with support for
    singleton and transient lifetimes.

    Example:
        container = ServiceContainer()
        container.register(SnapManager, lambda c: SnapManager())
        container.register(CommandManager, lifetime='singleton')

        snap_mgr = container.resolve(SnapManager)
        cmd_mgr = container.resolve(CommandManager)
    """

    def __init__(self) -> None:
        """Initialize the service container."""
        self._services: Dict[type, Dict[str, Any]] = {}
        self._instances: Dict[type, Any] = {}
        self._factories: Dict[type, Callable[["ServiceContainer"], Any]] = {}
        self._lifetimes: Dict[type, str] = {}  # 'singleton' or 'transient'

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Callable[["ServiceContainer"], T]] = None,
        lifetime: str = "singleton",
    ) -> None:
        """
        Register a service type with the container.

        Args:
            service_type: The type/interface being registered
            implementation: Factory function that creates the service instance.
                          If None, assumes service_type can be instantiated directly.
            lifetime: 'singleton' for single instance, 'transient' for new instance each time
        """
        if implementation is None:
            implementation = lambda c: service_type()

        self._factories[service_type] = implementation
        self._lifetimes[service_type] = lifetime

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register an existing instance as a singleton.

        Args:
            service_type: The type to register the instance as
            instance: The actual instance to return when resolving
        """
        self._instances[service_type] = instance
        self._lifetimes[service_type] = "singleton"

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service by type.

        For singletons, returns the cached instance (creating if needed).
        For transients, creates a new instance each time.

        Args:
            service_type: The type of service to resolve

        Returns:
            An instance of the requested service type

        Raises:
            KeyError: If the service type is not registered
        """
        # Check for pre-registered instance
        if service_type in self._instances:
            return self._instances[service_type]

        # Check if service is registered
        if service_type not in self._factories:
            raise KeyError(f"Service {service_type} is not registered")

        # Return cached singleton if available
        if self._lifetimes.get(service_type) == "singleton":
            if service_type not in self._instances:
                factory = self._factories[service_type]
                self._instances[service_type] = factory(self)
            return self._instances[service_type]

        # Create transient instance
        factory = self._factories[service_type]
        return factory(self)

    def get(self, service_type: Type[T], default: Optional[T] = None) -> Optional[T]:
        """
        Resolve a service, returning default if not found.

        Args:
            service_type: The type of service to resolve
            default: Value to return if service is not registered

        Returns:
            Resolved service or default value
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return default

    def is_registered(self, service_type: type) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: The type to check

        Returns:
            True if the service is registered, False otherwise
        """
        return service_type in self._factories or service_type in self._instances

    def clear(self) -> None:
        """Clear all registered services and instances."""
        self._services.clear()
        self._instances.clear()
        self._factories.clear()
        self._lifetimes.clear()

    @contextmanager
    def scoped(self):
        """
        Create a scoped context where new instances are created.

        Useful for testing or scenarios where you want isolated instances.
        """
        old_instances = self._instances.copy()
        try:
            self._instances.clear()
            yield self
        finally:
            self._instances = old_instances


class Lazy(Generic[T]):
    """
    Lazy initialization wrapper for services.

    Defers creation of a service until it's first accessed.

    Example:
        lazy_snap = Lazy(container, SnapManager)
        # SnapManager not created yet
        snap = lazy_snap.value  # Now it's created
    """

    def __init__(self, container: ServiceContainer, service_type: Type[T]) -> None:
        """
        Initialize lazy wrapper.

        Args:
            container: The DI container
            service_type: The type of service to lazily initialize
        """
        self._container = container
        self._service_type = service_type
        self._instance: Optional[T] = None

    @property
    def value(self) -> T:
        """Get the service instance, creating it if necessary."""
        if self._instance is None:
            self._instance = self._container.resolve(self._service_type)
        return self._instance

    def __call__(self) -> T:
        """Allow calling like a function to get the value."""
        return self.value


def inject(container: ServiceContainer) -> Callable[[Type[T]], T]:
    """
    Decorator for injecting dependencies into classes.

    Usage:
        @inject(container)
        class MyService:
            def __init__(self, dep1: Dep1, dep2: Dep2):
                ...

    Args:
        container: The DI container to use for resolution

    Returns:
        Decorated class with injected dependencies
    """

    def decorator(cls: Type[T]) -> T:
        import inspect

        sig = inspect.signature(cls.__init__)
        params = {}

        for name, param in sig.parameters.items():
            if name in ("self", "args", "kwargs"):
                continue
            if param.annotation != inspect.Parameter.empty:
                try:
                    params[name] = container.resolve(param.annotation)
                except KeyError:
                    if param.default != inspect.Parameter.empty:
                        params[name] = param.default

        return cls(**params)

    return decorator
