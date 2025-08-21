"""Deity data models for gods, pantheons, and divine domains."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry, validate_entries


class SymbolImage(BaseModel):
    """Image data for deity symbols."""

    type: str = Field(..., description="Type of image reference")
    href: dict[str, str] = Field(..., description="Image URL references")

    class Config:
        extra = "allow"


@content_type(
    enum_value="deity",
    file_patterns=["deity", "deities"],
    statblock_tags=["deity"],
    loader_type="json",
)
class Deity(BaseContent):
    """Gods, pantheons, and divine entities."""

    pantheon: str = Field(..., description="Pantheon this deity belongs to")
    alignment: list[str] = Field(
        ..., description="Alignment components (e.g., ['L', 'G'] for Lawful Good)"
    )
    title: str | None = Field(None, description="Deity's title or epithet")
    domains: list[str] | None = Field(
        None, description="Cleric domains associated with this deity"
    )
    symbol: str | None = Field(None, description="Description of the deity's symbol")
    symbol_img: SymbolImage | None = Field(
        None, alias="symbolImg", description="Symbol image data"
    )
    category: str | None = Field(None, description="Category within pantheon")
    province: list[str] | None = Field(
        None, description="Areas of influence or responsibility"
    )
    alt_names: list[str] | None = Field(
        None, alias="altNames", description="Alternative names"
    )
    reprinted_as: list[dict[str, str]] | None = Field(
        None, alias="reprintedAs", description="Later reprints of this deity"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Deity description and lore"
    )

    @field_validator("pantheon")
    @classmethod
    def validate_pantheon(cls, v: str) -> str:
        """Validate pantheon name is not empty."""
        if not v.strip():
            raise ValueError("Pantheon cannot be empty")
        return v.strip()

    @field_validator("alignment")
    @classmethod
    def validate_alignment(cls, v: list[str]) -> list[str]:
        """Validate alignment components."""
        if not v:
            raise ValueError("Alignment cannot be empty")

        valid_alignments = {
            # Lawful/Chaotic axis
            "L",
            "C",
            "N",  # Lawful, Chaotic, Neutral
            # Good/Evil axis
            "G",
            "E",
            # Good, Evil, Neutral
            # Special cases
            "U",  # Unaligned
            "A",  # Any alignment
        }

        for component in v:
            if component not in valid_alignments:
                raise ValueError(f"Invalid alignment component: {component}")

        # Validate logical combinations
        if len(v) > 2:
            raise ValueError("Alignment cannot have more than 2 components")

        if len(v) == 2:
            # Should have one from each axis
            lawful_chaotic = {"L", "C", "N"}
            good_evil = {"G", "E", "N"}

            axis1 = set(v) & lawful_chaotic
            axis2 = set(v) & good_evil

            if len(axis1) != 1 or len(axis2) != 1:
                # Allow some flexibility for special deity alignments
                pass

        return v

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v: list[str] | None) -> list[str] | None:
        """Validate domain names."""
        if v is not None:
            # Known cleric domains from official sources

            for domain in v:
                if not domain.strip():
                    raise ValueError("Domain name cannot be empty")
                # Don't enforce strict domain validation as new domains may be added

        return v

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entries(cls, v: list[str | dict[str, Any]] | None) -> list[Entry]:
        """Validate entries using the standard validator."""
        if v is None:
            return []
        if not isinstance(v, list):
            # Malformed data - let Pydantic's normal validation catch it
            raise ValueError(f"Expected list or None for entries, got {type(v)}")
        return validate_entries(v)

    def get_alignment_display(self) -> str:
        """Get human-readable alignment string."""
        if not self.alignment:
            return "Unaligned"

        if len(self.alignment) == 1:
            alignment_map = {
                "L": "Lawful",
                "C": "Chaotic",
                "N": "Neutral",
                "G": "Good",
                "E": "Evil",
                "U": "Unaligned",
                "A": "Any alignment",
            }
            return alignment_map.get(self.alignment[0], self.alignment[0])

        if len(self.alignment) == 2:
            # Two component alignment
            alignment_map = {
                "L": "Lawful",
                "C": "Chaotic",
                "N": "Neutral",
                "G": "Good",
                "E": "Evil",
            }

            parts = [alignment_map.get(comp, comp) for comp in self.alignment]

            # Handle True Neutral specially
            if parts == ["Neutral", "Neutral"]:
                return "True Neutral"

            return " ".join(parts)

        # Fallback for unusual cases
        return " ".join(self.alignment)

    def get_pantheon_display(self) -> str:
        """Get formatted pantheon name."""
        # Some pantheons have special formatting
        pantheon_map = {
            "dwarven": "Dwarven Pantheon (The Mordinsamman)",
            "elven": "Elven Pantheon (The Seldarine)",
            "gnomish": "Gnomish Pantheon",
            "halfling": "Halfling Pantheon",
            "orc": "Orc Pantheon",
            "draconic": "Draconic Pantheon",
            "giant": "Giant Pantheon",
            "egyptian": "Egyptian Pantheon",
            "greek": "Greek Pantheon",
            "norse": "Norse Pantheon",
            "celtic": "Celtic Pantheon",
        }

        return pantheon_map.get(self.pantheon.lower(), self.pantheon)

    def get_primary_domain(self) -> str | None:
        """Get the primary (first) domain for this deity."""
        return self.domains[0] if self.domains else None

    def is_from_pantheon(self, pantheon_name: str) -> bool:
        """Check if this deity belongs to a specific pantheon."""
        return self.pantheon.lower() == pantheon_name.lower()

    def has_domain(self, domain_name: str) -> bool:
        """Check if this deity is associated with a specific domain."""
        if not self.domains:
            return False
        return any(domain.lower() == domain_name.lower() for domain in self.domains)
