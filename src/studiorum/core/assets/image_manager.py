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


# Legacy classes for backward compatibility
class ImageSource(BaseModel):
    """Legacy configuration for an image source (backward compatibility)."""

    name: str = Field(description="Source name")
    base_url: str = Field(description="Base URL for images")
    local_path: Path | None = Field(None, description="Local cache path")
    priority: int = Field(
        default=100, description="Source priority (lower = higher priority)"
    )


class ImageAsset(BaseModel):
    """Legacy representation of a managed image asset (backward compatibility)."""

    original_url: str
    local_path: Path
    cache_key: str
    file_size: int
    last_accessed: float
    source_name: str


class ImageManager:
    """Legacy image manager with enhanced multi-source support.

    This class maintains backward compatibility while delegating to the new
    ImageSourceRegistry for enhanced image resolution capabilities. It handles
    migration from the old system and provides seamless integration with the
    enhanced image source system.
    """

    def __init__(self, paths_config: PathsConfig | None = None) -> None:
        """Initialise the image manager.

        Args:
            paths_config: Path configuration
        """
        self.paths_config = paths_config or PathsConfig()
        self.cache_dir = self.paths_config.build_path / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize new registry system
        self._registry = ImageSourceRegistry(cache_dir=self.cache_dir)

        # Legacy sources list for backward compatibility
        self.sources: list[ImageSource] = []

        # Legacy asset cache for backward compatibility
        self._asset_cache: dict[str, ImageAsset] = {}

        # Auto-configure default sources
        self._configure_default_sources()

        logger.info(
            f"Initialised ImageManager with enhanced registry (cache: {self.cache_dir})"
        )

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

        # Create legacy ImageSource objects for backward compatibility
        self.sources = [
            ImageSource(
                name="5etools-official",
                base_url="https://5e.tools/img",
                priority=20,
            ),
            ImageSource(
                name="5etools-mirror",
                base_url="https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main",
                priority=30,
            ),
        ]

    async def resolve_image(
        self, image_path: str, context: RenderingContext
    ) -> Path | None:
        """Resolve an image path to a local file.

        Args:
            image_path: Original image path (URL or relative path)
            context: Rendering context

        Returns:
            Local path to image file, or None if not found
        """
        logger.debug(f"Resolving image: {image_path}")

        # First try the enhanced registry system
        registry_result = await self._registry.resolve_image(image_path)
        if registry_result.is_success():
            if not hasattr(registry_result, "value"):
                logger.error("Success result missing value attribute")
                return None
            asset_info: ImageAssetInfo = registry_result.value

            # Update legacy cache for backward compatibility
            legacy_asset = ImageAsset(
                original_url=asset_info.original_path,
                local_path=asset_info.local_path,
                cache_key=asset_info.cache_key,
                file_size=asset_info.file_size,
                last_accessed=asset_info.last_accessed,
                source_name=asset_info.source_name,
            )
            self._asset_cache[asset_info.cache_key] = legacy_asset

            logger.debug(
                f"Resolved image '{image_path}' from source '{asset_info.source_name}'"
            )
            resolved_path: Path = asset_info.local_path
            return resolved_path

        # Fallback to legacy resolution for local paths
        if not image_path.startswith(("http://", "https://")):
            legacy_path = await self._resolve_local_path(image_path, context)
            if legacy_path:
                logger.debug(
                    f"Resolved image '{image_path}' via legacy local resolution"
                )
                return legacy_path

        # Fallback to legacy download and cache
        legacy_path = await self._download_and_cache(image_path)
        if legacy_path:
            logger.debug(f"Resolved image '{image_path}' via legacy download")
            return legacy_path

        logger.warning(f"Could not resolve image: {image_path}")
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

    async def _download_and_cache(self, image_url: str) -> Path | None:
        """Download an image and cache it locally.

        Args:
            image_url: URL to download

        Returns:
            Local path to cached image, or None if download failed
        """
        cache_key = self._generate_cache_key(image_url)

        # Determine file extension from URL
        parsed = urlparse(image_url)
        path_parts = Path(parsed.path).parts
        if path_parts:
            file_ext = Path(path_parts[-1]).suffix
        else:
            file_ext = ".png"  # Default extension

        # Create cache file path
        cache_file = self.cache_dir / f"{cache_key}{file_ext}"

        try:
            # Try to download from each source
            for source in sorted(self.sources, key=lambda s: s.priority):
                source_url = self._construct_source_url(image_url, source)
                if source_url:
                    success = await self._download_from_url(source_url, cache_file)
                    if success:
                        # Create asset record
                        asset = ImageAsset(
                            original_url=image_url,
                            local_path=cache_file,
                            cache_key=cache_key,
                            file_size=cache_file.stat().st_size,
                            last_accessed=asyncio.get_event_loop().time(),
                            source_name=source.name,
                        )
                        self._asset_cache[cache_key] = asset
                        return cache_file

            return None

        except Exception:
            # If download fails, return None
            return None

    def _construct_source_url(
        self, original_url: str, source: ImageSource
    ) -> str | None:
        """Construct source-specific URL for downloading.

        Args:
            original_url: Original image URL
            source: Image source configuration

        Returns:
            Source-specific URL or None if not applicable
        """
        # Parse the original URL to extract the path
        parsed = urlparse(original_url)

        # For 5etools URLs, extract the relative path
        if "5e.tools" in parsed.netloc or "5etools" in parsed.netloc:
            # Extract path after /img/
            path_parts = parsed.path.split("/img/", 1)
            if len(path_parts) > 1:
                relative_path = path_parts[1]
                return f"{source.base_url}/{relative_path}"

        # For other URLs, try direct download
        if source.name == "direct":
            return original_url

        return None

    async def _download_from_url(self, url: str, output_path: Path) -> bool:
        """Download a file from URL to local path.

        Args:
            url: URL to download from
            output_path: Local path to save to

        Returns:
            True if download succeeded
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Ensure parent directory exists
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        # Write file
                        with open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        return True

            return False

        except Exception:
            return False

    def _generate_cache_key(self, url: str) -> str:
        """Generate cache key for URL.

        Args:
            url: Image URL

        Returns:
            Cache key string
        """
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    def add_source(self, source: ImageSource) -> None:
        """Add an image source (legacy method).

        Args:
            source: Legacy image source to add
        """
        self.sources.append(source)
        # Re-sort by priority
        self.sources.sort(key=lambda s: s.priority)

        # Convert to new format and add to registry
        if source.base_url.startswith("https://") or source.base_url.startswith(
            "http://"
        ):
            api_config = HttpApiImageSourceConfig(
                name=source.name,
                base_url=source.base_url,
                priority=source.priority,
                path_template="{image_path}",
            )
            result = self._registry.add_source(api_config)
            if result.is_error():
                error_msg = (
                    result.error.message
                    if hasattr(result, "error")
                    else "Unknown error"
                )
                logger.warning(f"Failed to add legacy source to registry: {error_msg}")

    def add_local_source(self, name: str, path: Path, priority: int = 50) -> None:
        """Add a local directory as an image source.

        Args:
            name: Source name
            path: Local directory path
            priority: Source priority
        """
        # Add to legacy sources
        source = ImageSource(
            name=name,
            base_url="file://" + str(path),
            local_path=path,
            priority=priority,
        )
        self.add_source(source)

        # Also add to new registry (this is done in add_source above for HTTP sources)
        # For local sources, we need a different approach
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

        # Also clean up legacy cache
        import time

        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        # Clean up legacy asset cache
        to_remove = []
        for key, asset in self._asset_cache.items():
            age = current_time - asset.last_accessed
            if age > max_age_seconds or not asset.local_path.exists():
                to_remove.append(key)

        for key in to_remove:
            del self._asset_cache[key]

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the image cache (enhanced with registry stats).

        Returns:
            Dictionary with cache statistics
        """
        # Get stats from new registry
        registry_stats = self._registry.get_cache_stats()

        # Add legacy compatibility info
        legacy_stats = {
            "legacy_assets_in_memory": len(self._asset_cache),
            "legacy_sources": [
                {"name": s.name, "priority": s.priority} for s in self.sources
            ],
        }

        return {
            **registry_stats,
            **legacy_stats,
        }
