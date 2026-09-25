"""Security tests for LaTeX template injection vulnerabilities.

This test suite validates that all user-provided content is properly escaped
to prevent LaTeX code injection attacks.
"""

import re
import time

from hypothesis import given, strategies as st

from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine
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

    def test_spell_template_vulnerabilities(self):
        """Test current spell template for injection vulnerabilities."""

        # Create a proper mock spell with all required methods
        class MockSpell:
            def __init__(self):
                self.name = "Fireball\\newcommand{\\evil}{PWNED}"

            def get_level_text(self):
                return "3rd-level"

            def get_casting_time_text(self):
                return "1 action"

            def get_range_text(self):
                return "150 feet"

            def get_components_text(self):
                return "V, S, M"

            def get_duration_text(self):
                return "Instantaneous"

            def get_description_text(self, context=None):
                return "Test\\input{/etc/passwd}"

            def get_higher_level_text(self, context=None):
                return None

        # Test with a malicious spell name
        from studiorum.cli.context import get_services
        from studiorum.core.references.content_tracker import ContentTracker

        test_context = {
            "spell": MockSpell(),
            "level_text": "3rd-level",
            "casting_time": "1 action",
            "range_text": "150 feet",
            "components_text": "V, S, M",
            "duration_text": "Instantaneous",
            "description_text": "Test\\input{/etc/passwd}",
            "higher_level_text": None,
            "template_service": get_services().template_service,
            "content_tracker": ContentTracker(),
        }

        # This will demonstrate the vulnerability in current templates
        result = self.engine.render_template("spell_entry", test_context)

        assert "Fireball\\textbackslash{}newcommand\\{" in result
        assert "\\newcommand" not in result

    def test_creature_template_vulnerabilities(self):
        """Test current creature template for injection vulnerabilities."""

        # Create a proper mock creature with all required methods and attributes
        class MockCreature:
            def __init__(self):
                self.name = "Dragon\\def\\evil{PWNED}"
                self.ac = "19 (Natural Armor)"
                self.senses = None
                self.strength = 27
                self.dexterity = 10
                self.constitution = 19
                self.intelligence = 16
                self.wisdom = 13
                self.charisma = 21

                # Add mock source for testing source abbreviation
                class MockSource:
                    def __init__(self):
                        self.abbreviation = "TST"

                self.source = MockSource()

                # Add empty lists for optional attributes
                self.trait = []
                self.action = []
                self.legendary = []
                self.reaction = []
                self.bonus = []

            def requires_full_width_layout(self):
                return False

            def get_size_type_alignment(self):
                return "Large dragon, chaotic evil"

            def get_hp_text(self):
                return "256 (27d12 + 108)"

            def get_speed_text(self):
                return "40 ft., climb 40 ft., fly 80 ft."

            def get_formatted_saving_throws(self):
                return ""

            def get_formatted_skills(self):
                return ""

            def get_formatted_resistances(self):
                return ""

            def get_formatted_immunities(self):
                return ""

            def get_formatted_vulnerabilities(self):
                return ""

            def get_formatted_condition_immunities(self):
                return ""

            def get_formatted_senses(self):
                return ""

            def get_formatted_languages(self):
                return ""

            def get_enhanced_cr_text(self):
                return "17 (18,000 XP)"

            def get_initiative_modifier(self):
                return 0  # DEX modifier of 0 for testing

        test_context = {
            "creature": MockCreature(),
        }

        result = self.engine.render_template("creature_entry", test_context)

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
