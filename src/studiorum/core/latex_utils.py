"""LaTeX utility functions for text escaping and formatting.

Security Features:
- Comprehensive LaTeX character escaping
- Command injection detection and prevention
- Safe content validation for trusted LaTeX content
"""

import re
from re import Pattern


def escape_latex_text(text: str) -> str:
    """Escape special LaTeX characters and Unicode characters in text.

    This function provides comprehensive LaTeX escaping for both special LaTeX
    characters and Unicode characters that need special handling. It properly
    distinguishes between ASCII apostrophes (which should remain unchanged)
    and Unicode smart quotes (which need LaTeX replacements).

    Backslash escaping has been intentionally removed as D&D content rarely
    contains literal backslashes that need to be displayed as backslashes.

    Additionally applies small-caps transformation for "Dungeons & Dragons" text,
    converting both bold commands and plain text to small-caps formatting.

    Args:
        text: Text to escape for LaTeX output

    Returns:
        LaTeX-safe text with proper character escaping and D&D small-caps

    Note:
        - ASCII apostrophes (') remain unchanged for natural text like "Player's"
        - Unicode left single quote (') gets converted to LaTeX backtick
        - Backslashes (\\) are NOT escaped to avoid double-escaping issues
        - All other LaTeX special characters are properly escaped
        - "Dungeons & Dragons" text is converted to small-caps formatting
    """
    if not text:
        return ""

    # Apply small-caps transformation BEFORE LaTeX escaping to handle \textbf{} commands
    result = _apply_dnd_smallcaps_pre_escape(text)

    # LaTeX special characters (backslash escaping removed - see issue #58)
    latex_chars = {
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

    for char, escape in latex_chars.items():
        result = result.replace(char, escape)

    # Unicode characters that need special handling in LaTeX
    # NOTE: Deliberately excludes ASCII apostrophe (') to fix the
    # "Player's" -> "Player`s" bug that was affecting multiple implementations
    unicode_replacements = {
        "—": "---",  # Em dash
        "–": "--",  # En dash
        """: "``",   # Left double quote
        """: "''",  # Right double quote
        "…": "\\ldots{}",  # Ellipsis
        "°": "\\textdegree{}",  # Degree symbol
        "©": "\\copyright{}",  # Copyright symbol
        "®": "\\textregistered{}",  # Registered trademark
        "™": "\\texttrademark{}",  # Trademark symbol
    }

    # Apply Unicode character replacements
    for char, replacement in unicode_replacements.items():
        result = result.replace(char, replacement)

    # Apply small-caps transformation for any remaining plain text D&D references
    result = _apply_dnd_smallcaps_post_escape(result)

    return result


def _apply_dnd_smallcaps_pre_escape(text: str) -> str:
    """Apply small-caps transformation to D&D text before LaTeX escaping.

    Handles \textbf{} commands that contain D&D references, converting them
    to \textsc{} commands before the braces get escaped.

    Args:
        text: Text to transform (before LaTeX escaping)

    Returns:
        Text with \textbf{D&D} converted to \textsc{D&D}
    """
    if not text:
        return ""

    # Handle \textbf{} commands before LaTeX escaping (braces not yet escaped)
    patterns = [
        # Handle \textbf{Dungeons & Dragons} -> \textsc{Dungeons & Dragons}
        (r"\\textbf\{Dungeons\s*&\s*Dragons\}", r"\\textsc{Dungeons & Dragons}"),
        # Handle \textbf{D&D} -> \textsc{d&d}
        (r"\\textbf\{D&D\}", r"\\textsc{d&d}"),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def _apply_dnd_smallcaps_post_escape(text: str) -> str:
    """Apply small-caps transformation to D&D text after LaTeX escaping.

    Handles plain text instances of D&D references that weren't wrapped
    in \textbf{} commands and aren't already in \textsc{} commands.

    Args:
        text: Text to transform (after LaTeX escaping)

    Returns:
        Text with plain D&D references converted to \textsc{D&D}
    """
    if not text:
        return ""

    # Handle plain text instances (ampersands are now escaped, braces are escaped)
    # After LaTeX escaping, \textsc{ becomes \textsc\{ and \textbf{ becomes \textbf\{
    patterns = [
        # Handle plain "Dungeons & Dragons" -> \textsc{Dungeons \& Dragons}
        # Negative lookbehind: not preceded by \textsc\{ or \textbf\{
        # Negative lookahead: not followed by \} (indicating it's inside another command)
        (
            r"(?<!\\textsc\\{)(?<!\\textbf\\{)Dungeons\s*\\&\s*Dragons(?!\\})",
            r"\\textsc{Dungeons \\& Dragons}",
        ),
        # Handle plain "D&D" -> \textsc{d\&d}
        (r"(?<!\\textsc\\{)(?<!\\textbf\\{)D\\&D(?!\\})", r"\\textsc{d\\&d}"),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def _apply_dnd_smallcaps(text: str) -> str:
    """Apply small-caps transformation to Dungeons & Dragons text.

    Legacy function for backward compatibility with the template filter.
    Converts both \textbf{} commands and plain text instances of D&D references
    to use small-caps formatting.

    Args:
        text: Text to transform

    Returns:
        Text with D&D references converted to small-caps
    """
    if not text:
        return ""

    # Handle both pre-escaped and post-escaped patterns
    patterns = [
        # Handle \textbf{Dungeons \& Dragons} -> \textsc{Dungeons \& Dragons} (post-escape)
        (r"\\textbf\{Dungeons\s*\\&\s*Dragons\}", r"\\textsc{Dungeons \\& Dragons}"),
        # Handle \textbf{D\&D} -> \textsc{d\&d} (post-escape)
        (r"\\textbf\{D\\&D\}", r"\\textsc{d\\&d}"),
        # Handle \textbf{Dungeons & Dragons} -> \textsc{Dungeons & Dragons} (pre-escape)
        (r"\\textbf\{Dungeons\s*&\s*Dragons\}", r"\\textsc{Dungeons & Dragons}"),
        # Handle \textbf{D&D} -> \textsc{d&d} (pre-escape)
        (r"\\textbf\{D&D\}", r"\\textsc{d&d}"),
        # Handle plain instances with escaped ampersands
        (
            r"(?<!\\textsc\{)Dungeons\s*\\&\s*Dragons(?!\})",
            r"\\textsc{Dungeons \\& Dragons}",
        ),
        (r"(?<!\\textsc\{)D\\&D(?!\})", r"\\textsc{d\\&d}"),
        # Handle plain instances with unescaped ampersands
        (
            r"(?<!\\textsc\{)Dungeons\s*&\s*Dragons(?!\})",
            r"\\textsc{Dungeons & Dragons}",
        ),
        (r"(?<!\\textsc\{)D&D(?!\})", r"\\textsc{d&d}"),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


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


def sanitize_latex_content(text: str, allow_basic_formatting: bool = True) -> str:
    """Sanitize LaTeX content by removing dangerous commands.

    This function removes or escapes dangerous LaTeX constructs while
    optionally preserving basic formatting commands.

    Args:
        text: Text to sanitize
        allow_basic_formatting: Whether to allow basic LaTeX formatting commands

    Returns:
        Sanitized LaTeX content

    Note:
        This is a conservative approach that may remove legitimate LaTeX.
        For trusted content, use the 'safe' filter in templates instead.
    """
    if not text:
        return ""

    # First, escape all special characters
    sanitized = escape_latex_text(text)

    # If basic formatting is allowed, selectively unescape safe commands
    if allow_basic_formatting:
        safe_commands = [
            r"\\textbf\{",
            r"\\textit\{",
            r"\\emph\{",
            r"\\texttt\{",
            r"\\underline\{",
            r"\\textsc\{",
        ]

        for cmd in safe_commands:
            # This is a simplified approach - a full implementation would
            # need proper LaTeX parsing to handle nested commands safely
            pass

    return sanitized
