"""Deck models for card-based game elements."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class CardImage(BaseModel):
    """Represents a card image reference."""

    type: str = Field(..., description="Image type (e.g., 'image')")
    href: dict[str, Any] = Field(..., description="Image href data")
    width: int | None = Field(None, description="Image width")
    height: int | None = Field(None, description="Image height")


@content_type(
    enum_value="deck",
    file_patterns=["deck", "decks"],
    statblock_tags=["deck"],
    loader_type="json",
)
class Deck(BaseContent):
    """Represents a deck of cards."""

    page: int | None = Field(None, description="Source page number")
    srd: bool | None = Field(None, description="Whether this is SRD content")
    cards: list[str | dict[str, Any]] = Field(
        default_factory=list, description="List of card references"
    )
    back: CardImage | None = Field(None, description="Card back image")
    entries: list[Entry] = Field(
        default_factory=list, description="Deck description entries"
    )
    has_card_art: bool | None = Field(
        None, alias="hasCardArt", description="Whether cards have custom art"
    )
