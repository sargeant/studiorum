"""Creature filtering models for advanced creature collection and filtering."""

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from .creatures import Creature


class CreatureSortMode(str, Enum):
    """Sorting modes for creature collections."""

    CR = "cr"  # Group by challenge rating (default)
    TYPE = "type"  # Group by creature type
    NAME = "name"  # Alphabetical
    SIZE = "size"  # Group by size category
    ALIGNMENT = "alignment"  # Group by alignment


class CreatureFilterCriteria(BaseModel):
    """Comprehensive criteria for filtering creatures with validation.

    This model supports both encounter building use cases (specific creature names) and
    DM reference use cases (CR/type-based filtering) with advanced filtering
    options for combat stats, special abilities, movement, and senses.
    """

    # Challenge Rating filtering (handle fractional values properly)
    min_cr: float | None = Field(
        None, ge=0, le=30, description="Minimum challenge rating"
    )
    max_cr: float | None = Field(
        None, ge=0, le=30, description="Maximum challenge rating"
    )
    cr_range: str | None = Field(
        None, description="CR range string (e.g., '1/4-5', '10+', '0')"
    )
    exclude_variable_cr: bool = Field(
        True, description="Exclude 'varies' CR by default"
    )

    # Type and Size filtering (handle actual 5e.tools structure)
    creature_types: list[str] | None = Field(
        None, description="Creature types (aberration, beast, etc.)"
    )
    creature_tags: list[str] | None = Field(
        None, description="Creature tags (demon, devil, aarakocra, etc.)"
    )
    sizes: list[str] | None = Field(
        None, description="Creature sizes (tiny, small, medium, etc.)"
    )
    alignments: list[str] | None = Field(None, description="Creature alignments")

    # Combat Stats filtering (handle complex AC/HP)
    min_ac: int | None = Field(
        None, ge=1, description="Minimum armor class (use base AC value)"
    )
    max_ac: int | None = Field(
        None, ge=1, description="Maximum armor class (use base AC value)"
    )
    min_hp: int | None = Field(
        None, ge=1, description="Minimum hit points (use average HP)"
    )
    max_hp: int | None = Field(
        None, ge=1, description="Maximum hit points (use average HP)"
    )

    # Damage Types and Resistances
    damage_immunities: list[str] | None = Field(
        None, description="Required damage immunities"
    )
    damage_resistances: list[str] | None = Field(
        None, description="Required damage resistances"
    )
    damage_vulnerabilities: list[str] | None = Field(
        None, description="Required damage vulnerabilities"
    )
    condition_immunities: list[str] | None = Field(
        None, description="Required condition immunities"
    )

    # Special Abilities (clear boolean definitions)
    has_spellcasting: bool | None = Field(
        None, description="Filter by full spellcasting trait"
    )
    has_innate_spellcasting: bool | None = Field(
        None, description="Filter by innate spellcasting"
    )
    has_legendary_actions: bool | None = Field(
        None, description="Filter by legendary actions"
    )
    has_multiattack: bool | None = Field(
        None, description="Filter by multiattack action"
    )
    has_reactions: bool | None = Field(None, description="Filter by reaction abilities")
    has_bonus_actions: bool | None = Field(
        None, description="Filter by bonus action abilities"
    )

    # Movement and Senses (HIGH VALUE features)
    has_fly_speed: bool | None = Field(None, description="Filter by flying movement")
    has_swim_speed: bool | None = Field(None, description="Filter by swimming movement")
    has_climb_speed: bool | None = Field(
        None, description="Filter by climbing movement"
    )
    has_burrow_speed: bool | None = Field(
        None, description="Filter by burrowing movement"
    )
    has_darkvision: bool | None = Field(None, description="Filter by darkvision sense")
    has_blindsight: bool | None = Field(None, description="Filter by blindsight sense")
    has_tremorsense: bool | None = Field(None, description="Filter by tremorsense")
    has_truesight: bool | None = Field(None, description="Filter by truesight")

    # Communication and Skills
    speaks_language: list[str] | None = Field(
        None, description="Languages creature speaks"
    )
    has_skill: list[str] | None = Field(None, description="Skill proficiencies")

    # Standard filtering
    sources: list[str] | None = Field(None, description="Source book abbreviations")
    creature_names: list[str] | None = Field(
        None, description="Specific creature names to include"
    )

    @field_validator("cr_range")
    @classmethod
    def validate_cr_range(cls, v: str | None) -> str | None:
        """Validate CR range formats: '1/4-5', '10+', '0', '<1'."""
        if v is None:
            return v

        # Basic format validation - detailed parsing happens elsewhere
        if not any(c in v for c in ["-", "+", "<"]) and "/" not in v:
            # Single value like '5' or '1/4'
            try:
                cls._parse_single_cr(v)
            except ValueError:
                raise ValueError(f"Invalid CR value: {v}")

        return v.strip()

    @staticmethod
    def _parse_single_cr(cr_string: str) -> float:
        """Parse single CR value including fractions."""
        cr_string = cr_string.strip().lower()
        if cr_string in ["varies", "variable"]:
            raise ValueError("Variable CR not allowed in range")
        if "/" in cr_string:
            numerator, denominator = cr_string.split("/")
            return float(numerator) / float(denominator)
        return float(cr_string)

    @field_validator("creature_types")
    @classmethod
    def normalize_creature_types(cls, v: list[str] | None) -> list[str] | None:
        """Normalize creature type names to lowercase."""
        if v is None:
            return v
        return [ctype.strip().lower() for ctype in v if ctype.strip()]

    @field_validator("creature_tags")
    @classmethod
    def normalize_creature_tags(cls, v: list[str] | None) -> list[str] | None:
        """Normalize creature tag names to lowercase."""
        if v is None:
            return v
        return [tag.strip().lower() for tag in v if tag.strip()]

    @field_validator("sizes")
    @classmethod
    def normalize_sizes(cls, v: list[str] | None) -> list[str] | None:
        """Normalize size names to lowercase."""
        if v is None:
            return v

        # Map size abbreviations to full names
        size_map = {
            "t": "tiny",
            "s": "small",
            "m": "medium",
            "l": "large",
            "h": "huge",
            "g": "gargantuan",
        }

        normalized = []
        for size in v:
            size_clean = size.strip().lower()
            if size_clean in size_map:
                normalized.append(size_map[size_clean])
            else:
                normalized.append(size_clean)

        return normalized

    @field_validator("alignments")
    @classmethod
    def normalize_alignments(cls, v: list[str] | None) -> list[str] | None:
        """Normalize alignment names."""
        if v is None:
            return v
        return [alignment.strip().lower() for alignment in v if alignment.strip()]

    @field_validator(
        "damage_immunities", "damage_resistances", "damage_vulnerabilities"
    )
    @classmethod
    def normalize_damage_types(cls, v: list[str] | None) -> list[str] | None:
        """Normalize damage type names."""
        if v is None:
            return v
        return [dt.strip().lower() for dt in v if dt.strip()]

    @field_validator("condition_immunities")
    @classmethod
    def normalize_condition_immunities(cls, v: list[str] | None) -> list[str] | None:
        """Normalize condition immunity names."""
        if v is None:
            return v
        return [ci.strip().lower() for ci in v if ci.strip()]

    @field_validator("speaks_language")
    @classmethod
    def normalize_languages(cls, v: list[str] | None) -> list[str] | None:
        """Normalize language names."""
        if v is None:
            return v
        return [lang.strip().lower() for lang in v if lang.strip()]

    @field_validator("has_skill")
    @classmethod
    def normalize_skills(cls, v: list[str] | None) -> list[str] | None:
        """Normalize skill names."""
        if v is None:
            return v
        return [skill.strip().lower() for skill in v if skill.strip()]

    @field_validator("sources")
    @classmethod
    def normalize_sources(cls, v: list[str] | None) -> list[str] | None:
        """Normalize source abbreviations to uppercase."""
        if v is None:
            return v
        return [src.strip().upper() for src in v if src.strip()]

    @field_validator("creature_names")
    @classmethod
    def normalize_creature_names(cls, v: list[str] | None) -> list[str] | None:
        """Normalize creature names for consistent matching."""
        if v is None:
            return v
        return [name.strip() for name in v if name.strip()]

    def model_post_init(self, __context: dict | None = None) -> None:
        """Validate logical consistency of filter criteria."""
        # Check CR range consistency
        if (
            self.min_cr is not None
            and self.max_cr is not None
            and self.min_cr > self.max_cr
        ):
            raise ValueError("min_cr cannot be greater than max_cr")

        # Check AC range consistency
        if (
            self.min_ac is not None
            and self.max_ac is not None
            and self.min_ac > self.max_ac
        ):
            raise ValueError("min_ac cannot be greater than max_ac")

        # Check HP range consistency
        if (
            self.min_hp is not None
            and self.max_hp is not None
            and self.min_hp > self.max_hp
        ):
            raise ValueError("min_hp cannot be greater than max_hp")

        # Validate that at least one filtering criterion is provided
        has_criteria = any(
            [
                self.min_cr is not None,
                self.max_cr is not None,
                self.cr_range is not None,
                self.creature_types is not None,
                self.creature_tags is not None,
                self.sizes is not None,
                self.alignments is not None,
                self.min_ac is not None,
                self.max_ac is not None,
                self.min_hp is not None,
                self.max_hp is not None,
                self.damage_immunities is not None,
                self.damage_resistances is not None,
                self.damage_vulnerabilities is not None,
                self.condition_immunities is not None,
                self.has_spellcasting is not None,
                self.has_innate_spellcasting is not None,
                self.has_legendary_actions is not None,
                self.has_multiattack is not None,
                self.has_reactions is not None,
                self.has_bonus_actions is not None,
                self.has_fly_speed is not None,
                self.has_swim_speed is not None,
                self.has_climb_speed is not None,
                self.has_burrow_speed is not None,
                self.has_darkvision is not None,
                self.has_blindsight is not None,
                self.has_tremorsense is not None,
                self.has_truesight is not None,
                self.speaks_language is not None,
                self.has_skill is not None,
                self.sources is not None,
                self.creature_names is not None,
            ]
        )

        if not has_criteria:
            raise ValueError("At least one filtering criterion must be provided")

    def is_name_only_filter(self) -> bool:
        """Check if this is a name-only filter (encounter building use case).

        Returns:
            True if only creature names are specified
        """
        return self.creature_names is not None and all(
            criterion is None or (isinstance(criterion, bool) and not criterion)
            for attr, criterion in self.__dict__.items()
            if attr not in {"creature_names", "exclude_variable_cr"}
        )

    def matches_creature_type(
        self, creature_type: str, creature_tags: list[str] | None = None
    ) -> bool:
        """Check if a creature type/tags match the filter criteria.

        Args:
            creature_type: The main creature type
            creature_tags: Optional creature tags

        Returns:
            True if the creature type/tags match the criteria
        """
        # Check main type filtering
        if self.creature_types is not None:
            if creature_type.lower() not in self.creature_types:
                return False

        # Check tag filtering
        if self.creature_tags is not None and creature_tags is not None:
            creature_tags_lower = [tag.lower() for tag in creature_tags]
            if not any(tag in creature_tags_lower for tag in self.creature_tags):
                return False

        return True

    def matches_size(self, size: str | list[str]) -> bool:
        """Check if a creature size matches the filter criteria.

        Args:
            size: The creature size to check (string or list of strings)

        Returns:
            True if the size matches the criteria
        """
        if self.sizes is None:
            return True  # No size filtering

        # Handle both string and list formats
        if isinstance(size, list):
            if not size:
                return False
            size_str = size[0]  # Take the first size if multiple
        else:
            size_str = size

        # Normalize the input size using the same mapping as the validator
        size_map = {
            "t": "tiny",
            "s": "small",
            "m": "medium",
            "l": "large",
            "h": "huge",
            "g": "gargantuan",
        }

        size_clean = size_str.strip().lower()
        normalized_size = size_map.get(size_clean, size_clean)

        return normalized_size in self.sizes


