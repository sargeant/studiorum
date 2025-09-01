"""Migration helpers for converting between dataclass and Pydantic models.

This module provides conversion utilities to migrate from the original dataclass
implementations to the new Pydantic models while maintaining API compatibility.
"""

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .balancer import (
        BalanceAnalysis as BalanceAnalysisDataclass,
        BalanceMetrics as BalanceMetricsDataclass,
    )
    from .balancer_pydantic import (
        BalanceAnalysis as BalanceAnalysisPydantic,
        BalanceMetrics as BalanceMetricsPydantic,
    )
    from .themes import (
        EnvironmentalProfile as EnvironmentalProfileDataclass,
        ThematicProfile as ThematicProfileDataclass,
    )
    from .themes_pydantic import (
        EnvironmentalProfile as EnvironmentalProfilePydantic,
        ThematicProfile as ThematicProfilePydantic,
    )


# Runtime imports to avoid circular dependencies
def _get_dataclass_types() -> tuple[type, type, type, type]:
    """Get dataclass types at runtime to avoid circular imports."""
    from .balancer import (
        BalanceAnalysis as BalanceAnalysisDataclass,
        BalanceMetrics as BalanceMetricsDataclass,
    )
    from .themes import (
        EnvironmentalProfile as EnvironmentalProfileDataclass,
        ThematicProfile as ThematicProfileDataclass,
    )

    return (
        EnvironmentalProfileDataclass,
        ThematicProfileDataclass,
        BalanceMetricsDataclass,
        BalanceAnalysisDataclass,
    )


def _get_pydantic_types() -> tuple[type, type, type, type]:
    """Get Pydantic types at runtime to avoid circular imports."""
    from .balancer_pydantic import (
        BalanceAnalysis as BalanceAnalysisPydantic,
        BalanceMetrics as BalanceMetricsPydantic,
    )
    from .themes_pydantic import (
        EnvironmentalProfile as EnvironmentalProfilePydantic,
        ThematicProfile as ThematicProfilePydantic,
    )

    return (
        EnvironmentalProfilePydantic,
        ThematicProfilePydantic,
        BalanceMetricsPydantic,
        BalanceAnalysisPydantic,
    )


# Environmental Profile Conversions


def environmental_profile_to_pydantic(
    dataclass_profile: "EnvironmentalProfileDataclass",
) -> "EnvironmentalProfilePydantic":
    """Convert dataclass EnvironmentalProfile to Pydantic version.

    Args:
        dataclass_profile: Original dataclass environmental profile

    Returns:
        Equivalent Pydantic environmental profile with validation

    Raises:
        ValueError: If profile contains invalid data that fails Pydantic validation
    """
    from .themes_pydantic import EnvironmentalProfile as EnvironmentalProfilePydantic

    if not dataclass_profile:
        raise ValueError("Environmental profile cannot be None")

    return EnvironmentalProfilePydantic(
        environment=dataclass_profile.environment,
        climate=dataclass_profile.climate,
        terrain_difficulty=dataclass_profile.terrain_difficulty,
        lighting=dataclass_profile.lighting,
        weather=dataclass_profile.weather,
        visibility_range=dataclass_profile.visibility_range,
        movement_penalty=dataclass_profile.movement_penalty,
        stealth_modifier=dataclass_profile.stealth_modifier,
        sound_propagation=dataclass_profile.sound_propagation,
        creature_affinities=dataclass_profile.creature_affinities,
    )


def environmental_profile_to_dataclass(
    pydantic_profile: "EnvironmentalProfilePydantic",
) -> "EnvironmentalProfileDataclass":
    """Convert Pydantic EnvironmentalProfile to dataclass version.

    Args:
        pydantic_profile: Validated Pydantic environmental profile

    Returns:
        Equivalent dataclass environmental profile

    Raises:
        ValueError: If profile is None or invalid
    """
    from .themes import (
        EnvironmentalProfile as EnvironmentalProfileDataclass,
        EnvironmentType,
    )

    if not pydantic_profile:
        raise ValueError("Environmental profile cannot be None")

    # Convert string back to enum since Pydantic stores enum values as strings
    # First check if it's already an enum
    if isinstance(pydantic_profile.environment, EnvironmentType):
        environment_enum = pydantic_profile.environment
    else:
        try:
            environment_enum = EnvironmentType(pydantic_profile.environment)
        except (ValueError, TypeError):
            environment_enum = EnvironmentType.FOREST  # Fallback

    return EnvironmentalProfileDataclass(
        environment=environment_enum,
        climate=pydantic_profile.climate,
        terrain_difficulty=pydantic_profile.terrain_difficulty,
        lighting=pydantic_profile.lighting,
        weather=pydantic_profile.weather,
        visibility_range=pydantic_profile.visibility_range,
        movement_penalty=pydantic_profile.movement_penalty,
        stealth_modifier=pydantic_profile.stealth_modifier,
        sound_propagation=pydantic_profile.sound_propagation,
        creature_affinities=pydantic_profile.creature_affinities,
    )


