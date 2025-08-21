"""Tests for enhanced architecture error handling."""

from unittest.mock import Mock, patch

import pytest

from studiorum.core.errors.architecture_errors import (
    ArchitectureError,
    ConfigurationError,
    ContentLoadingError,
    ContentSourceError,
    ContentValidationError,
    ReferenceTrackingError,
    TemplateCompositionError,
    format_error_for_user,
    handle_content_source_error,
    handle_reference_tracking_error,
    log_architecture_error,
)
from tests.test_helpers import reset_test_environment


class TestArchitectureError:
    """Test base ArchitectureError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ArchitectureError initialization."""
        error = ArchitectureError("Test error message")

        assert str(error) == "Test error message"
        assert error.context == {}

    def test_init_with_context(self):
        """Test ArchitectureError with context."""
        context = {"file": "test.json", "line": 42}
        error = ArchitectureError("Test error", context)

        assert error.context == context
        assert "file=test.json" in str(error)
        assert "line=42" in str(error)
        assert "Context:" in str(error)

    def test_str_without_context(self):
        """Test string representation without context."""
        error = ArchitectureError("Simple error")

        assert str(error) == "Simple error"

    def test_str_with_empty_context(self):
        """Test string representation with empty context."""
        error = ArchitectureError("Simple error", {})

        assert str(error) == "Simple error"


class TestContentSourceError:
    """Test ContentSourceError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentSourceError initialization."""
        error = ContentSourceError(
            "Source error", source_location="/path/to/file.json", source_type="file"
        )

        assert "Source error" in str(error)
        assert error.context["source_location"] == "/path/to/file.json"
        assert error.context["source_type"] == "file"

    def test_init_with_additional_context(self):
        """Test ContentSourceError with additional context."""
        error = ContentSourceError(
            "Source error",
            source_location="stdin",
            source_type="stdin",
            additional_info="Extra context",
        )

        assert error.context["source_location"] == "stdin"
        assert error.context["source_type"] == "stdin"
        assert error.context["additional_info"] == "Extra context"

    def test_inheritance(self):
        """Test ContentSourceError inherits from ArchitectureError."""
        error = ContentSourceError("Test")

        assert isinstance(error, ArchitectureError)
        assert isinstance(error, ContentSourceError)


class TestContentValidationError:
    """Test ContentValidationError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentValidationError initialization."""
        error = ContentValidationError(
            "Validation failed", source_location="test.json", source_type="file"
        )

        assert "Validation failed" in str(error)
        assert isinstance(error, ContentSourceError)

    def test_init_with_validation_errors(self):
        """Test ContentValidationError with validation errors list."""
        validation_errors = ["Missing required field", "Invalid type"]
        error = ContentValidationError(
            "Validation failed",
            validation_errors=validation_errors,
            source_location="test.json",
        )

        assert error.context["validation_errors"] == validation_errors
        assert "Missing required field" in str(error.context["validation_errors"])


class TestContentLoadingError:
    """Test ContentLoadingError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ContentLoadingError initialization."""
        error = ContentLoadingError(
            "Loading failed", source_location="data.json", source_type="file"
        )

        assert "Loading failed" in str(error)
        assert error.context["items_processed"] == 0
        assert error.context["items_failed"] == 0

    def test_init_with_stats(self):
        """Test ContentLoadingError with processing statistics."""
        error = ContentLoadingError(
            "Partial loading failure",
            items_processed=10,
            items_failed=3,
            source_location="large_file.json",
        )

        assert error.context["items_processed"] == 10
        assert error.context["items_failed"] == 3
        assert "items_processed=10" in str(error)
        assert "items_failed=3" in str(error)


