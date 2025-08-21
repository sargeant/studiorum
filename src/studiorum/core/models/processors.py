"""
Service-aware model processors for core models.

This module provides processor classes that separate business logic from data
representation, enabling proper dependency injection and eliminating circular
dependencies between core models and CLI utilities.
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..error_types import BaseError, ProcessingError
from ..result import Error as Failure, Result, Success

if TYPE_CHECKING:
    from ...renderers.core.interfaces import RenderingContext
    from ..loaders.omnidexer import Omnidexer
    from ..text.tag_resolver import TagResolver
    from .creatures import Creature
    from .items import Item
    from .spells import Spell


@runtime_checkable
class ModelProcessorProtocol(Protocol):
    """Protocol for model processors that require services."""

    def process_with_services(
        self, tag_resolver: "TagResolver", omnidexer: "Omnidexer | None" = None
    ) -> Result[Any, BaseError]:
        """Process model with provided services."""
        ...


class CreatureProcessor:
    """Processor for creature model tag resolution and content enrichment."""

    def __init__(self, creature: "Creature"):
        from .creatures import Creature

        self.creature: Creature = creature

    def resolve_tags(
        self, tag_resolver: "TagResolver"
    ) -> Result["Creature", BaseError]:
        """Resolve tags in creature entries using provided tag resolver."""
        try:
            # Process senses with tag resolution
            processed_senses = None
            if self.creature.senses:
                processed_senses = self._process_senses_with_tag_resolver(
                    self.creature.senses, tag_resolver
                )

            # Create processed creature - for now, this just handles senses
            # Additional tag processing can be added here as needed
            if processed_senses is not None:
                # Note: We don't actually modify the creature here since senses
                # processing is handled by the get_processed_senses method.
                # This is a placeholder for future tag processing needs.
                pass

            return Success(self.creature)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to resolve creature tags: {e}",
                category=ErrorCategory.PROCESSING,
                source="CreatureProcessor.resolve_tags",
            )
            return Failure(error)

    def _process_senses_with_tag_resolver(
        self, senses: list[str], tag_resolver: "TagResolver"
    ) -> str:
        """Process senses with tag resolution."""
        from ...renderers.core.interfaces import RenderingContext
        from ...renderers.latex.entry_processor import RecursiveEntryProcessor

        # Create a proper rendering context for entry processing
        context = RenderingContext(
            output_format="latex",
            debug_mode=False,
            omnidexer=None,  # Not needed for senses processing
            tag_resolver=tag_resolver,
            metadata={
                "source_name": self.creature.source or "unknown",
                "tag_resolver": tag_resolver,
                "content_type": "creature",
            },
        )

        # Use recursive entry processor to handle 5e.tools markup
        processor = RecursiveEntryProcessor(use_dnd_template=True)

        # Convert senses to entry format and process
        if isinstance(senses, list):
            senses_text = ", ".join(senses)
        else:
            senses_text = str(senses)

        # Process the senses text
        processed_entries = processor.process_entries([senses_text], context)
        return "\n".join(processed_entries)

    def enrich_with_content(
        self, omnidexer: "Omnidexer", tag_resolver: "TagResolver"
    ) -> Result["Creature", BaseError]:
        """Enrich creature with additional content using provided services."""
        try:
            # Resolve tags first
            tag_result = self.resolve_tags(tag_resolver)
            if tag_result.is_error():
                return tag_result

            processed_creature = tag_result.unwrap()

            # Look up legendary actions if referenced
            if hasattr(processed_creature, "legendary_group"):
                legendary_result = self._lookup_legendary_group(
                    processed_creature.legendary_group, omnidexer
                )
                if legendary_result.is_error():
                    # Convert the legendary group error to a creature processing error
                    from ..error_types import ErrorCategory
                    from ..result import Error

                    error_info = (
                        legendary_result.error
                        if isinstance(legendary_result, Error)
                        else "Unknown error"
                    )
                    error = ProcessingError(
                        message=f"Failed to enrich creature with legendary data: {error_info}",
                        category=ErrorCategory.PROCESSING,
                        source="CreatureProcessor.enrich_with_content",
                    )
                    return Failure(error)

                legendary_result.unwrap()
                # For now, we don't modify the creature model directly
                # This could be extended to create an enriched creature variant
                # processed_creature = processed_creature.model_copy(
                #     update={'legendary_actions': legendary_data}
                # )

            return Success(processed_creature)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to enrich creature: {e}",
                category=ErrorCategory.PROCESSING,
                source="CreatureProcessor.enrich_with_content",
            )
            return Failure(error)

    def _lookup_legendary_group(
        self, group_name: str, omnidexer: "Omnidexer"
    ) -> Result[dict[str, Any], BaseError]:
        """Look up legendary group data."""
        try:
            # This is a placeholder for legendary group lookup
            # The actual implementation would depend on how legendary groups
            # are stored in the omnidexer
            legendary_group = None  # omnidexer.get_legendary_group(group_name)
            if not legendary_group:
                from ..error_types import ErrorCategory

                error = ProcessingError(
                    message=f"Legendary group not found: {group_name}",
                    category=ErrorCategory.PROCESSING,
                    source="CreatureProcessor._lookup_legendary_group",
                )
                return Failure(error)

            return Success(
                legendary_group.model_dump()
                if hasattr(legendary_group, "model_dump")
                else legendary_group
            )

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to lookup legendary group: {e}",
                category=ErrorCategory.PROCESSING,
                source="CreatureProcessor._lookup_legendary_group",
            )
            return Failure(error)

    def process_with_services(
        self, tag_resolver: "TagResolver", omnidexer: "Omnidexer | None" = None
    ) -> Result["Creature", BaseError]:
        """Process creature with provided services (implements ModelProcessorProtocol)."""
        if omnidexer:
            return self.enrich_with_content(omnidexer, tag_resolver)
        else:
            return self.resolve_tags(tag_resolver)


class SpellProcessor:
    """Processor for spell model tag resolution."""

    def __init__(self, spell: "Spell"):
        from .spells import Spell

        self.spell: Spell = spell

    def resolve_tags(self, tag_resolver: "TagResolver") -> Result["Spell", BaseError]:
        """Resolve tags in spell entries."""
        try:
            # The spell processing is currently handled by the get_description_text
            # and get_higher_level_text methods. For now, we just return the original
            # spell since the actual processing happens in the rendering context.
            # This can be extended if we need to pre-process spell entries.

            return Success(self.spell)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to resolve spell tags: {e}",
                category=ErrorCategory.PROCESSING,
                source="SpellProcessor.resolve_tags",
            )
            return Failure(error)

    def get_description_with_context(
        self, tag_resolver: "TagResolver", context: "RenderingContext | None" = None
    ) -> Result[str, BaseError]:
        """Get spell description with tag resolution using provided services."""
        try:
            from ...renderers.core.interfaces import RenderingContext
            from ...renderers.latex.entry_processor import RecursiveEntryProcessor

            # Use provided context or create one with injected services
            if context is None:
                context = RenderingContext(
                    output_format="latex",
                    debug_mode=False,
                    tag_resolver=tag_resolver,
                    metadata={
                        "source_name": self.spell.source or "unknown",
                        "tag_resolver": tag_resolver,
                        "content_type": "spell",
                    },
                )

            from ...core.entry_registry import ValidationMode

            processor = RecursiveEntryProcessor(
                use_dnd_template=True, validation_mode=ValidationMode.SILENT
            )

            # Convert Pydantic models to dicts for entry processor
            entries_data = []
            for entry in self.spell.entries:
                if hasattr(entry, "model_dump"):
                    entries_data.append(entry.model_dump())
                else:
                    entries_data.append(entry)

            # Process entries to get proper LaTeX with tag resolution
            processed_entries = processor.process_entries(entries_data, context)

            if not processed_entries:
                return Success("")

            # Format the first paragraph with \noindent and subsequent paragraphs with proper indentation
            formatted_paragraphs = []
            for i, entry in enumerate(processed_entries):
                if i == 0:
                    # First paragraph should not be indented
                    formatted_paragraphs.append(f"\\noindent {entry}")
                else:
                    # Subsequent paragraphs should use default paragraph indentation
                    formatted_paragraphs.append(entry)

            # Join with double newlines to create proper paragraph breaks for LaTeX
            result = "\n\n".join(formatted_paragraphs)
            return Success(result)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to process spell description: {e}",
                category=ErrorCategory.PROCESSING,
                source="SpellProcessor.get_description_with_context",
            )
            return Failure(error)

    def get_higher_level_with_context(
        self, tag_resolver: "TagResolver", context: "RenderingContext | None" = None
    ) -> Result[str, BaseError]:
        """Get spell higher level text with tag resolution using provided services."""
        try:
            if not self.spell.higher_level:
                return Success("")

            from ...renderers.core.interfaces import RenderingContext
            from ...renderers.latex.entry_processor import RecursiveEntryProcessor

            # Use provided context or create one with injected services
            if context is None:
                context = RenderingContext(
                    output_format="latex",
                    debug_mode=False,
                    tag_resolver=tag_resolver,
                    metadata={
                        "source_name": self.spell.source or "unknown",
                        "tag_resolver": tag_resolver,
                        "content_type": "spell",
                    },
                )

            from ...core.entry_registry import ValidationMode

            processor = RecursiveEntryProcessor(
                use_dnd_template=True, validation_mode=ValidationMode.SILENT
            )

            # Convert Pydantic models to dicts for entry processor
            entries_data = []
            for entry in self.spell.higher_level:
                if hasattr(entry, "model_dump"):
                    entries_data.append(entry.model_dump())
                else:
                    entries_data.append(entry)

            # Process entries to get proper LaTeX with tag resolution
            processed_entries = processor.process_entries(entries_data, context)
            result = " ".join(processed_entries)
            return Success(result)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to process spell higher level text: {e}",
                category=ErrorCategory.PROCESSING,
                source="SpellProcessor.get_higher_level_with_context",
            )
            return Failure(error)

    def process_with_services(
        self, tag_resolver: "TagResolver", omnidexer: "Omnidexer | None" = None
    ) -> Result["Spell", BaseError]:
        """Process spell with provided services (implements ModelProcessorProtocol)."""
        return self.resolve_tags(tag_resolver)


class ItemProcessor:
    """Processor for item model tag resolution."""

    def __init__(self, item: "Item"):
        from .items import Item

        self.item: Item = item

    def resolve_tags(self, tag_resolver: "TagResolver") -> Result["Item", BaseError]:
        """Resolve tags in item entries."""
        try:
            # The item processing is currently handled by the get_description_text method.
            # For now, we just return the original item since the actual processing
            # happens in the rendering context. This can be extended if we need to
            # pre-process item entries.

            return Success(self.item)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to resolve item tags: {e}",
                category=ErrorCategory.PROCESSING,
                source="ItemProcessor.resolve_tags",
            )
            return Failure(error)

    def get_description_with_context(
        self, tag_resolver: "TagResolver", context: "RenderingContext | None" = None
    ) -> Result[str, BaseError]:
        """Get item description with tag resolution using provided services."""
        try:
            # Start with item's own entries
            all_entries = []

            if self.item.entries:
                all_entries.extend(self.item.entries)

            # Add type-based entries if item has no entries
            if not self.item.entries:
                type_entries = self.item.get_type_entries()
                if type_entries:
                    # Convert string entries to proper entry format for processing
                    for entry_text in type_entries:
                        all_entries.append(entry_text)

            if not all_entries:
                return Success("")

            from ...renderers.core.interfaces import RenderingContext
            from ...renderers.latex.entry_processor import RecursiveEntryProcessor

            # Use provided context or create one with injected services
            if context is None:
                context = RenderingContext(
                    output_format="latex",
                    debug_mode=False,
                    tag_resolver=tag_resolver,
                    metadata={
                        "source_name": self.item.source or "unknown",
                        "tag_resolver": tag_resolver,
                        "content_type": "item",
                    },
                )

            from ...core.entry_registry import ValidationMode

            processor = RecursiveEntryProcessor(
                use_dnd_template=True, validation_mode=ValidationMode.SILENT
            )

            # Convert Pydantic models to dicts for entry processor
            entries_data = []
            for entry in all_entries:
                if hasattr(entry, "model_dump"):
                    entry_data = entry.model_dump()
                else:
                    entry_data = entry

                entries_data.append(entry_data)

            # Process entries to get proper LaTeX with tag resolution
            processed_entries = processor.process_entries(entries_data, context)

            if not processed_entries:
                return Success("")

            # Format the first paragraph with \noindent and subsequent paragraphs with proper indentation
            formatted_paragraphs = []
            for i, entry in enumerate(processed_entries):
                if i == 0:
                    # First paragraph should not be indented
                    formatted_paragraphs.append(f"\\noindent {entry}")
                else:
                    # Subsequent paragraphs should use default paragraph indentation
                    formatted_paragraphs.append(entry)

            # Join with double newlines to create proper paragraph breaks for LaTeX
            result = "\n\n".join(formatted_paragraphs)
            return Success(result)

        except Exception as e:
            from ..error_types import ErrorCategory

            error = ProcessingError(
                message=f"Failed to process item description: {e}",
                category=ErrorCategory.PROCESSING,
                source="ItemProcessor.get_description_with_context",
            )
            return Failure(error)

    def process_with_services(
        self, tag_resolver: "TagResolver", omnidexer: "Omnidexer | None" = None
    ) -> Result["Item", BaseError]:
        """Process item with provided services (implements ModelProcessorProtocol)."""
        return self.resolve_tags(tag_resolver)
