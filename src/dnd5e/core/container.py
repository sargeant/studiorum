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
    from dnd5e.core.entry_registry import EntryTypeRegistry
    from dnd5e.core.interfaces import ContentTypeRegistry
    from dnd5e.core.loaders.content_factory import ContentFactory
    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.text.tag_resolver import TagResolver
    from dnd5e.core.unified_references import ReferenceManager

from dnd5e.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ServiceError,
)
from dnd5e.core.result import Error, Result, Success

logger = logging.getLogger(__name__)


class ServiceContainer(Protocol):
    """Protocol for service containers that manage application dependencies."""

    def get_omnidexer(self) -> Result[Omnidexer, ServiceError]:
        """Get or create the omnidexer instance."""
        ...

    def get_tag_resolver(self) -> Result[TagResolver, ServiceError]:
        """Get or create the tag resolver instance."""
        ...

    def get_content_type_registry(self) -> Result[ContentTypeRegistry, ServiceError]:
        """Get or create the content type registry instance."""
        ...

    def get_display_manager(self) -> Result[DisplayManager, ServiceError]:
        """Get or create the display manager instance."""
        ...

    def get_content_factory(self) -> Result[ContentFactory, ServiceError]:
        """Get or create the content factory instance."""
        ...

    def get_entry_registry(self) -> Result[EntryTypeRegistry, ServiceError]:
        """Get or create the entry registry instance."""
        ...

    def get_app_config(self) -> Result[ApplicationConfig, ServiceError]:
        """Get or create the application configuration instance."""
        ...

    def get_reference_manager(self) -> Result[ReferenceManager, ServiceError]:
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
        self._entry_registry: EntryTypeRegistry | None = None
        self._app_config: ApplicationConfig | None = None
        self._reference_manager: ReferenceManager | None = None

        # Track if container is closed
        self._closed = False

    def get_omnidexer(self) -> Result[Omnidexer, ServiceError]:
        """Get or create the omnidexer instance.

        The omnidexer is lazily initialized and cached for the lifetime
        of the container.

        Returns:
            Success with omnidexer instance, or Error with service failure details

        Examples:
            ```python
            result = container.get_omnidexer()
            if result.is_success():
                omnidexer = result.unwrap()
            else:
                error = result.error
                print(f"Failed to load omnidexer: {error.message}")
            ```
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._omnidexer is None:
            logger.debug("Creating omnidexer instance")

            try:
                from dnd5e.core.loaders.omnidexer import Omnidexer

                self._omnidexer = Omnidexer()

                # Get display manager for progress display
                display_result = self.get_display_manager()
                if display_result.is_error():
                    # Fallback to no progress display if display manager fails
                    logger.warning("Display manager unavailable for progress display")
                    self._omnidexer.load_all_data()
                    self._resolve_copy_references()
                else:
                    display_manager = display_result.unwrap()
                    with display_manager.progress("Loading omnidexer") as _:
                        task = display_manager.add_task(
                            "[cyan]Loading content data...", total=None
                        )
                        self._omnidexer.load_all_data()
                        display_manager.update_task(task, completed=50)

                        # Resolve copy references after all data is loaded
                        display_manager.update_task(
                            task, description="[cyan]Resolving copy references..."
                        )
                        self._resolve_copy_references()
                        display_manager.update_task(task, completed=100)

            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize omnidexer: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_omnidexer",
                        suggestions=[
                            "Check data file availability and format",
                            "Verify memory availability for data loading",
                            "Check file system permissions",
                            "Review omnidexer configuration",
                        ],
                        data={
                            "service_name": "omnidexer",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._omnidexer)

    def get_tag_resolver(self) -> Result[TagResolver, ServiceError]:
        """Get or create the tag resolver instance.

        The tag resolver depends on the omnidexer and is lazily initialized.

        Returns:
            Success with tag resolver instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._tag_resolver is None:
            logger.debug("Creating tag resolver instance")

            try:
                from dnd5e.core.text.tag_resolver import TagResolver

                omnidexer_result = self.get_omnidexer()
                if omnidexer_result.is_error():
                    return Error(omnidexer_result.error)  # type: ignore[attr-defined]

                omnidexer = omnidexer_result.unwrap()
                self._tag_resolver = TagResolver(omnidexer)
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize tag resolver: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_tag_resolver",
                        suggestions=[
                            "Check omnidexer availability",
                            "Verify tag resolver dependencies",
                            "Check text processing configuration",
                        ],
                        data={
                            "service_name": "tag_resolver",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._tag_resolver)

    def get_content_type_registry(self) -> Result[ContentTypeRegistry, ServiceError]:
        """Get or create the content type registry instance.

        Returns:
            Success with content type registry instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._content_type_registry is None:
            logger.debug("Creating content type registry instance")

            try:
                from dnd5e.core.interfaces import ContentTypeRegistry

                # Create a basic interface-based registry
                # Content type mappings will be populated by the registry manager
                # when initialize_content_types() is called from elsewhere
                self._content_type_registry = ContentTypeRegistry()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize content type registry: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_content_type_registry",
                        suggestions=[
                            "Check content type registry dependencies",
                            "Verify interface module availability",
                            "Check registry configuration",
                        ],
                        data={
                            "service_name": "content_type_registry",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._content_type_registry)

    def get_display_manager(self) -> Result[DisplayManager, ServiceError]:
        """Get or create the display manager instance.

        Returns:
            Success with display manager instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._display_manager is None:
            logger.debug("Creating display manager instance")

            try:
                from dnd5e.cli.display_manager import DisplayManager

                self._display_manager = DisplayManager()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize display manager: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_display_manager",
                        suggestions=[
                            "Check CLI dependencies availability",
                            "Verify terminal/console support",
                            "Check display configuration",
                        ],
                        data={
                            "service_name": "display_manager",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._display_manager)

    def get_content_factory(self) -> Result[ContentFactory, ServiceError]:
        """Get or create the content factory instance.

        Returns:
            Success with content factory instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._content_factory is None:
            logger.debug("Creating content factory instance")

            try:
                from dnd5e.core.loaders.content_factory import ContentFactory

                self._content_factory = ContentFactory()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize content factory: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_content_factory",
                        suggestions=[
                            "Check content factory dependencies",
                            "Verify loader module availability",
                            "Check factory configuration",
                        ],
                        data={
                            "service_name": "content_factory",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._content_factory)

    def get_entry_registry(self) -> Result[EntryTypeRegistry, ServiceError]:
        """Get or create the entry registry instance.

        Returns:
            Success with entry registry instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._entry_registry is None:
            logger.debug("Creating entry registry instance")

            try:
                from dnd5e.core.entry_registry import EntryTypeRegistry

                self._entry_registry = EntryTypeRegistry()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize entry registry: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_entry_registry",
                        suggestions=[
                            "Check entry registry dependencies",
                            "Verify entry registry module availability",
                            "Check registry configuration",
                        ],
                        data={
                            "service_name": "entry_registry",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._entry_registry)

    def get_app_config(self) -> Result[ApplicationConfig, ServiceError]:
        """Get or create the application configuration instance.

        Returns:
            Success with application configuration instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._app_config is None:
            logger.debug("Creating application configuration instance")

            try:
                from dnd5e.core.config.unified_config import ApplicationConfig

                self._app_config = ApplicationConfig()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize application configuration: {e}",
                        error_code=MCPErrorCode.CONFIGURATION_ERROR,
                        category=ErrorCategory.CONFIGURATION,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_app_config",
                        suggestions=[
                            "Check application configuration dependencies",
                            "Verify configuration module availability",
                            "Check configuration file format",
                        ],
                        data={
                            "service_name": "app_config",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._app_config)

    def get_reference_manager(self) -> Result[ReferenceManager, ServiceError]:
        """Get or create the reference manager instance.

        Returns:
            Success with reference manager instance, or Error with service failure details
        """
        closed_check = self._check_not_closed()
        if closed_check.is_error():
            return Error(closed_check.error)  # type: ignore[attr-defined]

        if self._reference_manager is None:
            logger.debug("Creating reference manager instance")

            try:
                from dnd5e.core.unified_references import ReferenceManager

                self._reference_manager = ReferenceManager()
            except Exception as e:
                return Error(
                    ServiceError(
                        message=f"Failed to initialize reference manager: {e}",
                        error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.ERROR,
                        source="ServiceContainer.get_reference_manager",
                        suggestions=[
                            "Check reference manager dependencies",
                            "Verify reference module availability",
                            "Check reference configuration",
                        ],
                        data={
                            "service_name": "reference_manager",
                            "exception_type": type(e).__name__,
                            "operation": "initialization",
                        },
                    )
                )

        return Success(self._reference_manager)

    def _resolve_copy_references(self) -> None:
        """Resolve all pending copy references in the omnidexer."""
        if self._omnidexer is None:
            return

        try:
            from dnd5e.core.resolvers.copy_resolver import CopyResolver

            copy_resolver = CopyResolver(self._omnidexer)
            copy_resolver.resolve_copies_in_omnidexer()
        except Exception as e:
            logger.warning(f"Failed to resolve copy references: {e}")

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
        self._entry_registry = None
        self._app_config = None
        self._reference_manager = None

        self._closed = True

    def _check_not_closed(self) -> Result[None, ServiceError]:
        """Check that the container hasn't been closed.

        Returns:
            Success if container is open, Error if closed
        """
        if self._closed:
            return Error(
                ServiceError(
                    message="Service container has been closed",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer",
                    suggestions=[
                        "Create a new service container",
                        "Use a context manager to ensure proper cleanup",
                        "Check container lifecycle management",
                    ],
                    data={"container_state": "closed"},
                )
            )
        return Success(None)

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

    This properly closes the existing container and creates a new one,
    ensuring complete cleanup of all cached services and their resources.
    Used primarily for test isolation.
    """
    global _global_container
    if _global_container is not None:
        # Properly close the existing container to clean up resources
        _global_container.close()
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
