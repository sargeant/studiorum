"""Content organization utilities for document structure."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from ...core.models.content import BaseContent, ContentType
from ...core.models.document_metadata import ContentSection, DocumentType, SectionLevel


class ContentOrganizer:
    """Organizes content for structured document generation."""

    def __init__(self, document_type: DocumentType = DocumentType.BOOK):
        """Initialize content organizer.

        Args:
            document_type: Type of document being organized
        """
        self.document_type = document_type
        self._sorters: dict[str, Callable] = {
            ContentType.SPELL.value: self._sort_spells,
            ContentType.CREATURE.value: self._sort_creatures,
            ContentType.ITEM.value: self._sort_items,
            ContentType.CLASS.value: self._sort_alphabetically,
            ContentType.RACE.value: self._sort_alphabetically,
            ContentType.BACKGROUND.value: self._sort_alphabetically,
            ContentType.FEAT.value: self._sort_alphabetically,
        }

    def organize_content(
        self, content_items: list[BaseContent]
    ) -> dict[str, list[BaseContent]]:
        """Organize content items by type and sort appropriately.

        Args:
            content_items: List of content to organize

        Returns:
            Dictionary mapping content types to sorted lists
        """
        # Group by content type
        grouped = self._group_by_content_type(content_items)

        # Sort each group appropriately
        for content_type, items in grouped.items():
            sorter = self._sorters.get(content_type, self._sort_alphabetically)
            grouped[content_type] = sorter(items)

        return grouped

    def create_hierarchical_sections(
        self, organized_content: dict[str, list[BaseContent]]
    ) -> list[ContentSection]:
        """Create hierarchical sections from organized content.

        Args:
            organized_content: Content organized by type

        Returns:
            List of hierarchical sections
        """
        sections = []

        for content_type, items in organized_content.items():
            section = self._create_section_for_content_type(content_type, items)
            sections.append(section)

        return sections

    def organize_by_source(
        self, content_items: list[BaseContent]
    ) -> dict[str, dict[str, list[BaseContent]]]:
        """Organize content by source book and then by type.

        Args:
            content_items: List of content to organize

        Returns:
            Nested dictionary: source -> content_type -> items
        """
        organized = defaultdict(lambda: defaultdict(list))

        for item in content_items:
            source_key = item.source.abbreviation
            try:
                content_type = ContentType.from_content(item).value
            except ValueError:
                content_type = "unknown"

            organized[source_key][content_type].append(item)

        # Sort items within each group
        for source in organized:
            for content_type in organized[source]:
                sorter = self._sorters.get(content_type, self._sort_alphabetically)
                organized[source][content_type] = sorter(
                    organized[source][content_type]
                )

        return dict(organized)

    def organize_by_level(
        self, content_items: list[BaseContent]
    ) -> dict[str, list[BaseContent]]:
        """Organize content by level (for spells, creatures, etc.).

        Args:
            content_items: List of content to organize

        Returns:
            Dictionary mapping level ranges to content lists
        """
        organized = defaultdict(list)

        for item in content_items:
            level_key = self._get_level_key(item)
            organized[level_key].append(item)

        # Sort items within each level group
        for level_key in organized:
            organized[level_key] = self._sort_alphabetically(organized[level_key])

        return dict(organized)

    def create_table_of_contents_data(
        self, sections: list[ContentSection]
    ) -> list[dict[str, Any]]:
        """Create table of contents data structure.

        Args:
            sections: Document sections

        Returns:
            List of ToC entries with titles, levels, and page references
        """
        toc_data = []

        for section in sections:
            toc_data.extend(self._extract_toc_entries(section))

        return toc_data

    def _group_by_content_type(
        self, content_items: list[BaseContent]
    ) -> dict[str, list[BaseContent]]:
        """Group content items by their content type.

        Args:
            content_items: List of content to group

        Returns:
            Dictionary mapping content types to lists
        """
        grouped = defaultdict(list)

        for item in content_items:
            try:
                content_type = ContentType.from_content(item).value
            except ValueError:
                content_type = "unknown"

            grouped[content_type].append(item)

        return dict(grouped)

    def _sort_spells(self, spells: list[BaseContent]) -> list[BaseContent]:
        """Sort spells by level, then school, then name.

        Args:
            spells: List of spell content

        Returns:
            Sorted list of spells
        """

        def spell_sort_key(spell):
            level = getattr(spell, "level", 0)
            school = getattr(spell, "school", "")
            name = spell.name.lower()
            return (level, school, name)

        return sorted(spells, key=spell_sort_key)

    def _sort_creatures(self, creatures: list[BaseContent]) -> list[BaseContent]:
        """Sort creatures by challenge rating, then name.

        Args:
            creatures: List of creature content

        Returns:
            Sorted list of creatures
        """

        def creature_sort_key(creature):
            # Extract challenge rating
            cr = getattr(creature, "cr", 0)
            if isinstance(cr, dict):
                cr = cr.get("cr", 0)

            # Convert fractional CRs to decimal for sorting
            if isinstance(cr, str):
                if "/" in cr:
                    num, denom = cr.split("/")
                    cr = float(num) / float(denom)
                else:
                    try:
                        cr = float(cr)
                    except ValueError:
                        cr = 0

            name = creature.name.lower()
            return (cr, name)

        return sorted(creatures, key=creature_sort_key)

    def _sort_items(self, items: list[BaseContent]) -> list[BaseContent]:
        """Sort items by type, rarity, then name.

        Args:
            items: List of item content

        Returns:
            Sorted list of items
        """

        def item_sort_key(item):
            item_type = getattr(item, "type", "")
            rarity = getattr(item, "rarity", "common")

            # Rarity order for sorting
            rarity_order = {
                "common": 0,
                "uncommon": 1,
                "rare": 2,
                "very rare": 3,
                "legendary": 4,
                "artifact": 5,
            }

            rarity_num = rarity_order.get(rarity.lower(), 99)
            name = item.name.lower()

            return (item_type, rarity_num, name)

        return sorted(items, key=item_sort_key)

    def _sort_alphabetically(self, content: list[BaseContent]) -> list[BaseContent]:
        """Sort content alphabetically by name.

        Args:
            content: List of content to sort

        Returns:
            Sorted list of content
        """
        return sorted(content, key=lambda x: x.name.lower())

    def _get_level_key(self, content: BaseContent) -> str:
        """Get level-based key for content organization.

        Args:
            content: Content item to analyze

        Returns:
            Level key for grouping
        """
        # Handle spells
        if hasattr(content, "level"):
            level = content.level
            if level == 0:
                return "Cantrips"
            elif level <= 3:
                return f"Level {level} Spells"
            elif level <= 6:
                return f"Level {level} Spells"
            else:
                return f"Level {level}+ Spells"

        # Handle creatures by CR
        if hasattr(content, "cr"):
            cr = content.cr
            if isinstance(cr, dict):
                cr = cr.get("cr", 0)

            if isinstance(cr, str):
                if "/" in cr:
                    return f"CR {cr}"
                else:
                    try:
                        cr_num = float(cr)
                    except ValueError:
                        return "CR Unknown"
            else:
                cr_num = float(cr) if cr else 0

            if cr_num < 1:
                return "CR 0-1/2"
            elif cr_num <= 4:
                return "CR 1-4"
            elif cr_num <= 10:
                return "CR 5-10"
            elif cr_num <= 16:
                return "CR 11-16"
            else:
                return "CR 17+"

        return "Miscellaneous"

    def _create_section_for_content_type(
        self, content_type: str, items: list[BaseContent]
    ) -> ContentSection:
        """Create a section for a specific content type.

        Args:
            content_type: Type of content
            items: Content items of this type

        Returns:
            ContentSection for the content type
        """
        # Determine section level based on document type
        if self.document_type == DocumentType.ARTICLE:
            level = SectionLevel.SECTION
        else:
            level = SectionLevel.CHAPTER

        # Format title
        title = self._format_content_type_title(content_type)

        section = ContentSection(
            title=title,
            level=level,
            numbered=True,
            content_items=items,
        )

        # Create subsections for complex content types
        if content_type == ContentType.SPELL.value and len(items) > 10:
            section.subsections = self._create_spell_subsections(items)
        elif content_type == ContentType.CREATURE.value and len(items) > 15:
            section.subsections = self._create_creature_subsections(items)
        elif content_type == ContentType.ITEM.value and len(items) > 20:
            section.subsections = self._create_item_subsections(items)

        return section

    def _create_spell_subsections(
        self, spells: list[BaseContent]
    ) -> list[ContentSection]:
        """Create subsections for spells organized by level.

        Args:
            spells: List of spell content

        Returns:
            List of spell subsections
        """
        # Group spells by level
        by_level = defaultdict(list)
        for spell in spells:
            level = getattr(spell, "level", 0)
            level_key = "Cantrips" if level == 0 else f"Level {level}"
            by_level[level_key].append(spell)

        # Create subsections
        subsections = []
        for level_key in sorted(by_level.keys()):
            subsection = ContentSection(
                title=level_key,
                level=SectionLevel.SECTION,
                numbered=True,
                content_items=by_level[level_key],
            )
            subsections.append(subsection)

        return subsections

    def _create_creature_subsections(
        self, creatures: list[BaseContent]
    ) -> list[ContentSection]:
        """Create subsections for creatures organized by CR.

        Args:
            creatures: List of creature content

        Returns:
            List of creature subsections
        """
        # Group creatures by CR range
        by_cr = defaultdict(list)
        for creature in creatures:
            cr_key = self._get_level_key(creature)
            by_cr[cr_key].append(creature)

        # Create subsections
        subsections = []
        cr_order = ["CR 0-1/2", "CR 1-4", "CR 5-10", "CR 11-16", "CR 17+"]

        for cr_key in cr_order:
            if cr_key in by_cr:
                subsection = ContentSection(
                    title=cr_key,
                    level=SectionLevel.SECTION,
                    numbered=True,
                    content_items=by_cr[cr_key],
                )
                subsections.append(subsection)

        return subsections

    def _create_item_subsections(
        self, items: list[BaseContent]
    ) -> list[ContentSection]:
        """Create subsections for items organized by type.

        Args:
            items: List of item content

        Returns:
            List of item subsections
        """
        # Group items by type
        by_type = defaultdict(list)
        for item in items:
            item_type = getattr(item, "type", "Miscellaneous")
            if isinstance(item_type, list):
                item_type = item_type[0] if item_type else "Miscellaneous"
            by_type[item_type].append(item)

        # Create subsections
        subsections = []
        for item_type in sorted(by_type.keys()):
            subsection = ContentSection(
                title=item_type,
                level=SectionLevel.SECTION,
                numbered=True,
                content_items=by_type[item_type],
            )
            subsections.append(subsection)

        return subsections

    def _format_content_type_title(self, content_type: str) -> str:
        """Format content type as a human-readable title.

        Args:
            content_type: Content type string

        Returns:
            Formatted title
        """
        title_mapping = {
            ContentType.SPELL.value: "Spells",
            ContentType.CREATURE.value: "Creatures and NPCs",
            ContentType.ITEM.value: "Magic Items and Equipment",
            ContentType.CLASS.value: "Classes",
            ContentType.RACE.value: "Races",
            ContentType.BACKGROUND.value: "Backgrounds",
            ContentType.FEAT.value: "Feats",
            ContentType.ADVENTURE.value: "Adventures",
            ContentType.BOOK.value: "Books",
            ContentType.SUPPLEMENT.value: "Supplemental Material",
            "unknown": "Additional Content",
        }

        return title_mapping.get(content_type, content_type.replace("_", " ").title())

    def _extract_toc_entries(
        self, section: ContentSection, level: int = 1
    ) -> list[dict[str, Any]]:
        """Extract table of contents entries from a section.

        Args:
            section: Section to extract from
            level: Current ToC level

        Returns:
            List of ToC entry dictionaries
        """
        entries = []

        # Add main section entry
        entries.append(
            {
                "title": section.title,
                "level": level,
                "numbered": section.numbered,
                "label": section.label,
                "page_ref": f"\\pageref{{{section.label}}}" if section.label else "",
            }
        )

        # Add subsection entries
        for subsection in section.subsections:
            entries.extend(self._extract_toc_entries(subsection, level + 1))

        return entries
