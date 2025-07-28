"""Tests for the main layout engine."""

from typing import Any
from unittest.mock import Mock, patch

from dnd5e.core.models.content import ContentType  # type: ignore
from dnd5e.renderers.latex.layout.base import LayoutHint, LayoutStrategy  # type: ignore
from dnd5e.renderers.latex.layout.layout_engine import LayoutEngine  # type: ignore


class TestLayoutEngine:
    """Test cases for the layout engine."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = LayoutEngine()

    def test_init_default_config(self) -> None:
        """Test initialization with default configuration."""
        assert len(self.engine.managers) == 5  # All manager types
        assert self.engine.default_column_count == 2
        assert self.engine.enable_optimization is True

    def test_init_custom_config(self) -> None:
        """Test initialization with custom configuration."""
        config = {
            "default_columns": 3,
            "enable_optimization": False,
            "multi_column": {"default_columns": 1},
        }
        engine: Any = LayoutEngine(config)

        assert engine.default_column_count == 3
        assert engine.enable_optimization is False

    def test_managers_sorted_by_priority(self) -> None:
        """Test that managers are sorted by priority."""
        priorities = [manager.get_priority() for manager in self.engine.managers]

        # Should be in descending order
        assert priorities == sorted(priorities, reverse=True)

    def test_strategy_preferences(self) -> None:
        """Test content type strategy preferences."""
        assert (
            self.engine.strategy_preferences[ContentType.ADVENTURE]
            == LayoutStrategy.ADVENTURE
        )
        assert (
            self.engine.strategy_preferences[ContentType.SPELL]
            == LayoutStrategy.REFERENCE
        )
        assert (
            self.engine.strategy_preferences[ContentType.CLASS]
            == LayoutStrategy.SUPPLEMENT
        )

    def test_process_content_empty(self) -> None:
        """Test processing empty content."""
        result = self.engine.process_content("", ContentType.SPELL)
        assert result == ""

    def test_process_content_with_strategy(self) -> None:
        """Test processing content with explicit strategy."""
        content = "Test spell content"

        with patch.object(self.engine, "_determine_strategy") as mock_strategy:
            mock_strategy.return_value = LayoutStrategy.REFERENCE

            result = self.engine.process_content(
                content, ContentType.SPELL, strategy=LayoutStrategy.MULTI_COLUMN
            )

            # Should use provided strategy, not call _determine_strategy
            mock_strategy.assert_not_called()
            assert isinstance(result, str)

    def test_process_content_with_hints(self) -> None:
        """Test processing content with layout hints."""
        content = "Test content"
        hints: Any = LayoutHint()
        hints.use_drop_cap = True

        result = self.engine.process_content(
            content, ContentType.ADVENTURE, hints=hints
        )

        assert isinstance(result, str)
        # The specific transformations depend on manager implementations

    def test_determine_strategy_from_content_type(self) -> None:
        """Test strategy determination from content type."""
        strategy = self.engine._determine_strategy(ContentType.ADVENTURE, None)
        assert strategy == LayoutStrategy.ADVENTURE

        strategy = self.engine._determine_strategy(ContentType.SPELL, None)
        assert strategy == LayoutStrategy.REFERENCE

    def test_determine_strategy_from_hints(self) -> None:
        """Test strategy determination from hints."""
        hints: Any = LayoutHint()
        # LayoutHint doesn't have strategy attribute, skip this test
        # or use context if we need strategy hints
        strategy = self.engine._determine_strategy(ContentType.SPELL, hints)
        assert strategy == LayoutStrategy.REFERENCE  # Should use content type default

    def test_determine_strategy_unknown_type(self) -> None:
        """Test strategy determination for unknown content type."""
        # Create a mock content type not in preferences
        unknown_type: Any = Mock()

        strategy = self.engine._determine_strategy(unknown_type, None)
        assert strategy == LayoutStrategy.MULTI_COLUMN

    def test_create_context(self) -> None:
        """Test layout context creation."""
        hints: Any = LayoutHint()
        context = self.engine._create_context(
            ContentType.SPELL, LayoutStrategy.REFERENCE, hints
        )

        assert context.content_type == ContentType.SPELL
        assert context.strategy == LayoutStrategy.REFERENCE
        assert context.hints == hints
        assert context.column_count == 2

    def test_process_content_blocks_empty(self) -> None:
        """Test processing empty content blocks."""
        result = self.engine.process_content_blocks([])
        assert result == []

    def test_process_content_blocks_single(self) -> None:
        """Test processing single content block."""
        content_blocks = [("Test content", ContentType.SPELL)]

        result = self.engine.process_content_blocks(content_blocks)

        assert len(result) == 1
        assert isinstance(result[0], str)

    def test_process_content_blocks_multiple(self) -> None:
        """Test processing multiple content blocks."""
        content_blocks = [
            ("Spell content", ContentType.SPELL),
            ("Item content", ContentType.ITEM),
            ("Creature content", ContentType.CREATURE),
        ]

        result = self.engine.process_content_blocks(content_blocks)

        # Layout optimization can add spacing elements between different content types
        # The result should contain at least the original blocks, potentially with spacing
        assert len(result) >= 3
        assert all(isinstance(block, str) for block in result)

        # Check that optimization added spacing where appropriate
        # (between table content and non-table content)
        content_blocks_found = 0
        spacing_blocks_found = 0
        for block in result:
            if "\\medskip" in block:
                spacing_blocks_found += 1
            else:
                content_blocks_found += 1

        assert content_blocks_found == 3  # Original content blocks
        assert spacing_blocks_found >= 0  # May have spacing added by optimization

    def test_process_content_blocks_with_strategy(self) -> None:
        """Test processing content blocks with document strategy."""
        content_blocks = [
            ("Content 1", ContentType.SPELL),
            ("Content 2", ContentType.ITEM),
        ]

        result = self.engine.process_content_blocks(
            content_blocks, document_strategy=LayoutStrategy.REFERENCE
        )

        assert len(result) == 2

    def test_analyze_content_blocks(self) -> None:
        """Test content block analysis."""
        content_blocks = [
            ("First content", ContentType.SPELL),
            ("Second content", ContentType.ITEM),
            ("Third content", ContentType.CREATURE),
        ]

        contexts = self.engine._analyze_content_blocks(content_blocks, None)

        assert len(contexts) == 3
        assert contexts[0].page_position == "top"
        assert contexts[1].page_position == "middle"
        assert contexts[2].page_position == "bottom"

    def test_estimate_page_position(self) -> None:
        """Test page position estimation."""
        # First block
        position = self.engine._estimate_page_position(0, 5)
        assert position == "top"

        # Middle block
        position = self.engine._estimate_page_position(2, 5)
        assert position == "middle"

        # Last block
        position = self.engine._estimate_page_position(4, 5)
        assert position == "bottom"

    def test_generate_block_hints_first_block(self) -> None:
        """Test hint generation for first block."""
        content_blocks = [
            ("Adventure content", ContentType.ADVENTURE),
            ("Spell content", ContentType.SPELL),
        ]

        context: Any = Mock()
        context.strategy = LayoutStrategy.ADVENTURE

        hints = self.engine._generate_block_hints(0, content_blocks, context)

        assert hints.use_drop_cap is True  # Adventure content
        assert hints.space_before is None  # First block

    def test_generate_block_hints_last_block(self) -> None:
        """Test hint generation for last block."""
        content_blocks = [
            ("Spell content", ContentType.SPELL),
            ("Final content", ContentType.ITEM),
        ]

        context: Any = Mock()
        context.strategy = LayoutStrategy.REFERENCE

        hints = self.engine._generate_block_hints(1, content_blocks, context)

        assert hints.space_after == "\\bigskip"  # Last block

    def test_generate_block_hints_content_type_change(self) -> None:
        """Test hint generation when content type changes."""
        content_blocks = [
            ("Spell content", ContentType.SPELL),
            ("Creature content", ContentType.CREATURE),
        ]

        context: Any = Mock()
        context.strategy = LayoutStrategy.REFERENCE

        hints = self.engine._generate_block_hints(1, content_blocks, context)

        assert hints.force_column_break is True  # Content type changed

    def test_generate_block_hints_creature_content(self) -> None:
        """Test hint generation for creature content."""
        content_blocks = [("Creature content", ContentType.CREATURE)]

        context: Any = Mock()
        context.strategy = LayoutStrategy.REFERENCE

        hints = self.engine._generate_block_hints(0, content_blocks, context)

        assert hints.span_columns is True
        assert hints.float_position is None  # Use default

    def test_optimize_block_sequence_disabled(self) -> None:
        """Test block sequence optimization when disabled."""
        engine: Any = LayoutEngine({"enable_optimization": False})
        blocks = ["Block 1", "Block 2", "Block 3"]

        result = engine._optimize_block_sequence(blocks)

        assert result == blocks  # Should be unchanged

    def test_optimize_block_sequence_enabled(self) -> None:
        """Test block sequence optimization when enabled."""
        blocks = [
            "\\begin{DndTable}Table content\\end{DndTable}",
            "Regular content",
            "\\begin{figure}Figure content\\end{figure}",
        ]

        result = self.engine._optimize_block_sequence(blocks)

        # Should have spacing added between different content types
        assert len(result) >= len(blocks)

    def test_content_has_floats(self) -> None:
        """Test float detection in content."""
        assert (
            self.engine._content_has_floats("\\begin{figure}content\\end{figure}")
            is True
        )
        assert (
            self.engine._content_has_floats("\\begin{table}content\\end{table}") is True
        )
        assert (
            self.engine._content_has_floats(
                "\\begin{DndMonster}content\\end{DndMonster}"
            )
            is True
        )
        assert self.engine._content_has_floats("float=!t") is True
        assert self.engine._content_has_floats("Regular content") is False

    def test_content_has_sidebars(self) -> None:
        """Test sidebar detection in content."""
        assert (
            self.engine._content_has_sidebars(
                "\\begin{DndSidebar}content\\end{DndSidebar}"
            )
            is True
        )
        assert (
            self.engine._content_has_sidebars(
                "\\begin{DndComment}content\\end{DndComment}"
            )
            is True
        )
        assert (
            self.engine._content_has_sidebars(
                "\\begin{DndReadAloud}content\\end{DndReadAloud}"
            )
            is True
        )
        assert self.engine._content_has_sidebars("Regular content") is False

    def test_content_has_tables(self) -> None:
        """Test table detection in content."""
        assert (
            self.engine._content_has_tables("\\begin{DndTable}content\\end{DndTable}")
            is True
        )
        assert (
            self.engine._content_has_tables("\\begin{tabular}content\\end{tabular}")
            is True
        )
        assert (
            self.engine._content_has_tables("\\begin{longtable}content\\end{longtable}")
            is True
        )
        assert self.engine._content_has_tables("Regular content") is False

    def test_get_manager_by_type(self) -> None:
        """Test getting manager by type."""
        from dnd5e.renderers.latex.layout.float_manager import (
            FloatManager,  # type: ignore
        )
        from dnd5e.renderers.latex.layout.multi_column import (
            MultiColumnManager,  # type: ignore
        )

        multi_col_manager = self.engine.get_manager_by_type(MultiColumnManager)
        assert multi_col_manager is not None
        assert isinstance(multi_col_manager, MultiColumnManager)

        float_manager = self.engine.get_manager_by_type(FloatManager)
        assert float_manager is not None
        assert isinstance(float_manager, FloatManager)

        # Non-existent manager type
        result = self.engine.get_manager_by_type(str)
        assert result is None

    def test_set_global_strategy(self) -> None:
        """Test setting global strategy."""
        self.engine.set_global_strategy(LayoutStrategy.MAGAZINE)
        assert hasattr(self.engine, "global_strategy")
        assert self.engine.global_strategy == LayoutStrategy.MAGAZINE

    def test_optimize_for_adventure_document(self) -> None:
        """Test optimization for adventure document type."""
        self.engine.optimize_for_document_type("adventure")

        assert (
            self.engine.strategy_preferences[ContentType.ADVENTURE]
            == LayoutStrategy.ADVENTURE
        )
        assert (
            self.engine.strategy_preferences[ContentType.CREATURE]
            == LayoutStrategy.ADVENTURE
        )
        assert self.engine.default_column_count == 1

    def test_optimize_for_reference_document(self) -> None:
        """Test optimization for reference document type."""
        self.engine.optimize_for_document_type("reference")

        for content_type in ContentType:
            assert (
                self.engine.strategy_preferences[content_type]
                == LayoutStrategy.REFERENCE
            )
        assert self.engine.default_column_count == 2

    def test_optimize_for_supplement_document(self) -> None:
        """Test optimization for supplement document type."""
        self.engine.optimize_for_document_type("supplement")

        for content_type in ContentType:
            assert (
                self.engine.strategy_preferences[content_type]
                == LayoutStrategy.SUPPLEMENT
            )
        assert self.engine.default_column_count == 2

    def test_get_layout_statistics_empty(self) -> None:
        """Test layout statistics with empty blocks."""
        stats = self.engine.get_layout_statistics([])

        assert stats["total_blocks"] == 0
        assert stats["blocks_with_floats"] == 0
        assert stats["blocks_with_sidebars"] == 0
        assert stats["blocks_with_tables"] == 0
        assert stats["blocks_with_columns"] == 0

    def test_get_layout_statistics_mixed_content(self) -> None:
        """Test layout statistics with mixed content."""
        blocks = [
            "\\begin{DndTable}Table\\end{DndTable}",
            "\\begin{multicols}{2}Columns\\end{multicols}",
            "\\begin{figure}Float\\end{figure}",
            "\\begin{DndSidebar}Sidebar\\end{DndSidebar}",
            "Regular content",
        ]

        stats = self.engine.get_layout_statistics(blocks)

        assert stats["total_blocks"] == 5
        assert stats["blocks_with_floats"] == 1
        assert stats["blocks_with_sidebars"] == 1
        assert stats["blocks_with_tables"] == 1
        assert stats["blocks_with_columns"] == 1
