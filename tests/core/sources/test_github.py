"""Tests for GitHub source manager."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from studiorum.core.config.sources import ContentSource, SourceType
from studiorum.core.sources.github import GitHubSourceManager
from tests.test_helpers import reset_test_environment


class TestGitHubSourceManager:
    """Test GitHub source manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.manager = GitHubSourceManager(self.cache_dir)

        # Create test source
        self.test_source = ContentSource(
            name="test-repo",
            type=SourceType.GITHUB,
            url="https://github.com/test/repo.git",
            branch="main",
            auto_update=True,
            enabled=True,
        )
        self.non_github_source = ContentSource(
            name="local-source",
            type=SourceType.DIRECTORY,
            path="/some/path",
            enabled=True,
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test GitHubSourceManager initialization."""
        assert self.manager.cache_dir == self.cache_dir
        assert self.manager.repos_dir == self.cache_dir / "repositories"
        assert self.manager.repos_dir.exists()

    def test_get_repo_path_valid_source(self):
        """Test getting repository path for valid GitHub source."""
        repo_path = self.manager.get_repo_path(self.test_source)
        expected_path = self.cache_dir / "repositories" / "test-repo"
        assert repo_path == expected_path

    def test_get_repo_path_invalid_source(self):
        """Test getting repository path for non-GitHub source raises error."""
        with pytest.raises(ValueError, match="is not a GitHub source"):
            self.manager.get_repo_path(self.non_github_source)

    @pytest.mark.asyncio
    async def test_ensure_repository_clone_new(self):
        """Test ensuring repository clones when doesn't exist."""
        with patch.object(self.manager, "_clone_repository") as mock_clone:
            mock_clone.return_value = None

            repo_path = await self.manager.ensure_repository(self.test_source)

            expected_path = self.cache_dir / "repositories" / "test-repo"
            assert repo_path == expected_path
            mock_clone.assert_called_once_with(self.test_source, expected_path)

    @pytest.mark.asyncio
    async def test_ensure_repository_update_existing(self):
        """Test ensuring repository updates when exists and auto_update is True."""
        # Create fake repository directory
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)

        with patch.object(self.manager, "_update_repository") as mock_update:
            mock_update.return_value = None

            result_path = await self.manager.ensure_repository(self.test_source)

            assert result_path == repo_path
            mock_update.assert_called_once_with(self.test_source, repo_path)

    @pytest.mark.asyncio
    async def test_ensure_repository_no_update_when_disabled(self):
        """Test ensuring repository doesn't update when auto_update is False."""
        # Create source with auto_update disabled
        source = ContentSource(
            name="test-repo",
            type=SourceType.GITHUB,
            url="https://github.com/test/repo.git",
            branch="main",
            auto_update=False,
            enabled=True,
        )

        # Create fake repository directory
        repo_path = self.manager.get_repo_path(source)
        repo_path.mkdir(parents=True)

        with patch.object(self.manager, "_update_repository") as mock_update:
            result_path = await self.manager.ensure_repository(source)

            assert result_path == repo_path
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_repository_invalid_source_type(self):
        """Test ensuring repository with non-GitHub source raises error."""
        with pytest.raises(ValueError, match="is not a GitHub source"):
            await self.manager.ensure_repository(self.non_github_source)

    @pytest.mark.asyncio
    async def test_clone_repository_success(self):
        """Test successful repository cloning."""
        repo_path = self.manager.get_repo_path(self.test_source)

        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await self.manager._clone_repository(self.test_source, repo_path)

            # Verify git clone command was called
            mock_process.communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_repository_with_branch(self):
        """Test repository cloning with specific branch."""
        repo_path = self.manager.get_repo_path(self.test_source)

        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"success", b"")

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            await self.manager._clone_repository(self.test_source, repo_path)

            # Verify command includes branch specification
            call_args = mock_exec.call_args[0]
            assert "--branch" in call_args
            assert "main" in call_args

    @pytest.mark.asyncio
    async def test_clone_repository_no_url(self):
        """Test repository cloning with missing URL."""
        # Create a source with URL initially, then set to None to bypass validation
        source = ContentSource(
            name="test-repo",
            type=SourceType.GITHUB,
            url="https://example.com",
            enabled=True,
        )
        source.url = None  # Set to None after creation
        repo_path = self.manager.get_repo_path(source)

        # The method should raise RuntimeError, not ValueError directly
        with pytest.raises(RuntimeError, match="Failed to clone repository"):
            await self.manager._clone_repository(source, repo_path)

    @pytest.mark.asyncio
    async def test_clone_repository_git_failure(self):
        """Test repository cloning with git command failure."""
        repo_path = self.manager.get_repo_path(self.test_source)

        # Mock failed subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"fatal: repository not found")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(RuntimeError, match="Failed to clone repository"):
                await self.manager._clone_repository(self.test_source, repo_path)

    @pytest.mark.asyncio
    async def test_clone_repository_exception_cleanup(self):
        """Test repository cloning cleans up on exception."""
        repo_path = self.manager.get_repo_path(self.test_source)

        # Create partial repository directory
        repo_path.mkdir(parents=True)
        test_file = repo_path / "test.txt"
        test_file.write_text("test")

        # Mock subprocess to raise exception
        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("Network error")
        ):
            with pytest.raises(RuntimeError, match="Failed to clone repository"):
                await self.manager._clone_repository(self.test_source, repo_path)

            # Verify cleanup happened
            assert not repo_path.exists()

    @pytest.mark.asyncio
    async def test_update_repository_success(self):
        """Test successful repository update."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()  # Fake git directory

        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Already up to date.", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await self.manager._update_repository(self.test_source, repo_path)

            mock_process.communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_repository_not_git_repo(self):
        """Test update when directory is not a git repository."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        # No .git directory - not a git repo

        with patch.object(self.manager, "_clone_repository") as mock_clone:
            mock_clone.return_value = None

            await self.manager._update_repository(self.test_source, repo_path)

            # Should re-clone instead of update
            mock_clone.assert_called_once_with(self.test_source, repo_path)
            assert not repo_path.exists()  # Directory should be removed

    @pytest.mark.asyncio
    async def test_update_repository_git_failure(self):
        """Test update with git command failure (should not raise)."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        # Mock failed subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"fatal: not a git repository")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Should not raise exception
            await self.manager._update_repository(self.test_source, repo_path)

    @pytest.mark.asyncio
    async def test_update_repository_exception(self):
        """Test update with exception (should not raise)."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("Network error")
        ):
            # Should not raise exception
            await self.manager._update_repository(self.test_source, repo_path)

    def test_is_git_available_true(self):
        """Test git availability check when git is available."""
        with (
            patch("subprocess.run") as mock_run,
            patch("dnd5e.core.sources.github.get_git_executable") as mock_get_git,
        ):
            mock_get_git.return_value = "git"
            mock_run.return_value = None  # Successful completion

            result = self.manager.is_git_available()

            assert result is True
            mock_get_git.assert_called_once()
            mock_run.assert_called_once_with(
                ["git", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

    def test_is_git_available_false_not_found(self):
        """Test git availability check when git command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = self.manager.is_git_available()
            assert result is False

    def test_is_git_available_false_command_error(self):
        """Test git availability check when git command fails."""
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            result = self.manager.is_git_available()
            assert result is False

    def test_get_repository_info_success(self):
        """Test getting repository information successfully."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        # Mock subprocess responses
        responses = [
            Mock(stdout="abc123def456", returncode=0),  # commit hash
            Mock(stdout="2023-07-28 12:00:00 +1200", returncode=0),  # commit date
            Mock(stdout="main", returncode=0),  # current branch
        ]

        with patch("subprocess.run", side_effect=responses):
            info = self.manager.get_repository_info(self.test_source)

            assert info is not None
            assert info["commit_hash"] == "abc123def456"
            assert info["last_commit_date"] == "2023-07-28 12:00:00 +1200"
            assert info["current_branch"] == "main"
            assert info["local_path"] == str(repo_path)

    def test_get_repository_info_no_repo(self):
        """Test getting repository information when repo doesn't exist."""
        info = self.manager.get_repository_info(self.test_source)
        assert info is None

    def test_get_repository_info_not_git_repo(self):
        """Test getting repository information when directory is not a git repo."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        # No .git directory

        info = self.manager.get_repository_info(self.test_source)
        assert info is None

    def test_get_repository_info_git_command_failure(self):
        """Test getting repository information when git commands fail."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            info = self.manager.get_repository_info(self.test_source)
            assert info is None

    def test_remove_repository_success(self):
        """Test successful repository removal."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)
        test_file = repo_path / "test.txt"
        test_file.write_text("test")

        result = self.manager.remove_repository(self.test_source)

        assert result is True
        assert not repo_path.exists()

    def test_remove_repository_not_exists(self):
        """Test removing repository that doesn't exist."""
        result = self.manager.remove_repository(self.test_source)
        assert result is True  # Already removed

    def test_remove_repository_failure(self):
        """Test repository removal failure."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)

        with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
            result = self.manager.remove_repository(self.test_source)
            assert result is False

    def test_list_content_files_success(self):
        """Test listing content files in repository."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)

        # Create test JSON files
        data_dir = repo_path / "data"
        data_dir.mkdir()

        # Valid content files (ensure they're large enough to pass size filter)
        spell_file = data_dir / "spells.json"
        spell_file.write_text(
            '{"spell": [{"name": "Fireball", "description": "A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame."}]}'
        )

        monster_file = data_dir / "monsters.json"
        monster_file.write_text(
            '{"monster": [{"name": "Goblin", "description": "A small, black-hearted, selfish humanoid that ranges from 3 to 3 1/2 feet tall."}]}'
        )

        # Files that should be excluded
        (repo_path / "package.json").write_text('{"name": "test"}')
        (repo_path / "meta.json").write_text('{"version": "1.0"}')

        # Small file that should be excluded
        small_file = data_dir / "small.json"
        small_file.write_text("{}")  # Very small content

        files = self.manager.list_content_files(self.test_source)

        # Should include only the larger content files
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "spells.json" in file_names
        assert "monsters.json" in file_names
        assert "package.json" not in file_names
        assert "meta.json" not in file_names
        assert "small.json" not in file_names

    def test_list_content_files_no_repo(self):
        """Test listing content files when repository doesn't exist."""
        files = self.manager.list_content_files(self.test_source)
        assert files == []

    def test_list_content_files_exclude_patterns(self):
        """Test content file listing excludes common non-content patterns."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)

        # Create directories and files that should be excluded
        node_modules = repo_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "test.json").write_text('{"test": "data"}')

        git_dir = repo_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.json").write_text('{"test": "data"}')

        pycache = repo_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cache.json").write_text('{"test": "data"}')

        # Valid content file (ensure it's large enough to pass size filter)
        data_dir = repo_path / "data"
        data_dir.mkdir()
        content_file = data_dir / "content.json"
        content_file.write_text(
            '{"content": [{"name": "Test Content", "description": "This is a test content file with enough content to pass the size filter for proper testing."}]}'
        )

        files = self.manager.list_content_files(self.test_source)

        # Should only include the valid content file
        assert len(files) == 1
        assert files[0].name == "content.json"

    def test_list_content_files_file_access_error(self):
        """Test content file listing handles file access errors gracefully."""
        repo_path = self.manager.get_repo_path(self.test_source)
        repo_path.mkdir(parents=True)

        # Create a file we can access (ensure it's large enough to pass size filter)
        valid_file = repo_path / "valid.json"
        valid_file.write_text(
            '{"valid": "content", "description": "This is a valid test file with sufficient content to pass the size filter."}'
        )

        # Create mock file that raises OSError on stat()
        error_file = Mock()
        error_file.stat.side_effect = OSError("Permission denied")
        error_file.__str__ = Mock(return_value="error.json")

        with patch("pathlib.Path.rglob") as mock_rglob:
            # Setup mock to return files including one that will error on stat()
            mock_rglob.return_value = [error_file, valid_file]

            files = self.manager.list_content_files(self.test_source)

            # Should skip the error file and include the valid one
            assert len(files) == 1
            assert files[0].name == "valid.json"


class TestGitHubSourceManagerEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.manager = GitHubSourceManager(self.cache_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_clone_repository_default_branch(self):
        """Test repository cloning with default master branch."""
        source = ContentSource(
            name="test-repo",
            type=SourceType.GITHUB,
            url="https://github.com/test/repo.git",
            branch="master",  # Default branch should not add --branch flag
            enabled=True,
        )
        repo_path = self.manager.get_repo_path(source)

        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"success", b"")

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            await self.manager._clone_repository(source, repo_path)

            # Verify command does NOT include branch specification for master
            call_args = mock_exec.call_args[0]
            assert "--branch" not in call_args

    @pytest.mark.asyncio
    async def test_clone_repository_no_branch(self):
        """Test repository cloning with no branch specified."""
        source = ContentSource(
            name="test-repo",
            type=SourceType.GITHUB,
            url="https://github.com/test/repo.git",
            branch=None,
            enabled=True,
        )
        repo_path = self.manager.get_repo_path(source)

        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"success", b"")

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            await self.manager._clone_repository(source, repo_path)

            # Verify command does NOT include branch specification
            call_args = mock_exec.call_args[0]
            assert "--branch" not in call_args
