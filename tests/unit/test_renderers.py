"""Tests for rendering system."""

from pathlib import Path
from typing import Any

import pytest

from dnd5e.core.models.content import ContentType  # type: ignore
from dnd5e.renderers.base import RenderContext, RenderingError  # type: ignore
from dnd5e.renderers.latex import (  # type: ignore
    LaTeXCreatureRenderer,
    LaTeXDocumentRenderer,
    LaTeXItemRenderer,
    LaTeXSpellRenderer,
    LaTeXTemplateEngine,
)


class TestRenderContext:
    """Tests for RenderContext class."""

    def test_render_context_creation(self) -> None:
        """Test basic render context creation."""
        context: Any = RenderContext()
        assert context.include_images is False
        assert context.include_toc is True
        assert context.include_items is True

    def test_render_context_with_options(self) -> None:
        """Test render context with custom options."""
        context: Any = RenderContext(
            title="Test Document",
            include_images=True,
            include_toc=False,
            page_size="a4paper",
        )

        assert context.title == "Test Document"
        assert context.include_images is True
        assert context.include_toc is False
        assert context.page_size == "a4paper"

    def test_should_include_content_type(self) -> None:
        """Test content type inclusion filtering."""
        context: Any = RenderContext(
            include_items=False, include_creatures=True, include_spells=True
        )

        assert not context.should_include_content_type("item")
        assert context.should_include_content_type("creature")
        assert context.should_include_content_type("spell")

    def test_context_copy(self) -> None:
        """Test context copying with updates."""
        original: Any = RenderContext(title="Original", include_images=False)
        copy = original.copy(title="Updated", include_images=True)

        assert original.title == "Original"
        assert original.include_images is False
        assert copy.title == "Updated"
        assert copy.include_images is True

    def test_get_image_path(self, tmp_path: Any) -> None:
        """Test image path resolution."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        context: Any = RenderContext(images_dir=images_dir)

        image_path = context.get_image_path("test.png")
        assert image_path == images_dir / "test.png"

        # Test with no images_dir
        context_no_dir: Any = RenderContext()
        assert context_no_dir.get_image_path("test.png") is None


class TestLaTeXTemplateEngine:
    """Tests for LaTeX template engine."""

    def test_template_engine_creation(self) -> None:
        """Test template engine creation."""
        engine: Any = LaTeXTemplateEngine()
        assert engine is not None
        assert engine.templates_dir is not None

    def test_builtin_templates_loaded(self) -> None:
        """Test that built-in templates are available."""
        engine: Any = LaTeXTemplateEngine()

        required_templates = [
            "spell",
            "creature",
            "item",
        ]

        for template_name in required_templates:
            assert engine.template_exists(template_name)

    def test_render_simple_template(self) -> None:
        """Test rendering template with variables."""
        engine: Any = LaTeXTemplateEngine()

        # Create a simple test template
        test_template = engine.templates_dir / "test.tex.j2"
        test_template.write_text("Hello <# name #>, you are <# age #> years old.")

        try:
            result = engine.render_template("test", {"name": "Alice", "age": 25})
            assert result == "Hello Alice, you are 25 years old."
        finally:
            test_template.unlink(missing_ok=True)

    def test_render_template_with_conditionals(self) -> None:
        """Test template with conditional blocks."""
        engine: Any = LaTeXTemplateEngine()

        # Create a conditional test template
        conditional_template = engine.templates_dir / "conditional.tex.j2"
        conditional_template.write_text("""Name: <# name #>
