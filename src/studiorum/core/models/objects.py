"""Object content models for interactive dungeon elements."""

from typing import Any

from pydantic import Field

from .content import BaseContent


class Object(BaseContent):
    """Interactive objects like doors, chests, and magical constructs."""

    # Core object properties
    size: list[str] = Field(default_factory=list, description="Object size categories")
    object_type: str | None = Field(
        None, alias="objectType", description="Type of object (SW, G, etc.)"
    )

    # Combat stats
    ac: int | dict[str, Any] | None = Field(None, description="Armor Class")
    hp: int | dict[str, Any] | None = Field(None, description="Hit Points")

    # Resistances and immunities
    resist: list[str] = Field(default_factory=list, description="Damage resistances")
    immune: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Damage immunities"
    )
    vulnerable: list[str] = Field(
        default_factory=list, description="Damage vulnerabilities"
    )

    # Actions and abilities
    action_entries: list[dict[str, Any]] = Field(
        default_factory=list, alias="actionEntries", description="Object actions"
    )

    # Optional properties
    speed: dict[str, Any] | int | None = Field(
        None, description="Movement speeds if mobile"
    )
    senses: list[str] = Field(default_factory=list, description="Special senses")

    # Visual properties
    token_credit: str | None = Field(
        None, alias="tokenCredit", description="Token artwork credit"
    )
    alt_art: list[dict[str, Any]] = Field(
        default_factory=list, alias="altArt", description="Alternative artwork"
    )
