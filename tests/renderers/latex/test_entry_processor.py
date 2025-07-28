"""Tests for LaTeX entry processor."""

from unittest.mock import Mock

from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor


class TestRecursiveEntryProcessor:
    """Test recursive entry processor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor(use_dnd_template=True)
        self.context = RenderContext()

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

        assert "\\begin{figure}[ht]" in result
        assert "\\includegraphics[width=0.8\\textwidth]{path/to/image.png}" in result
        assert "\\caption{Test Image}" in result
        assert "\\end{figure}" in result

    def test_process_entry_dict_image_without_title(self):
        """Test processing image without title."""
        entry = {"type": "image", "href": "path/to/image.png"}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{center}" in result
        assert "\\includegraphics[width=0.8\\textwidth]{path/to/image.png}" in result
        assert "\\end{center}" in result

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
        assert "caption={Test Table}" in result
        assert "cols={ll}" in result
        assert "Name & Value \\\\" in result
        assert "Item 1 & 10 \\\\" in result
        assert "Item 2 & 20 \\\\" in result
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


class TestRecursiveEntryProcessorWithoutDNDTemplate:
    """Test processor without DND template."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor(use_dnd_template=False)
        self.context = RenderContext()

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(side_effect=lambda x: f"processed_{x}")
        self.context.tag_resolver = mock_tag_resolver

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


class TestRecursiveEntryProcessorEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor()
        self.context = RenderContext()

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(side_effect=lambda x: x)
        self.context.tag_resolver = mock_tag_resolver

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


