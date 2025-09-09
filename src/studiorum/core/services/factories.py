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

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from studiorum.core.error_types import (
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
)
from studiorum.core.logging import get_logger
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.fluff import BaseFluff
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.result import Error, Result, Success

from .protocols import (
    AsyncResourceProtocol,
    CacheProtocol,
    ConfigurableServiceProtocol,
    ConfigurationProtocol,
    ContentAttributionProtocol,
    ContentFactoryProtocol,
    ContentTypeRegistryProtocol,
    DisplayManagerProtocol,
    EntryTypeRegistryProtocol,
    FluffDeduplicatorProtocol,
    OmnidexerProtocol,
    ReferenceManagerProtocol,
    ServiceProtocol,
    SourceManagerProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from studiorum.cli.display_manager import DisplayManager
    from studiorum.core.cache import CacheManager
    from studiorum.core.config.unified_config import ApplicationConfig
    from studiorum.core.entry_registry import EntryTypeRegistry
    from studiorum.core.interfaces import ContentTypeRegistry
    from studiorum.core.loaders.content_factory import ContentFactory
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.core.services.container import ServiceContainer
    from studiorum.core.text.protocols import TextExtractionProtocol
    from studiorum.core.text.tag_resolver import TagResolver
    from studiorum.core.unified_references import ReferenceManager
    from studiorum.latex_engine.formatters.protocols import LaTeXFormattingProtocol
    from studiorum.latex_engine.services.protocols import (
        ContextBoundTemplateProtocol,
        TemplateServiceProtocol,
    )
    from studiorum.renderers.core.interfaces import RenderingContext

logger = get_logger(__name__)


# Configuration Services


def create_configuration_service_sync(
    config_override: ApplicationConfig | None = None,
) -> ConfigurationProtocol:
    """Synchronous factory for configuration service with hot-reload support.

    This is the sync alternative to create_configuration_service for CLI usage.

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

            logger.debug("Configuration hot-reloaded")

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
                # For now, return current config as placeholder
                # TODO: Implement proper config file reloading from source
                await self.reload_config(self._config)
                return Success(self._config)

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

    # Get configuration synchronously
    if config_override is not None:
        config = config_override
    else:
        # Load configuration synchronously for CLI usage
        from studiorum.core.config.unified_config import (
            ApplicationConfig,
            get_default_config_path,
        )

        config_path = get_default_config_path()

        if config_path.exists():
            # For sync loading, use simple file reading
            import yaml

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                config = ApplicationConfig.model_validate(config_data)
                logger.debug(f"Configuration loaded from {config_path}")
            except Exception as e:
                # File exists but failed to load, use default with warning
                config = ApplicationConfig()
                logger.warning(f"Failed to load config from {config_path}: {e}")
        else:
            # No config file, use default
            config = ApplicationConfig()
            logger.debug(f"No config file found at {config_path}, using defaults")

    return ConfigurationService(config)


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

            logger.debug("Configuration hot-reloaded")

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
                # For now, return current config as placeholder
                # TODO: Implement proper config file reloading from source
                await self.reload_config(self._config)
                return Success(self._config)

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
        # Load configuration from file using ConfigurationManager
        from studiorum.core.config.dynamic_manager import ConfigurationManager
        from studiorum.core.config.unified_config import get_default_config_path

        config_path = get_default_config_path()
        manager = ConfigurationManager(config_path)

        if config_path.exists():
            # Load from file if it exists
            result = await manager.load_config_from_file()
            if result.is_success():
                config = result.unwrap()
                logger.debug(f"Configuration loaded from {config_path}")
            else:
                # File exists but failed to load, use default with warning
                from studiorum.core.config.unified_config import ApplicationConfig
                from studiorum.core.result import Error

                config = ApplicationConfig()
                if isinstance(result, Error):
                    logger.warning(
                        f"Failed to load config from {config_path}: {result.error.message}"
                    )
        else:
            # No config file, use default
            from studiorum.core.config.unified_config import ApplicationConfig

            config = ApplicationConfig()
            logger.debug(f"No config file found at {config_path}, using defaults")

    return ConfigurationService(config)


# Core Async Resource Services


def create_omnidexer_service_sync(
    config_service: ConfigurationProtocol,
    *,
    progress_callback: ProgressCallback | None = None,
) -> OmnidexerProtocol:
    """Synchronous factory for omnidexer service for CLI usage.

    This is the sync alternative to create_omnidexer_service for CLI commands.

    Args:
        config_service: Configuration service for accessing app config

    Returns:
        Omnidexer service implementing OmnidexerProtocol
    """

    class SyncOmnidexerService(OmnidexerProtocol):
        """Sync omnidexer service for CLI usage."""

        def __init__(
            self,
            config: ApplicationConfig,
            progress_callback: ProgressCallback | None = None,
        ) -> None:
            self._config = config
            self._omnidexer: Omnidexer | None = None
            self._initialized = False
            self._data_loaded = False
            self._progress_callback = progress_callback

        def get_service_name(self) -> str:
            return "OmnidexerService"

        def initialize_sync(self) -> None:
            """Synchronous initialization of omnidexer resources."""
            if self._initialized:
                return

            logger.debug("Initializing omnidexer service synchronously")

            try:
                from studiorum.core.loaders.omnidexer import Omnidexer

                self._omnidexer = Omnidexer()

                # DON'T load all data immediately - let lazy loading work
                # The omnidexer will load data on-demand when first accessed

                self._initialized = True
                logger.debug(
                    "Omnidexer service initialized successfully (sync, lazy loading enabled)"
                )

            except Exception:
                logger.exception("Failed to initialize omnidexer service synchronously")
                raise

        async def initialize(self) -> None:
            """Async initialization wrapper for compatibility."""
            self.initialize_sync()

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

        def set_progress_callback(self, callback: ProgressCallback | None) -> None:
            """Set progress callback for data loading operations."""
            self._progress_callback = callback

        def _ensure_data_loaded(self) -> None:
            """Ensure data is loaded on first access (lazy loading)."""
            if not self._data_loaded and self._omnidexer:
                logger.debug("Lazy loading omnidexer data on first access")

                # Use progress callback if available
                if self._progress_callback:
                    operation_id = self._progress_callback.start_operation(
                        "Loading 5e content data", metadata={"stage": "lazy_loading"}
                    )
                    try:
                        self._omnidexer.load_all_data(
                            progress_callback=self._progress_callback
                        )
                        self._progress_callback.complete_operation(
                            operation_id, result="Content data loaded successfully"
                        )
                    except Exception as e:
                        self._progress_callback.complete_operation(
                            operation_id, error=e
                        )
                        raise
                else:
                    # Fallback to original behavior without progress
                    self._omnidexer.load_all_data()

                # Resolve copy references after data loading (matches async version)
                self._resolve_copy_references()

                self._data_loaded = True

        def _resolve_copy_references(self) -> None:
            """Resolve copy references after data loading (sync version)."""
            if not self._omnidexer:
                return

            try:
                from studiorum.core.resolvers.copy_resolver import CopyResolver

                copy_resolver = CopyResolver(self._omnidexer)
                copy_resolver.resolve_copies_in_omnidexer()

            except Exception as e:
                logger.warning(f"Failed to resolve copy references: {e}")

        async def load_content_sources(self, sources: list[str]) -> None:
            """Load content from specified sources."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            logger.debug(f"Loading content sources: {sources}")

        def get_content(self, content_type: str, identifier: str) -> object:
            """Get specific content by type and identifier."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            results = self._omnidexer.search_by_name_prefix(identifier)
            return results[0] if results else None

        def search(
            self, query: str, content_type: ContentType | None = None, limit: int = 50
        ) -> list[BaseContent]:
            """Search for content matching the query."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            results = self._omnidexer.search(query, content_type, limit)
            return list(results)

        def get_all_by_type(self, content_type: ContentType) -> list[BaseContent]:
            """Get all content of a specific type."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            results = self._omnidexer.get_all_by_type(content_type)
            return list(results)

        def get_all_by_source(self, source: str) -> list[BaseContent]:
            """Get all content from a specific source."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            return self._omnidexer.get_all_by_source(source)

        def find(
            self, content_type: ContentType, name: str, source: str | None = None
        ) -> BaseContent | None:
            """Find content by type, name, and optionally source."""
            if not self._initialized:
                logger.warning("Omnidexer not initialized - returning None")
                return None

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            if self._omnidexer is not None and hasattr(self._omnidexer, "find"):
                return self._omnidexer.find(content_type, name, source)
            else:
                return None

        def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
            """Find all content matching type and name across all sources."""
            if not self._initialized:
                logger.warning("Omnidexer not initialized - returning empty results")
                return []

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            if self._omnidexer is not None and hasattr(self._omnidexer, "find_all"):
                return self._omnidexer.find_all(content_type, name)
            else:
                return []

        async def ensure_sources_ready(self) -> None:
            """Ensure all content sources are loaded and ready."""
            if not self._initialized:
                self.initialize_sync()
            # Ensure data is loaded when sources are needed
            self._ensure_data_loaded()

        async def search_content_async(
            self,
            query: str,
            content_type: str | None = None,
            context: object | None = None,
            limit: int = 50,
        ) -> object:
            """High-performance async search with intelligent caching."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            results = self.search(query)
            return {"success": True, "data": results[:limit]}

        async def get_content_async(
            self,
            content_type: str,
            name: str,
            source: str | None = None,
            context: object | None = None,
        ) -> object:
            """Async content retrieval with intelligent caching."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            result = self.get_content(content_type, name)
            return {"success": True, "data": result}

        def get_fluff_for_content(
            self, content: BaseContent, content_type: ContentType
        ) -> BaseFluff | None:
            """Get fluff entry for the given content, if available."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # Lazy load data when first accessed
            self._ensure_data_loaded()

            return self._omnidexer.get_fluff_for_content(content, content_type)

        def get_performance_statistics(self) -> dict[str, object]:
            """Get comprehensive performance statistics."""
            return {
                "initialized": self._initialized,
                "omnidexer_type": "SyncOmnidexerService",
                "performance_mode": "sync_cli_optimized",
            }

    # Get configuration from injected service
    config = config_service.get_config()

    # Create and initialize service synchronously
    service = SyncOmnidexerService(config, progress_callback)
    service.initialize_sync()

    return service


async def create_omnidexer_service(
    config_service: ConfigurationProtocol,
    *,
    progress_callback: ProgressCallback | None = None,
) -> OmnidexerProtocol:
    """Factory for async omnidexer with proper resource management.

    Args:
        config_service: Configuration service for accessing app config

    Returns:
        Omnidexer service implementing OmnidexerProtocol
    """

    class AsyncOmnidexerService(OmnidexerProtocol):
        """Async omnidexer service with resource management."""

        def __init__(
            self,
            config: ApplicationConfig,
            progress_callback: ProgressCallback | None = None,
        ) -> None:
            self._config = config
            self._omnidexer: Omnidexer | None = None
            self._initialized = False
            self._progress_callback = progress_callback

        def get_service_name(self) -> str:
            return "OmnidexerService"

        def set_progress_callback(self, callback: ProgressCallback | None) -> None:
            """Set progress callback for data loading operations."""
            self._progress_callback = callback

        async def initialize(self) -> None:
            """Async initialization of omnidexer resources."""
            if self._initialized:
                return

            logger.debug("Initializing omnidexer service")

            try:
                from studiorum.core.loaders.omnidexer import Omnidexer
                from studiorum.core.loaders.unified_source_manager import (
                    UnifiedSourceManager,
                )

                # Create UnifiedSourceManager with configuration
                config = config_service.get_config()
                unified_source_manager = UnifiedSourceManager(config)

                # Initialize the source manager properly in async context
                await unified_source_manager.initialize()

                # Create omnidexer with configured source manager
                self._omnidexer = Omnidexer(source_manager=unified_source_manager)

                # Load all data (this will use the already initialized source manager)
                if self._progress_callback:
                    operation_id = self._progress_callback.start_operation(
                        "Loading 5e content data",
                        metadata={"stage": "async_initialization"},
                    )
                    try:
                        self._omnidexer.load_all_data(
                            progress_callback=self._progress_callback
                        )
                        self._progress_callback.complete_operation(
                            operation_id, result="Content data loaded successfully"
                        )
                    except Exception as e:
                        self._progress_callback.complete_operation(
                            operation_id, error=e
                        )
                        raise
                else:
                    self._omnidexer.load_all_data()

                # Resolve copy references
                await self._resolve_copy_references()

                self._initialized = True
                logger.debug("Omnidexer service initialized successfully")

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
            logger.debug(f"Loading content sources: {sources}")

        def get_content(self, content_type: str, identifier: str) -> object:
            """Get specific content by type and identifier."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            # Use actual omnidexer search by name - simplified implementation
            results = self._omnidexer.search_by_name_prefix(identifier)
            return results[0] if results else None

        def search(
            self, query: str, content_type: ContentType | None = None, limit: int = 50
        ) -> list[BaseContent]:
            """Search for content matching the query."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")
            # Use actual omnidexer search methods with matching signature
            results = self._omnidexer.search(query, content_type, limit)
            return list(results)

        def get_all_by_type(self, content_type: ContentType) -> list[BaseContent]:
            """Get all content of a specific type."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            results = self._omnidexer.get_all_by_type(content_type)
            return list(results)

        def find(
            self, content_type: ContentType, name: str, source: str | None = None
        ) -> BaseContent | None:
            """Find content by type, name, and optionally source."""
            if not self._initialized:
                logger.warning("Omnidexer not initialized - returning None")
                return None

            if self._omnidexer is not None and hasattr(self._omnidexer, "find"):
                return self._omnidexer.find(content_type, name, source)
            else:
                return None

        def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
            """Find all content matching type and name across all sources."""
            if not self._initialized:
                logger.warning("Omnidexer not initialized - returning empty results")
                return []

            # Delegate to the concrete omnidexer
            if self._omnidexer is not None and hasattr(self._omnidexer, "find_all"):
                return self._omnidexer.find_all(content_type, name)
            else:
                # Fallback implementation
                return []

        async def ensure_sources_ready(self) -> None:
            """Ensure all content sources are loaded and ready."""
            if not self._initialized:
                await self.initialize()

        # Enhanced performance methods for P5 optimization
        async def search_content_async(
            self,
            query: str,
            content_type: str | None = None,
            context: object | None = None,
            limit: int = 50,
        ) -> object:
            """High-performance async search with intelligent caching."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # For now, delegate to synchronous search
            # TODO: Implement proper async search in P5 Phase 2
            results = self.search(query)

            # Simulate result wrapper - would be proper Result[List[BaseContent], ContentNotFoundError] in full implementation
            return {"success": True, "data": results[:limit]}

        async def get_content_async(
            self,
            content_type: str,
            name: str,
            source: str | None = None,
            context: object | None = None,
        ) -> object:
            """Async content retrieval with intelligent caching."""
            if not self._omnidexer:
                raise RuntimeError("Omnidexer not initialized")

            # For now, delegate to synchronous get_content
            # TODO: Implement proper async retrieval in P5 Phase 2
            result = self.get_content(content_type, name)

            # Simulate result wrapper - would be proper Result[Optional[BaseContent], ContentNotFoundError] in full implementation
            return {"success": True, "data": result}

        def get_performance_statistics(self) -> dict[str, object]:
            """Get comprehensive performance statistics."""
            return {
                "initialized": self._initialized,
                "omnidexer_type": "AsyncOmnidexerService",
                "performance_mode": "legacy_compatibility",
            }

        async def _resolve_copy_references(self) -> None:
            """Resolve copy references after data loading."""
            if not self._omnidexer:
                return

            try:
                from studiorum.core.resolvers.copy_resolver import CopyResolver

                copy_resolver = CopyResolver(self._omnidexer)
                copy_resolver.resolve_copies_in_omnidexer()

            except Exception as e:
                logger.warning(f"Failed to resolve copy references: {e}")

    # Get configuration from injected service
    config = config_service.get_config()

    # Create and initialize service
    service = AsyncOmnidexerService(config, progress_callback)
    await service.initialize()

    return service


# Hot-Reloadable Scoped Services


def create_tag_resolver_service(
    omnidexer: OmnidexerProtocol,
    config_service: ConfigurationProtocol,
) -> TagResolverProtocol:
    """Factory for configurable tag resolver service.

    Args:
        omnidexer: Omnidexer service for content resolution
        config_service: Configuration service for accessing app config

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
                from studiorum.core.text.tag_resolver import TagResolver

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
            logger.debug("Reloading tag resolver configuration")
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

        def process_text(
            self, text: str, context: RenderingContext | None = None
        ) -> str:
            """Process text with tags using the underlying TagResolver.

            This method provides the interface expected by the entry processor.
            """
            if not self._tag_resolver:
                raise RuntimeError("TagResolver not initialized")
            return self._tag_resolver.process_text(text, context)

    # Get configuration from injected service
    config = config_service.get_config()

    return ConfigurableTagResolverService(omnidexer, config)


# Infrastructure Services


def create_content_type_registry_service() -> ContentTypeRegistryProtocol:
    """Factory for content type registry service.

    Returns:
        Content type registry implementing ContentTypeRegistryProtocol
    """

    class ContentTypeRegistryService:
        """Content type registry service wrapping the legacy ContentTypeRegistry."""

        def __init__(self) -> None:
            from studiorum.core.interfaces import ContentTypeRegistry
            from studiorum.core.models.content import ContentType

            self._legacy_registry = ContentTypeRegistry()
            # Register default content types
            self._initialize_default_types()

        def get_service_name(self) -> str:
            return "ContentTypeRegistryService"

        def _initialize_default_types(self) -> None:
            """Initialize default content type registrations."""
            try:
                from studiorum.core.models.content import ContentType

                # The legacy registry will be populated by the system initialization
                # This service provides protocol compliance without duplicating state
                logger.debug("ContentTypeRegistry service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize default content types: {e}")

        def register_content_type(self, content_type: str, handler: type) -> None:
            """Register a content type handler."""
            # For now, this is a no-op since the legacy registry doesn't support dynamic registration
            # In the future, this could be enhanced to support runtime registration
            logger.debug(
                f"Content type registration requested: {content_type} -> {handler}"
            )

        def get_content_handler(self, content_type: str) -> type | None:
            """Get handler for a content type."""
            # Return None for now - the legacy registry doesn't provide handler lookup
            return None

        def get_registered_types(self) -> list[str]:
            """Get list of registered content types."""
            # Return the content types from the legacy registry
            content_types = self._legacy_registry.get_all_types()
            return [ct.value for ct in content_types]

        # Provide access to the underlying registry for legacy code
        def get_legacy_registry(self) -> ContentTypeRegistry:
            """Get the underlying ContentTypeRegistry for legacy compatibility."""
            return self._legacy_registry

    return ContentTypeRegistryService()


async def create_display_manager_service(
    container: ServiceContainer,
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
                from studiorum.cli.display_manager import DisplayManager

                self._display_manager = DisplayManager()
                logger.debug("Display manager initialized")
            except Exception:
                logger.exception("Failed to initialize display manager")
                raise

        async def reload_config(self, new_config: ApplicationConfig) -> None:
            """Hot-reload display configuration."""
            logger.debug("Reloading display manager configuration")
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
            from studiorum.cli.display_manager import TaskID

            actual_task_id = (
                TaskID(int(task_id)) if isinstance(task_id, str) else task_id
            )
            self._display_manager.update_task(actual_task_id, advance=completed)

    # Get configuration from container
    config_service = await container.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
    config = config_service.get_config()

    return DisplayManagerService(config)


def create_content_factory_service() -> ContentFactoryProtocol:
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
                from studiorum.core.loaders.content_factory import ContentFactory

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
            from studiorum.core.interfaces import ContentType

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


def create_entry_registry_service() -> EntryTypeRegistryProtocol:
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
                from studiorum.core.entry_registry import EntryTypeRegistry

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
    container: ServiceContainer,
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
                from studiorum.core.unified_references import ReferenceManager

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
            from studiorum.core.unified_references import Reference

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


def create_cache_service() -> CacheProtocol:
    """Factory for cache service.

    Returns:
        Cache service implementing CacheProtocol
    """

    class CacheService:
        """Cache service wrapping diskcache with protocol interface."""

        def __init__(self) -> None:
            self._cache_manager: type[CacheManager] | None = None
            self._initialize_cache()

        def get_service_name(self) -> str:
            return "CacheService"

        def _initialize_cache(self) -> None:
            """Initialize cache manager."""
            try:
                from studiorum.core.cache import CacheManager

                self._cache_manager = CacheManager
                logger.debug("Cache service initialized")
            except Exception:
                logger.exception("Failed to initialize cache service")
                raise

        def get(self, key: str, default: object = None) -> object:
            """Get value from cache."""
            if not self._cache_manager:
                raise RuntimeError("Cache not initialized")
            cache = self._cache_manager.get_instance()
            return cache.get(key, default)

        def set(self, key: str, value: object, expire: float | None = None) -> None:
            """Set value in cache."""
            if not self._cache_manager:
                raise RuntimeError("Cache not initialized")
            cache = self._cache_manager.get_instance()
            cache.set(key, value, expire=expire)

        def delete(self, key: str) -> bool:
            """Delete key from cache."""
            if not self._cache_manager:
                raise RuntimeError("Cache not initialized")
            cache = self._cache_manager.get_instance()
            return cache.delete(key)

        def clear(self) -> None:
            """Clear entire cache."""
            if not self._cache_manager:
                raise RuntimeError("Cache not initialized")
            self._cache_manager.clear()

        def get_stats(self) -> dict[str, object]:
            """Get cache statistics."""
            if not self._cache_manager:
                return {}
            return self._cache_manager.get_stats()

    return CacheService()


# Source Management Services


def create_data_source_manager_service_sync(
    config_service: ConfigurationProtocol,
) -> SourceManagerProtocol:
    """Synchronous factory for data source manager service for CLI usage.

    Args:
        config_service: Configuration service dependency

    Returns:
        Data source manager service implementing SourceManagerProtocol
    """
    from studiorum.core.loaders.unified_source_manager import UnifiedSourceManager

    # Get configuration from the service and pass to UnifiedSourceManager
    config = config_service.get_config()
    unified_source_manager = UnifiedSourceManager(config)

    # For CLI usage, initialize synchronously (no async resources needed)
    logger.debug("UnifiedSourceManager service initialized successfully (sync)")
    return unified_source_manager


async def create_data_source_manager_service(
    config_service: ConfigurationProtocol,
) -> SourceManagerProtocol:
    """Factory for data source manager service with async resource management.

    Args:
        config_service: Configuration service dependency

    Returns:
        Data source manager service implementing SourceManagerProtocol
    """
    from studiorum.core.loaders.unified_source_manager import UnifiedSourceManager

    # Get configuration from the service and pass to UnifiedSourceManager
    config = config_service.get_config()
    unified_source_manager = UnifiedSourceManager(config)

    # The UnifiedSourceManager implements AsyncResourceProtocol
    # Initialize it immediately in the factory
    await unified_source_manager.initialize()

    logger.debug("UnifiedSourceManager service initialized successfully")
    return unified_source_manager


def create_content_attribution_service() -> ContentAttributionProtocol:
    """Factory for content attribution service.

    Returns:
        Content attribution service implementing ContentAttributionProtocol
    """
    from studiorum.core.loaders.content_attribution_manager import (
        ContentAttributionManager,
    )

    content_attribution = ContentAttributionManager()
    logger.debug("ContentAttributionManager service initialized successfully")
    return content_attribution


def create_text_extractor_service() -> TextExtractionProtocol:
    """Factory for text extraction service.

    Returns:
        Text extraction service implementing TextExtractionProtocol
    """
    from studiorum.core.text.text_extractor import TextExtractor

    text_extractor = TextExtractor()
    logger.debug("TextExtractor service initialized successfully")
    return text_extractor


def create_latex_formatter_service() -> LaTeXFormattingProtocol:
    """Factory for LaTeX formatting service.

    Returns:
        LaTeX formatting service implementing LaTeXFormattingProtocol
    """
    from studiorum.latex_engine.formatters.latex_formatter import LaTeXFormatter

    latex_formatter = LaTeXFormatter()
    logger.debug("LaTeXFormatter service initialized successfully")
    return latex_formatter


def create_template_service_with_components(
    text_extractor: TextExtractionProtocol,
    latex_formatter: LaTeXFormattingProtocol,
    tag_resolver: TagResolverProtocol,
    omnidexer: OmnidexerProtocol,
) -> TemplateServiceProtocol:
    """Factory for component-based template service.

    Args:
        text_extractor: Text extraction component
        latex_formatter: LaTeX formatting component
        tag_resolver: Tag resolver service
        omnidexer: Omnidexer service

    Returns:
        Template service with injected components
    """
    from studiorum.latex_engine.services.template_service import TemplateService

    template_service = TemplateService(
        text_extractor=text_extractor,
        latex_formatter=latex_formatter,
        tag_resolver=tag_resolver,
        omnidexer=omnidexer,
    )
    logger.debug("TemplateService with components initialized successfully")
    return template_service


def create_context_bound_template_service(
    template_service: TemplateServiceProtocol,
    content_tracker: ContentTracker,
) -> ContextBoundTemplateProtocol:
    """Factory for context-bound template service with clean APIs.

    Args:
        template_service: Base template service to bind context to
        content_tracker: ContentTracker context to bind for all operations

    Returns:
        Context-bound template service with clean APIs (no tracker parameters)
    """
    from studiorum.latex_engine.services.context_bound_template_service import (
        ContextBoundTemplateService,
    )

    bound_service = ContextBoundTemplateService(template_service, content_tracker)
    logger.debug("ContextBoundTemplateService initialized successfully")
    return bound_service


# Fluff Services


def create_fluff_deduplicator_service(
    container: ServiceContainer | None = None,
) -> FluffDeduplicatorProtocol:
    """Factory for fluff deduplication service.

    The FluffDeduplicator helps prevent duplicate narrative content
    in compendiums by detecting identical fluff entries and providing
    cross-references instead of duplicating content.

    Args:
        container: Service container for dependency injection (optional)

    Returns:
        FluffDeduplicator service instance
    """
    from .fluff_deduplicator import (
        DeduplicationStrategy,
        create_fluff_deduplicator_service,
    )

    # Use strict deduplication by default - can be configured via service creation
    service = create_fluff_deduplicator_service(
        strategy=DeduplicationStrategy.STRICT,
        content_tracker=None,  # Will be injected when needed
    )
    logger.debug("FluffDeduplicator service initialized successfully")
    return service
