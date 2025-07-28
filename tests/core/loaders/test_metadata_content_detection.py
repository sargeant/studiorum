"""Test metadata vs content file detection for adventures and books."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import IsolatedAsyncioTestCase

from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.models.content import ContentType


class TestMetadataContentDetection(IsolatedAsyncioTestCase):
    """Test metadata vs content file detection logic."""

    def test_detect_adventure_metadata_file(self) -> None:
        """Test detection of adventure metadata files (adventures.json)."""
        # Mock adventure metadata structure
        metadata_data = {
            "adventure": [
                {
                    "name": "Lost Mine of Phandelver",
                    "id": "LMoP",
                    "source": "LMoP",
                    "published": "2014-07-15",
                    "author": "Richard Baker, James Jacobs, Steve Winter",
                    "contents": [
                        {"name": "Introduction", "headers": ["Background", "Overview"]},
                        {
                            "name": "Part 1: Goblin Ambush",
                            "headers": ["The Goblin Ambush", "Cragmaw Hideout"],
                        },
                    ],
                    "level": {"min": 1, "max": 5},
                }
            ]
        }

        loader = JsonDataLoader(ContentType.ADVENTURE)
        is_metadata = loader._is_adventure_metadata_file(metadata_data)

        self.assertTrue(is_metadata, "Should detect adventure metadata file")

    def test_detect_adventure_content_file(self) -> None:
        """Test detection of adventure content files (adventure-*.json)."""
        # Mock adventure content structure
        content_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": [
                        "Lost Mine of Phandelver is an adventure for four to five 1st-level characters.",
                        "The adventure provides enough content to advance characters to 5th level.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Part 1: Goblin Ambush",
                    "id": "001",
                    "entries": [
                        "The adventure begins as the heroes are traveling down the High Road.",
                        "When the characters get within a few feet of the horses, read:",
                        "Two dead horses are sprawled about fifty feet ahead of you, blocking the trail.",
                    ],
                },
            ]
        }

        loader = JsonDataLoader(ContentType.ADVENTURE)
        is_content = loader._is_adventure_content_file(content_data)

        self.assertTrue(is_content, "Should detect adventure content file")

    def test_detect_book_metadata_file(self) -> None:
        """Test detection of book metadata files (books.json)."""
        # Mock book metadata structure
        metadata_data = {
            "book": [
                {
                    "name": "Player's Handbook",
                    "id": "PHB",
                    "source": "PHB",
                    "published": "2014-08-19",
                    "author": "Jeremy Crawford, James Wyatt, Robert J. Schwalb",
                    "contents": [
                        {
                            "name": "Introduction",
                            "headers": ["Worlds of Adventure", "Using This Book"],
                        },
                        {
                            "name": "Chapter 1: Step-by-Step Characters",
                            "headers": ["Beyond 1st Level", "Class Features"],
                        },
                    ],
                }
            ]
        }

        loader = JsonDataLoader(ContentType.BOOK)
        is_metadata = loader._is_book_metadata_file(metadata_data)

        self.assertTrue(is_metadata, "Should detect book metadata file")

    def test_detect_book_content_file(self) -> None:
        """Test detection of book content files (book-*.json)."""
        # Mock book content structure
        content_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": [
                        "The Dungeons & Dragons roleplaying game is about storytelling in worlds of swords and sorcery.",
                        "It shares elements with childhood games of make-believe.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 1: Step-by-Step Characters",
                    "id": "001",
                    "entries": [
                        "Your first step in playing an adventurer in the Dungeons & Dragons game is to imagine and create a character of your own.",
                        "Your character is a combination of game statistics, roleplaying hooks, and your imagination.",
                    ],
                },
            ]
        }

        loader = JsonDataLoader(ContentType.BOOK)
        is_content = loader._is_book_content_file(content_data)

        self.assertTrue(is_content, "Should detect book content file")

    def test_other_content_types_not_detected_as_metadata(self) -> None:
        """Test that other content types are not detected as metadata files."""
        # Mock spell data structure
        spell_data = {
            "spell": [
                {
                    "name": "Fireball",
                    "source": "PHB",
                    "level": 3,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 150},
                    },
                }
            ]
        }

        # Test with different content types
        for content_type in [ContentType.SPELL, ContentType.CREATURE, ContentType.ITEM]:
            loader = JsonDataLoader(content_type)

            # The methods exist but should return False for non-adventure/book data
            self.assertFalse(loader._is_adventure_metadata_file(spell_data))
            self.assertFalse(loader._is_adventure_content_file(spell_data))
            self.assertFalse(loader._is_book_metadata_file(spell_data))
            self.assertFalse(loader._is_book_content_file(spell_data))

    def test_adventure_metadata_vs_content_distinction(self) -> None:
        """Test that we can distinguish between adventure metadata and content."""
        # Metadata has 'adventure' key but no 'data' key
        metadata_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "id": "TEST",
                    "source": "TEST",
                    "contents": [],
                }
            ]
        }

        # Content has 'data' key but no 'adventure' key
        content_data = {
            "data": [
                {"type": "section", "name": "Test Section", "entries": ["Test content"]}
            ]
        }

        # Mixed data should not be classified as either (shouldn't exist in real data)
        mixed_data = {
            "adventure": [{"name": "Test"}],
            "data": [{"type": "section", "name": "Test"}],
        }

        loader = JsonDataLoader(ContentType.ADVENTURE)

        self.assertTrue(loader._is_adventure_metadata_file(metadata_data))
        self.assertFalse(loader._is_adventure_content_file(metadata_data))

        self.assertFalse(loader._is_adventure_metadata_file(content_data))
        self.assertTrue(loader._is_adventure_content_file(content_data))

        # Mixed data should not be classified as either type
        self.assertFalse(loader._is_adventure_metadata_file(mixed_data))
        self.assertFalse(loader._is_adventure_content_file(mixed_data))

    def test_book_metadata_vs_content_distinction(self) -> None:
        """Test that we can distinguish between book metadata and content."""
        # Metadata has 'book' key but no 'data' key
        metadata_data = {
            "book": [
                {"name": "Test Book", "id": "TEST", "source": "TEST", "contents": []}
            ]
        }

        # Content has 'data' key but no 'book' key
        content_data = {
            "data": [
                {"type": "section", "name": "Test Chapter", "entries": ["Test content"]}
            ]
        }

        loader = JsonDataLoader(ContentType.BOOK)

        self.assertTrue(loader._is_book_metadata_file(metadata_data))
        self.assertFalse(loader._is_book_content_file(metadata_data))

        self.assertFalse(loader._is_book_metadata_file(content_data))
        self.assertTrue(loader._is_book_content_file(content_data))

    async def test_loader_can_still_load_content_files_directly(self) -> None:
        """Test that JsonDataLoader can still load content files when used directly (for backwards compatibility)."""
        # Create adventure content file
        content_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Test Section",
                    "entries": ["This content should be loaded when called directly"],
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(content_data, f, indent=2)
            temp_path = Path(f.name)

        try:
            loader = JsonDataLoader(ContentType.ADVENTURE)
            adventures = await loader.load(temp_path)

            # Should successfully load the adventure from content file when called directly
            self.assertEqual(len(adventures), 1)
            adventure = adventures[0]
            self.assertIsNotNone(adventure.name)

        finally:
            temp_path.unlink()

    async def test_loader_can_still_load_book_content_files_directly(self) -> None:
        """Test that JsonDataLoader can still load book content files when used directly (for backwards compatibility)."""
        # Create book content file
        content_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Test Chapter",
                    "entries": ["This content should be loaded when called directly"],
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(content_data, f, indent=2)
            temp_path = Path(f.name)

        try:
            loader = JsonDataLoader(ContentType.BOOK)
            books = await loader.load(temp_path)

            # Should successfully load the book from content file when called directly
            self.assertEqual(len(books), 1)
            book = books[0]
            self.assertIsNotNone(book.name)

        finally:
            temp_path.unlink()

    async def test_loader_processes_metadata_files_normally(self) -> None:
        """Test that JsonDataLoader processes metadata files normally."""
        # Create adventure metadata file (should be processed)
        metadata_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "id": "TEST",
                    "source": "TEST",
                    "published": "2024-01-01",
                    "contents": [
                        {"name": "Chapter 1", "headers": ["Section A", "Section B"]}
                    ],
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(metadata_data, f, indent=2)
            temp_path = Path(f.name)

        try:
            loader = JsonDataLoader(ContentType.ADVENTURE)
            adventures = await loader.load(temp_path)

            # Should successfully load the adventure from metadata file
            self.assertEqual(len(adventures), 1)
            adventure = adventures[0]
            self.assertEqual(adventure.name, "Test Adventure")
            # Type assertion since we know this is an Adventure model
            if hasattr(adventure, "id"):
                self.assertEqual(adventure.id, "TEST")

        finally:
            temp_path.unlink()
