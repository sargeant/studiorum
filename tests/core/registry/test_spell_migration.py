"""Tests for Spell content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestSpellMigration:
    """Test that Spell content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_spell_decorator_functionality(self):
        """Test that the decorator works correctly with a test spell class."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.spells import Spell
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="test_spell_decorator",
                file_patterns=["test_spell"],
                statblock_tags=["test_spell"],
                loader_type="json",
            )
            class TestSpell(Spell):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "test_spell_decorator"
        assert metadata.model_class == TestSpell
        assert metadata.file_patterns == ["test_spell"]
        assert metadata.statblock_tags == ["test_spell"]
        assert metadata.loader_type == "json"

    def test_spell_enum_already_exists(self):
        """Test that SPELL enum already exists in ContentType."""
        # Import spells to register via decorator
        from dnd5e.core.models import spells

        # SPELL should already exist in ContentType enum
        assert hasattr(ContentType, "SPELL")
        assert ContentType.SPELL == "spell"

        # Initialize should work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "SPELL")
        assert ContentType.SPELL == "spell"

    def test_spell_content_creation(self):
        """Test that Spell content can be created and validated."""
        from dnd5e.core.models.spells import (
            Spell,
            SpellComponent,
            SpellDuration,
            SpellRange,
            SpellTime,
        )

        # Create a spell instance
        spell = Spell(
            name="Test Cantrip",
            source="PHB",
            level=0,
            school="Evocation",
            time=[SpellTime(unit="action")],
            range=SpellRange(type="point"),
            components=SpellComponent(verbal=True),
            duration=[SpellDuration(type="instant")],
            entries=["A simple test spell."],
        )

        assert spell.name == "Test Cantrip"
        assert spell.source.abbreviation == "PHB"
        assert spell.level == 0
        assert spell.school == "Evocation"
        assert len(spell.casting_time) == 1
        assert spell.casting_time[0].unit == "action"

    def test_spell_with_complex_data(self):
        """Test that Spell works with complex spell data."""
        from dnd5e.core.models.spells import (
            Spell,
            SpellComponent,
            SpellDuration,
            SpellRange,
            SpellTime,
        )

        # Create a more complex spell
        spell = Spell(
            name="Fireball",
            source="PHB",
            level=3,
            school="V",  # Should be parsed to "Evocation"
            time=[SpellTime(unit="action")],
            range=SpellRange(type="point"),
            components=SpellComponent(v=True, s=True, m="A tiny ball of bat guano"),
            duration=[SpellDuration(type="instant")],
            entries=["A bright streak flashes from your pointing finger..."],
            entriesHigherLevel=[
                "When you cast this spell using a spell slot of 4th level or higher..."
            ],
        )

        assert spell.school == "Evocation"  # Should be parsed from "V"
        assert spell.components.verbal is True
        assert spell.components.somatic is True
        assert spell.components.material == "A tiny ball of bat guano"
        assert spell.higher_level is not None
        assert len(spell.higher_level) == 1

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        # Test that initialize_content_types() completes without errors
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
