"""Example test demonstrating improved factory fixture patterns for better test isolation."""

import pytest

from dnd5e.core.models.spells import Spell


class TestImprovedFixturePatterns:
    """Demonstrate modern pytest fixture patterns that avoid mutable state sharing."""

    def test_factory_fixtures_provide_isolation(
        self, make_sample_spell_data, make_temp_data_dir, make_omnidexer
    ):
        """Test that factory fixtures provide proper test isolation."""
        # Create custom spell data for this test only
        spell_data = make_sample_spell_data(name="Lightning Bolt", level=3)
        spell_data2 = make_sample_spell_data(name="Fireball", level=3)

        # Create isolated temporary directory with custom data
        temp_dir = make_temp_data_dir(spell_data=[spell_data, spell_data2])

        # Create omnidexer with isolated data
        omnidexer = make_omnidexer(
            temp_data_dir=temp_dir, spell_data=[spell_data, spell_data2]
        )

        # Verify data is loaded correctly and isolated
        spells = omnidexer.get_all_by_type("spell")
        spell_names = [spell.name for spell in spells]

        assert "Lightning Bolt" in spell_names
        assert "Fireball" in spell_names
        assert len(spells) == 2

    def test_factory_fixtures_allow_customization(
        self, make_sample_spell_data, make_temp_data_dir, make_omnidexer
    ):
        """Test that factory fixtures allow easy customization per test."""
        # Create a different spell for this test
        custom_spell = make_sample_spell_data(name="Magic Missile", level=1)

        temp_dir = make_temp_data_dir(spell_data=[custom_spell])
        omnidexer = make_omnidexer(temp_data_dir=temp_dir, spell_data=[custom_spell])

        spells = omnidexer.get_all_by_type("spell")
        assert len(spells) == 1
        assert spells[0].name == "Magic Missile"
        assert spells[0].level == 1

    def test_factory_data_creation_isolation(self, make_sample_spell_data):
        """Test that factory data creation provides proper isolation."""
        # Create two separate instances
        spell1_data = make_sample_spell_data(name="Spell 1")
        spell2_data = make_sample_spell_data(name="Spell 2")

        # Modify one instance
        spell1_data["level"] = 9

        # Verify the other instance is not affected
        assert spell1_data["level"] == 9
        assert spell2_data["level"] == 3  # Default value
        assert spell1_data["name"] == "Spell 1"
        assert spell2_data["name"] == "Spell 2"

    def test_pydantic_model_creation_with_factory_data(self, make_sample_spell_data):
        """Test creating Pydantic models with factory data."""
        spell_data = make_sample_spell_data(name="Test Spell", level=5)
        spell = Spell.model_validate(spell_data)

        assert spell.name == "Test Spell"
        assert spell.level == 5
        assert spell.school == "Evocation"  # School converted from "V" abbreviation
