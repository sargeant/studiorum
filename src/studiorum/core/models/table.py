"""Table content model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


@content_type(
    enum_value="table",
    file_patterns=["table", "tables"],
    loader_type="json",
    statblock_tags=["table"],
)
class Table(BaseContent):
    """Table model for structured tabular data.

    Tables represent game data organized in rows and columns,
    such as random tables, treasure tables, or reference tables.
    """

    # Required fields
    col_labels: list[str] = Field(
        ..., description="Column header labels", alias="colLabels"
    )
    rows: list[list[str | Entry]] = Field(..., description="Table row data")

    # Optional fields
    col_styles: list[str] | None = Field(
        None, description="CSS styles for columns", alias="colStyles"
    )
    caption: str | None = Field(None, description="Table caption")
    rollable_col_labels: list[str] | None = Field(
        None,
        description="Labels for rollable columns",
        alias="rollableColLabels",
    )
    intro: list[Entry] | None = Field(
        None, description="Introduction text before the table"
    )
    outro: list[Entry] | None = Field(
        None, description="Conclusion text after the table"
    )
    table_include: dict[str, Any] | None = Field(
        None,
        description="Reference to include another table",
        alias="tableInclude",
    )
    is_named_creature: bool | None = Field(
        None,
        description="Whether this table contains named creatures",
        alias="isNamedCreature",
    )
    is_striped: bool | None = Field(
        None, description="Whether to use striped row styling", alias="isStriped"
    )
    sort_by: str | None = Field(None, description="Column to sort by", alias="sortBy")
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this table",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this table",
        alias="otherSources",
    )

    @field_validator("col_labels", mode="before")
    @classmethod
    def validate_col_labels(cls, v: Any) -> list[str]:
        """Validate column labels are not empty."""
        if not v or not isinstance(v, list):
            raise ValueError("Table must have column labels")
        if not all(isinstance(label, str) and label.strip() for label in v):
            raise ValueError("All column labels must be non-empty strings")
        return list(v)

    @field_validator("rows", mode="before")
    @classmethod
    def validate_rows(cls, v: Any) -> list[list[str | Entry]]:
        """Validate table rows structure."""
        if not v or not isinstance(v, list):
            raise ValueError("Table must have rows")
        if not all(isinstance(row, list) for row in v):
            raise ValueError("All table rows must be lists")
        return list(v)

    @field_validator("col_styles", mode="before")
    @classmethod
    def validate_col_styles(cls, v: Any) -> list[str] | None:
        """Validate column styles if provided."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Table name cannot be empty")
        return str(v).strip()

    def get_column_count(self) -> int:
        """Get the number of columns in the table."""
        return len(self.col_labels)

    def get_row_count(self) -> int:
        """Get the number of rows in the table."""
        return len(self.rows)

    def has_column_styles(self) -> bool:
        """Check if this table has column styles defined."""
        return bool(self.col_styles)

    def has_caption(self) -> bool:
        """Check if this table has a caption."""
        return bool(self.caption)

    def is_rollable(self) -> bool:
        """Check if this table has rollable columns."""
        return bool(self.rollable_col_labels)

    def has_introduction(self) -> bool:
        """Check if this table has introduction text."""
        return bool(self.intro)

    def has_conclusion(self) -> bool:
        """Check if this table has conclusion text."""
        return bool(self.outro)

    def includes_other_table(self) -> bool:
        """Check if this table includes another table."""
        return bool(self.table_include)

    def get_rollable_column_indices(self) -> list[int]:
        """Get the indices of rollable columns."""
        if not self.rollable_col_labels:
            return []

        indices = []
        for rollable_label in self.rollable_col_labels:
            try:
                index = self.col_labels.index(rollable_label)
                indices.append(index)
            except ValueError:
                # Rollable label not found in col_labels
                continue
        return indices

    def get_column_index(self, column_name: str) -> int | None:
        """Get the index of a column by name."""
        try:
            return self.col_labels.index(column_name)
        except ValueError:
            return None

    def get_row_data(self, row_index: int) -> list[str | Entry] | None:
        """Get data for a specific row by index."""
        if 0 <= row_index < len(self.rows):
            return self.rows[row_index]
        return None

    def get_column_data(self, column_index: int) -> list[str | Entry]:
        """Get all data for a specific column by index."""
        if column_index < 0 or column_index >= self.get_column_count():
            return []

        column_data = []
        for row in self.rows:
            if column_index < len(row):
                column_data.append(row[column_index])
            else:
                column_data.append("")  # Empty cell
        return column_data

    def get_cell_data(self, row_index: int, column_index: int) -> str | Entry | None:
        """Get data for a specific cell."""
        row_data = self.get_row_data(row_index)
        if row_data and column_index < len(row_data):
            return row_data[column_index]
        return None

    def is_rectangular(self) -> bool:
        """Check if all rows have the same number of columns."""
        if not self.rows:
            return True

        expected_columns = len(self.rows[0])
        return all(len(row) == expected_columns for row in self.rows)

    def validate_structure(self) -> bool:
        """Validate that the table structure is consistent."""
        if not self.col_labels or not self.rows:
            return False

        # Check if column styles match column count
        if self.col_styles and len(self.col_styles) != len(self.col_labels):
            return False

        # Check if rollable columns exist in col_labels
        if self.rollable_col_labels:
            for rollable_col in self.rollable_col_labels:
                if rollable_col not in self.col_labels:
                    return False

        return True

    def get_table_summary(self) -> str:
        """Get a summary description of this table."""
        parts = [f"{self.get_row_count()} rows"]
        parts.append(f"{self.get_column_count()} columns")

        if self.is_rollable():
            rollable_count = len(self.rollable_col_labels or [])
            parts.append(f"{rollable_count} rollable columns")

        if self.has_caption():
            parts.append("with caption")

        if self.has_introduction():
            parts.append("with introduction")

        if self.has_conclusion():
            parts.append("with conclusion")

        return ", ".join(parts)

    def get_referenced_table(self) -> str | None:
        """Get the name of the table this table includes, if any."""
        if not self.table_include:
            return None
        return self.table_include.get("name")


@content_type(
    enum_value="tableGroup",
    file_patterns=["tableGroup", "tablegroups", "tables"],
    loader_type="json",
    statblock_tags=["tableGroup"],
)
class TableGroup(BaseContent):
    """A collection of related tables grouped together.

    Used to organize multiple tables that work together or
    represent variations on a theme.
    """

    tables: list[dict[str, Any]] = Field(
        default_factory=list, description="List of tables in this group"
    )

    def get_display_name(self) -> str:
        """Get display name for the table group."""
        return self.name

    def get_table_count(self) -> int:
        """Get number of tables in this group."""
        return len(self.tables)

    def get_table_names(self) -> list[str]:
        """Get names of all tables in this group."""
        names = []
        for table_data in self.tables:
            if isinstance(table_data, dict) and "name" in table_data:
                names.append(table_data["name"])
        return names

    def has_tables(self) -> bool:
        """Check if this group contains any tables."""
        return len(self.tables) > 0
