"""LaTeX content-specific renderers."""

from typing import Any, Dict, List, Optional, Set

from src.core.models.content import BaseContent, ContentType
from src.core.models.creatures import Creature
from src.core.models.items import Item
from src.core.models.spells import Spell
from src.renderers.base import ContentRenderer, RenderContext

from .templates import LaTeXTemplateEngine


class LaTeXContentRenderer(ContentRenderer):
    """Base LaTeX content renderer with common functionality."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
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
    """LaTeX renderer for spell content."""

    @property
    def supported_content_types(self) -> Set[ContentType]:
        """Return supported content types."""
        return {ContentType.SPELL}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render spell content to LaTeX.

        Args:
            content: Spell to render
            context: Rendering context

        Returns:
            LaTeX representation of spell
        """
        if not isinstance(content, Spell):
            raise ValueError(f"Expected Spell, got {type(content)}")

        # Build template variables
        variables = {
            "name": self.escape_latex(content.name),
            "level_text": content.get_level_text(),
            "school": content.school,
            "casting_time": content.get_casting_time_text(),
            "range_text": content.get_range_text(),
            "components_text": content.get_components_text(),
            "duration_text": content.get_duration_text(),
            "description": self._format_entries(content.entries, context),
            "higher_levels": (
                self._format_higher_levels(content, context)
                if content.higher_level
                else None
            ),
        }

        return self.template_engine.render_template("spell", variables)

    def _format_casting_time(self, time_data: List[Dict[str, Any]]) -> str:
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

    def _format_range(self, range_data: Dict[str, Any]) -> str:
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

    def _format_components(self, components: Dict[str, Any]) -> str:
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

    def _format_duration(self, duration_data: List[Dict[str, Any]]) -> str:
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

    def _format_entries(self, entries: List[str], context: RenderContext) -> str:
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

    def _format_higher_levels(
        self, spell: Spell, context: RenderContext
    ) -> Optional[str]:
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


