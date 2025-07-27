"""Tests for adventure deep indexing functionality."""

import pytest

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.adventures import Adventure, AdventureChapter
from dnd5e.core.models.content import ContentType, Source
from dnd5e.core.models.nested_content import (
    AdventureInset,
    AdventureSection,
    AdventureTable,
)


class TestAdventureDeepIndexing:
    """Test adventure deep indexing functionality."""

    def test_adventure_implements_deep_indexable(self):
        """Test that Adventure implements DeepIndexable protocol."""
        adventure = Adventure(
            name="Test Adventure", source=Source(abbreviation="TEST"), contents=[]
        )

        # Should have the method
        assert hasattr(adventure, "get_deep_index_entries")
        assert callable(adventure.get_deep_index_entries)

    def test_adventure_with_no_content_returns_empty_list(self):
        """Test that adventure with no content returns empty list."""
        adventure = Adventure(
            name="Empty Adventure", source=Source(abbreviation="TEST"), contents=[]
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert result == []

    def test_adventure_with_chapter_but_no_entries(self):
        """Test adventure with chapter but no entries."""
        chapter = AdventureChapter(name="Empty Chapter", entries=[])

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert result == []

    def test_adventure_parses_section_entries(self):
        """Test that adventure parses section entries correctly."""
        chapter = AdventureChapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "section",
                    "name": "The Goblin Cave",
                    "page": 10,
                    "id": "goblin-cave",
                    "entries": [
                        "A dark cave entrance yawns before you.",
                        "The sound of goblin voices echoes from within.",
                    ],
                }
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], AdventureSection)
        assert result[0].name == "The Goblin Cave"
        assert result[0].page == 10
        assert result[0].id == "goblin-cave"
        assert result[0].parent_name == "Test Adventure > Chapter 1"
        assert result[0].source.abbreviation == "TEST"

    def test_adventure_parses_table_entries(self):
        """Test that adventure parses table entries correctly."""
        chapter = AdventureChapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "table",
                    "caption": "Random Encounters",
                    "page": 15,
                    "id": "random-encounters",
                    "colLabels": ["d6", "Encounter"],
                    "rows": [
                        ["1-2", "2d4 goblins"],
                        ["3-4", "1 owlbear"],
                        ["5-6", "1d3 wolves"],
                    ],
                }
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], AdventureTable)
        assert result[0].name == "Random Encounters"
        assert result[0].caption == "Random Encounters"
        assert result[0].page == 15
        assert result[0].col_labels == ["d6", "Encounter"]
        assert len(result[0].rows) == 3
        assert result[0].rows[0] == ["1-2", "2d4 goblins"]

    def test_adventure_parses_inset_entries(self):
        """Test that adventure parses inset entries correctly."""
        chapter = AdventureChapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "insetReadaloud",
                    "name": "Read Aloud Text",
                    "page": 20,
                    "id": "readaloud-1",
                    "entries": [
                        "The ancient door creaks open, revealing darkness beyond."
                    ],
                }
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], AdventureInset)
        assert result[0].name == "Read Aloud Text"
        assert result[0].inset_type == "insetReadaloud"
        assert result[0].page == 20

    def test_adventure_parses_nested_sections(self):
        """Test that adventure parses nested sections correctly."""
        chapter = AdventureChapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "section",
                    "name": "The Village",
                    "page": 25,
                    "entries": [
                        "A small village nestled in the valley.",
                        {
                            "type": "section",
                            "name": "The Tavern",
                            "page": 26,
                            "entries": [
                                "The local tavern is called 'The Prancing Pony'."
                            ],
                        },
                    ],
                }
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        # Should get both the parent section and the nested section
        assert len(result) == 2

        village_section = next(s for s in result if s.name == "The Village")
        tavern_section = next(s for s in result if s.name == "The Tavern")

        assert village_section.parent_name == "Test Adventure > Chapter 1"
        assert tavern_section.parent_name == "Test Adventure > Chapter 1 > The Village"

    def test_adventure_handles_multiple_chapters(self):
        """Test that adventure handles multiple chapters correctly."""
        chapter1 = AdventureChapter(
            name="Chapter 1",
            ordinal={"type": "chapter", "identifier": "1"},
            entries=[
                {
                    "type": "section",
                    "name": "Beginning",
                    "entries": ["The adventure begins..."],
                }
            ],
        )

        chapter2 = AdventureChapter(
            name="Chapter 2",
            ordinal={"type": "chapter", "identifier": "2"},
            entries=[
                {
                    "type": "section",
                    "name": "The Middle",
                    "entries": ["The plot thickens..."],
                }
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter1, chapter2],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert len(result) == 2

        beginning_section = next(s for s in result if s.name == "Beginning")
        middle_section = next(s for s in result if s.name == "The Middle")

        assert beginning_section.parent_name == "Test Adventure > Chapter 1: Chapter 1"
        assert middle_section.parent_name == "Test Adventure > Chapter 2: Chapter 2"

    def test_adventure_handles_parsing_errors_gracefully(self):
        """Test that adventure handles parsing errors gracefully."""
        chapter = AdventureChapter(
            name="Problematic Chapter",
            entries=[
                {
                    "type": "section",
                    "name": "Good Section",
                    "entries": ["This is fine."],
                },
                # This could cause parsing issues
                {"type": "unknown_type", "weird_field": None},
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        # Should not raise an exception
        result = adventure.get_deep_index_entries(omnidexer)

        # Should still get the good section
        assert len(result) >= 1
        good_section = next((s for s in result if s.name == "Good Section"), None)
        assert good_section is not None

    def test_adventure_generates_unique_hash_keys(self):
        """Test that nested content generates unique hash keys."""
        chapter = AdventureChapter(
            name="Chapter 1",
            entries=[
                {"type": "section", "name": "Section A", "entries": ["Content A"]},
                {
                    "type": "table",
                    "caption": "Table B",
                    "colLabels": ["Col1"],
                    "rows": [["Row1"]],
                },
            ],
        )

        adventure = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = adventure.get_deep_index_entries(omnidexer)

        assert len(result) == 2

        hash_keys = [item.get_hash_key() for item in result]

        # All hash keys should be unique
        assert len(hash_keys) == len(set(hash_keys))

        # Hash keys should contain expected components
        section_hash = next(h for h in hash_keys if "adventuresection" in h)
        table_hash = next(h for h in hash_keys if "adventuretable" in h)

        assert "Section A" in section_hash
        assert "TEST" in section_hash
        assert "Table B" in table_hash
        assert "TEST" in table_hash
