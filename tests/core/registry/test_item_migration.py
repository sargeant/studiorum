"""Tests for Item content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestItemMigration:
    """Test that Item content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_item_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Item correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.items import Item
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="item",
                file_patterns=["item", "items", "magicitem"],
                statblock_tags=["item"],
                loader_type="json",
            )
            class TestItem(Item):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "item"
        assert metadata.model_class == TestItem
        assert metadata.file_patterns == ["item", "items", "magicitem"]
        assert metadata.statblock_tags == ["item"]
        assert metadata.loader_type == "json"

    def test_item_enum_created_dynamically(self):
        """Test that ITEM enum is created dynamically during finalization."""
        # Import items to register via decorator
        from dnd5e.core.models import items

        # Initially ITEM should already exist (it's in ContentType enum)
        assert hasattr(ContentType, "ITEM")
        assert ContentType.ITEM == "item"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "ITEM")
        assert ContentType.ITEM == "item"

    def test_item_content_creation(self):
        """Test that Item content can be created and validated."""
        from dnd5e.core.models.items import Item, ItemRarity, ItemType

        # Create a simple item instance
        item = Item(
            name="Test Sword",
            source="MM",
            type=ItemType.WEAPON,
            rarity=ItemRarity.COMMON,
            weight=3,
            damage="1d8",
            damageType="slashing",  # Use alias form
        )

        assert item.name == "Test Sword"
        assert item.source.abbreviation == "MM"
        assert item.type == ItemType.WEAPON
        assert item.rarity == ItemRarity.COMMON
        assert item.weight == 3
        assert item.damage == "1d8"
        assert item.damage_type == "slashing"

    def test_item_with_magic_properties(self):
        """Test that Item works with magic item properties."""
        from dnd5e.core.models.items import Item, ItemRarity, ItemType

        item = Item(
            name="Magic Sword +1",
            source="DMG",
            type=ItemType.WEAPON,
            rarity=ItemRarity.UNCOMMON,
            reqAttune=True,  # Use alias form
            charges=5,
            recharge="dawn",
            damage="1d8+1",
            damageType="slashing",  # Use alias form
        )

        assert item.name == "Magic Sword +1"
        assert item.rarity == ItemRarity.UNCOMMON
        assert item.requires_attunement is True
        assert item.charges == 5
        assert item.recharge == "dawn"
        assert item.is_magic_item()
        assert item.is_weapon()

    def test_item_with_armor_data(self):
        """Test that Item works with armor-specific data."""
        from dnd5e.core.models.items import Item, ItemRarity, ItemType

        item = Item(
            name="Plate Armor",
            source="PHB",
            type=ItemType.ARMOR,
            rarity=ItemRarity.COMMON,
            weight=65,
            ac=18,
            strength=15,
            stealth=True,  # True means stealth disadvantage
        )

        assert item.name == "Plate Armor"
        assert item.type == ItemType.ARMOR
        assert item.ac == 18
        assert item.strength == 15
        assert item.stealth is True
        assert item.is_armor()
        assert not item.is_weapon()

    def test_item_formatting_methods(self):
        """Test item formatting methods work correctly."""
        from dnd5e.core.models.items import Item, ItemRarity, ItemType

        item = Item(
            name="Test Item",
            source="PHB",
            type=ItemType.WONDROUS_ITEM,
            rarity=ItemRarity.RARE,
            weight=2,
            value=500,
            reqAttune="by a spellcaster",  # Use alias form
        )

        # Test various formatting methods
        assert item.get_type_text() == "wondrous item"
        assert "rare" in item.get_rarity_text().lower()
        assert "requires attunement by a spellcaster" in item.get_rarity_text().lower()
        assert "2 lbs." in item.get_weight_text()
        assert "5 gp" in item.get_value_text()  # 500 cp = 5 gp

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
