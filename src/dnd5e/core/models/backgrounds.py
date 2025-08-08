"""Pydantic models for backgrounds."""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="background",
    file_patterns=["background", "backgrounds"],
    statblock_tags=["background"],
    loader_type="json",
)
class Background(BaseContent):
    """A character background."""

    skill_proficiencies: list[Any] | None = Field(
        default=None, alias="skillProficiencies"
    )
    tool_proficiencies: list[Any] | None = Field(
        default=None, alias="toolProficiencies"
    )
    language_proficiencies: list[Any] | None = Field(
        default=None, alias="languageProficiencies"
    )
    entries: list[Any]
