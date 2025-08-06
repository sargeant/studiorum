"""Tests for LaTeX tag rendering (formatting only)."""

from unittest.mock import Mock

import pytest

from dnd5e.core.models.content import ContentType, Source
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.spells import Spell
from dnd5e.core.text.tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
)
from dnd5e.renderers.latex.tag_renderer import (
    ConfigurableLaTeXTagRenderer,
    ContentTypeStyleConfig,
    LaTeXTagRenderer,
)


class TestLaTeXTagRenderer:
    """Tests for LaTeX tag rendering without semantic resolution concerns."""

    def test_content_reference_rendering_resolved(self) -> None:
        """Test rendering resolved content references."""
        renderer = LaTeXTagRenderer()

        # Create proper content instances instead of Mock objects
        test_source = Source(
            abbreviation="MM", name="Monster Manual", url="https://example.com"
        )

        creature_content = Creature(
            name="Ancient Red Dragon",
            source=test_source,
            size=["Gargantuan"],
            type="dragon",
            alignment=["chaotic", "evil"],
            hp={"average": 546},
            ac=[{"ac": 22}],
            speed={"walk": 40, "climb": 40, "fly": 80},
            str=30,
            dex=10,
            con=29,
            int=18,
            wis=15,
            cha=23,
        )

        # Test creature (should be bold)
        creature_ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Ancient Red Dragon",
            resolved_content=creature_content,
        )

        result = renderer.render(creature_ref)
        assert result == "\\textbf{Ancient Red Dragon}"

        # Create spell content
        spell_content = Spell(
            name="Fireball",
            source=test_source,
            level=3,
            school="evocation",
            time=[{"number": 1, "unit": "action"}],
            range={"type": "point", "distance": {"type": "feet", "amount": 150}},
            duration=[{"type": "instant"}],
            components={
                "v": True,
                "s": True,
                "m": "A tiny ball of bat guano and sulfur",
            },
            entries=["A bright streak flashes from your pointing finger..."],
        )

        # Test spell (should be italic)
        spell_ref = ContentReference(
            content_type=ContentType.SPELL,
            name="Fireball",
            resolved_content=spell_content,
        )

        result = renderer.render(spell_ref)
        assert result == "\\textit{Fireball}"

    def test_content_reference_rendering_unresolved(self) -> None:
        """Test rendering unresolved content references."""
        renderer = LaTeXTagRenderer()

        # Unresolved creature reference (backward compatibility: no formatting when unresolved)
        creature_ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Unknown Creature",
            resolved_content=None,
        )

        result = renderer.render(creature_ref)
        assert result == "Unknown Creature"

    def test_content_reference_with_display_text(self) -> None:
        """Test rendering content references with custom display text."""
        renderer = LaTeXTagRenderer()

        # Unresolved reference - no formatting applied (backward compatibility)
        creature_ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="strahd_von_zarovich",
            display_text="the vampire lord",
            resolved_content=None,
        )

        result = renderer.render(creature_ref)
        assert result == "the vampire lord"

    def test_content_reference_with_page_numbers(self) -> None:
        """Test rendering content references with page numbers."""
        renderer = LaTeXTagRenderer()

        # Adventure with page
        adventure_ref = ContentReference(
            content_type=ContentType.ADVENTURE,
            name="Curse of Strahd",
            page="42",
            resolved_content=None,
        )

        result = renderer.render(adventure_ref)
        assert result == "Curse of Strahd (p. 42)"

        # Book with page
        book_ref = ContentReference(
            content_type=ContentType.BOOK,
            name="Player's Handbook",
            page="123",
            resolved_content=None,
        )

        result = renderer.render(book_ref)
        assert result == "Player's Handbook, p. 123"

    def test_formatting_node_rendering(self) -> None:
        """Test rendering pure formatting nodes."""
        renderer = LaTeXTagRenderer()

        # Bold formatting
        bold_node = FormattingNode(
            format_type=FormatType.BOLD,
            content="important text",
        )
        result = renderer.render(bold_node)
        assert result == "\\textbf{important text}"

        # Italic formatting
        italic_node = FormattingNode(
            format_type=FormatType.ITALIC,
            content="emphasized text",
        )
        result = renderer.render(italic_node)
        assert result == "\\textit{emphasized text}"

        # Monospace formatting
        mono_node = FormattingNode(
            format_type=FormatType.MONOSPACE,
            content="1d6+2",
        )
        result = renderer.render(mono_node)
        assert result == "\\texttt{1d6+2}"

        # Emphasis formatting
        emph_node = FormattingNode(
            format_type=FormatType.EMPHASIS,
            content="subtle emphasis",
        )
        result = renderer.render(emph_node)
        assert result == "\\emph{subtle emphasis}"

    def test_special_tag_rendering(self) -> None:
        """Test rendering special tags."""
        renderer = LaTeXTagRenderer()

        # Hit tag
        hit_tag = SpecialTag(tag_type="hit", value="5")
        result = renderer.render(hit_tag)
        assert result == "+5"

        # DC tag
        dc_tag = SpecialTag(tag_type="dc", value="15")
        result = renderer.render(dc_tag)
        assert result == "DC 15"

        # Chance tag (percentage)
        chance_tag = SpecialTag(tag_type="chance", value="75")
        result = renderer.render(chance_tag)
        assert result == "75\\%"

        # Note tag
        note_tag = SpecialTag(tag_type="note", value="see sidebar")
        result = renderer.render(note_tag)
        assert result == "(see sidebar)"

        # Recharge tag
        recharge_tag = SpecialTag(tag_type="recharge", value="5--6")
        result = renderer.render(recharge_tag)
        assert result == "(Recharge 5--6)"

        # Coinflip tag
        coinflip_tag = SpecialTag(tag_type="coinflip", value="50")
        result = renderer.render(coinflip_tag)
        assert result == "50\\%"

    def test_special_tag_with_display_text(self) -> None:
        """Test special tags with custom display text."""
        renderer = LaTeXTagRenderer()

        dc_tag = SpecialTag(tag_type="dc", value="15", display_text="difficult save")
        result = renderer.render(dc_tag)
        assert result == "DC difficult save"

    def test_ui_tag_omission(self) -> None:
        """Test that UI-specific tags are omitted from output."""
        renderer = LaTeXTagRenderer()

        # Filter and loader tags should produce empty strings
        filter_tag = SpecialTag(tag_type="filter", value="creatures")
        result = renderer.render(filter_tag)
        assert result == ""

        loader_tag = SpecialTag(tag_type="loader", value="spells")
        result = renderer.render(loader_tag)
        assert result == ""

    def test_latex_escaping(self) -> None:
        """Test proper LaTeX character escaping."""
        renderer = LaTeXTagRenderer()

        # Test common special characters
        test_cases = [
            ("normal text", "normal text"),
            ("text & more", "text \\& more"),
            ("50% chance", "50\\% chance"),
            ("$100 cost", "\\$100 cost"),
            ("item #1", "item \\#1"),
            ("text^superscript", "text\\textasciicircum{}superscript"),
            ("file_name", "file\\_name"),
            ("{braced}", "\\{braced\\}"),
            ("~tilde", "\\textasciitilde{}tilde"),
            ("back\\slash", "back\\slash"),
        ]

        for input_text, expected in test_cases:
            result = renderer._escape_latex(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_plain_string_rendering(self) -> None:
        """Test rendering plain strings (fallback case)."""
        renderer = LaTeXTagRenderer()

        result = renderer.render("plain text")
        assert result == "plain text"

        # With special characters
        result = renderer.render("text & symbols")
        assert result == "text \\& symbols"

    def test_unknown_result_type(self) -> None:
        """Test handling of unknown result types."""
        renderer = LaTeXTagRenderer()

        # Mock unknown object
        unknown_obj = object()
        result = renderer.render(unknown_obj)  # type: ignore[arg-type]

        # Should convert to string and return
        expected = str(unknown_obj)
        assert result == expected


class TestContentTypeStyleConfig:
    """Tests for content type styling configuration."""

    def test_default_styles(self) -> None:
        """Test default content type styles."""
        config = ContentTypeStyleConfig()

        assert config.get_style(ContentType.CREATURE) == "bold"
        assert config.get_style(ContentType.CLASS) == "bold"
        assert config.get_style(ContentType.FEAT) == "bold"
        assert config.get_style(ContentType.SPELL) == "italic"
        assert config.get_style(ContentType.ITEM) == "italic"
        assert config.get_style(ContentType.BACKGROUND) == "plain"
        assert config.get_style(ContentType.RACE) == "plain"

    def test_style_customization(self) -> None:
        """Test customizing content type styles."""
        config = ContentTypeStyleConfig()

        # Change creature style to italic
        config.set_style(ContentType.CREATURE, "italic")
        assert config.get_style(ContentType.CREATURE) == "italic"

        # Invalid style should raise error
        with pytest.raises(ValueError):
            config.set_style(ContentType.SPELL, "invalid")


class TestConfigurableLaTeXTagRenderer:
    """Tests for configurable LaTeX tag renderer."""

    def test_custom_style_configuration(self) -> None:
        """Test renderer with custom style configuration."""
        config = ContentTypeStyleConfig()
        config.set_style(ContentType.CREATURE, "italic")  # Normally bold
        config.set_style(ContentType.SPELL, "plain")  # Normally italic

        renderer = ConfigurableLaTeXTagRenderer(config)

        # Creature should now render as italic
        creature_ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=None,
        )
        result = renderer.render(creature_ref)
        assert result == "\\textit{Dragon}"

        # Spell should now render as plain text
        spell_ref = ContentReference(
            content_type=ContentType.SPELL,
            name="Fireball",
            resolved_content=None,
        )
        result = renderer.render(spell_ref)
        assert result == "Fireball"

    def test_default_configuration(self) -> None:
        """Test renderer with default configuration."""
        renderer = ConfigurableLaTeXTagRenderer()

        # Should behave same as regular renderer
        creature_ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=None,
        )
        result = renderer.render(creature_ref)
        assert result == "\\textbf{Dragon}"
