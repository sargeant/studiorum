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

# Import progress protocols for re-export
from studiorum.core.protocols.progress import ProgressAwareService, ProgressCallback

# Template service protocol defined below with other protocols

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from studiorum.core.config.unified_config import ApplicationConfig
    from studiorum.core.error_types import ConfigurationError
    from studiorum.core.interfaces import ContentTypeRegistry
    from studiorum.core.models.content import BaseContent, ContentType
    from studiorum.core.models.fluff import BaseFluff
    from studiorum.core.protocols.progress import ProgressCallback
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.core.result import Result
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
    access to 5e content data. Requires async initialization due
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

    def get_all_by_type(self, content_type: ContentType) -> list[BaseContent]:
        """Get all content of a specific type.

        Args:
            content_type: Content type enum or string identifier

        Returns:
            List of all content matching the specified type
        """
        ...

    def find(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Find content by type, name, and optionally source.

        Args:
            content_type: Content type enum or string identifier
            name: Content name to search for
            source: Optional source abbreviation to restrict search

        Returns:
            First content matching the specified criteria, or None if not found
        """
        ...

    def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
        """Find all content matching type and name across all sources.

        Args:
            content_type: Content type enum or string identifier
            name: Content name to search for

        Returns:
            List of all content matching the specified type and name
        """
        ...

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Set progress callback for data loading operations.

        Args:
            callback: Progress callback to report loading progress (None to disable)
        """
        ...


@runtime_checkable
class TagResolverProtocol(ServiceProtocol, ConfigurableServiceProtocol, Protocol):
    """Protocol for tag resolution and rendering services.

    The tag resolver handles parsing and rendering of {@tag} syntax
    in 5e content. Supports hot-reload for rendering configuration
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

    def process_text(self, text: str, context: RenderingContext | None = None) -> str:
        """Process text containing tags and return rendered text.

        Args:
            text: Text containing tags to process
            context: Rendering context for tag resolution

        Returns:
            Processed text with tags resolved
        """
        ...


@runtime_checkable
class TemplateServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for template processing services.

    Provides explicit context passing for template rendering, eliminating
    the need for stack inspection and ensuring consistent behavior across
    all template rendering operations.
    """

    # Legacy method render_entry_description removed - use RecursiveEntryProcessor instead


@runtime_checkable
class TextExtractionProtocol(ServiceProtocol, Protocol):
    """Protocol for text extraction from 5etools entry structures."""

    def extract_from_entry(self, entry: Any) -> str:
        """Extract full text including entry names.

        Args:
            entry: Entry object in various 5etools formats

        Returns:
            Extracted text content with names included
        """
        ...

    def extract_content_only_from_entry(self, entry: Any) -> str:
        """Extract content text excluding entry names.

        Args:
            entry: Entry object in various 5etools formats

        Returns:
            Extracted text content without entry names
        """
        ...


@runtime_checkable
class LaTeXFormattingProtocol(ServiceProtocol, Protocol):
    """Protocol for LaTeX formatting operations."""

    def format_text(self, text: str, original_entry: Any = None) -> str:
        """Apply LaTeX formatting to processed text.

        Args:
            text: Text content to format
            original_entry: Original entry object for structure-based formatting

        Returns:
            LaTeX-formatted text
        """
        ...

    def escape_latex_chars(self, text: str) -> str:
        """Escape LaTeX special characters.

        Args:
            text: Text to escape

        Returns:
            Text with LaTeX special characters escaped
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

    def get_legacy_registry(self) -> ContentTypeRegistry:
        """Get the underlying ContentTypeRegistry for legacy compatibility.

        Returns:
            Legacy content type registry instance
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


@runtime_checkable
class SourceManagerProtocol(ServiceProtocol, AsyncResourceProtocol, Protocol):
    """Protocol for source management services.

    Manages data repositories (GitHub repos, local directories) and provides
    unified access to 5e content files. Separates data source management
    from content attribution concerns.
    """

    async def ensure_sources_ready(self) -> None:
        """Ensure all data sources are loaded and ready.

        This method handles async source preparation like GitHub
        repository cloning or remote data downloads.

        Raises:
            SourceManagerError: If source preparation fails
        """
        ...

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type.

        For adventures and books, this should return only metadata files to prevent
        duplicate loading. Content files are loaded on-demand by ContentResolver.

        Returns:
            Dictionary mapping content types to data file paths
        """
        ...

    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files organized by content type.

        Metadata files contain lightweight index information (names, IDs, TOC)
        and are loaded by the omnidexer. Content files are excluded.

        Returns:
            Dictionary mapping content types to metadata file paths
        """
        ...

    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to content files organized by content type.

        Content files contain the actual entry data for adventures and books.
        These are loaded on-demand and merged with metadata.

        Returns:
            Dictionary mapping content types to content file paths
        """
        ...

    def get_source_statistics(self) -> dict[str, Any]:
        """Get statistics about configured sources.

        Returns:
            Dictionary with source counts, sync status, and performance metrics
        """
        ...

    def clear_cache(self) -> None:
        """Clear internal caches to force reload of data sources.

        This method forces a complete rebuild of the internal content index
        and should be called when sources have been modified externally.
        """
        ...


@runtime_checkable
class ContentAttributionProtocol(ServiceProtocol, Protocol):
    """Protocol for content source attribution services.

    Manages 5e source attribution (PHB, MM, DMG, etc.) and priority
    resolution. Separates content attribution from data repository concerns.
    """

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information.

        Args:
            source_abbrev: Source abbreviation (e.g., 'PHB', 'MM', 'DMG')

        Returns:
            Source information dictionary or None if not found
        """
        ...

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority).

        Args:
            source_abbrev: Source abbreviation to check

        Returns:
            Priority value (0 = highest priority)
        """
        ...

    def get_all_sources(self) -> list[str]:
        """Get list of all known source abbreviations.

        Returns:
            List of source abbreviations in priority order
        """
        ...

    def get_source_metadata(self, source_abbrev: str) -> dict[str, Any] | None:
        """Get detailed metadata for a source.

        Args:
            source_abbrev: Source abbreviation

        Returns:
            Metadata dictionary with publication info, type, etc.
        """
        ...


@runtime_checkable
class CacheProtocol(ServiceProtocol, Protocol):
    """Protocol for cache management services.

    Provides unified caching interface for improved performance
    across the application.
    """

    def get(self, key: str, default: object = None) -> object:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        ...

    def set(self, key: str, value: object, expire: float | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
        """
        ...

    def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        ...

    def clear(self) -> None:
        """Clear entire cache."""
        ...

    def get_stats(self) -> dict[str, object]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics and metrics
        """
        ...


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@runtime_checkable
class FluffDeduplicatorProtocol(ServiceProtocol, Protocol):
    """Protocol for fluff deduplication services.

    Handles deduplication of fluff content to prevent duplicate
    narrative content in compendiums, particularly useful for
    shared content like dragon lairs that appear across multiple creatures.
    """

    def should_include(self, fluff: BaseFluff) -> bool:
        """Check if fluff content is unique and should be included.

        Args:
            fluff: The fluff entry to check

        Returns:
            True if the fluff content should be included, False if it's a duplicate
        """
        ...

    def get_duplicate_references(self, fluff: BaseFluff) -> list[str]:
        """Get list of content names that reference the same fluff.

        Args:
            fluff: The fluff entry to check

        Returns:
            List of content names that would have shown the same fluff content
        """
        ...

    def get_statistics(self) -> dict[str, int]:
        """Get deduplication statistics.

        Returns:
            Dictionary with statistics about processed and deduplicated content
        """
        ...


@runtime_checkable
class FluffImageExtractorProtocol(ServiceProtocol, Protocol):
    """Protocol for fluff image extraction services (Phase 5).

    Handles extraction of images from fluff content for integration
    with the image processing system.
    """

    def extract_images_from_fluff(self, fluff: BaseFluff) -> list[Any]:
        """Extract all images from a fluff entry.

        Args:
            fluff: The fluff entry to extract images from

        Returns:
            List of FluffImageInfo objects with image details
        """
        ...

    def filter_images_by_type(
        self, images: list[Any], image_types: list[str]
    ) -> list[Any]:
        """Filter images by their type.

        Args:
            images: List of image info objects
            image_types: List of image types to include

        Returns:
            Filtered list of images
        """
        ...

    def filter_images_by_format(
        self, images: list[Any], supported_only: bool = True
    ) -> list[Any]:
        """Filter images by format support.

        Args:
            images: List of image info objects
            supported_only: Whether to include only supported formats

        Returns:
            Filtered list of images
        """
        ...

    def get_image_statistics(self, images: list[Any]) -> dict[str, Any]:
        """Get statistics about extracted images.

        Args:
            images: List of image info objects

        Returns:
            Dictionary with image statistics
        """
        ...

    def create_image_manifest(self, images: list[Any]) -> dict[str, Any]:
        """Create a manifest of all extracted images for future processing.

        Args:
            images: List of image info objects

        Returns:
            Image manifest dictionary suitable for JSON serialization
        """
        ...

    def reset(self) -> None:
        """Reset the deduplicator state for a new document."""
        ...


@runtime_checkable
class ContentListWriterProtocol(ServiceProtocol, Protocol):
    """Protocol for content list writing services.

    Handles writing tracked content to files in enhanced format with counts,
    sources, and metadata. Supports filtering by content type and various
    output formatting options.
    """

    def write_content_list(
        self,
        content_tracker: ContentTracker,
        output_path: Path,
        *,
        content_type_filter: str | None = None,
        title: str | None = None,
        sort_by_count: bool = False,
        include_zero_counts: bool = False,
    ) -> Result[int, Any]:
        """Write tracked content to a file in enhanced format.

        Args:
            content_tracker: ContentTracker instance containing tracked content
            output_path: Path where the content list should be written
            content_type_filter: Optional filter to include only specific content type
            title: Optional title for the content list (e.g., adventure name)
            sort_by_count: If True, sort by reference count (descending), else by name
            include_zero_counts: If True, include content with zero reference counts

        Returns:
            Result containing the number of entries written, or an error
        """
        ...

    def write_all_content_types(
        self,
        content_tracker: ContentTracker,
        output_directory: Path,
        *,
        title: str | None = None,
        sort_by_count: bool = False,
        include_zero_counts: bool = False,
    ) -> Result[dict[str, int], Any]:
        """Write separate files for each content type.

        Args:
            content_tracker: ContentTracker instance containing tracked content
            output_directory: Directory where content type files should be written
            title: Optional title for the content lists
            sort_by_count: If True, sort by reference count (descending), else by name
            include_zero_counts: If True, include content with zero reference counts

        Returns:
            Result containing a dict mapping content type to number of entries written
        """
        ...


# Export all protocols
__all__ = [
    # Base protocols
    "ServiceProtocol",
    "AsyncResourceProtocol",
    "ConfigurableServiceProtocol",
    # Core service protocols
    "OmnidexerProtocol",
    "TagResolverProtocol",
    "ConfigurationProtocol",
    "ContentTypeRegistryProtocol",
    "DisplayManagerProtocol",
    "ContentFactoryProtocol",
    "EntryTypeRegistryProtocol",
    "ReferenceManagerProtocol",
    "SourceManagerProtocol",
    "ContentAttributionProtocol",
    "CacheProtocol",
    # Progress protocols
    "ProgressCallback",
    "ProgressAwareService",
    # Template service protocols
    "TemplateServiceProtocol",
    "TextExtractionProtocol",
    "LaTeXFormattingProtocol",
    # Fluff service protocols (Phase 5)
    "FluffDeduplicatorProtocol",
    "FluffImageExtractorProtocol",
    # Content list writer protocol
    "ContentListWriterProtocol",
]
