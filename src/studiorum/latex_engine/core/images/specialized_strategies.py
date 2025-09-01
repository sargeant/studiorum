"""Specialized placement strategies optimized for different content types.

This module implements content-type-specific placement strategies that build
upon the ContentAwarePlacementStrategy but with specialized logic for:
- Bestiary content (creature statblocks)
- Adventure content (narrative with maps/NPCs)
- Item collections (equipment, spells, etc.)
"""

from __future__ import annotations

from typing import Any

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.content_aware_strategy import (
    ContentAwarePlacementStrategy,
    PlacementWeights,
    UserPreferences,
)
from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageMetadata,
    PageContext,
    PlacementDecision,
    create_placement_factor,
)

logger = get_logger(__name__)


class BestiaryPlacementStrategy(ContentAwarePlacementStrategy):
    """Specialized strategy for bestiary content with creature statblocks.

    Optimizes for:
    - Creature portraits alongside statblocks
    - Habitat and behaviour illustrations
    - Wrapped text placement to maintain readability
    - Consistent sizing for comparison
    """

    def __init__(self, enable_caching: bool = True) -> None:
        """Initialize bestiary-optimized placement strategy."""
        # Bestiary-specific weights: prioritize surrounding context and image characteristics
        bestiary_weights = PlacementWeights(
            image_characteristics=0.30,  # Higher - creature images have specific characteristics
            content_flow=0.15,  # Lower - bestiary entries are more modular
            page_position=0.10,  # Lower - position less critical than content match
            surrounding_context=0.35,  # Higher - matching creature to statblock is crucial
            user_preferences=0.05,  # Lower - less flexibility for creatures
            technical_constraints=0.05,  # Lower - standardized creature layouts
        )

        super().__init__(weights=bestiary_weights, enable_caching=enable_caching)
        logger.debug(
            "Initialized BestiaryPlacementStrategy with creature-optimized weights"
        )

    async def determine_placement(
        self,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
        page_context: PageContext | None = None,
        user_prefs: UserPreferences | None = None,
    ) -> Result[PlacementDecision, str]:
        """Determine placement optimized for bestiary content."""
        # Validate that this is bestiary content
        if content_context.content_type != ContentType.BESTIARY:
            logger.warning(
                f"BestiaryPlacementStrategy used for non-bestiary content: "
                f"{content_context.content_type}"
            )

        # Get base decision from parent strategy
        result = await super().determine_placement(
            image, content_context, document_context, page_context, user_prefs
        )

        if result.is_error():
            return result

        decision = result.unwrap()

        # Apply bestiary-specific optimizations
        decision = await self._apply_bestiary_optimizations(
            decision, image, content_context
        )

        return Success(decision)

    async def _apply_bestiary_optimizations(
        self,
        decision: PlacementDecision,
        image: ImageMetadata,
        content_context: ContentContext,
    ) -> PlacementDecision:
        """Apply bestiary-specific placement optimizations."""
        # Detect creature images
        is_creature_image = (
            "creature" in image.content_hints
            or ImageCharacteristic.PORTRAIT in image.characteristics
            or any(
                hint in image.content_hints for hint in ["monster", "npc", "character"]
            )
        )

        if is_creature_image:
            # Creature images should be wrapped for readability with statblocks
            if decision.placement not in {
                ImagePlacement.WRAP_LEFT,
                ImagePlacement.WRAP_RIGHT,
            }:
                # Override placement for creatures
                decision.placement = ImagePlacement.WRAP_RIGHT
                decision.size = ImageSize.PORTRAIT

            # Always add bestiary-specific factor for creature images
            creature_factor = create_placement_factor(
                name="Bestiary Creature Optimization",
                weight=0.2,
                score=0.9,
                reasoning="Creature images optimized for wrapped placement alongside statblocks",
            )
            decision.factors.append(creature_factor)
            decision.overall_score = min(1.0, decision.overall_score + 0.1)

        # Handle habitat/environment images
        if any(
            hint in image.content_hints for hint in ["environment", "habitat", "lair"]
        ):
            # Environment images work well as full-width or at chapter/section breaks
            if decision.confidence < 0.7:  # Only override if not confident
                decision.placement = ImagePlacement.FULL_WIDTH
                decision.size = ImageSize.FULL_WIDTH

                habitat_factor = create_placement_factor(
                    name="Bestiary Habitat Optimization",
                    weight=0.15,
                    score=0.85,
                    reasoning="Habitat images benefit from full-width display for immersion",
                )
                decision.factors.append(habitat_factor)

        # Add bestiary metadata
        decision.metadata.update(
            {
                "specialized_strategy": "BestiaryPlacementStrategy",
                "creature_detected": is_creature_image,
                "content_optimization": "creature_statblock_layout",
            }
        )

        return decision


