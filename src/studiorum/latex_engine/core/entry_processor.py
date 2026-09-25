"""Recursive entry processor for LaTeX rendering of 5etools entry structures."""

from collections.abc import Callable
from typing import Any

from studiorum.core.entry_registry import ValidationMode, get_registry
from studiorum.core.error_types import create_processing_error
from studiorum.core.logging import get_logger
from studiorum.core.result import Error
from studiorum.renderers.context import RenderingContext
from studiorum.renderers.escape import escape

from .images import emit
from .images.resolve import ImageResolver

logger = get_logger(__name__)


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
        image_resolver: ImageResolver | None = None,
    ):
        """Initialize the recursive entry processor.

        Args:
            use_dnd_template: Whether to use DND template environments
            validation_mode: Override global validation mode for this processor
            image_resolver: Finds image files; built from the config if not given
        """
        self.use_dnd_template = use_dnd_template
        self._depth = 0  # Track nesting depth for proper sectioning
        self._validation_mode = validation_mode
        self._registry = get_registry()
        self._entries_processed = 0
        self._errors_encountered = 0

        self._image_resolver = image_resolver

    def process_entries(
        self, entries: list[str | dict[str, Any]], context: RenderingContext
    ) -> list[str]:
        """Process a list of entries into LaTeX content.

        Args:
            entries: List of entry objects/strings
            context: Rendering context

        Returns:
            List of processed LaTeX strings

        Note:
            This method maintains the list[str] interface for backward compatibility
            while using Result patterns internally for error handling.
        """
        processed = []

        for entry in entries:
            if isinstance(entry, str):
                # Plain text entry - process tags
                processed.append(self._process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                result = self.process_entry_dict(entry, context)
                processed.append(result)
            else:
                # Handle Pydantic models by converting to dict
                import os

                # Debug logging for entry processing issues
                if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                    logger.warning(
                        f"Entry processing fallback triggered for type {type(entry).__name__}: {entry}"
                    )

                try:
                    # Check if it's a Pydantic model with model_dump method
                    if hasattr(entry, "model_dump"):
                        if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                            logger.info(
                                f"Converting Pydantic model {type(entry).__name__} to dict"
                            )
                        entry_dict = entry.model_dump(exclude_none=True)
                        result = self.process_entry_dict(entry_dict, context)
                        processed.append(result)
                    # Check if it's a dataclass
                    elif hasattr(entry, "__dataclass_fields__"):
                        import dataclasses

                        if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                            logger.info(
                                f"Converting dataclass {type(entry).__name__} to dict"
                            )
                        entry_dict = dataclasses.asdict(entry)
                        result = self.process_entry_dict(entry_dict, context)
                        processed.append(result)
                    else:
                        # Check if strict mode is enabled
                        if os.getenv(
                            "STUDIORUM_STRICT_ENTRY_PROCESSING", ""
                        ).lower() in (
                            "1",
                            "true",
                            "yes",
                        ):
                            error = create_processing_error(
                                message=f"Unknown entry type {type(entry).__name__} encountered in strict mode",
                                context={
                                    "entry_type_name": type(entry).__name__,
                                    "entry_data": str(entry),
                                    "strict_mode": True,
                                },
                            )
                            logger.error(
                                f"Strict mode processing failure: {error.message}"
                            )
                            raise ValueError(
                                f"Unknown entry type {type(entry).__name__} encountered in strict mode"
                            )

                        # Fallback for other types with logging
                        if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                            logger.warning(
                                f"Using str() fallback for unknown entry type {type(entry).__name__}: {entry}"
                            )
                        processed.append(str(entry))
                except Exception as e:
                    # Check if strict mode is enabled
                    if os.getenv("STUDIORUM_STRICT_ENTRY_PROCESSING", "").lower() in (
                        "1",
                        "true",
                        "yes",
                    ):
                        error = create_processing_error(
                            message=f"Failed to process entry {type(entry).__name__} in strict mode: {e}",
                            context={
                                "entry_type_name": type(entry).__name__,
                                "entry_data": str(entry),
                                "strict_mode": True,
                                "exception_type": type(e).__name__,
                            },
                        )
                        logger.error(
                            f"Strict mode entry conversion failure: {error.message}"
                        )
                        raise ValueError(
                            f"Failed to process entry {type(entry).__name__} in strict mode: {e}"
                        ) from e

                    # If conversion fails, fallback to string with logging
                    if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                        logger.error(
                            f"Entry conversion failed for {type(entry).__name__}, using str() fallback: {e}"
                        )
                    processed.append(str(entry))

        # Return processed entries (errors are logged but don't fail the whole operation)
        return processed

    def process_entry_dict(
        self, entry: dict[str, Any], context: RenderingContext
    ) -> str:
        """Process a dictionary entry into LaTeX.

        Args:
            entry: Entry dictionary
            context: Rendering context

        Returns:
            LaTeX string

        Note:
            This method maintains the str interface for backward compatibility
            while using Result patterns internally for error handling.
        """
        self._entries_processed += 1
        entry_type = entry.get("type", "")

        # Log entry processing for debugging
        logger.debug(
            f"Processing LaTeX entry type '{entry_type}' at depth {self._depth}"
        )

        # Validate entry type if not empty and not in SILENT mode
        if entry_type and self._validation_mode != ValidationMode.SILENT:
            validation_result = self._registry.validate_entry_type(
                entry_type,
                source=context.metadata.get("source_name", "unknown"),
                parent_name=f"depth_{self._depth}",
                validation_mode=self._validation_mode,
            )
            if isinstance(validation_result, Error):
                self._errors_encountered += 1
                # For backward compatibility, log error and return empty string
                logger.error(
                    f"Failed to validate LaTeX entry type '{entry_type}': {validation_result.error}"
                )
                return ""

        # Dispatch to specific processing methods
        try:
            if entry_type == "section":
                latex_result = self._process_section(entry, context)
            elif entry_type == "entries":
                latex_result = self._process_entries_block(entry, context)
            elif entry_type == "insetReadaloud":
                latex_result = self._process_inset_readaloud(entry, context)
            elif entry_type == "inset":
                latex_result = self._process_inset(entry, context)
            elif entry_type == "image":
                latex_result = self._process_image(entry, context)
            elif entry_type == "gallery":
                latex_result = self._process_gallery(entry, context)
            elif entry_type == "list":
                latex_result = self._process_list(entry, context)
            elif entry_type == "table":
                latex_result = self._process_table(entry, context)
            elif entry_type == "quote":
                latex_result = self._process_quote(entry, context)
            elif entry_type == "actions":
                latex_result = self._process_actions(entry, context)
            elif entry_type == "attack":
                latex_result = self._process_attack(entry, context)
            elif entry_type == "options":
                latex_result = self._process_options(entry, context)
            elif entry_type == "variant":
                latex_result = self._process_variant(entry, context)
            elif entry_type == "variantSub":
                latex_result = self._process_variant_sub(entry, context)
            elif entry_type == "abilityDc":
                latex_result = self._process_ability_dc(entry, context)
            elif entry_type == "abilityAttackMod":
                latex_result = self._process_ability_attack_mod(entry, context)
            elif entry_type == "abilityGeneric":
                latex_result = self._process_ability_generic(entry, context)
            elif entry_type == "spellcasting":
                latex_result = self._process_spellcasting(entry, context)
            elif entry_type == "bonus":
                latex_result = self._process_bonus(entry, context)
            elif entry_type == "bonusSpeed":
                latex_result = self._process_bonus_speed(entry, context)
            elif entry_type == "dice":
                latex_result = self._process_dice(entry, context)
            elif entry_type == "item":
                latex_result = self._process_item(entry, context)
            elif entry_type == "cell":
                latex_result = self._process_cell(entry, context)
            elif entry_type == "statblock":
                latex_result = self._process_statblock(entry, context)
            else:
                # Generic entry with name and entries
                if entry_type:
                    logger.debug(
                        f"Using generic processing for entry type '{entry_type}' at depth {self._depth}"
                    )
                latex_result = self._process_generic_entry(entry, context)

            return latex_result

        except Exception as e:
            self._errors_encountered += 1

            # Create structured error with context
            error = create_processing_error(
                message=f"Failed to process LaTeX entry: {str(e)}",
                entry_type=entry_type,
                source=context.metadata.get("source_name", "unknown"),
                parent_name=f"depth_{self._depth}",
                context={
                    "entry_data": entry,
                    "exception_type": type(e).__name__,
                    "depth": self._depth,
                },
            )

            # For backward compatibility, log error and return empty string
            logger.error(f"LaTeX entry processing failed: {error.message}")
            return ""

    def _process_section(
        self, section: dict[str, Any], context: RenderingContext
    ) -> str:
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
            section_cmd = self._get_section_command(self._depth, context)
            processed_name = self._process_text_with_tags(name, context)
            result.append(f"\\{section_cmd}{{{processed_name}}}")

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
        self, block: dict[str, Any], context: RenderingContext
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
            section_cmd = self._get_section_command(self._depth + 1, context)
            processed_name = self._process_text_with_tags(name, context)
            result.append(f"\\{section_cmd}{{{processed_name}}}")

        if entries:
            self._depth += 1
            try:
                processed_entries = self.process_entries(entries, context)
                result.extend(processed_entries)
            finally:
                self._depth -= 1

        return "\n\n".join(result)

    def _process_inset_readaloud(
        self, inset: dict[str, Any], context: RenderingContext
    ) -> str:
        """Process a read-aloud inset using DND template environments.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entries = inset.get("entries", [])

        # Create sidebar context for nested entries
        sidebar_context = RenderingContext(
            output_format=context.output_format,
            debug_mode=context.debug_mode,
            omnidexer=context.omnidexer,
            content_tracker=context.content_tracker,
            tag_resolver=context.tag_resolver,
            metadata={**context.metadata, "in_sidebar": True},
        )

        processed_entries = self.process_entries(entries, sidebar_context)
        content = "\n\n".join(processed_entries)

        if self.use_dnd_template:
            return f"\\begin{{DndReadAloud}}\n{content}\n\\end{{DndReadAloud}}"
        return f"\\begin{{quotation}}\\em\n{content}\n\\end{{quotation}}"

    def _process_inset(self, inset: dict[str, Any], context: RenderingContext) -> str:
        """Process a generic inset using DND template environments.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = inset.get("name", "")
        entries = inset.get("entries", [])

        # Create sidebar context for nested entries
        sidebar_context = RenderingContext(
            output_format=context.output_format,
            debug_mode=context.debug_mode,
            omnidexer=context.omnidexer,
            content_tracker=context.content_tracker,
            tag_resolver=context.tag_resolver,
            metadata={**context.metadata, "in_sidebar": True},
        )

        processed_entries = self.process_entries(entries, sidebar_context)
        content = "\n\n".join(processed_entries)

        if self.use_dnd_template:
            if name:
                return f"\\begin{{DndSidebar}}{{{escape(name)}}}\n{content}\n\\end{{DndSidebar}}"
            return f"\\begin{{DndSidebar}}{{}}\n{content}\n\\end{{DndSidebar}}"
        result = []
        if name:
            result.append(f"\\textbf{{{escape(name)}}}")
        result.append(f"\\begin{{quotation}}\n{content}\n\\end{{quotation}}")
        return "\n\n".join(result)

    def _process_image(self, image: dict[str, Any], context: RenderingContext) -> str:
        """Process an image entry."""
        return emit.image(image, context, self._resolver(), self._text(context))

    def _process_gallery(
        self, gallery: dict[str, Any], context: RenderingContext
    ) -> str:
        """Process a gallery entry."""
        return emit.gallery(gallery, context, self._resolver(), self._text(context))

    def _text(self, context: RenderingContext) -> Callable[[str], str]:
        return lambda text: self._process_text_with_tags(text, context)

    def _resolver(self) -> ImageResolver:
        if self._image_resolver is None:
            from studiorum.core.config.unified_config import get_app_config

            self._image_resolver = ImageResolver.from_config(get_app_config().image)
        return self._image_resolver

    def _process_list(
        self, list_entry: dict[str, Any], context: RenderingContext
    ) -> str:
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

        # Determine list environment based on style
        if list_type == "ordered":
            env = "enumerate"
        elif list_type in ("list-hang-notitle", "list-hang", "list-hang-subtrait"):
            env = "description"
        else:
            env = "itemize"

        # Check for Credits-style structure: first item is a list, rest are entries
        is_credits_style = (
            env == "description"
            and len(items) > 1
            and isinstance(items[0], dict)
            and items[0].get("type") == "list"
            and all(
                isinstance(item, dict) and item.get("type") == "entries"
                for item in items[1:]
            )
        )

        if is_credits_style:
            # For Credits-style structure, don't wrap the first list in an outer list
            result = []
            list_is_open = False
        else:
            result = [f"\\begin{{{env}}}"]
            list_is_open = True

        for i, item in enumerate(items):
            if isinstance(item, str):
                if env == "description":
                    # For description lists, use mbox for consistent spacing
                    result.append(
                        f"\\item[\\mbox{{}}] {self._process_text_with_tags(item, context)}"
                    )
                else:
                    result.append(
                        f"\\item {self._process_text_with_tags(item, context)}"
                    )
            elif isinstance(item, dict):
                # Handle nested entries in list items
                if item.get("type") == "list":
                    processed_item = self.process_entry_dict(item, context)
                    if is_credits_style and i == 0:
                        # For Credits-style first list, include directly without wrapping
                        result.append(processed_item)
                    elif env == "description":
                        # Use \item[\mbox{}] for better spacing in nested description lists
                        result.append(f"\\item[\\mbox{{}}] {processed_item}")
                    else:
                        result.append(f"\\item {processed_item}")
                elif env == "description":
                    # For description lists, try to extract name as label
                    item_name = item.get("name", "")
                    if item_name:
                        # For description lists, process only the content part (not the name)
                        if item.get("type") in ("item", "itemSub"):
                            # Special handling for "item" type - extract just entry/entries/text
                            entry_content = item.get("entry", "") or item.get(
                                "text", ""
                            )  # Support both "entry" and "text" fields
                            entries_content = item.get("entries", [])
                            if entry_content:
                                processed_content = self._process_text_with_tags(
                                    entry_content, context
                                )
                            elif entries_content:
                                processed_content = "\n\n".join(
                                    self.process_entries(entries_content, context)
                                )
                            else:
                                processed_content = ""
                        else:
                            # For other dict types, process normally
                            processed_content = self.process_entry_dict(item, context)
                        # Apply punctuation logic to the label
                        processed_name = self._process_text_with_tags(
                            item_name, context
                        )
                        if item_name.rstrip().endswith((".", ":", ";")):
                            label = processed_name
                        else:
                            label = f"{processed_name}."
                        result.append(f"\\item[{label}] {processed_content}")
                    else:
                        # Check if this is an entries block that should break out of the list
                        if item.get("type") == "entries":
                            # End the current list, process the entries block
                            if list_is_open:
                                result.append(f"\\end{{{env}}}")
                                list_is_open = False
                            processed_item = self.process_entry_dict(item, context)
                            result.append(processed_item)
                            # Check if we need to restart the list (if there are more non-entries items)
                            remaining_items = items[i + 1 :]
                            if any(
                                isinstance(it, str)
                                or (
                                    isinstance(it, dict) and it.get("type") != "entries"
                                )
                                for it in remaining_items
                            ):
                                result.append(f"\\begin{{{env}}}")
                                list_is_open = True
                        else:
                            processed_item = self.process_entry_dict(item, context)
                            result.append(f"\\item[\\mbox{{}}] {processed_item}")
                else:
                    processed_item = self.process_entry_dict(item, context)
                    result.append(f"\\item {processed_item}")
            else:
                if env == "description":
                    result.append(f"\\item[\\mbox{{}}] {str(item)}")
                else:
                    result.append(f"\\item {str(item)}")

        # Only close the list if it's still open
        if list_is_open:
            result.append(f"\\end{{{env}}}")
        return "\n".join(result)

    def _process_table(self, table: dict[str, Any], context: RenderingContext) -> str:
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

            # Debug logging for wide table handling
            import os

            if os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
                logger.info(
                    f"Table '{caption}': col_styles={col_styles}, col_count={col_count}, col_spec='{col_spec}'"
                )

            # Use correct DndTable syntax: \begin{DndTable}[header=Name]{column_spec}
            # Only include header parameter if caption exists
            if caption:
                header_text = escape(caption)
                result.append(
                    f"\\begin{{DndTable}}[header={{{header_text}}}]{{{col_spec}}}"
                )
            else:
                result.append(f"\\begin{{DndTable}}{{{col_spec}}}")

            # Header row (only if we have col_labels)
            if col_labels:
                # Process header labels with tag resolution like data cells
                processed_headers = []
                for label in col_labels:
                    processed_label = self._process_text_with_tags(str(label), context)
                    processed_headers.append(processed_label)
                header_row = " & ".join(processed_headers)
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
        # Fallback to basic table
        return self._process_basic_table(table, context)

    def _process_basic_table(
        self, table: dict[str, Any], context: RenderingContext
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
            result.append(f"\\caption{{{escape(caption)}}}")
        result.append(f"\\begin{{tabular}}{{{col_spec}}}")
        result.append("\\hline")

        # Header row
        if col_labels:
            header_row = " & ".join([escape(str(label)) for label in col_labels])
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

        # Handle tables with too many columns for the available width
        if col_count >= 4:
            fixed_columns = [
                i for i, spec in enumerate(col_specs) if spec in ["c", "l", "r"]
            ]

            # If we have 3+ fixed columns in a 4+ column table, convert some to expandable
            if len(fixed_columns) >= 3:
                # Keep the first fixed column (often labels), convert others to X
                # Prioritize converting 'c' columns (centered numbers) as they're most flexible
                converted = 0
                for i in reversed(fixed_columns[1:]):  # Skip first fixed column
                    if col_specs[i] == "c" and converted < len(fixed_columns) - 2:
                        col_specs[i] = "X"
                        converted += 1

        return "".join(col_specs)

    def _process_quote(self, quote: dict[str, Any], context: RenderingContext) -> str:
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
        content = "\n\n".join(processed_entries)

        result = []
        result.append("\\begin{quotation}")
        result.append("\\em")
        result.append(content)
        if by:
            result.append(f"\n\\hfill --- {escape(by)}")
        result.append("\\end{quotation}")

        return "\n".join(result)

    def _process_generic_entry(
        self, entry: dict[str, Any], context: RenderingContext
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
        content = entry.get("content", "")
        text = entry.get("text", "")

        result = []
        if name:
            section_cmd = self._get_section_command(self._depth + 1, context)
            processed_name = self._process_text_with_tags(name, context)
            result.append(f"\\{section_cmd}{{{processed_name}}}")

        if entries:
            self._depth += 1
            try:
                processed_entries = self.process_entries(entries, context)
                result.extend(processed_entries)
            finally:
                self._depth -= 1
        elif content:
            # Handle entries that only have content (e.g., from FluffEntry models)
            processed_content = self._process_text_with_tags(content, context)
            result.append(processed_content)
        elif text:
            # Handle entries that only have text field (common in 5etools format)
            processed_text = self._process_text_with_tags(text, context)
            result.append(processed_text)

        # Handle case where we have both name and text (section header + content)
        if name and text and not entries and not content:
            processed_text = self._process_text_with_tags(text, context)
            result.append(processed_text)

        # Debug logging for generic entries that produce no output
        import os

        if not result and os.getenv("STUDIORUM_DEBUG_ENTRY_PROCESSING"):
            entry_type = entry.get("type", "")
            logger.warning(
                f"Generic entry processing produced no output for type '{entry_type}', keys: {list(entry.keys())}"
            )

        return "\n\n".join(result)

    def _get_section_command(self, depth: int, context: RenderingContext) -> str:
        """Get appropriate sectioning command for the given depth.

        Args:
            depth: Nesting depth (0 = section, 1 = subsection, etc.)
            context: Rendering context to check document type

        Returns:
            LaTeX sectioning command name
        """
        from studiorum.core.models.document_metadata import DocumentType

        # Check if we have document type information
        document_type = None
        if context.metadata and context.metadata.get("document_type"):
            document_type = context.metadata.get("document_type")

        # Check if this is spell or item content that should use deeper sectioning
        is_spell_content = context.metadata.get("content_type") == "spell"
        is_item_content = context.metadata.get("content_type") == "item"
        is_in_sidebar = context.metadata.get("in_sidebar", False)

        # Check special content types first (these override document type)
        if is_spell_content:
            # For spells, use deeper sectioning so "At Higher Levels" becomes \paragraph
            commands = [
                "subsubsection",  # depth 0 - rarely used in spells
                "paragraph",  # depth 1 - "At Higher Levels" entries
                "subparagraph",  # depth 2+ - deeper nested content
            ]
        elif is_item_content:
            # For items, use deeper sectioning so "Spells", "Regaining Charges" become \subparagraph for indentation
            commands = [
                "subsubsection",  # depth 0 - rarely used in items
                "subparagraph",  # depth 1 - "Spells", "Regaining Charges" entries with indentation
                "subparagraph",  # depth 2+ - deeper nested content
            ]
        elif is_in_sidebar:
            # For sidebar content, use deeper sectioning so named entries become \paragraph
            commands = [
                "subsubsection",  # depth 0 - rarely used in sidebars
                "paragraph",  # depth 1 - named entries within sidebars
                "subparagraph",  # depth 2+ - deeper nested content
            ]
        elif document_type in [DocumentType.BOOK, DocumentType.ADVENTURE]:
            # For books and adventures, entry content should start at section level
            # because the document structure builder already creates \chapter{} commands
            # Map JSON depths to LaTeX sectioning to match expected hierarchy
            commands = [
                "section",  # depth 0 - "Key Plot Points", "Nakari's Lair"
                "subsection",  # depth 1 - intermediate level
                "subsection",  # depth 2 - "Lair Locations"
                "subsubsection",  # depth 3 - "N1: East Entrance", etc.
                "paragraph",  # depth 4+ - deeper nested content
            ]
        else:
            # For articles, supplements, etc. - no chapters, start with sections
            commands = [
                "section",  # depth 0
                "subsection",  # depth 1
                "subsubsection",  # depth 2
                "paragraph",  # depth 3
                "subparagraph",  # depth 4+
            ]

        return commands[min(depth, len(commands) - 1)]

    def _process_text_with_tags(self, text: str, context: RenderingContext) -> str:
        """Process text containing 5etools tags.

        Args:
            text: Text that may contain tags
            context: Rendering context

        Returns:
            Text with tags processed
        """
        if not text or not context.tag_resolver:
            return escape(text)

        # Skip obvious non-tag content to avoid parser warnings
        if not self._is_valid_tag_input(text):
            return escape(text)

        # Use tag resolver directly from context field
        tag_resolver = context.tag_resolver
        result = tag_resolver.process_text(text, context) if tag_resolver else text
        return str(result)

    def _is_valid_tag_input(self, text: str) -> bool:
        """Check if text might contain valid 5etools tags.

        This method pre-filters obvious non-tag content to prevent
        unnecessary parser warnings and improve performance.

        Args:
            text: Text to validate

        Returns:
            True if text might contain valid tags, False to skip parsing
        """
        if not text or not isinstance(text, str):
            return False

        # Skip obvious dict/json strings that were stringified from cell objects
        if text.startswith(("{'", '{"')) and text.endswith(("'}", '"}')):
            return False

        # Skip other obvious non-tag patterns
        if text.startswith(("dict(", "list(", "tuple(")):
            return False

        # If text contains potential tag markers, it's worth parsing
        if "{@" in text:
            return True

        # For short text without tag markers, skip parsing (performance optimization)
        if len(text) < 3:
            return False

        # Default to parsing for other content
        return True

    def _process_actions(
        self, actions: dict[str, Any], context: RenderingContext
    ) -> str:
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
            result.append(f"\\textbf{{{escape(name)}.}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_attack(self, attack: dict[str, Any], context: RenderingContext) -> str:
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
            result.append(f"\\textit{{{escape(name)}.}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_options(
        self, options: dict[str, Any], context: RenderingContext
    ) -> str:
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

    def _process_variant(
        self, variant: dict[str, Any], context: RenderingContext
    ) -> str:
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
            result.append(f"\\textbf{{Variant: {escape(name)}}}")
        else:
            result.append("\\textbf{Variant:}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return "\n\n".join(result)

    def _process_variant_sub(
        self, variant_sub: dict[str, Any], context: RenderingContext
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
            result.append(f"\\textit{{{escape(name)}:}}")

        if entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_ability_dc(
        self, ability_dc: dict[str, Any], context: RenderingContext
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

        result = [f"\\textbf{{{escape(name)}:}}"]

        if attributes:
            # Use first attribute for DC calculation
            attr = attributes[0]
            ability_name = ability_names.get(attr, attr.capitalize())
            result.append(f"8 + proficiency bonus + {ability_name} modifier")
        else:
            result.append("8 + proficiency bonus + ability modifier")

        return " ".join(result)

    def _process_ability_attack_mod(
        self, ability_mod: dict[str, Any], context: RenderingContext
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

        result = [f"\\textbf{{{escape(name)}:}}"]

        if attributes:
            # Use first attribute for attack bonus calculation
            attr = attributes[0]
            ability_name = ability_names.get(attr, attr.capitalize())
            result.append(f"proficiency bonus + {ability_name} modifier")
        else:
            result.append("proficiency bonus + ability modifier")

        return " ".join(result)

    def _process_ability_generic(
        self, ability: dict[str, Any], context: RenderingContext
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
            result.append(f"\\textbf{{{escape(name)}:}}")

        if text:
            result.append(self._process_text_with_tags(text, context))

        return " ".join(result)

    def _process_spellcasting(
        self, spellcasting: dict[str, Any], context: RenderingContext
    ) -> str:
        """Process a spellcasting or innate spellcasting entry for creature abilities."""
        import re

        name = spellcasting.get("name", "Spellcasting")
        render_header = bool(spellcasting.get("renderHeader", True))
        header_entries = spellcasting.get("headerEntries", [])
        footer_entries = spellcasting.get("footerEntries", [])
        spells = spellcasting.get("spells", {})
        at_will = spellcasting.get("will", [])
        daily = spellcasting.get("daily", {})
        constant = spellcasting.get("constant", [])

        result: list[str] = []

        # Add header (unless suppressed by caller)
        if render_header and name:
            result.append(f"\\textbf{{{escape(name)}.}}")

        # Header text before spells block
        if header_entries:
            processed_headers = self.process_entries(header_entries, context)
            result.extend(processed_headers)

        # Begin structured spell blocks if any spell content exists
        has_innate = bool(at_will or daily or constant)
        has_leveled = bool(spells)

        if has_innate or has_leveled:
            in_spells_env = False
            # Use DnDMonsterSpells macros only when rendering in creature/bestiary contexts
            macro_allowed = False
            try:
                if context and context.metadata:
                    tmpl = context.metadata.get("template")
                    ctype = context.metadata.get("content_type")
                    macro_allowed = bool(
                        tmpl == "bestiary"
                        or ctype == "creature"
                        or context.metadata.get("use_dnd_monster_macros")
                    )
            except Exception:
                macro_allowed = False

            # Innate spellcasting: at-will, daily, constant
            if has_innate:
                # At-will
                def _strip_textit(items: list[str]) -> list[str]:
                    cleaned: list[str] = []
                    for s in items:
                        # Remove outer \textit{...} wrappers if present
                        if s.startswith("\\textit{") and s.endswith("}"):
                            cleaned.append(s[len("\\textit{") : -1])
                        else:
                            cleaned.append(s)
                    return cleaned

                if at_will:
                    processed = self.process_entries(at_will, context)
                    # If processed contains formatting commands, fall back to plain text
                    if any("\\textit{" in s for s in processed):
                        result.append("\\textbf{At will:} " + ", ".join(processed))
                    else:
                        if macro_allowed:
                            if not in_spells_env:
                                result.append("\\begin{DndMonsterSpells}")
                                in_spells_env = True
                            at_will_text = ", ".join(processed)
                            result.append(f"  \\DndInnateSpellLevel{{{at_will_text}}}")
                        else:
                            result.append("\\textbf{At will:} " + ", ".join(processed))

                # Daily (e.g., {'3e': [...], '1': [...]})
                if daily:

                    def sort_key(k: str) -> int:
                        m = re.match(r"(\d+)", str(k))
                        return int(m.group(1)) if m else 999

                    for freq in sorted(daily.keys(), key=sort_key):
                        spell_list = daily.get(freq, [])
                        processed = self.process_entries(spell_list, context)
                        if any("\\textit{" in s for s in processed):
                            # Fallback to plain text label
                            # Keep original frequency label
                            label = escape(str(freq))
                            result.append(
                                f"\\textbf{{{label}:}} " + ", ".join(processed)
                            )
                        else:
                            # Extract leading integer for macro formatting
                            m = re.match(r"(\d+)", str(freq).strip())
                            if m:
                                n = m.group(1)
                                if macro_allowed:
                                    if not in_spells_env:
                                        result.append("\\begin{DndMonsterSpells}")
                                        in_spells_env = True
                                    result.append(
                                        f"  \\DndInnateSpellLevel[{n}]{{{', '.join(processed)}}}"
                                    )
                                else:
                                    result.append(
                                        f"\\textbf{{{n}/day:}} " + ", ".join(processed)
                                    )
                            else:
                                label = escape(str(freq))
                                result.append(
                                    f"  \\textbf{{{label}:}} {', '.join(processed)}"
                                )

                # Constant effects (no dedicated macro in template; format plainly)
                if constant:
                    processed = self.process_entries(constant, context)
                    result.append("  " + "\\textbf{Constant:} " + ", ".join(processed))

            # Prepared/leveled spellcasting
            if has_leveled:
                for level, spell_data in sorted(
                    spells.items(),
                    key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999,
                ):
                    # Support both dict-based and model-based spell level data
                    if isinstance(spell_data, dict):
                        spell_list = spell_data.get("spells", [])
                        slots = spell_data.get("slots")
                    else:
                        spell_list = getattr(spell_data, "spells", [])
                        slots = getattr(spell_data, "slots", None)

                    if not spell_list:
                        continue

                    processed_spells = self.process_entries(spell_list, context)
                    if any("\\textit{" in s for s in processed_spells):
                        # Plain text fallback for formatted content
                        if str(level) == "0":
                            level_header = "\\textbf{Cantrips (at will):}"
                        else:
                            suffix_map = {"1": "st", "2": "nd", "3": "rd"}
                            level_suffix = suffix_map.get(str(level), "th")
                            if slots:
                                level_header = f"\\textbf{{{level}{level_suffix} level ({slots} slots):}}"
                            else:
                                level_header = (
                                    f"\\textbf{{{level}{level_suffix} level:}}"
                                )
                        result.append(f"{level_header} " + ", ".join(processed_spells))
                    else:
                        spell_text = ", ".join(processed_spells)
                        if str(level) == "0":
                            if macro_allowed:
                                if not in_spells_env:
                                    result.append("\\begin{DndMonsterSpells}")
                                    in_spells_env = True
                                result.append(
                                    f"  \\DndMonsterSpellLevel{{{spell_text}}}"
                                )
                            else:
                                result.append(
                                    "\\textbf{Cantrips (at will):} " + spell_text
                                )
                        else:
                            try:
                                lvl = int(level)
                            except Exception:
                                lvl = None
                            if lvl is not None and slots is not None:
                                if macro_allowed:
                                    if not in_spells_env:
                                        result.append("\\begin{DndMonsterSpells}")
                                        in_spells_env = True
                                    result.append(
                                        f"  \\DndMonsterSpellLevel[{lvl}][{slots}]{{{spell_text}}}"
                                    )
                                else:
                                    # Compose the ordinal suffix like earlier
                                    suffix_map = {"1": "st", "2": "nd", "3": "rd"}
                                    suffix = suffix_map.get(str(lvl), "th")
                                    result.append(
                                        f"\\textbf{{{lvl}{suffix} level ({slots} slots):}} "
                                        + spell_text
                                    )
                            elif lvl is not None:
                                if macro_allowed:
                                    if not in_spells_env:
                                        result.append("\\begin{DndMonsterSpells}")
                                        in_spells_env = True
                                    result.append(
                                        f"  \\DndMonsterSpellLevel[{lvl}]{{{spell_text}}}"
                                    )
                                else:
                                    suffix_map = {"1": "st", "2": "nd", "3": "rd"}
                                    suffix = suffix_map.get(str(lvl), "th")
                                    result.append(
                                        f"\\textbf{{{lvl}{suffix} level:}} "
                                        + spell_text
                                    )
                            else:
                                result.append(f"  {spell_text}")

            if in_spells_env:
                result.append("\\end{DndMonsterSpells}")

        # Footer text
        if footer_entries:
            processed_footers = self.process_entries(footer_entries, context)
            result.extend(processed_footers)

        return "\n".join(result)

    def _process_bonus(self, bonus: dict[str, Any], context: RenderingContext) -> str:
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
        return str(value)

    def _process_bonus_speed(
        self, bonus_speed: dict[str, Any], context: RenderingContext
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
        return f"{value} ft."

    def _process_dice(self, dice: dict[str, Any], context: RenderingContext) -> str:
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

    def _process_item(self, item: dict[str, Any], context: RenderingContext) -> str:
        """Process an item entry for list items.

        Args:
            item: Item dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = item.get("name", "")
        entry = item.get("entry", "") or item.get(
            "text", ""
        )  # Support both "entry" and "text" fields
        entries = item.get("entries", [])

        # Handle both "entry" and "text" fields for content

        result = []

        if name:
            # Process name with tag resolution
            processed_name = self._process_text_with_tags(name, context)
            # Add period only if name doesn't end with punctuation
            if name.rstrip().endswith((".", ":", ";")):
                result.append(f"\\textbf{{{processed_name}}}")
            else:
                result.append(f"\\textbf{{{processed_name}.}}")

        # Handle either single entry or multiple entries
        if entry:
            result.append(self._process_text_with_tags(entry, context))
        elif entries:
            processed_entries = self.process_entries(entries, context)
            result.extend(processed_entries)

        return " ".join(result)

    def _process_cell(self, cell: dict[str, Any], context: RenderingContext) -> str:
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
            return processed_entry

        return roll_text

    def _process_statblock(
        self, statblock: dict[str, Any], context: RenderingContext
    ) -> str:
        """Process a statblock entry by resolving external content references.

        Args:
            statblock: Statblock dictionary with tag, name, source, and optional style
            context: Rendering context

        Returns:
            LaTeX string with resolved content rendered inline or as section
        """
        tag = statblock.get("tag", "")
        name = statblock.get("name", "")
        source = statblock.get("source", "")
        style = statblock.get("style", "")

        logger.debug(
            f"Processing statblock: tag={tag}, name={name}, source={source}, style={style}"
        )

        # Special handling for all statblocks with inset style
        if style == "inset" and context.omnidexer and tag:
            try:
                from studiorum.core.models.content import ContentType

                # Map tag to ContentType using existing mapping
                tag_to_content_type = {
                    "variantrule": ContentType.VARIANTRULE,
                    "action": ContentType.ACTION,
                    "condition": ContentType.CONDITION,
                    "sense": ContentType.SENSE,
                    "hazard": ContentType.HAZARD,
                    "status": ContentType.STATUS,
                    "item": ContentType.ITEM,
                    "creature": ContentType.CREATURE,
                    "reward": ContentType.REWARD,
                    "deity": ContentType.DEITY,
                    "charoption": ContentType.CHAROPTION,
                }

                content_type = tag_to_content_type.get(tag)
                if not content_type:
                    logger.debug(f"No ContentType mapping for statblock tag: {tag}")
                    # Fall through to generic resolution
                else:
                    resolved_content = context.omnidexer.find(
                        content_type, name, source
                    )

                    if resolved_content:
                        # Handle displayName override
                        display_name = statblock.get("displayName")
                        original_name = None
                        if display_name:
                            # Temporarily override the content's name for rendering
                            original_name = resolved_content.name
                            resolved_content.name = display_name

                        try:
                            # Use specialized renderer for creature/item, generic for others
                            if tag == "creature":
                                from .entry_renderers import CreatureEntryRenderer

                                creature_renderer = CreatureEntryRenderer()
                                result = creature_renderer.render(
                                    resolved_content, context
                                )
                            elif tag == "item":
                                from .entry_renderers import ItemEntryRenderer

                                item_renderer = ItemEntryRenderer()
                                result = item_renderer.render(resolved_content, context)
                            else:
                                # Generic rendering for other content types
                                if hasattr(resolved_content, "model_dump"):
                                    content_dict = resolved_content.model_dump()
                                elif hasattr(resolved_content, "__dict__"):
                                    content_dict = resolved_content.__dict__
                                else:
                                    content_dict = {
                                        "name": name,
                                        "entries": [str(resolved_content)],
                                    }

                                result = self._render_statblock_content(
                                    content_dict, name, context, style
                                )

                            # Restore original name if we overrode it
                            if display_name and original_name is not None:
                                resolved_content.name = original_name

                            return result
                        finally:
                            # Ensure name is restored even if rendering fails
                            if display_name and original_name is not None:
                                resolved_content.name = original_name

            except Exception as e:
                logger.warning(f"Error rendering {tag} statblock '{name}': {e}")

        # Try to resolve the external reference for other content types
        resolved_content = self._resolve_statblock_reference(tag, name, source, context)

        if resolved_content:
            # Render the resolved content with style information
            return self._render_statblock_content(
                resolved_content, name, context, style
            )
        # Fallback: render just the name as a header (current behavior)
        logger.warning(
            f"Could not resolve statblock reference: {tag} '{name}' from {source}"
        )
        section_cmd = self._get_section_command(self._depth, context)
        processed_name = self._process_text_with_tags(name, context)
        return f"\\{section_cmd}{{{processed_name}}}"

    def _resolve_statblock_reference(
        self, tag: str, name: str, source: str, context: RenderingContext
    ) -> dict[str, Any] | None:
        """Resolve a statblock reference to actual content.

        Args:
            tag: Content type tag (variantrule, action, condition, etc.)
            name: Content name
            source: Source abbreviation
            context: Rendering context

        Returns:
            Resolved content dictionary or None if not found
        """
        # Map statblock tags to ContentType enums
        tag_to_content_type = {
            "variantrule": "VARIANTRULE",  # Fixed to match develop ContentType
            "action": "ACTION",
            "condition": "CONDITION",
            "sense": "SENSE",
            "hazard": "HAZARD",
            "status": "STATUS",
            "item": "ITEM",
            "creature": "CREATURE",
        }

        content_type_name = tag_to_content_type.get(tag)
        if not content_type_name:
            logger.debug(f"Unsupported statblock tag type: {tag}")
            return None

        try:
            from studiorum.core.models.content import ContentType

            content_type = getattr(ContentType, content_type_name)
        except AttributeError:
            logger.debug(f"ContentType.{content_type_name} not found")
            return None

        # Try to find the content in the omnidexer
        if context.omnidexer:
            try:
                resolved_content = context.omnidexer.find(content_type, name, source)
                if resolved_content:
                    # Return the content as a dictionary for processing
                    if hasattr(resolved_content, "model_dump"):
                        content_dict = resolved_content.model_dump()
                        return dict(content_dict) if content_dict else None
                    if hasattr(resolved_content, "__dict__"):
                        content_dict = resolved_content.__dict__
                        return dict(content_dict) if content_dict else None
                    return {"name": name, "entries": [str(resolved_content)]}
            except Exception as e:
                logger.warning(
                    f"Error resolving statblock reference {tag} '{name}': {e}"
                )

        return None

    def _render_statblock_content(
        self,
        content: dict[str, Any],
        name: str,
        context: RenderingContext,
        style: str = "",
    ) -> str:
        """Render resolved statblock content with appropriate formatting based on style.

        Args:
            content: Resolved content dictionary
            name: Content name for header
            context: Rendering context
            style: Style hint - "inset" for inline rendering, empty for section header

        Returns:
            LaTeX string with appropriate formatting
        """
        entries = content.get("entries", [])

        if not entries:
            # No entries found
            if style == "inset":
                # For inset style, render just the processed name inline
                return self._process_text_with_tags(name, context)
            # For regular style, render name as section header
            section_cmd = self._get_section_command(self._depth, context)
            processed_name = self._process_text_with_tags(name, context)
            return f"\\{section_cmd}{{{processed_name}}}"

        # Process the entries
        processed_entries = self.process_entries(entries, context)
        content_text = "\n\n".join(processed_entries)

        if style == "inset":
            # For inset style, render content inline without section header
            # Use a simple paragraph with bold name if content exists
            processed_name = self._process_text_with_tags(name, context)
            if self.use_dnd_template:
                # Use DND inset styling
                return f"\\begin{{DndSidebar}}{{{processed_name}}}\\n{content_text}\\n\\end{{DndSidebar}}"
            # Use basic bold name + content
            return f"\\textbf{{{processed_name}}}\\n\\n{content_text}"
        # Regular style: add section header for the statblock
        section_cmd = self._get_section_command(self._depth, context)
        processed_name = self._process_text_with_tags(name, context)
        header = f"\\{section_cmd}{{{processed_name}}}"

        # Combine header with content
        return f"{header}\n\n{content_text}"

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics for this processor instance.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "entries_processed": self._entries_processed,
            "errors_encountered": self._errors_encountered,
            "current_depth": self._depth,
            "registry_statistics": dict(self._registry.entry_counts),
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
