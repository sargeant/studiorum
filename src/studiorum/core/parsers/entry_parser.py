"""Parsers for extracting nested content from adventure and book entries."""

from collections.abc import Iterator
from typing import Any, Union

from studiorum.core.logging import get_logger

from ..entry_registry import ValidationMode, get_registry
from ..exceptions import EntryProcessingError
from ..models.content import Source
from ..models.nested_content import (
    # Legacy imports for backward compatibility
    Inset,
    Section,
    Table,
    VariantRule,
)
from ..types import (
    EntryDict,
    InsetEntry,
    NestedEntriesEntry,
    ParsingStatistics,
    SectionEntry,
    TableEntry,
)

logger = get_logger(__name__)


class EntryParser:
    """Parser for extracting indexable content from entries.

    This parser provides enhanced validation and error handling for entry processing,
    with comprehensive logging and statistics tracking.
    """

    def __init__(
        self,
        source: Source,
        parent_name: str,
        validation_mode: ValidationMode | None = None,
    ):
        """Initialize parser with source and parent context.

        Args:
            source: Source information for context
            parent_name: Name of parent section/container
            validation_mode: Override global validation mode for this parser instance
        """
        self.source = source
        self.parent_name = parent_name
        self._validation_mode = validation_mode
        self._registry = get_registry()
        self._entries_processed = 0
        self._errors_encountered = 0

    def parse_entries(
        self, entries: list[str | EntryDict], content_type: str = "adventure"
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

    def _parse_single_entry(
        self, entry: str | EntryDict, content_type: str
    ) -> Iterator[Any]:
        """Parse a single entry and yield indexable content.

        Args:
            entry: Entry object to parse
            content_type: Type of content ("adventure" or "book")

        Yields:
            Indexable content objects

        Raises:
            EntryProcessingError: If entry processing fails critically
        """
        self._entries_processed += 1

        try:
            # Validate basic entry structure
            if isinstance(entry, str):
                # Plain text entries don't create indexable content
                logger.debug(f"Skipping plain text entry in {self.parent_name}")
                return

            if not isinstance(entry, dict):
                logger.warning(
                    f"Non-dict entry encountered in {self.parent_name}: {type(entry).__name__}"
                )
                return

            entry_type = entry.get("type", "")

            # Log entry processing for debugging
            logger.debug(
                f"Processing entry type '{entry_type}' in {self.parent_name} (source: {self.source.abbreviation})"
            )

            # Validate entry type if not empty
            if entry_type:
                # Create ValidationContext for modern interface
                from ..entry_registry import ValidationContext

                context = ValidationContext(
                    entry_data=entry,
                    source=self.source.abbreviation,
                    parent_name=self.parent_name,
                    entry_type=entry_type,
                    validation_mode=self._validation_mode,
                )

                # Use modern ValidationContext interface
                self._registry.validate_entry_type(context)

            # Dispatch to specific parsing methods
            if entry_type == "section":
                yield from self._parse_section(entry, content_type)  # type: ignore[arg-type]
            elif entry_type == "table":
                yield from self._parse_table(entry, content_type)  # type: ignore[arg-type]
            elif entry_type in ("inset", "insetReadaloud"):
                yield from self._parse_inset(entry, content_type)  # type: ignore[arg-type]
            elif entry_type == "entries":
                # Nested entries - can be variant rules or subsections
                yield from self._parse_nested_entries(entry, content_type)  # type: ignore[arg-type]
            else:
                # For unknown/unhandled entry types, still recursively parse nested entries
                if entry_type:
                    logger.debug(
                        f"Using fallback processing for entry type '{entry_type}' in {self.parent_name}"
                    )

                nested_entries = entry.get("entries", [])
                if nested_entries:
                    yield from self.parse_entries(nested_entries, content_type)

        except Exception as e:
            self._errors_encountered += 1

            # Re-raise our own exceptions
            if isinstance(e, EntryProcessingError):
                raise

            # Wrap other exceptions with context
            raise EntryProcessingError(
                message=f"Failed to parse entry: {str(e)}",
                entry=entry if isinstance(entry, dict) else None,  # type: ignore[arg-type]
                source=self.source.abbreviation,
                parent_name=self.parent_name,
                entry_type=entry.get("type") if isinstance(entry, dict) else None,
            ) from e

    def _parse_section(self, entry: SectionEntry, content_type: str) -> Iterator[Any]:
        """Parse a section entry."""
        name = entry.get("name", "Unnamed Section")
        page = entry.get("page")
        section_id = entry.get("id")
        entries = entry.get("entries", [])

        section = Section(
            name=name,
            source=self.source,
            section_type="section",
            page=page,
            id=section_id,
            parent_name=self.parent_name,
            entries=entries,
            document_type=content_type,
        )

        yield section

        # Parse nested content within this section with updated parent context
        if entries:
            nested_parser = EntryParser(self.source, f"{self.parent_name} > {name}")
            yield from nested_parser.parse_entries(entries, content_type)

    def _parse_table(self, entry: TableEntry, content_type: str) -> Iterator[Any]:
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

        table = Table(
            name=name,
            source=self.source,
            caption=entry.get("caption"),
            page=page,
            id=table_id,
            parent_name=self.parent_name,
            col_labels=col_labels,
            rows=processed_rows,
            document_type=content_type,
        )

        yield table

    def _parse_inset(self, entry: InsetEntry, content_type: str) -> Iterator[Any]:
        """Parse an inset/sidebar entry."""
        name = entry.get("name", "Inset")
        if not name or name == "Inset":
            inset_type = entry.get("type", "inset")
            name = f"{inset_type.title()} (page {entry.get('page', '?')})"

        page = entry.get("page")
        inset_id = entry.get("id")
        inset_type = entry.get("type", "inset")
        entries = entry.get("entries", [])

        inset = Inset(
            name=name,
            source=self.source,
            inset_type=inset_type,
            page=page,
            id=inset_id,
            parent_name=self.parent_name,
            entries=entries,
            document_type=content_type,
        )

        yield inset

    def _parse_nested_entries(
        self, entry: NestedEntriesEntry, content_type: str
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
            # Check if this should be treated as a variant rule
            if self._is_variant_rule_content(name, entries, content_type):
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
                # Treat as a section
                section = Section(
                    name=name,
                    source=self.source,
                    section_type="entries",
                    page=page,
                    id=entry_id,
                    parent_name=self.parent_name,
                    entries=entries,
                    document_type=content_type,
                )
                yield section
        else:
            # For adventures, treat as sections
            section = Section(
                name=name,
                source=self.source,
                section_type="entries",
                page=page,
                id=entry_id,
                parent_name=self.parent_name,
                entries=entries,
                document_type=content_type,
            )
            yield section

        # Note: Nested parsing is handled by _parse_section separately to avoid duplication

    def _is_variant_rule_content(
        self, name: str, entries: list[str | EntryDict], content_type: str
    ) -> bool:
        """Determine if content should be treated as a variant rule.

        This replaces the brittle heuristic _looks_like_variant_rule with more
        explicit validation based on content type and structure.

        Args:
            name: Entry name
            entries: Entry content
            content_type: Type of content ("adventure" or "book")

        Returns:
            True if this should be treated as variant rule content
        """
        # Only books typically contain variant rules
        if content_type != "book":
            return False

        # Check for explicit variant rule markers in name
        name_lower = name.lower()
        explicit_variants = [
            "variant:",
            "optional:",
            "alternative:",
            "variant rule:",
            "optional rule:",
        ]

        if any(marker in name_lower for marker in explicit_variants):
            logger.debug(f"Identified variant rule by explicit marker: {name}")
            return True

        # For ambiguous cases without explicit markers, default to regular section
        # Log for debugging purposes
        ambiguous_keywords = [
            "variant",
            "optional",
            "alternative",
            "option",
            "using",
            "different",
            "custom",
        ]
        if any(keyword in name_lower for keyword in ambiguous_keywords):
            logger.debug(
                f"Ambiguous content name (treating as section): {name} "
                f"(source: {self.source.abbreviation}, parent: {self.parent_name})"
            )

        return False

    def get_processing_statistics(self) -> ParsingStatistics:
        """Get processing statistics for this parser instance.

        Returns:
            Dictionary with processing statistics
        """
        return ParsingStatistics(
            entries_processed=self._entries_processed,
            errors_encountered=self._errors_encountered,
            source=self.source.abbreviation,
            parent_name=self.parent_name,
            registry_statistics=self._registry.statistics.entry_counts.copy(),
            unknown_types=list(self._registry.unknown_types),
        )

    def log_processing_summary(self) -> None:
        """Log a summary of processing statistics."""
        stats = self.get_processing_statistics()

        logger.info(
            f"Entry parser summary for {self.parent_name} "
            f"(source: {self.source.abbreviation}): "
            f"{stats['entries_processed']} entries processed, "
            f"{stats['errors_encountered']} errors encountered"
        )

        if stats["unknown_types"]:
            logger.warning(
                f"Unknown entry types in {self.parent_name}: "
                f"{', '.join(stats['unknown_types'])}"
            )
