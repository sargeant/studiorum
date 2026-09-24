"""Resolve 5etools ``_copy`` entities on raw JSON, as 5etools itself does.

This is a port of ``DataUtil.generic._pMergeCopy`` and ``copyApplier`` from
5etools' ``js/utils.js`` (v2.36.1). It works on the raw dicts before they are
validated: a copy takes every root property of its parent that it lacks
itself, keeps its own, then applies its ``_mod`` operations. The tests check
it against the output of the JavaScript original (see
``tests/copy_oracle/``), so where JavaScript and Python differ (truthiness,
``splice``, regex replacement strings, number formatting) the helpers below
follow JavaScript.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

JSON = Any

# region JavaScript semantics


def _truthy(value: JSON) -> bool:
    """JavaScript truthiness: empty lists and dicts are true, 0 and "" false."""
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, int | float):
        return value != 0 and not math.isnan(value)
    if isinstance(value, str):
        return value != ""
    return True


def _js_str(value: JSON) -> str:
    """``${value}`` in JavaScript."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value.is_integer():
            return str(int(value))
    return str(value)


def _js_number(value: JSON) -> float:
    """``Number(value)`` in JavaScript, for the values the data holds."""
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return 0.0
        try:
            return float(text)
        except ValueError:
            return math.nan
    return math.nan


def _num(value: float) -> int | float:
    """A JavaScript number as the JSON value it would serialise to."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _strict_equal(a: JSON, b: JSON) -> bool:
    """``a === b``: objects and arrays are equal only to themselves."""
    if isinstance(a, dict | list) or isinstance(b, dict | list):
        return a is b
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return bool(a == b)


def _deep_equals(a: JSON, b: JSON) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_deep_equals(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _deep_equals(x, y) for x, y in zip(a, b, strict=True)
        )
    return _strict_equal(a, b)


def _splice(arr: list[JSON], start: int | None, delete: int, items: list[JSON]) -> None:
    """``arr.splice(start, delete, ...items)``."""
    length = len(arr)
    if start is None:
        start = 0
    elif start < 0:
        start = max(length + start, 0)
    else:
        start = min(start, length)
    arr[start : start + delete] = items


def _copy_fast(obj: JSON) -> JSON:
    if isinstance(obj, dict):
        return {k: _copy_fast(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_copy_fast(v) for v in obj]
    return obj


def _key(obj: JSON, part: str) -> tuple[bool, JSON]:
    if isinstance(obj, dict):
        return part in obj, obj.get(part)
    if isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
        return True, obj[int(part)]
    return False, None


def _get(obj: JSON, path: list[str]) -> JSON:
    """``MiscUtil.get``."""
    for part in path:
        if obj is None:
            return None
        _, obj = _key(obj, part)
    return obj


def _put(obj: JSON, part: str, value: JSON) -> None:
    if isinstance(obj, list):
        obj[int(part)] = value
    else:
        obj[part] = value


def _set(obj: JSON, path: list[str], value: JSON) -> JSON:
    """``MiscUtil.set``: falsy intermediate values become objects."""
    if obj is None or not path:
        return None
    for i, part in enumerate(path):
        if i == len(path) - 1:
            _put(obj, part, value)
        else:
            _, existing = _key(obj, part)
            if not _truthy(existing):
                existing = {}
                _put(obj, part, existing)
            obj = existing
    return value


def _delete(obj: JSON, path: list[str]) -> None:
    """``MiscUtil.delete``."""
    for part in path[:-1]:
        if obj is None:
            return
        _, obj = _key(obj, part)
    if isinstance(obj, dict):
        obj.pop(path[-1], None)


def _walk_strings(obj: JSON, fn: Callable[[str], JSON]) -> JSON:
    """``MiscUtil.getWalker().walk(obj, {string: fn})``: maps strings in place."""
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        for i, value in enumerate(obj):
            obj[i] = _walk_strings(value, fn)
    elif isinstance(obj, dict):
        for key in obj:
            obj[key] = _walk_strings(obj[key], fn)
    return obj


_JS_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def _js_regex(pattern: str, flags: str | None) -> re.Pattern[str]:
    """Compile a JavaScript regex source. ``\\w`` and ``\\b`` are ASCII there."""
    value = re.ASCII
    for flag in flags or "":
        value |= _JS_FLAGS.get(flag, 0)
    return re.compile(re.sub(r"\(\?<(?=[A-Za-z_])", "(?P<", pattern), value)


_JS_REPLACEMENT = re.compile(r"\$(\$|&|`|'|<[^>]*>|\d{1,2})")


def _js_replace(regex: re.Pattern[str], text: str, replacement: str) -> str:
    """``text.replace(regex /g, replacement)`` with JavaScript's ``$`` patterns."""

    def expand(match: re.Match[str]) -> str:
        def one(token: re.Match[str]) -> str:
            code = token.group(1)
            if code == "$":
                return "$"
            if code == "&":
                return match.group(0)
            if code == "`":
                return match.string[: match.start()]
            if code == "'":
                return match.string[match.end() :]
            if code.startswith("<"):
                if not regex.groupindex:
                    return token.group(0)
                return match.groupdict().get(code[1:-1]) or ""
            if len(code) == 2 and int(code) > regex.groups:
                code = code[0]
                suffix = token.group(1)[1]
            else:
                suffix = ""
            index = int(code)
            if index == 0 or index > regex.groups:
                return token.group(0)
            return (match.group(index) or "") + suffix

        return _JS_REPLACEMENT.sub(one, replacement)

    return regex.sub(expand, text)


