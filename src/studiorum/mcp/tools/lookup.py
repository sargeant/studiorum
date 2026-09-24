"""Lookup tools: one entry in full, and the books and adventures loaded."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from pydantic import Field

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.books import Book
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.mcp.deps import get_services
from studiorum.mcp.errors import not_found
from studiorum.mcp.models import ContentEntry, Publication, Publications
from studiorum.services import Services

# Adventures and books are read by section, not whole.
EntryType = Literal[
    "action",
    "background",
    "class",
    "condition",
    "creature",
    "deity",
    "disease",
    "feat",
    "hazard",
    "item",
    "optionalfeature",
    "race",
    "spell",
    "subclass",
    "trap",
    "variantrule",
    "vehicle",
]


async def get_content(
    content_type: EntryType,
    name: str,
    source: Annotated[
        str | None, Field(description="Source abbreviation; else the first match")
    ] = None,
    srd_only: Annotated[
        bool, Field(description="Only content 5etools marks as in the 2014 or 5.2 SRD")
    ] = True,
    services: Services = Depends(get_services),
) -> ContentEntry:
    """One entry in full (a statblock, a spell's text), found by type and name."""
    entry = find_one(services, content_type, name, source, srd_only)
    return ContentEntry(
        type=content_type,
        name=entry.name,
        source=entry.source.abbreviation,
        srd=entry.is_srd,
        data=entry.model_dump(mode="json", by_alias=True, exclude_none=True)
        | {"source": entry.source.abbreviation},
    )


def find_one(
    services: Services,
    content_type: str,
    name: str,
    source: str | None,
    srd_only: bool,
) -> BaseContent:
    """The first entry with this type, name and source; a ToolError if none is allowed."""
    omnidexer = services.omnidexer
    ctype = ContentType(content_type)
    matches = [
        c
        for c in omnidexer.find_all(ctype, name)
        if source is None or c.source.abbreviation.lower() == source.lower()
    ]
    if not matches:
        names = [c.name for c in omnidexer.get_all_by_type(ctype)]
        raise not_found(content_type, name, names)
    allowed = [c for c in matches if c.is_srd or not srd_only]
    if not allowed:
        found = ", ".join(c.source.abbreviation for c in matches)
        raise ToolError(
            f"{matches[0].name} ({found}) is not in the SRD; pass srd_only=false."
        )
    return allowed[0]


async def list_publications(
    kind: Literal["book", "adventure"] | None = None,
    services: Services = Depends(get_services),
) -> Publications:
    """The books and adventures loaded, oldest first."""
    omnidexer = services.omnidexer
    found: list[Publication] = []
    if kind in (None, "book"):
        found += [
            Publication(
                id=b.source.abbreviation,
                name=b.name,
                kind="book",
                published=b.published,
                group=getattr(b, "group", None),
            )
            for b in omnidexer.get_all_by_type(ContentType.BOOK)
            if isinstance(b, Book)
        ]
    if kind in (None, "adventure"):
        found += [
            Publication(
                id=a.source.abbreviation,
                name=a.name,
                kind="adventure",
                published=a.published,
                group=a.group,
                storyline=a.storyline,
            )
            for a in omnidexer.get_all_by_type(ContentType.ADVENTURE)
            if isinstance(a, Adventure)
        ]
    found.sort(key=lambda p: (p.published or "", p.name))
    return Publications(total=len(found), publications=found)
