"""Async service factories for protocol-based dependency injection.

This module provides factory functions for creating all 8 core services
with proper dependency injection, async initialization, and hot-reload support.

Each factory follows the modern async pattern and implements the appropriate
protocols for type safety and lifecycle management.

Service Factories:
- create_configuration_service: Hot-reloadable configuration management
- create_omnidexer_service: Async resource omnidexer with GitHub source support
- create_tag_resolver_service: Hot-reloadable tag resolution with rendering context
- create_content_type_registry_service: Singleton content type registry
- create_display_manager_service: Scoped display management with request-specific config
- create_content_factory_service: Singleton content factory
- create_entry_registry_service: Singleton entry type registry
- create_reference_manager_service: Scoped reference management
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from dnd5e.core.error_types import (
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
)
from dnd5e.core.result import Error, Result, Success

from .protocols import (
    AsyncResourceProtocol,
    ConfigurableServiceProtocol,
    ConfigurationProtocol,
    ContentFactoryProtocol,
    ContentTypeRegistryProtocol,
    DisplayManagerProtocol,
    EntryTypeRegistryProtocol,
    OmnidexerProtocol,
    ReferenceManagerProtocol,
    ServiceProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from dnd5e.cli.display_manager import DisplayManager
    from dnd5e.core.config.unified_config import ApplicationConfig
    from dnd5e.core.entry_registry import EntryTypeRegistry
    from dnd5e.core.interfaces import ContentTypeRegistry
    from dnd5e.core.loaders.content_factory import ContentFactory
    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.services.container import ModernServiceContainer
    from dnd5e.core.text.tag_resolver import TagResolver
    from dnd5e.core.unified_references import ReferenceManager
    from dnd5e.renderers.core.interfaces import RenderingContext

logger = logging.getLogger(__name__)


# Configuration Services


async def create_configuration_service(
    config_override: ApplicationConfig | None = None,
) -> ConfigurationProtocol:
    """Factory for configuration service with hot-reload support.

    Args:
        config_override: Optional configuration override

    Returns:
        Configuration service implementing ConfigurationProtocol
    """

    class ConfigurationService:
        """Configuration service with hot-reload capability."""

        def __init__(self, config: ApplicationConfig) -> None:
            self._config = config
            self._reload_callbacks: list[Callable[[], None]] = []

        def get_service_name(self) -> str:
            return "ConfigurationService"

        def get_config(self) -> ApplicationConfig:
            return self._config

        async def reload_config(self, new_config: ApplicationConfig) -> None:
            """Hot-reload configuration."""
            self._config = new_config

            logger.info("Configuration hot-reloaded")

            # Notify other services of config change via callbacks
            for callback in self._reload_callbacks:
                try:
                    # Fix: callbacks take no parameters based on type annotation
                    callback()
                except Exception as e:
                    logger.warning(f"Config reload callback failed: {e}")

        def supports_hot_reload(self) -> bool:
            return True

        async def reload_from_source(
            self, source: str
        ) -> Result[ApplicationConfig, ConfigurationError]:
            """Reload configuration from source."""
            try:
                # Use unified config system for reloading
                from dnd5e.core.config.unified_config import get_app_config

                # For now, return current config as placeholder
                # TODO: Implement proper config file reloading
                current_config = get_app_config()
                await self.reload_config(current_config)
                return Success(current_config)

            except Exception as e:
                return Error(
                    ConfigurationError(
                        message=f"Failed to reload configuration from {source}: {e}",
                        error_code=MCPErrorCode.CONFIGURATION_ERROR,
                        category=ErrorCategory.CONFIGURATION,
                        severity=ErrorSeverity.ERROR,
                        source="ConfigurationService.reload_from_source",
                        suggestions=[
                            "Check file path and permissions",
                            "Verify configuration file format",
                            "Check for configuration syntax errors",
                        ],
                    )
                )

        def validate_config(self) -> Result[ApplicationConfig, ConfigurationError]:
            """Validate current configuration."""
            try:
                # Configuration is already validated by Pydantic during creation
                return Success(self._config)
            except Exception as e:
                return Error(
                    ConfigurationError(
                        message=f"Configuration validation failed: {e}",
                        error_code=MCPErrorCode.CONFIGURATION_ERROR,
                        category=ErrorCategory.CONFIGURATION,
                        severity=ErrorSeverity.ERROR,
                        source="ConfigurationService.validate_config",
                    )
                )

        def add_reload_callback(self, callback: Callable[[], None]) -> None:
            """Add callback for configuration reload notifications."""
            self._reload_callbacks.append(callback)

    # Get configuration
    if config_override is not None:
        config = config_override
    else:
        from dnd5e.core.config.unified_config import get_app_config

        config = get_app_config()

    return ConfigurationService(config)


# Core Async Resource Services


async def create_omnidexer_service(
    container: ModernServiceContainer,
) -> OmnidexerProtocol:
    """Factory for async omnidexer with proper resource management.

    Args:
        container: Service container for dependency resolution

    Returns:
        Omnidexer service implementing OmnidexerProtocol
    """

    class AsyncOmnidexerService:
        """Async omnidexer service with resource management."""

        def __init__(self, config: ApplicationConfig) -> None:
            self._config = config
            self._omnidexer: Omnidexer | None = None
            self._initialized = False

        def get_service_name(self) -> str:
            return "OmnidexerService"

        async def initialize(self) -> None:
            """Async initialization of omnidexer resources."""
            if self._initialized:
                return

            logger.debug("Initializing omnidexer service")

            try:
                from dnd5e.core.loaders.omnidexer import Omnidexer

                # Create omnidexer (constructor doesn't take sources)
                self._omnidexer = Omnidexer()

                # Async source preparation (GitHub cloning, etc)
                if hasattr(self._omnidexer, "ensure_sources_ready"):
                    await self._omnidexer.ensure_sources_ready()

                # Load all data
                self._omnidexer.load_all_data()

                # Resolve copy references
                await self._resolve_copy_references()

                self._initialized = True
                logger.info("Omnidexer service initialized successfully")

            except Exception:
                logger.exception("Failed to initialize omnidexer service")
                raise

        async def cleanup(self) -> None:
            """Clean up omnidexer resources."""
            if self._omnidexer and hasattr(self._omnidexer, "cleanup"):
                try:
                    await self._omnidexer.cleanup()
                    logger.debug("Omnidexer resources cleaned up")
                except Exception as e:
                    logger.warning(f"Omnidexer cleanup failed: {e}")

            self._omnidexer = None
            self._initialized = False

        def is_initialized(self) -> bool:
            return self._initialized

        async def load_content_sources(self, sources: list[str]) -> None:
            """Load content from specified sources."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Implementation would reload omnidexer with new sources
            logger.info(f"Loading content sources: {sources}")

        def get_content(self, content_type: str, identifier: str) -> object:
            """Get specific content by type and identifier."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            # Use actual omnidexer search by name - simplified implementation
            results = self._omnidexer.search_by_name_prefix(identifier)
            return results[0] if results else None

        def search(self, query: str) -> list[object]:
            """Search for content matching the query."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            # Use actual omnidexer search methods
            results = self._omnidexer.get_all_by_type(query) if query else []
            return list(results)

        async def ensure_sources_ready(self) -> None:
            """Ensure all content sources are loaded and ready."""
            if not self._initialized:
                await self.initialize()

        async def _resolve_copy_references(self) -> None:
            """Resolve copy references after data loading."""
            if not self._omnidexer:
                return

            try:
                from dnd5e.core.resolvers.copy_resolver import CopyResolver

                copy_resolver = CopyResolver(self._omnidexer)
                copy_resolver.resolve_copies_in_omnidexer()

            except Exception as e:
                logger.warning(f"Failed to resolve copy references: {e}")

    # Get configuration from container
    config_service = cast(
        ConfigurationProtocol, await container.get_service(ConfigurationProtocol)
    )
    config = config_service.get_config()

    # Create and initialize service
    service = AsyncOmnidexerService(config)
    await service.initialize()

    return service


