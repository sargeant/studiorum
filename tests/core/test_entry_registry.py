"""Tests for entry type registry and validation infrastructure."""

import warnings
from unittest.mock import patch

import pytest

from dnd5e.core.entry_registry import (
    EntryTypeCategory,
    EntryTypeRegistry,
    ValidationMode,
    get_registry,
    set_validation_mode,
)
from dnd5e.core.exceptions import (
    EntryProcessingWarning,
    EntryValidationError,
    MalformedEntryError,
    UnknownEntryTypeError,
)
from tests.test_helpers import reset_test_environment


class TestValidationMode:
    """Test ValidationMode enum."""

    def test_validation_modes_exist(self):
        """Test that all expected validation modes exist."""
        assert ValidationMode.STRICT.value == "strict"
        assert ValidationMode.PERMISSIVE.value == "permissive"
        assert ValidationMode.SILENT.value == "silent"


class TestEntryTypeCategory:
    """Test EntryTypeCategory enum."""

    def test_categories_exist(self):
        """Test that all expected categories exist."""
        categories = [
            EntryTypeCategory.RECURSIVE,
            EntryTypeCategory.BLOCK,
            EntryTypeCategory.INLINE,
            EntryTypeCategory.LIST_ITEM,
            EntryTypeCategory.EMBEDDED,
            EntryTypeCategory.MEDIA,
            EntryTypeCategory.MISC,
        ]
        assert len(categories) == 7