# Thematic Profile Conversions


def thematic_profile_to_pydantic(
    dataclass_profile: "ThematicProfileDataclass",
) -> "ThematicProfilePydantic":
    """Convert dataclass ThematicProfile to Pydantic version.

    Args:
        dataclass_profile: Original dataclass thematic profile

    Returns:
        Equivalent Pydantic thematic profile with validation

    Raises:
        ValueError: If profile contains invalid data that fails Pydantic validation
    """
    from .themes_pydantic import ThematicProfile as ThematicProfilePydantic

    if not dataclass_profile:
        raise ValueError("Thematic profile cannot be None")

    return ThematicProfilePydantic(
        theme=dataclass_profile.theme,
        intensity=dataclass_profile.intensity,
        allow_mixed=dataclass_profile.allow_mixed,
        narrative_context=dataclass_profile.narrative_context,
    )


def thematic_profile_to_dataclass(
    pydantic_profile: "ThematicProfilePydantic",
) -> "ThematicProfileDataclass":
    """Convert Pydantic ThematicProfile to dataclass version.

    Args:
        pydantic_profile: Validated Pydantic thematic profile

    Returns:
        Equivalent dataclass thematic profile

    Raises:
        ValueError: If profile is None or invalid
    """
    from .themes import EncounterTheme, ThematicProfile as ThematicProfileDataclass

    if not pydantic_profile:
        raise ValueError("Thematic profile cannot be None")

    # Convert string back to enum since Pydantic stores enum values as strings
    # First check if it's already an enum
    if isinstance(pydantic_profile.theme, EncounterTheme):
        theme_enum = pydantic_profile.theme
    else:
        try:
            theme_enum = EncounterTheme(pydantic_profile.theme)
        except (ValueError, TypeError):
            theme_enum = EncounterTheme.BEAST_WILDERNESS  # Fallback

    return ThematicProfileDataclass(
        theme=theme_enum,
        intensity=pydantic_profile.intensity,
        allow_mixed=pydantic_profile.allow_mixed,
        narrative_context=pydantic_profile.narrative_context,
    )


# Balance Metrics Conversions


def balance_metrics_to_pydantic(
    dataclass_metrics: "BalanceMetricsDataclass",
) -> "BalanceMetricsPydantic":
    """Convert dataclass BalanceMetrics to Pydantic version.

    Args:
        dataclass_metrics: Original dataclass balance metrics

    Returns:
        Equivalent Pydantic balance metrics with validation

    Raises:
        ValueError: If metrics contain invalid data that fails Pydantic validation
    """
    from .balancer_pydantic import BalanceMetrics as BalanceMetricsPydantic

    if not dataclass_metrics:
        raise ValueError("Balance metrics cannot be None")

    return BalanceMetricsPydantic(
        xp_accuracy=dataclass_metrics.xp_accuracy,
        tactical_balance=dataclass_metrics.tactical_balance,
        action_economy_score=dataclass_metrics.action_economy_score,
        environmental_fit=dataclass_metrics.environmental_fit,
        narrative_alignment=dataclass_metrics.narrative_alignment,
        overall_balance=dataclass_metrics.overall_balance,
        strengths=dataclass_metrics.strengths,
        weaknesses=dataclass_metrics.weaknesses,
        optimization_suggestions=dataclass_metrics.optimization_suggestions,
    )


