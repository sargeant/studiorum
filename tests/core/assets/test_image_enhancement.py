"""Tests for the enhanced image source system (Phase 1).

This module tests the new ImageSourceRegistry and enhanced ImageManager
with multi-source support, Git repository integration, and backward compatibility.
"""

import tempfile
from pathlib import Path

import pytest

from studiorum.core.assets.image_sources import (
    GitImageSourceConfig,
    HttpApiImageSourceConfig,
    ImageSourceRegistry,
    ImageSourceType,
    LocalDirectoryImageSourceConfig,
)


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
