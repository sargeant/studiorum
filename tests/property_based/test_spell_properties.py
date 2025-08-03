"""Property-based tests for spell models using Hypothesis.

These tests verify D&D 5e rule invariants and data integrity constraints
automatically across thousands of generated test cases.
"""

import pytest
from hypothesis import assume, example, given, strategies as st
from hypothesis.strategies import composite

from dnd5e.core.models.spells import (
    ClassReference,
    DistanceDetails,
    DurationDetails,
    EntryContent,
    Spell,
    SpellClassList,
    SpellComponent,
    SpellDuration,
    SpellRange,
    SpellTime,
)

# ==== Hypothesis Strategies for D&D Domain Objects ====


@composite
def valid_spell_levels(draw) -> int:
    """Generate valid D&D 5e spell levels (0-9)."""
    return draw(st.integers(min_value=0, max_value=9))


@composite
def valid_spell_schools(draw) -> str:
    """Generate valid D&D 5e schools of magic."""
    schools = [
        "Abjuration",
        "Conjuration",
        "Divination",
        "Enchantment",
        "Evocation",
        "Illusion",
        "Necromancy",
        "Transmutation",
    ]
    return draw(st.sampled_from(schools))


@composite
def valid_spell_school_abbreviations(draw) -> str:
    """Generate valid school abbreviations that should be expanded."""
    abbreviations = ["A", "C", "D", "E", "V", "I", "N", "T"]
    return draw(st.sampled_from(abbreviations))


@composite
def valid_time_units(draw) -> str:
    """Generate valid casting time units."""
    units = ["action", "bonus action", "reaction", "minute", "hour", "day", "week"]
    return draw(st.sampled_from(units))


@composite
def valid_duration_types(draw) -> str:
    """Generate valid duration types."""
    return draw(st.sampled_from(["instant", "timed", "permanent", "special"]))


@composite
def valid_range_types(draw) -> str:
    """Generate valid range types."""
    return draw(
        st.sampled_from(["point", "self", "sight", "unlimited", "line", "cone"])
    )


@composite
def valid_distance_types(draw) -> str:
    """Generate valid distance units."""
    return draw(st.sampled_from(["feet", "miles", "touch", "self"]))


@composite
def valid_spell_components(draw) -> dict:
    """Generate valid spell component combinations."""
    # Use predefined component combinations for efficiency
    component_combinations = [
        {"v": True},  # Verbal only
        {"s": True},  # Somatic only
        {"m": True},  # Material only (boolean)
        {"v": True, "s": True},  # Verbal + Somatic
        {"v": True, "m": True},  # Verbal + Material
        {"s": True, "m": True},  # Somatic + Material
        {"v": True, "s": True, "m": True},  # All three
        {"v": True, "s": True, "m": "a pinch of sulfur"},  # With material description
        {"m": "a crystal rod worth 10 gp"},  # Material description only
    ]

    return draw(st.sampled_from(component_combinations))


@composite
def valid_spell_times(draw) -> list[dict]:
    """Generate valid casting time structures."""
    time_data = {
        "number": draw(st.integers(min_value=1, max_value=24)),
        "unit": draw(valid_time_units()),
    }

    # Optionally add condition
    if draw(st.booleans()):
        time_data["condition"] = draw(st.text(min_size=1, max_size=50))

    return [time_data]


@composite
def valid_spell_ranges(draw) -> dict:
    """Generate valid spell range structures."""
    range_type = draw(valid_range_types())
    range_data = {"type": range_type}

    # Add distance for applicable types
    if range_type in ["point", "self"]:
        distance_type = draw(valid_distance_types())
        range_data["distance"] = {
            "type": distance_type,
            "amount": draw(st.integers(min_value=0, max_value=1000))
            if distance_type != "touch"
            else 0,
        }

    return range_data


