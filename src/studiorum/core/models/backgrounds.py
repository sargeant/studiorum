"""Pydantic models for backgrounds."""

from typing import Any

from pydantic import Field

from .content import BaseContent


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
