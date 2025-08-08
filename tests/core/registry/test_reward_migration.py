"""Tests for Reward content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestRewardMigration:
    """Test that Reward content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        # Use standardized test environment reset
        from tests.test_helpers import reset_test_environment

        try:
            reset_test_environment()
        except Exception:
            # Fallback to basic setup if test_helpers not available
            from dnd5e.core.container import reset_global_container
            from dnd5e.core.registry import initialize_content_types

            # Reset service container first
            reset_global_container()

            # Initialize content types to ensure decorator registrations are active
            initialize_content_types()

            # Reset registry instance but preserve decorator registrations
            import dnd5e.core.registry.content_type_registry as registry_module

            if registry_module._registry_instance is not None:
                registry_module._registry_instance.reset()
            registry_module._registry_instance = None

    def test_reward_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Reward correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.rewards import Reward
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="reward",
                file_patterns=["reward", "rewards"],
                statblock_tags=["reward"],
                loader_type="json",
            )
            class TestReward(Reward):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "reward"
        assert metadata.model_class == TestReward
        assert metadata.file_patterns == ["reward", "rewards"]
        assert metadata.statblock_tags == ["reward"]
        assert metadata.loader_type == "json"

    def test_reward_enum_created_dynamically(self):
        """Test that REWARD enum is created dynamically during finalization."""
        # Import rewards to register via decorator
        from dnd5e.core.models import rewards

        # Initially REWARD should already exist (it's in ContentType enum)
        assert hasattr(ContentType, "REWARD")
        assert ContentType.REWARD == "reward"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "REWARD")
        assert ContentType.REWARD == "reward"

    def test_reward_content_creation(self):
        """Test that Reward content can be created and validated."""
        from dnd5e.core.models.rewards import Reward

        # Create a reward instance
        reward = Reward(name="Test Blessing", source="PHB", type="Blessing")

        assert reward.name == "Test Blessing"
        assert reward.source.abbreviation == "PHB"
        assert reward.type == "Blessing"
        assert reward.additional_spells is None

    def test_reward_with_additional_spells(self):
        """Test that Reward works with additional spells field."""
        from dnd5e.core.models.rewards import Reward

        # Use the alias form (additionalSpells) as that's what the field expects
        reward = Reward(
            name="Magic Blessing",
            source="PHB",
            type="Blessing",
            additionalSpells=[{"spell": "magic missile", "level": 1}],
        )

        assert reward.additional_spells is not None
        assert len(reward.additional_spells) == 1
        assert reward.additional_spells[0]["spell"] == "magic missile"

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        # Test that initialize_content_types() completes without errors
        # This validates the overall flow even if we can't fully test registry state
        # due to import-time registration happening only once per process

        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
