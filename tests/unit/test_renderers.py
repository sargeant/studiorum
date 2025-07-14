"""Tests for rendering system."""

from pathlib import Path

import pytest

from src.core.models.content import ContentType
from src.renderers.base import RenderContext, RenderingError
from src.renderers.latex import (
    LaTeXCreatureRenderer,
    LaTeXDocumentRenderer,
    LaTeXItemRenderer,
    LaTeXSpellRenderer,
    LaTeXTemplateEngine,
)


class TestRenderContext:
    """Tests for RenderContext class."""

    def test_render_context_creation(self):
        """Test basic render context creation."""
        context = RenderContext()
        assert context.include_images is False
        assert context.include_toc is True
        assert context.include_items is True

    def test_render_context_with_options(self):
        """Test render context with custom options."""
        context = RenderContext(
            title="Test Document",
            include_images=True,
            include_toc=False,
            page_size="a4paper",
        )

        assert context.title == "Test Document"
        assert context.include_images is True
        assert context.include_toc is False
        assert context.page_size == "a4paper"

    def test_should_include_content_type(self):
        """Test content type inclusion filtering."""
        context = RenderContext(
            include_items=False, include_creatures=True, include_spells=True
        )

        assert not context.should_include_content_type("item")
        assert context.should_include_content_type("creature")
        assert context.should_include_content_type("spell")

    def test_context_copy(self):
        """Test context copying with updates."""
        original = RenderContext(title="Original", include_images=False)
        copy = original.copy(title="Updated", include_images=True)

        assert original.title == "Original"
        assert original.include_images is False
        assert copy.title == "Updated"
        assert copy.include_images is True

    def test_get_image_path(self, tmp_path):
        """Test image path resolution."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        context = RenderContext(images_dir=images_dir)

        image_path = context.get_image_path("test.png")
        assert image_path == images_dir / "test.png"

        # Test with no images_dir
        context_no_dir = RenderContext()
        assert context_no_dir.get_image_path("test.png") is None


class TestLaTeXTemplateEngine:
    """Tests for LaTeX template engine."""

    def test_template_engine_creation(self):
        """Test template engine creation."""
        engine = LaTeXTemplateEngine()
        assert engine is not None
        assert len(engine._template_cache) > 0

    def test_builtin_templates_loaded(self):
        """Test that built-in templates are loaded."""
        engine = LaTeXTemplateEngine()

        required_templates = [
            "document_header",
            "document_footer",
            "spell",
            "creature",
            "item",
        ]

        for template_name in required_templates:
            assert template_name in engine._template_cache

    def test_render_simple_template(self):
        """Test rendering template with variables."""
        engine = LaTeXTemplateEngine()

        # Add a simple test template
        engine._template_cache["test"] = "Hello {name}, you are {age} years old."

        result = engine.render_template("test", {"name": "Alice", "age": 25})
        assert result == "Hello Alice, you are 25 years old."

    def test_render_template_with_conditionals(self):
        """Test template with conditional blocks."""
        engine = LaTeXTemplateEngine()

        engine._template_cache["conditional"] = """
