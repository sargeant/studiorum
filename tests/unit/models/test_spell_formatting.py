"""Tests for enhanced Spell model formatting methods."""

from typing import Any
from unittest.mock import Mock

import pytest

from dnd5e.core.models.content import Source
from dnd5e.core.models.spells import (
    Spell,
    SpellComponent,
    SpellDuration,
    SpellRange,
    SpellTime,
)


class TestSpellFormattingMethods:
    """Test enhanced formatting methods on Spell model."""

    @pytest.fixture
    def sample_spell_data(self) -> dict[str, Any]:
        """Sample spell data for testing."""
        return {
            "name": "Fireball",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241},
            "level": 3,
            "school": "V",  # Evocation
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
            "components": {
                "v": True,
                "s": True,
                "m": {"text": "a tiny ball of bat guano and sulfur"},
            },
            "duration": [{"type": "instant"}],
            "entries": [
                "A bright streak flashes from your pointing finger to a point you choose.",
                "Each creature in a 20-foot-radius sphere centered on that point must make a Dexterity saving throw.",
            ],
            "entriesHigherLevel": [
                {
                    "type": "entries",
                    "name": "At Higher Levels",
                    "entries": [
                        "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
                    ],
                }
            ],
            "damageInflict": ["fire"],
            "savingThrow": ["dexterity"],
            "areaTags": ["S"],  # Sphere
        }

    @pytest.fixture
    def cantrip_data(self) -> dict[str, Any]:
        """Sample cantrip data for testing."""
        return {
            "name": "Eldritch Blast",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 237},
            "level": 0,
            "school": "V",  # Evocation
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 120}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            "entries": [
                "A beam of crackling energy streaks toward a creature within range."
            ],
            "damageInflict": ["force"],
            "spellAttack": ["ranged"],
        }

    @pytest.fixture
    def concentration_spell_data(self) -> dict[str, Any]:
        """Sample concentration spell data."""
        return {
            "name": "Hold Person",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 251},
            "level": 2,
            "school": "E",  # Enchantment
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 60}},
            "components": {
                "v": True,
                "s": True,
                "m": {"text": "a small, straight piece of iron"},
            },
            "duration": [
                {
                    "type": "timed",
                    "duration": {"type": "minute", "amount": 1},
                    "concentration": True,
                }
            ],
            "entries": ["Choose a humanoid that you can see within range."],
            "conditionInflict": ["paralyzed"],
            "savingThrow": ["wisdom"],
        }

    def test_get_spell_attack_text(
        self, sample_spell_data: dict[str, Any], cantrip_data: dict[str, Any]
    ) -> None:
        """Test spell attack text formatting."""
        # Test spell with saving throw
        fireball = Spell.model_validate(sample_spell_data)
        assert fireball.get_spell_attack_text() == "Dexterity saving throw"

        # Test spell with spell attack
        eldritch_blast = Spell.model_validate(cantrip_data)
        assert eldritch_blast.get_spell_attack_text() == "ranged spell attack"

        # Test spell with no attack or save
        spell_no_attack = Spell.model_validate(
            {**sample_spell_data, "savingThrow": None, "spellAttack": None}
        )
        assert spell_no_attack.get_spell_attack_text() == ""

    def test_get_damage_text(self, sample_spell_data: dict[str, Any]) -> None:
        """Test damage type text formatting."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.get_damage_text() == "fire"

        # Test multiple damage types
        multi_damage_data = {**sample_spell_data, "damageInflict": ["fire", "radiant"]}
        multi_spell = Spell.model_validate(multi_damage_data)
        assert multi_spell.get_damage_text() == "fire, radiant"

        # Test no damage
        no_damage_data = {**sample_spell_data, "damageInflict": None}
        no_damage_spell = Spell.model_validate(no_damage_data)
        assert no_damage_spell.get_damage_text() == ""

    def test_get_condition_text(self, concentration_spell_data: dict[str, Any]) -> None:
        """Test condition inflicted text formatting."""
        spell = Spell.model_validate(concentration_spell_data)
        assert spell.get_condition_text() == "paralyzed"

        # Test multiple conditions
        multi_condition_data = {
            **concentration_spell_data,
            "conditionInflict": ["paralyzed", "stunned"],
        }
        multi_spell = Spell.model_validate(multi_condition_data)
        assert multi_spell.get_condition_text() == "paralyzed, stunned"

    def test_get_area_text(self, sample_spell_data: dict[str, Any]) -> None:
        """Test area of effect text formatting."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.get_area_text() == "Sphere"

        # Test multiple area types
        multi_area_data = {**sample_spell_data, "areaTags": ["S", "C"]}  # Sphere, Cone
        multi_spell = Spell.model_validate(multi_area_data)
        assert multi_spell.get_area_text() == "Sphere, Cone"

    def test_get_enhanced_level_text(
        self, sample_spell_data: dict[str, Any], cantrip_data: dict[str, Any]
    ) -> None:
        """Test enhanced level text with school and additional info."""
        # Regular spell
        fireball = Spell.model_validate(sample_spell_data)
        expected = "3rd-level evocation (fire damage, Dexterity saving throw)"
        assert fireball.get_enhanced_level_text() == expected

        # Cantrip
        cantrip = Spell.model_validate(cantrip_data)
        expected_cantrip = "Evocation cantrip (force damage, ranged spell attack)"
        assert cantrip.get_enhanced_level_text() == expected_cantrip

    def test_get_enhanced_components_text(
        self, sample_spell_data: dict[str, Any]
    ) -> None:
        """Test enhanced components text with material component descriptions."""
        spell = Spell.model_validate(sample_spell_data)
        expected = "V, S, M (a tiny ball of bat guano and sulfur)"
        assert spell.get_enhanced_components_text() == expected

        # Test without material components
        no_material_data = {**sample_spell_data, "components": {"v": True, "s": True}}
        no_material_spell = Spell.model_validate(no_material_data)
        assert no_material_spell.get_enhanced_components_text() == "V, S"

        # Test only verbal
        verbal_only_data = {**sample_spell_data, "components": {"v": True}}
        verbal_spell = Spell.model_validate(verbal_only_data)
        assert verbal_spell.get_enhanced_components_text() == "V"

    def test_get_enhanced_duration_text(
        self, concentration_spell_data: dict[str, Any]
    ) -> None:
        """Test enhanced duration text with concentration indicator."""
        spell = Spell.model_validate(concentration_spell_data)
        expected = "Concentration, up to 1 minute"
        assert spell.get_enhanced_duration_text() == expected

        # Test instantaneous
        instant_data = {**concentration_spell_data, "duration": [{"type": "instant"}]}
        instant_spell = Spell.model_validate(instant_data)
        assert instant_spell.get_enhanced_duration_text() == "Instantaneous"

    def test_get_higher_level_scaling_text(
        self, sample_spell_data: dict[str, Any]
    ) -> None:
        """Test higher level scaling text extraction."""
        spell = Spell.model_validate(sample_spell_data)
        expected = "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
        assert spell.get_higher_level_scaling_text() == expected

        # Test spell without higher level scaling
        no_scaling_data = {**sample_spell_data, "entriesHigherLevel": None}
        no_scaling_spell = Spell.model_validate(no_scaling_data)
        assert no_scaling_spell.get_higher_level_scaling_text() == ""

    def test_get_spell_list_classes(self, sample_spell_data: dict[str, Any]) -> None:
        """Test spell list class formatting."""
        # Add spell list data
        spell_data_with_classes = {
            **sample_spell_data,
            "classes": {
                "fromClassList": [
                    {"name": "Sorcerer", "source": "PHB"},
                    {"name": "Wizard", "source": "PHB"},
                ]
            },
        }
        spell = Spell.model_validate(spell_data_with_classes)
        assert spell.get_spell_list_classes() == "Sorcerer, Wizard"

        # Test spell without class lists
        spell_no_classes = Spell.model_validate(sample_spell_data)
        assert spell_no_classes.get_spell_list_classes() == ""

    def test_is_concentration(
        self,
        concentration_spell_data: dict[str, Any],
        sample_spell_data: dict[str, Any],
    ) -> None:
        """Test concentration detection."""
        concentration_spell = Spell.model_validate(concentration_spell_data)
        assert concentration_spell.is_concentration() is True

        regular_spell = Spell.model_validate(sample_spell_data)
        assert regular_spell.is_concentration() is False

    def test_has_verbal_components(self, sample_spell_data: dict[str, Any]) -> None:
        """Test verbal component detection."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.has_verbal_components() is True

        no_verbal_data = {**sample_spell_data, "components": {"s": True}}
        no_verbal_spell = Spell.model_validate(no_verbal_data)
        assert no_verbal_spell.has_verbal_components() is False

    def test_has_somatic_components(self, sample_spell_data: dict[str, Any]) -> None:
        """Test somatic component detection."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.has_somatic_components() is True

        no_somatic_data = {**sample_spell_data, "components": {"v": True}}
        no_somatic_spell = Spell.model_validate(no_somatic_data)
        assert no_somatic_spell.has_somatic_components() is False

    def test_has_material_components(self, sample_spell_data: dict[str, Any]) -> None:
        """Test material component detection."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.has_material_components() is True

        no_material_data = {**sample_spell_data, "components": {"v": True, "s": True}}
        no_material_spell = Spell.model_validate(no_material_data)
        assert no_material_spell.has_material_components() is False

    def test_get_latex_safe_name(self, sample_spell_data: dict[str, Any]) -> None:
        """Test LaTeX-safe name formatting."""
        # Test name with special characters
        special_name_data = {
            **sample_spell_data,
            "name": "Mordenkainen's Magnificent Mansion",
        }
        special_spell = Spell.model_validate(special_name_data)
        expected = (
            "Mordenkainen's Magnificent Mansion"  # Apostrophe should be preserved
        )
        assert special_spell.get_latex_safe_name() == expected

        # Test name with LaTeX special characters
        latex_chars_data = {**sample_spell_data, "name": "Spell & Magic"}
        latex_spell = Spell.model_validate(latex_chars_data)
        expected = "Spell \\& Magic"
        assert latex_spell.get_latex_safe_name() == expected

    def test_edge_cases(self, sample_spell_data: dict[str, Any]) -> None:
        """Test edge cases and error handling."""
        # Test spell with minimal data
        minimal_data = {
            "name": "Test Spell",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "level": 1,
            "school": "A",  # Abjuration
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "self"},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test spell description."],
        }
        minimal_spell = Spell.model_validate(minimal_data)

        # All methods should handle missing optional data gracefully
        assert minimal_spell.get_spell_attack_text() == ""
        assert minimal_spell.get_damage_text() == ""
        assert minimal_spell.get_condition_text() == ""
        assert minimal_spell.get_area_text() == ""
        assert minimal_spell.get_higher_level_scaling_text() == ""
        assert minimal_spell.get_spell_list_classes() == ""
        assert minimal_spell.is_concentration() is False
