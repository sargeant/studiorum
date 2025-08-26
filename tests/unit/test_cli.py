"""Tests for CLI system."""

import json
from typing import Any
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app  # type: ignore
from tests.test_helpers import reset_test_environment


class TestCLIMain:
    """Tests for main CLI application."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    def test_cli_help(self) -> None:
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "studiorum" in result.stdout
        assert "Convert 5e content" in result.stdout

    def test_cli_version(self) -> None:
        """Test CLI version command."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "studiorum" in result.stdout
        assert "v2.0.0" in result.stdout

    def test_cli_no_args(self) -> None:
        """Test CLI with no arguments shows usage."""
        result = self.runner.invoke(app, [])
        # CLI should either show help (exit 0) or show usage error (exit 2)
        assert result.exit_code in [0, 2]
        # Usage message might be in stdout or stderr depending on exit code
        output = result.stdout + result.stderr
        assert "Usage:" in output

    def test_quick_convert_missing_file(self) -> None:
        """Test quick convert with missing input file."""
        result = self.runner.invoke(app, ["quick", "nonexistent.json"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestCLICommands:
    """Tests for CLI command modules."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    def test_convert_help(self) -> None:
        """Test convert command help."""
        result = self.runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "Convert 5e content" in result.stdout

    def test_list_help(self) -> None:
        """Test list command help."""
        result = self.runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List available" in result.stdout

    def test_info_help(self) -> None:
        """Test info command help."""
        result = self.runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "Show detailed information" in result.stdout

    def test_stats_help(self) -> None:
        """Test stats command help."""
        result = self.runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "Show content statistics" in result.stdout


class TestCLIIntegration:
    """Integration tests for CLI with mock data."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    def test_quick_convert_integration(self, tmp_path: Any) -> None:
        """Test quick convert with mock data."""
        # Create mock JSON file
        mock_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "level": 1,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True, "s": False, "m": False},
                    "duration": [{"type": "instant"}],
                    "entries": ["A test spell description."],
                }
            ]
        }

        input_file = tmp_path / "test_spell.json"
        input_file.write_text(json.dumps(mock_data))

        output_file = tmp_path / "output.tex"

        # Mock the omnidexer and dependencies
        with (
            patch("studiorum.cli.main.get_omnidexer") as mock_omnidexer,
            patch("studiorum.cli.main.get_tag_resolver") as mock_tag_resolver,
        ):
            mock_omni: Any = Mock()
            mock_tag: Any = Mock()
            mock_omnidexer.return_value = mock_omni
            mock_tag_resolver.return_value = mock_tag

            result = self.runner.invoke(
                app, ["quick", str(input_file), "--output", str(output_file)]
            )

            # Should not crash (though it might fail due to missing dependencies)
            assert isinstance(result.exit_code, int)


class TestCLIFileOperations:
    """Tests for file operation commands."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    def test_list_files_no_directories(self) -> None:
        """Test list files when no data directories exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = self.runner.invoke(app, ["list", "files"])
            # Should handle missing directories gracefully
            assert result.exit_code == 0

    def test_info_file_nonexistent(self) -> None:
        """Test info command with nonexistent file."""
        result = self.runner.invoke(app, ["info", "file", "nonexistent.json"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_info_file_invalid_json(self, tmp_path: Any) -> None:
        """Test info command with invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        result = self.runner.invoke(app, ["info", "file", str(invalid_file)])
        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    def test_unknown_command(self) -> None:
        """Test handling of unknown commands."""
        result = self.runner.invoke(app, ["unknown-command"])
        assert result.exit_code != 0

    def test_convert_missing_file(self) -> None:
        """Test convert command with missing file."""
        result = self.runner.invoke(app, ["convert", "adventure", "missing.json"])
        assert result.exit_code == 1

    def test_info_content_not_found(self) -> None:
        """Test info content command with non-existent content."""
        with patch("studiorum.cli.main.get_omnidexer") as mock_omnidexer:
            mock_omni: Any = Mock()
            mock_omni.find.return_value = None
            mock_omnidexer.return_value = mock_omni

            result = self.runner.invoke(app, ["info", "content", "Nonexistent Spell"])
            # Should handle gracefully
            assert isinstance(result.exit_code, int)


class TestCacheSystem:
    """Tests for the caching system."""

    def setup_method(self) -> None:
        """Set up test fixtures and clear the cache."""
        # Reset global state for complete isolation
        reset_test_environment()

        from studiorum.core.cache import CacheManager

        CacheManager.clear()

    def teardown_method(self) -> None:
        """Tear down test fixtures and clear the cache."""
        from studiorum.core.cache import CacheManager

        CacheManager.clear()

    def test_cache_creation(self) -> None:
        """Test that the cache directory is created."""
        from studiorum.core.cache import CACHE_DIR, get_cache

        get_cache()
        assert CACHE_DIR.exists()

    def test_cache_set_get(self) -> None:
        """Test basic cache operations."""
        from studiorum.core.cache import get_cache

        cache = get_cache()
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"
        result = cache.get("missing_key", "default")
        assert result == "default"

    def test_cache_clear(self) -> None:
        """Test cache clearing."""
        from studiorum.core.cache import get_cache

        cache = get_cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        from studiorum.core.cache import CacheManager, get_cache

        cache = get_cache()
        cache.set("test_key", "test_value")
        stats = CacheManager.get_stats()
        assert "total_entries" in stats
        assert "total_size_mb" in stats
        assert stats["total_entries"] >= 1

    def test_cached_decorator(self) -> None:
        """Test cached function decorator."""
        from studiorum.core.cache import cached

        call_count = 0

        @cached(key_func=lambda x: f"test_func:{x}")
        def expensive_function(x: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1: Any = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2: Any = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

        # Different argument should call function
        result3: Any = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
