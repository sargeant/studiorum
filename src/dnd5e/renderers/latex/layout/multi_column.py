"""Multi-column layout management for D&D content."""

from typing import Any

from ....core.models.content import ContentType
from ....core.registry import get_content_type_registry
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

        # Content type specific column preferences (Phase 3 migration)
        self.content_columns = self._build_column_preferences()

    def _build_column_preferences(self) -> dict[ContentType, int]:
        """Build content type to column count mapping using registry.

        Returns dynamic mapping based on available content types,
        following Phase 3 migration pattern.

        Returns:
            Dictionary mapping content types to preferred column counts
        """
        # Base column preferences
        column_map = {
            "spell": 2,
            "item": 2,
            "magicvariant": 2,
            "feat": 2,
            "action": 2,
            "condition": 2,
            "sense": 2,
            "hazard": 2,
            "status": 2,
            "background": 1,  # Backgrounds often need full width
            "class": 1,  # Class descriptions need space
            "subclass": 1,
            "race": 2,
            "subrace": 2,
            "creature": 1,  # Creature stat blocks are wide
            "adventure": 1,  # Adventures have complex layouts
            "book": 1,  # Books have complex layouts
            "deity": 2,
            "cult": 1,
            "boon": 2,
            "table": 1,  # Tables need full width
            "variantrule": 1,
            "reward": 2,
            "charoption": 1,
            "optionalfeature": 2,
            "disease": 2,
            "trap": 1,
            "vehicle": 1,
            "object": 2,
        }

        # Build preferences from registry
        registry = get_content_type_registry()
        preferences = {}

        for content_type_str, metadata in registry.get_all().items():
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                # Skip content types that don't exist as enum members (like fluff types)
                continue

            if content_type_str in column_map:
                preferences[content_type] = column_map[content_type_str]
            else:
                # Default to 2 columns for unknown content types
                preferences[content_type] = 2

        return preferences

    def get_supported_content_types(self) -> set[ContentType]:
        """Support all registered content types with different column strategies."""
        registry = get_content_type_registry()
        content_types = set()
        for content_type_str in registry.get_all():
            try:
                content_types.add(ContentType(content_type_str))
            except ValueError:
                # Skip content types that don't exist as enum members (like fluff types)
                continue
        return content_types

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
            column_count = getattr(context.hints, "column_count", self.default_columns)
            return (
                int(column_count) if column_count is not None else self.default_columns
            )

        # Use content type preferences
        return int(self.content_columns.get(context.content_type, self.default_columns))

    def _should_use_columns(self, context: LayoutContext) -> bool:
        """Determine if columns should be used for this content."""
        # Don't use columns for content that spans columns
        if context.hints and context.hints.span_columns:
            return False

        # Some content types work better in single column
        single_column_types = {"creature", "adventure"}

        return context.content_type.value not in single_column_types

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

        if content_type.value == "spell":
            hint.allow_float = True
            hint.avoid_column_break = True  # Keep spells together
        elif content_type.value == "creature":
            hint.span_columns = True  # Stat blocks need full width
            hint.allow_float = True
        elif content_type.value == "item":
            hint.allow_float = True
            hint.group_with_next = True  # Group similar items
        elif content_type.value == "background":
            hint.span_columns = True  # Backgrounds need detail space

        return hint
