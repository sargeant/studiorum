"""Models for rules glossary content (actions, conditions, senses, hazards, statuses)."""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="action",
    file_patterns=["action", "actions", "conditionsdiseases"],
    statblock_tags=["action"],
    loader_type="json",
)
class Action(BaseContent):
    """Represents an action rule from the rules glossary."""

    page: int | None = Field(None, description="Page number")
    entries: list[Any] = Field(default_factory=list, description="Action description")
    time: list[dict[str, Any] | str] = Field(
        default_factory=list, description="Time requirement for the action"
    )
    srd: bool | None = Field(None, description="Available in System Reference Document")
    basic_rules: bool | None = Field(
        None, alias="basicRules", description="Available in Basic Rules"
    )

    def get_hash_key(self) -> str:
        """Generate unique hash key for indexing."""
        return f"action:{self.name}:{self.source.abbreviation}"


@content_type(
    enum_value="condition",
    file_patterns=["condition", "conditions", "conditionsdiseases"],
    statblock_tags=["condition"],
    loader_type="json",
)
class Condition(BaseContent):
    """Represents a condition rule from the rules glossary."""

    page: int | None = Field(None, description="Page number")
    entries: list[Any] = Field(
        default_factory=list, description="Condition description"
    )
    srd: bool | None = Field(None, description="Available in System Reference Document")
    basic_rules: bool | None = Field(
        None, alias="basicRules", description="Available in Basic Rules"
    )
    reprinted_as: list[str] = Field(
        default_factory=list, alias="reprintedAs", description="Reprinted as references"
    )

    def get_hash_key(self) -> str:
        """Generate unique hash key for indexing."""
        return f"condition:{self.name}:{self.source.abbreviation}"


@content_type(
    enum_value="sense",
    file_patterns=["sense", "senses", "conditionsdiseases"],
    statblock_tags=["sense"],
    loader_type="json",
)
class Sense(BaseContent):
    """Represents a sense rule from the rules glossary."""

    page: int | None = Field(None, description="Page number")
    entries: list[Any] = Field(default_factory=list, description="Sense description")
    srd: bool | None = Field(None, description="Available in System Reference Document")
    basic_rules: bool | None = Field(
        None, alias="basicRules", description="Available in Basic Rules"
    )
    reprinted_as: list[str] = Field(
        default_factory=list, alias="reprintedAs", description="Reprinted as references"
    )

    def get_hash_key(self) -> str:
        """Generate unique hash key for indexing."""
        return f"sense:{self.name}:{self.source.abbreviation}"


@content_type(
    enum_value="hazard",
    file_patterns=["hazard", "hazards", "conditionsdiseases"],
    statblock_tags=["hazard"],
    loader_type="json",
)
class Hazard(BaseContent):
    """Represents a hazard rule from the rules glossary."""

    page: int | None = Field(None, description="Page number")
    entries: list[Any] = Field(default_factory=list, description="Hazard description")
    trap_haz_type: str | None = Field(
        None, alias="trapHazType", description="Type of trap or hazard"
    )

    def get_hash_key(self) -> str:
        """Generate unique hash key for indexing."""
        return f"hazard:{self.name}:{self.source.abbreviation}"


@content_type(
    enum_value="status",
    file_patterns=["status", "statuses", "conditionsdiseases"],
    statblock_tags=["status"],
    loader_type="json",
)
class Status(BaseContent):
    """Represents a status rule from the rules glossary."""

    page: int | None = Field(None, description="Page number")
    entries: list[Any] = Field(default_factory=list, description="Status description")
    srd: bool | None = Field(None, description="Available in System Reference Document")
    basic_rules: bool | None = Field(
        None, alias="basicRules", description="Available in Basic Rules"
    )
    reprinted_as: list[str] = Field(
        default_factory=list, alias="reprintedAs", description="Reprinted as references"
    )

    def get_hash_key(self) -> str:
        """Generate unique hash key for indexing."""
        return f"status:{self.name}:{self.source.abbreviation}"
