"""Data source manager for managing data repositories and file discovery.

This module provides the DataSourceManager class that handles data repository
management (GitHub repos, local directories) separately from content attribution
concerns. This provides the data repository functionality for UnifiedSourceManager.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config.unified_config import ApplicationConfig

from ..config.sources import get_content_config
from ..logging import get_logger
from ..models.content import ContentType
from ..result import Error, Result, Success
from ..sources import ContentSourceManager
from .base import SourceManager

logger = get_logger(__name__)


class DataSourceError(Exception):
    """Base exception for data source operations."""


class SourceNotFoundError(DataSourceError):
    """Source repository not found or accessible."""


class DataSourceManager(SourceManager):
    """Data source manager for handling data repositories.

    Manages data repositories (GitHub repos, local directories) and provides
    unified file discovery and indexing. Separates data repository management
    from content attribution concerns.

    This class implements 5etools dual-file architecture for adventures and books:

    **Metadata Files:**
    - `adventures.json`: Contains lightweight adventure metadata (names, IDs, TOC structure)
    - `books.json`: Contains lightweight book metadata (names, IDs, TOC structure)
    - Loaded by omnidexer during startup for catalog/index population
    - Provide structure and metadata but no actual content entries

    **Content Files:**
    - `adventure-{id}.json`: Contains full adventure content data
    - `book-{id}.json`: Contains full book content data
    - Loaded on-demand when specific content is requested
    - Provide actual entry data but minimal metadata
    - ID is lowercase version of metadata ID (e.g., "CoS" → "adventure-cos.json")

    **Loading Strategy:**
    1. Omnidexer loads only metadata files to build content catalog
    2. ContentResolver loads content files on-demand when adventures/books are accessed
    3. ContentMerger combines metadata structure with content data at runtime
    """

    def __init__(self, app_config: ApplicationConfig | None = None) -> None:
        """Initialize with application configuration.

        Args:
            app_config: Application configuration instance. If None, will load from get_app_config()
                       for backward compatibility (deprecated).
        """
        from studiorum.core.logging import get_logger

        logger = get_logger(__name__)

        # Handle dependency injection vs backward compatibility
        if app_config is None:
            # Backward compatibility mode - load from service container
            from studiorum.core.services.access import get_app_config

            logger.warning(
                "DataSourceManager initialized without dependency injection. "
                "Consider using service container for proper configuration management."
            )
            app_config = get_app_config()

        # Use new data sources configuration if available, fallback to old system
        try:
            import os

            # Check if primary override should be disabled for testing
            disable_primary_override = os.environ.get(
                "STUDIORUM_DISABLE_PRIMARY_OVERRIDE", ""
            ).lower() in ("true", "1", "yes")

            logger.debug(
                f"DataSourceManager: Checking data sources config - has data_sources: {app_config.data_sources is not None}"
            )

            if app_config.data_sources and not disable_primary_override:
                is_primary_enabled = app_config.data_sources.is_primary_enabled()
                logger.debug(
                    f"DataSourceManager: Primary override enabled: {is_primary_enabled}"
                )

                if is_primary_enabled:
                    # Use new configuration system with primary override
                    logger.debug(
                        f"DataSourceManager: Using primary override from {app_config.data_sources.primary_override.path}"
                    )
                    self.config = self._create_config_from_new_system(
                        app_config.data_sources
                    )
                else:
                    # Fallback to old system
                    logger.debug(
                        "DataSourceManager: Primary override not enabled, using old system"
                    )
                    self.config = get_content_config()
            else:
                if disable_primary_override:
                    logger.debug(
                        "DataSourceManager: Primary override disabled by environment variable, using old system"
                    )
                else:
                    logger.debug(
                        "DataSourceManager: No data_sources config found, using old system"
                    )
                self.config = get_content_config()
        except Exception as e:
            # Fallback to old system if new system fails
            logger.error(
                f"DataSourceManager: Error loading new config, falling back to old system: {e}"
            )
            self.config = get_content_config()

        self.content_manager = ContentSourceManager(self.config)
        self._data_paths_cache: dict[ContentType, list[Path]] | None = None
        self._is_initialized = False

    def _create_config_from_new_system(self, data_sources_config: Any) -> Any:
        """Create old ContentConfiguration from new DataSourcesConfig."""
        from pathlib import Path

        from ..config.sources import ContentConfiguration, ContentSource, SourceType

        config = ContentConfiguration()

        # Add SRD source if not overridden
        if not data_sources_config.is_primary_enabled():
            # Find project root for SRD data
            project_root = self._find_project_root()
            config.add_source(
                ContentSource(
                    name="srd",
                    type=SourceType.DIRECTORY,
                    path=project_root / "srd-data",
                    enabled=True,
                    priority=1,
                    url=None,
                )
            )

        # Add primary override if enabled
        if data_sources_config.is_primary_enabled():
            primary_path = Path(data_sources_config.primary_override.path)
            config.add_source(
                ContentSource(
                    name="primary",
                    type=SourceType.DIRECTORY,
                    path=primary_path,
                    enabled=True,
                    priority=0,  # Highest priority
                    url=None,
                )
            )

        # Add extensions
        for i, ext in enumerate(data_sources_config.get_enabled_extensions()):
            if ext.source:
                ext_path = Path(ext.source)
                # For now, treat all extensions as DIRECTORY type since the old system
                # doesn't have a FILE type. The ContentSource.path can handle both
                # files and directories
                config.add_source(
                    ContentSource(
                        name=ext.name or f"extension-{i + 1}",
                        type=SourceType.DIRECTORY,
                        path=ext_path,
                        enabled=True,
                        priority=10 + i,  # Lower priority than primary
                        url=None,
                    )
                )

        return config

    def _find_project_root(self) -> Path:
        """Find the project root directory containing data sources."""
        current = Path(__file__).parent
        for parent in [current] + list(current.parents):
            if (parent / "srd-data").exists():
                return parent
        # Fallback
        return Path.cwd()

    def get_service_name(self) -> str:
        """Return service name for debugging and logging."""
        return "DataSourceManager"

    async def initialize(self) -> None:
        """Initialize async resources."""
        await self._ensure_sources_ready_async()
        self._is_initialized = True

    async def cleanup(self) -> None:
        """Clean up async resources."""
        # ContentSourceManager doesn't require explicit cleanup currently
        self._data_paths_cache = None
        self._is_initialized = False

    def is_initialized(self) -> bool:
        """Return True if service is fully initialized."""
        return self._is_initialized

    async def ensure_sources_ready(self) -> None:
        """Ensure all content sources are available and indexed."""
        await self._ensure_sources_ready_async()

    async def _ensure_sources_ready_async(self) -> None:
        """Async implementation of ensure_sources_ready."""
        try:
            await self.content_manager.ensure_all_sources()
            await self.content_manager.build_content_index()
        except Exception as e:
            logger.error(f"Failed to prepare data sources: {e}")
            raise SourceNotFoundError(f"Failed to prepare data sources: {e}") from e

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type.

        For adventures and books, this returns only metadata files to prevent
        duplicate loading. Content files are loaded on-demand by ContentResolver.
        Other content types use the original pattern-based discovery.
        """
        # Use internal Result-based implementation
        result = self._get_data_paths_result()
        if isinstance(result, Error):
            # Convert Result error to exception for backward compatibility
            raise result.error
        return result.unwrap()

    def _get_data_paths_result(
        self,
    ) -> Result[dict[ContentType, list[Path]], DataSourceError]:
        """Internal Result-based implementation of get_data_paths.

        Returns:
            Success with data paths dictionary, or Error with DataSourceError
        """
        if self._data_paths_cache is not None:
            return Success(self._data_paths_cache)

        # Check if content index is built
        if not self.content_manager._index_built:
            logger.warning("Content index not built. Run ensure_sources_ready() first.")
            return Success({})

        # Start with metadata files for adventures and books
        data_paths = self.get_metadata_files()

        # Get content patterns from registry manager
        # Check if content_patterns attribute exists vs is empty
        if hasattr(self.__class__, "content_patterns"):
            content_patterns = self.__class__.content_patterns
            if not content_patterns:
                # Attribute exists but is empty - this is a misconfiguration
                return Error(
                    DataSourceError(
                        "DataSourceManager content patterns not initialized by registry manager. "
                        "Ensure initialize_content_types() is called before using DataSourceManager."
                    )
                )
        else:
            # Attribute doesn't exist - likely a test scenario, fall back gracefully
            logger.warning(
                "DataSourceManager content_patterns attribute not set. "
                "This is normal in test scenarios. Falling back to metadata-only mode."
            )
            return Success(data_paths)

        content_patterns = self.__class__.content_patterns

        all_files = self.content_manager.get_all_content_files()

        # Track files already assigned to avoid conflicts
        assigned_files = set()

        # Start by marking all metadata files as assigned to prevent duplication
        for content_type, paths in data_paths.items():
            for path in paths:
                assigned_files.add(path)

        # Configure shared files for cross-type content
        shared_files = self._configure_shared_files(content_patterns, all_files)

        # Organize content types by priority
        fluff_content_types = [
            ct for ct in content_patterns.keys() if ct.value.endswith("Fluff")
        ]
        regular_content_types = [
            ct for ct in content_patterns.keys() if not ct.value.endswith("Fluff")
        ]
        all_content_types = fluff_content_types + regular_content_types

        # PHASE 1: Assign files based on directory names (high confidence)
        data_paths = self._assign_files_by_directory(
            data_paths,
            all_content_types,
            content_patterns,
            all_files,
            assigned_files,
            shared_files,
        )

        # PHASE 2: Assign remaining files based on filename patterns (lower confidence)
        data_paths = self._assign_files_by_filename(
            data_paths,
            all_content_types,
            content_patterns,
            all_files,
            assigned_files,
            shared_files,
        )

        # Final deduplication pass for all content types
        data_paths = self._deduplicate_paths(data_paths)

        # CRITICAL: Filter out content files from adventures and books in data_paths
        # According to the dual-file architecture, get_data_paths() should only return
        # metadata files for adventures/books to prevent duplicate loading
        data_paths = self._filter_out_content_files_from_data_paths(data_paths)

        self._data_paths_cache = data_paths

        logger.debug("Discovered data files (metadata for adventures/books):")
        for content_type, paths in data_paths.items():
            logger.debug(f"  {content_type.value}: {len(paths)} files")
            for path in paths:
                logger.debug(f"    - {path}")

        return Success(data_paths)

    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files organized by content type.

        Metadata files contain lightweight index information (names, IDs, TOC)
        and are loaded by the omnidexer. Content files are excluded.

        Returns:
            Dictionary mapping content types to metadata file paths
        """
        if not self.content_manager._index_built:
            logger.warning("Content index not built. Run ensure_sources_ready() first.")
            return {}

        metadata_paths: dict[ContentType, list[Path]] = {}
        all_files = self.content_manager.get_all_content_files()

        # Find metadata files
        for source_name, files in all_files.items():
            for file_path in files:
                if self._is_metadata_file(file_path):
                    filename = file_path.name.lower()

                    # Map metadata files to content types using dynamic resolution
                    if filename == "adventures.json":
                        try:
                            adventure_type = ContentType("adventure")
                            if adventure_type not in metadata_paths:
                                metadata_paths[adventure_type] = []
                            metadata_paths[adventure_type].append(file_path)
                        except ValueError:
                            logger.warning(
                                "Adventure content type not found, skipping adventures.json"
                            )
                    elif filename == "books.json":
                        try:
                            book_type = ContentType("book")
                            if book_type not in metadata_paths:
                                metadata_paths[book_type] = []
                            metadata_paths[book_type].append(file_path)
                        except ValueError:
                            logger.warning(
                                "Book content type not found, skipping books.json"
                            )

        logger.debug("Discovered metadata files:")
        for content_type, paths in metadata_paths.items():
            logger.debug(f"  {content_type.value}: {len(paths)} files")
            for path in paths:
                logger.debug(f"    - {path}")

        return metadata_paths

    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to content files organized by content type.

        Content files contain the actual entry data for adventures and books.
        These are loaded on-demand and merged with metadata.

        Returns:
            Dictionary mapping content types to content file paths
        """
        if not self.content_manager._index_built:
            logger.warning("Content index not built. Run ensure_sources_ready() first.")
            return {}

        content_paths: dict[ContentType, list[Path]] = {}
        all_files = self.content_manager.get_all_content_files()

        # Find content files
        for source_name, files in all_files.items():
            for file_path in files:
                if self._is_content_file(file_path):
                    filename = file_path.name.lower()

                    # Map content files to content types using dynamic resolution
                    if filename.startswith("adventure-"):
                        try:
                            adventure_type = ContentType("adventure")
                            if adventure_type not in content_paths:
                                content_paths[adventure_type] = []
                            content_paths[adventure_type].append(file_path)
                        except ValueError:
                            logger.warning(
                                "Adventure content type not found, skipping adventure files"
                            )
                    elif filename.startswith("book-"):
                        try:
                            book_type = ContentType("book")
                            if book_type not in content_paths:
                                content_paths[book_type] = []
                            content_paths[book_type].append(file_path)
                        except ValueError:
                            logger.warning(
                                "Book content type not found, skipping book files"
                            )

        logger.debug("Discovered content files:")
        for content_type, paths in content_paths.items():
            logger.debug(f"  {content_type.value}: {len(paths)} files")

        return content_paths

    def get_source_statistics(self) -> dict[str, Any]:
        """Get statistics about configured sources.

        Returns:
            Dictionary with source counts, sync status, and performance metrics
        """
        stats: dict[str, Any] = {
            "enabled_sources": len(self.config.get_enabled_sources()),
            "is_initialized": self._is_initialized,
        }

        if self._is_initialized:
            # Use full content index for statistics instead of just metadata files
            all_files = self.content_manager.get_all_content_files()
            total_files = sum(len(files) for files in all_files.values())

            # Get metadata files for content type breakdown (represents what's actually loadable)
            data_paths = self.get_data_paths()

            stats["content_types"] = len(data_paths)
            stats["total_files"] = total_files  # Show full indexed content count

            by_type: dict[str, int] = {}
            for content_type, paths in data_paths.items():
                by_type[content_type.value] = len(paths)
            stats["by_type"] = by_type

        return stats

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation - not handled by DataSourceManager.

        This method exists for SourceManager compatibility but delegates
        to ContentAttributionManager in the unified architecture.
        """
        logger.warning(
            f"resolve_source({source_abbrev}) called on DataSourceManager. "
            "Content attribution should be handled by ContentAttributionManager."
        )
        return None

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get source priority - not handled by DataSourceManager.

        This method exists for SourceManager compatibility but delegates
        to ContentAttributionManager in the unified architecture.
        """
        logger.warning(
            f"get_source_priority({source_abbrev}) called on DataSourceManager. "
            "Content attribution should be handled by ContentAttributionManager."
        )
        return 1000  # High number for unknown sources

    def clear_cache(self) -> None:
        """Clear internal caches to force rebuild."""
        self._data_paths_cache = None

    def _configure_shared_files(
        self,
        content_patterns: dict[ContentType, list[str]],
        all_files: dict[str, list[Path]],
    ) -> dict[str, list[ContentType]]:
        """Configure files that should be shared between multiple content types."""
        shared_files: dict[str, list[ContentType]] = {}

        # Files that should be shared between multiple content types
        try:
            condition_type = ContentType("condition")
            status_type = ContentType("status")
            shared_files["conditionsdiseases.json"] = [condition_type, status_type]
        except ValueError:
            logger.warning(
                "Condition or status content types not found, skipping conditionsdiseases file mapping"
            )

        # Add bestiary file sharing between creature and creatureFluff
        try:
            # Find creature and creatureFluff types from content_patterns
            creature_type = None
            creature_fluff_type = None

            for ct in content_patterns.keys():
                if ct.value == "creature":
                    creature_type = ct
                elif ct.value == "creatureFluff":
                    creature_fluff_type = ct

            if creature_type and creature_fluff_type:
                # Mark all bestiary files as shared between creature and creatureFluff
                for source_name, files in all_files.items():
                    for file_path in files:
                        file_name = file_path.name.lower()
                        parent_name = file_path.parent.name.lower()

                        # If file is in bestiary directory or has bestiary in name
                        if (
                            "bestiary" in parent_name
                            and not file_name.startswith("fluff-")
                        ) or (
                            file_name.startswith("bestiary-")
                            and not file_name.startswith("fluff-")
                        ):
                            shared_files[file_name] = [
                                creature_type,
                                creature_fluff_type,
                            ]
                        elif file_name.startswith("fluff-bestiary-"):
                            # Fluff bestiary files go only to creatureFluff
                            shared_files[file_name] = [creature_fluff_type]

                logger.debug(
                    f"Configured bestiary file sharing between {len([f for f in shared_files.values() if creature_type in f])} files"
                )
            else:
                logger.warning(
                    f"Could not find creature types for bestiary sharing: creature={creature_type is not None}, creatureFluff={creature_fluff_type is not None}"
                )

        except Exception as e:
            logger.warning(f"Error setting up bestiary file sharing: {e}")

        return shared_files

    def _assign_files_by_directory(
        self,
        data_paths: dict[ContentType, list[Path]],
        all_content_types: list[ContentType],
        content_patterns: dict[ContentType, list[str]],
        all_files: dict[str, list[Path]],
        assigned_files: set[Path],
        shared_files: dict[str, list[ContentType]],
    ) -> dict[ContentType, list[Path]]:
        """Assign files based on directory names (high confidence)."""
        for content_type in all_content_types:
            patterns = content_patterns[content_type]
            type_paths = []

            # Search through all source files for directory matches
            for source_name, files in all_files.items():
                for file_path in files:
                    file_name = file_path.name.lower()

                    # Skip files already assigned or should be filtered
                    # Exception: allow shared files to be assigned to multiple content types
                    is_shared_file = (
                        file_name in shared_files
                        and content_type in shared_files[file_name]
                    )

                    if (
                        file_path in assigned_files
                        and not is_shared_file
                        or self._should_skip_file_at_discovery(file_path)
                    ):
                        continue

                    parent_name = file_path.parent.name.lower()

                    # Check parent directory names
                    if any(pattern in parent_name for pattern in patterns):
                        # Special case: exclude monsterfeatures from feat matching
                        if (
                            content_type.value == "feat"
                            and "monsterfeature" in file_name
                        ):
                            continue

                        # Special case: For fluff content types, be more restrictive
                        # Only match files that actually have "fluff" in the name
                        if content_type.value.endswith("Fluff"):
                            if "fluff" not in file_name:
                                continue

                        type_paths.append(file_path)
                        # Only mark as assigned if it's not a shared file
                        if not (
                            file_name in shared_files
                            and len(shared_files[file_name]) > 1
                        ):
                            assigned_files.add(file_path)

            if type_paths:
                # Remove duplicates while preserving order (PHASE 1)
                existing_paths = data_paths.get(content_type, [])
                all_paths = existing_paths + type_paths
                data_paths[content_type] = self._remove_duplicates_preserve_order(
                    all_paths
                )

        return data_paths

    def _assign_files_by_filename(
        self,
        data_paths: dict[ContentType, list[Path]],
        all_content_types: list[ContentType],
        content_patterns: dict[ContentType, list[str]],
        all_files: dict[str, list[Path]],
        assigned_files: set[Path],
        shared_files: dict[str, list[ContentType]],
    ) -> dict[ContentType, list[Path]]:
        """Assign remaining files based on filename patterns (lower confidence)."""
        for content_type in all_content_types:
            patterns = content_patterns[content_type]
            type_paths = data_paths.get(content_type, [])

            # Search through all source files for filename matches
            for source_name, files in all_files.items():
                for file_path in files:
                    file_name = file_path.name.lower()

                    # Skip files already assigned or should be filtered
                    # Exception: allow shared files to be assigned to multiple content types
                    is_shared_file = (
                        file_name in shared_files
                        and content_type in shared_files[file_name]
                    )

                    if (
                        file_path in assigned_files
                        and not is_shared_file
                        or self._should_skip_file_at_discovery(file_path)
                    ):
                        continue

                    # Check filename patterns
                    if any(pattern in file_name for pattern in patterns):
                        # Special case: exclude monsterfeatures from feat matching
                        if (
                            content_type.value == "feat"
                            and "monsterfeature" in file_name
                        ):
                            continue

                        # Special case: For fluff content types, be more restrictive
                        # Only match files that actually have "fluff" in the name
                        if content_type.value.endswith("Fluff"):
                            if "fluff" not in file_name:
                                continue

                        type_paths.append(file_path)
                        # Only mark as assigned if it's not a shared file
                        if not (
                            file_name in shared_files
                            and len(shared_files[file_name]) > 1
                        ):
                            assigned_files.add(file_path)

            if type_paths:
                data_paths[content_type] = self._remove_duplicates_preserve_order(
                    type_paths
                )

        return data_paths

    def _deduplicate_paths(
        self, data_paths: dict[ContentType, list[Path]]
    ) -> dict[ContentType, list[Path]]:
        """Final deduplication pass for all content types."""
        for content_type in data_paths:
            if data_paths[content_type]:
                data_paths[content_type] = self._remove_duplicates_preserve_order(
                    data_paths[content_type]
                )
        return data_paths

    def _remove_duplicates_preserve_order(self, paths: list[Path]) -> list[Path]:
        """Remove duplicates while preserving order."""
        unique_paths = []
        seen = set()
        for path in paths:
            if path not in seen:
                unique_paths.append(path)
                seen.add(path)
        return unique_paths

    def _is_metadata_file(self, file_path: Path) -> bool:
        """Check if file is a metadata file (adventures.json, books.json)."""
        filename = file_path.name.lower()
        metadata_files = {"adventures.json", "books.json"}
        return filename in metadata_files

    def _is_content_file(self, file_path: Path) -> bool:
        """Check if file is a content file (adventure-*.json, book-*.json)."""
        filename = file_path.name.lower()
        content_patterns = [
            "adventure-",  # adventure-cos.json, adventure-hotdq.json, etc.
            "book-",  # book-phb.json, book-mm.json, etc.
        ]
        return filename.endswith(".json") and any(
            filename.startswith(pattern) for pattern in content_patterns
        )

    def _filter_out_content_files_from_data_paths(
        self, data_paths: dict[ContentType, list[Path]]
    ) -> dict[ContentType, list[Path]]:
        """Filter out content files from adventures and books in data paths.

        According to the dual-file architecture, get_data_paths() should only return
        metadata files for adventures/books. Content files are loaded separately
        via get_content_files() on-demand.

        Args:
            data_paths: Current data paths with mixed metadata and content files

        Returns:
            Filtered data paths with content files removed from adventures/books
        """
        filtered_paths = {}

        for content_type, paths in data_paths.items():
            filtered_type_paths = []

            # For adventures and books, filter out content files
            if content_type.value in ("adventure", "book"):
                for path in paths:
                    # Keep only metadata files, exclude content files
                    if self._is_metadata_file(path) and not self._is_content_file(path):
                        filtered_type_paths.append(path)
                    elif not self._is_content_file(path):
                        # If it's not a content file and not clearly a metadata file,
                        # it's probably other adventure/book content that should be kept
                        # but this is a safety net
                        filtered_type_paths.append(path)
            else:
                # For all other content types, keep all files
                filtered_type_paths = paths

            if filtered_type_paths:
                filtered_paths[content_type] = filtered_type_paths

        return filtered_paths

    def _should_skip_file_at_discovery(self, file_path: Path) -> bool:
        """Check if file should be skipped during discovery phase."""
        filename = file_path.name.lower()

        # Skip non-JSON files
        if not filename.endswith(".json"):
            return True

        # Skip specific directories
        skip_directories = {
            "search",  # Search indices
            "generated",  # Generated metadata
            "node_modules",  # Node.js dependencies
            ".git",  # Git directory
            "test",  # Test files
            "tests",  # Test files
            "spec",  # Specification files
            "docs",  # Documentation
            "build",  # Build artifacts
            "dist",  # Distribution files
        }

        # Check if any parent directory should be skipped
        path_parts = file_path.parts
        for part in path_parts:
            if part.lower() in skip_directories:
                return True

        # Skip specific file patterns
        skip_file_patterns = [
            "cspell.json",
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "eslint.config",
            "jest.config",
            "webpack.config",
            "rollup.config",
            "vite.config",
            "manifest.json",
            "sw-",  # Service worker files
            "gendata-",  # Generated data files
            "index-",  # Search index files
        ]

        # Check filename patterns
        for pattern in skip_file_patterns:
            if filename.startswith(pattern) or pattern in filename:
                return True

        return False
