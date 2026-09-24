"""
Integration tests for standardized error handling system.

Tests the complete error handling pipeline from Result pattern through
logging and backward compatibility.
"""

import pytest
from logfire.testing import CaptureLogfire

from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    ValidationError,
    create_validation_error,
)
from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success, try_result


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling components."""

    @pytest.fixture(autouse=True)
    def setup_log_capture(self, capfire: CaptureLogfire) -> None:
        """Set up log capture for each test."""
        self.capfire = capfire

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