<@ if age @>
Age: <# age #>
<@ endif @>""")

        try:
            # With age
            result1 = engine.render_template(
                "conditional", {"name": "Alice", "age": 25}
            )
            assert "Age: 25" in result1

            # Without age
            result2 = engine.render_template(
                "conditional", {"name": "Bob", "age": None}
            )
            assert "Age:" not in result2
        finally:
            conditional_template.unlink(missing_ok=True)

    def test_unknown_template(self) -> None:
        """Test error handling for unknown template."""
        engine: Any = LaTeXTemplateEngine()

        with pytest.raises(
            FileNotFoundError, match="Template 'unknown.tex.j2' not found"
        ):
            engine.render_template("unknown", {})


class TestLaTeXSpellRenderer:
    """Tests for LaTeX spell renderer."""

    def test_spell_renderer_creation(self) -> None:
        """Test spell renderer creation."""
        renderer: Any = LaTeXSpellRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.SPELL in renderer.supported_content_types

    def test_can_render_spell(self, sample_spell: Any) -> None:
        """Test spell renderer can handle spells."""
        renderer: Any = LaTeXSpellRenderer()
        assert renderer.can_render(sample_spell)

    def test_render_spell_content(self, sample_spell: Any) -> None:
        """Test rendering spell content."""
        renderer: Any = LaTeXSpellRenderer()
        context: Any = RenderContext()

        result = renderer.render_content(sample_spell, context)

        # Enhanced renderer uses DND template
        assert "\\DndSpellHeader" in result
        assert "Fireball" in result
        assert "3rd-level evocation" in result
        assert "1 action" in result
        assert "150 feet" in result
        assert "V, S, M" in result
        assert "Instantaneous" in result

    def test_render_spell_with_wrong_type(self, sample_creature: Any) -> None:
        """Test error when rendering wrong content type."""
        renderer: Any = LaTeXSpellRenderer()
        context: Any = RenderContext()

        with pytest.raises(ValueError, match="Expected Spell, got"):
            renderer.render_content(sample_creature, context)

    def test_format_casting_time(self) -> None:
        """Test casting time formatting."""
        renderer: Any = LaTeXSpellRenderer()

        # Single action
        time_data = [{"number": 1, "unit": "action"}]
        result = renderer._format_casting_time(time_data)
        assert result == "1 action"

        # Multiple rounds
        time_data = [{"number": 3, "unit": "round"}]
        result = renderer._format_casting_time(time_data)
        assert result == "3 rounds"

    def test_format_range(self) -> None:
        """Test range formatting."""
        renderer: Any = LaTeXSpellRenderer()

        # Point range
        range_data = {"type": "point", "distance": {"type": "feet", "amount": 150}}
        result = renderer._format_range(range_data)
        assert result == "150 feet"

        # Self range
        range_data = {"type": "point", "distance": {"type": "self"}}
        result = renderer._format_range(range_data)
        assert result == "Self"

        # Touch range
        range_data = {"type": "point", "distance": {"type": "touch"}}
        result = renderer._format_range(range_data)
        assert result == "Touch"

    def test_format_components(self) -> None:
        """Test components formatting."""
        renderer: Any = LaTeXSpellRenderer()

        # VSM components
        components = {"v": True, "s": True, "m": "a tiny ball of bat guano and sulfur"}
        result = renderer._format_components(components)
        assert "V, S, M" in result
        assert "bat guano and sulfur" in result

        # Only verbal
        components = {"v": True}
        result = renderer._format_components(components)
        assert result == "V"


class TestLaTeXCreatureRenderer:
    """Tests for LaTeX creature renderer."""

    def test_creature_renderer_creation(self) -> None:
        """Test creature renderer creation."""
        renderer: Any = LaTeXCreatureRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.CREATURE in renderer.supported_content_types

    def test_can_render_creature(self, sample_creature: Any) -> None:
        """Test creature renderer can handle creatures."""
        renderer: Any = LaTeXCreatureRenderer()
        assert renderer.can_render(sample_creature)

    def test_render_creature_content(self, sample_creature: Any) -> None:
        """Test rendering creature content."""
        renderer: Any = LaTeXCreatureRenderer()
        context: Any = RenderContext()

        result = renderer.render_content(sample_creature, context)

        # Enhanced renderer uses DND template
        assert "\\begin{DndMonster}" in result
        assert "Ancient Red Dragon" in result
        assert "Gargantuan dragon" in result
        assert (
            "22 (natural armor)" in result
        )  # AC format in DND template (corrected value)
        assert "546" in result  # HP
        assert "40 ft." in result  # Speed

    def test_format_size(self) -> None:
        """Test size formatting."""
        renderer: Any = LaTeXCreatureRenderer()

        assert renderer._format_size(["G"]) == "Gargantuan"
        assert renderer._format_size(["M"]) == "Medium"
        assert renderer._format_size(["T"]) == "Tiny"

    def test_format_alignment(self) -> None:
        """Test alignment formatting."""
        renderer: Any = LaTeXCreatureRenderer()

        assert renderer._format_alignment(["C", "E"]) == "chaotic evil"
        assert renderer._format_alignment(["L", "G"]) == "lawful good"
        assert renderer._format_alignment(["N"]) == "neutral"

    def test_format_ac(self) -> None:
        """Test AC formatting."""
        renderer: Any = LaTeXCreatureRenderer()

        # AC with armor type
        ac_data = [{"ac": 18, "from": ["natural armor"]}]
        result = renderer._format_ac(ac_data)
        assert result == "18 (natural armor)"

        # AC without armor type
        ac_data = [{"ac": 12}]
        result = renderer._format_ac(ac_data)
        assert result == "12"

    def test_format_ability_score(self) -> None:
        """Test ability score formatting."""
        renderer: Any = LaTeXCreatureRenderer()

        # High score (positive modifier)
        result = renderer._format_ability_score(16)
        assert result == "16 (+3)"

        # Low score (negative modifier)
        result = renderer._format_ability_score(8)
        assert result == "8 (-1)"

        # Average score (zero modifier)
        result = renderer._format_ability_score(10)
        assert result == "10 (+0)"


class TestLaTeXItemRenderer:
    """Tests for LaTeX item renderer."""

    def test_item_renderer_creation(self) -> None:
        """Test item renderer creation."""
        renderer: Any = LaTeXItemRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.ITEM in renderer.supported_content_types

    def test_format_rarity(self) -> None:
        """Test rarity formatting."""
        renderer: Any = LaTeXItemRenderer()

        assert renderer._format_rarity("uncommon") == ", uncommon"
        assert renderer._format_rarity("legendary") == ", legendary"
        assert renderer._format_rarity(None) == ""

    def test_format_properties(self) -> None:
        """Test properties formatting."""
        renderer: Any = LaTeXItemRenderer()

        properties = ["finesse", "light", "thrown"]
        result = renderer._format_properties(properties)
        assert result == "finesse, light, thrown"

        assert renderer._format_properties(None) is None
        assert renderer._format_properties([]) is None


class TestLaTeXDocumentRenderer:
    """Tests for LaTeX document renderer."""

    def test_document_renderer_creation(self) -> None:
        """Test document renderer creation."""
        renderer: Any = LaTeXDocumentRenderer()
        assert renderer.output_format == "latex"
        assert renderer.template_engine is not None
        assert renderer.entry_registry is not None

    @pytest.mark.asyncio
    async def test_render_single_spell(
        self, sample_spell: Any, tag_resolver: Any
    ) -> None:
        """Test rendering single spell as document."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Test Spell Document", tag_resolver=tag_resolver
        )

        result = renderer.render_document([sample_spell], context)

        assert "\\documentclass" in result
        assert "\\title{Test Spell Document}" in result
        assert (
            "\\DndSpellHeader" in result or "Fireball" in result
        )  # DND template format
        assert "\\end{document}" in result

    @pytest.mark.asyncio
    async def test_render_multiple_content(
        self, sample_spell: Any, sample_creature: Any, tag_resolver: Any
    ) -> None:
        """Test rendering multiple content items."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Mixed Content Document",
            include_toc=True,
            tag_resolver=tag_resolver,
        )

        content_items = [sample_spell, sample_creature]
        result = renderer.render_document(content_items, context)

        assert "\\documentclass" in result
        assert "\\tableofcontents" in result
        assert "Fireball" in result
        assert "Ancient Red Dragon" in result
        assert "\\end{document}" in result

    def test_render_document_header(self) -> None:
        """Test document header rendering."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Test Document",
            author="Test Author",
            page_size="a4paper",
            font_size="12pt",
        )

        result = renderer.render_document_header(context)

        assert "\\documentclass[12pt,a4paper]{book}" in result
        assert "\\title{Test Document}" in result
        assert "\\author{Test Author}" in result
        assert "\\begin{document}" in result

    def test_render_document_footer(self) -> None:
        """Test document footer rendering."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext()

        result = renderer.render_document_footer(context)
        assert result == "\\end{document}"

    @pytest.mark.asyncio
    async def test_content_filtering(
        self, sample_spell: Any, sample_creature: Any, tag_resolver: Any
    ) -> None:
        """Test content filtering based on context."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            include_spells=True, include_creatures=False, tag_resolver=tag_resolver
        )

        content_items = [sample_spell, sample_creature]
        result = renderer.render_document(content_items, context)

        # Should include spell but not creature
        assert "Fireball" in result
        assert "Ancient Red Dragon" not in result

    def test_render_to_file(self, sample_spell: Any, tmp_path: Any) -> None:
        """Test rendering document to file."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(title="File Test")
        output_path = tmp_path / "test.tex"

        renderer.render_document_to_file([sample_spell], output_path, context)

        assert output_path.exists()
        content = output_path.read_text()
        assert "\\documentclass" in content
        assert "Fireball" in content

    def test_render_to_file_error_handling(self, sample_spell: Any) -> None:
        """Test error handling when rendering to file fails."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext()
        invalid_path: Any = Path("/invalid/path/test.tex")

        with pytest.raises(RenderingError):
            renderer.render_document_to_file([sample_spell], invalid_path, context)


