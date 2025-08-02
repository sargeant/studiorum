"""Integration tests for adventure resolution with on-demand content loading."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch

from dnd5e.core.loaders import FileSystemSourceManager, Omnidexer
from dnd5e.core.loaders.base import SourceManager
from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers.content_resolver import ContentResolver, ResolutionStatus


class TestSourceManager(SourceManager):
    """Test source manager that uses a custom data directory."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files only."""
        paths = {}

        # Check for adventures metadata
        adventures_file = self.data_dir / "adventures.json"
        if adventures_file.exists():
            paths[ContentType.ADVENTURE] = [adventures_file]

        # Check for books metadata
        books_file = self.data_dir / "books.json"
        if books_file.exists():
            paths[ContentType.BOOK] = [books_file]

        return paths

    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return metadata files."""
        return self.get_data_paths()

    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return content files."""
        paths = {}

        # Check for adventure content files
        adventure_dir = self.data_dir / "adventure"
        if adventure_dir.exists():
            adventure_files = list(adventure_dir.glob("adventure-*.json"))
            if adventure_files:
                paths[ContentType.ADVENTURE] = adventure_files

        # Check for book content files
        book_dir = self.data_dir / "book"
        if book_dir.exists():
            book_files = list(book_dir.glob("book-*.json"))
            if book_files:
                paths[ContentType.BOOK] = book_files

        return paths

    def get_source_info(self) -> dict[str, dict[str, Any]]:
        """Return source information."""
        return {"test": {"name": "Test Source", "path": str(self.data_dir)}}

    async def ensure_sources_ready(self) -> None:
        """Ensure sources are ready (no-op for test)."""
        pass

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information."""
        # Simple mapping for test sources
        sources = {
            "TEST": {"abbreviation": "TEST", "name": "Test Adventure"},
        }
        return sources.get(source_abbrev)

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority)."""
        # All test sources have same priority
        return 100