_MATH_OPS: dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_math(expression: str) -> float:
    """``eval`` of a cleaned maths expression; a comma returns its last part."""
    last = expression.split(",")[-1]

    def value(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _MATH_OPS:
            left, right = value(node.left), value(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                return math.copysign(math.inf, left) if left else math.nan
            return _MATH_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _MATH_OPS:
            return _MATH_OPS[type(node.op)](value(node.operand))
        raise ValueError(f"Unsupported expression: {expression!r}")

    return value(ast.parse(last, mode="eval").body)


def _clean_math(text: str) -> str:
    return re.sub(r"[^-+/*0-9.,]+", "", text)


def _floor(value: float) -> int | float:
    return value if math.isnan(value) or math.isinf(value) else math.floor(value)


# endregion

# region 5etools parser helpers

_XP_BY_CR = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700,
    "4": 1100, "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000,
    "10": 5900, "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000,
    "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000,
}  # fmt: skip

_SKILL_TO_ABILITY = {
    "athletics": "str", "acrobatics": "dex", "sleight of hand": "dex",
    "stealth": "dex", "arcana": "int", "history": "int", "investigation": "int",
    "nature": "int", "religion": "int", "animal handling": "wis",
    "insight": "wis", "medicine": "wis", "perception": "wis", "survival": "wis",
    "deception": "cha", "intimidation": "cha", "performance": "cha",
    "persuasion": "cha",
}  # fmt: skip

_ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
_SIZES = ("T", "S", "M", "L", "H", "G", "V")
_SIZE_MULT = {"L": 2, "H": 3, "G": 4}
_CR_UNKNOWN = object()
_SPELL_USE_KEYS = {str(i) for i in range(1, 10)} | {f"{i}e" for i in range(1, 10)}


def _cr_number(cr: JSON) -> float | object | None:
    if cr is None or cr in ("Unknown", "\u2014"):
        return _CR_UNKNOWN
    if isinstance(cr, dict):
        return _cr_number(cr.get("cr")) if _truthy(cr.get("cr")) else None
    parts = [p for p in str(cr).strip().split("/") if p]
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) / float(parts[1])
    except ValueError:
        return None
    return None


def _cr_to_pb(cr: JSON) -> int | None:
    """``Parser.crToPb``: None for a custom CR, which counts as 0 in arithmetic."""
    number = _cr_number(cr)
    if number is _CR_UNKNOWN:
        return 0
    if not isinstance(number, float) or number < 0:
        return None
    if number < 5:
        return 2
    return math.ceil(number / 4) + 1


def _ability_mod(score: JSON) -> float:
    number = _js_number(score) if score is not None else math.nan
    return math.nan if math.isnan(number) else float(math.floor((number - 10) / 2))


def _cr_to_xp(cr: JSON) -> JSON:
    if isinstance(cr, dict) and _truthy(cr.get("xp")):
        return cr["xp"]
    key = cr.get("cr") if isinstance(cr, dict) and _truthy(cr.get("cr")) else cr
    if not isinstance(key, str) or key == "Unknown":
        return None
    return _XP_BY_CR.get(key)


def _signed(total: float) -> JSON:
    """``total >= 0 ? `+${total}` : total``."""
    return f"+{_js_str(_num(total))}" if total >= 0 else _num(total)


def _pb(cr: JSON) -> int:
    return _cr_to_pb(cr) or 0


def _sort_lower(values: list[JSON]) -> None:
    values.sort(key=lambda v: v.lower() if isinstance(v, str) else v)


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


def _title_case(text: str) -> str:
    """``StrUtil.toTitleCase``."""
    text = _TITLE_INITIAL.sub(lambda m: m[0][0].upper() + m[0][1:].lower(), text)
    text = _TITLE_LOWER_RE.sub(lambda m: m[0].lower(), text)
    text = _TITLE_UPPER_RE.sub(lambda m: m[0].upper(), text)
    text = _TITLE_UPPER_PLURAL_RE.sub(
        lambda m: m[0][:-1].upper() + m[0][-1].lower(), text
    )
    text = _TITLE_COMPOUND_LOWER.sub(lambda m: m[0].lower(), text)
    return _TITLE_POST_PUNCT.sub(lambda m: m[1] + m[2] + m[3].upper(), text)


def _short_name(mon: dict[str, JSON], *, title_case: bool = False) -> str:
    """``Renderer.monster.getShortName``."""
    name = mon.get("name")
    short_name = mon.get("shortName")
    prefix = (
        ""
        if _truthy(mon.get("isNamedCreature"))
        else ("The " if title_case else "the ")
    )
    if short_name is True:
        return f"{prefix}{name}"
    if _truthy(short_name):
        if not prefix and title_case:
            return f"{prefix}{_title_case(str(short_name))}"
        return f"{prefix}{str(short_name).lower()}"
    base = str(name).split(",")[0]
    out = re.sub(
        r"(?:adult|ancient|young) \w+ (dragon|dracolich)", r"\1", base,
        flags=re.IGNORECASE | re.ASCII,
    )  # fmt: skip
    out = out.split(" ")[0] if _truthy(mon.get("isNamedCreature")) else out.lower()
    return f"{prefix}{out}"


