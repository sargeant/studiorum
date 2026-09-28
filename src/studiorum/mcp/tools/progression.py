"""A class's table by level: proficiency bonus, features and its own columns."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.data.class_entries import class_progression, nested_features
from studiorum.data.models.content import BaseContent, ContentType
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.errors import ClientError, not_found
from studiorum.mcp.markdown import strip_tags
from studiorum.mcp.models import ClassProgression, FeatureRef, ProgressionLevel
from studiorum.mcp.tools.lookup import find_one
from studiorum.mcp.tools.search import drop_reprinted
from studiorum.services import Services


async def get_class_progression(
    class_name: Annotated[str, Field(description="A class, e.g. Wizard")],
    source: Annotated[
        str | None, Field(description="Source abbreviation; else the latest edition")
    ] = None,
    subclass: Annotated[
        str | None,
        Field(
            description="A subclass's name or short name, e.g. Eldritch Knight, "
            "for its columns and features"
        ),
    ] = None,
    level: Annotated[
        int | None, Field(ge=1, le=20, description="One level; else all 20")
    ] = None,
    subclass_only: Annotated[
        bool,
        Field(
            description="With a subclass: only the levels it gains features at, "
            "and only its own columns"
        ),
    ] = False,
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ClassProgression:
    """A class's table by level: proficiency bonus, features, spell slots and the rest.

    Features come with 5etools uids for get_content. With a subclass, its
    table columns (an Eldritch Knight's spell slots) and features are added.
    Each level's cells line up with columns.
    """
    srd_only = default_srd if srd_only is None else srd_only
    if subclass_only and not subclass:
        raise ClientError("subclass_only needs a subclass.")
    cls = find_one(services, "class", class_name, source, srd_only)
    raw = cls.model_dump(by_alias=True, exclude_none=True)
    sub = _subclass(services, cls, subclass, srd_only) if subclass else None
    progression = class_progression(
        raw, sub.model_dump(by_alias=True, exclude_none=True) if sub else None
    )
    labels = _labels([(c.label, c.title) for c in progression.columns])
    only_sub = sub is not None and subclass_only
    # The subclass's columns follow the class's
    first = len(class_progression(raw).columns) if only_sub else 0
    return ClassProgression(
        name=cls.name,
        source=cls.source.abbreviation,
        srd=cls.is_srd,
        subclass=sub.name if sub else None,
        subclass_source=sub.source.abbreviation if sub else None,
        columns=labels[first:],
        levels=[
            ProgressionLevel(
                level=row.level,
                proficiency_bonus=row.proficiency_bonus,
                features=None
                if only_sub
                else _features(services, "classFeature", row.features) or None,
                subclass_features=_features(
                    services, "subclassFeature", row.subclass_features
                )
                or None,
                cells=[cell_text(c) for c in row.cells[first:]],
            )
            for row in progression.levels
            if (level is None or row.level == level)
            and (row.subclass_features or not only_sub)
        ],
    )


def _subclass(
    services: Services, cls: BaseContent, wanted: str, srd_only: bool
) -> BaseContent:
    """The class's subclass by name or short name, of the class's source if there is one."""
    ours = [
        sub
        for sub in services.catalogue.get_all_by_type(ContentType.SUBCLASS)
        if getattr(sub, "class_name", None) == cls.name and (sub.is_srd or not srd_only)
    ]
    key = wanted.lower()
    named = [
        sub
        for sub in ours
        if key in (sub.name.lower(), str(getattr(sub, "short_name", "") or "").lower())
    ]
    # The repo's SRD bundle points its subclasses at the PHB class
    same = [
        sub
        for sub in named
        if sub.model_dump(by_alias=True).get("classSource") == cls.source.abbreviation
    ]
    found = drop_reprinted(same or named)
    if not found:
        raise not_found(f"{cls.name} subclass", wanted, [sub.name for sub in ours])
    return found[0]


def _labels(columns: list[tuple[str, str | None]]) -> list[str]:
    """Column labels as text; a label that repeats is named with its group's title."""
    labels = [strip_tags(label) for label, _ in columns]
    return [
        f"{strip_tags(title)} {label}" if labels.count(label) > 1 and title else label
        for label, (_, title) in zip(labels, columns, strict=True)
    ]


def _features(services: Services, kind: str, uids: list[str]) -> list[FeatureRef]:
    """Features by uid, each followed by the features it refers to (Evoker's
    Evocation Savant and Potent Cantrip)."""
    out = []
    for uid in uids:
        out.append(_feature(kind, uid))
        for child_kind, child in nested_features(
            uid, ContentType(kind), services.catalogue
        ):
            out.append(_feature(child_kind.value, child))
    return out


def _feature(kind: str, uid: str) -> FeatureRef:
    return FeatureRef(name=uid.split("|")[0], uid=full_uid(kind, uid))


def full_uid(kind: str, uid: str) -> str:
    """A feature uid with the sources 5etools leaves to default filled in.

    A class's source defaults to PHB and a feature's to its class's (or
    subclass's), as in 5etools' unpackUidClassFeature.
    """
    parts = uid.split("|")
    if kind == "classFeature":
        name, cls, cls_source, level, source = (parts + [""] * 5)[:5]
        cls_source = cls_source or "PHB"
        return "|".join((name, cls, cls_source, level, source or cls_source))
    name, cls, cls_source, short, sub_source, level, source = (parts + [""] * 7)[:7]
    sub_source = sub_source or "PHB"
    return "|".join(
        (name, cls, cls_source or "PHB", short, sub_source, level, source or sub_source)
    )


def cell_text(cell: Any) -> str:
    """A class table cell as 5etools shows it: 0 as a dash, objects rendered."""
    if cell == 0:
        return "—"
    if isinstance(cell, dict):
        value = cell.get("value", 0)
        match cell.get("type"):
            case "bonus":
                return f"{'' if value < 0 else '+'}{value}"
            case "bonusSpeed":
                return "—" if value == 0 else f"{'' if value < 0 else '+'}{value} ft."
            case "dice":
                return _dice(cell)
    return strip_tags(str(cell))


def _dice(cell: dict[str, Any]) -> str:
    """5etools' getEntryDiceDisplayText."""
    if cell.get("displayText"):
        return str(cell["displayText"])
    if cell.get("successThresh") is not None:
        return f"{cell['successThresh']} percent"
    rolls = cell.get("toRoll")
    if isinstance(rolls, str):
        return rolls
    # Renderer.legacyDiceToString
    text = ""
    for r in rolls or []:
        sign = "-" if r.get("neg") else "" if not text else "+"
        mod = r.get("mod")
        text += f"{sign}{r.get('number') or 1}d{r.get('faces')}"
        text += (f"+{mod}" if mod > 0 else str(mod)) if mod else ""
    return text
