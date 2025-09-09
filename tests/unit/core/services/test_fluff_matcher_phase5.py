"""Tests for Phase 5 FluffMatcher enhancements."""

from unittest.mock import MagicMock, Mock

import pytest

from studiorum.core.models.content import Source
from studiorum.core.models.creatures import Creature
from studiorum.core.models.fluff import CreatureFluff, FluffEntry, FluffImage
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.core.services.fluff_matcher import FluffMatcher


@pytest.fixture
def mock_omnidexer():
    """Create a mock omnidexer."""
    omnidexer = Mock()
    return omnidexer


@pytest.fixture
def sample_creature():
    """Create a sample creature for testing."""
    source = Source(abbreviation="MM", full_name="Monster Manual")
    return Creature(
        name="Ancient Red Dragon",
        source=source,
        cr="24",
        type={"type": "dragon"},
        size=["Gargantuan"],
        alignment=["chaotic", "evil"],
        ac=[{"ac": 22}],
        hp={"average": 546, "formula": "28d20 + 252"},
        speed={"walk": 40, "climb": 40, "fly": 80},
        str=30,
        dex=10,
        con=29,
        int=18,
        wis=15,
        cha=23,
    )


@pytest.fixture
def sample_creature_fluff():
    """Create sample creature fluff with multiple sections."""
    source = Source(abbreviation="MM", full_name="Monster Manual")

    # Create entries with different names/types for section filtering
    # Use dict format since BaseFluff.parse_entries expects dicts, not FluffEntry objects
    entries = [
        {"name": "Lair Actions", "content": "Lair description here"},
        {"name": "Regional Effects", "content": "Regional effects description"},
        {"type": "tactics", "content": "Tactical information"},
        {"name": "Description", "content": "General description"},
        {"content": "Untagged lore content"},
    ]

    # Create sample images
    # Use dict format since BaseFluff.parse_images expects dicts, not FluffImage objects
    images = [
        {"type": "image", "href": {"path": "dragon/ancient-red.jpg"}, "credit": "WotC"},
        {"type": "image", "href": {"path": "dragon/lair-map.png"}},
    ]

    return CreatureFluff(
        name="Ancient Red Dragon", source=source, entries=entries, images=images
    )


