"""Automatic table formatting and optimization for D&D content."""

from typing import Any, Optional

from ....core.models.content import ContentType
from .base import (
    ContentLayoutManager,
    EnvironmentWrapper,
    LayoutContext,
    LayoutHint,
    LayoutStrategy,
)


class TableFormatter(ContentLayoutManager):
    """Manages automatic table formatting and optimization."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the table formatter."""
        super().__init__(config)

        # Column type detection patterns
        self.numeric_patterns = [
            r"^\d+$",  # Pure numbers
            r"^\d+\.\d+$",  # Decimals
            r"^\d+d\d+$",  # Dice notation
            r"^\+\d+$",  # Modifiers
            r"^\d+\s*(gp|sp|cp|pp)$",  # Currency
            r"^\d+\s*ft\.?$",  # Distances
            r"^\d+\s*lbs?\.?$",  # Weight
        ]

        # Table width preferences by content type
        self.table_widths = {
            ContentType.SPELL: "\\textwidth",
            ContentType.ITEM: "\\textwidth",
            ContentType.CLASS: "\\textwidth",
            ContentType.RACE: "0.8\\textwidth",
            ContentType.CREATURE: "\\textwidth",
            ContentType.BACKGROUND: "0.9\\textwidth",
        }

        # Column specifications by content pattern
        self.content_column_specs = {
            "spell_list": "l X c",  # Name, Description, Level
            "item_list": "l X r",  # Name, Description, Cost
            "ability_list": "l X",  # Name, Description
            "class_features": "l X",  # Feature, Description
            "class_table": "c l X",  # Level, Feature, Description
            "equipment": "l l r r",  # Item, Type, Weight, Cost
        }

    def get_supported_content_types(self) -> set[ContentType]:
        """Support all content types that use tables."""
        return set(ContentType)

    def can_handle(self, context: LayoutContext) -> bool:
        """Handle table formatting when table content is detected."""
        return self._context_contains_tables(context)

    def get_priority(self) -> int:
        """Medium priority for table formatting."""
        return 50

    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply automatic table formatting to content."""
        if not content.strip():
            return content

        # Process different types of table content
        if self._is_dnd_table(content):
            return self._optimize_dnd_table(content, context)
        elif self._is_raw_table_data(content):
            return self._create_formatted_table(content, context)
        elif self._is_list_data(content):
            return self._convert_list_to_table(content, context)

        return content

    def _context_contains_tables(self, context: LayoutContext) -> bool:
        """Check if context indicates table content."""
        # Check hints
        if context.hints and context.hints.table_columns:
            return True

        # Content types that commonly use tables
        table_heavy_types = {
            ContentType.CLASS,
            ContentType.SPELL,
            ContentType.ITEM,
        }

        return context.content_type in table_heavy_types

    def _is_dnd_table(self, content: str) -> bool:
        """Check if content contains DndTable environments."""
        return "\\begin{DndTable}" in content

    def _is_raw_table_data(self, content: str) -> bool:
        """Check if content contains raw tabular data."""
        indicators = [
            "\\begin{tabular}",
            "\\begin{longtable}",
            "\\begin{array}",
            "&" in content and "\\\\" in content,  # LaTeX table syntax
        ]
        return any(
            indicator
            for indicator in indicators
            if isinstance(indicator, bool) or indicator in content
        )

    def _is_list_data(self, content: str) -> bool:
        """Check if content is structured list data that would benefit from tables."""
        lines = content.split("\n")

        # Look for consistent patterns that suggest tabular data
        structured_lines = [
            line for line in lines if ":" in line or "|" in line or "\t" in line
        ]

        return len(structured_lines) >= 3  # At least 3 rows suggest a table

    def _optimize_dnd_table(self, content: str, context: LayoutContext) -> str:
        """Optimize existing DndTable environments."""
        lines = content.split("\n")
        optimized_lines = []

        for line in lines:
            if line.strip().startswith("\\begin{DndTable}"):
                # Optimize table header and column specification
                optimized_line = self._optimize_table_header(line, context)
                optimized_lines.append(optimized_line)
            else:
                optimized_lines.append(line)

        return "\n".join(optimized_lines)

    def _optimize_table_header(self, header_line: str, context: LayoutContext) -> str:
        """Optimize DndTable header line with better specifications."""
        # Extract existing parameters
        import re

        # Parse existing header
        match = re.match(
            r"\\begin\{DndTable\}(?:\[([^\]]*)\])?\{([^}]*)\}", header_line
        )
        if not match:
            return header_line

        options = match.group(1) or ""
        column_spec = match.group(2) or ""

        # Optimize column specification
        optimized_spec = self._optimize_column_specification(column_spec, context)

        # Add responsive width if not specified
        if "width=" not in options and context.content_type in self.table_widths:
            width = self.table_widths[context.content_type]
            if options:
                options += f",width={width}"
            else:
                options = f"width={width}"

        # Reconstruct header
        if options:
            return f"\\begin{{DndTable}}[{options}]{{{optimized_spec}}}"
        else:
            return f"\\begin{{DndTable}}{{{optimized_spec}}}"

    def _optimize_column_specification(
        self, column_spec: str, context: LayoutContext
    ) -> str:
        """Optimize column specification based on content analysis."""
        if not column_spec:
            # Generate default based on content type
            return self._generate_default_column_spec(context)

        # Analyze and improve existing specification
        columns = column_spec.split()
        optimized_columns = []

        for i, col in enumerate(columns):
            if col == "l" and i == len(columns) - 1:
                # Last left column should probably expand
                optimized_columns.append("X")
            elif col == "c" and i > 0:
                # Center columns for numeric data
                optimized_columns.append("c")
            else:
                optimized_columns.append(col)

        return " ".join(optimized_columns)

    def _generate_default_column_spec(self, context: LayoutContext) -> str:
        """Generate default column specification for content type."""
        content_type = context.content_type

        # Use predefined specs
        if content_type == ContentType.SPELL:
            return "l X c"  # Name, Description, Level
        elif content_type == ContentType.ITEM:
            return "l X r"  # Name, Description, Cost/Rarity
        elif content_type == ContentType.CLASS:
            return "c l X"  # Level, Feature, Description
        elif content_type == ContentType.FEAT:
            return "l X"  # Name, Description
        else:
            return "l X"  # Generic: Name, Description

    def _create_formatted_table(self, content: str, context: LayoutContext) -> str:
        """Create a formatted DndTable from raw table data."""
        # Parse the raw table data
        table_data = self._parse_table_data(content)
        if not table_data:
            return content

        # Determine optimal formatting
        column_spec = self._analyze_table_structure(table_data, context)
        header = self._extract_table_header(table_data)

        # Build DndTable
        return self._build_dnd_table(table_data, column_spec, header, context)

    def _parse_table_data(self, content: str) -> list[list[str]] | None:
        """Parse raw table data into structured format."""
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) < 2:
            return None

        table_data = []

        for line in lines:
            # Handle different delimiters
            if "&" in line and "\\\\" in line:
                # LaTeX format
                row = [cell.strip() for cell in line.replace("\\\\", "").split("&")]
            elif "|" in line:
                # Pipe delimited
                row = [cell.strip() for cell in line.split("|")]
            elif "\t" in line:
                # Tab delimited
                row = [cell.strip() for cell in line.split("\t")]
            else:
                # Space delimited (less reliable)
                row = line.split()

            if row:
                table_data.append(row)

        return table_data if table_data else None

    def _analyze_table_structure(
        self, table_data: list[list[str]], context: LayoutContext
    ) -> str:
        """Analyze table structure to determine optimal column specification."""
        if not table_data:
            return "l X"

        num_columns = len(table_data[0])
        column_types = []

        for col_index in range(num_columns):
            column_values = [
                row[col_index] if col_index < len(row) else ""
                for row in table_data[1:]  # Skip header
            ]

            col_type = self._detect_column_type(column_values)
            column_types.append(col_type)

        return " ".join(column_types)

    def _detect_column_type(self, column_values: list[str]) -> str:
        """Detect the appropriate LaTeX column type for a column."""
        import re

        # Count numeric values
        numeric_count = 0
        for value in column_values:
            if any(
                re.match(pattern, value.strip()) for pattern in self.numeric_patterns
            ):
                numeric_count += 1

        numeric_ratio = numeric_count / len(column_values) if column_values else 0

        # Determine column type
        if numeric_ratio > 0.7:
            return "r"  # Right-aligned for numbers
        elif numeric_ratio > 0.3:
            return "c"  # Centered for mixed
        else:
            # Check if it's the last column (usually description)
            return "X"  # Expanding for text

    def _extract_table_header(self, table_data: list[list[str]]) -> str | None:
        """Extract table header from data."""
        if not table_data:
            return None

        # First row is usually the header
        return " & ".join(table_data[0])

    def _build_dnd_table(
        self,
        table_data: list[list[str]],
        column_spec: str,
        header: str | None,
        context: LayoutContext,
    ) -> str:
        """Build a formatted DndTable from structured data."""
        # Build table options
        options = []
        if header:
            options.append(f"header={header}")

        if context.content_type in self.table_widths:
            width = self.table_widths[context.content_type]
            options.append(f"width={width}")

        options_str = f"[{','.join(options)}]" if options else ""

        # Build table content
        table_lines = [f"\\begin{{DndTable}}{options_str}{{{column_spec}}}"]

        # Add header row if present
        if header:
            table_lines.append(f"\\textbf{{{header.replace(' & ', '} & \\textbf{')}}}")

        # Add data rows (skip first row if it was used as header)
        start_row = 1 if header else 0
        for row in table_data[start_row:]:
            table_lines.append(" & ".join(row) + " \\\\")

        table_lines.append("\\end{DndTable}")

        return "\n".join(table_lines)

    def _convert_list_to_table(self, content: str, context: LayoutContext) -> str:
        """Convert structured list content to table format."""
        lines = content.split("\n")
        structured_data = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse different list formats
            if ":" in line:
                parts = line.split(":", 1)
                structured_data.append([parts[0].strip(), parts[1].strip()])
            elif line.startswith("-") or line.startswith("*"):
                # Simple list items
                item = line[1:].strip()
                structured_data.append([item])

        if len(structured_data) < 2:
            return content

        # Convert to table
        return self._build_dnd_table(structured_data, "l X", None, context)

    def create_class_progression_table(self, progression_data: dict[str, Any]) -> str:
        """Create a formatted class progression table."""
        if not progression_data:
            return ""

        # Extract table structure
        columns = progression_data.get("columns", [])
        rows = progression_data.get("rows", [])

        if not columns or not rows:
            return ""

        # Build column specification
        column_spec = (
            "c " + "c " * (len(columns) - 2) + "X"
        )  # Level, features, expanding last

        # Build header
        header = " & ".join(columns)

        # Build table
        table_lines = [
            f"\\begin{{DndTable}}[header=Class Features,width=\\textwidth]{{{column_spec}}}",
            f"\\textbf{{{header.replace(' & ', '} & \\textbf{')}}}",
        ]

        for row in rows:
            table_lines.append(" & ".join(str(cell) for cell in row) + " \\\\")

        table_lines.append("\\end{DndTable}")

        return "\n".join(table_lines)

    def get_table_layout_hints(self, content_type: ContentType) -> LayoutHint:
        """Get layout hints optimized for table content."""
        hint = LayoutHint()

        # Table-specific preferences
        hint.allow_table_split = True
        hint.table_width = self.table_widths.get(content_type)

        # Generate appropriate column specification
        if content_type == ContentType.CLASS:
            hint.table_columns = "c l X"
        elif content_type == ContentType.SPELL:
            hint.table_columns = "l X c"
        elif content_type == ContentType.ITEM:
            hint.table_columns = "l X r"
        else:
            hint.table_columns = "l X"

        return hint
