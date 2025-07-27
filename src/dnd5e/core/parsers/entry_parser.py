"""Parsers for extracting nested content from adventure and book entries."""

import logging
from collections.abc import Iterator
from typing import Any

from ..models.content import Source
from ..models.nested_content import (
    AdventureInset,
    AdventureSection,
    AdventureTable,
    BookInset,
    BookSection,
    BookTable,
    VariantRule,
)

logger = logging.getLogger(__name__)


class EntryParser:
    """Parser for extracting indexable content from entries."""

    def __init__(self, source: Source, parent_name: str):
        """Initialize parser with source and parent context."""
        self.source = source
        self.parent_name = parent_name

    def parse_entries(
        self, entries: list[Any], content_type: str = "adventure"
    ) -> Iterator[Any]:
        """Parse a list of entries and yield indexable content objects.

        Args:
            entries: List of entry objects to parse
            content_type: Type of content ("adventure" or "book")

        Yields:
            Indexable content objects for sections, tables, insets, etc.
        """
        if not entries:
            return

        for entry in entries:
            yield from self._parse_single_entry(entry, content_type)

    def _parse_single_entry(self, entry: Any, content_type: str) -> Iterator[Any]:
        """Parse a single entry and yield indexable content.

        Args:
            entry: Entry object to parse
            content_type: Type of content ("adventure" or "book")

        Yields:
            Indexable content objects
        """
        if isinstance(entry, str):
            # Plain text entries don't create indexable content
            return

        if not isinstance(entry, dict):
            return

        entry_type = entry.get("type", "")

        if entry_type == "section":
            yield from self._parse_section(entry, content_type)
        elif entry_type == "table":
            yield from self._parse_table(entry, content_type)
        elif entry_type in ("inset", "insetReadaloud"):
            yield from self._parse_inset(entry, content_type)
        elif entry_type == "entries":
            # Nested entries - can be variant rules or subsections
            yield from self._parse_nested_entries(entry, content_type)
        else:
            # For unknown entry types, still recursively parse nested entries
            nested_entries = entry.get("entries", [])
            if nested_entries:
                yield from self.parse_entries(nested_entries, content_type)

    def _parse_section(self, entry: dict[str, Any], content_type: str) -> Iterator[Any]:
        """Parse a section entry."""
        name = entry.get("name", "Unnamed Section")
        page = entry.get("page")
        section_id = entry.get("id")
        entries = entry.get("entries", [])

        if content_type == "adventure":
            section = AdventureSection(
                name=name,
                source=self.source,
                section_type="section",
                page=page,
                id=section_id,
                parent_name=self.parent_name,
                entries=entries,
            )
        else:
            section = BookSection(
                name=name,
                source=self.source,
                section_type="section",
                page=page,
                id=section_id,
                parent_name=self.parent_name,
                entries=entries,
            )

        yield section

        # Parse nested content within this section with updated parent context
        if entries:
            nested_parser = EntryParser(self.source, f"{self.parent_name} > {name}")
            yield from nested_parser.parse_entries(entries, content_type)

    def _parse_table(self, entry: dict[str, Any], content_type: str) -> Iterator[Any]:
        """Parse a table entry."""
        # Use caption as name, fallback to generic name
        name = entry.get("caption", "Table")
        if not name or name == "Table":
            name = f"Table (page {entry.get('page', '?')})"

        page = entry.get("page")
        table_id = entry.get("id")
        col_labels = entry.get("colLabels", [])
        rows = entry.get("rows", [])

        # Convert rows to list of strings
        processed_rows = []
        for row in rows:
            if isinstance(row, list):
                processed_rows.append([str(cell) for cell in row])
            else:
                processed_rows.append([str(row)])

        if content_type == "adventure":
            table = AdventureTable(
                name=name,
                source=self.source,
                caption=entry.get("caption"),
                page=page,
                id=table_id,
                parent_name=self.parent_name,
                col_labels=col_labels,
                rows=processed_rows,
            )
        else:
            table = BookTable(
                name=name,
                source=self.source,
                caption=entry.get("caption"),
                page=page,
                id=table_id,
                parent_name=self.parent_name,
                col_labels=col_labels,
                rows=processed_rows,
            )

        yield table

    def _parse_inset(self, entry: dict[str, Any], content_type: str) -> Iterator[Any]:
        """Parse an inset/sidebar entry."""
        name = entry.get("name", "Inset")
        if not name or name == "Inset":
            inset_type = entry.get("type", "inset")
            name = f"{inset_type.title()} (page {entry.get('page', '?')})"

        page = entry.get("page")
        inset_id = entry.get("id")
        inset_type = entry.get("type", "inset")
        entries = entry.get("entries", [])

        if content_type == "adventure":
            inset = AdventureInset(
                name=name,
                source=self.source,
                inset_type=inset_type,
                page=page,
                id=inset_id,
                parent_name=self.parent_name,
                entries=entries,
            )
        else:
            inset = BookInset(
                name=name,
                source=self.source,
                inset_type=inset_type,
                page=page,
                id=inset_id,
                parent_name=self.parent_name,
                entries=entries,
            )

        yield inset

    def _parse_nested_entries(
        self, entry: dict[str, Any], content_type: str
    ) -> Iterator[Any]:
        """Parse nested entries that might be variant rules or subsections."""
        name = entry.get("name")
        if not name:
            return

        page = entry.get("page")
        entry_id = entry.get("id")
        entries = entry.get("entries", [])

        # For books, treat named entries as potential variant rules or sections
        if content_type == "book":
            # Check if this looks like a variant rule (contains rule-like keywords)
            if self._looks_like_variant_rule(name, entries):
                variant_rule = VariantRule(
                    name=name,
                    source=self.source,
                    page=page,
                    id=entry_id,
                    parent_name=self.parent_name,
                    entries=entries,
                )
                yield variant_rule
            else:
                # Treat as a book section
                section = BookSection(
                    name=name,
                    source=self.source,
                    section_type="entries",
                    page=page,
                    id=entry_id,
                    parent_name=self.parent_name,
                    entries=entries,
                )
                yield section
        else:
            # For adventures, treat as adventure sections
            section = AdventureSection(
                name=name,
                source=self.source,
                section_type="entries",
                page=page,
                id=entry_id,
                parent_name=self.parent_name,
                entries=entries,
            )
            yield section

        # Note: Nested parsing is handled by _parse_section separately to avoid duplication

    def _looks_like_variant_rule(self, name: str, entries: list[Any]) -> bool:
        """Determine if an entry looks like a variant rule."""
        name_lower = name.lower()

        # Check for variant rule keywords in name
        variant_keywords = [
            "variant",
            "optional",
            "rule",
            "alternative",
            "option",
            "using",
            "different",
            "custom",
            "madness",
            "flanking",
            "grid",
            "diagonal",
            "facing",
            "initiative",
        ]

        if any(keyword in name_lower for keyword in variant_keywords):
            return True

        # Check content for rule-like language
        if entries:
            content_text = str(entries).lower()
            rule_indicators = [
                "you can use",
                "dungeon master",
                "dm can",
                "optional rule",
                "this variant",
                "instead of",
                "alternative to",
            ]
            if any(indicator in content_text for indicator in rule_indicators):
                return True

        return False
