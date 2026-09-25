"""Tests for rendering system."""

from typing import Any

import pytest

from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine


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
            "_content",
            "base",
            "book",
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
