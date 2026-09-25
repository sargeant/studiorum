"""5etools' property templates: ``{=baseName/l}`` and ``{=amount1/v}`` in text.

A port of ``Renderer.applyProperties`` and ``applyAllProperties``
(``js/render.js``), with the number formats they use from ``js/parser.js``.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any

from ..logging import get_logger

logger = get_logger(__name__)

type Raw = dict[str, Any]

_TEMPLATE = re.compile(r"\{=([^}/]+)(?:/([a-z]+))?\}")
_VULGAR = {"125": "⅛", "2": "⅕", "25": "¼", "375": "⅜", "4": "⅖", "5": "½", "6": "⅗", "625": "⅝", "75": "¾", "8": "⅘", "875": "⅞"}  # fmt: skip
_THIRDS_AND_SIXTHS = {"0.33": "⅓", "0.67": "⅔", "0.17": "⅙", "0.83": "⅚"}
_NUMBERS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")  # fmt: skip
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")  # fmt: skip


def apply_properties(entries: Any, props: Raw | None = None) -> Any:
    """Fill the templates in every string of ``entries``.

    With ``props``, from those; without, from the nearest object around each
    string (an ingredient's ``{=amount1/v}`` reads its own ``amount1``).
    """
    return _apply(entries, props, fixed=props is not None)


def _apply(entries: Any, props: Raw | None, *, fixed: bool) -> Any:
    if isinstance(entries, str):
        if props is None:
            return entries
        return _TEMPLATE.sub(lambda m: _fill(m, props), entries)
    if isinstance(entries, list):
        return [_apply(e, props, fixed=fixed) for e in entries]
    if isinstance(entries, dict):
        own = props if fixed else entries
        return {k: _apply(v, own, fixed=fixed) for k, v in entries.items()}
    return entries


def _fill(match: re.Match[str], props: Raw) -> str:
    value: Any = props.get(match.group(1))
    if value is None:
        logger.debug(f"No value for {match.group(0)}")
        return match.group(0)
    # 5etools applies the modifiers in the order written
    for modifier in match.group(2) or "":
        match modifier:
            case "a":
                value = "an" if str(value)[:1].lower() in "aeiou" else "a"
            case "l":
                value = str(value).lower()
            case "t":
                value = str(value).title()
            case "u":
                value = str(value).upper()
            case "v":
                value = number_to_vulgar(value)
            case "x":
                value = number_to_text(value)
            case "r":
                value = round(value)
            case "f":
                value = math.floor(value)
            case "c":
                value = math.ceil(value)
    return _js_str(value)


def _js_str(value: Any) -> str:
    """A value as JavaScript prints it: 2.0 as "2"."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def number_to_vulgar(number: float) -> str:
    """0.5 as "½", 1.25 as "1¼", else a fraction such as "3/10" (``Parser.numberToVulgar``)."""
    text = _js_str(number)
    whole, _, decimals = text.lstrip("-").partition(".")
    if not decimals:
        return text
    lead = ("-" if number < 0 else "") + ("" if whole == "0" else whole)
    if glyph := _VULGAR.get(decimals) or _THIRDS_AND_SIXTHS.get(
        f"{float('0.' + decimals):.2f}"
    ):
        return lead + glyph
    fraction = Fraction(str(abs(number)))
    sign = "-" if number < 0 else ""
    return f"{sign}{fraction.numerator}/{fraction.denominator}"


def number_to_text(number: float) -> str:
    """Whole numbers under 100 in words (``Parser.numberToText``); others as they are."""
    if not float(number).is_integer() or abs(number) >= 100:
        return _js_str(number)
    n = int(abs(number))
    words = (
        _NUMBERS[n]
        if n < 20
        else _TENS[n // 10] + (f"-{_NUMBERS[n % 10]}" if n % 10 else "")
    )
    return f"negative {words}" if number < 0 else words
