"""Creature data models."""

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field, field_validator

from ..registry import content_type
from ..types import (
    AlignmentDict,
    ChallengeRatingDict,
    CreatureTypeDict,
    DamageDict,
    SpeedDict,
)
from .content import BaseContent

if TYPE_CHECKING:
    from ..error_types import BaseError
    from ..loaders.omnidexer import Omnidexer
    from ..result import Result
    from ..text.tag_resolver import TagResolver
    from .processors import CreatureProcessor


class SkillBonus(BaseModel):
    """Structured skill bonus information."""

    value: str = Field(..., description="Skill bonus value (e.g., '+5')")
    proficiency: str | None = Field(None, description="Proficiency type")
    expertise: bool | None = Field(None, description="Expertise applied")


class SkillChoiceOptions(BaseModel):
    """Skill choice selection options."""

    from_: list[str] | None = Field(
        None, alias="from", description="Skills to choose from"
    )
    count: int | None = Field(None, description="Number of skills to choose")


class SkillChoice(BaseModel):
    """Skill choice/selection information."""

    choose: SkillChoiceOptions | None = Field(
        None, description="Skill choice structure"
    )
    proficiency: str | None = Field(None, description="Default proficiency level")


class CreatureEntryContent(BaseModel):
    """Complex creature entry structure with flexible fields."""

    type: str | None = Field(
        None, description="Entry type (entries, inset, table, etc.)"
    )
    name: str | None = Field(None, description="Entry name/title")
    text: str | None = Field(None, description="Direct text content")
    entries: list[str | dict[str, Any]] | None = Field(
        None, description="Nested entry content"
    )
    source: str | None = Field(None, description="Source reference")
    items: list[str | dict[str, Any]] | None = Field(None, description="List items")

    # Allow additional fields for different entry types
    model_config = {"extra": "allow"}


# Union type for flexible creature entry parsing
CreatureEntry = str | CreatureEntryContent


class ArmorClass(BaseModel):
    """Represents creature armor class."""

    ac: int | None = Field(None, description="Armor class value")
    from_: list[str] | None = Field(None, alias="from", description="AC sources")
    condition: str | None = Field(None, description="Conditional AC")
    special: str | None = Field(None, description="Special AC description")

    def __str__(self) -> str:
        if self.special:
            return self.special
        elif self.ac is not None:
            result = str(self.ac)
            if self.from_:
                sources = ", ".join(self.from_)
                result += f" ({sources})"
            if self.condition:
                result += f" {self.condition}"
            return result
        else:
            return "Unknown"

    def get_processed_ac_text(self) -> str:
        """Get armor class text with 5e.tools markup processed for LaTeX."""
        if self.special:
            try:
                from ...cli.utils import get_tag_resolver

                tag_resolver = get_tag_resolver()
                return str(tag_resolver.process_text(self.special))
            except Exception:
                return self.special
        elif self.ac is not None:
            result = str(self.ac)
            if self.from_:
                # Process 5e.tools markup tags in armor sources
                processed_sources = []
                for source in self.from_:
                    try:
                        from ...cli.utils import get_tag_resolver

                        tag_resolver = get_tag_resolver()
                        processed_source = tag_resolver.process_text(source)
                        processed_sources.append(str(processed_source))
                    except Exception:
                        # Fallback to raw source if tag processing fails
                        processed_sources.append(source)
                sources = ", ".join(processed_sources)
                result += f" ({sources})"
            if self.condition:
                try:
                    from ...cli.utils import get_tag_resolver

                    tag_resolver = get_tag_resolver()
                    processed_condition = tag_resolver.process_text(self.condition)
                    result += f" {processed_condition}"
                except Exception:
                    result += f" {self.condition}"
            return result
        else:
            return "Unknown"


class HitPoints(BaseModel):
    """Represents creature hit points."""

    average: int | None = Field(None, description="Average hit points")
    formula: str | None = Field(None, description="Hit dice formula")
    special: str | None = Field(None, description="Special HP description")

    def __str__(self) -> str:
        if self.special:
            return self.special
        elif self.average is not None and self.formula:
            return f"{self.average} ({self.formula})"
        elif self.average is not None:
            return str(self.average)
        elif self.formula:
            return self.formula
        else:
            return "Unknown"


class Speed(BaseModel):
    """Represents creature movement speeds."""

    walk: int | SpeedDict | None = Field(None, description="Walking speed")
    fly: int | SpeedDict | None = Field(None, description="Flying speed")
    swim: int | SpeedDict | None = Field(None, description="Swimming speed")
    climb: int | SpeedDict | None = Field(None, description="Climbing speed")
    burrow: int | SpeedDict | None = Field(None, description="Burrowing speed")

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
                    # Strip existing parentheses to avoid double wrapping
                    condition = condition.strip().strip("()")
                    speed_text += f" ({condition})"
                speeds.append(speed_text)

        return ", ".join(speeds) if speeds else "0 ft."


