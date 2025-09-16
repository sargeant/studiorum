"""Creature collection service for advanced creature filtering and gathering."""

import difflib
from typing import Any

from studiorum.core.logging import get_logger

from ..loaders.omnidexer import Omnidexer
from ..models.content import ContentType
from ..models.creature_filters import CreatureCollectionResult, CreatureFilterCriteria
from ..models.creatures import Creature
from ..models.legendarygroup import LegendaryGroup

logger = get_logger(__name__)


class CreatureCollector:
    """Service for collecting creatures based on advanced filter criteria.

    This service handles both encounter building use cases (specific creature names) and
    DM reference use cases (CR/type-based filtering) with comprehensive
    filtering capabilities.
    """

    def __init__(self, omnidexer: Omnidexer):
        """Initialize the creature collector with an omnidexer instance.

        Args:
            omnidexer: The omnidexer instance for content lookup
        """
        self.omnidexer = omnidexer

    def collect_creatures(
        self, criteria: CreatureFilterCriteria
    ) -> CreatureCollectionResult:
        """Collect creatures matching the given criteria.

        Args:
            criteria: The filtering criteria to apply

        Returns:
            CreatureCollectionResult with matched creatures and metadata
        """
        result = CreatureCollectionResult()

        # Handle name-only filtering (encounter building use case)
        if criteria.is_name_only_filter() and criteria.creature_names:
            return self._collect_by_names(
                criteria.creature_names, criteria.sources, criteria.creature_source_map
            )

        # Handle creature names with additional filtering
        if criteria.creature_names:
            name_result = self._collect_by_names(
                criteria.creature_names, criteria.sources, criteria.creature_source_map
            )
            # Filter the name-based results by the same criteria (excluding name and source filters)
            for creature in name_result.creatures:
                if self._matches_criteria(creature, criteria):
                    # Check if already added to avoid duplicates
                    if creature not in result.creatures:
                        source_abbrev = None
                        if hasattr(creature.source, "abbreviation"):
                            source_abbrev = creature.source.abbreviation
                        result.add_creature(creature, source_abbrev)

            # Add unresolved names
            result.unresolved_names.extend(name_result.unresolved_names)
            result.suggestions.update(name_result.suggestions)

        # Handle non-name-based filtering (CR/type/etc.)
        else:
            # Get all creatures from relevant sources
            if criteria.sources:
                all_creatures = []
                creature_type = ContentType("creature")

                # Get all creatures first, then filter by source case-insensitively
                # This fixes the case sensitivity mismatch where criteria.sources are normalized to uppercase
                # but omnidexer sources maintain their original case
                all_content = self.omnidexer.get_all_by_type(creature_type)
                for creature in all_content:
                    if isinstance(creature, Creature) and self._matches_sources(
                        creature, criteria.sources
                    ):
                        all_creatures.append(creature)
            else:
                # Get all creatures from all sources
                creature_type = ContentType("creature")
                all_content = self.omnidexer.get_all_by_type(creature_type)
                all_creatures = [
                    creature
                    for creature in all_content
                    if isinstance(creature, Creature)
                ]

            if not all_creatures:
                logger.warning("No creatures found in omnidexer")
                return result

            logger.debug(f"Filtering {len(all_creatures)} creatures with criteria")

            # Apply filters
            for creature_content in all_creatures:
                if not isinstance(creature_content, Creature):
                    logger.debug(
                        f"Skipping non-creature content: {type(creature_content)}"
                    )
                    continue

                if self._matches_criteria(creature_content, criteria):
                    # Get source abbreviation for tracking
                    source_abbrev = None
                    if hasattr(creature_content.source, "abbreviation"):
                        source_abbrev = creature_content.source.abbreviation

                    result.add_creature(creature_content, source_abbrev)

        logger.info(f"Collected {result.total_count} creatures matching criteria")

        # Populate lair actions for all collected creatures
        if result.creatures:
            self.populate_lair_actions(result.creatures)

        return result

    def collect_by_names(
        self,
        names: list[str],
        sources: list[str] | None = None,
        creature_source_map: dict[str, str] | None = None,
    ) -> CreatureCollectionResult:
        """Collect specific creatures by name with fuzzy matching.

        Args:
            names: List of creature names to find
            sources: Optional list of source abbreviations to limit search
            creature_source_map: Optional per-creature source specifications

        Returns:
            CreatureCollectionResult with found creatures and unresolved names
        """
        return self._collect_by_names(names, sources, creature_source_map)

    def collect_by_cr_range(
        self, min_cr: float, max_cr: float
    ) -> CreatureCollectionResult:
        """Collect all creatures within a CR range.

        Args:
            min_cr: Minimum challenge rating
            max_cr: Maximum challenge rating

        Returns:
            CreatureCollectionResult with collected creatures
        """
        # Create filter criteria for CR range filtering
        criteria = CreatureFilterCriteria(min_cr=min_cr, max_cr=max_cr)

        return self.collect_creatures(criteria)

    def collect_by_type(self, creature_types: list[str]) -> CreatureCollectionResult:
        """Collect all creatures of specific types.

        Args:
            creature_types: List of creature types (e.g., ['dragon', 'fiend'])

        Returns:
            CreatureCollectionResult with collected creatures
        """
        # Create filter criteria for type filtering
        criteria = CreatureFilterCriteria(creature_types=creature_types)

        return self.collect_creatures(criteria)

    def _collect_by_names(
        self,
        names: list[str],
        sources: list[str] | None = None,
        creature_source_map: dict[str, str] | None = None,
    ) -> CreatureCollectionResult:
        """Internal method to collect creatures by specific names.

        Args:
            names: List of creature names to find
            sources: Optional list of source abbreviations to limit search
            creature_source_map: Optional per-creature source specifications
        """
        result = CreatureCollectionResult()
        creature_type = ContentType("creature")

        # Use default sources if none specified
        if sources is None:
            from studiorum.cli.config_factory import get_default_sources

            sources = get_default_sources()

        for name in names:
            # Check if there's a specific source for this creature
            specific_source = None
            if creature_source_map and name in creature_source_map:
                specific_source = creature_source_map[name]

            # Try exact match with specific source if available
            if specific_source:
                # Use find() with specific source for targeted lookup
                creature = self.omnidexer.find(creature_type, name, specific_source)
                if creature and isinstance(creature, Creature):
                    source_abbrev = None
                    if hasattr(creature.source, "abbreviation"):
                        source_abbrev = creature.source.abbreviation
                    result.add_creature(creature, source_abbrev)
                else:
                    # Creature not found with specific source
                    suggestions = self._find_creature_suggestions(
                        name, [specific_source] if specific_source else sources
                    )
                    result.add_unresolved(name, suggestions)
            else:
                # Use original logic for creatures without specific sources
                matches = self.omnidexer.find_all(creature_type, name)

                if matches:
                    # Filter by sources (now always specified, either from parameter or default)
                    filtered_matches: list[Creature] = []
                    for creature in matches:
                        if isinstance(creature, Creature) and self._matches_sources(
                            creature, sources
                        ):
                            filtered_matches.append(creature)
                    creature_matches = filtered_matches

                    # Add all matching creatures
                    for creature in creature_matches:
                        source_abbrev = None
                        if hasattr(creature.source, "abbreviation"):
                            source_abbrev = creature.source.abbreviation
                        result.add_creature(creature, source_abbrev)

                    # If no matches after source filtering, treat as unresolved
                    if sources and not creature_matches:
                        suggestions = self._find_creature_suggestions(name, sources)
                        result.add_unresolved(name, suggestions)
                else:
                    # No exact match, try fuzzy matching
                    suggestions = self._find_creature_suggestions(name, sources)
                    result.add_unresolved(name, suggestions)

        # Populate lair actions for all collected creatures
        if result.creatures:
            self.populate_lair_actions(result.creatures)

        return result

    def _matches_criteria(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if a creature matches the given criteria.

        Args:
            creature: The creature to check
            criteria: The filter criteria

        Returns:
            True if the creature matches all criteria
        """
        # CR filtering
        if not self._matches_cr_criteria(creature, criteria):
            return False

        # Type and tag filtering
        if not self._matches_type_criteria(creature, criteria):
            return False

        # Size filtering
        if criteria.sizes and not criteria.matches_size(getattr(creature, "size", "")):
            return False

        # Alignment filtering
        if not self._matches_alignment_criteria(creature, criteria):
            return False

        # Combat stats filtering
        if not self._matches_combat_stats(creature, criteria):
            return False

        # Special abilities filtering
        if not self._matches_special_abilities(creature, criteria):
            return False

        # Movement and senses filtering
        if not self._matches_movement_and_senses(creature, criteria):
            return False

        # Communication filtering
        if not self._matches_communication(creature, criteria):
            return False

        # Source filtering
        if criteria.sources:
            if not self._matches_sources(creature, criteria.sources):
                return False

        return True

    def _matches_cr_criteria(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches CR filtering criteria."""
        if not hasattr(creature, "cr") or creature.cr is None:
            # If no CR data and we're filtering by CR, exclude it
            if any(
                [
                    criteria.min_cr is not None,
                    criteria.max_cr is not None,
                    criteria.cr_range is not None,
                ]
            ):
                return False
            return True

        # Extract CR value from potentially complex CR data structure
        cr_str = self._extract_cr_string(creature.cr)
        cr_value = self._parse_cr_value(cr_str)

        # Handle variable CR exclusion
        if cr_value is None and criteria.exclude_variable_cr:
            return False

        if cr_value is None:
            return True  # Variable CR allowed

        # Check min/max CR
        if criteria.min_cr is not None and cr_value < criteria.min_cr:
            return False
        if criteria.max_cr is not None and cr_value > criteria.max_cr:
            return False

        # Check CR range string
        if criteria.cr_range is not None:
            min_cr, max_cr = self._parse_cr_range(criteria.cr_range)
            if cr_value < min_cr or cr_value > max_cr:
                return False

        return True

    def _matches_type_criteria(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches type/tag filtering criteria."""
        if not hasattr(creature, "type"):
            return True  # No type filtering if no type data

        creature_type_data = creature.type

        # Parse creature type structure from 5e.tools data
        if isinstance(creature_type_data, dict):
            main_type = creature_type_data.get("type", "").lower()
            tags_data = creature_type_data.get("tags", [])
            creature_tags = [
                tag.lower() if isinstance(tag, str) else str(tag).lower()
                for tag in (tags_data if isinstance(tags_data, list) else [tags_data])
            ]
        elif isinstance(creature_type_data, str):
            main_type = creature_type_data.lower()
            creature_tags = []
        else:
            main_type = str(creature_type_data).lower()
            creature_tags = []

        return criteria.matches_creature_type(main_type, creature_tags or None)

    def _matches_alignment_criteria(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches alignment filtering criteria."""
        if criteria.alignments is None:
            return True

        if not hasattr(creature, "alignment") or not creature.alignment:
            return False

        # Handle alignment data structure
        creature_alignment = creature.alignment
        if isinstance(creature_alignment, list):
            alignment_str = " ".join(str(a) for a in creature_alignment).lower()
        else:
            alignment_str = str(creature_alignment).lower()

        return any(alignment in alignment_str for alignment in criteria.alignments)

    def _matches_combat_stats(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches combat stats criteria."""
        # AC filtering
        if criteria.min_ac is not None or criteria.max_ac is not None:
            if not hasattr(creature, "ac") or not creature.ac:
                return False

            creature_ac = self._extract_base_ac(creature.ac)
            if criteria.min_ac is not None and creature_ac < criteria.min_ac:
                return False
            if criteria.max_ac is not None and creature_ac > criteria.max_ac:
                return False

        # HP filtering
        if criteria.min_hp is not None or criteria.max_hp is not None:
            if not hasattr(creature, "hp") or not creature.hp:
                return False

            creature_hp = self._extract_average_hp(creature.hp)
            if criteria.min_hp is not None and creature_hp < criteria.min_hp:
                return False
            if criteria.max_hp is not None and creature_hp > criteria.max_hp:
                return False

        # Damage immunities/resistances/vulnerabilities filtering
        if not self._matches_damage_criteria(creature, criteria):
            return False

        # Condition immunities filtering
        if criteria.condition_immunities is not None:
            if not hasattr(creature, "conditionImmune") or not creature.conditionImmune:
                return False

            creature_immunities = [str(ci).lower() for ci in creature.conditionImmune]
            if not all(
                ci in creature_immunities for ci in criteria.condition_immunities
            ):
                return False

        return True

    def _matches_damage_criteria(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check damage-related filtering criteria."""
        # Damage immunities
        if criteria.damage_immunities is not None:
            if not hasattr(creature, "immune") or not creature.immune:
                return False
            creature_immunities = [str(di).lower() for di in creature.immune]
            if not all(di in creature_immunities for di in criteria.damage_immunities):
                return False

        # Damage resistances
        if criteria.damage_resistances is not None:
            if not hasattr(creature, "resist") or not creature.resist:
                return False
            creature_resistances = [str(dr).lower() for dr in creature.resist]
            if not all(
                dr in creature_resistances for dr in criteria.damage_resistances
            ):
                return False

        # Damage vulnerabilities
        if criteria.damage_vulnerabilities is not None:
            if not hasattr(creature, "vulnerable") or not creature.vulnerable:
                return False
            creature_vulnerabilities = [str(dv).lower() for dv in creature.vulnerable]
            if not all(
                dv in creature_vulnerabilities for dv in criteria.damage_vulnerabilities
            ):
                return False

        return True

    def _matches_special_abilities(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches special abilities criteria."""
        # Check spellcasting abilities
        if criteria.has_spellcasting is not None:
            has_spellcasting = self._creature_has_spellcasting(creature)
            if has_spellcasting != criteria.has_spellcasting:
                return False

        if criteria.has_innate_spellcasting is not None:
            has_innate = self._creature_has_innate_spellcasting(creature)
            if has_innate != criteria.has_innate_spellcasting:
                return False

        # Check legendary actions
        if criteria.has_legendary_actions is not None:
            has_legendary = bool(getattr(creature, "legendary", None))
            if has_legendary != criteria.has_legendary_actions:
                return False

        # Check multiattack
        if criteria.has_multiattack is not None:
            has_multiattack = self._creature_has_multiattack(creature)
            if has_multiattack != criteria.has_multiattack:
                return False

        # Check reactions
        if criteria.has_reactions is not None:
            has_reactions = bool(getattr(creature, "reaction", None))
            if has_reactions != criteria.has_reactions:
                return False

        # Check bonus actions
        if criteria.has_bonus_actions is not None:
            has_bonus_actions = self._creature_has_bonus_actions(creature)
            if has_bonus_actions != criteria.has_bonus_actions:
                return False

        return True

    def _matches_movement_and_senses(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches movement and senses criteria."""
        # Movement filtering
        movement_abilities = self._detect_movement_abilities(creature)

        if (
            criteria.has_fly_speed is not None
            and movement_abilities.get("has_fly_speed", False) != criteria.has_fly_speed
        ):
            return False
        if (
            criteria.has_swim_speed is not None
            and movement_abilities.get("has_swim_speed", False)
            != criteria.has_swim_speed
        ):
            return False
        if (
            criteria.has_climb_speed is not None
            and movement_abilities.get("has_climb_speed", False)
            != criteria.has_climb_speed
        ):
            return False
        if (
            criteria.has_burrow_speed is not None
            and movement_abilities.get("has_burrow_speed", False)
            != criteria.has_burrow_speed
        ):
            return False

        # Senses filtering
        senses_abilities = self._detect_senses(creature)

        if (
            criteria.has_darkvision is not None
            and senses_abilities.get("has_darkvision", False) != criteria.has_darkvision
        ):
            return False
        if (
            criteria.has_blindsight is not None
            and senses_abilities.get("has_blindsight", False) != criteria.has_blindsight
        ):
            return False
        if (
            criteria.has_tremorsense is not None
            and senses_abilities.get("has_tremorsense", False)
            != criteria.has_tremorsense
        ):
            return False
        if (
            criteria.has_truesight is not None
            and senses_abilities.get("has_truesight", False) != criteria.has_truesight
        ):
            return False

        return True

    def _matches_communication(
        self, creature: Creature, criteria: CreatureFilterCriteria
    ) -> bool:
        """Check if creature matches communication criteria."""
        # Language filtering
        if criteria.speaks_language is not None:
            if not hasattr(creature, "languages") or not creature.languages:
                return False

            creature_languages = []
            if isinstance(creature.languages, list):
                for lang in creature.languages:
                    creature_languages.append(str(lang).lower())
            else:
                creature_languages.append(str(creature.languages).lower())

            if not any(lang in creature_languages for lang in criteria.speaks_language):
                return False

        # Skill filtering
        if criteria.has_skill is not None:
            if not hasattr(creature, "skill") or not creature.skill:
                return False

            creature_skills: list[str] = []
            if isinstance(creature.skill, dict):
                creature_skills.extend(creature.skill.keys())
            elif creature.skill is not None:
                # Handle other non-None, non-dict types
                creature_skills.append(str(creature.skill).lower())

            creature_skills = [skill.lower() for skill in creature_skills]
            if not any(skill in creature_skills for skill in criteria.has_skill):
                return False

        return True

    def _extract_cr_string(self, cr_data: Any) -> str:
        """Extract CR string from various CR data formats.

        Args:
            cr_data: CR data which may be string, int, float, or dict

        Returns:
            String representation of the CR value
        """
        if isinstance(cr_data, dict):
            # Handle dictionary format: {'cr': '24', 'xpLair': 75000}
            return str(cr_data.get("cr", "varies"))
        else:
            # Handle simple formats: string, int, float
            return str(cr_data)

    def _parse_cr_value(self, cr_string: str) -> float | None:
        """Parse CR values including fractions: '1/4', '1/2', '0', '10', 'varies'."""
        cr_string = cr_string.strip().lower()
        if cr_string in ["varies", "variable"]:
            return None  # Handle variable CR
        if "/" in cr_string:
            # Handle fractions: 1/4 = 0.25, 1/8 = 0.125, 1/2 = 0.5
            try:
                numerator, denominator = cr_string.split("/")
                return float(numerator) / float(denominator)
            except (ValueError, ZeroDivisionError):
                return None
        try:
            return float(cr_string)
        except ValueError:
            return None

    def _parse_cr_range(self, cr_string: str) -> tuple[float, float]:
        """Parse CR range formats: '1/4-5', '10+', '0', '<1'."""
        cr_string = cr_string.strip()
        if "+" in cr_string:
            # Handle "10+" format
            min_cr_str = cr_string.replace("+", "")
            min_cr = self._parse_cr_value(min_cr_str)
            return (min_cr if min_cr is not None else 0.0, 30.0)  # Max CR in 5e
        elif "<" in cr_string:
            # Handle "<1" format
            max_cr_str = cr_string.replace("<", "")
            max_cr = self._parse_cr_value(max_cr_str)
            return (0.0, max_cr if max_cr is not None else 30.0)
        elif "-" in cr_string:
            # Handle "1/4-5" format
            min_str, max_str = cr_string.split("-", 1)
            min_cr = self._parse_cr_value(min_str)
            max_cr = self._parse_cr_value(max_str)
            return (
                min_cr if min_cr is not None else 0.0,
                max_cr if max_cr is not None else 30.0,
            )
        else:
            # Single CR value
            cr = self._parse_cr_value(cr_string)
            return (cr if cr is not None else 0.0, cr if cr is not None else 30.0)

    def _extract_base_ac(self, ac_data: Any) -> int:
        """Extract base AC value from 5e.tools AC data structure."""
        if isinstance(ac_data, list) and len(ac_data) > 0:
            # Take first AC value
            first_ac = ac_data[0]
            if isinstance(first_ac, dict):
                return int(first_ac.get("ac", 0))
            else:
                return int(first_ac)
        elif isinstance(ac_data, dict):
            return int(ac_data.get("ac", 0))
        elif isinstance(ac_data, int | str):
            try:
                return int(ac_data)
            except ValueError:
                return 0
        return 0

    def _extract_average_hp(self, hp_data: Any) -> int:
        """Extract average HP from 5e.tools HP data structure."""
        if isinstance(hp_data, dict):
            # Try "average" field first, then "special"
            if "average" in hp_data:
                return int(hp_data["average"])
            elif "special" in hp_data:
                # Try to parse numbers from special text
                import re

                special_text = str(hp_data["special"])
                numbers = re.findall(r"\d+", special_text)
                if numbers:
                    return int(numbers[0])
        elif isinstance(hp_data, int | str):
            try:
                return int(hp_data)
            except ValueError:
                return 0
        return 0

    def _detect_movement_abilities(self, creature: Creature) -> dict[str, bool]:
        """Detect movement abilities from 5e.tools speed data."""
        if not hasattr(creature, "speed") or not creature.speed:
            return {
                "has_fly_speed": False,
                "has_swim_speed": False,
                "has_climb_speed": False,
                "has_burrow_speed": False,
            }

        speed_data = creature.speed
        if isinstance(speed_data, dict):
            return {
                "has_fly_speed": "fly" in speed_data,
                "has_swim_speed": "swim" in speed_data,
                "has_climb_speed": "climb" in speed_data,
                "has_burrow_speed": "burrow" in speed_data,
            }

        return {
            "has_fly_speed": False,
            "has_swim_speed": False,
            "has_climb_speed": False,
            "has_burrow_speed": False,
        }

    def _detect_senses(self, creature: Creature) -> dict[str, bool]:
        """Detect special senses from 5e.tools senses data."""
        if not hasattr(creature, "senses") or not creature.senses:
            return {
                "has_darkvision": False,
                "has_blindsight": False,
                "has_tremorsense": False,
                "has_truesight": False,
            }

        senses_data = creature.senses
        if isinstance(senses_data, list):
            senses_text = " ".join(str(sense) for sense in senses_data)
        else:
            senses_text = str(senses_data)

        senses_text = senses_text.lower()

        return {
            "has_darkvision": "darkvision" in senses_text,
            "has_blindsight": "blindsight" in senses_text,
            "has_tremorsense": "tremorsense" in senses_text,
            "has_truesight": "truesight" in senses_text,
        }

    def _creature_has_spellcasting(self, creature: Creature) -> bool:
        """Check if creature has full spellcasting trait."""
        if hasattr(creature, "spellcasting") and creature.spellcasting:
            return True

        # Check in traits for "Spellcasting" ability
        if hasattr(creature, "trait") and creature.trait:
            for trait in creature.trait:
                if isinstance(trait, dict) and "name" in trait:
                    if "spellcasting" in str(trait["name"]).lower():
                        return True

        return False

    def _creature_has_innate_spellcasting(self, creature: Creature) -> bool:
        """Check if creature has innate spellcasting trait."""
        if hasattr(creature, "trait") and creature.trait:
            for trait in creature.trait:
                if isinstance(trait, dict) and "name" in trait:
                    if "innate spellcasting" in str(trait["name"]).lower():
                        return True

        return False

    def _creature_has_multiattack(self, creature: Creature) -> bool:
        """Check if creature has multiattack action."""
        if hasattr(creature, "action") and creature.action:
            for action in creature.action:
                if isinstance(action, dict) and "name" in action:
                    if "multiattack" in str(action["name"]).lower():
                        return True

        return False

    def _creature_has_bonus_actions(self, creature: Creature) -> bool:
        """Check if creature has bonus action abilities."""
        # Check for bonus actions in action list or separate bonus field
        return bool(getattr(creature, "bonus", None))

    def _matches_sources(self, creature: Creature, target_sources: list[str]) -> bool:
        """Check if creature source matches target sources.

        Args:
            creature: The creature to check
            target_sources: List of source abbreviations

        Returns:
            True if creature source is in target sources
        """
        source_abbrev = None

        # Handle Source objects (normal case)
        if hasattr(creature.source, "abbreviation"):
            source_abbrev = creature.source.abbreviation
        # Handle dictionary sources (from copy resolution)
        elif isinstance(creature.source, dict) and "abbreviation" in creature.source:
            source_abbrev = creature.source["abbreviation"]
        # Handle string sources (fallback)
        elif isinstance(creature.source, str):
            source_abbrev = creature.source

        if source_abbrev:
            return source_abbrev.upper() in [src.upper() for src in target_sources]

        return False

    def _find_creature_suggestions(
        self, name: str, sources: list[str] | None = None
    ) -> list[str]:
        """Find suggestions for a misspelled creature name.

        Args:
            name: The creature name to find suggestions for
            sources: Optional list of source abbreviations to limit suggestions

        Returns:
            List of suggested creature names
        """
        creature_type = ContentType("creature")

        # Get creatures from specified sources or all sources
        if sources:
            all_creatures = []
            for source in sources:
                source_creatures = self.omnidexer.get_all_by_source(source)
                for creature in source_creatures:
                    if isinstance(creature, Creature):
                        all_creatures.append(creature)
        else:
            all_content = self.omnidexer.get_all_by_type(creature_type)
            all_creatures = [
                creature for creature in all_content if isinstance(creature, Creature)
            ]

        if not all_creatures:
            return []

        # Get all creature names
        creature_names = []
        for creature in all_creatures:
            if isinstance(creature, Creature):
                creature_names.append(creature.name)

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(name, creature_names, n=5, cutoff=0.4)

        return suggestions

    def get_available_types(self) -> list[str]:
        """Get list of all creature types available.

        Returns:
            List of creature types
        """
        creature_type = ContentType("creature")
        all_creatures = self.omnidexer.get_all_by_type(creature_type)

        if not all_creatures:
            return []

        types = set()
        for creature in all_creatures:
            if isinstance(creature, Creature) and hasattr(creature, "type"):
                type_data = creature.type
                if isinstance(type_data, dict):
                    types.add(type_data.get("type", "unknown").lower())
                elif isinstance(type_data, str):
                    types.add(type_data.lower())

        return sorted(types)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about available creatures.

        Returns:
            Dictionary with creature statistics
        """
        creature_type = ContentType("creature")
        all_creatures = self.omnidexer.get_all_by_type(creature_type)

        if not all_creatures:
            return {"total": 0}

        stats: dict[str, Any] = {
            "total": len(all_creatures),
            "by_cr": {},
            "by_type": {},
            "by_source": {},
            "types": self.get_available_types(),
        }

        for creature in all_creatures:
            if isinstance(creature, Creature):
                # Count by CR
                cr_str = str(getattr(creature, "cr", "unknown"))
                stats["by_cr"][cr_str] = stats["by_cr"].get(cr_str, 0) + 1

                # Count by type
                if hasattr(creature, "type"):
                    type_data = creature.type
                    if isinstance(type_data, dict):
                        type_str = type_data.get("type", "unknown")
                    else:
                        type_str = str(type_data)
                    stats["by_type"][type_str] = stats["by_type"].get(type_str, 0) + 1

                # Count by source
                if hasattr(creature.source, "abbreviation"):
                    source = creature.source.abbreviation
                    stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        return stats

    def populate_lair_actions(self, creatures: list["Creature"]) -> None:
        """Populate lair actions for creatures from legendary group data.

        Args:
            creatures: List of creatures to enhance with lair actions
        """
        from ..models.content import ContentType
        from ..models.legendarygroup import LegendaryGroup

        # Get all legendary groups
        try:
            legendary_groups = self.omnidexer.get_all_by_type(
                ContentType.LEGENDARYGROUP
            )
        except Exception as e:
            logger.warning(f"Could not load legendary groups for lair actions: {e}")
            return

        if not legendary_groups:
            logger.debug("No legendary groups available for lair action linking")
            return

        # Create lookup map for efficient matching
        lg_lookup: dict[str, LegendaryGroup] = {}
        for lg in legendary_groups:
            if isinstance(lg, LegendaryGroup):
                key = f"{lg.name}|{lg.source.abbreviation}"
                lg_lookup[key] = lg

        logger.debug(f"Built legendary group lookup with {len(lg_lookup)} entries")

        # Link creatures to legendary groups
        linked_count = 0
        for creature in creatures:
            if self._link_creature_to_legendary_group(creature, lg_lookup):
                linked_count += 1

        logger.debug(f"Linked {linked_count} creatures with lair actions")

    def _link_creature_to_legendary_group(
        self, creature: "Creature", lg_lookup: dict[str, LegendaryGroup]
    ) -> bool:
        """Link a single creature to its legendary group if available.

        Args:
            creature: Creature to link
            lg_lookup: Lookup map of legendary groups by composite key

        Returns:
            True if creature was linked to legendary group, False otherwise
        """
        # Create composite key for lookup
        key = f"{creature.name}|{creature.source.abbreviation}"

        # Try to find matching legendary group
        legendary_group = lg_lookup.get(key)
        if not legendary_group:
            return False

        # Copy lair actions to creature if they exist
        if legendary_group.has_lair_actions() and legendary_group.lair_actions:
            # Convert legendary group entries to creature entries
            creature.lair_actions = self._convert_lg_entries_to_creature_entries(
                legendary_group.lair_actions
            )
            logger.debug(
                f"Added {len(creature.lair_actions)} lair actions to {creature.name}"
            )
            return True

        return False

    def _convert_lg_entries_to_creature_entries(self, lg_entries: list) -> list:
        """Convert legendary group entries to creature entry format.

        Args:
            lg_entries: List of legendary group entries

        Returns:
            List of creature entries (str | CreatureEntryContent)
        """
        from ..models.creatures import CreatureEntryContent

        converted_entries = []
        for entry in lg_entries:
            if isinstance(entry, str):
                # String entries can be used directly
                converted_entries.append(entry)
            elif hasattr(entry, "type") and entry.type == "list":
                # Convert ListEntry to CreatureEntryContent
                converted_entries.append(
                    CreatureEntryContent(
                        type="list",
                        name=getattr(entry, "name", None),
                        items=getattr(entry, "items", []),
                    )
                )
            elif isinstance(entry, dict):
                # Convert dict to CreatureEntryContent
                converted_entries.append(CreatureEntryContent(**entry))
            else:
                # For other entry types, convert to dict first then to CreatureEntryContent
                if hasattr(entry, "model_dump"):
                    converted_entries.append(CreatureEntryContent(**entry.model_dump()))
                else:
                    logger.warning(
                        f"Unknown entry type for lair actions: {type(entry)}"
                    )

        return converted_entries
