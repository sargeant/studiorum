"""Test source manager filtering of adventure/book content files."""

from pathlib import Path
from unittest import TestCase

from studiorum.core.loaders.configurable_source_manager import ConfigurableSourceManager


class TestSourceManagerFiltering(TestCase):
    """Test that ConfigurableSourceManager filters out adventure/book content files."""

    def test_should_skip_adventure_content_files(self) -> None:
        """Test that adventure content files are skipped during discovery."""
        source_manager = ConfigurableSourceManager()

        # These should be skipped (content files)
        adventure_content_files = [
            Path("/data/adventure-lmop.json"),
            Path("/data/adventure-cos.json"),
            Path("/data/adventure-skt.json"),
            Path("/data/some/path/adventure-test.json"),
        ]

        for file_path in adventure_content_files:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertTrue(
                should_skip, f"Should skip adventure content file: {file_path}"
            )

    def test_should_not_skip_adventure_metadata_files(self) -> None:
        """Test that adventure metadata files are not skipped during discovery."""
        source_manager = ConfigurableSourceManager()

        # These should NOT be skipped (metadata files)
        adventure_metadata_files = [
            Path("/data/adventures.json"),
            Path("/data/some/path/adventures.json"),
            Path("/data/adventure.json"),  # Single form
        ]

        for file_path in adventure_metadata_files:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertFalse(
                should_skip, f"Should not skip adventure metadata file: {file_path}"
            )

    def test_should_skip_book_content_files(self) -> None:
        """Test that book content files are skipped during discovery."""
        source_manager = ConfigurableSourceManager()

        # These should be skipped (content files)
        book_content_files = [
            Path("/data/book-phb.json"),
            Path("/data/book-mm.json"),
            Path("/data/book-dmg.json"),
            Path("/data/some/path/book-test.json"),
        ]

        for file_path in book_content_files:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertTrue(should_skip, f"Should skip book content file: {file_path}")

    def test_should_not_skip_book_metadata_files(self) -> None:
        """Test that book metadata files are not skipped during discovery."""
        source_manager = ConfigurableSourceManager()

        # These should NOT be skipped (metadata files)
        book_metadata_files = [
            Path("/data/books.json"),
            Path("/data/some/path/books.json"),
            Path("/data/book.json"),  # Single form
        ]

        for file_path in book_metadata_files:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertFalse(
                should_skip, f"Should not skip book metadata file: {file_path}"
            )

    def test_should_not_skip_other_content_files(self) -> None:
        """Test that other content types are not affected by the adventure/book filtering."""
        source_manager = ConfigurableSourceManager()

        # These should NOT be skipped (other content types)
        other_files = [
            Path("/data/spells.json"),
            Path("/data/spell-phb.json"),  # This pattern should not be filtered
            Path("/data/bestiary.json"),
            Path("/data/monster-mm.json"),  # This pattern should not be filtered
            Path("/data/items.json"),
            Path("/data/item-dmg.json"),  # This pattern should not be filtered
            Path("/data/classes.json"),
            Path("/data/class-fighter.json"),  # This pattern should not be filtered
        ]

        for file_path in other_files:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertFalse(
                should_skip, f"Should not skip other content file: {file_path}"
            )

    def test_adventure_book_edge_cases(self) -> None:
        """Test edge cases for adventure and book file filtering."""
        source_manager = ConfigurableSourceManager()

        # Edge cases that should NOT be skipped
        edge_cases = [
            Path("/data/adventurous.json"),  # Contains "adventure" but not prefix
            Path("/data/adventure.json"),  # Exact match, should not be skipped
            Path("/data/adventures.json"),  # Plural form, should not be skipped
            Path("/data/booking.json"),  # Contains "book" but not prefix
            Path("/data/book.json"),  # Exact match, should not be skipped
            Path("/data/books.json"),  # Plural form, should not be skipped
            Path("/data/some-adventure-guide.json"),  # Contains but not prefix
            Path("/data/my-book-collection.json"),  # Contains but not prefix
        ]

        for file_path in edge_cases:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertFalse(should_skip, f"Should not skip edge case: {file_path}")

        # Edge cases that SHOULD be skipped
        should_skip_cases = [
            Path("/data/adventure-custom-name.json"),
            Path("/data/book-custom-title.json"),
            Path("/data/adventure-.json"),  # Even with empty suffix
            Path("/data/book-.json"),  # Even with empty suffix
        ]

        for file_path in should_skip_cases:
            should_skip = source_manager._should_skip_file_at_discovery(file_path)
            self.assertTrue(should_skip, f"Should skip edge case: {file_path}")