class AdventurePlacementStrategy(ContentAwarePlacementStrategy):
    """Specialized strategy for adventure content with narrative and exploration.

    Optimizes for:
    - Maps and location illustrations
    - NPC portraits and scenes
    - Atmospheric artwork for immersion
    - Flexible placement supporting narrative flow
    """

    def __init__(self, enable_caching: bool = True) -> None:
        """Initialize adventure-optimized placement strategy."""
        # Adventure-specific weights: prioritize content flow and artistic presentation
        adventure_weights = PlacementWeights(
            image_characteristics=0.25,  # Standard - varied image types
            content_flow=0.30,  # Higher - narrative flow is crucial
            page_position=0.20,  # Higher - dramatic positioning matters
            surrounding_context=0.15,  # Lower - more narrative flexibility
            user_preferences=0.05,  # Lower - prioritize narrative flow
            technical_constraints=0.05,  # Lower - accept some technical trade-offs for narrative
        )

        super().__init__(weights=adventure_weights, enable_caching=enable_caching)
        logger.debug(
            "Initialized AdventurePlacementStrategy with narrative-optimized weights"
        )

    async def determine_placement(
        self,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
        page_context: PageContext | None = None,
        user_prefs: UserPreferences | None = None,
    ) -> Result[PlacementDecision, str]:
        """Determine placement optimized for adventure content."""
        # Validate that this is adventure content
        if content_context.content_type != ContentType.ADVENTURE:
            logger.warning(
                f"AdventurePlacementStrategy used for non-adventure content: "
                f"{content_context.content_type}"
            )

        # Get base decision from parent strategy
        result = await super().determine_placement(
            image, content_context, document_context, page_context, user_prefs
        )

        if result.is_error():
            return result

        decision = result.unwrap()

        # Apply adventure-specific optimizations
        decision = await self._apply_adventure_optimizations(
            decision, image, content_context, document_context
        )

        return Success(decision)

    async def _apply_adventure_optimizations(
        self,
        decision: PlacementDecision,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
    ) -> PlacementDecision:
        """Apply adventure-specific placement optimizations."""
        # Detect map images
        is_map_image = (
            "map" in image.content_hints
            or "location" in image.content_hints
            or ImageCharacteristic.TECHNICAL in image.characteristics
        )

        if is_map_image:
            # Maps should be prominent and easily readable
            if image.dimensions and image.dimensions.aspect_ratio > 1.3:
                # Wide maps work well full-width
                decision.placement = ImagePlacement.FULL_WIDTH
                decision.size = ImageSize.FULL_WIDTH
            else:
                # Square/portrait maps can float
                decision.placement = ImagePlacement.FLOAT_TOP
                decision.size = ImageSize.LARGE

            map_factor = create_placement_factor(
                name="Adventure Map Optimization",
                weight=0.25,
                score=0.9,
                reasoning="Maps require prominent placement for navigation reference",
            )
            decision.factors.append(map_factor)
            decision.overall_score = min(1.0, decision.overall_score + 0.15)

        # Detect NPC/character images
        is_npc_image = (
            "npc" in image.content_hints
            or "character" in image.content_hints
            or ImageCharacteristic.PORTRAIT in image.characteristics
        )

        if is_npc_image:
            # NPCs work well wrapped with dialogue or description
            if decision.placement not in {
                ImagePlacement.WRAP_LEFT,
                ImagePlacement.WRAP_RIGHT,
            }:
                decision.placement = ImagePlacement.WRAP_LEFT  # Left for dialogue flow
                decision.size = ImageSize.PORTRAIT

                npc_factor = create_placement_factor(
                    name="Adventure NPC Optimization",
                    weight=0.2,
                    score=0.85,
                    reasoning="NPC images wrapped to accompany dialogue and descriptions",
                )
                decision.factors.append(npc_factor)

        # Detect atmospheric/scene images
        is_scene_image = (
            ImageCharacteristic.ARTISTIC in image.characteristics
            or "scene" in image.content_hints
            or "atmosphere" in image.content_hints
        )

        if is_scene_image:
            # Scene images should be dramatic - consider chapter/section positioning
            if (
                content_context.reading_flow_position == "start"
                or document_context.section_depth <= 2
            ):
                decision.placement = ImagePlacement.FLOAT_TOP
                decision.size = ImageSize.LARGE

                scene_factor = create_placement_factor(
                    name="Adventure Scene Optimization",
                    weight=0.15,
                    score=0.8,
                    reasoning="Scene images positioned for maximum atmospheric impact",
                )
                decision.factors.append(scene_factor)

        # Add adventure metadata
        decision.metadata.update(
            {
                "specialized_strategy": "AdventurePlacementStrategy",
                "map_detected": is_map_image,
                "npc_detected": is_npc_image,
                "scene_detected": is_scene_image,
                "content_optimization": "narrative_flow_layout",
            }
        )

        return decision


