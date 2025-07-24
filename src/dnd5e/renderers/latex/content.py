"""LaTeX content-specific renderers."""

from typing import Any

from ...core.models.adventures import Adventure
from ...core.models.backgrounds import Background
from ...core.models.books import Book
from ...core.models.classes import Class
from ...core.models.content import BaseContent, ContentType
from ...core.models.creatures import Creature
from ...core.models.feats import Feat
from ...core.models.items import Item
from ...core.models.races import Race
from ...core.models.spells import Spell
from ..base import ContentRenderer, RenderContext
from .template_engine import LaTeXTemplateEngine


class LaTeXContentRenderer(ContentRenderer):
    """Base LaTeX content renderer with common functionality."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize LaTeX content renderer.

        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.template_engine = LaTeXTemplateEngine(config)

    @property
    def output_format(self) -> str:
        """Return the output format."""
        return "latex"

    def escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters.

        Args:
            text: Text to escape

        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""

        # LaTeX special characters
        replacements = {
            "\\": r"\textbackslash{}",
            "{": r"\{",
            "}": r"\}",
            "$": r"\$",
            "&": r"\&",
            "%": r"\%",
            "#": r"\#",
            "^": r"\textasciicircum{}",
            "_": r"\_",
            "~": r"\textasciitilde{}",
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result

    def process_text_with_tags(self, text: str, context: RenderContext) -> str:
        """Process text containing 5etools tags.

        Args:
            text: Text that may contain tags
            context: Rendering context with tag resolver

        Returns:
            Text with tags processed
        """
        if not text or not context.tag_resolver:
            return self.escape_latex(text)

        return context.tag_resolver.process_text(text)


class LaTeXSpellRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for spell content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize spell renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True
        self.use_spell_header = config.get("use_spell_header", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.SPELL}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render spell content to LaTeX using DND template environments.

        Args:
            content: Spell to render
            context: Rendering context

        Returns:
            LaTeX representation of spell using DND template
        """
        if not isinstance(content, Spell):
            raise ValueError(f"Expected Spell, got {type(content)}")

        # Determine template to use
        template_name = "spell_dnd" if self.use_dnd_template else "spell"

        # Build comprehensive template variables for DND template
        variables = self._build_spell_variables(content, context)

        return self.template_engine.render_template(template_name, variables)

    def _build_spell_variables(
        self, spell: Spell, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for spell rendering.

        Args:
            spell: Spell to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Basic info
        variables = {
            "name": self.escape_latex(spell.name),
            "level": spell.level,
            "school": self._expand_school_abbreviation(spell.school),
            "level_school_text": self._format_level_school(spell.level, spell.school),
        }

        # Casting details with enhanced formatting
        variables.update(
            {
                "casting_time": self._format_casting_time_enhanced(spell.casting_time),
                "range_text": self._format_range_enhanced(spell.range),
                "components_text": self._format_components_enhanced(spell.components),
                "duration_text": self._format_duration_enhanced(spell.duration),
            }
        )

        # Description with tag processing
        variables["description"] = self._format_entries(spell.entries, context)

        # Higher levels
        variables["higher_levels"] = (
            self._format_higher_levels(spell, context) if spell.higher_level else None
        )

        # Enhanced metadata
        variables.update(
            {
                "damage_types": getattr(spell, "damage_inflict", None),
                "saving_throws": self._format_saves(
                    getattr(spell, "saving_throw", None)
                ),
                "spell_attacks": self._format_attacks(
                    getattr(spell, "spell_attack", None)
                ),
                "classes_text": self._format_classes(getattr(spell, "classes", None)),
                "spell_lists": self._extract_spell_lists(
                    getattr(spell, "classes", None)
                ),
                "source_reference": self._format_source_reference(spell.source),
            }
        )

        # Template configuration
        variables.update(
            {
                "use_spell_header": self.use_spell_header,
            }
        )

        # Legacy compatibility
        variables.update(
            {
                "level_text": spell.get_level_text(),  # Fallback for old template
            }
        )

        return variables

    def _format_casting_time(self, time_data: list[dict[str, Any]]) -> str:
        """Format casting time data.

        Args:
            time_data: Time data from spell

        Returns:
            Formatted casting time string
        """
        if not time_data:
            return "Unknown"

        time_parts = []
        for time_entry in time_data:
            if "number" in time_entry and "unit" in time_entry:
                number = time_entry["number"]
                unit = time_entry["unit"]
                if number == 1:
                    time_parts.append(f"1 {unit}")
                else:
                    time_parts.append(f"{number} {unit}s")

        return ", ".join(time_parts) if time_parts else "Unknown"

    def _format_range(self, range_data: dict[str, Any]) -> str:
        """Format range data.

        Args:
            range_data: Range data from spell

        Returns:
            Formatted range string
        """
        if not range_data:
            return "Unknown"

        range_type = range_data.get("type", "")

        if range_type == "point":
            distance = range_data.get("distance", {})
            if distance.get("type") == "self":
                return "Self"
            elif distance.get("type") == "touch":
                return "Touch"
            elif distance.get("type") == "feet":
                amount = distance.get("amount", 0)
                return f"{amount} feet"
        elif range_type == "sphere":
            radius = range_data.get("distance", {}).get("amount", 0)
            return f"Self ({radius}-foot radius)"
        elif range_type == "cone":
            distance = range_data.get("distance", {}).get("amount", 0)
            return f"Self ({distance}-foot cone)"
        elif range_type == "line":
            distance = range_data.get("distance", {}).get("amount", 0)
            return f"Self ({distance}-foot line)"

        return str(range_data)

    def _format_components(self, components: dict[str, Any]) -> str:
        """Format components data.

        Args:
            components: Components data from spell

        Returns:
            Formatted components string
        """
        if not components:
            return "None"

        parts = []
        if components.get("v"):
            parts.append("V")
        if components.get("s"):
            parts.append("S")
        if components.get("m"):
            material = components.get("m")
            if isinstance(material, str):
                parts.append(f"M ({self.escape_latex(material)})")
            else:
                parts.append("M")

        return ", ".join(parts) if parts else "None"

    def _format_duration(self, duration_data: list[dict[str, Any]]) -> str:
        """Format duration data.

        Args:
            duration_data: Duration data from spell

        Returns:
            Formatted duration string
        """
        if not duration_data:
            return "Unknown"

        duration_parts = []
        for duration_entry in duration_data:
            duration_type = duration_entry.get("type", "")

            if duration_type == "instant":
                duration_parts.append("Instantaneous")
            elif duration_type == "timed":
                amount = duration_entry.get("duration", {}).get("amount", 1)
                unit = duration_entry.get("duration", {}).get("type", "minute")
                concentration = duration_entry.get("concentration", False)

                duration_text = f"{amount} {unit}"
                if amount != 1:
                    duration_text += "s"

                if concentration:
                    duration_text = f"Concentration, up to {duration_text}"

                duration_parts.append(duration_text)
            else:
                duration_parts.append(duration_type.title())

        return ", ".join(duration_parts) if duration_parts else "Unknown"

    def _format_entries(
        self, entries: list[str | dict[str, Any]], context: RenderContext
    ) -> str:
        """Format spell description entries.

        Args:
            entries: List of description text
            context: Rendering context

        Returns:
            Formatted description
        """
        if not entries:
            return ""

        formatted_entries = []
        for entry in entries:
            if isinstance(entry, str):
                formatted_entries.append(self.process_text_with_tags(entry, context))
            else:
                # Handle complex entry structures
                formatted_entries.append(str(entry))

        return "\n\n".join(formatted_entries)

    def _format_higher_levels(self, spell: Spell, context: RenderContext) -> str | None:
        """Format higher levels text.

        Args:
            spell: Spell object
            context: Rendering context

        Returns:
            Formatted higher levels text or None
        """
        if not spell.higher_level:
            return None

        # Handle higher level entries
        higher_entries = []
        for entry in spell.higher_level:
            if isinstance(entry, str):
                higher_entries.append(self.process_text_with_tags(entry, context))
            elif isinstance(entry, dict) and "entries" in entry:
                for sub_entry in entry["entries"]:
                    higher_entries.append(
                        self.process_text_with_tags(sub_entry, context)
                    )

        return " ".join(higher_entries) if higher_entries else None

    def _expand_school_abbreviation(self, school: str) -> str:
        """Expand school abbreviations to full names.

        Args:
            school: School abbreviation or full name

        Returns:
            Full school name
        """
        school_expansions = {
            "A": "Abjuration",
            "C": "Conjuration",
            "D": "Divination",
            "E": "Enchantment",
            "V": "Evocation",
            "I": "Illusion",
            "N": "Necromancy",
            "T": "Transmutation",
        }
        return school_expansions.get(school, school)

    def _format_level_school(self, level: int, school: str) -> str:
        """Format spell level and school for DND template.

        Args:
            level: Spell level
            school: School abbreviation or name

        Returns:
            Formatted level and school text
        """
        school_name = self._expand_school_abbreviation(school)

        if level == 0:
            return f"{school_name} cantrip"
        elif level == 1:
            return f"1st-level {school_name.lower()}"
        elif level == 2:
            return f"2nd-level {school_name.lower()}"
        elif level == 3:
            return f"3rd-level {school_name.lower()}"
        else:
            return f"{level}th-level {school_name.lower()}"

    def _format_casting_time_enhanced(self, casting_time: list[Any]) -> str:
        """Format casting time with enhanced handling.

        Args:
            casting_time: Casting time data

        Returns:
            Formatted casting time string
        """
        if not casting_time:
            return "1 action"

        time_parts = []
        for time_entry in casting_time:
            if hasattr(time_entry, "number") and hasattr(time_entry, "unit"):
                # Pydantic SpellTime model
                number = time_entry.number
                unit = time_entry.unit
                condition = getattr(time_entry, "condition", None)
            elif isinstance(time_entry, dict):
                # Dictionary format
                number = time_entry.get("number", 1)
                unit = time_entry.get("unit", "action")
                condition = time_entry.get("condition")
            else:
                time_parts.append(str(time_entry))
                continue

            if number == 1:
                time_text = f"1 {unit}"
            else:
                time_text = f"{number} {unit}s"

            if condition:
                time_text += f" ({condition})"

            time_parts.append(time_text)

        return ", ".join(time_parts) if time_parts else "1 action"

    def _format_range_enhanced(self, range_data: Any) -> str:
        """Format range with enhanced handling.

        Args:
            range_data: Range data

        Returns:
            Formatted range string
        """
        if not range_data:
            return "Self"

        if hasattr(range_data, "type"):
            # Pydantic SpellRange model
            range_type = range_data.type
            distance = getattr(range_data, "distance", None)
        elif isinstance(range_data, dict):
            # Dictionary format
            range_type = range_data.get("type", "self")
            distance = range_data.get("distance")
        else:
            return str(range_data)

        if range_type == "point" and distance:
            if isinstance(distance, dict):
                if distance.get("type") == "self":
                    return "Self"
                elif distance.get("type") == "touch":
                    return "Touch"
                elif distance.get("type") == "feet":
                    amount = distance.get("amount", 0)
                    return f"{amount} feet"
                elif distance.get("type") == "miles":
                    amount = distance.get("amount", 0)
                    return f"{amount} mile{'s' if amount != 1 else ''}"
        elif range_type == "sphere" and distance:
            if isinstance(distance, dict):
                radius = distance.get("amount", 0)
                return f"Self ({radius}-foot radius)"
        elif range_type == "cone" and distance:
            if isinstance(distance, dict):
                length = distance.get("amount", 0)
                return f"Self ({length}-foot cone)"
        elif range_type == "line" and distance:
            if isinstance(distance, dict):
                length = distance.get("amount", 0)
                return f"Self ({length}-foot line)"
        elif range_type == "sight":
            return "Sight"
        elif range_type == "unlimited":
            return "Unlimited"
        elif range_type == "self":
            return "Self"

        return str(range_data)

    def _format_components_enhanced(self, components: Any) -> str:
        """Format components with enhanced handling.

        Args:
            components: Components data

        Returns:
            Formatted components string
        """
        if not components:
            return "None"

        parts = []

        if hasattr(components, "verbal"):
            # Pydantic SpellComponent model
            if components.verbal:
                parts.append("V")
            if components.somatic:
                parts.append("S")
            if components.material:
                if isinstance(components.material, str):
                    parts.append(f"M ({self.escape_latex(components.material)})")
                else:
                    parts.append("M")
        elif isinstance(components, dict):
            # Dictionary format
            if components.get("v"):
                parts.append("V")
            if components.get("s"):
                parts.append("S")
            if components.get("m"):
                material = components.get("m")
                if isinstance(material, str):
                    parts.append(f"M ({self.escape_latex(material)})")
                else:
                    parts.append("M")

        return ", ".join(parts) if parts else "None"

    def _format_duration_enhanced(self, duration: list[Any]) -> str:
        """Format duration with enhanced handling.

        Args:
            duration: Duration data

        Returns:
            Formatted duration string
        """
        if not duration:
            return "Instantaneous"

        duration_parts = []
        for duration_entry in duration:
            if hasattr(duration_entry, "type"):
                # Pydantic SpellDuration model
                duration_type = duration_entry.type
                concentration = getattr(duration_entry, "concentration", False)
                duration_details = getattr(duration_entry, "duration", None)
            elif isinstance(duration_entry, dict):
                # Dictionary format
                duration_type = duration_entry.get("type", "instant")
                concentration = duration_entry.get("concentration", False)
                duration_details = duration_entry.get("duration")
            else:
                duration_parts.append(str(duration_entry))
                continue

            if duration_type == "instant":
                duration_parts.append("Instantaneous")
            elif duration_type == "timed" and duration_details:
                if isinstance(duration_details, dict):
                    amount = duration_details.get("amount", 1)
                    unit = duration_details.get("type", "minute")
                    duration_text = f"{amount} {unit}"
                    if amount != 1:
                        duration_text += "s"

                    if concentration:
                        duration_text = f"Concentration, up to {duration_text}"

                    duration_parts.append(duration_text)
            elif duration_type == "permanent":
                duration_parts.append("Until dispelled")
            elif duration_type == "special":
                duration_parts.append("Special")
            else:
                duration_parts.append(duration_type.title())

        return ", ".join(duration_parts) if duration_parts else "Instantaneous"

    def _format_saves(self, saving_throws: list[str] | None) -> list[str] | None:
        """Format saving throws list.

        Args:
            saving_throws: List of saving throw types

        Returns:
            Formatted saving throws list or None
        """
        if not saving_throws:
            return None

        # Expand abbreviations
        save_expansions = {
            "str": "Strength",
            "dex": "Dexterity",
            "con": "Constitution",
            "int": "Intelligence",
            "wis": "Wisdom",
            "cha": "Charisma",
        }

        formatted_saves = []
        for save in saving_throws:
            expanded = save_expansions.get(save.lower(), save.title())
            formatted_saves.append(expanded)

        return formatted_saves

    def _format_attacks(self, spell_attacks: list[str] | None) -> list[str] | None:
        """Format spell attack types.

        Args:
            spell_attacks: List of attack types

        Returns:
            Formatted attack types list or None
        """
        if not spell_attacks:
            return None

        # Format attack types
        attack_expansions = {
            "MS": "Melee Spell",
            "RS": "Ranged Spell",
            "MW": "Melee Weapon",
            "RW": "Ranged Weapon",
        }

        formatted_attacks = []
        for attack in spell_attacks:
            expanded = attack_expansions.get(attack, attack.title())
            formatted_attacks.append(expanded)

        return formatted_attacks

    def _format_classes(self, classes_data: dict[str, Any] | None) -> str | None:
        """Format spell classes information.

        Args:
            classes_data: Classes data dictionary

        Returns:
            Formatted classes string or None
        """
        if not classes_data:
            return None

        class_names = []
        for class_key, class_info in classes_data.items():
            if class_key == "fromClassList":
                for class_entry in class_info:
                    if isinstance(class_entry, dict) and "name" in class_entry:
                        class_names.append(class_entry["name"])
                    else:
                        class_names.append(str(class_entry))

        return ", ".join(sorted(class_names)) if class_names else None

    def _extract_spell_lists(
        self, classes_data: dict[str, Any] | None
    ) -> dict[str, list[str]] | None:
        """Extract spell list information by class.

        Args:
            classes_data: Classes data dictionary

        Returns:
            Dictionary mapping class names to spell list info or None
        """
        if not classes_data:
            return None

        # This would need more complex implementation based on actual data structure
        # For now, return None as placeholder
        return None

    def _format_source_reference(self, source: Any) -> str:
        """Format source reference.

        Args:
            source: Source object or data

        Returns:
            Formatted source reference
        """
        if not source:
            return ""

        if hasattr(source, "abbreviation"):
            # Pydantic Source model
            abbr = str(source.abbreviation)
            page = getattr(source, "page", None)
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        elif isinstance(source, dict):
            # Dictionary format
            abbr = str(source.get("abbreviation", ""))
            page = source.get("page")
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        else:
            return str(source)


class LaTeXCreatureRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for creature content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize creature renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.CREATURE}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render creature content to LaTeX using DND template environments.

        Args:
            content: Creature to render
            context: Rendering context

        Returns:
            LaTeX representation of creature using DND template
        """
        if not isinstance(content, Creature):
            raise ValueError(f"Expected Creature, got {type(content)}")

        # Determine template to use
        template_name = "creature_dnd" if self.use_dnd_template else "creature"

        # Build comprehensive template variables for DND template
        variables = self._build_creature_variables(content, context)

        return self.template_engine.render_template(template_name, variables)

    def _build_creature_variables(
        self, creature: Creature, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for creature rendering.

        Args:
            creature: Creature to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Basic info
        variables: dict[str, Any] = {
            "name": self.escape_latex(creature.name),
            "size_text": self._format_size(creature.size),
            "type_text": self._format_type(creature.type),
            "alignment_text": self._format_alignment(creature.alignment),
        }

        # Armor Class (enhanced for DND template)
        ac_data = self._parse_ac_data(creature.ac)
        variables.update(
            {
                "ac_value": ac_data["value"],
                "ac_source": ac_data["source"],
                "ac_text": ac_data["text"],  # Fallback for legacy template
            }
        )

        # Hit Points (enhanced for DND template)
        hp_data = self._parse_hp_data(creature.hp)
        variables.update(
            {
                "hp_average": hp_data["average"],
                "hp_formula": hp_data["formula"],
                "hp_text": hp_data["text"],  # Fallback for legacy template
            }
        )

        # Speed
        variables["speed_text"] = self._format_speed(creature.speed)

        # Ability Scores (enhanced for DND template)
        variables.update(
            {
                "str_score": creature.strength,
                "dex_score": creature.dexterity,
                "con_score": creature.constitution,
                "int_score": creature.intelligence,
                "wis_score": creature.wisdom,
                "cha_score": creature.charisma,
                # Legacy format for backward compatibility
                "str_text": self._format_ability_score(creature.strength),
                "dex_text": self._format_ability_score(creature.dexterity),
                "con_text": self._format_ability_score(creature.constitution),
                "int_text": self._format_ability_score(creature.intelligence),
                "wis_text": self._format_ability_score(creature.wisdom),
                "cha_text": self._format_ability_score(creature.charisma),
            }
        )

        # Details section
        saving_throws = self._format_saving_throws(getattr(creature, "save", None))
        skills = self._format_skills(getattr(creature, "skill", None))
        damage_resistances = self._format_damage_list(getattr(creature, "resist", None))
        damage_immunities = self._format_damage_list(getattr(creature, "immune", None))
        damage_vulnerabilities = self._format_damage_list(
            getattr(creature, "vulnerable", None)
        )
        condition_immunities = self._format_condition_list(
            getattr(creature, "conditionImmune", None)
        )
        senses = self._format_senses(getattr(creature, "senses", None))
        languages = self._format_languages(getattr(creature, "languages", None))
        cr_text = self._format_cr_enhanced(creature.cr)

        variables.update(
            {
                "saving_throws": saving_throws,
                "skills": skills,
                "damage_resistances": damage_resistances,
                "damage_immunities": damage_immunities,
                "damage_vulnerabilities": damage_vulnerabilities,
                "condition_immunities": condition_immunities,
                "senses": senses,
                "languages": languages,
                "cr_text": cr_text,
                "has_details": any(
                    [
                        saving_throws,
                        skills,
                        damage_resistances,
                        damage_immunities,
                        damage_vulnerabilities,
                        condition_immunities,
                        senses,
                        languages,
                    ]
                ),
            }
        )

        # Traits
        variables["traits"] = self._format_creature_abilities(
            getattr(creature, "trait", None), context
        )

        # Spellcasting (if present)
        spellcasting_data = self._extract_spellcasting_trait(
            getattr(creature, "trait", None)
        )
        if spellcasting_data:
            variables["spellcasting"] = spellcasting_data

        # Actions
        variables["actions"] = self._format_creature_abilities(
            getattr(creature, "action", None), context
        )

        # Legendary Actions
        legendary_actions_count = getattr(creature, "legendary_actions", None)
        legendary_actions = self._format_creature_abilities(
            getattr(creature, "legendary", None), context
        )
        variables.update(
            {
                "legendary_actions_count": legendary_actions_count,
                "legendary_actions": legendary_actions,
                "legendary_actions_description": self._get_legendary_actions_description(
                    creature.name, legendary_actions_count
                ),
            }
        )

        # Reactions
        variables["reactions"] = self._format_creature_abilities(
            getattr(creature, "reaction", None), context
        )

        # Lair Actions and Regional Effects (if present)
        variables.update(
            {
                "lair_actions": None,  # Would need to be added to creature model
                "lair_actions_description": None,
                "regional_effects": None,  # Would need to be added to creature model
                "regional_effects_description": None,
            }
        )

        # Layout options
        variables["full_width"] = self._should_use_full_width(creature)

        return variables

    def _format_size(self, size_data: list[str]) -> str:
        """Format creature size.

        Args:
            size_data: Size data from creature

        Returns:
            Formatted size string
        """
        if not size_data:
            return "Medium"

        size_map = {
            "T": "Tiny",
            "S": "Small",
            "M": "Medium",
            "L": "Large",
            "H": "Huge",
            "G": "Gargantuan",
        }

        return size_map.get(size_data[0], size_data[0])

    def _format_alignment(self, alignment: list[str | dict[str, Any]]) -> str:
        """Format creature alignment.

        Args:
            alignment: Alignment data

        Returns:
            Formatted alignment string
        """
        if not alignment:
            return "unaligned"

        alignment_map = {
            "L": "lawful",
            "N": "neutral",
            "C": "chaotic",
            "G": "good",
            "E": "evil",
        }

        parts = []
        for align in alignment:
            if isinstance(align, str):
                if align in alignment_map:
                    parts.append(alignment_map[align])
                else:
                    parts.append(align.lower())
            elif isinstance(align, dict):
                # Handle dict-based alignment data
                if "alignment" in align:
                    align_str = str(align["alignment"])
                    if align_str in alignment_map:
                        parts.append(alignment_map[align_str])
                    else:
                        parts.append(align_str.lower())
                else:
                    parts.append(str(align))

        return " ".join(parts) if parts else "unaligned"

    def _format_ac(self, ac_data: list[Any]) -> str:
        """Format armor class.

        Args:
            ac_data: AC data from creature

        Returns:
            Formatted AC string
        """
        if not ac_data:
            return "10"

        ac_entry = ac_data[0]
        if hasattr(ac_entry, "ac"):
            # Pydantic ArmorClass model
            return str(ac_entry)
        elif isinstance(ac_entry, dict):
            # Dictionary format
            ac_value = ac_entry.get("ac", 10)
            ac_from = ac_entry.get("from", [])
            if ac_from:
                return f"{ac_value} ({', '.join(ac_from)})"
            return str(ac_value)
        else:
            return str(ac_entry)

    def _format_hp(self, hp_data: Any) -> str:
        """Format hit points.

        Args:
            hp_data: HP data from creature

        Returns:
            Formatted HP string
        """
        if not hp_data:
            return "1 (1d4)"

        if hasattr(hp_data, "average"):
            # Pydantic HitPoints model
            return str(hp_data)
        elif isinstance(hp_data, dict):
            # Dictionary format
            average = hp_data.get("average", 1)
            formula = hp_data.get("formula", "1d4")
            return f"{average} ({formula})"
        else:
            return str(hp_data)

    def _format_speed(self, speed_data: Any) -> str:
        """Format speed.

        Args:
            speed_data: Speed data from creature

        Returns:
            Formatted speed string
        """
        if not speed_data:
            return "30 ft."

        if hasattr(speed_data, "walk"):
            # Pydantic Speed model
            return str(speed_data)
        elif isinstance(speed_data, dict):
            # Dictionary format
            speed_parts = []
            for speed_type, speed_value in speed_data.items():
                if speed_type == "walk":
                    speed_parts.append(f"{speed_value} ft.")
                else:
                    speed_parts.append(f"{speed_type} {speed_value} ft.")
            return ", ".join(speed_parts)
        else:
            return str(speed_data)

    def _format_ability_score(self, score: int) -> str:
        """Format ability score with modifier.

        Args:
            score: Ability score value

        Returns:
            Formatted score with modifier
        """
        modifier = (score - 10) // 2
        sign = "+" if modifier >= 0 else ""
        return f"{score} ({sign}{modifier})"

    def _format_cr(self, cr: str) -> str:
        """Format challenge rating.

        Args:
            cr: Challenge rating

        Returns:
            Formatted CR string
        """
        return f"{cr} (XP varies)"

    def _format_skills(self, skills: dict[str, Any] | None) -> str | None:
        """Format skills list.

        Args:
            skills: Skills data

        Returns:
            Formatted skills string or None
        """
        if not skills:
            return None

        skill_parts = []
        for skill, bonus in skills.items():
            # Handle both string ("+5") and integer (5) format
            if isinstance(bonus, str):
                # Already formatted with sign
                skill_parts.append(f"{skill.title()} {bonus}")
            else:
                # Integer format, add sign
                sign = "+" if bonus >= 0 else ""
                skill_parts.append(f"{skill.title()} {sign}{bonus}")

        return ", ".join(skill_parts) if skill_parts else None

    def _format_damage_list(self, damage_data: list[Any] | None) -> str | None:
        """Format damage resistance/immunity list.

        Args:
            damage_data: Damage data

        Returns:
            Formatted damage list or None
        """
        if not damage_data:
            return None

        damage_parts = []
        for item in damage_data:
            if isinstance(item, str):
                damage_parts.append(item)
            elif isinstance(item, dict):
                # Handle complex damage structures
                damage_parts.append(str(item))

        return ", ".join(damage_parts) if damage_parts else None

    def _format_condition_list(self, condition_data: list[str] | None) -> str | None:
        """Format condition immunity list.

        Args:
            condition_data: Condition data

        Returns:
            Formatted condition list or None
        """
        if not condition_data:
            return None

        return ", ".join(condition_data)

    def _format_senses(self, senses_data: list[str] | None) -> str | None:
        """Format senses list.

        Args:
            senses_data: Senses data

        Returns:
            Formatted senses string or None
        """
        if not senses_data:
            return None

        return ", ".join(senses_data)

    def _format_languages(self, languages_data: list[str] | None) -> str | None:
        """Format languages list.

        Args:
            languages_data: Languages data

        Returns:
            Formatted languages string or None
        """
        if not languages_data:
            return None

        return ", ".join(languages_data)

    def _format_traits(
        self, traits_data: list[dict[str, Any]] | None, context: RenderContext
    ) -> list[dict[str, str]] | None:
        """Format creature traits.

        Args:
            traits_data: Traits data
            context: Rendering context

        Returns:
            List of formatted trait dicts or None
        """
        if not traits_data:
            return None

        formatted_traits = []
        for trait in traits_data:
            if isinstance(trait, dict):
                name = trait.get("name", "")
                entries = trait.get("entries", [])

                description_parts = []
                for entry in entries:
                    if isinstance(entry, str):
                        description_parts.append(
                            self.process_text_with_tags(entry, context)
                        )

                formatted_traits.append(
                    {
                        "name": self.escape_latex(name),
                        "description": " ".join(description_parts),
                    }
                )

        return formatted_traits if formatted_traits else None

    def _format_actions(
        self, actions_data: list[dict[str, Any]] | None, context: RenderContext
    ) -> list[dict[str, str]] | None:
        """Format creature actions.

        Args:
            actions_data: Actions data
            context: Rendering context

        Returns:
            List of formatted action dicts or None
        """
        if not actions_data:
            return None

        formatted_actions = []
        for action in actions_data:
            if isinstance(action, dict):
                name = action.get("name", "")
                entries = action.get("entries", [])

                description_parts = []
                for entry in entries:
                    if isinstance(entry, str):
                        description_parts.append(
                            self.process_text_with_tags(entry, context)
                        )

                formatted_actions.append(
                    {
                        "name": self.escape_latex(name),
                        "description": " ".join(description_parts),
                    }
                )

        return formatted_actions if formatted_actions else None

    def _parse_ac_data(self, ac_data: list[Any]) -> dict[str, Any]:
        """Parse armor class data for DND template.

        Args:
            ac_data: AC data from creature

        Returns:
            Dictionary with AC value, source, and formatted text
        """
        if not ac_data:
            return {"value": 10, "source": None, "text": "10"}

        ac_entry = ac_data[0]
        if hasattr(ac_entry, "ac"):
            # Pydantic ArmorClass model
            value = ac_entry.ac
            source = ", ".join(ac_entry.from_) if ac_entry.from_ else None
            return {
                "value": value,
                "source": source,
                "text": f"{value} ({source})" if source else str(value),
            }
        elif isinstance(ac_entry, dict):
            # Dictionary format
            value = ac_entry.get("ac", 10)
            source_list = ac_entry.get("from", [])
            source = ", ".join(source_list) if source_list else None
            return {
                "value": value,
                "source": source,
                "text": f"{value} ({source})" if source else str(value),
            }
        else:
            # Simple integer
            value = int(ac_entry) if isinstance(ac_entry, int | str) else 10
            return {"value": value, "source": None, "text": str(value)}

    def _parse_hp_data(self, hp_data: Any) -> dict[str, Any]:
        """Parse hit points data for DND template.

        Args:
            hp_data: HP data from creature

        Returns:
            Dictionary with HP average, formula, and formatted text
        """
        if not hp_data:
            return {"average": 1, "formula": "1d4", "text": "1 (1d4)"}

        if hasattr(hp_data, "average"):
            # Pydantic HitPoints model
            average = hp_data.average
            formula = hp_data.formula
            return {
                "average": average,
                "formula": formula,
                "text": f"{average} ({formula})" if formula else str(average),
            }
        elif isinstance(hp_data, dict):
            # Dictionary format
            average = hp_data.get("average", 1)
            formula = hp_data.get("formula", "1d4")
            return {
                "average": average,
                "formula": formula,
                "text": f"{average} ({formula})",
            }
        else:
            # Simple integer
            average = int(hp_data) if isinstance(hp_data, int | str) else 1
            return {"average": average, "formula": None, "text": str(average)}

    def _format_type(self, type_data: Any) -> str:
        """Format creature type with enhanced handling.

        Args:
            type_data: Type data from creature

        Returns:
            Formatted type string
        """
        if not type_data:
            return "humanoid"

        if isinstance(type_data, str):
            return type_data
        elif hasattr(type_data, "type"):
            # Pydantic CreatureType model
            base_type = type_data.type
            if isinstance(base_type, dict):
                return str(base_type.get("type", "humanoid"))
            return str(base_type)
        elif isinstance(type_data, dict):
            # Dictionary format
            return str(type_data.get("type", "humanoid"))
        else:
            return str(type_data)

    def _format_saving_throws(self, save_data: dict[str, str] | None) -> str | None:
        """Format saving throw bonuses.

        Args:
            save_data: Saving throw data

        Returns:
            Formatted saving throws string or None
        """
        if not save_data:
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

        for ability, bonus in save_data.items():
            ability_name = ability_names.get(ability.lower(), ability.title())
            # Handle both string ("+5") and integer (5) format
            if isinstance(bonus, str):
                save_parts.append(f"{ability_name} {bonus}")
            else:
                sign = "+" if bonus >= 0 else ""
                save_parts.append(f"{ability_name} {sign}{bonus}")

        return ", ".join(save_parts) if save_parts else None

    def _format_cr_enhanced(self, cr: Any) -> str:
        """Format challenge rating with XP calculation.

        Args:
            cr: Challenge rating data

        Returns:
            Formatted CR string with XP
        """
        if not cr:
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

        cr_str = str(cr)
        xp = xp_table.get(cr_str, 0)

        if xp > 0:
            return f"{cr_str} ({xp:,} XP)"
        else:
            return f"{cr_str} (XP varies)"

    def _format_creature_abilities(
        self, abilities_data: list[dict[str, Any]] | None, context: RenderContext
    ) -> list[dict[str, Any]] | None:
        """Format creature abilities (traits, actions, etc.) with enhanced data.

        Args:
            abilities_data: Abilities data
            context: Rendering context

        Returns:
            List of formatted ability dicts or None
        """
        if not abilities_data:
            return None

        formatted_abilities = []
        for ability in abilities_data:
            if isinstance(ability, dict):
                name = ability.get("name", "")
                entries = ability.get("entries", [])

                description_parts = []
                for entry in entries:
                    if isinstance(entry, str):
                        description_parts.append(
                            self.process_text_with_tags(entry, context)
                        )
                    elif isinstance(entry, dict):
                        # Handle complex entry structures like attack details
                        description_parts.append(str(entry))

                # Extract cost for legendary actions
                cost = None
                if "legendaryGroup" in ability or "cost" in ability:
                    cost = ability.get("cost", 1)

                formatted_abilities.append(
                    {
                        "name": self.escape_latex(name),
                        "description": " ".join(description_parts),
                        "cost": cost,
                    }
                )

        return formatted_abilities if formatted_abilities else None

    def _extract_spellcasting_trait(
        self, traits_data: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Extract spellcasting information from traits.

        Args:
            traits_data: Traits data

        Returns:
            Spellcasting data dictionary or None
        """
        if not traits_data:
            return None

        for trait in traits_data:
            if (
                isinstance(trait, dict)
                and trait.get("name", "").lower() == "spellcasting"
            ):
                entries = trait.get("entries", [])
                description = " ".join(
                    str(entry) for entry in entries if isinstance(entry, str)
                )

                # Extract spell information (simplified)
                return {
                    "description": description,
                    "spells": {},  # Would need more complex parsing
                    "slots": {},  # Would need more complex parsing
                }

        return None

    def _get_legendary_actions_description(
        self, creature_name: str, count: int | None
    ) -> str | None:
        """Generate legendary actions description.

        Args:
            creature_name: Name of the creature
            count: Number of legendary actions

        Returns:
            Legendary actions description or None
        """
        if not count:
            return None

        name = self.escape_latex(creature_name)
        return (
            f"{name} can take {count} legendary actions, choosing from the options below. "
            f"Only one legendary action option can be used at a time and only at the end of "
            f"another creature's turn. {name} regains spent legendary actions at the start of its turn."
        )

    def _should_use_full_width(self, creature: Creature) -> bool:
        """Determine if creature should use full-width layout.

        Args:
            creature: Creature to check

        Returns:
            True if should use full-width layout
        """
        # Use full width for large creatures or those with many abilities
        large_sizes = ["L", "H", "G"]  # Large, Huge, Gargantuan
        has_many_abilities = (
            len(getattr(creature, "trait", []) or []) > 3
            or len(getattr(creature, "action", []) or []) > 3
            or getattr(creature, "legendary", None) is not None
        )

        return any(size in large_sizes for size in creature.size) or has_many_abilities


class LaTeXItemRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for item content using DND table formatting."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize item renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True
        self.table_format = config.get("table_format", False) if config else False

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.ITEM}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render item content to LaTeX using DND table formatting.

        Args:
            content: Item to render
            context: Rendering context

        Returns:
            LaTeX representation of item using DND template
        """
        if not isinstance(content, Item):
            raise ValueError(f"Expected Item, got {type(content)}")

        # Determine template to use
        template_name = "item_dnd" if self.use_dnd_template else "item"

        # Build comprehensive template variables for DND template
        variables = self._build_item_variables(content, context)

        return self.template_engine.render_template(template_name, variables)

    def render_item_table(
        self, items: list[Item], context: RenderContext, table_title: str = "Items"
    ) -> str:
        """Render multiple items as a DND table.

        Args:
            items: List of items to render
            context: Rendering context
            table_title: Title for the table

        Returns:
            LaTeX table representation of items
        """
        if not items:
            return ""

        # Determine table columns based on item types
        column_data = self._determine_table_columns(items)

        # Build variables for table rendering
        variables = {
            "is_table_format": True,
            "table_title": table_title,
            "table_columns": column_data["specification"],
            "table_headers": column_data["headers"],
            "items": [self._build_table_item_data(item, context) for item in items],
            "include_descriptions": any(
                getattr(item, "entries", None) for item in items
            ),
        }

        template_name = "item_dnd" if self.use_dnd_template else "item"
        return self.template_engine.render_template(template_name, variables)

    def _build_item_variables(
        self, item: Item, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for item rendering.

        Args:
            item: Item to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Basic info
        variables = {
            "name": self.escape_latex(item.name),
            "is_table_format": False,
            "use_subsection": getattr(context, "use_subsections", True),
        }

        # Item metadata line
        metadata_parts = []
        type_text = self._format_type_enhanced(item.type)
        if type_text:
            metadata_parts.append(type_text)

        rarity_text = self._format_rarity_enhanced(
            item.rarity, item.requires_attunement
        )
        if rarity_text:
            metadata_parts.append(rarity_text)

        variables["item_metadata"] = (
            ", ".join(metadata_parts) if metadata_parts else None
        )

        # Individual property texts
        variables.update(
            {
                "type_text": type_text,
                "rarity_text": rarity_text,
                "weight_text": self._format_weight(item.weight),
                "value_text": self._format_value(item.value),
                "ac_text": self._format_ac_enhanced(item),
                "damage_text": self._format_damage_enhanced(item),
                "range_text": self._format_range_item(item),
                "properties_list": self._format_properties_enhanced(item.properties),
                "requires_attunement_text": self._format_attunement(
                    item.requires_attunement
                ),
                "charges_text": self._format_charges(item.charges),
            }
        )

        # Description with tag processing
        variables["description"] = self._format_entries(
            getattr(item, "entries", []), context
        )

        # Properties table flag
        variables["has_properties_table"] = any(
            [
                variables["ac_text"],
                variables["damage_text"],
                variables["range_text"],
                variables["weight_text"],
                variables["value_text"],
                variables["properties_list"],
                variables["requires_attunement_text"],
                variables["charges_text"],
            ]
        )

        # Magic properties
        variables["magic_properties"] = self._extract_magic_properties(item)

        # Weapon statistics
        if item.is_weapon():
            variables["weapon_statistics"] = self._build_weapon_statistics(item)
        else:
            variables["weapon_statistics"] = None

        # Armor statistics
        if item.is_armor():
            variables["armor_statistics"] = self._build_armor_statistics(item)
        else:
            variables["armor_statistics"] = None

        # Variants (for magic items with multiple forms)
        variables["variants"] = self._extract_variants(item)

        # Creation rules (for magic items)
        variables["creation_rules"] = self._extract_creation_rules(item)

        # Source reference
        variables["source_reference"] = self._format_source_reference(item.source)

        return variables

    def _build_table_item_data(
        self, item: Item, context: RenderContext
    ) -> dict[str, str]:
        """Build item data for table display.

        Args:
            item: Item to process
            context: Rendering context

        Returns:
            Dictionary with formatted item data for tables
        """
        return {
            "name": self.escape_latex(item.name),
            "type_text": self._format_type_enhanced(item.type),
            "rarity_text": self._format_rarity_enhanced(
                item.rarity, item.requires_attunement
            ),
            "value_text": self._format_value(item.value) or "",
            "weight_text": self._format_weight(item.weight) or "",
            "description": self._format_entries(getattr(item, "entries", []), context),
        }

    def _determine_table_columns(self, items: list[Item]) -> dict:
        """Determine appropriate table columns based on items.

        Args:
            items: List of items to analyze

        Returns:
            Dictionary with LaTeX column specification and headers
        """
        # Check what properties are present across items
        has_weight = any(getattr(item, "weight", None) for item in items)
        has_value = any(getattr(item, "value", None) for item in items)
        has_rarity = any(getattr(item, "rarity", None) for item in items)

        # Check if items are focused on weapons or armor
        weapon_count = sum(
            1 for item in items if hasattr(item, "is_weapon") and item.is_weapon()
        )
        armor_count = sum(
            1 for item in items if hasattr(item, "is_armor") and item.is_armor()
        )

        headers = ["name", "type"]
        columns = "X l"

        # If majority are weapons, include weapon-specific columns
        if weapon_count > len(items) / 2:
            headers.extend(["damage", "properties"])
            columns += " l l"
        # If majority are armor, include armor-specific columns
        elif armor_count > len(items) / 2:
            headers.extend(["ac", "stealth"])
            columns += " l l"
        else:
            # General item columns based on available properties
            if has_rarity:
                headers.append("rarity")
                columns += " l"
            if has_value:
                headers.append("value")
                columns += " l"
            if has_weight:
                headers.append("weight")
                columns += " l"

        return {"specification": columns, "headers": headers}

    def _format_type_enhanced(self, item_type: Any) -> str:
        """Format item type with enhanced handling.

        Args:
            item_type: Item type data

        Returns:
            Formatted type string
        """
        if not item_type:
            return "Item"

        if hasattr(item_type, "value"):
            # Enum type
            return str(item_type.value).replace("_", " ").title()
        elif isinstance(item_type, str):
            return item_type.replace("_", " ").title()
        else:
            return str(item_type)

    def _format_rarity_enhanced(self, rarity: Any, attunement: Any = None) -> str:
        """Format item rarity with attunement.

        Args:
            rarity: Rarity value
            attunement: Attunement requirement

        Returns:
            Formatted rarity string with attunement
        """
        if not rarity:
            return ""

        rarity_text = str(rarity).replace("_", " ").title() if rarity else ""

        if attunement:
            if isinstance(attunement, bool) and attunement:
                rarity_text += " (requires attunement)"
            elif isinstance(attunement, str):
                rarity_text += f" (requires attunement {attunement})"

        return rarity_text

    def _format_weight(self, weight: Any) -> str | None:
        """Format item weight.

        Args:
            weight: Weight value

        Returns:
            Formatted weight string or None
        """
        if not weight:
            return None

        if isinstance(weight, int | float):
            if weight == 1:
                return "1 lb."
            else:
                return f"{weight} lb."
        else:
            return str(weight)

    def _format_value(self, value: Any) -> str | None:
        """Format item value.

        Args:
            value: Value data

        Returns:
            Formatted value string or None
        """
        if not value:
            return None

        if isinstance(value, int | float):
            # Convert copper pieces to appropriate currency
            if value >= 1000:
                gp = value / 100
                return f"{int(gp)} gp" if gp == int(gp) else f"{gp:.1f} gp"
            elif value >= 100:
                sp = value / 10
                return f"{int(sp)} sp" if sp == int(sp) else f"{sp:.1f} sp"
            else:
                return f"{value} cp"
        elif isinstance(value, dict):
            # Handle complex value structures
            return str(value)
        else:
            return str(value)

    def _format_ac_enhanced(self, item: Item) -> str | None:
        """Format armor class for armor items.

        Args:
            item: Item to check

        Returns:
            Formatted AC string or None
        """
        if not item.is_armor():
            return None

        ac = getattr(item, "ac", None)
        if not ac:
            return None

        ac_from = getattr(item, "ac_from", None)
        if ac_from:
            return f"{ac} + Dex modifier ({', '.join(ac_from)})"
        else:
            return str(ac)

    def _format_damage_enhanced(self, item: Item) -> str | None:
        """Format damage for weapon items.

        Args:
            item: Item to check

        Returns:
            Formatted damage string or None
        """
        if not item.is_weapon():
            return None

        damage = getattr(item, "damage", None)
        damage_type = getattr(item, "damage_type", None)

        if damage and damage_type:
            return f"{damage} {damage_type}"
        elif damage:
            return str(damage)
        else:
            return None

    def _format_range_item(self, item: Item) -> str | None:
        """Format range for weapon items.

        Args:
            item: Item to check

        Returns:
            Formatted range string or None
        """
        range_data = getattr(item, "range", None)
        if not range_data:
            return None

        return str(range_data)

    def _format_properties_enhanced(self, properties: list[str] | None) -> str | None:
        """Format weapon/item properties.

        Args:
            properties: List of properties

        Returns:
            Formatted properties string or None
        """
        if not properties:
            return None

        # Expand property abbreviations
        property_expansions = {
            "F": "Finesse",
            "H": "Heavy",
            "L": "Light",
            "R": "Reach",
            "T": "Thrown",
            "V": "Versatile",
            "2H": "Two-handed",
            "A": "Ammunition",
            "LD": "Loading",
            "S": "Special",
        }

        expanded = []
        for prop in properties:
            expanded.append(property_expansions.get(prop, prop))

        return ", ".join(expanded)

    def _format_attunement(self, attunement: Any) -> str | None:
        """Format attunement requirement.

        Args:
            attunement: Attunement data

        Returns:
            Formatted attunement string or None
        """
        if not attunement:
            return None

        if isinstance(attunement, bool):
            return "Required" if attunement else None
        else:
            return str(attunement)

    def _format_charges(self, charges: Any) -> str | None:
        """Format item charges.

        Args:
            charges: Charges data

        Returns:
            Formatted charges string or None
        """
        if not charges:
            return None

        if isinstance(charges, int | str):
            return str(charges)
        elif isinstance(charges, dict):
            # Handle complex charge structures
            return str(charges)
        else:
            return str(charges)

    def _extract_magic_properties(self, item: Item) -> list[dict[str, str]] | None:
        """Extract magic properties from item.

        Args:
            item: Item to analyze

        Returns:
            List of magic properties or None
        """
        # This would need implementation based on actual data structure
        # For now, return None as placeholder
        return None

    def _build_weapon_statistics(self, item: Item) -> dict[str, str] | None:
        """Build weapon statistics table data.

        Args:
            item: Weapon item

        Returns:
            Weapon statistics dictionary or None
        """
        if not item.is_weapon():
            return None

        stats = {}

        damage = getattr(item, "damage", None)
        damage_type = getattr(item, "damage_type", None)
        if damage and damage_type:
            stats["damage"] = f"{damage} {damage_type}"
        elif damage:
            stats["damage"] = damage
        else:
            stats["damage"] = "—"

        stats["damage_type"] = damage_type or "—"
        stats["range"] = getattr(item, "range", "—")
        stats["properties"] = (
            self._format_properties_enhanced(getattr(item, "properties", None)) or "—"
        )

        mastery = getattr(item, "mastery", None)
        if mastery:
            stats["mastery"] = ", ".join(mastery)

        return stats if any(v != "—" for v in stats.values()) else None

    def _build_armor_statistics(self, item: Item) -> dict[str, str] | None:
        """Build armor statistics table data.

        Args:
            item: Armor item

        Returns:
            Armor statistics dictionary or None
        """
        if not item.is_armor():
            return None

        stats = {}
        stats["type"] = self._format_type_enhanced(item.type)
        stats["ac"] = self._format_ac_enhanced(item) or "—"

        strength_req = getattr(item, "strength", None)
        if strength_req:
            stats["strength_req"] = str(strength_req)

        stats["stealth_disadvantage"] = str(getattr(item, "stealth", False))

        return stats

    def _extract_variants(self, item: Item) -> list[dict[str, str]] | None:
        """Extract item variants.

        Args:
            item: Item to analyze

        Returns:
            List of variants or None
        """
        # This would need implementation based on actual data structure
        # For now, return None as placeholder
        return None

    def _extract_creation_rules(self, item: Item) -> str | None:
        """Extract creation rules for magic items.

        Args:
            item: Item to analyze

        Returns:
            Creation rules text or None
        """
        # This would need implementation based on actual data structure
        # For now, return None as placeholder
        return None

    def _format_source_reference(self, source: Any) -> str:
        """Format source reference.

        Args:
            source: Source object or data

        Returns:
            Formatted source reference
        """
        if not source:
            return ""

        if hasattr(source, "abbreviation"):
            # Pydantic Source model
            abbr = str(source.abbreviation)
            page = getattr(source, "page", None)
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        elif isinstance(source, dict):
            # Dictionary format
            abbr = str(source.get("abbreviation", ""))
            page = source.get("page")
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        else:
            return str(source)

    def _format_entries(self, entries: list[Any], context: RenderContext) -> str:
        """Format item description entries.

        Args:
            entries: List of description entries
            context: Rendering context

        Returns:
            Formatted description
        """
        if not entries:
            return ""

        formatted_entries = []
        for entry in entries:
            if isinstance(entry, str):
                formatted_entries.append(self.process_text_with_tags(entry, context))
            else:
                formatted_entries.append(str(entry))

        return "\n\n".join(formatted_entries)

    # Legacy compatibility methods for backward compatibility with tests
    def _format_rarity(self, rarity: str | None) -> str:
        """Legacy method for backward compatibility with tests.

        Args:
            rarity: Rarity string

        Returns:
            Formatted rarity with leading comma
        """
        if not rarity:
            return ""
        return f", {rarity}"

    def _format_properties(self, properties: list[str] | None) -> str | None:
        """Legacy method for backward compatibility with tests.

        Args:
            properties: List of property strings

        Returns:
            Comma-separated properties string or None if empty
        """
        if not properties:
            return None
        return ", ".join(properties)


class LaTeXClassRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for D&D class content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize class renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.CLASS}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render class content to LaTeX using DND template environments.

        Args:
            content: Class to render
            context: Rendering context

        Returns:
            LaTeX representation of class using DND template
        """
        if not isinstance(content, Class):
            raise ValueError(f"Expected Class, got {type(content)}")

        # Determine template to use
        template_name = "class_dnd" if self.use_dnd_template else "class"

        # Build comprehensive template variables for DND template
        variables = self._build_class_variables(content, context)

        return self.template_engine.render_template(template_name, variables)

    def _build_class_variables(
        self, class_obj: Class, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for class rendering.

        Args:
            class_obj: Class to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Basic info
        variables = {
            "name": self.escape_latex(class_obj.name),
            "use_subsection": getattr(context, "use_subsections", True),
            "description": self._extract_class_description(class_obj),
        }

        # Hit dice information
        if class_obj.hd:
            variables["hit_dice_info"] = self._build_hit_dice_info(
                class_obj.hd, class_obj.name
            )

        # Starting proficiencies
        if class_obj.starting_proficiencies:
            variables["proficiencies"] = self._build_proficiencies_info(
                class_obj.starting_proficiencies
            )

        # Starting equipment
        if class_obj.starting_equipment:
            variables["starting_equipment"] = self._build_equipment_info(
                class_obj.starting_equipment
            )

        # Class table
        if class_obj.class_features:
            variables["class_table"] = self._build_class_table(class_obj)

        # Spellcasting table (if applicable)
        if self._is_spellcaster(class_obj):
            variables["spellcasting_table"] = self._build_spellcasting_table(class_obj)
            variables["spellcasting_rules"] = self._build_spellcasting_rules(class_obj)

        # Class features
        variables["class_features"] = self._build_class_features(
            class_obj.class_features or [], context
        )

        # Subclasses
        if class_obj.subclasses:
            variables["subclasses"] = self._build_subclasses_info(
                class_obj.subclasses, context
            )
            variables["subclass_intro"] = self._get_subclass_intro(class_obj.name)

        # Multiclassing
        if class_obj.multiclassing:
            variables["multiclassing"] = self._build_multiclassing_info(
                class_obj.multiclassing
            )

        # Source reference
        variables["source_reference"] = self._format_source_reference(class_obj.source)

        return variables

    def _extract_class_description(self, class_obj: Class) -> str | None:
        """Extract class description from fluff or entries.

        Args:
            class_obj: Class object

        Returns:
            Class description text or None
        """
        # This would need implementation based on actual data structure
        # Classes might have description in fluff or entries fields
        return None

    def _build_hit_dice_info(
        self, hd: dict[str, int], class_name: str
    ) -> dict[str, str]:
        """Build hit dice information.

        Args:
            hd: Hit dice data
            class_name: Name of the class

        Returns:
            Hit dice information dictionary
        """
        number = hd.get("number", 1)
        faces = hd.get("faces", 8)

        dice_text = f"{number}d{faces}"
        first_level = str(faces)
        higher_levels = f"{number}d{faces} (or {(faces // 2) + 1})"

        return {
            "dice_text": dice_text,
            "first_level": first_level,
            "higher_levels": higher_levels,
        }

    def _build_proficiencies_info(self, prof_data: dict[str, Any]) -> dict[str, str]:
        """Build proficiencies information.

        Args:
            prof_data: Proficiencies data

        Returns:
            Formatted proficiencies dictionary
        """
        proficiencies = {}

        # Armor proficiencies
        armor = prof_data.get("armor", [])
        if armor:
            proficiencies["armor"] = ", ".join(armor)

        # Weapon proficiencies
        weapons = prof_data.get("weapons", [])
        if weapons:
            proficiencies["weapons"] = ", ".join(weapons)

        # Tool proficiencies
        tools = prof_data.get("tools", [])
        if tools:
            if isinstance(tools, list):
                proficiencies["tools"] = ", ".join(str(tool) for tool in tools)
            else:
                proficiencies["tools"] = str(tools)

        # Saving throws
        saves = prof_data.get("savingThrows", [])
        if saves:
            # Convert abbreviations to full names
            save_names = {
                "str": "Strength",
                "dex": "Dexterity",
                "con": "Constitution",
                "int": "Intelligence",
                "wis": "Wisdom",
                "cha": "Charisma",
            }
            formatted_saves = [
                save_names.get(save.lower(), save.title()) for save in saves
            ]
            proficiencies["saving_throws"] = ", ".join(formatted_saves)

        # Skills
        skills = prof_data.get("skills", [])
        if skills:
            if isinstance(skills, list):
                proficiencies["skills"] = ", ".join(skills)
            else:
                proficiencies["skills"] = str(skills)

        return proficiencies

    def _build_equipment_info(self, equipment_data: dict[str, Any]) -> list[list[str]]:
        """Build starting equipment information.

        Args:
            equipment_data: Equipment data

        Returns:
            List of equipment options
        """
        # This would need complex implementation based on actual equipment structure
        # For now, return simplified structure
        default_equipment = equipment_data.get("default", [])
        if default_equipment:
            return [[str(item) for item in default_equipment]]
        return []

    def _build_class_table(self, class_obj: Class) -> dict[str, Any]:
        """Build class progression table.

        Args:
            class_obj: Class object

        Returns:
            Class table data
        """
        # This would need complex implementation to parse class table data
        # For now, return basic structure
        return {
            "columns": "c c c c",
            "header_row": "\\textbf{Level} & \\textbf{Proficiency Bonus} & \\textbf{Features} & \\textbf{Other}",
            "rows": ["1st & +2 & Class Feature & —"],  # Placeholder
        }

    def _is_spellcaster(self, class_obj: Class) -> bool:
        """Check if class is a spellcaster.

        Args:
            class_obj: Class object

        Returns:
            True if class has spellcasting
        """
        return (
            class_obj.spellcasting_ability is not None
            or class_obj.caster_progression is not None
            or class_obj.cantrip_progression is not None
        )

    def _build_spellcasting_table(self, class_obj: Class) -> dict[str, Any]:
        """Build spellcasting progression table.

        Args:
            class_obj: Class object

        Returns:
            Spellcasting table data
        """
        # This would need complex implementation based on spell slot progression
        # For now, return basic structure
        return {
            "columns": "c c c c c c c c c c",
            "header_row": "\\textbf{Level} & \\textbf{1st} & \\textbf{2nd} & \\textbf{3rd} & \\textbf{4th} & \\textbf{5th} & \\textbf{6th} & \\textbf{7th} & \\textbf{8th} & \\textbf{9th}",
            "rows": ["1st & 2 & — & — & — & — & — & — & — & —"],  # Placeholder
        }

    def _build_spellcasting_rules(self, class_obj: Class) -> dict[str, str]:
        """Build spellcasting rules text.

        Args:
            class_obj: Class object

        Returns:
            Spellcasting rules dictionary
        """
        rules = {}

        if class_obj.spellcasting_ability:
            ability_names = {"int": "Intelligence", "wis": "Wisdom", "cha": "Charisma"}
            ability = ability_names.get(
                class_obj.spellcasting_ability.lower(), class_obj.spellcasting_ability
            )
            rules["spellcasting_ability"] = (
                f"{ability} is your spellcasting ability for your {class_obj.name.lower()} spells."
            )

        # Add other spellcasting rules as needed
        return rules

    def _build_class_features(
        self, features_data: list[Any], context: RenderContext
    ) -> list[dict[str, Any]]:
        """Build class features list.

        Args:
            features_data: Features data
            context: Rendering context

        Returns:
            List of formatted features
        """
        if not features_data:
            return []

        # This would need complex implementation to parse feature structures
        # For now, return simplified structure
        formatted_features = []
        for feature in features_data:
            if isinstance(feature, dict):
                formatted_features.append(
                    {
                        "level_header": feature.get("level", ""),
                        "feature_name": feature.get("name", ""),
                        "description": str(feature.get("entries", "")),
                        "choices": None,
                        "table": None,
                    }
                )

        return formatted_features

    def _build_subclasses_info(
        self, subclasses: list[Any], context: RenderContext
    ) -> list[dict[str, Any]]:
        """Build subclasses information.

        Args:
            subclasses: List of subclasses
            context: Rendering context

        Returns:
            List of formatted subclasses
        """
        formatted_subclasses: list[dict[str, Any]] = []
        for subclass in subclasses:
            if hasattr(subclass, "name"):
                formatted_subclasses.append(
                    {
                        "name": self.escape_latex(subclass.name),
                        "description": None,  # Would need to extract from subclass data
                        "features": [],  # Would need to parse subclass features
                    }
                )

        return formatted_subclasses

    def _get_subclass_intro(self, class_name: str) -> str:
        """Get introduction text for subclasses.

        Args:
            class_name: Name of the class

        Returns:
            Subclass introduction text
        """
        return f"At a certain level, you choose an archetype that shapes the nature of your {class_name.lower()} abilities."

    def _build_multiclassing_info(
        self, multiclassing_data: dict[str, Any]
    ) -> dict[str, str]:
        """Build multiclassing information.

        Args:
            multiclassing_data: Multiclassing data

        Returns:
            Multiclassing information dictionary
        """
        mc_info = {}

        # Requirements
        requirements = multiclassing_data.get("requirements", {})
        if requirements:
            req_text = []
            for ability, score in requirements.items():
                ability_names = {
                    "str": "Strength",
                    "dex": "Dexterity",
                    "con": "Constitution",
                    "int": "Intelligence",
                    "wis": "Wisdom",
                    "cha": "Charisma",
                }
                ability_name = ability_names.get(ability.lower(), ability.title())
                req_text.append(f"{ability_name} {score}")
            mc_info["requirements"] = (
                "To qualify for multiclassing into this class, you must have "
                + " and ".join(req_text)
                + "."
            )

        # Proficiencies gained
        prof_gained = multiclassing_data.get("proficienciesGained", {})
        if prof_gained:
            prof_text = []
            for prof_type, profs in prof_gained.items():
                if isinstance(profs, list):
                    prof_text.append(f"{prof_type.title()}: {', '.join(profs)}")
                else:
                    prof_text.append(f"{prof_type.title()}: {profs}")
            mc_info["proficiencies"] = (
                "When you multiclass into this class, you gain the following proficiencies: "
                + "; ".join(prof_text)
                + "."
            )

        return mc_info

    def _format_source_reference(self, source: Any) -> str:
        """Format source reference.

        Args:
            source: Source object or data

        Returns:
            Formatted source reference
        """
        if not source:
            return ""

        if hasattr(source, "abbreviation"):
            # Pydantic Source model
            abbr = str(source.abbreviation)
            page = getattr(source, "page", None)
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        elif isinstance(source, dict):
            # Dictionary format
            abbr = str(source.get("abbreviation", ""))
            page = source.get("page")
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        else:
            return str(source)

    def _process_class_table_data(self, table_data: dict[str, Any]) -> dict[str, Any]:
        """Process class table data for rendering.

        Args:
            table_data: Table data with columns, column_labels, and rows

        Returns:
            Processed table data dictionary
        """
        # Extract headers from column_labels if available, otherwise use columns
        headers = table_data.get("column_labels", table_data.get("columns", []))

        # Generate LaTeX column specification
        # Start with level column (left-aligned), proficiency (center), then features (expandable)
        columns = "l c X"

        # Add remaining columns as center-aligned
        remaining_cols = len(headers) - 3
        if remaining_cols > 0:
            columns += " c" * remaining_cols

        return {
            "headers": headers,
            "rows": table_data.get("rows", []),
            "columns": columns,
        }

    def _format_class_features(
        self, features_data: list[Any], context: RenderContext
    ) -> list[dict[str, str]]:
        """Format class features for rendering.

        Args:
            features_data: List of feature data
            context: Rendering context

        Returns:
            List of formatted feature dictionaries
        """
        if not features_data:
            return []

        formatted_features = []
        for feature in features_data:
            if isinstance(feature, dict):
                name = feature.get("name", "")
                entries = feature.get("entries", [])

                # Process entries to create description
                description_parts = []
                for entry in entries:
                    if isinstance(entry, str):
                        description_parts.append(
                            self.process_text_with_tags(entry, context)
                        )
                    else:
                        description_parts.append(str(entry))

                formatted_features.append(
                    {
                        "name": self.escape_latex(name),
                        "description": " ".join(description_parts),
                    }
                )

        return formatted_features


class LaTeXRaceRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for D&D race content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize race renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.RACE}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render race content to LaTeX using DND template environments.

        Args:
            content: Race to render
            context: Rendering context

        Returns:
            LaTeX representation of race using DND template
        """
        if not isinstance(content, Race):
            raise ValueError(f"Expected Race, got {type(content)}")

        # Determine template to use
        template_name = "race_dnd" if self.use_dnd_template else "race"

        # Build comprehensive template variables for DND template
        variables = self._build_race_variables(content, context)

        return self.template_engine.render_template(template_name, variables)

    def _build_race_variables(
        self, race: Race, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for race rendering.

        Args:
            race: Race to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Basic info
        variables = {
            "name": self.escape_latex(race.name),
            "use_subsection": getattr(context, "use_subsections", True),
            "description": self._format_entries(getattr(race, "entries", []), context),
        }

        # Racial traits flag
        variables["racial_traits"] = True

        # Ability score increases
        if race.ability:
            variables["ability_score_info"] = self._format_ability_adjustments(
                race.ability
            )

        # Age information (if available in entries)
        variables["age_info"] = self._extract_age_info(race)

        # Size information
        if race.size:
            variables["size_info"] = self._format_size_info(race.size)

        # Speed information
        if race.speed:
            variables["speed_info"] = self._format_speed_info(race.speed)

        # Darkvision
        if race.darkvision:
            variables["darkvision_info"] = self._format_darkvision_info(race.darkvision)

        # Extract traits from entries
        variables["racial_traits"] = self._extract_racial_traits(race, context)

        # Proficiencies
        variables["proficiencies_info"] = self._build_proficiencies_info(race)

        # Resistances and immunities
        variables["resistances_info"] = self._build_resistances_info(race)

        # Racial spells
        if race.additionalSpells:
            variables["spells_info"] = self._format_racial_spells(race.additionalSpells)

        # Languages
        if race.language_proficiencies:
            # Convert language proficiencies to strings if they're dictionaries
            lang_list = []
            for lang in race.language_proficiencies:
                if isinstance(lang, dict):
                    lang_list.append(lang.get("name", str(lang)))
                else:
                    lang_list.append(str(lang))
            variables["languages_info"] = self._format_language_proficiencies(lang_list)

        # Subraces (placeholder - would need subrace data structure)
        variables["subraces"] = None
        variables["subrace_intro"] = None

        # Variant traits (placeholder)
        variables["variant_traits"] = None
        variables["variant_intro"] = None

        # Racial feat (placeholder)
        variables["racial_feat"] = None

        # Source reference
        variables["source_reference"] = self._format_source_reference(race.source)

        return variables

    def _format_ability_adjustments(self, abilities: list[Any]) -> str:
        """Format ability score adjustments.

        Args:
            abilities: List of ability adjustments

        Returns:
            Formatted ability adjustments string
        """
        if not abilities:
            return ""

        adjustments = []
        for ability in abilities:
            if hasattr(ability, "ability_name") and hasattr(ability, "value"):
                # Pydantic AbilityAdjustment model
                ability_names = {
                    "str": "Strength",
                    "dex": "Dexterity",
                    "con": "Constitution",
                    "int": "Intelligence",
                    "wis": "Wisdom",
                    "cha": "Charisma",
                }
                ability_name = ability_names.get(
                    ability.ability_name.lower(), ability.ability_name.title()
                )
                adjustments.append(
                    f"Your {ability_name} score increases by {ability.value}"
                )
            elif isinstance(ability, dict):
                # Dictionary format
                for abil, value in ability.items():
                    if abil.lower() in ["str", "dex", "con", "int", "wis", "cha"]:
                        ability_names = {
                            "str": "Strength",
                            "dex": "Dexterity",
                            "con": "Constitution",
                            "int": "Intelligence",
                            "wis": "Wisdom",
                            "cha": "Charisma",
                        }
                        ability_name = ability_names.get(abil.lower(), abil.title())
                        adjustments.append(
                            f"Your {ability_name} score increases by {value}"
                        )

        return ". ".join(adjustments) + "." if adjustments else ""

    def _extract_age_info(self, race: Race) -> str | None:
        """Extract age information from race entries.

        Args:
            race: Race object

        Returns:
            Age information string or None
        """
        # This would need implementation to parse age info from entries
        # For now, return None as placeholder
        return None

    def _format_size_info(self, size: list[str]) -> str:
        """Format size information.

        Args:
            size: List of size codes

        Returns:
            Formatted size string
        """
        if not size:
            return "Medium"

        size_map = {
            "T": "Tiny",
            "S": "Small",
            "M": "Medium",
            "L": "Large",
            "H": "Huge",
            "G": "Gargantuan",
        }

        size_names = [size_map.get(s, s) for s in size]
        return f"Your size is {' or '.join(size_names)}."

    def _format_speed_info(self, speed: Any) -> str:
        """Format speed information.

        Args:
            speed: Speed data

        Returns:
            Formatted speed string
        """
        if not speed:
            return "Your base walking speed is 30 feet."

        if isinstance(speed, dict):
            speed_parts = []
            for speed_type, value in speed.items():
                if speed_type == "walk":
                    speed_parts.append(f"Your base walking speed is {value} feet")
                else:
                    speed_parts.append(f"you have a {speed_type} speed of {value} feet")

            return ". ".join(speed_parts) + "."
        else:
            return f"Your base walking speed is {speed} feet."

    def _format_darkvision_info(self, darkvision: Any) -> str:
        """Format darkvision information.

        Args:
            darkvision: Darkvision range

        Returns:
            Formatted darkvision string
        """
        if isinstance(darkvision, int | str):
            range_value = str(darkvision)
            return (
                f"You have superior vision in dark and dim conditions. You can see in dim light within "
                f"{range_value} feet of you as if it were bright light, and in darkness as if it were dim light. "
                f"You can't discern color in darkness, only shades of gray."
            )
        else:
            return str(darkvision)

    def _extract_racial_traits(
        self, race: Race, context: RenderContext
    ) -> list[dict[str, str]]:
        """Extract racial traits from entries.

        Args:
            race: Race object
            context: Rendering context

        Returns:
            List of racial traits
        """
        # This would need complex implementation to parse traits from entries
        # For now, return empty list as placeholder
        return []

    def _build_proficiencies_info(self, race: Race) -> list[dict[str, str]]:
        """Build proficiencies information.

        Args:
            race: Race object

        Returns:
            List of proficiency descriptions
        """
        proficiencies = []

        # Skill proficiencies
        if race.skill_proficiencies:
            skill_names = [
                skill.get("name", str(skill)) if isinstance(skill, dict) else str(skill)
                for skill in race.skill_proficiencies
            ]
            proficiencies.append(
                {
                    "name": "Skills",
                    "description": f"You have proficiency in the {', '.join(skill_names)} skill(s).",
                }
            )

        # Weapon proficiencies
        if race.weapon_proficiencies:
            weapon_names = [
                weapon.get("name", str(weapon))
                if isinstance(weapon, dict)
                else str(weapon)
                for weapon in race.weapon_proficiencies
            ]
            proficiencies.append(
                {
                    "name": "Weapons",
                    "description": f"You have proficiency with {', '.join(weapon_names)}.",
                }
            )

        # Armor proficiencies
        if race.armor_proficiencies:
            armor_names = [
                armor.get("name", str(armor)) if isinstance(armor, dict) else str(armor)
                for armor in race.armor_proficiencies
            ]
            proficiencies.append(
                {
                    "name": "Armor",
                    "description": f"You have proficiency with {', '.join(armor_names)}.",
                }
            )

        # Tool proficiencies
        if race.tool_proficiencies:
            tool_names = [
                tool.get("name", str(tool)) if isinstance(tool, dict) else str(tool)
                for tool in race.tool_proficiencies
            ]
            proficiencies.append(
                {
                    "name": "Tools",
                    "description": f"You have proficiency with {', '.join(tool_names)}.",
                }
            )

        return proficiencies

    def _build_resistances_info(self, race: Race) -> list[dict[str, str]]:
        """Build resistances and immunities information.

        Args:
            race: Race object

        Returns:
            List of resistance descriptions
        """
        resistances = []

        # Damage resistances
        if race.resistances:
            resistances.append(
                {
                    "name": "Damage Resistance",
                    "description": f"You have resistance to {', '.join(race.resistances)} damage.",
                }
            )

        # Condition immunities
        if race.condition_immunities:
            resistances.append(
                {
                    "name": "Condition Immunity",
                    "description": f"You are immune to the {', '.join(race.condition_immunities)} condition(s).",
                }
            )

        return resistances

    def _format_racial_spells(self, spells: list[Any]) -> dict[str, str]:
        """Format racial spells information.

        Args:
            spells: List of additional spells

        Returns:
            Spells information dictionary
        """
        # This would need implementation based on AdditionalSpell model
        # For now, return basic info
        return {
            "name": "Spellcasting",
            "description": "You know certain spells based on your heritage.",
        }

    def _format_language_proficiencies(self, languages: list[str]) -> str:
        """Format language proficiencies.

        Args:
            languages: List of languages

        Returns:
            Formatted languages string
        """
        if not languages:
            return ""

        return f"You can speak, read, and write {', '.join(languages)}."

    def _format_entries(self, entries: list[Any], context: RenderContext) -> str:
        """Format race description entries.

        Args:
            entries: List of description entries
            context: Rendering context

        Returns:
            Formatted description
        """
        if not entries:
            return ""

        formatted_entries = []
        for entry in entries:
            if isinstance(entry, str):
                formatted_entries.append(self.process_text_with_tags(entry, context))
            else:
                formatted_entries.append(str(entry))

        return "\n\n".join(formatted_entries)

    def _format_source_reference(self, source: Any) -> str:
        """Format source reference.

        Args:
            source: Source object or data

        Returns:
            Formatted source reference
        """
        if not source:
            return ""

        if hasattr(source, "abbreviation"):
            # Pydantic Source model
            abbr = str(source.abbreviation)
            page = getattr(source, "page", None)
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        elif isinstance(source, dict):
            # Dictionary format
            abbr = str(source.get("abbreviation", ""))
            page = source.get("page")
            if page:
                return f"{abbr}, p. {page}"
            return abbr
        else:
            return str(source)

    def _format_ability_score_increases(self, abilities: list[Any]) -> str:
        """Format ability score increases for tests.

        Args:
            abilities: List of ability adjustments

        Returns:
            Formatted ability increases string
        """
        if not abilities:
            return ""

        adjustments = []
        for ability in abilities:
            if hasattr(ability, "ability_name") and hasattr(ability, "value"):
                # Pydantic AbilityAdjustment model
                ability_names = {
                    "str": "Strength",
                    "dex": "Dexterity",
                    "con": "Constitution",
                    "int": "Intelligence",
                    "wis": "Wisdom",
                    "cha": "Charisma",
                }
                ability_name = ability_names.get(
                    ability.ability_name.lower(), ability.ability_name.title()
                )
                adjustments.append(f"{ability_name} +{ability.value}")
            elif isinstance(ability, dict):
                # Dictionary format
                for abil, value in ability.items():
                    if abil.lower() in ["str", "dex", "con", "int", "wis", "cha"]:
                        ability_names = {
                            "str": "Strength",
                            "dex": "Dexterity",
                            "con": "Constitution",
                            "int": "Intelligence",
                            "wis": "Wisdom",
                            "cha": "Charisma",
                        }
                        ability_name = ability_names.get(abil.lower(), abil.title())
                        adjustments.append(f"{ability_name} +{value}")

        return ", ".join(adjustments)

    def _format_racial_traits(
        self, trait_tags: list[str], entries: list[str], context: RenderContext
    ) -> list[dict[str, str]]:
        """Format racial traits from tags and entries.

        Args:
            trait_tags: List of trait names
            entries: List of trait descriptions
            context: Rendering context

        Returns:
            List of formatted trait dictionaries
        """
        traits = []
        for i, (tag, entry) in enumerate(zip(trait_tags, entries, strict=False)):
            traits.append(
                {
                    "name": self.escape_latex(tag),
                    "description": self.process_text_with_tags(entry, context),
                }
            )
        return traits

    def _format_subraces(
        self, subraces: list[Any], context: RenderContext
    ) -> list[dict[str, str]]:
        """Format subraces information.

        Args:
            subraces: List of subrace data
            context: Rendering context

        Returns:
            List of formatted subrace dictionaries
        """
        formatted_subraces = []
        for subrace in subraces:
            if isinstance(subrace, dict):
                name = subrace.get("name", "")
                abilities = subrace.get("ability", [])
                entries = subrace.get("entries", [])

                # Format ability increases
                ability_increases = self._format_ability_score_increases(abilities)

                # Format entries
                description_parts = []
                for entry in entries:
                    if isinstance(entry, str):
                        description_parts.append(
                            self.process_text_with_tags(entry, context)
                        )
                    else:
                        description_parts.append(str(entry))

                formatted_subraces.append(
                    {
                        "name": self.escape_latex(name),
                        "ability_increases": ability_increases,
                        "description": " ".join(description_parts),
                    }
                )

        return formatted_subraces


class LaTeXAdventureRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for adventure content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize adventure renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.ADVENTURE}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render adventure content to LaTeX using DND template environments.

        Args:
            content: Adventure content to render
            context: Rendering context

        Returns:
            LaTeX markup string
        """
        if not isinstance(content, Adventure):
            raise ValueError(f"Expected Adventure, got {type(content)}")

        template_name = (
            "adventure_dnd.tex.j2" if self.use_dnd_template else "adventure.tex.j2"
        )

        template_vars = self._build_adventure_variables(content, context)

        return self.template_engine.render_template(template_name, template_vars)

    def _build_adventure_variables(
        self, adventure: Adventure, context: RenderContext
    ) -> dict[str, Any]:
        """Build template variables for adventure rendering.

        Args:
            adventure: Adventure to render
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Extract adventure content from entries
        adventure_hook = None
        summary = None
        background = None
        encounters: list[dict[str, Any]] = []
        npcs: list[dict[str, Any]] = []
        locations: list[dict[str, Any]] = []
        random_encounters: list[dict[str, Any]] = []
        conclusion = None

        # Process entries to extract structured content
        if hasattr(adventure, "entries") and adventure.entries:
            content_text = self._extract_text_from_entries(adventure.entries, context)
            summary = content_text

        return {
            "name": self.escape_latex(adventure.name),
            "use_section": True,
            "adventure_hook": adventure_hook,
            "summary": summary,
            "background": background,
            "encounters": encounters,
            "npcs": npcs,
            "locations": locations,
            "random_encounters": random_encounters,
            "conclusion": conclusion,
            "source_reference": self.escape_latex(getattr(adventure, "source", "")),
        }

    def _extract_text_from_entries(
        self, entries: list[Any], context: RenderContext
    ) -> str:
        """Extract and process text from entries list.

        Args:
            entries: List of entry objects
            context: Rendering context

        Returns:
            Processed text content
        """
        text_parts = []

        for entry in entries:
            if isinstance(entry, str):
                text_parts.append(self.process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                if "entries" in entry:
                    # Nested entries
                    nested_text = self._extract_text_from_entries(
                        entry["entries"], context
                    )
                    text_parts.append(nested_text)
                elif "name" in entry and "text" in entry:
                    # Named text block
                    name = self.escape_latex(entry["name"])
                    text = self.process_text_with_tags(entry["text"], context)
                    text_parts.append(f"\\textbf{{{name}}} {text}")
                elif "text" in entry:
                    text_parts.append(
                        self.process_text_with_tags(entry["text"], context)
                    )

        return "\n\n".join(text_parts)


class LaTeXBackgroundRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for background content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize background renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.BACKGROUND}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render background content to LaTeX using DND template environments.

        Args:
            content: Background content to render
            context: Rendering context

        Returns:
            LaTeX markup string
        """
        if not isinstance(content, Background):
            raise ValueError(f"Expected Background, got {type(content)}")

        template_name = (
            "background_dnd.tex.j2" if self.use_dnd_template else "background.tex.j2"
        )

        template_vars = self._build_background_variables(content, context)

        return self.template_engine.render_template(template_name, template_vars)

    def _build_background_variables(
        self, background: Background, context: RenderContext
    ) -> dict[str, Any]:
        """Build template variables for background rendering.

        Args:
            background: Background to render
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Process description from entries
        description = ""
        if hasattr(background, "entries") and background.entries:
            description = self._extract_text_from_entries(background.entries, context)

        # Format proficiencies
        skill_proficiencies = self._format_proficiencies(background.skill_proficiencies)
        tool_proficiencies = self._format_proficiencies(background.tool_proficiencies)
        language_proficiencies = self._format_proficiencies(
            background.language_proficiencies
        )

        return {
            "name": self.escape_latex(background.name),
            "use_subsection": False,
            "description": description,
            "skill_proficiencies": skill_proficiencies,
            "tool_proficiencies": tool_proficiencies,
            "language_proficiencies": language_proficiencies,
            "equipment": None,  # Could be extracted from entries if needed
            "feature": None,  # Could be extracted from entries if needed
            "personality_traits": [],  # Could be extracted from entries if needed
            "ideals": [],  # Could be extracted from entries if needed
            "bonds": [],  # Could be extracted from entries if needed
            "flaws": [],  # Could be extracted from entries if needed
            "variant": None,  # Could be extracted from entries if needed
            "source_reference": self.escape_latex(getattr(background, "source", "")),
        }

    def _format_proficiencies(self, proficiencies: list[Any] | None) -> str:
        """Format proficiency list for display.

        Args:
            proficiencies: List of proficiency objects

        Returns:
            Formatted proficiency string
        """
        if not proficiencies:
            return ""

        formatted_parts = []
        for prof in proficiencies:
            if isinstance(prof, str):
                formatted_parts.append(self.escape_latex(prof))
            elif isinstance(prof, dict):
                # Handle choice structures
                if "choose" in prof:
                    choose_data = prof["choose"]
                    if "from" in choose_data:
                        options = choose_data["from"]
                        count = choose_data.get("count", 1)
                        if isinstance(options, list):
                            option_str = ", ".join(
                                self.escape_latex(str(opt)) for opt in options[:3]
                            )
                            if len(options) > 3:
                                option_str += ", ..."
                            formatted_parts.append(f"Choose {count} from: {option_str}")
                        else:
                            formatted_parts.append(f"Choose {count}")
                else:
                    # Simple dict format
                    text = prof.get("text", prof.get("name", str(prof)))
                    if text:
                        formatted_parts.append(self.escape_latex(str(text)))

        return ", ".join(formatted_parts)

    def _extract_text_from_entries(
        self, entries: list[Any], context: RenderContext
    ) -> str:
        """Extract and process text from entries list.

        Args:
            entries: List of entry objects
            context: Rendering context

        Returns:
            Processed text content
        """
        text_parts = []

        for entry in entries:
            if isinstance(entry, str):
                text_parts.append(self.process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                if "entries" in entry:
                    # Nested entries
                    nested_text = self._extract_text_from_entries(
                        entry["entries"], context
                    )
                    text_parts.append(nested_text)
                elif "name" in entry and "text" in entry:
                    # Named text block
                    name = self.escape_latex(entry["name"])
                    text = self.process_text_with_tags(entry["text"], context)
                    text_parts.append(f"\\textbf{{{name}}} {text}")
                elif "text" in entry:
                    text_parts.append(
                        self.process_text_with_tags(entry["text"], context)
                    )

        return "\n\n".join(text_parts)


class LaTeXFeatRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for feat content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize feat renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.FEAT}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render feat content to LaTeX using DND template environments.

        Args:
            content: Feat content to render
            context: Rendering context

        Returns:
            LaTeX markup string
        """
        if not isinstance(content, Feat):
            raise ValueError(f"Expected Feat, got {type(content)}")

        template_name = "feat_dnd.tex.j2" if self.use_dnd_template else "feat.tex.j2"

        template_vars = self._build_feat_variables(content, context)

        return self.template_engine.render_template(template_name, template_vars)

    def _build_feat_variables(
        self, feat: Feat, context: RenderContext
    ) -> dict[str, Any]:
        """Build template variables for feat rendering.

        Args:
            feat: Feat to render
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        # Process description from entries
        description = ""
        if hasattr(feat, "entries") and feat.entries:
            description = self._extract_text_from_entries(feat.entries, context)

        # Format prerequisites
        prerequisite_text = self._format_prerequisites(feat.prerequisite)

        # Format ability score improvements
        ability_score_improvement = self._format_ability_improvements(feat.ability)

        return {
            "name": self.escape_latex(feat.name),
            "use_subsection": False,
            "prerequisite": prerequisite_text,
            "description": description,
            "ability_score_improvement": ability_score_improvement,
            "source_reference": self.escape_latex(getattr(feat, "source", "")),
        }

    def _format_prerequisites(self, prerequisites: list[Any] | None) -> str:
        """Format prerequisite list for display.

        Args:
            prerequisites: List of prerequisite objects

        Returns:
            Formatted prerequisite string
        """
        if not prerequisites:
            return ""

        formatted_parts = []
        for prereq in prerequisites:
            if isinstance(prereq, str):
                formatted_parts.append(self.escape_latex(prereq))
            elif hasattr(prereq, "other") and prereq.other:
                formatted_parts.append(self.escape_latex(prereq.other))
            elif isinstance(prereq, dict):
                if "other" in prereq:
                    formatted_parts.append(self.escape_latex(prereq["other"]))
                else:
                    # Handle ability score prerequisites
                    prereq_parts = []
                    for key, value in prereq.items():
                        if key in ["str", "dex", "con", "int", "wis", "cha"]:
                            ability_name = {
                                "str": "Strength",
                                "dex": "Dexterity",
                                "con": "Constitution",
                                "int": "Intelligence",
                                "wis": "Wisdom",
                                "cha": "Charisma",
                            }[key]
                            prereq_parts.append(f"{ability_name} {value}")
                    if prereq_parts:
                        formatted_parts.append(", ".join(prereq_parts))

        return ", ".join(formatted_parts) if formatted_parts else ""

    def _format_ability_improvements(
        self, abilities: list[dict[str, Any]] | None
    ) -> str:
        """Format ability score improvements for display.

        Args:
            abilities: List of ability improvement objects

        Returns:
            Formatted ability improvement string
        """
        if not abilities:
            return ""

        improvements = []
        for ability in abilities:
            if isinstance(ability, dict):
                for key, value in ability.items():
                    if key in ["str", "dex", "con", "int", "wis", "cha"]:
                        ability_name = {
                            "str": "Strength",
                            "dex": "Dexterity",
                            "con": "Constitution",
                            "int": "Intelligence",
                            "wis": "Wisdom",
                            "cha": "Charisma",
                        }[key]
                        if isinstance(value, int):
                            improvements.append(f"{ability_name} +{value}")
                        elif isinstance(value, dict) and "choose" in value:
                            improvements.append(f"{ability_name} (choice)")

        return ", ".join(improvements) if improvements else ""

    def _extract_text_from_entries(
        self, entries: list[Any], context: RenderContext
    ) -> str:
        """Extract and process text from entries list.

        Args:
            entries: List of entry objects
            context: Rendering context

        Returns:
            Processed text content
        """
        text_parts = []

        for entry in entries:
            if isinstance(entry, str):
                text_parts.append(self.process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                if "entries" in entry:
                    # Nested entries
                    nested_text = self._extract_text_from_entries(
                        entry["entries"], context
                    )
                    text_parts.append(nested_text)
                elif "name" in entry and "text" in entry:
                    # Named text block
                    name = self.escape_latex(entry["name"])
                    text = self.process_text_with_tags(entry["text"], context)
                    text_parts.append(f"\\textbf{{{name}}} {text}")
                elif "text" in entry:
                    text_parts.append(
                        self.process_text_with_tags(entry["text"], context)
                    )

        return "\n\n".join(text_parts)


class LaTeXBookRenderer(LaTeXContentRenderer):
    """Enhanced LaTeX renderer for book content using DND template environments."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize book renderer.

        Args:
            config: Configuration options including use_dnd_template flag
        """
        super().__init__(config)
        self.use_dnd_template = config.get("use_dnd_template", True) if config else True

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.BOOK}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render book content to LaTeX using DND template environments.

        Args:
            content: Book content to render
            context: Rendering context

        Returns:
            LaTeX markup string
        """
        if not isinstance(content, Book):
            raise ValueError(f"Expected Book, got {type(content)}")

        # Build template variables for book rendering
        variables = self._build_book_variables(content, context)

        # Use content-only template for embedding (prevents document structure duplication)
        template_name = "book_content" if self.use_dnd_template else "book_content"
        return self.template_engine.render_template(template_name, variables)

    def _build_book_variables(
        self, book: Book, context: RenderContext
    ) -> dict[str, Any]:
        """Build comprehensive template variables for book rendering.

        Args:
            book: Book to build variables for
            context: Rendering context

        Returns:
            Dictionary of template variables
        """
        variables = {
            "book": book,
            "name": book.name,
            "source": book.source.name if book.source else "",
            "source_abbr": book.source.abbreviation if book.source else "",
            "authors": book.get_authors_text(),
            "chapters": [],
            "metadata": book.metadata,
        }

        # Process chapters
        for chapter in book.contents:
            chapter_vars = {
                "name": chapter.name,
                "number": chapter.get_chapter_number(),
                "headers": chapter.get_formatted_headers(),
                "entries": self._process_entries(chapter.entries, context),
            }
            variables["chapters"].append(chapter_vars)

        return variables

    def _process_entries(self, entries: list[Any], context: RenderContext) -> list[str]:
        """Process chapter entries into LaTeX content.

        Args:
            entries: List of entry objects/strings
            context: Rendering context

        Returns:
            List of processed LaTeX strings
        """
        processed = []

        for entry in entries:
            if isinstance(entry, str):
                # Plain text entry
                processed.append(self.process_text_with_tags(entry, context))
            elif isinstance(entry, dict):
                processed.append(self._process_entry_dict(entry, context))
            else:
                # Fallback for other types
                processed.append(str(entry))

        return processed

    def _process_entry_dict(self, entry: dict[str, Any], context: RenderContext) -> str:
        """Process a dictionary entry into LaTeX.

        Args:
            entry: Entry dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entry_type = entry.get("type", "")

        if entry_type == "section":
            return self._process_section(entry, context)
        elif entry_type == "entries":
            return self._process_entries_block(entry, context)
        elif entry_type == "insetReadaloud":
            return self._process_inset_readaloud(entry, context)
        elif entry_type == "inset":
            return self._process_inset(entry, context)
        elif entry_type == "image":
            return self._process_image(entry, context)
        else:
            # Generic entry with name and entries
            name = entry.get("name", "")
            entries = entry.get("entries", [])

            result = []
            if name:
                result.append(f"\\subsection{{{self.escape_latex(name)}}}")

            if entries:
                processed_entries = self._process_entries(entries, context)
                result.extend(processed_entries)

            return "\n\n".join(result)

    def _process_section(self, section: dict[str, Any], context: RenderContext) -> str:
        """Process a section entry.

        Args:
            section: Section dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = section.get("name", "")
        entries = section.get("entries", [])

        result = []
        if name:
            result.append(f"\\section{{{self.escape_latex(name)}}}")

        if entries:
            processed_entries = self._process_entries(entries, context)
            result.extend(processed_entries)

        return "\n\n".join(result)

    def _process_entries_block(
        self, block: dict[str, Any], context: RenderContext
    ) -> str:
        """Process an entries block.

        Args:
            block: Entries block dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = block.get("name", "")
        entries = block.get("entries", [])

        result = []
        if name:
            result.append(f"\\subsection{{{self.escape_latex(name)}}}")

        if entries:
            processed_entries = self._process_entries(entries, context)
            result.extend(processed_entries)

        return "\n\n".join(result)

    def _process_inset_readaloud(
        self, inset: dict[str, Any], context: RenderContext
    ) -> str:
        """Process a read-aloud inset.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        entries = inset.get("entries", [])
        processed_entries = self._process_entries(entries, context)
        content = "\n".join(processed_entries)

        if self.use_dnd_template:
            return f"\\begin{{readaloud}}\n{content}\n\\end{{readaloud}}"
        else:
            return f"\\begin{{quotation}}\\em\n{content}\n\\end{{quotation}}"

    def _process_inset(self, inset: dict[str, Any], context: RenderContext) -> str:
        """Process a generic inset.

        Args:
            inset: Inset dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        name = inset.get("name", "")
        entries = inset.get("entries", [])
        processed_entries = self._process_entries(entries, context)
        content = "\n".join(processed_entries)

        if self.use_dnd_template:
            if name:
                return f"\\begin{{dndbox}}[{self.escape_latex(name)}]\n{content}\n\\end{{dndbox}}"
            else:
                return f"\\begin{{dndbox}}\n{content}\n\\end{{dndbox}}"
        else:
            result = []
            if name:
                result.append(f"\\textbf{{{self.escape_latex(name)}}}")
            result.append(f"\\begin{{quotation}}\n{content}\n\\end{{quotation}}")
            return "\n\n".join(result)

    def _process_image(self, image: dict[str, Any], context: RenderContext) -> str:
        """Process an image entry.

        Args:
            image: Image dictionary
            context: Rendering context

        Returns:
            LaTeX string
        """
        # For now, just add a placeholder comment
        href = image.get("href", {})
        path = href.get("path", "")
        return f"% Image: {path}"


class LaTeXContentRendererRegistry:
    """Registry for LaTeX content renderers."""

    def __init__(self) -> None:
        """Initialize renderer registry."""
        self._renderers: dict[ContentType, ContentRenderer] = {}
        self._register_default_renderers()

    def _register_default_renderers(self) -> None:
        """Register default content renderers."""
        self.register_renderer(ContentType.SPELL, LaTeXSpellRenderer())
        self.register_renderer(ContentType.CREATURE, LaTeXCreatureRenderer())
        self.register_renderer(ContentType.ITEM, LaTeXItemRenderer())
        self.register_renderer(ContentType.CLASS, LaTeXClassRenderer())
        self.register_renderer(ContentType.RACE, LaTeXRaceRenderer())
        self.register_renderer(ContentType.ADVENTURE, LaTeXAdventureRenderer())
        self.register_renderer(ContentType.BACKGROUND, LaTeXBackgroundRenderer())
        self.register_renderer(ContentType.FEAT, LaTeXFeatRenderer())
        self.register_renderer(ContentType.BOOK, LaTeXBookRenderer())

    def register_renderer(
        self, content_type: ContentType, renderer: ContentRenderer
    ) -> None:
        """Register a renderer for a content type.

        Args:
            content_type: Content type to handle
            renderer: Renderer instance
        """
        self._renderers[content_type] = renderer

    def get_renderer(self, content_type: ContentType) -> ContentRenderer | None:
        """Get renderer for content type.

        Args:
            content_type: Content type to get renderer for

        Returns:
            Renderer instance or None if not found
        """
        return self._renderers.get(content_type)
