"""
Backward compatibility shims for existing CLI behavior.

This module provides legacy methods that maintain existing behavior
for CLI and existing code while enabling gradual migration to the
new processor-based architecture.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer
    from ..text.tag_resolver import TagResolver
    from .creatures import Creature
    from .items import Item
    from .spells import Spell


logger = logging.getLogger(__name__)


def process_creature_senses_legacy(creature: "Creature") -> str | None:
    """Legacy method for processing creature senses with global services."""
    try:
        # Import only when needed to avoid circular dependencies
        from ...cli.utils import get_tag_resolver

        tag_resolver = get_tag_resolver()
        processor = creature.get_processor()

        # Use the processor's senses processing method
        if creature.senses:
            processed_senses = processor._process_senses_with_tag_resolver(
                creature.senses, tag_resolver
            )
            return processed_senses
        else:
            return creature.get_formatted_senses()

    except Exception as e:
        logger.warning(f"Failed to process creature senses: {e}")
        # Fallback to original formatted senses
        return creature.get_formatted_senses()


def get_spell_description_legacy(spell: "Spell", context: Any = None) -> str:
    """Legacy method for getting spell description with global services."""
    try:
        if context is None:
            from ...cli.utils import get_tag_resolver
            from ...renderers.core.interfaces import RenderingContext

            # Get the tag resolver for proper tag processing
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": spell.source or "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "spell",
                },
            )

        # Use the processor to get description
        processor = spell.get_processor()
        result = processor.get_description_with_context(
            context.metadata["tag_resolver"], context
        )

        if result.is_success():
            return result.unwrap()
        else:
            # Extract error from Result
            from ..result import Error

            if isinstance(result, Error):
                logger.warning(f"Failed to process spell description: {result.error}")
            # Fallback to simple text extraction
            return _extract_simple_text_from_entries(spell.entries)

    except Exception as e:
        logger.warning(f"Failed to get spell description: {e}")
        return _extract_simple_text_from_entries(spell.entries)


def get_spell_higher_level_legacy(spell: "Spell", context: Any = None) -> str:
    """Legacy method for getting spell higher level text with global services."""
    try:
        if not spell.higher_level:
            return ""

        if context is None:
            from ...cli.utils import get_tag_resolver
            from ...renderers.core.interfaces import RenderingContext

            # Get the tag resolver for proper tag processing
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": spell.source or "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "spell",
                },
            )

        # Use the processor to get higher level text
        processor = spell.get_processor()
        result = processor.get_higher_level_with_context(
            context.metadata["tag_resolver"], context
        )

        if result.is_success():
            return result.unwrap()
        else:
            # Extract error from Result
            from ..result import Error

            if isinstance(result, Error):
                logger.warning(f"Failed to process spell higher level: {result.error}")
            # Fallback to simple text extraction
            return _extract_simple_text_from_entries(spell.higher_level)

    except Exception as e:
        logger.warning(f"Failed to get spell higher level: {e}")
        return _extract_simple_text_from_entries(spell.higher_level or [])


def get_item_description_legacy(item: "Item") -> str:
    """Legacy method for getting item description with global services."""
    try:
        from ...cli.utils import get_tag_resolver

        tag_resolver = get_tag_resolver()
        processor = item.get_processor()

        result = processor.get_description_with_context(tag_resolver)

        if result.is_success():
            return result.unwrap()
        else:
            # Extract error from Result
            from ..result import Error

            if isinstance(result, Error):
                logger.warning(f"Failed to process item description: {result.error}")
            # Fallback to simple text extraction
            return _extract_simple_text_from_entries(item.entries or [])

    except Exception as e:
        logger.warning(f"Failed to get item description: {e}")
        return _extract_simple_text_from_entries(item.entries or [])


def _extract_simple_text_from_entries(entries: list[Any]) -> str:
    """Extract simple text from entries without processing."""
    if not entries:
        return ""

    text_parts = []
    for entry in entries:
        if isinstance(entry, str):
            text_parts.append(entry)
        elif hasattr(entry, "model_dump"):
            # For complex entries, try to extract text field
            entry_data = entry.model_dump()
            if isinstance(entry_data, dict) and "text" in entry_data:
                text_parts.append(str(entry_data["text"]))
            else:
                text_parts.append(str(entry_data))
        else:
            text_parts.append(str(entry))

    return " ".join(text_parts)