# Hot-Reloadable Scoped Services


async def create_tag_resolver_service(
    container: ModernServiceContainer,
) -> TagResolverProtocol:
    """Factory for configurable tag resolver service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Tag resolver service implementing TagResolverProtocol
    """

    class ConfigurableTagResolverService:
        """Tag resolver service with hot-reload capability."""

        def __init__(
            self, omnidexer: OmnidexerProtocol, config: ApplicationConfig
        ) -> None:
            self._omnidexer = omnidexer
            self._config = config
            self._tag_resolver: TagResolver | None = None
            self._initialize_resolver()

        def get_service_name(self) -> str:
            return "TagResolverService"

        def _initialize_resolver(self) -> None:
            """Initialize tag resolver with current config."""
            try:
                from dnd5e.core.text.tag_resolver import TagResolver

                # Get the underlying omnidexer instance
                omnidexer_instance = getattr(self._omnidexer, "_omnidexer", None)
                if omnidexer_instance is None:
                    raise RuntimeError("Omnidexer service not properly initialized")

                self._tag_resolver = TagResolver(omnidexer=omnidexer_instance)
                logger.debug("Tag resolver initialized")

            except Exception:
                logger.exception("Failed to initialize tag resolver")
                raise

        async def reload_config(self, new_config: ApplicationConfig) -> None:
            """Hot-reload tag resolver configuration."""
            logger.info("Reloading tag resolver configuration")
            self._config = new_config
            # Reinitialize with new config
            self._initialize_resolver()

        def supports_hot_reload(self) -> bool:
            return True

        def resolve_tag(self, tag: str, context: RenderingContext) -> str:
            """Resolve a tag to its rendered form."""
            if not self._tag_resolver:
                raise RuntimeError("TagResolver not initialized")
            # Use actual TagResolver interface - process_text method
            return self._tag_resolver.process_text(tag)

        def supports_tag_type(self, tag_type: str) -> bool:
            """Check if resolver supports a tag type."""
            if not self._tag_resolver:
                return False
            # Use actual TagResolver interface
            supported_types = self._tag_resolver.get_supported_tag_types()
            return tag_type in supported_types

    # Get dependencies from container
    omnidexer = await container.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]
    config_service = await container.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
    config = config_service.get_config()

    return ConfigurableTagResolverService(omnidexer, config)


