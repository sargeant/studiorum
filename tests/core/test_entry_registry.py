"""The entry type registry: which types are known, and what an unknown one does."""

import warnings

import pytest

from studiorum.core.entry_registry import (
    KNOWN_ENTRY_TYPES,
    EntryTypeRegistry,
    ValidationMode,
    get_registry,
    set_validation_mode,
)
from studiorum.core.exceptions import EntryProcessingWarning
from studiorum.core.models.entry_types import TYPED_ENTRY_TYPES
from studiorum.core.result import Error, Success


def test_known_types_cover_5etools_and_every_typed_entry() -> None:
    assert {"section", "abilityDc", "bonus", "statblock", "cell"} <= KNOWN_ENTRY_TYPES
    assert TYPED_ENTRY_TYPES <= KNOWN_ENTRY_TYPES
    assert {"text", "action", "spell", "creature"} <= TYPED_ENTRY_TYPES


def test_known_types_are_counted() -> None:
    registry = EntryTypeRegistry(ValidationMode.STRICT)

    for entry_type in ("section", "table", "table"):
        assert isinstance(registry.validate_entry_type(entry_type), Success)

    assert registry.entry_counts == {"section": 1, "table": 2}
    assert registry.unknown_types == set()


def test_an_unknown_type_fails_in_strict_mode() -> None:
    registry = EntryTypeRegistry(ValidationMode.STRICT)

    result = registry.validate_entry_type("unknownType")

    assert isinstance(result, Error)
    assert result.error.entry_type == "unknownType"
    assert registry.unknown_types == {"unknownType"}


def test_an_unknown_type_warns_in_permissive_mode() -> None:
    registry = EntryTypeRegistry(ValidationMode.PERMISSIVE)

    with pytest.warns(EntryProcessingWarning) as caught:
        result = registry.validate_entry_type(
            "unknownType", source="PHB", parent_name="Chapter 1"
        )

    assert isinstance(result, Success)
    message = str(caught[0].message)
    assert "unknownType" in message
    assert "PHB" in message
    assert "Chapter 1" in message
    assert registry.entry_counts["unknownType"] == 1


def test_an_unknown_type_passes_silently_in_silent_mode() -> None:
    registry = EntryTypeRegistry(ValidationMode.SILENT)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = registry.validate_entry_type("unknownType")

    assert isinstance(result, Success)
    assert registry.unknown_types == {"unknownType"}


def test_the_mode_can_be_overridden_per_call() -> None:
    registry = EntryTypeRegistry(ValidationMode.SILENT)

    result = registry.validate_entry_type(
        "unknownType", validation_mode=ValidationMode.STRICT
    )

    assert isinstance(result, Error)


def test_statistics_reset() -> None:
    registry = EntryTypeRegistry(ValidationMode.SILENT)
    registry.validate_entry_type("unknownType")

    registry.reset_statistics()

    assert not registry.entry_counts
    assert not registry.unknown_types


def test_the_global_registry_is_shared_and_its_mode_settable() -> None:
    assert get_registry() is get_registry()
    original = get_registry().validation_mode
    try:
        set_validation_mode(ValidationMode.STRICT)
        assert get_registry().validation_mode == ValidationMode.STRICT
    finally:
        set_validation_mode(original)
