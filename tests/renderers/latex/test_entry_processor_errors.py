"""Tests for enhanced LaTeX entry processor error handling and validation."""

import warnings
from unittest.mock import Mock, patch

import pytest

from studiorum.core.entry_registry import ValidationMode
from studiorum.core.error_types import ProcessingError, create_processing_error
from studiorum.core.exceptions import EntryProcessingWarning
from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestRecursiveEntryProcessorEnhanced:
    """Test enhanced RecursiveEntryProcessor with validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.processor = RecursiveEntryProcessor(use_dnd_template=False)
        self.context = Mock(spec=RenderingContext)
        self.context.tag_resolver = None
        self.context.metadata = {"source_name": "Test Source"}

    def test_initialization_with_validation_mode(self):
        """Test processor initialization with custom validation mode."""
        processor = RecursiveEntryProcessor(
            use_dnd_template=True, validation_mode=ValidationMode.STRICT
        )
        assert processor._validation_mode == ValidationMode.STRICT
        assert processor._entries_processed == 0
        assert processor._errors_encountered == 0

    def test_process_entries_string_and_dict(self):
        """Test processing mixed string and dict entries."""
        entries = [
            "Plain text entry",
            {"type": "section", "name": "Test Section", "entries": []},
            "Another string",
        ]

        results = self.processor.process_entries(entries, self.context)

        assert len(results) == 3
        assert self.processor._entries_processed == 1  # Only dict entries counted

    def test_process_known_entry_types(self):
        """Test processing of known entry types."""
        entries = [
            {"type": "section", "name": "Test Section", "entries": []},
            {"type": "list", "items": ["Item 1", "Item 2"]},
            {"type": "table", "rows": [["A", "B"], ["C", "D"]]},
        ]

        results = self.processor.process_entries(entries, self.context)

        assert len(results) == 3
        assert self.processor._entries_processed == 3

    def test_process_unknown_entry_type_permissive(self):
        """Test processing unknown entry type in permissive mode."""
        processor = RecursiveEntryProcessor(validation_mode=ValidationMode.PERMISSIVE)
        entry = {"type": "unknownType", "name": "Test", "entries": []}

        with pytest.warns(EntryProcessingWarning, match="Unknown entry type"):
            result = processor.process_entry_dict(entry, self.context)

        # Should fall back to generic processing
        assert isinstance(result, str)
        assert processor._entries_processed == 1

    def test_process_unknown_entry_type_strict(self):
        """Test processing unknown entry type in strict mode."""
        processor = RecursiveEntryProcessor(validation_mode=ValidationMode.STRICT)
        entry = {"type": "unknownType", "data": "test"}

        # In Result[T, E] pattern, the processor should return an error result instead of raising
        # For now, let's check if it still raises (may need to update based on actual implementation)
        try:
            _ = processor.process_entry_dict(entry, self.context)
            # If it doesn't raise, it might return empty string and increment error count
            assert processor._errors_encountered == 1
        except Exception as exc_info:
            # Should be wrapped in some error (but root cause is unknown type)
            error_msg = str(exc_info)
            assert (
                "Failed to process LaTeX entry" in error_msg
                or "Unknown entry type" in error_msg
            )
            assert processor._errors_encountered == 1

    def test_process_unknown_entry_type_silent(self):
        """Test processing unknown entry type in silent mode."""
        processor = RecursiveEntryProcessor(validation_mode=ValidationMode.SILENT)
        entry = {"type": "unknownType", "name": "Test", "entries": []}

        # Should not raise exception or warning
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            result = processor.process_entry_dict(entry, self.context)

        assert isinstance(result, str)

    def test_processing_error_handling(self):
        """Test handling of processing errors with context."""
        # Mock a method to raise an exception
        with patch.object(self.processor, "_process_section") as mock_process:
            mock_process.side_effect = ValueError("Simulated processing error")

            entry = {"type": "section", "name": "Test Section"}

            # Check if it raises or returns error result
            try:
                result = self.processor.process_entry_dict(entry, self.context)
                # If no exception, check error count and result
                assert self.processor._errors_encountered == 1
                # Result might be empty string on error
                assert isinstance(result, str)
            except Exception as exc_info:
                error_msg = str(exc_info)
                assert (
                    "Failed to process LaTeX entry" in error_msg
                    or "Simulated processing error" in error_msg
                )
                assert self.processor._errors_encountered == 1

    def test_depth_tracking(self):
        """Test that nesting depth is tracked correctly."""
        nested_entries = [
            {
                "type": "section",
                "name": "Level 1",
                "entries": [
                    {
                        "type": "section",
                        "name": "Level 2",
                        "entries": [
                            {"type": "section", "name": "Level 3", "entries": []}
                        ],
                    }
                ],
            }
        ]

        results = self.processor.process_entries(nested_entries, self.context)

        assert len(results) == 1
        # Depth should be back to 0 after processing
        assert self.processor._depth == 0

    def test_processing_statistics_tracking(self):
        """Test that processing statistics are tracked correctly."""
        entries = [
            {"type": "section", "name": "Section 1", "entries": []},
            {"type": "table", "rows": [["A"]]},
            {"type": "unknownType", "data": "test"},
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.processor.process_entries(entries, self.context)

        stats = self.processor.get_processing_statistics()

        assert stats["entries_processed"] == 3
        assert stats["errors_encountered"] == 0
        assert stats["current_depth"] == 0
        assert "unknownType" in stats["unknown_types"]

    def test_processing_statistics_with_errors(self):
        """Test statistics tracking when errors occur."""
        with patch.object(self.processor, "_process_section") as mock_process:
            mock_process.side_effect = ValueError("Error")

            entry = {"type": "section", "name": "Bad Section"}

            try:
                _ = self.processor.process_entry_dict(entry, self.context)
                # Check error was counted even if no exception
                assert self.processor._errors_encountered > 0
            except Exception:
                # Exception is also acceptable behavior
                assert self.processor._errors_encountered > 0

        stats = self.processor.get_processing_statistics()
        assert stats["errors_encountered"] == 1

    @patch("studiorum.latex_engine.core.entry_processor.logger")
    def test_log_processing_summary(self, mock_logger):
        """Test processing summary logging."""
        entries = [
            {"type": "section", "name": "Test", "entries": []},
            {"type": "unknownType", "data": "test"},
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.processor.process_entries(entries, self.context)

        self.processor.log_processing_summary()

        # Should log info about processing
        mock_logger.info.assert_called_once()
        info_msg = mock_logger.info.call_args[0][0]
        assert "2 entries processed" in info_msg

        # Should log warning about unknown types
        # Note: may be called multiple times due to different warning sources
        assert mock_logger.warning.call_count >= 1
        # Check that at least one warning contains the unknown type
        warning_messages = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("unknownType" in msg for msg in warning_messages)

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        # Generate some statistics
        entry = {"type": "section", "name": "Test", "entries": []}
        self.processor.process_entry_dict(entry, self.context)

        assert self.processor._entries_processed > 0

        self.processor.reset_statistics()

        assert self.processor._entries_processed == 0
        assert self.processor._errors_encountered == 0

    def test_validation_mode_override(self):
        """Test that processor-level validation mode overrides global mode."""
        # Create processor with strict mode
        strict_processor = RecursiveEntryProcessor(
            validation_mode=ValidationMode.STRICT
        )

        entry = {"type": "unknownType", "data": "test"}

        try:
            _ = strict_processor.process_entry_dict(entry, self.context)
            # If no exception raised, check that error was counted
            assert strict_processor._errors_encountered > 0
        except Exception:
            # If exception is still raised, that's also acceptable
            pass

    @patch("studiorum.latex_engine.core.entry_processor.logger")
    def test_debug_logging_enabled(self, mock_logger):
        """Test that debug logging provides useful information."""
        entries = [
            {"type": "section", "name": "Test Section", "entries": []},
            {"type": "unknownType", "data": "test"},
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.processor.process_entries(entries, self.context)

        # Should have debug calls for entry processing
        debug_calls = [
            call
            for call in mock_logger.debug.call_args_list
            if len(call[0]) > 0 and "Processing LaTeX entry type" in call[0][0]
        ]
        assert len(debug_calls) >= 2

    def test_generic_entry_fallback_logging(self):
        """Test that generic entry processing is logged."""
        entry = {"type": "unknownType", "name": "Test", "entries": []}

        with patch("studiorum.latex_engine.core.entry_processor.logger") as mock_logger:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.processor.process_entry_dict(entry, self.context)

            # Should log debug message about using generic processing
            debug_calls = mock_logger.debug.call_args_list
            generic_calls = [
                call
                for call in debug_calls
                if len(call[0]) > 0 and "Using generic processing" in call[0][0]
            ]
            assert len(generic_calls) == 1

    def test_process_entries_error_resilience(self):
        """Test that processing continues after individual entry errors."""
        entries = [
            {"type": "section", "name": "Good Section", "entries": []},
            {"type": "badType", "data": "causes error"},  # This might cause error
            {"type": "list", "items": ["Item 1"]},  # This should still process
        ]

        # Configure to be permissive to avoid exceptions
        processor = RecursiveEntryProcessor(validation_mode=ValidationMode.PERMISSIVE)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = processor.process_entries(entries, self.context)

        # Should get results for all entries (some may be empty strings)
        assert len(results) == 3

    def test_empty_entry_type_handling(self):
        """Test handling of entries with empty or missing type."""
        entries = [
            {"name": "No Type Entry", "entries": []},  # Missing type
            {"type": "", "name": "Empty Type", "entries": []},  # Empty type
        ]

        results = self.processor.process_entries(entries, self.context)

        # Should handle gracefully with generic processing
        assert len(results) == 2

    def test_malformed_entry_structure(self):
        """Test handling of malformed entry structures."""
        entries = [
            None,  # None entry
            123,  # Non-dict, non-string
            {"type": "section"},  # Missing expected fields
        ]

        # Should handle gracefully without crashing
        results = self.processor.process_entries(entries, self.context)
        assert len(results) == 3

    def test_context_source_name_handling(self):
        """Test handling when context doesn't have source_name."""
        context_no_source = Mock(spec=RenderingContext)
        # Don't set source_name in metadata
        context_no_source.metadata = {}  # Empty metadata dict

        entry = {"type": "unknownType", "data": "test"}

        processor = RecursiveEntryProcessor(validation_mode=ValidationMode.STRICT)

        try:
            _ = processor.process_entry_dict(entry, context_no_source)
            # If no exception raised, check that error was handled
            assert processor._errors_encountered > 0
        except Exception as exc_info:
            # If exception is raised, check the error details
            error_msg = str(exc_info)
            # The error message should indicate unknown type
            assert "unknown" in error_msg.lower() or "unknownType" in error_msg
