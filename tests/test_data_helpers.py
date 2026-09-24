"""Helper functions for data-dependent tests."""

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


def _is_full_data_opted_in() -> bool:
    import os

    return os.environ.get("STUDIORUM_TEST_FULL_DATA", "").lower() in (
        "1",
        "true",
        "yes",
    )


def _has_full_dataset_available(min_file_threshold: int = 50) -> bool:
    """Whether a full 5etools data directory is on this machine.

    Looks at $STUDIORUM_5ETOOLS_DIR (default ~/Code/5etools-src) and counts its
    data files without loading them.
    """
    import os
    from pathlib import Path

    from studiorum.core.loaders.data_dir import DataDir

    root = Path(
        os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
    )
    data_dir = DataDir(root / "data")
    return data_dir.root.is_dir() and len(data_dir.entity_files()) >= min_file_threshold


def requires_full_dataset(
    required_sources: list[str] | None = None,
    min_file_threshold: int = 50,
) -> pytest.MarkDecorator:
    """Mark test as requiring the full 5e dataset (beyond SRD/test-data).

    - Intent: requires STUDIORUM_TEST_FULL_DATA to be set (used by make test-full-data)
    - Availability: a 5etools checkout at $STUDIORUM_5ETOOLS_DIR or ~/Code/5etools-src

    Args:
        required_sources: Deprecated/ignored (kept for compatibility)
        min_file_threshold: Minimum number of data files across types to treat as "full"
    """
    opted_in = _is_full_data_opted_in()
    available = _has_full_dataset_available(min_file_threshold)

    return pytest.mark.skipif(
        not (opted_in and available),
        reason=(
            "Requires the full 5e dataset. Run 'make test-full-data' with a 5etools "
            "checkout at $STUDIORUM_5ETOOLS_DIR (default ~/Code/5etools-src)."
        ),
    )


def requires_full_5etools_data(
    required_sources: list[str] | None = None,
) -> pytest.MarkDecorator:
    """Deprecated: prefer requires_full_dataset().

    Kept for compatibility; delegates to requires_full_dataset() and ignores
    required_sources to avoid dataset branding in skip reasons.
    """
    return requires_full_dataset(required_sources=required_sources)


def _has_enough_creatures(min_count: int) -> bool:
    """Check if enough creatures are available (called during test execution)."""
    try:
        omnidexer = _get_omnidexer()
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
    opted_in = _is_full_data_opted_in()
    return pytest.mark.skipif(
        not opted_in,
        reason=(
            f"Requires at least {min_count} creatures from the full 5e dataset. "
            "Use 'make test-full-data' (sets STUDIORUM_TEST_FULL_DATA=1)."
        ),
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
