"""Tests for the image asset manager."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dnd5e.core.assets.image_manager import ImageAsset, ImageManager, ImageSource
from dnd5e.core.config.paths import PathsConfig
from dnd5e.renderers.base.context import RenderContext


class TestImageSource:
    """Test the image source configuration."""

    def test_image_source_creation(self):
        """Test creating an image source."""
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
        """Test image source with local path."""
        source = ImageSource(
            name="local-source",
            base_url="file:///tmp/images",
            local_path=Path("/tmp/images"),
            priority=10,
        )

        assert source.local_path == Path("/tmp/images")


class TestImageAsset:
    """Test the image asset model."""

    def test_image_asset_creation(self):
        """Test creating an image asset."""
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
        self.paths_config = Mock(spec=PathsConfig)
        self.paths_config.cache_dir = Path("/tmp/cache")
        self.manager = ImageManager(self.paths_config)

        # Mock the cache directory creation
        with patch("pathlib.Path.mkdir"):
            pass

    def test_init_default_sources(self):
        """Test initialization with default image sources."""
        assert len(self.manager.sources) == 2

        # Check 5etools sources are configured
        source_names = [s.name for s in self.manager.sources]
        assert "5etools-official" in source_names
        assert "5etools-mirror" in source_names

    def test_init_cache_dir_setup(self):
        """Test cache directory initialization."""
        assert self.manager.cache_dir == Path("/tmp/cache/images")

    @pytest.mark.asyncio
    async def test_resolve_image_local_path(self):
        """Test resolving local image paths."""
        context = Mock(spec=RenderContext)
        context.assets_dir = Path("/assets")
        context.images_dir = None

        with patch.object(
            self.manager, "_resolve_local_path", return_value=Path("/assets/test.png")
        ) as mock_resolve:
            result = await self.manager.resolve_image("test.png", context)

            assert result == Path("/assets/test.png")
            mock_resolve.assert_called_once_with("test.png", context)

    @pytest.mark.asyncio
    async def test_resolve_image_url_cached(self):
        """Test resolving URL with cached result."""
        context = Mock(spec=RenderContext)
        image_url = "https://example.com/test.png"

        # Add cached asset
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

        with patch.object(Path, "exists", return_value=True):
            result = await self.manager.resolve_image(image_url, context)

            assert result == cached_path

    @pytest.mark.asyncio
    async def test_resolve_image_url_download(self):
        """Test resolving URL with download."""
        context = Mock(spec=RenderContext)
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
        context = Mock(spec=RenderContext)
        context.assets_dir = Path("/assets")
        context.images_dir = None

        with patch.object(Path, "exists", return_value=True):
            result = await self.manager._resolve_local_path("test.png", context)

            assert result == Path("/assets/test.png")

    @pytest.mark.asyncio
    async def test_resolve_local_path_images_dir(self):
        """Test resolving local path from images directory."""
        context = Mock(spec=RenderContext)
        context.assets_dir = None
        context.images_dir = Path("/images")

        with patch.object(Path, "exists", return_value=True):
            result = await self.manager._resolve_local_path("test.png", context)

            assert result == Path("/images/test.png")

    @pytest.mark.asyncio
    async def test_resolve_local_path_not_found(self):
        """Test resolving local path when file not found."""
        context = Mock(spec=RenderContext)
        context.assets_dir = Path("/assets")
        context.images_dir = None

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

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_chunked = AsyncMock(return_value=[b"test data"])

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with (
            patch("aiohttp.ClientSession", return_value=mock_session),
            patch("aiofiles.open", AsyncMock()),
            patch("pathlib.Path.mkdir"),
        ):
            result = await self.manager._download_from_url(url, output_path)

            assert result is True

    @pytest.mark.asyncio
    async def test_download_from_url_http_error(self):
        """Test download with HTTP error."""
        url = "https://example.com/test.png"
        output_path = Path("/cache/test.png")

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

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

        self.manager.add_local_source("local", Path("/local/images"), priority=1)

        assert len(self.manager.sources) == original_count + 1

        # Find the added source
        local_source = next(s for s in self.manager.sources if s.name == "local")
        assert local_source.base_url == "file:///local/images"
        assert local_source.local_path == Path("/local/images")
        assert local_source.priority == 1

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """Test cache cleanup functionality."""
        # Create some test cache files
        old_file = self.manager.cache_dir / "old.png"
        new_file = self.manager.cache_dir / "new.png"

        with (
            patch.object(Path, "glob") as mock_glob,
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "stat") as mock_stat,
            patch.object(Path, "unlink") as mock_unlink,
            patch("time.time", return_value=1000000),
        ):
            # Mock old file (older than 30 days)
            old_stat = Mock()
            old_stat.st_mtime = 1000000 - (31 * 24 * 60 * 60)  # 31 days ago

            # Mock new file (recent)
            new_stat = Mock()
            new_stat.st_mtime = 1000000 - (10 * 24 * 60 * 60)  # 10 days ago

            mock_glob.return_value = [old_file, new_file]
            mock_stat.side_effect = (
                lambda: old_stat
                if "old" in str(mock_stat.call_args[0][0])
                else new_stat
            )

            await self.manager.cleanup_cache(max_age_days=30)

            # Old file should be deleted, new file should not
            mock_unlink.assert_called_once()

    def test_get_cache_info(self):
        """Test getting cache information."""
        with (
            patch.object(Path, "glob") as mock_glob,
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_glob.return_value = [Path("file1.png"), Path("file2.png")]
            mock_stat.return_value = Mock(st_size=1000)

            # Add some cached assets
            self.manager._asset_cache["key1"] = Mock()
            self.manager._asset_cache["key2"] = Mock()

            info = self.manager.get_cache_info()

            assert info["total_files"] == 2
            assert info["total_size_bytes"] == 2000
            assert info["total_size_mb"] == 2000 / (1024 * 1024)
            assert info["assets_in_memory"] == 2
            assert len(info["sources"]) == 2