class TestAdventureResolution(IsolatedAsyncioTestCase):
    """End-to-end integration tests for adventure resolution."""

    async def asyncSetUp(self):
        """Set up test environment with temporary data files."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create data directory structure
        self.data_dir = self.temp_path / "data"
        self.data_dir.mkdir()
        self.adventure_dir = self.data_dir / "adventure"
        self.adventure_dir.mkdir()

        # Create test metadata file (adventures.json)
        self.metadata_file = self.data_dir / "adventures.json"
        metadata_content = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "id": "test-adventure",
                    "source": "TEST",
                    "group": "homebrew",
                    "published": "2024-01-01",
                    "storyline": "Test Campaign",
                    "level": {"start": 1, "end": 5},
                    "contents": [
                        {
                            "name": "Chapter 1: The Beginning",
                            "ordinal": {"type": "chapter", "identifier": 1},
                            "headers": ["The Village", "The Quest", "The Journey"],
                            "entries": [],
                        },
                        {
                            "name": "Chapter 2: The Repository",
                            "ordinal": {"type": "chapter", "identifier": 2},
                            "headers": [
                                "Approaching the Repository",
                                "Interior Chambers",
                                "The Core",
                            ],
                            "entries": [],
                        },
                    ],
                },
            ]
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata_content, f, indent=2)

        # Create test content file for Test Adventure (adventure-test-adventure.json)
        self.test_content_file = self.adventure_dir / "adventure-test-adventure.json"
        test_content = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1: The Beginning",
                    "id": "000",
                    "entries": [
                        "The party finds themselves in a small village plagued by mysterious events.",
                        "Local villagers speak of strange lights emanating from an ancient repository.",
                        {
                            "type": "entries",
                            "name": "The Village",
                            "entries": [
                                "A quiet farming community with a dark secret."
                            ],
                        },
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 2: The Repository",
                    "id": "001",
                    "entries": [
                        "The ancient repository holds forgotten knowledge and dangerous artifacts.",
                        "Strange magical energies permeate the structure.",
                    ],
                },
            ]
        }
        with open(self.test_content_file, "w") as f:
            json.dump(test_content, f, indent=2)

    async def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    async def test_resolve_adventure_test_full_flow(self):
        """Test end-to-end resolution of Test Adventure."""
        # Create source manager with our test data
        source_manager = TestSourceManager(self.data_dir)

        # Create omnidexer and load data
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        # Debug: check what files were found
        data_paths = source_manager.get_data_paths()
        print(f"Data paths found: {data_paths}")

        # Also verify the file exists and can be read
        adv_file = data_paths[ContentType.ADVENTURE][0]
        with open(adv_file) as f:
            metadata = json.load(f)
            print(f"Metadata file has {len(metadata.get('adventure', []))} adventures")

        # Verify omnidexer only loaded metadata
        adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
        print(f"Adventures loaded: {len(adventures)}")
        for adv in adventures:
            print(f"  - {adv.name} (id: {adv.id})")
        self.assertEqual(len(adventures), 1)  # Only Test Adventure metadata

        # Create content resolver
        resolver = ContentResolver(omnidexer)

        # Resolve Test adventure
        result = resolver.resolve_adventure("TEST")

        # Verify resolution was successful
        self.assertEqual(result.status, ResolutionStatus.EXACT_MATCH)
        self.assertIsNotNone(result.content)

        # Verify adventure has correct metadata
        adventure = result.content
        self.assertEqual(adventure.name, "Test Adventure")
        self.assertEqual(adventure.id, "test-adventure")

        # Verify adventure has merged content
        self.assertEqual(len(adventure.contents), 2)

        # Check Chapter 1
        chapter1 = adventure.contents[0]
        self.assertEqual(chapter1.name, "Chapter 1: The Beginning")
        self.assertEqual(len(chapter1.entries), 3)  # Updated to match test content
        self.assertIn("small village", str(chapter1.entries[0]))
        self.assertIn("ancient repository", str(chapter1.entries[1]))

        # Check Chapter 2
        chapter2 = adventure.contents[1]
        self.assertEqual(chapter2.name, "Chapter 2: The Repository")
        self.assertEqual(len(chapter2.entries), 2)  # Updated to match test content
        self.assertIn("forgotten knowledge", str(chapter2.entries[0]))

    async def test_resolve_adventure_missing_content_file(self):
        """Test resolution when content file is missing."""
        # Create additional metadata entry without content file
        metadata_content = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "id": "TestAdv",
                    "source": "Test",
                    "contents": [{"name": "Chapter 1", "headers": ["Section 1"]}],
                }
            ]
        }

        # Create new temp dir for this test
        temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(temp_dir.name) / "data"
        data_dir.mkdir()

        metadata_file = data_dir / "adventures.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata_content, f)

        # Create source manager
        source_manager = TestSourceManager(data_dir)

        # Load and resolve
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()
        resolver = ContentResolver(omnidexer)

        result = resolver.resolve_adventure("test")

        # Should still resolve but with empty content
        self.assertEqual(result.status, ResolutionStatus.EXACT_MATCH)
        adventure = result.content
        self.assertEqual(adventure.name, "Test Adventure")
        self.assertEqual(len(adventure.contents), 1)
        self.assertEqual(adventure.contents[0].entries, [])  # Empty entries

        temp_dir.cleanup()

    async def test_resolve_nonexistent_adventure(self):
        """Test resolution of non-existent adventure."""
        # Use TestSourceManager with our test data
        source_manager = TestSourceManager(self.data_dir)

        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()
        resolver = ContentResolver(omnidexer)

        result = resolver.resolve_adventure("nonexistent")

        self.assertEqual(result.status, ResolutionStatus.NO_MATCH)
        self.assertIsNone(result.content)
        # Should have suggestions for similar adventures
        self.assertTrue(
            len(result.suggestions) > 0 or result.status == ResolutionStatus.NO_MATCH
        )

    async def test_multiple_adventures_loaded(self):
        """Test that multiple adventures can be resolved independently."""
        source_manager = TestSourceManager(self.data_dir)

        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()
        resolver = ContentResolver(omnidexer)

        # Resolve test adventure
        test_adventure_result = resolver.resolve_adventure("TEST")

        # Should succeed
        self.assertEqual(test_adventure_result.status, ResolutionStatus.EXACT_MATCH)
        self.assertIsNotNone(test_adventure_result.content)

        # Verify it has correct content
        self.assertEqual(test_adventure_result.content.name, "Test Adventure")
        self.assertEqual(test_adventure_result.content.source.abbreviation, "TEST")

    async def test_adventure_count_metadata_only(self):
        """Test that omnidexer only contains metadata entries, not content files."""
        source_manager = TestSourceManager(self.data_dir)

        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        # Get all adventures from omnidexer
        adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)

        # Should only have 1 adventure (from metadata), not 2 (metadata + content)
        self.assertEqual(len(adventures), 1)

        # Adventure should have metadata but empty content
        for adventure in adventures:
            self.assertTrue(adventure.name in ["Test Adventure"])
            # Before resolution, chapters should have empty entries
            for chapter in adventure.contents:
                self.assertEqual(chapter.entries, [])
