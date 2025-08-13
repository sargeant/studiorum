"""Spell collection service for advanced spell filtering and gathering."""

import difflib
import logging
from typing import Any

from ..loaders.omnidexer import Omnidexer
from ..models.content import ContentType
from ..models.spell_filters import SpellCollectionResult, SpellFilterCriteria
from ..models.spells import Spell

logger = logging.getLogger(__name__)


class SpellCollector:
    """Service for collecting spells based on advanced filter criteria.

    This service handles both wizard use cases (specific spell names) and
    cleric use cases (class/level-based filtering) with comprehensive
    filtering capabilities.
    """

    def __init__(self, omnidexer: Omnidexer):
        """Initialize the spell collector with an omnidexer instance.

        Args:
            omnidexer: The omnidexer instance for content lookup
        """
        self.omnidexer = omnidexer

    def collect_spells(self, criteria: SpellFilterCriteria) -> SpellCollectionResult:
        """Collect spells matching the given criteria.

        Args:
            criteria: The filtering criteria to apply

        Returns:
            SpellCollectionResult with matched spells and metadata
        """
        result = SpellCollectionResult()

        # Handle name-only filtering (wizard use case)
        if criteria.is_name_only_filter() and criteria.spell_names:
            return self._collect_by_names(criteria.spell_names, criteria.sources)

        # Handle spell names with source filtering
        if criteria.spell_names:
            name_result = self._collect_by_names(criteria.spell_names, criteria.sources)
            # Filter the name-based results by the same criteria (excluding name and source filters)
            for spell in name_result.spells:
                if self._matches_criteria(spell, criteria):
                    # Check if already added to avoid duplicates
                    if spell not in result.spells:
                        source_abbrev = None
                        if hasattr(spell.source, "abbreviation"):
                            source_abbrev = spell.source.abbreviation
                        result.add_spell(spell, source_abbrev)

            # Add unresolved names
            result.unresolved_names.extend(name_result.unresolved_names)
            result.suggestions.update(name_result.suggestions)

        # Handle non-name-based filtering (class/level/etc.)
        else:
            # Get all spells from relevant sources
            if criteria.sources:
                all_spells = []
                spell_type = ContentType("spell")
                for source in criteria.sources:
                    source_spells = self.omnidexer.get_all_by_source(source)
                    # Filter to only spells of the correct type
                    for spell in source_spells:
                        if isinstance(spell, Spell):
                            all_spells.append(spell)
            else:
                # Get all spells from all sources
                spell_type = ContentType("spell")
                all_content = self.omnidexer.get_all_by_type(spell_type)
                all_spells = [
                    spell for spell in all_content if isinstance(spell, Spell)
                ]

            if not all_spells:
                logger.warning("No spells found in omnidexer")
                return result

            logger.debug(f"Filtering {len(all_spells)} spells with criteria")

            # Apply filters
            for spell_content in all_spells:
                if not isinstance(spell_content, Spell):
                    logger.debug(f"Skipping non-spell content: {type(spell_content)}")
                    continue

                if self._matches_criteria(spell_content, criteria):
                    # Get source abbreviation for tracking
                    source_abbrev = None
                    if hasattr(spell_content.source, "abbreviation"):
                        source_abbrev = spell_content.source.abbreviation

                    result.add_spell(spell_content, source_abbrev)

        logger.info(f"Collected {result.total_count} spells matching criteria")
        return result

    def collect_by_names(self, names: list[str]) -> SpellCollectionResult:
        """Collect specific spells by name with fuzzy matching.

        Args:
            names: List of spell names to find

        Returns:
            SpellCollectionResult with found spells and unresolved names
        """
        return self._collect_by_names(names)

    def collect_by_class_and_level(
        self, classes: list[str], levels: list[int]
    ) -> SpellCollectionResult:
        """Collect all spells available to given classes at given levels.

        Args:
            classes: List of class names (e.g., ['wizard', 'cleric'])
            levels: List of spell levels (e.g., [1, 2, 3])

        Returns:
            SpellCollectionResult with collected spells
        """
        # Create filter criteria for class/level filtering
        criteria = SpellFilterCriteria(classes=classes, levels=levels)

        return self.collect_spells(criteria)

    def _collect_by_names(
        self, names: list[str], sources: list[str] | None = None
    ) -> SpellCollectionResult:
        """Internal method to collect spells by specific names.

        Args:
            names: List of spell names to find
            sources: Optional list of source abbreviations to limit search
        """
        result = SpellCollectionResult()
        spell_type = ContentType("spell")

        for name in names:
            # Try exact match first
            matches = self.omnidexer.find_all(spell_type, name)

            if matches:
                # Filter by sources if specified
                if sources:
                    filtered_matches: list[Spell] = []
                    for spell in matches:
                        if isinstance(spell, Spell) and self._matches_sources(
                            spell, sources
                        ):
                            filtered_matches.append(spell)
                    spell_matches = filtered_matches
                else:
                    spell_matches = [
                        spell for spell in matches if isinstance(spell, Spell)
                    ]

                # Add all matching spells
                for spell in spell_matches:
                    source_abbrev = None
                    if hasattr(spell.source, "abbreviation"):
                        source_abbrev = spell.source.abbreviation
                    result.add_spell(spell, source_abbrev)

                # If no matches after source filtering, treat as unresolved
                if sources and not spell_matches:
                    suggestions = self._find_spell_suggestions(name, sources)
                    result.add_unresolved(name, suggestions)
            else:
                # No exact match, try fuzzy matching
                suggestions = self._find_spell_suggestions(name, sources)
                result.add_unresolved(name, suggestions)

        return result

    def _matches_criteria(self, spell: Spell, criteria: SpellFilterCriteria) -> bool:
        """Check if a spell matches the given criteria.

        Args:
            spell: The spell to check
            criteria: The filter criteria

        Returns:
            True if the spell matches all criteria
        """
        # Level filtering
        if not criteria.matches_spell_level(spell.level):
            return False

        # School filtering
        if not criteria.matches_spell_school(spell.school):
            return False

        # Class filtering
        if criteria.classes and not self._spell_available_to_classes(
            spell, criteria.classes, criteria.include_optional
        ):
            return False

        # Component filtering
        if not self._matches_components(spell, criteria):
            return False

        # Combat filtering
        if not self._matches_combat_criteria(spell, criteria):
            return False

        # Source filtering
        if criteria.sources and not self._matches_sources(spell, criteria.sources):
            return False

        return True

    def _spell_available_to_classes(
        self, spell: Spell, target_classes: list[str], include_optional: bool = False
    ) -> bool:
        """Check if a spell is available to any of the target classes.

        Args:
            spell: The spell to check
            target_classes: List of class names to check against
            include_optional: Whether to include optional/variant class spells

        Returns:
            True if the spell is available to at least one target class
        """
        # If spell doesn't have class information, try to enhance it with lookup data
        if not spell.classes or not spell.classes.fromClassList:
            from .spell_class_lookup import get_spell_class_lookup_service

            lookup_service = get_spell_class_lookup_service()
            enhanced_spell = lookup_service.enhance_spell(spell, include_optional)

            # Use the enhanced spell if it has class information
            if enhanced_spell.classes and enhanced_spell.classes.fromClassList:
                spell = enhanced_spell
            else:
                return False

        # At this point we know spell.classes and fromClassList exist
        if not spell.classes or not spell.classes.fromClassList:
            return False

        spell_classes = [cls.name.lower() for cls in spell.classes.fromClassList]

        for target_class in target_classes:
            if target_class in spell_classes:
                return True

        return False

    def _matches_components(self, spell: Spell, criteria: SpellFilterCriteria) -> bool:
        """Check if spell components match the criteria.

        Args:
            spell: The spell to check
            criteria: The filter criteria

        Returns:
            True if components match the criteria
        """
        # Verbal component filtering
        if criteria.has_verbal is not None:
            if spell.has_verbal_components() != criteria.has_verbal:
                return False

        # Somatic component filtering
        if criteria.has_somatic is not None:
            if spell.has_somatic_components() != criteria.has_somatic:
                return False

        # Material component filtering
        if criteria.has_material is not None:
            if spell.has_material_components() != criteria.has_material:
                return False

        # No material components filter
        if criteria.no_material and spell.has_material_components():
            return False

        # Concentration filtering
        if criteria.concentration is not None:
            if spell.is_concentration() != criteria.concentration:
                return False

        # Ritual filtering
        # Note: Need to check if spell has ritual capability
        # This would require adding ritual detection to the Spell model
        if criteria.ritual is not None:
            # For now, skip ritual filtering as it's not implemented in Spell model
            # TODO: Add ritual detection to Spell model
            pass

        return True

    def _matches_combat_criteria(
        self, spell: Spell, criteria: SpellFilterCriteria
    ) -> bool:
        """Check if spell matches combat-related criteria.

        Args:
            spell: The spell to check
            criteria: The filter criteria

        Returns:
            True if combat criteria match
        """
        # Damage type filtering
        if criteria.damage_types:
            if not spell.damage_inflict:
                return False

            spell_damage_types = [dt.lower() for dt in spell.damage_inflict]
            if not any(dt in spell_damage_types for dt in criteria.damage_types):
                return False

        # Saving throw filtering
        if criteria.saving_throws:
            if not spell.saving_throw:
                return False

            spell_saves = [st.lower() for st in spell.saving_throw]
            if not any(st in spell_saves for st in criteria.saving_throws):
                return False

        # Attack spell filtering
        if criteria.attack_spells is not None:
            has_attack = bool(spell.spell_attack)
            if has_attack != criteria.attack_spells:
                return False

        return True

    def _matches_sources(self, spell: Spell, target_sources: list[str]) -> bool:
        """Check if spell source matches target sources.

        Args:
            spell: The spell to check
            target_sources: List of source abbreviations

        Returns:
            True if spell source is in target sources
        """
        if hasattr(spell.source, "abbreviation"):
            source_abbrev = spell.source.abbreviation.upper()
            return source_abbrev in [src.upper() for src in target_sources]

        return False

    def _find_spell_suggestions(
        self, name: str, sources: list[str] | None = None
    ) -> list[str]:
        """Find suggestions for a misspelled spell name.

        Args:
            name: The spell name to find suggestions for
            sources: Optional list of source abbreviations to limit suggestions

        Returns:
            List of suggested spell names
        """
        spell_type = ContentType("spell")

        # Get spells from specified sources or all sources
        if sources:
            all_spells = []
            for source in sources:
                source_spells = self.omnidexer.get_all_by_source(source)
                for spell in source_spells:
                    if isinstance(spell, Spell):
                        all_spells.append(spell)
        else:
            all_content = self.omnidexer.get_all_by_type(spell_type)
            all_spells = [spell for spell in all_content if isinstance(spell, Spell)]

        if not all_spells:
            return []

        # Get all spell names
        spell_names = []
        for spell in all_spells:
            if isinstance(spell, Spell):
                spell_names.append(spell.name)

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(name, spell_names, n=5, cutoff=0.4)

        return suggestions

    def get_available_classes(self) -> list[str]:
        """Get list of all classes that have spells available.

        Returns:
            List of class names that can cast spells
        """
        spell_type = ContentType("spell")
        all_spells = self.omnidexer.get_all_by_type(spell_type)

        if not all_spells:
            return []

        classes = set()
        for spell in all_spells:
            if (
                isinstance(spell, Spell)
                and spell.classes
                and spell.classes.fromClassList
            ):
                for cls in spell.classes.fromClassList:
                    classes.add(cls.name.lower())

        return sorted(classes)

    def get_available_schools(self) -> list[str]:
        """Get list of all spell schools available.

        Returns:
            List of spell schools
        """
        spell_type = ContentType("spell")
        all_spells = self.omnidexer.get_all_by_type(spell_type)

        if not all_spells:
            return []

        schools = set()
        for spell in all_spells:
            if isinstance(spell, Spell):
                schools.add(spell.school.lower())

        return sorted(schools)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about available spells.

        Returns:
            Dictionary with spell statistics
        """
        spell_type = ContentType("spell")
        all_spells = self.omnidexer.get_all_by_type(spell_type)

        if not all_spells:
            return {"total": 0}

        stats: dict[str, Any] = {
            "total": len(all_spells),
            "by_level": {},
            "by_school": {},
            "by_source": {},
            "classes": self.get_available_classes(),
            "schools": self.get_available_schools(),
        }

        for spell in all_spells:
            if isinstance(spell, Spell):
                # Count by level
                spell_level = spell.level
                stats["by_level"][spell_level] = (
                    stats["by_level"].get(spell_level, 0) + 1
                )

                # Count by school
                school = spell.school.lower()
                stats["by_school"][school] = stats["by_school"].get(school, 0) + 1

                # Count by source
                if hasattr(spell.source, "abbreviation"):
                    source = spell.source.abbreviation
                    stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        return stats