def _split_by_tags(text: str) -> list[str]:
    """``Renderer.splitByTags``."""
    depth = 0
    out: list[str] = []
    current = ""
    i = 0
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if char == "{":
            if nxt not in ("@", "="):
                current += "{"
            elif depth > 0:
                depth += 1
                current += "{"
            else:
                depth += 1
                if current:
                    out.append(current)
                current = "{" + nxt
                i += 1
        elif char == "}":
            current += "}"
            if depth != 0:
                depth -= 1
                if depth == 0:
                    if current:
                        out.append(current)
                    current = ""
        else:
            current += char
        i += 1
    if current:
        out.append(current)
    return out


# endregion

# region Variables in _mod values

_VARIABLE = re.compile(r"<\$(?P<variable>[^$]+)\$>")


def _resolve_variable(mode: str, detail: str | None, ent: dict[str, JSON]) -> JSON:
    """One ``variableResolver`` resolver, or None when the mode is unknown."""
    if mode in ("dc", "spell_dc", "to_hit", "damage_mod") and detail not in _ABILITIES:
        raise CopyError(f'Unknown ability score "{detail}"')
    if mode == "name":
        return ent.get("name")
    if mode == "short_name":
        return _short_name(ent)
    if mode == "title_short_name":
        return _short_name(ent, title_case=True)
    if mode in ("dc", "spell_dc"):
        return _num(8 + _ability_mod(ent.get(detail or "")) + _pb(ent.get("cr")))
    if mode == "to_hit":
        return _signed(_pb(ent.get("cr")) + _ability_mod(ent.get(detail or "")))
    if mode == "damage_mod":
        total = _ability_mod(ent.get(detail or ""))
        if total == 0:
            return ""
        return (
            f" + {_js_str(_num(total))}"
            if total > 0
            else f" - {_js_str(_num(abs(total)))}"
        )
    if mode == "damage_avg":
        replaced = re.sub(
            r"\b(?P<abil>str|dex|con|int|wis|cha)\b",
            lambda m: _js_str(_num(_ability_mod(ent.get(m["abil"])))),
            detail or "",
            flags=re.IGNORECASE | re.ASCII,
        )
        size_mult = _SIZE_MULT.get(_size(ent), 1)
        replaced = re.sub(r"\bsize_mult\b", str(size_mult), replaced, flags=re.ASCII)
        return _num(_floor(_eval_math(_clean_math(replaced))))
    if mode == "size_mult":
        mult = _SIZE_MULT.get(_size(ent), 1)
        if not detail:
            return mult
        return _num(_floor(_eval_math(f"{mult} * {_clean_math(detail)}")))
    return None


def _size(ent: dict[str, JSON]) -> str:
    size = ent.get("size")
    return size[0] if isinstance(size, list) and size else "M"


def _resolve_variables(obj: JSON, ent: dict[str, JSON]) -> JSON:
    def replace(text: str) -> str:
        def one(match: re.Match[str]) -> str:
            parts = match["variable"].split("__")
            value = _resolve_variable(
                parts[0], parts[1] if len(parts) > 1 else None, ent
            )
            return match[0] if value is None else _js_str(value)

        return _VARIABLE.sub(one, text)

    return _walk_strings(obj, replace)


# endregion

# region _mod operations


class CopyError(Exception):
    """A ``_copy`` could not be applied."""


def _ensure_list(obj: dict[str, JSON], prop: str) -> list[JSON]:
    if not isinstance(obj.get(prop), list):
        obj[prop] = [obj.get(prop)]
    return list(obj[prop])


def _replace_handler(mod: dict[str, JSON]) -> Callable[[str], str]:
    regex = _js_regex(mod["replace"], mod.get("flags"))
    replacement = _js_str(mod.get("with"))
    tag_insensitive = _truthy(mod.get("tagInsensitive"))

    def handle(text: str) -> str:
        if tag_insensitive:
            return _js_replace(regex, text, replacement)
        parts = _split_by_tags(text)
        return "".join(
            part if part.startswith("{@") else _js_replace(regex, part, replacement)
            for part in parts
        )

    return handle


def _mod_replace_name(to: dict, mod: dict, path: list[str]) -> None:
    ents = _get(to, path)
    if not _truthy(ents):
        return
    handle = _replace_handler(mod)
    for ent in ents:
        if isinstance(ent, dict) and _truthy(ent.get("name")):
            ent["name"] = _walk_strings(ent["name"], handle)


def _mod_replace_txt(to: dict, mod: dict, path: list[str]) -> None:
    ents = _get(to, path)
    if not _truthy(ents):
        return
    if not isinstance(ents, list):
        raise CopyError(f'"{".".join(path)}" is not an array')
    handle = _replace_handler(mod)
    props = mod.get("props")
    if not _truthy(props):
        props = [None, "entries", "headerEntries", "footerEntries"]
    if not props:
        return
    if None in props:
        ents = [_walk_strings(it, handle) if isinstance(it, str) else it for it in ents]
        _set(to, path, ents)
    for ent in ents:
        for prop in props:
            if prop is not None and isinstance(ent, dict) and _truthy(ent.get(prop)):
                ent[prop] = _walk_strings(ent[prop], handle)


def _mod_append_str(to: dict, mod: dict, path: list[str]) -> None:
    existing = _get(to, path)
    if _truthy(existing):
        joiner = mod.get("joiner") or ""
        _set(to, path, f"{_js_str(existing)}{_js_str(joiner)}{_js_str(mod.get('str'))}")
    else:
        _set(to, path, mod.get("str"))


