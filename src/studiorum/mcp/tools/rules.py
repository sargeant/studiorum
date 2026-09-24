"""search_rules: actions, conditions, statuses, variant rules and senses by name and text."""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.core.models.content import BaseContent, ContentType
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.markdown import render, snippet
from studiorum.mcp.models import RuleResults, RuleSummary
from studiorum.mcp.tools.search import LatestOnly, Limit, split_srd
from studiorum.services import Services

RuleType = Literal["action", "condition", "status", "variantrule", "sense"]


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
    kept, hidden = split_srd([r for *_, r in found], srd_only, latest_only)
    found = [f for f in found if id(f[3]) in set(map(id, kept))]
    found.sort(key=lambda f: (f[0], f[3].name.lower(), f[3].source.abbreviation))
    return RuleResults(
        hidden_by_srd=hidden,
        total=len(found),
        results=[
            RuleSummary(
                name=rule.name,
                type=kind,
                source=rule.source.abbreviation,
                srd=rule.is_srd,
                snippet=snippet(text, words),
            )
            for _, kind, text, rule in found[:limit]
        ],
    )
