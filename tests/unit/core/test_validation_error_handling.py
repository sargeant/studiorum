"""Tests for validation error handling improvements (Issue #56)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from dnd5e.core.config.settings import Settings
from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.models.content import ContentType


class TestValidationErrorDeduplication:
    """Test validation error deduplication functionality."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def sample_validation_error(self) -> ValidationError:
        """Create a sample ValidationError for testing."""
        try:
            from pydantic import BaseModel, Field

            class TestModel(BaseModel):
                required_field: str = Field(...)

            TestModel(invalid_data="test")  # This will raise ValidationError
        except ValidationError as e:
            return e

        # Fallback if the above doesn't work
        return ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("required_field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

    def test_error_tracker_deduplicates_identical_errors(
        self, sample_validation_error: ValidationError
    ) -> None:
        """Test that identical validation errors are deduplicated."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()
        context = {"file": "test.json", "item_name": "test_item"}

        # First occurrence should return True (should log)
        assert tracker.should_log_error(sample_validation_error, context) is True
        tracker.record_error(sample_validation_error, context)

        # Second occurrence should return False (already logged)
        assert tracker.should_log_error(sample_validation_error, context) is False

    def test_error_tracker_different_files_still_deduplicated(
        self, sample_validation_error: ValidationError
    ) -> None:
        """Test that identical errors from different files are still deduplicated."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()
        context1 = {"file": "test1.json", "item_name": "test_item"}
        context2 = {"file": "test2.json", "item_name": "test_item"}

        # First occurrence should return True
        assert tracker.should_log_error(sample_validation_error, context1) is True
        tracker.record_error(sample_validation_error, context1)

        # Same error from different file should still be deduplicated
        assert tracker.should_log_error(sample_validation_error, context2) is False

        # But error should be recorded in both files for summary
        tracker.record_error(sample_validation_error, context2)
        summary = tracker.get_summary()

        # Should show error occurred in multiple files
        error_sig = list(summary.keys())[0]
        assert len(summary[error_sig]["files"]) == 2
        assert "test1.json" in summary[error_sig]["files"]
        assert "test2.json" in summary[error_sig]["files"]

    def test_error_tracker_different_errors_not_deduplicated(
        self, sample_validation_error: ValidationError
    ) -> None:
        """Test that different validation errors are not deduplicated."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()
        context = {"file": "test.json", "item_name": "test_item"}

        # Create a different validation error
        different_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "string_type",
                    "loc": ("different_field",),
                    "msg": "Input should be a valid string",
                    "input": 123,
                }
            ],
        )

        # Both errors should be allowed to log
        assert tracker.should_log_error(sample_validation_error, context) is True
        tracker.record_error(sample_validation_error, context)

        assert tracker.should_log_error(different_error, context) is True
        tracker.record_error(different_error, context)

        # Summary should show two different errors
        summary = tracker.get_summary()
        assert len(summary) == 2

    def test_error_tracker_summary_includes_counts(
        self, sample_validation_error: ValidationError
    ) -> None:
        """Test that error summary includes occurrence counts."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()
        context = {"file": "test.json", "item_name": "test_item"}

        # Record the same error multiple times (simulating different items)
        tracker.record_error(sample_validation_error, context)
        tracker.record_error(sample_validation_error, {**context, "item_name": "item2"})
        tracker.record_error(sample_validation_error, {**context, "item_name": "item3"})

        summary = tracker.get_summary()
        error_sig = list(summary.keys())[0]

        assert summary[error_sig]["count"] == 3
        assert len(summary[error_sig]["files"]) == 1
        assert "test.json" in summary[error_sig]["files"]


class TestValidationStrictnessConfiguration:
    """Test validation strictness configuration options."""

    def test_default_settings_include_validation_options(self) -> None:
        """Test that default settings include validation configuration."""
        settings = Settings()

        # Should have default validation settings
        assert hasattr(settings, "validation_strictness")
        assert hasattr(settings, "validation_summary")
        assert hasattr(settings, "max_duplicate_errors")

    def test_validation_strictness_levels(self) -> None:
        """Test different validation strictness levels."""
        from dnd5e.core.validation.strictness import ValidationStrictness

        # Test that all expected levels exist
        assert ValidationStrictness.STRICT in ValidationStrictness
        assert ValidationStrictness.NORMAL in ValidationStrictness
        assert ValidationStrictness.LENIENT in ValidationStrictness

    @patch.dict("os.environ", {"VALIDATION_STRICTNESS": "strict"})
    def test_validation_strictness_from_environment(self) -> None:
        """Test that validation strictness can be set from environment."""
        settings = Settings()
        assert settings.validation_strictness == "strict"

    @patch.dict("os.environ", {"VALIDATION_SUMMARY": "true"})
    def test_validation_summary_from_environment(self) -> None:
        """Test that validation summary can be enabled from environment."""
        settings = Settings()
        assert settings.validation_summary is True


class TestJsonLoaderValidationIntegration:
    """Test integration of validation error handling with JsonDataLoader."""

    @pytest.fixture
    def mock_validation_tracker(self) -> MagicMock:
        """Mock ValidationErrorTracker for testing."""
        tracker = MagicMock()
        tracker.should_log_error.return_value = True
        tracker.get_summary.return_value = {}
        return tracker

    @patch("dnd5e.core.loaders.json_loader.ValidationErrorTracker")
    def test_json_loader_uses_error_tracker(
        self, mock_tracker_class: MagicMock, mock_validation_tracker: MagicMock
    ) -> None:
        """Test that JsonDataLoader uses ValidationErrorTracker for error handling."""
        mock_tracker_class.return_value = mock_validation_tracker

        loader = JsonDataLoader(ContentType.SPELL)

        # Simulate validation error during content creation
        with patch.object(loader._content_factory, "create_content") as mock_create:
            validation_error = ValidationError.from_exception_data(
                "TestModel",
                [
                    {
                        "type": "missing",
                        "loc": ("field",),
                        "msg": "Field required",
                        "input": {},
                    }
                ],
            )
            mock_create.side_effect = validation_error

            # Call load_from_data which should trigger error handling
            data = {"spell": [{"name": "Test Spell", "level": 1, "school": "A"}]}
            path = Path("/test/path.json")

            loader.load_from_data(data, path)

            # Verify tracker was used
            mock_tracker_class.assert_called_once()
            mock_validation_tracker.should_log_error.assert_called()
            mock_validation_tracker.record_error.assert_called()

    @patch("dnd5e.core.loaders.json_loader.get_settings")
    @patch("dnd5e.core.loaders.json_loader.ValidationErrorTracker")
    def test_json_loader_respects_strictness_setting(
        self, mock_tracker_class: MagicMock, mock_get_settings: MagicMock
    ) -> None:
        """Test that JsonDataLoader respects validation strictness settings."""
        mock_validation_tracker = MagicMock()
        mock_tracker_class.return_value = mock_validation_tracker

        # Test strict mode - should raise on validation error
        mock_settings = MagicMock()
        mock_settings.validation_strictness = "strict"
        mock_settings.validation_summary = False
        mock_get_settings.return_value = mock_settings

        loader = JsonDataLoader(ContentType.SPELL)

        with patch.object(loader._content_factory, "create_content") as mock_create:
            validation_error = ValidationError.from_exception_data(
                "TestModel",
                [
                    {
                        "type": "missing",
                        "loc": ("field",),
                        "msg": "Field required",
                        "input": {},
                    }
                ],
            )
            mock_create.side_effect = validation_error

            data = {"spell": [{"name": "Test Spell", "level": 1, "school": "A"}]}
            path = Path("/test/path.json")

            # In strict mode, should raise the validation error
            with pytest.raises(ValidationError):
                loader.load_from_data(data, path)

    @patch("dnd5e.core.loaders.json_loader.ValidationErrorTracker")
    def test_json_loader_logs_summary_when_enabled(
        self, mock_tracker_class: MagicMock, mock_validation_tracker: MagicMock
    ) -> None:
        """Test that JsonDataLoader logs validation summary when enabled."""
        mock_tracker_class.return_value = mock_validation_tracker
        mock_validation_tracker.get_summary.return_value = {
            "error_signature_1": {
                "count": 5,
                "files": ["file1.json", "file2.json"],
                "error_type": "missing_field",
                "message": "Field required",
                "field_path": "test_field",
            }
        }

        with patch("dnd5e.core.config.settings.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.validation_summary = True
            mock_get_settings.return_value = mock_settings

            loader = JsonDataLoader(ContentType.SPELL)

            with patch("dnd5e.core.loaders.json_loader.logger") as mock_logger:
                # Call summary logging method
                loader._log_validation_summary()

                # Verify summary was logged
                mock_logger.info.assert_called()
                # Check that summary information was logged
                calls = mock_logger.info.call_args_list
                summary_calls = [
                    call for call in calls if "Validation Summary" in str(call)
                ]
                assert len(summary_calls) > 0


class TestValidationErrorMessages:
    """Test improved validation error messages with contextual information."""

    def test_error_message_includes_context(self) -> None:
        """Test that error messages include contextual information."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()

        validation_error = ValidationError.from_exception_data(
            "Spell",
            [
                {
                    "type": "missing",
                    "loc": ("level",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        context = {
            "file": "/path/to/spells-phb.json",
            "item_name": "Magic Missile",
            "content_type": "SPELL",
        }

        formatted_message = tracker.format_error_message(validation_error, context)

        # Verify contextual information is included
        assert "Magic Missile" in formatted_message
        assert "spells-phb.json" in formatted_message
        assert "level" in formatted_message
        assert "Field required" in formatted_message

    def test_error_message_includes_suggested_fixes(self) -> None:
        """Test that error messages include suggested fixes for common issues."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()

        # Test missing level field for spell
        validation_error = ValidationError.from_exception_data(
            "Spell",
            [
                {
                    "type": "missing",
                    "loc": ("level",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        context = {"content_type": "SPELL", "file": "test.json", "item_name": "test"}
        formatted_message = tracker.format_error_message(validation_error, context)

        # Should include suggestion for missing spell level
        assert "Suggestion:" in formatted_message
        assert "level" in formatted_message.lower()

    def test_error_categorization(self) -> None:
        """Test that errors are properly categorized."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()

        missing_field_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        type_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "int_parsing",
                    "loc": ("number_field",),
                    "msg": "Input should be a valid integer",
                    "input": "not_a_number",
                }
            ],
        )

        # Test categorization
        assert (
            tracker._categorize_error(missing_field_error) == "missing_required_fields"
        )
        assert tracker._categorize_error(type_error) == "type_validation_errors"


class TestPerformanceImpact:
    """Test that validation error improvements don't significantly impact performance."""

    def test_error_tracker_performance_with_many_errors(self) -> None:
        """Test that error tracker performs well with many duplicate errors."""
        import time

        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()

        validation_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        context = {"file": "test.json", "item_name": "test_item"}

        # Time how long it takes to process many duplicate errors
        start_time = time.time()

        for i in range(1000):
            tracker.should_log_error(
                validation_error, {**context, "item_name": f"item_{i}"}
            )
            tracker.record_error(
                validation_error, {**context, "item_name": f"item_{i}"}
            )

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process 1000 errors in reasonable time (< 1 second)
        assert processing_time < 1.0

        # Verify deduplication is working
        summary = tracker.get_summary()
        assert len(summary) == 1  # Only one unique error type

        error_sig = list(summary.keys())[0]
        assert summary[error_sig]["count"] == 1000

    def test_hash_collision_handling(self) -> None:
        """Test that the system handles potential hash collisions gracefully."""
        from dnd5e.core.validation.error_tracker import ValidationErrorTracker

        tracker = ValidationErrorTracker()

        # Create two different errors that might have similar characteristics
        error1 = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field1",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        error2 = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field2",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        context = {"file": "test.json", "item_name": "test_item"}

        # Both errors should be allowed to log (they're different)
        assert tracker.should_log_error(error1, context) is True
        tracker.record_error(error1, context)

        assert tracker.should_log_error(error2, context) is True
        tracker.record_error(error2, context)

        # Summary should show two different errors
        summary = tracker.get_summary()
        assert len(summary) == 2


class TestBackwardCompatibility:
    """Test that changes maintain backward compatibility."""

    def test_existing_json_loader_behavior_preserved(self) -> None:
        """Test that existing JsonDataLoader behavior is preserved."""
        loader = JsonDataLoader(ContentType.SPELL)

        # Test that basic functionality still works
        spell_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "level": 1,
                    "school": "A",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {"type": "point", "distance": {"type": "self"}},
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["A test spell."],
                    "source": "TST",
                }
            ]
        }

        path = Path("/test/spells.json")
        result = loader.load_from_data(spell_data, path)

        # Should still return valid spell objects
        assert len(result) == 1
        assert hasattr(result[0], "name")
        assert result[0].name == "Test Spell"

    def test_existing_tests_still_pass(self) -> None:
        """Test that existing test patterns still work."""
        # This test verifies that our changes don't break existing functionality
        # by running a simplified version of existing tests

        loader = JsonDataLoader(ContentType.SPELL)

        # Test the _add_missing_required_fields method still works
        incomplete_spell = {"name": "Test", "source": "TST"}
        result = loader._add_missing_required_fields(incomplete_spell)

        # Should still add default fields as before
        assert "level" in result
        assert "school" in result
        assert "components" in result
        assert result["level"] == 0
        assert result["school"] == "T"
        assert result["components"] == {}
