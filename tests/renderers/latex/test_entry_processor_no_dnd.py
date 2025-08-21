"""Tests for LaTeX entry processor without DND template."""

from unittest.mock import Mock

import pytest

from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestRecursiveEntryProcessorWithoutDNDTemplate:
    """Test processor without DND template."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.processor = RecursiveEntryProcessor(use_dnd_template=False)
        self.context = RenderingContext(output_format="latex")

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(
            side_effect=lambda text, context=None: f"processed_{text}"
        )
        self.context = RenderingContext(
            output_format="latex", metadata={"tag_resolver": mock_tag_resolver}
        )

    def test_process_inset_readaloud_without_dnd(self):
        """Test read-aloud inset without DND template."""
        entry = {"type": "insetReadaloud", "entries": ["Read this aloud"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{quotation}\\em" in result
        assert "processed_Read this aloud" in result
        assert "\\end{quotation}" in result

    def test_process_inset_with_name_without_dnd(self):
        """Test named inset without DND template."""
        entry = {
            "type": "inset",
            "name": "Important Note",
            "entries": ["This is important"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Important Note}" in result
        assert "\\begin{quotation}" in result
        assert "processed_This is important" in result
        assert "\\end{quotation}" in result

    def test_process_inset_without_name_without_dnd(self):
        """Test unnamed inset without DND template."""
        entry = {"type": "inset", "entries": ["Sidebar content"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{quotation}" in result
        assert "processed_Sidebar content" in result
        assert "\\end{quotation}" in result

    def test_process_table_without_dnd_template(self):
        """Test table processing without DND template (fallback to basic)."""
        entry = {
            "type": "table",
            "caption": "Test Table",
            "colLabels": ["Name", "Value"],
            "rows": [["Item 1", "10"]],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        # Should call _process_basic_table
        assert "\\begin{table}[ht]" in result
        assert "\\caption{Test Table}" in result
        assert "\\begin{tabular}{ll}" in result
        assert "Name & Value \\\\ \\hline" in result
        assert "Item 1 & 10 \\\\" in result

    def test_process_basic_table_empty_rows(self):
        """Test basic table processing with empty rows."""
        table = {"caption": "Empty", "colLabels": ["A", "B"], "rows": []}
        result = self.processor._process_basic_table(table, self.context)

        assert result == ""

    def test_process_basic_table_variable_row_lengths(self):
        """Test basic table with variable row lengths."""
        table = {
            "caption": "Variable Table",
            "colLabels": ["A", "B"],
            "rows": [
                ["1"],  # Shorter row
                ["2", "3", "4"],  # Longer row
            ],
        }
        result = self.processor._process_basic_table(table, self.context)

        # Should use max columns (3)
        assert "\\begin{tabular}{lll}" in result
        assert "A & B \\\\ \\hline" in result
        assert "1 \\\\" in result
        assert "2 & 3 & 4 \\\\" in result

    def test_process_basic_table_no_column_labels(self):
        """Test basic table without column labels."""
        table = {"caption": "No Headers", "rows": [["A", "B"], ["C", "D"]]}
        result = self.processor._process_basic_table(table, self.context)

        assert "\\begin{table}[ht]" in result
        assert "\\caption{No Headers}" in result
        assert "\\begin{tabular}{ll}" in result
        # Should not have header row
        assert "A & B \\\\" in result
        assert "C & D \\\\" in result

    def test_process_basic_table_no_caption(self):
        """Test basic table without caption."""
        table = {"colLabels": ["X", "Y"], "rows": [["1", "2"]]}
        result = self.processor._process_basic_table(table, self.context)

        assert "\\begin{table}[ht]" in result
        assert "\\caption" not in result
        assert "X & Y \\\\ \\hline" in result
