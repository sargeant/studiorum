"""Pydantic models for feats."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .content import BaseContent


class Prerequisite(BaseModel):
    """A prerequisite for a feat."""

    other: Optional[str] = None


class AdditionalSpell(BaseModel):
    """A spell that can be cast in addition to the feat."""

    name: Optional[str] = None
    level: Optional[int] = None
    ability: Optional[Union[str, Dict[str, Any]]] = None
    innate: Optional[Dict[str, Any]] = None
    known: Optional[Dict[str, Any]] = None


class Feat(BaseContent):
    """A feat."""

    prerequisite: Optional[List[Prerequisite]] = None
    ability: Optional[List[Dict[str, Union[int, Dict[str, Any]]]]] = None
    additionalSpells: Optional[List[AdditionalSpell]] = Field(
        default=None, alias="additionalSpells"
    )
    entries: List[Any]
