"""search_rules: actions, conditions, statuses, variant rules, senses and hazards by name and text."""

from __future__ import annotations

from typing import Annotated, Any, Literal, get_args

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.data.models.content import BaseContent, ContentType
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.markdown import render, snippet, strip_tags
from studiorum.mcp.models import RuleResults, RuleSummary, next_offset
from studiorum.mcp.text import fold
from studiorum.mcp.tools.search import LatestOnly, Limit, Offset, split_srd
from studiorum.services import Services

RuleType = Literal[
    "action",
    "condition",
    "status",
    "variantrule",
    "sense",
    "hazard",
    "itemProperty",
    "itemMastery",
]


async def search_rules(
    query: Annotated[
        str, Field(min_length=2, description="Words to find in a rule's name or text")
    ],
    rule_type: RuleType | None = None,
    srd_only: SrdOnly = None,
    latest_only: LatestOnly = True,
    limit: Limit = 10,
    offset: Offset = 0,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> RuleResults:
    """Find rules by name or text: actions, conditions, variant rules, hazards and more.

    The types are actions, conditions, statuses, variant rules, senses,
    hazards (the 2024 Falling and Suffocation are hazards), and weapon
    properties and masteries (Finesse, Sap). Every word must appear in the name or text. A rule named the query comes
    first, then rules with a part named it (the 2024 Grapple and Shove are
    parts of Unarmed Strike), then other name matches. A variant rule that
    matches only in a part that is also an action of its own (the DMG's
    Climb onto a Bigger Creature, in Action Options) gives way to that
    action. Read one in full with get_content.
    """
    srd_only = default_srd if srd_only is None else srd_only
    words = fold(query).split()
    phrase = " ".join(words)
    split = _split_parts(services)
    found: list[tuple[int, str, str, BaseContent]] = []
    # Rules matched only in their split-out parts, with those parts' names
    via_parts: dict[int, set[str]] = {}
    for kind in (rule_type,) if rule_type else get_args(RuleType):
        for rule in services.catalogue.get_all_by_type(ContentType(kind)):
            name = fold(rule.name)
            raw = rule.model_dump(mode="json", by_alias=True, exclude_none=True)
            entries = raw.get("entries") or []
            text = render(entries)
            if not _matches(words, name, text):
                continue
            parts = split.get(name, set()) if kind == "variantrule" else set()
            if parts:
                own = render(_without(entries, parts))
                if _matches(words, name, own):
                    text = own
                else:
                    via_parts[id(rule)] = parts
            if name == phrase:
                rank = 0
            elif phrase in _part_names(raw.get("entries")):
                rank = 1
            elif all(w in name for w in words):
                rank = 2
            else:
                rank = 3
            found.append((rank, kind, text, rule))
    kept, hidden = split_srd([r for *_, r in found], srd_only, latest_only)
    found = [f for f in found if id(f[3]) in set(map(id, kept))]
    names = {fold(rule.name) for *_, rule in found}
    found = [f for f in found if not via_parts.get(id(f[3]), set()) & names]
    found.sort(key=lambda f: (f[0], f[3].name.lower(), f[3].source.abbreviation))
    return RuleResults(
        srd_only=srd_only,
        hidden_by_srd=hidden,
        total=len(found),
        next_offset=next_offset(len(found), offset, limit),
        results=[
            RuleSummary(
                name=rule.name,
                type=kind,
                source=rule.source.abbreviation,
                srd=rule.is_srd,
                snippet=snippet(text, words),
            )
            for _, kind, text, rule in found[offset : offset + limit]
        ],
    )


def _matches(words: list[str], name: str, text: str) -> bool:
    folded = fold(text)
    return all(w in name or w in folded for w in words)


def _split_parts(services: Services) -> dict[str, set[str]]:
    """Variant rules' parts that 5etools also keeps as actions (fromVariant), by
    the variant rule's name, folded."""
    found: dict[str, set[str]] = {}
    for action in services.catalogue.get_all_by_type(ContentType.ACTION):
        parent = action.model_dump(by_alias=True).get("fromVariant")
        if parent:
            found.setdefault(fold(str(parent).split("|")[0]), set()).add(
                fold(action.name)
            )
    return found


def _without(entries: Any, parts: set[str]) -> Any:
    """Entries without the named parts, folded names."""
    if isinstance(entries, list):
        return [
            _without(e, parts)
            for e in entries
            if not (
                isinstance(e, dict)
                and e.get("name")
                and fold(strip_tags(str(e["name"]))) in parts
            )
        ]
    if isinstance(entries, dict):
        return {k: _without(v, parts) for k, v in entries.items()}
    return entries


def _part_names(entries: Any) -> set[str]:
    """The names of the entries inside a rule, folded."""
    found: set[str] = set()

    def visit(entry: Any) -> None:
        if isinstance(entry, list):
            for e in entry:
                visit(e)
        elif isinstance(entry, dict):
            if entry.get("name"):
                found.add(fold(strip_tags(str(entry["name"]))))
            visit(entry.get("entries"))
            visit(entry.get("items"))

    visit(entries)
    return found