# Infrastructure Services


async def create_content_type_registry_service() -> ContentTypeRegistryProtocol:
    """Factory for content type registry service.

    Returns:
        Content type registry implementing ContentTypeRegistryProtocol
    """

    class ContentTypeRegistryService:
        """Content type registry service."""

        def __init__(self) -> None:
            self._registry: dict[str, type] = {}

        def get_service_name(self) -> str:
            return "ContentTypeRegistryService"

        def register_content_type(self, content_type: str, handler: type) -> None:
            """Register a content type handler."""
            self._registry[content_type] = handler
            logger.debug(f"Registered content type: {content_type}")

        def get_content_handler(self, content_type: str) -> type | None:
            """Get handler for a content type."""
            return self._registry.get(content_type)

        def get_registered_types(self) -> list[str]:
            """Get list of registered content types."""
            return list(self._registry.keys())

    # Initialize with basic registry
    try:
        from dnd5e.core.interfaces import ContentTypeRegistry

        # Create wrapper around existing registry
        class ProtocolWrapper(ContentTypeRegistryService):
            def __init__(self) -> None:
                super().__init__()
                self._legacy_registry = ContentTypeRegistry()

        return ProtocolWrapper()
    except Exception as e:
        logger.warning(f"Failed to create legacy registry wrapper: {e}")
        return ContentTypeRegistryService()


async def create_display_manager_service(
    container: ModernServiceContainer,
) -> DisplayManagerProtocol:
    """Factory for display manager service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Display manager implementing DisplayManagerProtocol
    """

    class DisplayManagerService:
        """Display manager service with configuration support."""

        def __init__(self, config: ApplicationConfig) -> None:
            self._config = config
            self._display_manager: DisplayManager | None = None
            self._initialize_display_manager()

        def get_service_name(self) -> str:
            return "DisplayManagerService"

        def _initialize_display_manager(self) -> None:
            """Initialize display manager."""
            try:
                from dnd5e.cli.display_manager import DisplayManager

                self._display_manager = DisplayManager()
                logger.debug("Display manager initialized")
            except Exception:
                logger.exception("Failed to initialize display manager")
                raise

        async def reload_config(self, new_config: ApplicationConfig) -> None:
            """Hot-reload display configuration."""
            logger.info("Reloading display manager configuration")
            self._config = new_config
            # Reinitialize with new config if needed
            self._initialize_display_manager()

        def supports_hot_reload(self) -> bool:
            return True

        def progress(self, description: str) -> object:
            """Create a progress context manager."""
            if not self._display_manager:
                raise RuntimeError("DisplayManager not initialized")
            return self._display_manager.progress(description)

        def add_task(self, description: str, total: int | None = None) -> str:
            """Add a progress tracking task."""
            if not self._display_manager:
                raise RuntimeError("DisplayManager not initialized")
            task_id = self._display_manager.add_task(description, total)
            # Convert TaskID to string for the protocol interface
            return str(task_id)

        def update_task(
            self,
            task_id: str,
            completed: int | None = None,
            description: str | None = None,
        ) -> None:
            """Update progress on a task."""
            if not self._display_manager:
                raise RuntimeError("DisplayManager not initialized")
            # Convert string task_id back to actual TaskID for DisplayManager
            from dnd5e.cli.display_manager import TaskID

            actual_task_id = (
                TaskID(int(task_id)) if isinstance(task_id, str) else task_id
            )
            self._display_manager.update_task(actual_task_id, advance=completed)

    # Get configuration from container
    config_service = await container.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
    config = config_service.get_config()

    return DisplayManagerService(config)


