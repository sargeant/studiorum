"""Spell data models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class SpellComponent(BaseModel):
    """Represents spell components (V, S, M)."""

    verbal: bool = Field(False, alias="v", description="Verbal component required")
    somatic: bool = Field(False, alias="s", description="Somatic component required")
    material: bool | str = Field(False, alias="m", description="Material component")

    @field_validator("material", mode="before")
    @classmethod
    def parse_material(cls, v: Any) -> bool | str:
        """Handle both boolean and string material components."""
        if isinstance(v, bool):
            return v
        elif isinstance(v, str):
            return v
        elif isinstance(v, dict) and "text" in v:
            return str(v["text"])
        return bool(v)


class SpellDuration(BaseModel):
    """Represents spell duration."""

    type: Literal["instant", "timed", "permanent", "special"]
    duration: dict[str, Any] | None = None
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
    condition: str | None = Field(None, description="Conditional casting time")

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
    distance: dict[str, Any] | None = Field(None, description="Distance specification")

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
    casting_time: list[SpellTime] = Field(..., alias="time", description="Casting time")
    range: SpellRange = Field(..., description="Spell range")
    components: SpellComponent = Field(..., description="Spell components")
    duration: list[SpellDuration] = Field(..., description="Spell duration")
    entries: list[str | dict[str, Any]] = Field(..., description="Spell description")
    higher_level: list[str | dict[str, Any]] | None = Field(
        None, alias="entriesHigherLevel", description="At higher levels"
    )
    damage_inflict: list[str] | None = Field(
        None, alias="damageInflict", description="Damage types"
    )
    saving_throw: list[str] | None = Field(
        None, alias="savingThrow", description="Saving throws"
    )
    spell_attack: list[str] | None = Field(
        None, alias="spellAttack", description="Spell attack types"
    )
    classes: dict[str, Any] | None = Field(None, description="Class lists")

    @field_validator("school", mode="before")
    @classmethod
    def parse_school(cls, v: Any) -> str:
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
        return school_map.get(v, str(v))

    @field_validator("casting_time", mode="before")
    @classmethod
    def parse_casting_time(cls, v: Any) -> list[SpellTime] | Any:
        """Parse casting time from various formats."""
        if isinstance(v, list):
            return [
                SpellTime.model_validate(item) if isinstance(item, dict) else item
                for item in v
            ]
        return v

    @field_validator("range", mode="before")
    @classmethod
    def parse_range(cls, v: Any) -> SpellRange | Any:
        """Parse range from various formats."""
        if isinstance(v, dict):
            return SpellRange.model_validate(v)
        return v

    @field_validator("duration", mode="before")
    @classmethod
    def parse_duration(cls, v: Any) -> list[SpellDuration] | Any:
        """Parse duration from various formats."""
        if isinstance(v, list):
            parsed_durations = []
            for item in v:
                if isinstance(item, dict):
                    # Handle concentration type conversion
                    if item.get("type") == "concentration":
                        item = item.copy()  # Don't modify original
                        item["type"] = "timed"
                        item["concentration"] = True
                    parsed_durations.append(SpellDuration.model_validate(item))
                else:
                    parsed_durations.append(item)
            return parsed_durations
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

    def get_description_text(self) -> str:
        """Extract text from complex entry structures."""
        return self._extract_text_from_entries(self.entries)

    def get_higher_level_text(self) -> str:
        """Extract text from complex higher level entries."""
        if not self.higher_level:
            return ""
        return self._extract_text_from_entries(self.higher_level)

    def _extract_text_from_entries(self, entries: Any) -> str:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                result = self._extract_text_from_entries(entry)
                if result:
                    text_parts.append(result)
        elif isinstance(entries, dict):
            # Handle different entry types
            if "entries" in entries:
                result = self._extract_text_from_entries(entries["entries"])
                if result:
                    text_parts.append(result)
            elif "text" in entries:
                text_parts.append(entries["text"])
            # Add name if present (for structured sections)
            if "name" in entries:
                text_parts.append(f"**{entries['name']}**")
            # Add attribution for quotes
            if "by" in entries:
                text_parts.append(f"— {entries['by']}")
            # Handle lists within entries
            if "items" in entries and isinstance(entries["items"], list):
                for item in entries["items"]:
                    if isinstance(item, str):
                        text_parts.append(f"• {item}")
                    elif isinstance(item, dict):
                        item_text_parts = []
                        if "name" in item:
                            item_text_parts.append(f"**{item['name']}**")
                        if "text" in item:
                            item_text_parts.append(item["text"])
                        if item_text_parts:
                            text_parts.append(f"• {' '.join(item_text_parts)}")
        elif isinstance(entries, str):
            text_parts.append(entries)

        return " ".join(text_parts) if text_parts else ""
