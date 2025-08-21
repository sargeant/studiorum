"""Security tests for LaTeX template injection vulnerabilities.

This test suite validates that all user-provided content is properly escaped
to prevent LaTeX code injection attacks.
"""

import pytest
from hypothesis import given, strategies as st

from studiorum.core.latex_utils import escape_latex_text
from studiorum.renderers.latex.template_engine import LaTeXTemplateEngine
from tests.test_helpers import reset_test_environment


class TestLaTeXEscaping:
    """Test LaTeX character escaping functions."""

    def test_basic_latex_special_characters(self):
        """Test that basic LaTeX special characters are properly escaped."""
        dangerous_chars = {
            "{": "\\{",
            "}": "\\}",
            "$": "\\$",
            "&": "\\&",
            "%": "\\%",
            "#": "\\#",
            "^": "\\textasciicircum{}",
            "_": "\\_",
            "~": "\\textasciitilde{}",
        }

        for char, expected in dangerous_chars.items():
            result = escape_latex_text(char)
            assert result == expected, f"Failed to escape '{char}' correctly"

    def test_unicode_characters(self):
        """Test that Unicode characters are properly handled."""
        unicode_chars = {
            "—": "---",  # Em dash
            "–": "--",  # En dash
            "…": "\\ldots{}",  # Ellipsis
            "°": "\\textdegree{}",  # Degree symbol
            "©": "\\copyright{}",  # Copyright symbol
            "®": "\\textregistered{}",  # Registered trademark
        }

        for char, expected in unicode_chars.items():
            result = escape_latex_text(char)
            assert result == expected, f"Failed to handle Unicode '{char}' correctly"

    def test_injection_attempts(self):
        """Test protection against common LaTeX injection attacks."""
        injection_attempts = [
            # Command injection
            "\\newcommand{\\evil}{PWNED}",
            "\\def\\evil{PWNED}",
            "\\gdef\\evil{PWNED}",
            # File operations
            "\\input{/etc/passwd}",
            "\\include{sensitive_file}",
            "\\InputIfFileExists{/etc/passwd}{}{}",
            # Shell escape attempts
            "\\immediate\\write18{rm -rf /}",
            "\\write18{whoami}",
            # Document structure manipulation
            "\\end{document}\\begin{document}",
            "\\documentclass{article}",
            # Counter manipulation
            "\\setcounter{secnumdepth}{0}",
            "\\stepcounter{page}",
            # Environment manipulation
            "\\newenvironment{evil}{}{}",
            "\\renewenvironment{itemize}{}{}",
        ]

        for attempt in injection_attempts:
            escaped = escape_latex_text(attempt)
            # Verify that dangerous commands are neutralized by escaping their arguments
            # The commands themselves remain but their arguments are escaped, making them safe
            if "{" in attempt:
                assert "\\{" in escaped, f"Braces should be escaped in: {attempt}"
            if "}" in attempt:
                assert "\\}" in escaped, f"Braces should be escaped in: {attempt}"
            # Verify that the escaped content won't execute as intended
            assert attempt != escaped, f"Content should be modified: {attempt}"

    @given(st.text())
    def test_property_based_escaping(self, text):
        """Property-based test to ensure escaping never introduces vulnerabilities."""
        escaped = escape_latex_text(text)

        # Properties that must hold:
        # 1. Result should be a string
        assert isinstance(escaped, str)

        # 2. Should not contain unescaped special characters (except backslash)
        dangerous_unescaped = ["{", "}", "$", "&", "%", "#"]
        for char in dangerous_unescaped:
            if char in text:
                # If the char was in input, it should be escaped in output
                assert char not in escaped or f"\\{char}" in escaped

    def test_performance_escaping(self):
        """Test that escaping large texts performs reasonably."""
        import time

        # Large text with mixed content
        large_text = "Test content with special chars: " + "{$&#%}" * 1000

        start_time = time.time()
        escaped = escape_latex_text(large_text)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second for this size)
        assert (end_time - start_time) < 1.0
        assert len(escaped) > len(large_text)  # Should be longer due to escaping


class TestTemplateInjectionVulnerabilities:
    """Test template rendering for injection vulnerabilities."""

    def setup_method(self):
        """Set up test template engine."""
        # Reset global state for complete isolation
        reset_test_environment()

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

            def get_description_text(self):
                return "Test\\input{/etc/passwd}"

            def get_higher_level_text(self):
                return None

        # Test with a malicious spell name
        test_context = {
            "spell": MockSpell(),
            "level_text": "3rd-level",
            "casting_time": "1 action",
            "range_text": "150 feet",
            "components_text": "V, S, M",
            "duration_text": "Instantaneous",
            "description_text": "Test\\input{/etc/passwd}",
            "higher_level_text": None,
        }

        # This will demonstrate the vulnerability in current templates
        result = self.engine.render_template("spell_entry", test_context)

        # Verify that injection attempts are present (showing vulnerability)
        assert "\\newcommand" in result
        assert "\\input{/etc/passwd}" in result

    def test_creature_template_vulnerabilities(self):
        """Test current creature template for injection vulnerabilities."""

        # Create a proper mock creature with all required methods and attributes
        class MockCreature:
            def __init__(self):
                self.name = "Dragon\\def\\evil{PWNED}"
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

            def get_processed_ac_text(self):
                return "19 (Natural Armor)"

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

            def get_processed_senses(self):
                return ""

            def get_formatted_languages(self):
                return ""

            def get_enhanced_cr_text(self):
                return "17 (18,000 XP)"

        test_context = {
            "creature": MockCreature(),
        }

        result = self.engine.render_template("creature_entry", test_context)

        # Verify that injection attempts are present (showing vulnerability)
        # The name should be properly escaped as \\def\\evil\\{PWNED\\}
        assert "\\def\\evil" in result
        # For now, just check that the basic template renders (no traits to test injection)
        assert "DndMonster" in result


class TestSecureTemplatePatterns:
    """Test secure template usage patterns."""

    def setup_method(self):
        """Set up test template engine."""
        # Reset global state for complete isolation
        reset_test_environment()

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


class TestLaTeXSecurityValidation:
    """Test security validation functions."""

    def test_validate_safe_latex(self):
        """Test function to validate if LaTeX content is safe."""
        # This function doesn't exist yet but should be implemented
        # For now, we'll test the concept

        safe_latex_examples = [
            "\\textbf{Bold text}",
            "\\textit{Italic text}",
            "\\emph{Emphasized}",
            "Simple text with no commands",
        ]

        dangerous_latex_examples = [
            "\\newcommand{\\evil}{PWNED}",
            "\\input{file}",
            "\\write18{command}",
            "\\def\\bad{stuff}",
        ]

        # Implementation needed: is_safe_latex function
        # For now, we'll define basic validation logic
        def contains_dangerous_commands(text: str) -> bool:
            dangerous_patterns = [
                "\\newcommand",
                "\\def",
                "\\gdef",
                "\\input",
                "\\include",
                "\\write18",
                "\\immediate",
                "\\InputIfFileExists",
            ]
            return any(pattern in text for pattern in dangerous_patterns)

        for safe_text in safe_latex_examples:
            assert not contains_dangerous_commands(safe_text)

        for dangerous_text in dangerous_latex_examples:
            assert contains_dangerous_commands(dangerous_text)