async def create_content_factory_service() -> ContentFactoryProtocol:
    """Factory for content factory service.

    Returns:
        Content factory implementing ContentFactoryProtocol
    """

    class ContentFactoryService:
        """Content factory service."""

        def __init__(self) -> None:
            self._factory: ContentFactory | None = None
            self._initialize_factory()

        def get_service_name(self) -> str:
            return "ContentFactoryService"

        def _initialize_factory(self) -> None:
            """Initialize content factory."""
            try:
                from dnd5e.core.loaders.content_factory import ContentFactory

                self._factory = ContentFactory()
                logger.debug("Content factory initialized")
            except Exception:
                logger.exception("Failed to initialize content factory")
                raise

        def create_content(self, content_type: str, data: dict) -> object:
            """Create content object from data."""
            if not self._factory:
                raise RuntimeError("ContentFactory not initialized")
            # Use the actual ContentFactory interface - need proper parameters
            from dnd5e.core.interfaces import ContentType

            content_type_enum = (
                ContentType(content_type)
                if hasattr(ContentType, content_type)
                else None
            )
            return (
                self._factory.create_content(data, content_type_enum)
                if content_type_enum
                else None
            )

        def supports_content_type(self, content_type: str) -> bool:
            """Check if factory supports a content type."""
            if not self._factory:
                return False
            # Use actual ContentFactory interface
            return hasattr(self._factory, "create_content")  # Simple check for now

    return ContentFactoryService()


async def create_entry_registry_service() -> EntryTypeRegistryProtocol:
    """Factory for entry type registry service.

    Returns:
        Entry registry implementing EntryTypeRegistryProtocol
    """

    class EntryTypeRegistryService:
        """Entry type registry service that delegates to actual EntryTypeRegistry."""

        def __init__(self) -> None:
            self._registry: EntryTypeRegistry | None = None
            self._initialize_registry()

        def get_service_name(self) -> str:
            return "EntryTypeRegistryService"

        def _initialize_registry(self) -> None:
            """Initialize entry type registry."""
            try:
                from dnd5e.core.entry_registry import EntryTypeRegistry

                self._registry = EntryTypeRegistry()
                logger.debug("Entry type registry initialized")
            except Exception:
                logger.exception("Failed to initialize entry type registry")
                raise

        def register_entry_type(self, entry_type: str, processor: type) -> None:
            """Register an entry type processor."""
            if not self._registry:
                raise RuntimeError("EntryTypeRegistry not initialized")
            # EntryTypeRegistry doesn't have register methods - it's for validation
            # This is a placeholder implementation
            pass

        def get_entry_processor(self, entry_type: str) -> type | None:
            """Get processor for an entry type."""
            if not self._registry:
                return None
            # EntryTypeRegistry doesn't have processor methods - return None
            return None

        # Delegate all other methods to the actual registry
        def __getattr__(self, name: str) -> Any:
            """Delegate unknown attributes to the actual EntryTypeRegistry."""
            if self._registry is None:
                raise RuntimeError("EntryTypeRegistry not initialized")
            return getattr(self._registry, name)

    return EntryTypeRegistryService()


async def create_reference_manager_service(
    container: ModernServiceContainer,
) -> ReferenceManagerProtocol:
    """Factory for reference manager service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Reference manager implementing ReferenceManagerProtocol
    """

    class ReferenceManagerService:
        """Reference manager service."""

        def __init__(self, omnidexer: OmnidexerProtocol) -> None:
            self._omnidexer = omnidexer
            self._reference_manager: ReferenceManager | None = None
            self._initialize_manager()

        def get_service_name(self) -> str:
            return "ReferenceManagerService"

        def _initialize_manager(self) -> None:
            """Initialize reference manager."""
            try:
                from dnd5e.core.unified_references import ReferenceManager

                self._reference_manager = ReferenceManager()
                logger.debug("Reference manager initialized")
            except Exception:
                logger.exception("Failed to initialize reference manager")
                raise

        def add_reference(self, source: str, target: str, ref_type: str) -> None:
            """Add a reference relationship."""
            if not self._reference_manager:
                raise RuntimeError("ReferenceManager not initialized")
            # ReferenceManager doesn't have add_reference method - create a simple reference
            # This is a placeholder implementation
            pass

        def resolve_reference(self, source: str, ref_type: str) -> list[str]:
            """Resolve references from a source."""
            if not self._reference_manager:
                return []
            # Use actual ReferenceManager interface
            from dnd5e.core.unified_references import Reference

            # Create a simple reference with required fields
            ref: Reference[list[str]] = Reference(
                source=source, target=source, content_type=list
            )
            result = self._reference_manager.resolve_reference(ref, None)
            return result if result else []

        def get_references_to(self, target: str) -> list[tuple[str, str]]:
            """Get all references pointing to a target."""
            if not self._reference_manager:
                return []
            # ReferenceManager doesn't have this method - return empty list
            return []

    # Get dependencies from container
    omnidexer = await container.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]

    return ReferenceManagerService(omnidexer)
