"""Base classes and interfaces for the layout management system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

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


@dataclass
class LayoutHint:
    """Layout hints that content renderers can provide to guide layout decisions."""

    # Float preferences
    float_position: FloatPosition | None = None
    allow_float: bool = True
    span_columns: bool = False

    # Column preferences
    force_column_break: bool = False
    avoid_column_break: bool = False

    # Sidebar preferences
    sidebar_type: SidebarType | None = None
    sidebar_position: FloatPosition | None = None

    # Typography preferences
    use_drop_cap: bool = False
    emphasis_level: int = 0  # 0=normal, 1=emphasized, 2=strong

    # Table preferences
    table_width: str | None = None
    table_columns: str | None = None
    allow_table_split: bool = True

    # Spacing preferences
    space_before: str | None = None
    space_after: str | None = None

    # Content organization
    group_with_next: bool = False
    group_with_previous: bool = False


@dataclass
class LayoutContext:
    """Context information for layout decisions."""

    strategy: LayoutStrategy
    content_type: ContentType
    page_position: str | None = None  # top, middle, bottom
    column_count: int = 2
    column_position: int | None = None  # which column (0-based)
    available_space: float | None = None  # in points

    # Current document state
    float_count: int = 0
    sidebar_count: int = 0
    table_count: int = 0

    # Layout preferences
    hints: LayoutHint | None = None


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
