"""Recursive entry processor for LaTeX rendering of 5etools entry structures."""

import logging
from typing import Any

from ..base import RenderContext
from .unicode_mappings import (
    get_latex_special_chars,
    get_unicode_to_latex_mappings,
    get_unmapped_unicode_chars,
)


class RecursiveEntryProcessor:
    """Processes 5etools entry structures recursively into LaTeX content.

    This class handles the recursive processing of nested entry structures
    commonly found in 5etools data, such as books, adventures, and other
    complex content types.
    """

    def __init__(self, use_dnd_template: bool = True):
        """Initialize the recursive entry processor.

        Args:
            use_dnd_template: Whether to use DND template environments
        """
        self.use_dnd_template = use_dnd_template
        self._depth = 0  # Track nesting depth for proper sectioning

    def process_entries(
        self, entries: list[str | dict[str, Any]], context: RenderContext
    ) -> list[str]:
        """Process a list of entries into LaTeX content.

        Args:
            entries: List of entry objects/strings
            context: Rendering context

        Returns:
            List of processed LaTeX strings
        """
        processed = []

        for entry in entries:
            if isinstance(entry, str):
                # Plain text entry - process tags
                processed.append(self._process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                processed.append(self.process_entry_dict(entry, context))
            else:
                # Fallback for other types
                processed.append(str(entry))

        return processed

    def process_entry_dict(self, entry: dict[str, Any], context: RenderContext) -> str:
        """Process a dictionary entry into LaTeX.

        Args:
            entry: Entry dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entry_type = entry.get("type", "")

        if entry_type == "section":
            return self._process_section(entry, context)
        elif entry_type == "entries":
            return self._process_entries_block(entry, context)
        elif entry_type == "insetReadaloud":
            return self._process_inset_readaloud(entry, context)
        elif entry_type == "inset":
            return self._process_inset(entry, context)
        elif entry_type == "image":
            return self._process_image(entry, context)
        elif entry_type == "list":
            return self._process_list(entry, context)
        elif entry_type == "table":
            return self._process_table(entry, context)
        elif entry_type == "quote":
            return self._process_quote(entry, context)
        else:
            # Generic entry with name and entries
            return self._process_generic_entry(entry, context)

    def _process_section(self, section: dict[str, Any], context: RenderContext) -> str:
        """Process a section entry with proper nesting depth.

        Args:
            section: Section dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = section.get("name", "")
        entries = section.get("entries", [])

        result = []
        if name:
            # Determine sectioning command based on depth
            section_cmd = self._get_section_command(self._depth)
            result.append(f"\\{section_cmd}{{{self._escape_latex(name)}}}")

        if entries:
            # Increase depth for nested entries
            self._depth += 1
            try:
                processed_entries = self.process_entries(entries, context)
                result.extend(processed_entries)
            finally:
                self._depth -= 1

        return "\n\n".join(result)

    def _process_entries_block(
        self, block: dict[str, Any], context: RenderContext
    ) -> str:
        """Process an entries block.

        Args:
            block: Entries block dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = block.get("name", "")
        entries = block.get("entries", [])

        result = []
        if name:
            # Use subsection for named entries blocks
            section_cmd = self._get_section_command(self._depth + 1)
            result.append(f"\\{section_cmd}{{{self._escape_latex(name)}}}")

        if entries:
            self._depth += 1
            try:
                processed_entries = self.process_entries(entries, context)
                result.extend(processed_entries)
            finally:
                self._depth -= 1

        return "\n\n".join(result)

    def _process_inset_readaloud(
        self, inset: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a read-aloud inset using DND template environments.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entries = inset.get("entries", [])
        processed_entries = self.process_entries(entries, context)
        content = "\n".join(processed_entries)

        if self.use_dnd_template:
            return f"\\begin{{DndReadAloud}}\n{content}\n\\end{{DndReadAloud}}"
        else:
            return f"\\begin{{quotation}}\\em\n{content}\n\\end{{quotation}}"

    def _process_inset(self, inset: dict[str, Any], context: RenderContext) -> str:
        """Process a generic inset using DND template environments.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = inset.get("name", "")
        entries = inset.get("entries", [])
        processed_entries = self.process_entries(entries, context)
        content = "\n".join(processed_entries)

        if self.use_dnd_template:
            if name:
                return f"\\begin{{DndSidebar}}{{{self._escape_latex(name)}}}\n{content}\n\\end{{DndSidebar}}"
            else:
                return f"\\begin{{DndSidebar}}\n{content}\n\\end{{DndSidebar}}"
        else:
            result = []
            if name:
                result.append(f"\\textbf{{{self._escape_latex(name)}}}")
            result.append(f"\\begin{{quotation}}\n{content}\n\\end{{quotation}}")
            return "\n\n".join(result)

    def _process_image(self, image: dict[str, Any], context: RenderContext) -> str:
        """Process an image entry.

        Args:
            image: Image dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        href = image.get("href", "")
        title = image.get("title", "")

        if not href:
            return f"% Image placeholder: {title}" if title else "% Image placeholder"

        # Basic image inclusion
        result = []
        if title:
            result.append("\\begin{figure}[ht]")
            result.append("\\centering")
            result.append(f"\\includegraphics[width=0.8\\textwidth]{{{href}}}")
            result.append(f"\\caption{{{self._escape_latex(title)}}}")
            result.append("\\end{figure}")
        else:
            result.append("\\begin{center}")
            result.append(f"\\includegraphics[width=0.8\\textwidth]{{{href}}}")
            result.append("\\end{center}")

        return "\n".join(result)

    def _process_list(self, list_entry: dict[str, Any], context: RenderContext) -> str:
        """Process a list entry.

        Args:
            list_entry: List dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        items = list_entry.get("items", [])
        list_type = list_entry.get("style", "unordered")

        if not items:
            return ""

        # Determine list environment
        env = "enumerate" if list_type == "ordered" else "itemize"

        result = [f"\\begin{{{env}}}"]

        for item in items:
            if isinstance(item, str):
                result.append(f"\\item {self._process_text_with_tags(item, context)}")
            elif isinstance(item, dict):
                # Handle nested entries in list items
                processed_item = self.process_entry_dict(item, context)
                result.append(f"\\item {processed_item}")
            else:
                result.append(f"\\item {str(item)}")

        result.append(f"\\end{{{env}}}")
        return "\n".join(result)

    def _process_table(self, table: dict[str, Any], context: RenderContext) -> str:
        """Process a table entry using DND template environments.

        Args:
            table: Table dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        caption = table.get("caption", "")
        col_labels = table.get("colLabels", [])
        rows = table.get("rows", [])

        if not rows:
            return f"% Empty table: {caption}" if caption else "% Empty table"

        # Use DND table if available
        if self.use_dnd_template and col_labels:
            result = []
            if caption:
                result.append(f"% Table: {caption}")

            # Build column specification
            col_spec = "l" * len(col_labels)

            result.append("\\begin{DndTable}[")
            result.append(
                f"  caption={{{self._escape_latex(caption) if caption else 'Table'}}},"
            )
            result.append(f"  cols={{{col_spec}}}")
            result.append("]")

            # Header row
            header_row = " & ".join(
                [self._escape_latex(str(label)) for label in col_labels]
            )
            result.append(f"{header_row} \\\\")

            # Data rows
            for row in rows:
                if isinstance(row, list):
                    row_data = " & ".join(
                        [self._escape_latex(str(cell)) for cell in row]
                    )
                    result.append(f"{row_data} \\\\")

            result.append("\\end{DndTable}")
            return "\n".join(result)
        else:
            # Fallback to basic table
            return self._process_basic_table(table, context)

    def _process_basic_table(
        self, table: dict[str, Any], context: RenderContext
    ) -> str:
        """Process table with basic LaTeX table environment.

        Args:
            table: Table dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        caption = table.get("caption", "")
        col_labels = table.get("colLabels", [])
        rows = table.get("rows", [])

        if not rows:
            return ""

        # Determine column count
        max_cols = max(len(row) if isinstance(row, list) else 1 for row in rows)
        if col_labels:
            max_cols = max(max_cols, len(col_labels))

        col_spec = "l" * max_cols

        result = []
        result.append("\\begin{table}[ht]")
        result.append("\\centering")
        if caption:
            result.append(f"\\caption{{{self._escape_latex(caption)}}}")
        result.append(f"\\begin{{tabular}}{{{col_spec}}}")
        result.append("\\hline")

        # Header row
        if col_labels:
            header_row = " & ".join(
                [self._escape_latex(str(label)) for label in col_labels]
            )
            result.append(f"{header_row} \\\\ \\hline")

        # Data rows
        for row in rows:
            if isinstance(row, list):
                row_data = " & ".join([self._escape_latex(str(cell)) for cell in row])
                result.append(f"{row_data} \\\\")

        result.append("\\hline")
        result.append("\\end{tabular}")
        result.append("\\end{table}")

        return "\n".join(result)

    def _process_quote(self, quote: dict[str, Any], context: RenderContext) -> str:
        """Process a quote entry.

        Args:
            quote: Quote dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entries = quote.get("entries", [])
        by = quote.get("by", "")

        processed_entries = self.process_entries(entries, context)
        content = "\n".join(processed_entries)

        result = []
        result.append("\\begin{quotation}")
        result.append("\\em")
        result.append(content)
        if by:
            result.append(f"\n\\hfill --- {self._escape_latex(by)}")
        result.append("\\end{quotation}")

        return "\n".join(result)

    def _process_generic_entry(
        self, entry: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a generic entry with name and entries.

        Args:
            entry: Entry dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = entry.get("name", "")
        entries = entry.get("entries", [])

        result = []
        if name:
            section_cmd = self._get_section_command(self._depth + 1)
            result.append(f"\\{section_cmd}{{{self._escape_latex(name)}}}")

        if entries:
            self._depth += 1
            try:
                processed_entries = self.process_entries(entries, context)
                result.extend(processed_entries)
            finally:
                self._depth -= 1

        return "\n\n".join(result)

    def _get_section_command(self, depth: int) -> str:
        """Get appropriate sectioning command for the given depth.

        Args:
            depth: Nesting depth (0 = section, 1 = subsection, etc.)

        Returns:
            LaTeX sectioning command name
        """
        commands = [
            "section",
            "subsection",
            "subsubsection",
            "paragraph",
            "subparagraph",
        ]
        return commands[min(depth, len(commands) - 1)]

    def _process_text_with_tags(self, text: str, context: RenderContext) -> str:
        """Process text containing 5etools tags.

        Args:
            text: Text that may contain tags
            context: Rendering context

        Returns:
            Text with tags processed
        """
        if not text or not context.tag_resolver:
            return self._escape_latex(text)

        return context.tag_resolver.process_text(text)

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters and Unicode characters.

        This method handles both LaTeX special characters and Unicode characters
        that need conversion to LaTeX equivalents. It uses comprehensive mappings
        based on PyLaTeX best practices.

        Args:
            text: Text to escape

        Returns:
            LaTeX-safe text with proper character escaping
        """
        if not text:
            return ""

        # Get character mappings from the unicode_mappings module
        latex_special_chars = get_latex_special_chars()
        unicode_to_latex = get_unicode_to_latex_mappings()

        result = text

        # Apply LaTeX special character escaping first
        # Order matters: backslash must be escaped first to avoid double-escaping
        for char, replacement in latex_special_chars.items():
            result = result.replace(char, replacement)

        # Then apply Unicode character replacements
        for char, replacement in unicode_to_latex.items():
            result = result.replace(char, replacement)

        # Log any unmapped Unicode characters for debugging
        unmapped_chars = get_unmapped_unicode_chars(result)
        if unmapped_chars:
            logging.debug(
                "Found unmapped Unicode characters in text: %s",
                ", ".join(f"'{char}' (U+{ord(char):04X})" for char in unmapped_chars),
            )

        return result
