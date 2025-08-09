"""Base classes and interfaces for the layout management system."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ....core.base_context import DocumentContext
from ....core.models.content import ContentType


class LayoutStrategy(Enum):
    """Layout strategies for different document types and content."""

    SINGLE_COLUMN = "single_column"
    MULTI_COLUMN = "multi_column"
    MAGAZINE = "magazine"
    REFERENCE = "reference"
    ADVENTURE = "adventure"
    SUPPLEMENT = "supplement"


class FloatPosition(Enum):
    """Float positioning preferences."""

    HERE = "!h"
    TOP = "!t"
    BOTTOM = "!b"
    PAGE = "!p"
    FORCE_HERE = "H"
    FULL_WIDTH_BOTTOM = "float*=b"


class SidebarType(Enum):
    """Types of sidebar environments."""

    SIDEBAR = "DndSidebar"
    COMMENT = "DndComment"
    READ_ALOUD = "DndReadAloud"
    AREA = "DndArea"
    SUB_AREA = "DndSubArea"


class LayoutHint(BaseModel):
    """Layout hints that content renderers can provide to guide layout decisions."""

    # Float preferences
    float_position: FloatPosition | None = Field(
        None, description="Preferred float position"
    )
    allow_float: bool = Field(True, description="Whether content can be floated")
    span_columns: bool = Field(
        False, description="Whether content should span multiple columns"
    )

    # Column preferences
    force_column_break: bool = Field(
        False, description="Force a column break before this content"
    )
    avoid_column_break: bool = Field(
        False, description="Avoid column breaks within this content"
    )
    column_count: int | None = Field(
        None, ge=1, le=4, description="Override for number of columns to use"
    )

    # Sidebar preferences
    sidebar_type: SidebarType | None = Field(
        None, description="Type of sidebar if applicable"
    )
    sidebar_position: FloatPosition | None = Field(
        None, description="Sidebar positioning preference"
    )

    # Typography preferences
    use_drop_cap: bool = Field(False, description="Use drop cap for first letter")
    emphasis_level: int = Field(
        0, ge=0, le=2, description="Emphasis level (0=normal, 1=emphasized, 2=strong)"
    )

    # Table preferences
    table_width: str | None = Field(
        None, description="Preferred table width specification"
    )
    table_columns: str | None = Field(None, description="Table column specification")
    allow_table_split: bool = Field(
        True, description="Allow table to split across pages"
    )

    # Spacing preferences
    space_before: str | None = Field(None, description="Space to add before content")
    space_after: str | None = Field(None, description="Space to add after content")

    # Content organization
    group_with_next: bool = Field(
        False, description="Group this content with the next item"
    )
    group_with_previous: bool = Field(
        False, description="Group this content with the previous item"
    )

    @field_validator("table_width", "table_columns", "space_before", "space_after")
    @classmethod
    def validate_latex_lengths(cls, v: str | None) -> str | None:
        """Validate LaTeX length specifications."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class LayoutContext(DocumentContext):
    """Context information for layout decisions with validation.

    Inherits from DocumentContext to provide standardized document state management
    while adding layout-specific configuration and validation.
    """

    # Layout-specific configuration
    strategy: LayoutStrategy = Field(description="Layout strategy to use")
    page_position: str | None = Field(
        None, description="Position on page (top, middle, bottom)"
    )
    column_count: int = Field(2, ge=1, le=4, description="Number of columns in layout")
    column_position: int | None = Field(
        None, ge=0, description="Current column position (0-based)"
    )
    available_space: float | None = Field(
        None, ge=0, description="Available space in points"
    )

    # Layout preferences
    hints: LayoutHint | None = Field(None, description="Layout hints for this content")

    def __init__(self, **data: Any) -> None:
        # Map content_type to document_type for backward compatibility
        if "content_type" in data and "document_type" not in data:
            content_type = data.pop("content_type")
            if hasattr(content_type, "value"):
                data["document_type"] = content_type.value
            else:
                data["document_type"] = str(content_type)
        super().__init__(**data)

    @property
    def content_type(self) -> ContentType:
        """Get content type from document type for backward compatibility."""
        try:
            return ContentType(self.document_type)
        except ValueError:
            # Fallback to a default if document_type doesn't map to ContentType
            return ContentType("supplement")  # Use supplement as a reasonable default

    @field_validator("page_position")
    @classmethod
    def validate_page_position(cls, v: str | None) -> str | None:
        """Validate page position values."""
        if v is None:
            return v
        valid_positions = {"top", "middle", "bottom"}
        cleaned = v.strip().lower()
        if cleaned and cleaned not in valid_positions:
            raise ValueError(
                f"Page position must be one of {valid_positions}, got '{cleaned}'"
            )
        return cleaned if cleaned else None

    @field_validator("column_position")
    @classmethod
    def validate_column_position(cls, v: int | None, info: Any) -> int | None:
        """Validate column position is within column count."""
        if v is None:
            return v
        if "column_count" in info.data and v >= info.data["column_count"]:
            raise ValueError("Column position must be less than column count")
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class LayoutManager(ABC):
    """Base class for all layout managers."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the layout manager with optional configuration."""
        self.config = config or {}

    @abstractmethod
    def can_handle(self, context: LayoutContext) -> bool:
        """Check if this manager can handle the given layout context."""
        pass

    @abstractmethod
    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply layout transformations to the content."""
        pass

    def get_priority(self) -> int:
        """Get the priority of this layout manager (higher = more important)."""
        return 0


class ContentLayoutManager(LayoutManager):
    """Base class for content-specific layout managers."""

    @abstractmethod
    def get_supported_content_types(self) -> set[ContentType]:
        """Get the content types this manager supports."""
        pass

    def can_handle(self, context: LayoutContext) -> bool:
        """Check if this manager supports the content type."""
        return context.content_type in self.get_supported_content_types()


class EnvironmentWrapper:
    """Helper class for wrapping content in LaTeX environments."""

    @staticmethod
    def wrap_environment(
        content: str,
        environment: str,
        options: str | None = None,
        title: str | None = None,
    ) -> str:
        """Wrap content in a LaTeX environment with optional parameters."""
        if options and title:
            begin = f"\\begin{{{environment}}}[{options}]{{{title}}}"
        elif options:
            begin = f"\\begin{{{environment}}}[{options}]"
        elif title:
            begin = f"\\begin{{{environment}}}{{{title}}}"
        else:
            begin = f"\\begin{{{environment}}}"

        end = f"\\end{{{environment}}}"

        return f"{begin}\n{content}\n{end}"

    @staticmethod
    def wrap_multicols(
        content: str, columns: int = 2, column_sep: str | None = None
    ) -> str:
        """Wrap content in multicols environment."""
        if column_sep:
            begin = f"\\begin{{multicols}}{{{columns}}}[\\setlength{{\\columnsep}}{{{column_sep}}}]"
        else:
            begin = f"\\begin{{multicols}}{{{columns}}}"

        return f"{begin}\n{content}\n\\end{{multicols}}"

    @staticmethod
    def add_column_break() -> str:
        """Add a column break."""
        return "\\columnbreak\n"

    @staticmethod
    def add_page_break() -> str:
        """Add a page break."""
        return "\\newpage\n"

    @staticmethod
    def add_vertical_space(space: str) -> str:
        """Add vertical space."""
        return f"\\vspace{{{space}}}\n"
