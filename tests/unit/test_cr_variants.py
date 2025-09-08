"""Tests for Challenge Rating variants with XP values (xpLair, xpCoven, etc.)."""

import pytest

from studiorum.core.models.creatures import Creature


def create_test_creature(**kwargs):
    """Create a test creature with minimal required fields."""
    defaults = {
        "name": "Test Creature",
        "source": {"abbreviation": "TEST"},
        "size": ["Medium"],
        "type": "humanoid",
        "ac": [10],
        "hp": {"average": 10, "formula": "2d8+1"},
        "speed": {"walk": 30},
        "str": 10,
        "dex": 10,
        "con": 10,
        "int": 10,
        "wis": 10,
        "cha": 10,
    }
    defaults.update(kwargs)
    return Creature(**defaults)


class TestChallengeRatingVariants:
    """Test Challenge Rating display with all variant formats."""

    def test_simple_cr_string(self):
        """Test simple CR string format."""
        creature = create_test_creature(cr="5")
        assert creature.get_enhanced_cr_text() == "5 (1,800 XP)"

    def test_cr_with_fraction(self):
        """Test fractional CR values."""
        creature = create_test_creature(cr="1/4")
        assert creature.get_enhanced_cr_text() == "1/4 (50 XP)"

    def test_cr_dict_basic(self):
        """Test CR dictionary with just base CR."""
        creature = create_test_creature(cr={"cr": "10"})
        assert creature.get_enhanced_cr_text() == "10 (5,900 XP)"

    def test_cr_with_xp_override(self):
        """Test CR with custom XP override."""
        creature = create_test_creature(cr={"cr": "10", "xp": 6000})
        assert creature.get_enhanced_cr_text() == "10 (6,000 XP)"

    def test_cr_with_xp_lair(self):
        """Test CR with xpLair variant (Ancient Red Dragon case)."""
        creature = create_test_creature(
            name="Ancient Red Dragon", cr={"cr": "24", "xpLair": 75000}
        )
        expected = "24 (62,000 XP) or 24 (75,000 XP) when encountered in lair"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_with_lair_different_cr(self):
        """Test CR with different lair CR value."""
        creature = create_test_creature(cr={"cr": "10", "lair": "12", "xpLair": 8400})
        expected = "10 (5,900 XP) or 12 (8,400 XP) when encountered in lair"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_with_coven(self):
        """Test CR with coven variant (Green Hag case)."""
        creature = create_test_creature(name="Green Hag", cr={"cr": "3", "coven": "5"})
        expected = "3 (700 XP) or 5 (1,800 XP) when part of a coven"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_with_coven_and_xp(self):
        """Test CR with coven and custom XP values."""
        creature = create_test_creature(cr={"cr": "6", "coven": "8", "xpCoven": 4000})
        expected = "6 (2,300 XP) or 8 (4,000 XP) when part of a coven"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_with_all_variants(self):
        """Test CR with both lair and coven variants."""
        creature = create_test_creature(
            cr={
                "cr": "10",
                "xp": 6000,
                "lair": "12",
                "xpLair": 9000,
                "coven": "13",
                "xpCoven": 11000,
            }
        )
        expected = "10 (6,000 XP) or 12 (9,000 XP) when encountered in lair or 13 (11,000 XP) when part of a coven"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_with_special_override(self):
        """Test CR with special text override."""
        creature = create_test_creature(cr={"cr": "10", "special": "Varies (see text)"})
        assert creature.get_enhanced_cr_text() == "Varies (see text)"

    def test_cr_none(self):
        """Test creature with no CR."""
        creature = create_test_creature(cr=None)
        assert creature.get_enhanced_cr_text() == "0 (10 XP)"

    def test_cr_zero(self):
        """Test CR of 0."""
        creature = create_test_creature(cr="0")
        assert creature.get_enhanced_cr_text() == "0 (10 XP)"

    def test_cr_unknown_value(self):
        """Test CR with unknown value."""
        creature = create_test_creature(cr="99")
        assert creature.get_enhanced_cr_text() == "99 (XP varies)"

    def test_cr_only_xp_lair_no_base(self):
        """Test CR with only xpLair and no lair CR (uses base CR)."""
        creature = create_test_creature(cr={"cr": "20", "xpLair": 30000})
        expected = "20 (25,000 XP) or 20 (30,000 XP) when encountered in lair"
        assert creature.get_enhanced_cr_text() == expected

    def test_cr_empty_dict(self):
        """Test CR with empty dictionary."""
        creature = create_test_creature(cr={})
        assert creature.get_enhanced_cr_text() == "0 (10 XP)"

    def test_get_cr_text_compatibility(self):
        """Test that get_cr_text() still works for backward compatibility."""
        creature = create_test_creature(cr={"cr": "10", "xpLair": 7000})
        # get_cr_text should return just the CR value
        assert creature.get_cr_text() == "10"


class TestRealWorldExamples:
    """Test with real 5etools data examples."""

    def test_ancient_red_dragon_xmm(self):
        """Test Ancient Red Dragon from XMM with xpLair."""
        creature = create_test_creature(
            name="Ancient Red Dragon",
            source={"abbreviation": "XMM"},
            cr={"cr": "24", "xpLair": 75000},
        )
        expected = "24 (62,000 XP) or 24 (75,000 XP) when encountered in lair"
        assert creature.get_enhanced_cr_text() == expected

    def test_ancient_gold_dragon_xmm(self):
        """Test Ancient Gold Dragon from XMM with xpLair."""
        creature = create_test_creature(
            name="Ancient Gold Dragon",
            source={"abbreviation": "XMM"},
            cr={"cr": "24", "xpLair": 75000},
        )
        expected = "24 (62,000 XP) or 24 (75,000 XP) when encountered in lair"
        assert creature.get_enhanced_cr_text() == expected

    def test_green_hag_mm(self):
        """Test Green Hag from MM with coven."""
        creature = create_test_creature(
            name="Green Hag",
            source={"abbreviation": "MM"},
            cr={"cr": "3", "coven": "5"},
        )
        expected = "3 (700 XP) or 5 (1,800 XP) when part of a coven"
        assert creature.get_enhanced_cr_text() == expected

    def test_annis_hag_mpmm(self):
        """Test Annis Hag from MPMM with coven."""
        creature = create_test_creature(
            name="Annis Hag",
            source={"abbreviation": "MPMM"},
            cr={"cr": "6", "coven": "8"},
        )
        expected = "6 (2,300 XP) or 8 (3,900 XP) when part of a coven"
        assert creature.get_enhanced_cr_text() == expected
