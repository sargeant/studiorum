"""Image asset management and caching system."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiofiles
import aiohttp
from pydantic import BaseModel, Field

from dnd5e.core.config.paths import PathsConfig
from dnd5e.renderers.base.context import RenderContext


class ImageSource(BaseModel):
    """Configuration for an image source."""

    name: str = Field(description="Source name")
    base_url: str = Field(description="Base URL for images")
    local_path: Path | None = Field(None, description="Local cache path")
    priority: int = Field(
        default=100, description="Source priority (lower = higher priority)"
    )


class ImageAsset(BaseModel):
    """Represents a managed image asset."""

    original_url: str
    local_path: Path
    cache_key: str
    file_size: int
    last_accessed: float
    source_name: str


class ImageManager:
    """Manages image assets, caching, and source resolution.

    Handles downloading images from various sources (5etools-img, user directories)
    and maintains a local cache for efficient access.
    """

    def __init__(self, paths_config: PathsConfig | None = None) -> None:
        """Initialize the image manager.

        Args:
            paths_config: Path configuration
        """
        self.paths_config = paths_config or PathsConfig()
        self.cache_dir = self.paths_config.cache_dir / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize image sources
        self.sources: list[ImageSource] = [
            ImageSource(
                name="5etools-official",
                base_url="https://5e.tools/img",
                priority=10,
            ),
            ImageSource(
                name="5etools-mirror",
                base_url="https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main",
                priority=20,
            ),
        ]

        # Asset cache (in-memory)
        self._asset_cache: dict[str, ImageAsset] = {}

    async def resolve_image(
        self, image_path: str, context: RenderContext
    ) -> Path | None:
        """Resolve an image path to a local file.

        Args:
            image_path: Original image path (URL or relative path)
            context: Rendering context

        Returns:
            Local path to image file, or None if not found
        """
        # Check if it's already a local path
        if not image_path.startswith(("http://", "https://")):
            return await self._resolve_local_path(image_path, context)

        # Handle URL - check cache first
        cache_key = self._generate_cache_key(image_path)

        if cache_key in self._asset_cache:
            asset = self._asset_cache[cache_key]
            if asset.local_path.exists():
                return asset.local_path

        # Download and cache the image
        return await self._download_and_cache(image_path)

    async def _resolve_local_path(
        self, image_path: str, context: RenderContext
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

        # Add assets directory from context
        if context.assets_dir:
            search_paths.append(context.assets_dir)

        # Add images directory from context
        if context.images_dir:
            search_paths.append(context.images_dir)

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
                        async with aiofiles.open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)

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
        return hashlib.md5(url.encode()).hexdigest()

    def add_source(self, source: ImageSource) -> None:
        """Add an image source.

        Args:
            source: Image source to add
        """
        self.sources.append(source)
        # Re-sort by priority
        self.sources.sort(key=lambda s: s.priority)

    def add_local_source(self, name: str, path: Path, priority: int = 50) -> None:
        """Add a local directory as an image source.

        Args:
            name: Source name
            path: Local directory path
            priority: Source priority
        """
        source = ImageSource(
            name=name,
            base_url="file://" + str(path),
            local_path=path,
            priority=priority,
        )
        self.add_source(source)

    async def cleanup_cache(self, max_age_days: int = 30) -> None:
        """Clean up old cached images.

        Args:
            max_age_days: Maximum age in days for cached images
        """
        import time

        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        # Clean up cache files
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        cache_file.unlink()
                    except OSError:
                        pass

        # Clean up asset cache
        to_remove = []
        for key, asset in self._asset_cache.items():
            if not asset.local_path.exists():
                to_remove.append(key)

        for key in to_remove:
            del self._asset_cache[key]

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the image cache.

        Returns:
            Dictionary with cache statistics
        """
        total_files = len(list(self.cache_dir.glob("*")))
        total_size = sum(
            f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file()
        )

        return {
            "cache_directory": str(self.cache_dir),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "assets_in_memory": len(self._asset_cache),
            "sources": [{"name": s.name, "priority": s.priority} for s in self.sources],
        }
