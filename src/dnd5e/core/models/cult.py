"""Cult content model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


@content_type(
    enum_value="cult",
    file_patterns=["cult", "cults", "cultsboons"],
    loader_type="json",
    statblock_tags=["cult"],
)
class Cult(BaseContent):
    """Cult model for religious organizations and their practices.

    Cults represent organized groups with specific goals, signature spells,
    and associated cultists or followers.
    """

    # Required fields
    cult_type: str | None = Field(
        None, description="Type of cult (Diabolical, Elder Evil, etc.)", alias="type"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Cult description and mechanics entries"
    )

    # Optional fields
    goal: str | None = Field(None, description="Primary goal of the cult")
    cultists: list[dict[str, Any]] | None = Field(
        None, description="Associated cultists and followers"
    )
    signature_spells: list[dict[str, Any]] | None = Field(
        None, description="Signature spells of the cult", alias="signatureSpells"
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None, description="Other sources that reference this cult", alias="otherSources"
    )
    reprinted_as: list[dict[str, Any]] | None = Field(
        None, description="Reprints of this cult content", alias="reprintedAs"
    )

    @field_validator("cult_type", mode="before")
    @classmethod
    def validate_cult_type(cls, v: Any) -> str | None:
        """Validate cult type."""
        if v is None:
            return None
        return str(v)

    @field_validator("cultists", mode="before")
    @classmethod
    def validate_cultists(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate cultists structure."""
        if v is None:
            return None
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return None

    @field_validator("signature_spells", mode="before")
    @classmethod
    def validate_signature_spells(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate signature spells structure."""
        if v is None:
            return None
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Cult name cannot be empty")
        return str(v).strip()

    def get_cult_type(self) -> str:
        """Get the cult type, defaulting to 'Unknown' if not specified."""
        return self.cult_type or "Unknown"

    def has_goal(self) -> bool:
        """Check if this cult has a specified goal."""
        return bool(self.goal)

    def has_cultists(self) -> bool:
        """Check if this cult has associated cultists."""
        return bool(self.cultists)

    def has_signature_spells(self) -> bool:
        """Check if this cult has signature spells."""
        return bool(self.signature_spells)

    def get_cultist_count(self) -> int:
        """Get the number of associated cultists."""
        return len(self.cultists) if self.cultists else 0

    def get_signature_spell_count(self) -> int:
        """Get the number of signature spells."""
        return len(self.signature_spells) if self.signature_spells else 0

    def is_diabolical(self) -> bool:
        """Check if this is a diabolical cult."""
        return self.get_cult_type().lower() == "diabolical"

    def is_elder_evil(self) -> bool:
        """Check if this is an elder evil cult."""
        return self.get_cult_type().lower() == "elder evil"
