"""What a document gives the entry renderer and templates while rendering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker

# Sectioning commands by nesting depth; the last repeats below it
SPELL_HEADINGS = ("subsubsection", "paragraph", "subparagraph")
ITEM_HEADINGS = ("subsubsection", "subparagraph", "subparagraph")
SIDEBAR_HEADINGS = ("subsubsection", "paragraph", "subparagraph")
# Books and adventures: the document already opens each chapter
BOOK_HEADINGS = ("section", "subsection", "subsection", "subsubsection", "paragraph")
ARTICLE_HEADINGS = (
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
)


@dataclass(frozen=True)
class Style:
    """How the surrounding document shapes entries."""

    content_type: str | None = (
        None  # "spell", "item" and "vehicle" nest headings deeper
    )
    book: bool = False  # a book or adventure, whose chapters the document opens
    sidebar: bool = False
    monster_spells: bool = False  # DndMonsterSpells macros, in statblocks only
    images: bool = True
    statblock: Literal["2014", "2024"] = "2024"  # 2024 puts saves in the ability table

    @property
    def headings(self) -> tuple[str, ...]:
        if self.content_type == "spell":
            return SPELL_HEADINGS
        if self.content_type in ("item", "vehicle"):
            return ITEM_HEADINGS
        if self.sidebar:
            return SIDEBAR_HEADINGS
        return BOOK_HEADINGS if self.book else ARTICLE_HEADINGS


@dataclass(frozen=True)
class RenderingContext:
    """The tracker, data and style a document renders its entries with.

    ``fluff`` maps a creature's, spell's or item's name to its fluff, and
    ``fluff_images`` to its fluff images (None when fluff images are off).
    ``creature_level`` scales proficiency bonuses in statblocks.
    """

    content_tracker: ContentTracker | None = None
    omnidexer: Omnidexer | None = None
    style: Style = field(default_factory=Style)
    fluff: Mapping[str, Any] = field(default_factory=dict)
    fluff_images: Mapping[str, list[Any]] | None = None
    creature_level: int = 1
