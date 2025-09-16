"""Tests for base command enhanced file support functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import click
import pytest

from studiorum.cli.commands.convert.base import BaseConvertCommand
from studiorum.core.models.content import ContentType
from tests.test_helpers import reset_test_environment


@pytest.mark.fast
class TestBaseEnhancedFileSupport:
    """Test base command enhanced file support methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.base_command = BaseConvertCommand()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_file(self, content: str, filename: str = "test.txt") -> Path:
        """Create a test file with the given content."""
        file_path = self.temp_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_get_name_list_from_file_simple_format(self) -> None:
        """Test loading simple name list (backward compatibility)."""
        content = "Fireball\nMagic Missile\nShield"
        file_path = self.create_test_file(content)

        names = self.base_command.get_name_list_from_file(file_path, "spell")

        expected = ["Fireball", "Magic Missile", "Shield"]
        assert names == expected

    def test_get_enhanced_name_list_from_file_simple_format(self) -> None:
        """Test loading enhanced format with simple names."""
        content = "Fireball\nMagic Missile\nShield"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", None),
            (1, "Magic Missile", None),
            (1, "Shield", None),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_count_format(self) -> None:
        """Test loading enhanced format with counts."""
        content = "3 Fireball\n1 Magic Missile\n2 Shield"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (3, "Fireball", None),
            (1, "Magic Missile", None),
            (2, "Shield", None),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_source_format(self) -> None:
        """Test loading enhanced format with sources."""
        content = "Fireball|PHB\nMagic Missile|PHB\nShield|PHB"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", "PHB"),
            (1, "Magic Missile", "PHB"),
            (1, "Shield", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_full_format(self) -> None:
        """Test loading enhanced format with counts and sources."""
        content = "3 Fireball|PHB\n1 Magic Missile|PHB\n2 Shield|PHB"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (3, "Fireball", "PHB"),
            (1, "Magic Missile", "PHB"),
            (2, "Shield", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_mixed_format(self) -> None:
        """Test loading enhanced format with mixed line formats."""
        content = """Fireball
3 Magic Missile|PHB
Shield|PHB
2 Counterspell
Haste|PHB"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", None),
            (3, "Magic Missile", "PHB"),
            (1, "Shield", "PHB"),
            (2, "Counterspell", None),
            (1, "Haste", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_with_comments(self) -> None:
        """Test loading enhanced format with comments and empty lines."""
        content = """# This is a spell list
Fireball|PHB

# More spells
3 Magic Missile|PHB

# End of list"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", "PHB"),
            (3, "Magic Missile", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_with_inline_comments(self) -> None:
        """Test loading enhanced format with inline comments."""
        content = """Fireball|PHB  # A fireball spell
3 Magic Missile|PHB  # Multiple missiles
Shield  # Protection spell"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", "PHB"),
            (3, "Magic Missile", "PHB"),
            (1, "Shield", None),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_whitespace_handling(self) -> None:
        """Test enhanced format handles whitespace correctly."""
        content = """  Fireball  |  PHB
 3   Magic Missile   |   PHB
   Shield   """
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", "PHB"),
            (3, "Magic Missile", "PHB"),
            (1, "Shield", None),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_zero_count(self) -> None:
        """Test enhanced format with zero counts."""
        content = "0 Fireball|PHB\n3 Magic Missile|PHB\n0 Shield"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (0, "Fireball", "PHB"),
            (3, "Magic Missile", "PHB"),
            (0, "Shield", None),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_large_counts(self) -> None:
        """Test enhanced format with large counts."""
        content = "100 Fireball|PHB\n999 Magic Missile|PHB"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (100, "Fireball", "PHB"),
            (999, "Magic Missile", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_empty_source(self) -> None:
        """Test enhanced format with empty source specifications."""
        content = "Fireball|\n3 Magic Missile|  \nShield|PHB"
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (1, "Fireball", None),  # Empty source becomes None
            (3, "Magic Missile", None),  # Whitespace-only source becomes None
            (1, "Shield", "PHB"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_complex_names(self) -> None:
        """Test enhanced format with complex names containing spaces and special characters."""
        content = """Ancient Red Dragon|MM
3 Goblin Boss|MM
Baba Yaga's Hut|CoS
2 Will-o'-Wisp|MM"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "creature"
        )

        expected = [
            (1, "Ancient Red Dragon", "MM"),
            (3, "Goblin Boss", "MM"),
            (1, "Baba Yaga's Hut", "CoS"),
            (2, "Will-o'-Wisp", "MM"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_different_content_types(self) -> None:
        """Test enhanced format works with different content types."""
        content = "3 Test Item|PHB\n1 Another Item|DMG"
        file_path = self.create_test_file(content)

        # Test with item content type
        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "item"
        )

        expected = [
            (3, "Test Item", "PHB"),
            (1, "Another Item", "DMG"),
        ]
        assert structured_data == expected

    def test_get_enhanced_name_list_from_file_invalid_content_type(self) -> None:
        """Test error handling for invalid content type."""
        content = "Fireball|PHB"
        file_path = self.create_test_file(content)

        with pytest.raises(click.exceptions.Exit):  # typer.Exit(1)
            self.base_command.get_enhanced_name_list_from_file(
                file_path, "invalid_type"
            )

    def test_get_enhanced_name_list_from_file_missing_file(self) -> None:
        """Test error handling for missing file."""
        missing_file = self.temp_dir / "nonexistent.txt"

        with pytest.raises(click.exceptions.Exit):  # typer.Exit(1)
            self.base_command.get_enhanced_name_list_from_file(missing_file, "spell")

    def test_get_enhanced_name_list_from_file_empty_file(self) -> None:
        """Test error handling for empty file."""
        empty_file = self.create_test_file("")

        with pytest.raises(click.exceptions.Exit):  # typer.Exit(1)
            self.base_command.get_enhanced_name_list_from_file(empty_file, "spell")

    def test_get_enhanced_name_list_from_file_comments_only(self) -> None:
        """Test error handling for file with only comments."""
        content = "# Only comments\n# No actual content\n\n# More comments"
        file_path = self.create_test_file(content)

        with pytest.raises(click.exceptions.Exit):  # typer.Exit(1)
            self.base_command.get_enhanced_name_list_from_file(file_path, "spell")

    def test_backward_compatibility_with_existing_method(self) -> None:
        """Test that enhanced method is compatible with existing get_name_list_from_file."""
        content = """3 Fireball|PHB
1 Magic Missile|PHB
Shield"""
        file_path = self.create_test_file(content)

        # Old method should return just names
        names = self.base_command.get_name_list_from_file(file_path, "spell")
        expected_names = ["Fireball", "Magic Missile", "Shield"]
        assert names == expected_names

        # Enhanced method should return structured data
        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )
        expected_structured = [
            (3, "Fireball", "PHB"),
            (1, "Magic Missile", "PHB"),
            (1, "Shield", None),
        ]
        assert structured_data == expected_structured

    def test_content_type_validation(self) -> None:
        """Test content type validation in enhanced method."""
        content = "Test Content|PHB"
        file_path = self.create_test_file(content)

        # Valid content types should work
        valid_types = ["spell", "creature", "item"]
        for content_type in valid_types:
            structured_data = self.base_command.get_enhanced_name_list_from_file(
                file_path, content_type
            )
            assert len(structured_data) == 1
            assert structured_data[0] == (1, "Test Content", "PHB")

    def test_file_validation_in_enhanced_method(self) -> None:
        """Test file validation behavior in enhanced method."""
        # Create a valid file
        content = "Valid Content|PHB"
        file_path = self.create_test_file(content)

        # Should work normally
        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )
        assert len(structured_data) == 1

        # Make file unreadable (simulate permission error)
        file_path.chmod(0o000)

        try:
            with pytest.raises(
                click.exceptions.Exit
            ):  # Should handle permission error gracefully
                self.base_command.get_enhanced_name_list_from_file(file_path, "spell")
        finally:
            # Restore permissions for cleanup
            file_path.chmod(0o644)

    def test_source_parsing_edge_cases(self) -> None:
        """Test edge cases in source parsing."""
        content = """Name with complex desc|PHB
Name|Source|With|Pipes
Normal Name|PHB"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        # First pipe should be the delimiter, rest should be part of source
        expected = [
            (1, "Name with complex desc", "PHB"),
            (1, "Name", "Source|With|Pipes"),  # Only first | is delimiter
            (1, "Normal Name", "PHB"),
        ]
        assert structured_data == expected

    def test_count_parsing_edge_cases(self) -> None:
        """Test edge cases in count parsing."""
        content = """123 Large Count|PHB
0 Zero Count|PHB
001 Leading Zeros|PHB
Not A Number Count|PHB
1.5 Decimal Count|PHB"""
        file_path = self.create_test_file(content)

        structured_data = self.base_command.get_enhanced_name_list_from_file(
            file_path, "spell"
        )

        expected = [
            (123, "Large Count", "PHB"),
            (0, "Zero Count", "PHB"),
            (1, "Leading Zeros", "PHB"),  # "001" should parse as 1
            (1, "Not A Number Count", "PHB"),  # Invalid number, defaults to 1
            (1, "1.5 Decimal Count", "PHB"),  # Decimal not valid, whole line as name
        ]
        assert structured_data == expected
