"""Tests for the Jinja2-based LaTeX template engine."""

from typing import Any
from unittest.mock import patch

import pytest
from jinja2 import UndefinedError
from markupsafe import Markup

from studiorum.latex_engine.core.template_engine import (
    LaTeXTemplateEngine,
    check_output,
    environment,
)


@pytest.mark.rendering
class TestLaTeXTemplateEngine:
    """Test cases for LaTeX template engine."""

    def test_init_default_config(self) -> None:
        """Test engine initialization with default configuration."""
        engine: Any = LaTeXTemplateEngine()

        # Path should now be absolute and point to the templates directory
        assert engine.templates_dir.name == "templates"
        assert str(engine.templates_dir).endswith(
            "src/studiorum/latex_engine/templates"
        )
        assert engine.env is not None

    def test_template_caching_removed(self) -> None:
        """Test that template caching has been removed."""
        engine: Any = LaTeXTemplateEngine()

        # Verify that template cache attributes no longer exist
        assert not hasattr(engine, "_template_cache")
        assert not hasattr(engine, "clear_cache")

    def test_render_template_not_found(self) -> None:
        """Test rendering with non-existent template."""
        engine: Any = LaTeXTemplateEngine()

        with pytest.raises(
            FileNotFoundError, match="Template 'nonexistent.tex.j2' not found"
        ):
            engine.render_template("nonexistent", {})

    def test_post_process_output(self) -> None:
        """Test output post-processing."""
        engine: Any = LaTeXTemplateEngine()

        # Test removing excessive blank lines
        input_text = "Line 1\n\n\n\nLine 2\n\n\n\nLine 3"
        expected = "Line 1\n\nLine 2\n\nLine 3"
        result = engine._post_process_output(input_text)
        assert result == expected

        # Test LaTeX environment spacing
        input_text = "Before\\begin{itemize}Content\\end{itemize}After"
        result = engine._post_process_output(input_text)
        assert "\\begin{itemize}" in result
        assert "\\end{itemize}" in result

    @patch("studiorum.latex_engine.core.template_engine.FileSystemLoader")
    def test_jinja_environment_configuration(self, mock_loader: Any) -> None:
        """Test Jinja2 environment configuration."""
        engine: Any = LaTeXTemplateEngine()

        # Check environment configuration
        assert engine.env.trim_blocks is True
        assert engine.env.lstrip_blocks is True
        assert engine.env.keep_trailing_newline is True

        # Check custom delimiters
        assert engine.env.block_start_string == "<@"
        assert engine.env.block_end_string == "@>"
        assert engine.env.variable_start_string == "<#"
        assert engine.env.variable_end_string == "#>"
        assert engine.env.comment_start_string == "<#--"
        assert engine.env.comment_end_string == "--#>"


@pytest.mark.rendering
class TestAutoescape:
    """Printed values are LaTeX-escaped unless they are already LaTeX."""

    def render(self, source: str, **context: Any) -> str:
        return environment().from_string(source).render(**context)

    def test_plain_text_is_escaped(self) -> None:
        assert self.render("<# t #>", t="Tom & Jerry's 50%") == "Tom \\& Jerry's 50\\%"

    def test_numbers_print_as_text(self) -> None:
        assert self.render("<# n #>", n=-3) == "-3"

    def test_safe_values_and_macros_are_not_escaped_again(self) -> None:
        source = (
            "<@ macro b(x) @>\\textbf{<# x #>}<@ endmacro @><# b(t) #> <# s | safe #>"
        )
        assert (
            self.render(source, t="A&B", s="\\emph{x}") == "\\textbf{A\\&B} \\emph{x}"
        )

    def test_the_entries_filter_returns_latex(self) -> None:
        assert self.render("<# e | entries #>", e=["{@b bold} & more"]) == (
            "\\textbf{bold} \\& more"
        )

    def test_none_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="printed None"):
            self.render("<# x #>", x=None)

    def test_undefined_is_an_error(self) -> None:
        with pytest.raises(UndefinedError):
            self.render("<# missing #>")

    def test_html_escaping_is_caught(self) -> None:
        mixed = self.render("<# m ~ t #>", m=Markup("\\x"), t=" & y")
        with pytest.raises(ValueError, match="escaped as HTML"):
            check_output(mixed)


if __name__ == "__main__":
    pytest.main([__file__])
