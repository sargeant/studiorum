"""LaTeX error parsing and analysis utilities."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ErrorSeverity(Enum):
    """Severity levels for LaTeX errors and warnings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Categories of LaTeX errors for better user guidance."""

    MISSING_PACKAGE = "missing_package"
    MISSING_FILE = "missing_file"
    SYNTAX_ERROR = "syntax_error"
    FONT_ERROR = "font_error"
    TEMPLATE_ERROR = "template_error"
    COMPILATION_ERROR = "compilation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN = "unknown"


@dataclass
class LaTeXError:
    """Represents a single LaTeX error or warning."""

    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    file_path: str | None = None
    line_number: int | None = None
    context: str | None = None
    suggestion: str | None = None

    def __str__(self) -> str:
        """Human-readable error description."""
        parts = [f"{self.severity.value.upper()}: {self.message}"]

        if self.file_path and self.line_number:
            parts.append(f"  at {self.file_path}:{self.line_number}")
        elif self.file_path:
            parts.append(f"  in {self.file_path}")

        if self.context:
            parts.append(f"  Context: {self.context}")

        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")

        return "\n".join(parts)


class LaTeXErrorParser:
    """Parses LaTeX compilation logs to extract errors and warnings."""

    def __init__(self) -> None:
        """Initialize the error parser."""
        self._error_patterns = self._build_error_patterns()
        self._suggestion_rules = self._build_suggestion_rules()

    def parse_log(
        self, log_content: str, log_file_path: Path | None = None
    ) -> list[LaTeXError]:
        """Parse LaTeX log content and extract errors.

        Args:
            log_content: Content of the LaTeX log file
            log_file_path: Path to the log file (for context)

        Returns:
            List of parsed errors and warnings
        """
        errors = []
        lines = log_content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Try to match each error pattern
            for pattern_info in self._error_patterns:
                match = pattern_info["pattern"].match(line)
                if match:
                    error = self._extract_error_from_match(
                        match, pattern_info, lines, i
                    )
                    if error:
                        errors.append(error)
                    break

            i += 1

        # Add suggestions to errors
        for error in errors:
            error.suggestion = self._get_suggestion(error)

        return errors

    def analyze_compilation_failure(
        self, return_code: int, stdout: str, stderr: str, timeout_occurred: bool = False
    ) -> list[LaTeXError]:
        """Analyze compilation failure and generate error reports.

        Args:
            return_code: Process return code
            stdout: Standard output from compilation
            stderr: Standard error from compilation
            timeout_occurred: Whether compilation timed out

        Returns:
            List of errors explaining the failure
        """
        errors = []

        if timeout_occurred:
            errors.append(
                LaTeXError(
                    severity=ErrorSeverity.FATAL,
                    category=ErrorCategory.TIMEOUT_ERROR,
                    message="Compilation timed out",
                    suggestion="Document may be too large or complex. Try reducing content or using draft mode.",
                )
            )
            return errors

        # Parse stderr for immediate errors
        if stderr:
            errors.extend(self.parse_log(stderr))

        # Parse stdout for detailed log information
        if stdout:
            errors.extend(self.parse_log(stdout))

        # If no specific errors found but compilation failed
        if not errors and return_code != 0:
            errors.append(
                LaTeXError(
                    severity=ErrorSeverity.FATAL,
                    category=ErrorCategory.COMPILATION_ERROR,
                    message=f"Compilation failed with exit code {return_code}",
                    suggestion="Check the full compilation log for details.",
                )
            )

        return errors

    def _build_error_patterns(self) -> list[dict]:
        """Build regex patterns for matching LaTeX errors.

        Returns:
            List of pattern information dictionaries
        """
        return [
            {
                "pattern": re.compile(r"! LaTeX Error: File `(.+?)' not found"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.MISSING_FILE,
                "extract": lambda m: f"Missing file: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"! Package dnd Error: (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.TEMPLATE_ERROR,
                "extract": lambda m: f"DND template error: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"! Package (\w+) Error: (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.MISSING_PACKAGE,
                "extract": lambda m: f"Package {m.group(1)} error: {m.group(2)}",
            },
            {
                "pattern": re.compile(r"! Undefined control sequence"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.SYNTAX_ERROR,
                "extract": lambda m: "Undefined command or macro",
            },
            {
                "pattern": re.compile(r"! Font .* not loadable: (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.FONT_ERROR,
                "extract": lambda m: f"Font loading error: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"fontspec error: (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.FONT_ERROR,
                "extract": lambda m: f"Fontspec error: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"LaTeX Warning: (.+)"),
                "severity": ErrorSeverity.WARNING,
                "category": ErrorCategory.UNKNOWN,
                "extract": lambda m: f"Warning: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"! (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.SYNTAX_ERROR,
                "extract": lambda m: m.group(1),
            },
        ]

    def _build_suggestion_rules(self) -> dict[ErrorCategory, list[str]]:
        """Build suggestion rules for different error categories.

        Returns:
            Dictionary mapping error categories to suggestion lists
        """
        return {
            ErrorCategory.MISSING_PACKAGE: [
                "Install the DND-5e-LaTeX-Template following the guide at: docs/installation/latex_setup.md",
                "Ensure LaTeX package repositories are up to date",
                "Check if the package name is spelled correctly",
            ],
            ErrorCategory.MISSING_FILE: [
                "Verify all input files exist and paths are correct",
                "Check file permissions and accessibility",
                "Ensure working directory is set correctly",
            ],
            ErrorCategory.FONT_ERROR: [
                "Install template-compatible fonts or use fallback configuration",
                "Check font installation in your system",
                "Verify fontspec package is properly configured",
            ],
            ErrorCategory.TEMPLATE_ERROR: [
                "Update DND-5e-LaTeX-Template to the latest version",
                "Check template documentation for usage requirements",
                "Verify template installation is complete",
            ],
            ErrorCategory.SYNTAX_ERROR: [
                "Check LaTeX syntax for typos and missing braces",
                "Verify all commands are properly defined",
                "Review recent changes for syntax issues",
            ],
            ErrorCategory.TIMEOUT_ERROR: [
                "Try using draft mode for faster compilation",
                "Reduce document content or split into smaller parts",
                "Check for infinite loops in LaTeX code",
            ],
        }

    def _extract_error_from_match(
        self, match: re.Match, pattern_info: dict, lines: list[str], line_index: int
    ) -> LaTeXError | None:
        """Extract error information from a regex match.

        Args:
            match: Regex match object
            pattern_info: Pattern information dictionary
            lines: All log lines
            line_index: Current line index

        Returns:
            LaTeXError object or None
        """
        try:
            message = pattern_info["extract"](match)

            # Try to extract file and line number from context
            file_path, line_number = self._extract_location_info(lines, line_index)

            # Get additional context lines
            context = self._extract_context(lines, line_index)

            return LaTeXError(
                severity=pattern_info["severity"],
                category=pattern_info["category"],
                message=message,
                file_path=file_path,
                line_number=line_number,
                context=context,
            )
        except Exception:
            # If extraction fails, return None
            return None

    def _extract_location_info(
        self, lines: list[str], error_line_index: int
    ) -> tuple[str | None, int | None]:
        """Extract file path and line number from log context.

        Args:
            lines: All log lines
            error_line_index: Index of the error line

        Returns:
            Tuple of (file_path, line_number)
        """
        file_path = None
        line_number = None

        # Look backwards for file information
        for i in range(max(0, error_line_index - 10), error_line_index):
            line = lines[i]

            # Look for file path indicators
            if line.startswith("(./") or line.startswith("(/"):
                # Extract file path
                match = re.search(r"\((\.?/[^)]+)", line)
                if match:
                    file_path = match.group(1)

            # Look for line number indicators
            line_match = re.search(r"l\.(\d+)", line)
            if line_match:
                line_number = int(line_match.group(1))

        return file_path, line_number

    def _extract_context(self, lines: list[str], error_line_index: int) -> str | None:
        """Extract context around an error.

        Args:
            lines: All log lines
            error_line_index: Index of the error line

        Returns:
            Context string or None
        """
        # Get a few lines after the error for context
        context_lines = []
        for i in range(error_line_index + 1, min(len(lines), error_line_index + 4)):
            line = lines[i].strip()
            if line and not line.startswith("!"):
                context_lines.append(line)
            else:
                break

        return " ".join(context_lines) if context_lines else None

    def _get_suggestion(self, error: LaTeXError) -> str | None:
        """Get suggestion for fixing an error.

        Args:
            error: LaTeX error to suggest fix for

        Returns:
            Suggestion string or None
        """
        suggestions = self._suggestion_rules.get(error.category, [])

        # Return the first relevant suggestion
        if suggestions:
            # For specific errors, we could add more intelligent suggestion selection
            return suggestions[0]

        return None

    def get_error_summary(self, errors: list[LaTeXError]) -> str:
        """Generate a human-readable summary of errors.

        Args:
            errors: List of errors to summarize

        Returns:
            Summary string
        """
        if not errors:
            return "No errors found."

        # Count by severity
        severity_counts: dict[ErrorSeverity, int] = {}
        for error in errors:
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1

        # Build summary
        parts: list[str] = []

        if ErrorSeverity.FATAL in severity_counts:
            parts.append(f"{severity_counts[ErrorSeverity.FATAL]} fatal error(s)")

        if ErrorSeverity.ERROR in severity_counts:
            parts.append(f"{severity_counts[ErrorSeverity.ERROR]} error(s)")

        if ErrorSeverity.WARNING in severity_counts:
            parts.append(f"{severity_counts[ErrorSeverity.WARNING]} warning(s)")

        summary = "Compilation issues found: " + ", ".join(parts)

        # Add most critical errors
        critical_errors = [
            e
            for e in errors
            if e.severity in [ErrorSeverity.FATAL, ErrorSeverity.ERROR]
        ]
        if critical_errors:
            summary += "\n\nMost critical issues:"
            for error in critical_errors[:3]:  # Show top 3
                summary += f"\n  • {error.message}"
                if error.suggestion:
                    summary += f"\n    → {error.suggestion}"

        return summary
