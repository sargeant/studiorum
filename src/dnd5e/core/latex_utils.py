"""LaTeX utility functions for text escaping and formatting."""


def escape_latex_text(text: str) -> str:
    """Escape special LaTeX characters and Unicode characters in text.

    This function provides comprehensive LaTeX escaping for both special LaTeX
    characters and Unicode characters that need special handling. It properly
    distinguishes between ASCII apostrophes (which should remain unchanged)
    and Unicode smart quotes (which need LaTeX replacements).

    Backslash escaping has been intentionally removed as D&D content rarely
    contains literal backslashes that need to be displayed as backslashes.

    Args:
        text: Text to escape for LaTeX output

    Returns:
        LaTeX-safe text with proper character escaping

    Note:
        - ASCII apostrophes (') remain unchanged for natural text like "Player's"
        - Unicode left single quote (') gets converted to LaTeX backtick
        - Backslashes (\\) are NOT escaped to avoid double-escaping issues
        - All other LaTeX special characters are properly escaped
    """
    if not text:
        return ""

    # Direct replacement approach (placeholders not needed without backslash escaping)

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

    result = text
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

    return result
