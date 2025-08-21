"""Protocol-based service interfaces for modern dependency injection.

This module defines the protocol interfaces that all services must implement,
providing type safety, runtime verification, and clear contracts for
dependency injection and lifecycle management.

Protocols include:
- Base service protocols (ServiceProtocol, AsyncResourceProtocol, ConfigurableServiceProtocol)
- Specific service protocols for each of the 8 core services
- Runtime-checkable interfaces for type safety and validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from studiorum.cli.display_manager import DisplayManager
    from studiorum.core.config.unified_config import ApplicationConfig
    from studiorum.core.entry_registry import EntryTypeRegistry
    from studiorum.core.error_types import ConfigurationError
    from studiorum.core.interfaces import ContentTypeRegistry
    from studiorum.core.loaders.content_factory import ContentFactory
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.models.content import BaseContent
    from studiorum.core.result import Result
    from studiorum.core.text.tag_resolver import TagResolver
    from studiorum.core.unified_references import ReferenceManager
    from studiorum.renderers.core.interfaces import RenderingContext


@runtime_checkable
class ServiceProtocol(Protocol):
    """Base protocol for all services.

    This protocol provides the foundational interface that all services
    must implement, enabling consistent service identification and debugging.
    """

    def get_service_name(self) -> str:
        """Return the service name for debugging and logging.

        Returns:
            Human-readable service name for identification
        """
        ...


@runtime_checkable
class AsyncResourceProtocol(Protocol):
    """Protocol for services requiring async initialization/cleanup.

    Services implementing this protocol require async resource management,
    such as network connections, file handles, or async initialization.
    Essential for MCP server async lifecycle management.
    """

    async def initialize(self) -> None:
        """Initialize async resources.

        This method is called during service creation to set up any
        async resources like network connections, file handles, or
        background tasks.

        Raises:
            ServiceInitializationError: If initialization fails
        """
        ...

    async def cleanup(self) -> None:
        """Clean up async resources.

        This method is called during service container shutdown
        to properly clean up any resources allocated during
        initialization.

        Should be idempotent - safe to call multiple times.
        """
        ...

    def is_initialized(self) -> bool:
        """Return True if service is fully initialized.

        Returns:
            True if initialize() has completed successfully
        """
        ...


@runtime_checkable
class ConfigurableServiceProtocol(Protocol):
    """Protocol for services that support hot-reload.

    Services implementing this protocol can receive configuration
    updates at runtime without requiring a full restart. Critical
    for long-running MCP servers that need configuration updates.
    """

    async def reload_config(self, new_config: ApplicationConfig) -> None:
        """Reload service configuration without restart.

        Args:
            new_config: New application configuration to apply

        Raises:
            ConfigurationError: If configuration reload fails
        """
        ...

    def supports_hot_reload(self) -> bool:
        """Return True if service supports configuration hot-reload.

        Returns:
            True if the service can handle runtime configuration changes
        """
        ...


# Core Service Protocols


@runtime_checkable
class OmnidexerProtocol(ServiceProtocol, AsyncResourceProtocol, Protocol):
    """Protocol for content indexing and retrieval services.

    The omnidexer is responsible for loading, indexing, and providing
    access to D&D 5e content data. Requires async initialization due
    to potential GitHub source downloads and large data processing.
    """

    async def load_content_sources(self, sources: list[str]) -> None:
        """Load content from specified sources.

        Args:
            sources: List of content source identifiers to load
        """
        ...

    def get_content(self, content_type: str, identifier: str) -> object:
        """Get specific content by type and identifier.

        Args:
            content_type: Type of content (e.g., 'spell', 'creature')
            identifier: Unique identifier for the content

        Returns:
            Content object or None if not found
        """
        ...

    def search(self, query: str) -> list[BaseContent]:
        """Search for content matching the query.

        Args:
            query: Search query string

        Returns:
            List of matching content objects
        """
        ...

    async def ensure_sources_ready(self) -> None:
        """Ensure all content sources are loaded and ready.

        This method handles async source preparation like GitHub
        repository cloning or remote data downloads.
        """
        ...

    # Enhanced performance methods for P5 optimization
    async def search_content_async(
        self,
        query: str,
        content_type: str | None = None,
        context: object | None = None,
        limit: int = 50,
    ) -> object:  # Result[List[BaseContent], ContentNotFoundError]
        """High-performance async search with intelligent caching.

        Args:
            query: Search query string
            content_type: Optional content type filter
            context: Optional request context for performance tracking
            limit: Maximum results to return

        Returns:
            Result object containing list of matching content or error
        """
        ...

    async def get_content_async(
        self,
        content_type: str,
        name: str,
        source: str | None = None,
        context: object | None = None,
    ) -> object:  # Result[Optional[BaseContent], ContentNotFoundError]
        """Async content retrieval with intelligent caching.

        Args:
            content_type: Type of content (e.g., 'spell', 'creature')
            name: Content name
            source: Optional source filter
            context: Optional request context for performance tracking

        Returns:
            Result object containing content or error
        """
        ...

    def get_performance_statistics(self) -> dict[str, object]:
        """Get comprehensive performance statistics.

        Returns:
            Dictionary with cache stats, performance metrics, and usage data
        """
        ...

    def get_all_by_type(self, content_type: object) -> list[BaseContent]:
        """Get all content of a specific type.

        Args:
            content_type: Content type enum or string identifier

        Returns:
            List of all content matching the specified type
        """
        ...


@runtime_checkable
class TagResolverProtocol(ServiceProtocol, ConfigurableServiceProtocol, Protocol):
    """Protocol for tag resolution and rendering services.

    The tag resolver handles parsing and rendering of {@tag} syntax
    in D&D content. Supports hot-reload for rendering configuration
    changes without restart.
    """

    def resolve_tag(self, tag: str, context: RenderingContext) -> str:
        """Resolve a tag to its rendered form.

        Args:
            tag: Tag string to resolve (e.g., '{@spell fireball}')
            context: Rendering context with output format and metadata

        Returns:
            Rendered tag content appropriate for the context
        """
        ...

    def supports_tag_type(self, tag_type: str) -> bool:
        """Check if the resolver supports a specific tag type.

        Args:
            tag_type: Tag type to check (e.g., 'spell', 'creature')

        Returns:
            True if the tag type is supported
        """
        ...


@runtime_checkable
class ConfigurationProtocol(ServiceProtocol, ConfigurableServiceProtocol, Protocol):
    """Protocol for configuration management services.

    Provides access to application configuration with hot-reload
    support for runtime configuration updates.
    """

    def get_config(self) -> ApplicationConfig:
        """Get the current application configuration.

        Returns:
            Current application configuration object
        """
        ...

    async def reload_from_source(
        self, source: str
    ) -> Result[ApplicationConfig, ConfigurationError]:
        """Reload configuration from a source.

        Args:
            source: Configuration source (file path, URL, etc.)

        Returns:
            Result with new configuration or error details
        """
        ...

    def validate_config(self) -> Result[ApplicationConfig, ConfigurationError]:
        """Validate the current configuration.

        Returns:
            Result with validated configuration or error details
        """
        ...


@runtime_checkable
class ContentTypeRegistryProtocol(ServiceProtocol, Protocol):
    """Protocol for content type registry services.

    Manages registration and lookup of content type handlers
    and validation logic.
    """

    def register_content_type(self, content_type: str, handler: type) -> None:
        """Register a content type handler.

        Args:
            content_type: Type identifier (e.g., 'spell', 'creature')
            handler: Handler class for this content type
        """
        ...

    def get_content_handler(self, content_type: str) -> type | None:
        """Get handler for a content type.

        Args:
            content_type: Type identifier to look up

        Returns:
            Handler class or None if not registered
        """
        ...

    def get_registered_types(self) -> list[str]:
        """Get list of all registered content types.

        Returns:
            List of registered content type identifiers
        """
        ...


@runtime_checkable
class DisplayManagerProtocol(ServiceProtocol, ConfigurableServiceProtocol, Protocol):
    """Protocol for display and UI management services.

    Handles progress displays, user interaction, and output formatting.
    Supports hot-reload for display preference changes.
    """

    def progress(self, description: str) -> object:
        """Create a progress context manager.

        Args:
            description: Description of the operation

        Returns:
            Progress context manager
        """
        ...

    def add_task(self, description: str, total: int | None = None) -> str:
        """Add a progress tracking task.

        Args:
            description: Task description
            total: Total units of work (None for indeterminate)

        Returns:
            Task identifier for updates
        """
        ...

    def update_task(
        self, task_id: str, completed: int | None = None, description: str | None = None
    ) -> None:
        """Update progress on a task.

        Args:
            task_id: Task identifier from add_task
            completed: Units completed
            description: Updated description
        """
        ...


@runtime_checkable
class ContentFactoryProtocol(ServiceProtocol, Protocol):
    """Protocol for content factory services.

    Handles creation and instantiation of content objects
    from raw data.
    """

    def create_content(self, content_type: str, data: dict) -> object:
        """Create content object from data.

        Args:
            content_type: Type of content to create
            data: Raw content data

        Returns:
            Created content object
        """
        ...

    def supports_content_type(self, content_type: str) -> bool:
        """Check if factory supports a content type.

        Args:
            content_type: Type to check

        Returns:
            True if supported
        """
        ...


@runtime_checkable
class EntryTypeRegistryProtocol(ServiceProtocol, Protocol):
    """Protocol for entry type registry services.

    Manages registration and lookup of entry type processors
    for different content entry formats.
    """

    def register_entry_type(self, entry_type: str, processor: type) -> None:
        """Register an entry type processor.

        Args:
            entry_type: Type identifier
            processor: Processor class for this entry type
        """
        ...

    def get_entry_processor(self, entry_type: str) -> type | None:
        """Get processor for an entry type.

        Args:
            entry_type: Type identifier

        Returns:
            Processor class or None if not registered
        """
        ...


@runtime_checkable
class ReferenceManagerProtocol(ServiceProtocol, Protocol):
    """Protocol for reference management services.

    Handles cross-reference resolution and tracking within
    and between content objects.
    """

    def add_reference(self, source: str, target: str, ref_type: str) -> None:
        """Add a reference relationship.

        Args:
            source: Source content identifier
            target: Target content identifier
            ref_type: Type of reference relationship
        """
        ...

    def resolve_reference(self, source: str, ref_type: str) -> list[str]:
        """Resolve references from a source.

        Args:
            source: Source content identifier
            ref_type: Type of reference to resolve

        Returns:
            List of target identifiers
        """
        ...

    def get_references_to(self, target: str) -> list[tuple[str, str]]:
        """Get all references pointing to a target.

        Args:
            target: Target content identifier

        Returns:
            List of (source, ref_type) tuples
        """
        ...