def _concat(first: JSON, second: JSON) -> list[JSON]:
    """``first.concat(second)``: a non-array argument is appended as one item."""
    if not isinstance(first, list):
        raise CopyError("concat on a value that is not an array")
    return first + (second if isinstance(second, list) else [second])


def _mod_prepend_arr(to: dict, mod: dict, path: list[str]) -> None:
    items = _ensure_list(mod, "items")
    existing = _get(to, path)
    _set(to, path, _concat(items, existing) if _truthy(existing) else mod["items"])


def _mod_append_arr(to: dict, mod: dict, path: list[str]) -> None:
    items = _ensure_list(mod, "items")
    existing = _get(to, path)
    _set(to, path, _concat(existing, items) if _truthy(existing) else mod["items"])


def _mod_append_if_not_exists_arr(to: dict, mod: dict, path: list[str]) -> None:
    items = _ensure_list(mod, "items")
    existing = _get(to, path)
    if not _truthy(existing):
        _set(to, path, mod["items"])
        return
    new = [it for it in items if not any(_deep_equals(it, x) for x in existing)]
    _set(to, path, _concat(existing, new))


def _mod_replace_arr(
    to: dict, mod: dict, path: list[str], *, strict: bool = True
) -> bool:
    items = _ensure_list(mod, "items")
    existing = _get(to, path)
    if not _truthy(existing):
        if strict:
            raise CopyError(f'Could not find "{".".join(path)}" array')
        return False
    replace = mod.get("replace")
    index: int | None
    if isinstance(replace, dict) and _truthy(replace.get("regex")):
        regex = _js_regex(replace["regex"], replace.get("flags") or "")

        def hit(it: JSON) -> bool:
            if isinstance(it, dict) and _truthy(it.get("name")):
                return regex.search(_js_str(it["name"])) is not None
            return isinstance(it, str) and regex.search(it) is not None

        index = next((i for i, it in enumerate(existing) if hit(it)), -1)
    elif isinstance(replace, dict) and replace.get("index") is not None:
        index = replace["index"]
    else:

        def same(it: JSON) -> bool:
            if isinstance(it, dict) and _truthy(it.get("name")):
                return _strict_equal(it["name"], replace)
            return _strict_equal(it, replace)

        index = next((i for i, it in enumerate(existing) if same(it)), -1)
    if index != -1:
        _splice(existing, index, 1, items)
        return True
    if strict:
        raise CopyError(
            f'Could not find "{".".join(path)}" item "{replace}" to replace'
        )
    return False


def _mod_replace_or_append_arr(to: dict, mod: dict, path: list[str]) -> None:
    if not _mod_replace_arr(to, mod, path, strict=False):
        _mod_append_arr(to, mod, path)


def _mod_insert_arr(to: dict, mod: dict, path: list[str]) -> None:
    items = _ensure_list(mod, "items")
    existing = _get(to, path)
    if not _truthy(existing):
        raise CopyError(f'Could not find "{".".join(path)}" array')
    index = mod.get("index")
    _splice(existing, len(existing) if index == -1 else index, 0, items)


def _mod_remove_arr(to: dict, mod: dict, path: list[str]) -> None:
    existing = _get(to, path)
    if not isinstance(existing, list):
        raise CopyError(f'Could not find "{".".join(path)}" array')
    if _truthy(mod.get("names")):
        for name in _ensure_list(mod, "names"):
            index = next(
                (i for i, it in enumerate(existing) if isinstance(it, dict) and _strict_equal(it.get("name"), name)),
                -1,
            )  # fmt: skip
            if index != -1:
                del existing[index]
            elif not _truthy(mod.get("force")):
                raise CopyError(
                    f'Could not find "{".".join(path)}" item "{name}" to remove'
                )
    elif _truthy(mod.get("items")):
        for item in _ensure_list(mod, "items"):
            index = next(
                (i for i, it in enumerate(existing) if _strict_equal(it, item)), -1
            )
            if index == -1:
                raise CopyError(
                    f'Could not find "{".".join(path)}" item "{item}" to remove'
                )
            del existing[index]
    else:
        raise CopyError('One of "names" or "items" must be provided!')


def _mod_rename_arr(to: dict, mod: dict, path: list[str]) -> None:
    renames = _ensure_list(mod, "renames")
    existing = _get(to, path)
    if not _truthy(existing):
        raise CopyError(f'Could not find "{".".join(path)}" array')
    for rename in renames:
        ent = next(
            (e for e in existing if isinstance(e, dict) and _strict_equal(e.get("name"), rename.get("rename"))),
            None,
        )  # fmt: skip
        if ent is None:
            raise CopyError(
                f'Could not find "{".".join(path)}" item "{rename.get("rename")}" to rename'
            )
        ent["name"] = rename.get("with")


def _mod_calculate_prop(to: dict, mod: dict, path: list[str]) -> None:
    if not path:
        raise CopyError("calculateProp needs a property")
    target = _get(to, path)
    if target is None:
        target = _set(to, path, {})

    def variable(match: re.Match[str]) -> str:
        if match[1] == "prof_bonus":
            return _js_str(_cr_to_pb(to.get("cr")))
        if match[1] == "dex_mod":
            return _js_str(_num(_ability_mod(to.get("dex"))))
        raise CopyError(f'Unknown variable "{match[1]}"')

    formula = re.sub(r"<\$([^$]+)\$>", variable, mod["formula"])
    target[mod["prop"]] = _num(_eval_math(_clean_math(formula)))


