"""Pydantic implementations of encounter balancer models.

This module provides Pydantic BaseModel versions of the encounter balancer dataclasses,
adding validation, serialization, and enhanced type safety for MCP tools and APIs.

These models maintain API compatibility with the original dataclass implementations
while adding field validation and JSON serialization capabilities.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from studiorum.core.models.encounter_types import EncounterId
from studiorum.core.services.encounter_collector import EncounterGenerationResult

from .balancer import BalanceStrategy, OptimizationGoal


class BalanceMetrics(BaseModel):
    """Comprehensive encounter balance assessment metrics with validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    xp_accuracy: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How close to target XP (0.0-1.0)",
    )
    tactical_balance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Tactical variety and balance (0.0-1.0)",
    )
    action_economy_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Action economy balance (0.0-1.0)",
    )
    environmental_fit: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Environment suitability (0.0-1.0)",
    )
    narrative_alignment: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Story/theme alignment (0.0-1.0)",
    )
    overall_balance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weighted overall score (0.0-1.0)",
    )

    # Detailed breakdowns
    strengths: list[str] = Field(
        default_factory=list,
        description="Identified encounter strengths",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Identified encounter weaknesses",
    )
    optimization_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )

    @field_validator("strengths", "weaknesses", "optimization_suggestions")
    @classmethod
    def validate_string_lists(cls, v: list[str]) -> list[str]:
        """Validate that list items are non-empty strings.

        Args:
            v: List of strings to validate

        Returns:
            Validated list of strings

        Raises:
            ValueError: If any item is not a non-empty string
        """
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(
                    f"List item at index {i} must be a string, got: {type(item).__name__}"
                )
            if not item.strip():
                raise ValueError(
                    f"List item at index {i} cannot be empty or whitespace-only"
                )
        return v

    def calculate_overall_balance(self) -> None:
        """Calculate weighted overall balance score.

        Computes a weighted average of all balance metrics where:
        - XP accuracy: 30% weight (most important for game balance)
        - Tactical balance: 25% weight (combat variety and interest)
        - Action economy: 20% weight (turn-by-turn balance)
        - Environmental fit: 15% weight (world immersion)
        - Narrative alignment: 10% weight (story coherence)
        """
        self.overall_balance = (
            self.xp_accuracy * 0.3
            + self.tactical_balance * 0.25
            + self.action_economy_score * 0.2
            + self.environmental_fit * 0.15
            + self.narrative_alignment * 0.1
        )


class BalanceAnalysis(BaseModel):
    """Complete encounter balance analysis result with validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    encounter_id: EncounterId
    original_encounter: EncounterGenerationResult
    balanced_encounter: EncounterGenerationResult | None = Field(
        default=None,
        description="Rebalanced encounter, if rebalancing was performed",
    )
    metrics: BalanceMetrics
    strategy_used: BalanceStrategy
    optimization_goal: OptimizationGoal | None = Field(
        default=None,
        description="Optimization goal used, if any",
    )
    processing_time_ms: float = Field(
        ge=0.0,
        description="Time spent processing the analysis in milliseconds",
    )
    iterations_performed: int = Field(
        ge=0,
        description="Number of optimization iterations performed",
    )

    @property
    def improvement_gained(self) -> float:
        """Calculate balance improvement from original to balanced encounter.

        Returns:
            Balance score improvement (positive = better, negative = worse)
            Returns 0.0 if no balanced encounter was generated
        """
        if not self.balanced_encounter:
            return 0.0
        return (
            self.balanced_encounter.balance_score
            - self.original_encounter.balance_score
        )

    @field_validator("processing_time_ms")
    @classmethod
    def validate_processing_time(cls, v: float) -> float:
        """Validate processing time is reasonable for encounter balancing.

        Args:
            v: Processing time in milliseconds

        Returns:
            Validated processing time

        Raises:
            ValueError: If processing time is negative or unreasonably high
        """
        if v < 0:
            raise ValueError(f"Processing time cannot be negative, got: {v}ms")
        if v > 60_000:  # 60 seconds
            raise ValueError(f"Processing time seems unreasonably high: {v}ms (>60s)")
        return v

    @field_validator("iterations_performed")
    @classmethod
    def validate_iterations(cls, v: int) -> int:
        """Validate iteration count is reasonable for optimization.

        Args:
            v: Number of optimization iterations performed

        Returns:
            Validated iteration count

        Raises:
            ValueError: If iteration count is negative or excessive
        """
        if v < 0:
            raise ValueError(f"Iteration count cannot be negative, got: {v}")
        if v > 1000:
            raise ValueError(f"Too many iterations performed: {v} (max: 1000)")
        return v
