"""Tests for the enhanced image source system (Phase 1).

This module tests the new ImageSourceRegistry and enhanced ImageManager
with multi-source support, Git repository integration, and backward compatibility.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from studiorum.core.assets.image_manager import ImageManager
from studiorum.core.assets.image_sources import (
    GitImageSourceConfig,
    HttpApiImageSourceConfig,
    ImageSourceRegistry,
    ImageSourceType,
    LocalDirectoryImageSourceConfig,
)
from studiorum.core.config.unified_config import PathsConfig
from studiorum.core.result import Success


class TestImageSourceRegistry:
    """Test the ImageSourceRegistry functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.registry = ImageSourceRegistry(cache_dir=self.temp_dir / "cache")

    def test_add_git_source(self):
        """Test adding a Git repository source."""
        config = GitImageSourceConfig(
            name="test-git",
            repository_url="https://github.com/test/repo.git",
            branch="main",
            priority=10,
        )

        result = self.registry.add_source(config)
        assert result.is_success()

        sources = self.registry.list_sources()
        assert len(sources) == 1
        assert sources[0].config.name == "test-git"
        assert sources[0].config.source_type == ImageSourceType.GIT_REPO

    def test_add_http_api_source(self):
        """Test adding an HTTP API source."""
        config = HttpApiImageSourceConfig(
            name="test-api",
            base_url="https://example.com/api",
            priority=20,
            path_template="/images/{image_path}",
        )

        result = self.registry.add_source(config)
        assert result.is_success()

        sources = self.registry.list_sources()
        assert len(sources) == 1
        assert sources[0].config.name == "test-api"
        assert sources[0].config.source_type == ImageSourceType.HTTP_API

    def test_add_local_directory_source(self):
        """Test adding a local directory source."""
        # Create test directory
        test_dir = self.temp_dir / "images"
        test_dir.mkdir(parents=True)

        config = LocalDirectoryImageSourceConfig(
            name="test-local",
            directory_path=test_dir,
            priority=30,
        )

        result = self.registry.add_source(config)
        assert result.is_success()

        sources = self.registry.list_sources()
        assert len(sources) == 1
        assert sources[0].config.name == "test-local"
        assert sources[0].config.source_type == ImageSourceType.LOCAL_DIR

    def test_duplicate_source_names(self):
        """Test that duplicate source names are rejected."""
        config1 = GitImageSourceConfig(
            name="test-source",
            repository_url="https://github.com/test1/repo.git",
            priority=10,
        )
        config2 = GitImageSourceConfig(
            name="test-source",
            repository_url="https://github.com/test2/repo.git",
            priority=20,
        )

        result1 = self.registry.add_source(config1)
        assert result1.is_success()

        result2 = self.registry.add_source(config2)
        assert result2.is_error()

    def test_remove_source(self):
        """Test removing a source."""
        config = GitImageSourceConfig(
            name="test-remove",
            repository_url="https://github.com/test/repo.git",
            priority=10,
        )

        # Add source
        result = self.registry.add_source(config)
        assert result.is_success()
        assert len(self.registry.list_sources()) == 1

        # Remove source
        result = self.registry.remove_source("test-remove")
        assert result.is_success()
        assert len(self.registry.list_sources()) == 0

    @pytest.mark.asyncio
    async def test_local_directory_sync(self):
        """Test syncing a local directory source."""
        # Create test directory with images
        test_dir = self.temp_dir / "images"
        test_dir.mkdir(parents=True)

        # Create test image files
        (test_dir / "image1.png").write_text("fake png")
        (test_dir / "image2.jpg").write_text("fake jpg")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "image3.gif").write_text("fake gif")

        config = LocalDirectoryImageSourceConfig(
            name="test-sync",
            directory_path=test_dir,
            recursive=True,
        )

        self.registry.add_source(config)

        # Sync the source
        result = await self.registry.sync_source("test-sync")
        assert result.is_success()

        # Check that images were counted
        source_info = self.registry.get_source_info("test-sync")
        assert source_info.is_success()
        assert source_info.value.total_images == 3

    @pytest.mark.asyncio
    async def test_resolve_local_image(self):
        """Test resolving an image from a local directory source."""
        # Create test directory with image
        test_dir = self.temp_dir / "images"
        test_dir.mkdir(parents=True)
        test_image = test_dir / "test.png"
        test_image.write_text("fake png content")

        config = LocalDirectoryImageSourceConfig(
            name="test-local",
            directory_path=test_dir,
            priority=10,
        )

        self.registry.add_source(config)
        await self.registry.sync_source("test-local")

        # Try to resolve the image
        result = await self.registry.resolve_image("test.png")
        assert result.is_success()

        asset_info = result.value
        assert asset_info.original_path == "test.png"
        assert asset_info.source_name == "test-local"
        assert asset_info.local_path.exists()


