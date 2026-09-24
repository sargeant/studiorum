"""What the MCP tools return."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SpellSummary(BaseModel):
    name: str
    source: str
    srd: bool
    level: int
    school: str


class CreatureSummary(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str
    type: str


class ItemSummary(BaseModel):
    name: str
    source: str
    srd: bool
    type: str | None
    rarity: str | None


class SpellResults(BaseModel):
    total: int = Field(description="Matches before the limit")
    results: list[SpellSummary]


class CreatureResults(BaseModel):
    total: int = Field(description="Matches before the limit")
    results: list[CreatureSummary]


class ItemResults(BaseModel):
    total: int = Field(description="Matches before the limit")
    results: list[ItemSummary]


class ContentEntry(BaseModel):
    type: str
    name: str
    source: str
    srd: bool
    data: dict[str, Any] = Field(description="The entry as 5etools models it")


class Publication(BaseModel):
    id: str
    name: str
    kind: Literal["book", "adventure"]
    published: str | None = None
    group: str | None = None
    storyline: str | None = None


class Publications(BaseModel):
    total: int
    publications: list[Publication]
