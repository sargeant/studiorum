"""Unicode character mappings for LaTeX rendering.

This module provides comprehensive Unicode-to-LaTeX character mappings
following PyLaTeX best practices and industry standards for robust
text processing in LaTeX documents.
"""

# LaTeX special characters that need escaping
LATEX_SPECIAL_CHARS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "^": r"\textasciicircum{}",
    "_": r"\_",
    "~": r"\textasciitilde{}",
}

# Unicode characters that need special handling in LaTeX
# Using explicit Unicode code points to avoid encoding issues
UNICODE_TO_LATEX: dict[str, str] = {
    # Quotation marks
    chr(0x201C): "``",  # Left double quotation mark → ``
    chr(0x201D): "''",  # Right double quotation mark → ''
    chr(0x2018): "`",  # Left single quotation mark → `
    chr(0x2019): "'",  # Right single quotation mark → '
    chr(0x201A): ",",  # Single low-9 quotation mark → ,
    chr(0x201E): ",,",  # Double low-9 quotation mark → ,,
    # Dashes
    chr(0x2014): "---",  # Em dash → ---
    chr(0x2013): "--",  # En dash → --
    chr(0x2010): "-",  # Hyphen → -
    chr(0x2011): "-",  # Non-breaking hyphen → -
    # Spaces
    chr(0x00A0): "~",  # Non-breaking space → ~
    chr(0x2002): r"\enspace{}",  # En space
    chr(0x2003): r"\quad{}",  # Em space
    chr(0x2009): r"\,",  # Thin space
    chr(0x200B): "",  # Zero width space → remove
    # Mathematical and typographical symbols
    chr(0x2026): r"\ldots{}",  # Horizontal ellipsis → \ldots
    chr(0x00B0): r"\textdegree{}",  # Degree sign → \textdegree
    chr(0x00B1): r"\textpm{}",  # Plus-minus sign → \textpm
    chr(0x00D7): r"\texttimes{}",  # Multiplication sign → \texttimes
    chr(0x00F7): r"\textdiv{}",  # Division sign → \textdiv
    # Currency symbols (requires textcomp package)
    chr(0x20AC): r"\texteuro{}",  # Euro sign → \texteuro
    chr(0x00A2): r"\textcent{}",  # Cent sign → \textcent
    chr(0x00A3): r"\textsterling{}",  # Pound sign → \textsterling
    chr(0x00A5): r"\textyen{}",  # Yen sign → \textyen
    # Copyright and trademark symbols (requires textcomp package)
    chr(0x00A9): r"\textcopyright{}",  # Copyright sign → \textcopyright
    chr(0x00AE): r"\textregistered{}",  # Registered trademark → \textregistered
    chr(0x2122): r"\texttrademark{}",  # Trade mark sign → \texttrademark
    # Fractions (requires textcomp or amsmath package)
    chr(0x00BC): r"\textonequarter{}",  # Vulgar fraction one quarter
    chr(0x00BD): r"\textonehalf{}",  # Vulgar fraction one half
    chr(0x00BE): r"\textthreequarters{}",  # Vulgar fraction three quarters
    # Ordinal indicators
    chr(0x00AA): r"\textordfeminine{}",  # Feminine ordinal indicator
    chr(0x00BA): r"\textordmasculine{}",  # Masculine ordinal indicator
    # Section and paragraph symbols
    chr(0x00A7): r"\S{}",  # Section sign → \S
    chr(0x00B6): r"\P{}",  # Pilcrow sign → \P
    # Miscellaneous symbols
    chr(0x2020): r"\textdagger{}",  # Dagger → \textdagger
    chr(0x2021): r"\textdaggerdbl{}",  # Double dagger → \textdaggerdbl
    chr(0x2022): r"\textbullet{}",  # Bullet → \textbullet
    chr(0x2030): r"\textperthousand{}",  # Per mille sign → \textperthousand
    chr(0x2032): r"\textquotesingle{}",  # Prime → \textquotesingle
    chr(0x2033): r"\textquotedbl{}",  # Double prime → \textquotedbl
}

# Common problematic Unicode characters that should be handled
# but might not have direct LaTeX equivalents
UNICODE_PROBLEMATIC: dict[str, str] = {
    # Zero-width characters (remove)
    chr(0x200C): "",  # Zero width non-joiner
    chr(0x200D): "",  # Zero width joiner
    chr(0xFEFF): "",  # Zero width no-break space (BOM)
    # Directional marks (remove in most contexts)
    chr(0x200E): "",  # Left-to-right mark
    chr(0x200F): "",  # Right-to-left mark
    chr(0x202A): "",  # Left-to-right embedding
    chr(0x202B): "",  # Right-to-left embedding
    chr(0x202C): "",  # Pop directional formatting
    chr(0x202D): "",  # Left-to-right override
    chr(0x202E): "",  # Right-to-left override
}


def get_latex_special_chars() -> dict[str, str]:
    """Get LaTeX special character mappings.

    Returns:
        Dictionary mapping special characters to LaTeX escape sequences
    """
    return LATEX_SPECIAL_CHARS.copy()


def get_unicode_to_latex_mappings() -> dict[str, str]:
    """Get Unicode to LaTeX character mappings.

    Returns:
        Dictionary mapping Unicode characters to LaTeX representations
    """
    return UNICODE_TO_LATEX.copy()


def get_all_character_mappings() -> dict[str, str]:
    """Get all character mappings (special chars + Unicode).

    Returns:
        Combined dictionary of all character mappings
    """
    mappings = {}
    mappings.update(LATEX_SPECIAL_CHARS)
    mappings.update(UNICODE_TO_LATEX)
    mappings.update(UNICODE_PROBLEMATIC)
    return mappings


def validate_unicode_char(char: str) -> bool:
    """Validate if a Unicode character has a known LaTeX mapping.

    Args:
        char: Single Unicode character to validate

    Returns:
        True if character has a known mapping, False otherwise
    """
    if len(char) != 1:
        return False

    return (
        char in LATEX_SPECIAL_CHARS
        or char in UNICODE_TO_LATEX
        or char in UNICODE_PROBLEMATIC
    )


def get_unmapped_unicode_chars(text: str) -> set[str]:
    """Get Unicode characters in text that don't have LaTeX mappings.

    Args:
        text: Text to analyze

    Returns:
        Set of unmapped Unicode characters
    """
    unmapped = set()
    for char in text:
        if ord(char) > 127 and not validate_unicode_char(char):
            unmapped.add(char)
    return unmapped
