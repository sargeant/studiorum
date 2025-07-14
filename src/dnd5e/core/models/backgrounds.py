"""Pydantic models for backgrounds."""

from typing import Any, List, Optional

from pydantic import Field

from .content import BaseContent


class Background(BaseContent):
    """A character background."""

    skill_proficiencies: Optional[List[Any]] = Field(
        default=None, alias="skillProficiencies"
    )
    tool_proficiencies: Optional[List[Any]] = Field(
        default=None, alias="toolProficiencies"
    )
    language_proficiencies: Optional[List[Any]] = Field(
        default=None, alias="languageProficiencies"
    )
    entries: List[Any]
