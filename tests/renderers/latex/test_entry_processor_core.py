"""Tests for LaTeX entry processor core functionality."""

from unittest.mock import Mock

from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor


class TestRecursiveEntryProcessor:
    """Test recursive entry processor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor(use_dnd_template=True)
        self.context = RenderContext()
        self.context.include_images = True  # Enable image processing

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(side_effect=lambda x: f"processed_{x}")
        self.context.tag_resolver = mock_tag_resolver

    def test_init_default(self):
        """Test processor initialization with defaults."""
        processor = RecursiveEntryProcessor()
        assert processor.use_dnd_template is True
        assert processor._depth == 0

    def test_init_without_dnd_template(self):
        """Test processor initialization without DND template."""
        processor = RecursiveEntryProcessor(use_dnd_template=False)
        assert processor.use_dnd_template is False
        assert processor._depth == 0

    def test_process_entries_empty_list(self):
        """Test processing empty entries list."""
        result = self.processor.process_entries([], self.context)
        assert result == []

    def test_process_entries_string_only(self):
        """Test processing entries with only strings."""
        entries = ["Hello world", "Another string"]
        result = self.processor.process_entries(entries, self.context)

        assert len(result) == 2
        assert result[0] == "processed_Hello world"
        assert result[1] == "processed_Another string"

    def test_process_entries_mixed_types(self):
        """Test processing entries with mixed types."""
        entries = [
            "Plain text",
            {"type": "section", "name": "Test Section", "entries": []},
            123,  # Non-string, non-dict type
        ]
        result = self.processor.process_entries(entries, self.context)

        assert len(result) == 3
        assert result[0] == "processed_Plain text"
        assert "\\section{Test Section}" in result[1]
        assert result[2] == "123"

    def test_process_entry_dict_section(self):
        """Test processing section entry."""
        entry = {"type": "section", "name": "Test Section", "entries": ["Content here"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\section{Test Section}" in result
        assert "processed_Content here" in result

    def test_process_entry_dict_entries_block(self):
        """Test processing entries block."""
        entry = {
            "type": "entries",
            "name": "Entries Block",
            "entries": ["Some content"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\subsection{Entries Block}" in result
        assert "processed_Some content" in result

    def test_process_entry_dict_inset_readaloud(self):
        """Test processing read-aloud inset."""
        entry = {"type": "insetReadaloud", "entries": ["Read this aloud"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{DndReadAloud}" in result
        assert "processed_Read this aloud" in result
        assert "\\end{DndReadAloud}" in result

    def test_process_entry_dict_inset_with_name(self):
        """Test processing named inset."""
        entry = {
            "type": "inset",
            "name": "Important Note",
            "entries": ["This is important"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{DndSidebar}{Important Note}" in result
        assert "processed_This is important" in result
        assert "\\end{DndSidebar}" in result

    def test_process_entry_dict_inset_without_name(self):
        """Test processing unnamed inset."""
        entry = {"type": "inset", "entries": ["Sidebar content"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{DndSidebar}" in result
        assert "processed_Sidebar content" in result
        assert "\\end{DndSidebar}" in result

    def test_process_entry_dict_image_with_title(self):
        """Test processing image with title."""
        entry = {"type": "image", "href": "path/to/image.png", "title": "Test Image"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{figure}[htbp]" in result
        assert "\\centering" in result
        assert "\\includegraphics[width=0.6\\textwidth]{path/to/image.png}" in result
        assert "\\caption{Test Image}" in result
        assert "\\label{fig:test-image}" in result
        assert "\\end{figure}" in result

    def test_process_entry_dict_image_without_title(self):
        """Test processing image without title."""
        entry = {"type": "image", "href": "path/to/image.png"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{figure}[htbp]" in result
        assert "\\centering" in result
        assert "\\includegraphics[width=0.6\\textwidth]{path/to/image.png}" in result
        assert "\\end{figure}" in result
        # Should not have caption for images without title
        assert "\\caption{" not in result

    def test_process_entry_dict_image_no_href(self):
        """Test processing image without href."""
        entry = {"type": "image", "title": "Missing Image"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "% Image placeholder: Missing Image"

    def test_process_entry_dict_image_no_href_no_title(self):
        """Test processing image without href or title."""
        entry = {"type": "image"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "% Image placeholder"

    def test_process_entry_dict_list_unordered(self):
        """Test processing unordered list."""
        entry = {"type": "list", "items": ["First item", "Second item"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{itemize}" in result
        assert "\\item processed_First item" in result
        assert "\\item processed_Second item" in result
        assert "\\end{itemize}" in result

    def test_process_entry_dict_list_ordered(self):
        """Test processing ordered list."""
        entry = {
            "type": "list",
            "style": "ordered",
            "items": ["First item", "Second item"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{enumerate}" in result
        assert "\\item processed_First item" in result
        assert "\\item processed_Second item" in result
        assert "\\end{enumerate}" in result

    def test_process_entry_dict_list_empty(self):
        """Test processing empty list."""
        entry = {"type": "list", "items": []}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == ""

    def test_process_entry_dict_list_with_dict_items(self):
        """Test processing list with dictionary items."""
        entry = {
            "type": "list",
            "items": [
                "String item",
                {"type": "entries", "name": "Nested", "entries": ["content"]},
                123,  # Non-string, non-dict
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{itemize}" in result
        assert "\\item processed_String item" in result
        assert "\\item \\subsection{Nested}" in result
        assert "\\item 123" in result

    def test_process_entry_dict_table_with_dnd_template(self):
        """Test processing table with DND template."""
        entry = {
            "type": "table",
            "caption": "Test Table",
            "colLabels": ["Name", "Value"],
            "rows": [["Item 1", "10"], ["Item 2", "20"]],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{DndTable}[" in result
        assert "header={Test Table}" in result  # Updated format
        assert "{ll}" in result  # Column spec format
        assert "Name & Value \\\\" in result
        assert "processed_Item 1 & 10 \\\\" in result
        assert "processed_Item 2 & 20 \\\\" in result
        assert "\\end{DndTable}" in result

    def test_process_entry_dict_table_empty_rows(self):
        """Test processing table with empty rows."""
        entry = {
            "type": "table",
            "caption": "Empty Table",
            "colLabels": ["Name", "Value"],
            "rows": [],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "% Empty table: Empty Table"

    def test_process_entry_dict_table_no_caption_empty(self):
        """Test processing empty table without caption."""
        entry = {"type": "table", "rows": []}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "% Empty table"

    def test_process_entry_dict_quote(self):
        """Test processing quote entry."""
        entry = {"type": "quote", "entries": ["This is a quote"], "by": "Famous Person"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{quotation}" in result
        assert "\\em" in result
        assert "processed_This is a quote" in result
        assert "\\hfill --- Famous Person" in result
        assert "\\end{quotation}" in result

    def test_process_entry_dict_quote_no_by(self):
        """Test processing quote without attribution."""
        entry = {"type": "quote", "entries": ["Anonymous quote"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{quotation}" in result
        assert "processed_Anonymous quote" in result
        assert "\\hfill ---" not in result

    def test_process_entry_dict_generic(self):
        """Test processing generic entry."""
        entry = {"name": "Generic Entry", "entries": ["Some content"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\subsection{Generic Entry}" in result
        assert "processed_Some content" in result

    def test_process_section_depth_tracking(self):
        """Test section processing with proper depth tracking."""
        section = {
            "type": "section",
            "name": "Main Section",
            "entries": [
                {
                    "type": "section",
                    "name": "Nested Section",
                    "entries": ["Deep content"],
                }
            ],
        }
        result = self.processor.process_entry_dict(section, self.context)

        assert "\\section{Main Section}" in result
        assert "\\subsection{Nested Section}" in result
        assert "processed_Deep content" in result

    def test_get_section_command_all_depths(self):
        """Test section command generation for all depths."""
        assert self.processor._get_section_command(0) == "section"
        assert self.processor._get_section_command(1) == "subsection"
        assert self.processor._get_section_command(2) == "subsubsection"
        assert self.processor._get_section_command(3) == "paragraph"
        assert self.processor._get_section_command(4) == "subparagraph"
        assert self.processor._get_section_command(10) == "subparagraph"  # Max depth

    def test_process_text_with_tags_no_resolver(self):
        """Test text processing without tag resolver."""
        context_no_resolver = RenderContext()
        context_no_resolver.tag_resolver = None

        result = self.processor._process_text_with_tags(
            "Test & text", context_no_resolver
        )
        assert result == "Test \\& text"  # LaTeX escaped

    def test_process_text_with_tags_empty_text(self):
        """Test text processing with empty text."""
        result = self.processor._process_text_with_tags("", self.context)
        assert result == ""

    def test_escape_latex_special_characters(self):
        """Test LaTeX special character escaping."""
        # Test each character separately
        assert self.processor._escape_latex("{") == r"\{"
        assert self.processor._escape_latex("}") == r"\}"
        assert self.processor._escape_latex("$") == r"\$"
        assert self.processor._escape_latex("&") == r"\&"
        assert self.processor._escape_latex("%") == r"\%"
        assert self.processor._escape_latex("#") == r"\#"
        assert self.processor._escape_latex("_") == r"\_"

        # These replacements contain braces that will be escaped
        # So we need to check the actual output
        result = self.processor._escape_latex("\\")
        assert "textbackslash" in result

        result = self.processor._escape_latex("^")
        assert "textasciicircum" in result

        result = self.processor._escape_latex("~")
        assert "textasciitilde" in result

    def test_escape_latex_unicode_characters(self):
        """Test LaTeX Unicode character replacement."""
        # Test simple replacements using explicit Unicode code points
        assert self.processor._escape_latex(chr(0x2014)) == "---"  # Em dash
        assert self.processor._escape_latex(chr(0x2013)) == "--"  # En dash
        assert self.processor._escape_latex(chr(0x201C)) == "``"  # Left double quote
        assert self.processor._escape_latex(chr(0x201D)) == "''"  # Right double quote
        assert self.processor._escape_latex(chr(0x2018)) == "`"  # Left single quote

        # These contain braces that may be escaped
        result = self.processor._escape_latex(chr(0x2026))  # Ellipsis
        assert "ldots" in result

        result = self.processor._escape_latex(chr(0x00B0))  # Degree
        assert "textdegree" in result

        result = self.processor._escape_latex(chr(0x00A9))  # Copyright
        assert "copyright" in result

        result = self.processor._escape_latex(chr(0x00AE))  # Registered
        assert "textregistered" in result

        result = self.processor._escape_latex(chr(0x2122))  # Trademark
        assert "texttrademark" in result

    def test_escape_latex_complex_text(self):
        """Test LaTeX escaping with complex text."""
        # Use explicit em dash character to avoid encoding issues
        text = f'Price: $5.99 & tax 10% {chr(0x2014)} "special" characters!'
        result = self.processor._escape_latex(text)

        assert "\\$" in result
        assert "\\&" in result
        assert "\\%" in result
        assert "---" in result  # Em dash should be converted
        # The quotes are regular ASCII quotes, not converted to LaTeX quotes
        assert '"' in result

    def test_escape_latex_empty_text(self):
        """Test LaTeX escaping with empty text."""
        result = self.processor._escape_latex("")
        assert result == ""

    def test_escape_latex_none_text(self):
        """Test LaTeX escaping with None text."""
        result = self.processor._escape_latex(None)
        assert result == ""

    def test_escape_latex_additional_unicode_chars(self):
        """Test additional Unicode characters from the new mappings."""
        # Test quotation marks using explicit Unicode
        assert self.processor._escape_latex(chr(0x2019)) == "'"  # Right single quote

        # Test spaces
        assert self.processor._escape_latex(chr(0x00A0)) == "~"  # Non-breaking space

        # Test mathematical symbols
        assert self.processor._escape_latex(chr(0x00B1)) == r"\textpm{}"  # Plus-minus

        # Test currency symbols
        result = self.processor._escape_latex(chr(0x20AC))  # Euro sign
        assert "texteuro" in result

        # Test section symbol
        assert self.processor._escape_latex(chr(0x00A7)) == r"\S{}"  # Section sign

    def test_escape_latex_mixed_content(self):
        """Test escaping text with mixed special chars and Unicode."""
        # Use explicit em dash to avoid encoding issues
        text = f'LaTeX: $100 {chr(0x2014)} "smart quotes" & 50% off!'
        result = self.processor._escape_latex(text)

        # Check LaTeX special chars are escaped
        assert "\\$" in result
        assert "\\&" in result
        assert "\\%" in result

        # Check Unicode chars are converted
        assert "---" in result  # Em dash

        # Regular ASCII quotes should remain
        assert '"' in result