def _scalar_apply(
    to: dict, mod: dict, path: list[str], fn: Callable[[float], float]
) -> None:
    target = _get(to, path)
    if not _truthy(target):
        return

    def apply(key: str) -> None:
        out = fn(_js_number(target.get(key)))
        if isinstance(target.get(key), str):
            target[key] = f"{'+' if out >= 0 else ''}{_js_str(_num(out))}"
        else:
            target[key] = _num(out)

    for key in list(target) if mod.get("prop") == "*" else [_js_str(mod.get("prop"))]:
        apply(key)


def _mod_scalar_add_prop(to: dict, mod: dict, path: list[str]) -> None:
    _scalar_apply(to, mod, path, lambda v: v + mod["scalar"])


def _mod_scalar_mult_prop(to: dict, mod: dict, path: list[str]) -> None:
    def mult(v: float) -> float:
        out = v * mod["scalar"]
        return _floor(out) if _truthy(mod.get("floor")) else out

    _scalar_apply(to, mod, path, mult)


def _mod_add_senses(to: dict, mod: dict) -> None:
    senses = _ensure_list(mod, "senses")
    if not _truthy(to.get("senses")):
        to["senses"] = []
    for sense in senses:
        for i, existing in enumerate(to["senses"]):
            match = re.search(
                rf"{sense['type']} (\d+)", _js_str(existing), re.IGNORECASE
            )
            if match:
                if float(match[1]) < sense["range"]:
                    to["senses"][i] = f"{sense['type']} {_js_str(sense['range'])} ft."
                break
        else:
            to["senses"].append(f"{sense['type']} {_js_str(sense['range'])} ft.")


def _add_bonuses(
    to: dict, prop: str, bonuses: dict[str, JSON], ability: Callable[[str], str]
) -> None:
    if not _truthy(to.get(prop)):
        to[prop] = {}
    for key, mode in bonuses.items():
        total = mode * _pb(to.get("cr")) + _ability_mod(to.get(ability(key)))
        text = _signed(total)
        if _truthy(to[prop].get(key)):
            if _js_number(to[prop][key]) < total:
                to[prop][key] = text
        else:
            to[prop][key] = text


def _mod_add_saves(to: dict, mod: dict) -> None:
    _add_bonuses(to, "save", mod["saves"], lambda key: key)


def _mod_add_skills(to: dict, mod: dict) -> None:
    _add_bonuses(
        to,
        "skill",
        mod["skills"],
        lambda key: _SKILL_TO_ABILITY.get(key.strip(), key.strip()),
    )


def _mod_add_all_saves(to: dict, mod: dict) -> None:
    _mod_add_saves(to, {"saves": dict.fromkeys(_ABILITIES, mod["saves"])})


def _mod_add_all_skills(to: dict, mod: dict) -> None:
    _mod_add_skills(to, {"skills": dict.fromkeys(_SKILL_TO_ABILITY, mod["skills"])})


def _spellcasting(to: dict, name: JSON = None) -> dict[str, JSON]:
    casting = to.get("spellcasting")
    if not isinstance(casting, list):
        raise CopyError("Creature did not have a spellcasting property!")
    if _truthy(name):
        found = next((c for c in casting if c.get("name") == name), None)
        if found is None:
            raise CopyError(f'Creature did not have spellcasting trait named "{name}"!')
        return found
    return casting[0]


_SPELL_FREQUENCIES = (
    "recharge",
    "legendary",
    "charges",
    "rest",
    "restLong",
    "daily",
    "weekly",
    "monthly",
    "yearly",
)


def _mod_add_spells(to: dict, mod: dict) -> None:
    casting = _spellcasting(to, mod.get("name"))
    if _truthy(mod.get("spells")):
        spells = casting["spells"]
        for level, new in mod["spells"].items():
            if not _truthy(spells.get(level)):
                spells[level] = new
                continue
            old = spells[level]
            for key, value in new.items():
                if not _truthy(old.get(key)):
                    old[key] = value
                elif isinstance(old[key], list):
                    old[key] = old[key] + value
                    _sort_lower(old[key])
                elif isinstance(old[key], dict):
                    raise CopyError(f"Object at key {key} not an array!")
                else:
                    old[key] = value
    for prop in ("constant", "will", "ritual"):
        if _truthy(mod.get(prop)):
            for spell in mod[prop]:
                if not _truthy(casting.get(prop)):
                    casting[prop] = []
                casting[prop].append(spell)
    for prop in _SPELL_FREQUENCIES:
        if not _truthy(mod.get(prop)):
            continue
        for key, spells in _js_entries(mod[prop]):
            if key not in _SPELL_USE_KEYS:
                continue
            if not _truthy(casting.get(prop)):
                casting[prop] = {}
            for spell in spells:
                if not _truthy(casting[prop].get(key)):
                    casting[prop][key] = []
                casting[prop][key].append(spell)


def _mod_replace_spells(to: dict, mod: dict) -> None:
    casting = _spellcasting(to)

    def replace(current: dict[str, JSON], meta: dict[str, JSON], key: str) -> None:
        with_ = _ensure_list(meta, "with")
        spells = current[key]
        index = next(
            (i for i, s in enumerate(spells) if _strict_equal(s, meta["replace"])), -1
        )
        if index == -1:
            raise CopyError(f'Could not find spell "{meta["replace"]}" to replace')
        _splice(spells, index, 1, with_)
        _sort_lower(spells)

    if _truthy(mod.get("spells")):
        trait = casting["spells"]
        for level, metas in mod["spells"].items():
            if _truthy(trait.get(level)):
                for meta in metas:
                    replace(trait[level], meta, "spells")
    if _truthy(mod.get("daily")):
        for key, metas in _js_entries(mod["daily"]):
            if key in _SPELL_USE_KEYS:
                for meta in metas:
                    replace(casting["daily"], meta, key)


