"""Specific magic items from generic variants: "+3 Armor" and "Plate Armor" make "+3 Plate Armor".

A port of 5etools' ``Renderer.item._createSpecificVariants`` (``js/render.js``).
5etools builds these when the items page loads rather than shipping them, so
the loader builds them the same way. ``tests/magic_variants/variants.mjs``
runs 5etools' own code as the oracle.
"""

from __future__ import annotations

import ast
import copy
import operator
import re
from collections.abc import Callable
from typing import Any

from ..logging import get_logger

logger = get_logger(__name__)

type Raw = dict[str, Any]

# Inherited props a generic variant doesn't copy onto itself
_SELF_BLOCKLIST = {
    "entries",
    "propertyAdd",
    "namePrefix",
    "nameSuffix",
    "propertyRemove",
}
# Title case, as 5etools writes them outside its "classic" style
_DAMAGE_TYPES = {"A": "Acid", "B": "Bludgeoning", "C": "Cold", "F": "Fire", "O": "Force", "L": "Lightning", "N": "Necrotic", "P": "Piercing", "I": "Poison", "Y": "Psychic", "R": "Radiant", "S": "Slashing", "T": "Thunder"}  # fmt: skip
_CORE_SOURCES = {"PHB", "XPHB", "DMG", "XDMG"}
_VULN_RESIST_IMMUNE = ("vulnerable", "resist", "immune")
_TEMPLATE = re.compile(r"\{=([^}/]+)(?:/([a-z]+))?\}")
_EXPRESSION = re.compile(r"\[\[([^\]]+)]]")


def expand(base_items: list[Raw], generic_variants: list[Raw]) -> list[Raw]:
    """Every specific variant 5etools makes from these base items and generic variants."""
    generics = [_with_inherited(g) for g in generic_variants if "inherits" in g]
    out = []
    for base in base_items:
        if base.get("packContents"):
            continue
        for generic in generics:
            if not _edition_match(base, generic):
                continue
            if not any(
                _matches(base, r, every=True) for r in generic.get("requires", [])
            ):
                continue
            if _matches(base, generic.get("excludes"), every=False):
                continue
            out.append(_specific(base, generic))
    return out


def _with_inherited(generic: Raw) -> Raw:
    """A copy of a generic variant with its inherited props applied to itself."""
    generic = copy.deepcopy(generic)
    inherits = generic["inherits"]
    for prop, value in inherits.items():
        if prop in _SELF_BLOCKLIST:
            continue
        if value is None:
            generic.pop(prop, None)
        elif isinstance(generic.get(prop), list) and isinstance(value, list):
            generic[prop] = generic[prop] + value
        else:
            generic[prop] = value
    if not generic.get("entries") and inherits.get("entries"):
        generic["entries"] = apply_properties(inherits["entries"], inherits)
    if inherits.get("propertyAdd"):
        generic["property"] = [*generic.get("property", []), *inherits["propertyAdd"]]
    if generic.get("requires") and isinstance(generic["requires"], dict):
        generic["requires"] = [generic["requires"]]
    return generic


def _edition_match(base: Raw, generic: Raw) -> bool:
    """5etools' table: a 2014 base item takes 2014 variants, a 2024 one takes the rest."""
    base_edition, generic_edition = base.get("edition"), generic.get("edition")
    if base_edition == generic_edition:
        return True
    if base_edition == "classic":
        return False
    if base_edition is None:
        return True
    return generic_edition != "classic"


def _matches(candidate: Any, requirements: Any, *, every: bool) -> bool:
    if not isinstance(candidate, dict) or not isinstance(requirements, dict):
        return False
    for key, requirement in requirements.items():
        hit = _value_matches(candidate.get(key), requirement, every=every)
        if every and not hit:
            return False
        if not every and hit:
            return True
    return every


def _value_matches(value: Any, requirement: Any, *, every: bool) -> bool:
    if isinstance(requirement, list):
        if isinstance(value, list):
            return any(v in requirement for v in value)
        return value in requirement
    if isinstance(requirement, dict):
        return _matches(value, requirement, every=every)
    if isinstance(value, list):
        return requirement in value
    return bool(requirement == value)