Name: {name}
{% if age %}
Age: {age}
{% endif %}
""".strip()

        # With age
        result1 = engine.render_template("conditional", {"name": "Alice", "age": 25})
        assert "Age: 25" in result1

        # Without age
        result2 = engine.render_template("conditional", {"name": "Bob", "age": None})
        assert "Age:" not in result2

    def test_unknown_template(self):
        """Test error handling for unknown template."""
        engine = LaTeXTemplateEngine()

        with pytest.raises(ValueError, match="Template 'unknown' not found"):
            engine.render_template("unknown", {})


class TestLaTeXSpellRenderer:
    """Tests for LaTeX spell renderer."""

    def test_spell_renderer_creation(self):
        """Test spell renderer creation."""
        renderer = LaTeXSpellRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.SPELL in renderer.supported_content_types

    def test_can_render_spell(self, sample_spell):
        """Test spell renderer can handle spells."""
        renderer = LaTeXSpellRenderer()
        assert renderer.can_render(sample_spell)

    def test_render_spell_content(self, sample_spell):
        """Test rendering spell content."""
        renderer = LaTeXSpellRenderer()
        context = RenderContext()

        result = renderer.render_content(sample_spell, context)

        assert "\\subsection{Fireball}" in result
        assert "3rd-level evocation" in result
        assert "Casting Time:" in result
        assert "Range:" in result
        assert "Components:" in result
        assert "Duration:" in result

    def test_render_spell_with_wrong_type(self, sample_creature):
        """Test error when rendering wrong content type."""
        renderer = LaTeXSpellRenderer()
        context = RenderContext()

        with pytest.raises(ValueError, match="Expected Spell, got"):
            renderer.render_content(sample_creature, context)

    def test_format_casting_time(self):
        """Test casting time formatting."""
        renderer = LaTeXSpellRenderer()

        # Single action
        time_data = [{"number": 1, "unit": "action"}]
        result = renderer._format_casting_time(time_data)
        assert result == "1 action"

        # Multiple rounds
        time_data = [{"number": 3, "unit": "round"}]
        result = renderer._format_casting_time(time_data)
        assert result == "3 rounds"

    def test_format_range(self):
        """Test range formatting."""
        renderer = LaTeXSpellRenderer()

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

    def test_format_components(self):
        """Test components formatting."""
        renderer = LaTeXSpellRenderer()

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

    def test_creature_renderer_creation(self):
        """Test creature renderer creation."""
        renderer = LaTeXCreatureRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.CREATURE in renderer.supported_content_types

    def test_can_render_creature(self, sample_creature):
        """Test creature renderer can handle creatures."""
        renderer = LaTeXCreatureRenderer()
        assert renderer.can_render(sample_creature)

    def test_render_creature_content(self, sample_creature):
        """Test rendering creature content."""
        renderer = LaTeXCreatureRenderer()
        context = RenderContext()

        result = renderer.render_content(sample_creature, context)

        assert "\\subsection{Ancient Red Dragon}" in result
        assert "Gargantuan dragon" in result
        assert "Armor Class" in result
        assert "Hit Points" in result
        assert "Speed" in result
        assert "STR" in result and "DEX" in result

    def test_format_size(self):
        """Test size formatting."""
        renderer = LaTeXCreatureRenderer()

        assert renderer._format_size(["G"]) == "Gargantuan"
        assert renderer._format_size(["M"]) == "Medium"
        assert renderer._format_size(["T"]) == "Tiny"

    def test_format_alignment(self):
        """Test alignment formatting."""
        renderer = LaTeXCreatureRenderer()

        assert renderer._format_alignment(["C", "E"]) == "chaotic evil"
        assert renderer._format_alignment(["L", "G"]) == "lawful good"
        assert renderer._format_alignment(["N"]) == "neutral"

    def test_format_ac(self):
        """Test AC formatting."""
        renderer = LaTeXCreatureRenderer()

        # AC with armor type
        ac_data = [{"ac": 18, "from": ["natural armor"]}]
        result = renderer._format_ac(ac_data)
        assert result == "18 (natural armor)"

        # AC without armor type
        ac_data = [{"ac": 12}]
        result = renderer._format_ac(ac_data)
        assert result == "12"

    def test_format_ability_score(self):
        """Test ability score formatting."""
        renderer = LaTeXCreatureRenderer()

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

    def test_item_renderer_creation(self):
        """Test item renderer creation."""
        renderer = LaTeXItemRenderer()
        assert renderer.output_format == "latex"
        assert ContentType.ITEM in renderer.supported_content_types

    def test_format_rarity(self):
        """Test rarity formatting."""
        renderer = LaTeXItemRenderer()

        assert renderer._format_rarity("uncommon") == ", uncommon"
        assert renderer._format_rarity("legendary") == ", legendary"
        assert renderer._format_rarity(None) == ""

    def test_format_properties(self):
        """Test properties formatting."""
        renderer = LaTeXItemRenderer()

        properties = ["finesse", "light", "thrown"]
        result = renderer._format_properties(properties)
        assert result == "finesse, light, thrown"

        assert renderer._format_properties(None) is None
        assert renderer._format_properties([]) is None


class TestLaTeXDocumentRenderer:
    """Tests for LaTeX document renderer."""

    def test_document_renderer_creation(self):
        """Test document renderer creation."""
        renderer = LaTeXDocumentRenderer()
        assert renderer.output_format == "latex"
        assert renderer.template_engine is not None
        assert renderer.content_registry is not None

    @pytest.mark.asyncio
    async def test_render_single_spell(self, sample_spell, tag_resolver):
        """Test rendering single spell as document."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(title="Test Spell Document", tag_resolver=tag_resolver)

        result = renderer.render_document([sample_spell], context)

        assert "\\documentclass" in result
        assert "\\title{Test Spell Document}" in result
        assert "\\subsection{Fireball}" in result
        assert "\\end{document}" in result

    @pytest.mark.asyncio
    async def test_render_multiple_content(
        self, sample_spell, sample_creature, tag_resolver
    ):
        """Test rendering multiple content items."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(
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

    def test_render_document_header(self):
        """Test document header rendering."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(
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

    def test_render_document_footer(self):
        """Test document footer rendering."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext()

        result = renderer.render_document_footer(context)
        assert result == "\\end{document}"

    @pytest.mark.asyncio
    async def test_content_filtering(self, sample_spell, sample_creature, tag_resolver):
        """Test content filtering based on context."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(
            include_spells=True, include_creatures=False, tag_resolver=tag_resolver
        )

        content_items = [sample_spell, sample_creature]
        result = renderer.render_document(content_items, context)

        # Should include spell but not creature
        assert "Fireball" in result
        assert "Ancient Red Dragon" not in result

    def test_render_to_file(self, sample_spell, tmp_path):
        """Test rendering document to file."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(title="File Test")
        output_path = tmp_path / "test.tex"

        renderer.render_document_to_file([sample_spell], output_path, context)

        assert output_path.exists()
        content = output_path.read_text()
        assert "\\documentclass" in content
        assert "Fireball" in content

    def test_render_to_file_error_handling(self, sample_spell):
        """Test error handling when rendering to file fails."""
        renderer = LaTeXDocumentRenderer()
        context = RenderContext()
        invalid_path = Path("/invalid/path/test.tex")

        with pytest.raises(RenderingError):
            renderer.render_document_to_file([sample_spell], invalid_path, context)


class TestRendererIntegration:
    """Integration tests for renderer system."""

    @pytest.mark.asyncio
    async def test_full_rendering_pipeline(self, loaded_omnidexer):
        """Test complete rendering pipeline with real data."""
        omnidexer = loaded_omnidexer

        # Get some content
        spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        creature = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")

        assert spell is not None
        assert creature is not None

        # Create renderer and context
        renderer = LaTeXDocumentRenderer()
        context = RenderContext(
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
        assert "\\subsection{Fireball}" in result
        assert "\\subsection{Ancient Red Dragon}" in result
        assert "\\end{document}" in result

        # Verify content details
        assert "3rd-level evocation" in result
        assert "Gargantuan dragon" in result

    @pytest.mark.asyncio
    async def test_error_handling_unknown_content_type(self, loaded_omnidexer):
        """Test handling of unknown content types."""
        omnidexer = loaded_omnidexer

        # Create a mock content object of unknown type
        from src.core.models.content import BaseContent, Source

        unknown_content = BaseContent(
            name="Unknown Content",
            source=Source(abbreviation="TEST", name="Test Source"),
        )

        renderer = LaTeXDocumentRenderer()
        context = RenderContext(omnidexer=omnidexer)

        # Should use fallback rendering
        result = renderer.render_content_item(unknown_content, context)

        assert "\\subsection{Unknown Content}" in result
        assert "not yet fully supported" in result