class TestRendererIntegration:
    """Integration tests for renderer system."""

    @pytest.mark.asyncio
    async def test_full_rendering_pipeline(self, loaded_omnidexer: Any) -> None:
        """Test complete rendering pipeline with real data."""
        omnidexer = loaded_omnidexer

        # Get some content
        spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        creature = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")

        assert spell is not None
        assert creature is not None

        # Create renderer and context
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Integration Test Document",
            include_toc=True,
            include_index=False,
            omnidexer=omnidexer,
        )

        # Render document
        result = renderer.render_document([spell, creature], context)

        # Verify structure
        assert "\\documentclass" in result
        assert "\\title{Integration Test Document}" in result
        assert "\\tableofcontents" in result
        # Enhanced renderers use DND templates
        assert "Fireball" in result
        assert "Ancient Red Dragon" in result
        assert "\\end{document}" in result

        # Verify content details
        assert "3rd-level evocation" in result
        assert "G dragon" in result

    @pytest.mark.asyncio
    async def test_error_handling_unknown_content_type(
        self, loaded_omnidexer: Any
    ) -> None:
        """Test handling of unknown content types."""
        omnidexer = loaded_omnidexer

        # Create a mock content object of unknown type
        from dnd5e.core.models.content import BaseContent, Source  # type: ignore

        unknown_content: Any = BaseContent(
            name="Unknown Content",
            source=Source(abbreviation="TEST", name="Test Source"),
        )

        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(omnidexer=omnidexer)

        # Should use fallback rendering
        result = renderer.render_content_item(unknown_content, context)

        assert "\\subsection{Unknown Content}" in result
        assert "not yet fully supported" in result
