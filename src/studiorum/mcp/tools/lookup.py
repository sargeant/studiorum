"""Lookup tools: one entry in full, and the books and adventures loaded."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from fastmcp.dependencies import Depends
from pydantic import BaseModel, Field

from studiorum.data.class_entries import dereferenced
from studiorum.data.models.adventures import Adventure
from studiorum.data.models.books import Book
from studiorum.data.models.content import BaseContent, ContentType
from studiorum.data.models.itemproperties import ItemProperty
from studiorum.mcp import markdown
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.errors import ClientError, not_found
from studiorum.mcp.layouts import entry_data, to_markdown
from studiorum.mcp.models import (
    PAGE_CHARS,
    ContentBatch,
    ContentEntry,
    ContentMissing,
    ContentResults,
    ContentSummary,
    Publication,
    Publications,
    Reference,
    next_offset,
)
from studiorum.mcp.text import fold
from studiorum.mcp.tools.search import (
    IncludeText,
    LatestOnly,
    Limit,
    Offset,
    drop_reprinted,
    paged,
    reprint_uids,
    split_srd,
)
from studiorum.services import Services

MAX_BATCH = 20

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
    "itemMastery",
    "itemProperty",
    "language",
    "optionalfeature",
    "race",
    "sense",
    "spell",
    "status",
    "subclass",
    "subclassFeature",
    "table",
    "tableGroup",
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
    include_references: Annotated[
        bool,
        Field(
            description="List what the entry's text links to, to read with get_content"
        ),
    ] = True,
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ContentEntry:
    """One entry in full (a statblock, a spell, a class and its features), by type and name.

    A condition comes with the conditions its text names, in turn (Unconscious:
    Incapacitated and Prone).
    """
    srd_only = default_srd if srd_only is None else srd_only
    entry = find_one(services, content_type, name, source, srd_only)
    return _content_entry(
        services, content_type, entry, format, include_references, srd_only
    )


def _content_entry(
    services: Services,
    content_type: str,
    entry: BaseContent,
    format: str,  # noqa: A002 - as get_content names it
    include_references: bool,
    srd_only: bool,
) -> ContentEntry:
    data = _layout_data(services, content_type, entry, srd_only)
    found = markdown.references(data)
    if content_type == "item":
        found += _item_references(services, data)
    references = [
        r
        for r in resolve_references(services, found)
        if (r.name.lower(), (r.source or "").lower())
        != (entry.name.lower(), entry.source.abbreviation.lower())
    ]
    text = None
    if format == "markdown":
        text = to_markdown(content_type, data)
        if content_type == "condition":
            text = "\n\n".join([text, *_included_conditions(services, entry)])
    return ContentEntry(
        type=content_type,
        name=entry.name,
        source=entry.source.abbreviation,
        srd=entry.is_srd,
        text=text,
        data={k: v for k, v in data.items() if k not in _SITE_ONLY}
        if format == "json"
        else None,
        references=references if include_references else [],
    )


# What 5etools keeps for its site's filters, tokens and art, not the rules; the
# tags are read from the text, which the entry keeps
_SITE_ONLY = frozenset(
    {
        "actionTags",
        "altArt",
        "areaTags",
        "conditionInflict",
        "conditionInflictLegendary",
        "conditionInflictSpell",
        "creatureTypeTags",
        "damageInflict",
        "damageTags",
        "damageTagsLegendary",
        "damageTagsSpell",
        "hasFluff",
        "hasFluffImages",
        "hasRefs",
        "hasToken",
        "isNamedCreature",
        "isNpc",
        "languageTags",
        "lootTables",
        "miscTags",
        "reqAttuneTags",
        "savingThrowForced",
        "savingThrowForcedLegendary",
        "savingThrowForcedSpell",
        "senseTags",
        "soundClip",
        "spellcastingTags",
        "tokenCredit",
        "tokenCustom",
        "traitTags",
    }
)


def _included_conditions(services: Services, condition: BaseContent) -> list[str]:
    """The Markdown of the conditions a condition names (Paralyzed: Incapacitated),
    and those they name in turn, each once."""
    seen = {(condition.name.lower(), condition.source.abbreviation.lower())}
    queue = [condition]
    out = []
    while queue:
        data = entry_data(queue.pop(0))
        for ref in resolve_references(services, markdown.references(data)):
            key = (ref.name.lower(), (ref.source or "").lower())
            if ref.type != "condition" or not ref.source or key in seen:
                continue
            seen.add(key)
            found = services.catalogue.find(ContentType.CONDITION, ref.name, ref.source)
            if found is not None:
                queue.append(found)
                out.append(to_markdown("condition", entry_data(found)))
    return out


class Wanted(BaseModel):
    content_type: EntryType
    name: str = Field(description="A name, or a 5etools uid")
    source: str | None = None


async def get_contents(
    items: Annotated[list[Wanted], Field(min_length=1, max_length=MAX_BATCH)],
    format: Annotated[  # noqa: A002 - the name clients see
        Literal["markdown", "json"],
        Field(description="markdown: laid out to read; json: the 5etools data"),
    ] = "markdown",
    offset: Annotated[
        int, Field(ge=0, description="Start at this item, to resume a batch")
    ] = 0,
    include_references: Annotated[
        bool,
        Field(
            description="List what each entry's text links to, to read with get_content"
        ),
    ] = False,
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ContentBatch:
    """Several entries in full, as get_content returns them, up to 24,000 characters.

    When the entries would run past that, the reply stops short and
    next_offset says where to resume. An entry asked for twice comes once.
    """
    srd_only = default_srd if srd_only is None else srd_only
    if offset >= len(items):
        raise ClientError(
            f"offset {offset} is past the end of the {len(items)} item(s) asked for."
        )
    entries: list[ContentEntry] = []
    missing: list[ContentMissing] = []
    seen: set[tuple[str, str, str]] = set()
    size = 0
    for i, item in enumerate(items[offset:], start=offset):
        try:
            found = find_one(
                services, item.content_type, item.name, item.source, srd_only
            )
        except ClientError as e:
            missing.append(ContentMissing(index=i, **item.model_dump(), error=str(e)))
            continue
        key = (item.content_type, found.name, found.source.abbreviation)
        if key in seen:
            continue
        seen.add(key)
        entry = _content_entry(
            services, item.content_type, found, format, include_references, srd_only
        )
        chars = len(entry.text or "") + (
            len(json.dumps(entry.data)) if entry.data else 0
        )
        if entries and size + chars > PAGE_CHARS:
            return ContentBatch(entries=entries, not_found=missing, next_offset=i)
        entries.append(entry)
        size += chars
    return ContentBatch(entries=entries, not_found=missing)


def _layout_data(
    services: Services, content_type: str, entry: BaseContent, srd_only: bool
) -> dict[str, Any]:
    """The data get_content lays out: the entry, a class's subclasses, and a
    feature with the features it refers to in place."""
    data = entry_data(entry)
    if content_type == "class":
        data["subclasses"] = _subclasses(services, entry, srd_only)
    if content_type in ("classFeature", "subclassFeature"):
        data["entries"] = dereferenced(data.get("entries", []), services.catalogue)
    return data


def _item_references(services: Services, data: dict[str, Any]) -> list[dict[str, str]]:
    """An item's weapon properties and mastery, which it names by uid, not by tag."""
    properties = {
        (p.abbreviation.lower(), p.source.abbreviation.lower()): p
        for p in services.catalogue.get_all_by_type(ContentType.ITEM_PROPERTY)
        if isinstance(p, ItemProperty)
    }
    found = []
    for value in data.get("property") or []:
        uid = value.get("uid", "") if isinstance(value, dict) else str(value)
        abbreviation, _, source = uid.partition("|")
        prop = properties.get((abbreviation.lower(), (source or "PHB").lower()))
        if prop is not None:
            found.append(
                {
                    "type": "itemProperty",
                    "name": prop.name,
                    "source": prop.source.abbreviation,
                }
            )
    for value in data.get("mastery") or []:
        uid = value.get("uid", "") if isinstance(value, dict) else str(value)
        name, _, source = uid.partition("|")
        found.append({"type": "itemMastery", "name": name, "source": source or "XPHB"})
    return found


