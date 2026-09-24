"""search_rules: actions, conditions, statuses, variant rules and senses by name and text."""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.core.models.content import BaseContent, ContentType
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.markdown import render
from studiorum.mcp.models import RuleResults, RuleSummary
from studiorum.mcp.tools.search import LatestOnly, Limit, drop_reprinted
from studiorum.services import Services

RuleType = Literal["action", "condition", "status", "variantrule", "sense"]
SNIPPET = 240


async def search_rules(
    query: Annotated[
        str, Field(min_length=2, description="Words to find in a rule's name or text")
    ],
    rule_type: RuleType | None = None,
    srd_only: SrdOnly = None,
    latest_only: LatestOnly = True,
    limit: Limit = 10,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> RuleResults:
    """Find rules by name or text: actions, conditions, statuses, variant rules and senses.

    Every word must appear in the name or text. Name matches come first. The
    2024 rules put some actions elsewhere: grappling is under the Unarmed
    Strike variant rule. Read one in full with get_content.
    """
    srd_only = default_srd if srd_only is None else srd_only
    words = query.lower().split()
    found: list[tuple[int, str, str, BaseContent]] = []
    for kind in (rule_type,) if rule_type else get_args(RuleType):
        for rule in services.omnidexer.get_all_by_type(ContentType(kind)):
            if srd_only and not rule.is_srd:
                continue
            name = rule.name.lower()
            raw = rule.model_dump(mode="json", by_alias=True, exclude_none=True)
            text = render(raw.get("entries") or [])
            if not all(w in name or w in text.lower() for w in words):
                continue
            rank = (
                0
                if name == query.lower()
                else 1
                if all(w in name for w in words)
                else 2
            )
            found.append((rank, kind, text, rule))
    if latest_only:
        kept = set(map(id, drop_reprinted([r for *_, r in found])))
        found = [f for f in found if id(f[3]) in kept]
    found.sort(key=lambda f: (f[0], f[3].name.lower(), f[3].source.abbreviation))
    return RuleResults(
        total=len(found),
        results=[
            RuleSummary(
                name=rule.name,
                type=kind,
                source=rule.source.abbreviation,
                srd=rule.is_srd,
                snippet=_snippet(text, words),
            )
            for _, kind, text, rule in found[:limit]
        ],
    )


def _snippet(text: str, words: list[str]) -> str:
    flat = " ".join(w for w in text.split() if w.strip("#"))
    at = min((i for w in words if (i := flat.lower().find(w)) >= 0), default=0)
    start = max(0, at - SNIPPET // 3)
    piece = flat[start : start + SNIPPET]
    return ("…" if start else "") + piece + ("…" if start + SNIPPET < len(flat) else "")
