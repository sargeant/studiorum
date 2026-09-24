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
    text: str | None = Field(None, description="The entry as Markdown")
    data: dict[str, Any] | None = Field(
        None, description="The entry as 5etools models it"
    )


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


class EncounterBudget(BaseModel):
    rules: Literal["2024", "2014"]
    party_levels: list[int]
    xp: dict[str, int] = Field(
        description="2024: the most XP for each difficulty. "
        "2014: the least adjusted XP for each difficulty."
    )


class RatedCreature(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str
    xp: int | None = Field(description="XP each; none when the CR has no XP")
    count: int


class EncounterRating(BaseModel):
    rules: Literal["2024", "2014"]
    party_levels: list[int]
    creatures: list[RatedCreature]
    total_xp: int
    multiplier: float = Field(description="2014 only; 1 under 2024 rules")
    adjusted_xp: int
    difficulty: str
    budgets: dict[str, int]


class SuggestedCreature(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str
    xp: int
    type: str
    environment: list[str]


class CreatureSuggestions(BaseModel):
    rules: Literal["2024", "2014"]
    difficulty: str
    count: int
    xp_each: tuple[int, int] = Field(
        description="The XP range per creature that puts the group at this difficulty"
    )
    total: int = Field(description="Matches before the limit")
    results: list[SuggestedCreature]


class SectionRef(BaseModel):
    id: str
    name: str
    depth: int = Field(description="1 for the top level listed")
    chars: int = Field(description="Size in Markdown characters")


class Contents(BaseModel):
    id: str
    name: str
    kind: Literal["book", "adventure"]
    sections: list[SectionRef]


class SectionText(BaseModel):
    publication: str
    id: str
    name: str
    path: list[str] = Field(
        description="The sections this one sits in, outermost first"
    )
    page: int
    pages: int
    text: str = Field(description="Markdown")
    sections: list[SectionRef] = Field(description="Subsections, to read on their own")


class RuleSummary(BaseModel):
    name: str
    type: str
    source: str
    srd: bool
    snippet: str = Field(description="Text around the first match")


class RuleResults(BaseModel):
    total: int = Field(description="Matches before the limit")
    results: list[RuleSummary]