@composite
def valid_spell_durations(draw) -> list[dict]:
    """Generate valid spell duration structures."""
    duration_type = draw(valid_duration_types())
    duration_data = {"type": duration_type}

    # Add duration details for timed spells
    if duration_type == "timed":
        duration_data["duration"] = {
            "type": draw(st.sampled_from(["minute", "hour", "day", "week"])),
            "amount": draw(st.integers(min_value=1, max_value=24)),
        }
        # Optionally add concentration
        duration_data["concentration"] = draw(st.booleans())

    return [duration_data]


@composite
def valid_spell_entries(draw) -> list:
    """Generate valid spell description entries."""
    # Use generic test entries to avoid copyright issues
    simple_entries = [
        "This spell creates a magical effect within the specified range.",
        "The caster channels arcane energy to produce the desired outcome.",
        "Upon casting, magical forces align to manifest the spell's purpose.",
        "The spell weaves magical energies to achieve its intended effect.",
        "Arcane power flows through the caster to create the spell's result.",
    ]

    structured_entries = [
        {
            "type": "entries",
            "entries": ["The spell creates a magical effect."],
            "name": "Spell Effect",
        },
        {
            "type": "inset",
            "entries": ["This is important information about the spell."],
        },
        {
            "type": "quote",
            "entries": ["Words of power echo through the air."],
            "by": "Ancient Wizard",
        },
    ]

    # Mix simple and structured entries
    entries = []
    num_entries = draw(st.integers(min_value=1, max_value=3))

    for _ in range(num_entries):
        if draw(st.booleans()):
            entries.append(draw(st.sampled_from(simple_entries)))
        else:
            entries.append(draw(st.sampled_from(structured_entries)))

    return entries


@composite
def valid_spells(draw) -> dict:
    """Generate complete valid spell data using only SRD-compatible content."""
    # Use only SRD-compatible spell names (public domain/OGL content)
    spell_names = [
        "Test Spell",
        "Magic Test",
        "Healing Test",
        "Protection Test",
        "Enchantment Test",
        "Divination Test",
        "Evocation Test",
        "Sample Spell",
        "Basic Cantrip",
        "Simple Spell",
        "Minor Magic",
        "Lesser Effect",
    ]

    # Use only test data sources, not copyrighted material
    source_books = ["SRD", "TEST", "SAMPLE", "OGL"]

    return {
        "name": draw(st.sampled_from(spell_names)),
        "source": draw(st.sampled_from(source_books)),
        "level": draw(valid_spell_levels()),
        "school": draw(
            st.one_of(valid_spell_schools(), valid_spell_school_abbreviations())
        ),
        "time": draw(valid_spell_times()),
        "range": draw(valid_spell_ranges()),
        "components": draw(valid_spell_components()),
        "duration": draw(valid_spell_durations()),
        "entries": draw(valid_spell_entries()),
    }


# ==== Property-Based Tests ====