class ItemCollectionPlacementStrategy(ContentAwarePlacementStrategy):
    """Specialized strategy for item collections (equipment, spells, etc.).

    Optimizes for:
    - Consistent sizing for comparison
    - Efficient space usage with multiple items
    - Inline or small wrapped placement
    - Grid-like organization when possible
    """

    def __init__(self, enable_caching: bool = True) -> None:
        """Initialize item collection-optimized placement strategy."""
        # Item collection-specific weights: prioritize technical constraints and efficiency
        item_weights = PlacementWeights(
            image_characteristics=0.20,  # Lower - items are more standardized
            content_flow=0.15,  # Lower - collections are less narrative
            page_position=0.15,  # Lower - position less critical
            surrounding_context=0.20,  # Standard - context still matters
            user_preferences=0.10,  # Standard - some user flexibility
            technical_constraints=0.20,  # Higher - efficient layout important
        )

        super().__init__(weights=item_weights, enable_caching=enable_caching)
        logger.debug(
            "Initialized ItemCollectionPlacementStrategy with efficiency-optimized weights"
        )

    async def determine_placement(
        self,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
        page_context: PageContext | None = None,
        user_prefs: UserPreferences | None = None,
    ) -> Result[PlacementDecision, str]:
        """Determine placement optimized for item collections."""
        # Validate that this is item collection content
        if content_context.content_type != ContentType.ITEM_COLLECTION:
            logger.warning(
                f"ItemCollectionPlacementStrategy used for non-item content: "
                f"{content_context.content_type}"
            )

        # Get base decision from parent strategy
        result = await super().determine_placement(
            image, content_context, document_context, page_context, user_prefs
        )

        if result.is_error():
            return result

        decision = result.unwrap()

        # Apply item collection-specific optimizations
        decision = await self._apply_item_optimizations(
            decision, image, content_context
        )

        return Success(decision)

    async def _apply_item_optimizations(
        self,
        decision: PlacementDecision,
        image: ImageMetadata,
        content_context: ContentContext,
    ) -> PlacementDecision:
        """Apply item collection-specific placement optimizations."""
        # Detect item images
        is_item_image = (
            "item" in image.content_hints
            or "equipment" in image.content_hints
            or "weapon" in image.content_hints
            or "armor" in image.content_hints
            or ImageCharacteristic.ICON in image.characteristics
        )

        # Count nearby items for collection optimization
        # Include both generic terms and specific D&D weapon/armor/item names
        item_keywords = [
            # Generic terms
            "item",
            "equipment",
            "weapon",
            "armor",
            "gear",
            "tool",
            # Weapons - melee
            "sword",
            "axe",
            "mace",
            "hammer",
            "dagger",
            "knife",
            "blade",
            "spear",
            "lance",
            "halberd",
            "glaive",
            "scimitar",
            "rapier",
            "shortsword",
            "longsword",
            "greatsword",
            "battleaxe",
            "handaxe",
            "warhammer",
            "maul",
            "club",
            "mace",
            "flail",
            "morningstar",
            "pike",
            "trident",
            "whip",
            "scythe",
            "sickle",
            # Weapons - ranged
            "bow",
            "crossbow",
            "longbow",
            "shortbow",
            "sling",
            "dart",
            "javelin",
            "arrow",
            "bolt",
            "quiver",
            # Armor
            "helm",
            "helmet",
            "breastplate",
            "chainmail",
            "plate",
            "leather",
            "studded",
            "scale",
            "splint",
            "ring",
            "padded",
            "shield",
            "gauntlets",
            "boots",
            "greaves",
            "pauldrons",
            # Magic items & accessories
            "ring",
            "amulet",
            "pendant",
            "bracelet",
            "cloak",
            "robe",
            "staff",
            "wand",
            "rod",
            "orb",
            "crystal",
            "gem",
            "stone",
            "potion",
            "scroll",
            "tome",
            "book",
            "coin",
            "gold",
            "silver",
            # Tools & gear
            "rope",
            "torch",
            "lantern",
            "backpack",
            "bag",
            "chest",
            "lock",
            "key",
            "pick",
            "thieves",
            "tools",
            "kit",
            "supplies",
        ]

        nearby_item_count = len(
            [
                hint
                for hint in content_context.nearby_images
                if any(item_hint in hint.lower() for item_hint in item_keywords)
            ]
        )

        if is_item_image:
            if nearby_item_count > 2:
                # Multiple items - use consistent small sizing
                decision.placement = ImagePlacement.INLINE
                decision.size = ImageSize.SMALL

                collection_factor = create_placement_factor(
                    name="Item Collection Optimization",
                    weight=0.25,
                    score=0.85,
                    reasoning=f"Multiple items ({nearby_item_count}) optimized for consistent comparison",
                )
                decision.factors.append(collection_factor)
            else:
                # Single or few items - can be larger
                decision.placement = ImagePlacement.WRAP_RIGHT
                decision.size = ImageSize.MEDIUM

                single_item_factor = create_placement_factor(
                    name="Individual Item Optimization",
                    weight=0.2,
                    score=0.75,
                    reasoning="Individual item can be larger for detail visibility",
                )
                decision.factors.append(single_item_factor)

        # Detect spell/ability icons (but not if already processed as item)
        is_spell_image = (
            "spell" in image.content_hints or "ability" in image.content_hints
        ) and not is_item_image  # Don't override item processing

        if is_spell_image:
            # Spells often work well inline or in margins
            if (
                image.dimensions
                and min(image.dimensions.width, image.dimensions.height) < 100
            ):
                # Small spell icons can go inline or margin
                decision.placement = ImagePlacement.INLINE
                decision.size = ImageSize.SMALL
            else:
                # Larger spell illustrations
                decision.placement = ImagePlacement.WRAP_LEFT
                decision.size = ImageSize.MEDIUM

            spell_factor = create_placement_factor(
                name="Spell/Ability Optimization",
                weight=0.15,
                score=0.8,
                reasoning="Spell images optimized for quick reference alongside descriptions",
            )
            decision.factors.append(spell_factor)

        # Handle tables and lists in item collections
        if "table" in content_context.structural_elements:
            # Tables need careful image placement
            decision.placement = ImagePlacement.FLOAT_TOP
            decision.size = ImageSize.MEDIUM

            table_factor = create_placement_factor(
                name="Item Table Optimization",
                weight=0.2,
                score=0.7,
                reasoning="Images with tables require float placement to avoid layout conflicts",
            )
            decision.factors.append(table_factor)

        # Add item collection metadata
        decision.metadata.update(
            {
                "specialized_strategy": "ItemCollectionPlacementStrategy",
                "item_detected": is_item_image,
                "spell_detected": is_spell_image,
                "nearby_items": nearby_item_count,
                "content_optimization": "efficient_collection_layout",
            }
        )

        return decision


