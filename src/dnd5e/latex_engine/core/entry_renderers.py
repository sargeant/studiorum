"""New focused EntryRenderer classes for individual content types."""

from abc import ABC, abstractmethod
from typing import Any

from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.renderers.core.interfaces import RenderingContext
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
        self, content: Any, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context using model formatting methods."""
        pass

    def render(self, content: Any, context: RenderingContext) -> str:
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
        self, content: Spell, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for spell using model methods."""
        # Provide both the spell object and preprocessed fields for compatibility
        return {
            "spell": content,
            "level_text": content.get_enhanced_level_text(),
            "components_text": content.get_enhanced_components_text(),
            "duration_text": content.get_enhanced_duration_text(),
            "description_text": content.get_description_text(),
            "higher_level_text": content.get_higher_level_text(),
        }


class CreatureEntryRenderer(BaseEntryRenderer):
    """Focused renderer for individual creature stat blocks."""

    def get_template_name(self) -> str:
        """Return creature entry template name."""
        return "creature_entry"

    def get_template_context(
        self, content: Creature, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for creature using model methods."""
        # Provide both the creature object and preprocessed fields for compatibility
        return {
            "creature": content,
            "size_type_alignment": content.get_size_type_alignment(),
            "ability_scores": {
                "str": content.strength,
                "dex": content.dexterity,
                "con": content.constitution,
                "int": content.intelligence,
                "wis": content.wisdom,
                "cha": content.charisma,
            },
            "formatted_abilities": {
                "str": content.get_ability_text(content.strength),
                "dex": content.get_ability_text(content.dexterity),
                "con": content.get_ability_text(content.constitution),
                "int": content.get_ability_text(content.intelligence),
                "wis": content.get_ability_text(content.wisdom),
                "cha": content.get_ability_text(content.charisma),
            },
        }


class ItemEntryRenderer(BaseEntryRenderer):
    """Focused renderer for individual item descriptions."""

    def get_template_name(self) -> str:
        """Return item entry template name."""
        return "item_entry"

    def get_template_context(
        self, content: Item, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for item using model methods."""
        # Provide both the item object and preprocessed fields for compatibility
        return {
            "item": content,
            "type_text": content.get_type_text(),
            "rarity_text": content.get_rarity_text(),
            "weight_text": content.get_weight_text(),
            "value_text": content.get_value_text(),
        }


class ClassEntryRenderer(BaseEntryRenderer):
    """Focused renderer for class descriptions."""

    def get_template_name(self) -> str:
        """Return class entry template name."""
        return "class_entry"

    def get_template_context(
        self, content: Any, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for class."""
        return {"class": content}


class RaceEntryRenderer(BaseEntryRenderer):
    """Focused renderer for race descriptions."""

    def get_template_name(self) -> str:
        """Return race entry template name."""
        return "race_entry"

    def get_template_context(
        self, content: Any, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for race."""
        return {"race": content}


class BackgroundEntryRenderer(BaseEntryRenderer):
    """Focused renderer for background descriptions."""

    def get_template_name(self) -> str:
        """Return background entry template name."""
        return "background_entry"

    def get_template_context(
        self, content: Any, context: RenderingContext
    ) -> dict[str, Any]:
        """Generate template context for background."""
        return {"background": content}


class FeatEntryRenderer(BaseEntryRenderer):
    """Focused renderer for feat descriptions."""

    def get_template_name(self) -> str:
        """Return feat entry template name."""
        return "feat_entry"

    def get_template_context(
        self, content: Any, context: RenderingContext
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
