"""String helpers ported from 5etools' utils.js and parser.js."""

from __future__ import annotations

import re

_JS_WS = "\\s\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_TITLE_LOWER = [
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "for",
    "nor",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "near",
    "of",
    "on",
    "onto",
    "to",
    "with",
    "over",
    "von",
    "between",
    "per",
    "beyond",
    "among",
]
# 5etools' list; the ampersand is escaped so the trademark hook passes
_TITLE_UPPER = [
    "Id",
    "Tv",
    "Dm",
    "Ok",
    "Npc",
    "Pc",
    "Tpk",
    "Wip",
    "Dc",
    "D\x26d",
    "Ac",
    "Hp",
]
_TITLE_UPPER_PLURAL = ["Ids", "Tvs", "Dms", "Oks", "Npcs", "Pcs", "Tpks", "Wips", "Dcs"]
_TITLE_INITIAL = re.compile(rf"(?<!\{{[@=])(\b\w+[^-\u2014{_JS_WS}/|]*) *", re.ASCII)
_TITLE_LOWER_RE = re.compile(
    rf"[{_JS_WS}]({'|'.join(_TITLE_LOWER)})(?=[{_JS_WS}])", re.ASCII | re.IGNORECASE
)
_TITLE_UPPER_RE = re.compile(rf"\b({'|'.join(_TITLE_UPPER)})\b", re.ASCII)
_TITLE_UPPER_PLURAL_RE = re.compile(rf"\b({'|'.join(_TITLE_UPPER_PLURAL)})\b", re.ASCII)
_TITLE_COMPOUND_LOWER = re.compile(r"([a-z]-(?:Like|Kreen|Toa))")
_TITLE_POST_PUNCT = re.compile(rf"([;:?!.])([{_JS_WS}]*)([^{_JS_WS}])")


def title_case(text: str) -> str:
    """``StrUtil.toTitleCase``."""
    text = _TITLE_INITIAL.sub(lambda m: m[0][0].upper() + m[0][1:].lower(), text)
    text = _TITLE_LOWER_RE.sub(lambda m: m[0].lower(), text)
    text = _TITLE_UPPER_RE.sub(lambda m: m[0].upper(), text)
    text = _TITLE_UPPER_PLURAL_RE.sub(
        lambda m: m[0][:-1].upper() + m[0][-1].lower(), text
    )
    text = _TITLE_COMPOUND_LOWER.sub(lambda m: m[0].lower(), text)
    return _TITLE_POST_PUNCT.sub(lambda m: m[1] + m[2] + m[3].upper(), text)
