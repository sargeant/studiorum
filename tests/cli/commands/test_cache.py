"""Tests for cache CLI commands."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.commands.cache import app
from studiorum.core.cache import CacheManager


@pytest.fixture
def runner():
    """Test runner for CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_cache_stats():
    """Mock cache statistics."""
    return {
        "cache_dir": "/test/cache",
        "total_entries": 1247,
        "total_size_mb": 45.2,
        "max_size_mb": 100.0,
    }


class TestCacheShow:
    """Test cache show command."""

    @patch.object(CacheManager, "get_stats")
    def test_cache_show_displays_stats(self, mock_get_stats, runner, mock_cache_stats):
        """Test that cache show displays statistics correctly."""
        mock_get_stats.return_value = mock_cache_stats

        result = runner.invoke(app, ["show"])

        assert result.exit_code == 0
        assert "Disk Cache" in result.stdout
        assert "45.2 MB" in result.stdout
        assert "100 MB" in result.stdout
        assert "1,247" in result.stdout
        assert "/test/cache" in result.stdout

    @patch.object(CacheManager, "get_stats")
    def test_cache_show_high_usage_warning(self, mock_get_stats, runner):
        """Test warning when cache usage is high."""
        mock_get_stats.return_value = {
            "cache_dir": "/test/cache",
            "total_entries": 1000,
            "total_size_mb": 85.0,
            "max_size_mb": 100.0,
        }

        result = runner.invoke(app, ["show"])

        assert result.exit_code == 0
        assert "Recommendation" in result.stdout
        assert "cache clear" in result.stdout

    @patch.object(CacheManager, "get_stats")
    def test_cache_show_low_usage_status(self, mock_get_stats, runner):
        """Test status message when cache usage is low."""
        mock_get_stats.return_value = {
            "cache_dir": "/test/cache",
            "total_entries": 100,
            "total_size_mb": 5.0,
            "max_size_mb": 100.0,
        }

        result = runner.invoke(app, ["show"])

        assert result.exit_code == 0
        assert "plenty of space" in result.stdout


class TestCacheClear:
    """Test cache clear command."""

    @patch.object(CacheManager, "get_stats")
    @patch.object(CacheManager, "clear")
    def test_cache_clear_with_yes_flag(
        self, mock_clear, mock_get_stats, runner, mock_cache_stats
    ):
        """Test cache clear with --yes flag skips confirmation."""
        mock_get_stats.return_value = mock_cache_stats

        result = runner.invoke(app, ["clear", "--yes"])

        assert result.exit_code == 0
        mock_clear.assert_called_once()
        assert "Cache cleared successfully" in result.stdout
        assert "Freed 45.2 MB" in result.stdout

    @patch.object(CacheManager, "get_stats")
    def test_cache_clear_empty_cache(self, mock_get_stats, runner):
        """Test cache clear when cache is already empty."""
        mock_get_stats.return_value = {
            "cache_dir": "/test/cache",
            "total_entries": 0,
            "total_size_mb": 0.0,
            "max_size_mb": 100.0,
        }

        result = runner.invoke(app, ["clear"])

        assert result.exit_code == 0
        assert "already empty" in result.stdout

    @patch.object(CacheManager, "get_stats")
    @patch.object(CacheManager, "clear")
    def test_cache_clear_with_confirmation(
        self, mock_clear, mock_get_stats, runner, mock_cache_stats
    ):
        """Test cache clear with user confirmation."""
        mock_get_stats.return_value = mock_cache_stats

        result = runner.invoke(app, ["clear"], input="y\n")

        assert result.exit_code == 0
        mock_clear.assert_called_once()
        assert "Cache cleared successfully" in result.stdout

    @patch.object(CacheManager, "get_stats")
    @patch.object(CacheManager, "clear")
    def test_cache_clear_cancelled(
        self, mock_clear, mock_get_stats, runner, mock_cache_stats
    ):
        """Test cache clear cancelled by user."""
        mock_get_stats.return_value = mock_cache_stats

        result = runner.invoke(app, ["clear"], input="n\n")

        assert result.exit_code == 0
        mock_clear.assert_not_called()
        assert "cancelled" in result.stdout