def entry_markdown(
    services: Services, content_type: str, entry: BaseContent, srd_only: bool
) -> str:
    """An entry as get_content's Markdown."""
    return to_markdown(
        content_type, _layout_data(services, content_type, entry, srd_only)
    )


def _subclasses(
    services: Services, cls: BaseContent, srd_only: bool
) -> list[dict[str, str]]:
    """The loaded subclasses of a class, which 5etools keeps apart from it."""
    named = [
        (sub, sub.model_dump(by_alias=True).get("classSource"))
        for sub in services.catalogue.get_all_by_type(ContentType.SUBCLASS)
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
    exact = services.catalogue.find_uid(ctype, uid)
    found = [exact] if exact else []
    fields = _FEATURE_UID_FIELDS.get(ctype)
    if fields:
        parts = uid.split("|")
        wanted = {k: parts[i] for k, i in fields.items() if i < len(parts) and parts[i]}
        for c in services.catalogue.find_all(ctype, parts[0]):
            raw = c.model_dump(by_alias=True)
            if c is not exact and all(
                str(raw.get(k, "")).lower() == v.lower() for k, v in wanted.items()
            ):
                found.append(c)
    return found


def _by_name(services: Services, ctype: ContentType, name: str) -> list[BaseContent]:
    """Entries with this name, else those whose name matches it folded, as "Rothe" does "Rothé"."""
    catalogue = services.catalogue
    found = catalogue.find_all(ctype, name)
    if found:
        return found
    key = fold(name)
    names = {c.name for c in catalogue.get_all_by_type(ctype) if fold(c.name) == key}
    return [c for n in sorted(names) for c in catalogue.find_all(ctype, n)]


def find_one(
    services: Services,
    content_type: str,
    name: str,
    source: str | None,
    srd_only: bool,
) -> BaseContent:
    """The first entry with this type, name and source; a ToolError if none is allowed."""
    catalogue = services.catalogue
    ctype = ContentType(content_type)
    matches = [
        c
        for c in (
            _by_uid(services, ctype, name)
            if "|" in name
            else _by_name(services, ctype, name)
        )
        if source is None or c.source.abbreviation.lower() == source.lower()
    ]
    if not matches:
        every = catalogue.get_all_by_type(ctype)
        names = [c.name for c in every]
        if source is None:
            raise not_found(content_type, name, names)
        elsewhere = sorted(
            {c.source.abbreviation for c in _by_name(services, ctype, name)}
        )
        if elsewhere and "|" not in name:
            raise ClientError(
                f"No {content_type} named '{name}' in {source}; "
                f"there is one in {', '.join(elsewhere)}."
            )
        # Names from the source asked for first, then any source
        raise not_found(
            content_type,
            name,
            [c.name for c in every if c.source.abbreviation.lower() == source.lower()],
            names,
            where=source,
        )
    allowed = [c for c in matches if c.is_srd or not srd_only]
    if not allowed:
        found = ", ".join(c.source.abbreviation for c in matches)
        raise ClientError(
            f"{matches[0].name} ({found}) is not in the SRD; pass srd_only=false."
        )
    latest = drop_reprinted(allowed) or allowed
    best = min(latest, key=_preference)
    if content_type in _FEATURES and "|" not in name:
        _check_one_owner(
            content_type, [c for c in latest if _preference(c) == _preference(best)]
        )
    return best


_FEATURES = ("classFeature", "subclassFeature")


def _check_one_owner(content_type: str, features: list[BaseContent]) -> None:
    """A ClientError if features of this name belong to more than one class or subclass."""
    by_owner: dict[tuple[str, str], BaseContent] = {}
    for feature in features:
        raw = feature.model_dump(by_alias=True)
        owner = (str(raw.get("className")), str(raw.get("subclassShortName")))
        known = by_owner.get(owner)
        if known is None or int(raw.get("level") or 0) < int(
            known.model_dump(by_alias=True).get("level") or 0
        ):
            by_owner[owner] = feature
    if len(by_owner) > 1:
        uids = [content_uid(content_type, f) for f in by_owner.values()]
        raise ClientError(
            f"{len(by_owner)} {content_type}s are named '{features[0].name}'; "
            f"pass one's uid as the name: {', '.join(sorted(str(u) for u in uids))}."
        )


def _preference(content: BaseContent) -> tuple[bool, bool, bool, bool]:
    """How to choose among entries of one name, best first.

    5etools marks 2024 content edition "one"; then the 2024 core rules, the
    2014 core rules, and an entry with text over one that only names itself.
    """
    raw = content.model_dump(by_alias=True, exclude_none=True)
    return (
        getattr(content, "edition", None) != "one",
        not (raw.get("srd52") or raw.get("basicRules2024")),
        not (raw.get("srd") or raw.get("basicRules")),
        not raw.get("entries"),
    )


async def search_content(
    content_type: EntryType,
    query: Annotated[
        str, Field(min_length=1, description="Text the name must contain")
    ],
    srd_only: SrdOnly = None,
    latest_only: LatestOnly = True,
    include_text: IncludeText = False,
    limit: Limit = 20,
    offset: Offset = 0,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ContentResults:
    """Find entries of any type get_content reads by name, e.g. deities, feats, races.

    With include_text, a page is capped at 24,000 characters of text, so it
    can hold fewer results than limit; next_offset is where the rest start.
    """
    srd_only = default_srd if srd_only is None else srd_only
    needle = fold(query)
    named = [
        c
        for c in services.catalogue.get_all_by_type(ContentType(content_type))
        if needle in fold(c.name)
    ]
    kept, hidden = split_srd(named, srd_only, latest_only)
    if latest_only and content_type in _OWNER_FIELDS:
        kept = _drop_reprinted_features(services, content_type, kept)
    kept.sort(
        key=lambda c: (fold(c.name) != needle, c.name.lower(), c.source.abbreviation)
    )
    page, after = paged(
        kept,
        offset,
        limit,
        (lambda c: entry_markdown(services, content_type, c, srd_only))
        if include_text
        else None,
    )
    return ContentResults(
        type=content_type,
        srd_only=srd_only,
        hidden_by_srd=hidden,
        total=len(kept),
        next_offset=after,
        results=[
            ContentSummary(
                name=c.name,
                source=c.source.abbreviation,
                srd=c.is_srd,
                uid=content_uid(content_type, c),
                detail=_detail(content_type, c),
                text=text,
            )
            for c, text in page
        ],
    )


# A feature's class or subclass: its type, and the fields holding its name and source
_OWNER_FIELDS = {
    "classFeature": (ContentType.CLASS, "className", "classSource"),
    "subclassFeature": (ContentType.SUBCLASS, "subclassShortName", "subclassSource"),
}


def _drop_reprinted_features(
    services: Services, content_type: str, found: list[BaseContent]
) -> list[BaseContent]:
    """Leave out features of a reprinted class or subclass that its reprint has too.

    5etools marks the class reprinted (PHB Wizard as XPHB's), not its features.
    """
    owner_type, name_field, source_field = _OWNER_FIELDS[content_type]
    # A reprint uid starts with the name (a subclass's short name), ends with the source
    reprints: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for owner in services.catalogue.get_all_by_type(owner_type):
        if uids := reprint_uids(owner):
            name = str(getattr(owner, "short_name", None) or owner.name).lower()
            reprints[(name, owner.source.abbreviation.lower())] = {
                (u.split("|")[0].lower(), u.split("|")[-1].lower()) for u in uids
            }

    def owned_by(c: BaseContent) -> tuple[str, str, str]:
        raw = c.model_dump(by_alias=True)
        return (
            c.name.lower(),
            str(raw.get(name_field) or "").lower(),
            str(raw.get(source_field) or "").lower(),
        )

    present = {owned_by(c) for c in found}
    return [
        c
        for c in found
        if not any(
            (name, *target) in present
            for name, owned, source in [owned_by(c)]
            for target in reprints.get((owned, source), ())
        )
    ]


def resolve_references(
    services: Services, found: list[dict[str, str]]
) -> list[Reference]:
    """References with the name and source of the entry each one finds, as it has them."""
    out = []
    for ref in found:
        if ref.get("source") and ref["type"] in ContentType._value2member_map_:
            match = services.catalogue.find(
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
    query: Annotated[
        str | None, Field(description="Text the name or id must contain")
    ] = None,
    published_after: Annotated[
        str | None,
        Field(
            pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
            description="Only those published on or after this: YYYY, YYYY-MM or YYYY-MM-DD",
        ),
    ] = None,
    newest_first: Annotated[
        bool, Field(description="Newest first; false for oldest first")
    ] = True,
    limit: Annotated[int, Field(ge=1, le=200)] = 20,
    offset: Offset = 0,
    services: Services = Depends(get_services),
) -> Publications:
    """The books and adventures loaded, newest first unless newest_first=false."""
    catalogue = services.catalogue
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
            for b in catalogue.get_all_by_type(ContentType.BOOK)
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
            for a in catalogue.get_all_by_type(ContentType.ADVENTURE)
            if isinstance(a, Adventure)
        ]
    needle = fold(query or "")
    found = [
        p
        for p in found
        if (needle in fold(p.name) or needle in fold(p.id))
        and (not published_after or (p.published or "") >= published_after)
    ]
    # Stable, so names stay A to Z within a date either way
    found.sort(key=lambda p: p.name)
    found.sort(key=lambda p: p.published or "", reverse=newest_first)
    return Publications(
        total=len(found),
        next_offset=next_offset(len(found), offset, limit),
        publications=found[offset : offset + limit],
    )
