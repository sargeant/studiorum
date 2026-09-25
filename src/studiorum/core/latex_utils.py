"""Detection of dangerous LaTeX commands."""

import re
from re import Pattern

# Dangerous LaTeX patterns that should never appear in user content
DANGEROUS_LATEX_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\\(?:new|renew|provide)command"),  # Command definitions
    re.compile(r"\\(?:def|gdef|edef|xdef)"),  # Primitive definitions
    re.compile(r"\\(?:input|include|InputIfFileExists)"),  # File operations
    re.compile(r"\\(?:immediate\s*)?\\write18"),  # Shell escape
    re.compile(r"\\(?:document(?:class|style)|usepackage)"),  # Document structure
    re.compile(r"\\(?:catcode|lccode|uccode|sfcode|mathcode)"),  # Category codes
    re.compile(r"\\(?:end|begin)\{document\}"),  # Document boundaries
    re.compile(r"\\(?:expandafter|noexpand|csname|endcsname)"),  # Expansion control
    re.compile(r"\\(?:the|number|romannumeral)"),  # Counter access
    re.compile(r"\\(?:jobname|meaning)"),  # System information
]


def contains_dangerous_latex(text: str) -> bool:
    """Check if text contains dangerous LaTeX commands.

    This function identifies potentially dangerous LaTeX constructs that
    could be used for code injection, file system access, or document
    structure manipulation.

    Args:
        text: Text to check for dangerous patterns

    Returns:
        True if dangerous patterns are found, False otherwise

    Examples:
        >>> contains_dangerous_latex("Normal text")
        False
        >>> contains_dangerous_latex("\\input{/etc/passwd}")
        True
        >>> contains_dangerous_latex("\\newcommand{\\evil}{PWNED}")
        True
    """
    if not text:
        return False

    for pattern in DANGEROUS_LATEX_PATTERNS:
        if pattern.search(text):
            return True
    return False


def validate_safe_latex(text: str) -> tuple[bool, list[str]]:
    """Validate that LaTeX content is safe for inclusion.

    This function checks for dangerous patterns and provides details
    about any security issues found.

    Args:
        text: LaTeX content to validate

    Returns:
        Tuple of (is_safe, list_of_issues)

    Examples:
        >>> validate_safe_latex("\\textbf{Safe content}")
        (True, [])
        >>> validate_safe_latex("\\input{file}")
        (False, ['File inclusion command detected'])
    """
    if not text:
        return True, []

    issues = []

    for pattern in DANGEROUS_LATEX_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            if "command" in pattern.pattern:
                issues.append("Command definition detected")
            elif "input" in pattern.pattern:
                issues.append("File inclusion command detected")
            elif "write18" in pattern.pattern:
                issues.append("Shell escape command detected")
            elif "document" in pattern.pattern:
                issues.append("Document structure manipulation detected")
            elif "catcode" in pattern.pattern:
                issues.append("Category code manipulation detected")
            else:
                issues.append(
                    f"Dangerous pattern detected: {matches[0] if matches else 'unknown'}"
                )

    return len(issues) == 0, issues
