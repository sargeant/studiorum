"""Advanced content preprocessing for enhanced LaTeX rendering.

This module provides content processors that prepare D&D content for rendering
by extracting, organizing, and transforming data structures for optimal output.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from ...core.models.content import BaseContent, ContentType
from ...core.models.creatures import Creature
from ...core.models.items import Item
from ...core.models.spells import Spell
from ..base import RenderContext


class ContentProcessor(ABC):
    """Abstract base class for content processors."""

    @abstractmethod
    def process(self, content: BaseContent, context: RenderContext) -> dict[str, Any]:
        """Process content and return enhanced data for rendering.

        Args:
            content: Content to process
            context: Rendering context

        Returns:
            Dictionary of processed data
        """
        pass

    @abstractmethod
    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports the given content type.

        Args:
            content_type: Content type to check

        Returns:
            True if processor supports the content type
        """
        pass


class SpellProcessor(ContentProcessor):
    """Processor for spell content with enhanced parsing."""

    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports spell content."""
        return content_type == ContentType.SPELL

    def process(self, content: BaseContent, context: RenderContext) -> dict[str, Any]:
        """Process spell content for enhanced rendering.

        Args:
            content: Spell to process
            context: Rendering context

        Returns:
            Enhanced spell data
        """
        if not isinstance(content, Spell):
            raise ValueError(f"Expected Spell, got {type(content)}")

        processed_data = {
            "spell_level_ordinal": self._get_spell_level_ordinal(content.level),
            "is_cantrip": content.level == 0,
            "is_ritual": self._is_ritual_spell(content),
            "damage_dice": self._extract_damage_dice(content),
            "spell_tags": self._extract_spell_tags(content),
            "verbal_component": self._has_verbal_component(content),
            "somatic_component": self._has_somatic_component(content),
            "material_component": self._extract_material_component(content),
            "concentration_required": self._requires_concentration(content),
            "upcast_effects": self._extract_upcast_effects(content),
            "class_availability": self._get_class_availability(content),
        }

        return processed_data

    def _get_spell_level_ordinal(self, level: int) -> str:
        """Get ordinal text for spell level."""
        ordinals = {
            0: "Cantrip",
            1: "1st",
            2: "2nd",
            3: "3rd",
            4: "4th",
            5: "5th",
            6: "6th",
            7: "7th",
            8: "8th",
            9: "9th",
        }
        return ordinals.get(level, f"{level}th")

    def _is_ritual_spell(self, spell: Spell) -> bool:
        """Check if spell can be cast as a ritual."""
        # This would need implementation based on actual data structure
        return False

    def _extract_damage_dice(self, spell: Spell) -> str | None:
        """Extract damage dice from spell description."""
        if not hasattr(spell, "entries") or not spell.entries:
            return None

        # Look for damage dice patterns in entries
        dice_pattern = r"(\d+d\d+(?:\s*[+\-]\s*\d+)?)"
        for entry in spell.entries:
            if isinstance(entry, str):
                matches = re.findall(dice_pattern, entry)
                if matches:
                    return matches[0]

        return None

    def _extract_spell_tags(self, spell: Spell) -> list[str]:
        """Extract semantic tags from spell."""
        tags = []

        # Add damage type tags
        if hasattr(spell, "damage_inflict") and spell.damage_inflict:
            tags.extend(spell.damage_inflict)

        # Add mechanic tags
        if hasattr(spell, "saving_throw") and spell.saving_throw:
            tags.append("save")

        if hasattr(spell, "spell_attack") and spell.spell_attack:
            tags.append("attack")

        return tags

    def _has_verbal_component(self, spell: Spell) -> bool:
        """Check if spell has verbal component."""
        if hasattr(spell.components, "verbal"):
            return spell.components.verbal
        elif isinstance(spell.components, dict):
            return spell.components.get("v", False)
        return False

    def _has_somatic_component(self, spell: Spell) -> bool:
        """Check if spell has somatic component."""
        if hasattr(spell.components, "somatic"):
            return spell.components.somatic
        elif isinstance(spell.components, dict):
            return spell.components.get("s", False)
        return False

    def _extract_material_component(self, spell: Spell) -> str | None:
        """Extract material component description."""
        if hasattr(spell.components, "material"):
            material = spell.components.material
            if isinstance(material, str):
                return material
        elif isinstance(spell.components, dict):
            material = spell.components.get("m")
            if isinstance(material, str):
                return material
        return None

    def _requires_concentration(self, spell: Spell) -> bool:
        """Check if spell requires concentration."""
        if not spell.duration:
            return False

        for duration_entry in spell.duration:
            if hasattr(duration_entry, "concentration"):
                return duration_entry.concentration
            elif isinstance(duration_entry, dict):
                return duration_entry.get("concentration", False)

        return False

    def _extract_upcast_effects(self, spell: Spell) -> str | None:
        """Extract upcast effects from higher level text."""
        if not spell.higher_level:
            return None

        # Process higher level entries
        effects = []
        for entry in spell.higher_level:
            if isinstance(entry, str):
                effects.append(entry)

        return " ".join(effects) if effects else None

    def _get_class_availability(self, spell: Spell) -> list[str]:
        """Get list of classes that can cast this spell."""
        if not hasattr(spell, "classes") or not spell.classes:
            return []

        class_names = []
        classes_data = spell.classes

        if isinstance(classes_data, dict):
            for class_key, class_info in classes_data.items():
                if class_key == "fromClassList":
                    for class_entry in class_info:
                        if isinstance(class_entry, dict) and "name" in class_entry:
                            class_names.append(class_entry["name"])

        return class_names


class CreatureProcessor(ContentProcessor):
    """Processor for creature content with stat block enhancements."""

    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports creature content."""
        return content_type == ContentType.CREATURE

    def process(self, content: BaseContent, context: RenderContext) -> dict[str, Any]:
        """Process creature content for enhanced rendering.

        Args:
            content: Creature to process
            context: Rendering context

        Returns:
            Enhanced creature data
        """
        if not isinstance(content, Creature):
            raise ValueError(f"Expected Creature, got {type(content)}")

        processed_data = {
            "cr_numeric": self._get_numeric_cr(content.cr),
            "cr_category": self._get_cr_category(content.cr),
            "size_category": self._get_size_category(content.size),
            "proficiency_bonus": self._calculate_proficiency_bonus(content.cr),
            "ability_modifiers": self._calculate_ability_modifiers(content),
            "passive_perception": self._calculate_passive_perception(content),
            "is_spellcaster": self._is_spellcaster(content),
            "legendary_creature": self._is_legendary(content),
            "creature_tags": self._extract_creature_tags(content),
            "environment_tags": self._extract_environment_tags(content),
        }

        return processed_data

    def _get_numeric_cr(self, cr: Any) -> float:
        """Convert CR to numeric value for calculations."""
        if not cr:
            return 0.0

        cr_str = str(cr)
        if cr_str == "1/8":
            return 0.125
        elif cr_str == "1/4":
            return 0.25
        elif cr_str == "1/2":
            return 0.5
        else:
            try:
                return float(cr_str)
            except ValueError:
                return 0.0

    def _get_cr_category(self, cr: Any) -> str:
        """Get CR category for grouping."""
        numeric_cr = self._get_numeric_cr(cr)

        if numeric_cr == 0:
            return "Trivial"
        elif numeric_cr <= 0.5:
            return "Low"
        elif numeric_cr <= 4:
            return "Medium"
        elif numeric_cr <= 10:
            return "High"
        elif numeric_cr <= 16:
            return "Epic"
        else:
            return "Legendary"

    def _get_size_category(self, size: list[str]) -> str:
        """Get primary size category."""
        if not size:
            return "Medium"

        primary_size = size[0] if size else "M"

        return {
            "T": "Tiny",
            "S": "Small",
            "M": "Medium",
            "L": "Large",
            "H": "Huge",
            "G": "Gargantuan",
        }.get(primary_size, "Medium")

    def _calculate_proficiency_bonus(self, cr: Any) -> int:
        """Calculate proficiency bonus based on CR."""
        numeric_cr = self._get_numeric_cr(cr)

        if numeric_cr <= 4:
            return 2
        elif numeric_cr <= 8:
            return 3
        elif numeric_cr <= 12:
            return 4
        elif numeric_cr <= 16:
            return 5
        elif numeric_cr <= 20:
            return 6
        elif numeric_cr <= 24:
            return 7
        elif numeric_cr <= 28:
            return 8
        else:
            return 9

    def _calculate_ability_modifiers(self, creature: Creature) -> dict[str, int]:
        """Calculate ability modifiers."""
        abilities = {
            "str": creature.strength,
            "dex": creature.dexterity,
            "con": creature.constitution,
            "int": creature.intelligence,
            "wis": creature.wisdom,
            "cha": creature.charisma,
        }

        modifiers = {}
        for ability, score in abilities.items():
            modifiers[ability] = (score - 10) // 2

        return modifiers

    def _calculate_passive_perception(self, creature: Creature) -> int:
        """Calculate passive perception."""
        wis_mod = (creature.wisdom - 10) // 2
        prof_bonus = self._calculate_proficiency_bonus(creature.cr)

        # Check if creature has perception proficiency
        has_perception = False
        if hasattr(creature, "skill") and creature.skill:
            has_perception = "perception" in creature.skill

        base_passive = 10 + wis_mod
        if has_perception:
            base_passive += prof_bonus

        return base_passive

    def _is_spellcaster(self, creature: Creature) -> bool:
        """Check if creature has spellcasting abilities."""
        if not hasattr(creature, "trait") or not creature.trait:
            return False

        for trait in creature.trait:
            if isinstance(trait, dict):
                name = trait.get("name", "").lower()
                if "spellcasting" in name:
                    return True

        return False

    def _is_legendary(self, creature: Creature) -> bool:
        """Check if creature has legendary actions."""
        return (
            hasattr(creature, "legendary")
            and creature.legendary is not None
            and len(creature.legendary) > 0
        )

    def _extract_creature_tags(self, creature: Creature) -> list[str]:
        """Extract semantic tags from creature."""
        tags = []

        # Size tag
        if creature.size:
            tags.append(self._get_size_category(creature.size).lower())

        # Type tag
        if creature.type:
            if isinstance(creature.type, str):
                tags.append(creature.type.lower())
            else:
                tags.append(str(creature.type).lower())

        # CR category
        tags.append(self._get_cr_category(creature.cr).lower())

        # Special abilities
        if self._is_spellcaster(creature):
            tags.append("spellcaster")

        if self._is_legendary(creature):
            tags.append("legendary")

        return tags

    def _extract_environment_tags(self, creature: Creature) -> list[str]:
        """Extract environment tags from creature."""
        # This would need implementation based on creature environment data
        return []


