"""Tests for the tag enhancement framework."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, create_autospec

import pytest

from studiorum.core.models.content import ContentType
from studiorum.renderers.core.enhancers import (
    CompositeEnhancer,
    ContentTrackerEnhancer,
    HyperlinkEnhancer,
    LaTeXFormatEnhancer,
    ValidationEnhancer,
    create_latex_enhancement_pipeline,
    create_plain_text_enhancement_pipeline,
)
from studiorum.renderers.core.interfaces import (
    ContentReferenceInfo,
    FormatStyle,
    RenderingContext,
)


@pytest.mark.rendering
class TestLaTeXFormatEnhancer:
    """Tests for LaTeX format enhancement."""

    def test_init_with_priority(self):
        """Test enhancer initialization with priority."""
        enhancer = LaTeXFormatEnhancer(priority=150)
        assert enhancer.get_enhancement_priority() == 150

    def test_default_priority(self):
        """Test default priority value."""
        enhancer = LaTeXFormatEnhancer()
        assert enhancer.get_enhancement_priority() == 100

    def test_bold_formatting(self):
        """Test bold format style application."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            format_style=FormatStyle.BOLD,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\textbf{Ancient Red Dragon}"

    def test_italic_formatting(self):
        """Test italic format style application."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Fireball",
            display_text="fireball",
            format_style=FormatStyle.ITALIC,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\textit{fireball}"

    def test_monospace_formatting(self):
        """Test monospace format style application."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="code",
            display_text="some code",
            format_style=FormatStyle.MONOSPACE,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\texttt{some code}"

    def test_emphasis_formatting(self):
        """Test emphasis format style application."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="important",
            display_text="important text",
            format_style=FormatStyle.EMPHASIS,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\emph{important text}"

    def test_plain_formatting(self):
        """Test plain format style (no formatting)."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="plain",
            display_text="plain text",
            format_style=FormatStyle.PLAIN,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "plain text"

    def test_latex_escaping(self):
        """Test that special LaTeX characters are escaped."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="special",
            display_text="Text with $ and & and %",
            format_style=FormatStyle.PLAIN,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        # Should escape LaTeX special characters
        assert "$" not in result or "\\$" in result
        assert "&" not in result or "\\&" in result
        assert "%" not in result or "\\%" in result

    def test_adventure_page_reference(self):
        """Test adventure page reference formatting."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Lost Mine of Phandelver",
            display_text="Lost Mine of Phandelver",
            page="5",
            content_type=ContentType("adventure"),
            format_style=FormatStyle.ITALIC,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\textit{Lost Mine of Phandelver} (p. 5)"

    def test_book_page_reference(self):
        """Test book page reference formatting."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Player's Handbook",
            display_text="Player's Handbook",
            page="15",
            content_type=ContentType("book"),
            format_style=FormatStyle.ITALIC,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "\\textit{Player's Handbook}, p. 15"

    def test_skip_page_one(self):
        """Test that page reference '1' is not added."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Something",
            display_text="Something",
            page="1",
            format_style=FormatStyle.PLAIN,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=True)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Something"
        assert "p. 1" not in result

    def test_disabled_formatting(self):
        """Test behavior when LaTeX formatting is disabled."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            format_style=FormatStyle.BOLD,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"enhancement_config": Mock(enable_latex_formatting=False)},
        )

        result = enhancer.enhance_content_reference(content_info, context)
        # Should just escape, no formatting
        assert result == "Ancient Red Dragon"
        assert "\\textbf" not in result

    def test_no_config(self):
        """Test behavior with no enhancement config."""
        enhancer = LaTeXFormatEnhancer()
        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            format_style=FormatStyle.BOLD,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={},  # No config
        )

        result = enhancer.enhance_content_reference(content_info, context)
        # Should just escape, no formatting
        assert result == "Ancient Red Dragon"


@pytest.mark.rendering
class TestHyperlinkEnhancer:
    """Tests for hyperlink enhancement."""

    def test_init_with_priority(self):
        """Test enhancer initialization with priority."""
        enhancer = HyperlinkEnhancer(priority=250)
        assert enhancer.get_enhancement_priority() == 250

    def test_default_priority(self):
        """Test default priority value."""
        enhancer = HyperlinkEnhancer()
        assert enhancer.get_enhancement_priority() == 200

    def test_creates_hyperlink_when_enabled(self):
        """Test hyperlink creation when enabled and manager available."""
        enhancer = HyperlinkEnhancer()

        # Mock hyperlink manager
        mock_hyperlink_manager = Mock()
        mock_hyperlink_manager.should_create_hyperlink.return_value = True
        mock_hyperlink_manager.create_hyperlink.return_value = (
            "\\hyperref[creature:dragon]{Dragon}"
        )

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_hyperlinks=True),
                "hyperlink_manager": mock_hyperlink_manager,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)

        # Verify hyperlink manager was called correctly
        mock_hyperlink_manager.should_create_hyperlink.assert_called_once_with(
            "creature"
        )
        mock_hyperlink_manager.create_hyperlink.assert_called_once_with(
            text="Ancient Red Dragon",
            ref_id="creature:dragon",
            content_type="creature",
        )

        assert result == "\\hyperref[creature:dragon]{Dragon}"

    def test_skips_when_disabled(self):
        """Test that hyperlinks are skipped when disabled in config."""
        enhancer = HyperlinkEnhancer()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_hyperlinks=False),
                "hyperlink_manager": Mock(),
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"

    def test_skips_when_no_manager(self):
        """Test that hyperlinks are skipped when no manager available."""
        enhancer = HyperlinkEnhancer()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_hyperlinks=True),
                "hyperlink_manager": None,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"

    def test_skips_when_manager_says_no(self):
        """Test that hyperlinks are skipped when manager says not to create."""
        enhancer = HyperlinkEnhancer()

        mock_hyperlink_manager = Mock()
        mock_hyperlink_manager.should_create_hyperlink.return_value = False

        content_info = ContentReferenceInfo(
            name="Filter",
            display_text="Some filter",
            content_type=None,  # No specific type, typically not hyperlinked
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_hyperlinks=True),
                "hyperlink_manager": mock_hyperlink_manager,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)

        mock_hyperlink_manager.should_create_hyperlink.assert_called_once_with(
            "content"
        )
        mock_hyperlink_manager.create_hyperlink.assert_not_called()

        assert result == "Some filter"

    def test_ref_id_generation(self):
        """Test reference ID generation for different content types."""
        enhancer = HyperlinkEnhancer()

        # Test with source
        content_info = ContentReferenceInfo(
            name="Dragon Wyrmling",
            display_text="Red Dragon Wyrmling",
            source="MM",
            content_type=ContentType("creature"),
        )

        ref_id = enhancer._generate_ref_id(content_info)
        assert ref_id == "creature:dragon-wyrmling:mm"

        # Test without source
        content_info_no_source = ContentReferenceInfo(
            name="Fireball",
            display_text="fireball",
            content_type=ContentType("spell"),
        )

        ref_id_no_source = enhancer._generate_ref_id(content_info_no_source)
        assert ref_id_no_source == "spell:fireball"

    def test_handles_hyperlink_creation_error(self):
        """Test graceful handling of hyperlink creation errors."""
        enhancer = HyperlinkEnhancer()

        mock_hyperlink_manager = Mock()
        mock_hyperlink_manager.should_create_hyperlink.return_value = True
        mock_hyperlink_manager.create_hyperlink.side_effect = Exception(
            "Hyperlink error"
        )

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_hyperlinks=True),
                "hyperlink_manager": mock_hyperlink_manager,
            },
        )

        # Should not raise, should return original text
        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"


@pytest.mark.rendering
class TestContentTrackerEnhancer:
    """Tests for content tracking enhancement."""

    def test_init_with_priority(self):
        """Test enhancer initialization with priority."""
        enhancer = ContentTrackerEnhancer(priority=350)
        assert enhancer.get_enhancement_priority() == 350

    def test_default_priority(self):
        """Test default priority value."""
        enhancer = ContentTrackerEnhancer()
        assert enhancer.get_enhancement_priority() == 300

    def test_tracks_content_when_enabled(self):
        """Test content tracking when enabled and tracker available."""
        enhancer = ContentTrackerEnhancer()

        mock_content_tracker = Mock()

        content_info = ContentReferenceInfo(
            name="Ancient Red Dragon",
            display_text="Ancient Red Dragon",
            source="MM",
            page="5",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_content_tracking=True),
                "content_tracker": mock_content_tracker,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)

        # Verify content was tracked
        mock_content_tracker.add_content.assert_called_once_with(
            content_type="creature",
            name="Ancient Red Dragon",
            source="MM",
            page="5",
        )

        # Should return original text
        assert result == "Ancient Red Dragon"

    def test_skips_when_disabled(self):
        """Test that tracking is skipped when disabled in config."""
        enhancer = ContentTrackerEnhancer()

        mock_content_tracker = Mock()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_content_tracking=False),
                "content_tracker": mock_content_tracker,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)

        mock_content_tracker.add_content.assert_not_called()
        assert result == "Ancient Red Dragon"

    def test_skips_when_no_tracker(self):
        """Test that tracking is skipped when no tracker available."""
        enhancer = ContentTrackerEnhancer()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_content_tracking=True),
                "content_tracker": None,
            },
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"

    def test_handles_tracking_error(self):
        """Test graceful handling of content tracking errors."""
        enhancer = ContentTrackerEnhancer()

        mock_content_tracker = Mock()
        mock_content_tracker.add_content.side_effect = Exception("Tracking error")

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            metadata={
                "enhancement_config": Mock(enable_content_tracking=True),
                "content_tracker": mock_content_tracker,
            },
        )

        # Should not raise, should return original text
        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"


@pytest.mark.rendering
class TestValidationEnhancer:
    """Tests for validation enhancement."""

    def test_init_with_priority(self):
        """Test enhancer initialization with priority."""
        enhancer = ValidationEnhancer(priority=450)
        assert enhancer.get_enhancement_priority() == 450

    def test_default_priority(self):
        """Test default priority value."""
        enhancer = ValidationEnhancer()
        assert enhancer.get_enhancement_priority() == 400

    def test_skips_when_not_debug_mode(self):
        """Test that validation is skipped when not in debug mode."""
        enhancer = ValidationEnhancer()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
        )

        context = RenderingContext(
            output_format="latex",
            debug_mode=False,  # Not debug mode
            omnidexer=Mock(),
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"

    def test_validates_in_debug_mode(self):
        """Test that validation runs in debug mode."""
        enhancer = ValidationEnhancer()

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            debug_mode=True,
            omnidexer=Mock(),
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"

    def test_detects_suspicious_content_name(self):
        """Test detection of suspicious content names."""
        enhancer = ValidationEnhancer()

        content_info = ContentReferenceInfo(
            name="   ",  # Whitespace only name (passes min_length but suspicious)
            display_text="Some display text",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            debug_mode=True,
            omnidexer=Mock(),
        )

        result = enhancer.enhance_content_reference(content_info, context)
        assert result.startswith("[EMPTY:")
        assert "Some display text" in result

    def test_handles_validation_error(self):
        """Test graceful handling of validation errors."""
        enhancer = ValidationEnhancer()

        # Mock omnidexer that raises exception
        mock_omnidexer = Mock()
        mock_omnidexer.side_effect = Exception("Validation error")

        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
        )

        context = RenderingContext(
            output_format="latex",
            debug_mode=True,
            omnidexer=mock_omnidexer,
        )

        # Should not raise, should return original text
        result = enhancer.enhance_content_reference(content_info, context)
        assert result == "Ancient Red Dragon"


@pytest.mark.rendering
class TestCompositeEnhancer:
    """Tests for composite enhancer functionality."""

    def test_init_with_enhancers(self):
        """Test composite enhancer initialization."""
        latex_enhancer = LaTeXFormatEnhancer(priority=100)
        hyperlink_enhancer = HyperlinkEnhancer(priority=200)

        composite = CompositeEnhancer([latex_enhancer, hyperlink_enhancer])

        # Should be sorted by priority
        assert len(composite.enhancers) == 2
        assert composite.enhancers[0] is latex_enhancer  # Priority 100
        assert composite.enhancers[1] is hyperlink_enhancer  # Priority 200

    def test_get_priority_returns_lowest(self):
        """Test that composite returns lowest priority of constituents."""
        latex_enhancer = LaTeXFormatEnhancer(priority=100)
        hyperlink_enhancer = HyperlinkEnhancer(priority=200)

        composite = CompositeEnhancer([latex_enhancer, hyperlink_enhancer])
        assert composite.get_enhancement_priority() == 100

    def test_applies_enhancers_in_sequence(self):
        """Test that enhancers are applied in priority order."""
        # Mock enhancers to track call order
        mock_enhancer1 = Mock()
        mock_enhancer1.get_enhancement_priority.return_value = 100
        mock_enhancer1.enhance_content_reference.return_value = "Step 1"

        mock_enhancer2 = Mock()
        mock_enhancer2.get_enhancement_priority.return_value = 200
        mock_enhancer2.enhance_content_reference.return_value = "Step 2"

        composite = CompositeEnhancer(
            [mock_enhancer2, mock_enhancer1]
        )  # Note: reversed order

        content_info = ContentReferenceInfo(
            name="Test",
            display_text="Original",
        )

        context = RenderingContext(output_format="latex")

        result = composite.enhance_content_reference(content_info, context)

        # Should be called in priority order (enhancer1 first)
        assert mock_enhancer1.enhance_content_reference.call_count == 1
        assert mock_enhancer2.enhance_content_reference.call_count == 1

        # Result should be from the last enhancer
        assert result == "Step 2"

    def test_handles_enhancer_errors(self):
        """Test graceful handling of individual enhancer errors."""
        # First enhancer fails
        mock_enhancer1 = Mock()
        mock_enhancer1.get_enhancement_priority.return_value = 100
        mock_enhancer1.enhance_content_reference.side_effect = Exception(
            "Enhancer 1 error"
        )

        # Second enhancer succeeds
        mock_enhancer2 = Mock()
        mock_enhancer2.get_enhancement_priority.return_value = 200
        mock_enhancer2.enhance_content_reference.return_value = "Success"

        composite = CompositeEnhancer([mock_enhancer1, mock_enhancer2])

        content_info = ContentReferenceInfo(
            name="Test",
            display_text="Original",
        )

        context = RenderingContext(output_format="latex")

        result = composite.enhance_content_reference(content_info, context)

        # Should continue despite first enhancer failing
        assert result == "Success"


@pytest.mark.rendering
class TestPipelineFactories:
    """Tests for enhancement pipeline factory functions."""

    def test_create_latex_enhancement_pipeline(self):
        """Test LaTeX pipeline creation."""
        enhancers = create_latex_enhancement_pipeline()

        assert len(enhancers) == 4

        # Check types and priorities
        priorities = [e.get_enhancement_priority() for e in enhancers]
        assert priorities == [100, 200, 300, 400]  # Should be sorted

        # Check types
        types = [type(e).__name__ for e in enhancers]
        assert "LaTeXFormatEnhancer" in types
        assert "HyperlinkEnhancer" in types
        assert "ContentTrackerEnhancer" in types
        assert "ValidationEnhancer" in types

    def test_create_plain_text_enhancement_pipeline(self):
        """Test plain text pipeline creation."""
        enhancers = create_plain_text_enhancement_pipeline()

        assert len(enhancers) == 2

        # Check types
        types = [type(e).__name__ for e in enhancers]
        assert "ContentTrackerEnhancer" in types
        assert "ValidationEnhancer" in types

        # Should not include LaTeX formatting or hyperlinks
        assert "LaTeXFormatEnhancer" not in types
        assert "HyperlinkEnhancer" not in types
