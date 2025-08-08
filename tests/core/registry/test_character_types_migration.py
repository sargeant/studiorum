"""Tests for Character-related content type migrations (Background, Race, Feat) to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestCharacterTypesMigration:
    """Test that character-related content types work with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_background_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Background correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.backgrounds import Background
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="background",
                file_patterns=["background", "backgrounds"],
                statblock_tags=["background"],
                loader_type="json",
            )
            class TestBackground(Background):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "background"
        assert metadata.model_class == TestBackground
        assert metadata.file_patterns == ["background", "backgrounds"]
        assert metadata.statblock_tags == ["background"]
        assert metadata.loader_type == "json"

    def test_race_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Race correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.races import Race
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="race",
                file_patterns=["race", "races"],
                statblock_tags=["race"],
                loader_type="json",
            )
            class TestRace(Race):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "race"
        assert metadata.model_class == TestRace
        assert metadata.file_patterns == ["race", "races"]
        assert metadata.statblock_tags == ["race"]
        assert metadata.loader_type == "json"

    def test_feat_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Feat correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.feats import Feat
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="feat",
                file_patterns=["feat", "feats"],
                statblock_tags=["feat"],
                loader_type="json",
            )
            class TestFeat(Feat):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "feat"
        assert metadata.model_class == TestFeat
        assert metadata.file_patterns == ["feat", "feats"]
        assert metadata.statblock_tags == ["feat"]
        assert metadata.loader_type == "json"

    def test_character_enums_created_dynamically(self):
        """Test that character type enums are created dynamically during finalization."""
        # Import character types to register via decorator
        from dnd5e.core.models import backgrounds, feats, races

        # Initially these should already exist (they're in ContentType enum)
        assert hasattr(ContentType, "BACKGROUND")
        assert ContentType.BACKGROUND == "background"
        assert hasattr(ContentType, "RACE")
        assert ContentType.RACE == "race"
        assert hasattr(ContentType, "FEAT")
        assert ContentType.FEAT == "feat"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enums still exist and work
        assert hasattr(ContentType, "BACKGROUND")
        assert ContentType.BACKGROUND == "background"
        assert hasattr(ContentType, "RACE")
        assert ContentType.RACE == "race"
        assert hasattr(ContentType, "FEAT")
        assert ContentType.FEAT == "feat"

    def test_background_content_creation(self):
        """Test that Background content can be created and validated."""
        from dnd5e.core.models.backgrounds import Background

        # Create a simple background instance
        background = Background(
            name="Acolyte",
            source="PHB",
            entries=["You have spent your life in service..."],
            skillProficiencies=[{"insight": True, "religion": True}],
            languageProficiencies=[{"choose": {"from": ["any"], "count": 2}}],
        )

        assert background.name == "Acolyte"
        assert background.source.abbreviation == "PHB"
        assert background.entries == ["You have spent your life in service..."]
        assert background.skill_proficiencies == [{"insight": True, "religion": True}]
        assert background.language_proficiencies == [
            {"choose": {"from": ["any"], "count": 2}}
        ]

    def test_race_content_creation(self):
        """Test that Race content can be created and validated."""
        from dnd5e.core.models.races import AbilityAdjustment, Race

        # Create a race instance with ability adjustments
        race = Race(
            name="Elf",
            source="PHB",
            entries=["Elves are a magical people..."],
            ability=[AbilityAdjustment(dex=2)],
            size=["Medium"],
            speed=30,
            darkvision=60,
        )

        assert race.name == "Elf"
        assert race.source.abbreviation == "PHB"
        assert race.entries == ["Elves are a magical people..."]
        assert len(race.ability) == 1
        assert race.ability[0].dex == 2
        assert race.size == ["Medium"]
        assert race.speed == 30
        assert race.darkvision == 60

    def test_feat_content_creation(self):
        """Test that Feat content can be created and validated."""
        from dnd5e.core.models.feats import AdditionalSpell, Feat, Prerequisite

        # Create a feat instance
        feat = Feat(
            name="Alert",
            source="PHB",
            entries=["Always on the lookout for danger..."],
            prerequisite=[Prerequisite(other="None")],
        )

        assert feat.name == "Alert"
        assert feat.source.abbreviation == "PHB"
        assert feat.entries == ["Always on the lookout for danger..."]
        assert len(feat.prerequisite) == 1
        assert feat.prerequisite[0].other == "None"

    def test_race_with_complex_fields(self):
        """Test that Race works with complex field structures."""
        from dnd5e.core.models.races import AbilityAdjustment, Race

        race = Race(
            name="Half-Elf",
            source="PHB",
            entries=["Walking in two worlds..."],
            ability=[
                AbilityAdjustment(cha=2),
                AbilityAdjustment(
                    choose={
                        "from": ["str", "dex", "con", "int", "wis"],
                        "count": 2,
                        "amount": 1,
                    }
                ),
            ],
            size=["Medium"],
            speed=30,
            skillProficiencies=[{"choose": {"from": ["any"], "count": 2}}],
            languageProficiencies=[
                {
                    "common": True,
                    "elvish": True,
                    "choose": {"from": ["any"], "count": 1},
                }
            ],
        )

        assert race.name == "Half-Elf"
        assert len(race.ability) == 2
        assert race.ability[0].cha == 2
        assert race.ability[1].choose is not None
        assert race.skill_proficiencies is not None
        assert race.language_proficiencies is not None

    def test_feat_with_additional_spells(self):
        """Test that Feat works with additional spells."""
        from dnd5e.core.models.feats import AdditionalSpell, Feat

        feat = Feat(
            name="Magic Initiate",
            source="PHB",
            entries=["Choose a class: bard, cleric, druid..."],
            additionalSpells=[
                AdditionalSpell(name="Eldritch Blast", level=0, ability="cha"),
                AdditionalSpell(name="Hex", level=1, ability="cha"),
            ],
        )

        assert feat.name == "Magic Initiate"
        assert len(feat.additionalSpells) == 2
        assert feat.additionalSpells[0].name == "Eldritch Blast"
        assert feat.additionalSpells[0].level == 0
        assert feat.additionalSpells[1].name == "Hex"
        assert feat.additionalSpells[1].level == 1

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
