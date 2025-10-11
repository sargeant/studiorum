"""Image asset management and caching system.

This module provides backward-compatible image management while integrating
with the new enhanced image source registry system. The ImageManager class
now delegates to ImageSourceRegistry for multi-source image resolution.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field

from studiorum.core.assets.image_sources import (
    GitImageSourceConfig,
    HttpApiImageSourceConfig,
    ImageAssetInfo,
    ImageSourceRegistry,
    ImageSourceType,
)
from studiorum.core.config.unified_config import PathsConfig
from studiorum.core.logging import get_logger
from studiorum.renderers.core.interfaces import RenderingContext

logger = get_logger(__name__)


class ImageManager:
    """Image manager with multi-source support.

    Delegates to ImageSourceRegistry for enhanced image resolution capabilities.
    """

    def __init__(self, paths_config: PathsConfig | None = None) -> None:
        """Initialise the image manager.

        Args:
            paths_config: Path configuration
        """
        self.paths_config = paths_config or PathsConfig()
        self.cache_dir = self.paths_config.build_path / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize registry system
        self._registry = ImageSourceRegistry(cache_dir=self.cache_dir)

        # Auto-configure default sources
        self._configure_default_sources()

        logger.info(f"Initialised ImageManager with registry (cache: {self.cache_dir})")

    def _configure_default_sources(self) -> None:
        """Configure default 5etools image sources."""
        # Add Git-based 5etools-img source (primary)
        git_config = GitImageSourceConfig(
            name="5etools-img-git",
            repository_url="https://github.com/5etools-mirror-3/5etools-img.git",
            branch="main",
            priority=10,
            sync_interval_hours=12,
            shallow_clone=True,
        )
        self._registry.add_source(git_config)

        # Add HTTP API fallback sources
        api_configs = [
            HttpApiImageSourceConfig(
                name="5etools-official",
                base_url="https://5e.tools/img",
                priority=20,
                path_template="{image_path}",
            ),
            HttpApiImageSourceConfig(
                name="5etools-mirror",
                base_url="https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main",
                priority=30,
                path_template="{image_path}",
            ),
        ]

        for config in api_configs:
            self._registry.add_source(config)

    async def resolve_image(
        self, image_path: str, context: RenderingContext
    ) -> Path | None:
        """Resolve an image path to a local file.

        Args:
            image_path: Original image path (URL or relative path)
            context: Rendering context

        Returns:
            Local path to image file, or None if not found

        Resolution order:
        1) Local path resolution (assets_dir/images_dir/paths_config.assets_dir)
        2) ImageSourceRegistry (HTTP/Git/Local sources)
        """
        logger.debug(f"Resolving image: {image_path}")

        # Branch based on whether this looks like a URL
        is_url = str(image_path).startswith(("http://", "https://"))

        # 1) Local path handling first
        if not is_url:
            # Try simple local resolution
            local = await self._resolve_local_path(image_path, context)
            if local is not None:
                return local

        # 2) Try registry for any kind of path
        registry_result = await self._registry.resolve_image(image_path)
        if registry_result.is_success():
            asset_info: ImageAssetInfo = registry_result.value  # type: ignore[attr-defined]
            logger.debug(
                f"Resolved image '{image_path}' from source '{asset_info.source_name}'"
            )
            return asset_info.local_path

        # 3) No resolution found
        logger.debug(f"Could not resolve image: {image_path}")
        return None

    async def _resolve_local_path(
        self, image_path: str, context: RenderingContext
    ) -> Path | None:
        """Resolve a local image path.

        Args:
            image_path: Local image path
            context: Rendering context

        Returns:
            Resolved local path or None
        """
        # Try various local path resolutions
        search_paths = []

        # Add assets directory from context metadata
        assets_dir = context.metadata.get("assets_dir")
        if assets_dir:
            search_paths.append(Path(assets_dir))

        # Add images directory from context metadata
        images_dir = context.metadata.get("images_dir")
        if images_dir:
            search_paths.append(Path(images_dir))

        # Add default assets directory
        if hasattr(self.paths_config, "assets_dir"):
            search_paths.append(self.paths_config.assets_dir)

        # Try each search path
        for base_path in search_paths:
            full_path = base_path / image_path
            if full_path.exists():
                return full_path

        return None

    def add_local_source(self, name: str, path: Path, priority: int = 50) -> None:
        """Add a local directory as an image source.

        Args:
            name: Source name
            path: Local directory path
            priority: Source priority
        """
        from studiorum.core.assets.image_sources import LocalDirectoryImageSourceConfig

        local_config = LocalDirectoryImageSourceConfig(
            name=name,
            directory_path=path,
            priority=priority,
        )
        result = self._registry.add_source(local_config)
        if result.is_error():
            error_msg = (
                result.error.message if hasattr(result, "error") else "Unknown error"
            )
            logger.warning(f"Failed to add local source to registry: {error_msg}")

    # New methods that delegate to registry
    async def sync_sources(self) -> None:
        """Sync all image sources."""
        logger.info("Syncing all image sources")
        for source_info in self._registry.list_sources():
            if source_info.config.enabled:
                result = await self._registry.sync_source(source_info.config.name)
                if result.is_error():
                    error_msg = (
                        result.error.message
                        if hasattr(result, "error")
                        else "Unknown error"
                    )
                    logger.error(
                        f"Failed to sync source '{source_info.config.name}': {error_msg}"
                    )

    async def sync_source(self, name: str) -> bool:
        """Sync a specific image source.

        Args:
            name: Name of the source to sync

        Returns:
            True if sync was successful
        """
        result = await self._registry.sync_source(name)
        return result.is_success()

    def get_registry(self) -> ImageSourceRegistry:
        """Get the underlying image source registry.

        Returns:
            The ImageSourceRegistry instance
        """
        return self._registry

    async def cleanup_cache(self, max_age_days: int = 30) -> None:
        """Clean up old cached images (delegates to registry).

        Args:
            max_age_days: Maximum age in days for cached images
        """
        max_age_hours = max_age_days * 24
        result = await self._registry.cleanup_cache(max_age_hours=max_age_hours)

        if result.is_success():
            if not hasattr(result, "value"):
                logger.error("Success result missing value attribute in cleanup")
                return
            stats = result.value
            logger.info(
                f"Cache cleanup completed: removed {stats['removed_old']} old items, {stats['removed_oversized']} oversized items"
            )
        else:
            error_msg = (
                result.error.message if hasattr(result, "error") else "Unknown error"
            )
            logger.error(f"Cache cleanup failed: {error_msg}")

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the image cache.

        Returns:
            Dictionary with cache statistics from the image source registry
        """
        return self._registry.get_cache_stats()
