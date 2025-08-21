"""Spell filtering models for advanced spell collection and filtering."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from .spells import Spell


class SpellFilterCriteria(BaseModel):
    """Comprehensive criteria for filtering spells with validation.

    This model supports both wizard use cases (specific spell names) and
    cleric use cases (class/level-based filtering) with advanced filtering
    options for components, schools, damage types, and more.
    """

    # Level filtering
    min_level: int | None = Field(
        None, ge=0, le=9, description="Minimum spell level (0-9)"
    )
    max_level: int | None = Field(
        None, ge=0, le=9, description="Maximum spell level (0-9)"
    )
    levels: list[int] | None = Field(
        None, description="Specific spell levels to include"
    )

    # Class filtering
    classes: list[str] | None = Field(
        None, description="Spellcaster classes (wizard, cleric, etc.)"
    )
    include_optional: bool = Field(
        False, description="Include optional/variant class spells"
    )

    # School filtering
    schools: list[str] | None = Field(
        None, description="Schools of magic (evocation, abjuration, etc.)"
    )

    # Component filtering
    has_verbal: bool | None = Field(
        None, description="Filter by verbal component requirement"
    )
    has_somatic: bool | None = Field(
        None, description="Filter by somatic component requirement"
    )
    has_material: bool | None = Field(
        None, description="Filter by material component requirement"
    )
    no_material: bool = Field(
        False, description="Exclude spells with material components"
    )
    concentration: bool | None = Field(
        None, description="Filter by concentration requirement"
    )
    ritual: bool | None = Field(None, description="Filter by ritual casting capability")

    # Combat filtering
    damage_types: list[str] | None = Field(
        None, description="Damage types inflicted by spell"
    )
    saving_throws: list[str] | None = Field(
        None, description="Required saving throw types"
    )
    attack_spells: bool | None = Field(
        None, description="Filter for spells with attack rolls"
    )

    # Source filtering
    sources: list[str] | None = Field(None, description="Source book abbreviations")

    # Name filtering (for wizard use case)
    spell_names: list[str] | None = Field(
        None, description="Specific spell names to include"
    )

    @field_validator("levels")
    @classmethod
    def validate_levels(cls, v: list[int] | None) -> list[int] | None:
        """Validate spell levels are in valid range."""
        if v is None:
            return v

        for level in v:
            if level < 0 or level > 9:
                raise ValueError(f"Spell level must be 0-9, got {level}")

        return sorted(list(set(v)))  # Remove duplicates and sort

    @field_validator("min_level", "max_level")
    @classmethod
    def validate_level_range(cls, v: int | None) -> int | None:
        """Validate individual level values."""
        if v is not None and (v < 0 or v > 9):
            raise ValueError(f"Spell level must be 0-9, got {v}")
        return v

    @field_validator("classes")
    @classmethod
    def normalize_classes(cls, v: list[str] | None) -> list[str] | None:
        """Normalize class names to lowercase."""
        if v is None:
            return v
        return [cls_name.strip().lower() for cls_name in v if cls_name.strip()]

    @field_validator("schools")
    @classmethod
    def normalize_schools(cls, v: list[str] | None) -> list[str] | None:
        """Normalize school names to lowercase."""
        if v is None:
            return v

        # Map common abbreviations to full names
        school_map = {
            "a": "abjuration",
            "c": "conjuration",
            "d": "divination",
            "e": "enchantment",
            "v": "evocation",
            "i": "illusion",
            "n": "necromancy",
            "t": "transmutation",
        }

        normalized = []
        for school in v:
            school_clean = school.strip().lower()
            if school_clean in school_map:
                normalized.append(school_map[school_clean])
            else:
                normalized.append(school_clean)

        return normalized

    @field_validator("damage_types")
    @classmethod
    def normalize_damage_types(cls, v: list[str] | None) -> list[str] | None:
        """Normalize damage type names."""
        if v is None:
            return v
        return [dt.strip().lower() for dt in v if dt.strip()]

    @field_validator("saving_throws")
    @classmethod
    def normalize_saving_throws(cls, v: list[str] | None) -> list[str] | None:
        """Normalize saving throw names."""
        if v is None:
            return v

        # Map common abbreviations to full names
        save_map = {
            "str": "strength",
            "dex": "dexterity",
            "con": "constitution",
            "int": "intelligence",
            "wis": "wisdom",
            "cha": "charisma",
        }

        normalized = []
        for save in v:
            save_clean = save.strip().lower()
            if save_clean in save_map:
                normalized.append(save_map[save_clean])
            else:
                normalized.append(save_clean)

        return normalized

    @field_validator("sources")
    @classmethod
    def normalize_sources(cls, v: list[str] | None) -> list[str] | None:
        """Normalize source abbreviations to uppercase."""
        if v is None:
            return v
        return [src.strip().upper() for src in v if src.strip()]

    @field_validator("spell_names")
    @classmethod
    def normalize_spell_names(cls, v: list[str] | None) -> list[str] | None:
        """Normalize spell names for consistent matching."""
        if v is None:
            return v
        return [name.strip() for name in v if name.strip()]

    def model_post_init(self, __context: dict | None = None) -> None:
        """Validate logical consistency of filter criteria."""
        # Check level range consistency
        if (
            self.min_level is not None
            and self.max_level is not None
            and self.min_level > self.max_level
        ):
            raise ValueError("min_level cannot be greater than max_level")

        # Check conflicting material component filters
        if self.has_material is True and self.no_material is True:
            raise ValueError("Cannot require material components and exclude them")

        # Validate that at least one filtering criterion is provided
        has_criteria = any(
            [
                self.min_level is not None,
                self.max_level is not None,
                self.levels is not None,
                self.classes is not None,
                self.schools is not None,
                self.has_verbal is not None,
                self.has_somatic is not None,
                self.has_material is not None,
                self.no_material is True,
                self.concentration is not None,
                self.ritual is not None,
                self.damage_types is not None,
                self.saving_throws is not None,
                self.attack_spells is not None,
                self.sources is not None,
                self.spell_names is not None,
            ]
        )

        if not has_criteria:
            raise ValueError("At least one filtering criterion must be provided")

    def get_effective_levels(self) -> list[int] | None:
        """Get the effective list of levels to filter by.

        Returns:
            List of spell levels or None if no level filtering
        """
        if self.levels is not None:
            return self.levels

        if self.min_level is not None or self.max_level is not None:
            min_lvl = self.min_level if self.min_level is not None else 0
            max_lvl = self.max_level if self.max_level is not None else 9
            return list(range(min_lvl, max_lvl + 1))

        return None

    def matches_spell_level(self, spell_level: int) -> bool:
        """Check if a spell level matches the filter criteria.

        Args:
            spell_level: The spell level to check (0-9)

        Returns:
            True if the spell level matches the criteria
        """
        effective_levels = self.get_effective_levels()
        if effective_levels is None:
            return True  # No level filtering

        return spell_level in effective_levels

    def matches_spell_school(self, school: str) -> bool:
        """Check if a spell school matches the filter criteria.

        Args:
            school: The spell school to check

        Returns:
            True if the school matches the criteria
        """
        if self.schools is None:
            return True  # No school filtering

        return school.lower() in self.schools

    def is_name_only_filter(self) -> bool:
        """Check if this is a name-only filter (wizard use case).

        Returns:
            True if only spell names are specified
        """
        return self.spell_names is not None and all(
            criterion is None or (isinstance(criterion, bool) and not criterion)
            for attr, criterion in self.__dict__.items()
            if attr != "spell_names"
        )


class SpellCollectionResult(BaseModel):
    """Result of spell collection operation with metadata."""

    spells: list = Field(default_factory=list, description="Collected spells")
    total_count: int = Field(0, description="Total number of spells collected")
    by_level: dict[int, int] = Field(
        default_factory=dict, description="Count by spell level"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="Source books used"
    )
    unresolved_names: list[str] = Field(
        default_factory=list, description="Spell names that couldn't be resolved"
    )
    suggestions: dict[str, list[str]] = Field(
        default_factory=dict, description="Suggestions for unresolved names"
    )

    def add_spell(self, spell: "Spell", source: str | None = None) -> None:
        """Add a spell to the collection with metadata tracking."""
        self.spells.append(spell)
        self.total_count += 1

        # Track by level
        spell_level = getattr(spell, "level", 0)
        self.by_level[spell_level] = self.by_level.get(spell_level, 0) + 1

        # Track sources
        if source and source not in self.sources_used:
            self.sources_used.append(source)

    def add_unresolved(self, name: str, suggestions: list[str] | None = None) -> None:
        """Add an unresolved spell name with optional suggestions."""
        if name not in self.unresolved_names:
            self.unresolved_names.append(name)

        if suggestions:
            self.suggestions[name] = suggestions

    def get_level_summary(self) -> str:
        """Get a formatted summary of spells by level."""
        if not self.by_level:
            return "No spells collected"

        parts = []
        for level in sorted(self.by_level.keys()):
            count = self.by_level[level]
            level_name = "Cantrips" if level == 0 else f"Level {level}"
            parts.append(f"{level_name}: {count}")

        return ", ".join(parts)