class CreatureType(BaseModel):
    """Represents creature type information."""

    type: str | CreatureTypeDict = Field(..., description="Base creature type")
    subtype: str | None = Field(None, description="Creature subtype")
    tags: list[str | CreatureTypeDict] | None = Field(
        None, description="Additional tags"
    )

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "CreatureType":
        """Handle string input and special dict formats by wrapping in type field."""
        if isinstance(obj, str):
            return super().model_validate(
                {"type": obj},
                strict=strict,
                from_attributes=from_attributes,
                context=context,
            )
        elif isinstance(obj, dict):
            # If dict doesn't have 'type' key but has other recognizable keys,
            # wrap the entire dict as the type
            if "type" not in obj and ("choose" in obj or "special" in obj):
                return super().model_validate(
                    {"type": obj},
                    strict=strict,
                    from_attributes=from_attributes,
                    context=context,
                )
        return super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
        )

    def __str__(self) -> str:
        if isinstance(self.type, dict):
            if "choose" in self.type:
                # Handle choice format
                choices = self.type["choose"]
                if isinstance(choices, list):
                    result = " or ".join(choices)
                else:
                    result = str(choices)
            else:
                result = str(self.type)
        else:
            result = self.type

        if self.subtype:
            result += f" ({self.subtype})"

        # Handle tags if present
        if self.tags:
            tag_texts = []
            for tag in self.tags:
                if isinstance(tag, str):
                    tag_texts.append(tag)
                elif isinstance(tag, dict):
                    # Handle complex tag format like {'tag': 'elf', 'prefix': 'High'}
                    if "tag" in tag:
                        tag_text = tag["tag"]
                        if "prefix" in tag:
                            tag_text = f"{tag['prefix']} {tag_text}"
                        tag_texts.append(tag_text)
                    else:
                        tag_texts.append(str(tag))

            if tag_texts:
                if self.subtype:
                    # Tags are part of subtype
                    result = result[:-1] + f", {', '.join(tag_texts)})"
                else:
                    result += f" ({', '.join(tag_texts)})"

        return result


class Ability(BaseModel):
    """Represents a creature ability (trait, action, etc.)."""

    name: str = Field(..., description="Ability name")
    entries: list[CreatureEntry] = Field(..., description="Ability description")

    def __str__(self) -> str:
        return self.name

    def get_processed_name(self) -> str:
        """Get ability name with 5e.tools markup processed for LaTeX."""
        try:
            from ...cli.utils import get_omnidexer, get_tag_resolver
            from ...latex_engine.core.entry_processor import RecursiveEntryProcessor
            from ...renderers.core.interfaces import RenderingContext

            # Get services for proper tag processing
            omnidexer = get_omnidexer()
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "creature",
                },
            )

            # Use recursive entry processor to handle 5e.tools markup
            processor = RecursiveEntryProcessor(use_dnd_template=True)

            # Process the name as if it were entry content
            if self.name:
                # Convert name to entry format and process
                processed_entries = processor.process_entries([self.name], context)
                return "\n".join(processed_entries)
            else:
                return ""

        except Exception:
            # Fallback to original name if processing fails
            return self.name

    def get_description_text(self) -> str:
        """Extract text from complex entry structures using proper entry processing."""
        try:
            from ...cli.utils import get_omnidexer, get_tag_resolver
            from ...latex_engine.core.entry_processor import RecursiveEntryProcessor
            from ...renderers.core.interfaces import RenderingContext

            # Get services for proper tag processing
            omnidexer = get_omnidexer()
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "creature",
                },
            )

            # Use recursive entry processor to handle 5e.tools markup
            processor = RecursiveEntryProcessor(use_dnd_template=True)

            # Process entries and return rendered text
            if self.entries:
                # Convert Pydantic models to dicts for entry processor
                converted_entries: list[str | dict[str, Any]] = []
                for entry in self.entries:
                    if isinstance(entry, str):
                        converted_entries.append(entry)
                    elif hasattr(entry, "model_dump"):
                        # Convert Pydantic model to dict
                        converted_entries.append(entry.model_dump())
                    else:
                        # Fallback for other types - convert to dict or string
                        if hasattr(entry, "__dict__"):
                            converted_entries.append(vars(entry))
                        else:
                            converted_entries.append(str(entry))

                processed_entries = processor.process_entries(
                    converted_entries, context
                )
                return "\n".join(processed_entries)
            else:
                return ""

        except Exception:
            # Fallback to simple text extraction if entry processing fails
            return self._extract_text_from_entries(self.entries)

    def _extract_text_from_entries(self, entries: Any) -> str:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                result = self._extract_text_from_entries(entry)
                if result:
                    text_parts.append(result)
        elif isinstance(entries, CreatureEntryContent):
            # Handle Pydantic CreatureEntryContent objects
            if entries.text:
                text_parts.append(entries.text)
            if entries.name:
                text_parts.append(f"**{entries.name}**")
            if entries.entries:
                result = self._extract_text_from_entries(entries.entries)
                if result:
                    text_parts.append(result)
            if entries.items:
                for item in entries.items:
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
        elif isinstance(entries, dict):
            # Handle structured dict entries (current 5etools format)
            if "entries" in entries:
                result = self._extract_text_from_entries(entries["entries"])
                if result:
                    text_parts.append(result)
            elif "text" in entries:
                text_parts.append(entries["text"])
            # Add name if present (for structured sections)
            if "name" in entries:
                text_parts.append(f"**{entries['name']}**")
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


