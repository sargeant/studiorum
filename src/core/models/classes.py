"""Pydantic models for character classes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .content import BaseContent


class ClassFeature(BaseModel):
    """A feature for a character class."""

    class_feature: str = Field(..., alias="classFeature")
    gain_subclass_feature: bool = Field(..., alias="gainSubclassFeature")
    level: int
    name: str
    source: str


class Subclass(BaseModel):
    """A subclass for a character."""

    name: str
    short_name: str = Field(..., alias="shortName")
    source: str
    subclass_features: str = Field(..., alias="subclassFeatures")


class Class(BaseContent):
    """A character class."""

    hd: Dict[str, int]
    proficiency: List[str]
    spellcasting_ability: Optional[str] = Field(default=None, alias="spellcastingAbility")
    caster_progression: Optional[str] = Field(default=None, alias="casterProgression")
    cantrip_progression: Optional[List[int]] = Field(
        default=None, alias="cantripProgression"
    )
    starting_proficiencies: Optional[Dict[str, Any]] = Field(
        default=None, alias="startingProficiencies"
    )
    starting_equipment: Optional[Dict[str, Any]] = Field(
        default=None, alias="startingEquipment"
    )
    multiclassing: Optional[Dict[str, Any]] = None
    class_features: List[Any] = Field(..., alias="classFeatures")
    subclasses: List[Subclass] = Field(default_factory=list)
