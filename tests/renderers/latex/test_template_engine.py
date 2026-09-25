"""Tests for the Jinja2-based LaTeX template engine."""

from typing import Any
from unittest.mock import patch

import pytest

from studiorum.latex_engine.core.template_engine import (
    LaTeXTemplateEngine,  # type: ignore
)


@pytest.mark.rendering
class TestLaTeXTemplateEngine:
    """Test cases for LaTeX template engine."""

    def test_init_default_config(self) -> None:
        """Test engine initialization with default configuration."""
        engine: Any = LaTeXTemplateEngine()

        assert engine.config == {}
        assert engine.debug is False
        # Path should now be absolute and point to the templates directory
        assert engine.templates_dir.name == "templates"
        assert str(engine.templates_dir).endswith(
            "src/studiorum/latex_engine/templates"
        )
        assert engine.env is not None

    def test_latex_escape_filter(self) -> None:
        """Test LaTeX escaping filter."""
        engine: Any = LaTeXTemplateEngine()

        # The filter is renderers.escape.escape; tests/renderers/test_escape.py has the cases
        assert engine.env.filters["latex_escape"]("Hello & World") == "Hello \\& World"
        assert engine.env.filters["latex_escape"]("50% off") == "50\\% off"
        assert engine.env.filters["latex_escape"]("Cost: $5") == "Cost: \\$5"
        assert engine.env.filters["latex_escape"]("Section #1") == "Section \\#1"
        # The centralized implementation produces final LaTeX output directly
        assert engine.env.filters["latex_escape"]("x^2") == "x\\textasciicircum{}2"
        assert engine.env.filters["latex_escape"]("file_name") == "file\\_name"
        assert engine.env.filters["latex_escape"]("{hello}") == "\\{hello\\}"
        assert engine.env.filters["latex_escape"]("~home") == "\\textasciitilde{}home"
        assert (
            engine.env.filters["latex_escape"]("path\\to") == "path\\textbackslash{}to"
        )

        # Test non-string input
        assert engine.env.filters["latex_escape"](123) == "123"
        assert engine.env.filters["latex_escape"](None) == "None"

    def test_create_template_context(self) -> None:
        """Test template context creation."""
        config = {"debug": True}
        engine: Any = LaTeXTemplateEngine(config)

        context = engine.create_template_context(
            title="Test Document", author="Test Author"
        )

        assert context["config"] == config
        assert context["debug"] is True
        assert context["title"] == "Test Document"
        assert context["author"] == "Test Author"

    def test_template_exists(self) -> None:
        """Test template existence check."""
        engine: Any = LaTeXTemplateEngine()

        # Test with existing template
        base_template = engine.templates_dir / "base.tex.j2"
        if base_template.exists():
            assert engine.template_exists("base") is True
            assert engine.template_exists("base.tex.j2") is True

        # Test with non-existing template
        assert engine.template_exists("nonexistent") is False

    def test_get_template_path(self) -> None:
        """Test template path resolution."""
        engine: Any = LaTeXTemplateEngine()

        # Test without extension
        path = engine.get_template_path("base")
        assert path.name == "base.tex.j2"
        assert path.parent == engine.templates_dir

        # Test with extension
        path = engine.get_template_path("base.tex.j2")
        assert path.name == "base.tex.j2"
        assert path.parent == engine.templates_dir

    def test_list_templates(self) -> None:
        """Test template listing."""
        engine: Any = LaTeXTemplateEngine()

        templates = engine.list_templates()
        assert isinstance(templates, list)

        # Check if our created templates are in the list
        expected_templates = ["base", "book", "article", "supplement", "reference"]
        for template in expected_templates:
            if engine.template_exists(template):
                assert template in templates

    def test_validate_template_valid(self) -> None:
        """Test template validation with valid template."""
        engine: Any = LaTeXTemplateEngine()

        # Test with existing template
        if engine.template_exists("base"):
            assert engine.validate_template("base") is True

    def test_validate_template_invalid(self) -> None:
        """Test template validation with invalid template."""
        engine: Any = LaTeXTemplateEngine()

        # Test with non-existing template
        assert engine.validate_template("nonexistent") is False

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
class TestTemplateRendering:
    """Test cases for template rendering with real templates."""

    def setup_method(self) -> None:
        """Set up test fixtures."""

        self.engine = LaTeXTemplateEngine()

    def test_render_simple_template(self) -> None:
        """Test rendering a simple template."""
        # Create a temporary template for testing
        template_path = self.engine.templates_dir / "test_simple.tex.j2"
        template_content = """
% Simple test template
\\documentclass{article}
\\title{<# title | latex_escape #>}
\\author{<# author | latex_escape #>}
\\begin{document}
\\maketitle
<# content #>
\\end{document}
"""

        try:
            template_path.write_text(template_content)

            context = {
                "title": "Test & Document",
                "author": "Test Author",
                "content": "This is test content.",
            }

            result = self.engine.render_template("test_simple", context)

            # Check that template was rendered correctly
            assert "\\title{Test \\& Document}" in result
            assert "\\author{Test Author}" in result
            assert "This is test content." in result
            assert "\\documentclass{article}" in result

        finally:
            # Clean up
            if template_path.exists():
                template_path.unlink()

    def test_render_template_with_conditionals(self) -> None:
        """Test rendering template with conditional blocks."""
        template_path = self.engine.templates_dir / "test_conditionals.tex.j2"
        template_content = """
\\documentclass{article}
\\begin{document}
<@ if show_title @>
\\title{<# title | latex_escape #>}
<@ endif @>
<@ if show_author @>
\\author{<# author | latex_escape #>}
<@ endif @>
\\end{document}
"""

        try:
            template_path.write_text(template_content)

            # Test with both conditions true
            context = {
                "show_title": True,
                "show_author": True,
                "title": "Test Title",
                "author": "Test Author",
            }

            result = self.engine.render_template("test_conditionals", context)
            assert "\\title{Test Title}" in result
            assert "\\author{Test Author}" in result

            # Test with one condition false
            context["show_author"] = False
            result = self.engine.render_template("test_conditionals", context)
            assert "\\title{Test Title}" in result
            assert "\\author{Test Author}" not in result

        finally:
            # Clean up
            if template_path.exists():
                template_path.unlink()

    def test_render_template_with_loops(self) -> None:
        """Test rendering template with loop constructs."""
        template_path = self.engine.templates_dir / "test_loops.tex.j2"
        template_content = """
\\documentclass{article}
\\begin{document}
<@ for item in items @>
\\section{<# item.name | latex_escape #>}
<# item.description #>
<@ endfor @>
\\end{document}
"""

        try:
            template_path.write_text(template_content)

            context = {
                "items": [
                    {"name": "Item 1", "description": "Description 1"},
                    {"name": "Item & 2", "description": "Description 2"},
                ]
            }

            result = self.engine.render_template("test_loops", context)
            assert "\\section{Item 1}" in result
            assert "Description 1" in result
            assert "\\section{Item \\& 2}" in result
            assert "Description 2" in result

        finally:
            # Clean up
            if template_path.exists():
                template_path.unlink()

    def test_render_template_inheritance(self) -> None:
        """Test template inheritance functionality."""
        # Create base template
        base_template_path = self.engine.templates_dir / "test_base.tex.j2"
        base_template_content = """
\\documentclass{article}
\\begin{document}
<@ block header @>
Default header
<@ endblock @>
<@ block content @>
Default content
<@ endblock @>
\\end{document}
"""

        # Create child template
        child_template_path = self.engine.templates_dir / "test_child.tex.j2"
        child_template_content = """
<@ extends "test_base.tex.j2" @>
<@ block header @>
Custom header: <# title | latex_escape #>
<@ endblock @>
<@ block content @>
Custom content: <# content #>
<@ endblock @>
"""

        try:
            base_template_path.write_text(base_template_content)
            child_template_path.write_text(child_template_content)

            context = {"title": "Test Title", "content": "Test content"}

            result = self.engine.render_template("test_child", context)
            assert "Custom header: Test Title" in result
            assert "Custom content: Test content" in result
            assert "Default header" not in result
            assert "Default content" not in result

        finally:
            # Clean up
            for path in [base_template_path, child_template_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
