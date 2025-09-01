"""Main content source manager that coordinates all source types."""

import asyncio
from pathlib import Path
from typing import cast

from ..config.sources import (
    ContentConfiguration,
    ContentSource,
    SourceType,
    get_content_config,
)
from ..logging import get_logger
from .github import GitHubSourceManager

logger = get_logger(__name__)


class ContentSourceManager:
    """Manages all content sources and provides unified access."""

    def __init__(self, config: ContentConfiguration | None = None):
        """Initialize content source manager."""
        self.config = config or get_content_config()
        self.github_manager = GitHubSourceManager(self.config.cache_dir)
        self._content_index: dict[str, list[Path]] = {}
        self._index_built = False

    async def ensure_all_sources(self) -> None:
        """Ensure all enabled sources are available and up to date."""
        enabled_sources = self.config.get_enabled_sources()

        if not enabled_sources:
            logger.warning("No enabled content sources configured")
            return

        logger.info(f"Ensuring {len(enabled_sources)} content sources are available")

        # Check git availability for GitHub sources
        github_sources = [s for s in enabled_sources if s.type == SourceType.GITHUB]
        if github_sources and not self.github_manager.is_git_available():
            logger.error("Git is not available but GitHub sources are configured")
            raise RuntimeError(
                "Git is required for GitHub sources but is not installed"
            )

        # Process sources in parallel
        tasks = []
        for source in enabled_sources:
            if source.type == SourceType.GITHUB:
                tasks.append(self._ensure_github_source(source))
            elif source.type == SourceType.DIRECTORY:
                tasks.append(self._ensure_directory_source(source))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _ensure_github_source(self, source: ContentSource) -> None:
        """Ensure a GitHub source is available."""
        try:
            await self.github_manager.ensure_repository(source)
            logger.info(f"GitHub source '{source.name}' is ready")
        except Exception as e:
            logger.error(f"Failed to ensure GitHub source '{source.name}': {e}")
            raise

    async def _ensure_directory_source(self, source: ContentSource) -> None:
        """Ensure a directory source is available."""
        if not source.path:
            raise FileNotFoundError(
                f"Directory source path not specified for: {source.name}"
            )

        path = Path(source.path)
        if not path.exists():
            logger.error(
                f"Directory source '{source.name}' path does not exist: {source.path}"
            )
            raise FileNotFoundError(f"Directory source path not found: {source.path}")

        if not path.is_dir():
            logger.error(
                f"Directory source '{source.name}' path is not a directory: {source.path}"
            )
            raise ValueError(f"Path is not a directory: {source.path}")

        logger.info(f"Directory source '{source.name}' is ready")

    async def build_content_index(self, force_rebuild: bool = False) -> None:
        """Build index of all available content files."""
        if self._index_built and not force_rebuild:
            return

        logger.info("Building content index...")
        self._content_index.clear()

        enabled_sources = self.config.get_enabled_sources()

        # Create tasks for all sources to process concurrently
        source_tasks = []
        for source in enabled_sources:
            task = self._get_source_files(source)
            source_tasks.append((source, task))

        # Execute all source indexing concurrently
        tasks = [task for _, task in source_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, (source, _) in enumerate(source_tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to index source '{source.name}': {result}")
                self._content_index[source.name] = []
            else:
                files = cast(list[Path], result)
                self._content_index[source.name] = files
                logger.info(f"Indexed {len(files)} files from source '{source.name}'")

        total_files = sum(len(files) for files in self._content_index.values())
        logger.info(
            f"Content index built with {total_files} total files from {len(enabled_sources)} sources"
        )
        self._index_built = True

    def build_content_index_sync(self, force_rebuild: bool = False) -> None:
        """Build index of all available content files synchronously.

        This is the synchronous version for test environments and CLI contexts
        where async processing is not needed or available.
        """
        if self._index_built and not force_rebuild:
            return

        logger.info("Building content index (sync mode)...")
        self._content_index.clear()

        enabled_sources = self.config.get_enabled_sources()

        # Process sources sequentially (no async/await needed)
        for source in enabled_sources:
            try:
                files = self._get_source_files_sync(source)
                self._content_index[source.name] = files
                logger.info(f"Indexed {len(files)} files from source '{source.name}'")
            except Exception as e:
                logger.error(f"Failed to index source '{source.name}': {e}")
                self._content_index[source.name] = []

        total_files = sum(len(files) for files in self._content_index.values())
        logger.info(
            f"Content index built (sync) with {total_files} total files from {len(enabled_sources)} sources"
        )
        self._index_built = True

    async def _get_source_files(self, source: ContentSource) -> list[Path]:
        """Get list of content files from a source."""
        if source.type == SourceType.GITHUB:
            # Ensure repository is available first
            await self.github_manager.ensure_repository(source)
            return self.github_manager.list_content_files(source)

        elif source.type == SourceType.DIRECTORY:
            if not source.path:
                return []

            path = Path(source.path)
            if not path.exists():
                return []

            # Find all JSON files in directory
            json_files = []
            for json_file in path.rglob("*.json"):
                try:
                    if json_file.stat().st_size < 50:  # Skip very small files
                        continue
                    json_files.append(json_file)
                except OSError:
                    continue

            return sorted(json_files)

        else:
            logger.warning(f"Unsupported source type: {source.type}")
            return []

    def _get_source_files_sync(self, source: ContentSource) -> list[Path]:
        """Get list of content files from a source synchronously.

        This is the synchronous version for test environments and CLI contexts.
        For GitHub sources, this will skip the ensure_repository step which is async.
        """
        if source.type == SourceType.GITHUB:
            # In sync mode, assume GitHub repository is already available
            # This is mainly for test environments that should use directory sources
            logger.warning(
                f"GitHub source '{source.name}' processed in sync mode - repository may not be available"
            )
            try:
                return self.github_manager.list_content_files(source)
            except Exception as e:
                logger.error(f"Failed to list GitHub source files: {e}")
                return []

        elif source.type == SourceType.DIRECTORY:
            if not source.path:
                return []

            path = Path(source.path)
            if not path.exists():
                return []

            # Find all JSON files in directory
            json_files = []
            for json_file in path.rglob("*.json"):
                try:
                    if json_file.stat().st_size < 50:  # Skip very small files
                        continue
                    json_files.append(json_file)
                except OSError:
                    continue

            return sorted(json_files)

        else:
            logger.warning(f"Unsupported source type: {source.type}")
            return []

    def get_all_content_files(self) -> dict[str, list[Path]]:
        """Get all indexed content files by source."""
        if not self._index_built:
            raise RuntimeError(
                "Content index not built. Call build_content_index() first."
            )

        return self._content_index.copy()

    def get_source_files(self, source_name: str) -> list[Path]:
        """Get content files from a specific source."""
        if not self._index_built:
            raise RuntimeError(
                "Content index not built. Call build_content_index() first."
            )

        return self._content_index.get(source_name, [])

    def get_files_by_pattern(self, pattern: str) -> dict[str, list[Path]]:
        """Get files matching a pattern from all sources."""
        if not self._index_built:
            raise RuntimeError(
                "Content index not built. Call build_content_index() first."
            )

        results = {}
        for source_name, files in self._content_index.items():
            matching_files = [f for f in files if pattern.lower() in f.name.lower()]
            if matching_files:
                results[source_name] = matching_files

        return results

    def get_source_info(self, source_name: str) -> dict | None:
        """Get information about a specific source."""
        source = self.config.get_source_by_name(source_name)
        if not source:
            return None

        info = {
            "name": source.name,
            "type": source.type.value,
            "enabled": source.enabled,
            "priority": source.priority,
            "auto_update": source.auto_update,
            "file_count": len(self._content_index.get(source_name, [])),
        }

        if source.type == SourceType.GITHUB:
            info["url"] = source.url or ""
            info["branch"] = source.branch or ""
            # Get git repository info
            git_info = self.github_manager.get_repository_info(source)
            if git_info:
                info.update(git_info)

        elif source.type == SourceType.DIRECTORY:
            info["path"] = str(source.path)

        return info

    async def update_source(self, source_name: str) -> bool:
        """Update a specific source."""
        source = self.config.get_source_by_name(source_name)
        if not source:
            logger.error(f"Source '{source_name}' not found")
            return False

        try:
            if source.type == SourceType.GITHUB:
                await self._ensure_github_source(source)
            elif source.type == SourceType.DIRECTORY:
                await self._ensure_directory_source(source)

            # Rebuild index for this source
            files = await self._get_source_files(source)
            self._content_index[source_name] = files

            logger.info(f"Updated source '{source_name}' with {len(files)} files")
            return True

        except Exception as e:
            logger.error(f"Failed to update source '{source_name}': {e}")
            return False

    async def remove_source_data(self, source_name: str) -> bool:
        """Remove cached data for a source."""
        source = self.config.get_source_by_name(source_name)
        if not source:
            return False

        try:
            if source.type == SourceType.GITHUB:
                success = self.github_manager.remove_repository(source)
            else:
                success = True  # Nothing to remove for directory sources

            # Remove from index
            self._content_index.pop(source_name, None)

            return success

        except Exception as e:
            logger.error(f"Failed to remove data for source '{source_name}': {e}")
            return False

    def get_statistics(self) -> dict:
        """Get statistics about all sources."""
        if not self._index_built:
            return {"error": "Content index not built"}

        enabled_sources = self.config.get_enabled_sources()
        total_files = sum(len(files) for files in self._content_index.values())

        source_stats = []
        for source in enabled_sources:
            file_count = len(self._content_index.get(source.name, []))
            source_stats.append(
                {
                    "name": source.name,
                    "type": source.type.value,
                    "enabled": source.enabled,
                    "file_count": file_count,
                }
            )

        return {
            "total_sources": len(enabled_sources),
            "total_files": total_files,
            "sources": source_stats,
            "cache_dir": str(self.config.cache_dir),
        }
