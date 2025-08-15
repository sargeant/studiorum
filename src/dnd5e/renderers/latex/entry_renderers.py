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
        # New template expects direct access to spell object and its methods
        return {
            "spell": content,
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
        # New template expects direct access to creature object and its methods
        return {
            "creature": content,
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
        # New template expects direct access to item object and its methods
        return {
            "item": content,
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
