"""Object content models for interactive dungeon elements."""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="object",
    file_patterns=["object", "objects"],
    loader_type="json",
    statblock_tags=["object"],
)
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

    def get_primary_size(self) -> str:
        """Get the primary size category."""
        return self.size[0] if self.size else "Medium"

    def has_actions(self) -> bool:
        """Check if the object has any actions."""
        return len(self.action_entries) > 0

    def is_destructible(self) -> bool:
        """Check if the object can be destroyed (has HP)."""
        return self.hp is not None and isinstance(self.hp, int) and self.hp > 0

    def is_siege_weapon(self) -> bool:
        """Check if this is a siege weapon."""
        return self.object_type == "SW"

    def is_generic_object(self) -> bool:
        """Check if this is a generic object."""
        return self.object_type == "G"

    def get_damage_threshold(self) -> int | None:
        """Get damage threshold if specified in entries."""
        # Objects often have damage threshold mentioned in their description
        # This would need to be parsed from the entries text
        return None  # Placeholder for now
