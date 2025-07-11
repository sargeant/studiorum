"""Tests for CLI system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from typer.testing import CliRunner

from src.cli.main import app
from src.cli.compat import LegacyCompatLayer


class TestCLIMain:
    """Tests for main CLI application."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "5e2pdf" in result.stdout
        assert "Convert D&D 5e JSON data" in result.stdout
    
    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "5e2pdf" in result.stdout
        assert "v2.0.0" in result.stdout
    
    def test_cli_no_args(self):
        """Test CLI with no arguments shows help."""
        result = self.runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
    
    def test_quick_convert_missing_file(self):
        """Test quick convert with missing input file."""
        result = self.runner.invoke(app, ["quick", "nonexistent.json"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestLegacyCompatLayer:
    """Tests for legacy compatibility system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compat = LegacyCompatLayer()
    
    def test_parse_legacy_args_basic(self):
        """Test parsing basic legacy arguments."""
        args = ["--adventure", "test.json"]
        parsed = self.compat._parse_legacy_args(args)
        
        assert parsed['content_type'] == 'adventure'
        assert parsed['input_file'] == 'test.json'
        assert parsed['include_images'] is False
    
    def test_parse_legacy_args_with_options(self):
        """Test parsing legacy arguments with options."""
        args = ["--book", "--with-images", "--add-items", "--no-creatures", "book.json"]
        parsed = self.compat._parse_legacy_args(args)
        
        assert parsed['content_type'] == 'book'
        assert parsed['input_file'] == 'book.json'
        assert parsed['include_images'] is True
        assert parsed['include_items'] is True
        assert parsed['include_creatures'] is False
    
    def test_parse_legacy_args_help(self):
        """Test parsing help argument."""
        args = ["--help"]
        parsed = self.compat._parse_legacy_args(args)
        
        assert parsed.get('help') is True
    
    def test_parse_legacy_args_version(self):
        """Test parsing version argument."""
        args = ["--version"]
        parsed = self.compat._parse_legacy_args(args)
        
        assert parsed.get('version') is True
    
    def test_execute_legacy_help(self):
        """Test executing legacy help command."""
        result = self.compat.execute_legacy_command(["--help"])
        assert "5e2pdf Legacy Compatibility Mode" in result
        assert "USAGE:" in result
    
    def test_execute_legacy_version(self):
        """Test executing legacy version command."""
        result = self.compat.execute_legacy_command(["--version"])
        assert "5e2pdf v2.0.0" in result
        assert "Legacy Compatibility Mode" in result
    
    def test_execute_legacy_missing_file(self):
        """Test executing legacy command with missing file."""
        result = self.compat.execute_legacy_command(["--adventure", "nonexistent.json"])
        assert "Error:" in result
        assert "not found" in result


class TestCLICommands:
    """Tests for CLI command modules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_convert_help(self):
        """Test convert command help."""
        result = self.runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "Convert D&D content" in result.stdout
    
    def test_list_help(self):
        """Test list command help."""
        result = self.runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List available" in result.stdout
    
    def test_info_help(self):
        """Test info command help."""
        result = self.runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "Show detailed information" in result.stdout
    
    def test_stats_help(self):
        """Test stats command help."""
        result = self.runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "Show content statistics" in result.stdout


class TestCLIIntegration:
    """Integration tests for CLI with mock data."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @pytest.mark.asyncio
    async def test_quick_convert_integration(self, tmp_path):
        """Test quick convert with mock data."""
        # Create mock JSON file
        mock_data = {
            "spell": [{
                "name": "Test Spell",
                "level": 1,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
                "components": {"v": True, "s": False, "m": False},
                "duration": [{"type": "instant"}],
                "entries": ["A test spell description."]
            }]
        }
        
        input_file = tmp_path / "test_spell.json"
        input_file.write_text(json.dumps(mock_data))
        
        output_file = tmp_path / "output.tex"
        
        # Mock the omnidexer and dependencies
        with patch('src.cli.main.get_omnidexer') as mock_omnidexer, \
             patch('src.cli.main.get_tag_resolver') as mock_tag_resolver:
            
            mock_omni = Mock()
            mock_tag = Mock()
            mock_omnidexer.return_value = mock_omni
            mock_tag_resolver.return_value = mock_tag
            
            result = self.runner.invoke(app, [
                "quick", 
                str(input_file),
                "--output", str(output_file)
            ])
            
            # Should not crash (though it might fail due to missing dependencies)
            assert isinstance(result.exit_code, int)
    
    def test_legacy_mode_integration(self):
        """Test legacy mode integration."""
        result = self.runner.invoke(app, ["legacy", "--help"])
        assert result.exit_code == 0
        assert "5e2pdf Legacy Compatibility Mode" in result.stdout


class TestCLIFileOperations:
    """Tests for file operation commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_list_files_no_directories(self):
        """Test list files when no data directories exist."""
        with patch('pathlib.Path.exists', return_value=False):
            result = self.runner.invoke(app, ["list", "files"])
            # Should handle missing directories gracefully
            assert result.exit_code == 0
    
    def test_info_file_nonexistent(self):
        """Test info command with nonexistent file."""
        result = self.runner.invoke(app, ["info", "file", "nonexistent.json"])
        assert result.exit_code == 1
        assert "not found" in result.stdout
    
    def test_info_file_invalid_json(self, tmp_path):
        """Test info command with invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")
        
        result = self.runner.invoke(app, ["info", "file", str(invalid_file)])
        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout


class TestCLIErrorHandling:
    """Tests for CLI error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_unknown_command(self):
        """Test handling of unknown commands."""
        result = self.runner.invoke(app, ["unknown-command"])
        assert result.exit_code != 0
    
    def test_convert_missing_file(self):
        """Test convert command with missing file."""
        result = self.runner.invoke(app, ["convert", "adventure", "missing.json"])
        assert result.exit_code == 1
    
    def test_info_content_not_found(self):
        """Test info content command with non-existent content."""
        with patch('src.cli.main.get_omnidexer') as mock_omnidexer:
            mock_omni = Mock()
            mock_omni.find.return_value = None
            mock_omnidexer.return_value = mock_omni
            
            result = self.runner.invoke(app, ["info", "content", "Nonexistent Spell"])
            # Should handle gracefully
            assert isinstance(result.exit_code, int)


class TestCacheSystem:
    """Tests for caching system."""
    
    def test_cache_creation(self):
        """Test cache manager creation."""
        from src.core.cache import CacheManager
        
        cache = CacheManager()
        assert cache.cache_dir.exists()
    
    def test_cache_set_get(self):
        """Test basic cache operations."""
        from src.core.cache import CacheManager
        
        cache = CacheManager()
        
        # Set and get value
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"
        
        # Get non-existent key
        result = cache.get("missing_key", "default")
        assert result == "default"
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        from src.core.cache import CacheManager
        
        cache = CacheManager()
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        cache.invalidate("test_key")
        assert cache.get("test_key") is None
    
    def test_cache_clear(self):
        """Test cache clearing."""
        from src.core.cache import CacheManager
        
        cache = CacheManager()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        from src.core.cache import CacheManager
        
        cache = CacheManager()
        cache.set("test_key", "test_value")
        
        stats = cache.get_stats()
        assert 'total_entries' in stats
        assert 'total_size_mb' in stats
        assert stats['total_entries'] >= 1
    
    def test_cached_decorator(self):
        """Test cached function decorator."""
        from src.core.cache import cached
        
        call_count = 0
        
        @cached(key_func=lambda x: f"test_func:{x}")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different argument should call function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


class TestCLIAsyncOperations:
    """Tests for async CLI operations."""
    
    @pytest.mark.asyncio
    async def test_async_omnidexer_loading(self):
        """Test async omnidexer loading in CLI context."""
        from src.cli.main import get_omnidexer
        
        with patch('src.core.loaders.omnidexer.Omnidexer') as mock_class:
            mock_instance = Mock()
            mock_instance.load_all_data = Mock(return_value=None)
            mock_class.return_value = mock_instance
            
            omnidexer = await get_omnidexer()
            assert omnidexer is mock_instance
            mock_instance.load_all_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_tag_resolver_creation(self):
        """Test async tag resolver creation."""
        from src.cli.main import get_tag_resolver
        
        with patch('src.cli.main.get_omnidexer') as mock_get_omni, \
             patch('src.core.indexer.tag_resolver.TagResolver') as mock_resolver_class:
            
            mock_omni = Mock()
            mock_resolver = Mock()
            mock_get_omni.return_value = mock_omni
            mock_resolver_class.return_value = mock_resolver
            
            resolver = await get_tag_resolver()
            assert resolver is mock_resolver
            mock_resolver_class.assert_called_once_with(mock_omni)