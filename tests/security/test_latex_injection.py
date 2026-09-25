"""Security tests for LaTeX template injection vulnerabilities.

This test suite validates that all user-provided content is properly escaped
to prevent LaTeX code injection attacks.
"""

import re
import time

from hypothesis import given, strategies as st

from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine
from studiorum.latex_engine.document import render_models
from studiorum.renderers.context import RenderingContext
from studiorum.renderers.escape import escape

_COMMAND = re.compile(r"\\(newcommand|def|input|immediate|write18|end|begin)\b")


class TestLaTeXEscaping:
    """Escaping neutralises LaTeX commands in content."""

    @given(st.text())
    def test_no_special_character_survives(self, text):
        escaped = escape(text)
        for char in "$&%#_":
            assert re.search(rf"(?<!\\){re.escape(char)}", escaped) is None
        assert "^" not in escaped
        assert _COMMAND.search(escaped) is None

    def test_injection_attempts_are_neutralised(self):
        attempts = [
            "\\newcommand{\\evil}{PWNED}",
            "\\def\\evil{PWNED}",
            "\\input{/etc/passwd}",
            "\\immediate\\write18{rm -rf /}",
            "\\end{document}\\begin{document}",
        ]
        for attempt in attempts:
            escaped = escape(attempt)
            assert escaped.startswith("\\textbackslash{}")
            assert _COMMAND.search(escaped) is None, escaped

    def test_performance_escaping(self):
        large_text = "Test content with special chars: " + "{$&#%}\\" * 1000
        start_time = time.time()
        escape(large_text)
        assert (time.time() - start_time) < 1.0


class TestTemplateInjectionVulnerabilities:
    """Test template rendering for injection vulnerabilities."""

    def setup_method(self):
        """Set up test template engine."""

        self.engine = LaTeXTemplateEngine()

    def test_template_variable_injection(self):
        """Test that template variables are vulnerable without escaping."""
        # Create a test template that doesn't use escaping
        test_template_content = """
\\section{<# title #>}
<# content #>
        """.strip()

        # Write test template
        template_path = self.engine.get_template_path("test_injection")
        template_path.write_text(test_template_content)

        try:
            # Test with malicious content
            malicious_content = {
                "title": "Test\\newcommand{\\evil}{PWNED}",
                "content": "\\input{/etc/passwd}",
            }

            result = self.engine.render_template("test_injection", malicious_content)

            # This should contain the raw injection attempts (demonstrating vulnerability)
            assert "\\newcommand" in result
            assert "\\input{/etc/passwd}" in result

        finally:
            # Clean up test template
            if template_path.exists():
                template_path.unlink()

    def test_spell_name_cannot_inject(self):
        from studiorum.core.models.spells import Spell

        spell = Spell.model_validate(
            {
                "name": "Fireball\\newcommand{\\evil}{PWNED}",
                "source": "PHB",
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
                "components": {"v": True, "s": True},
                "duration": [{"type": "instant"}],
                "entries": ["Test\\input{/etc/passwd}"],
            }
        )

        result = render_models("spell", [spell], RenderingContext())

        assert "Fireball\\textbackslash{}newcommand\\{" in result
        assert "\\newcommand" not in result
        assert "\\input" not in result

    def test_creature_name_cannot_inject(self):
        from studiorum.core.models.creatures import Creature

        creature = Creature.model_validate(
            {
                "name": "Dragon\\def\\evil{PWNED}",
                "source": "TST",
                "size": ["L"],
                "type": "dragon",
                "alignment": ["C", "E"],
                "ac": [19],
                "hp": {"average": 256, "formula": "27d12 + 108"},
                "speed": {"walk": 40},
                "str": 27,
                "dex": 10,
                "con": 19,
                "int": 16,
                "wis": 13,
                "cha": 21,
                "cr": "17",
            }
        )

        result = render_models("creature", [creature], RenderingContext())

        assert "\\def\\evil" not in result
        assert "DndMonster" in result


class TestSecureTemplatePatterns:
    """Test secure template usage patterns."""

    def setup_method(self):
        """Set up test template engine."""

        self.engine = LaTeXTemplateEngine()

    def test_secure_variable_usage(self):
        """Test that latex_escape filter prevents injection."""
        # Create a secure test template
        secure_template_content = """
\\section{<# title | latex_escape #>}
<# content | latex_escape #>
        """.strip()

        template_path = self.engine.get_template_path("test_secure")
        template_path.write_text(secure_template_content)

        try:
            # Test with malicious content
            malicious_content = {
                "title": "Test\\newcommand{\\evil}{PWNED}",
                "content": "\\input{/etc/passwd}",
            }

            result = self.engine.render_template("test_secure", malicious_content)

            # Verify that dangerous commands are neutralized by escaping their arguments
            # Commands themselves may remain but their arguments are escaped
            assert "\\{" in result and "\\}" in result, "Braces should be escaped"
            # Verify content doesn't match original (meaning it was modified)
            assert malicious_content["title"] not in result
            assert malicious_content["content"] not in result

        finally:
            # Clean up test template
            if template_path.exists():
                template_path.unlink()

    def test_safe_content_handling(self):
        """Test that trusted content can be marked as safe."""
        safe_template_content = """
\\section{<# title | latex_escape #>}
<# trusted_latex | safe #>
        """.strip()

        template_path = self.engine.get_template_path("test_safe")
        template_path.write_text(safe_template_content)

        try:
            content = {
                "title": "Test{With}Special",
                "trusted_latex": "\\textbf{This is trusted LaTeX}",
            }

            result = self.engine.render_template("test_safe", content)

            # Title should be escaped
            assert "Test\\{With\\}Special" in result
            # Trusted content should pass through
            assert "\\textbf{This is trusted LaTeX}" in result

        finally:
            if template_path.exists():
                template_path.unlink()
