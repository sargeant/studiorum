"""ContentListWriter service for saving tracked content to files in enhanced format.

This service processes ContentTracker data and writes it to files in the enhanced
"Count Name|Source" format, providing structured content lists for appendix generation.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..references.content_tracker import ContentTracker
    from ..result import Result

from ..logging import get_logger
from ..result import Error, Success

logger = get_logger(__name__)


class ContentListWriterError(Exception):
    """Errors that can occur during content list writing operations."""

    pass


class ContentListWriter:
    """Service for writing tracked content to files in enhanced format.

    This service takes ContentTracker data and writes it to files using the enhanced
    "Count Name|Source" format. It provides filtering by content type, handles missing
    sources gracefully, and includes descriptive headers for generated files.

    Features:
    - Enhanced format with reference counts and source abbreviations
    - Content type filtering for targeted exports
    - Descriptive file headers with metadata
    - Graceful handling of edge cases (missing sources, zero counts)
    - Path-based file output with automatic directory creation
    - Comprehensive error handling and logging

    Example output format:
        # Generated content list for adventure: Curse of Strahd
        # Format: [Count] Name|Source
        # Generated: 2025-09-15 14:30:00
        3 Goblin|MM
        1 Strahd von Zarovich|CoS
        2 Wolf|MM
    """

    def __init__(self) -> None:
        """Initialize the ContentListWriter service."""
        logger.debug("ContentListWriter service initialized")

    def write_content_list(
        self,
        content_tracker: ContentTracker,
        output_path: Path,
        *,
        content_type_filter: str | None = None,
        title: str | None = None,
        sort_by_count: bool = False,
        include_zero_counts: bool = False,
    ) -> Result[int, ContentListWriterError]:
        """Write tracked content to a file in enhanced format.

        Args:
            content_tracker: ContentTracker instance containing tracked content
            output_path: Path where the content list should be written
            content_type_filter: Optional filter to include only specific content type
            title: Optional title for the content list (e.g., adventure name)
            sort_by_count: If True, sort by reference count (descending), else by name
            include_zero_counts: If True, include content with zero reference counts

        Returns:
            Result containing the number of entries written, or an error

        Example:
            writer = ContentListWriter()
            result = writer.write_content_list(
                tracker,
                Path("output/creatures.txt"),
                content_type_filter="creature",
                title="Curse of Strahd",
                sort_by_count=True
            )
            if isinstance(result, Success):
                print(f"Wrote {result.unwrap()} entries")
        """
        try:
            logger.info(
                "Writing content list",
                output_path=str(output_path),
                content_type_filter=content_type_filter,
                title=title,
            )

            # Get tracked content data
            export_data = content_tracker.export_for_appendix()

            if not export_data:
                logger.warning("No tracked content found, writing empty file")
                return self._write_empty_file(output_path, title)

            # Filter by content type if specified
            if content_type_filter:
                content_type_filter = content_type_filter.lower().strip()
                if content_type_filter not in export_data:
                    logger.warning(
                        "Content type filter not found in tracked data",
                        filter=content_type_filter,
                        available_types=list(export_data.keys()),
                    )
                    return self._write_empty_file(output_path, title)

                filtered_data = {content_type_filter: export_data[content_type_filter]}
                logger.debug(
                    "Applied content type filter",
                    filter=content_type_filter,
                    entries_count=len(filtered_data[content_type_filter]),
                )
            else:
                filtered_data = export_data

            # Prepare entries for writing
            entries = self._prepare_entries(
                filtered_data, sort_by_count, include_zero_counts
            )

            if not entries:
                logger.warning("No entries to write after filtering")
                return self._write_empty_file(output_path, title)

            # Write to file
            entries_written = self._write_entries_to_file(output_path, entries, title)

            logger.info(
                "Content list written successfully",
                output_path=str(output_path),
                entries_written=entries_written,
            )

            return Success(entries_written)

        except Exception as e:
            error_msg = f"Failed to write content list to {output_path}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(ContentListWriterError(error_msg))

    def write_all_content_types(
        self,
        content_tracker: ContentTracker,
        output_directory: Path,
        *,
        title: str | None = None,
        sort_by_count: bool = False,
        include_zero_counts: bool = False,
    ) -> Result[dict[str, int], ContentListWriterError]:
        """Write separate files for each content type.

        Args:
            content_tracker: ContentTracker instance containing tracked content
            output_directory: Directory where content type files should be written
            title: Optional title for the content lists
            sort_by_count: If True, sort by reference count (descending), else by name
            include_zero_counts: If True, include content with zero reference counts

        Returns:
            Result containing a dict mapping content type to number of entries written

        Example:
            writer = ContentListWriter()
            result = writer.write_all_content_types(
                tracker,
                Path("output/"),
                title="Tomb of Annihilation"
            )
            if isinstance(result, Success):
                counts = result.unwrap()
                print(f"Wrote {counts['creature']} creatures, {counts['spell']} spells")
        """
        try:
            logger.info(
                "Writing all content types to separate files",
                output_directory=str(output_directory),
                title=title,
            )

            # Ensure output directory exists
            output_directory.mkdir(parents=True, exist_ok=True)

            export_data = content_tracker.export_for_appendix()
            results: dict[str, int] = {}

            if not export_data:
                logger.warning("No tracked content found")
                return Success(results)

            for content_type in export_data.keys():
                output_path = output_directory / f"{content_type}.txt"

                result = self.write_content_list(
                    content_tracker,
                    output_path,
                    content_type_filter=content_type,
                    title=title,
                    sort_by_count=sort_by_count,
                    include_zero_counts=include_zero_counts,
                )

                if isinstance(result, Error):
                    error_msg = f"Failed to write {content_type} list: {result.error}"
                    logger.error(error_msg)
                    return Error(ContentListWriterError(error_msg))

                count = result.unwrap()
                results[content_type] = count

                logger.debug(
                    "Content type file written",
                    content_type=content_type,
                    output_path=str(output_path),
                    entries_count=count,
                )

            logger.info(
                "All content type files written successfully",
                output_directory=str(output_directory),
                content_types=list(results.keys()),
                total_entries=sum(results.values()),
            )

            return Success(results)

        except Exception as e:
            error_msg = f"Failed to write content type files to {output_directory}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(ContentListWriterError(error_msg))

    def _prepare_entries(
        self,
        export_data: dict[str, list[dict[str, str | int]]],
        sort_by_count: bool,
        include_zero_counts: bool,
    ) -> list[tuple[str, str, int]]:
        """Prepare entries for writing by formatting and sorting.

        Args:
            export_data: Export data from ContentTracker
            sort_by_count: Whether to sort by reference count
            include_zero_counts: Whether to include entries with zero counts

        Returns:
            List of tuples containing (formatted_line, name_for_sorting, count)
        """
        entries: list[tuple[str, str, int]] = []

        for content_type, content_list in export_data.items():
            for content_entry in content_list:
                name = str(content_entry["name"])
                source = content_entry.get("source", "")
                count = int(content_entry.get("reference_count", 0))

                # Filter zero counts if requested
                if not include_zero_counts and count == 0:
                    continue

                # Format the line
                if source:
                    formatted_line = f"{count} {name}|{source}"
                else:
                    # Handle missing source gracefully
                    formatted_line = f"{count} {name}|Unknown"
                    logger.debug(
                        "Content entry missing source",
                        name=name,
                        content_type=content_type,
                    )

                entries.append((formatted_line, name, count))

        # Sort entries
        if sort_by_count:
            # Sort by count (descending), then by name (ascending)
            entries.sort(key=lambda x: (-x[2], x[1].lower()))
        else:
            # Sort by name (ascending)
            entries.sort(key=lambda x: x[1].lower())

        return entries

    def _write_entries_to_file(
        self, output_path: Path, entries: list[tuple[str, str, int]], title: str | None
    ) -> int:
        """Write formatted entries to file with header.

        Args:
            output_path: Path to write the file
            entries: Prepared entries to write
            title: Optional title for the header

        Returns:
            Number of entries written
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # Write header
            self._write_file_header(f, title)

            # Write entries
            for formatted_line, _, _ in entries:
                f.write(f"{formatted_line}\n")

        return len(entries)

    def _write_file_header(self, file_handle: Any, title: str | None) -> None:
        """Write descriptive header to file.

        Args:
            file_handle: Open file handle to write to
            title: Optional title for the content list
        """
        title_line = f"adventure: {title}" if title else "content tracking session"
        file_handle.write(f"# Generated content list for {title_line}\n")
        file_handle.write("# Format: [Count] Name|Source\n")
        file_handle.write(
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        file_handle.write("#\n")

    def _write_empty_file(
        self, output_path: Path, title: str | None
    ) -> Result[int, ContentListWriterError]:
        """Write an empty file with header when no content is available.

        Args:
            output_path: Path to write the file
            title: Optional title for the header

        Returns:
            Success result with 0 entries written
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w", encoding="utf-8") as f:
                self._write_file_header(f, title)
                f.write("# No content entries found\n")

            logger.info("Empty content list file written", output_path=str(output_path))
            return Success(0)

        except Exception as e:
            error_msg = f"Failed to write empty file to {output_path}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(ContentListWriterError(error_msg))

    def get_service_name(self) -> str:
        """Return the service name for identification."""
        return "ContentListWriter"
