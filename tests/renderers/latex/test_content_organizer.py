"""Tests for content organization utilities."""

from typing import Any
from unittest.mock import patch

from dnd5e.core.models.content import BaseContent, Source  # type: ignore
from dnd5e.core.models.document_metadata import (  # type: ignore
    DocumentType,
    SectionLevel,
)
from dnd5e.renderers.latex.content_organizer import ContentOrganizer  # type: ignore
from tests.test_helpers import reset_test_environment


class MockSpell(BaseContent):
    """Mock spell for testing."""

    def __init__(self, name: str, level: int = 1, school: str = "evocation"):
        super().__init__(name=name, source=Source(abbreviation="TEST"))
        self.level = level
        self.school = school


class MockCreature(BaseContent):
    """Mock creature for testing."""

    def __init__(self, name: str, cr: Any = 1.0):
        super().__init__(name=name, source=Source(abbreviation="TEST"))
        self.cr = cr


class MockItem(BaseContent):
    """Mock item for testing."""

    def __init__(self, name: str, item_type: str = "weapon", rarity: str = "common"):
        super().__init__(name=name, source=Source(abbreviation="TEST"))
        self.type = item_type
        self.rarity = rarity


class MockContent(BaseContent):
    """Generic mock content for testing."""

    def __init__(
        self, name: str, content_type: str = "unknown", source_abbr: str = "TEST"
    ):
        super().__init__(name=name, source=Source(abbreviation=source_abbr))
        self._content_type = content_type