class LaTeXCreatureRenderer(LaTeXContentRenderer):
    """LaTeX renderer for creature content."""

    @property
    def supported_content_types(self) -> Set[ContentType]:
        """Return supported content types."""
        return {ContentType.CREATURE}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render creature content to LaTeX.

        Args:
            content: Creature to render
            context: Rendering context

        Returns:
            LaTeX representation of creature
        """
        if not isinstance(content, Creature):
            raise ValueError(f"Expected Creature, got {type(content)}")

        # Build template variables
        variables = {
            "name": self.escape_latex(content.name),
            "size_text": self._format_size(content.size),
            "type_text": content.type,
            "alignment_text": self._format_alignment(content.alignment),
            "ac_text": self._format_ac(content.ac),
            "hp_text": self._format_hp(content.hp),
            "speed_text": self._format_speed(content.speed),
            "str_text": self._format_ability_score(content.strength),
            "dex_text": self._format_ability_score(content.dexterity),
            "con_text": self._format_ability_score(content.constitution),
            "int_text": self._format_ability_score(content.intelligence),
            "wis_text": self._format_ability_score(content.wisdom),
            "cha_text": self._format_ability_score(content.charisma),
            "cr_text": self._format_cr(content.cr),
            "skills": self._format_skills(getattr(content, "skill", None)),
            "damage_resistances": self._format_damage_list(
                getattr(content, "resist", None)
            ),
            "damage_immunities": self._format_damage_list(
                getattr(content, "immune", None)
            ),
            "condition_immunities": self._format_condition_list(
                getattr(content, "conditionImmune", None)
            ),
            "senses": self._format_senses(getattr(content, "senses", None)),
            "languages": self._format_languages(getattr(content, "languages", None)),
            "traits": self._format_traits(getattr(content, "trait", None), context),
            "actions": self._format_actions(getattr(content, "action", None), context),
        }

        return self.template_engine.render_template("creature", variables)

    def _format_size(self, size_data: List[str]) -> str:
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

    def _format_alignment(self, alignment: List[str]) -> str:
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
            if align in alignment_map:
                parts.append(alignment_map[align])
            else:
                parts.append(align.lower())

        return " ".join(parts) if parts else "unaligned"

    def _format_ac(self, ac_data: List[Any]) -> str:
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

    def _format_skills(self, skills: Optional[Dict[str, Any]]) -> Optional[str]:
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
            sign = "+" if bonus >= 0 else ""
            skill_parts.append(f"{skill.title()} {sign}{bonus}")

        return ", ".join(skill_parts) if skill_parts else None

    def _format_damage_list(self, damage_data: Optional[List[Any]]) -> Optional[str]:
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

    def _format_condition_list(
        self, condition_data: Optional[List[str]]
    ) -> Optional[str]:
        """Format condition immunity list.

        Args:
            condition_data: Condition data

        Returns:
            Formatted condition list or None
        """
        if not condition_data:
            return None

        return ", ".join(condition_data)

    def _format_senses(self, senses_data: Optional[List[str]]) -> Optional[str]:
        """Format senses list.

        Args:
            senses_data: Senses data

        Returns:
            Formatted senses string or None
        """
        if not senses_data:
            return None

        return ", ".join(senses_data)

    def _format_languages(self, languages_data: Optional[List[str]]) -> Optional[str]:
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
        self, traits_data: Optional[List[Dict[str, Any]]], context: RenderContext
    ) -> Optional[List[Dict[str, str]]]:
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
        self, actions_data: Optional[List[Dict[str, Any]]], context: RenderContext
    ) -> Optional[List[Dict[str, str]]]:
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


class LaTeXItemRenderer(LaTeXContentRenderer):
    """LaTeX renderer for item content."""

    @property
    def supported_content_types(self) -> Set[ContentType]:
        """Return supported content types."""
        return {ContentType.ITEM}

    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render item content to LaTeX.

        Args:
            content: Item to render
            context: Rendering context

        Returns:
            LaTeX representation of item
        """
        if not isinstance(content, Item):
            raise ValueError(f"Expected Item, got {type(content)}")

        # Build template variables
        variables = {
            "name": self.escape_latex(content.name),
            "type_text": content.type if hasattr(content, "type") else "Item",
            "rarity_text": self._format_rarity(getattr(content, "rarity", None)),
            "description": self._format_entries(
                getattr(content, "entries", []), context
            ),
            "properties": self._format_properties(getattr(content, "property", None)),
        }

        return self.template_engine.render_template("item", variables)

    def _format_rarity(self, rarity: Optional[str]) -> str:
        """Format item rarity.

        Args:
            rarity: Rarity value

        Returns:
            Formatted rarity string
        """
        if not rarity:
            return ""

        return f", {rarity}"

    def _format_entries(self, entries: List[Any], context: RenderContext) -> str:
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

    def _format_properties(self, properties: Optional[List[str]]) -> Optional[str]:
        """Format item properties.

        Args:
            properties: List of properties

        Returns:
            Formatted properties string or None
        """
        if not properties:
            return None

        return ", ".join(properties)


class LaTeXContentRendererRegistry:
    """Registry for LaTeX content renderers."""

    def __init__(self):
        """Initialize renderer registry."""
        self._renderers: Dict[ContentType, ContentRenderer] = {}
        self._register_default_renderers()

    def _register_default_renderers(self):
        """Register default content renderers."""
        self.register_renderer(ContentType.SPELL, LaTeXSpellRenderer())
        self.register_renderer(ContentType.CREATURE, LaTeXCreatureRenderer())
        self.register_renderer(ContentType.ITEM, LaTeXItemRenderer())

    def register_renderer(self, content_type: ContentType, renderer: ContentRenderer):
        """Register a renderer for a content type.

        Args:
            content_type: Content type to handle
            renderer: Renderer instance
        """
        self._renderers[content_type] = renderer

    def get_renderer(self, content_type: ContentType) -> Optional[ContentRenderer]:
        """Get renderer for content type.

        Args:
            content_type: Content type to get renderer for

        Returns:
            Renderer instance or None if not found
        """
        return self._renderers.get(content_type)
