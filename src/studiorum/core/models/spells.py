"""Spell data models."""

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from ...renderers.core.interfaces import RenderingContext
    from ..error_types import BaseError
    from ..result import Result
    from ..text.tag_resolver import TagResolver
    from .processors import SpellProcessor

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry, validate_entries


class DurationDetails(BaseModel):
    """Structured duration information for timed spells."""

    type: str = Field(..., description="Duration unit (hour, minute, day, etc.)")
    amount: int = Field(..., description="Duration amount")


class DistanceDetails(BaseModel):
    """Structured distance information for spell ranges."""

    type: str = Field(..., description="Distance unit (feet, miles, self, etc.)")
    amount: int | None = Field(
        None, description="Distance amount (None for special types)"
    )


class ClassReference(BaseModel):
    """Reference to a character class in spell lists."""

    name: str = Field(..., description="Class name")
    source: str | None = Field(None, description="Source book")


class SpellClassList(BaseModel):
    """Spell class availability information."""

    fromClassList: list[ClassReference] = Field(
        default_factory=list, description="Classes that can cast this spell"
    )


# Use the new typed Entry system
# EntryContent is replaced by the discriminated union in entry_types.py


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
    duration: DurationDetails | None = None
    concentration: bool = False

    def __str__(self) -> str:
        if self.type == "instant":
            return "Instantaneous"
        elif self.type == "permanent":
            return "Permanent"
        elif self.type == "special":
            return "Special"
        elif self.duration:
            amount = self.duration.amount
            unit = self.duration.type
            duration_str = f"{amount} {unit}"
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
    distance: DistanceDetails | None = Field(None, description="Distance specification")

    def __str__(self) -> str:
        if self.type == "point":
            if self.distance:
                dist_type = self.distance.type
                amount = self.distance.amount or 0
                if amount == 0:
                    return "Touch"
                return f"{amount} {dist_type}"
            return "Touch"
        elif self.type == "self":
            if self.distance:
                area_type = self.distance.type
                amount = self.distance.amount or 0
                return f"Self ({amount}-foot {area_type})"
            return "Self"
        elif self.type == "sight":
            return "Sight"
        elif self.type == "unlimited":
            return "Unlimited"
        else:
            return self.type.title()


