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
    validate_entry_structure,
    validate_entry_type,
)
from dnd5e.core.exceptions import (
    EntryProcessingWarning,
    EntryValidationError,
    MalformedEntryError,
    UnknownEntryTypeError,
)


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
        self.registry = EntryTypeRegistry(ValidationMode.PERMISSIVE)

    def test_initialization(self):
        """Test registry initialization."""
        registry = EntryTypeRegistry(ValidationMode.STRICT)
        assert registry.validation_mode == ValidationMode.STRICT
        assert len(registry.known_types) > 0
        assert len(registry.unknown_types) == 0
        assert len(registry.statistics) == 0

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
        # Should not raise any exceptions or warnings
        self.registry.validate_entry_type("section")
        self.registry.validate_entry_type("table", {"type": "table"})

        # Check statistics are updated
        assert self.registry.statistics["section"] == 1
        assert self.registry.statistics["table"] == 1

    def test_validate_entry_type_unknown_strict(self):
        """Test validation of unknown entry types in strict mode."""
        strict_registry = EntryTypeRegistry(ValidationMode.STRICT)

        with pytest.raises(UnknownEntryTypeError) as exc_info:
            strict_registry.validate_entry_type("unknownType")

        assert exc_info.value.entry_type == "unknownType"
        assert "unknownType" in strict_registry.unknown_types

    def test_validate_entry_type_unknown_permissive(self):
        """Test validation of unknown entry types in permissive mode."""
        with pytest.warns(EntryProcessingWarning, match="Unknown entry type"):
            self.registry.validate_entry_type("unknownType")

        assert "unknownType" in self.registry.unknown_types
        assert self.registry.statistics["unknownType"] == 1

    def test_validate_entry_type_unknown_silent(self):
        """Test validation of unknown entry types in silent mode."""
        silent_registry = EntryTypeRegistry(ValidationMode.SILENT)

        # Should not raise exception or warning
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            silent_registry.validate_entry_type("unknownType")

        assert "unknownType" in silent_registry.unknown_types

    def test_validate_entry_type_with_context(self):
        """Test validation with full context information."""
        entry = {"type": "unknownType", "name": "Test"}

        with pytest.warns(EntryProcessingWarning) as warning_info:
            self.registry.validate_entry_type(
                "unknownType", entry=entry, source="PHB", parent_name="Chapter 1"
            )

        warning_msg = str(warning_info[0].message)
        assert "unknownType" in warning_msg
        assert "PHB" in warning_msg
        assert "Chapter 1" in warning_msg

    def test_validate_entry_structure_string(self):
        """Test validation of string entries."""
        result = self.registry.validate_entry_structure("Plain text entry")
        assert result == {"type": "text", "content": "Plain text entry"}

    def test_validate_entry_structure_dict(self):
        """Test validation of dict entries."""
        entry = {"type": "section", "name": "Test Section"}
        result = self.registry.validate_entry_structure(entry)
        assert result == entry

    def test_validate_entry_structure_invalid(self):
        """Test validation of invalid entry structures."""
        with pytest.raises(MalformedEntryError) as exc_info:
            self.registry.validate_entry_structure(123)

        assert "must be dict or string" in str(exc_info.value)

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        entry = {"type": "section", "name": "Test Section"}
        required_fields = {"type", "name"}

        # Should not raise exception
        self.registry.validate_required_fields(entry, required_fields)

    def test_validate_required_fields_missing(self):
        """Test validation with missing required fields."""
        entry = {"type": "section"}  # Missing 'name'
        required_fields = {"type", "name", "entries"}

        with pytest.raises(EntryValidationError) as exc_info:
            self.registry.validate_required_fields(entry, required_fields)

        error_msg = str(exc_info.value)
        assert "Missing required fields" in error_msg
        assert "entries" in error_msg
        assert "name" in error_msg

    def test_get_common_fields(self):
        """Test get_common_fields method."""
        # Section is recursive but also has specific handling for 'name'
        fields = self.registry.get_common_fields("section")
        assert "type" in fields
        assert "name" in fields

        # Other recursive types should include 'entries'
        fields = self.registry.get_common_fields("inset")
        assert "type" in fields
        assert "name" in fields

        # Tables should include 'rows'
        fields = self.registry.get_common_fields("table")
        assert "type" in fields
        assert "rows" in fields

        # Lists should include 'items'
        fields = self.registry.get_common_fields("list")
        assert "type" in fields
        assert "items" in fields

        # Generic recursive types should have entries
        fields = self.registry.get_common_fields(
            "options"
        )  # This is recursive but not specifically handled
        assert "type" in fields
        assert "entries" in fields

        # Unknown types should just have 'type'
        fields = self.registry.get_common_fields("unknownType")
        assert fields == {"type"}

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        # Generate some statistics
        self.registry.validate_entry_type("section")
        self.registry.validate_entry_type("unknownType")

        assert len(self.registry.statistics) > 0
        assert len(self.registry.unknown_types) > 0

        # Reset and verify
        self.registry.reset_statistics()
        assert len(self.registry.statistics) == 0
        assert len(self.registry.unknown_types) == 0

    @patch("dnd5e.core.entry_registry.logger")
    def test_log_statistics(self, mock_logger):
        """Test statistics logging."""
        # Generate some statistics
        self.registry.validate_entry_type("section")
        self.registry.validate_entry_type("section")  # Test count
        self.registry.validate_entry_type("unknownType")

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

    def test_validate_entry_type_global(self):
        """Test global validate_entry_type function."""
        original_mode = get_registry().validation_mode

        try:
            set_validation_mode(ValidationMode.PERMISSIVE)

            # Should use global registry
            with pytest.warns(EntryProcessingWarning):
                validate_entry_type("unknownGlobalType")

            assert "unknownGlobalType" in get_registry().unknown_types
        finally:
            set_validation_mode(original_mode)
            get_registry().reset_statistics()

    def test_validate_entry_structure_global(self):
        """Test global validate_entry_structure function."""
        result = validate_entry_structure("test string")
        assert result == {"type": "text", "content": "test string"}

        entry = {"type": "test"}
        result = validate_entry_structure(entry)
        assert result == entry
