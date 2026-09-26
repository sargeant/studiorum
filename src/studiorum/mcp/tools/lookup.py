"""Lookup tools: one entry in full, and the books and adventures loaded."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from pydantic import Field

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.books import Book
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.mcp import markdown
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.errors import not_found
from studiorum.mcp.layouts import to_markdown
from studiorum.mcp.models import (
    ContentEntry,
    ContentResults,
    ContentSummary,
    Publication,
    Publications,
    Reference,
)
from studiorum.mcp.tools.search import (
    LatestOnly,
    Limit,
    Offset,
    drop_reprinted,
    split_srd,
)
from studiorum.services import Services

# Adventures and books are read by section, not whole.
EntryType = Literal[
    "action",
    "background",
    "class",
    "classFeature",
    "condition",
    "creature",
    "deity",
    "disease",
    "feat",
    "hazard",
    "item",
    "language",
    "optionalfeature",
    "race",
    "sense",
    "spell",
    "status",
    "subclass",
    "subclassFeature",
    "trap",
    "variantrule",
    "vehicle",
    "vehicleUpgrade",
]


async def get_content(
    content_type: EntryType,
    name: Annotated[
        str,
        Field(
            description="A name, or a 5etools uid such as "
            "'Spell Mastery|Wizard|XPHB|18' for a class feature"
        ),
    ],
    source: Annotated[
        str | None, Field(description="Source abbreviation; else the latest edition")
    ] = None,
    format: Annotated[  # noqa: A002 - the name clients see
        Literal["markdown", "json"],
        Field(description="markdown: laid out to read; json: the 5etools data"),
    ] = "markdown",
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ContentEntry:
    """One entry in full (a statblock, a spell, a class and its features), by type and name."""
    srd_only = default_srd if srd_only is None else srd_only
    entry = find_one(services, content_type, name, source, srd_only)
    data = entry.model_dump(mode="json", by_alias=True, exclude_none=True) | {
        "source": entry.source.abbreviation
    }
    if content_type == "class":
        data["subclasses"] = _subclasses(services, entry, srd_only)
    return ContentEntry(
        type=content_type,
        name=entry.name,
        source=entry.source.abbreviation,
        srd=entry.is_srd,
        text=to_markdown(content_type, data) if format == "markdown" else None,
        data=data if format == "json" else None,
        references=[
            r
            for r in resolve_references(services, markdown.references(data))
            if (r.name.lower(), (r.source or "").lower())
            != (entry.name.lower(), entry.source.abbreviation.lower())
        ],
    )


def _subclasses(
    services: Services, cls: BaseContent, srd_only: bool
) -> list[dict[str, str]]:
    """The loaded subclasses of a class, which 5etools keeps apart from it."""
    named = [
        (sub, sub.model_dump(by_alias=True).get("classSource"))
        for sub in services.omnidexer.get_all_by_type(ContentType.SUBCLASS)
        if getattr(sub, "class_name", None) == cls.name and (sub.is_srd or not srd_only)
    ]
    # The repo's SRD bundle points its subclasses at the PHB class
    exact = [sub for sub, source in named if source == cls.source.abbreviation]
    return sorted(
        (
            {"name": sub.name, "source": sub.source.abbreviation}
            for sub in exact or [sub for sub, _ in named]
        ),
        key=lambda s: s["name"],
    )


# Where a feature uid keeps the class name and level ("name|class|classSource|level")
_FEATURE_UID_FIELDS = {
    ContentType.CLASS_FEATURE: {"className": 1, "level": 3},
    ContentType.SUBCLASS_FEATURE: {"className": 1, "subclassShortName": 3, "level": 5},
}


def _by_uid(services: Services, ctype: ContentType, uid: str) -> list[BaseContent]:
    """The entry a 5etools uid names, then for features any with the same name, class and level.

    The looser match finds features whose sources differ from their uid's,
    as in the repo's SRD bundle.
    """
    exact = services.omnidexer.find_uid(ctype, uid)
    found = [exact] if exact else []
    fields = _FEATURE_UID_FIELDS.get(ctype)
    if fields:
        parts = uid.split("|")
        wanted = {k: parts[i] for k, i in fields.items() if i < len(parts) and parts[i]}
        for c in services.omnidexer.find_all(ctype, parts[0]):
            raw = c.model_dump(by_alias=True)
            if c is not exact and all(
                str(raw.get(k, "")).lower() == v.lower() for k, v in wanted.items()
            ):
                found.append(c)
    return found


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
        for c in (
            _by_uid(services, ctype, name)
            if "|" in name
            else omnidexer.find_all(ctype, name)
        )
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
    latest = drop_reprinted(allowed) or allowed
    # 5etools marks 2024 content edition "one"; prefer it when nothing else decides
    return sorted(latest, key=lambda c: getattr(c, "edition", None) != "one")[0]


async def search_content(
    content_type: EntryType,
    query: Annotated[
        str, Field(min_length=1, description="Text the name must contain")
    ],
    srd_only: SrdOnly = None,
    latest_only: LatestOnly = True,
    limit: Limit = 20,
    offset: Offset = 0,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ContentResults:
    """Find entries of any type get_content reads by name, e.g. deities, feats, races."""
    srd_only = default_srd if srd_only is None else srd_only
    needle = query.lower()
    named = [
        c
        for c in services.omnidexer.get_all_by_type(ContentType(content_type))
        if needle in c.name.lower()
    ]
    kept, hidden = split_srd(named, srd_only, latest_only)
    kept.sort(
        key=lambda c: (c.name.lower() != needle, c.name.lower(), c.source.abbreviation)
    )
    return ContentResults(
        type=content_type,
        srd_only=srd_only,
        hidden_by_srd=hidden,
        total=len(kept),
        results=[
            ContentSummary(
                name=c.name,
                source=c.source.abbreviation,
                srd=c.is_srd,
                uid=content_uid(content_type, c),
                detail=_detail(content_type, c),
            )
            for c in kept[offset : offset + limit]
        ],
    )


def resolve_references(
    services: Services, found: list[dict[str, str]]
) -> list[Reference]:
    """References with the name and source of the entry each one finds, as it has them."""
    out = []
    for ref in found:
        if ref.get("source") and ref["type"] in ContentType._value2member_map_:
            match = services.omnidexer.find(
                ContentType(ref["type"]), ref["name"], ref["source"]
            )
            if match is not None:
                ref = ref | {"name": match.name, "source": match.source.abbreviation}
        out.append(Reference(**ref))
    return out


def content_uid(content_type: str, content: BaseContent) -> str | None:
    """The 5etools uid for types whose name and source don't identify one entry."""
    raw = content.model_dump(by_alias=True)
    fields = {
        "deity": ("name", "pantheon", "source"),
        "classFeature": ("name", "className", "classSource", "level", "source"),
        "subclassFeature": (
            "name",
            "className",
            "classSource",
            "subclassShortName",
            "subclassSource",
            "level",
            "source",
        ),  # fmt: skip
        "subclass": ("shortName", "className", "classSource", "source"),
    }.get(content_type)
    if fields is None:
        return None
    raw["source"] = content.source.abbreviation
    return "|".join(str(raw.get(f) or "") for f in fields)


def _detail(content_type: str, content: BaseContent) -> str | None:
    raw = content.model_dump(by_alias=True)
    if content_type == "deity":
        return raw.get("pantheon")
    if content_type in ("classFeature", "subclassFeature"):
        owner = raw.get("subclassShortName") or raw.get("className")
        return f"Level {raw.get('level')} {owner}" if owner else None
    if content_type == "subclass":
        return raw.get("className")
    return None


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
                id=b.id or b.source.abbreviation,
                source=b.source.abbreviation,
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
                id=a.id or a.source.abbreviation,
                source=a.source.abbreviation,
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
