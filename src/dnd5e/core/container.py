"""Dependency injection container for managing application services.

This module provides a centralized service container that manages the lifecycle
of core application components, replacing global singletons with proper
dependency injection.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

# Lazy imports to avoid circular dependencies
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from dnd5e.cli.display_manager import DisplayManager
    from dnd5e.core.config.unified_config import ApplicationConfig
    from dnd5e.core.content_type_resolver import RegistryBasedContentTypeResolver
    from dnd5e.core.entry_registry import EntryTypeRegistry
    from dnd5e.core.interfaces import ContentTypeRegistry
    from dnd5e.core.loaders.content_factory import ContentFactory
    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.text.tag_resolver import TagResolver
    from dnd5e.core.unified_references import ReferenceManager

logger = logging.getLogger(__name__)


class ServiceContainer(Protocol):
    """Protocol for service containers that manage application dependencies."""

    def get_omnidexer(self) -> Omnidexer:
        """Get or create the omnidexer instance."""
        ...

    def get_tag_resolver(self) -> TagResolver:
        """Get or create the tag resolver instance."""
        ...

    def get_content_type_registry(self) -> ContentTypeRegistry:
        """Get or create the content type registry instance."""
        ...

    def get_display_manager(self) -> DisplayManager:
        """Get or create the display manager instance."""
        ...

    def get_content_factory(self) -> ContentFactory:
        """Get or create the content factory instance."""
        ...

    def get_content_type_resolver(self) -> RegistryBasedContentTypeResolver:
        """Get or create the content type resolver instance."""
        ...

    def get_entry_registry(self) -> EntryTypeRegistry:
        """Get or create the entry registry instance."""
        ...

    def get_app_config(self) -> ApplicationConfig:
        """Get or create the application configuration instance."""
        ...

    def get_reference_manager(self) -> ReferenceManager:
        """Get or create the reference manager instance."""
        ...

    def close(self) -> None:
        """Clean up all managed resources."""
        ...


class DefaultServiceContainer:
    """Default implementation of the service container.

    This container manages the lifecycle of all core application services,
    providing lazy initialization and proper cleanup.
    """

    def __init__(self) -> None:
        """Initialize the service container."""
        # Core services
        self._omnidexer: Omnidexer | None = None
        self._tag_resolver: TagResolver | None = None

        # Infrastructure services
        self._content_type_registry: ContentTypeRegistry | None = None
        self._display_manager: DisplayManager | None = None
        self._content_factory: ContentFactory | None = None
        self._content_type_resolver: RegistryBasedContentTypeResolver | None = None
        self._entry_registry: EntryTypeRegistry | None = None
        self._app_config: ApplicationConfig | None = None
        self._reference_manager: ReferenceManager | None = None

        # Track if container is closed
        self._closed = False

    def get_omnidexer(self) -> Omnidexer:
        """Get or create the omnidexer instance.

        The omnidexer is lazily initialized and cached for the lifetime
        of the container.

        Returns:
            The omnidexer instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._omnidexer is None:
            logger.debug("Creating omnidexer instance")
            from dnd5e.core.loaders.omnidexer import Omnidexer

            self._omnidexer = Omnidexer()

            # Load data with progress display if available
            display_manager = self.get_display_manager()
            with display_manager.progress("Loading omnidexer") as _:
                task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                self._omnidexer.load_all_data()
                display_manager.update_task(task, completed=100)

        return self._omnidexer

    def get_tag_resolver(self) -> TagResolver:
        """Get or create the tag resolver instance.

        The tag resolver depends on the omnidexer and is lazily initialized.

        Returns:
            The tag resolver instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._tag_resolver is None:
            logger.debug("Creating tag resolver instance")
            from dnd5e.core.text.tag_resolver import TagResolver

            omnidexer = self.get_omnidexer()
            self._tag_resolver = TagResolver(omnidexer)

        return self._tag_resolver

    def get_content_type_registry(self) -> ContentTypeRegistry:
        """Get or create the content type registry instance.

        Returns:
            The content type registry instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._content_type_registry is None:
            logger.debug("Creating content type registry instance")
            from dnd5e.core.interfaces import ContentTypeRegistry

            self._content_type_registry = ContentTypeRegistry()

        return self._content_type_registry

    def get_display_manager(self) -> DisplayManager:
        """Get or create the display manager instance.

        Returns:
            The display manager instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._display_manager is None:
            logger.debug("Creating display manager instance")
            from dnd5e.cli.display_manager import DisplayManager

            self._display_manager = DisplayManager()

        return self._display_manager

    def get_content_factory(self) -> ContentFactory:
        """Get or create the content factory instance.

        Returns:
            The content factory instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._content_factory is None:
            logger.debug("Creating content factory instance")
            from dnd5e.core.loaders.content_factory import ContentFactory

            self._content_factory = ContentFactory()

        return self._content_factory

    def get_content_type_resolver(self) -> RegistryBasedContentTypeResolver:
        """Get or create the content type resolver instance.

        Returns:
            The content type resolver instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._content_type_resolver is None:
            logger.debug("Creating content type resolver instance")
            from dnd5e.core.content_type_resolver import (
                RegistryBasedContentTypeResolver,
            )

            self._content_type_resolver = RegistryBasedContentTypeResolver()

        return self._content_type_resolver

    def get_entry_registry(self) -> EntryTypeRegistry:
        """Get or create the entry registry instance.

        Returns:
            The entry registry instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._entry_registry is None:
            logger.debug("Creating entry registry instance")
            from dnd5e.core.entry_registry import EntryTypeRegistry

            self._entry_registry = EntryTypeRegistry()

        return self._entry_registry

    def get_app_config(self) -> ApplicationConfig:
        """Get or create the application configuration instance.

        Returns:
            The application configuration instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._app_config is None:
            logger.debug("Creating application configuration instance")
            from dnd5e.core.config.unified_config import ApplicationConfig

            self._app_config = ApplicationConfig()

        return self._app_config

    def get_reference_manager(self) -> ReferenceManager:
        """Get or create the reference manager instance.

        Returns:
            The reference manager instance

        Raises:
            RuntimeError: If container has been closed
        """
        self._check_not_closed()

        if self._reference_manager is None:
            logger.debug("Creating reference manager instance")
            from dnd5e.core.unified_references import ReferenceManager

            self._reference_manager = ReferenceManager()

        return self._reference_manager

    def close(self) -> None:
        """Clean up all managed resources.

        This method should be called when the container is no longer needed
        to ensure proper cleanup of resources.
        """
        if self._closed:
            return

        logger.debug("Closing service container")

        # Clean up services that might need explicit cleanup
        if self._omnidexer is not None:
            # Omnidexer might have cleanup logic in the future
            pass

        # Mark all services as None to prevent reuse
        self._omnidexer = None
        self._tag_resolver = None
        self._content_type_registry = None
        self._display_manager = None
        self._content_factory = None
        self._content_type_resolver = None
        self._entry_registry = None
        self._app_config = None

        self._closed = True

    def _check_not_closed(self) -> None:
        """Check that the container hasn't been closed.

        Raises:
            RuntimeError: If the container has been closed
        """
        if self._closed:
            raise RuntimeError("Service container has been closed")

    def __repr__(self) -> str:
        """Return string representation of the container."""
        status = "closed" if self._closed else "open"
        services = []

        if not self._closed:
            if self._omnidexer is not None:
                services.append("omnidexer")
            if self._tag_resolver is not None:
                services.append("tag_resolver")
            if self._content_type_registry is not None:
                services.append("content_type_registry")
            if self._display_manager is not None:
                services.append("display_manager")
            if self._content_factory is not None:
                services.append("content_factory")
            if self._content_type_resolver is not None:
                services.append("content_type_resolver")
            if self._entry_registry is not None:
                services.append("entry_registry")
            if self._app_config is not None:
                services.append("app_config")
            if self._reference_manager is not None:
                services.append("reference_manager")

        services_str = f", services=[{', '.join(services)}]" if services else ""
        return f"DefaultServiceContainer(status={status}{services_str})"


@contextmanager
def service_container() -> Iterator[ServiceContainer]:
    """Create and manage a service container as a context manager.

    This context manager ensures proper cleanup of the container when done.

    Usage:
        with service_container() as container:
            omnidexer = container.get_omnidexer()
            # ... use services
        # Container is automatically closed here

    Yields:
        A service container instance
    """
    container = DefaultServiceContainer()
    try:
        yield container
    finally:
        container.close()


# Global container instance for CLI usage
_global_container: DefaultServiceContainer | None = None


def get_global_container() -> DefaultServiceContainer:
    """Get the global service container instance.

    This provides a global container for CLI usage while still allowing
    dependency injection in tests and other contexts.

    Returns:
        The global service container instance
    """
    global _global_container
    if _global_container is None:
        _global_container = DefaultServiceContainer()
    return _global_container


def reset_global_container() -> None:
    """Reset the global service container for testing.

    This creates a new container instance, effectively clearing all
    cached services. Used primarily for test isolation.
    """
    global _global_container
    _global_container = None


def reset_all_services() -> None:
    """Reset all services managed by the container and other global state.

    This is a comprehensive reset function for tests that ensures complete
    isolation by resetting both container services and other global singletons.
    """
    reset_global_container()

    # Reset other global state that may not be in the container yet
    try:
        from dnd5e.core.config.paths import reset_path_config

        reset_path_config()
    except ImportError:
        pass

    try:
        from dnd5e.core.config.unified_config import reset_app_config

        reset_app_config()
    except ImportError:
        pass

    try:
        from dnd5e.core.config.sources import reset_config_manager

        reset_config_manager()
    except ImportError:
        pass