def balance_metrics_to_dataclass(
    pydantic_metrics: "BalanceMetricsPydantic",
) -> "BalanceMetricsDataclass":
    """Convert Pydantic BalanceMetrics to dataclass version.

    Args:
        pydantic_metrics: Validated Pydantic balance metrics

    Returns:
        Equivalent dataclass balance metrics

    Raises:
        ValueError: If metrics are None or invalid
    """
    from .balancer import BalanceMetrics as BalanceMetricsDataclass

    if not pydantic_metrics:
        raise ValueError("Balance metrics cannot be None")

    return BalanceMetricsDataclass(
        xp_accuracy=pydantic_metrics.xp_accuracy,
        tactical_balance=pydantic_metrics.tactical_balance,
        action_economy_score=pydantic_metrics.action_economy_score,
        environmental_fit=pydantic_metrics.environmental_fit,
        narrative_alignment=pydantic_metrics.narrative_alignment,
        overall_balance=pydantic_metrics.overall_balance,
        strengths=pydantic_metrics.strengths,
        weaknesses=pydantic_metrics.weaknesses,
        optimization_suggestions=pydantic_metrics.optimization_suggestions,
    )


# Balance Analysis Conversions


def balance_analysis_to_pydantic(
    dataclass_analysis: "BalanceAnalysisDataclass",
) -> "BalanceAnalysisPydantic":
    """Convert dataclass BalanceAnalysis to Pydantic version.

    Args:
        dataclass_analysis: Original dataclass balance analysis

    Returns:
        Equivalent Pydantic balance analysis with validation

    Raises:
        ValueError: If analysis contains invalid data that fails Pydantic validation
    """
    from .balancer_pydantic import BalanceAnalysis as BalanceAnalysisPydantic

    if not dataclass_analysis:
        raise ValueError("Balance analysis cannot be None")

    return BalanceAnalysisPydantic(
        encounter_id=dataclass_analysis.encounter_id,
        original_encounter=dataclass_analysis.original_encounter,
        balanced_encounter=dataclass_analysis.balanced_encounter,
        metrics=balance_metrics_to_pydantic(dataclass_analysis.metrics),
        strategy_used=dataclass_analysis.strategy_used,
        optimization_goal=dataclass_analysis.optimization_goal,
        processing_time_ms=dataclass_analysis.processing_time_ms,
        iterations_performed=dataclass_analysis.iterations_performed,
    )


def balance_analysis_to_dataclass(
    pydantic_analysis: "BalanceAnalysisPydantic",
) -> "BalanceAnalysisDataclass":
    """Convert Pydantic BalanceAnalysis to dataclass version.

    Args:
        pydantic_analysis: Validated Pydantic balance analysis

    Returns:
        Equivalent dataclass balance analysis

    Raises:
        ValueError: If analysis is None or invalid
    """
    from .balancer import BalanceAnalysis as BalanceAnalysisDataclass

    if not pydantic_analysis:
        raise ValueError("Balance analysis cannot be None")

    return BalanceAnalysisDataclass(
        encounter_id=pydantic_analysis.encounter_id,
        original_encounter=pydantic_analysis.original_encounter,
        balanced_encounter=pydantic_analysis.balanced_encounter,
        metrics=balance_metrics_to_dataclass(pydantic_analysis.metrics),
        strategy_used=pydantic_analysis.strategy_used,
        optimization_goal=pydantic_analysis.optimization_goal,
        processing_time_ms=pydantic_analysis.processing_time_ms,
        iterations_performed=pydantic_analysis.iterations_performed,
    )


# Utility functions for JSON serialization


def serialize_environmental_profile(
    profile: "EnvironmentalProfileDataclass",
) -> dict[str, str | int | float | bool | dict | list]:
    """Serialize EnvironmentalProfile to JSON-compatible dict.

    Args:
        profile: Dataclass environmental profile to serialize

    Returns:
        JSON-serializable dictionary representation

    Raises:
        ValueError: If profile is invalid or serialization fails
    """
    if not profile:
        raise ValueError("Cannot serialize None profile")

    pydantic_profile = environmental_profile_to_pydantic(profile)
    return pydantic_profile.model_dump()


