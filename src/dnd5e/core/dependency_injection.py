"""Dependency injection container for breaking tight coupling."""

from dataclasses import dataclass
from functools import wraps
from typing import Any, Optional, Protocol, TypeVar, runtime_checkable

from .interfaces import (
    ContentIndexer,
    ContentLoader,
    ContentTypeResolver,
    ServiceLocator,
    TagResolver,
    get_service_locator,
)
from .models.content import BaseContent, ContentType

T = TypeVar("T")


@runtime_checkable
class ServiceFactory(Protocol):
    """Protocol for service factories."""

    def create(self, container: "DependencyContainer") -> Any:
        """Create a service instance."""
        ...


@dataclass
class ServiceRegistration:
    """Registration information for a service."""

    service_type: type
    factory: ServiceFactory
    singleton: bool = True
    instance: Any | None = None


class DependencyContainer:
    """Dependency injection container."""

    def __init__(self) -> None:
        self._services: dict[type, ServiceRegistration] = {}
        self._building: set[type] = set()

    def register(
        self, service_type: type, factory: ServiceFactory, singleton: bool = True
    ) -> None:
        """Register a service with the container.

        Args:
            service_type: Type of service to register
            factory: Factory function to create the service
            singleton: Whether to create a singleton instance
        """
        self._services[service_type] = ServiceRegistration(
            service_type=service_type, factory=factory, singleton=singleton
        )

    def register_instance(self, service_type: type, instance: Any) -> None:
        """Register a service instance directly.

        Args:
            service_type: Type of service to register
            instance: Service instance
        """
        self._services[service_type] = ServiceRegistration(
            service_type=service_type,
            factory=lambda _: instance,
            singleton=True,
            instance=instance,
        )

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service from the container.

        Args:
            service_type: Type of service to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered or circular dependency detected
        """
        if service_type not in self._services:
            raise ValueError(f"Service {service_type} is not registered")

        registration = self._services[service_type]

        # Check for circular dependencies
        if service_type in self._building:
            raise ValueError(f"Circular dependency detected for {service_type}")

        # Return existing singleton instance if available
        if registration.singleton and registration.instance is not None:
            return registration.instance

        # Create new instance
        self._building.add(service_type)
        try:
            instance = registration.factory.create(self)
            if registration.singleton:
                registration.instance = instance
            return instance
        finally:
            self._building.discard(service_type)

    def has_service(self, service_type: type) -> bool:
        """Check if a service is registered.

        Args:
            service_type: Type of service to check

        Returns:
            True if service is registered
        """
        return service_type in self._services


class LambdaServiceFactory:
    """Service factory using a lambda function."""

    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func

    def create(self, container: DependencyContainer) -> Any:
        """Create service instance using factory function."""
        return self.factory_func(container)


class ClassServiceFactory:
    """Service factory for class instantiation."""

    def __init__(self, service_class: type, *args, **kwargs) -> None:
        self.service_class = service_class
        self.args = args
        self.kwargs = kwargs

    def create(self, container: DependencyContainer) -> Any:
        """Create service instance using class constructor."""
        return self.service_class(*self.args, **self.kwargs)


def inject(*dependencies: type) -> Any:
    """Decorator for dependency injection into functions.

    Args:
        *dependencies: Service types to inject

    Example:
        @inject(ContentIndexer, TagResolver)
        def process_content(content, indexer, resolver):
            # indexer and resolver are automatically injected
            pass
    """

    def decorator(func) -> Any:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            container = get_dependency_container()

            # Resolve dependencies
            injected_args = []
            for dep_type in dependencies:
                injected_args.append(container.resolve(dep_type))

            # Call original function with injected dependencies
            return func(*args, *injected_args, **kwargs)

        return wrapper

    return decorator


# Global dependency container
_dependency_container = DependencyContainer()


def get_dependency_container() -> DependencyContainer:
    """Get the global dependency container.

    Returns:
        Global dependency container instance
    """
    return _dependency_container


def configure_services() -> None:
    """Configure default services in the dependency container."""
    container = get_dependency_container()

    # Register content type resolver
    from .content_type_resolver import get_content_type_resolver

    container.register_instance(ContentTypeResolver, get_content_type_resolver())

    # Register content factory
    from .loaders.content_factory import get_content_factory

    container.register_instance(ContentLoader, get_content_factory())

    # Register omnidexer as content indexer
    def create_omnidexer(container: DependencyContainer) -> Any:
        from .loaders.omnidexer import Omnidexer

        return Omnidexer()

    container.register(ContentIndexer, LambdaServiceFactory(create_omnidexer))

    # Register tag resolver
    def create_tag_resolver(container: DependencyContainer) -> Any:
        from .indexer.tag_resolver import TagResolver

        indexer = container.resolve(ContentIndexer)
        return TagResolver(indexer)

    container.register(TagResolver, LambdaServiceFactory(create_tag_resolver))

    # Register service locator for backward compatibility
    service_locator = get_service_locator()
    service_locator.register(
        ContentTypeResolver, container.resolve(ContentTypeResolver)
    )
    service_locator.register(ContentLoader, container.resolve(ContentLoader))
    service_locator.register(ContentIndexer, container.resolve(ContentIndexer))
    service_locator.register(TagResolver, container.resolve(TagResolver))


# Auto-configure services when module is imported
configure_services()