class ItemProcessor(ContentProcessor):
    """Processor for item content with enhanced categorization."""

    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports item content."""
        return content_type == ContentType.ITEM

    def process(self, content: BaseContent, context: RenderContext) -> dict[str, Any]:
        """Process item content for enhanced rendering.

        Args:
            content: Item to process
            context: Rendering context

        Returns:
            Enhanced item data
        """
        if not isinstance(content, Item):
            raise ValueError(f"Expected Item, got {type(content)}")

        processed_data = {
            "item_category": self._get_item_category(content),
            "rarity_tier": self._get_rarity_tier(content),
            "is_magic_item": self._is_magic_item(content),
            "requires_attunement": self._requires_attunement(content),
            "item_properties": self._extract_item_properties(content),
            "damage_output": self._get_damage_output(content),
            "armor_rating": self._get_armor_rating(content),
            "value_tier": self._get_value_tier(content),
        }

        return processed_data

    def _get_item_category(self, item: Item) -> str:
        """Get broad item category."""
        if item.is_weapon():
            return "Weapon"
        elif item.is_armor():
            return "Armor"
        elif self._is_magic_item(item):
            return "Magic Item"
        else:
            return "Equipment"

    def _get_rarity_tier(self, item: Item) -> str:
        """Get rarity tier for organization."""
        if not item.rarity:
            return "Common"

        rarity_str = str(item.rarity).lower()
        if "legendary" in rarity_str:
            return "Legendary"
        elif "very rare" in rarity_str:
            return "Very Rare"
        elif "rare" in rarity_str:
            return "Rare"
        elif "uncommon" in rarity_str:
            return "Uncommon"
        else:
            return "Common"

    def _is_magic_item(self, item: Item) -> bool:
        """Check if item is magical."""
        return item.is_magic_item() if hasattr(item, "is_magic_item") else False

    def _requires_attunement(self, item: Item) -> bool:
        """Check if item requires attunement."""
        if not item.requires_attunement:
            return False

        if isinstance(item.requires_attunement, bool):
            return item.requires_attunement
        else:
            return True

    def _extract_item_properties(self, item: Item) -> list[str]:
        """Extract item properties."""
        if not item.properties:
            return []

        return list(item.properties)

    def _get_damage_output(self, item: Item) -> str | None:
        """Get damage output for weapons."""
        if not item.is_weapon():
            return None

        damage = getattr(item, "damage", None)
        if damage:
            return str(damage)

        return None

    def _get_armor_rating(self, item: Item) -> int | None:
        """Get armor class for armor items."""
        if not item.is_armor():
            return None

        ac = getattr(item, "ac", None)
        if ac:
            return int(ac) if isinstance(ac, int | str) else None

        return None

    def _get_value_tier(self, item: Item) -> str:
        """Get value tier for organization."""
        if not item.value:
            return "Priceless"

        try:
            value = float(item.value)
            if value >= 50000:  # 500+ gp
                return "Expensive"
            elif value >= 10000:  # 100+ gp
                return "Costly"
            elif value >= 1000:  # 10+ gp
                return "Moderate"
            elif value >= 100:  # 1+ gp
                return "Affordable"
            else:
                return "Cheap"
        except (ValueError, TypeError):
            return "Variable"


class ContentProcessorRegistry:
    """Registry for content processors."""

    def __init__(self) -> None:
        """Initialize processor registry."""
        self._processors: dict[ContentType, ContentProcessor] = {}
        self._register_default_processors()

    def _register_default_processors(self) -> None:
        """Register default content processors."""
        self.register_processor(SpellProcessor())
        self.register_processor(CreatureProcessor())
        self.register_processor(ItemProcessor())

    def register_processor(self, processor: ContentProcessor) -> None:
        """Register a content processor.

        Args:
            processor: Processor to register
        """
        for content_type in ContentType:
            if processor.supports_content_type(content_type):
                self._processors[content_type] = processor

    def get_processor(self, content_type: ContentType) -> ContentProcessor | None:
        """Get processor for content type.

        Args:
            content_type: Content type to get processor for

        Returns:
            Processor instance or None if not found
        """
        return self._processors.get(content_type)

    def process_content(
        self, content: BaseContent, context: RenderContext
    ) -> dict[str, Any]:
        """Process content using appropriate processor.

        Args:
            content: Content to process
            context: Rendering context

        Returns:
            Processed content data
        """
        content_type = ContentType.from_content(content)
        processor = self.get_processor(content_type)

        if processor:
            return processor.process(content, context)
        else:
            return {}
