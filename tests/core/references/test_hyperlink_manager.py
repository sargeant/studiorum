"""Tests for hyperlink manager."""

from typing import Any

import pytest

from dnd5e.core.references.hyperlink_manager import (  # type: ignore
    HyperlinkManager,
    HyperlinkStyle,
)
from tests.test_helpers import reset_test_environment


class TestHyperlinkStyle:
    """Test HyperlinkStyle dataclass."""

    def test_hyperlink_style_defaults(self) -> None:
        """Test default hyperlink style."""
        style: Any = HyperlinkStyle()

        assert style.color == "black"
        assert style.border is False
        assert style.underline is False
        assert style.font_style == "normal"

    def test_hyperlink_style_custom(self) -> None:
        """Test custom hyperlink style."""
        style: Any = HyperlinkStyle(
            color="blue",
            border=True,
            underline=True,
            font_style="bold",
        )

        assert style.color == "blue"
        assert style.border is True
        assert style.underline is True
        assert style.font_style == "bold"


class TestHyperlinkManager:
    """Test hyperlink manager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.manager = HyperlinkManager()

    def test_manager_initialization(self) -> None:
        """Test manager initialization."""
        assert self.manager.enabled is True
        assert self.manager.auto_page_refs is True
        assert "creature" in self.manager.content_styles
        assert "spell" in self.manager.content_styles
        assert "default" in self.manager.content_styles

    def test_should_create_hyperlink(self) -> None:
        """Test hyperlink creation conditions."""
        # Should create for most content types
        assert self.manager.should_create_hyperlink("creature")
        assert self.manager.should_create_hyperlink("spell")
        assert self.manager.should_create_hyperlink("item")

        # Should not create for filtered types
        assert not self.manager.should_create_hyperlink("filter")
        assert not self.manager.should_create_hyperlink("loader")

        # Should not create when disabled
        self.manager.enable_hyperlinks(False)
        assert not self.manager.should_create_hyperlink("creature")

    def test_create_basic_hyperlink(self) -> None:
        """Test creating basic hyperlinks."""
        hyperlink = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
        )

        assert "\\hyperref[creature:dragon]" in hyperlink
        assert "\\textbf{Dragon}" in hyperlink
        assert "\\pageref{creature:dragon}" in hyperlink

    def test_create_hyperlink_no_page_ref(self) -> None:
        """Test creating hyperlink without page reference."""
        hyperlink = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
            include_page_ref=False,
        )

        assert "\\hyperref[creature:dragon]" in hyperlink
        assert "\\textbf{Dragon}" in hyperlink
        assert "\\pageref" not in hyperlink

    def test_create_hyperlink_custom_style(self) -> None:
        """Test creating hyperlink with custom style."""
        custom_style: Any = HyperlinkStyle(
            color="red",
            font_style="italic",
        )

        hyperlink = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
            custom_style=custom_style,
            include_page_ref=False,
        )

        assert "\\hyperref[creature:dragon]" in hyperlink
        assert "\\textit{Dragon}" in hyperlink  # Should use italic from custom style

    def test_apply_text_formatting(self) -> None:
        """Test text formatting application."""
        style_normal: Any = HyperlinkStyle(font_style="normal")
        style_bold: Any = HyperlinkStyle(font_style="bold")
        style_italic: Any = HyperlinkStyle(font_style="italic")
        style_bolditalic: Any = HyperlinkStyle(font_style="bolditalic")

        assert self.manager._apply_text_formatting("text", style_normal) == "text"
        assert (
            self.manager._apply_text_formatting("text", style_bold) == "\\textbf{text}"
        )
        assert (
            self.manager._apply_text_formatting("text", style_italic)
            == "\\textit{text}"
        )
        assert (
            self.manager._apply_text_formatting("text", style_bolditalic)
            == "\\textbf{\\textit{text}}"
        )

    def test_content_type_styles(self) -> None:
        """Test content type specific styles."""
        # Test creature (should be bold)
        creature_link = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
            include_page_ref=False,
        )
        assert "\\textbf{Dragon}" in creature_link

        # Test spell (should be italic)
        spell_link = self.manager.create_hyperlink(
            text="Fireball",
            ref_id="spell:fireball",
            content_type="spell",
            include_page_ref=False,
        )
        assert "\\textit{Fireball}" in spell_link

    def test_create_external_link(self) -> None:
        """Test creating external URL links."""
        external_link = self.manager.create_external_link(
            text="D&D Beyond",
            url="https://www.dndbeyond.com",
        )

        assert "\\href{https://www.dndbeyond.com}" in external_link
        assert "D&D Beyond" in external_link

    def test_create_section_reference(self) -> None:
        """Test creating section references."""
        # Test nameref
        nameref = self.manager.create_section_reference(
            text="Introduction",
            section_label="sec:introduction",
            ref_type="nameref",
        )
        assert nameref == "\\nameref{sec:introduction}"

        # Test ref
        ref = self.manager.create_section_reference(
            text="Introduction",
            section_label="sec:introduction",
            ref_type="ref",
        )
        assert ref == "\\ref{sec:introduction}"

        # Test pageref
        pageref = self.manager.create_section_reference(
            text="Introduction",
            section_label="sec:introduction",
            ref_type="pageref",
        )
        assert pageref == "page \\pageref{sec:introduction}"

    def test_create_footnote_reference(self) -> None:
        """Test creating footnote references."""
        footnote_ref = self.manager.create_footnote_reference(
            text="Note",
            footnote_id="fn:note1",
        )

        assert footnote_ref == "\\footref{fn:note1}"

    def test_set_content_style(self) -> None:
        """Test setting custom content styles."""
        custom_style: Any = HyperlinkStyle(color="purple", font_style="bold")
        self.manager.set_content_style("custom", custom_style)

        assert "custom" in self.manager.content_styles
        assert self.manager.content_styles["custom"] == custom_style

    def test_set_page_reference_types(self) -> None:
        """Test setting page reference types."""
        new_types = {"creature", "spell"}
        self.manager.set_page_reference_types(new_types)

        assert self.manager.page_ref_types == new_types

        # Test that only these types get page refs
        creature_link = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
        )
        assert "\\pageref" in creature_link

        item_link = self.manager.create_hyperlink(
            text="Sword",
            ref_id="item:sword",
            content_type="item",
        )
        assert "\\pageref" not in item_link

    def test_enable_disable_features(self) -> None:
        """Test enabling/disabling features."""
        # Test hyperlinks
        self.manager.enable_hyperlinks(False)
        assert not self.manager.enabled

        hyperlink = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
        )
        assert hyperlink == "Dragon"  # Should return plain text

        # Test auto page refs
        self.manager.enable_hyperlinks(True)
        self.manager.enable_auto_page_refs(False)

        hyperlink = self.manager.create_hyperlink(
            text="Dragon",
            ref_id="creature:dragon",
            content_type="creature",
        )
        assert "\\pageref" not in hyperlink

    def test_get_latex_packages(self) -> None:
        """Test getting required LaTeX packages."""
        packages = self.manager.get_latex_packages()

        expected_packages = ["hyperref", "xcolor", "nameref", "footmisc"]
        for package in expected_packages:
            assert package in packages

    def test_get_latex_setup_commands(self) -> None:
        """Test getting LaTeX setup commands."""
        commands = self.manager.get_latex_setup_commands()

        assert any("\\hypersetup{" in cmd for cmd in commands)
        assert any("colorlinks=true" in cmd for cmd in commands)
        assert any("}" in cmd for cmd in commands)  # Should close hypersetup

    def test_create_bookmark(self) -> None:
        """Test creating PDF bookmarks."""
        bookmark = self.manager.create_bookmark("Chapter 1", level=1)

        assert "\\pdfbookmark[1]{Chapter 1}" in bookmark
        assert "chapter-1" in bookmark  # Sanitized ID

    def test_sanitize_bookmark_id(self) -> None:
        """Test bookmark ID sanitization."""
        test_cases = [
            ("Chapter 1", "chapter-1"),
            ("The Big Adventure!", "the-big-adventure"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("", ""),
        ]

        for input_text, expected in test_cases:
            result = self.manager._sanitize_bookmark_id(input_text)
            assert result == expected

    def test_validate_hyperlinks(self) -> None:
        """Test hyperlink validation."""
        content = """
        \\hyperref[creature:dragon]{Dragon}
        \\href{https://example.com}{Link}
        \\hyperref[invalid--ref]{Bad Ref}
        \\href{not-a-url}{Bad URL}
        """

        issues = self.manager.validate_hyperlinks(content)

        # Should find issues with invalid ref ID and URL
        assert len(issues) >= 1

        # Check that we can categorize issues by type
        issue_types = {issue["type"] for issue in issues}
        assert len(issue_types) > 0

        # Note: The validation logic needs to be more sophisticated
        # This test shows the expected structure

    def test_get_hyperlink_statistics(self) -> None:
        """Test getting hyperlink statistics."""
        content = """
        \\hyperref[creature:dragon]{Dragon}
        \\hyperref[spell:fireball]{Fireball}
        \\href{https://example.com}{External}
        """

        stats = self.manager.get_hyperlink_statistics(content)

        assert "total_internal_links" in stats
        assert "total_external_links" in stats
        assert "by_content_type" in stats

        assert stats["total_internal_links"] == 2
        assert stats["total_external_links"] == 1
        assert "creature" in stats["by_content_type"]
        assert "spell" in stats["by_content_type"]


class TestHyperlinkManagerEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.manager = HyperlinkManager()

    def test_empty_text(self) -> None:
        """Test handling of empty text."""
        hyperlink = self.manager.create_hyperlink(
            text="",
            ref_id="creature:dragon",
            content_type="creature",
        )

        # Should handle empty text gracefully
        assert "\\hyperref[creature:dragon]" in hyperlink

    def test_special_characters_in_text(self) -> None:
        """Test handling of special LaTeX characters in text."""
        hyperlink = self.manager.create_hyperlink(
            text="Dragon & Wyvern",
            ref_id="creature:dragon",
            content_type="creature",
            include_page_ref=False,
        )

        # Should include the text as-is (escaping should be handled elsewhere)
        assert "Dragon & Wyvern" in hyperlink

    def test_invalid_ref_id(self) -> None:
        """Test handling of invalid reference IDs."""
        # Should handle gracefully without crashing
        hyperlink = self.manager.create_hyperlink(
            text="Test",
            ref_id="",
            content_type="creature",
        )

        assert hyperlink is not None

    def test_unknown_content_type(self) -> None:
        """Test handling of unknown content types."""
        hyperlink = self.manager.create_hyperlink(
            text="Test",
            ref_id="unknown:test",
            content_type="unknown",
        )

        # Should use default style
        assert hyperlink is not None

    def test_disabled_manager(self) -> None:
        """Test behavior when manager is disabled."""
        self.manager.enable_hyperlinks(False)

        # All creation methods should return plain text
        hyperlink = self.manager.create_hyperlink(
            "Dragon", "creature:dragon", "creature"
        )
        external = self.manager.create_external_link("Link", "https://example.com")
        section = self.manager.create_section_reference("Intro", "sec:intro")

        assert hyperlink == "Dragon"
        assert external == "Link"
        assert section == "Intro"


if __name__ == "__main__":
    pytest.main([__file__])
