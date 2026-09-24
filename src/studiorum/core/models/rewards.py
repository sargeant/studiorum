"""Pydantic models for rewards (blessings, charms, etc.)."""

from typing import Any

from pydantic import Field

from .content import BaseContent


class Reward(BaseContent):
    """A reward (blessing, charm, etc.)."""

    type: str = Field(description="Type of reward (Blessing, Charm, etc.)")
    additional_spells: list[dict[str, Any]] | None = Field(
        None, alias="additionalSpells"
    )
