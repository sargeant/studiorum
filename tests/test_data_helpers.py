"""Helper functions for data-dependent tests."""

from typing import Any

import pytest


# Lazy imports to avoid slow collection
def _get_omnidexer():
    """Lazy omnidexer import and creation."""
    from studiorum.core.loaders.omnidexer import Omnidexer

    return Omnidexer()


def _get_content_type(name: str):
    """Lazy ContentType import."""
    from studiorum.core.models.content import ContentType

    return ContentType(name)


def get_available_sources() -> set[str]:
    """Get available data sources in the test environment.

    Returns:
        Set of source abbreviations available in test data
    """
    try:
        omnidexer = _get_omnidexer()
        omnidexer.source_manager.ensure_sources_ready_sync()
        omnidexer.load_all_data()

        # Get all creatures to check what sources are available
        creature_type = _get_content_type("creature")
        creatures = omnidexer.get_all_by_type(creature_type)

        sources = {creature.source.abbreviation.lower() for creature in creatures}
        return sources

    except Exception:
        return set()


def _has_sources(required_sources: list[str]) -> bool:
    """Check if required sources are available (called during test execution)."""
    available_sources = get_available_sources()
    required_lower = {src.lower() for src in required_sources}
    return required_lower.issubset(available_sources)


def requires_full_5etools_data(
    required_sources: list[str] = None,
) -> pytest.MarkDecorator:
    """Mark test as requiring full 5etools dataset.

    Args:
        required_sources: Specific sources required (defaults to xphb, xmm, xdmg)

    Returns:
        pytest skip decorator
    """
    import os

    if required_sources is None:
        required_sources = ["xphb", "xmm", "xdmg"]

    # Simple environment check - skip unless explicitly running full data tests
    # This avoids slow data loading during collection
    is_full_data_test = os.environ.get("STUDIORUM_TEST_FULL_DATA", "").lower() in (
        "1",
        "true",
        "yes",
    )

    return pytest.mark.skipif(
        not is_full_data_test,
        reason=f"Requires full 5etools data with sources {required_sources}. "
        f"Run 'make test-full-data' to test with full dataset (sets STUDIORUM_TEST_FULL_DATA=1).",
    )


def _has_enough_creatures(min_count: int) -> bool:
    """Check if enough creatures are available (called during test execution)."""
    try:
        omnidexer = _get_omnidexer()
        omnidexer.source_manager.ensure_sources_ready_sync()
        omnidexer.load_all_data()

        creature_type = _get_content_type("creature")
        creatures = omnidexer.get_all_by_type(creature_type)
        return len(creatures) >= min_count

    except Exception:
        return False


def requires_minimum_creatures(min_count: int = 10) -> pytest.MarkDecorator:
    """Mark test as requiring minimum number of creatures.

    Args:
        min_count: Minimum number of creatures needed

    Returns:
        pytest skip decorator
    """
    import os

    # Simple environment check - skip unless explicitly running full data tests
    # This avoids slow data loading during collection
    is_full_data_test = os.environ.get("STUDIORUM_TEST_FULL_DATA", "").lower() in (
        "1",
        "true",
        "yes",
    )

    return pytest.mark.skipif(
        not is_full_data_test,
        reason=f"Requires at least {min_count} creatures for meaningful testing. "
        f"Run 'make test-full-data' to test with full dataset (sets STUDIORUM_TEST_FULL_DATA=1).",
    )


def requires_content_type(content_type_name: str) -> pytest.MarkDecorator:
    """Mark test as requiring a specific content type to be registered.

    Args:
        content_type_name: Name of the content type

    Returns:
        pytest skip decorator
    """
    try:
        _get_content_type(content_type_name)
        has_type = True
    except ValueError:
        has_type = False

    return pytest.mark.skipif(
        not has_type,
        reason=f"ContentType '{content_type_name}' is not registered. "
        f"This feature may not be fully implemented yet.",
    )


def requires_latex_template() -> pytest.MarkDecorator:
    """Mark test as requiring DND-5e-LaTeX-Template.

    Returns:
        pytest skip decorator
    """
    import subprocess

    try:
        result = subprocess.run(
            ["kpsewhich", "DND-5e.cls"], capture_output=True, text=True, timeout=10
        )
        has_template = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        has_template = False

    return pytest.mark.skipif(
        not has_template,
        reason="DND-5e-LaTeX-Template not installed. "
        "Install with: pip install git+https://github.com/rpgtex/DND-5e-LaTeX-Template.git",
    )
