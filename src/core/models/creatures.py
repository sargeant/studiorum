"""Creature data models."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class ArmorClass(BaseModel):
    """Represents creature armor class."""

    ac: int = Field(..., description="Armor class value")
    from_: Optional[List[str]] = Field(None, alias="from", description="AC sources")
    condition: Optional[str] = Field(None, description="Conditional AC")

    def __str__(self) -> str:
        result = str(self.ac)
        if self.from_:
            sources = ", ".join(self.from_)
            result += f" ({sources})"
        if self.condition:
            result += f" {self.condition}"
        return result


class HitPoints(BaseModel):
    """Represents creature hit points."""

    average: int = Field(..., description="Average hit points")
    formula: str = Field(..., description="Hit dice formula")

    def __str__(self) -> str:
        return f"{self.average} ({self.formula})"


class Speed(BaseModel):
    """Represents creature movement speeds."""

    walk: Optional[Union[int, Dict[str, Any]]] = Field(
        None, description="Walking speed"
    )
    fly: Optional[Union[int, Dict[str, Any]]] = Field(None, description="Flying speed")
    swim: Optional[Union[int, Dict[str, Any]]] = Field(
        None, description="Swimming speed"
    )
    climb: Optional[Union[int, Dict[str, Any]]] = Field(
        None, description="Climbing speed"
    )
    burrow: Optional[Union[int, Dict[str, Any]]] = Field(
        None, description="Burrowing speed"
    )

    def __str__(self) -> str:
        speeds = []

        # Walking speed (always first, no label if it's the only one)
        if self.walk:
            walk_speed = (
                self.walk if isinstance(self.walk, int) else self.walk.get("number", 30)
            )
            speeds.append(f"{walk_speed} ft.")

        # Other speeds with labels
        for speed_type, value in [
            ("fly", self.fly),
            ("swim", self.swim),
            ("climb", self.climb),
            ("burrow", self.burrow),
        ]:
            if value:
                speed_val = value if isinstance(value, int) else value.get("number", 0)
                condition = (
                    value.get("condition", "") if isinstance(value, dict) else ""
                )
                speed_text = f"{speed_type} {speed_val} ft."
                if condition:
                    speed_text += f" ({condition})"
                speeds.append(speed_text)

        return ", ".join(speeds) if speeds else "0 ft."


class CreatureType(BaseModel):
    """Represents creature type information."""

    type: str = Field(..., description="Base creature type")
    subtype: Optional[str] = Field(None, description="Creature subtype")
    tags: Optional[List[str]] = Field(None, description="Additional tags")

    def __str__(self) -> str:
        result = self.type
        if self.subtype:
            result += f" ({self.subtype})"
        return result


class Ability(BaseModel):
    """Represents a creature ability (trait, action, etc.)."""

    name: str = Field(..., description="Ability name")
    entries: List[str] = Field(..., description="Ability description")

    def __str__(self) -> str:
        return self.name


class Creature(BaseContent):
    """Represents a D&D creature/monster."""

    size: List[str] = Field(..., description="Creature size")
    type: Union[str, CreatureType, Dict[str, Any]] = Field(
        ..., description="Creature type"
    )
    alignment: List[str] = Field(..., description="Creature alignment")

    # Combat stats
    ac: List[Union[int, ArmorClass, Dict[str, Any]]] = Field(
        ..., description="Armor class"
    )
    hp: Union[HitPoints, Dict[str, Any]] = Field(..., description="Hit points")
    speed: Union[Speed, Dict[str, Any]] = Field(..., description="Movement speeds")

    # Ability scores
    strength: int = Field(..., ge=1, le=30, alias="str")
    dexterity: int = Field(..., ge=1, le=30, alias="dex")
    constitution: int = Field(..., ge=1, le=30, alias="con")
    intelligence: int = Field(..., ge=1, le=30, alias="int")
    wisdom: int = Field(..., ge=1, le=30, alias="wis")
    charisma: int = Field(..., ge=1, le=30, alias="cha")

    # Optional attributes
    save: Optional[Dict[str, str]] = Field(None, description="Saving throw bonuses")
    skill: Optional[Dict[str, str]] = Field(None, description="Skill bonuses")
    senses: Optional[List[str]] = Field(None, description="Special senses")
    passive: Optional[int] = Field(None, description="Passive perception")
    languages: Optional[List[str]] = Field(None, description="Known languages")
    cr: Optional[Union[str, int, Dict[str, Any]]] = Field(
        None, description="Challenge rating"
    )

    # Abilities
    trait: Optional[List[Union[Ability, Dict[str, Any]]]] = Field(
        None, description="Traits"
    )
    action: Optional[List[Union[Ability, Dict[str, Any]]]] = Field(
        None, description="Actions"
    )
    legendary_actions: Optional[int] = Field(
        None, alias="legendaryActions", description="Number of legendary actions"
    )
    legendary: Optional[List[Union[Ability, Dict[str, Any]]]] = Field(
        None, description="Legendary actions"
    )
    reaction: Optional[List[Union[Ability, Dict[str, Any]]]] = Field(
        None, description="Reactions"
    )
    bonus: Optional[List[Union[Ability, Dict[str, Any]]]] = Field(
        None, description="Bonus actions"
    )

    # Resistances and immunities
    resist: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None, description="Damage resistances"
    )
    immune: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None, description="Damage immunities"
    )
    vulnerable: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None, description="Damage vulnerabilities"
    )
    conditionImmune: Optional[List[str]] = Field(
        None, description="Condition immunities"
    )

    @field_validator("type", mode="before")
    @classmethod
    def parse_type(cls, v):
        """Parse creature type from various formats."""
        if isinstance(v, str):
            return CreatureType(type=v)
        elif isinstance(v, dict):
            if "type" in v:
                return CreatureType.model_validate(v)
            else:
                # Handle legacy format
                return CreatureType(type=str(v))
        return v

    @field_validator("ac", mode="before")
    @classmethod
    def parse_ac(cls, v):
        """Parse AC from various formats."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, int):
                    result.append(ArmorClass(ac=item))
                elif isinstance(item, dict):
                    result.append(ArmorClass.model_validate(item))
                else:
                    result.append(item)
            return result
        elif isinstance(v, int):
            return [ArmorClass(ac=v)]
        return v

    @field_validator("hp", mode="before")
    @classmethod
    def parse_hp(cls, v):
        """Parse HP from various formats."""
        if isinstance(v, dict):
            return HitPoints.model_validate(v)
        return v

    @field_validator("speed", mode="before")
    @classmethod
    def parse_speed(cls, v):
        """Parse speed from various formats."""
        if isinstance(v, dict):
            return Speed.model_validate(v)
        return v

    @field_validator("trait", "action", "legendary", "reaction", "bonus", mode="before")
    @classmethod
    def parse_abilities(cls, v):
        """Parse ability lists from various formats."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    result.append(Ability.model_validate(item))
                else:
                    result.append(item)
            return result
        return v

    def get_ability_modifier(self, ability_score: int) -> int:
        """Calculate ability modifier from score."""
        return (ability_score - 10) // 2

    def get_ability_text(self, score: int) -> str:
        """Get formatted ability score with modifier."""
        modifier = self.get_ability_modifier(score)
        mod_text = f"+{modifier}" if modifier >= 0 else str(modifier)
        return f"{score} ({mod_text})"

    def get_size_type_alignment(self) -> str:
        """Get formatted size, type, and alignment text."""
        size_text = (
            ", ".join(self.size) if isinstance(self.size, list) else str(self.size)
        )
        type_text = str(self.type)
        alignment_text = (
            " ".join(self.alignment)
            if isinstance(self.alignment, list)
            else str(self.alignment)
        )

        return f"{size_text} {type_text}, {alignment_text}"

    def get_ac_text(self) -> str:
        """Get formatted AC text."""
        if isinstance(self.ac, list):
            return ", ".join(str(ac) for ac in self.ac)
        return str(self.ac)

    def get_hp_text(self) -> str:
        """Get formatted HP text."""
        return str(self.hp)

    def get_speed_text(self) -> str:
        """Get formatted speed text."""
        return str(self.speed)

    def get_cr_text(self) -> str:
        """Get formatted challenge rating text."""
        if self.cr is None:
            return "Unknown"
        elif isinstance(self.cr, dict):
            return str(self.cr.get("cr", "Unknown"))
        return str(self.cr)