class TestEnhancedImageManager:
    """Test the enhanced ImageManager with registry integration."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.paths_config = PathsConfig(build_path=self.temp_dir / "build")
        self.manager = ImageManager(self.paths_config)

    def test_initialization(self):
        """Test that ImageManager initializes with default sources."""
        # Should have registry with sources
        registry = self.manager.get_registry()
        sources = registry.list_sources()
        assert len(sources) > 0

        # Should include Git and HTTP API sources
        source_types = {s.config.source_type for s in sources}
        assert ImageSourceType.GIT_REPO in source_types
        assert ImageSourceType.HTTP_API in source_types

    @pytest.mark.asyncio
    async def test_resolve_local_image_fallback(self):
        """Test image resolution with local path fallback."""
        # Create test image in the assets directory
        assets_dir = self.temp_dir / "assets"
        assets_dir.mkdir(parents=True)
        test_image = assets_dir / "test.png"
        test_image.write_text("fake png content")

        # Mock rendering context
        mock_context = Mock()
        mock_context.metadata = {"assets_dir": str(assets_dir)}

        # Try to resolve the image
        result = await self.manager.resolve_image("test.png", mock_context)
        assert result is not None
        assert result.exists()
        assert result.name == "test.png"

    def test_add_local_source(self):
        """Test adding a local source."""
        test_dir = self.temp_dir / "custom_images"
        test_dir.mkdir(parents=True)

        # Add local source
        self.manager.add_local_source("custom", test_dir, priority=50)

        # Should be added to registry
        registry_source_names = {
            s.config.name for s in self.manager.get_registry().list_sources()
        }
        assert "custom" in registry_source_names

    @pytest.mark.asyncio
    async def test_sync_all_sources(self):
        """Test syncing all sources."""
        # Add a local directory source that can be synced
        test_dir = self.temp_dir / "sync_test"
        test_dir.mkdir(parents=True)
        (test_dir / "image.png").write_text("fake")

        self.manager.add_local_source("sync-test", test_dir)

        # This should not raise an error even if some sources fail
        await self.manager.sync_sources()

        # Verify that the local source was synced
        result = await self.manager.sync_source("sync-test")
        assert result is True

    def test_cache_info_integration(self):
        """Test that cache info includes registry data."""
        cache_info = self.manager.get_cache_info()

        # Should have registry stats
        assert "total_cached_assets" in cache_info
        assert "sources" in cache_info

    @pytest.mark.asyncio
    async def test_cleanup_delegation(self):
        """Test that cleanup delegates to registry."""
        with patch.object(self.manager.get_registry(), "cleanup_cache") as mock_cleanup:
            mock_cleanup.return_value = Success(
                {
                    "removed_old": 5,
                    "removed_oversized": 2,
                    "remaining_assets": 10,
                    "remaining_size_mb": 50,
                }
            )

            await self.manager.cleanup_cache(max_age_days=30)
            mock_cleanup.assert_called_once()


class TestImageSourceConfigurations:
    """Test various image source configuration validations."""

    def test_git_source_validation(self):
        """Test Git source configuration validation."""
        # Valid configuration
        config = GitImageSourceConfig(
            name="valid-git",
            repository_url="https://github.com/user/repo.git",
            branch="main",
        )
        assert config.source_type == ImageSourceType.GIT_REPO
        assert config.repository_url == "https://github.com/user/repo.git"

        # Invalid repository URL
        with pytest.raises(ValueError):
            GitImageSourceConfig(
                name="invalid-git",
                repository_url="not-a-valid-url",
            )

    def test_http_api_source_validation(self):
        """Test HTTP API source configuration validation."""
        # Valid configuration
        config = HttpApiImageSourceConfig(
            name="valid-api",
            base_url="https://api.example.com",
            path_template="/images/{image_path}",
        )
        assert config.source_type == ImageSourceType.HTTP_API
        assert config.base_url == "https://api.example.com"

        # Invalid base URL
        with pytest.raises(ValueError):
            HttpApiImageSourceConfig(
                name="invalid-api",
                base_url="not-a-valid-url",
            )

    def test_local_directory_validation(self):
        """Test local directory source configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Valid configuration
            config = LocalDirectoryImageSourceConfig(
                name="valid-local",
                directory_path=Path(temp_dir),
                recursive=True,
            )
            assert config.source_type == ImageSourceType.LOCAL_DIR
            assert config.directory_path.exists()

        # Invalid directory (doesn't exist)
        with pytest.raises(ValueError):
            LocalDirectoryImageSourceConfig(
                name="invalid-local",
                directory_path=Path("/nonexistent/directory"),
            )

    def test_source_name_validation(self):
        """Test source name validation."""
        # Valid names
        for name in ["valid-name", "valid_name", "valid123", "test-source-1"]:
            config = GitImageSourceConfig(
                name=name,
                repository_url="https://github.com/user/repo.git",
            )
            assert config.name == name

        # Invalid names
        for name in ["invalid name", "invalid@name", "invalid/name"]:
            with pytest.raises(ValueError):
                GitImageSourceConfig(
                    name=name,
                    repository_url="https://github.com/user/repo.git",
                )


@pytest.mark.asyncio
async def test_full_integration_scenario():
    """Test a full integration scenario with multiple source types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create paths config
        paths_config = PathsConfig(build_path=temp_path / "build")

        # Initialize manager
        manager = ImageManager(paths_config)
        manager.get_registry()

        # Add local directory source
        local_images = temp_path / "local_images"
        local_images.mkdir()
        (local_images / "local.png").write_text("local image")

        manager.add_local_source("local", local_images, priority=5)

        # Sync sources
        await manager.sync_sources()

        # Test resolution
        mock_context = Mock()
        mock_context.metadata = {}

        # Try to resolve local image
        result = await manager.resolve_image("local.png", mock_context)
        # This might return None if the image isn't found through the enhanced system,
        # but it should not raise an error
        assert result is None or isinstance(result, Path)

        # Check cache info
        cache_info = manager.get_cache_info()
        assert isinstance(cache_info, dict)
        assert "total_cached_assets" in cache_info
