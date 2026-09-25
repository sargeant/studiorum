"""Creature data models."""

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field, field_validator

from studiorum.core.logging import get_logger

from ..encounter import XP_BY_CR
from ..types import (
    AlignmentDict,
    ChallengeRatingDict,
    CreatureTypeDict,
    DamageDict,
    SpeedDict,
)
from .content import BaseContent

logger = get_logger(__name__)

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


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

    def get_processed_name(self) -> str:
        """Get entry name for display (used by template)."""
        return self.name or ""


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
        if self.ac is not None:
            result = str(self.ac)
            if self.from_:
                sources = ", ".join(self.from_)
                result += f" ({sources})"
            if self.condition:
                result += f" {self.condition}"
            return result
        return "Unknown"


class HitPoints(BaseModel):
    """Represents creature hit points."""

    average: int | None = Field(None, description="Average hit points")
    formula: str | None = Field(None, description="Hit dice formula")
    special: str | None = Field(None, description="Special HP description")

    def __str__(self) -> str:
        if self.special:
            return self.special
        if self.average is not None and self.formula:
            return f"{self.average} ({self.formula})"
        if self.average is not None:
            return str(self.average)
        if self.formula:
            return self.formula
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
        extra: Any = None,
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
        if isinstance(obj, dict):
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


class SpellcasterSpells(BaseModel):
    """Spell list for a specific spell level."""

    slots: int | None = Field(None, description="Number of spell slots")
    spells: list[str] = Field(..., description="List of spells with {@spell} tags")


class SpellEntry(BaseModel):
    """Individual spell entry that can be either a string or object with entry/hidden fields."""

    entry: str = Field(..., description="Spell tag (e.g., '{@spell wish}')")
    hidden: bool | None = Field(
        None, description="Whether this spell should be hidden in display"
    )


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
    will: list[str | SpellEntry] | None = Field(None, description="At-will spells")
    daily: dict[str, list[str | SpellEntry]] | None = Field(
        None, description="Daily use spells"
    )
    ability: str | None = Field(None, description="Spellcasting ability")
    hidden: list[str] | None = Field(None, description="Hidden sections")
    displayAs: str | None = Field(
        None, description="Where to display this spellcasting feature"
    )