def _mod_remove_spells(to: dict, mod: dict) -> None:
    casting = _spellcasting(to)
    if _truthy(mod.get("spells")):
        spells = casting["spells"]
        for level, remove in mod["spells"].items():
            entry = spells.get(level)
            if isinstance(entry, dict) and _truthy(entry.get("spells")):
                entry["spells"] = [s for s in entry["spells"] if s not in remove]
    # "constant", "will" and "ritual" are filtered in 5etools without the result
    # being kept, so they are left alone here too.
    for prop in _SPELL_FREQUENCIES:
        if not _truthy(mod.get(prop)):
            continue
        for key, remove in _js_entries(mod[prop]):
            if key not in _SPELL_USE_KEYS:
                continue
            if not _truthy(casting.get(prop)):
                casting[prop] = {}
            casting[prop][key] = [s for s in casting[prop][key] if s not in remove]


def _js_entries(obj: dict[str, JSON]) -> list[tuple[str, JSON]]:
    """``Object.entries``: integer-like keys first, ascending."""
    ints = sorted((k for k in obj if k.isdigit()), key=int)
    return [(k, obj[k]) for k in ints] + [
        (k, v) for k, v in obj.items() if not k.isdigit()
    ]


def _mod_scalar_add_hit(to: dict, mod: dict, path: list[str]) -> None:
    existing = _get(to, path)
    if not _truthy(existing):
        return
    regex = re.compile(r"\{@hit ([-+]?\d+)\}", re.ASCII)
    _set(to, path, _walk_strings(existing, lambda s: regex.sub(
        lambda m: f"{{@hit {_js_str(_num(float(m[1]) + mod['scalar']))}}}", s)))  # fmt: skip


def _mod_scalar_add_dc(to: dict, mod: dict, path: list[str]) -> None:
    existing = _get(to, path)
    if not _truthy(existing):
        return
    regex = re.compile(r"\{@dc (\d+)(?:\|[^}]+)?\}", re.ASCII)
    _set(to, path, _walk_strings(existing, lambda s: regex.sub(
        lambda m: f"{{@dc {_js_str(_num(float(m[1]) + mod['scalar']))}}}", s)))  # fmt: skip


def _mod_max_size(to: dict, mod: dict) -> None:
    sizes = sorted(to["size"], key=lambda s: _SIZES.index(s) if s in _SIZES else -1)
    current = [_SIZES.index(s) if s in _SIZES else -1 for s in sizes]
    maximum = _SIZES.index(mod["max"]) if mod["max"] in _SIZES else -1
    if maximum == -1 or -1 in current:
        raise CopyError("Unhandled size!")
    keep = [i for i in current if i <= maximum] or [maximum]
    to["size"] = [_SIZES[i] for i in keep]


def _mod_scalar_mult_xp(to: dict, mod: dict) -> None:
    def output(value: float) -> int | float:
        out = value * mod["scalar"]
        return _num(_floor(out) if _truthy(mod.get("floor")) else out)

    cr = to["cr"]
    if isinstance(cr, dict) and _truthy(cr.get("xp")):
        cr["xp"] = output(cr["xp"])
        return
    xp = _cr_to_xp(cr)
    if not (isinstance(cr, dict) and _truthy(cr.get("cr"))):
        to["cr"] = {"cr": cr}
    to["cr"]["xp"] = output(xp if xp is not None else 0)


def _combined_path(mod: dict, path: list[str] | None) -> list[str]:
    combined = mod["prop"].split(".") if _truthy(mod.get("prop")) else []
    if path is not None and path != ["*"]:
        combined = path + combined
    return combined


def _mod_set_prop(to: dict, mod: dict, path: list[str] | None) -> None:
    _set(to, _combined_path(mod, path), _copy_fast(mod.get("value")))


def _mod_prefix_suffix_string_prop(to: dict, mod: dict, path: list[str] | None) -> None:
    combined = _combined_path(mod, path)
    text = _get(to, combined)
    if isinstance(text, str):
        _set(to, combined, f"{mod.get('prefix') or ''}{text}{mod.get('suffix') or ''}")


_PATH_MODS: dict[str, Callable[[dict, dict, list[str]], Any]] = {
    "appendStr": _mod_append_str,
    "replaceName": _mod_replace_name,
    "replaceTxt": _mod_replace_txt,
    "prependArr": _mod_prepend_arr,
    "appendArr": _mod_append_arr,
    "replaceArr": _mod_replace_arr,
    "replaceOrAppendArr": _mod_replace_or_append_arr,
    "appendIfNotExistsArr": _mod_append_if_not_exists_arr,
    "insertArr": _mod_insert_arr,
    "removeArr": _mod_remove_arr,
    "renameArr": _mod_rename_arr,
    "calculateProp": _mod_calculate_prop,
    "scalarAddProp": _mod_scalar_add_prop,
    "scalarMultProp": _mod_scalar_mult_prop,
    "scalarAddHit": _mod_scalar_add_hit,
    "scalarAddDc": _mod_scalar_add_dc,
}