class TestEntryTypeRegistry:
    """Test EntryTypeRegistry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.registry = EntryTypeRegistry(ValidationMode.PERMISSIVE)

    def test_initialization(self):
        """Test registry initialization."""
        registry = EntryTypeRegistry(ValidationMode.STRICT)
        assert registry.validation_mode == ValidationMode.STRICT
        assert len(registry.known_types) > 0
        assert len(registry.unknown_types) == 0
        assert registry.statistics.total_entries == 0

    def test_known_types_comprehensive(self):
        """Test that registry contains expected known types from 5etools."""
        known_types = self.registry.known_types

        # Test some key types from each category
        recursive_types = {"entries", "section", "table", "inset", "variant"}
        assert recursive_types.issubset(known_types)

        block_types = {"abilityDc", "abilityAttackMod", "abilityGeneric"}
        assert block_types.issubset(known_types)

        inline_types = {"bonus", "dice", "actions", "attack"}
        assert inline_types.issubset(known_types)

        # Test total count is reasonable (should be 30+ types)
        assert len(known_types) >= 30

    def test_is_known_type(self):
        """Test is_known_type method."""
        assert self.registry.is_known_type("section")
        assert self.registry.is_known_type("table")
        assert self.registry.is_known_type("entries")
        assert not self.registry.is_known_type("unknownType")
        assert not self.registry.is_known_type("")

    def test_get_category(self):
        """Test get_category method."""
        assert self.registry.get_category("section") == EntryTypeCategory.RECURSIVE
        assert self.registry.get_category("abilityDc") == EntryTypeCategory.BLOCK
        assert self.registry.get_category("bonus") == EntryTypeCategory.INLINE
        assert self.registry.get_category("item") == EntryTypeCategory.LIST_ITEM
        assert self.registry.get_category("image") == EntryTypeCategory.MEDIA
        assert self.registry.get_category("unknownType") is None

    def test_validate_entry_type_known(self):
        """Test validation of known entry types."""
        from dnd5e.core.entry_registry import ValidationContext

        # Test with ValidationContext (modern interface)
        context1 = ValidationContext(entry_data={}, entry_type="section")
        self.registry.validate_entry_type(context1)

        context2 = ValidationContext(entry_data={"type": "table"}, entry_type="table")
        self.registry.validate_entry_type(context2)

        # Check statistics are updated
        assert self.registry.statistics.entry_counts["section"] == 1
        assert self.registry.statistics.entry_counts["table"] == 1

    def test_validate_entry_type_unknown_strict(self):
        """Test validation of unknown entry types in strict mode."""
        from dnd5e.core.entry_registry import ValidationContext

        strict_registry = EntryTypeRegistry(ValidationMode.STRICT)

        context = ValidationContext(entry_data={}, entry_type="unknownType")

        with pytest.raises(UnknownEntryTypeError) as exc_info:
            strict_registry.validate_entry_type(context)

        assert exc_info.value.entry_type == "unknownType"
        assert "unknownType" in strict_registry.unknown_types

    def test_validate_entry_type_unknown_permissive(self):
        """Test validation of unknown entry types in permissive mode."""
        from dnd5e.core.entry_registry import ValidationContext

        context = ValidationContext(entry_data={}, entry_type="unknownType")

        with pytest.warns(EntryProcessingWarning, match="Unknown entry type"):
            self.registry.validate_entry_type(context)

        assert "unknownType" in self.registry.unknown_types
        assert self.registry.statistics.entry_counts["unknownType"] == 1

    def test_validate_entry_type_unknown_silent(self):
        """Test validation of unknown entry types in silent mode."""
        from dnd5e.core.entry_registry import ValidationContext

        silent_registry = EntryTypeRegistry(ValidationMode.SILENT)

        context = ValidationContext(entry_data={}, entry_type="unknownType")

        # Should not raise exception or warning
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            silent_registry.validate_entry_type(context)

        assert "unknownType" in silent_registry.unknown_types

    def test_validate_entry_type_with_context(self):
        """Test validation with full context information."""
        from dnd5e.core.entry_registry import ValidationContext

        entry = {"type": "unknownType", "name": "Test"}

        context = ValidationContext(
            entry_data=entry,
            source="PHB",
            parent_name="Chapter 1",
            entry_type="unknownType",
        )

        with pytest.warns(EntryProcessingWarning) as warning_info:
            self.registry.validate_entry_type(context)

        warning_msg = str(warning_info[0].message)
        assert "unknownType" in warning_msg
        assert "PHB" in warning_msg
        assert "Chapter 1" in warning_msg

    def test_validate_entry_structure_string(self):
        """Test validation of string entries."""
        from dnd5e.core.entry_registry import ValidationContext

        context = ValidationContext(entry_data="Plain text entry")
        result = self.registry.validate_entry_structure(context)

        assert result.success is True
        assert result.entry.type == "text"
        assert result.entry.content == "Plain text entry"

    def test_validate_entry_structure_dict(self):
        """Test validation of dict entries."""
        from dnd5e.core.entry_registry import ValidationContext

        entry = {"type": "section", "name": "Test Section"}
        context = ValidationContext(entry_data=entry)
        result = self.registry.validate_entry_structure(context)

        assert result.success is True
        assert result.entry.type == "section"
        assert result.entry.name == "Test Section"

    def test_validate_entry_structure_invalid(self):
        """Test validation of invalid entry structures."""
        from dnd5e.core.entry_registry import ValidationContext

        context = ValidationContext(entry_data=123)
        result = self.registry.validate_entry_structure(context)

        assert result.success is False
        assert len(result.errors) == 1
        assert "must be dict or string" in result.errors[0]

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        from dnd5e.core.entry_registry import ValidationContext

        # Generate some statistics
        context1 = ValidationContext(entry_data={}, entry_type="section")
        self.registry.validate_entry_type(context1)

        context2 = ValidationContext(entry_data={}, entry_type="unknownType")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore warnings for this test
            self.registry.validate_entry_type(context2)

        assert self.registry.statistics.total_entries > 0
        assert len(self.registry.unknown_types) > 0

        # Reset and verify
        self.registry.reset_statistics()
        assert self.registry.statistics.total_entries == 0
        assert len(self.registry.unknown_types) == 0

    @patch("dnd5e.core.entry_registry.logger")
    def test_log_statistics(self, mock_logger):
        """Test statistics logging."""
        from dnd5e.core.entry_registry import ValidationContext

        # Generate some statistics
        context1 = ValidationContext(entry_data={}, entry_type="section")
        self.registry.validate_entry_type(context1)
        self.registry.validate_entry_type(context1)  # Test count

        context2 = ValidationContext(entry_data={}, entry_type="unknownType")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore warnings for this test
            self.registry.validate_entry_type(context2)

        self.registry.log_statistics()

        # Verify logging calls
        assert mock_logger.info.call_count >= 2  # Total + known types
        assert mock_logger.warning.call_count >= 1  # Unknown types

    @patch("dnd5e.core.entry_registry.logger")
    def test_log_statistics_empty(self, mock_logger):
        """Test statistics logging with no data."""
        self.registry.log_statistics()

        mock_logger.info.assert_called_once_with(
            "No entry processing statistics available"
        )


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_registry(self):
        """Test get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_set_validation_mode(self):
        """Test set_validation_mode changes global mode."""
        original_mode = get_registry().validation_mode

        try:
            set_validation_mode(ValidationMode.STRICT)
            assert get_registry().validation_mode == ValidationMode.STRICT

            set_validation_mode(ValidationMode.SILENT)
            assert get_registry().validation_mode == ValidationMode.SILENT
        finally:
            # Restore original mode
            set_validation_mode(original_mode)