def deserialize_environmental_profile(
    data: dict[str, str | int | float | bool | dict | list],
) -> "EnvironmentalProfileDataclass":
    """Deserialize EnvironmentalProfile from JSON-compatible dict.

    Args:
        data: Dictionary containing serialized environmental profile data

    Returns:
        Deserialized and validated environmental profile dataclass

    Raises:
        ValueError: If data is invalid or deserialization fails
    """
    from .themes_pydantic import EnvironmentalProfile as EnvironmentalProfilePydantic

    if not data:
        raise ValueError("Cannot deserialize empty data")

    pydantic_profile = EnvironmentalProfilePydantic.model_validate(data)
    return environmental_profile_to_dataclass(pydantic_profile)


def serialize_thematic_profile(
    profile: "ThematicProfileDataclass",
) -> dict[str, str | int | float | bool | dict | list]:
    """Serialize ThematicProfile to JSON-compatible dict.

    Args:
        profile: Dataclass thematic profile to serialize

    Returns:
        JSON-serializable dictionary representation

    Raises:
        ValueError: If profile is invalid or serialization fails
    """
    if not profile:
        raise ValueError("Cannot serialize None profile")

    pydantic_profile = thematic_profile_to_pydantic(profile)
    return pydantic_profile.model_dump()


def deserialize_thematic_profile(
    data: dict[str, str | int | float | bool | dict | list],
) -> "ThematicProfileDataclass":
    """Deserialize ThematicProfile from JSON-compatible dict.

    Args:
        data: Dictionary containing serialized thematic profile data

    Returns:
        Deserialized and validated thematic profile dataclass

    Raises:
        ValueError: If data is invalid or deserialization fails
    """
    from .themes_pydantic import ThematicProfile as ThematicProfilePydantic

    if not data:
        raise ValueError("Cannot deserialize empty data")

    pydantic_profile = ThematicProfilePydantic.model_validate(data)
    return thematic_profile_to_dataclass(pydantic_profile)


def serialize_balance_metrics(
    metrics: "BalanceMetricsDataclass",
) -> dict[str, str | int | float | bool | dict | list]:
    """Serialize BalanceMetrics to JSON-compatible dict.

    Args:
        metrics: Dataclass balance metrics to serialize

    Returns:
        JSON-serializable dictionary representation

    Raises:
        ValueError: If metrics are invalid or serialization fails
    """
    if not metrics:
        raise ValueError("Cannot serialize None metrics")

    pydantic_metrics = balance_metrics_to_pydantic(metrics)
    return pydantic_metrics.model_dump()


def deserialize_balance_metrics(
    data: dict[str, str | int | float | bool | dict | list],
) -> "BalanceMetricsDataclass":
    """Deserialize BalanceMetrics from JSON-compatible dict.

    Args:
        data: Dictionary containing serialized balance metrics data

    Returns:
        Deserialized and validated balance metrics dataclass

    Raises:
        ValueError: If data is invalid or deserialization fails
    """
    from .balancer_pydantic import BalanceMetrics as BalanceMetricsPydantic

    if not data:
        raise ValueError("Cannot deserialize empty data")

    pydantic_metrics = BalanceMetricsPydantic.model_validate(data)
    return balance_metrics_to_dataclass(pydantic_metrics)


def serialize_balance_analysis(
    analysis: "BalanceAnalysisDataclass",
) -> dict[str, str | int | float | bool | dict | list]:
    """Serialize BalanceAnalysis to JSON-compatible dict.

    Args:
        analysis: Dataclass balance analysis to serialize

    Returns:
        JSON-serializable dictionary representation

    Raises:
        ValueError: If analysis is invalid or serialization fails
    """
    if not analysis:
        raise ValueError("Cannot serialize None analysis")

    pydantic_analysis = balance_analysis_to_pydantic(analysis)
    return pydantic_analysis.model_dump()


def deserialize_balance_analysis(
    data: dict[str, str | int | float | bool | dict | list],
) -> "BalanceAnalysisDataclass":
    """Deserialize BalanceAnalysis from JSON-compatible dict.

    Args:
        data: Dictionary containing serialized balance analysis data

    Returns:
        Deserialized and validated balance analysis dataclass

    Raises:
        ValueError: If data is invalid or deserialization fails
    """
    from .balancer_pydantic import BalanceAnalysis as BalanceAnalysisPydantic

    if not data:
        raise ValueError("Cannot deserialize empty data")

    pydantic_analysis = BalanceAnalysisPydantic.model_validate(data)
    return balance_analysis_to_dataclass(pydantic_analysis)
