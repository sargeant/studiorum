"""Tables and table groups: 5etools' ``tables.json`` and the tables it generates."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from .content import BaseContent
from .entry_types import Entry

# A row is a list of cells, or a {"type": "row", "row": [...]} object
type Row = list[str | int | float | Entry] | dict[str, Any]


class Table(BaseContent):
    """Table model for structured tabular data.

    Tables represent game data organized in rows and columns,
    such as random tables, treasure tables, or reference tables.
    """

    # Required fields
    col_labels: list[str] | None = Field(
        None, description="Column header labels", alias="colLabels"
    )
    rows: list[Row] = Field(..., description="Table row data")

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
    # Props of a 5etools table entry, which the generated tables keep
    col_label_rows: list[list[str | Entry]] | None = Field(
        None, description="Several rows of column headers", alias="colLabelRows"
    )
    footnotes: list[Entry] | None = Field(None, description="Table footnotes")
    is_name_generator: bool | None = Field(
        None, description="Whether the table rolls a name", alias="isNameGenerator"
    )
    chapter: dict[str, Any] | None = Field(
        None, description="The chapter 5etools generated the table from"
    )
    parent_entity: dict[str, Any] | None = Field(
        None, description="The entity 5etools found the table in", alias="parentEntity"
    )

    @field_validator("col_labels", mode="before")
    @classmethod
    def validate_col_labels(cls, v: Any) -> list[str]:
        """Column labels are strings; the first may be empty, over a row label."""
        if not v or not isinstance(v, list):
            raise ValueError("Table must have column labels")
        if not all(isinstance(label, str) for label in v):
            raise ValueError("All column labels must be strings")
        return list(v)

    @field_validator("rows", mode="before")
    @classmethod
    def validate_rows(cls, v: Any) -> list[Row]:
        """Rows are lists of cells or 5etools row objects."""
        if not v or not isinstance(v, list):
            raise ValueError("Table must have rows")
        if not all(isinstance(row, list | dict) for row in v):
            raise ValueError("All table rows must be lists or row objects")
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


class TableGroup(BaseContent):
    """A collection of related tables grouped together.

    Used to organize multiple tables that work together or
    represent variations on a theme.
    """

    tables: list[dict[str, Any]] = Field(
        default_factory=list, description="List of tables in this group"
    )
