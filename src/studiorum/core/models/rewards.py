"""Pydantic models for rewards (blessings, charms, etc.)."""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="reward",
    file_patterns=["reward", "rewards"],
    statblock_tags=["reward"],
    loader_type="json",
)
class Reward(BaseContent):
    """A reward (blessing, charm, etc.)."""

    type: str = Field(description="Type of reward (Blessing, Charm, etc.)")
    additional_spells: list[dict[str, Any]] | None = Field(
        None, alias="additionalSpells"
    )
