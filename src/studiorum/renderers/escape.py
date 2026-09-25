"""Plain text as LaTeX: the one escape function.

``escape`` escapes LaTeX's special characters and a few Unicode ones with
pylatexenc, then sets the game's name in small caps (see the Trademark Handling
decision). Other Unicode passes through for xelatex and lualatex to set.
"""

from __future__ import annotations

import re

from pylatexenc.latexencode import (
    RULE_DICT,
    UnicodeToLatexConversionRule,
    UnicodeToLatexEncoder,
)

_RULES = {
    "\\": r"\textbackslash",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde",
    "^": r"\textasciicircum",
    "—": "---",
    "–": "--",
    "…": r"\ldots",
    "°": r"\textdegree",
    "©": r"\copyright",
    "®": r"\textregistered",
    "™": r"\texttrademark",
    " ": "~",
}

# The template's fonts have ¼, ½ and ¾ but no other vulgar fractions
_FRACTIONS = {"⅓": (1, 3), "⅔": (2, 3), "⅕": (1, 5), "⅖": (2, 5), "⅗": (3, 5), "⅘": (4, 5), "⅙": (1, 6), "⅚": (5, 6), "⅛": (1, 8), "⅜": (3, 8), "⅝": (5, 8), "⅞": (7, 8)}  # fmt: skip
_FRACTION_RULES = {
    char: rf"\textsuperscript{{{top}}}/\textsubscript{{{bottom}}}"
    for char, (top, bottom) in _FRACTIONS.items()
}

_ENCODER = UnicodeToLatexEncoder(
    conversion_rules=[
        UnicodeToLatexConversionRule(
            RULE_DICT,
            {ord(char): latex for char, latex in (_RULES | _FRACTION_RULES).items()},
        )
    ],
    replacement_latex_protection="braces-after-macro",
    unknown_char_policy="keep",
    unknown_char_warning=False,
)

_SMALL_CAPS = (
    (
        re.compile(r"(?<![A-Za-z])Dungeons\s*\\&\s*Dragons(?![A-Za-z])", re.IGNORECASE),
        r"\\textsc{Dungeons \\& Dragons}",
    ),
    (re.compile(r"(?<![A-Za-z])D\\&D(?![A-Za-z])", re.IGNORECASE), r"\\textsc{d\\&d}"),
)

# hyperref takes these escaped in an \href URL, which also works inside another
# command's argument or a table cell.
_URL = {"#": r"\#", "%": r"\%", "&": r"\&"}


def escape(text: str) -> str:
    """Plain text as LaTeX, with the game's name in small caps."""
    if not text:
        return ""
    latex = _ENCODER.unicode_to_latex(text)
    for pattern, replacement in _SMALL_CAPS:
        latex = pattern.sub(replacement, latex)
    return latex


def escape_url(url: str) -> str:
    """A URL for the first argument of ``\\href``."""
    return "".join(_URL.get(char, char) for char in url)
