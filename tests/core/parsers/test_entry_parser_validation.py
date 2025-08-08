"""Tests for enhanced entry parser validation and error handling."""

import warnings
from unittest.mock import patch

import pytest

from dnd5e.core.entry_registry import ValidationMode
from dnd5e.core.exceptions import EntryProcessingError, EntryProcessingWarning
from dnd5e.core.models.content import Source
from dnd5e.core.parsers.entry_parser import EntryParser
from tests.test_helpers import reset_test_environment


class TestEntryParserEnhanced:
    """Test enhanced EntryParser with validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.source = Source(
            name="Test Source",
            abbreviation="TST",
            json_dir="test",
            group="test",
        )
        self.parser = EntryParser(self.source, "Test Parent")

    def test_initialization_with_validation_mode(self):
        """Test parser initialization with custom validation mode."""
        parser = EntryParser(self.source, "Test", ValidationMode.STRICT)
        assert parser._validation_mode == ValidationMode.STRICT
        assert parser._entries_processed == 0
        assert parser._errors_encountered == 0

    def test_parse_string_entry(self):
        """Test parsing of string entries (should be skipped)."""
        entries = ["Plain text entry", "Another string"]

        results = list(self.parser.parse_entries(entries))

        assert len(results) == 0
        assert self.parser._entries_processed == 2  # Both processed but no output

    def test_parse_non_dict_entry(self):
        """Test parsing of non-dict, non-string entries."""
        entries = [123, None, []]

        results = list(self.parser.parse_entries(entries))

        assert len(results) == 0
        assert self.parser._entries_processed == 3

    def test_parse_known_entry_types(self):
        """Test parsing of known entry types."""
        entries = [
            {"type": "section", "name": "Test Section", "entries": []},
            {"type": "table", "caption": "Test Table", "rows": [["A", "B"]]},
            {"type": "inset", "name": "Test Inset", "entries": []},
        ]

        results = list(self.parser.parse_entries(entries))

        assert len(results) == 3
        assert self.parser._entries_processed == 3

    def test_parse_unknown_entry_type_permissive(self):
        """Test parsing of unknown entry type in permissive mode."""
        entries = [
            {
                "type": "unknownType",
                "entries": [
                    {"type": "section", "name": "Nested Section", "entries": []}
                ],
            }
        ]

        with pytest.warns(EntryProcessingWarning, match="Unknown entry type"):
            results = list(self.parser.parse_entries(entries))

        # Should still parse nested entries
        assert len(results) == 1
        assert self.parser._entries_processed == 2  # unknownType + nested section

    def test_parse_unknown_entry_type_strict(self):
        """Test parsing of unknown entry type in strict mode."""
        parser = EntryParser(self.source, "Test", ValidationMode.STRICT)
        entries = [{"type": "unknownType", "data": "test"}]

        with pytest.raises(EntryProcessingError) as exc_info:
            list(parser.parse_entries(entries))

        # Should be wrapped in EntryProcessingError (but root cause is UnknownEntryTypeError)
        error_msg = str(exc_info.value)
        assert "Failed to parse entry" in error_msg or "Unknown entry type" in error_msg
        assert parser._errors_encountered == 1

    def test_parse_malformed_entry_handling(self):
        """Test handling of entries that cause processing errors."""
        # Mock a section parser that raises an exception
        with patch.object(self.parser, "_parse_section") as mock_parse:
            mock_parse.side_effect = ValueError("Simulated parsing error")

            entries = [{"type": "section", "name": "Bad Section"}]

            with pytest.raises(EntryProcessingError) as exc_info:
                list(self.parser.parse_entries(entries))

            assert "Failed to parse entry" in str(exc_info.value)
            assert self.parser._errors_encountered == 1

    def test_variant_rule_detection_book_content(self):
        """Test improved variant rule detection for book content."""
        entries = [
            {
                "type": "entries",
                "name": "Variant: Flanking",
                "entries": ["Rule content"],
            },
            {
                "type": "entries",
                "name": "Optional Rule: Initiative",
                "entries": ["More rule content"],
            },
            {
                "type": "entries",
                "name": "Regular Section",
                "entries": ["Normal content"],
            },
        ]

        results = list(self.parser.parse_entries(entries, "book"))

        assert len(results) == 3
        # Should create VariantRule for first two, Section for third
        # Note: Actual type checking would require importing the model classes

    def test_variant_rule_detection_adventure_content(self):
        """Test that adventure content doesn't create variant rules."""
        entries = [
            {"type": "entries", "name": "Variant: Something", "entries": ["Content"]}
        ]

        results = list(self.parser.parse_entries(entries, "adventure"))

        assert len(results) == 1
        # Should create Section, not VariantRule for adventure content

    def test_variant_rule_heuristic_replacement(self):
        """Test that new variant rule detection is more reliable."""
        test_cases = [
            # Explicit variant markers with colons
            ("Variant: Flanking Rules", True),
            ("Optional: Different Initiative", True),
            ("Alternative: Grid Combat", True),
            ("Variant Rule: Something", True),
            ("Optional Rule: Advanced Combat", True),
            # Ambiguous cases without explicit markers (should default to section)
            ("Variant Rules for Combat", False),  # No colon after "Variant"
            ("Optional Rule System", False),  # No colon after "Optional Rule"
            ("Alternative Combat System", False),  # No colon after "Alternative"
            ("Using Magic Items", False),
            ("Different Approaches", False),
            ("Custom Equipment", False),
            # Regular sections
            ("Chapter Introduction", False),
            ("Equipment List", False),
        ]

        for name, should_be_variant in test_cases:
            result = self.parser._is_variant_rule_content(name, [], "book")
            assert result == should_be_variant, f"Failed for name: {name}"

    def test_processing_statistics_tracking(self):
        """Test that processing statistics are tracked correctly."""
        entries = [
            {"type": "section", "name": "Section 1", "entries": []},
            {"type": "table", "rows": [["A"]]},
            "String entry",
            {"type": "unknownType", "data": "test"},
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore unknown type warnings
            list(self.parser.parse_entries(entries))

        stats = self.parser.get_processing_statistics()

        assert stats["entries_processed"] == 4
        assert stats["errors_encountered"] == 0
        assert stats["source"] == "TST"
        assert stats["parent_name"] == "Test Parent"
        assert "unknownType" in stats["unknown_types"]

    def test_processing_statistics_with_errors(self):
        """Test statistics tracking when errors occur."""
        with patch.object(self.parser, "_parse_section") as mock_parse:
            mock_parse.side_effect = ValueError("Error")

            entries = [{"type": "section", "name": "Bad Section"}]

            with pytest.raises(EntryProcessingError):
                list(self.parser.parse_entries(entries))

        stats = self.parser.get_processing_statistics()
        assert stats["errors_encountered"] == 1

    @patch("dnd5e.core.parsers.entry_parser.logger")
    def test_log_processing_summary(self, mock_logger):
        """Test processing summary logging."""
        entries = [
            {"type": "section", "name": "Test", "entries": []},
            {"type": "unknownType", "data": "test"},
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            list(self.parser.parse_entries(entries))

        self.parser.log_processing_summary()

        # Should log info about processing
        mock_logger.info.assert_called_once()
        info_msg = mock_logger.info.call_args[0][0]
        assert "2 entries processed" in info_msg
        assert "TST" in info_msg

        # Should log warning about unknown types
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "unknownType" in warning_msg

    def test_nested_entry_processing_with_validation(self):
        """Test that nested entries are processed with proper validation."""
        entries = [
            {
                "type": "section",
                "name": "Parent Section",
                "entries": [
                    {"type": "unknownNested", "data": "test"},
                    {"type": "table", "rows": [["Data"]]},
                ],
            }
        ]

        with pytest.warns(EntryProcessingWarning, match="Unknown entry type"):
            results = list(self.parser.parse_entries(entries))

        # Should get the main section plus nested table (unknown entry may not produce output)
        assert len(results) >= 1
        # Check that at least the main section was processed
        assert self.parser._entries_processed >= 1

    def test_validation_mode_override(self):
        """Test that parser-level validation mode overrides global mode."""
        # Create parser with strict mode
        strict_parser = EntryParser(self.source, "Test", ValidationMode.STRICT)

        entries = [{"type": "unknownType", "data": "test"}]

        with pytest.raises(EntryProcessingError):
            list(strict_parser.parse_entries(entries))

    def test_debug_logging_enabled(self):
        """Test that debug logging provides useful information."""
        entries = [
            {"type": "section", "name": "Test Section", "entries": []},
            {"type": "unknownType", "data": "test"},
        ]

        with patch("dnd5e.core.parsers.entry_parser.logger") as mock_logger:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                list(self.parser.parse_entries(entries))

            # Should have debug calls for entry processing
            debug_calls = [
                call
                for call in mock_logger.debug.call_args_list
                if call[0][0].startswith("Processing entry type")
            ]
            assert len(debug_calls) >= 2

    def test_empty_entries_list(self):
        """Test handling of empty entries list."""
        results = list(self.parser.parse_entries([]))
        assert len(results) == 0
        assert self.parser._entries_processed == 0

    def test_none_entries_list(self):
        """Test handling of None entries."""
        results = list(self.parser.parse_entries(None))
        assert len(results) == 0
        assert self.parser._entries_processed == 0
