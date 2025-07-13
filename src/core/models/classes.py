"""Pydantic models for character classes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

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

    # Core fields - optional for sidekicks
    hd: Optional[Dict[str, int]] = None
    proficiency: Optional[List[str]] = None
    class_features: Optional[List[Any]] = Field(default=None, alias="classFeatures")

    # Sidekick identification
    is_sidekick: Optional[bool] = Field(default=None, alias="isSidekick")

    # Optional fields
    spellcasting_ability: Optional[str] = Field(
        default=None, alias="spellcastingAbility"
    )
    caster_progression: Optional[str] = Field(default=None, alias="casterProgression")
    cantrip_progression: Optional[List[int]] = Field(
        default=None, alias="cantripProgression"
    )
    spells_known_progression: Optional[List[int]] = Field(
        default=None, alias="spellsKnownProgression"
    )
    starting_proficiencies: Optional[Dict[str, Any]] = Field(
        default=None, alias="startingProficiencies"
    )
    starting_equipment: Optional[Dict[str, Any]] = Field(
        default=None, alias="startingEquipment"
    )
    multiclassing: Optional[Dict[str, Any]] = None
    subclasses: List[Subclass] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields_for_regular_classes(self):
        """Validate that required fields are present for regular (non-sidekick) classes."""
        # If this is not a sidekick class, certain fields are required
        if not self.is_sidekick:
            missing_fields = []
            if self.hd is None:
                missing_fields.append("hd")
            if self.proficiency is None:
                missing_fields.append("proficiency")
            if self.class_features is None:
                missing_fields.append("classFeatures")

            if missing_fields:
                raise ValueError(
                    f"Regular classes require these fields: {', '.join(missing_fields)}"
                )

        return self
