"""Recursive entry processor for LaTeX rendering of 5etools entry structures."""

import logging
from typing import Any

from ...core.entry_registry import ValidationMode, get_registry
from ...core.exceptions import EntryProcessingError
from ...core.types import EntryData, ProcessingContext
from ..base import RenderContext
from .unicode_mappings import (
    get_latex_special_chars,
    get_unicode_to_latex_mappings,
    get_unmapped_unicode_chars,
)

logger = logging.getLogger(__name__)


class RecursiveEntryProcessor:
    """Processes 5etools entry structures recursively into LaTeX content.

    This class handles the recursive processing of nested entry structures
    commonly found in 5etools data, such as books, adventures, and other
    complex content types.

    Enhanced with validation, error handling, and comprehensive logging.
    """

    def __init__(
        self,
        use_dnd_template: bool = True,
        validation_mode: ValidationMode | None = None,
    ):
        """Initialize the recursive entry processor.

        Args:
            use_dnd_template: Whether to use DND template environments
            validation_mode: Override global validation mode for this processor
        """
        self.use_dnd_template = use_dnd_template
        self._depth = 0  # Track nesting depth for proper sectioning
        self._validation_mode = validation_mode
        self._registry = get_registry()
        self._entries_processed = 0
        self._errors_encountered = 0

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

        Raises:
            EntryProcessingError: If entry processing fails critically
        """
        self._entries_processed += 1
        entry_type = entry.get("type", "")

        try:
            # Log entry processing for debugging
            logger.debug(
                f"Processing LaTeX entry type '{entry_type}' at depth {self._depth}"
            )

            # Validate entry type if not empty
            if entry_type:
                # Create ValidationContext for modern interface
                from ...core.entry_registry import ValidationContext

                validation_context = ValidationContext(
                    entry_data=entry,
                    source=getattr(context, "source_name", "unknown"),
                    parent_name=f"depth_{self._depth}",
                    entry_type=entry_type,
                    validation_mode=self._validation_mode,
                )

                # Use modern ValidationContext interface
                self._registry.validate_entry_type(validation_context)

            # Dispatch to specific processing methods
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
            elif entry_type == "actions":
                return self._process_actions(entry, context)
            elif entry_type == "attack":
                return self._process_attack(entry, context)
            elif entry_type == "options":
                return self._process_options(entry, context)
            elif entry_type == "variant":
                return self._process_variant(entry, context)
            elif entry_type == "variantSub":
                return self._process_variant_sub(entry, context)
            elif entry_type == "abilityDc":
                return self._process_ability_dc(entry, context)
            elif entry_type == "abilityAttackMod":
                return self._process_ability_attack_mod(entry, context)
            elif entry_type == "abilityGeneric":
                return self._process_ability_generic(entry, context)
            elif entry_type == "spellcasting":
                return self._process_spellcasting(entry, context)
            elif entry_type == "bonus":
                return self._process_bonus(entry, context)
            elif entry_type == "bonusSpeed":
                return self._process_bonus_speed(entry, context)
            elif entry_type == "dice":
                return self._process_dice(entry, context)
            elif entry_type == "item":
                return self._process_item(entry, context)
            elif entry_type == "cell":
                return self._process_cell(entry, context)
            else:
                # Generic entry with name and entries
                if entry_type:
                    logger.debug(
                        f"Using generic processing for entry type '{entry_type}' at depth {self._depth}"
                    )
                return self._process_generic_entry(entry, context)

        except Exception as e:
            self._errors_encountered += 1

            # Re-raise our own exceptions
            if isinstance(e, EntryProcessingError):
                raise

            # Wrap other exceptions with context
            raise EntryProcessingError(
                message=f"Failed to process LaTeX entry: {str(e)}",
                entry=entry,
                source=getattr(context, "source_name", "unknown"),
                parent_name=f"depth_{self._depth}",
                entry_type=entry_type,
            ) from e

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
                return f"\\begin{{DndSidebar}}{{}}\n{content}\n\\end{{DndSidebar}}"
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
        col_styles = table.get("colStyles", [])
        rows = table.get("rows", [])

        if not rows:
            return f"% Empty table: {caption}" if caption else "% Empty table"

        # Use DND table if available
        if self.use_dnd_template:
            result = []
            if caption:
                result.append(f"% Table: {caption}")

            # Determine column count from col_labels, col_styles, or first row
            if col_labels:
                col_count = len(col_labels)
            elif col_styles:
                col_count = len(col_styles)
            elif rows and isinstance(rows[0], list):
                col_count = len(rows[0])
            else:
                col_count = 2  # Default fallback

            # Build column specification from colStyles or use defaults
            col_spec = self._build_column_spec(col_styles, col_count)

            # Use correct DndTable syntax: \begin{DndTable}[header=Name]{column_spec}
            header_text = self._escape_latex(caption) if caption else "Table"
            result.append(
                f"\\begin{{DndTable}}[header={{{header_text}}}]{{{col_spec}}}"
            )

            # Header row (only if we have col_labels)
            if col_labels:
                header_row = " & ".join(
                    [self._escape_latex(str(label)) for label in col_labels]
                )
                result.append(f"{header_row} \\\\")

            # Data rows
            for row in rows:
                if isinstance(row, list):
                    processed_cells = []
                    for cell in row:
                        if isinstance(cell, dict):
                            # Process dict cells (e.g., {"type": "cell", "roll": {...}})
                            processed_cell = self.process_entry_dict(cell, context)
                        else:
                            # Process string cells
                            processed_cell = self._process_text_with_tags(
                                str(cell), context
                            )
                        processed_cells.append(processed_cell)

                    row_data = " & ".join(processed_cells)
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
                processed_cells = []
                for cell in row:
                    if isinstance(cell, dict):
                        # Process dict cells (e.g., {"type": "cell", "roll": {...}})
                        processed_cell = self.process_entry_dict(cell, context)
                    else:
                        # Process string cells
                        processed_cell = self._process_text_with_tags(
                            str(cell), context
                        )
                    processed_cells.append(processed_cell)

                row_data = " & ".join(processed_cells)
                result.append(f"{row_data} \\\\")

        result.append("\\hline")
        result.append("\\end{tabular}")
        result.append("\\end{table}")

        return "\n".join(result)

    def _build_column_spec(self, col_styles: list[str], col_count: int) -> str:
        """Build LaTeX column specification from 5etools colStyles.

        Args:
            col_styles: List of Bootstrap column style classes (e.g., ["col-2 bold", "col-10"])
            col_count: Number of columns as fallback

        Returns:
            LaTeX column specification string using only DndTable-supported types (e.g., "cl")
        """
        if not col_styles:
            # Fallback: use left-aligned columns
            return "l" * col_count

        col_specs = []
        for style in col_styles:
            # Parse Bootstrap classes like "col-2 bold", "col-10", "col-4 text-center"
            classes = style.split()
            col_width = None
            alignment = "l"  # default left

            for cls in classes:
                if cls.startswith("col-"):
                    try:
                        width_num = int(cls.split("-")[1])
                        col_width = width_num
                    except (IndexError, ValueError):
                        continue
                elif cls == "text-center":
                    alignment = "c"
                elif cls == "text-right":
                    alignment = "r"
                # Note: "bold" and other text styling are passed through as CSS classes - not handled in column specs
                # The JavaScript code shows colStyles primarily handle layout (Bootstrap grid) and alignment

            # Smart hybrid approach: use X for wide columns, l for most content
            if col_width is None:
                # No width specified, default to left-aligned
                col_specs.append("l")
            elif col_width >= 8:
                # Wide description columns - use expandable columns for text wrapping
                col_specs.append("X")
            elif col_width <= 2 and alignment == "c":
                # Only center narrow columns when explicitly marked text-center
                col_specs.append("c")
            elif alignment == "r":
                # Respect explicit right alignment
                col_specs.append("r")
            else:
                # Default to left-aligned for most content
                col_specs.append("l")

        return "".join(col_specs)

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

        # Type cast needed due to forward reference in RenderContext
        result = context.tag_resolver.process_text(text)
        return str(result)

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

    def _process_actions(self, actions: dict[str, Any], context: RenderContext) -> str:
        """Process an actions entry for creature statblocks.

        Args:
            actions: Actions dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = actions.get("name", "")
        entries = actions.get("entries", [])

        result = []
        if name:
            result.append(f"\\textbf{{{self._escape_latex(name)}.}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_attack(self, attack: dict[str, Any], context: RenderContext) -> str:
        """Process an attack entry for creature statblocks.

        Args:
            attack: Attack dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = attack.get("name", "")
        entries = attack.get("entries", [])

        result = []
        if name:
            result.append(f"\\textit{{{self._escape_latex(name)}.}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_options(self, options: dict[str, Any], context: RenderContext) -> str:
        """Process an options entry for choice-based content.

        Args:
            options: Options dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entries = options.get("entries", [])

        if not entries:
            return ""

        result = ["\\begin{itemize}"]

        for entry in entries:
            if isinstance(entry, str):
                result.append(f"\\item {self._process_text_with_tags(entry, context)}")
            elif isinstance(entry, dict):
                processed_entry = self.process_entry_dict(entry, context)
                result.append(f"\\item {processed_entry}")
            else:
                result.append(f"\\item {str(entry)}")

        result.append("\\end{itemize}")
        return "\n".join(result)

    def _process_variant(self, variant: dict[str, Any], context: RenderContext) -> str:
        """Process a variant entry for alternative rules.

        Args:
            variant: Variant dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = variant.get("name", "")
        entries = variant.get("entries", [])

        result = []

        # Create variant header
        if name:
            result.append(f"\\textbf{{Variant: {self._escape_latex(name)}}}")
        else:
            result.append("\\textbf{Variant:}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return "\n\n".join(result)

    def _process_variant_sub(
        self, variant_sub: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a variantSub entry for sub-variants.

        Args:
            variant_sub: VariantSub dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = variant_sub.get("name", "")
        entries = variant_sub.get("entries", [])

        result = []

        if name:
            result.append(f"\\textit{{{self._escape_latex(name)}:}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_ability_dc(
        self, ability_dc: dict[str, Any], context: RenderContext
    ) -> str:
        """Process an abilityDc entry for save DC descriptions.

        Args:
            ability_dc: AbilityDc dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = ability_dc.get("name", "Save DC")
        attributes = ability_dc.get("attributes", [])

        # Map ability scores to full names
        ability_names = {
            "str": "Strength",
            "dex": "Dexterity",
            "con": "Constitution",
            "int": "Intelligence",
            "wis": "Wisdom",
            "cha": "Charisma",
        }

        result = [f"\\textbf{{{self._escape_latex(name)}:}}"]

        if attributes:
            # Use first attribute for DC calculation
            attr = attributes[0]
            ability_name = ability_names.get(attr, attr.capitalize())
            result.append(f"8 + proficiency bonus + {ability_name} modifier")
        else:
            result.append("8 + proficiency bonus + ability modifier")

        return " ".join(result)

    def _process_ability_attack_mod(
        self, ability_mod: dict[str, Any], context: RenderContext
    ) -> str:
        """Process an abilityAttackMod entry for attack modifiers.

        Args:
            ability_mod: AbilityAttackMod dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = ability_mod.get("name", "Attack Bonus")
        attributes = ability_mod.get("attributes", [])

        # Map ability scores to full names
        ability_names = {
            "str": "Strength",
            "dex": "Dexterity",
            "con": "Constitution",
            "int": "Intelligence",
            "wis": "Wisdom",
            "cha": "Charisma",
        }

        result = [f"\\textbf{{{self._escape_latex(name)}:}}"]

        if attributes:
            # Use first attribute for attack bonus calculation
            attr = attributes[0]
            ability_name = ability_names.get(attr, attr.capitalize())
            result.append(f"proficiency bonus + {ability_name} modifier")
        else:
            result.append("proficiency bonus + ability modifier")

        return " ".join(result)

    def _process_ability_generic(
        self, ability: dict[str, Any], context: RenderContext
    ) -> str:
        """Process an abilityGeneric entry for generic ability descriptions.

        Args:
            ability: AbilityGeneric dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = ability.get("name", "")
        text = ability.get("text", "")

        result = []
        if name:
            result.append(f"\\textbf{{{self._escape_latex(name)}:}}")

        if text:
            result.append(self._process_text_with_tags(text, context))

        return " ".join(result)

    def _process_spellcasting(
        self, spellcasting: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a spellcasting entry for creature spell abilities.

        Args:
            spellcasting: Spellcasting dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = spellcasting.get("name", "Spellcasting")
        header_entries = spellcasting.get("headerEntries", [])
        spells = spellcasting.get("spells", {})

        result = []

        # Add header
        result.append(f"\\textbf{{{self._escape_latex(name)}.}}")

        # Process header entries
        if header_entries:
            processed_headers = self.process_entries(header_entries, context)
            result.extend(processed_headers)

        # Process spell levels
        for level, spell_data in sorted(
            spells.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999
        ):
            spell_list = spell_data.get("spells", [])
            slots = spell_data.get("slots")

            if not spell_list:
                continue

            # Format spell level header
            if level == "0":
                level_header = "\\textbf{Cantrips (at will):}"
            else:
                level_suffix = {"1": "st", "2": "nd", "3": "rd"}.get(level, "th")
                if slots:
                    level_header = (
                        f"\\textbf{{{level}{level_suffix} level ({slots} slots):}}"
                    )
                else:
                    level_header = f"\\textbf{{{level}{level_suffix} level:}}"

            result.append(level_header)

            # Process spells for this level
            processed_spells = self.process_entries(spell_list, context)
            result.append(", ".join(processed_spells))

        return "\n\n".join(result)

    def _process_bonus(self, bonus: dict[str, Any], context: RenderContext) -> str:
        """Process a bonus entry for numerical bonuses.

        Args:
            bonus: Bonus dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        value = bonus.get("value", 0)

        if value >= 0:
            return f"+{value}"
        else:
            return str(value)

    def _process_bonus_speed(
        self, bonus_speed: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a bonusSpeed entry for speed bonuses.

        Args:
            bonus_speed: BonusSpeed dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        value = bonus_speed.get("value", 0)

        if value >= 0:
            return f"+{value} ft."
        else:
            return f"{value} ft."

    def _process_dice(self, dice: dict[str, Any], context: RenderContext) -> str:
        """Process a dice entry for dice roll notation.

        Args:
            dice: Dice dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        to_roll = dice.get("toRoll", [])

        if not to_roll:
            return ""

        dice_strings = []
        for roll in to_roll:
            number = roll.get("number", 1)
            faces = roll.get("faces", 6)
            modifier = roll.get("modifier", 0)

            dice_str = f"{number}d{faces}"
            if modifier > 0:
                dice_str += f"+{modifier}"
            elif modifier < 0:
                dice_str += str(modifier)

            dice_strings.append(dice_str)

        return ", ".join(dice_strings)

    def _process_item(self, item: dict[str, Any], context: RenderContext) -> str:
        """Process an item entry for list items.

        Args:
            item: Item dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = item.get("name", "")
        entry = item.get("entry", "")
        entries = item.get("entries", [])

        result = []

        if name:
            result.append(f"\\textbf{{{self._escape_latex(name)}.}}")

        # Handle either single entry or multiple entries
        if entry:
            result.append(self._process_text_with_tags(entry, context))
        elif entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_cell(self, cell: dict[str, Any], context: RenderContext) -> str:
        """Process a cell entry with roll data for tables.

        Args:
            cell: Cell dictionary with optional roll data
            context: Rendering context

        Returns:
            LaTeX string for table cell content

        Examples:
            {"type": "cell", "roll": {"exact": 1}} -> "1"
            {"type": "cell", "roll": {"min": 3, "max": 4}} -> "3–4"
            {"type": "cell", "roll": {"exact": 2}, "entry": "{@creature goblin}"} -> "2 Goblin"
        """
        roll_data = cell.get("roll", {})
        entry_content = cell.get("entry", "")

        # Format roll data if present
        roll_text = ""
        if roll_data:
            if "exact" in roll_data:
                roll_text = str(roll_data["exact"])
            elif "min" in roll_data and "max" in roll_data:
                min_val = roll_data["min"]
                max_val = roll_data["max"]
                if min_val == max_val:
                    roll_text = str(min_val)
                else:
                    # Use en dash for ranges
                    roll_text = f"{min_val}–{max_val}"

        # Process entry content if present (may contain tags)
        if entry_content:
            processed_entry = self._process_text_with_tags(entry_content, context)
            if roll_text:
                return f"{roll_text} {processed_entry}"
            else:
                return processed_entry

        return roll_text

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics for this processor instance.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "entries_processed": self._entries_processed,
            "errors_encountered": self._errors_encountered,
            "current_depth": self._depth,
            "registry_statistics": self._registry.statistics,
            "unknown_types": list(self._registry.unknown_types),
        }

    def log_processing_summary(self) -> None:
        """Log a summary of processing statistics."""
        stats = self.get_processing_statistics()

        logger.info(
            f"LaTeX entry processor summary: "
            f"{stats['entries_processed']} entries processed, "
            f"{stats['errors_encountered']} errors encountered, "
            f"max depth: {stats['current_depth']}"
        )

        if stats["unknown_types"]:
            logger.warning(
                f"Unknown entry types in LaTeX processing: "
                f"{', '.join(stats['unknown_types'])}"
            )

    def reset_statistics(self) -> None:
        """Reset processing statistics."""
        self._entries_processed = 0
        self._errors_encountered = 0