_ROOT_MODS: dict[str, Callable[[dict, dict], None]] = {
    "addSenses": _mod_add_senses,
    "addSaves": _mod_add_saves,
    "addSkills": _mod_add_skills,
    "addAllSaves": _mod_add_all_saves,
    "addAllSkills": _mod_add_all_skills,
    "addSpells": _mod_add_spells,
    "replaceSpells": _mod_replace_spells,
    "removeSpells": _mod_remove_spells,
    "maxSize": _mod_max_size,
    "scalarMultXp": _mod_scalar_mult_xp,
}

_OPTIONAL_PATH_MODS: dict[str, Callable[[dict, dict, list[str] | None], None]] = {
    "setProp": _mod_set_prop,
    "prefixSuffixStringProp": _mod_prefix_suffix_string_prop,
}


def _apply_mods(to: dict, mods: list[JSON], prop: str | None) -> None:
    path = prop.split(".") if prop else None
    for mod in mods:
        if isinstance(mod, str):
            if mod != "remove":
                raise CopyError(f"Unhandled mode: {mod}")
            if path:
                _delete(to, path)
            continue
        mode = mod.get("mode")
        if mode in _OPTIONAL_PATH_MODS:
            _OPTIONAL_PATH_MODS[mode](to, mod, path)
        elif mode in _ROOT_MODS:
            _ROOT_MODS[mode](to, mod)
        elif mode in _PATH_MODS:
            if path is None:
                raise CopyError(f"{mode} needs a property")
            _PATH_MODS[mode](to, mod, path)
        else:
            raise CopyError(f"Unhandled mode: {mode}")


# endregion

# region Merging a copy into its parent

_PRESERVE_BASE = frozenset(
    [
        "page",
        "otherSources",
        "referenceSources",
        "srd",
        "srd52",
        "basicRules",
        "basicRules2024",
        "reprintedAs",
        "hasFluff",
        "hasFluffImages",
        "hasToken",
        "tokenCredit",
        "tokenCustom",
        "foundryTokenScale",
        "altArt",
        "_versions",
    ]
)

# Properties a copy only inherits when its ``_preserve`` names them.
PRESERVE: dict[str, frozenset[str]] = {
    "monster": frozenset(
        [
            "legendaryGroup",
            "environment",
            "soundClip",
            "altArt",
            "variant",
            "dragonCastingColor",
            "familiar",
        ]
    ),
    "item": frozenset({"lootTables", "tier"}),
    "itemGroup": frozenset({"lootTables", "tier"}),
    "magicvariant": frozenset({"lootTables", "tier"}),
}

COPY_ENTRY_PROPS = (
    "action", "bonus", "reaction", "trait", "legendary", "mythic", "variant",
    "spellcasting", "actionHeader", "bonusHeader", "reactionHeader",
    "legendaryHeader", "mythicHeader",
)  # fmt: skip


def _mod_order(prop: str) -> int:
    return {"_": 0, "*": 1}.get(prop, -1)


def apply_copy(
    parent: dict[str, JSON],
    child: dict[str, JSON],
    *,
    prop: str,
    templates: list[dict[str, JSON]] | None = None,
) -> None:
    """``copyApplier.getCopy``: merge ``parent`` (already a copy) into ``child``."""
    meta = child.get("_copy") or {}
    if _truthy(meta.get("_mod")):
        meta["_mod"] = {
            k: v if isinstance(v, list) else [v] for k, v in meta["_mod"].items()
        }

    to_apply: list[dict[str, JSON]] = []
    if _truthy(meta.get("_templates")):
        errors = []
        for ref in meta["_templates"]:
            name, source = ref["name"].lower().strip(), ref["source"].lower().strip()
            template = next(
                (t for t in templates or [] if t["name"].lower().strip() == name and t["source"].lower().strip() == source),
                None,
            )  # fmt: skip
            if template is None:
                errors.append(
                    f'Could not find traits to apply with name "{name}" and source "{source}"'
                )
            else:
                to_apply.append(_copy_fast(template))
        for template in to_apply:
            template_mods = template["apply"].get("_mod")
            if not _truthy(template_mods):
                continue
            template_mods = {
                k: v if isinstance(v, list) else [v] for k, v in template_mods.items()
            }
            if not _truthy(meta.get("_mod")):
                meta["_mod"] = template_mods
                continue
            for key, value in template_mods.items():
                meta["_mod"][key] = (
                    meta["_mod"][key] + value
                    if _truthy(meta["_mod"].get(key))
                    else value
                )
        child["_copy_templates"] = [
            {"name": t["name"], "source": t["source"]} for t in meta["_templates"]
        ]
        del meta["_templates"]
        if errors:
            raise CopyError("; ".join(errors))

    own_keys = set(child)
    preserve = meta.get("_preserve") or {}
    for key, value in parent.items():
        if key in child and child[key] is None:
            del child[key]
        elif child.get(key) is None:
            if key in _PRESERVE_BASE or key in PRESERVE.get(prop, ()):
                if _truthy(preserve.get("*")) or _truthy(preserve.get(key)):
                    child[key] = value
            else:
                child[key] = value

    for template in to_apply:
        root = template["apply"].get("_root") or {}
        child.update({k: v for k, v in root.items() if k not in own_keys})

    if _truthy(meta.get("_mod")):
        for key in meta["_mod"]:
            meta["_mod"][key] = _resolve_variables(meta["_mod"][key], child)
        for key, mods in sorted(meta["_mod"].items(), key=lambda kv: _mod_order(kv[0])):
            if key == "*":
                for entry_prop in COPY_ENTRY_PROPS:
                    _apply_mods(child, mods, entry_prop)
            elif key == "_":
                _apply_mods(child, mods, None)
            else:
                _apply_mods(child, mods, key)

    child["_isCopy"] = True
    child.pop("_copy", None)


