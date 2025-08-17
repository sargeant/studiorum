"""Appendix generation service for creating appendices from ContentTracker data."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.core.references.content_tracker import ContentTracker
from dnd5e.core.services.creature_collector import CreatureCollector
from dnd5e.core.services.item_collector import ItemCollector
from dnd5e.core.services.spell_collector import SpellCollector

if TYPE_CHECKING:
    from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine


class AppendixFlags(BaseModel):
    """Configuration flags for appendix generation."""

    spells: bool = Field(default=False, description="Generate spells appendix")
    items: bool = Field(default=False, description="Generate items appendix")
    creatures: bool = Field(default=False, description="Generate creatures appendix")

    def has_any_enabled(self) -> bool:
        """Check if any appendix flags are enabled."""
        return self.spells or self.items or self.creatures


class AppendixSection(BaseModel):
    """A generated appendix section with content and metadata."""

    title: str = Field(description="Appendix title (e.g., 'Appendix A: Spells')")
    content: str = Field(description="Rendered LaTeX content")
    content_type: str = Field(description="Content type (spell/item/creature)")
    item_count: int = Field(description="Number of items in appendix")


class AppendixGenerator:
    """Generates appendices from ContentTracker data using collector services."""

    def __init__(self, omnidexer: Omnidexer, template_engine: "LaTeXTemplateEngine"):
        """Initialize the appendix generator with required services.

        Args:
            omnidexer: The omnidexer for content lookup
            template_engine: LaTeX template engine for rendering appendices
        """
        self.omnidexer = omnidexer
        self.template_engine = template_engine
        self.spell_collector = SpellCollector(omnidexer)
        self.item_collector = ItemCollector(omnidexer)
        self.creature_collector = CreatureCollector(omnidexer)

        # Use existing entry renderer system for consistent rendering
        from dnd5e.renderers.latex.entry_renderers import EntryRendererRegistry

        self.entry_registry = EntryRendererRegistry()

    def generate_appendices(
        self, content_tracker: ContentTracker, flags: AppendixFlags
    ) -> list[AppendixSection]:
        """Generate appendix sections based on tracked content and flags.

        Args:
            content_tracker: ContentTracker with tracked references
            flags: AppendixFlags indicating which appendices to generate

        Returns:
            List of AppendixSection objects with rendered content
        """
        appendices: list[AppendixSection] = []

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
    ) -> list[AppendixSection]:
        """Generate appendices with recursive reference tracking.

        Args:
            content_tracker: Initial tracked content from main document
            flags: Which appendix types to generate
            max_depth: Maximum recursion depth (default 2 = original + 1 level)

        Returns:
            List of AppendixSection objects with recursive content
        """
        if not flags.has_any_enabled() or max_depth < 1:
            return []

        # Start with primary appendices (depth 1)
        primary_appendices = self.generate_appendices(content_tracker, flags)

        if max_depth == 1 or not primary_appendices:
            return primary_appendices

        # Track secondary references from primary appendix content
        secondary_tracker = ContentTracker()

        for appendix in primary_appendices:
            if appendix.content_type == "creature" and flags.spells:
                # Track spells referenced by creatures in creature appendix
                self._track_references_in_content(appendix.content, secondary_tracker)
            elif appendix.content_type == "spell" and flags.creatures:
                # Track creatures referenced by spells in spell appendix
                self._track_references_in_content(appendix.content, secondary_tracker)
            # Items don't typically reference other content types, so skip

        # Generate secondary appendices if new content was found
        secondary_data = secondary_tracker.export_for_appendix()
        if not any(len(items) > 0 for items in secondary_data.values()):
            return primary_appendices

        # Create flags for secondary content (only generate what was referenced)
        secondary_flags = AppendixFlags(
            spells=flags.spells
            and "spell" in secondary_data
            and len(secondary_data["spell"]) > 0,
            creatures=flags.creatures
            and "creature" in secondary_data
            and len(secondary_data["creature"]) > 0,
            items=False,  # Items don't typically have references
        )

        if not secondary_flags.has_any_enabled():
            return primary_appendices

        secondary_appendices = self.generate_appendices(
            secondary_tracker, secondary_flags
        )

        # Merge secondary content into primary appendices rather than creating separate sections
        merged_appendices = self._merge_appendix_content(
            primary_appendices, secondary_appendices
        )

        return merged_appendices

    def _track_references_in_content(
        self, content: str, tracker: ContentTracker
    ) -> None:
        """Extract and track references from rendered LaTeX content.

        Args:
            content: Rendered LaTeX content to scan for references
            tracker: ContentTracker to store found references
        """
        import re

        # Find and process all tags in the content
        # This is a simplified approach - we'll look for common tag patterns
        # Pattern to match any {@tag ...} format
        tag_pattern = r"\{@(\w+)(?:\s+([^}]+))?\}"

        for match in re.finditer(tag_pattern, content):
            tag_type = match.group(1)
            tag_content = match.group(2) if match.group(2) else ""

            # Only track creature and spell tags for recursive references
            if tag_type in ["creature", "spell"] and tag_content:
                # Parse the tag content to extract name
                # Handle formats like "creature name" or "creature name|display text"
                parts = tag_content.split("|")
                entity_name = parts[0].strip()

                if entity_name:
                    # Add to tracker using add_content method
                    tracker.add_content(tag_type, entity_name, "recursive_appendix")

    def _merge_appendix_content(
        self, primary: list[AppendixSection], secondary: list[AppendixSection]
    ) -> list[AppendixSection]:
        """Merge secondary appendix content into primary appendices.

        Args:
            primary: Primary appendix sections
            secondary: Secondary appendix sections to merge

        Returns:
            Merged appendix sections
        """
        # Create a lookup for primary appendices by content type
        primary_by_type = {appendix.content_type: appendix for appendix in primary}

        # Merge secondary content into matching primary appendices
        for secondary_appendix in secondary:
            content_type = secondary_appendix.content_type

            if content_type in primary_by_type:
                primary_appendix = primary_by_type[content_type]

                # Add a section separator and merge the content
                merged_content = (
                    primary_appendix.content
                    + "\n\n\\vspace{1em}\n"
                    + "\\subsection{Additional "
                    + content_type.title()
                    + "s}\n"
                    + secondary_appendix.content
                )

                # Update the primary appendix with merged content
                primary_appendix.content = merged_content
                primary_appendix.item_count += secondary_appendix.item_count
            else:
                # If no primary appendix exists for this type, add secondary as new
                primary.append(secondary_appendix)

        return primary

    def _generate_spell_appendix(
        self, tracked_spells: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> AppendixSection | None:
        """Generate spells appendix using SpellCollector and spellbook template.

        Args:
            tracked_spells: List of tracked spell references

        Returns:
            AppendixSection with spell content or None if no spells found
        """
        if not tracked_spells:
            return None

        # Extract spell names from tracked content
        spell_names = [content["name"] for content in tracked_spells]

        # Use existing collector service
        collection_result = self.spell_collector.collect_by_names(spell_names)

        if not collection_result.spells:
            return None

        # Group spells by level for template rendering
        spells_by_level: dict[int, list] = {}
        for spell in collection_result.spells:
            spell_level = spell.level
            if spell_level not in spells_by_level:
                spells_by_level[spell_level] = []
            spells_by_level[spell_level].append(spell)

        # Sort levels (cantrips first, then 1-9)
        sorted_levels = sorted(spells_by_level.keys())

        # Generate spell content manually using the same structure as spellbook template
        content_parts = []

        for level in sorted_levels:
            spell_list = spells_by_level[level]

            # Level header
            if level == 0:
                content_parts.append("\\section{Cantrips}")
            else:
                ordinal = f"{level}{'st' if level == 1 else 'nd' if level == 2 else 'rd' if level == 3 else 'th'}"
                content_parts.append(f"\\section{{{ordinal} Level Spells}}")

            content_parts.append("\\vspace{0.5em}")

            # Spells in this level
            for i, spell in enumerate(spell_list):
                spell_latex = self._render_spell_entry(spell, content_tracker)
                content_parts.append(spell_latex)

                if i < len(spell_list) - 1:  # Not the last spell
                    content_parts.append("\\vspace{0.8em}")

            content_parts.append("")  # Add space between levels

        content = "\n".join(content_parts)

        return AppendixSection(
            title="Appendix A: Spells",
            content=content,
            content_type="spell",
            item_count=len(collection_result.spells),
        )

    def _generate_item_appendix(
        self, tracked_items: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> AppendixSection | None:
        """Generate items appendix using ItemCollector and itemcompendium template.

        Args:
            tracked_items: List of tracked item references

        Returns:
            AppendixSection with item content or None if no items found
        """
        if not tracked_items:
            return None

        # Extract item names from tracked content
        item_names = [content["name"] for content in tracked_items]

        # Use existing collector service
        collection_result = self.item_collector.collect_by_names(item_names)

        if not collection_result.items:
            return None

        # Create a single group for all items (appendix doesn't need complex grouping)
        items_by_group = {"All Items": collection_result.items}

        # Generate item content manually using the same structure as itemcompendium template
        content_parts = []

        for group_name, item_list in items_by_group.items():
            # Group header
            if group_name == "All Items":
                content_parts.append("\\section{Items}")
            else:
                content_parts.append(f"\\section{{{group_name}}}")

            content_parts.append("\\vspace{0.5em}")

            # Items in this group
            for i, item in enumerate(item_list):
                item_latex = self._render_item_entry(item, content_tracker)
                content_parts.append(item_latex)

                if i < len(item_list) - 1:  # Not the last item
                    content_parts.append("\\vspace{0.8em}")

            content_parts.append("")  # Add space between groups

        content = "\n".join(content_parts)

        return AppendixSection(
            title="Appendix B: Magic Items",
            content=content,
            content_type="item",
            item_count=len(collection_result.items),
        )

    def _generate_creature_appendix(
        self, tracked_creatures: list[dict[str, Any]], content_tracker: ContentTracker
    ) -> AppendixSection | None:
        """Generate creatures appendix using CreatureCollector and bestiary template.

        Args:
            tracked_creatures: List of tracked creature references

        Returns:
            AppendixSection with creature content or None if no creatures found
        """
        if not tracked_creatures:
            return None

        # Extract creature names from tracked content
        creature_names = [content["name"] for content in tracked_creatures]

        # Use existing collector service
        collection_result = self.creature_collector.collect_by_names(creature_names)

        if not collection_result.creatures:
            return None

        # Create a single group for all creatures (appendix doesn't need complex grouping)
        creatures_by_group = {"All Creatures": collection_result.creatures}

        # Generate creature content using entry renderer for each creature
        content_parts = []

        for group_name, creature_list in creatures_by_group.items():
            # Group header
            content_parts.append(f"\\section{{{group_name}}}")
            content_parts.append("\\vspace{0.5em}")

            # Creatures in this group
            for i, creature in enumerate(creature_list):
                creature_latex = self._render_creature_entry(creature, content_tracker)
                content_parts.append(creature_latex)

                # Add float barrier every 10 creatures to prevent accumulation (same as bestiary)
                if (i + 1) % 10 == 0 and i < len(creature_list) - 1:
                    content_parts.append("\\FloatBarrier")

                if i < len(creature_list) - 1:  # Not the last creature
                    content_parts.append("\\vspace{1.2em}")

            # Add float barrier at end of each group (same as bestiary)
            content_parts.append("\\FloatBarrier")
            content_parts.append("")  # Add space between groups

        content = "\n".join(content_parts)

        return AppendixSection(
            title="Appendix C: Creatures",
            content=content,
            content_type="creature",
            item_count=len(collection_result.creatures),
        )

    def _render_spell_entry(self, spell: Spell, content_tracker: ContentTracker) -> str:
        """Render a single spell entry using the entry renderer system.

        Args:
            spell: Spell object to render
            content_tracker: ContentTracker for tracking references

        Returns:
            LaTeX content for the spell entry
        """
        # Use existing entry renderer for consistent rendering
        from dnd5e.renderers.core.interfaces import RenderingContext

        # Create rendering context with ContentTracker for tracking references
        context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
        )

        # Get spell renderer and render
        spell_renderer = self.entry_registry.get_renderer("spell")
        return spell_renderer.render(spell, context)

    def _render_item_entry(self, item: Item, content_tracker: ContentTracker) -> str:
        """Render a single item entry using the entry renderer system.

        Args:
            item: Item object to render
            content_tracker: ContentTracker for tracking references

        Returns:
            LaTeX content for the item entry
        """
        # Use existing entry renderer for consistent rendering
        from dnd5e.renderers.core.interfaces import RenderingContext

        # Create rendering context with ContentTracker for tracking references
        context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
        )

        # Get item renderer and render
        item_renderer = self.entry_registry.get_renderer("item")
        return item_renderer.render(item, context)

    def _render_creature_entry(
        self, creature: Creature, content_tracker: ContentTracker
    ) -> str:
        """Render a single creature entry using the entry renderer system.

        Args:
            creature: Creature object to render
            content_tracker: ContentTracker for tracking references

        Returns:
            LaTeX content for the creature entry
        """
        # Use existing entry renderer for consistent rendering
        from dnd5e.renderers.core.interfaces import RenderingContext

        # Create rendering context with ContentTracker for tracking references
        context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
        )

        # Get creature renderer and render
        creature_renderer = self.entry_registry.get_renderer("creature")
        return creature_renderer.render(creature, context)
