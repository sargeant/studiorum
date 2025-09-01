"""
Integration tests for standardized error handling system.

Tests the complete error handling pipeline from Result pattern through
logging and backward compatibility.
"""

from typing import Any

import pytest
from logfire.testing import CaptureLogfire
from pydantic import BaseModel, Field

from studiorum.core.entry_validation import StandardizedEntryValidator
from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    ProcessingError,
    ValidationError,
    create_processing_error,
    create_validation_error,
)
from studiorum.core.logging import get_logger
from studiorum.core.model_validation import validate_model, validate_required_field
from studiorum.core.result import Error, Result, Success, collect_results, try_result
from tests.test_helpers import reset_test_environment


class TestModel(BaseModel):
    """Test model for validation testing."""

    name: str = Field(min_length=1, description="Test name")
    level: int = Field(ge=1, le=10, description="Test level")
    optional_field: str | None = Field(default=None, description="Optional field")


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling components."""

    @pytest.fixture(autouse=True)
    def setup_log_capture(self, capfire: CaptureLogfire) -> None:
        """Set up log capture for each test."""
        self.capfire = capfire

    def setup_method(self) -> None:
        """Set up test environment."""
        # Reset global state for complete isolation
        reset_test_environment()

    def get_log_output(self) -> str:
        """Get captured log output from Logfire spans."""
        messages = []
        for span in self.capfire.exporter.exported_spans:
            if hasattr(span, "attributes") and span.attributes:
                msg = span.attributes.get("logfire.msg", "")
                if msg:
                    messages.append(msg)
        return "\n".join(messages)

    def test_result_pattern_basic_usage(self) -> None:
        """Test basic Result pattern usage."""
        # Success case
        success_result: Result[str, ValidationError] = Success("test value")
        assert success_result.is_success()
        assert not success_result.is_error()
        assert success_result.unwrap() == "test value"

        # Error case
        error = create_validation_error("Test error message")
        error_result: Result[str, ValidationError] = Error(error)
        assert error_result.is_error()
        assert not error_result.is_success()

        # Test unwrap_or
        assert error_result.unwrap_or("default") == "default"

        # Test unwrap_or_else
        assert (
            error_result.unwrap_or_else(lambda e: f"Error: {e.message}")
            == "Error: Test error message"
        )

    def test_validation_result_integration(self) -> None:
        """Test validation using Result pattern."""
        # Valid data
        valid_data = {"name": "Test Item", "level": 5}
        result = validate_model(TestModel, valid_data, source="test.json")

        assert result.is_success()
        model = result.unwrap()
        assert model.name == "Test Item"
        assert model.level == 5

        # Invalid data - missing required field
        invalid_data = {"level": 5}
        result = validate_model(TestModel, invalid_data, source="test.json")

        assert result.is_error()
        error = result.error  # type: ignore[attr-defined]
        assert isinstance(error, ValidationError)
        assert "name" in error.message.lower()
        assert error.field_name == "name"
        assert error.source == "test.json"

    def test_field_validation(self) -> None:
        """Test individual field validation."""
        data = {"name": "Test", "level": 5, "extra": "field"}

        # Required field exists
        result = validate_required_field(data, "name")
        assert result.is_success()
        assert result.unwrap() == "Test"

        # Required field missing
        result = validate_required_field(data, "missing_field")
        assert result.is_error()
        error = result.error  # type: ignore[attr-defined]
        assert "missing_field" in error.message
        assert error.field_name == "missing_field"

    def test_batch_validation(self) -> None:
        """Test batch validation using collect_results."""
        data_list = [
            {"name": "Item 1", "level": 1},
            {"name": "Item 2", "level": 2},
            {"name": "Item 3", "level": 3},
        ]

        # All valid
        results = [validate_model(TestModel, data) for data in data_list]
        batch_result = collect_results(results)

        assert batch_result.is_success()
        models = batch_result.unwrap()
        assert len(models) == 3
        assert all(isinstance(m, TestModel) for m in models)

        # Some invalid
        invalid_data_list = [
            {"name": "Item 1", "level": 1},
            {"level": 2},  # Missing name
            {"name": "Item 3", "level": 15},  # Invalid level
        ]

        results = [validate_model(TestModel, data) for data in invalid_data_list]
        batch_result = collect_results(results)

        assert batch_result.is_error()
        errors = batch_result.error  # type: ignore[attr-defined]
        assert len(errors) == 2  # Two validation errors

    def test_error_chaining(self) -> None:
        """Test error chaining with and_then."""

        def process_model(model: TestModel) -> Result[str, ProcessingError]:
            if model.level > 5:
                return Error(create_processing_error("Level too high for processing"))
            return Success(f"Processed {model.name}")

        # Success chain
        valid_data = {"name": "Test", "level": 3}
        result = validate_model(TestModel, valid_data).and_then(process_model)

        assert result.is_success()
        assert result.unwrap() == "Processed Test"

        # Error in validation step
        invalid_data = {"level": 3}  # Missing name
        result = validate_model(TestModel, invalid_data).and_then(process_model)

        assert result.is_error()
        # Should be validation error, not processing error
        error = result.error  # type: ignore[attr-defined]
        assert isinstance(error, ValidationError)

        # Error in processing step
        high_level_data = {"name": "Test", "level": 8}
        result = validate_model(TestModel, high_level_data).and_then(process_model)

        assert result.is_error()
        # Should be processing error this time
        error = result.error  # type: ignore[attr-defined]
        assert isinstance(error, ProcessingError)
        assert "Level too high" in error.message

    def test_standard_logging(self) -> None:
        """Test standard logging integration."""
        logger = get_logger("test_module")

        # Log successful result
        success_result = Success("test value")
        if success_result.is_success():
            logger.info("Operation completed: test_operation")

        log_output = self.get_log_output()
        assert "Operation completed" in log_output
        assert "test_operation" in log_output

        # Log error result
        error = create_validation_error(
            message="Test validation failed",
            field_name="test_field",
            suggestions=["Check the field value"],
        )
        error_result = Error(error)
        if error_result.is_error():
            logger.error(f"Validation error in test_operation: {error.message}")

        log_output = self.get_log_output()
        assert "Test validation failed" in log_output
        assert "test_operation" in log_output

    def test_basic_logging_context(self) -> None:
        """Test basic logging with context information."""
        logger = get_logger("test_module")

        # Simulate logging with context
        operation = "test_operation"
        content_type = "test_content"
        content_name = "test_item"
        file_path = "test.json"

        logger.info(
            f"Starting {operation} for {content_type}: {content_name} from {file_path}"
        )

        log_output = self.get_log_output()
        assert "test_operation" in log_output
        assert "test_content" in log_output
        assert "test_item" in log_output
        assert "test.json" in log_output

    def test_try_result_utility(self) -> None:
        """Test try_result utility function."""
        # Success case
        result = try_result(lambda: 10 / 2)
        assert result.is_success()
        assert result.unwrap() == 5.0

        # Exception case
        result = try_result(lambda: 10 / 0)
        assert result.is_error()
        error = result.error  # type: ignore[attr-defined]
        assert isinstance(error, ZeroDivisionError)

    def test_standardized_entry_validator(self) -> None:
        """Test the standardized entry validator."""
        validator = StandardizedEntryValidator()

        # Test string entry
        result = validator.validate_entry("This is a text entry")
        assert result.is_success()
        entry = result.unwrap()
        assert entry.type == "text"
        assert entry.content == "This is a text entry"

        # Test dictionary entry
        entry_data = {
            "type": "section",
            "name": "Test Section",
            "entries": ["Some content"],
        }
        result = validator.validate_entry(entry_data, source="test.json")
        assert result.is_success()
        entry = result.unwrap()
        assert entry.type == "section"
        assert entry.name == "Test Section"

        # Test invalid entry (None)
        result = validator.validate_entry(None)
        assert result.is_error()
        error = result.error  # type: ignore[attr-defined]
        assert "cannot be None" in error.message

    def test_error_severity_handling(self) -> None:
        """Test that different error severities are handled correctly."""
        logger = get_logger("test_module")

        # Test different severity levels
        severities = [
            (ErrorSeverity.INFO, "INFO"),
            (ErrorSeverity.WARNING, "WARNING"),
            (ErrorSeverity.ERROR, "ERROR"),
            (ErrorSeverity.CRITICAL, "CRITICAL"),
        ]

        # Track initial span count to isolate new messages
        len(self.capfire.exporter.exported_spans)

        for severity, expected_level in severities:
            error = ValidationError(
                message=f"Test {severity.value} message",
                category=ErrorCategory.VALIDATION,
                severity=severity,
            )

            # Log based on severity
            if severity == ErrorSeverity.INFO:
                logger.info(f"Validation info: {error.message}")
            elif severity == ErrorSeverity.WARNING:
                logger.warning(f"Validation warning: {error.message}")
            elif severity == ErrorSeverity.ERROR:
                logger.error(f"Validation error: {error.message}")
            elif severity == ErrorSeverity.CRITICAL:
                # Logfire doesn't have critical, use error for critical severity
                logger.error(f"Validation critical: {error.message}")

        # Check all new log messages
        log_output = self.get_log_output()
        for severity, expected_level in severities:
            assert f"Test {severity.value} message" in log_output

    def test_error_suggestions(self) -> None:
        """Test that error suggestions are properly handled."""
        error = create_validation_error(
            message="Field validation failed",
            field_name="level",
            suggestions=[
                "Check that level is between 1 and 10",
                "Ensure level is an integer",
            ],
        )

        logger = get_logger("test_module")
        # Log error with suggestions
        suggestion_text = "; ".join(error.suggestions or [])
        logger.error(f"{error.message}. Suggestions: {suggestion_text}")

        log_output = self.get_log_output()
        assert "Field validation failed" in log_output
        assert "Check that level is between 1 and 10" in log_output
        assert "Ensure level is an integer" in log_output

    def test_integration_with_pydantic_errors(self) -> None:
        """Test integration with Pydantic validation errors."""
        # Test with invalid data that will trigger Pydantic validation
        invalid_data = {
            "name": "",  # Too short (min_length=1)
            "level": 15,  # Too high (le=10)
        }

        result = validate_model(TestModel, invalid_data, source="test.json")
        assert result.is_error()

        error = result.error  # type: ignore[attr-defined]
        assert isinstance(error, ValidationError)
        assert error.source == "test.json"
        assert error.entry_type == "TestModel"

        # Should have suggestions
        assert error.suggestions is not None
        assert len(error.suggestions) > 0

    def test_end_to_end_error_flow(self) -> None:
        """Test complete error handling flow from validation to logging."""
        logger = get_logger("integration_test")
        validator = StandardizedEntryValidator()

        # Test data with various error conditions
        test_entries = [
            "Valid text entry",
            {"type": "section", "name": "Valid Section"},
            {"type": "unknown_type", "content": "Unknown type"},
            None,  # Invalid entry
            {"name": "Missing type field"},
        ]

        # Log the start of batch validation
        logger.info("Starting batch_validation for mixed_entries from test_batch.json")

        results = []
        for i, entry_data in enumerate(test_entries):
            result = validator.validate_entry(
                entry_data, source="test_batch.json", parent_name=f"entry[{i}]"
            )
            results.append(result)

            # Log each result
            if result.is_success():
                logger.info(f"validate_entry_{i} completed successfully")
            else:
                error = result.error  # type: ignore[attr-defined]
                logger.error(f"validate_entry_{i} failed: {error.message}")

        # Collect batch results
        batch_result = collect_results(results)
        if batch_result.is_success():
            logger.info("batch_validation completed successfully")
        else:
            logger.error("batch_validation failed with errors")

        log_output = self.get_log_output()

        # Should have success messages for valid entries
        assert "completed successfully" in log_output

        # Should have error messages for invalid entries
        assert (
            "cannot be None" in log_output
            or "Required field 'type' is missing" in log_output
        )

        # Should have context information
        assert "batch_validation" in log_output
        assert "test_batch.json" in log_output

    def test_performance_with_large_batch(self) -> None:
        """Test performance with larger batch of validations."""
        StandardizedEntryValidator()

        # Create large batch of test data
        large_batch = []
        for i in range(1000):
            if i % 10 == 0:
                # Add some invalid entries
                large_batch.append({"level": i})  # Missing name
            else:
                large_batch.append({"name": f"Item {i}", "level": i % 10 + 1})

        # Validate batch
        results = []
        for entry_data in large_batch:
            result = validate_model(TestModel, entry_data)
            results.append(result)

        batch_result = collect_results(results)

        # Should handle the batch correctly
        assert batch_result.is_error()  # Due to invalid entries
        errors = batch_result.error  # type: ignore[attr-defined]
        assert len(errors) == 100  # 10% of entries are invalid

        # All errors should be validation errors
        assert all(isinstance(e, ValidationError) for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