class TestFluffMatcherPhase5:
    """Test Phase 5 enhancements to FluffMatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    def test_section_filtering(
        self, mock_omnidexer, sample_creature, sample_creature_fluff
    ):
        """Test filtering fluff by specific sections."""
        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [sample_creature_fluff]

        # Test filtering to only lair-related sections
        result = matcher.match_creature_fluff(
            sample_creature, allowed_sections=["lair", "regional"]
        )

        assert result is not None
        assert (
            len(result.entries) == 2
        )  # Should only include Lair Actions and Regional Effects
        assert any(
            "lair" in entry.name.lower() for entry in result.entries if entry.name
        )
        assert any(
            "regional" in entry.name.lower() for entry in result.entries if entry.name
        )

    def test_source_filtering(self, mock_omnidexer, sample_creature):
        """Test filtering fluff by source."""
        matcher = FluffMatcher(mock_omnidexer)

        # Create fluff from different sources
        mm_source = Source(abbreviation="MM", full_name="Monster Manual")
        vgm_source = Source(abbreviation="VGM", full_name="Volo's Guide")

        mm_fluff = CreatureFluff(
            name="Ancient Red Dragon",
            source=mm_source,
            entries=[FluffEntry(content="MM content")],
        )

        vgm_fluff = CreatureFluff(
            name="Ancient Red Dragon",
            source=vgm_source,
            entries=[FluffEntry(content="VGM content")],
        )

        mock_omnidexer.get_all_by_type.return_value = [mm_fluff, vgm_fluff]

        # Test filtering to only MM sources
        result = matcher.match_creature_fluff(sample_creature, allowed_sources=["MM"])

        assert result is not None
        assert result.source.abbreviation == "MM"

    def test_combined_filtering(
        self, mock_omnidexer, sample_creature, sample_creature_fluff
    ):
        """Test combining section and source filtering."""
        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [sample_creature_fluff]

        # Test filtering both by section and source
        result = matcher.match_creature_fluff(
            sample_creature, allowed_sections=["lair"], allowed_sources=["MM"]
        )

        assert result is not None
        assert result.source.abbreviation == "MM"
        assert len(result.entries) == 1  # Should only include Lair Actions
        assert "lair" in result.entries[0].name.lower()

    def test_get_fluff_sections(self, mock_omnidexer, sample_creature_fluff):
        """Test extracting available section names."""
        matcher = FluffMatcher(mock_omnidexer)

        sections = matcher.get_fluff_sections(sample_creature_fluff)

        expected_sections = [
            "description",
            "lair actions",
            "regional effects",
            "tactics",
        ]
        assert all(section in sections for section in expected_sections)

    def test_extract_fluff_images(self, mock_omnidexer, sample_creature_fluff):
        """Test extracting images from fluff content."""
        matcher = FluffMatcher(mock_omnidexer)

        images = matcher.extract_fluff_images(sample_creature_fluff)

        assert len(images) == 2
        assert images[0]["path"] == "dragon/ancient-red.jpg"
        assert images[0]["credit"] == "WotC"
        assert images[1]["path"] == "dragon/lair-map.png"
        assert all(img["source_fluff"] == "Ancient Red Dragon" for img in images)
        assert all(img["source_abbreviation"] == "MM" for img in images)

    def test_empty_section_filter_returns_all(
        self, mock_omnidexer, sample_creature, sample_creature_fluff
    ):
        """Test that empty section filter returns all content."""
        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [sample_creature_fluff]

        result = matcher.match_creature_fluff(sample_creature, allowed_sections=[])

        assert result is not None
        assert len(result.entries) == len(
            sample_creature_fluff.entries
        )  # All entries included

    def test_no_matching_sections_returns_empty(
        self, mock_omnidexer, sample_creature, sample_creature_fluff
    ):
        """Test that non-matching section filter returns empty content."""
        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [sample_creature_fluff]

        result = matcher.match_creature_fluff(
            sample_creature, allowed_sections=["nonexistent_section"]
        )

        assert result is not None
        assert len(result.entries) == 0  # No matching entries

    def test_spell_fluff_filtering(self, mock_omnidexer):
        """Test section filtering works for spell fluff."""
        from studiorum.core.models.fluff import SpellFluff

        spell = Spell(
            name="Fireball",
            source=Source(abbreviation="PHB", full_name="Player's Handbook"),
            level=3,
            school="evocation",
            time=[{"number": 1, "unit": "action"}],
            range={"type": "point", "distance": {"type": "feet", "amount": 150}},
            components={
                "verbal": True,
                "somatic": True,
                "material": "a tiny ball of bat guano and sulfur",
            },
            duration=[{"type": "instant"}],
            entries=["A bright streak flashes from your pointing finger..."],
        )

        spell_fluff = SpellFluff(
            name="Fireball",
            source=Source(abbreviation="PHB", full_name="Player's Handbook"),
            entries=[
                {"name": "History", "content": "Historical information"},
                {"name": "Variants", "content": "Spell variants"},
                {"content": "General lore"},
            ],
        )

        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [spell_fluff]

        result = matcher.match_spell_fluff(spell, allowed_sections=["history"])

        assert result is not None
        assert len(result.entries) == 1
        assert (
            result.entries[0].name is not None
            and "history" in result.entries[0].name.lower()
        )

    def test_item_fluff_filtering(self, mock_omnidexer):
        """Test section filtering works for item fluff."""
        from studiorum.core.models.fluff import ItemFluff

        item = Item(
            name="Sword of Kas",
            source=Source(abbreviation="DMG", full_name="Dungeon Master's Guide"),
            rarity="artifact",
        )

        item_fluff = ItemFluff(
            name="Sword of Kas",
            source=Source(abbreviation="DMG", full_name="Dungeon Master's Guide"),
            entries=[
                {"name": "Lore", "content": "Legendary sword lore"},
                {"name": "Properties", "content": "Special properties"},
                {"content": "General description"},
            ],
        )

        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [item_fluff]

        result = matcher.match_item_fluff(item, allowed_sections=["lore"])

        assert result is not None
        assert len(result.entries) == 1
        assert (
            result.entries[0].name is not None
            and "lore" in result.entries[0].name.lower()
        )

    def test_backward_compatibility(
        self, mock_omnidexer, sample_creature, sample_creature_fluff
    ):
        """Test that existing code without Phase 5 features still works."""
        matcher = FluffMatcher(mock_omnidexer)
        mock_omnidexer.get_all_by_type.return_value = [sample_creature_fluff]

        # Call without any Phase 5 parameters
        result = matcher.match_creature_fluff(sample_creature)

        assert result is not None
        assert len(result.entries) == len(
            sample_creature_fluff.entries
        )  # All entries included
        assert result.source.abbreviation == "MM"
