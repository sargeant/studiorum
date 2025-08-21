"""Character progression models for the MCP character tools.

This module provides Pydantic models for character progression analysis,
building on the existing BaseContent architecture. Models include progression
data, analysis results, and character optimization data.

Key Features:
- CharacterProgressionData for comprehensive progression information
- LevelProgressionAnalysis for level-by-level progression details
- SpellProgressionData for spellcaster progression
- FeatAnalysis and MulticlassOption for character optimization
- Built on existing Pydantic patterns with computed fields
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, computed_field

from studiorum.core.models.base import Source
from studiorum.core.models.content import BaseContent


class SpellProgressionData(BaseModel):
    """Spell progression data for spellcasting classes."""

    spellcasting_ability: str | None = None
    caster_progression: str | None = None  # "full", "half", "third", "warlock", etc.
    cantrips_known: int | None = None
    spells_known: int | None = None
    spell_slots: dict[str, int] = Field(
        default_factory=dict
    )  # "1st": 4, "2nd": 3, etc.
    pact_slots: int | None = None  # For warlocks
    pact_slot_level: int | None = None  # For warlocks
    ritual_casting: bool = False
    spellbook: bool = False  # For wizards


class ClassFeatureData(BaseModel):
    """Individual class feature data."""

    name: str
    level: int
    description: str | None = None
    entries: list[Any] = Field(default_factory=list)
    subclass_feature: bool = False
    optional: bool = False


class LevelProgressionAnalysis(BaseModel):
    """Analysis of progression at a specific level."""

    level: int
    hit_dice: str
    hit_points_average: int
    proficiency_bonus: int
    features_gained: list[ClassFeatureData] = Field(default_factory=list)
    ability_score_improvement: bool = False
    spell_progression: SpellProgressionData | None = None

    @computed_field
    def total_features(self) -> int:
        """Total number of features at this level."""
        return len(self.features_gained)


class FeatAnalysis(BaseModel):
    """Analysis of feat options for a character."""

    feat: BaseContent
    prerequisite_met: bool = True
    prerequisites: list[str] = Field(default_factory=list)
    optimization_score: float = 0.0  # 0-10 scale for character build
    synergy_analysis: str | None = None
    recommended: bool = False


class MulticlassRequirement(BaseModel):
    """Requirement for multiclassing."""

    ability: str
    minimum_score: int
    description: str


class MulticlassOption(BaseModel):
    """Multiclass option analysis."""

    target_class: str
    source: Source
    requirements_met: bool
    requirements: list[MulticlassRequirement] = Field(default_factory=list)
    synergy_rating: float = 0.0  # 0-10 scale
    recommended_levels: list[int] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class CharacterProgressionData(BaseContent):
    """Comprehensive character progression data."""

    character_class: str = Field(..., alias="class")
    level: int
    subclass: str | None = None

    # Core progression data
    hit_dice: str
    proficiency_bonus: int
    class_features: list[ClassFeatureData] = Field(default_factory=list)
    subclass_features: list[ClassFeatureData] = Field(default_factory=list)

    # Spell progression (if applicable)
    spell_progression: SpellProgressionData | None = None

    # Level-by-level breakdown
    level_progression: list[LevelProgressionAnalysis] = Field(default_factory=list)

    # Analysis data (populated based on request parameters)
    analysis_type: str = "basic"
    eligible_feats: list[FeatAnalysis] = Field(default_factory=list)
    multiclass_options: list[MulticlassOption] = Field(default_factory=list)
    optimization_focus: str | None = None
    optimization_recommendations: list[str] = Field(default_factory=list)

    @computed_field
    def total_class_features(self) -> int:
        """Total number of class features."""
        return len(self.class_features)

    @computed_field
    def total_subclass_features(self) -> int:
        """Total number of subclass features."""
        return len(self.subclass_features)

    @computed_field
    def is_spellcaster(self) -> bool:
        """Whether this class is a spellcaster."""
        return self.spell_progression is not None

    @computed_field
    def next_asi_level(self) -> int | None:
        """Next level that grants an Ability Score Improvement."""
        # Standard ASI levels for most classes: 4, 8, 12, 16, 19
        # Fighters get additional at 6, 14
        # Rogues get additional at 10
        asi_levels = [4, 8, 12, 16, 19]

        # Add class-specific ASI levels
        if self.character_class.lower() == "fighter":
            asi_levels.extend([6, 14])
        elif self.character_class.lower() == "rogue":
            asi_levels.append(10)

        # Find next ASI level after current level
        for asi_level in sorted(asi_levels):
            if asi_level > self.level:
                return asi_level

        return None

    def get_features_at_level(self, target_level: int) -> list[ClassFeatureData]:
        """Get all features gained at a specific level."""
        features: list[ClassFeatureData] = []

        # Class features
        features.extend(
            feature for feature in self.class_features if feature.level == target_level
        )

        # Subclass features
        features.extend(
            feature
            for feature in self.subclass_features
            if feature.level == target_level
        )

        return features

    def get_spell_slots_at_level(self, target_level: int) -> dict[str, int]:
        """Get spell slots available at a specific level."""
        if not self.spell_progression:
            return {}

        # This would be populated from spell slot progression tables
        # For now, return current spell slots
        return self.spell_progression.spell_slots


class CharacterAnalysisRequest(BaseModel):
    """Request model for character progression analysis."""

    character_class: str
    level: int
    subclass: str | None = None
    analysis_type: str = "basic"
    include_feat_analysis: bool = False
    include_multiclass_options: bool = False
    optimization_focus: str | None = None
    sources: list[str] = Field(default_factory=list)


class CharacterAnalysisResponse(BaseModel):
    """Response model for character progression analysis."""

    progression_data: CharacterProgressionData
    performance_metrics: dict[str, Any] = Field(default_factory=dict)
    cached: bool = False
    sources_used: list[str] = Field(default_factory=list)

    @computed_field
    def analysis_summary(self) -> dict[str, Any]:
        """Summary of analysis performed."""
        return {
            "class": self.progression_data.character_class,
            "level": self.progression_data.level,
            "subclass": self.progression_data.subclass,
            "analysis_type": self.progression_data.analysis_type,
            "features_count": (
                len(self.progression_data.class_features)
                + len(self.progression_data.subclass_features)
            ),
            "is_spellcaster": self.progression_data.is_spellcaster,
            "eligible_feats": len(self.progression_data.eligible_feats),
            "multiclass_options": len(self.progression_data.multiclass_options),
            "next_asi_level": self.progression_data.next_asi_level,
        }


# Type aliases for clarity
FeatList = list[FeatAnalysis]
MulticlassList = list[MulticlassOption]
ProgressionAnalysis = CharacterProgressionData
