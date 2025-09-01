"""Comprehensive unit tests for ContentSourceManager."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from studiorum.core.config.sources import (  # type: ignore
    ContentConfiguration,
    ContentSource,
    SourceType,
)
from studiorum.core.sources.github import GitHubSourceManager  # type: ignore
from studiorum.core.sources.manager import ContentSourceManager  # type: ignore


class TestContentSourceManager:
    """Test suite for ContentSourceManager with comprehensive coverage."""

    @pytest.fixture
    def mock_config(self) -> Any:
        """Create a mock ContentConfiguration."""
        config: Any = Mock(spec=ContentConfiguration)
        config.cache_dir = Path("/tmp/test_cache")
        config.get_enabled_sources.return_value = []
        config.get_source_by_name.return_value = None
        return config

    @pytest.fixture
    def github_source(self) -> Any:
        """Create a mock GitHub source."""
        source: Any = Mock(spec=ContentSource)
        source.name = "test-github"
        source.type = SourceType.GITHUB
        source.url = "https://github.com/test/repo"
        source.branch = "main"
        source.enabled = True
        source.priority = 1
        source.auto_update = True
        source.path = None
        return source

    @pytest.fixture
    def directory_source(self: Any, tmp_path: Any) -> Any:
        """Create a mock directory source."""
        source: Any = Mock(spec=ContentSource)
        source.name = "test-directory"
        source.type = SourceType.DIRECTORY
        source.path = tmp_path / "data"
        source.path.mkdir(exist_ok=True)
        source.enabled = True
        source.priority = 2
        source.auto_update = False
        source.url = None
        source.branch = None
        return source

    @pytest.fixture
    def manager(self: Any, mock_config: Any) -> Generator[Any, None, None]:
        """Create ContentSourceManager with mocked dependencies."""
        with patch(
            "studiorum.core.sources.manager.get_content_config",
            return_value=mock_config,
        ):
            with patch(
                "studiorum.core.sources.manager.GitHubSourceManager"
            ) as mock_github:
                mock_github_instance: Any = Mock(spec=GitHubSourceManager)
                mock_github.return_value = mock_github_instance
                manager: Any = ContentSourceManager()
                manager.github_manager = mock_github_instance
                yield manager

    # Initialization Tests
    def test_init_with_config(self, mock_config: Any) -> None:
        """Test initialization with provided config."""
        with patch("studiorum.core.sources.manager.GitHubSourceManager") as mock_github:
            manager: Any = ContentSourceManager(mock_config)
            assert manager.config == mock_config
            assert isinstance(manager._content_index, dict)
            assert manager._index_built is False
            mock_github.assert_called_once_with(mock_config.cache_dir)

    def test_init_with_default_config(self) -> None:
        """Test initialization with default config."""
        mock_config: Any = Mock(spec=ContentConfiguration)
        mock_config.cache_dir = Path("/tmp/cache")

        with patch(
            "studiorum.core.sources.manager.get_content_config",
            return_value=mock_config,
        ):
            with patch("studiorum.core.sources.manager.GitHubSourceManager"):
                manager: Any = ContentSourceManager()
                assert manager.config == mock_config

    # Source Availability Tests
    @pytest.mark.asyncio
    async def test_ensure_all_sources_no_sources(
        self, manager: Any, mock_config: Any
    ) -> None:
        """Test ensure_all_sources with no enabled sources."""
        mock_config.get_enabled_sources.return_value = []

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            await manager.ensure_all_sources()
            mock_logger.warning.assert_called_once_with(
                "No enabled content sources configured"
            )

    @pytest.mark.asyncio
    async def test_ensure_all_sources_git_not_available(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test ensure_all_sources when git is not available."""
        mock_config.get_enabled_sources.return_value = [github_source]
        manager.github_manager.is_git_available.return_value = False

        with pytest.raises(RuntimeError, match="Git is required for GitHub sources"):
            await manager.ensure_all_sources()

    @pytest.mark.asyncio
    async def test_ensure_all_sources_success(
        self, manager: Any, mock_config: Any, github_source: Any, directory_source: Any
    ) -> None:
        """Test successful ensure_all_sources operation."""
        mock_config.get_enabled_sources.return_value = [github_source, directory_source]
        manager.github_manager.is_git_available.return_value = True
        manager.github_manager.ensure_repository = AsyncMock()

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            await manager.ensure_all_sources()

            # Check that the right number of sources is logged
            mock_logger.info.assert_any_call("Ensuring 2 content sources are available")
            manager.github_manager.ensure_repository.assert_called_once_with(
                github_source
            )

    @pytest.mark.asyncio
    async def test_ensure_all_sources_with_exceptions(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test ensure_all_sources handling exceptions."""
        mock_config.get_enabled_sources.return_value = [github_source]
        manager.github_manager.is_git_available.return_value = True

        # Test that the method doesn't raise even if there are exceptions
        with patch.object(
            manager, "_ensure_github_source", side_effect=Exception("Test error")
        ):
            await manager.ensure_all_sources()  # Should not raise

    # GitHub Source Tests
    @pytest.mark.asyncio
    async def test_ensure_github_source_success(
        self, manager: Any, github_source: Any
    ) -> None:
        """Test successful GitHub source ensuring."""
        manager.github_manager.ensure_repository = AsyncMock()

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            await manager._ensure_github_source(github_source)

            manager.github_manager.ensure_repository.assert_called_once_with(
                github_source
            )
            mock_logger.info.assert_called_with("GitHub source 'test-github' is ready")

    @pytest.mark.asyncio
    async def test_ensure_github_source_failure(
        self, manager: Any, github_source: Any
    ) -> None:
        """Test GitHub source ensuring with failure."""
        manager.github_manager.ensure_repository = AsyncMock(
            side_effect=Exception("Network error")
        )

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            with pytest.raises(Exception, match="Network error"):
                await manager._ensure_github_source(github_source)

            mock_logger.error.assert_called_with(
                "Failed to ensure GitHub source 'test-github': Network error"
            )

    # Directory Source Tests
    @pytest.mark.asyncio
    async def test_ensure_directory_source_success(
        self, manager: Any, directory_source: Any
    ) -> None:
        """Test successful directory source ensuring."""
        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            await manager._ensure_directory_source(directory_source)
            mock_logger.info.assert_called_with(
                "Directory source 'test-directory' is ready"
            )

    @pytest.mark.asyncio
    async def test_ensure_directory_source_path_not_exists(
        self, manager: Any, directory_source: Any
    ) -> None:
        """Test directory source ensuring when path doesn't exist."""
        directory_source.path = Path("/nonexistent/path")

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            with pytest.raises(
                FileNotFoundError, match="Directory source path not found"
            ):
                await manager._ensure_directory_source(directory_source)

            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_directory_source_path_none(
        self, manager: Any, directory_source: Any
    ) -> None:
        """Test directory source ensuring with None path."""
        directory_source.path = None

        with pytest.raises(FileNotFoundError):
            await manager._ensure_directory_source(directory_source)

    @pytest.mark.asyncio
    async def test_ensure_directory_source_not_directory(
        self, manager: Any, directory_source: Any, tmp_path: Any
    ) -> None:
        """Test directory source ensuring when path is not a directory."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")
        directory_source.path = file_path

        with pytest.raises(ValueError, match="Path is not a directory"):
            await manager._ensure_directory_source(directory_source)

    # Content Index Building Tests
    @pytest.mark.asyncio
    async def test_build_content_index_already_built(self, manager: Any) -> None:
        """Test build_content_index when already built."""
        manager._index_built = True

        with patch.object(manager, "_get_source_files") as mock_get_files:
            await manager.build_content_index()
            mock_get_files.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_content_index_force_rebuild(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test build_content_index with force rebuild."""
        manager._index_built = True
        mock_config.get_enabled_sources.return_value = [github_source]

        mock_files = [Path("/test/file1.json"), Path("/test/file2.json")]
        with patch.object(
            manager, "_get_source_files", return_value=mock_files
        ) as mock_get_files:
            with patch("studiorum.core.sources.manager.logger") as mock_logger:
                await manager.build_content_index(force_rebuild=True)

                mock_get_files.assert_called_once_with(github_source)
                assert manager._content_index[github_source.name] == mock_files
                assert manager._index_built is True
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_build_content_index_with_exception(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test build_content_index handling exceptions."""
        mock_config.get_enabled_sources.return_value = [github_source]

        with patch.object(
            manager, "_get_source_files", side_effect=Exception("Test error")
        ):
            with patch("studiorum.core.sources.manager.logger") as mock_logger:
                await manager.build_content_index()

                assert manager._content_index[github_source.name] == []
                mock_logger.error.assert_called()

    # Source Files Discovery Tests
    @pytest.mark.asyncio
    async def test_get_source_files_github(
        self, manager: Any, github_source: Any
    ) -> None:
        """Test _get_source_files for GitHub source."""
        mock_files = [Path("/repo/spells.json"), Path("/repo/creatures.json")]
        manager.github_manager.ensure_repository = AsyncMock()
        manager.github_manager.list_content_files.return_value = mock_files

        result = await manager._get_source_files(github_source)

        assert result == mock_files
        manager.github_manager.ensure_repository.assert_called_once_with(github_source)
        manager.github_manager.list_content_files.assert_called_once_with(github_source)

    @pytest.mark.asyncio
    async def test_get_source_files_directory(
        self, manager: Any, directory_source: Any, tmp_path: Any
    ) -> None:
        """Test _get_source_files for directory source."""
        # Create test JSON files
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)

        file1 = data_dir / "spells.json"
        file1.write_text('{"spell": []}' + "x" * 50)  # Make it large enough

        directory_source.path = data_dir

        result = await manager._get_source_files(directory_source)

        # Should find the valid JSON file
        assert len(result) >= 1
        assert any(f.name == "spells.json" for f in result)

    @pytest.mark.asyncio
    async def test_get_source_files_directory_not_exists(
        self, manager: Any, directory_source: Any
    ) -> None:
        """Test _get_source_files for non-existent directory."""
        directory_source.path = Path("/nonexistent")

        result = await manager._get_source_files(directory_source)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_source_files_directory_none_path(
        self, manager: Any, directory_source: Any
    ) -> None:
        """Test _get_source_files for directory with None path."""
        directory_source.path = None

        result = await manager._get_source_files(directory_source)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_source_files_unsupported_type(self, manager: Any) -> None:
        """Test _get_source_files for unsupported source type."""
        source: Any = Mock()
        source.type = "UNSUPPORTED"

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            result = await manager._get_source_files(source)

            assert result == []
            mock_logger.warning.assert_called_with(
                "Unsupported source type: UNSUPPORTED"
            )

    # Index Access Tests
    def test_get_all_content_files_not_built(self, manager: Any) -> None:
        """Test get_all_content_files when index not built."""
        with pytest.raises(RuntimeError, match="Content index not built"):
            manager.get_all_content_files()

    def test_get_all_content_files_success(self, manager: Any) -> None:
        """Test successful get_all_content_files."""
        manager._index_built = True
        test_data = {"source1": [Path("/file1.json")], "source2": [Path("/file2.json")]}
        manager._content_index = test_data

        result = manager.get_all_content_files()

        assert result == test_data
        assert result is not manager._content_index  # Should be a copy

    def test_get_source_files_not_built(self, manager: Any) -> None:
        """Test get_source_files when index not built."""
        with pytest.raises(RuntimeError, match="Content index not built"):
            manager.get_source_files("test")

    def test_get_source_files_success(self, manager: Any) -> None:
        """Test successful get_source_files."""
        manager._index_built = True
        test_files = [Path("/file1.json"), Path("/file2.json")]
        manager._content_index = {"test-source": test_files}

        result = manager.get_source_files("test-source")
        assert result == test_files

    def test_get_source_files_not_found(self, manager: Any) -> None:
        """Test get_source_files for non-existent source."""
        manager._index_built = True
        manager._content_index = {}

        result = manager.get_source_files("nonexistent")
        assert result == []

    def test_get_files_by_pattern_not_built(self, manager: Any) -> None:
        """Test get_files_by_pattern when index not built."""
        with pytest.raises(RuntimeError, match="Content index not built"):
            manager.get_files_by_pattern("spell")

    def test_get_files_by_pattern_success(self, manager: Any) -> None:
        """Test successful get_files_by_pattern."""
        manager._index_built = True
        manager._content_index = {
            "source1": [Path("/spells.json"), Path("/creatures.json")],
            "source2": [Path("/items.json"), Path("/spell-list.json")],
        }

        result = manager.get_files_by_pattern("spell")

        expected = {
            "source1": [Path("/spells.json")],
            "source2": [Path("/spell-list.json")],
        }
        assert result == expected

    def test_get_files_by_pattern_no_matches(self, manager: Any) -> None:
        """Test get_files_by_pattern with no matches."""
        manager._index_built = True
        manager._content_index = {"source1": [Path("/creatures.json")]}

        result = manager.get_files_by_pattern("nonexistent")
        assert result == {}

    # Source Info Tests
    def test_get_source_info_not_found(self, manager: Any, mock_config: Any) -> None:
        """Test get_source_info for non-existent source."""
        mock_config.get_source_by_name.return_value = None

        result = manager.get_source_info("nonexistent")
        assert result is None

    def test_get_source_info_github(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test get_source_info for GitHub source."""
        mock_config.get_source_by_name.return_value = github_source
        manager._content_index = {
            github_source.name: [Path("/file1.json"), Path("/file2.json")]
        }

        git_info = {"last_commit": "abc123", "last_updated": "2023-01-01"}
        manager.github_manager.get_repository_info.return_value = git_info

        result = manager.get_source_info(github_source.name)

        expected = {
            "name": github_source.name,
            "type": github_source.type.value,
            "enabled": github_source.enabled,
            "priority": github_source.priority,
            "auto_update": github_source.auto_update,
            "file_count": 2,
            "url": github_source.url,
            "branch": github_source.branch,
            **git_info,
        }
        assert result == expected

    def test_get_source_info_directory(
        self, manager: Any, mock_config: Any, directory_source: Any
    ) -> None:
        """Test get_source_info for directory source."""
        mock_config.get_source_by_name.return_value = directory_source
        manager._content_index = {directory_source.name: [Path("/file1.json")]}

        result = manager.get_source_info(directory_source.name)

        expected = {
            "name": directory_source.name,
            "type": directory_source.type.value,
            "enabled": directory_source.enabled,
            "priority": directory_source.priority,
            "auto_update": directory_source.auto_update,
            "file_count": 1,
            "path": str(directory_source.path),
        }
        assert result == expected

    def test_get_source_info_github_no_git_info(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test get_source_info for GitHub source without git info."""
        mock_config.get_source_by_name.return_value = github_source
        manager._content_index = {github_source.name: []}
        manager.github_manager.get_repository_info.return_value = None

        result = manager.get_source_info(github_source.name)

        # Should not include git info fields
        assert "last_commit" not in result
        assert result["url"] == github_source.url

    # Source Update Tests
    @pytest.mark.asyncio
    async def test_update_source_not_found(
        self, manager: Any, mock_config: Any
    ) -> None:
        """Test update_source for non-existent source."""
        mock_config.get_source_by_name.return_value = None

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            result = await manager.update_source("nonexistent")

            assert result is False
            mock_logger.error.assert_called_with("Source 'nonexistent' not found")

    @pytest.mark.asyncio
    async def test_update_source_github_success(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test successful GitHub source update."""
        mock_config.get_source_by_name.return_value = github_source
        mock_files = [Path("/updated/file.json")]

        with patch.object(manager, "_ensure_github_source") as mock_ensure:
            with patch.object(
                manager, "_get_source_files", return_value=mock_files
            ) as mock_get_files:
                with patch("studiorum.core.sources.manager.logger") as mock_logger:
                    result = await manager.update_source(github_source.name)

                    assert result is True
                    mock_ensure.assert_called_once_with(github_source)
                    mock_get_files.assert_called_once_with(github_source)
                    assert manager._content_index[github_source.name] == mock_files
                    mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_update_source_directory_success(
        self, manager: Any, mock_config: Any, directory_source: Any
    ) -> None:
        """Test successful directory source update."""
        mock_config.get_source_by_name.return_value = directory_source
        mock_files = [Path("/updated/file.json")]

        with patch.object(manager, "_ensure_directory_source") as mock_ensure:
            with patch.object(manager, "_get_source_files", return_value=mock_files):
                result = await manager.update_source(directory_source.name)

                assert result is True
                mock_ensure.assert_called_once_with(directory_source)

    @pytest.mark.asyncio
    async def test_update_source_failure(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test update_source with failure."""
        mock_config.get_source_by_name.return_value = github_source

        with patch.object(
            manager, "_ensure_github_source", side_effect=Exception("Update failed")
        ):
            with patch("studiorum.core.sources.manager.logger") as mock_logger:
                result = await manager.update_source(github_source.name)

                assert result is False
                mock_logger.error.assert_called()

    # Source Removal Tests
    @pytest.mark.asyncio
    async def test_remove_source_data_not_found(
        self, manager: Any, mock_config: Any
    ) -> None:
        """Test remove_source_data for non-existent source."""
        mock_config.get_source_by_name.return_value = None

        result = await manager.remove_source_data("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_source_data_github_success(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test successful GitHub source data removal."""
        mock_config.get_source_by_name.return_value = github_source
        manager._content_index[github_source.name] = [Path("/file.json")]
        manager.github_manager.remove_repository.return_value = True

        result = await manager.remove_source_data(github_source.name)

        assert result is True
        manager.github_manager.remove_repository.assert_called_once_with(github_source)
        assert github_source.name not in manager._content_index

    @pytest.mark.asyncio
    async def test_remove_source_data_directory_success(
        self, manager: Any, mock_config: Any, directory_source: Any
    ) -> None:
        """Test successful directory source data removal."""
        mock_config.get_source_by_name.return_value = directory_source
        manager._content_index[directory_source.name] = [Path("/file.json")]

        result = await manager.remove_source_data(directory_source.name)

        assert result is True
        assert directory_source.name not in manager._content_index

    @pytest.mark.asyncio
    async def test_remove_source_data_exception(
        self, manager: Any, mock_config: Any, github_source: Any
    ) -> None:
        """Test remove_source_data with exception."""
        mock_config.get_source_by_name.return_value = github_source
        manager.github_manager.remove_repository.side_effect = Exception(
            "Removal failed"
        )

        with patch("studiorum.core.sources.manager.logger") as mock_logger:
            result = await manager.remove_source_data(github_source.name)

            assert result is False
            mock_logger.error.assert_called()

    # Statistics Tests
    def test_get_statistics_not_built(self, manager: Any) -> None:
        """Test get_statistics when index not built."""
        result = manager.get_statistics()
        assert result == {"error": "Content index not built"}

    def test_get_statistics_success(
        self, manager: Any, mock_config: Any, github_source: Any, directory_source: Any
    ) -> None:
        """Test successful get_statistics."""
        manager._index_built = True
        manager._content_index = {
            github_source.name: [Path("/file1.json"), Path("/file2.json")],
            directory_source.name: [Path("/file3.json")],
        }
        mock_config.get_enabled_sources.return_value = [github_source, directory_source]
        mock_config.cache_dir = Path("/cache")

        result = manager.get_statistics()

        expected = {
            "total_sources": 2,
            "total_files": 3,
            "sources": [
                {
                    "name": github_source.name,
                    "type": github_source.type.value,
                    "enabled": github_source.enabled,
                    "file_count": 2,
                },
                {
                    "name": directory_source.name,
                    "type": directory_source.type.value,
                    "enabled": directory_source.enabled,
                    "file_count": 1,
                },
            ],
            "cache_dir": "/cache",
        }
        assert result == expected

    def test_get_statistics_empty_sources(self, manager: Any, mock_config: Any) -> None:
        """Test get_statistics with no sources."""
        manager._index_built = True
        manager._content_index = {}
        mock_config.get_enabled_sources.return_value = []
        mock_config.cache_dir = Path("/cache")

        result = manager.get_statistics()

        expected = {
            "total_sources": 0,
            "total_files": 0,
            "sources": [],
            "cache_dir": "/cache",
        }
        assert result == expected


class TestContentSourceManagerIntegration:
    """Integration tests for ContentSourceManager with real file system."""

    @pytest.mark.asyncio
    async def test_directory_source_integration(self, tmp_path: Any) -> None:
        """Integration test with real directory source."""
        # Create test data structure
        data_dir = tmp_path / "test_data"
        data_dir.mkdir(exist_ok=True)

        spells_dir = data_dir / "spells"
        spells_dir.mkdir(exist_ok=True)

        spell_file = spells_dir / "core.json"
        spell_file.write_text(
            '{"spell": [{"name": "Fireball"}]}' + "x" * 50
        )  # Make it large enough

        items_file = data_dir / "items.json"
        items_file.write_text(
            '{"item": [{"name": "Sword"}]}' + "y" * 50
        )  # Make it large enough

        # Create source
        source: Any = Mock(spec=ContentSource)
        source.name = "test"
        source.type = SourceType.DIRECTORY
        source.path = data_dir
        source.enabled = True
        source.priority = 1
        source.auto_update = False

        # Create config
        config: Any = Mock(spec=ContentConfiguration)
        config.cache_dir = tmp_path / "cache"
        config.get_enabled_sources.return_value = [source]
        config.get_source_by_name.return_value = source

        # Test manager
        with patch(
            "studiorum.core.sources.manager.get_content_config", return_value=config
        ):
            with patch("studiorum.core.sources.manager.GitHubSourceManager"):
                manager: Any = ContentSourceManager()

                # Test source ensuring
                await manager.ensure_all_sources()

                # Test index building
                await manager.build_content_index()

                # Verify results
                files = manager.get_source_files("test")
                assert len(files) == 2
                assert any(f.name == "core.json" for f in files)
                assert any(f.name == "items.json" for f in files)

                # Test pattern matching
                spell_files = manager.get_files_by_pattern("core")
                assert "test" in spell_files
                assert len(spell_files["test"]) == 1
