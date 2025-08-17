"""Tests for Content Source Abstraction."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from dnd5e.core.errors.architecture_errors import (
    ContentLoadingError,
    ContentSourceError,
    ContentValidationError,
)
from dnd5e.core.loaders.content_sources import (
    ContentLoader,
    ContentSource,
    ContentSourceMetadata,
    FileContentSource,
    InlineContentSource,
    OmnidexerContentSource,
    StdinContentSource,
    ValidationResult,
    create_file_source,
    create_inline_source,
    create_omnidexer_source,
    create_stdin_source,
)
from dnd5e.core.models.content import ContentType
from tests.test_helpers import reset_test_environment


class TestValidationResult:
    """Test ValidationResult model."""

    def test_init_valid(self):
        """Test initialization of valid result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """Test adding error makes result invalid."""
        result = ValidationResult(is_valid=True)
        result.add_error("Something went wrong")

        assert result.is_valid is False
        assert "Something went wrong" in result.errors

    def test_add_warning(self):
        """Test adding warning keeps result valid."""
        result = ValidationResult(is_valid=True)
        result.add_warning("This is a warning")

        assert result.is_valid is True
        assert "This is a warning" in result.warnings


class TestContentSourceMetadata:
    """Test ContentSourceMetadata model."""

    def test_creation(self):
        """Test metadata creation."""
        metadata = ContentSourceMetadata(
            source_type="file",
            location="/path/to/file.json",
            description="Test file",
            content_count=5,
            estimated_size="1 KB",
        )

        assert metadata.source_type == "file"
        assert metadata.location == "/path/to/file.json"
        assert metadata.description == "Test file"
        assert metadata.content_count == 5
        assert metadata.estimated_size == "1 KB"


