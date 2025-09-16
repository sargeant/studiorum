"""Tests for enhanced file format parsing in NameListFileSource."""

import tempfile
from pathlib import Path

import pytest

from studiorum.core.loaders.content_sources import NameListFileSource
from studiorum.core.models.content import ContentType
from tests.test_helpers import reset_test_environment


@pytest.mark.fast
class TestEnhancedFileFormatParsing:
    """Test enhanced file format parsing functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_file(self, content: str) -> Path:
        """Create a test file with the given content."""
        file_path = self.temp_dir / "test_file.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_simple_name_format(self) -> None:
        """Test parsing simple name format (backward compatibility)."""
        content = "Goblin\nOrc\nKobold"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", None),
            (1, "Orc", None),
            (1, "Kobold", None),
        ]
        assert structured_data == expected

    def test_count_format(self) -> None:
        """Test parsing count format."""
        content = "3 Goblin\n1 Orc\n5 Kobold"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (3, "Goblin", None),
            (1, "Orc", None),
            (5, "Kobold", None),
        ]
        assert structured_data == expected

    def test_source_format(self) -> None:
        """Test parsing source format."""
        content = "Goblin|MM\nOrc|VGM\nKobold|VGM"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", "MM"),
            (1, "Orc", "VGM"),
            (1, "Kobold", "VGM"),
        ]
        assert structured_data == expected

    def test_count_and_source_format(self) -> None:
        """Test parsing count and source format."""
        content = "3 Goblin|MM\n1 Orc|VGM\n10 Kobold|VGM"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (3, "Goblin", "MM"),
            (1, "Orc", "VGM"),
            (10, "Kobold", "VGM"),
        ]
        assert structured_data == expected

    def test_mixed_formats(self) -> None:
        """Test parsing mixed formats in same file."""
        content = """Goblin
3 Orc
Kobold|VGM
5 Troll|MM
Bugbear|VGM
2 Hobgoblin"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", None),
            (3, "Orc", None),
            (1, "Kobold", "VGM"),
            (5, "Troll", "MM"),
            (1, "Bugbear", "VGM"),
            (2, "Hobgoblin", None),
        ]
        assert structured_data == expected

    def test_comments_and_empty_lines(self) -> None:
        """Test parsing with comments and empty lines."""
        content = """# This is a comment
Goblin|MM

# Another comment
3 Orc|VGM

# Empty lines and comments should be ignored
Kobold"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", "MM"),
            (3, "Orc", "VGM"),
            (1, "Kobold", None),
        ]
        assert structured_data == expected

    def test_inline_comments(self) -> None:
        """Test parsing with inline comments."""
        content = """Goblin|MM  # This is a goblin
3 Orc|VGM  # Multiple orcs
Kobold  # Simple kobold"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", "MM"),
            (3, "Orc", "VGM"),
            (1, "Kobold", None),
        ]
        assert structured_data == expected

    def test_whitespace_handling(self) -> None:
        """Test proper whitespace handling."""
        content = """  Goblin  |  MM
 3   Orc   |   VGM
   Kobold   """
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", "MM"),
            (3, "Orc", "VGM"),
            (1, "Kobold", None),
        ]
        assert structured_data == expected

    def test_empty_source_handling(self) -> None:
        """Test handling of empty source specifications."""
        content = """Goblin|
3 Orc|
Kobold|MM"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Goblin", None),  # Empty source becomes None
            (3, "Orc", None),  # Whitespace-only source becomes None
            (1, "Kobold", "MM"),
        ]
        assert structured_data == expected

    def test_zero_count(self) -> None:
        """Test handling of zero counts."""
        content = """0 Goblin|MM
3 Orc|VGM
0 Kobold"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (0, "Goblin", "MM"),
            (3, "Orc", "VGM"),
            (0, "Kobold", None),
        ]
        assert structured_data == expected

    def test_large_count(self) -> None:
        """Test handling of large counts."""
        content = "100 Goblin|MM\n999 Orc|VGM"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (100, "Goblin", "MM"),
            (999, "Orc", "VGM"),
        ]
        assert structured_data == expected

    def test_complex_names_with_spaces(self) -> None:
        """Test handling of complex names with spaces."""
        content = """Ancient Red Dragon|MM
3 Goblin Boss|MM
1 Orc War Chief|VGM
Fire Giant|MM"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Ancient Red Dragon", "MM"),
            (3, "Goblin Boss", "MM"),
            (1, "Orc War Chief", "VGM"),
            (1, "Fire Giant", "MM"),
        ]
        assert structured_data == expected

    def test_names_with_special_characters(self) -> None:
        """Test handling of names with special characters."""
        content = """Baba Yaga's Hut|CoS
