"""Tests for Pydantic encounter theme models.

Comprehensive tests validating the enhanced Pydantic implementations
with proper type safety, validation, and JSON serialization.
"""

import pytest
from pydantic import ValidationError

from studiorum.mcp.tools.encounter.themes import EncounterTheme, EnvironmentType
from studiorum.mcp.tools.encounter.themes_pydantic import (
    EnvironmentalProfile,
    ThematicProfile,
)


class TestEnvironmentalProfile:
    """Test EnvironmentalProfile Pydantic implementation."""

    def test_valid_environmental_profile_creation(self):
        """Test creating a valid environmental profile."""
        profile = EnvironmentalProfile(
            environment=EnvironmentType.FOREST,
            climate="tropical",
            terrain_difficulty="difficult",
            lighting="dim",
            weather="rain",
            visibility_range=60,
            movement_penalty=0.75,
            stealth_modifier=2,
            sound_propagation=0.8,
        )

        assert (
            profile.environment == EnvironmentType.FOREST.value
        )  # Pydantic uses enum values
        assert profile.climate == "tropical"
        assert profile.terrain_difficulty == "difficult"
        assert profile.lighting == "dim"
        assert profile.weather == "rain"
        assert profile.visibility_range == 60
        assert profile.movement_penalty == 0.75
        assert profile.stealth_modifier == 2
        assert profile.sound_propagation == 0.8
        assert isinstance(profile.creature_affinities, dict)

    def test_default_values(self):
        """Test environmental profile with default values."""
        profile = EnvironmentalProfile(environment=EnvironmentType.URBAN)

        assert profile.climate == "temperate"
        assert profile.terrain_difficulty == "normal"
        assert profile.lighting == "normal"
        assert profile.weather == "clear"
        assert profile.visibility_range == 120
        assert profile.movement_penalty == 1.0
        assert profile.stealth_modifier == 0
        assert profile.sound_propagation == 1.0

    def test_creature_affinities_initialization(self):
        """Test creature affinities are properly initialized."""
        profile = EnvironmentalProfile(environment=EnvironmentType.DUNGEON)

        assert len(profile.creature_affinities) > 0
        assert "undead" in profile.creature_affinities
        assert profile.creature_affinities["undead"] > 1.0  # Dungeons favor undead

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = EnvironmentalProfile(
            environment=EnvironmentType.SWAMP,
            climate="tropical",
            weather="fog",
            visibility_range=30,
        )

        # Serialize to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["environment"] == "swamp"
        assert data["climate"] == "tropical"
        assert data["weather"] == "fog"
        assert data["visibility_range"] == 30

        # Deserialize back
        restored = EnvironmentalProfile.model_validate(data)
        assert (
            restored.environment == original.environment
        )  # Both are already string values
        assert restored.climate == original.climate
        assert restored.weather == original.weather
        assert restored.visibility_range == original.visibility_range

    def test_validation_errors(self):
        """Test field validation errors."""
        # Invalid visibility range
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST, visibility_range=-10
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Invalid movement penalty
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST,
                movement_penalty=0.0,  # Must be > 0.0
            )
        assert "greater than 0" in str(exc_info.value)

        # Invalid stealth modifier
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST,
                stealth_modifier=15,  # Must be <= 10
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_creature_affinity_validation(self):
        """Test creature affinity validation."""
        # Valid creature affinities
        profile = EnvironmentalProfile(
            environment=EnvironmentType.FOREST,
            creature_affinities={
                "beast": 1.5,
                "fey": 2.0,
                "undead": 0.3,
            },
        )
        assert profile.creature_affinities["beast"] == 1.5

        # Invalid affinity value - too high
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST,
                creature_affinities={"dragon": 4.0},  # > 3.0
            )
        assert "must be between 0.0 and 3.0" in str(exc_info.value)

        # Invalid affinity value - negative
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST, creature_affinities={"beast": -0.5}
            )
        assert "must be between 0.0 and 3.0" in str(exc_info.value)

        # Invalid creature type - empty string
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST, creature_affinities={"": 1.0}
            )
        assert "non-empty string" in str(exc_info.value)

        # Invalid affinity type
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST,
                creature_affinities={"beast": "high"},  # Should be numeric
            )
        assert "Input should be a valid number" in str(exc_info.value)

    def test_weather_validation(self):
        """Test weather condition validation."""
        # Valid weather
        profile = EnvironmentalProfile(
            environment=EnvironmentType.ARCTIC, weather="blizzard"
        )
        assert profile.weather == "blizzard"

        # Unknown weather (should log warning but not fail)
        profile = EnvironmentalProfile(
            environment=EnvironmentType.FOREST, weather="volcanic_ash"
        )
        assert profile.weather == "volcanic_ash"

        # Invalid weather type
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST,
                weather=123,  # Should be string
            )
        assert "Input should be a valid string" in str(exc_info.value)

    def test_pattern_validation(self):
        """Test regex pattern validation for constrained fields."""
        # Valid climate
        profile = EnvironmentalProfile(
            environment=EnvironmentType.DESERT, climate="arid"
        )
        assert profile.climate == "arid"

        # Invalid climate pattern
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.DESERT, climate="super_hot"
            )
        assert "String should match pattern" in str(
            exc_info.value
        )  # Pydantic 2.x format

        # Invalid terrain difficulty
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.MOUNTAIN, terrain_difficulty="impossible"
            )
        assert "String should match pattern" in str(
            exc_info.value
        )  # Pydantic 2.x format

        # Invalid lighting
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.UNDERDARK, lighting="pitch_black"
            )
        assert "String should match pattern" in str(
            exc_info.value
        )  # Pydantic 2.x format

    def test_model_config(self):
        """Test model configuration settings."""
        # Test extra fields are forbidden
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalProfile(
                environment=EnvironmentType.FOREST, invalid_field="test"
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestThematicProfile:
    """Test ThematicProfile Pydantic implementation."""

    def test_valid_thematic_profile_creation(self):
        """Test creating a valid thematic profile."""
        profile = ThematicProfile(
            theme=EncounterTheme.UNDEAD_HORROR,
            intensity=1.5,
            allow_mixed=True,
            narrative_context={
                "location": "ancient_cemetery",
                "threat_level": 7,
                "is_cursed": True,
                "bonus_xp": 0.25,
            },
        )

        assert (
            profile.theme == EncounterTheme.UNDEAD_HORROR.value
        )  # Pydantic uses enum values
        assert profile.intensity == 1.5
        assert profile.allow_mixed is True
        assert profile.narrative_context["location"] == "ancient_cemetery"
        assert profile.narrative_context["threat_level"] == 7
        assert profile.narrative_context["is_cursed"] is True
        assert profile.narrative_context["bonus_xp"] == 0.25

    def test_default_values(self):
        """Test thematic profile with default values."""
        profile = ThematicProfile(theme=EncounterTheme.FEY_MYSTERY)

        assert profile.intensity == 1.0
        assert profile.allow_mixed is False
        assert profile.narrative_context == {}

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = ThematicProfile(
            theme=EncounterTheme.DRACONIC_POWER,
            intensity=2.0,
            allow_mixed=True,
            narrative_context={"dragon_type": "red", "age_category": 12},
        )

        # Serialize to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["theme"] == "draconic_power"
        assert data["intensity"] == 2.0
        assert data["allow_mixed"] is True
        assert data["narrative_context"]["dragon_type"] == "red"

        # Deserialize back
        restored = ThematicProfile.model_validate(data)
        assert restored.theme == original.theme  # Both should be string values
        assert restored.intensity == original.intensity
        assert restored.allow_mixed == original.allow_mixed
        assert restored.narrative_context == original.narrative_context

    def test_intensity_validation(self):
        """Test intensity field validation."""
        # Valid intensity values
        for intensity in [0.0, 0.5, 1.0, 1.5, 2.0]:
            profile = ThematicProfile(
                theme=EncounterTheme.GIANT_MIGHT, intensity=intensity
            )
            assert profile.intensity == intensity

        # Invalid intensity - too low
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(theme=EncounterTheme.GIANT_MIGHT, intensity=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Invalid intensity - too high
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(theme=EncounterTheme.GIANT_MIGHT, intensity=2.1)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_narrative_context_validation(self):
        """Test narrative context validation."""
        # Valid narrative context with different types
        profile = ThematicProfile(
            theme=EncounterTheme.ELEMENTAL_CHAOS,
            narrative_context={
                "element": "fire",  # string
                "chaos_level": 8,  # int
                "temperature": 98.6,  # float
                "is_active": True,  # bool
            },
        )
        assert len(profile.narrative_context) == 4

        # Invalid context key - empty string
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(
                theme=EncounterTheme.ELEMENTAL_CHAOS, narrative_context={"": "value"}
            )
        assert "non-empty strings" in str(exc_info.value)

        # Invalid context key - non-string
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(
                theme=EncounterTheme.ELEMENTAL_CHAOS, narrative_context={123: "value"}
            )
        assert "Input should be a valid string" in str(exc_info.value)

        # Invalid context value - complex object
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(
                theme=EncounterTheme.ELEMENTAL_CHAOS,
                narrative_context={"complex": {"nested": "object"}},
            )
        # Pydantic v2 tries each union member and reports all failures
        error_str = str(exc_info.value)
        assert (
            "Input should be a valid string" in error_str
            or "must be string, int, float, or bool" in error_str
        )

        # Invalid context value - list
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(
                theme=EncounterTheme.ELEMENTAL_CHAOS,
                narrative_context={"items": ["sword", "shield"]},
            )
        # Pydantic v2 tries each union member and reports all failures
        error_str = str(exc_info.value)
        assert (
            "Input should be a valid string" in error_str
            or "must be string, int, float, or bool" in error_str
        )

    def test_model_config(self):
        """Test model configuration settings."""
        profile = ThematicProfile(theme=EncounterTheme.BEAST_WILDERNESS)

        # Test extra fields are forbidden
        with pytest.raises(ValidationError) as exc_info:
            ThematicProfile(theme=EncounterTheme.BEAST_WILDERNESS, invalid_field="test")
        assert "Extra inputs are not permitted" in str(exc_info.value)

        # Test enum values are used
        data = profile.model_dump()
        assert data["theme"] == "beast_wilderness"  # Enum value, not name


class MockCreature:
    """Mock creature for testing methods that require creature analysis."""

    def __init__(
        self,
        creature_type: str = "beast",
        has_darkvision: bool = False,
        can_fly: bool = False,
        senses: str | None = None,
        speed: dict | None = None,
    ):
        if isinstance(creature_type, str):
            self.type = creature_type
        else:
            self.type = {"type": creature_type}

        if senses or has_darkvision:
            self.senses = senses or (
                "darkvision 60 ft." if has_darkvision else "passive Perception 12"
            )
        else:
            self.senses = None

        if speed or can_fly:
            self.speed = speed or ({"walk": 30, "fly": 60} if can_fly else {"walk": 30})
        else:
            self.speed = None


class TestEnvironmentalProfileMethods:
    """Test EnvironmentalProfile calculation methods."""

    def test_calculate_creature_suitability_basic(self):
        """Test basic creature suitability calculation."""
        profile = EnvironmentalProfile(environment=EnvironmentType.FOREST)

        # Test beast in forest (should be good fit)
        beast = MockCreature(creature_type="beast")
        suitability = profile.calculate_creature_suitability(beast)
        assert suitability > 1.0  # Above neutral

        # Test construct in forest (should be neutral - no affinity defined)
        construct = MockCreature(creature_type="construct")
        suitability = profile.calculate_creature_suitability(construct)
        assert suitability == 1.0  # Neutral for undefined types

    def test_creature_suitability_with_darkvision(self):
        """Test creature suitability with darkvision in dark conditions."""
        profile = EnvironmentalProfile(
            environment=EnvironmentType.UNDERDARK, lighting="dark"
        )

        # Creature with darkvision should be more suitable in dark
        darkvision_creature = MockCreature(
            creature_type="aberration", has_darkvision=True
        )
        suitability_dark = profile.calculate_creature_suitability(darkvision_creature)

        # Creature without darkvision should be less suitable
        normal_creature = MockCreature(creature_type="aberration", has_darkvision=False)
        suitability_normal = profile.calculate_creature_suitability(normal_creature)

        assert suitability_dark > suitability_normal

    def test_creature_suitability_with_flight(self):
        """Test creature suitability with flight in difficult terrain."""
        profile = EnvironmentalProfile(
            environment=EnvironmentType.MOUNTAIN, terrain_difficulty="extreme"
        )

        # Flying creature should be more suitable in difficult terrain
        flying_creature = MockCreature(creature_type="dragon", can_fly=True)
        suitability_flying = profile.calculate_creature_suitability(flying_creature)

        # Ground creature should be less suitable
        ground_creature = MockCreature(creature_type="dragon", can_fly=False)
        suitability_ground = profile.calculate_creature_suitability(ground_creature)

        assert suitability_flying > suitability_ground

    def test_creature_suitability_bounds(self):
        """Test that creature suitability stays within bounds."""
        profile = EnvironmentalProfile(
            environment=EnvironmentType.UNDERWATER,
            lighting="dark",
            terrain_difficulty="extreme",
            weather="storm",
        )

        # Even with multiple negative modifiers, should not go below 0.0
        poor_creature = MockCreature(creature_type="construct")
        suitability = profile.calculate_creature_suitability(poor_creature)
        assert 0.0 <= suitability <= 2.0

        # Even with multiple positive modifiers, should not exceed 2.0
        good_creature = MockCreature(
            creature_type="elemental", has_darkvision=True, can_fly=True
        )
        suitability = profile.calculate_creature_suitability(good_creature)
        assert 0.0 <= suitability <= 2.0


class TestThematicProfileMethods:
    """Test ThematicProfile calculation methods."""

    def test_calculate_thematic_fit_basic(self):
        """Test basic thematic fit calculation."""
        profile = ThematicProfile(theme=EncounterTheme.UNDEAD_HORROR)

        # Test undead creature (perfect fit)
        undead = MockCreature(creature_type="undead")
        fit = profile.calculate_thematic_fit(undead)
        assert fit >= 1.8  # Very high fit

        # Test celestial creature (very poor fit)
        celestial = MockCreature(creature_type="celestial")
        fit = profile.calculate_thematic_fit(celestial)
        assert fit <= 0.2  # Very low fit

    def test_thematic_fit_with_intensity(self):
        """Test thematic fit with different intensity levels."""
        high_intensity = ThematicProfile(
            theme=EncounterTheme.FIENDISH_CORRUPTION, intensity=2.0
        )
        low_intensity = ThematicProfile(
            theme=EncounterTheme.FIENDISH_CORRUPTION, intensity=0.5
        )

        # Good fit creature (fiend)
        fiend = MockCreature(creature_type="fiend")
        fit_high = high_intensity.calculate_thematic_fit(fiend)
        fit_low = low_intensity.calculate_thematic_fit(fiend)
        assert fit_high >= fit_low  # High intensity enhances good fits more

        # Poor fit creature (celestial)
        celestial = MockCreature(creature_type="celestial")
        fit_high = high_intensity.calculate_thematic_fit(celestial)
        fit_low = low_intensity.calculate_thematic_fit(celestial)
        assert fit_high <= fit_low  # High intensity penalizes poor fits more

    def test_thematic_fit_with_mixed_themes(self):
        """Test thematic fit when mixed themes are allowed."""
        strict_profile = ThematicProfile(
            theme=EncounterTheme.FEY_MYSTERY, allow_mixed=False
        )
        mixed_profile = ThematicProfile(
            theme=EncounterTheme.FEY_MYSTERY, allow_mixed=True
        )

        # Poor fit creature for fey theme
        construct = MockCreature(creature_type="construct")
        fit_strict = strict_profile.calculate_thematic_fit(construct)
        fit_mixed = mixed_profile.calculate_thematic_fit(construct)

        assert fit_mixed >= 0.3  # Mixed themes have minimum floor
        assert fit_mixed >= fit_strict  # Mixed should be >= strict

    def test_thematic_fit_bounds(self):
        """Test that thematic fit stays within bounds."""
        profile = ThematicProfile(theme=EncounterTheme.DRACONIC_POWER, intensity=2.0)

        # Perfect match should not exceed 2.0
        dragon = MockCreature(creature_type="dragon")
        fit = profile.calculate_thematic_fit(dragon)
        assert 0.0 <= fit <= 2.0

        # Poor match should not go below 0.0
        ooze = MockCreature(creature_type="ooze")
        fit = profile.calculate_thematic_fit(ooze)
        assert 0.0 <= fit <= 2.0


def test_integration_environmental_and_thematic():
    """Test integration between environmental and thematic profiles."""
    # Create profiles that complement each other
    env_profile = EnvironmentalProfile(
        environment=EnvironmentType.SWAMP, lighting="dim", weather="fog"
    )

    thematic_profile = ThematicProfile(
        theme=EncounterTheme.UNDEAD_HORROR, intensity=1.5
    )

    # Test creature that fits both profiles well
    swamp_undead = MockCreature(creature_type="undead", has_darkvision=True)

    env_fit = env_profile.calculate_creature_suitability(swamp_undead)
    theme_fit = thematic_profile.calculate_thematic_fit(swamp_undead)

    # Both should be good fits
    assert env_fit > 1.0
    assert theme_fit > 1.5

    # Test creature that fits neither profile well
    celestial_construct = MockCreature(creature_type="celestial")

    env_fit = env_profile.calculate_creature_suitability(celestial_construct)
    theme_fit = thematic_profile.calculate_thematic_fit(celestial_construct)

    # Both should be poor fits
    assert env_fit < 1.0  # Environmental fit for celestials in swamp
    assert theme_fit < 0.3  # Thematic fit for celestials in undead horror
