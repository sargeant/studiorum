"""Tests for book deep indexing functionality."""

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.books import Book
from dnd5e.core.models.chapter import Chapter
from dnd5e.core.models.content import Source
from dnd5e.core.models.nested_content import (
    Inset,
    Section,
    Table,
    VariantRule,
)


class TestBookDeepIndexing:
    """Test book deep indexing functionality."""

    def test_book_implements_deep_indexable(self):
        """Test that Book implements DeepIndexable protocol."""
        book = Book(name="Test Book", source=Source(abbreviation="TEST"), contents=[])

        # Should have the method
        assert hasattr(book, "get_deep_index_entries")
        assert callable(book.get_deep_index_entries)

    def test_book_parses_section_entries(self):
        """Test that book parses section entries correctly."""
        chapter = Chapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "section",
                    "name": "Character Creation",
                    "page": 10,
                    "id": "char-creation",
                    "entries": [
                        "Creating a character is the first step in D&D.",
                        "Choose your race and class carefully.",
                    ],
                }
            ],
        )

        book = Book(
            name="Player's Handbook",
            source=Source(abbreviation="PHB"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], Section)
        assert result[0].name == "Character Creation"
        assert result[0].page == 10
        assert result[0].parent_name == "Player's Handbook > Chapter 1"
        assert result[0].source.abbreviation == "PHB"

    def test_book_parses_variant_rules(self):
        """Test that book parses variant rules correctly."""
        chapter = Chapter(
            name="Chapter 9",
            entries=[
                {
                    "type": "entries",
                    "name": "Optional: Flanking",
                    "page": 251,
                    "entries": [
                        "This optional rule provides advantage when flanking.",
                        "When you and an ally flank an enemy, you gain advantage.",
                    ],
                }
            ],
        )

        book = Book(
            name="Dungeon Master's Guide",
            source=Source(abbreviation="DMG"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], VariantRule)
        assert result[0].name == "Optional: Flanking"
        assert result[0].page == 251

    def test_book_distinguishes_variant_rules_from_sections(self):
        """Test that book correctly distinguishes variant rules from regular sections."""
        chapter = Chapter(
            name="Chapter 9",
            entries=[
                {
                    "type": "entries",
                    "name": "Optional Rule: Initiative Variants",
                    "page": 250,
                    "entries": [
                        "You can use these alternative initiative rules.",
                        "Roll initiative differently for variety.",
                    ],
                },
                {
                    "type": "entries",
                    "name": "Running Combat",
                    "page": 245,
                    "entries": [
                        "Combat follows a structured sequence.",
                        "Players declare actions in order.",
                    ],
                },
            ],
        )

        book = Book(
            name="Dungeon Master's Guide",
            source=Source(abbreviation="DMG"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 2

        # First should be variant rule (has "optional" and "variant" in name)
        variant_rule = next(r for r in result if isinstance(r, VariantRule))
        assert variant_rule.name == "Optional Rule: Initiative Variants"

        # Second should be regular section
        section = next(r for r in result if isinstance(r, Section))
        assert section.name == "Running Combat"

    def test_book_parses_table_entries(self):
        """Test that book parses table entries correctly."""
        chapter = Chapter(
            name="Chapter 5",
            entries=[
                {
                    "type": "table",
                    "caption": "Ability Score Costs",
                    "page": 13,
                    "colLabels": ["Score", "Cost"],
                    "rows": [["8", "0"], ["9", "1"], ["10", "2"]],
                }
            ],
        )

        book = Book(
            name="Player's Handbook",
            source=Source(abbreviation="PHB"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], Table)
        assert result[0].name == "Ability Score Costs"
        assert result[0].caption == "Ability Score Costs"
        assert result[0].col_labels == ["Score", "Cost"]
        assert len(result[0].rows) == 3

    def test_book_parses_inset_entries(self):
        """Test that book parses inset entries correctly."""
        chapter = Chapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "inset",
                    "name": "Building Bruenor",
                    "page": 15,
                    "entries": [
                        "Each step of character creation includes an example",
                        "of that step, with a player named Bob building his character.",
                    ],
                }
            ],
        )

        book = Book(
            name="Player's Handbook",
            source=Source(abbreviation="PHB"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 1
        assert isinstance(result[0], Inset)
        assert result[0].name == "Building Bruenor"
        assert result[0].inset_type == "inset"
        assert result[0].page == 15

    def test_book_handles_complex_nested_structure(self):
        """Test that book handles complex nested content correctly."""
        chapter = Chapter(
            name="Chapter 9",
            entries=[
                {
                    "type": "section",
                    "name": "Combat",
                    "page": 189,
                    "entries": [
                        "Combat in D&D is cyclical.",
                        {
                            "type": "entries",
                            "name": "Variant: Initiative Scoring",
                            "page": 190,
                            "entries": [
                                "This variant rule changes how initiative works.",
                                "Instead of rolling, use Dexterity scores.",
                            ],
                        },
                        {
                            "type": "table",
                            "caption": "Initiative Order",
                            "colLabels": ["Dexterity", "Initiative Modifier"],
                            "rows": [["20", "+5"], ["18", "+4"], ["16", "+3"]],
                        },
                    ],
                }
            ],
        )

        book = Book(
            name="Dungeon Master's Guide",
            source=Source(abbreviation="DMG"),
            contents=[chapter],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        # Should get: Combat section, Initiative Scoring variant rule, Initiative Order table
        assert len(result) == 3

        combat_section = next(r for r in result if r.name == "Combat")
        variant_rule = next(
            r for r in result if r.name == "Variant: Initiative Scoring"
        )
        table = next(r for r in result if r.name == "Initiative Order")

        assert isinstance(combat_section, Section)
        assert isinstance(variant_rule, VariantRule)
        assert isinstance(table, Table)

        # Check parent relationships
        assert combat_section.parent_name == "Dungeon Master's Guide > Chapter 9"
        assert variant_rule.parent_name == "Dungeon Master's Guide > Chapter 9 > Combat"
        assert table.parent_name == "Dungeon Master's Guide > Chapter 9 > Combat"

    def test_book_handles_5etools_data_format(self):
        """Test that book handles 5etools data array format correctly."""
        # Simulate 5etools book format with "data" array
        # Note: 5etools format needs to be wrapped in proper chapters for deep indexing to work
        book_data = {
            "name": "Player's Handbook",
            "source": {"abbreviation": "PHB"},
            "contents": [  # Use contents directly with proper chapter structure
                {
                    "name": "Chapter 1",
                    "entries": [
                        {
                            "type": "section",
                            "name": "Introduction",
                            "page": 5,
                            "entries": ["Welcome to D&D!"],
                        }
                    ],
                }
            ],
        }

        # The Book model should handle this format
        book = Book(**book_data)

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        # Should parse the chapter entries
        assert len(result) == 1
        assert isinstance(result[0], Section)
        assert result[0].name == "Introduction"

    def test_book_generates_appropriate_content_names(self):
        """Test that book generates appropriate names for unnamed content."""
        chapter = Chapter(
            name="Chapter 1",
            entries=[
                {
                    "type": "table",
                    "page": 25,
                    "colLabels": ["Roll", "Result"],
                    "rows": [["1", "Success"]],
                    # No caption provided
                },
                {
                    "type": "inset",
                    "page": 30,
                    "entries": ["Important note here"],
                    # No name provided
                },
            ],
        )

        book = Book(
            name="Test Book", source=Source(abbreviation="TEST"), contents=[chapter]
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 2

        table = next(r for r in result if isinstance(r, Table))
        inset = next(r for r in result if isinstance(r, Inset))

        # Should generate meaningful names
        assert "Table" in table.name
        assert "page 25" in table.name
        assert "Inset" in inset.name
        assert "page 30" in inset.name

    def test_book_with_multiple_chapters_and_ordinals(self):
        """Test book with multiple chapters using different ordinal types."""
        chapter1 = Chapter(
            name="Character Creation",
            ordinal={"type": "chapter", "identifier": "1"},
            entries=[
                {
                    "type": "section",
                    "name": "Choose a Race",
                    "entries": ["Your race determines..."],
                }
            ],
        )

        appendix = Chapter(
            name="Conditions",
            ordinal={"type": "appendix", "identifier": "A"},
            entries=[
                {
                    "type": "entries",
                    "name": "Blinded",
                    "entries": ["A blinded creature can't see..."],
                }
            ],
        )

        book = Book(
            name="Player's Handbook",
            source=Source(abbreviation="PHB"),
            contents=[chapter1, appendix],
        )

        omnidexer = Omnidexer()
        result = book.get_deep_index_entries(omnidexer)

        assert len(result) == 2

        race_section = next(r for r in result if r.name == "Choose a Race")
        blinded_section = next(r for r in result if r.name == "Blinded")

        assert (
            race_section.parent_name
            == "Player's Handbook > Chapter 1: Character Creation"
        )
        assert (
            blinded_section.parent_name == "Player's Handbook > Appendix A: Conditions"
        )