class TestSpellInvariants:
    """Test D&D 5e spell rule invariants."""

    @given(valid_spell_levels())
    def test_spell_level_constraints(self, level: int):
        """Spell levels must always be 0-9."""
        assert 0 <= level <= 9
        assert isinstance(level, int)

    @given(valid_spell_schools())
    def test_spell_school_names(self, school: str):
        """Spell schools must be valid D&D schools."""
        valid_schools = {
            "Abjuration",
            "Conjuration",
            "Divination",
            "Enchantment",
            "Evocation",
            "Illusion",
            "Necromancy",
            "Transmutation",
        }
        assert school in valid_schools
        assert school.istitle()  # Proper capitalization

    @given(valid_spell_school_abbreviations())
    def test_school_abbreviation_expansion(self, abbreviation: str):
        """School abbreviations should expand to full names."""
        spell_data = {
            "name": "Test Spell",
            "source": "TEST",
            "level": 1,
            "school": abbreviation,
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test description"],
        }

        spell = Spell.model_validate(spell_data)

        # Verify abbreviation was expanded
        expected_schools = {
            "A": "Abjuration",
            "C": "Conjuration",
            "D": "Divination",
            "E": "Enchantment",
            "V": "Evocation",
            "I": "Illusion",
            "N": "Necromancy",
            "T": "Transmutation",
        }
        assert spell.school == expected_schools[abbreviation]

    @given(valid_spell_components())
    def test_spell_components_validation(self, components: dict):
        """Spells must have at least one component (V, S, or M)."""
        spell_component = SpellComponent.model_validate(components)

        # At least one component must be present
        assert (
            spell_component.verbal
            or spell_component.somatic
            or bool(spell_component.material)
        )

        # Material component handling
        if spell_component.material:
            assert isinstance(spell_component.material, bool | str)
            if isinstance(spell_component.material, str):
                assert len(spell_component.material) > 0

    @given(valid_spells())
    def test_spell_serialization_roundtrip(self, spell_data: dict):
        """Spells should serialize and deserialize consistently."""
        # Create spell from data
        spell = Spell.model_validate(spell_data)

        # Serialize back to dict using aliases for proper field names
        serialized = spell.model_dump(by_alias=True)

        # Deserialize again
        spell2 = Spell.model_validate(serialized)

        # Core properties should match
        assert spell.name == spell2.name
        assert spell.level == spell2.level
        assert spell.school == spell2.school
        assert len(spell.casting_time) == len(spell2.casting_time)
        assert spell.range.type == spell2.range.type

    @given(valid_spells())
    def test_spell_level_text_formatting(self, spell_data: dict):
        """Spell level text should follow D&D formatting conventions."""
        spell = Spell.model_validate(spell_data)
        level_text = spell.get_level_text()

        if spell.level == 0:
            assert "cantrip" in level_text.lower()
            assert spell.school.lower() in level_text.lower()
        elif spell.level == 1:
            assert "1st-level" in level_text
        elif spell.level == 2:
            assert "2nd-level" in level_text
        elif spell.level == 3:
            assert "3rd-level" in level_text
        else:
            assert f"{spell.level}th-level" in level_text

        # School should be in lowercase for leveled spells (not cantrips)
        if spell.level > 0:
            assert spell.school.lower() in level_text

    @given(valid_spells())
    def test_spell_components_text_formatting(self, spell_data: dict):
        """Component text should follow standard D&D format."""
        spell = Spell.model_validate(spell_data)
        components_text = spell.get_components_text()

        # Should not be empty (every spell has components)
        assert len(components_text) > 0

        # Check component indicators
        if spell.components.verbal:
            assert "V" in components_text
        if spell.components.somatic:
            assert "S" in components_text
        if spell.components.material:
            assert "M" in components_text

        # Material component with description should be in parentheses
        if isinstance(spell.components.material, str):
            assert "(" in components_text and ")" in components_text

    @given(valid_spells())
    def test_spell_name_non_empty(self, spell_data: dict):
        """Spell names must be non-empty after stripping whitespace."""
        spell = Spell.model_validate(spell_data)
        assert len(spell.name.strip()) > 0
        assert spell.name == spell.name.strip()  # No leading/trailing whitespace

    @given(valid_spells())
    def test_spell_latex_safety(self, spell_data: dict):
        """LaTeX-safe names should escape dangerous characters."""
        spell = Spell.model_validate(spell_data)
        latex_name = spell.get_latex_safe_name()

        # Check that dangerous LaTeX characters are escaped
        dangerous_chars = ["&", "%", "$", "#", "_", "{", "}", "^", "~"]
        for char in dangerous_chars:
            if char in spell.name:
                # The character should be escaped in the latex version
                assert char not in latex_name or f"\\{char}" in latex_name

    @given(
        st.integers(min_value=1, max_value=10),
        st.sampled_from(["action", "bonus action", "minute", "hour"]),
    )
    def test_spell_time_formatting(self, number: int, unit: str):
        """Casting time formatting should handle singular/plural correctly."""
        time_data = {"number": number, "unit": unit}
        spell_time = SpellTime.model_validate(time_data)
        time_text = str(spell_time)

        if number == 1:
            assert f"1 {unit}" in time_text
            assert unit + "s" not in time_text  # No plural for 1
        else:
            assert f"{number} {unit}s" in time_text  # Plural for > 1

    @given(valid_duration_types(), st.booleans())
    def test_spell_duration_concentration_rules(
        self, duration_type: str, concentration: bool
    ):
        """Concentration rules should be consistent with duration types."""
        if duration_type == "instant":
            # Instant spells cannot have concentration
            duration_data = {"type": duration_type, "concentration": False}
        elif duration_type == "timed":
            # Timed spells can have concentration
            duration_data = {
                "type": duration_type,
                "concentration": concentration,
                "duration": {"type": "hour", "amount": 1},
            }
        else:
            duration_data = {"type": duration_type, "concentration": concentration}

        duration = SpellDuration.model_validate(duration_data)
        duration_text = str(duration)

        # Concentration should only appear for timed spells
        if duration.concentration and duration_type == "timed":
            assert "concentration" in duration_text.lower()
        elif duration_type == "instant":
            assert "instantaneous" in duration_text.lower()
            assert not duration.concentration  # Should be False
        elif duration_type == "permanent":
            assert "permanent" in duration_text.lower()