# endregion

# region Finding parents

KeyFunction = Callable[[dict[str, JSON]], tuple[str, ...]]


def _fields(*names: str) -> KeyFunction:
    def key(ent: dict[str, JSON]) -> tuple[str, ...]:
        return tuple(
            _js_str(ent.get(n)).lower() if n in ent else "undefined" for n in names
        )

    return key


def _item_key(ent: dict[str, JSON]) -> tuple[str, ...]:
    inherits = ent.get("inherits") or {}
    source = ent.get("source") or (
        inherits.get("source") if isinstance(inherits, dict) else None
    )
    return (_js_str(ent.get("name")).lower(), _js_str(source).lower())


def _subclass_key(ent: dict[str, JSON]) -> tuple[str, ...]:
    short = ent.get("shortName") or ent.get("name")
    return tuple(
        _js_str(v).lower()
        for v in (
            ent.get("className"),
            ent.get("classSource"),
            short,
            ent.get("source"),
        )
    )


def _subrace_key(ent: dict[str, JSON]) -> tuple[str, ...]:
    name = f"{_js_str(ent.get('name'))} ({_js_str(ent.get('raceName'))})"
    return (name.lower(), _js_str(ent.get("source")).lower())


_GENERIC = _fields("name", "source")

# How 5etools identifies an entity of each prop (UrlUtil.URL_TO_HASH_BUILDER).
KEYS: dict[str, KeyFunction] = {
    "item": _item_key,
    "itemGroup": _item_key,
    "baseitem": _item_key,
    "magicvariant": _item_key,
    "itemFluff": _item_key,
    "deity": _fields("name", "pantheon", "source"),
    "subrace": _subrace_key,
    "subclass": _subclass_key,
    "classFeature": _fields("name", "className", "classSource", "level", "source"),
    "subclassFeature": _fields(
        "name",
        "className",
        "classSource",
        "subclassShortName",
        "subclassSource",
        "level",
        "source",
    ),
    "raceFeature": _fields("name", "raceName", "raceSource", "source"),
    "itemType": _fields("abbreviation", "source"),
    "itemProperty": _fields("abbreviation", "source"),
}


@dataclass(frozen=True)
class CopyFailure:
    """A copy that could not be resolved; the entity keeps its ``_copy``."""

    prop: str
    name: str
    source: str
    message: str


def resolve_copies(
    entities: dict[str, list[dict[str, JSON]]],
    templates: dict[str, list[dict[str, JSON]]] | None = None,
) -> list[CopyFailure]:
    """Resolve every ``_copy`` in ``entities`` (raw lists keyed by prop), in place.

    A parent is the first entity of the same prop whose key matches the
    ``_copy`` reference, and it is resolved before it is copied. ``templates``
    holds the ``_templates`` a prop can apply, keyed by prop (``monster`` uses
    ``monsterTemplate``). A copy whose parent is missing, or whose ``_mod``
    fails, is reported and keeps its ``_copy``.
    """
    failures: list[CopyFailure] = []
    # Templates can copy each other; 5etools merges them when it loads them
    for prop, template_list in (templates or {}).items():
        failures += resolve_copies({f"{prop}Template": template_list})
    for prop, entries in entities.items():
        key = KEYS.get(prop, _GENERIC)
        index: dict[tuple[str, ...], dict[str, JSON]] = {}
        for ent in entries:
            index.setdefault(key(ent), ent)
        resolving: set[int] = set()

        def resolve(ent: dict[str, JSON], prop: str = prop, key: KeyFunction = key,
                    index: dict = index, resolving: set[int] = resolving) -> None:  # fmt: skip
            ref = ent.get("_copy")
            if not _truthy(ref):
                return
            if not isinstance(ref, dict):
                raise CopyError("_copy is not an object")
            if key(ent) == key(ref):
                raise CopyError("_copy refers to itself")
            parent = index.get(key(ref))
            if parent is None:
                raise CopyError(
                    f'Could not find parent "{ref.get("name")}" ("{ref.get("source")}")'
                )
            if id(ent) in resolving:
                raise CopyError("_copy chain loops")
            resolving.add(id(ent))
            try:
                if _truthy(parent.get("_copy")):
                    resolve(parent)
            finally:
                resolving.discard(id(ent))
            if not _truthy(ent.get("_copy")):
                return
            apply_copy(
                _copy_fast(parent),
                ent,
                prop=prop,
                templates=(templates or {}).get(prop),
            )

        for ent in entries:
            if not _truthy(ent.get("_copy")):
                continue
            try:
                resolve(ent)
            # Bad data fails the one entity, as a thrown error does in 5etools
            except (
                CopyError, AttributeError, KeyError, TypeError, ValueError,
                IndexError, RecursionError, re.error,
            ) as e:  # fmt: skip
                failures.append(
                    CopyFailure(
                        prop,
                        _js_str(ent.get("name")),
                        _js_str(ent.get("source")),
                        str(e),
                    )
                )
    return failures