class SpellcasterSpells(BaseModel):
    """Spell list for a specific spell level."""

    slots: int | None = Field(None, description="Number of spell slots")
    spells: list[str] = Field(..., description="List of spells with {@spell} tags")


class Spellcasting(BaseModel):
    """Creature spellcasting ability."""

    name: str = Field(..., description="Name of the spellcasting feature")
    type: str | None = Field(
        None, description="Type of spellcasting (e.g., 'spellcasting')"
    )
    headerEntries: list[str] | None = Field(None, description="Descriptive header text")
    footerEntries: list[str] | None = Field(None, description="Descriptive footer text")
    spells: dict[str, SpellcasterSpells] | None = Field(
        None, description="Spells by level"
    )
    will: list[str] | None = Field(None, description="At-will spells")
    daily: dict[str, list[str]] | None = Field(None, description="Daily use spells")
    ability: str | None = Field(None, description="Spellcasting ability")
    hidden: list[str] | None = Field(None, description="Hidden sections")
    displayAs: str | None = Field(
        None, description="Where to display this spellcasting feature"
    )

    def get_processed_name(self) -> str:
        """Get spellcasting name with 5e.tools markup processed for LaTeX."""
        try:
            from ...cli.utils import get_omnidexer, get_tag_resolver
            from ...latex_engine.core.entry_processor import RecursiveEntryProcessor
            from ...renderers.core.interfaces import RenderingContext

            # Get services for proper tag processing
            omnidexer = get_omnidexer()
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "creature",
                },
            )

            # Use recursive entry processor to handle 5e.tools markup
            processor = RecursiveEntryProcessor(use_dnd_template=True)

            # Process the name as if it were entry content
            if self.name:
                # Convert name to entry format and process
                processed_entries = processor.process_entries([self.name], context)
                return "\n".join(processed_entries)
            else:
                return ""

        except Exception:
            # Fallback to original name if processing fails
            return self.name

    def get_description_text(self) -> str:
        """Generate formatted spellcasting description with all spell information."""
        try:
            from ...cli.utils import get_omnidexer, get_tag_resolver
            from ...latex_engine.core.entry_processor import RecursiveEntryProcessor
            from ...renderers.core.interfaces import RenderingContext

            # Get services for proper tag processing
            omnidexer = get_omnidexer()
            tag_resolver = get_tag_resolver()

            # Create a proper rendering context for entry processing
            context = RenderingContext(
                output_format="latex",
                debug_mode=False,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata={
                    "source_name": "unknown",
                    "tag_resolver": tag_resolver,
                    "content_type": "creature",
                },
            )

            # Use recursive entry processor to handle 5e.tools markup
            processor = RecursiveEntryProcessor(use_dnd_template=True)

            # Build the complete spellcasting description
            description_parts = []

            # Add header entries
            if self.headerEntries:
                # Cast to correct type - headerEntries is list[str] but process_entries expects list[str | dict[str, Any]]
                processed_headers = processor.process_entries(
                    cast(list[str | dict[str, Any]], self.headerEntries), context
                )
                description_parts.extend(processed_headers)

            # Add spell lists
            if self.spells:
                for level in sorted(self.spells.keys()):
                    spell_data = self.spells[level]
                    if spell_data.spells:
                        # Create spell level entry
                        if level == "0":
                            level_text = (
                                f"Cantrips (at will): {', '.join(spell_data.spells)}"
                            )
                        else:
                            slot_info = (
                                f" ({spell_data.slots} slots)"
                                if spell_data.slots
                                else ""
                            )
                            level_text = f"{level}{'st' if level == '1' else 'nd' if level == '2' else 'rd' if level == '3' else 'th'} level{slot_info}: {', '.join(spell_data.spells)}"

                        processed_level = processor.process_entries(
                            [level_text], context
                        )
                        description_parts.extend(processed_level)

            # Add at-will spells
            if self.will:
                will_text = f"At will: {', '.join(self.will)}"
                processed_will = processor.process_entries([will_text], context)
                description_parts.extend(processed_will)

            # Add daily spells
            if self.daily:
                for frequency, spells in self.daily.items():
                    if spells:
                        daily_text = f"{frequency}: {', '.join(spells)}"
                        processed_daily = processor.process_entries(
                            [daily_text], context
                        )
                        description_parts.extend(processed_daily)

            # Add footer entries
            if self.footerEntries:
                # Cast to correct type - footerEntries is list[str] but process_entries expects list[str | dict[str, Any]]
                processed_footers = processor.process_entries(
                    cast(list[str | dict[str, Any]], self.footerEntries), context
                )
                description_parts.extend(processed_footers)

            return "\n\n".join(description_parts)

        except Exception:
            # Fallback to simple text if processing fails
            fallback_parts = []
            if self.headerEntries:
                fallback_parts.extend(self.headerEntries)
            if self.will:
                fallback_parts.append(f"At will: {', '.join(self.will)}")
            if self.daily:
                for freq, spells in self.daily.items():
                    fallback_parts.append(f"{freq}: {', '.join(spells)}")
            return " ".join(fallback_parts)


