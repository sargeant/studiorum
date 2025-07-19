"""Tests for LaTeX-enhanced tag renderer."""

import pytest

from dnd5e.core.indexer.cross_reference_manager import CrossReferenceManager
from dnd5e.core.indexer.hyperlink_manager import HyperlinkManager
from dnd5e.core.indexer.latex_tag_renderer import (
    LaTeXContentTracker,
    LaTeXRendererContext,
    LaTeXTagRenderer,
)
from dnd5e.core.indexer.tag_ast import TagNode


class MockTagNode:
    """Mock tag node for testing."""

    def __init__(self, tag_type: str, name: str, source: str | None = None):
        self.tag_type = tag_type
        self.name = name
        self.source = source
        self.children = []


class TestLaTeXRendererContext:
    """Test LaTeX renderer context."""

    def test_context_initialization(self):
        """Test context initialization."""
        renderer = LaTeXTagRenderer()
        cross_ref_mgr = CrossReferenceManager()
        hyperlink_mgr = HyperlinkManager()

        context = LaTeXRendererContext(
            renderer=renderer,
            cross_ref_manager=cross_ref_mgr,
            hyperlink_manager=hyperlink_mgr,
        )

        assert context.renderer is renderer
        assert context.cross_ref_manager is cross_ref_mgr
        assert context.hyperlink_manager is hyperlink_mgr
        assert context.latex_mode is True

    def test_context_without_managers(self):
        """Test context without optional managers."""
        renderer = LaTeXTagRenderer()

        context = LaTeXRendererContext(renderer)

        assert context.renderer is renderer
        assert context.cross_ref_manager is None
        assert context.hyperlink_manager is None
        assert context.latex_mode is True


class TestLaTeXTagRenderer:
    """Test LaTeX tag renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cross_ref_mgr = CrossReferenceManager()
        self.hyperlink_mgr = HyperlinkManager()
        self.renderer = LaTeXTagRenderer(
            cross_ref_manager=self.cross_ref_mgr,
            hyperlink_manager=self.hyperlink_mgr,
        )

    def test_renderer_initialization(self):
        """Test renderer initialization."""
        assert self.renderer.cross_ref_manager is self.cross_ref_mgr
        assert self.renderer.hyperlink_manager is self.hyperlink_mgr
        assert isinstance(self.renderer.latex_content_tracker, LaTeXContentTracker)

    def test_is_content_reference_tag(self):
        """Test content reference tag detection."""
        creature_node = MockTagNode("creature", "Dragon")
        spell_node = MockTagNode("spell", "Fireball")
        bold_node = MockTagNode("bold", "text")

        assert self.renderer._is_content_reference_tag(creature_node)
        assert self.renderer._is_content_reference_tag(spell_node)
        assert not self.renderer._is_content_reference_tag(bold_node)

    def test_generate_reference_id(self):
        """Test reference ID generation."""
        node = MockTagNode("creature", "Ancient Red Dragon")
        ref_id = self.renderer._generate_reference_id(node)

        assert ref_id == "creature:ancient-red-dragon"

    def test_sanitize_for_label(self):
        """Test label sanitization."""
        test_cases = [
            ("Ancient Red Dragon", "ancient-red-dragon"),
            ("Sphere of Annihilation", "sphere-of-annihilation"),
            ("Bag of Holding", "bag-of-holding"),
            ("AC (Armor Class)", "ac-armor-class"),
            ("", "unnamed"),
            ("123", "123"),
            ("Test--Multiple---Hyphens", "test-multiple-hyphens"),
        ]

        for input_text, expected in test_cases:
            result = self.renderer._sanitize_for_label(input_text)
            assert result == expected

    def test_enhance_with_cross_reference(self):
        """Test cross-reference enhancement."""
        context = LaTeXRendererContext(
            self.renderer,
            cross_ref_manager=self.cross_ref_mgr,
            hyperlink_manager=self.hyperlink_mgr,
        )

        node = MockTagNode("creature", "Dragon")
        base_text = "\\textbf{Dragon}"

        result = self.renderer._enhance_with_cross_reference(node, base_text, context)

        # Should contain hyperref and pageref
        assert "\\hyperref[creature:dragon]" in result
        assert "\\pageref{creature:dragon}" in result
        assert "\\textbf{Dragon}" in result

    def test_cross_reference_database(self):
        """Test cross-reference database access."""
        context = LaTeXRendererContext(
            self.renderer,
            cross_ref_manager=self.cross_ref_mgr,
            hyperlink_manager=self.hyperlink_mgr,
        )

        node = MockTagNode("spell", "Fireball")
        base_text = "\\textit{Fireball}"

        self.renderer._enhance_with_cross_reference(node, base_text, context)

        database = self.renderer.get_cross_reference_database()
        assert "spell:fireball" in database
        assert database["spell:fireball"].name == "Fireball"
        assert database["spell:fireball"].content_type == "spell"

    def test_enable_disable_hyperlinks(self):
        """Test hyperlink enable/disable functionality."""
        self.renderer.enable_hyperlinks(False)
        assert not self.renderer.hyperlink_manager.enabled

        self.renderer.enable_hyperlinks(True)
        assert self.renderer.hyperlink_manager.enabled

    def test_set_cross_reference_format(self):
        """Test cross-reference format setting."""
        self.renderer.set_cross_reference_format("section")
        assert self.renderer.cross_ref_manager.reference_format == "section"

        with pytest.raises(ValueError):
            self.renderer.set_cross_reference_format("invalid")


class TestLaTeXTagRendererIntegration:
    """Integration tests for LaTeX tag renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXTagRenderer()

    def test_render_without_enhancements(self):
        """Test rendering without LaTeX enhancements."""
        # This would require actual tag parsing, which needs the full system
        # For now, test that the renderer initializes correctly
        assert self.renderer is not None
        assert hasattr(self.renderer, "cross_ref_manager")
        assert hasattr(self.renderer, "hyperlink_manager")

    @pytest.mark.integration
    def test_render_with_content_reference(self):
        """Test rendering content reference with enhancements."""
        # This would test the full rendering pipeline
        # Requires AST nodes and proper context
        pass

    @pytest.mark.integration
    def test_multiple_references_same_content(self):
        """Test multiple references to same content."""
        # Should increment usage count and maintain same ref_id
        pass

    @pytest.mark.integration
    def test_complex_document_rendering(self):
        """Test rendering complex document with many references."""
        # Test performance and correctness with large documents
        pass


class TestLaTeXTagRendererErrorHandling:
    """Test error handling in LaTeX tag renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXTagRenderer()

    def test_missing_node_attributes(self):
        """Test handling of nodes with missing attributes."""

        class IncompleteNode:
            tag_type = "creature"
            # Missing name attribute

        node = IncompleteNode()
        ref_id = self.renderer._generate_reference_id(node)

        # Should handle gracefully with fallback
        assert ref_id == "creature:unnamed"

    def test_invalid_content_type(self):
        """Test handling of invalid content types."""
        node = MockTagNode("invalid_type", "Test")

        # Should not be treated as content reference
        assert not self.renderer._is_content_reference_tag(node)

    def test_none_values(self):
        """Test handling of None values."""
        node = MockTagNode("creature", None)
        ref_id = self.renderer._generate_reference_id(node)

        # Should handle None name gracefully
        assert "creature:" in ref_id


if __name__ == "__main__":
    pytest.main([__file__])
