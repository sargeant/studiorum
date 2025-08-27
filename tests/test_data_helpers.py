"""Helper functions for data-dependent tests."""

from typing import Any

import pytest

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType


def get_available_sources() -> set[str]:
    """Get available data sources in the test environment.

    Returns:
        Set of source abbreviations available in test data
    """
    try:
        omnidexer = Omnidexer()
        omnidexer.source_manager.ensure_sources_ready_sync()
        omnidexer.load_all_data()

        # Get all creatures to check what sources are available
        creature_type = ContentType("creature")
        creatures = omnidexer.get_all_by_type(creature_type)

        sources = {creature.source.abbreviation.lower() for creature in creatures}
        return sources

    except Exception:
        return set()


def requires_full_5etools_data(
    required_sources: list[str] = None,
) -> pytest.MarkDecorator:
    """Mark test as requiring full 5etools dataset.

    Args:
        required_sources: Specific sources required (defaults to xphb, xmm, xdmg)

    Returns:
        pytest skip decorator
    """
    if required_sources is None:
        required_sources = ["xphb", "xmm", "xdmg"]

    available_sources = get_available_sources()
    required_lower = {src.lower() for src in required_sources}
    has_required = required_lower.issubset(available_sources)

    return pytest.mark.skipif(
        not has_required,
        reason=f"Requires full 5etools data with sources {required_sources}. "
        f"Available: {sorted(available_sources)}. "
        f"Run 'make test-full-data' to test with full dataset.",
    )


def requires_minimum_creatures(min_count: int = 10) -> pytest.MarkDecorator:
    """Mark test as requiring minimum number of creatures.

    Args:
        min_count: Minimum number of creatures needed

    Returns:
        pytest skip decorator
    """
    try:
        omnidexer = Omnidexer()
        omnidexer.source_manager.ensure_sources_ready_sync()
        omnidexer.load_all_data()

        creature_type = ContentType("creature")
        creatures = omnidexer.get_all_by_type(creature_type)
        has_enough = len(creatures) >= min_count

    except Exception:
        has_enough = False

    return pytest.mark.skipif(
        not has_enough,
        reason=f"Requires at least {min_count} creatures for meaningful testing. "
        f"Run 'make test-full-data' to test with full dataset.",
    )


def requires_content_type(content_type_name: str) -> pytest.MarkDecorator:
    """Mark test as requiring a specific content type to be registered.

    Args:
        content_type_name: Name of the content type

    Returns:
        pytest skip decorator
    """
    try:
        ContentType(content_type_name)
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
