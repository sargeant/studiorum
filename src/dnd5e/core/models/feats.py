"""Pydantic models for feats."""

from typing import Any

from pydantic import BaseModel, Field

from .content import BaseContent


class Prerequisite(BaseModel):
    """A prerequisite for a feat."""

    other: str | None = None


class AdditionalSpell(BaseModel):
    """A spell that can be cast in addition to the feat."""

    name: str | None = None
    level: int | None = None
    ability: str | dict[str, Any] | None = None
    innate: dict[str, Any] | None = None
    known: dict[str, Any] | None = None


class Feat(BaseContent):
    """A feat."""

    prerequisite: list[Prerequisite] | None = None
    ability: list[dict[str, int | dict[str, Any]]] | None = None
    additionalSpells: list[AdditionalSpell] | None = Field(
        default=None, alias="additionalSpells"
    )
    entries: list[Any]
