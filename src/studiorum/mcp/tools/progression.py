"""A class's table by level: proficiency bonus, features and its own columns."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.data.class_entries import class_progression
from studiorum.data.models.content import BaseContent, ContentType
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.errors import not_found
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
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ClassProgression:
    """A class's table by level: proficiency bonus, features, spell slots and the rest.

    Features come with 5etools uids for get_content. With a subclass, its
    table columns (an Eldritch Knight's spell slots) and features are added.
    """
    srd_only = default_srd if srd_only is None else srd_only
    cls = find_one(services, "class", class_name, source, srd_only)
    raw = cls.model_dump(by_alias=True, exclude_none=True)
    sub = _subclass(services, cls, subclass, srd_only) if subclass else None
    progression = class_progression(
        raw, sub.model_dump(by_alias=True, exclude_none=True) if sub else None
    )
    labels = _labels([(c.label, c.title) for c in progression.columns])
    return ClassProgression(
        name=cls.name,
        source=cls.source.abbreviation,
        srd=cls.is_srd,
        subclass=sub.name if sub else None,
        subclass_source=sub.source.abbreviation if sub else None,
        columns=labels,
        levels=[
            ProgressionLevel(
                level=row.level,
                proficiency_bonus=row.proficiency_bonus,
                features=[_feature(uid) for uid in row.features],
                subclass_features=[_feature(uid) for uid in row.subclass_features],
                columns=dict(zip(labels, map(cell_text, row.cells), strict=True)),
            )
            for row in progression.levels
            if level is None or row.level == level
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


def _feature(uid: str) -> FeatureRef:
    return FeatureRef(name=uid.split("|")[0], uid=uid)


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
