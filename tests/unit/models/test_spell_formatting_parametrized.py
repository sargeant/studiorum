"""Tests for enhanced Spell model formatting methods - Parametrized Version."""

from typing import Any

import pytest

from dnd5e.core.models.spells import Spell


class TestSpellFormattingMethodsParametrized:
    """Test enhanced formatting methods on Spell model using parametrization."""

    @pytest.fixture
    def base_spell_data(self) -> dict[str, Any]:
        """Base spell data for testing."""
        return {
            "name": "Test Spell",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241},
            "level": 3,
            "school": "V",  # Evocation
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test spell description."],
        }

    @pytest.mark.parametrize(
        "spell_modifications,expected_attack_text",
        [
            # Spell with saving throw
            ({"savingThrow": ["dexterity"]}, "Dexterity saving throw"),
            # Spell with spell attack
            ({"spellAttack": ["ranged"]}, "ranged spell attack"),
            # Spell with melee spell attack
            ({"spellAttack": ["melee"]}, "melee spell attack"),
            # Spell with no attack or save
            ({}, ""),
            # Spell with multiple saving throws
            (
                {"savingThrow": ["dexterity", "constitution"]},
                "Dexterity, Constitution saving throw",
            ),
        ],
    )
    def test_get_spell_attack_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        spell_modifications: dict[str, Any],
        expected_attack_text: str,
    ) -> None:
        """Test spell attack text formatting with various configurations."""
        spell_data = {**base_spell_data, **spell_modifications}
        spell = Spell.model_validate(spell_data)
        assert spell.get_spell_attack_text() == expected_attack_text

    @pytest.mark.parametrize(
        "damage_types,expected_damage_text",
        [
            # Single damage type
            (["fire"], "fire"),
            # Multiple damage types
            (["fire", "radiant"], "fire, radiant"),
            # No damage
            (None, ""),
            # Empty list
            ([], ""),
            # Three damage types
            (["fire", "cold", "lightning"], "fire, cold, lightning"),
        ],
    )
    def test_get_damage_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        damage_types: list[str] | None,
        expected_damage_text: str,
    ) -> None:
        """Test damage type text formatting with various damage combinations."""
        spell_data = {**base_spell_data, "damageInflict": damage_types}
        spell = Spell.model_validate(spell_data)
        assert spell.get_damage_text() == expected_damage_text

    @pytest.mark.parametrize(
        "conditions,expected_condition_text",
        [
            # Single condition
            (["paralyzed"], "paralyzed"),
            # Multiple conditions
            (["paralyzed", "stunned"], "paralyzed, stunned"),
            # No conditions
            (None, ""),
            # Empty list
            ([], ""),
            # Three conditions
            (
                ["charmed", "frightened", "restrained"],
                "charmed, frightened, restrained",
            ),
        ],
    )
    def test_get_condition_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        conditions: list[str] | None,
        expected_condition_text: str,
    ) -> None:
        """Test condition inflicted text formatting with various condition combinations."""
        spell_data = {**base_spell_data, "conditionInflict": conditions}
        spell = Spell.model_validate(spell_data)
        assert spell.get_condition_text() == expected_condition_text

    @pytest.mark.parametrize(
        "area_tags,expected_area_text",
        [
            # Single area type
            (["S"], "Sphere"),
            # Multiple area types
            (["S", "C"], "Sphere, Cone"),
            # No area
            (None, ""),
            # Line and square
            (["L", "Q"], "Line, Square"),
        ],
    )
    def test_get_area_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        area_tags: list[str] | None,
        expected_area_text: str,
    ) -> None:
        """Test area of effect text formatting with various area types."""
        spell_data = {**base_spell_data, "areaTags": area_tags}
        spell = Spell.model_validate(spell_data)
        assert spell.get_area_text() == expected_area_text

    @pytest.mark.parametrize(
        "level,school,damage_types,attack_info,expected_text",
        [
            # Regular spell with fire damage and saving throw
            (
                3,
                "V",
                ["fire"],
                {"savingThrow": ["dexterity"]},
                "3rd-level evocation (fire damage, Dexterity saving throw)",
            ),
            # Cantrip with force damage and spell attack
            (
                0,
                "V",
                ["force"],
                {"spellAttack": ["ranged"]},
                "Evocation cantrip (force damage, ranged spell attack)",
            ),
            # 1st level spell with no damage or attack
            (1, "E", None, {}, "1st-level enchantment"),
            # 9th level spell with multiple damage types
            (
                9,
                "N",
                ["necrotic", "psychic"],
                {"savingThrow": ["constitution"]},
                "9th-level necromancy (necrotic, psychic damage, Constitution saving throw)",
            ),
        ],
    )
    def test_get_enhanced_level_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        level: int,
        school: str,
        damage_types: list[str] | None,
        attack_info: dict[str, Any],
        expected_text: str,
    ) -> None:
        """Test enhanced level text with various spell configurations."""
        spell_data = {
            **base_spell_data,
            "level": level,
            "school": school,
            "damageInflict": damage_types,
            **attack_info,
        }
        spell = Spell.model_validate(spell_data)
        assert spell.get_enhanced_level_text() == expected_text

    @pytest.mark.parametrize(
        "components,expected_text",
        [
            # V, S, M with material description
            (
                {"v": True, "s": True, "m": {"text": "a tiny ball of bat guano"}},
                "V, S, M (a tiny ball of bat guano)",
            ),
            # V, S only
            ({"v": True, "s": True}, "V, S"),
            # Only verbal
            ({"v": True}, "V"),
            # Only somatic
            ({"s": True}, "S"),
            # Only material
            (
                {"m": {"text": "a diamond worth 1,000 gp"}},
                "M (a diamond worth 1,000 gp)",
            ),
            # V and M
            ({"v": True, "m": {"text": "a feather"}}, "V, M (a feather)"),
        ],
    )
    def test_get_enhanced_components_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        components: dict[str, Any],
        expected_text: str,
    ) -> None:
        """Test enhanced components text with various component combinations."""
        spell_data = {**base_spell_data, "components": components}
        spell = Spell.model_validate(spell_data)
        assert spell.get_enhanced_components_text() == expected_text

    @pytest.mark.parametrize(
        "duration_config,expected_text",
        [
            # Concentration spell
            (
                [
                    {
                        "type": "timed",
                        "duration": {"type": "minute", "amount": 1},
                        "concentration": True,
                    }
                ],
                "Concentration, up to 1 minute",
            ),
            # Instantaneous
            ([{"type": "instant"}], "Instantaneous"),
            # Timed without concentration
            ([{"type": "timed", "duration": {"type": "hour", "amount": 8}}], "8 hour"),
            # Permanent
            ([{"type": "permanent"}], "Permanent"),
            # Special duration
            ([{"type": "special"}], "Special"),
        ],
    )
    def test_get_enhanced_duration_text_parametrized(
        self,
        base_spell_data: dict[str, Any],
        duration_config: list[dict[str, Any]],
        expected_text: str,
    ) -> None:
        """Test enhanced duration text with various duration configurations."""
        spell_data = {**base_spell_data, "duration": duration_config}
        spell = Spell.model_validate(spell_data)
        assert spell.get_enhanced_duration_text() == expected_text

    @pytest.mark.parametrize(
        "spell_name,level,school,components,damage_types,conditions,area_tags,attack_info",
        [
            # Fireball-like spell
            (
                "Fireball",
                3,
                "V",
                {"v": True, "s": True, "m": {"text": "bat guano"}},
                ["fire"],
                None,
                ["S"],
                {"savingThrow": ["dexterity"]},
            ),
            # Hold Person-like spell
            (
                "Hold Person",
                2,
                "E",
                {"v": True, "s": True, "m": {"text": "iron piece"}},
                None,
                ["paralyzed"],
                None,
                {"savingThrow": ["wisdom"]},
            ),
            # Eldritch Blast-like cantrip
            (
                "Eldritch Blast",
                0,
                "V",
                {"v": True, "s": True},
                ["force"],
                None,
                None,
                {"spellAttack": ["ranged"]},
            ),
        ],
    )
    def test_complete_spell_formatting_integration(
        self,
        base_spell_data: dict[str, Any],
        spell_name: str,
        level: int,
        school: str,
        components: dict[str, Any],
        damage_types: list[str] | None,
        conditions: list[str] | None,
        area_tags: list[str] | None,
        attack_info: dict[str, Any],
    ) -> None:
        """Integration test for complete spell formatting with realistic spell configurations."""
        spell_data = {
            **base_spell_data,
            "name": spell_name,
            "level": level,
            "school": school,
            "components": components,
            "damageInflict": damage_types,
            "conditionInflict": conditions,
            "areaTags": area_tags,
            **attack_info,
        }

        spell = Spell.model_validate(spell_data)

        # Verify all formatting methods work without errors
        level_text = spell.get_enhanced_level_text()
        components_text = spell.get_enhanced_components_text()
        damage_text = spell.get_damage_text()
        condition_text = spell.get_condition_text()
        area_text = spell.get_area_text()

        # Basic assertions to ensure methods return meaningful data
        assert spell_name.lower() in spell.name.lower()
        assert len(level_text) > 0
        assert len(components_text) > 0

        if damage_types:
            assert len(damage_text) > 0

        if conditions:
            assert len(condition_text) > 0

        if area_tags:
            assert len(area_text) > 0
