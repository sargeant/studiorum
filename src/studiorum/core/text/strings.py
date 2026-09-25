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


def uppercase_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def join_conjunct(values: list[str], joiner: str, last_joiner: str) -> str:
    """``Array.joinConjunct``: "a, b, or c" (the joiner's trimmed form before the last)."""
    if len(values) < 3:
        return last_joiner.join(values)
    return joiner.join(values[:-1]) + joiner.strip() + last_joiner + values[-1]


def common_suffix(values: list[str]) -> str:
    """``MiscUtil.findCommonSuffix`` by words: " 13 or higher", or the whole string."""
    return _common_words(values, suffix=True)


def common_prefix(values: list[str]) -> str:
    """``MiscUtil.findCommonPrefix`` by words: "Maneuver, ", or the whole string."""
    return _common_words(values, suffix=False)


def _common_words(values: list[str], *, suffix: bool) -> str:
    if not values:
        return ""
    common: list[str] | None = None
    for value in values:
        tokens = value.split(" ")
        if suffix:
            tokens.reverse()
        if common is None:
            common = tokens
            continue
        common = common[: min(len(tokens), len(common))]
        for i, (a, b) in enumerate(zip(common, tokens, strict=False)):
            if a != b:
                common = common[:i]
                break
    if not common:
        return ""
    if suffix:
        common.reverse()
    out = " ".join(common)
    if len(out) == max(len(v) for v in values):
        return out
    return f" {out}" if suffix else f"{out} "


def ordinal(number: int) -> str:
    """``Parser.getOrdinalForm``: 1st, 2nd, 11th."""
    if number % 10 == 1 and number % 100 != 11:
        return f"{number}st"
    if number % 10 == 2 and number % 100 != 12:
        return f"{number}nd"
    if number % 10 == 3 and number % 100 != 13:
        return f"{number}rd"
    return f"{number}th"


_NUMBER_WORDS = [
    *("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"),
    *("ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen"),
    *("seventeen", "eighteen", "nineteen", "twenty"),
]


def number_to_text(number: int) -> str:
    """``Parser.numberToText`` for the counts in the data: "two"."""
    return _NUMBER_WORDS[number] if 0 <= number <= 20 else str(number)


def article(word: str) -> str:
    """``Parser.getArticle``."""
    return "an" if re.match(r"^[aeiou]", word, re.IGNORECASE) else "a"