@content_type(
    enum_value="spell",
    file_patterns=["spell", "spells"],
    statblock_tags=["spell"],
    loader_type="json",
)
class Spell(BaseContent):
    """Represents a D&D spell."""

    level: int = Field(..., ge=0, le=9, description="Spell level (0-9)")
    school: str = Field(..., description="School of magic")
    casting_time: list[SpellTime] = Field(..., alias="time", description="Casting time")
    range: SpellRange = Field(..., description="Spell range")
    components: SpellComponent = Field(..., description="Spell components")
    duration: list[SpellDuration] = Field(..., description="Spell duration")
    entries: list[Entry] = Field(..., description="Spell description")
    higher_level: list[Entry] | None = Field(
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
    classes: SpellClassList | None = Field(None, description="Class lists")
    condition_inflict: list[str] | None = Field(
        None, alias="conditionInflict", description="Conditions inflicted"
    )
    area_tags: list[str] | None = Field(
        None, alias="areaTags", description="Area of effect tags"
    )

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

    @field_validator("classes", mode="before")
    @classmethod
    def parse_classes(cls, v: Any) -> SpellClassList | None:
        """Parse classes from various formats."""
        if v is None:
            return None
        if isinstance(v, dict):
            return SpellClassList.model_validate(v)
        # For unexpected types, return None rather than Any
        return None

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, v: Any) -> list[Entry] | Any:
        """Parse entries from various formats using new typed entry system."""
        if not isinstance(v, list):
            return v
        return validate_entries(v)

    @field_validator("higher_level", mode="before")
    @classmethod
    def parse_higher_level(cls, v: Any) -> list[Entry] | None | Any:
        """Parse higher level entries from various formats using new typed entry system."""
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        return validate_entries(v)

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

    # Enhanced formatting methods for the new architecture
    def get_spell_attack_text(self) -> str:
        """Get formatted spell attack or saving throw text."""
        if self.saving_throw:
            if len(self.saving_throw) == 1:
                return f"{self.saving_throw[0].title()} saving throw"
            else:
                formatted_saves = [save.title() for save in self.saving_throw]
                return f"{', '.join(formatted_saves)} saving throw"
        elif self.spell_attack:
            if "ranged" in self.spell_attack:
                return "ranged spell attack"
            elif "melee" in self.spell_attack:
                return "melee spell attack"
            else:
                return "spell attack"
        return ""

    def get_damage_text(self) -> str:
        """Get formatted damage types text."""
        if not self.damage_inflict:
            return ""
        return ", ".join(self.damage_inflict)

    def has_verbal_components(self) -> bool:
        """Check if spell requires verbal components."""
        return self.components.verbal

    def has_somatic_components(self) -> bool:
        """Check if spell requires somatic components."""
        return self.components.somatic

    def has_material_components(self) -> bool:
        """Check if spell requires material components."""
        return bool(self.components.material)

    def is_concentration(self) -> bool:
        """Check if spell requires concentration."""
        return any(d.concentration for d in self.duration)

    def get_condition_text(self) -> str:
        """Get formatted conditions inflicted text."""
        if self.condition_inflict:
            return ", ".join(self.condition_inflict)
        return ""

    def get_area_text(self) -> str:
        """Get formatted area of effect text."""
        if self.area_tags:
            area_map = {
                "S": "Sphere",
                "C": "Cone",
                "L": "Line",
                "ST": "Single Target",
                "MT": "Multiple Targets",
                "Q": "Square",
                "R": "Rectangle",
                "H": "Hemisphere",
                "Y": "Cylinder",
            }
            formatted_areas = [area_map.get(tag, tag) for tag in self.area_tags]
            return ", ".join(formatted_areas)
        return ""

    def get_enhanced_level_text(self) -> str:
        """Get enhanced level text with additional information."""
        base_level = self.get_level_text()

        # Add damage and attack info
        additional_info = []
        damage_text = self.get_damage_text()
        if damage_text:
            additional_info.append(f"{damage_text} damage")

        attack_text = self.get_spell_attack_text()
        if attack_text:
            additional_info.append(attack_text)

        if additional_info:
            return f"{base_level} ({', '.join(additional_info)})"
        return base_level

    def get_enhanced_components_text(self) -> str:
        """Get enhanced components text (same as current implementation)."""
        return self.get_components_text()

    def get_enhanced_duration_text(self) -> str:
        """Get enhanced duration text (same as current implementation)."""
        return self.get_duration_text()

    def get_higher_level_scaling_text(self) -> str:
        """Get higher level scaling description text."""
        if not self.higher_level:
            return ""

        # Try modern processor pattern first, fallback to simple text extraction
        try:
            # Try to get tag resolver from service container
            from ..container import get_global_container
            from ..result import Error
            from ..text.tag_resolver import TagResolver

            # Use sync access since this method is sync
            container = get_global_container()
            tag_resolver = container.get_service_sync(TagResolver)

            processor = self.get_processor()
            result = processor.get_higher_level_with_context(tag_resolver)
            if isinstance(result, Error):
                # Service worked but processing failed, use fallback
                text = self._extract_simple_text_from_entries(self.higher_level or [])
            else:
                text = result.unwrap()

        except Exception:
            # Service container failed, use simple text extraction fallback
            text = self._extract_simple_text_from_entries(
                self.higher_level or [], skip_section_names=True
            )

        # Remove LaTeX paragraph headers since we want just the content
        import re

        # Remove paragraph headers like \paragraph{At Higher Levels}
        text = re.sub(r"\\paragraph\{[^}]*\}\s*", "", text)
        # Remove textbf headers as well
        text = text.replace("**At Higher Levels**", "")
        text = text.replace("\\textbf{At Higher Levels}", "")
        # Clean up extra whitespace
        return text.strip()

    @staticmethod
    def _extract_simple_text_from_entries(
        entries: list[Any], skip_section_names: bool = False
    ) -> str:
        """Extract simple text from entries without processing.

        Args:
            entries: List of entry objects to extract text from
            skip_section_names: If True, don't include names from "entries" type objects
        """
        if not entries:
            return ""

        text_parts = []

        def extract_text_recursive(entry: Any) -> None:
            if isinstance(entry, str):
                text_parts.append(entry)
            elif hasattr(entry, "model_dump"):
                # For Pydantic models, get the dict representation
                entry_data = entry.model_dump()
                extract_text_recursive(entry_data)
            elif isinstance(entry, dict):
                # Handle dict entries
                # Include name if present, unless we're skipping section names for "entries" type
                if "name" in entry and not (
                    skip_section_names and entry.get("type") == "entries"
                ):
                    text_parts.append(str(entry["name"]))

                # Always include "by" if present (for quote attributions)
                if "by" in entry:
                    text_parts.append(str(entry["by"]))

                if "text" in entry:
                    text_parts.append(str(entry["text"]))
                elif "entries" in entry:
                    # Recursively process nested entries
                    for nested_entry in entry["entries"]:
                        extract_text_recursive(nested_entry)
                else:
                    # Try to extract any string values from the dict (excluding name and by which we already handled)
                    for key, value in entry.items():
                        if key not in ("name", "by") and isinstance(value, str):
                            text_parts.append(value)
                        elif isinstance(value, list):
                            for item in value:
                                extract_text_recursive(item)
            elif isinstance(entry, list):
                for item in entry:
                    extract_text_recursive(item)
            else:
                text_parts.append(str(entry))

        for entry in entries:
            extract_text_recursive(entry)

        return " ".join(text_parts)

    def get_description_text(self, context: "RenderingContext | None" = None) -> str:
        """Get spell description text using modern service patterns."""
        processor = self.get_processor()

        try:
            # Import here to avoid circular dependencies
            from ..container import get_global_container
            from ..result import Error
            from ..text.tag_resolver import TagResolver

            # If context has tag_resolver, use it directly
            if context and hasattr(context, "tag_resolver") and context.tag_resolver:
                result = processor.get_description_with_context(
                    context.tag_resolver, context
                )
                if isinstance(result, Error):
                    return ""
                return result.unwrap()

            # Try to get tag resolver from service container

            container = get_global_container()
            tag_resolver = container.get_service_sync(TagResolver)

            result = processor.get_description_with_context(tag_resolver, context)
            if isinstance(result, Error):
                return ""
            return result.unwrap()

        except Exception:
            # Fallback to simple text extraction
            return self._extract_simple_text_from_entries(self.entries)

    def get_higher_level_text(self, context: "RenderingContext | None" = None) -> str:
        """Get spell higher level text using modern service patterns."""
        if not self.higher_level:
            return ""

        processor = self.get_processor()

        try:
            # Import here to avoid circular dependencies
            from ..container import get_global_container
            from ..result import Error
            from ..text.tag_resolver import TagResolver

            # If context has tag_resolver, use it directly
            if context and hasattr(context, "tag_resolver") and context.tag_resolver:
                result = processor.get_higher_level_with_context(
                    context.tag_resolver, context
                )
                if isinstance(result, Error):
                    return ""
                return result.unwrap()

            # Try to get tag resolver from service container

            container = get_global_container()
            tag_resolver = container.get_service_sync(TagResolver)

            result = processor.get_higher_level_with_context(tag_resolver, context)
            if isinstance(result, Error):
                return ""
            return result.unwrap()

        except Exception:
            # Fallback to simple text extraction
            return self._extract_simple_text_from_entries(self.higher_level or [])

    def get_spell_list_classes(self) -> str:
        """Get formatted list of classes that can cast this spell."""
        if not self.classes or not self.classes.fromClassList:
            return ""

        class_names = []
        for class_ref in self.classes.fromClassList:
            class_names.append(class_ref.name)

        return ", ".join(class_names)

    def get_latex_safe_name(self) -> str:
        """Get LaTeX-safe version of spell name."""
        # Basic LaTeX escaping for common characters
        name = self.name
        latex_escapes = {
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "^": "\\textasciicircum{}",
            "~": "\\textasciitilde{}",
        }

        for char, escape in latex_escapes.items():
            name = name.replace(char, escape)

        return name

    def get_processor(self) -> "SpellProcessor":
        """Get processor for this spell that can work with services."""
        from .processors import SpellProcessor

        return SpellProcessor(self)

    def resolve_tags_with_service(
        self, tag_resolver: "TagResolver"
    ) -> "Result[Spell, BaseError]":
        """Resolve tags using provided tag resolver service."""
        processor = self.get_processor()
        return processor.resolve_tags(tag_resolver)
