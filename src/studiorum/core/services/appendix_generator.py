"""Appendix generation service for creating appendices from ContentTracker data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.models.chapter import ChapterType
from studiorum.core.models.creatures import Creature
from studiorum.core.models.document_metadata import ContentSection, SectionLevel
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.creature_collector import CreatureCollector
from studiorum.core.services.item_collector import ItemCollector
from studiorum.core.services.spell_collector import SpellCollector

logger = get_logger(__name__)

if TYPE_CHECKING:
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine


class AppendixFlags(BaseModel):
    """Configuration flags for appendix generation."""

    spells: bool = Field(default=False, description="Generate spells appendix")
    items: bool = Field(default=False, description="Generate items appendix")
    creatures: bool = Field(default=False, description="Generate creatures appendix")

    def has_any_enabled(self) -> bool:
        """Check if any appendix flags are enabled."""
        return self.spells or self.items or self.creatures


class AppendixGenerator:
    """Generates appendices from ContentTracker data using collector services."""

    def __init__(self, omnidexer: Omnidexer):
        """Initialize the appendix generator with required services.

        Args:
            omnidexer: The omnidexer for content lookup
        """
        self.omnidexer = omnidexer
        self.spell_collector = SpellCollector(omnidexer)
        self.item_collector = ItemCollector(omnidexer)
        self.creature_collector = CreatureCollector(omnidexer)

    def generate_appendices(
        self, content_tracker: ContentTracker, flags: AppendixFlags
    ) -> list[ContentSection]:
        """Generate appendix sections based on tracked content and flags.

        Args:
            content_tracker: ContentTracker with tracked references
            flags: AppendixFlags indicating which appendices to generate

        Returns:
            List of ContentSection objects for template-based rendering
        """
        appendices: list[ContentSection] = []

        if not flags.has_any_enabled():
            return appendices

        # Export initial tracked content by type
        tracked_content = content_tracker.export_for_appendix()

        # Generate creature appendix first (may add spell references during rendering)
        if flags.creatures and "creature" in tracked_content:
            creatures_appendix = self._generate_creature_appendix(
                tracked_content["creature"], content_tracker
            )
            if creatures_appendix:
                appendices.append(creatures_appendix)

        # Re-export tracked content to capture any new references from creature rendering
        tracked_content = content_tracker.export_for_appendix()

        # Generate remaining appendices in alphabetical order
        if flags.items and "item" in tracked_content:
            items_appendix = self._generate_item_appendix(
                tracked_content["item"], content_tracker
            )
            if items_appendix:
                appendices.append(items_appendix)

        if flags.spells and "spell" in tracked_content:
            spells_appendix = self._generate_spell_appendix(
                tracked_content["spell"], content_tracker
            )
            if spells_appendix:
                appendices.append(spells_appendix)

        return appendices

    def generate_recursive_appendices(
        self, content_tracker: ContentTracker, flags: AppendixFlags, max_depth: int = 2
    ) -> list[ContentSection]:
        """Generate appendices with recursive reference tracking.

        Args:
            content_tracker: Initial tracked content from main document
            flags: Which appendix types to generate
            max_depth: Maximum recursion depth (default 2 = original + 1 level)

        Returns:
            List of ContentSection objects with recursive content
        """
        # For now, recursive generation is simplified - return standard appendices
        # TODO: Implement proper recursive content tracking for template-first approach
        logger.debug("Using simplified recursive appendix generation")
        return self.generate_appendices(content_tracker, flags)

    def _generate_spell_appendix(
        self, tracked_spells: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> ContentSection | None:
        """Generate spells appendix using SpellCollector and template-based rendering.

        Args:
            tracked_spells: List of tracked spell references
            content_tracker: Content tracker for additional references

        Returns:
            ContentSection with spell objects for template rendering or None if no spells found
        """
        if not tracked_spells:
            return None

        # Extract spell names from tracked content
        spell_names = [content["name"] for content in tracked_spells]

        # Use existing collector service
        collection_result = self.spell_collector.collect_by_names(spell_names)

        if not collection_result.spells:
            return None

        # Create ContentSection with spell objects for template-based rendering
        return ContentSection(
            title="Spells",
            level=SectionLevel.CHAPTER,
            numbered=False,  # Appendices use LaTeX's automatic lettering after \appendix
            chapter_type=ChapterType.APPENDIX,
            label="ch:appendix-spells",
            page_break_before=False,
            page_break_after=False,
            two_column=None,
            content_items=collection_result.spells,  # Raw spell objects for template rendering
        )

    def _generate_item_appendix(
        self, tracked_items: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> ContentSection | None:
        """Generate items appendix using ItemCollector and template-based rendering.

        Args:
            tracked_items: List of tracked item references
            content_tracker: Content tracker for additional references

        Returns:
            ContentSection with item objects for template rendering or None if no items found
        """
        if not tracked_items:
            return None

        # Extract item names from tracked content
        item_names = [content["name"] for content in tracked_items]

        # Use existing collector service
        collection_result = self.item_collector.collect_by_names(item_names)

        if not collection_result.items:
            return None

        # Create ContentSection with item objects for template-based rendering
        return ContentSection(
            title="Magic Items",
            level=SectionLevel.CHAPTER,
            numbered=False,  # Appendices use LaTeX's automatic lettering after \appendix
            chapter_type=ChapterType.APPENDIX,
            label="ch:appendix-items",
            page_break_before=False,
            page_break_after=False,
            two_column=None,
            content_items=collection_result.items,  # Raw item objects for template rendering
        )

    def _generate_creature_appendix(
        self, tracked_creatures: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> ContentSection | None:
        """Generate creatures appendix using CreatureCollector and template-based rendering.

        Args:
            tracked_creatures: List of tracked creature references

        Returns:
            ContentSection with creature objects for template rendering or None if no creatures found
        """
        if not tracked_creatures:
            return None

        # Extract creature names from tracked content
        creature_names = [content["name"] for content in tracked_creatures]

        # Extract unique sources from tracked creatures to ensure we include adventure-specific sources
        from studiorum.cli.config_factory import get_default_sources

        tracked_sources = set()
        for creature_data in tracked_creatures:
            if "source" in creature_data and creature_data["source"]:
                tracked_sources.add(creature_data["source"])

        # Combine default sources with adventure sources
        default_sources = get_default_sources()
        all_sources = list(set(default_sources + list(tracked_sources)))

        # Use existing collector service with combined sources
        collection_result = self.creature_collector.collect_by_names(
            creature_names, all_sources
        )

        if not collection_result.creatures:
            return None

        # Create ContentSection with creature objects for template-based rendering
        return ContentSection(
            title="Creatures",
            level=SectionLevel.CHAPTER,
            numbered=False,  # Appendices use LaTeX's automatic lettering after \appendix
            chapter_type=ChapterType.APPENDIX,
            label="ch:appendix-creatures",
            page_break_before=False,
            page_break_after=False,
            two_column=None,
            content_items=collection_result.creatures,  # Raw creature objects for template rendering
        )