class TestReferenceTrackingError:
    """Test ReferenceTrackingError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ReferenceTrackingError initialization."""
        error = ReferenceTrackingError(
            "Reference tracking failed",
            reference_type="spell",
            reference_name="Fireball",
        )

        assert "Reference tracking failed" in str(error)
        assert error.context["reference_type"] == "spell"
        assert error.context["reference_name"] == "Fireball"

    def test_init_with_context(self):
        """Test ReferenceTrackingError with additional context."""
        error = ReferenceTrackingError(
            "Tracking error",
            reference_type="creature",
            reference_name="Dragon",
            source="MM",
            location="adventure.json",
        )

        assert error.context["reference_type"] == "creature"
        assert error.context["reference_name"] == "Dragon"
        assert error.context["source"] == "MM"
        assert error.context["location"] == "adventure.json"


class TestConfigurationError:
    """Test ConfigurationError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic ConfigurationError initialization."""
        error = ConfigurationError(
            "Config error", config_key="paper_size", config_source="user_config"
        )

        assert "Config error" in str(error)
        assert error.context["config_key"] == "paper_size"
        assert error.context["config_source"] == "user_config"

    def test_init_with_context(self):
        """Test ConfigurationError with additional context."""
        error = ConfigurationError(
            "Invalid configuration",
            config_key="fonts.main_font",
            config_source="CLI",
            provided_value="NonexistentFont",
            valid_values=["Times", "Arial", "Helvetica"],
        )

        assert error.context["config_key"] == "fonts.main_font"
        assert error.context["config_source"] == "CLI"
        assert error.context["provided_value"] == "NonexistentFont"
        assert error.context["valid_values"] == ["Times", "Arial", "Helvetica"]


class TestTemplateCompositionError:
    """Test TemplateCompositionError class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init_basic(self):
        """Test basic TemplateCompositionError initialization."""
        error = TemplateCompositionError(
            "Template error",
            template_name="base.tex.j2",
            component_name="header.tex.j2",
        )

        assert "Template error" in str(error)
        assert error.context["template_name"] == "base.tex.j2"
        assert error.context["component_name"] == "header.tex.j2"

    def test_init_with_context(self):
        """Test TemplateCompositionError with additional context."""
        error = TemplateCompositionError(
            "Component not found",
            template_name="document.tex.j2",
            component_name="missing_component.tex.j2",
            search_paths=["/templates", "/components"],
            suggested_fix="Check component name spelling",
        )

        assert error.context["template_name"] == "document.tex.j2"
        assert error.context["component_name"] == "missing_component.tex.j2"
        assert error.context["search_paths"] == ["/templates", "/components"]
        assert error.context["suggested_fix"] == "Check component name spelling"


class TestErrorDecorators:
    """Test error handling decorators."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_handle_content_source_error_passthrough(self):
        """Test content source error decorator passes through architecture errors."""

        @handle_content_source_error
        def failing_function():
            raise ContentSourceError("Original error", source_location="test.json")

        with pytest.raises(ContentSourceError) as exc_info:
            failing_function()

        assert "Original error" in str(exc_info.value)
        assert exc_info.value.context["source_location"] == "test.json"

    def test_handle_content_source_error_wrap_generic(self):
        """Test content source error decorator wraps generic exceptions."""

        class MockSource:
            location = "mock_source.json"

        @handle_content_source_error
        def failing_function(source):
            raise ValueError("Generic error")

        mock_source = MockSource()

        with pytest.raises(ContentSourceError) as exc_info:
            failing_function(mock_source)

        wrapped_error = exc_info.value
        assert "Unexpected error in content source operation" in str(wrapped_error)
        assert wrapped_error.context["source_location"] == "mock_source.json"
        assert wrapped_error.context["source_type"] == "MockSource"
        assert wrapped_error.context["original_error"] == "Generic error"
        assert wrapped_error.context["original_type"] == "ValueError"

    def test_handle_content_source_error_no_args(self):
        """Test content source error decorator with no arguments."""

        @handle_content_source_error
        def failing_function():
            raise RuntimeError("No args error")

        with pytest.raises(ContentSourceError) as exc_info:
            failing_function()

        wrapped_error = exc_info.value
        assert wrapped_error.context["source_location"] == "unknown"
        assert wrapped_error.context["source_type"] == "unknown"

    def test_handle_reference_tracking_error_passthrough(self):
        """Test reference tracking error decorator passes through architecture errors."""

        @handle_reference_tracking_error
        def failing_function():
            raise ReferenceTrackingError("Original tracking error")

        with pytest.raises(ReferenceTrackingError) as exc_info:
            failing_function()

        assert "Original tracking error" in str(exc_info.value)

    def test_handle_reference_tracking_error_wrap_generic(self):
        """Test reference tracking error decorator wraps generic exceptions."""

        @handle_reference_tracking_error
        def failing_function(content_type="spell", name="Fireball"):
            raise KeyError("Missing reference")

        with pytest.raises(ReferenceTrackingError) as exc_info:
            failing_function()

        wrapped_error = exc_info.value
        assert "Unexpected error in reference tracking" in str(wrapped_error)
        assert wrapped_error.context["reference_type"] == "spell"
        assert wrapped_error.context["reference_name"] == "Fireball"
        assert wrapped_error.context["original_error"] == "Missing reference"

    def test_handle_reference_tracking_error_extract_kwargs(self):
        """Test reference tracking error decorator extracts context from kwargs."""

        @handle_reference_tracking_error
        def failing_function(**kwargs):
            raise IndexError("Index error")

        with pytest.raises(ReferenceTrackingError) as exc_info:
            failing_function(
                content_type="creature", name="Dragon", extra_arg="ignored"
            )

        wrapped_error = exc_info.value
        assert wrapped_error.context["reference_type"] == "creature"
        assert wrapped_error.context["reference_name"] == "Dragon"