class TestFileContentSource:
    """Test FileContentSource implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init(self):
        """Test FileContentSource initialization."""
        file_path = Path("/test/file.json")
        source = FileContentSource(file_path, ContentType.SPELL)

        assert source.file_path == file_path
        assert source.content_type == ContentType.SPELL
        assert source.location == str(file_path)
        assert "JSON file: file.json" in source.description

    def test_get_metadata_nonexistent_file(self):
        """Test metadata for non-existent file."""
        file_path = Path("/nonexistent/file.json")
        source = FileContentSource(file_path)

        metadata = source.get_metadata()
        assert metadata.source_type == "file"
        assert metadata.location == str(file_path)
        assert metadata.content_count == 0
        assert metadata.estimated_size == "unknown"

    def test_get_metadata_existing_file(self):
        """Test metadata for existing file."""
        test_data = {
            "spell": [
                {"name": "Fireball", "level": 3},
                {"name": "Magic Missile", "level": 1},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path)
            metadata = source.get_metadata()

            assert metadata.source_type == "file"
            assert metadata.content_count == 2
            assert "bytes" in metadata.estimated_size or "KB" in metadata.estimated_size
        finally:
            file_path.unlink()

    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file."""
        file_path = Path("/nonexistent/file.json")
        source = FileContentSource(file_path)

        result = source.validate()
        assert result.is_valid is False
        assert any("does not exist" in error for error in result.errors)

    def test_validate_valid_file(self):
        """Test validation of valid JSON file."""
        test_data = {"spell": [{"name": "Test", "level": 1}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path)
            result = source.validate()

            assert result.is_valid is True
            assert result.errors == []
        finally:
            file_path.unlink()

    def test_validate_invalid_json(self):
        """Test validation of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path)
            result = source.validate()

            assert result.is_valid is False
            assert any("Invalid JSON format" in error for error in result.errors)
        finally:
            file_path.unlink()

    def test_load_with_specific_content_type(self):
        """Test loading with specific content type."""
        test_data = {
            "spell": [
                {"name": "Fireball", "level": 3, "source": {"abbreviation": "PHB"}},
                {
                    "name": "Magic Missile",
                    "level": 1,
                    "source": {"abbreviation": "PHB"},
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path, ContentType.SPELL)

            # Mock the ContentFactory to return mock objects
            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory

                mock_spell1 = Mock()
                mock_spell1.name = "Fireball"
                mock_spell2 = Mock()
                mock_spell2.name = "Magic Missile"
                mock_factory.create_content.side_effect = [mock_spell1, mock_spell2]

                content = source.load()

                assert len(content) == 2
                assert content[0].name == "Fireball"
                assert content[1].name == "Magic Missile"
                assert mock_factory.create_content.call_count == 2
        finally:
            file_path.unlink()

    def test_load_auto_detect_content_type(self):
        """Test loading with auto-detection of content types."""
        test_data = {
            "spell": [
                {"name": "Fireball", "level": 3, "source": {"abbreviation": "PHB"}}
            ],
            "monster": [
                {"name": "Dragon", "cr": "10", "source": {"abbreviation": "MM"}}
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path)  # No content type specified

            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory

                mock_spell = Mock()
                mock_spell.name = "Fireball"
                mock_creature = Mock()
                mock_creature.name = "Dragon"
                mock_factory.create_content.side_effect = [mock_spell, mock_creature]

                content = source.load()

                assert len(content) == 2
                assert mock_factory.create_content.call_count == 2
        finally:
            file_path.unlink()

    def test_caching_behavior(self):
        """Test that content is cached properly."""
        test_data = {
            "spell": [{"name": "Test", "level": 1, "source": {"abbreviation": "PHB"}}]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            source = FileContentSource(file_path)

            # First load should populate cache
            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory

                mock_spell = Mock()
                mock_spell.name = "Test"
                mock_factory.create_content.return_value = mock_spell
                content1 = source.load()
                first_call_count = mock_factory.create_content.call_count

            # Second load should use cache (no additional create_content calls)
            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory
                mock_factory.create_content.return_value = Mock()
                content2 = source.load()
                second_call_count = mock_factory.create_content.call_count

            assert len(content1) == len(content2)
            assert first_call_count > 0
            assert second_call_count == 0  # Should use cache
        finally:
            file_path.unlink()


class TestOmnidexerContentSource:
    """Test OmnidexerContentSource implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init(self):
        """Test OmnidexerContentSource initialization."""
        mock_omnidexer = Mock()
        source = OmnidexerContentSource(mock_omnidexer, ContentType.CREATURE)

        assert source.omnidexer == mock_omnidexer
        assert source.content_type == ContentType.CREATURE
        assert "omnidexer:creature" in source.location
        assert "Omnidexer content: creature" in source.description

    def test_get_metadata(self):
        """Test metadata retrieval."""
        mock_omnidexer = Mock()
        mock_content = [Mock(), Mock(), Mock()]
        mock_omnidexer.find_all.return_value = mock_content

        source = OmnidexerContentSource(mock_omnidexer, ContentType.SPELL)
        metadata = source.get_metadata()

        assert metadata.source_type == "omnidexer"
        assert metadata.content_count == 3
        assert "3 items" in metadata.estimated_size

    def test_validate_valid_omnidexer(self):
        """Test validation with valid omnidexer."""
        mock_omnidexer = Mock()
        mock_omnidexer.find_all.return_value = []

        source = OmnidexerContentSource(mock_omnidexer, ContentType.SPELL)
        result = source.validate()

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_none_omnidexer(self):
        """Test validation with None omnidexer."""
        source = OmnidexerContentSource(None, ContentType.SPELL)
        result = source.validate()

        assert result.is_valid is False
        assert any("not available" in error for error in result.errors)

    def test_load(self):
        """Test content loading."""
        mock_omnidexer = Mock()
        mock_content = [Mock(), Mock()]
        mock_omnidexer.find_all.return_value = mock_content

        source = OmnidexerContentSource(mock_omnidexer, ContentType.ITEM)
        content = source.load()

        assert content == mock_content
        mock_omnidexer.find_all.assert_called_once_with(ContentType.ITEM)

    def test_supports_streaming(self):
        """Test streaming support."""
        mock_omnidexer = Mock()
        source = OmnidexerContentSource(mock_omnidexer, ContentType.SPELL)

        assert source.supports_streaming() is True


class TestContentLoader:
    """Test ContentLoader unified loader."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init(self):
        """Test ContentLoader initialization."""
        loader = ContentLoader()
        assert loader._sources == []

    def test_add_source(self):
        """Test adding content sources."""
        loader = ContentLoader()
        mock_source = Mock()

        loader.add_source(mock_source)
        assert len(loader._sources) == 1
        assert loader._sources[0] == mock_source

    def test_validate_all(self):
        """Test validation of all sources."""
        loader = ContentLoader()

        mock_source1 = Mock()
        mock_source1.validate.return_value = ValidationResult(is_valid=True)

        mock_source2 = Mock()
        invalid_result = ValidationResult(is_valid=False)
        invalid_result.add_error("Test error")
        mock_source2.validate.return_value = invalid_result

        loader.add_source(mock_source1)
        loader.add_source(mock_source2)

        results = loader.validate_all()

        assert len(results) == 2
        assert results["source_0"].is_valid is True
        assert results["source_1"].is_valid is False

    def test_load_all(self):
        """Test loading content from all sources."""
        loader = ContentLoader()

        mock_content1 = [Mock(), Mock()]
        mock_source1 = Mock()
        mock_source1.load.return_value = mock_content1

        mock_content2 = [Mock()]
        mock_source2 = Mock()
        mock_source2.load.return_value = mock_content2

        loader.add_source(mock_source1)
        loader.add_source(mock_source2)

        all_content = loader.load_all()

        assert len(all_content) == 3
        assert all_content[:2] == mock_content1
        assert all_content[2:] == mock_content2

    def test_load_all_with_error(self):
        """Test loading with one source failing."""
        loader = ContentLoader()

        mock_content = [Mock()]
        mock_source1 = Mock()
        mock_source1.load.return_value = mock_content

        mock_source2 = Mock()
        mock_source2.load.side_effect = Exception("Load failed")
        mock_source2.get_metadata.return_value = Mock(location="test_source")

        loader.add_source(mock_source1)
        loader.add_source(mock_source2)

        # Should not raise exception, but log error
        all_content = loader.load_all()

        assert len(all_content) == 1
        assert all_content == mock_content

    def test_get_source_metadata(self):
        """Test getting metadata for all sources."""
        loader = ContentLoader()

        mock_metadata1 = Mock()
        mock_source1 = Mock()
        mock_source1.get_metadata.return_value = mock_metadata1

        mock_metadata2 = Mock()
        mock_source2 = Mock()
        mock_source2.get_metadata.return_value = mock_metadata2

        loader.add_source(mock_source1)
        loader.add_source(mock_source2)

        metadata = loader.get_source_metadata()

        assert len(metadata) == 2
        assert metadata[0] == mock_metadata1
        assert metadata[1] == mock_metadata2

    def test_clear(self):
        """Test clearing all sources."""
        loader = ContentLoader()
        loader.add_source(Mock())
        loader.add_source(Mock())

        assert len(loader._sources) == 2

        loader.clear()
        assert len(loader._sources) == 0


class TestFactoryFunctions:
    """Test factory functions for content sources."""

    def test_create_file_source(self):
        """Test file source factory."""
        file_path = Path("/test/file.json")
        source = create_file_source(file_path, ContentType.SPELL)

        assert isinstance(source, FileContentSource)
        assert source.file_path == file_path
        assert source.content_type == ContentType.SPELL

    def test_create_omnidexer_source(self):
        """Test omnidexer source factory."""
        mock_omnidexer = Mock()
        source = create_omnidexer_source(mock_omnidexer, ContentType.CREATURE)

        assert isinstance(source, OmnidexerContentSource)
        assert source.omnidexer == mock_omnidexer
        assert source.content_type == ContentType.CREATURE

    def test_create_stdin_source(self):
        """Test stdin source factory."""
        source = create_stdin_source(ContentType.ITEM)

        assert isinstance(source, StdinContentSource)
        assert source.content_type == ContentType.ITEM

    def test_create_inline_source(self):
        """Test inline source factory."""
        adventure_data = {"data": []}
        source = create_inline_source(adventure_data, ContentType.CREATURE)

        assert isinstance(source, InlineContentSource)
        assert source.adventure_data == adventure_data
        assert source.content_type == ContentType.CREATURE


@pytest.mark.integration
class TestContentSourceIntegration:
    """Integration tests for content sources."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_file_to_loader_integration(self):
        """Test full integration from file source to loader."""
        test_data = {
            "spell": [
                {"name": "Fireball", "level": 3, "source": {"abbreviation": "PHB"}},
                {
                    "name": "Magic Missile",
                    "level": 1,
                    "source": {"abbreviation": "PHB"},
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            # Create loader with file source
            loader = ContentLoader()
            file_source = create_file_source(file_path, ContentType.SPELL)
            loader.add_source(file_source)

            # Validate all sources
            validation_results = loader.validate_all()
            assert all(result.is_valid for result in validation_results.values())

            # Get metadata
            metadata_list = loader.get_source_metadata()
            assert len(metadata_list) == 1
            assert metadata_list[0].content_count == 2

            # Load content
            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory

                mock_spell = Mock()
                mock_spell.name = "Test Spell"
                mock_factory.create_content.return_value = mock_spell

                content = loader.load_all()
                assert len(content) == 2
                assert all(item.name == "Test Spell" for item in content)
        finally:
            file_path.unlink()

    def test_multiple_sources_integration(self):
        """Test integration with multiple content sources."""
        # Create file source
        test_data = {"spell": [{"name": "Test Spell", "level": 1}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            # Create omnidexer source
            mock_omnidexer = Mock()
            mock_omnidexer.find_all.return_value = [Mock(), Mock()]

            # Set up loader with multiple sources
            loader = ContentLoader()
            loader.add_source(create_file_source(file_path, ContentType.SPELL))
            loader.add_source(
                create_omnidexer_source(mock_omnidexer, ContentType.CREATURE)
            )

            # Validate all
            validation_results = loader.validate_all()
            assert len(validation_results) == 2

            # Load all content
            with patch(
                "dnd5e.core.loaders.content_factory.ContentFactory"
            ) as mock_factory_class:
                mock_factory = Mock()
                mock_factory_class.return_value = mock_factory

                mock_item = Mock()
                mock_item.name = "Test Item"
                mock_factory.create_content.return_value = mock_item

                content = loader.load_all()
                # 1 from file + 2 from omnidexer
                assert len(content) == 3
        finally:
            file_path.unlink()