@content_type(
    enum_value="creature",
    file_patterns=["bestiary", "monster", "creatures"],
    statblock_tags=["creature"],
    loader_type="json",
)
class Creature(BaseContent):
    """Represents a D&D creature/monster."""

    size: list[str] = Field(..., description="Creature size")
    type: str | CreatureType | CreatureTypeDict = Field(
        ..., description="Creature type"
    )
    alignment: list[str | AlignmentDict] = Field(..., description="Creature alignment")

    # Combat stats
    ac: list[int | ArmorClass] = Field(..., description="Armor class")
    hp: HitPoints = Field(..., description="Hit points")
    speed: Speed = Field(..., description="Movement speeds")

    # Ability scores
    strength: int = Field(..., ge=1, le=30, alias="str")
    dexterity: int = Field(..., ge=1, le=30, alias="dex")
    constitution: int = Field(..., ge=1, le=30, alias="con")
    intelligence: int = Field(..., ge=1, le=30, alias="int")
    wisdom: int = Field(..., ge=1, le=30, alias="wis")
    charisma: int = Field(..., ge=1, le=30, alias="cha")

    # Optional attributes
    save: dict[str, str] | None = Field(None, description="Saving throw bonuses")
    skill: dict[str, str | SkillBonus | list[Any]] | None = Field(
        None, description="Skill bonuses"
    )
    senses: list[str] | None = Field(None, description="Special senses")
    passive: int | str | None = Field(None, description="Passive perception")
    languages: list[str] | None = Field(None, description="Known languages")
    cr: str | int | ChallengeRatingDict | None = Field(
        None, description="Challenge rating"
    )

    # Abilities
    trait: list[Ability] | None = Field(None, description="Traits")
    action: list[Ability] | None = Field(None, description="Actions")
    legendary_actions: int | None = Field(
        None, alias="legendaryActions", description="Number of legendary actions"
    )
    legendary: list[Ability] | None = Field(None, description="Legendary actions")
    reaction: list[Ability] | None = Field(None, description="Reactions")
    bonus: list[Ability] | None = Field(None, description="Bonus actions")

    # Spellcasting abilities
    spellcasting: list[Spellcasting] | None = Field(
        None, description="Spellcasting features"
    )

    # Resistances and immunities
    resist: list[str | DamageDict] | None = Field(
        None, description="Damage resistances"
    )
    immune: list[str | DamageDict] | None = Field(None, description="Damage immunities")
    vulnerable: list[str | DamageDict] | None = Field(
        None, description="Damage vulnerabilities"
    )
    conditionImmune: list[str | DamageDict] | None = Field(
        None, description="Condition immunities"
    )

    @field_validator("type", mode="before")
    @classmethod
    def parse_type(cls, v: Any) -> CreatureType | Any:
        """Parse creature type from various formats."""
        if isinstance(v, str):
            return CreatureType(type=v)  # type: ignore[call-arg]
        elif isinstance(v, dict):
            if "type" in v:
                return CreatureType.model_validate(v)
            else:
                # Handle choice format and other dict structures
                return CreatureType(type=v)  # type: ignore[call-arg]
        return v

    @field_validator("ac", mode="before")
    @classmethod
    def parse_ac(cls, v: Any) -> list[ArmorClass | int] | Any:
        """Parse AC from various formats."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, int):
                    result.append(ArmorClass(ac=item))  # type: ignore[call-arg]
                elif isinstance(item, dict):
                    result.append(ArmorClass.model_validate(item))
                else:
                    result.append(item)
            return result
        elif isinstance(v, int):
            return [ArmorClass(ac=v)]  # type: ignore[call-arg]
        return v

    @field_validator("hp", mode="before")
    @classmethod
    def parse_hp(cls, v: Any) -> HitPoints | Any:
        """Parse HP from various formats."""
        if isinstance(v, dict):
            return HitPoints.model_validate(v)
        return v

    @field_validator("speed", mode="before")
    @classmethod
    def parse_speed(cls, v: Any) -> Speed | Any:
        """Parse speed from various formats."""
        if isinstance(v, dict):
            return Speed.model_validate(v)
        return v

    @field_validator("trait", "action", "legendary", "reaction", "bonus", mode="before")
    @classmethod
    def parse_abilities(cls, v: Any) -> list[Ability] | Any:
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

    @field_validator("skill", mode="before")
    @classmethod
    def parse_skill(cls, v: Any) -> dict[str, str | SkillBonus | list[Any]] | None:
        """Parse skill field, converting structured dicts to SkillBonus models."""
        if v is None:
            return None
        if isinstance(v, dict):
            result: dict[str, str | SkillBonus | list[Any]] = {}
            for skill_name, skill_value in v.items():
                if isinstance(skill_value, dict):
                    # Convert structured skill dict to SkillBonus
                    result[skill_name] = SkillBonus.model_validate(skill_value)
                elif isinstance(skill_value, list):
                    # Keep complex list structures as-is (e.g., choice structures)
                    result[skill_name] = skill_value
                elif isinstance(skill_value, str):
                    # Keep simple string values as-is
                    result[skill_name] = skill_value
                else:
                    # Fallback for unexpected types - convert to string
                    result[skill_name] = str(skill_value)
            return result
        # If not dict or None, we should validate this is the expected type
        if isinstance(v, dict):  # This is redundant but helps type checker
            return v
        # For any other type, let Pydantic handle the validation error
        raise ValueError(f"Expected dict or None for skill field, got {type(v)}")

    @field_validator("spellcasting", mode="before")
    @classmethod
    def parse_spellcasting(cls, v: Any) -> list[Spellcasting] | Any:
        """Parse spellcasting from various formats."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    # Handle spells dict transformation if present
                    if "spells" in item and isinstance(item["spells"], dict):
                        # Transform spells structure to match our model
                        spells_dict = {}
                        for level, spell_data in item["spells"].items():
                            if isinstance(spell_data, dict):
                                spells_dict[level] = SpellcasterSpells.model_validate(
                                    spell_data
                                )
                            else:
                                # Handle edge cases where spell data isn't dict
                                spells_dict[level] = SpellcasterSpells(
                                    spells=spell_data
                                    if isinstance(spell_data, list)
                                    else []
                                )
                        item = dict(item)  # Make a copy
                        item["spells"] = spells_dict

                    # Validate the item using our Spellcasting model
                    result.append(Spellcasting.model_validate(item))
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
        """Get formatted size, type, and alignment text with 5etools compatibility."""
        # Process size abbreviations to full names
        size_text = self._get_size_text()
        type_text = str(self.type)
        alignment_text = self._get_alignment_text()

        return f"{size_text} {type_text}, {alignment_text}"

    def _get_size_text(self) -> str:
        """Convert size abbreviations to full names based on 5etools mapping."""
        # 5etools size abbreviation mapping
        SIZE_ABV_TO_FULL = {
            "F": "Fine",
            "D": "Diminutive",
            "T": "Tiny",
            "S": "Small",
            "M": "Medium",
            "L": "Large",
            "H": "Huge",
            "G": "Gargantuan",
            "C": "Colossal",
            "V": "Varies",
        }

        if isinstance(self.size, list):
            sizes = [SIZE_ABV_TO_FULL.get(s, s) for s in self.size]
            return ", ".join(sizes)
        else:
            return SIZE_ABV_TO_FULL.get(str(self.size), str(self.size))

    def _get_alignment_text(self) -> str:
        """Get formatted alignment text with 5etools compatibility."""
        if not self.alignment:
            return "unaligned"

        return self._process_alignment_list(self.alignment)

    def _process_alignment_list(self, align_list: list) -> str:
        """Process alignment list using 5etools logic."""
        if not align_list:
            return ""

        # 5etools alignment abbreviation mapping
        ALIGNMENT_ABV_TO_FULL = {
            "L": "lawful",
            "N": "neutral",
            "NX": "neutral (law/chaos axis)",
            "NY": "neutral (good/evil axis)",
            "C": "chaotic",
            "G": "good",
            "E": "evil",
            "U": "unaligned",
            "A": "any alignment",
        }

        # Handle complex alignment structures (objects with special properties)
        if any(isinstance(item, dict) for item in align_list):
            processed = []
            for alignment_item in align_list:
                if isinstance(alignment_item, dict):
                    if alignment_item.get("special"):
                        return str(alignment_item["special"])
                    elif "choose" in alignment_item:
                        # Handle choose format: {"choose": [["L", "G"], ["L", "N"]]}
                        # Use the first choice for simplicity
                        choose_options = alignment_item["choose"]
                        if choose_options and isinstance(choose_options[0], list):
                            processed.extend(choose_options[0])
                        else:
                            processed.extend(choose_options)
                    elif "alignment" in alignment_item:
                        sub_align = alignment_item["alignment"]
                        if isinstance(sub_align, list):
                            processed.extend(sub_align)
                        else:
                            processed.append(str(sub_align))
                else:
                    processed.append(str(alignment_item))
            align_list = processed

        # Convert string items to uppercase for processing
        align_list = [str(item).upper() for item in align_list]

        # 5etools alignment processing logic
        if len(align_list) == 1:
            return str(ALIGNMENT_ABV_TO_FULL.get(align_list[0], align_list[0].lower()))
        elif len(align_list) == 2:
            # Pair like ["L", "G"] -> "lawful good"
            return " ".join(
                ALIGNMENT_ABV_TO_FULL.get(a) or a.lower() for a in align_list
            )
        elif len(align_list) == 3:
            if "NX" in align_list and "NY" in align_list and "N" in align_list:
                return "any neutral alignment"
        elif len(align_list) == 4:
            if "L" not in align_list and "NX" not in align_list:
                return "any chaotic alignment"
            elif "G" not in align_list and "NY" not in align_list:
                return "any evil alignment"
            elif "C" not in align_list and "NX" not in align_list:
                return "any lawful alignment"
            elif "E" not in align_list and "NY" not in align_list:
                return "any good alignment"
        elif len(align_list) == 5:
            if "G" not in align_list:
                return "any non-good alignment"
            elif "E" not in align_list:
                return "any non-evil alignment"
            elif "L" not in align_list:
                return "any non-lawful alignment"
            elif "C" not in align_list:
                return "any non-chaotic alignment"

        # Fallback - just join the converted abbreviations
        return " ".join(ALIGNMENT_ABV_TO_FULL.get(a) or a.lower() for a in align_list)

    def get_ac_text(self) -> str:
        """Get formatted AC text."""
        if isinstance(self.ac, list):
            return ", ".join(str(ac) for ac in self.ac)
        return str(self.ac)

    def get_processed_ac_text(self) -> str:
        """Get formatted AC text with 5e.tools markup processed."""
        if isinstance(self.ac, list):
            ac_parts = []
            for ac_item in self.ac:
                if isinstance(ac_item, int):
                    ac_parts.append(str(ac_item))
                else:
                    # ArmorClass object
                    ac_parts.append(ac_item.get_processed_ac_text())
            return ", ".join(ac_parts)
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
            if "special" in self.cr:
                return str(self.cr["special"])
            elif "cr" in self.cr:
                return str(self.cr["cr"])
            else:
                return "Unknown"
        return str(self.cr)

    def get_formatted_saving_throws(self) -> str | None:
        """Get formatted saving throw bonuses."""
        if not hasattr(self, "save") or not self.save:
            return None

        save_parts = []
        ability_names = {
            "str": "Str",
            "dex": "Dex",
            "con": "Con",
            "int": "Int",
            "wis": "Wis",
            "cha": "Cha",
        }

        for ability, bonus in self.save.items():
            ability_name = ability_names.get(ability.lower(), ability.title())
            # Handle both string ("+5") and integer (5) format
            if isinstance(bonus, str):
                save_parts.append(f"{ability_name} {bonus}")
            else:
                sign = "+" if bonus >= 0 else ""
                save_parts.append(f"{ability_name} {sign}{bonus}")

        return ", ".join(save_parts) if save_parts else None

    def get_formatted_skills(self) -> str | None:
        """Get formatted skills list."""
        if not hasattr(self, "skill") or not self.skill:
            return None

        skill_parts = []
        for skill_name, bonus in self.skill.items():
            # Convert camelCase to proper case (e.g., "animalHandling" -> "Animal Handling")
            formatted_skill = "".join(
                [
                    " " + c.lower() if c.isupper() and i > 0 else c
                    for i, c in enumerate(skill_name)
                ]
            )
            formatted_skill = formatted_skill.strip().title()

            # Handle both string ("+5") and integer (5) format
            if isinstance(bonus, str):
                skill_parts.append(f"{formatted_skill} {bonus}")
            elif isinstance(bonus, int | float):
                numeric_bonus = cast(int | float, bonus)
                sign = "+" if numeric_bonus >= 0 else ""
                skill_parts.append(f"{formatted_skill} {sign}{bonus}")
            else:
                skill_parts.append(f"{formatted_skill} {bonus}")

        return ", ".join(skill_parts) if skill_parts else None

    def get_formatted_senses(self) -> str | None:
        """Get formatted senses list."""
        if not hasattr(self, "senses") or not self.senses:
            return None

        return (
            ", ".join(self.senses)
            if isinstance(self.senses, list)
            else str(self.senses)
        )

    def get_processed_senses(self) -> str | None:
        """Get senses with 5e.tools markup processed for LaTeX using modern service patterns."""
        if not self.senses:
            return None

        try:
            # Try to get tag resolver from service container
            from ..container import get_global_container
            from ..services.protocols import TagResolverProtocol

            container = get_global_container()
            tag_resolver = container.get_service_sync(TagResolverProtocol)

            processor = self.get_processor()
            # Use the processor's senses processing method if available
            if hasattr(processor, "_process_senses_with_tag_resolver"):
                return processor._process_senses_with_tag_resolver(
                    self.senses, tag_resolver
                )
            else:
                # Fallback to basic tag processing
                if isinstance(self.senses, str):
                    return tag_resolver.process_text(self.senses)
                else:
                    return str(self.senses)

        except Exception:
            # Fallback to formatted senses
            return self.get_formatted_senses()

    def get_formatted_languages(self) -> str | None:
        """Get formatted languages list."""
        if not hasattr(self, "languages") or not self.languages:
            return None

        return (
            ", ".join(self.languages)
            if isinstance(self.languages, list)
            else str(self.languages)
        )

    def get_formatted_resistances(self) -> str | None:
        """Get formatted damage resistances."""
        if not hasattr(self, "resist") or not self.resist:
            return None

        resistance_parts = []
        for resistance in self.resist:
            if isinstance(resistance, str):
                resistance_parts.append(resistance)
            elif isinstance(resistance, dict):
                # Handle complex resistance structures
                if "resist" in resistance:
                    resist_types = resistance["resist"]
                    if isinstance(resist_types, list):
                        # Filter to only string types to satisfy mypy
                        string_types = [
                            str(r) if not isinstance(r, str) else r
                            for r in resist_types
                        ]
                        resistance_parts.extend(string_types)
                    else:
                        resistance_parts.append(str(resist_types))
                elif "special" in resistance:
                    resistance_parts.append(resistance["special"])
                else:
                    resistance_parts.append(str(resistance))
            else:
                resistance_parts.append(str(resistance))

        return ", ".join(resistance_parts) if resistance_parts else None

    def get_formatted_immunities(self) -> str | None:
        """Get formatted damage immunities."""
        if not hasattr(self, "immune") or not self.immune:
            return None

        immunity_parts = []
        for immunity in self.immune:
            if isinstance(immunity, str):
                immunity_parts.append(immunity)
            elif isinstance(immunity, dict):
                # Handle complex immunity structures
                if "immune" in immunity:
                    immune_types = immunity["immune"]
                    if isinstance(immune_types, list):
                        # Filter to only string types to satisfy mypy
                        string_types = [
                            str(i) if not isinstance(i, str) else i
                            for i in immune_types
                        ]
                        immunity_parts.extend(string_types)
                    else:
                        immunity_parts.append(str(immune_types))
                elif "special" in immunity:
                    immunity_parts.append(immunity["special"])
                else:
                    immunity_parts.append(str(immunity))
            else:
                immunity_parts.append(str(immunity))

        return ", ".join(immunity_parts) if immunity_parts else None

    def get_formatted_vulnerabilities(self) -> str | None:
        """Get formatted damage vulnerabilities."""
        if not hasattr(self, "vulnerable") or not self.vulnerable:
            return None

        vulnerability_parts = []
        for vulnerability in self.vulnerable:
            if isinstance(vulnerability, str):
                vulnerability_parts.append(vulnerability)
            elif isinstance(vulnerability, dict):
                # Handle complex vulnerability structures
                if "vulnerable" in vulnerability:
                    vuln_types = vulnerability["vulnerable"]
                    if isinstance(vuln_types, list):
                        # Filter to only string types to satisfy mypy
                        string_types = [
                            str(v) if not isinstance(v, str) else v for v in vuln_types
                        ]
                        vulnerability_parts.extend(string_types)
                    else:
                        vulnerability_parts.append(str(vuln_types))
                elif "special" in vulnerability:
                    vulnerability_parts.append(vulnerability["special"])
                else:
                    vulnerability_parts.append(str(vulnerability))
            else:
                vulnerability_parts.append(str(vulnerability))

        return ", ".join(vulnerability_parts) if vulnerability_parts else None

    def get_formatted_condition_immunities(self) -> str | None:
        """Get formatted condition immunities."""
        if not hasattr(self, "conditionImmune") or not self.conditionImmune:
            return None

        if isinstance(self.conditionImmune, list):
            # Handle mixed string/dict list
            condition_parts = []
            for condition in self.conditionImmune:
                if isinstance(condition, str):
                    condition_parts.append(condition)
                elif isinstance(condition, dict):
                    # Handle complex condition immunity structure
                    # Cast DamageDict to dict for the method
                    formatted_condition = self._format_condition_immunity_dict(
                        cast(dict[str, Any], condition)
                    )
                    if formatted_condition:
                        condition_parts.append(formatted_condition)
                else:
                    condition_parts.append(str(condition))
            return ", ".join(condition_parts)
        else:
            return str(self.conditionImmune)

    def _format_condition_immunity_dict(self, condition_dict: dict) -> str:
        """Format a complex condition immunity dictionary."""
        # Handle 5etools condition immunity format:
        # {'note': '(with Mind Blank)', 'cond': True, 'conditionImmune': ['charmed']}
        conditions = []
        note = ""

        if "conditionImmune" in condition_dict:
            immune_list = condition_dict["conditionImmune"]
            if isinstance(immune_list, list):
                conditions.extend(immune_list)
            else:
                conditions.append(str(immune_list))

        if "note" in condition_dict:
            note = condition_dict["note"]

        if conditions:
            condition_text = ", ".join(conditions)
            if note:
                return f"{condition_text} {note}"
            else:
                return condition_text

        return ""

    def get_enhanced_cr_text(self) -> str:
        """Get enhanced challenge rating text with XP calculation."""
        if not self.cr:
            return "0 (10 XP)"

        # XP table for challenge ratings
        xp_table = {
            "0": 10,
            "1/8": 25,
            "1/4": 50,
            "1/2": 100,
            "1": 200,
            "2": 450,
            "3": 700,
            "4": 1100,
            "5": 1800,
            "6": 2300,
            "7": 2900,
            "8": 3900,
            "9": 5000,
            "10": 5900,
            "11": 7200,
            "12": 8400,
            "13": 10000,
            "14": 11500,
            "15": 13000,
            "16": 15000,
            "17": 18000,
            "18": 20000,
            "19": 22000,
            "20": 25000,
            "21": 33000,
            "22": 41000,
            "23": 50000,
            "24": 62000,
            "25": 75000,
            "26": 90000,
            "27": 105000,
            "28": 120000,
            "29": 135000,
            "30": 155000,
        }

        cr_value = None
        if isinstance(self.cr, dict):
            if "special" in self.cr:
                return str(self.cr["special"])
            elif "cr" in self.cr:
                cr_value = str(self.cr["cr"])
        else:
            cr_value = str(self.cr)

        if cr_value and cr_value in xp_table:
            xp = xp_table[cr_value]
            return f"{cr_value} ({xp:,} XP)"
        elif cr_value:
            return f"{cr_value} (XP varies)"
        else:
            return "0 (10 XP)"

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Extract spell references from creature traits and actions."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.references import (
            SpellReferenceParser,
            SpellReferenceResolver,
        )

        # Check if spells are available in the omnidexer before attempting resolution
        # During loading, spell references may be processed before spells are loaded
        try:
            spell_count = len(omnidexer.get_all_by_type(ContentType.SPELL))
            if spell_count == 0:
                # Spells not loaded yet, skip resolution to avoid warnings
                return []
        except Exception:
            # Error accessing spell data, skip resolution
            return []

        spell_references = []

        # Parse spell references from all ability lists
        ability_lists = [
            self.trait or [],
            self.action or [],
            self.legendary or [],
            self.reaction or [],
            self.bonus or [],
        ]

        for ability_list in ability_lists:
            for ability in ability_list:
                if isinstance(ability, Ability):
                    # Extract spell references from raw entries before processing
                    for entry in ability.entries:
                        if isinstance(entry, str):
                            # Parse spell references from string entries
                            references = SpellReferenceParser.extract_spell_references(
                                entry
                            )
                            spell_references.extend(references)
                        elif hasattr(entry, "model_dump"):
                            # Convert complex entries to strings for parsing
                            entry_text = str(entry.model_dump())
                            references = SpellReferenceParser.extract_spell_references(
                                entry_text
                            )
                            spell_references.extend(references)

        # Parse spell references from spellcasting features
        if self.spellcasting:
            for spellcasting_feature in self.spellcasting:
                # Extract spells from header entries
                if spellcasting_feature.headerEntries:
                    for header in spellcasting_feature.headerEntries:
                        references = SpellReferenceParser.extract_spell_references(
                            header
                        )
                        spell_references.extend(references)

                # Extract spells from footer entries
                if spellcasting_feature.footerEntries:
                    for footer in spellcasting_feature.footerEntries:
                        references = SpellReferenceParser.extract_spell_references(
                            footer
                        )
                        spell_references.extend(references)

                # Extract spells from spell lists
                if spellcasting_feature.spells:
                    for level, spell_level_data in spellcasting_feature.spells.items():
                        for spell in spell_level_data.spells:
                            references = SpellReferenceParser.extract_spell_references(
                                spell
                            )
                            spell_references.extend(references)

                # Extract at-will spells
                if spellcasting_feature.will:
                    for spell in spellcasting_feature.will:
                        references = SpellReferenceParser.extract_spell_references(
                            spell
                        )
                        spell_references.extend(references)

                # Extract daily spells
                if spellcasting_feature.daily:
                    # Type annotation: daily is dict[str, list[str]]
                    daily_spells: dict[str, list[str]] = spellcasting_feature.daily
                    for frequency, spell_list in daily_spells.items():
                        for spell in spell_list:
                            references = SpellReferenceParser.extract_spell_references(
                                spell
                            )
                            spell_references.extend(references)

        # Resolve spell references to actual spell objects
        if spell_references:
            resolver = SpellReferenceResolver(omnidexer)
            resolved_spells = resolver.resolve_spell_references(spell_references)
            return resolved_spells

        return []

    def requires_full_width_layout(self) -> bool:
        """
        Determine if creature is too large for two-column layout.

        Large creatures with complex stat blocks should use single-column
        layout to prevent awkward page breaks and readability issues.

        Returns:
            True if creature should use full-width layout, False otherwise
        """
        # Primary indicator: creatures with legendary actions are typically large
        if self.legendary and len(self.legendary) > 0:
            return True

        # - Many traits (complex abilities)
        if self.trait and len(self.trait) > 6:
            return True

        # - Many actions (complex combat)
        if self.action and len(self.action) > 6:
            return True

        # - Spellcasters with many spell levels (complex spellcasting)
        # This would require analyzing trait/action text for spellcasting blocks
        # For now, check if creature has both spellcasting traits and many actions
        if self.trait and self.action and len(self.action) > 4:
            for trait in self.trait:
                if hasattr(trait, "name") and "spellcasting" in str(trait.name).lower():
                    return True

        return False

    def get_processor(self) -> "CreatureProcessor":
        """Get processor for this creature that can work with services."""
        from .processors import CreatureProcessor

        return CreatureProcessor(self)

    def resolve_tags_with_service(
        self, tag_resolver: "TagResolver"
    ) -> "Result[Creature, BaseError]":
        """Resolve tags using provided tag resolver service."""
        processor = self.get_processor()
        return processor.resolve_tags(tag_resolver)

    def enrich_with_services(
        self, omnidexer: "Omnidexer", tag_resolver: "TagResolver"
    ) -> "Result[Creature, BaseError]":
        """Enrich creature using provided services."""
        processor = self.get_processor()
        return processor.enrich_with_content(omnidexer, tag_resolver)