class TestNewEntryTypes:
    """Test new entry types added for issue #89."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor(use_dnd_template=True)
        self.context = RenderContext()

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(side_effect=lambda x: f"processed_{x}")
        self.context.tag_resolver = mock_tag_resolver

    def test_process_entry_dict_actions(self):
        """Test processing actions entry."""
        entry = {
            "type": "actions",
            "name": "Multiattack",
            "entries": ["The creature makes two weapon attacks."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Multiattack.}" in result
        assert "processed_The creature makes two weapon attacks." in result

    def test_process_entry_dict_actions_no_name(self):
        """Test processing actions entry without name."""
        entry = {"type": "actions", "entries": ["The creature attacks."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_The creature attacks." in result
        assert "\\textbf{" not in result

    def test_process_entry_dict_attack(self):
        """Test processing attack entry."""
        entry = {
            "type": "attack",
            "name": "Longsword",
            "entries": [
                "{@atk mw} {@hit 7} to hit, reach 5 ft., one target. {@h}11 ({@damage 2d8 + 2}) slashing damage."
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textit{Longsword.}" in result
        assert "processed_{@atk mw} {@hit 7} to hit" in result

    def test_process_entry_dict_attack_no_name(self):
        """Test processing attack entry without name."""
        entry = {"type": "attack", "entries": ["{@atk mw} {@hit 5} to hit."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_{@atk mw} {@hit 5} to hit." in result
        assert "\\textit{" not in result

    def test_process_entry_dict_options(self):
        """Test processing options entry."""
        entry = {
            "type": "options",
            "entries": [
                {
                    "type": "entries",
                    "name": "Option 1",
                    "entries": ["First choice description"],
                },
                {
                    "type": "entries",
                    "name": "Option 2",
                    "entries": ["Second choice description"],
                },
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{itemize}" in result
        assert "\\item \\subsection{Option 1}" in result
        assert "\\item \\subsection{Option 2}" in result
        assert "processed_First choice description" in result
        assert "processed_Second choice description" in result
        assert "\\end{itemize}" in result

    def test_process_entry_dict_options_empty(self):
        """Test processing empty options entry."""
        entry = {"type": "options", "entries": []}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == ""

    def test_process_entry_dict_variant(self):
        """Test processing variant entry."""
        entry = {
            "type": "variant",
            "name": "Optional Rule",
            "entries": ["This variant rule changes how combat works."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Variant: Optional Rule}" in result
        assert "processed_This variant rule changes how combat works." in result

    def test_process_entry_dict_variant_no_name(self):
        """Test processing variant entry without name."""
        entry = {"type": "variant", "entries": ["This is a variant rule."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Variant:}" in result
        assert "processed_This is a variant rule." in result

    def test_process_entry_dict_variant_sub(self):
        """Test processing variantSub entry."""
        entry = {
            "type": "variantSub",
            "name": "Sub-variant",
            "entries": ["This is a sub-variant of the main rule."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textit{Sub-variant:}" in result
        assert "processed_This is a sub-variant of the main rule." in result

    def test_process_entry_dict_variant_sub_no_name(self):
        """Test processing variantSub entry without name."""
        entry = {"type": "variantSub", "entries": ["A sub-variant rule."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_A sub-variant rule." in result
        assert "\\textit{" not in result

    def test_process_entry_dict_ability_dc(self):
        """Test processing abilityDc entry."""
        entry = {"type": "abilityDc", "name": "Spell Save DC", "attributes": ["cha"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spell Save DC:}" in result
        assert "8 + proficiency bonus + Charisma modifier" in result

    def test_process_entry_dict_ability_dc_no_name(self):
        """Test processing abilityDc entry without name."""
        entry = {"type": "abilityDc", "attributes": ["wis"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Save DC:}" in result
        assert "8 + proficiency bonus + Wisdom modifier" in result

    def test_process_entry_dict_ability_attack_mod(self):
        """Test processing abilityAttackMod entry."""
        entry = {
            "type": "abilityAttackMod",
            "name": "Spell Attack Bonus",
            "attributes": ["int"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spell Attack Bonus:}" in result
        assert "proficiency bonus + Intelligence modifier" in result

    def test_process_entry_dict_ability_generic(self):
        """Test processing abilityGeneric entry."""
        entry = {
            "type": "abilityGeneric",
            "name": "Special Ability",
            "text": "+{@mod str} to damage rolls",
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Special Ability:}" in result
        assert "processed_+{@mod str} to damage rolls" in result

    def test_process_entry_dict_spellcasting(self):
        """Test processing spellcasting entry."""
        entry = {
            "type": "spellcasting",
            "name": "Spellcasting",
            "headerEntries": ["The creature is an 11th-level spellcaster."],
            "spells": {
                "0": {"spells": ["{@spell mage hand}", "{@spell minor illusion}"]},
                "1": {
                    "slots": 4,
                    "spells": ["{@spell magic missile}", "{@spell shield}"],
                },
            },
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spellcasting.}" in result
        assert "processed_The creature is an 11th-level spellcaster." in result
        assert "\\textbf{Cantrips (at will):}" in result
        assert "processed_{@spell mage hand}" in result
        assert "\\textbf{1st level (4 slots):}" in result
        assert "processed_{@spell magic missile}" in result

    def test_process_entry_dict_bonus(self):
        """Test processing bonus entry."""
        entry = {"type": "bonus", "value": 2}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "+2"

    def test_process_entry_dict_bonus_negative(self):
        """Test processing negative bonus entry."""
        entry = {"type": "bonus", "value": -1}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "-1"

    def test_process_entry_dict_bonus_speed(self):
        """Test processing bonusSpeed entry."""
        entry = {"type": "bonusSpeed", "value": 10}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "+10 ft."

    def test_process_entry_dict_dice(self):
        """Test processing dice entry."""
        entry = {"type": "dice", "toRoll": [{"number": 2, "faces": 6, "modifier": 3}]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "2d6+3"

    def test_process_entry_dict_dice_multiple(self):
        """Test processing dice entry with multiple dice."""
        entry = {
            "type": "dice",
            "toRoll": [
                {"number": 1, "faces": 8},
                {"number": 2, "faces": 4, "modifier": -1},
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "1d8, 2d4-1"

    def test_process_entry_dict_item_simple(self):
        """Test processing item entry as simple string."""
        entry = {
            "type": "item",
            "name": "Simple Item",
            "entry": "This is a simple list item.",
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Simple Item.}" in result
        assert "processed_This is a simple list item." in result

    def test_process_entry_dict_item_with_entries(self):
        """Test processing item entry with nested entries."""
        entry = {
            "type": "item",
            "name": "Complex Item",
            "entries": ["First paragraph.", "Second paragraph."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Complex Item.}" in result
        assert "processed_First paragraph." in result
        assert "processed_Second paragraph." in result

    def test_process_entry_dict_item_no_name(self):
        """Test processing item entry without name."""
        entry = {"type": "item", "entry": "Unnamed item content."}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_Unnamed item content." in result
        assert "\\textbf{" not in result