class TestContentOrganizer:
    """Tests for ContentOrganizer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.organizer = ContentOrganizer(DocumentType.BOOK)

    def test_organizer_initialization(self) -> None:
        """Test organizer initialization."""
        assert self.organizer.document_type == DocumentType.BOOK
        assert "spell" in self.organizer._sorters
        assert "creature" in self.organizer._sorters
        assert "item" in self.organizer._sorters

    def test_sort_spells(self) -> None:
        """Test spell sorting by level, school, and name."""
        spells = [
            MockSpell("Fireball", level=3, school="evocation"),
            MockSpell("Magic Missile", level=1, school="evocation"),
            MockSpell("Charm Person", level=1, school="enchantment"),
            MockSpell("Lightning Bolt", level=3, school="evocation"),
            MockSpell("Cantrip", level=0, school="transmutation"),
        ]

        sorted_spells = self.organizer._sort_spells(spells)  # type: ignore[arg-type]

        # Should be sorted by level first
        assert (
            isinstance(sorted_spells[0], MockSpell) and sorted_spells[0].level == 0
        )  # Cantrips first
        assert isinstance(sorted_spells[1], MockSpell) and sorted_spells[1].level == 1
        assert isinstance(sorted_spells[2], MockSpell) and sorted_spells[2].level == 1
        assert isinstance(sorted_spells[3], MockSpell) and sorted_spells[3].level == 3
        assert isinstance(sorted_spells[4], MockSpell) and sorted_spells[4].level == 3

        # Within same level, should be sorted by school then name
        level_1_spells = [
            s for s in sorted_spells if isinstance(s, MockSpell) and s.level == 1
        ]
        assert (
            level_1_spells[0].school == "enchantment"
        )  # "enchantment" before "evocation"
        assert level_1_spells[1].school == "evocation"

    def test_sort_creatures(self) -> None:
        """Test creature sorting by challenge rating and name."""
        creatures = [
            MockCreature("Dragon", cr=15.0),
            MockCreature("Goblin", cr=0.25),
            MockCreature("Orc", cr=0.5),
            MockCreature("Troll", cr=5.0),
            MockCreature("Kobold", cr=0.125),
        ]

        sorted_creatures = self.organizer._sort_creatures(creatures)  # type: ignore[arg-type]

        # Should be sorted by CR ascending
        crs = [c.cr for c in sorted_creatures if isinstance(c, MockCreature)]
        assert crs == [0.125, 0.25, 0.5, 5.0, 15.0]

    def test_sort_creatures_string_cr(self) -> None:
        """Test creature sorting with string CR values."""
        creatures = [
            MockCreature("Strong", cr="2"),
            MockCreature("Weak", cr="1/4"),
            MockCreature("Medium", cr="1"),
            MockCreature("Very Weak", cr="1/8"),
        ]

        sorted_creatures = self.organizer._sort_creatures(creatures)  # type: ignore[arg-type]

        # Should handle string CRs correctly
        assert sorted_creatures[0].name == "Very Weak"  # 1/8 = 0.125
        assert sorted_creatures[1].name == "Weak"  # 1/4 = 0.25
        assert sorted_creatures[2].name == "Medium"  # 1 = 1.0
        assert sorted_creatures[3].name == "Strong"  # 2 = 2.0

    def test_sort_items(self) -> None:
        """Test item sorting by type, rarity, and name."""
        items = [
            MockItem("Sword +1", "weapon", "uncommon"),
            MockItem("Dagger", "weapon", "common"),
            MockItem("Ring of Protection", "ring", "rare"),
            MockItem("Potion of Healing", "potion", "common"),
            MockItem("Legendary Sword", "weapon", "legendary"),
        ]

        sorted_items = self.organizer._sort_items(items)  # type: ignore[arg-type]

        # Should group by type first
        types = [item.type for item in sorted_items if isinstance(item, MockItem)]
        # All items of same type should be grouped together
        potion_indices = [i for i, t in enumerate(types) if t == "potion"]
        [i for i, t in enumerate(types) if t == "ring"]
        [i for i, t in enumerate(types) if t == "weapon"]

        # Within each type group, indices should be consecutive
        if len(potion_indices) > 1:
            assert all(
                potion_indices[i] + 1 == potion_indices[i + 1]
                for i in range(len(potion_indices) - 1)
            )

    def test_sort_alphabetically(self) -> None:
        """Test alphabetical sorting."""
        content = [
            MockContent("Zebra"),
            MockContent("Apple"),
            MockContent("Banana"),
            MockContent("cherry"),  # lowercase to test case insensitivity
        ]

        sorted_content = self.organizer._sort_alphabetically(content)  # type: ignore[arg-type]
        names = [c.name for c in sorted_content]

        assert names == ["Apple", "Banana", "cherry", "Zebra"]

    def test_organize_content(self) -> None:
        """Test complete content organization."""
        content_items = [
            MockSpell("Fireball", level=3),
            MockCreature("Dragon", cr=15.0),
            MockItem("Sword", "weapon", "common"),
            MockSpell("Magic Missile", level=1),
            MockCreature("Goblin", cr=0.25),
        ]

        # Mock the ContentType.from_content method
        from unittest.mock import patch

        with patch(
            "dnd5e.renderers.latex.content_organizer.ContentType.from_content"
        ) as mock_from_content:

            def side_effect(content: Any) -> Any:
                if isinstance(content, MockSpell):
                    from dnd5e.core.models.content import ContentType  # type: ignore

                    return ContentType.SPELL
                elif isinstance(content, MockCreature):
                    from dnd5e.core.models.content import ContentType  # type: ignore

                    return ContentType.CREATURE
                elif isinstance(content, MockItem):
                    from dnd5e.core.models.content import ContentType  # type: ignore

                    return ContentType.ITEM
                else:
                    raise ValueError("Unknown type")

            mock_from_content.side_effect = side_effect

            organized = self.organizer.organize_content(content_items)

            assert "spell" in organized
            assert "creature" in organized
            assert "item" in organized

            # Check sorting within each group
            spells = organized["spell"]
            assert isinstance(spells[0], MockSpell)
            assert (
                spells[0].level == 1
            )  # Magic Missile (level 1) before Fireball (level 3)
            assert isinstance(spells[1], MockSpell)
            assert spells[1].level == 3

            creatures = organized["creature"]
            assert isinstance(creatures[0], MockCreature)
            assert creatures[0].cr == 0.25  # Goblin before Dragon
            assert isinstance(creatures[1], MockCreature)
            assert creatures[1].cr == 15.0

    def test_organize_by_source(self) -> None:
        """Test organization by source book."""
        content_items = [
            MockContent("Content 1", "spell", "PHB"),
            MockContent("Content 2", "creature", "PHB"),
            MockContent("Content 3", "spell", "MM"),
            MockContent("Content 4", "item", "DMG"),
        ]

        with patch(
            "dnd5e.renderers.latex.content_organizer.ContentType.from_content"
        ) as mock_from_content:

            def side_effect(content: Any) -> Any:
                from dnd5e.core.models.content import ContentType  # type: ignore

                return ContentType(content._content_type)

            mock_from_content.side_effect = side_effect

            organized = self.organizer.organize_by_source(content_items)  # type: ignore[arg-type]

            assert "PHB" in organized
            assert "MM" in organized
            assert "DMG" in organized

            assert "spell" in organized["PHB"]
            assert "creature" in organized["PHB"]
            assert "spell" in organized["MM"]
            assert "item" in organized["DMG"]

            assert len(organized["PHB"]["spell"]) == 1
            assert len(organized["PHB"]["creature"]) == 1

    def test_organize_by_level_spells(self) -> None:
        """Test organization by level for spells."""
        spells = [
            MockSpell("Cantrip", level=0),
            MockSpell("Level 1 Spell", level=1),
            MockSpell("Level 3 Spell", level=3),
            MockSpell("Level 9 Spell", level=9),
        ]

        organized = self.organizer.organize_by_level(spells)  # type: ignore[arg-type]

        assert "Cantrips" in organized
        assert "Level 1 Spells" in organized
        assert "Level 3 Spells" in organized
        assert "Level 9+ Spells" in organized

    def test_organize_by_level_creatures(self) -> None:
        """Test organization by level for creatures."""
        creatures = [
            MockCreature("Weak", cr=0.25),
            MockCreature("Low", cr=2.0),
            MockCreature("Medium", cr=8.0),
            MockCreature("High", cr=14.0),
            MockCreature("Epic", cr=20.0),
        ]

        organized = self.organizer.organize_by_level(creatures)  # type: ignore[arg-type]

        assert "CR 0-1/2" in organized
        assert "CR 1-4" in organized
        assert "CR 5-10" in organized
        assert "CR 11-16" in organized
        assert "CR 17+" in organized

    def test_get_level_key_unknown_content(self) -> None:
        """Test level key for unknown content types."""
        content: Any = MockContent("Unknown")
        level_key = self.organizer._get_level_key(content)
        assert level_key == "Miscellaneous"

    def test_create_hierarchical_sections(self) -> None:
        """Test creation of hierarchical sections."""
        organized_content = {
            "spell": [MockSpell("Fireball"), MockSpell("Magic Missile")],
            "creature": [MockCreature("Dragon")],
        }

        sections = self.organizer.create_hierarchical_sections(organized_content)  # type: ignore[arg-type]

        assert len(sections) == 2
        assert any(section.title == "Spells" for section in sections)
        assert any(section.title == "Creatures and NPCs" for section in sections)

        # Check that content items are assigned
        spell_section: Any = next(s for s in sections if "Spells" in s.title)
        assert len(spell_section.content_items) == 2

    def test_create_section_for_content_type_article(self) -> None:
        """Test section creation for article document type."""
        self.organizer.document_type = DocumentType.ARTICLE
        items = [MockSpell("Test Spell")]

        section = self.organizer._create_section_for_content_type("spell", items)  # type: ignore[arg-type]

        assert section.level == SectionLevel.SECTION  # Articles use sections
        assert section.title == "Spells"
        assert len(section.content_items) == 1

    def test_create_section_for_content_type_book(self) -> None:
        """Test section creation for book document type."""
        self.organizer.document_type = DocumentType.BOOK
        items = [MockSpell("Test Spell")]

        section = self.organizer._create_section_for_content_type("spell", items)  # type: ignore[arg-type]

        assert section.level == SectionLevel.CHAPTER  # Books use chapters
        assert section.title == "Spells"

    def test_create_spell_subsections(self) -> None:
        """Test creation of spell subsections by level."""
        spells = [
            MockSpell("Cantrip", level=0),
            MockSpell("Level 1 A", level=1),
            MockSpell("Level 1 B", level=1),
            MockSpell("Level 2", level=2),
        ]

        subsections = self.organizer._create_spell_subsections(spells)  # type: ignore[arg-type]

        # Should create subsections for each level
        level_titles = [sub.title for sub in subsections]
        assert "Cantrips" in level_titles
        assert "Level 1" in level_titles
        assert "Level 2" in level_titles

        # Check content distribution
        level_1_section: Any = next(s for s in subsections if s.title == "Level 1")
        assert len(level_1_section.content_items) == 2

    def test_create_creature_subsections(self) -> None:
        """Test creation of creature subsections by CR."""
        creatures = [
            MockCreature("Weak", cr=0.25),
            MockCreature("Low", cr=2.0),
            MockCreature("High", cr=12.0),
        ]

        subsections = self.organizer._create_creature_subsections(creatures)  # type: ignore[arg-type]

        # Should create subsections for CR ranges
        cr_titles = [sub.title for sub in subsections]
        assert "CR 0-1/2" in cr_titles
        assert "CR 1-4" in cr_titles
        assert "CR 11-16" in cr_titles

    def test_create_item_subsections(self) -> None:
        """Test creation of item subsections by type."""
        items = [
            MockItem("Sword", "weapon"),
            MockItem("Shield", "armor"),
            MockItem("Potion", "potion"),
            MockItem("Dagger", "weapon"),
        ]

        subsections = self.organizer._create_item_subsections(items)  # type: ignore[arg-type]

        # Should create subsections for each item type
        type_titles = [sub.title for sub in subsections]
        assert "weapon" in type_titles
        assert "armor" in type_titles
        assert "potion" in type_titles

        # Check content distribution
        weapon_section: Any = next(s for s in subsections if s.title == "weapon")
        assert len(weapon_section.content_items) == 2

    def test_format_content_type_title(self) -> None:
        """Test content type title formatting."""
        assert self.organizer._format_content_type_title("spell") == "Spells"
        assert (
            self.organizer._format_content_type_title("creature")
            == "Creatures and NPCs"
        )
        assert (
            self.organizer._format_content_type_title("item")
            == "Magic Items and Equipment"
        )
        assert (
            self.organizer._format_content_type_title("unknown") == "Additional Content"
        )
        assert self.organizer._format_content_type_title("custom_type") == "Custom Type"

    def test_create_table_of_contents_data(self) -> None:
        """Test creation of table of contents data."""
        from dnd5e.core.models.document_metadata import (  # type: ignore
            ContentSection,
            SectionLevel,
        )

        sections = [
            ContentSection(
                title="Chapter 1",
                level=SectionLevel.CHAPTER,
                numbered=True,
                label="ch:1",
            ),
            ContentSection(
                title="Chapter 2",
                level=SectionLevel.CHAPTER,
                numbered=True,
                label="ch:2",
            ),
        ]

        # Add a subsection to the first chapter
        subsection: Any = ContentSection(
            title="Section 1.1",
            level=SectionLevel.SECTION,
            numbered=True,
            label="sec:1-1",
        )
        sections[0].subsections.append(subsection)

        toc_data = self.organizer.create_table_of_contents_data(sections)

        assert len(toc_data) == 3  # 2 chapters + 1 subsection

        # Check structure
        assert toc_data[0]["title"] == "Chapter 1"
        assert toc_data[0]["level"] == 1
        assert toc_data[0]["label"] == "ch:1"

        assert toc_data[1]["title"] == "Section 1.1"
        assert toc_data[1]["level"] == 2  # Subsection should be level 2

        assert toc_data[2]["title"] == "Chapter 2"
        assert toc_data[2]["level"] == 1


class TestContentOrganizerIntegration:
    """Integration tests for content organizer."""

    def test_organize_mixed_content_for_book(self) -> None:
        """Test organizing mixed content for book document."""
        organizer: Any = ContentOrganizer(DocumentType.BOOK)

        content_items = [
            MockSpell("Fireball", level=3),
            MockSpell("Magic Missile", level=1),
            MockCreature("Dragon", cr=15.0),
            MockCreature("Goblin", cr=0.25),
            MockItem("Sword +1", "weapon", "uncommon"),
            MockContent("Custom Feature", "feat"),
        ]

        with patch(
            "dnd5e.renderers.latex.content_organizer.ContentType.from_content"
        ) as mock_from_content:

            def side_effect(content: Any) -> Any:
                from dnd5e.core.models.content import ContentType  # type: ignore

                if isinstance(content, MockSpell):
                    return ContentType.SPELL
                elif isinstance(content, MockCreature):
                    return ContentType.CREATURE
                elif isinstance(content, MockItem):
                    return ContentType.ITEM
                else:
                    return ContentType.FEAT

            mock_from_content.side_effect = side_effect

            organized = organizer.organize_content(content_items)
            sections = organizer.create_hierarchical_sections(organized)

            # Should have sections for each content type
            section_titles = [section.title for section in sections]
            assert "Spells" in section_titles
            assert "Creatures and NPCs" in section_titles
            assert "Magic Items and Equipment" in section_titles
            assert "Feats" in section_titles

            # Check content is properly sorted and assigned
            spell_section: Any = next(s for s in sections if "Spells" in s.title)
            spell_names = [item.name for item in spell_section.content_items]
            assert spell_names == [
                "Magic Missile",
                "Fireball",
            ]  # Level 1 before level 3

    def test_organize_large_spell_collection(self) -> None:
        """Test organizing large spell collection with subsections."""
        organizer: Any = ContentOrganizer(DocumentType.SUPPLEMENT)

        # Create 15 spells to trigger subsection creation
        spells = (
            [MockSpell(f"Cantrip {i}", level=0) for i in range(3)]
            + [MockSpell(f"Level 1 Spell {i}", level=1) for i in range(4)]
            + [MockSpell(f"Level 2 Spell {i}", level=2) for i in range(3)]
            + [MockSpell(f"Level 3 Spell {i}", level=3) for i in range(5)]
        )

        with patch(
            "dnd5e.renderers.latex.content_organizer.ContentType.from_content"
        ) as mock_from_content:
            from dnd5e.core.models.content import ContentType  # type: ignore

            mock_from_content.return_value = ContentType.SPELL

            organized = organizer.organize_content(spells)
            sections = organizer.create_hierarchical_sections(organized)

            # Should have one spell section
            spell_section = sections[0]
            assert "Spells" in spell_section.title

            # Should have subsections for different spell levels
            assert len(spell_section.subsections) > 0
            subsection_titles = [sub.title for sub in spell_section.subsections]
            assert "Cantrips" in subsection_titles
            assert "Level 1" in subsection_titles
            assert "Level 2" in subsection_titles
            assert "Level 3" in subsection_titles
