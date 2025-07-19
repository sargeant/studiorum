"""Tests for multi-column layout manager."""

from unittest.mock import Mock

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.renderers.latex.layout.base import LayoutContext, LayoutHint, LayoutStrategy
from dnd5e.renderers.latex.layout.multi_column import MultiColumnManager


class TestMultiColumnManager:
    """Test cases for multi-column layout manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = MultiColumnManager()

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        assert self.manager.default_columns == 2
        assert self.manager.column_sep == "1cm"
        assert self.manager.balance_columns is True

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "default_columns": 3,
            "column_sep": "2cm",
            "balance_columns": False,
        }
        manager = MultiColumnManager(config)

        assert manager.default_columns == 3
        assert manager.column_sep == "2cm"
        assert manager.balance_columns is False

    def test_get_supported_content_types(self):
        """Test that all content types are supported."""
        supported = self.manager.get_supported_content_types()
        assert supported == set(ContentType)

    def test_can_handle_multi_column_strategy(self):
        """Test handling of multi-column strategies."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        assert self.manager.can_handle(context) is True

    def test_can_handle_magazine_strategy(self):
        """Test handling of magazine strategy."""
        context = LayoutContext(
            strategy=LayoutStrategy.MAGAZINE, content_type=ContentType.SPELL
        )
        assert self.manager.can_handle(context) is True

    def test_cannot_handle_single_column_strategy(self):
        """Test rejection of single column strategy."""
        context = LayoutContext(
            strategy=LayoutStrategy.SINGLE_COLUMN, content_type=ContentType.SPELL
        )
        assert self.manager.can_handle(context) is False

    def test_get_priority(self):
        """Test priority level."""
        assert self.manager.get_priority() == 80

    def test_determine_column_count_spell(self):
        """Test column count determination for spells."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        count = self.manager._determine_column_count(context)
        assert count == 2

    def test_determine_column_count_creature(self):
        """Test column count determination for creatures."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.CREATURE
        )
        count = self.manager._determine_column_count(context)
        assert count == 1

    def test_determine_column_count_with_hints(self):
        """Test column count determination with hints."""
        hints = LayoutHint()
        hints.column_count = 3

        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN,
            content_type=ContentType.SPELL,
            hints=hints,
        )
        count = self.manager._determine_column_count(context)
        assert count == 3

    def test_should_use_columns_normal_content(self):
        """Test column usage for normal content."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        assert self.manager._should_use_columns(context) is True

    def test_should_not_use_columns_with_span_hint(self):
        """Test column avoidance with span columns hint."""
        hints = LayoutHint()
        hints.span_columns = True

        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN,
            content_type=ContentType.SPELL,
            hints=hints,
        )
        assert self.manager._should_use_columns(context) is False

    def test_should_not_use_columns_for_creatures(self):
        """Test column avoidance for creature content."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.CREATURE
        )
        assert self.manager._should_use_columns(context) is False

    def test_apply_layout_empty_content(self):
        """Test layout application with empty content."""
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        result = self.manager.apply_layout("", context)
        assert result == ""

    def test_apply_layout_single_column(self):
        """Test layout application for single column content."""
        content = "Test content"
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN,
            content_type=ContentType.CREATURE,  # Forces single column
        )
        result = self.manager.apply_layout(content, context)
        assert result == content  # Should be unchanged

    def test_apply_layout_multi_column(self):
        """Test layout application for multi-column content."""
        content = "Test spell content"
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        result = self.manager.apply_layout(content, context)

        assert "\\begin{multicols}{2}" in result
        assert content in result
        assert "\\end{multicols}" in result

    def test_apply_layout_with_custom_column_sep(self):
        """Test layout application with custom column separation."""
        manager = MultiColumnManager({"column_sep": "2cm"})
        content = "Test content"
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        result = manager.apply_layout(content, context)

        assert "\\setlength{\\columnsep}{2cm}" in result

    def test_apply_layout_with_balancing(self):
        """Test layout application with column balancing."""
        content = "Test content"
        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN, content_type=ContentType.SPELL
        )
        result = self.manager.apply_layout(content, context)

        assert "\\raggedcolumns" in result
        assert "\\flushcolumns" in result

    def test_process_column_breaks_force_break(self):
        """Test processing column breaks with force break hint."""
        hints = LayoutHint()
        hints.force_column_break = True

        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN,
            content_type=ContentType.SPELL,
            hints=hints,
        )

        content = "Test content"
        result = self.manager._process_column_breaks(content, context)

        assert "\\columnbreak" in result
        assert content in result

    def test_process_column_breaks_avoid_break(self):
        """Test processing column breaks with avoid break hint."""
        hints = LayoutHint()
        hints.avoid_column_break = True

        context = LayoutContext(
            strategy=LayoutStrategy.MULTI_COLUMN,
            content_type=ContentType.SPELL,
            hints=hints,
        )

        content = "Test content"
        result = self.manager._process_column_breaks(content, context)

        assert "\\nopagebreak" in result
        assert content in result

    def test_create_column_span_content(self):
        """Test creating column-spanning content."""
        content = "Wide content that spans columns"
        result = self.manager.create_column_span_content(content)

        assert "\\end{multicols}" in result
        assert content in result
        assert "\\begin{multicols}{2}" in result

    def test_add_intelligent_column_break_before(self):
        """Test adding column break before content."""
        content = "Test content"
        result = self.manager.add_intelligent_column_break(content, "before")

        assert result.startswith("\\columnbreak")
        assert content in result

    def test_add_intelligent_column_break_after(self):
        """Test adding column break after content."""
        content = "Test content"
        result = self.manager.add_intelligent_column_break(content, "after")

        assert result.endswith("\\columnbreak\n")
        assert content in result

    def test_add_intelligent_column_break_auto_short(self):
        """Test automatic column break with short content."""
        content = "Short"
        result = self.manager.add_intelligent_column_break(content, "auto")

        # Should not add break for short content
        assert result == content
        assert "\\columnbreak" not in result

    def test_add_intelligent_column_break_auto_long(self):
        """Test automatic column break with long content."""
        content = (
            "This is a very long piece of content that should trigger an automatic column break. "
            * 10
        )
        content += "\n\nParagraph break here.\n\nMore content after break."

        result = self.manager.add_intelligent_column_break(content, "auto")

        # Should add break at paragraph boundary
        assert "\\columnbreak" in result

    def test_optimize_column_balance_empty(self):
        """Test column balance optimization with empty content."""
        result = self.manager.optimize_column_balance([])
        assert result == []

    def test_optimize_column_balance_single_item(self):
        """Test column balance optimization with single item."""
        content = ["Single item"]
        result = self.manager.optimize_column_balance(content)
        assert result == content

    def test_optimize_column_balance_multiple_items(self):
        """Test column balance optimization with multiple items."""
        content = [
            "Short item",
            "This is a much longer item that contains more text",
            "Another short item",
            "Final item with moderate length content",
        ]

        result = self.manager.optimize_column_balance(content)

        # Should return balanced content (exact balancing depends on algorithm)
        assert len(result) >= 1
        assert all(item.strip() for item in result)  # No empty items

    def test_get_column_layout_hints_spell(self):
        """Test layout hints for spell content."""
        hint = self.manager.get_column_layout_hints(ContentType.SPELL)

        assert hint.allow_float is True
        assert hint.avoid_column_break is True

    def test_get_column_layout_hints_creature(self):
        """Test layout hints for creature content."""
        hint = self.manager.get_column_layout_hints(ContentType.CREATURE)

        assert hint.span_columns is True
        assert hint.allow_float is True

    def test_get_column_layout_hints_item(self):
        """Test layout hints for item content."""
        hint = self.manager.get_column_layout_hints(ContentType.ITEM)

        assert hint.allow_float is True
        assert hint.group_with_next is True

    def test_get_column_layout_hints_background(self):
        """Test layout hints for background content."""
        hint = self.manager.get_column_layout_hints(ContentType.BACKGROUND)

        assert hint.span_columns is True
