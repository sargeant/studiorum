"""Tests for custom D&D 5e exceptions."""

import pytest

from dnd5e.core.exceptions import (
    DnD5eError,
    EntryProcessingError,
    EntryProcessingWarning,
    EntryValidationError,
    MalformedEntryError,
    UnknownEntryTypeError,
)


class TestDnD5eError:
    """Test the base DnD5eError exception."""

    def test_basic_exception(self):
        """Test basic exception creation and inheritance."""
        error = DnD5eError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestEntryProcessingError:
    """Test EntryProcessingError with context."""

    def test_basic_error(self):
        """Test basic error without context."""
        error = EntryProcessingError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.entry is None
        assert error.source is None
        assert error.parent_name is None
        assert error.entry_type is None

    def test_error_with_full_context(self):
        """Test error with complete context information."""
        entry = {"type": "section", "name": "Test Section"}
        error = EntryProcessingError(
            message="Processing failed",
            entry=entry,
            source="PHB",
            parent_name="Chapter 1",
            entry_type="section",
        )

        expected_msg = (
            "Processing failed (source: PHB, parent: Chapter 1, type: section)"
        )
        assert str(error) == expected_msg
        assert error.entry == entry
        assert error.source == "PHB"
        assert error.parent_name == "Chapter 1"
        assert error.entry_type == "section"

    def test_error_with_partial_context(self):
        """Test error with only some context fields."""
        error = EntryProcessingError(
            message="Processing failed",
            source="PHB",
            entry_type="table",
        )

        expected_msg = "Processing failed (source: PHB, type: table)"
        assert str(error) == expected_msg
        assert error.source == "PHB"
        assert error.entry_type == "table"
        assert error.parent_name is None


class TestUnknownEntryTypeError:
    """Test UnknownEntryTypeError specific functionality."""

    def test_unknown_type_error(self):
        """Test unknown entry type error creation."""
        entry = {"type": "unknownType", "data": "test"}
        error = UnknownEntryTypeError(
            entry_type="unknownType",
            entry=entry,
            source="Custom",
            parent_name="Test Parent",
        )

        expected_msg = "Unknown entry type: 'unknownType' (source: Custom, parent: Test Parent, type: unknownType)"
        assert str(error) == expected_msg
        assert error.entry_type == "unknownType"
        assert error.entry == entry

    def test_unknown_type_minimal(self):
        """Test unknown entry type error with minimal context."""
        error = UnknownEntryTypeError(entry_type="mystery")

        expected_msg = "Unknown entry type: 'mystery' (type: mystery)"
        assert str(error) == expected_msg
        assert error.entry_type == "mystery"


class TestEntryValidationError:
    """Test EntryValidationError with field validation context."""

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        entry = {"type": "table"}  # Missing required 'rows' field
        error = EntryValidationError(
            message="Field is required",
            field_name="rows",
            entry=entry,
            source="DMG",
            entry_type="table",
        )

        expected_msg = "Validation failed for field 'rows': Field is required (source: DMG, type: table)"
        assert str(error) == expected_msg
        assert error.field_name == "rows"
        assert error.entry == entry

    def test_validation_error_without_field(self):
        """Test validation error without specific field."""
        error = EntryValidationError(
            message="Entry structure is invalid",
            entry_type="section",
        )

        expected_msg = "Entry structure is invalid (type: section)"
        assert str(error) == expected_msg
        assert error.field_name is None


class TestMalformedEntryError:
    """Test MalformedEntryError for structural problems."""

    def test_malformed_dict_entry(self):
        """Test malformed error with dict entry."""
        entry = {"invalid": "structure", "missing": "type"}
        error = MalformedEntryError(
            message="Missing required structure",
            entry=entry,
            source="Test",
        )

        expected_msg = "Malformed entry: Missing required structure (source: Test)"
        assert str(error) == expected_msg
        assert error.entry == entry

    def test_malformed_non_dict_entry(self):
        """Test malformed error with non-dict entry."""
        entry = 123  # Should be dict or string
        error = MalformedEntryError(
            message="Wrong data type",
            entry=entry,
        )

        expected_msg = "Malformed entry: Wrong data type"
        assert str(error) == expected_msg
        assert error.entry is None  # Non-dict entries are not stored as entry_dict

    def test_malformed_error_inheritance(self):
        """Test that MalformedEntryError inherits from EntryProcessingError."""
        error = MalformedEntryError("Test error")
        assert isinstance(error, EntryProcessingError)
        assert isinstance(error, DnD5eError)


class TestEntryProcessingWarning:
    """Test EntryProcessingWarning for non-fatal issues."""

    def test_warning_creation(self):
        """Test warning creation and inheritance."""
        warning = EntryProcessingWarning("This is a warning")
        assert str(warning) == "This is a warning"
        assert isinstance(warning, UserWarning)

    def test_warning_can_be_raised(self):
        """Test that warning can be raised and caught."""
        with pytest.warns(EntryProcessingWarning, match="Test warning"):
            import warnings

            warnings.warn("Test warning", EntryProcessingWarning, stacklevel=2)


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from DnD5eError."""
        exceptions = [
            EntryProcessingError("test"),
            UnknownEntryTypeError("test"),
            EntryValidationError("test"),
            MalformedEntryError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, DnD5eError)
            assert isinstance(exc, Exception)

    def test_processing_error_inheritance(self):
        """Test specific inheritance for processing-related errors."""
        exceptions = [
            UnknownEntryTypeError("test"),
            EntryValidationError("test"),
            MalformedEntryError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, EntryProcessingError)
            assert isinstance(exc, DnD5eError)
