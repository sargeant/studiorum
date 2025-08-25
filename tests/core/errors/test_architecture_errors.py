"""Tests for Result-based architecture error handling."""

from unittest.mock import Mock, patch

import pytest

from studiorum.core.error_types import (
    ContentLoadingError,
    ContentSourceError,
    ContentValidationError,
    ErrorCategory,
    ErrorSeverity,
    ReferenceTrackingError,
    TemplateCompositionError,
    create_content_loading_error,
    create_content_source_error,
    create_content_validation_error,
    create_reference_tracking_error,
    create_template_composition_error,
)
from studiorum.core.result import Error, Result, Success
from tests.test_helpers import reset_test_environment


class TestContentSourceError:
    """Test ContentSourceError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentSourceError initialization."""
        error = create_content_source_error(
            "Source error", source_location="test.json", source_type="file"
        )

        assert error.message == "Source error"
        assert error.category == ErrorCategory.IO
        assert error.severity == ErrorSeverity.ERROR
        assert error.source_location == "test.json"
        assert error.source_type == "file"

    def test_init_with_additional_context(self):
        """Test ContentSourceError with additional context."""
        error = create_content_source_error(
            "Source error",
            source_location="test.json",
            source_type="file",
            source="loader.py",
            severity=ErrorSeverity.WARNING,
            suggestions=["Check file permissions"],
        )

        assert error.source == "loader.py"
        assert error.severity == ErrorSeverity.WARNING
        assert error.suggestions == ["Check file permissions"]

    def test_inheritance(self):
        """Test ContentSourceError inherits from BaseError."""
        error = create_content_source_error("Test")

        # Check that it's the correct type
        assert isinstance(error, ContentSourceError)


class TestContentValidationError:
    """Test ContentValidationError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentValidationError initialization."""
        error = create_content_validation_error(
            "Validation failed", source_location="test.json"
        )

        assert error.message == "Validation failed"
        assert error.category == ErrorCategory.VALIDATION
        assert isinstance(error, ContentSourceError)

    def test_init_with_validation_errors_list(self):
        """Test ContentValidationError with validation errors list."""
        validation_errors = ["Field 'name' is required", "Invalid type for 'age'"]
        error = create_content_validation_error(
            "Multiple validation errors",
            validation_errors=validation_errors,
            source_location="test.json",
        )

        assert error.validation_errors == validation_errors


class TestContentLoadingError:
    """Test ContentLoadingError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentLoadingError initialization."""
        error = create_content_loading_error(
            "Loading failed", source_location="data.json"
        )

        assert error.message == "Loading failed"
        assert error.category == ErrorCategory.IO
        assert error.items_processed == 0
        assert error.items_failed == 0

    def test_init_with_processing_statistics(self):
        """Test ContentLoadingError with processing statistics."""
        error = create_content_loading_error(
            "Partial loading failure",
            items_processed=5,
            items_failed=2,
            source_location="data.json",
        )

        assert error.items_processed == 5
        assert error.items_failed == 2


class TestReferenceTrackingError:
    """Test ReferenceTrackingError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ReferenceTrackingError initialization."""
        error = create_reference_tracking_error(
            "Tracking error", reference_type="spell"
        )

        assert error.message == "Tracking error"
        assert error.category == ErrorCategory.PROCESSING
        assert error.reference_type == "spell"
        assert error.reference_name == "unknown"

    def test_init_with_additional_context(self):
        """Test ReferenceTrackingError with additional context."""
        error = create_reference_tracking_error(
            "Reference not found",
            reference_type="spell",
            reference_name="fireball",
            source="spell_tracker.py",
        )

        assert error.reference_type == "spell"
        assert error.reference_name == "fireball"
        assert error.source == "spell_tracker.py"


class TestTemplateCompositionError:
    """Test TemplateCompositionError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic TemplateCompositionError initialization."""
        error = create_template_composition_error(
            "Template error", template_name="base.tex"
        )

        assert error.message == "Template error"
        assert error.category == ErrorCategory.RENDER
        assert error.template_name == "base.tex"
        assert error.component_name == "unknown"

    def test_init_with_additional_context(self):
        """Test TemplateCompositionError with additional context."""
        error = create_template_composition_error(
            "Component missing",
            template_name="spell.tex",
            component_name="description",
            source="template_engine.py",
        )

        assert error.template_name == "spell.tex"
        assert error.component_name == "description"
        assert error.source == "template_engine.py"


class TestResultPatternUsage:
    """Test using architecture errors with Result pattern."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_content_source_error_in_result(self):
        """Test ContentSourceError used in Result pattern."""
        error = create_content_source_error(
            "File not found", source_location="missing.json"
        )
        result = Error(error)

        assert isinstance(result, Error)
        assert result.error.message == "File not found"
        assert result.error.source_location == "missing.json"

    def test_validation_error_in_result(self):
        """Test ContentValidationError used in Result pattern."""
        error = create_content_validation_error(
            "Invalid data",
            validation_errors=["Missing required field"],
            source_location="test.json",
        )
        result = Error(error)

        assert isinstance(result, Error)
        assert result.error.validation_errors == ["Missing required field"]

    def test_success_result(self):
        """Test successful operation with Result pattern."""
        result = Success("operation completed")

        assert isinstance(result, Success)
        assert result.unwrap() == "operation completed"


class TestErrorIntegration:
    """Test integration of different error types."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_error_hierarchy(self):
        """Test error type hierarchy."""
        content_error = create_content_source_error(
            "Source error", source_location="test.json"
        )
        validation_error = create_content_validation_error(
            "Validation error", source_location="test.json"
        )
        loading_error = create_content_loading_error(
            "Loading error", source_location="test.json"
        )

        # All should be BaseError instances through inheritance
        assert hasattr(content_error, "message")
        assert hasattr(validation_error, "message")
        assert hasattr(loading_error, "message")

        # Validation and Loading should also be ContentSourceError instances
        assert isinstance(validation_error, ContentValidationError)
        assert isinstance(loading_error, ContentLoadingError)

    def test_error_with_suggestions(self):
        """Test error creation with suggestions."""
        error = create_reference_tracking_error(
            "Reference not found",
            reference_type="spell",
            reference_name="fireball",
            suggestions=["Check spell list", "Verify spelling"],
        )

        assert error.suggestions == ["Check spell list", "Verify spelling"]

    def test_error_severity_levels(self):
        """Test different error severity levels."""
        warning = create_content_source_error(
            "Minor issue", severity=ErrorSeverity.WARNING
        )
        error = create_content_source_error("Major issue", severity=ErrorSeverity.ERROR)
        critical = create_content_source_error(
            "Critical issue", severity=ErrorSeverity.CRITICAL
        )

        assert warning.severity == ErrorSeverity.WARNING
        assert error.severity == ErrorSeverity.ERROR
        assert critical.severity == ErrorSeverity.CRITICAL

    def test_complex_error_context(self):
        """Test complex error with multiple context fields."""
        error = create_template_composition_error(
            "Template composition failed",
            template_name="complex.tex",
            component_name="spell-description",
            source="template_engine.py",
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check template syntax",
                "Verify component exists",
                "Review template documentation",
            ],
        )

        assert error.template_name == "complex.tex"
        assert error.component_name == "spell-description"
        assert error.source == "template_engine.py"
        assert len(error.suggestions) == 3
        assert "Check template syntax" in error.suggestions
