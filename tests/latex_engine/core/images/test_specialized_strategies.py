"""Tests for specialized placement strategies.

This module tests the content-type-specific placement strategies that build
upon the ContentAwarePlacementStrategy with specialized optimizations.
"""

from pathlib import Path

import pytest

from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
)
from studiorum.latex_engine.core.images.specialized_strategies import (
    AdventurePlacementStrategy,
    BestiaryPlacementStrategy,
    ItemCollectionPlacementStrategy,
    SpellCollectionPlacementStrategy,
    create_specialized_strategy,
)


class TestBestiaryPlacementStrategy:
    """Test BestiaryPlacementStrategy for creature content."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = BestiaryPlacementStrategy()

        # Create creature image metadata
        self.creature_image = ImageMetadata(
            path="/test/dragon.png",
            dimensions=ImageDimensions.from_dimensions(400, 600),
            characteristics=[ImageCharacteristic.PORTRAIT],
            content_hints=["creature", "dragon"],
            quality_score=0.8,
        )

        # Create bestiary content context
        self.bestiary_context = ContentContext(
            content_type=ContentType.BESTIARY,
            section_title="Ancient Dragons",
            word_count=300,
            structural_elements=["statblock"],
        )

        self.document_context = DocumentContext(
            total_pages=50,
            current_page=10,
        )

    def test_initialization(self):
        """Test bestiary strategy initialization."""
        strategy = BestiaryPlacementStrategy()

        # Should have bestiary-optimized weights
        assert (
            strategy.weights.surrounding_context > 0.3
        )  # Higher for creature matching
        assert (
            strategy.weights.image_characteristics > 0.25
        )  # Higher for creature characteristics
        assert strategy.weights.content_flow < 0.2  # Lower for modular entries

    @pytest.mark.asyncio
    async def test_creature_image_optimization(self):
        """Test that creature images get optimized for wrapped placement."""
        result = await self.strategy.determine_placement(
            self.creature_image,
            self.bestiary_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Creature images should prefer wrapped placement
        assert decision.placement in {
            ImagePlacement.WRAP_LEFT,
            ImagePlacement.WRAP_RIGHT,
        }
        assert decision.size == ImageSize.PORTRAIT

        # Should have bestiary-specific optimization factor
        factor_names = [f.name for f in decision.factors]
        assert "Bestiary Creature Optimization" in factor_names

    @pytest.mark.asyncio
    async def test_habitat_image_optimization(self):
        """Test habitat/environment image handling."""
        habitat_image = ImageMetadata(
            path="/test/dragon_lair.png",
            dimensions=ImageDimensions.from_dimensions(800, 400),
            characteristics=[ImageCharacteristic.ARTISTIC],
            content_hints=["environment", "habitat", "lair"],
        )

        result = await self.strategy.determine_placement(
            habitat_image,
            self.bestiary_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Habitat images should be full-width for immersion
        assert decision.placement == ImagePlacement.FULL_WIDTH
        assert decision.size == ImageSize.FULL_WIDTH

    @pytest.mark.asyncio
    async def test_non_bestiary_content_warning(self):
        """Test warning when using bestiary strategy on non-bestiary content."""
        adventure_context = ContentContext(
            content_type=ContentType.ADVENTURE,
            section_title="The Dragon's Lair",
        )

        # Should still work but log a warning
        result = await self.strategy.determine_placement(
            self.creature_image,
            adventure_context,
            self.document_context,
        )

        assert result.is_success()

    @pytest.mark.asyncio
    async def test_bestiary_metadata_addition(self):
        """Test that bestiary-specific metadata is added."""
        result = await self.strategy.determine_placement(
            self.creature_image,
            self.bestiary_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        assert decision.metadata["specialized_strategy"] == "BestiaryPlacementStrategy"
        assert decision.metadata["creature_detected"] is True
        assert decision.metadata["content_optimization"] == "creature_statblock_layout"


class TestAdventurePlacementStrategy:
    """Test AdventurePlacementStrategy for narrative content."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = AdventurePlacementStrategy()

        self.map_image = ImageMetadata(
            path="/test/dungeon_map.png",
            dimensions=ImageDimensions.from_dimensions(1000, 600),
            characteristics=[ImageCharacteristic.TECHNICAL],
            content_hints=["map", "location"],
        )

        self.adventure_context = ContentContext(
            content_type=ContentType.ADVENTURE,
            section_title="The Lost Temple",
            word_count=800,
            reading_flow_position="start",
        )

        self.document_context = DocumentContext()

    def test_initialization(self):
        """Test adventure strategy initialization."""
        strategy = AdventurePlacementStrategy()

        # Should prioritize narrative flow and dramatic positioning
        assert strategy.weights.content_flow > 0.25  # Higher for narrative flow
        assert strategy.weights.page_position > 0.15  # Higher for dramatic positioning

    @pytest.mark.asyncio
    async def test_map_image_optimization(self):
        """Test map image placement optimization."""
        result = await self.strategy.determine_placement(
            self.map_image,
            self.adventure_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Wide maps should be full-width
        assert decision.placement == ImagePlacement.FULL_WIDTH
        assert decision.size == ImageSize.FULL_WIDTH

        # Should have map optimization factor
        factor_names = [f.name for f in decision.factors]
        assert "Adventure Map Optimization" in factor_names

    @pytest.mark.asyncio
    async def test_npc_image_optimization(self):
        """Test NPC/character image handling."""
        npc_image = ImageMetadata(
            path="/test/sage.png",
            dimensions=ImageDimensions.from_dimensions(400, 600),
            characteristics=[ImageCharacteristic.PORTRAIT],
            content_hints=["npc", "character"],
        )

        result = await self.strategy.determine_placement(
            npc_image,
            self.adventure_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # NPCs should be wrapped for dialogue flow
        assert decision.placement == ImagePlacement.WRAP_LEFT  # Left for dialogue flow
        assert decision.size == ImageSize.PORTRAIT

    @pytest.mark.asyncio
    async def test_scene_image_optimization(self):
        """Test atmospheric scene image handling."""
        scene_image = ImageMetadata(
            path="/test/temple_entrance.png",
            characteristics=[ImageCharacteristic.ARTISTIC],
            content_hints=["scene", "atmosphere"],
        )

        context_at_start = ContentContext(
            content_type=ContentType.ADVENTURE,
            reading_flow_position="start",
        )

        result = await self.strategy.determine_placement(
            scene_image,
            context_at_start,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Scene images at section start should be dramatic
        assert decision.placement == ImagePlacement.FLOAT_TOP
        assert decision.size == ImageSize.LARGE

    @pytest.mark.asyncio
    async def test_adventure_metadata_addition(self):
        """Test adventure-specific metadata."""
        result = await self.strategy.determine_placement(
            self.map_image,
            self.adventure_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        assert decision.metadata["specialized_strategy"] == "AdventurePlacementStrategy"
        assert decision.metadata["map_detected"] is True
        assert decision.metadata["content_optimization"] == "narrative_flow_layout"


class TestItemCollectionPlacementStrategy:
    """Test ItemCollectionPlacementStrategy for item catalogs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = ItemCollectionPlacementStrategy()

        self.item_image = ImageMetadata(
            path="/test/sword.png",
            dimensions=ImageDimensions.from_dimensions(300, 400),
            characteristics=[ImageCharacteristic.ICON],
            content_hints=["item", "weapon"],
        )

        self.item_context = ContentContext(
            content_type=ContentType.ITEM_COLLECTION,
            section_title="Magic Weapons",
            word_count=200,
            nearby_images=["axe.png", "bow.png", "dagger.png"],  # Multiple items
        )

        self.document_context = DocumentContext()

    def test_initialization(self):
        """Test item collection strategy initialization."""
        strategy = ItemCollectionPlacementStrategy()

        # Should prioritize technical constraints and efficiency
        assert strategy.weights.technical_constraints > 0.15
        assert strategy.weights.content_flow < 0.2  # Lower for collections

    @pytest.mark.asyncio
    async def test_multiple_items_optimization(self):
        """Test optimization for multiple items in collection."""
        result = await self.strategy.determine_placement(
            self.item_image,
            self.item_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Multiple items should use consistent small sizing
        assert decision.placement == ImagePlacement.INLINE
        assert decision.size == ImageSize.SMALL

        # Should have collection optimization factor
        factor_names = [f.name for f in decision.factors]
        assert "Item Collection Optimization" in factor_names

    @pytest.mark.asyncio
    async def test_single_item_optimization(self):
        """Test optimization for individual items."""
        single_item_context = ContentContext(
            content_type=ContentType.ITEM_COLLECTION,
            section_title="Legendary Sword",
            word_count=300,
            nearby_images=[],  # No other items
        )

        result = await self.strategy.determine_placement(
            self.item_image,
            single_item_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Individual items can be larger
        assert decision.placement == ImagePlacement.WRAP_RIGHT
        assert decision.size == ImageSize.MEDIUM

    @pytest.mark.asyncio
    async def test_table_integration_optimization(self):
        """Test item placement with tables."""
        table_context = ContentContext(
            content_type=ContentType.ITEM_COLLECTION,
            structural_elements=["table"],
        )

        result = await self.strategy.determine_placement(
            self.item_image,
            table_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Tables need float placement to avoid conflicts
        assert decision.placement == ImagePlacement.FLOAT_TOP
        assert decision.size == ImageSize.MEDIUM

    @pytest.mark.asyncio
    async def test_item_metadata_addition(self):
        """Test item collection metadata."""
        result = await self.strategy.determine_placement(
            self.item_image,
            self.item_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        assert (
            decision.metadata["specialized_strategy"]
            == "ItemCollectionPlacementStrategy"
        )
        assert decision.metadata["item_detected"] is True
        assert decision.metadata["nearby_items"] == 3  # From nearby_images


class TestSpellCollectionPlacementStrategy:
    """Test SpellCollectionPlacementStrategy for spell collections."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = SpellCollectionPlacementStrategy()

        self.spell_image = ImageMetadata(
            path="/test/fireball.png",
            characteristics=[ImageCharacteristic.ICON],
            content_hints=["spell", "evocation"],
        )

        self.spell_context = ContentContext(
            content_type=ContentType.SPELL_COLLECTION,
            section_title="Evocation Spells",
        )

        self.document_context = DocumentContext()

    @pytest.mark.asyncio
    async def test_spell_school_optimization(self):
        """Test spell school image optimization."""
        school_image = ImageMetadata(
            path="/test/evocation_school.png",
            content_hints=["evocation", "spell"],
            characteristics=[ImageCharacteristic.ARTISTIC],
        )

        result = await self.strategy.determine_placement(
            school_image,
            self.spell_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # School illustrations should be prominent
        assert decision.placement == ImagePlacement.FLOAT_HERE
        assert decision.size == ImageSize.MEDIUM

        # Should have school optimization factor
        factor_names = [f.name for f in decision.factors]
        assert "Spell School Optimization" in factor_names

    @pytest.mark.asyncio
    async def test_component_image_optimization(self):
        """Test spell component image handling."""
        component_image = ImageMetadata(
            path="/test/bat_wing.png",
            content_hints=["component", "material"],
        )

        result = await self.strategy.determine_placement(
            component_image,
            self.spell_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Components should be inline for reference
        assert decision.placement == ImagePlacement.INLINE
        assert decision.size == ImageSize.SMALL

    @pytest.mark.asyncio
    async def test_spell_metadata_addition(self):
        """Test spell collection metadata."""
        result = await self.strategy.determine_placement(
            self.spell_image,
            self.spell_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        assert (
            decision.metadata["specialized_strategy"]
            == "SpellCollectionPlacementStrategy"
        )
        assert decision.metadata["content_optimization"] == "spell_reference_layout"


class TestSpecializedStrategyFactory:
    """Test the factory function for creating specialized strategies."""

    def test_create_bestiary_strategy(self):
        """Test creating bestiary strategy."""
        strategy = create_specialized_strategy(ContentType.BESTIARY)
        assert isinstance(strategy, BestiaryPlacementStrategy)

    def test_create_adventure_strategy(self):
        """Test creating adventure strategy."""
        strategy = create_specialized_strategy(ContentType.ADVENTURE)
        assert isinstance(strategy, AdventurePlacementStrategy)

    def test_create_item_collection_strategy(self):
        """Test creating item collection strategy."""
        strategy = create_specialized_strategy(ContentType.ITEM_COLLECTION)
        assert isinstance(strategy, ItemCollectionPlacementStrategy)

    def test_create_spell_collection_strategy(self):
        """Test creating spell collection strategy."""
        strategy = create_specialized_strategy(ContentType.SPELL_COLLECTION)
        assert isinstance(strategy, SpellCollectionPlacementStrategy)

    def test_create_fallback_strategy(self):
        """Test creating strategy for unknown content type."""
        from studiorum.latex_engine.core.images.content_aware_strategy import (
            ContentAwarePlacementStrategy,
        )

        strategy = create_specialized_strategy(ContentType.UNKNOWN)
        assert isinstance(strategy, ContentAwarePlacementStrategy)
        assert not isinstance(strategy, BestiaryPlacementStrategy)

    def test_create_with_caching_disabled(self):
        """Test creating strategy with caching disabled."""
        strategy = create_specialized_strategy(
            ContentType.BESTIARY, enable_caching=False
        )
        assert isinstance(strategy, BestiaryPlacementStrategy)
        assert strategy.enable_caching is False


class TestStrategyInheritance:
    """Test that specialized strategies properly inherit base functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_image = ImageMetadata(path="/test/image.png")
        self.base_context = ContentContext(content_type=ContentType.UNKNOWN)
        self.base_document = DocumentContext()

    @pytest.mark.asyncio
    async def test_bestiary_inherits_base_factors(self):
        """Test that bestiary strategy includes base factor analysis."""
        strategy = BestiaryPlacementStrategy()

        result = await strategy.determine_placement(
            self.base_image,
            self.base_context,
            self.base_document,
        )

        assert result.is_success()
        decision = result.value

        # Should have all base factors
        factor_names = [f.name for f in decision.factors]
        base_factors = [
            "Image Characteristics",
            "Content Flow",
            "Page Position",
            "Surrounding Context",
            "User Preferences",
            "Technical Constraints",
        ]

        for base_factor in base_factors:
            assert base_factor in factor_names

    @pytest.mark.asyncio
    async def test_adventure_inherits_base_factors(self):
        """Test that adventure strategy includes base factor analysis."""
        strategy = AdventurePlacementStrategy()

        result = await strategy.determine_placement(
            self.base_image,
            self.base_context,
            self.base_document,
        )

        assert result.is_success()
        decision = result.value

        # Should have confidence calculation
        assert 0.0 <= decision.confidence <= 1.0
        assert decision.overall_score >= 0.0

    @pytest.mark.asyncio
    async def test_item_strategy_weight_inheritance(self):
        """Test that item strategy has properly normalized weights."""
        strategy = ItemCollectionPlacementStrategy()

        # Weights should still sum to 1.0 after customization
        total_weight = (
            strategy.weights.image_characteristics
            + strategy.weights.content_flow
            + strategy.weights.page_position
            + strategy.weights.surrounding_context
            + strategy.weights.user_preferences
            + strategy.weights.technical_constraints
        )

        assert total_weight == pytest.approx(1.0, abs=0.001)
