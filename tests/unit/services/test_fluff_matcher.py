"""Tests for FluffMatcher service."""

from unittest.mock import Mock

import pytest

from studiorum.core.models.content import Source
from studiorum.core.models.creatures import Creature
from studiorum.core.models.fluff import CreatureFluff, ItemFluff, SpellFluff
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.core.services.fluff_matcher import FluffMatcher
from tests.test_helpers import reset_test_environment


class TestFluffMatcher:
    """Test FluffMatcher service functionality."""

    def setup_method(self) -> None:
        """Set up test environment for each test."""
        reset_test_environment()
        self.mock_omnidexer = Mock()
        self.matcher = FluffMatcher(self.mock_omnidexer)

    def test_initialization(self) -> None:
        """Test FluffMatcher initializes correctly."""
        assert self.matcher.omnidexer is self.mock_omnidexer
        assert isinstance(self.matcher._copy_cache, dict)
        assert len(self.matcher._copy_cache) == 0

    def test_normalize_name(self) -> None:
        """Test name normalization functionality."""
        test_cases = [
            ("Ancient Red Dragon", "ancient red dragon"),
            ("  Spaced   Out  ", "spaced out"),
            ("'Apostrophe's' Name", "apostrophes name"),
            ('"Quoted" Name', "quoted name"),
            ("The Ancient One", "the ancient one"),
        ]

        for input_name, expected in test_cases:
            assert self.matcher._normalize_name(input_name) == expected

    def test_generate_name_variations(self) -> None:
        """Test name variation generation."""
        # Test "the" prefix handling
        variations = self.matcher._generate_name_variations("ancient dragon")
        assert "ancient dragon" in variations
        assert "the ancient dragon" in variations

        variations = self.matcher._generate_name_variations("the ancient dragon")
        assert "ancient dragon" in variations
        assert "the ancient dragon" in variations

        # Test plural handling
        variations = self.matcher._generate_name_variations("dragons")
        assert "dragons" in variations
        assert "dragon" in variations

        variations = self.matcher._generate_name_variations("dragon")
        assert "dragon" in variations
        assert "dragons" in variations

        # Test "ies" -> "y" pattern
        variations = self.matcher._generate_name_variations("pixies")
        assert "pixies" in variations
        assert "pixie" in variations
        assert "pixy" in variations

        # Test "y" -> "ies" pattern
        variations = self.matcher._generate_name_variations("pixie")
        assert "pixie" in variations
        assert "pixies" in variations

        # Test abbreviation expansions
        variations = self.matcher._generate_name_variations("dr evil")
        assert "dr evil" in variations
        assert "doctor evil" in variations

    def test_exact_match(self) -> None:
        """Test exact name and source matching."""
        # Create test data
        creature = Creature(
            name="Ancient Red Dragon",
            source=Source(abbreviation="MM", name="Monster Manual"),
            size=["H"],
            type="dragon",
            alignment=["CE"],
            ac=[{"ac": 22}],
            hp={"average": 546, "formula": "28d20+252"},
            speed={"walk": 40, "climb": 40, "fly": 80},
            str=30,
            dex=14,
            con=29,
            int=18,
            wis=15,
            cha=23,
            cr="24",
        )

        fluff_entries = [
            CreatureFluff(
                name="Ancient Red Dragon",
                source=Source(abbreviation="MM", name="Monster Manual"),
            ),
            CreatureFluff(
                name="Ancient Red Dragon",
                source=Source(abbreviation="CUSTOM", name="Custom Source"),
            ),
            CreatureFluff(
                name="Different Dragon",
                source=Source(abbreviation="MM", name="Monster Manual"),
            ),
        ]

        match = self.matcher._find_exact_match(creature, fluff_entries)
        assert match is not None
        assert match.name == "Ancient Red Dragon"
        assert match.source.abbreviation == "MM"

    def test_name_only_match_prefers_same_source(self) -> None:
        """Test name-only matching with source preference."""
        creature = Creature(
            name="Dragon",
            source=Source(abbreviation="MM", name="Monster Manual"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        fluff_entries = [
            CreatureFluff(
                name="Dragon",
                source=Source(abbreviation="CUSTOM", name="Custom Source"),
            ),
            CreatureFluff(
                name="Dragon", source=Source(abbreviation="MM", name="Monster Manual")
            ),
        ]

        match = self.matcher._find_name_only_match(creature, fluff_entries)
        assert match is not None
        assert match.name == "Dragon"
        assert match.source.abbreviation == "MM"  # Prefers same source

    def test_fuzzy_match(self) -> None:
        """Test fuzzy matching with name variations."""
        creature = Creature(
            name="Ancient Dragon",
            source=Source(abbreviation="MM", name="Monster Manual"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        fluff_entries = [
            CreatureFluff(
                name="The Ancient Dragon",  # "The" prefix variation
                source=Source(abbreviation="MM", name="Monster Manual"),
            )
        ]

        match = self.matcher._find_fuzzy_match(creature, fluff_entries)
        assert match is not None
        assert match.name == "The Ancient Dragon"
        assert match.source.abbreviation == "MM"

    def test_match_creature_fluff_with_provided_entries(self) -> None:
        """Test creature fluff matching with provided entries."""
        creature = Creature(
            name="Test Dragon",
            source=Source(abbreviation="TEST", name="Test Source"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        fluff_entries = [
            CreatureFluff(
                name="Test Dragon",
                source=Source(abbreviation="TEST", name="Test Source"),
            )
        ]

        match = self.matcher.match_creature_fluff(creature, fluff_entries)
        assert match is not None
        assert match.name == "Test Dragon"
        assert match.source.abbreviation == "TEST"

    def test_match_creature_fluff_with_omnidexer(self) -> None:
        """Test creature fluff matching using omnidexer."""
        creature = Creature(
            name="Test Dragon",
            source=Source(abbreviation="TEST", name="Test Source"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        fluff_entry = CreatureFluff(
            name="Test Dragon", source=Source(abbreviation="TEST", name="Test Source")
        )

        # Mock omnidexer to return our test data
        self.mock_omnidexer.get_all_by_type.return_value = [fluff_entry]

        match = self.matcher.match_creature_fluff(creature)
        assert match is not None
        assert match.name == "Test Dragon"
        self.mock_omnidexer.get_all_by_type.assert_called_once_with("creatureFluff")

    def test_match_spell_fluff(self) -> None:
        """Test spell fluff matching."""
        spell = Spell(
            name="Fireball",
            source=Source(abbreviation="PHB", name="Player's Handbook"),
            level=3,
            school="evocation",
            time=[{"number": 1, "unit": "action"}],
            range={"type": "point", "distance": {"type": "feet", "amount": 150}},
            components={"v": True, "s": True, "m": "a tiny ball of bat guano"},
            duration=[{"type": "instant"}],
            entries=["A bright streak..."],
        )

        fluff_entries = [
            SpellFluff(
                name="Fireball",
                source=Source(abbreviation="PHB", name="Player's Handbook"),
            )
        ]

        match = self.matcher.match_spell_fluff(spell, fluff_entries)
        assert match is not None
        assert match.name == "Fireball"
        assert match.source.abbreviation == "PHB"

    def test_match_item_fluff(self) -> None:
        """Test item fluff matching."""
        item = Item(
            name="Sword of Sharpness",
            source=Source(abbreviation="DMG", name="Dungeon Master's Guide"),
            type="weapon",
            rarity="very rare",
            reqAttune=True,
            entries=["This magic sword..."],
        )

        fluff_entries = [
            ItemFluff(
                name="Sword of Sharpness",
                source=Source(abbreviation="DMG", name="Dungeon Master's Guide"),
            )
        ]

        match = self.matcher.match_item_fluff(item, fluff_entries)
        assert match is not None
        assert match.name == "Sword of Sharpness"
        assert match.source.abbreviation == "DMG"

    def test_no_match_returns_none(self) -> None:
        """Test that no match returns None."""
        creature = Creature(
            name="Nonexistent Dragon",
            source=Source(abbreviation="TEST", name="Test Source"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        fluff_entries = [
            CreatureFluff(
                name="Different Dragon",
                source=Source(abbreviation="TEST", name="Test Source"),
            )
        ]

        match = self.matcher.match_creature_fluff(creature, fluff_entries)
        assert match is None

    def test_empty_fluff_entries_returns_none(self) -> None:
        """Test that empty fluff entries returns None."""
        creature = Creature(
            name="Test Dragon",
            source=Source(abbreviation="TEST", name="Test Source"),
            size=["L"],
            type="dragon",
            alignment=["N"],
            ac=[{"ac": 15}],
            hp={"average": 100, "formula": "10d10+50"},
            speed={"walk": 30},
            str=20,
            dex=12,
            con=20,
            int=10,
            wis=12,
            cha=10,
            cr="5",
        )

        match = self.matcher.match_creature_fluff(creature, [])
        assert match is None