class TestErrorFormatting:
    """Test error formatting functions."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_format_error_for_user_content_validation(self):
        """Test user-friendly formatting of ContentValidationError."""
        error = ContentValidationError("Validation failed", source_location="test.json")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Content validation failed:")
        assert "Validation failed" in formatted

    def test_format_error_for_user_content_loading(self):
        """Test user-friendly formatting of ContentLoadingError."""
        error = ContentLoadingError("Loading failed", source_location="data.json")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Content loading failed:")
        assert "Loading failed" in formatted

    def test_format_error_for_user_content_source(self):
        """Test user-friendly formatting of ContentSourceError."""
        error = ContentSourceError("Source error", source_location="file.json")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Content source error:")
        assert "Source error" in formatted

    def test_format_error_for_user_reference_tracking(self):
        """Test user-friendly formatting of ReferenceTrackingError."""
        error = ReferenceTrackingError("Tracking error", reference_type="spell")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Reference tracking error:")
        assert "Tracking error" in formatted

    def test_format_error_for_user_configuration(self):
        """Test user-friendly formatting of ConfigurationError."""
        error = ConfigurationError("Config error", config_key="paper_size")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Configuration error:")
        assert "Config error" in formatted

    def test_format_error_for_user_template_composition(self):
        """Test user-friendly formatting of TemplateCompositionError."""
        error = TemplateCompositionError("Template error", template_name="base.tex")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Template error:")
        assert "Template error" in formatted

    def test_format_error_for_user_generic_architecture(self):
        """Test user-friendly formatting of generic ArchitectureError."""
        error = ArchitectureError("Generic architecture error")

        formatted = format_error_for_user(error)

        assert formatted.startswith("Architecture error:")
        assert "Generic architecture error" in formatted


class TestErrorLogging:
    """Test error logging functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    @patch("studiorum.core.errors.architecture_errors.get_logger")
    def test_log_architecture_error_basic(self, mock_get_logger):
        """Test basic error logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        error = ArchitectureError("Test error")

        log_architecture_error(error)

        # Should log the error
        mock_logger.error.assert_called()
        call_args = mock_logger.error.call_args_list
        assert any("ArchitectureError: Test error" in str(call) for call in call_args)

    @patch("studiorum.core.errors.architecture_errors.get_logger")
    def test_log_architecture_error_with_context(self, mock_get_logger):
        """Test error logging with context."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        context = {"file": "test.json", "line": 42}
        error = ArchitectureError("Test error", context)

        log_architecture_error(error)

        # Should log error and context
        call_args = mock_logger.error.call_args_list
        assert len(call_args) >= 2

        # Check that context was logged
        context_logged = any("Error context:" in str(call) for call in call_args)
        assert context_logged

    @patch("studiorum.core.errors.architecture_errors.get_logger")
    def test_log_architecture_error_with_cause(self, mock_get_logger):
        """Test error logging with original cause."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create error with cause
        try:
            raise ValueError("Original error")
        except ValueError as e:
            wrapped_error = ArchitectureError("Wrapped error")
            wrapped_error.__cause__ = e

        log_architecture_error(wrapped_error)

        # Should log error and original cause
        call_args = mock_logger.error.call_args_list
        assert len(call_args) >= 2

        # Check that original exception was logged
        cause_logged = any("Original exception:" in str(call) for call in call_args)
        assert cause_logged

    def test_log_architecture_error_custom_logger(self):
        """Test error logging with custom logger."""
        custom_logger = Mock()

        error = ArchitectureError("Test error")

        log_architecture_error(error, custom_logger)

        # Should use custom logger
        custom_logger.error.assert_called()


@pytest.mark.integration
class TestArchitectureErrorsIntegration:
    """Integration tests for architecture errors."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_error_hierarchy_and_handling(self):
        """Test complete error hierarchy and handling workflow."""

        # Test that errors maintain proper inheritance
        content_error = ContentSourceError("Source error", source_location="test.json")
        validation_error = ContentValidationError(
            "Validation error", source_location="test.json"
        )
        loading_error = ContentLoadingError(
            "Loading error", source_location="test.json"
        )

        # All should be ArchitectureError instances
        assert isinstance(content_error, ArchitectureError)
        assert isinstance(validation_error, ArchitectureError)
        assert isinstance(loading_error, ArchitectureError)

        # Validation and Loading should also be ContentSourceError instances
        assert isinstance(validation_error, ContentSourceError)
        assert isinstance(loading_error, ContentSourceError)

        # Test error formatting works for all types
        errors = [content_error, validation_error, loading_error]
        for error in errors:
            formatted = format_error_for_user(error)
            assert isinstance(formatted, str)
            assert len(formatted) > 0

        # Test logging works for all types
        with patch(
            "studiorum.core.errors.architecture_errors.get_logger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            for error in errors:
                log_architecture_error(error)

            # Should have logged all errors
            assert mock_logger.error.call_count >= len(errors)

    def test_decorator_integration_with_actual_functions(self):
        """Test decorators work with realistic function scenarios."""

        class MockContentSource:
            def __init__(self, location):
                self.location = location

            @handle_content_source_error
            def load_content(self):
                # Simulate a loading failure
                raise FileNotFoundError(f"File not found: {self.location}")

        source = MockContentSource("missing_file.json")

        with pytest.raises(ContentSourceError) as exc_info:
            source.load_content()

        error = exc_info.value
        assert error.context["source_location"] == "missing_file.json"
        assert error.context["source_type"] == "MockContentSource"
        assert "FileNotFoundError" in error.context["original_type"]

        # Test formatting the resulting error
        formatted = format_error_for_user(error)
        assert "Content source error:" in formatted

        # Test logging the resulting error
        with patch(
            "studiorum.core.errors.architecture_errors.get_logger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            log_architecture_error(error)

            mock_logger.error.assert_called()

    def test_context_preservation_through_error_chain(self):
        """Test that context is preserved through error wrapping."""

        original_context = {"file": "source.json", "line": 100}

        # Create base error with context
        base_error = ArchitectureError("Base error", original_context)

        # Wrap in more specific error
        source_error = ContentSourceError(
            f"Source error: {base_error}",
            source_location="wrapper.json",
            source_type="file",
            original_context=original_context,
        )

        # Context should be preserved and extended
        assert source_error.context["source_location"] == "wrapper.json"
        assert source_error.context["source_type"] == "file"
        assert source_error.context["original_context"] == original_context

        # String representation should include all context
        error_str = str(source_error)
        assert "source_location=wrapper.json" in error_str
        assert "source_type=file" in error_str