class TestSpellDataIntegrity:
    """Test spell data integrity and consistency."""

    @given(valid_spells())
    def test_spell_entries_non_empty(self, spell_data: dict):
        """Spells must have non-empty description entries."""
        spell = Spell.model_validate(spell_data)

        assert len(spell.entries) > 0
        description_text = spell.get_description_text()
        assert len(description_text.strip()) > 0

    @given(valid_spells())
    def test_spell_range_consistency(self, spell_data: dict):
        """Spell range should be internally consistent."""
        spell = Spell.model_validate(spell_data)
        range_text = spell.get_range_text()

        # Range text should not be empty
        assert len(range_text) > 0

        # Self spells should indicate "Self"
        if spell.range.type == "self":
            assert "self" in range_text.lower()

        # Point spells with distance should show distance
        if spell.range.type == "point" and spell.range.distance:
            if spell.range.distance.amount and spell.range.distance.amount > 0:
                assert str(spell.range.distance.amount) in range_text

    @given(
        valid_spells(),
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=3),
    )
    def test_spell_saving_throw_formatting(self, spell_data: dict, saves: list[str]):
        """Saving throw formatting should handle multiple saves correctly."""
        spell_data["savingThrow"] = saves
        spell = Spell.model_validate(spell_data)
        attack_text = spell.get_spell_attack_text()

        if len(saves) == 1:
            assert saves[0].title() in attack_text
            assert "saving throw" in attack_text
        else:
            # Multiple saves should be comma-separated
            for save in saves:
                assert save.title() in attack_text
            if len(saves) > 1:
                assert "," in attack_text


# ==== Edge Case and Integration Tests ====


class TestSpellEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cantrip_level_zero_handling(self):
        """Cantrips (level 0) should be handled correctly."""
        spell_data = {
            "name": "Test Cantrip",
            "source": "TEST",
            "level": 0,
            "school": "V",  # Evocation
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 60}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            "entries": ["A simple cantrip for testing."],
        }

        spell = Spell.model_validate(spell_data)

        assert spell.level == 0
        assert "cantrip" in spell.get_level_text().lower()
        assert "evocation" in spell.get_level_text().lower()

    @example(
        spell_data={
            "name": "Test Spell",
            "source": "SRD",
            "level": 3,
            "school": "V",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
            "components": {"v": True, "s": True, "m": "a focus crystal"},
            "duration": [{"type": "instant"}],
            "entries": ["A magical effect emanates from your focus..."],
        }
    )
    @given(valid_spells())
    def test_classic_spell_examples(self, spell_data: dict):
        """Test with classic D&D spell examples."""
        spell = Spell.model_validate(spell_data)

        # Basic validation
        assert 0 <= spell.level <= 9
        assert len(spell.name.strip()) > 0
        assert spell.school in [
            "Abjuration",
            "Conjuration",
            "Divination",
            "Enchantment",
            "Evocation",
            "Illusion",
            "Necromancy",
            "Transmutation",
        ]


if __name__ == "__main__":
    # Run a few property tests manually for verification
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