def _specific(base: Raw, generic: Raw) -> Raw:
    inherits = generic["inherits"]
    item = copy.deepcopy(base)
    for prop in ("value", "srd", "srd52", "basicRules", "basicRules2024", "page",
                 "reprintedAs", "referenceSources", "hasFluff", "hasFluffImages"):  # fmt: skip
        item.pop(prop, None)
    item["baseItem"] = f"{base['name']}|{base['source']}".lower()
    entries = list(item.get("entries") or [])
    # Removals first, so a suffix can replace what a removal took out
    for prop, value in sorted(inherits.items(), key=lambda kv: "Remove" not in kv[0]):
        match prop:
            case "namePrefix":
                item["name"] = f"{value}{item['name']}"
            case "nameSuffix":
                item["name"] = f"{item['name']}{value}"
            case "nameRemove":
                item["name"] = item["name"].replace(value, "")
            case "entries":
                entries[0:0] = apply_properties(value, _injectable(base, inherits))
            case "vulnerable" | "resist" | "immune":
                pass
            case "conditionImmune":
                item[prop] = list(dict.fromkeys([*item.get(prop, []), *value]))
            case "weightExpression" | "valueExpression":
                result = _evaluate(value, base, item)
                if result is not None:
                    item["weight" if prop == "weightExpression" else "value"] = result
            case "barding":
                item["bardingType"] = base.get("type")
            case "propertyAdd":
                have = [_uid(p) for p in item.get("property", [])]
                item["property"] = [
                    *item.get("property", []),
                    *(p for p in value if _uid(p) not in have),
                ]
            case "propertyRemove":
                kept = [p for p in item.get("property", []) if _uid(p) not in value]
                if kept:
                    item["property"] = kept
                else:
                    item.pop("property", None)
            case _:
                item[prop] = copy.deepcopy(value)
    _merge_vulnerable_resist_immune(item, inherits)
    for prop in ("hasFluff", "hasFluffImages"):
        if generic.get(prop):
            item[prop] = generic[prop]
    item["genericVariant"] = {"name": generic["name"], "source": generic["source"]}
    if base["source"] not in _CORE_SOURCES:
        page = f", page {base['page']}" if base.get("page") else ""
        entries.insert(
            0,
            f"{{@note The {{@item {base['name']}|{base['source']}|base item}} "
            f"can be found in {base['source']}{page}.}}",
        )
    if entries:
        item["entries"] = entries
    return item


def _uid(prop: Any) -> Any:
    return prop.get("uid") if isinstance(prop, dict) else prop


def _injectable(base: Raw, inherits: Raw) -> Raw:
    props = {
        "baseName": base["name"],
        "dmgType": _DAMAGE_TYPES.get(str(base.get("dmgType"))),
    }
    for key in ("bonusAc", "bonusWeapon", "bonusWeaponAttack", "bonusWeaponDamage",
                "bonusWeaponCritDamage", "bonusSpellAttack", "bonusSpellSaveDc",
                "bonusSavingThrow"):  # fmt: skip
        props[key] = inherits.get(key)
    return props


def apply_properties(entries: Any, props: Raw) -> Any:
    """Fill ``{=baseName/l}``-style templates in every string, as 5etools' applyAllProperties."""
    if isinstance(entries, str):
        return _TEMPLATE.sub(lambda m: _fill(m, props), entries)
    if isinstance(entries, list):
        return [apply_properties(e, props) for e in entries]
    if isinstance(entries, dict):
        return {k: apply_properties(v, props) for k, v in entries.items()}
    return entries


def _fill(match: re.Match[str], props: Raw) -> str:
    value = props.get(match.group(1))
    if value is None:
        logger.debug(f"No value for {match.group(0)}")
        return match.group(0)
    text = str(value)
    # 5etools applies the modifiers in the order written
    for modifier in match.group(2) or "":
        match modifier:
            case "a":
                text = "an" if text[:1].lower() in "aeiou" else "a"
            case "l":
                text = text.lower()
            case "t":
                text = text.title()
            case "u":
                text = text.upper()
    return text


_OPERATORS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _evaluate(expression: str, base: Raw, item: Raw) -> float | int | None:
    """``[[baseItem.value]] * 4`` with the values filled in, or None when one is missing."""

    def value(m: re.Match[str]) -> str:
        path = m.group(1).split(".")
        source = base if path[0] == "baseItem" else item
        found: Any = source
        for key in path[1:] if path[0] in ("item", "baseItem") else path:
            found = found.get(key) if isinstance(found, dict) else None
        return str(found) if isinstance(found, int | float) else "None"

    text = _EXPRESSION.sub(value, expression)
    try:
        return _arithmetic(ast.parse(text, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None


def _arithmetic(node: ast.expr) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        result = _OPERATORS[type(node.op)](
            _arithmetic(node.left), _arithmetic(node.right)
        )
        return (
            int(result) if isinstance(result, float) and result.is_integer() else result
        )
    raise ValueError(f"Not arithmetic: {ast.dump(node)}")


def _merge_vulnerable_resist_immune(item: Raw, inherits: Raw) -> None:
    """A damage type a variant grants leaves the other two lists, as in 5etools."""
    from_base = {p: list(item[p]) for p in _VULN_RESIST_IMMUNE if item.get(p)}
    for prop in _VULN_RESIST_IMMUNE:
        if prop not in inherits:
            continue
        granted = inherits[prop]
        if granted is None:
            from_base.pop(prop, None)
            continue
        names = {g for g in granted if isinstance(g, str)} | {
            s
            for g in granted
            if isinstance(g, dict)
            for s in g.get(prop, [])
            if isinstance(s, str)
        }
        for other in _VULN_RESIST_IMMUNE:
            if other == prop or other not in from_base:
                continue
            from_base[other] = [
                v for v in from_base[other] if not (isinstance(v, str) and v in names)
            ]
            if not from_base[other]:
                del from_base[other]
    for prop in _VULN_RESIST_IMMUNE:
        combined = [*from_base.get(prop, []), *(inherits.get(prop) or [])]
        if combined:
            unique: list[Any] = []
            for v in combined:
                if v not in unique:
                    unique.append(v)
            item[prop] = unique
        else:
            item.pop(prop, None)
