"""Creature data models."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


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

    walk: int | dict[str, Any] | None = Field(None, description="Walking speed")
    fly: int | dict[str, Any] | None = Field(None, description="Flying speed")
    swim: int | dict[str, Any] | None = Field(None, description="Swimming speed")
    climb: int | dict[str, Any] | None = Field(None, description="Climbing speed")
    burrow: int | dict[str, Any] | None = Field(None, description="Burrowing speed")

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

    type: str | dict[str, Any] = Field(..., description="Base creature type")
    subtype: str | None = Field(None, description="Creature subtype")
    tags: list[str | dict[str, Any]] | None = Field(None, description="Additional tags")

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
    entries: list[str | dict[str, Any]] = Field(..., description="Ability description")

    def __str__(self) -> str:
        return self.name

    def get_description_text(self) -> str:
        """Extract text from complex entry structures."""
        return self._extract_text_from_entries(self.entries)

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


class Creature(BaseContent):
    """Represents a D&D creature/monster."""

    size: list[str] = Field(..., description="Creature size")
    type: str | CreatureType | dict[str, Any] = Field(..., description="Creature type")
    alignment: list[str | dict[str, Any]] = Field(..., description="Creature alignment")

    # Combat stats
    ac: list[int | ArmorClass | dict[str, Any]] = Field(..., description="Armor class")
    hp: HitPoints | dict[str, Any] = Field(..., description="Hit points")
    speed: Speed | dict[str, Any] = Field(..., description="Movement speeds")

    # Ability scores
    strength: int = Field(..., ge=1, le=30, alias="str")
    dexterity: int = Field(..., ge=1, le=30, alias="dex")
    constitution: int = Field(..., ge=1, le=30, alias="con")
    intelligence: int = Field(..., ge=1, le=30, alias="int")
    wisdom: int = Field(..., ge=1, le=30, alias="wis")
    charisma: int = Field(..., ge=1, le=30, alias="cha")

    # Optional attributes
    save: dict[str, str] | None = Field(None, description="Saving throw bonuses")
    skill: dict[str, str | list[Any] | Any] | None = Field(
        None, description="Skill bonuses"
    )
    senses: list[str] | None = Field(None, description="Special senses")
    passive: int | str | None = Field(None, description="Passive perception")
    languages: list[str] | None = Field(None, description="Known languages")
    cr: str | int | dict[str, Any] | None = Field(None, description="Challenge rating")

    # Abilities
    trait: list[Ability | dict[str, Any]] | None = Field(None, description="Traits")
    action: list[Ability | dict[str, Any]] | None = Field(None, description="Actions")
    legendary_actions: int | None = Field(
        None, alias="legendaryActions", description="Number of legendary actions"
    )
    legendary: list[Ability | dict[str, Any]] | None = Field(
        None, description="Legendary actions"
    )
    reaction: list[Ability | dict[str, Any]] | None = Field(
        None, description="Reactions"
    )
    bonus: list[Ability | dict[str, Any]] | None = Field(
        None, description="Bonus actions"
    )

    # Resistances and immunities
    resist: list[str | dict[str, Any]] | None = Field(
        None, description="Damage resistances"
    )
    immune: list[str | dict[str, Any]] | None = Field(
        None, description="Damage immunities"
    )
    vulnerable: list[str | dict[str, Any]] | None = Field(
        None, description="Damage vulnerabilities"
    )
    conditionImmune: list[str | dict[str, Any]] | None = Field(
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
        alignment_text = self._get_alignment_text()

        return f"{size_text} {type_text}, {alignment_text}"

    def _get_alignment_text(self) -> str:
        """Get formatted alignment text handling complex structures."""
        if not self.alignment:
            return "unaligned"

        alignment_parts = []
        for alignment_item in self.alignment:
            if isinstance(alignment_item, str):
                alignment_parts.append(alignment_item)
            elif isinstance(alignment_item, dict):
                # Handle complex alignment structures like {'alignment': ['N', 'G']}
                if "alignment" in alignment_item:
                    sub_alignment = alignment_item["alignment"]
                    if isinstance(sub_alignment, list):
                        alignment_parts.extend(sub_alignment)
                    else:
                        alignment_parts.append(str(sub_alignment))
                else:
                    alignment_parts.append(str(alignment_item))
            else:
                alignment_parts.append(str(alignment_item))

        return " ".join(alignment_parts) if alignment_parts else "unaligned"

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
                sign = "+" if bonus >= 0 else ""
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
                        resistance_parts.extend(resist_types)
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
                        immunity_parts.extend(immune_types)
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
                        vulnerability_parts.extend(vuln_types)
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
                else:
                    condition_parts.append(str(condition))
            return ", ".join(condition_parts)
        else:
            return str(self.conditionImmune)

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
        from ..references import SpellReferenceParser, SpellReferenceResolver

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
                    # Extract text from ability entries
                    text = ability.get_description_text()
                    # Parse spell references
                    references = SpellReferenceParser.extract_spell_references(text)
                    spell_references.extend(references)

        # Resolve spell references to actual spell objects
        if spell_references:
            resolver = SpellReferenceResolver(omnidexer)
            resolved_spells = resolver.resolve_spell_references(spell_references)
            return resolved_spells

        return []
