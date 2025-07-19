"""Multi-column layout management for D&D content."""

from typing import Any, Optional

from ....core.models.content import ContentType
from .base import (
    ContentLayoutManager,
    EnvironmentWrapper,
    LayoutContext,
    LayoutHint,
    LayoutStrategy,
)


class MultiColumnManager(ContentLayoutManager):
    """Manages multi-column layout for different content types."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the multi-column manager."""
        super().__init__(config)

        # Default configurations
        self.default_columns = self.config.get("default_columns", 2)
        self.column_sep = self.config.get("column_sep", "1cm")
        self.balance_columns = self.config.get("balance_columns", True)

        # Content type specific column preferences
        self.content_columns = {
            ContentType.SPELL: 2,
            ContentType.ITEM: 2,
            ContentType.FEAT: 2,
            ContentType.BACKGROUND: 1,  # Backgrounds often need full width
            ContentType.CLASS: 1,  # Class descriptions need space
            ContentType.RACE: 2,
            ContentType.CREATURE: 1,  # Creature stat blocks are wide
            ContentType.ADVENTURE: 1,  # Adventures have complex layouts
        }

    def get_supported_content_types(self) -> set[ContentType]:
        """Support all content types with different column strategies."""
        return set(ContentType)

    def can_handle(self, context: LayoutContext) -> bool:
        """Handle multi-column strategies."""
        return context.strategy in {
            LayoutStrategy.MULTI_COLUMN,
            LayoutStrategy.MAGAZINE,
            LayoutStrategy.REFERENCE,
            LayoutStrategy.SUPPLEMENT,
        }

    def get_priority(self) -> int:
        """High priority for column layout decisions."""
        return 80

    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply multi-column layout based on content type and context."""
        if not content.strip():
            return content

        # Determine optimal column count
        columns = self._determine_column_count(context)

        # Handle column breaks and spacing
        content = self._process_column_breaks(content, context)

        # Apply column layout if needed
        if columns > 1 and self._should_use_columns(context):
            content = self._apply_column_layout(content, columns, context)

        return content

    def _determine_column_count(self, context: LayoutContext) -> int:
        """Determine the optimal number of columns for the content."""
        # Check hints first
        if context.hints and hasattr(context.hints, "column_count"):
            return getattr(context.hints, "column_count", self.default_columns)

        # Use content type preferences
        return self.content_columns.get(context.content_type, self.default_columns)

    def _should_use_columns(self, context: LayoutContext) -> bool:
        """Determine if columns should be used for this content."""
        # Don't use columns for content that spans columns
        if context.hints and context.hints.span_columns:
            return False

        # Some content types work better in single column
        single_column_types = {
            ContentType.CREATURE,  # Stat blocks are wide
            ContentType.ADVENTURE,  # Complex adventure layouts
        }

        return context.content_type not in single_column_types

    def _process_column_breaks(self, content: str, context: LayoutContext) -> str:
        """Process and optimize column breaks in the content."""
        if not context.hints:
            return content

        # Add column break if requested
        if context.hints.force_column_break:
            content = EnvironmentWrapper.add_column_break() + content

        # Avoid column breaks by adding glue
        if context.hints.avoid_column_break:
            content = "\\nopagebreak\n" + content

        return content

    def _apply_column_layout(
        self, content: str, columns: int, context: LayoutContext
    ) -> str:
        """Apply the multi-column layout to content."""
        # Add column separation if configured
        column_sep = self.column_sep if self.column_sep else None

        # Apply multicols environment
        result = EnvironmentWrapper.wrap_multicols(
            content, columns=columns, column_sep=column_sep
        )

        # Add balancing command if enabled
        if self.balance_columns and columns > 1:
            result = "\\raggedcolumns\n" + result + "\n\\flushcolumns"

        return result

    def create_column_span_content(self, content: str) -> str:
        """Create content that spans all columns."""
        return f"\\end{{multicols}}\n{content}\n\\begin{{multicols}}{{{self.default_columns}}}"

    def add_intelligent_column_break(self, content: str, position: str = "auto") -> str:
        """Add intelligent column breaks based on content position."""
        if position == "before":
            return EnvironmentWrapper.add_column_break() + content
        elif position == "after":
            return content + EnvironmentWrapper.add_column_break()
        elif position == "auto":
            # Add break if content is long enough
            if len(content) > 500:  # Rough heuristic
                middle = len(content) // 2
                # Find a good break point (end of paragraph)
                break_point = content.find("\n\n", middle)
                if break_point != -1:
                    return (
                        content[:break_point]
                        + EnvironmentWrapper.add_column_break()
                        + content[break_point:]
                    )

        return content

    def optimize_column_balance(self, content: list[str]) -> list[str]:
        """Optimize the balance of content across columns."""
        if len(content) < 2:
            return content

        # Simple balancing algorithm
        total_length = sum(len(c) for c in content)
        target_length = total_length // len(content)

        balanced_content = []
        current_content = ""
        current_length = 0

        for item in content:
            if current_length + len(item) <= target_length * 1.2:  # 20% tolerance
                current_content += item + "\n\n"
                current_length += len(item)
            else:
                balanced_content.append(current_content.strip())
                current_content = item + "\n\n"
                current_length = len(item)

        if current_content.strip():
            balanced_content.append(current_content.strip())

        return balanced_content

    def get_column_layout_hints(self, content_type: ContentType) -> LayoutHint:
        """Get layout hints optimized for multi-column display."""
        hint = LayoutHint()

        if content_type == ContentType.SPELL:
            hint.allow_float = True
            hint.avoid_column_break = True  # Keep spells together
        elif content_type == ContentType.CREATURE:
            hint.span_columns = True  # Stat blocks need full width
            hint.allow_float = True
        elif content_type == ContentType.ITEM:
            hint.allow_float = True
            hint.group_with_next = True  # Group similar items
        elif content_type == ContentType.BACKGROUND:
            hint.span_columns = True  # Backgrounds need detail space

        return hint
