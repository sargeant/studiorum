"""Tests for the image asset manager."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.core.assets.image_manager import ImageManager
from studiorum.core.config.unified_config import PathsConfig
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


class TestImageManager:
    """Test the image manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

        self.paths_config = Mock(spec=PathsConfig)
        self.paths_config.build_path = Path("/tmp/build")
        with patch("pathlib.Path.mkdir"):
            self.manager = ImageManager(self.paths_config)

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

    def test_add_local_source(self):
        """Test adding a local directory source."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            with patch.object(self.manager._registry, "add_source") as mock_add_source:
                from studiorum.core.result import Success

                mock_add_source.return_value = Success(None)

                self.manager.add_local_source("local", test_path, priority=1)

                mock_add_source.assert_called_once()
                call_args = mock_add_source.call_args[0][0]
                assert call_args.name == "local"
                assert call_args.directory_path == test_path
                assert call_args.priority == 1

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """Test cache cleanup functionality."""
        from studiorum.core.result import Success

        mock_registry_stats = {
            "removed_old": 1,
            "removed_oversized": 0,
            "remaining_assets": 1,
            "remaining_size_mb": 1,
        }

        with patch.object(
            self.manager._registry,
            "cleanup_cache",
            return_value=Success(mock_registry_stats),
        ) as mock_registry_cleanup:
            await self.manager.cleanup_cache(max_age_days=30)

            mock_registry_cleanup.assert_called_once_with(max_age_hours=30 * 24)

    def test_get_cache_info(self):
        """Test getting cache information."""
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
            info = self.manager.get_cache_info()

            assert info["total_cached_assets"] == 3
            assert info["total_cache_size_bytes"] == 3000
            assert info["total_cache_size_mb"] == 3000 / (1024 * 1024)
            assert info["cache_directory"] == str(self.manager.cache_dir)

            assert "sources" in info
            assert len(info["sources"]) == 2
            assert "5etools-official" in info["sources"]
            assert "5etools-mirror" in info["sources"]
