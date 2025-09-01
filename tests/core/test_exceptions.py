"""Tests for Result[T, E] error handling patterns.

This test file has been updated for Phase 3 to test Result patterns
instead of legacy exception classes. Only EntryProcessingWarning
remains for backward compatibility.
"""

import pytest

from studiorum.core.error_types import (
    BaseError,
    ProcessingError,
    UnknownTypeError,
    ValidationError,
    create_processing_error,
    create_unknown_type_error,
    create_validation_error,
)
from studiorum.core.exceptions import EntryProcessingWarning
from studiorum.core.result import Error, Success


class TestBaseError:
    """Test the base BaseError structured error type."""

    def test_basic_error(self):
        """Test basic error creation and properties."""
        error = create_processing_error(
            message="Test error", entry_type="test", source="TEST"
        )
        assert error.message == "Test error"
        assert error.entry_type == "test"
        assert error.source == "TEST"
        assert isinstance(error, BaseError)


class TestProcessingError:
    """Test ProcessingError structured error type."""

    def test_basic_error(self):
        """Test basic error without context."""
        error = create_processing_error("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.entry_type is None
        assert error.source is None
        assert error.parent_name is None

    def test_error_with_full_context(self):
        """Test error with complete context information."""
        error = create_processing_error(
            message="Processing failed",
            entry_type="section",
            source="PHB",
            parent_name="Chapter 1",
            context={"entry_data": {"type": "section", "name": "Test Section"}},
        )

        assert error.message == "Processing failed"
        assert error.entry_type == "section"
        assert error.source == "PHB"
        assert error.parent_name == "Chapter 1"
        assert error.context is not None
        assert error.context["entry_data"]["type"] == "section"

    def test_error_with_partial_context(self):
        """Test error with only some context fields."""
        error = create_processing_error(
            message="Processing failed",
            source="PHB",
            entry_type="table",
        )

        assert error.message == "Processing failed"
        assert error.source == "PHB"
        assert error.entry_type == "table"
        assert error.parent_name is None


class TestUnknownTypeError:
    """Test UnknownTypeError structured error type."""

    def test_unknown_type_error(self):
        """Test unknown entry type error creation."""
        error = create_unknown_type_error(
            entry_type="unknownType",
            available_types=["section", "table", "inset"],
            source="Custom",
            parent_name="Test Parent",
        )

        assert error.message == "Unknown entry type: 'unknownType'"
        assert error.entry_type == "unknownType"
        assert error.source == "Custom"
        assert error.parent_name == "Test Parent"
        assert error.available_types == ["section", "table", "inset"]

    def test_unknown_type_minimal(self):
        """Test unknown entry type error with minimal context."""
        error = create_unknown_type_error(entry_type="mystery")

        assert error.message == "Unknown entry type: 'mystery'"
        assert error.entry_type == "mystery"
        assert error.source is None
        assert error.parent_name is None


class TestValidationError:
    """Test ValidationError structured error type."""

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        error = create_validation_error(
            message="Field is required",
            field_name="rows",
            entry_type="table",
            source="DMG",
        )

        assert error.message == "Field is required"
        assert error.field_name == "rows"
        assert error.entry_type == "table"
        assert error.source == "DMG"

    def test_validation_error_without_field(self):
        """Test validation error without specific field."""
        error = create_validation_error(
            message="Entry structure is invalid",
            entry_type="section",
        )

        assert error.message == "Entry structure is invalid"
        assert error.entry_type == "section"
        assert error.field_name is None


class TestMalformedDataError:
    """Test MalformedDataError for structural problems."""

    def test_malformed_dict_entry(self):
        """Test malformed error with expected structure."""
        error = create_processing_error(
            message="Missing required structure",
            source="Test",
            context={
                "expected_type": "dict",
                "actual_type": "invalid_structure",
                "entry_data": {"invalid": "structure", "missing": "type"},
            },
        )

        assert error.message == "Missing required structure"
        assert error.source == "Test"
        assert error.context is not None
        assert error.context["expected_type"] == "dict"

    def test_malformed_non_dict_entry(self):
        """Test malformed error with wrong data type."""
        error = create_processing_error(
            message="Wrong data type",
            context={
                "expected_type": "dict",
                "actual_type": "int",
                "actual_value": 123,
            },
        )

        assert error.message == "Wrong data type"
        assert error.context["actual_type"] == "int"
        assert error.context["actual_value"] == 123

    def test_malformed_error_is_processing_error(self):
        """Test that malformed data errors are processing errors."""
        error = create_processing_error("Test error")
        assert isinstance(error, ProcessingError)
        assert isinstance(error, BaseError)


class TestEntryProcessingWarning:
    """Test EntryProcessingWarning for non-fatal issues (backward compatibility)."""

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


class TestResultPatterns:
    """Test Result[T, E] pattern integration with error types."""

    def test_error_result_creation(self):
        """Test creating Error results with structured errors."""
        error = create_processing_error("Test failed", entry_type="test")
        result = Error(error)

        assert result.is_error()
        assert not result.is_success()
        assert isinstance(result, Error)

    def test_success_result_creation(self):
        """Test creating Success results."""
        result = Success("test data")

        assert result.is_success()
        assert not result.is_error()
        assert result.unwrap() == "test data"

    def test_error_with_context_chaining(self):
        """Test error context chaining using with_context."""
        base_error = create_processing_error(
            "Base error", entry_type="test", source="TEST"
        )
        result = Error(base_error)

        chained_result = result.with_context(
            "Higher level operation failed",
            operation="test_operation",
            context_id="123",
        )

        assert isinstance(chained_result, Error)
        assert isinstance(chained_result.error, dict)
        assert chained_result.error["message"] == "Higher level operation failed"
        assert chained_result.error["underlying"] == base_error


class TestErrorTypeHierarchy:
    """Test structured error type hierarchy."""

    def test_all_inherit_from_base(self):
        """Test that all structured errors inherit from BaseError."""
        errors = [
            create_processing_error("test"),
            create_validation_error("test"),
            create_unknown_type_error("test"),
        ]

        for error in errors:
            assert isinstance(error, BaseError)

    def test_specific_error_types(self):
        """Test specific error type inheritance."""
        processing_error = create_processing_error("test")
        validation_error = create_validation_error("test")
        unknown_type_error = create_unknown_type_error("test")

        assert isinstance(processing_error, ProcessingError)
        assert isinstance(validation_error, ValidationError)
        assert isinstance(unknown_type_error, UnknownTypeError)

        # All should inherit from BaseError
        for error in [processing_error, validation_error, unknown_type_error]:
            assert isinstance(error, BaseError)
