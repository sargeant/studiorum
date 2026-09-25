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

_ENCODER = UnicodeToLatexEncoder(
    conversion_rules=[
        UnicodeToLatexConversionRule(
            RULE_DICT, {ord(char): latex for char, latex in _RULES.items()}
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
