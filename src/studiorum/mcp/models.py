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


class Filtered(BaseModel):
    srd_only: bool = Field(True, description="Whether this call kept to the SRD")
    hidden_by_srd: int = Field(
        0,
        description="Matches left out because they aren't SRD; srd_only=false shows them",
    )


class SpellResults(Filtered):
    total: int = Field(description="Matches before the limit")
    results: list[SpellSummary]


class CreatureResults(Filtered):
    total: int = Field(description="Matches before the limit")
    results: list[CreatureSummary]


class ItemResults(Filtered):
    total: int = Field(description="Matches before the limit")
    results: list[ItemSummary]


class Reference(BaseModel):
    """Something the text links to: content for get_content, or a section for read_section."""

    type: str = Field(description="A get_content type, or 'section'")
    name: str = Field(description="The name, or a uid for class and subclass features")
    source: str | None = None
    section_id: str | None = Field(
        None, description="For a section in this publication"
    )
    publication: str | None = Field(
        None, description="For a book or adventure, its id for get_table_of_contents"
    )


class ContentEntry(BaseModel):
    type: str
    name: str
    source: str
    srd: bool
    text: str | None = Field(None, description="The entry as Markdown")
    data: dict[str, Any] | None = Field(
        None, description="The entry as 5etools models it"
    )
    references: list[Reference] = Field(
        default_factory=list, description="What the entry's text links to"
    )


class Publication(BaseModel):
    id: str
    source: str = Field(description="The source abbreviation its content carries")
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
    notes: list[str] = Field(default_factory=list, description="Editions to check")


class SuggestedCreature(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str
    xp: int
    type: str
    environment: list[str]


class CreatureSuggestions(Filtered):
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
    statblocks: list[str] | None = Field(
        None, description="Set when the section holds only these statblocks"
    )


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
    references: list[Reference] = Field(
        default_factory=list, description="What this page links to"
    )


class RuleSummary(BaseModel):
    name: str
    type: str
    source: str
    srd: bool
    snippet: str = Field(description="Text around the first match")


class RuleResults(Filtered):
    total: int = Field(description="Matches before the limit")
    results: list[RuleSummary]


class SectionMatch(BaseModel):
    id: str
    name: str
    path: list[str] = Field(
        description="The sections this one sits in, outermost first"
    )
    chars: int = Field(description="Size in Markdown characters")
    snippet: str = Field(description="Text around the first match")


class SectionMatches(BaseModel):
    publication: str
    total: int = Field(description="Matches before the limit")
    results: list[SectionMatch]


class ContentSummary(BaseModel):
    name: str
    source: str
    srd: bool
    uid: str | None = Field(
        None, description="Pass as get_content's name when the name and source repeat"
    )
    detail: str | None = Field(None, description="What tells it apart, e.g. a pantheon")


class ContentResults(Filtered):
    type: str
    total: int = Field(description="Matches before the limit")
    results: list[ContentSummary]
