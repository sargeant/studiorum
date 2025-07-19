"""Tests for LaTeX error parsing."""

from pathlib import Path

import pytest

from dnd5e.renderers.latex.error_parser import (
    ErrorCategory,
    ErrorSeverity,
    LaTeXError,
    LaTeXErrorParser,
)


class TestErrorSeverity:
    """Tests for error severity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.FATAL.value == "fatal"


class TestErrorCategory:
    """Tests for error category enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert ErrorCategory.MISSING_PACKAGE.value == "missing_package"
        assert ErrorCategory.MISSING_FILE.value == "missing_file"
        assert ErrorCategory.SYNTAX_ERROR.value == "syntax_error"
        assert ErrorCategory.FONT_ERROR.value == "font_error"
        assert ErrorCategory.TEMPLATE_ERROR.value == "template_error"
        assert ErrorCategory.COMPILATION_ERROR.value == "compilation_error"
        assert ErrorCategory.TIMEOUT_ERROR.value == "timeout_error"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestLaTeXError:
    """Tests for LaTeX error representation."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYNTAX_ERROR,
            message="Undefined control sequence",
        )

        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.SYNTAX_ERROR
        assert error.message == "Undefined control sequence"
        assert error.file_path is None
        assert error.line_number is None
        assert error.context is None
        assert error.suggestion is None

    def test_error_with_location(self):
        """Test error with file and line information."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYNTAX_ERROR,
            message="Missing brace",
            file_path="document.tex",
            line_number=42,
        )

        assert error.file_path == "document.tex"
        assert error.line_number == 42

    def test_error_with_context_and_suggestion(self):
        """Test error with context and suggestion."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.MISSING_PACKAGE,
            message="Package not found",
            context="\\usepackage{nonexistent}",
            suggestion="Install the package or check the name",
        )

        assert error.context == "\\usepackage{nonexistent}"
        assert error.suggestion == "Install the package or check the name"

    def test_str_representation_basic(self):
        """Test string representation of basic error."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYNTAX_ERROR,
            message="Undefined control sequence",
        )

        str_repr = str(error)
        assert "ERROR: Undefined control sequence" in str_repr

    def test_str_representation_with_location(self):
        """Test string representation with location."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYNTAX_ERROR,
            message="Missing brace",
            file_path="document.tex",
            line_number=42,
        )

        str_repr = str(error)
        assert "ERROR: Missing brace" in str_repr
        assert "at document.tex:42" in str_repr

    def test_str_representation_with_file_only(self):
        """Test string representation with file but no line."""
        error = LaTeXError(
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.UNKNOWN,
            message="Some warning",
            file_path="document.tex",
        )

        str_repr = str(error)
        assert "WARNING: Some warning" in str_repr
        assert "in document.tex" in str_repr

    def test_str_representation_full(self):
        """Test string representation with all fields."""
        error = LaTeXError(
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.MISSING_PACKAGE,
            message="Package not found",
            file_path="document.tex",
            line_number=10,
            context="\\usepackage{missing}",
            suggestion="Install the missing package",
        )

        str_repr = str(error)
        assert "FATAL: Package not found" in str_repr
        assert "at document.tex:10" in str_repr
        assert "Context: \\usepackage{missing}" in str_repr
        assert "Suggestion: Install the missing package" in str_repr


class TestLaTeXErrorParser:
    """Tests for LaTeX error parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LaTeXErrorParser()

    def test_parser_initialization(self):
        """Test parser initialization."""
        assert self.parser._error_patterns is not None
        assert self.parser._suggestion_rules is not None
        assert len(self.parser._error_patterns) > 0
        assert len(self.parser._suggestion_rules) > 0

    def test_parse_missing_file_error(self):
        """Test parsing missing file error."""
        log_content = "! LaTeX Error: File `missing.sty' not found."

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.MISSING_FILE
        assert "missing.sty" in error.message
        assert error.suggestion is not None

    def test_parse_package_error(self):
        """Test parsing package error."""
        log_content = (
            "! Package fontspec Error: The font 'missing-font' cannot be found."
        )

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.MISSING_PACKAGE
        assert "fontspec" in error.message

    def test_parse_undefined_control_sequence(self):
        """Test parsing undefined control sequence error."""
        log_content = "! Undefined control sequence."

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.SYNTAX_ERROR
        assert "Undefined command" in error.message

    def test_parse_font_error(self):
        """Test parsing font error."""
        log_content = (
            "! Font TU/cmr/m/n/10=file not loadable: Metric (TFM) file not found."
        )

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.FONT_ERROR
        assert "Font loading error" in error.message

    def test_parse_fontspec_error(self):
        """Test parsing fontspec error."""
        log_content = "fontspec error: 'Font not found'"

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.FONT_ERROR
        assert "Fontspec error" in error.message

    def test_parse_dnd_package_error(self):
        """Test parsing DND package error."""
        log_content = "! Package dnd Error: Invalid option for dndbook class"

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.TEMPLATE_ERROR
        assert "DND template error" in error.message

    def test_parse_warning(self):
        """Test parsing LaTeX warning."""
        log_content = "LaTeX Warning: Reference `undefined-ref' on page 1 undefined"

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 1

        error = errors[0]
        assert error.severity == ErrorSeverity.WARNING
        assert error.category == ErrorCategory.UNKNOWN
        assert "Warning" in error.message

    def test_parse_multiple_errors(self):
        """Test parsing multiple errors."""
        log_content = """! LaTeX Error: File `missing.sty' not found.
! Undefined control sequence.
LaTeX Warning: Reference undefined"""

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 3

        # Check error types
        categories = [error.category for error in errors]
        assert ErrorCategory.MISSING_FILE in categories
        assert ErrorCategory.SYNTAX_ERROR in categories
        assert ErrorCategory.UNKNOWN in categories

    def test_parse_empty_log(self):
        """Test parsing empty log."""
        errors = self.parser.parse_log("")
        assert len(errors) == 0

    def test_parse_no_errors(self):
        """Test parsing log with no errors."""
        log_content = "This is pdfTeX, Version 3.14159265-2.6-1.40.21\nOutput written on document.pdf (1 page)."

        errors = self.parser.parse_log(log_content)
        assert len(errors) == 0

    def test_analyze_compilation_failure_timeout(self):
        """Test analyzing compilation failure due to timeout."""
        errors = self.parser.analyze_compilation_failure(
            return_code=1, stdout="", stderr="", timeout_occurred=True
        )

        assert len(errors) == 1
        error = errors[0]
        assert error.severity == ErrorSeverity.FATAL
        assert error.category == ErrorCategory.TIMEOUT_ERROR
        assert "timed out" in error.message

    def test_analyze_compilation_failure_with_stderr(self):
        """Test analyzing compilation failure with stderr."""
        stderr = "! LaTeX Error: File not found"

        errors = self.parser.analyze_compilation_failure(
            return_code=1, stdout="", stderr=stderr, timeout_occurred=False
        )

        assert len(errors) >= 1
        # Should parse the error from stderr
        error_messages = [error.message for error in errors]
        assert any("File not found" in msg for msg in error_messages)

    def test_analyze_compilation_failure_generic(self):
        """Test analyzing generic compilation failure."""
        errors = self.parser.analyze_compilation_failure(
            return_code=2, stdout="", stderr="", timeout_occurred=False
        )

        assert len(errors) == 1
        error = errors[0]
        assert error.severity == ErrorSeverity.FATAL
        assert error.category == ErrorCategory.COMPILATION_ERROR
        assert "exit code 2" in error.message

    def test_analyze_compilation_success(self):
        """Test analyzing successful compilation."""
        errors = self.parser.analyze_compilation_failure(
            return_code=0,
            stdout="Output written on document.pdf",
            stderr="",
            timeout_occurred=False,
        )

        # Should not generate errors for successful compilation
        assert len(errors) == 0

    def test_get_error_summary_empty(self):
        """Test error summary for empty error list."""
        summary = self.parser.get_error_summary([])
        assert summary == "No errors found."

    def test_get_error_summary_single_error(self):
        """Test error summary for single error."""
        error = LaTeXError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYNTAX_ERROR,
            message="Test error",
            suggestion="Fix the syntax",
        )

        summary = self.parser.get_error_summary([error])
        assert "1 error(s)" in summary
        assert "Test error" in summary
        assert "Fix the syntax" in summary

    def test_get_error_summary_multiple_severities(self):
        """Test error summary with multiple severities."""
        errors = [
            LaTeXError(
                severity=ErrorSeverity.FATAL,
                category=ErrorCategory.MISSING_PACKAGE,
                message="Fatal error",
            ),
            LaTeXError(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.SYNTAX_ERROR,
                message="Syntax error",
            ),
            LaTeXError(
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.UNKNOWN,
                message="Warning message",
            ),
        ]

        summary = self.parser.get_error_summary(errors)
        assert "1 fatal error(s)" in summary
        assert "1 error(s)" in summary
        assert "1 warning(s)" in summary
        assert "Fatal error" in summary
        assert "Syntax error" in summary

    def test_get_error_summary_limits_critical_errors(self):
        """Test that error summary limits critical errors shown."""
        # Create 5 errors
        errors = [
            LaTeXError(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.SYNTAX_ERROR,
                message=f"Error {i}",
            )
            for i in range(5)
        ]

        summary = self.parser.get_error_summary(errors)

        # Should show only first 3 critical errors
        assert "Error 0" in summary
        assert "Error 1" in summary
        assert "Error 2" in summary
        # Should not show all 5
        assert summary.count("Error") <= 3

    def test_suggestions_for_categories(self):
        """Test that suggestions are provided for different categories."""
        parser = LaTeXErrorParser()

        # Test each category has suggestions
        categories_with_suggestions = [
            ErrorCategory.MISSING_PACKAGE,
            ErrorCategory.MISSING_FILE,
            ErrorCategory.FONT_ERROR,
            ErrorCategory.TEMPLATE_ERROR,
            ErrorCategory.SYNTAX_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
        ]

        for category in categories_with_suggestions:
            suggestions = parser._suggestion_rules.get(category, [])
            assert len(suggestions) > 0, f"No suggestions found for {category}"
