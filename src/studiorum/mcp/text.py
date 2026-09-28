"""Folding text so a query matches it however either is typed."""

from __future__ import annotations

import re
import unicodedata

# str.replace, not str.translate: translate takes a second over the library's text
_QUOTES = (("‘", "'"), ("’", "'"), ("ʼ", "'"), ("“", '"'), ("”", '"'))
# Latin letters with accents, and ß; without them, text only lower-cases
_ACCENTED = re.compile(r"[À-ɏ]")
_MARKS = re.compile(r"[̀-ͯ]")


def fold(text: str) -> str:
    """Text in lower case, with curly quotes straight and accents dropped.

    "Bigby’s" folds to "bigby's" and "Rothé" to "rothe".
    """
    if text.isascii():
        return text.lower()
    for curly, straight in _QUOTES:
        text = text.replace(curly, straight)
    if not _ACCENTED.search(text):
        return text.lower()
    return _MARKS.sub("", unicodedata.normalize("NFKD", text)).casefold()
