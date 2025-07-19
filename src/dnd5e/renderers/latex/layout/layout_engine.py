"""Main layout engine that coordinates all layout managers."""

from typing import Any, Optional

from ....core.models.content import ContentType
from .base import LayoutContext, LayoutHint, LayoutManager, LayoutStrategy
from .float_manager import FloatManager
from .multi_column import MultiColumnManager
from .sidebar_manager import SidebarManager
from .table_formatter import TableFormatter
from .typography import TypographyManager


class LayoutEngine:
    """Coordinates multiple layout managers to create optimal document layouts."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the layout engine with managers."""
        self.config = config or {}

        # Initialize layout managers
        self.managers: list[LayoutManager] = [
            MultiColumnManager(self.config.get("multi_column", {})),
            FloatManager(self.config.get("float", {})),
            SidebarManager(self.config.get("sidebar", {})),
            TableFormatter(self.config.get("table", {})),
            TypographyManager(self.config.get("typography", {})),
        ]

        # Sort managers by priority (higher priority first)
        self.managers.sort(key=lambda m: m.get_priority(), reverse=True)

        # Layout strategy preferences
        self.strategy_preferences = {
            ContentType.ADVENTURE: LayoutStrategy.ADVENTURE,
            ContentType.CLASS: LayoutStrategy.SUPPLEMENT,
            ContentType.RACE: LayoutStrategy.SUPPLEMENT,
            ContentType.SPELL: LayoutStrategy.REFERENCE,
            ContentType.ITEM: LayoutStrategy.REFERENCE,
            ContentType.CREATURE: LayoutStrategy.REFERENCE,
            ContentType.BACKGROUND: LayoutStrategy.SUPPLEMENT,
            ContentType.FEAT: LayoutStrategy.REFERENCE,
        }

        # Global layout options
        self.default_column_count = self.config.get("default_columns", 2)
        self.enable_optimization = self.config.get("enable_optimization", True)

    def process_content(
        self,
        content: str,
        content_type: ContentType,
        hints: LayoutHint | None = None,
        strategy: LayoutStrategy | None = None,
    ) -> str:
        """Process content through the layout system."""
        if not content.strip():
            return content

        # Determine layout strategy
        if not strategy:
            strategy = self._determine_strategy(content_type, hints)

        # Create layout context
        context = self._create_context(content_type, strategy, hints)

        # Apply layout managers in priority order
        processed_content = content
        for manager in self.managers:
            if manager.can_handle(context):
                processed_content = manager.apply_layout(processed_content, context)
                # Update context after each manager
                context = self._update_context(context, manager, processed_content)

        return processed_content

    def process_content_blocks(
        self,
        content_blocks: list[tuple[str, ContentType]],
        document_strategy: LayoutStrategy | None = None,
    ) -> list[str]:
        """Process multiple content blocks with coordinated layout decisions."""
        if not content_blocks:
            return []

        # Analyze blocks for optimal layout
        block_contexts = self._analyze_content_blocks(content_blocks, document_strategy)

        # Process each block with context awareness
        processed_blocks = []
        for i, ((content, content_type), context) in enumerate(
            zip(content_blocks, block_contexts, strict=False)
        ):
            # Get hints from analysis
            hints = self._generate_block_hints(i, content_blocks, context)

            # Process the block
            processed_content = self.process_content(
                content, content_type, hints, context.strategy
            )
            processed_blocks.append(processed_content)

        # Apply global optimizations
        if self.enable_optimization:
            processed_blocks = self._optimize_block_sequence(processed_blocks)

        return processed_blocks

    def _determine_strategy(
        self, content_type: ContentType, hints: LayoutHint | None
    ) -> LayoutStrategy:
        """Determine the optimal layout strategy for content."""
        # Use explicit hint first
        if hints and hasattr(hints, "strategy"):
            return hints.strategy

        # Use content type preferences
        return self.strategy_preferences.get(content_type, LayoutStrategy.MULTI_COLUMN)

    def _create_context(
        self,
        content_type: ContentType,
        strategy: LayoutStrategy,
        hints: LayoutHint | None,
    ) -> LayoutContext:
        """Create layout context for processing."""
        return LayoutContext(
            strategy=strategy,
            content_type=content_type,
            column_count=self.default_column_count,
            hints=hints,
        )

    def _update_context(
        self,
        context: LayoutContext,
        manager: LayoutManager,
        processed_content: str,
    ) -> LayoutContext:
        """Update context after manager application."""
        # Update counters based on what was added
        if isinstance(manager, FloatManager):
            if self._content_has_floats(processed_content):
                context.float_count += 1

        elif isinstance(manager, SidebarManager):
            if self._content_has_sidebars(processed_content):
                context.sidebar_count += 1

        elif isinstance(manager, TableFormatter):
            if self._content_has_tables(processed_content):
                context.table_count += 1

        return context

    def _analyze_content_blocks(
        self,
        content_blocks: list[tuple[str, ContentType]],
        document_strategy: LayoutStrategy | None,
    ) -> list[LayoutContext]:
        """Analyze content blocks to create optimal layout contexts."""
        contexts = []

        for i, (content, content_type) in enumerate(content_blocks):
            # Determine strategy for this block
            if document_strategy:
                strategy = document_strategy
            else:
                strategy = self._determine_strategy(content_type, None)

            # Create context with position information
            context = LayoutContext(
                strategy=strategy,
                content_type=content_type,
                column_count=self.default_column_count,
                page_position=self._estimate_page_position(i, len(content_blocks)),
            )

            contexts.append(context)

        return contexts

    def _estimate_page_position(self, block_index: int, total_blocks: int) -> str:
        """Estimate where a block will appear on the page."""
        position_ratio = block_index / max(1, total_blocks - 1)

        if position_ratio < 0.3:
            return "top"
        elif position_ratio > 0.7:
            return "bottom"
        else:
            return "middle"

    def _generate_block_hints(
        self,
        block_index: int,
        content_blocks: list[tuple[str, ContentType]],
        context: LayoutContext,
    ) -> LayoutHint:
        """Generate layout hints based on block position and content."""
        content, content_type = content_blocks[block_index]
        hint = LayoutHint()

        # First block considerations
        if block_index == 0:
            hint.use_drop_cap = content_type == ContentType.ADVENTURE
            hint.space_before = None

        # Last block considerations
        if block_index == len(content_blocks) - 1:
            hint.space_after = "\\bigskip"

        # Adjacent block considerations
        if block_index > 0:
            prev_content_type = content_blocks[block_index - 1][1]
            if prev_content_type != content_type:
                hint.force_column_break = True

        # Content-specific hints
        if content_type == ContentType.CREATURE:
            hint.span_columns = True
            hint.float_position = None  # Use default float behavior

        elif content_type in {ContentType.SPELL, ContentType.FEAT}:
            hint.group_with_next = block_index < len(content_blocks) - 1

        return hint

    def _optimize_block_sequence(self, blocks: list[str]) -> list[str]:
        """Apply global optimizations to the sequence of blocks."""
        optimized = []

        for i, block in enumerate(blocks):
            # Add appropriate spacing between different types of content
            if i > 0 and self._blocks_need_separation(blocks[i - 1], block):
                optimized.append("\\medskip\n")

            optimized.append(block)

        return optimized

    def _blocks_need_separation(self, prev_block: str, current_block: str) -> bool:
        """Determine if blocks need additional separation."""
        # Check for different content types
        prev_has_table = self._content_has_tables(prev_block)
        current_has_table = self._content_has_tables(current_block)

        prev_has_float = self._content_has_floats(prev_block)
        current_has_float = self._content_has_floats(current_block)

        # Separate different content types
        if (prev_has_table and not current_has_table) or (
            not prev_has_table and current_has_table
        ):
            return True

        if (prev_has_float and not current_has_float) or (
            not prev_has_float and current_has_float
        ):
            return True

        return False

    def _content_has_floats(self, content: str) -> bool:
        """Check if content contains float environments."""
        float_indicators = [
            "\\begin{figure}",
            "\\begin{table}",
            "\\begin{DndMonster}",
            "float=",
            "float*=",
        ]
        return any(indicator in content for indicator in float_indicators)

    def _content_has_sidebars(self, content: str) -> bool:
        """Check if content contains sidebar environments."""
        sidebar_indicators = [
            "\\begin{DndSidebar}",
            "\\begin{DndComment}",
            "\\begin{DndReadAloud}",
        ]
        return any(indicator in content for indicator in sidebar_indicators)

    def _content_has_tables(self, content: str) -> bool:
        """Check if content contains table environments."""
        table_indicators = [
            "\\begin{DndTable}",
            "\\begin{tabular}",
            "\\begin{longtable}",
        ]
        return any(indicator in content for indicator in table_indicators)

    def get_manager_by_type(self, manager_type: type) -> LayoutManager | None:
        """Get a specific manager by type."""
        for manager in self.managers:
            if isinstance(manager, manager_type):
                return manager
        return None

    def set_global_strategy(self, strategy: LayoutStrategy) -> None:
        """Set global layout strategy for all content."""
        self.global_strategy = strategy

    def optimize_for_document_type(self, document_type: str) -> None:
        """Optimize layout engine for specific document types."""
        if document_type == "adventure":
            self.strategy_preferences.update(
                {
                    ContentType.ADVENTURE: LayoutStrategy.ADVENTURE,
                    ContentType.CREATURE: LayoutStrategy.ADVENTURE,
                    ContentType.SPELL: LayoutStrategy.ADVENTURE,
                }
            )
            self.default_column_count = 1

        elif document_type == "reference":
            for content_type in ContentType:
                self.strategy_preferences[content_type] = LayoutStrategy.REFERENCE
            self.default_column_count = 2

        elif document_type == "supplement":
            for content_type in ContentType:
                self.strategy_preferences[content_type] = LayoutStrategy.SUPPLEMENT
            self.default_column_count = 2

    def get_layout_statistics(self, processed_blocks: list[str]) -> dict[str, int]:
        """Get statistics about layout usage in processed content."""
        stats = {
            "total_blocks": len(processed_blocks),
            "blocks_with_floats": 0,
            "blocks_with_sidebars": 0,
            "blocks_with_tables": 0,
            "blocks_with_columns": 0,
        }

        for block in processed_blocks:
            if self._content_has_floats(block):
                stats["blocks_with_floats"] += 1
            if self._content_has_sidebars(block):
                stats["blocks_with_sidebars"] += 1
            if self._content_has_tables(block):
                stats["blocks_with_tables"] += 1
            if "multicols" in block:
                stats["blocks_with_columns"] += 1

        return stats