class SpellCollectionPlacementStrategy(ItemCollectionPlacementStrategy):
    """Specialized strategy for spell collections, inheriting from item collections.

    Optimizes for:
    - Spell icons and visual components
    - School-of-magic illustrations
    - Consistent sizing for spell comparison
    - Integration with spell statistics
    """

    def __init__(self, enable_caching: bool = True) -> None:
        """Initialize spell collection-optimized placement strategy."""
        super().__init__(enable_caching=enable_caching)
        logger.debug("Initialized SpellCollectionPlacementStrategy")

    async def _apply_item_optimizations(
        self,
        decision: PlacementDecision,
        image: ImageMetadata,
        content_context: ContentContext,
    ) -> PlacementDecision:
        """Apply spell collection-specific optimizations."""
        # Get base item optimizations
        decision = await super()._apply_item_optimizations(
            decision, image, content_context
        )

        # Detect spell school images
        is_school_image = any(
            school in image.content_hints
            for school in [
                "evocation",
                "illusion",
                "enchantment",
                "abjuration",
                "transmutation",
                "divination",
                "conjuration",
                "necromancy",
            ]
        )

        if is_school_image:
            # School illustrations can be more prominent
            decision.placement = ImagePlacement.FLOAT_HERE
            decision.size = ImageSize.MEDIUM

            school_factor = create_placement_factor(
                name="Spell School Optimization",
                weight=0.2,
                score=0.9,
                reasoning="Spell school illustrations benefit from prominent float placement",
            )
            decision.factors.append(school_factor)

        # Detect spell component images
        is_component_image = (
            "component" in image.content_hints
            or "material" in image.content_hints
            or "focus" in image.content_hints
        )

        if is_component_image:
            # Components work well inline or in margins
            decision.placement = ImagePlacement.INLINE
            decision.size = ImageSize.SMALL

            component_factor = create_placement_factor(
                name="Spell Component Optimization",
                weight=0.15,
                score=0.8,
                reasoning="Spell components optimized for inline reference",
            )
            decision.factors.append(component_factor)

        # Update metadata
        decision.metadata.update(
            {
                "specialized_strategy": "SpellCollectionPlacementStrategy",
                "spell_school_detected": is_school_image,
                "component_detected": is_component_image,
                "content_optimization": "spell_reference_layout",
            }
        )

        return decision


# Factory function for creating appropriate strategy
def create_specialized_strategy(
    content_type: ContentType, enable_caching: bool = True
) -> ContentAwarePlacementStrategy:
    """Create the appropriate specialized strategy for content type.

    Args:
        content_type: Type of content to optimize for
        enable_caching: Whether to enable result caching

    Returns:
        Specialized placement strategy instance
    """
    strategy_map = {
        ContentType.BESTIARY: BestiaryPlacementStrategy,
        ContentType.ADVENTURE: AdventurePlacementStrategy,
        ContentType.ITEM_COLLECTION: ItemCollectionPlacementStrategy,
        ContentType.SPELL_COLLECTION: SpellCollectionPlacementStrategy,
    }

    strategy_class = strategy_map.get(content_type, ContentAwarePlacementStrategy)
    return strategy_class(enable_caching=enable_caching)
