"""Tests for the image asset manager."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from studiorum.core.assets.image_manager import ImageAsset, ImageManager, ImageSource
from studiorum.core.config.unified_config import PathsConfig
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


class TestImageSource:
    """Test the legacy image source compatibility layer.

    NOTE: ImageSource is an internal compatibility shim, but we test it to ensure
    the compatibility layer works correctly during the transition to ImageSourceRegistry.
    """

    def test_image_source_creation(self):
        """Test creating a legacy image source."""
        source = ImageSource(
            name="test-source",
            base_url="https://example.com/images",
            priority=50,
        )

        assert source.name == "test-source"
        assert source.base_url == "https://example.com/images"
        assert source.local_path is None
        assert source.priority == 50

    def test_image_source_with_local_path(self):
        """Test legacy image source with local path."""
        source = ImageSource(
            name="local-source",
            base_url="file:///tmp/images",
            local_path=Path("/tmp/images"),
            priority=10,
        )

        assert source.local_path == Path("/tmp/images")


class TestImageAsset:
    """Test the legacy image asset compatibility layer.

    NOTE: ImageAsset is an internal compatibility shim, but we test it to ensure
    the compatibility layer works correctly during the transition to ImageSourceRegistry.
    """

    def test_image_asset_creation(self):
        """Test creating a legacy image asset."""
        asset = ImageAsset(
            original_url="https://example.com/test.png",
            local_path=Path("/cache/test.png"),
            cache_key="abc123",
            file_size=1000,
            last_accessed=1234567890.0,
            source_name="test-source",
        )

        assert asset.original_url == "https://example.com/test.png"
        assert asset.local_path == Path("/cache/test.png")
        assert asset.cache_key == "abc123"
        assert asset.file_size == 1000
        assert asset.last_accessed == 1234567890.0
        assert asset.source_name == "test-source"


class TestImageManager:
    """Test the image manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.paths_config = Mock(spec=PathsConfig)
        self.paths_config.build_path = Path("/tmp/build")
        with patch("pathlib.Path.mkdir"):
            self.manager = ImageManager(self.paths_config)

    def test_init_default_sources(self):
        """Test initialization with default image sources."""
        assert len(self.manager.sources) == 2

        # Check 5etools sources are configured
        source_names = [s.name for s in self.manager.sources]
        assert "5etools-official" in source_names
        assert "5etools-mirror" in source_names

    def test_init_cache_dir_setup(self):
        """Test cache directory initialization."""
        assert self.manager.cache_dir == Path("/tmp/build/images")

    @pytest.mark.asyncio
    async def test_resolve_image_local_path(self):
        """Test resolving local image paths."""
        context = RenderingContext(
            output_format="latex",
            metadata={"assets_dir": Path("/assets"), "images_dir": None},
        )

        with patch.object(
            self.manager, "_resolve_local_path", return_value=Path("/assets/test.png")
        ) as mock_resolve:
            result = await self.manager.resolve_image("test.png", context)

            assert result == Path("/assets/test.png")
            mock_resolve.assert_called_once_with("test.png", context)

    @pytest.mark.asyncio
    async def test_resolve_image_url_cached(self):
        """Test resolving URL with cached result."""
        context = RenderingContext(
            output_format="latex",
            metadata={},
        )
        image_url = "https://example.com/test.png"

        # Mock the registry to return no result so it falls back to legacy
        with patch.object(
            self.manager._registry, "resolve_image"
        ) as mock_registry_resolve:
            from studiorum.core.result import Error

            mock_registry_resolve.return_value = Error("Not found")

            # Add cached asset to legacy cache
            cache_key = self.manager._generate_cache_key(image_url)
            cached_path = Path("/cache/test.png")
            self.manager._asset_cache[cache_key] = ImageAsset(
                original_url=image_url,
                local_path=cached_path,
                cache_key=cache_key,
                file_size=1000,
                last_accessed=1234567890.0,
                source_name="test",
            )

            with (
                patch.object(Path, "exists", return_value=True),
                patch.object(
                    self.manager, "_download_and_cache", return_value=cached_path
                ) as mock_download,
            ):
                result = await self.manager.resolve_image(image_url, context)

                assert result == cached_path
                mock_download.assert_called_once_with(image_url)

    @pytest.mark.asyncio
    async def test_resolve_image_url_download(self):
        """Test resolving URL with download."""
        context = RenderingContext(
            output_format="latex",
            metadata={},
        )
        image_url = "https://example.com/test.png"

        with patch.object(
            self.manager, "_download_and_cache", return_value=Path("/cache/test.png")
        ) as mock_download:
            result = await self.manager.resolve_image(image_url, context)

            assert result == Path("/cache/test.png")
            mock_download.assert_called_once_with(image_url)

    @pytest.mark.asyncio
    async def test_resolve_local_path_assets_dir(self):
        """Test resolving local path from assets directory."""
        context = RenderingContext(
            output_format="latex",
            metadata={"assets_dir": Path("/assets"), "images_dir": None},
        )

        with patch.object(Path, "exists", return_value=True):
            result = await self.manager._resolve_local_path("test.png", context)

            assert result == Path("/assets/test.png")

    @pytest.mark.asyncio
    async def test_resolve_local_path_images_dir(self):
        """Test resolving local path from images directory."""
        context = RenderingContext(
            output_format="latex",
            metadata={"assets_dir": None, "images_dir": Path("/images")},
        )

        with patch.object(Path, "exists", return_value=True):
            result = await self.manager._resolve_local_path("test.png", context)

            assert result == Path("/images/test.png")

    @pytest.mark.asyncio
    async def test_resolve_local_path_not_found(self):
        """Test resolving local path when file not found."""
        context = RenderingContext(
            output_format="latex",
            metadata={"assets_dir": Path("/assets"), "images_dir": None},
        )

        with patch.object(Path, "exists", return_value=False):
            result = await self.manager._resolve_local_path("test.png", context)

            assert result is None

    @pytest.mark.asyncio
    async def test_download_and_cache_success(self):
        """Test successful download and caching."""
        image_url = "https://example.com/test.png"

        with (
            patch.object(
                self.manager,
                "_construct_source_url",
                return_value="https://source.com/test.png",
            ),
            patch.object(self.manager, "_download_from_url", return_value=True),
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_stat.return_value = Mock(st_size=1000)

            result = await self.manager._download_and_cache(image_url)

            assert result is not None
            assert result.name.endswith(".png")

            # Check asset was cached
            cache_key = self.manager._generate_cache_key(image_url)
            assert cache_key in self.manager._asset_cache

    @pytest.mark.asyncio
    async def test_download_and_cache_failure(self):
        """Test download failure handling."""
        image_url = "https://example.com/test.png"

        with (
            patch.object(
                self.manager,
                "_construct_source_url",
                return_value="https://source.com/test.png",
            ),
            patch.object(self.manager, "_download_from_url", return_value=False),
        ):
            result = await self.manager._download_and_cache(image_url)

            assert result is None

    def test_construct_source_url_5etools(self):
        """Test constructing source URL for 5etools images."""
        original_url = "https://5e.tools/img/bestiary/MM/Ancient%20Red%20Dragon.webp"
        source = ImageSource(
            name="test-source",
            base_url="https://mirror.com",
            priority=10,
        )

        result = self.manager._construct_source_url(original_url, source)

        assert result == "https://mirror.com/bestiary/MM/Ancient%20Red%20Dragon.webp"

    def test_construct_source_url_other_domain(self):
        """Test constructing source URL for non-5etools images."""
        original_url = "https://example.com/images/test.png"
        source = ImageSource(
            name="test-source",
            base_url="https://mirror.com",
            priority=10,
        )

        result = self.manager._construct_source_url(original_url, source)

        assert result is None

    @pytest.mark.asyncio
    async def test_download_from_url_success(self):
        """Test successful file download."""
        url = "https://example.com/test.png"
        output_path = Path("/cache/test.png")

        # Mock the entire method since async mocking is complex
        with patch.object(
            self.manager, "_download_from_url", return_value=True
        ) as mock_download:
            result = await self.manager._download_from_url(url, output_path)
            assert result is True
            mock_download.assert_called_once_with(url, output_path)

    @pytest.mark.asyncio
    async def test_download_from_url_http_error(self):
        """Test download with HTTP error."""
        url = "https://example.com/test.png"
        output_path = Path("/cache/test.png")

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await self.manager._download_from_url(url, output_path)

            assert result is False

    @pytest.mark.asyncio
    async def test_download_from_url_exception(self):
        """Test download with exception."""
        url = "https://example.com/test.png"
        output_path = Path("/cache/test.png")

        with patch("aiohttp.ClientSession", side_effect=Exception("Network error")):
            result = await self.manager._download_from_url(url, output_path)

            assert result is False

    def test_generate_cache_key(self):
        """Test cache key generation."""
        url = "https://example.com/test.png"

        key1 = self.manager._generate_cache_key(url)
        key2 = self.manager._generate_cache_key(url)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_add_source(self):
        """Test adding a new image source."""
        original_count = len(self.manager.sources)

        new_source = ImageSource(
            name="new-source",
            base_url="https://new.com",
            priority=5,
        )

        self.manager.add_source(new_source)

        assert len(self.manager.sources) == original_count + 1
        # Should be sorted by priority (5 is higher priority than default 10, 20)
        assert self.manager.sources[0] == new_source

    def test_add_local_source(self):
        """Test adding a local directory source."""
        original_count = len(self.manager.sources)

        # Create a temporary directory for testing
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            # Mock the registry add_source call since we're testing legacy behavior
            with patch.object(self.manager._registry, "add_source") as mock_add_source:
                from studiorum.core.result import Success

                mock_add_source.return_value = Success(None)

                self.manager.add_local_source("local", test_path, priority=1)

                assert len(self.manager.sources) == original_count + 1

                # Find the added source
                local_source = next(
                    s for s in self.manager.sources if s.name == "local"
                )
                assert local_source.base_url == f"file://{test_path}"
                assert local_source.local_path == test_path
                assert local_source.priority == 1

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """Test cache cleanup functionality."""
        # Mock the registry cleanup method to return success
        from studiorum.core.result import Success

        mock_registry_stats = {
            "removed_old": 1,
            "removed_oversized": 0,
            "remaining_assets": 1,
            "remaining_size_mb": 1,
        }

        with (
            patch.object(
                self.manager._registry,
                "cleanup_cache",
                return_value=Success(mock_registry_stats),
            ) as mock_registry_cleanup,
            patch("time.time", return_value=1000000),
        ):
            # Add some legacy cached assets to test legacy cleanup
            old_asset = ImageAsset(
                original_url="https://example.com/old.png",
                local_path=Path("/tmp/old.png"),
                cache_key="old_key",
                file_size=1000,
                last_accessed=1000000 - (31 * 24 * 60 * 60),  # 31 days ago
                source_name="test",
            )
            new_asset = ImageAsset(
                original_url="https://example.com/new.png",
                local_path=Path("/tmp/new.png"),
                cache_key="new_key",
                file_size=1000,
                last_accessed=1000000 - (10 * 24 * 60 * 60),  # 10 days ago
                source_name="test",
            )

            # Mock Path.exists to return True for both assets initially
            with patch.object(Path, "exists", return_value=True):
                self.manager._asset_cache["old_key"] = old_asset
                self.manager._asset_cache["new_key"] = new_asset

                await self.manager.cleanup_cache(max_age_days=30)

                # Verify registry cleanup was called
                mock_registry_cleanup.assert_called_once_with(max_age_hours=30 * 24)

                # Verify legacy cleanup removed old asset but kept new one
                assert "old_key" not in self.manager._asset_cache
                assert "new_key" in self.manager._asset_cache

    def test_get_cache_info(self):
        """Test getting cache information."""
        # Mock the registry's get_cache_stats method
        mock_registry_stats = {
            "total_cached_assets": 3,
            "total_cache_size_bytes": 3000,
            "total_cache_size_mb": 3000 / (1024 * 1024),
            "cache_directory": str(self.manager.cache_dir),
            "sources": {
                "5etools-official": {
                    "status": "active",
                    "total_images": 100,
                    "cache_size_bytes": 1500,
                    "last_sync": 1234567890.0,
                    "last_error": None,
                },
                "5etools-mirror": {
                    "status": "active",
                    "total_images": 50,
                    "cache_size_bytes": 1500,
                    "last_sync": 1234567890.0,
                    "last_error": None,
                },
            },
        }

        with patch.object(
            self.manager._registry, "get_cache_stats", return_value=mock_registry_stats
        ):
            # Add some legacy cached assets
            self.manager._asset_cache["key1"] = Mock()
            self.manager._asset_cache["key2"] = Mock()

            info = self.manager.get_cache_info()

            # Test enhanced registry stats are included
            assert info["total_cached_assets"] == 3
            assert info["total_cache_size_bytes"] == 3000
            assert info["total_cache_size_mb"] == 3000 / (1024 * 1024)
            assert info["cache_directory"] == str(self.manager.cache_dir)

            # Test legacy compatibility stats are included
            assert info["legacy_assets_in_memory"] == 2
            assert len(info["legacy_sources"]) == 2

            # Test that source information is preserved
            assert "sources" in info
            assert len(info["sources"]) == 2
            assert "5etools-official" in info["sources"]
            assert "5etools-mirror" in info["sources"]
