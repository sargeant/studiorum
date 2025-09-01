"""Tests for entry parser functionality."""

from studiorum.core.models.content import Source
from studiorum.core.models.nested_content import (
    Inset,
    Section,
    Table,
    VariantRule,
)
from studiorum.core.parsers.entry_parser import EntryParser


class TestEntryParser:
    """Test entry parser functionality."""

    def test_parser_handles_empty_entries(self):
        """Test that parser handles empty entries gracefully."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Parent")

        result = list(parser.parse_entries([], "adventure"))
        assert result == []

        result = list(parser.parse_entries(None, "adventure"))
        assert result == []

    def test_parser_ignores_string_entries(self):
        """Test that parser ignores plain string entries."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Parent")

        entries = ["This is plain text.", "Another string entry.", "Should be ignored."]

        result = list(parser.parse_entries(entries, "adventure"))
        assert result == []

    def test_parser_ignores_non_dict_entries(self):
        """Test that parser ignores non-dict entries."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Parent")

        entries = [123, ["list", "entry"], None, True]

        result = list(parser.parse_entries(entries, "adventure"))
        assert result == []

    def test_parse_section_adventure(self):
        """Test parsing section entry for adventure."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Adventure")

        entries = [
            {
                "type": "section",
                "name": "The Dark Forest",
                "page": 15,
                "id": "dark-forest",
                "entries": [
                    "Ancient trees tower overhead.",
                    "Shadows dance between the trunks.",
                ],
            }
        ]

        result = list(parser.parse_entries(entries, "adventure"))

        assert len(result) == 1
        assert isinstance(result[0], Section)
        assert result[0].name == "The Dark Forest"
        assert result[0].page == 15
        assert result[0].id == "dark-forest"
        assert result[0].parent_name == "Test Adventure"
        assert result[0].source.abbreviation == "TEST"

    def test_parse_section_book(self):
        """Test parsing section entry for book."""
        source = Source(abbreviation="PHB")
        parser = EntryParser(source, "Player's Handbook")

        entries = [
            {
                "type": "section",
                "name": "Ability Scores",
                "page": 12,
                "entries": [
                    "Six abilities define every creature.",
                    "Strength measures physical power.",
                ],
            }
        ]

        result = list(parser.parse_entries(entries, "book"))

        assert len(result) == 1
        assert isinstance(result[0], Section)
        assert result[0].name == "Ability Scores"
        assert result[0].page == 12

    def test_parse_table_adventure(self):
        """Test parsing table entry for adventure."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Adventure")

        entries = [
            {
                "type": "table",
                "caption": "Random Encounters",
                "page": 20,
                "id": "encounters",
                "colLabels": ["d10", "Encounter"],
                "rows": [
                    ["1-3", "2d4 goblins"],
                    ["4-6", "1 owlbear"],
                    ["7-10", "Nothing happens"],
                ],
            }
        ]

        result = list(parser.parse_entries(entries, "adventure"))

        assert len(result) == 1
        assert isinstance(result[0], Table)
        assert result[0].name == "Random Encounters"
        assert result[0].caption == "Random Encounters"
        assert result[0].col_labels == ["d10", "Encounter"]
        assert len(result[0].rows) == 3
        assert result[0].rows[0] == ["1-3", "2d4 goblins"]

    def test_parse_table_without_caption(self):
        """Test parsing table entry without caption."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test")

        entries = [
            {
                "type": "table",
                "page": 25,
                "colLabels": ["Roll", "Result"],
                "rows": [["1", "Success"]],
            }
        ]

        result = list(parser.parse_entries(entries, "book"))

        assert len(result) == 1
        assert isinstance(result[0], Table)
        assert result[0].name == "Table (page 25)"
        assert result[0].caption is None

    def test_parse_inset_adventure(self):
        """Test parsing inset entry for adventure."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Adventure")

        entries = [
            {
                "type": "insetReadaloud",
                "name": "Dramatic Entrance",
                "page": 30,
                "entries": [
                    "Lightning illuminates the castle spires.",
                    "Thunder echoes across the valley.",
                ],
            }
        ]

        result = list(parser.parse_entries(entries, "adventure"))

        assert len(result) == 1
        assert isinstance(result[0], Inset)
        assert result[0].name == "Dramatic Entrance"
        assert result[0].inset_type == "insetReadaloud"
        assert result[0].page == 30

    def test_parse_inset_without_name(self):
        """Test parsing inset entry without name."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test")

        entries = [
            {"type": "inset", "page": 35, "entries": ["Important sidebar information."]}
        ]

        result = list(parser.parse_entries(entries, "book"))

        assert len(result) == 1
        assert isinstance(result[0], Inset)
        assert result[0].name == "Inset (page 35)"
        assert result[0].inset_type == "inset"

    def test_parse_entries_variant_rule_detection(self):
        """Test parsing entries that should be detected as variant rules."""
        source = Source(abbreviation="DMG")
        parser = EntryParser(source, "Dungeon Master's Guide")

        variant_entries = [
            {
                "type": "entries",
                "name": "Optional Rule: Flanking",
                "page": 251,
                "entries": ["When you and an ally flank an enemy, you gain advantage."],
            },
            {
                "type": "entries",
                "name": "Variant: Initiative",
                "page": 252,
                "entries": ["You can use this alternative initiative system."],
            },
            {
                "type": "entries",
                "name": "Optional: Grid Systems",
                "page": 253,
                "entries": ["Dungeon masters can use hexagonal grids instead."],
            },
        ]

        result = list(parser.parse_entries(variant_entries, "book"))

        assert len(result) == 3
        for item in result:
            assert isinstance(item, VariantRule)

        names = [item.name for item in result]
        assert "Optional Rule: Flanking" in names
        assert "Variant: Initiative" in names
        assert "Optional: Grid Systems" in names

    def test_parse_entries_regular_section_detection(self):
        """Test parsing entries that should be regular sections, not variant rules."""
        source = Source(abbreviation="PHB")
        parser = EntryParser(source, "Player's Handbook")

        entries = [
            {
                "type": "entries",
                "name": "Character Creation",
                "page": 11,
                "entries": [
                    "Creating a character is straightforward.",
                    "Follow these steps to build your hero.",
                ],
            },
            {
                "type": "entries",
                "name": "Equipment",
                "page": 143,
                "entries": ["Characters start with equipment based on class."],
            },
        ]

        result = list(parser.parse_entries(entries, "book"))

        assert len(result) == 2
        for item in result:
            assert isinstance(item, Section)
            assert not isinstance(item, VariantRule)

    def test_parse_nested_sections_with_updated_parent(self):
        """Test that nested sections get updated parent names."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Test Adventure")

        entries = [
            {
                "type": "section",
                "name": "The Town",
                "entries": [
                    "A bustling settlement.",
                    {
                        "type": "section",
                        "name": "The Market Square",
                        "entries": [
                            "Vendors hawk their wares.",
                            {
                                "type": "section",
                                "name": "The Fountain",
                                "entries": ["An ornate fountain stands here."],
                            },
                        ],
                    },
                ],
            }
        ]

        result = list(parser.parse_entries(entries, "adventure"))

        assert len(result) == 3

        town = next(s for s in result if s.name == "The Town")
        market = next(s for s in result if s.name == "The Market Square")
        fountain = next(s for s in result if s.name == "The Fountain")

        assert town.parent_name == "Test Adventure"
        assert market.parent_name == "Test Adventure > The Town"
        assert fountain.parent_name == "Test Adventure > The Town > The Market Square"

    def test_variant_rule_detection_logic(self):
        """Test the variant rule detection logic specifically."""
        source = Source(abbreviation="DMG")
        parser = EntryParser(source, "Test")

        # Test cases that should be detected as variant rules (explicit markers only)
        variant_cases = [
            ("Variant: Something", ["content"]),
            ("Optional: Combat Rules", ["dungeon master can use this"]),
            ("Alternative: Initiative", ["this variant changes how"]),
            ("Variant Rule: Madness", ["instead of the normal rules"]),
        ]

        for name, entries in variant_cases:
            assert parser._is_variant_rule_content(name, entries, "book"), (
                f"Should detect '{name}' as variant rule"
            )

        # Test cases that should NOT be detected as variant rules
        normal_cases = [
            ("Combat Basics", ["combat follows these steps"]),
            ("Character Creation", ["create your character"]),
            ("Equipment List", ["here are the items"]),
            ("Spellcasting", ["magic works like this"]),
            (
                "Using Different Dice",
                ["you can use d12s instead"],
            ),  # No explicit marker
            (
                "Optional Combat Rules",
                ["dungeon master can use this"],
            ),  # No colon after "Optional"
            (
                "Alternative Initiative",
                ["this variant changes how"],
            ),  # No colon after "Alternative"
            (
                "Custom Madness Rules",
                ["instead of the normal rules"],
            ),  # No explicit marker
        ]

        for name, entries in normal_cases:
            assert not parser._is_variant_rule_content(name, entries, "book"), (
                f"Should NOT detect '{name}' as variant rule"
            )

    def test_mixed_entry_types_parsing(self):
        """Test parsing mixed entry types in one go."""
        source = Source(abbreviation="TEST")
        parser = EntryParser(source, "Mixed Content")

        entries = [
            "Plain text string (ignored)",
            {
                "type": "section",
                "name": "Important Section",
                "entries": ["Section content"],
            },
            123,  # Non-dict entry (ignored)
            {
                "type": "table",
                "caption": "Data Table",
                "colLabels": ["A", "B"],
                "rows": [["1", "2"]],
            },
            {"type": "inset", "name": "Side Note", "entries": ["This is a sidebar"]},
            {"type": "unknown", "weird": "field"},  # Unknown type (ignored)
        ]

        result = list(parser.parse_entries(entries, "adventure"))

        assert len(result) == 3  # Only section, table, and inset should be parsed

        types = [type(item).__name__ for item in result]
        assert "Section" in types
        assert "Table" in types
        assert "Inset" in types
