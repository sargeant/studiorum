"""Tests for LaTeX entry processor edge cases."""

from unittest.mock import Mock

import pytest

from studiorum.renderers.core.interfaces import RenderingContext
from studiorum.renderers.latex.entry_processor import RecursiveEntryProcessor
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestRecursiveEntryProcessorEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.processor = RecursiveEntryProcessor()
        self.context = RenderingContext(output_format="latex")

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(
            side_effect=lambda text, context=None: text
        )
        self.context = RenderingContext(
            output_format="latex", metadata={"tag_resolver": mock_tag_resolver}
        )

    def test_process_section_no_name_no_entries(self):
        """Test section processing with no name or entries."""
        section = {"type": "section"}
        result = self.processor.process_entry_dict(section, self.context)

        assert result == ""

    def test_process_section_name_only(self):
        """Test section processing with name but no entries."""
        section = {"type": "section", "name": "Empty Section"}
        result = self.processor.process_entry_dict(section, self.context)

        assert result == "\\section{Empty Section}"

    def test_process_entries_block_no_name_no_entries(self):
        """Test entries block with no name or entries."""
        block = {"type": "entries"}
        result = self.processor.process_entry_dict(block, self.context)

        assert result == ""

    def test_process_generic_entry_no_name_no_entries(self):
        """Test generic entry with no name or entries."""
        entry = {"some_field": "value"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == ""

    def test_process_quote_empty_entries(self):
        """Test quote processing with empty entries."""
        quote = {"type": "quote", "entries": []}
        result = self.processor.process_entry_dict(quote, self.context)

        assert "\\begin{quotation}" in result
        assert "\\end{quotation}" in result

    def test_depth_tracking_complex_nesting(self):
        """Test depth tracking with complex nesting."""
        complex_entry = {
            "type": "section",
            "name": "Level 0",
            "entries": [
                {
                    "type": "entries",
                    "name": "Level 1",
                    "entries": [
                        {
                            "type": "section",
                            "name": "Level 2",
                            "entries": [
                                {"name": "Level 3", "entries": ["Deep content"]}
                            ],
                        }
                    ],
                }
            ],
        }

        result = self.processor.process_entry_dict(complex_entry, self.context)

        assert "\\section{Level 0}" in result
        # "entries" type uses depth+1, so Level 1 becomes subsubsection
        assert "\\subsubsection{Level 1}" in result
        assert "\\subsubsection{Level 2}" in result
        # Generic entry with depth tracking
        assert "\\subparagraph{Level 3}" in result

    def test_table_with_non_list_rows(self):
        """Test table processing with non-list rows."""
        table = {"type": "table", "colLabels": ["A"], "rows": ["not a list", 123, None]}
        result = self.processor._process_basic_table(table, self.context)

        # Should handle gracefully - max_cols calculation should work
        assert "\\begin{tabular}{l}" in result
