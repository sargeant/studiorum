"""
High-level content processing service with dependency injection.

This service provides a clean interface for processing content with
injected services, enabling request-scoped processing and proper
separation of concerns.
"""

from typing import TYPE_CHECKING, Any, Union, cast

from ..error_types import BaseError
from ..result import Error as Failure, Result, Success

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer
    from ..text.tag_resolver import TagResolver

from ..models.creatures import Creature
from ..models.items import Item
from ..models.spells import Spell


class ContentProcessingService:
    """High-level service for processing content with injected dependencies."""

    def __init__(
        self, tag_resolver: "TagResolver", omnidexer: "Omnidexer | None" = None
    ):
        self.tag_resolver = tag_resolver
        self.omnidexer = omnidexer

    def process_creature(
        self, creature: Creature, enrich_content: bool = True
    ) -> Result[Creature, BaseError]:
        """Process creature with tag resolution and optional content enrichment."""
        processor = creature.get_processor()

        if enrich_content and self.omnidexer:
            return processor.enrich_with_content(self.omnidexer, self.tag_resolver)
        else:
            return processor.resolve_tags(self.tag_resolver)

    def process_spell(self, spell: Spell) -> Result[Spell, BaseError]:
        """Process spell with tag resolution."""
        processor = spell.get_processor()
        return processor.resolve_tags(self.tag_resolver)

    def process_item(self, item: Item) -> Result[Item, BaseError]:
        """Process item with tag resolution."""
        processor = item.get_processor()
        return processor.resolve_tags(self.tag_resolver)

    def get_spell_description(
        self, spell: Spell, context: Any = None
    ) -> Result[str, BaseError]:
        """Get processed spell description text."""
        processor = spell.get_processor()
        return processor.get_description_with_context(self.tag_resolver, context)

    def get_spell_higher_level(
        self, spell: Spell, context: Any = None
    ) -> Result[str, BaseError]:
        """Get processed spell higher level text."""
        processor = spell.get_processor()
        return processor.get_higher_level_with_context(self.tag_resolver, context)

    def get_item_description(
        self, item: Item, context: Any = None
    ) -> Result[str, BaseError]:
        """Get processed item description text."""
        processor = item.get_processor()
        return processor.get_description_with_context(self.tag_resolver, context)

    def process_content_list(
        self,
        content_list: list[Creature | Spell | Item],
        enrich_content: bool = True,
    ) -> Result[list[Creature | Spell | Item], list[BaseError]]:
        """Process a list of content items."""
        processed_items: list[Creature | Spell | Item] = []
        errors: list[BaseError] = []

        for item in content_list:
            if hasattr(item, "get_processor"):
                # Use type-specific processing
                if isinstance(item, Creature):
                    result = cast(
                        Result[Creature | Spell | Item, BaseError],
                        self.process_creature(item, enrich_content),
                    )
                elif isinstance(item, Spell):
                    result = cast(
                        Result[Creature | Spell | Item, BaseError],
                        self.process_spell(item),
                    )
                elif isinstance(item, Item):
                    result = cast(
                        Result[Creature | Spell | Item, BaseError],
                        self.process_item(item),
                    )
                else:
                    result = Success(item)  # Unknown type, pass through

                if result.is_success():
                    processed_items.append(result.unwrap())
                else:
                    # Extract error from Result
                    from ..result import Error

                    if isinstance(result, Error):
                        errors.append(result.error)
                    processed_items.append(item)  # Include original on error
            else:
                # Pass through items without processors
                processed_items.append(item)

        if errors:
            return Failure(errors)
        else:
            return Success(processed_items)
