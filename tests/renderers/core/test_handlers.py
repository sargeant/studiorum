"""Tests for core tag handlers with consolidated business logic."""

from unittest.mock import MagicMock, Mock

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.renderers.core.handlers import (
    BaseCoreTagHandler,
    CoreAdventureTagHandler,
    CoreBackgroundTagHandler,
    CoreBookTagHandler,
    CoreClassTagHandler,
    CoreConditionTagHandler,
    CoreCreatureTagHandler,
    CoreFeatTagHandler,
    CoreItemTagHandler,
    CoreRaceTagHandler,
    CoreSpellTagHandler,
    get_default_core_handlers,
)
from dnd5e.renderers.core.interfaces import (
    FormatStyle,
    RenderingContext,
    TagValidationError,
)


@pytest.mark.rendering
class TestBaseCoreTagHandler:
    """Test the base core tag handler functionality."""

    def test_base_handler_initialization(self):
        """Test creating a base handler."""
        handler = BaseCoreTagHandler("test", ContentType("creature"))

        assert handler.tag_type == "test"
        assert handler.content_type == ContentType("creature")

    def test_handles_tag_type(self):
        """Test tag type checking."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        assert handler.handles_tag_type("creature") is True
        assert handler.handles_tag_type("spell") is False

    def test_should_include_page_reference(self):
        """Test page reference business rule."""
        handler = BaseCoreTagHandler("test", None)

        # Page "1" should not be included
        assert handler.should_include_page_reference("1") is False

        # Other pages should be included
        assert handler.should_include_page_reference("2") is True
        assert handler.should_include_page_reference("100") is True

        # None should not be included
        assert handler.should_include_page_reference(None) is False

    def test_extract_display_text_with_display_text_nodes(self):
        """Test display text extraction with display_text_nodes."""
        handler = BaseCoreTagHandler("test", None)
        context = RenderingContext(output_format="latex")

        # Create mock node with display_text_nodes
        mock_child1 = Mock()
        mock_child1.text = "Hello "
        mock_child2 = Mock()
        mock_child2.text = "World"

        mock_node = Mock()
        mock_node.display_text_nodes = [mock_child1, mock_child2]
        mock_node.name = "fallback name"

        result = handler._extract_display_text(mock_node, context)
        assert result == "Hello World"

    def test_extract_display_text_fallback_to_name(self):
        """Test display text extraction falling back to name."""
        handler = BaseCoreTagHandler("test", None)
        context = RenderingContext(output_format="latex")

        # Create mock node without display_text_nodes but with name
        mock_node = Mock()
        mock_node.display_text_nodes = None
        mock_node.name = "Test Name"

        result = handler._extract_display_text(mock_node, context)
        assert result == "Test Name"

    def test_extract_display_text_final_fallback(self):
        """Test display text extraction final fallback to str(node)."""
        handler = BaseCoreTagHandler("test", None)
        context = RenderingContext(output_format="latex")

        # Create mock node without display_text_nodes or name
        mock_node = Mock()
        mock_node.display_text_nodes = None
        mock_node.name = None
        mock_node.__str__ = Mock(return_value="Mock Node String")

        result = handler._extract_display_text(mock_node, context)
        assert result == "Mock Node String"

    def test_validate_content_reference_success(self):
        """Test successful content validation."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        # Create mock context with omnidexer
        mock_content = Mock()
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = mock_content

        context = RenderingContext(output_format="latex", omnidexer=mock_omnidexer)

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Goblin"
        mock_node.source = "MM"

        # Validate
        errors = handler.validate_content_reference(mock_node, context)

        assert errors == []
        mock_omnidexer.find.assert_called_once_with(
            ContentType("creature"), "Goblin", "MM"
        )

    def test_validate_content_reference_not_found(self):
        """Test validation when content is not found."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        # Create mock context with omnidexer that returns None
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        context = RenderingContext(output_format="latex", omnidexer=mock_omnidexer)

        # Create mock node
        mock_node = Mock()
        mock_node.name = "NonexistentCreature"
        mock_node.source = "MM"

        # Validate
        errors = handler.validate_content_reference(mock_node, context)

        assert len(errors) == 1
        error = errors[0]
        assert error.error_type == "missing_content"
        assert "NonexistentCreature" in error.message
        assert "MM" in error.message
        assert error.tag_type == "creature"
        assert error.tag_name == "NonexistentCreature"
        assert error.source == "MM"

    def test_validate_content_reference_no_omnidexer(self):
        """Test validation when no omnidexer is available."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        context = RenderingContext(output_format="latex")  # No omnidexer
        mock_node = Mock()
        mock_node.name = "Goblin"

        # Should skip validation and return no errors
        errors = handler.validate_content_reference(mock_node, context)
        assert errors == []

    def test_track_content_for_appendix(self):
        """Test content tracking for appendix generation."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        # Create mock content tracker
        mock_tracker = Mock()
        context = RenderingContext(output_format="latex", content_tracker=mock_tracker)

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Goblin"
        mock_node.source = "MM"
        mock_node.page = "166"

        # Track content
        handler.track_content_for_appendix(mock_node, context)

        mock_tracker.add_content.assert_called_once_with(
            "creature", "Goblin", "MM", "166"
        )

    def test_track_content_no_tracker(self):
        """Test content tracking when no tracker is available."""
        handler = BaseCoreTagHandler("creature", ContentType("creature"))

        context = RenderingContext(output_format="latex")  # No content_tracker
        mock_node = Mock()

        # Should not raise exception
        handler.track_content_for_appendix(mock_node, context)


@pytest.mark.rendering
class TestCreatureTagHandler:
    """Test the creature tag handler."""

    def test_creature_handler_initialization(self):
        """Test creature handler setup."""
        handler = CoreCreatureTagHandler()

        assert handler.tag_type == "creature"
        assert handler.content_type == ContentType("creature")
        assert handler.handles_tag_type("creature") is True
        assert handler.handles_tag_type("spell") is False

    def test_extract_content_info(self):
        """Test extracting creature content information."""
        handler = CoreCreatureTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Adult Red Dragon"
        mock_node.source = "MM"
        mock_node.page = "98"
        mock_node.display_text_nodes = None  # Use name fallback

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Adult Red Dragon"
        assert info.display_text == "Adult Red Dragon"
        assert info.source == "MM"
        assert info.page == "98"
        assert info.content_type == ContentType("creature")
        assert info.format_style == FormatStyle.BOLD  # Creatures are bold


@pytest.mark.rendering
class TestSpellTagHandler:
    """Test the spell tag handler."""

    def test_spell_handler_initialization(self):
        """Test spell handler setup."""
        handler = CoreSpellTagHandler()

        assert handler.tag_type == "spell"
        assert handler.content_type == ContentType("spell")

    def test_extract_content_info(self):
        """Test extracting spell content information."""
        handler = CoreSpellTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Fireball"
        mock_node.source = "PHB"
        mock_node.page = "241"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Fireball"
        assert info.display_text == "Fireball"
        assert info.source == "PHB"
        assert info.page == "241"
        assert info.content_type == ContentType("spell")
        assert info.format_style == FormatStyle.ITALIC  # Spells are italic


@pytest.mark.rendering
class TestItemTagHandler:
    """Test the item tag handler."""

    def test_item_handler_initialization(self):
        """Test item handler setup."""
        handler = CoreItemTagHandler()

        assert handler.tag_type == "item"
        assert handler.content_type == ContentType("item")

    def test_extract_content_info(self):
        """Test extracting item content information."""
        handler = CoreItemTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Longsword"
        mock_node.source = "PHB"
        mock_node.page = "149"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Longsword"
        assert info.display_text == "Longsword"
        assert info.format_style == FormatStyle.ITALIC  # Items are italic


@pytest.mark.rendering
class TestAdventureTagHandler:
    """Test the adventure tag handler with special page handling."""

    def test_adventure_handler_initialization(self):
        """Test adventure handler setup."""
        handler = CoreAdventureTagHandler()

        assert handler.tag_type == "adventure"
        assert handler.content_type == ContentType("adventure")

    def test_extract_content_info_with_page(self):
        """Test adventure content extraction with page reference."""
        handler = CoreAdventureTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Lost Mine of Phandelver"
        mock_node.source = "Starter Set"
        mock_node.page = "15"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Lost Mine of Phandelver"
        # Core handlers return display_text without page formatting (enhancers handle that)
        assert info.display_text == "Lost Mine of Phandelver"
        assert info.page == "15"
        assert info.format_style == FormatStyle.PLAIN

    def test_extract_content_info_page_one(self):
        """Test adventure content extraction with page '1' (should be excluded)."""
        handler = CoreAdventureTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node with page "1"
        mock_node = Mock()
        mock_node.name = "Adventure Start"
        mock_node.page = "1"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Adventure Start"
        # Page "1" should not be appended
        assert info.display_text == "Adventure Start"
        assert info.page == "1"


@pytest.mark.rendering
class TestBookTagHandler:
    """Test the book tag handler with different page handling."""

    def test_book_handler_initialization(self):
        """Test book handler setup."""
        handler = CoreBookTagHandler()

        assert handler.tag_type == "book"
        assert handler.content_type == ContentType("book")

    def test_extract_content_info_with_page(self):
        """Test book content extraction with page reference."""
        handler = CoreBookTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node
        mock_node = Mock()
        mock_node.name = "Player's Handbook"
        mock_node.page = "123"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Player's Handbook"
        # Core handlers return display_text without page formatting (enhancers handle that)
        assert info.display_text == "Player's Handbook"
        assert info.page == "123"
        assert info.format_style == FormatStyle.PLAIN

    def test_extract_content_info_page_one(self):
        """Test book content extraction with page '1' (should be included for books)."""
        handler = CoreBookTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node with page "1"
        mock_node = Mock()
        mock_node.name = "Test Book"
        mock_node.page = "1"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "Test Book"
        # Core handlers return display_text without page formatting (enhancers handle that)
        assert info.display_text == "Test Book"
        assert info.page == "1"


@pytest.mark.rendering
class TestConditionTagHandler:
    """Test the condition tag handler."""

    def test_condition_handler_initialization(self):
        """Test condition handler setup."""
        handler = CoreConditionTagHandler()

        assert handler.tag_type == "condition"
        assert (
            handler.content_type is None
        )  # Conditions don't have content type validation yet

    def test_extract_content_info_with_condition_attribute(self):
        """Test condition extraction using 'condition' attribute."""
        handler = CoreConditionTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node with condition attribute
        mock_node = Mock()
        mock_node.condition = "charmed"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "charmed"
        assert info.display_text == "charmed"
        assert info.source is None
        assert info.page is None
        assert info.format_style == FormatStyle.ITALIC  # Conditions are italic

    def test_extract_content_info_fallback_to_name(self):
        """Test condition extraction falling back to 'name' attribute."""
        handler = CoreConditionTagHandler()
        context = RenderingContext(output_format="latex")

        # Create mock node without condition but with name
        mock_node = Mock()
        mock_node.condition = None
        mock_node.name = "poisoned"
        mock_node.display_text_nodes = None

        # Extract content info
        info = handler.extract_content_info(mock_node, context)

        assert info.name == "poisoned"
        assert info.display_text == "poisoned"


@pytest.mark.rendering
class TestDefaultCoreHandlers:
    """Test the default handler registry."""

    def test_get_default_core_handlers(self):
        """Test that all expected handlers are included."""
        handlers = get_default_core_handlers()

        # Check that we have all the expected handler types
        handler_types = [h.tag_type for h in handlers]
        expected_types = [
            "creature",
            "spell",
            "item",
            "class",
            "feat",
            "race",
            "background",
            "adventure",
            "book",
            "condition",
            "dc",
            "dice",
            "formatting",
        ]

        for expected_type in expected_types:
            assert expected_type in handler_types, (
                f"Missing handler for {expected_type}"
            )

        assert len(handlers) == len(expected_types)

    def test_handlers_are_properly_typed(self):
        """Test that handlers implement the CoreTagHandler protocol."""
        handlers = get_default_core_handlers()

        for handler in handlers:
            # Check that handler implements required methods
            assert hasattr(handler, "handles_tag_type")
            assert hasattr(handler, "extract_content_info")
            assert hasattr(handler, "should_include_page_reference")
            assert hasattr(handler, "validate_content_reference")
            assert hasattr(handler, "track_content_for_appendix")

            # Check that methods are callable
            assert callable(handler.handles_tag_type)
            assert callable(handler.extract_content_info)
            assert callable(handler.should_include_page_reference)
            assert callable(handler.validate_content_reference)
            assert callable(handler.track_content_for_appendix)