3 Will-o'-Wisp|MM
Castle Ravenloft (Location)|CoS"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        structured_data = source.load_structured()

        expected = [
            (1, "Baba Yaga's Hut", "CoS"),
            (3, "Will-o'-Wisp", "MM"),
            (1, "Castle Ravenloft (Location)", "CoS"),
        ]
        assert structured_data == expected

    def test_backward_compatibility_load(self) -> None:
        """Test backward compatibility with regular load() method."""
        content = """3 Goblin|MM
1 Orc|VGM
Kobold"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)

        # Regular load should return just names
        names = source.load()
        expected_names = ["Goblin", "Orc", "Kobold"]
        assert names == expected_names

        # Structured load should return full data
        structured_data = source.load_structured()
        expected_structured = [
            (3, "Goblin", "MM"),
            (1, "Orc", "VGM"),
            (1, "Kobold", None),
        ]
        assert structured_data == expected_structured

    def test_empty_file(self) -> None:
        """Test handling of empty file."""
        content = ""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)

        with pytest.raises(ValueError, match="No names found in file"):
            source.load_structured()

    def test_comments_only_file(self) -> None:
        """Test handling of file with only comments."""
        content = """# This is a comment
# Another comment

# More comments"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)

        with pytest.raises(ValueError, match="No names found in file"):
            source.load_structured()

    def test_file_not_found(self) -> None:
        """Test handling of missing file."""
        file_path = self.temp_dir / "nonexistent.txt"

        source = NameListFileSource(file_path, ContentType.CREATURE)

        with pytest.raises(FileNotFoundError):
            source.load_structured()

    def test_validation_success(self) -> None:
        """Test validation of valid file."""
        content = "3 Goblin|MM\nOrc|VGM"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        validation = source.validate()

        assert validation.is_valid
        assert len(validation.errors) == 0
        assert len(validation.warnings) == 0

    def test_validation_empty_file_warning(self) -> None:
        """Test validation warning for empty file."""
        content = "# Only comments\n\n# Nothing else"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        validation = source.validate()

        assert not validation.is_valid
        assert len(validation.errors) == 1
        assert "Failed to read file" in validation.errors[0]

    def test_validation_missing_file(self) -> None:
        """Test validation error for missing file."""
        file_path = self.temp_dir / "missing.txt"

        source = NameListFileSource(file_path, ContentType.CREATURE)
        validation = source.validate()

        assert not validation.is_valid
        assert len(validation.errors) == 1
        assert "File does not exist" in validation.errors[0]

    def test_metadata_with_structured_count(self) -> None:
        """Test metadata calculation includes counts from structured data."""
        content = """3 Goblin|MM
2 Orc|VGM
1 Kobold"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)
        metadata = source.get_metadata()

        # Content count should be sum of individual counts (3 + 2 + 1 = 6)
        assert metadata.content_count == 6
        assert metadata.source_type == "name_list"
        assert str(file_path) in metadata.location

    def test_caching_behavior(self) -> None:
        """Test that parsed data is properly cached."""
        content = "3 Goblin|MM\nOrc|VGM"
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.CREATURE)

        # First call should parse the file
        data1 = source.load_structured()

        # Second call should return cached data
        data2 = source.load_structured()

        assert data1 == data2
        assert data1 is data2  # Should be the same cached object

    def test_spell_content_type(self) -> None:
        """Test parsing works with different content types."""
        content = """Fireball|PHB
3 Magic Missile|PHB
Shield"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.SPELL)
        structured_data = source.load_structured()

        expected = [
            (1, "Fireball", "PHB"),
            (3, "Magic Missile", "PHB"),
            (1, "Shield", None),
        ]
        assert structured_data == expected

    def test_item_content_type(self) -> None:
        """Test parsing works with item content type."""
        content = """Longsword|PHB
2 Shortsword|PHB
Magic Sword"""
        file_path = self.create_test_file(content)

        source = NameListFileSource(file_path, ContentType.ITEM)
        structured_data = source.load_structured()

        expected = [
            (1, "Longsword", "PHB"),
            (2, "Shortsword", "PHB"),
            (1, "Magic Sword", None),
        ]
        assert structured_data == expected
