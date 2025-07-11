"""Spell data models."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class SpellComponent(BaseModel):
    """Represents spell components (V, S, M)."""

    verbal: bool = Field(False, alias="v", description="Verbal component required")
    somatic: bool = Field(False, alias="s", description="Somatic component required")
    material: Union[bool, str] = Field(
        False, alias="m", description="Material component"
    )

    @field_validator("material", mode="before")
    @classmethod
    def parse_material(cls, v):
        """Handle both boolean and string material components."""
        if isinstance(v, bool):
            return v
        elif isinstance(v, str):
            return v
        elif isinstance(v, dict) and "text" in v:
            return v["text"]
        return bool(v)


class SpellDuration(BaseModel):
    """Represents spell duration."""

    type: Literal["instant", "timed", "permanent", "special"]
    duration: Optional[Dict[str, Any]] = None
    concentration: bool = False

    def __str__(self) -> str:
        if self.type == "instant":
            return "Instantaneous"
        elif self.type == "permanent":
            return "Permanent"
        elif self.type == "special":
            return "Special"
        elif self.duration:
            amount = self.duration.get("amount", 1)
            unit = self.duration.get("type", "unknown")
            duration_str = f"{amount} {unit}" if amount != 1 else unit
            if self.concentration:
                return f"Concentration, up to {duration_str}"
            return duration_str
        return "Unknown"


class SpellTime(BaseModel):
    """Represents casting time."""

    number: int = Field(1, description="Number of time units")
    unit: str = Field(..., description="Time unit (action, bonus action, etc.)")
    condition: Optional[str] = Field(None, description="Conditional casting time")

    def __str__(self) -> str:
        if self.number == 1:
            result = f"1 {self.unit}"
        else:
            result = f"{self.number} {self.unit}s"

        if self.condition:
            result += f" ({self.condition})"

        return result


class SpellRange(BaseModel):
    """Represents spell range."""

    type: str = Field(..., description="Range type (point, line, cone, etc.)")
    distance: Optional[Dict[str, Any]] = Field(
        None, description="Distance specification"
    )

    def __str__(self) -> str:
        if self.type == "point":
            if self.distance:
                dist_type = self.distance.get("type", "feet")
                amount = self.distance.get("amount", 0)
                if amount == 0:
                    return "Touch"
                return f"{amount} {dist_type}"
            return "Touch"
        elif self.type == "self":
            if self.distance:
                area_type = self.distance.get("type", "")
                amount = self.distance.get("amount", 0)
                return f"Self ({amount}-foot {area_type})"
            return "Self"
        elif self.type == "sight":
            return "Sight"
        elif self.type == "unlimited":
            return "Unlimited"
        else:
            return self.type.title()


class Spell(BaseContent):
    """Represents a D&D spell."""

    level: int = Field(..., ge=0, le=9, description="Spell level (0-9)")
    school: str = Field(..., description="School of magic")
    casting_time: List[SpellTime] = Field(..., alias="time", description="Casting time")
    range: SpellRange = Field(..., description="Spell range")
    components: SpellComponent = Field(..., description="Spell components")
    duration: List[SpellDuration] = Field(..., description="Spell duration")
    entries: List[str] = Field(..., description="Spell description")
    higher_level: Optional[List[str]] = Field(
        None, alias="entriesHigherLevel", description="At higher levels"
    )
    damage_inflict: Optional[List[str]] = Field(
        None, alias="damageInflict", description="Damage types"
    )
    saving_throw: Optional[List[str]] = Field(
        None, alias="savingThrow", description="Saving throws"
    )
    spell_attack: Optional[List[str]] = Field(
        None, alias="spellAttack", description="Spell attack types"
    )
    classes: Optional[Dict[str, Any]] = Field(None, description="Class lists")

    @field_validator("school", mode="before")
    @classmethod
    def parse_school(cls, v):
        """Parse school abbreviations to full names."""
        school_map = {
            "A": "Abjuration",
            "C": "Conjuration",
            "D": "Divination",
            "E": "Enchantment",
            "V": "Evocation",
            "I": "Illusion",
            "N": "Necromancy",
            "T": "Transmutation",
        }
        return school_map.get(v, v)

    @field_validator("casting_time", mode="before")
    @classmethod
    def parse_casting_time(cls, v):
        """Parse casting time from various formats."""
        if isinstance(v, list):
            return [
                SpellTime.model_validate(item) if isinstance(item, dict) else item
                for item in v
            ]
        return v

    @field_validator("range", mode="before")
    @classmethod
    def parse_range(cls, v):
        """Parse range from various formats."""
        if isinstance(v, dict):
            return SpellRange.model_validate(v)
        return v

    @field_validator("duration", mode="before")
    @classmethod
    def parse_duration(cls, v):
        """Parse duration from various formats."""
        if isinstance(v, list):
            return [
                SpellDuration.model_validate(item) if isinstance(item, dict) else item
                for item in v
            ]
        return v

    def get_level_text(self) -> str:
        """Get formatted spell level text."""
        if self.level == 0:
            return f"{self.school} cantrip"
        elif self.level == 1:
            return f"1st-level {self.school.lower()}"
        elif self.level == 2:
            return f"2nd-level {self.school.lower()}"
        elif self.level == 3:
            return f"3rd-level {self.school.lower()}"
        else:
            return f"{self.level}th-level {self.school.lower()}"

    def get_casting_time_text(self) -> str:
        """Get formatted casting time text."""
        return ", ".join(str(ct) for ct in self.casting_time)

    def get_range_text(self) -> str:
        """Get formatted range text."""
        return str(self.range)

    def get_duration_text(self) -> str:
        """Get formatted duration text."""
        return ", ".join(str(d) for d in self.duration)

    def get_components_text(self) -> str:
        """Get formatted components text."""
        parts = []
        if self.components.verbal:
            parts.append("V")
        if self.components.somatic:
            parts.append("S")
        if self.components.material:
            if isinstance(self.components.material, str):
                parts.append(f"M ({self.components.material})")
            else:
                parts.append("M")

        return ", ".join(parts)
