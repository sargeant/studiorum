"""New focused EntryRenderer classes for individual content types."""

from abc import ABC, abstractmethod
from typing import Any

from dnd5e.core.models.content import BaseContent
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.renderers.base.context import RenderContext
from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine


class BaseEntryRenderer(ABC):
    """Abstract base class for focused entry renderers.

    Each EntryRenderer handles a single content type and delegates
    formatting logic to the model itself.
    """

    def __init__(self) -> None:
        """Initialize the entry renderer."""
        self.template_engine = LaTeXTemplateEngine()

    @abstractmethod
    def get_template_name(self) -> str:
        """Return the template name for this content type."""
        pass

    @abstractmethod
    def get_template_context(
        self, content: Any, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context using model formatting methods."""
        pass

    def render(self, content: Any, context: RenderContext) -> str:
        """Render content using model formatting and templates."""
        template_name = self.get_template_name()
        template_context = self.get_template_context(content, context)
        return self.template_engine.render_template(template_name, template_context)


class SpellEntryRenderer(BaseEntryRenderer):
    """Focused renderer for individual spell entries."""

    def get_template_name(self) -> str:
        """Return spell entry template name."""
        return "spell_entry"

    def get_template_context(
        self, content: Spell, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for spell using model methods."""
        # Process description text through tag resolver if available
        if context.tag_resolver:
            description_text = context.tag_resolver.process_text(
                content.get_description_text()
            )
            higher_level_text = context.tag_resolver.process_text(
                content.get_higher_level_scaling_text()
            )
        else:
            description_text = content.get_description_text()
            higher_level_text = content.get_higher_level_scaling_text()

        return {
            "spell": content,
            "level_text": content.get_enhanced_level_text(),
            "components_text": content.get_enhanced_components_text(),
            "duration_text": content.get_enhanced_duration_text(),
            "description_text": description_text,
            "higher_level_text": higher_level_text,
            "casting_time": content.get_casting_time_text(),
            "range_text": content.get_range_text(),
        }


class CreatureEntryRenderer(BaseEntryRenderer):
    """Focused renderer for individual creature stat blocks."""

    def get_template_name(self) -> str:
        """Return creature entry template name."""
        return "creature_entry"

    def get_template_context(
        self, content: Creature, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for creature using model methods."""
        # Use enhanced creature formatting methods
        return {
            "creature": content,
            "size_type_alignment": content.get_size_type_alignment(),
            "ac_text": content.get_ac_text(),
            "hp_text": content.get_hp_text(),
            "speed_text": content.get_speed_text(),
            "ability_scores": {
                "str": content.get_ability_text(content.strength),
                "dex": content.get_ability_text(content.dexterity),
                "con": content.get_ability_text(content.constitution),
                "int": content.get_ability_text(content.intelligence),
                "wis": content.get_ability_text(content.wisdom),
                "cha": content.get_ability_text(content.charisma),
            },
            "saving_throws": content.get_formatted_saving_throws(),
            "skills": content.get_formatted_skills(),
            "senses": content.get_formatted_senses(),
            "languages": content.get_formatted_languages(),
            "damage_resistances": content.get_formatted_resistances(),
            "damage_immunities": content.get_formatted_immunities(),
            "damage_vulnerabilities": content.get_formatted_vulnerabilities(),
            "condition_immunities": content.get_formatted_condition_immunities(),
            "cr_text": content.get_enhanced_cr_text(),
            "formatted_abilities": self._format_creature_abilities(content, context),
        }

    def _format_creature_abilities(
        self, creature: Creature, context: RenderContext
    ) -> dict[str, list[str]]:
        """Format creature abilities by type."""
        abilities = {}

        if creature.trait:
            abilities["traits"] = [
                self._format_ability_entry(ability, context)
                for ability in creature.trait
            ]

        if creature.action:
            abilities["actions"] = [
                self._format_ability_entry(ability, context)
                for ability in creature.action
            ]

        if creature.legendary:
            abilities["legendary"] = [
                self._format_ability_entry(ability, context)
                for ability in creature.legendary
            ]

        if creature.reaction:
            abilities["reactions"] = [
                self._format_ability_entry(ability, context)
                for ability in creature.reaction
            ]

        if creature.bonus:
            abilities["bonus"] = [
                self._format_ability_entry(ability, context)
                for ability in creature.bonus
            ]

        return abilities

    def _format_ability_entry(self, ability: Any, context: RenderContext) -> str:
        """Format a single ability entry."""
        if hasattr(ability, "get_description_text"):
            description = str(ability.get_description_text())
        else:
            # Fallback for basic ability structures
            description = str(ability)

        if context.tag_resolver:
            processed = context.tag_resolver.process_text(description)
            return str(processed)

        return description


class ItemEntryRenderer(BaseEntryRenderer):
    """Focused renderer for individual item descriptions."""

    def get_template_name(self) -> str:
        """Return item entry template name."""
        return "item_entry"

    def get_template_context(
        self, content: Item, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for item using model methods."""
        # Process description text through tag resolver if available
        description_text = content.get_description_text()
        if context.tag_resolver:
            description_text = context.tag_resolver.process_text(description_text)

        return {
            "item": content,
            "type_text": content.get_type_text(),
            "rarity_text": content.get_rarity_text(),
            "enhanced_rarity_text": content.get_enhanced_rarity_text(),
            "metadata_line": content.get_item_metadata_line(),
            "weight_text": content.get_weight_text(),
            "value_text": content.get_value_text(),
            "attunement_text": content.get_attunement_text(),
            "ac_text": content.get_ac_text(),
            "damage_text": content.get_damage_text(),
            "range_text": content.get_range_text(),
            "properties": content.get_properties_text(),
            "charges_text": content.get_charges_text(),
            "description_text": description_text,
        }


class ClassEntryRenderer(BaseEntryRenderer):
    """Focused renderer for class descriptions."""

    def get_template_name(self) -> str:
        """Return class entry template name."""
        return "class_entry"

    def get_template_context(
        self, content: Any, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for class."""
        return {"class": content}


class RaceEntryRenderer(BaseEntryRenderer):
    """Focused renderer for race descriptions."""

    def get_template_name(self) -> str:
        """Return race entry template name."""
        return "race_entry"

    def get_template_context(
        self, content: Any, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for race."""
        return {"race": content}


class BackgroundEntryRenderer(BaseEntryRenderer):
    """Focused renderer for background descriptions."""

    def get_template_name(self) -> str:
        """Return background entry template name."""
        return "background_entry"

    def get_template_context(
        self, content: Any, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for background."""
        return {"background": content}


class FeatEntryRenderer(BaseEntryRenderer):
    """Focused renderer for feat descriptions."""

    def get_template_name(self) -> str:
        """Return feat entry template name."""
        return "feat_entry"

    def get_template_context(
        self, content: Any, context: RenderContext
    ) -> dict[str, Any]:
        """Generate template context for feat."""
        return {"feat": content}


class EntryRendererRegistry:
    """Registry for managing EntryRenderer instances."""

    def __init__(self) -> None:
        """Initialize the registry with default renderers."""
        self._renderers: dict[str, BaseEntryRenderer] = {}
        self._register_default_renderers()

    def _register_default_renderers(self) -> None:
        """Register all default entry renderers."""
        self.register_renderer("spell", SpellEntryRenderer())
        self.register_renderer("creature", CreatureEntryRenderer())
        self.register_renderer("item", ItemEntryRenderer())
        self.register_renderer("class", ClassEntryRenderer())
        self.register_renderer("race", RaceEntryRenderer())
        self.register_renderer("background", BackgroundEntryRenderer())
        self.register_renderer("feat", FeatEntryRenderer())

    def register_renderer(self, content_type: str, renderer: BaseEntryRenderer) -> None:
        """Register a renderer for a content type."""
        self._renderers[content_type] = renderer

    def get_renderer(self, content_type: str) -> BaseEntryRenderer:
        """Get renderer for the specified content type."""
        if content_type not in self._renderers:
            raise ValueError(f"No renderer registered for content type: {content_type}")
        return self._renderers[content_type]
