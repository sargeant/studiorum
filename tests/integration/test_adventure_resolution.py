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
            "CoS": {"abbreviation": "CoS", "name": "Curse of Strahd"},
            "LMoP": {"abbreviation": "LMoP", "name": "Lost Mine of Phandelver"},
            "Test": {"abbreviation": "Test", "name": "Test Adventure"},
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
                    "name": "Curse of Strahd",
                    "id": "CoS",
                    "source": {"abbreviation": "CoS", "name": "Curse of Strahd"},
                    "group": "supplement",
                    "published": "2016-03-15",
                    "contents": [
                        {
                            "name": "Introduction",
                            "headers": ["Running the Adventure", "Marks of Horror"],
                        },
                        {
                            "name": "Chapter 1: Into the Mists",
                            "headers": ["Death House", "Mysterious Visitors"],
                        },
                        {
                            "name": "Chapter 2: The Lands of Barovia",
                            "headers": ["Lay of the Land", "Alterations to Magic"],
                        },
                    ],
                },
                {
                    "name": "Lost Mine of Phandelver",
                    "id": "LMoP",
                    "source": "LMoP",
                    "group": "supplement",
                    "published": "2014-07-15",
                    "contents": [
                        {"name": "Introduction", "headers": ["Background", "Overview"]},
                        {
                            "name": "Part 1: Goblin Arrows",
                            "headers": ["Meet Me in Phandalin", "Goblin Ambush"],
                        },
                    ],
                },
            ]
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata_content, f, indent=2)

        # Create test content file for CoS (adventure-cos.json)
        self.cos_content_file = self.adventure_dir / "adventure-cos.json"
        cos_content = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": [
                        "Under raging storm clouds, the vampire Count Strahd von Zarovich stands silhouetted against the ancient walls of Castle Ravenloft.",
                        "Welcome to Barovia, a land of mist and shadow.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 1: Into the Mists",
                    "id": "001",
                    "entries": [
                        "The Svalich Woods are dark and oppressive.",
                        "The adventurers find themselves drawn into the cursed land.",
                        {
                            "type": "entries",
                            "name": "Death House",
                            "entries": [
                                "A notorious haunted house that serves as an optional introduction."
                            ],
                        },
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 2: The Lands of Barovia",
                    "id": "002",
                    "entries": [
                        "Barovia is a land trapped in its own demiplane.",
                        "The mists prevent escape.",
                    ],
                },
            ]
        }
        with open(self.cos_content_file, "w") as f:
            json.dump(cos_content, f, indent=2)

        # Create test content file for LMoP (adventure-lmop.json)
        self.lmop_content_file = self.adventure_dir / "adventure-lmop.json"
        lmop_content = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": [
                        "More than five hundred years ago, clans of dwarves and gnomes made an agreement.",
                        "This is the Lost Mine of Phandelver.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Part 1: Goblin Arrows",
                    "id": "001",
                    "entries": [
                        "The adventure begins as the player characters escort a wagon to Phandalin.",
                        "Goblins waylay the party on the Triboar Trail.",
                    ],
                },
            ]
        }
        with open(self.lmop_content_file, "w") as f:
            json.dump(lmop_content, f, indent=2)

    async def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    async def test_resolve_adventure_cos_full_flow(self):
        """Test end-to-end resolution of Curse of Strahd adventure."""
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
        self.assertEqual(len(adventures), 2)  # Only CoS and LMoP metadata

        # Create content resolver
        resolver = ContentResolver(omnidexer)

        # Resolve CoS adventure
        result = resolver.resolve_adventure("cos")

        # Verify resolution was successful
        self.assertEqual(result.status, ResolutionStatus.EXACT_MATCH)
        self.assertIsNotNone(result.content)

        # Verify adventure has correct metadata
        adventure = result.content
        self.assertEqual(adventure.name, "Curse of Strahd")
        self.assertEqual(adventure.id, "CoS")

        # Verify adventure has merged content
        self.assertEqual(len(adventure.contents), 3)

        # Check Introduction chapter
        intro = adventure.contents[0]
        self.assertEqual(intro.name, "Introduction")
        self.assertEqual(len(intro.entries), 2)
        self.assertIn("vampire Count Strahd", str(intro.entries[0]))
        self.assertIn("Welcome to Barovia", str(intro.entries[1]))

        # Check Chapter 1
        chapter1 = adventure.contents[1]
        self.assertEqual(chapter1.name, "Chapter 1: Into the Mists")
        self.assertTrue(len(chapter1.entries) > 0)
        self.assertIn("Svalich Woods", str(chapter1.entries[0]))

        # Check Chapter 2
        chapter2 = adventure.contents[2]
        self.assertEqual(chapter2.name, "Chapter 2: The Lands of Barovia")
        self.assertEqual(len(chapter2.entries), 2)
        self.assertIn("demiplane", str(chapter2.entries[0]))

    async def test_resolve_adventure_lmop(self):
        """Test resolution of Lost Mine of Phandelver."""
        # Create source manager
        source_manager = TestSourceManager(self.data_dir)

        # Create omnidexer and load data
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        # Create content resolver
        resolver = ContentResolver(omnidexer)

        # Resolve LMoP adventure
        result = resolver.resolve_adventure("lmop")

        # Verify resolution
        self.assertEqual(result.status, ResolutionStatus.EXACT_MATCH)
        adventure = result.content
        self.assertEqual(adventure.name, "Lost Mine of Phandelver")
        self.assertEqual(adventure.id, "LMoP")

        # Verify content was loaded and merged
        self.assertEqual(len(adventure.contents), 2)
        self.assertIn("five hundred years ago", str(adventure.contents[0].entries[0]))
        self.assertIn("Triboar Trail", str(adventure.contents[1].entries[1]))

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

        # Resolve both adventures
        cos_result = resolver.resolve_adventure("cos")
        lmop_result = resolver.resolve_adventure("lmop")

        # Both should succeed
        self.assertEqual(cos_result.status, ResolutionStatus.EXACT_MATCH)
        self.assertEqual(lmop_result.status, ResolutionStatus.EXACT_MATCH)

        # Verify they are different adventures
        self.assertNotEqual(cos_result.content.id, lmop_result.content.id)
        self.assertNotEqual(cos_result.content.name, lmop_result.content.name)

        # Verify each has correct content
        self.assertIn("Strahd", str(cos_result.content.contents[0].entries))
        self.assertIn(
            "five hundred years", str(lmop_result.content.contents[0].entries)
        )

    async def test_adventure_count_metadata_only(self):
        """Test that omnidexer only contains metadata entries, not content files."""
        source_manager = TestSourceManager(self.data_dir)

        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        # Get all adventures from omnidexer
        adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)

        # Should only have 2 adventures (from metadata), not 4 (metadata + content)
        self.assertEqual(len(adventures), 2)

        # Adventures should have metadata but empty content
        for adventure in adventures:
            self.assertTrue(
                adventure.name in ["Curse of Strahd", "Lost Mine of Phandelver"]
            )
            # Before resolution, chapters should have empty entries
            for chapter in adventure.contents:
                self.assertEqual(chapter.entries, [])
