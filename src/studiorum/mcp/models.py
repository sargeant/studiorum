"""What the MCP tools return."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# The most Markdown one reply carries (about 6,000 tokens)
PAGE_CHARS = 24_000


def _empty(value: object) -> bool:
    return value is None or value == [] or value == {}


def optional(description: str) -> Any:
    """A field left out of the reply when it's None, rather than sent as null."""
    return Field(None, description=description, exclude_if=_empty)


def listed(description: str) -> Any:
    """A list left out of the reply when it's empty."""
    return Field(default_factory=list, description=description, exclude_if=_empty)


NextOffset = Annotated[
    int | None,
    Field(
        description="The offset of the next page; left out on the last",
        exclude_if=_empty,
    ),
]


def next_offset(total: int, offset: int, shown: int) -> int | None:
    """Where the page after ``shown`` results from ``offset`` starts, if any remain."""
    return offset + shown if offset + shown < total else None


class SpellSummary(BaseModel):
    name: str
    source: str
    srd: bool
    level: int
    school: str
    text: str | None = optional("As Markdown, with include_text")


class CreatureSummary(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str | None = optional("Left out when it scales with a spell or level")
    type: str = Field(description='e.g. humanoid, or "celestial | fey" for a choice')
    text: str | None = optional("As Markdown, with include_text")


class ItemSummary(BaseModel):
    name: str
    source: str
    srd: bool
    type: str | None = optional("Left out when 5etools gives none")
    rarity: str | None = optional("Left out when 5etools gives none")
    text: str | None = optional("As Markdown, with include_text")


class Filtered(BaseModel):
    srd_only: bool = Field(True, description="Whether this call kept to the SRD")
    hidden_by_srd: int = Field(
        0,
        description="Matches left out because they aren't SRD; srd_only=false shows them",
    )


class SpellResults(Filtered):
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[SpellSummary] = listed("Left out when nothing matched")


class CreatureResults(Filtered):
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[CreatureSummary] = listed("Left out when nothing matched")


class ItemResults(Filtered):
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[ItemSummary] = listed("Left out when nothing matched")


class Reference(BaseModel):
    """Something the text links to: content for get_content, or a section for read_section."""

    type: str = Field(description="A get_content type, or 'section'")
    name: str = Field(description="The name, or a uid for class and subclass features")
    source: str | None = optional("The source, when the link names one")
    section_id: str | None = optional("For a section in this publication")
    publication: str | None = optional(
        "For a book or adventure, its id for get_table_of_contents"
    )


class ContentEntry(BaseModel):
    type: str
    name: str
    source: str
    srd: bool
    text: str | None = optional("The entry as Markdown, with format=markdown")
    data: dict[str, Any] | None = optional(
        "The entry as 5etools models it, with format=json"
    )
    references: list[Reference] = listed(
        "What the entry's text links to, with include_references; "
        "left out when it links to nothing"
    )


class ContentMissing(BaseModel):
    index: int = Field(description="Its place in the items asked for, from 0")
    content_type: str
    name: str
    source: str | None = optional("The source asked for")
    error: str


class ContentBatch(BaseModel):
    entries: list[ContentEntry] = listed("Left out when none was found")
    not_found: list[ContentMissing] = listed(
        "Requests that found nothing, and why; left out when all were found"
    )
    next_offset: int | None = optional(
        "Where to resume when the size cap stopped short; left out when it didn't"
    )


class Publication(BaseModel):
    id: str
    source: str = Field(description="The source abbreviation its content carries")
    name: str
    kind: Literal["book", "adventure"]
    published: str | None = optional("YYYY-MM-DD")
    group: str | None = optional("5etools' grouping, e.g. core or supplement")
    storyline: str | None = optional("The storyline an adventure belongs to")


class Publications(BaseModel):
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    publications: list[Publication] = listed("Left out when nothing matched")


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
    cr: str | None = optional("Left out when it scales with a spell or level")
    xp: int | None = optional("XP each; left out when the CR has no XP")
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
    notes: list[str] = listed("Editions to check; left out when none")


class SuggestedCreature(BaseModel):
    name: str
    source: str
    srd: bool
    cr: str | None = optional("Left out when it scales with a spell or level")
    xp: int
    type: str
    environment: list[str] = listed("Left out when 5etools gives none")


class CreatureSuggestions(Filtered):
    rules: Literal["2024", "2014"]
    difficulty: str
    count: int
    xp_each: tuple[int, int] = Field(
        description="The XP range per creature that puts the group at this difficulty"
    )
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[SuggestedCreature] = listed("Left out when nothing matched")


class SectionRef(BaseModel):
    id: str
    name: str
    depth: int = Field(description="1 for the top level listed")
    chars: int = Field(description="Size in Markdown characters")
    statblocks: list[str] = listed("Set when the section holds only these statblocks")


class Contents(BaseModel):
    id: str
    name: str
    kind: Literal["book", "adventure"]
    total: int = Field(description="Sections at the depth asked for, before the limit")
    next_offset: NextOffset = None
    sections: list[SectionRef] = listed("Left out when there are none")


class SectionText(BaseModel):
    publication: str
    id: str
    name: str
    path: list[str] = listed(
        "The sections this one sits in, outermost first; left out at the top level"
    )
    page: int
    pages: int
    text: str = Field(description="Markdown")
    sections: list[SectionRef] = listed(
        "Subsections too long for this text, which names them; read them on their own"
    )
    references: list[Reference] = listed(
        "What this page links to, with include_references; left out when nothing"
    )


class RuleSummary(BaseModel):
    name: str
    type: str
    source: str
    srd: bool
    snippet: str = Field(description="Text around the first match")


class RuleResults(Filtered):
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[RuleSummary] = listed("Left out when nothing matched")


class SectionMatch(BaseModel):
    publication: str = Field(description="The book or adventure id")
    id: str
    name: str
    path: list[str] = listed(
        "The sections this one sits in, outermost first; left out at the top level"
    )
    chars: int | None = optional("Size in Markdown characters; not with names_only")
    snippet: str | None = optional("Text around the first match; not with names_only")


class SectionMatches(BaseModel):
    publication: str | None = optional("Left out when every one was searched")
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[SectionMatch] = listed("Left out when nothing matched")


class ContentSummary(BaseModel):
    name: str
    source: str
    srd: bool
    uid: str | None = optional(
        "Pass as get_content's name when the name and source repeat"
    )
    detail: str | None = optional("What tells it apart, e.g. a pantheon")
    text: str | None = optional("As Markdown, with include_text")


class ContentResults(Filtered):
    type: str
    total: int = Field(description="Matches before the limit")
    next_offset: NextOffset = None
    results: list[ContentSummary] = listed("Left out when nothing matched")


class FeatureRef(BaseModel):
    name: str
    uid: str = Field(description="Pass as get_content's name, with the feature type")


class ProgressionLevel(BaseModel):
    level: int
    proficiency_bonus: int
    features: list[FeatureRef] = listed("Class features gained; left out when none")
    subclass_features: list[FeatureRef] = listed(
        "The subclass's features gained, each followed by those it holds; "
        "left out when none"
    )
    cells: list[str] = listed(
        "This level's value in each of columns; left out when there are none"
    )


class ClassProgression(BaseModel):
    name: str
    source: str
    srd: bool
    subclass: str | None = optional("With a subclass asked for")
    subclass_source: str | None = optional("With a subclass asked for")
    columns: list[str] = listed(
        "The class table's own columns, e.g. spell slots by level; "
        "left out when there are none"
    )
    levels: list[ProgressionLevel]
