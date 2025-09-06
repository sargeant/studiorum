"""New focused EntryRenderer classes for individual content types."""

from abc import ABC, abstractmethod
from typing import Any

from studiorum.core.models.creatures import Creature
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.result import Error, Success
from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine
from studiorum.renderers.core.interfaces import RenderingContext


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
        # Entry renderers do not perform tag processing - that happens at a different layer
        # Always use simple text extraction to avoid architectural layering violations
        description_text = content._extract_simple_text_from_entries(content.entries)
        higher_level_text = content._extract_simple_text_from_entries(
            content.higher_level or [], skip_section_names=True
        )

        # Get template service for explicit context passing
        # Try to get from context first, fallback to CLI service
        template_service = None
        if hasattr(context, "template_service") and context.template_service:
            template_service = context.template_service
        else:
            from ...cli.services import get_cli_template_service

            template_service = get_cli_template_service()

        # Get entry processor for structured content handling
        from .entry_processor import RecursiveEntryProcessor

        entry_processor = RecursiveEntryProcessor(use_dnd_template=True)

        # Ensure sectioning depth for spells uses paragraph at depth 1
        # by marking the rendering context with content_type="spell".
        try:
            spell_metadata = dict(context.metadata or {})
            spell_metadata["content_type"] = "spell"
            from studiorum.renderers.core.interfaces import RenderingContext as RC

            rendering_context = RC(
                output_format=context.output_format,
                debug_mode=context.debug_mode,
                omnidexer=context.omnidexer,
                content_tracker=context.content_tracker,
                tag_resolver=context.tag_resolver,
                metadata=spell_metadata,
            )
        except Exception:
            # Fallback: use original context unmodified
            rendering_context = context

        # Provide both the spell object and preprocessed fields for compatibility
        return {
            "spell": content,
            "level_text": content.get_enhanced_level_text(),
            "components_text": content.get_enhanced_components_text(),
            "duration_text": content.get_enhanced_duration_text(),
            "description_text": description_text,
            "higher_level_text": higher_level_text,
            "rendering_context": rendering_context,
            "template_service": template_service,
            "entry_processor": entry_processor,
            "content_tracker": context.content_tracker or ContentTracker(),
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
        # Get template service for explicit context passing
        # Try to get from context first, fallback to CLI service
        template_service = None
        if hasattr(context, "template_service") and context.template_service:
            template_service = context.template_service
        else:
            from ...cli.services import get_cli_template_service

            template_service = get_cli_template_service()

        # Get entry processor for structured content handling
        from .entry_processor import RecursiveEntryProcessor

        entry_processor = RecursiveEntryProcessor(use_dnd_template=True)

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
            "rendering_context": context,
            "template_service": template_service,
            "entry_processor": entry_processor,
            "content_tracker": context.content_tracker or ContentTracker(),
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
        # Get template service for explicit context passing
        # Try to get from context first, fallback to CLI service
        template_service = None
        if hasattr(context, "template_service") and context.template_service:
            template_service = context.template_service
        else:
            from ...cli.services import get_cli_template_service

            template_service = get_cli_template_service()

        # Get entry processor for structured content handling
        from .entry_processor import RecursiveEntryProcessor

        entry_processor = RecursiveEntryProcessor(use_dnd_template=True)

        # Ensure sectioning depth for items uses subparagraph for named subentries
        # by marking the rendering context with content_type="item".
        try:
            item_metadata = dict(context.metadata or {})
            item_metadata["content_type"] = "item"
            from studiorum.renderers.core.interfaces import RenderingContext as RC

            rendering_context = RC(
                output_format=context.output_format,
                debug_mode=context.debug_mode,
                omnidexer=context.omnidexer,
                content_tracker=context.content_tracker,
                tag_resolver=context.tag_resolver,
                metadata=item_metadata,
            )
        except Exception:
            # Fallback: use original context unmodified
            rendering_context = context

        # Provide both the item object and preprocessed fields for compatibility
        return {
            "item": content,
            "type_text": content.get_type_text(),
            "rarity_text": content.get_rarity_text(),
            "weight_text": content.get_weight_text(),
            "value_text": content.get_value_text(),
            "rendering_context": rendering_context,
            "template_service": template_service,
            "entry_processor": entry_processor,
            "content_tracker": context.content_tracker or ContentTracker(),
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
