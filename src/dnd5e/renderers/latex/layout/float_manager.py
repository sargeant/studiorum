"""Float positioning and management for D&D content."""

from typing import Any

from ....core.models.content import ContentType
from .base import (
    ContentLayoutManager,
    FloatPosition,
    LayoutContext,
    LayoutHint,
)


class FloatManager(ContentLayoutManager):
    """Manages float positioning for figures, tables, and stat blocks."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the float manager."""
        super().__init__(config)

        # Float positioning preferences by content type
        self.content_float_preferences = {
            ContentType.CREATURE: FloatPosition.FULL_WIDTH_BOTTOM,
            ContentType.SPELL: FloatPosition.HERE,
            ContentType.ITEM: FloatPosition.HERE,
            ContentType.CLASS: FloatPosition.TOP,
            ContentType.RACE: FloatPosition.HERE,
            ContentType.BACKGROUND: FloatPosition.HERE,
            ContentType.FEAT: FloatPosition.HERE,
            ContentType.ADVENTURE: FloatPosition.HERE,
        }

        # Maximum floats per page
        self.max_floats_per_page = self.config.get("max_floats_per_page", 3)

        # Float size thresholds (in approximate lines)
        self.small_float_threshold = self.config.get("small_float_threshold", 10)
        self.large_float_threshold = self.config.get("large_float_threshold", 30)

    def get_supported_content_types(self) -> set[ContentType]:
        """Support all content types that can be floated."""
        return set(ContentType)

    def can_handle(self, context: LayoutContext) -> bool:
        """Handle float management for appropriate content."""
        return bool(
            context.hints
            and context.hints.allow_float
            and self._should_float_content(context)
        )

    def get_priority(self) -> int:
        """Medium-high priority for float decisions."""
        return 70

    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply float positioning to content."""
        if not content.strip() or not self._should_float_content(context):
            return content

        # Determine float position
        float_pos = self._determine_float_position(context)

        # Apply appropriate float environment
        return self._apply_float_environment(content, float_pos, context)

    def _should_float_content(self, context: LayoutContext) -> bool:
        """Determine if content should be floated."""
        if not context.hints or not context.hints.allow_float:
            return False

        # Don't float if we have too many floats already
        if context.float_count >= self.max_floats_per_page:
            return False

        # Some content types always float
        always_float_types = {ContentType.CREATURE}
        if context.content_type in always_float_types:
            return True

        # Float based on content size and position
        return self._analyze_float_benefit(context)

    def _analyze_float_benefit(self, context: LayoutContext) -> bool:
        """Analyze whether floating would benefit the layout."""
        # Float large content to avoid page breaks
        if (
            context.available_space
            and context.available_space < self.large_float_threshold
        ):
            return True

        # Float when specifically requested
        if context.hints and context.hints.float_position:
            return True

        return False

    def _determine_float_position(self, context: LayoutContext) -> FloatPosition:
        """Determine the optimal float position for content."""
        # Use explicit hint first
        if context.hints and context.hints.float_position:
            return context.hints.float_position

        # Use content type preferences
        default_pos = self.content_float_preferences.get(
            context.content_type, FloatPosition.HERE
        )

        # Adjust based on context
        return self._optimize_float_position(default_pos, context)

    def _optimize_float_position(
        self, position: FloatPosition, context: LayoutContext
    ) -> FloatPosition:
        """Optimize float position based on current layout context."""
        # If we're at the top of a page, prefer HERE or TOP
        if context.page_position == "top":
            if position == FloatPosition.BOTTOM:
                return FloatPosition.HERE

        # If we're at the bottom of a page, prefer BOTTOM or PAGE
        elif context.page_position == "bottom":
            if position == FloatPosition.TOP:
                return FloatPosition.BOTTOM

        # If there are many floats, prefer PAGE placement
        if context.float_count >= 2:
            if position in {FloatPosition.HERE, FloatPosition.TOP}:
                return FloatPosition.PAGE

        return position

    def _apply_float_environment(
        self, content: str, position: FloatPosition, context: LayoutContext
    ) -> str:
        """Apply the appropriate float environment to content."""
        content_type = context.content_type

        # Special handling for creature stat blocks (already use DndMonster)
        if content_type == ContentType.CREATURE:
            return self._apply_creature_float(content, position)

        # Table content
        elif self._is_table_content(content):
            return self._apply_table_float(content, position)

        # Figure content (images, diagrams)
        elif self._is_figure_content(content):
            return self._apply_figure_float(content, position)

        # General content float
        else:
            return self._apply_general_float(content, position)

    def _apply_creature_float(self, content: str, position: FloatPosition) -> str:
        """Apply float to creature stat blocks (DndMonster environment)."""
        # DndMonster already handles floating, just ensure correct position
        if position == FloatPosition.FULL_WIDTH_BOTTOM:
            # This is already the default for DndMonster
            return content
        elif position == FloatPosition.HERE:
            # Modify to use inline positioning
            return content.replace(
                "float*=b,width=\\textwidth + 8pt", "width=\\textwidth + 8pt"
            )
        else:
            # Use standard float positions
            pos_str = position.value
            return content.replace("float*=b", f"float={pos_str}")

    def _apply_table_float(self, content: str, position: FloatPosition) -> str:
        """Apply float to table content."""
        # Wrap in table environment if not already wrapped
        if not content.strip().startswith("\\begin{table}"):
            pos_str = position.value
            if position == FloatPosition.FULL_WIDTH_BOTTOM:
                pos_str = "b"

            return f"\\begin{{table}}[{pos_str}]\n{content}\n\\end{{table}}"

        return content

    def _apply_figure_float(self, content: str, position: FloatPosition) -> str:
        """Apply float to figure content."""
        if not content.strip().startswith("\\begin{figure}"):
            pos_str = position.value
            if position == FloatPosition.FULL_WIDTH_BOTTOM:
                # Use figure* for full-width
                return f"\\begin{{figure*}}[b]\n{content}\n\\end{{figure*}}"
            else:
                return f"\\begin{{figure}}[{pos_str}]\n{content}\n\\end{{figure}}"

        return content

    def _apply_general_float(self, content: str, position: FloatPosition) -> str:
        """Apply float to general content using LaTeX's float package."""
        pos_str = position.value

        # Use a generic float environment
        return f"\\begin{{float}}[{pos_str}]\n{content}\n\\end{{float}}"

    def _is_table_content(self, content: str) -> bool:
        """Check if content contains table elements."""
        table_indicators = [
            "\\begin{DndTable}",
            "\\begin{tabular}",
            "\\begin{longtable}",
            "\\begin{array}",
        ]
        return any(indicator in content for indicator in table_indicators)

    def _is_figure_content(self, content: str) -> bool:
        """Check if content contains figure elements."""
        figure_indicators = [
            "\\includegraphics",
            "\\begin{tikzpicture}",
            "\\begin{pgfpicture}",
        ]
        return any(indicator in content for indicator in figure_indicators)

    def create_float_barrier(self) -> str:
        """Create a float barrier to force float placement."""
        return "\\FloatBarrier\n"

    def optimize_float_placement(self, content_blocks: list[str]) -> list[str]:
        """Optimize float placement across multiple content blocks."""
        optimized = []
        float_count = 0

        for i, block in enumerate(content_blocks):
            # Check if this block contains floats
            if self._contains_float(block):
                float_count += 1

                # Add float barrier if too many floats
                if float_count > self.max_floats_per_page:
                    optimized.append(self.create_float_barrier())
                    float_count = 1

                optimized.append(block)
            else:
                optimized.append(block)

                # Reset float count after non-float content
                if len(block.strip()) > 100:  # Substantial content
                    float_count = max(0, float_count - 1)

        return optimized

    def _contains_float(self, content: str) -> bool:
        """Check if content contains float environments."""
        float_indicators = [
            "\\begin{figure}",
            "\\begin{table}",
            "\\begin{DndMonster}",
            "float=",
            "float*=",
        ]
        return any(indicator in content for indicator in float_indicators)

    def get_float_layout_hints(self, content_type: ContentType) -> LayoutHint:
        """Get layout hints optimized for float management."""
        hint = LayoutHint()
        hint.allow_float = True
        hint.float_position = self.content_float_preferences.get(content_type)

        # Special preferences by content type
        if content_type == ContentType.CREATURE:
            hint.span_columns = True
            hint.avoid_column_break = True
        elif content_type in {ContentType.SPELL, ContentType.FEAT}:
            hint.group_with_next = True

        return hint