class CreatureCollectionResult(BaseModel):
    """Result of creature collection operation with metadata."""

    creatures: list = Field(default_factory=list, description="Collected creatures")
    total_count: int = Field(0, description="Total number of creatures collected")
    matched_count: int = Field(
        0, description="Number of creatures that matched the criteria"
    )
    total_available: int = Field(
        0, description="Total number of creatures available to search"
    )
    criteria_used: "CreatureFilterCriteria | None" = Field(
        None, description="Filter criteria used for this collection"
    )
    search_time_ms: int = Field(
        0, description="Time taken for the search in milliseconds"
    )
    by_cr: dict[str, int] = Field(
        default_factory=dict, description="Count by challenge rating"
    )
    by_type: dict[str, int] = Field(
        default_factory=dict, description="Count by creature type"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="Source books used"
    )
    unresolved_names: list[str] = Field(
        default_factory=list, description="Creature names that couldn't be resolved"
    )
    suggestions: dict[str, list[str]] = Field(
        default_factory=dict, description="Suggestions for unresolved names"
    )

    def add_creature(self, creature: "Creature", source: str | None = None) -> None:
        """Add a creature to the collection with metadata tracking."""
        self.creatures.append(creature)
        self.total_count += 1
        self.matched_count += 1

        # Track by CR
        cr_str = str(getattr(creature, "cr", "unknown"))
        self.by_cr[cr_str] = self.by_cr.get(cr_str, 0) + 1

        # Track by type
        creature_type = getattr(creature, "type", "unknown")
        if isinstance(creature_type, dict):
            type_str = creature_type.get("type", "unknown")
        else:
            type_str = str(creature_type)
        self.by_type[type_str] = self.by_type.get(type_str, 0) + 1

        # Track sources
        if source and source not in self.sources_used:
            self.sources_used.append(source)

    def add_unresolved(self, name: str, suggestions: list[str] | None = None) -> None:
        """Add an unresolved creature name with optional suggestions."""
        if name not in self.unresolved_names:
            self.unresolved_names.append(name)

        if suggestions:
            self.suggestions[name] = suggestions

    def get_cr_summary(self) -> str:
        """Get a formatted summary of creatures by challenge rating."""
        if not self.by_cr:
            return "No creatures collected"

        # Sort CRs logically (0, 1/8, 1/4, 1/2, 1, 2, etc.)
        def cr_sort_key(cr_str: str) -> tuple[float, str]:
            try:
                if "/" in cr_str:
                    num, den = cr_str.split("/")
                    return (float(num) / float(den), cr_str)
                else:
                    return (float(cr_str), cr_str)
            except (ValueError, ZeroDivisionError):
                return (999.0, cr_str)  # Put unknown CRs at the end

        sorted_crs = sorted(self.by_cr.keys(), key=cr_sort_key)

        parts = []
        for cr in sorted_crs:
            count = self.by_cr[cr]
            parts.append(f"CR {cr}: {count}")

        return ", ".join(parts)

    def get_type_summary(self) -> str:
        """Get a formatted summary of creatures by type."""
        if not self.by_type:
            return "No creatures collected"

        parts = []
        for creature_type in sorted(self.by_type.keys()):
            count = self.by_type[creature_type]
            parts.append(f"{creature_type.title()}: {count}")

        return ", ".join(parts)