class Creature(BaseContent):
    """Represents a 5e creature/monster."""

    size: list[str] = Field(..., description="Creature size")
    type: str | CreatureType | CreatureTypeDict = Field(
        ..., description="Creature type"
    )
    alignment: list[str | AlignmentDict] | None = Field(
        None, description="Creature alignment"
    )

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
    lair_actions: list[CreatureEntry] | None = Field(
        None, description="Lair actions (populated from legendary group data)"
    )
    reaction: list[Ability] | None = Field(None, description="Reactions")
    bonus: list[Ability] | None = Field(None, description="Bonus actions")

    # 5etools parity fields
    legendary_actions_lair: int | None = Field(
        None, alias="legendaryActionsLair", description="Legendary actions when in lair"
    )
    legendary_header: list[CreatureEntry] | None = Field(
        None,
        alias="legendaryHeader",
        description="Custom legendary actions header entries",
    )
    traits_header: list[CreatureEntry] | None = Field(
        None, alias="traitsHeader", description="Custom Traits header entries"
    )
    actions_header: list[CreatureEntry] | None = Field(
        None, alias="actionsHeader", description="Custom Actions header entries"
    )
    reactions_header: list[CreatureEntry] | None = Field(
        None, alias="reactionsHeader", description="Custom Reactions header entries"
    )
    bonus_header: list[CreatureEntry] | None = Field(
        None, alias="bonusHeader", description="Custom Bonus Actions header entries"
    )
    is_named_creature: bool | None = Field(
        None,
        alias="isNamedCreature",
        description="Named/unique creature (affects pronouns)",
    )
    short_name: str | bool | None = Field(
        None, alias="shortName", description="Short reference name"
    )

    # Optional read-only compatibility (not yet wired)
    display_name: str | None = Field(None, alias="_displayName")
    display_short_name: str | None = Field(None, alias="_displayShortName")

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
        if isinstance(v, dict):
            if "type" in v:
                return CreatureType.model_validate(v)
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
        if isinstance(v, int):
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
                    if "choose" in alignment_item:
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
        if len(align_list) == 2:
            # Pair like ["L", "G"] -> "lawful good"
            return " ".join(
                ALIGNMENT_ABV_TO_FULL.get(a) or a.lower() for a in align_list
            )
        if len(align_list) == 3:
            if "NX" in align_list and "NY" in align_list and "N" in align_list:
                return "any neutral alignment"
        elif len(align_list) == 4:
            if "L" not in align_list and "NX" not in align_list:
                return "any chaotic alignment"
            if "G" not in align_list and "NY" not in align_list:
                return "any evil alignment"
            if "C" not in align_list and "NX" not in align_list:
                return "any lawful alignment"
            if "E" not in align_list and "NY" not in align_list:
                return "any good alignment"
        elif len(align_list) == 5:
            if "G" not in align_list:
                return "any non-good alignment"
            if "E" not in align_list:
                return "any non-evil alignment"
            if "L" not in align_list:
                return "any non-lawful alignment"
            if "C" not in align_list:
                return "any non-chaotic alignment"

        # Fallback - just join the converted abbreviations
        return " ".join(ALIGNMENT_ABV_TO_FULL.get(a) or a.lower() for a in align_list)

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

    def get_initiative_modifier(self) -> int:
        """Get initiative modifier for display.

        Defaults to the Dexterity modifier, but if 5etools 2024 data provides
        an `initiative` field with proficiency scaling (e.g.,
        `{ "proficiency": 2 }`), include proficiency bonus accordingly to
        match 2024 statblock conventions.
        """

        # Base from Dexterity modifier
        base = self.get_ability_modifier(self.dexterity)

        init_data = getattr(self, "initiative", None)
        if init_data is None:
            return base

        # Helper: compute proficiency bonus from CR (2014/2024 ranges)
        def _proficiency_bonus_from_cr(cr: Any) -> int:
            # Convert CR to a numeric value
            def _numeric_cr(val: Any) -> float:
                if val is None:
                    return 0.0
                # Handle dict form { "cr": "X" } or { "special": "..." }
                if isinstance(val, dict):
                    if "cr" in val:
                        return _numeric_cr(val["cr"])
                    return 0.0
                s = str(val).strip()
                if "/" in s:
                    try:
                        num, den = s.split("/", 1)
                        return float(num) / float(den)
                    except Exception:
                        return 0.0
                try:
                    return float(s)
                except Exception:
                    return 0.0

            ncr = _numeric_cr(self.cr)
            if ncr <= 4:
                return 2
            if ncr <= 8:
                return 3
            if ncr <= 12:
                return 4
            if ncr <= 16:
                return 5
            if ncr <= 20:
                return 6
            if ncr <= 24:
                return 7
            if ncr <= 28:
                return 8
            return 9

        # If initiative is a simple number, treat as override
        if isinstance(init_data, int | float):
            try:
                return int(init_data)
            except Exception:
                return base

        # If initiative is a string number, try to parse
        if isinstance(init_data, str):
            s = init_data.strip().lstrip("+")
            if s and s.replace("-", "").isdigit():
                try:
                    return int(s)
                except Exception:
                    logger.debug(
                        "Failed to parse initiative override '%s' as int",
                        init_data,
                        exc_info=True,
                    )
            return base

        # If initiative is a dict, check for proficiency scaling per 5etools 2024
        if isinstance(init_data, dict):
            prof_mult = init_data.get("proficiency")
            try:
                if prof_mult is not None:
                    pm = int(prof_mult)
                    pb = _proficiency_bonus_from_cr(self.cr)
                    return base + pm * pb
            except Exception:
                # Fall back to base if parsing fails
                return base

        # Fallback
        return base

    def get_cr_text(self) -> str:
        """Get formatted challenge rating text."""
        if self.cr is None:
            return "Unknown"
        if isinstance(self.cr, dict):
            if "special" in self.cr:
                return str(self.cr["special"])
            if "cr" in self.cr:
                return str(self.cr["cr"])
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

    def get_save_value(self, ability: str) -> int | None:
        """Get saving throw bonus for a specific ability.

        Args:
            ability: Ability name (str, dex, con, int, wis, cha)

        Returns:
            Save bonus as integer, or None if not proficient
            Note: Returns None for expressions containing "PB" (proficiency bonus)
        """
        if not hasattr(self, "save") or not self.save:
            return None

        save_value = self.save.get(ability.lower())
        if save_value is None:
            return None

        # Handle proficiency bonus expressions (e.g., "3 plus PB", "+2 plus PB")
        if isinstance(save_value, str) and "PB" in save_value:
            # Default to level 1 if no context provided
            return self._evaluate_pb_expression(save_value, creature_level=1)

        # Convert string format ("+5" or "5") to integer
        if isinstance(save_value, str):
            return int(save_value.replace("+", ""))
        return int(save_value)

    def _calculate_proficiency_bonus(self, creature_level: int) -> int:
        """Calculate proficiency bonus for a given creature level.

        Args:
            creature_level: Creature level (1-20)

        Returns:
            Proficiency bonus (+2 to +6)
        """
        # 5e proficiency bonus progression
        if creature_level >= 17:
            return 6
        if creature_level >= 13:
            return 5
        if creature_level >= 9:
            return 4
        if creature_level >= 5:
            return 3
        return 2

    def _evaluate_pb_expression(self, expression: str, creature_level: int) -> int:
        """Evaluate a proficiency bonus expression like '3 plus PB' or '+2 plus PB'.

        Args:
            expression: String expression containing PB
            creature_level: Creature level for calculating PB

        Returns:
            Evaluated integer value
        """
        import re

        pb = self._calculate_proficiency_bonus(creature_level)

        # Normalize the expression
        expr = expression.strip().lower()
        expr = expr.replace("plus", "+")

        # Handle patterns like "3 plus PB", "+2 plus PB", "PB", etc.
        # Replace PB with the actual proficiency bonus value
        expr = expr.replace("pb", str(pb))

        # Evaluate simple arithmetic expressions
        # Remove any extra whitespace around operators
        expr = re.sub(r"\s*([+\-])\s*", r"\1", expr)

        try:
            # Use ast.literal_eval for safe arithmetic evaluation
            # Only allow numbers, +, -, and whitespace
            if re.match(r"^[+\-\d\s]+$", expr):
                import ast

                return int(ast.literal_eval(expr))
            raise ValueError(f"Invalid PB expression: {expression}")
        except Exception:
            # Fallback: try to extract base number and add PB
            base_match = re.search(r"([+\-]?\d+)", expression)
            if base_match:
                base = int(base_match.group(1))
                return base + pb
            # If we can't parse it, just return the PB
            return pb

    def get_save_value_with_level(
        self, ability: str, creature_level: int
    ) -> int | None:
        """Get saving throw bonus for a specific ability at a given creature level.

        Args:
            ability: Ability name (str, dex, con, int, wis, cha)
            creature_level: Creature level for PB calculations

        Returns:
            Save bonus as integer, or None if not proficient
        """
        if not hasattr(self, "save") or not self.save:
            return None

        save_value = self.save.get(ability.lower())
        if save_value is None:
            return None

        # Handle proficiency bonus expressions
        if isinstance(save_value, str) and "PB" in save_value:
            return self._evaluate_pb_expression(save_value, creature_level)

        # Convert string format ("+5" or "5") to integer
        if isinstance(save_value, str):
            return int(save_value.replace("+", ""))
        return int(save_value)

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
        """Get formatted damage resistances following 5etools format."""
        if not hasattr(self, "resist") or not self.resist:
            return None

        resistance_groups = []
        for resistance in self.resist:
            if isinstance(resistance, str):
                resistance_groups.append(resistance)
            elif isinstance(resistance, dict):
                # Handle complex resistance structures
                if "resist" in resistance:
                    resist_types = resistance["resist"]
                    if isinstance(resist_types, list):
                        # Format as "type1, type2, and type3" for multiple types
                        string_types = [
                            str(r) if not isinstance(r, str) else r
                            for r in resist_types
                        ]
                        if len(string_types) == 1:
                            resist_text = string_types[0]
                        elif len(string_types) == 2:
                            resist_text = f"{string_types[0]} and {string_types[1]}"
                        else:
                            resist_text = f"{', '.join(string_types[:-1])}, and {string_types[-1]}"

                        # Add note if present
                        if "note" in resistance:
                            resist_text = f"{resist_text} {resistance['note']}"
                        resistance_groups.append(resist_text)
                    else:
                        resist_text = str(resist_types)
                        if "note" in resistance:
                            resist_text = f"{resist_text} {resistance['note']}"
                        resistance_groups.append(resist_text)
                elif "special" in resistance:
                    resistance_groups.append(resistance["special"])
                else:
                    resistance_groups.append(str(resistance))
            else:
                resistance_groups.append(str(resistance))

        return "; ".join(resistance_groups) if resistance_groups else None

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
            return condition_text

        return ""

    def get_enhanced_cr_text(self) -> str:
        """Get enhanced challenge rating text with XP calculation.

        Supports multiple CR variants:
        - Base CR with optional XP override
        - Lair variant with "when encountered in lair"
        - Coven variant with "when part of a coven"

        Returns formatted text like:
        - "24 (62,000 XP)"
        - "24 (62,000 XP) or 24 (75,000 XP) when encountered in lair"
        - "3 (700 XP) or 5 (1,800 XP) when part of a coven"
        """
        if not self.cr:
            return "0 (10 XP)"

        def format_cr_with_xp(cr: str | None, xp_override: int | None = None) -> str:
            """Format a single CR value with XP."""
            if not cr:
                return ""

            # Use override XP if provided, otherwise look up from table
            if xp_override is not None:
                xp = xp_override
            elif cr in XP_BY_CR:
                xp = XP_BY_CR[cr]
            else:
                return f"{cr} (XP varies)"

            return f"{cr} ({xp:,} XP)"

        # Handle dictionary format with variants
        if isinstance(self.cr, dict):
            # Special override takes precedence
            if "special" in self.cr and self.cr["special"]:
                return str(self.cr["special"])

            # Build list of CR variants
            variants = []

            # Base CR
            base_cr = self.cr.get("cr")
            if base_cr:
                base_xp = self.cr.get("xp")
                variants.append(format_cr_with_xp(base_cr, base_xp))

            # Lair variant
            lair_cr = self.cr.get("lair")
            xp_lair = self.cr.get("xpLair")
            if lair_cr or xp_lair:
                # If only xpLair is provided, use base CR
                lair_cr_value = lair_cr if lair_cr else base_cr
                lair_text = format_cr_with_xp(lair_cr_value, xp_lair)
                if lair_text:
                    variants.append(f"{lair_text} when encountered in lair")

            # Coven variant
            coven_cr = self.cr.get("coven")
            xp_coven = self.cr.get("xpCoven")
            if coven_cr or xp_coven:
                # If only xpCoven is provided, use coven CR
                coven_text = format_cr_with_xp(coven_cr, xp_coven)
                if coven_text:
                    variants.append(f"{coven_text} when part of a coven")

            # Join variants with " or "
            if variants:
                return " or ".join(variants)
            return "0 (10 XP)"

        # Handle simple string/int format
        cr_value = str(self.cr)
        return format_cr_with_xp(cr_value)

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
                    for spell_entry in spellcasting_feature.will:
                        spell_text = (
                            spell_entry
                            if isinstance(spell_entry, str)
                            else spell_entry.entry
                        )
                        references = SpellReferenceParser.extract_spell_references(
                            spell_text
                        )
                        spell_references.extend(references)

                # Extract daily spells
                if spellcasting_feature.daily:
                    for frequency, spell_list in spellcasting_feature.daily.items():
                        for spell_entry in spell_list:
                            spell_text = (
                                spell_entry
                                if isinstance(spell_entry, str)
                                else spell_entry.entry
                            )
                            references = SpellReferenceParser.extract_spell_references(
                                spell_text
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

    def get_pronoun_subject(self) -> str:
        """Subject pronoun for the creature: they/it (5etools parity)."""
        return "they" if self.is_named_creature else "it"

    def get_pronoun_object(self) -> str:
        """Object pronoun for the creature: them/its (5etools uses 'its' for generic)."""
        return "them" if self.is_named_creature else "its"

    def get_pronoun_possessive(self) -> str:
        """Possessive pronoun: their/its."""
        return "their" if self.is_named_creature else "its"

    def get_short_name(
        self, *, is_title_case: bool = False, is_sentence_case: bool = False
    ) -> str:
        """Short name compatible with 5etools behavior (approximate casing rules).

        - Use self.short_name if provided (True→use self.name; str→use value).
        - Else: first segment before a comma in self.name.
        - Named: do not prefix; Generic: prefix with 'the/The' depending on case.
        - Title/sentence casing simplified; acceptable for parity in output.
        """
        base_name = None
        if self.short_name is True:
            base_name = self.name
        elif isinstance(self.short_name, str):
            base_name = self.short_name
        else:
            base_name = (self.name or "").split(",")[0]

        if self.is_named_creature and base_name:
            base_name = base_name.split(" ")[0]

        if is_title_case and base_name:
            base_name = base_name.title()
        elif is_sentence_case and base_name:
            base_name = base_name[:1].upper() + base_name[1:].lower()
        elif not self.is_named_creature and base_name:
            base_name = base_name.lower()

        if not self.is_named_creature:
            prefix = "The " if (is_title_case or is_sentence_case) else "the "
            return f"{prefix}{base_name}"
        return base_name or ""

    def get_section_header(self, section_name: str) -> list[CreatureEntry] | None:
        """Return custom header entries for a section name, if present."""
        field_name = f"{section_name}_header"
        return getattr(self, field_name, None)

    def get_legendary_actions_header(
        self, *, style_hint: str | None = "classic"
    ) -> list[CreatureEntry] | None:
        """Generate classic legendary actions header entries.

        Precedence: legendary_header → generic 'legendary' section header → generated text.
        Defaults: action_count = (legendary_actions or 3), lair_count = (legendary_actions_lair or action_count).
        """
        if not getattr(self, "legendary", None):
            return None
        if self.legendary_header:
            return self.legendary_header
        generic = self.get_section_header("legendary")
        if generic:
            return generic

        action_count = (
            self.legendary_actions if getattr(self, "legendary_actions", None) else 3
        )
        lair_count = (
            self.legendary_actions_lair
            if getattr(self, "legendary_actions_lair", None)
            else action_count
        )

        name_title = self.get_short_name(is_title_case=True)
        pro_poss = self.get_pronoun_possessive()

        header = f"{name_title} can take {action_count} legendary action"
        if action_count != 1:
            header += "s"
        if lair_count != action_count:
            header += f" (or {lair_count} when in {pro_poss} lair)"
        header += ", choosing from the options below. Only one legendary action can be used at a time and only at the end of another creature's turn. "
        header += f"{name_title} regains spent legendary actions at the start of {pro_poss} turn."

        return [header]
