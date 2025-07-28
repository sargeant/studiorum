"""Tests for LaTeX reference resolver."""

from unittest.mock import Mock

import pytest

from dnd5e.renderers.latex.reference_resolver import ReferenceContext, ReferenceResolver


class TestReferenceContext:
    """Test reference context dataclass."""

    def test_init_defaults(self):
        """Test context initialization with defaults."""
        context = ReferenceContext()

        assert context.document_type == "general"
        assert context.current_section == ""
        assert context.current_page == 0
        assert context.appendix_mode is False
        assert context.cross_ref_enabled is True
        assert context.hyperlinks_enabled is True

    def test_init_custom_values(self):
        """Test context initialization with custom values."""
        context = ReferenceContext(
            document_type="adventure",
            current_section="Chapter 1",
            current_page=42,
            appendix_mode=True,
            cross_ref_enabled=False,
            hyperlinks_enabled=False,
        )

        assert context.document_type == "adventure"
        assert context.current_section == "Chapter 1"
        assert context.current_page == 42
        assert context.appendix_mode is True
        assert context.cross_ref_enabled is False
        assert context.hyperlinks_enabled is False


class TestReferenceResolver:
    """Test reference resolver functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock tag integration
        self.mock_tag_integration = Mock()

        # Create mock cross-reference manager
        self.mock_cross_ref_mgr = Mock()
        self.mock_cross_ref_mgr.register_content.return_value = "ref_id_123"
        self.mock_cross_ref_mgr.create_latex_reference.return_value = (
            "\\ref{ref_id_123}"
        )
        self.mock_cross_ref_mgr.create_latex_label.return_value = "\\label{ref_id_123}"
        self.mock_cross_ref_mgr.get_all_references.return_value = {}
        self.mock_cross_ref_mgr.get_reference_statistics.return_value = {"total": 0}

        # Create mock hyperlink manager
        self.mock_hyperlink_mgr = Mock()
        self.mock_hyperlink_mgr.should_create_hyperlink.return_value = True

        # Make create_hyperlink return dynamic value based on input
        def mock_create_hyperlink(text, **kwargs):
            return f"\\hyperref[ref_id_123]{{{text}}}"

        self.mock_hyperlink_mgr.create_hyperlink.side_effect = mock_create_hyperlink
        self.mock_hyperlink_mgr.create_section_reference.return_value = (
            "\\nameref{section-label}"
        )

        # Create mock content tracker
        self.mock_content_tracker = Mock()
        self.mock_content_tracker.get_latex_content.return_value = None
        self.mock_content_tracker.get_latex_statistics.return_value = {"total": 0}
        self.mock_content_tracker.get_most_referenced_content.return_value = []

        # Setup tag integration
        self.mock_tag_integration.cross_ref_manager = self.mock_cross_ref_mgr
        self.mock_tag_integration.hyperlink_manager = self.mock_hyperlink_mgr
        self.mock_tag_integration.content_tracker = self.mock_content_tracker
        self.mock_tag_integration.get_required_latex_packages.return_value = [
            "hyperref"
        ]
        self.mock_tag_integration.get_latex_preamble_commands.return_value = [
            "\\usepackage{hyperref}"
        ]
        self.mock_tag_integration.export_cross_reference_data.return_value = {}
        self.mock_tag_integration.export_appendix_data.return_value = {}

        # Create resolver
        self.resolver = ReferenceResolver(self.mock_tag_integration)
        self.context = ReferenceContext()

    def test_init(self):
        """Test resolver initialization."""
        resolver = ReferenceResolver(self.mock_tag_integration)

        assert resolver.tag_integration == self.mock_tag_integration
        assert resolver.reference_cache == {}
        assert resolver.forward_references == {}
        assert resolver.backward_references == {}
        assert resolver.unresolved_references == set()

    def test_resolve_content_reference_with_cache(self):
        """Test content reference resolution with caching."""
        # Pre-populate cache
        cache_key = "creature:Dragon:general"
        cached_result = "\\textbf{Cached Dragon}"
        self.resolver.reference_cache[cache_key] = cached_result

        result = self.resolver.resolve_content_reference(
            content_type="creature", name="Dragon", context=self.context
        )

        assert result == cached_result
        # Should not call cross-reference manager
        self.mock_cross_ref_mgr.register_content.assert_not_called()

    def test_resolve_content_reference_no_cross_ref_manager(self):
        """Test content reference resolution without cross-reference manager."""
        self.mock_tag_integration.cross_ref_manager = None

        result = self.resolver.resolve_content_reference(
            content_type="creature", name="Dragon", context=self.context
        )

        assert result == "\\textbf{Dragon}"
        # Should cache the result
        cache_key = "creature:Dragon:general"
        assert self.resolver.reference_cache[cache_key] == "\\textbf{Dragon}"

    def test_resolve_content_reference_with_hyperlink(self):
        """Test content reference resolution with hyperlink."""
        result = self.resolver.resolve_content_reference(
            content_type="creature", name="Dragon", context=self.context
        )

        assert result == "\\hyperref[ref_id_123]{\\textbf{Dragon}}"

        # Verify method calls
        self.mock_cross_ref_mgr.register_content.assert_called_once_with(
            "creature", "Dragon"
        )
        self.mock_hyperlink_mgr.should_create_hyperlink.assert_called_once_with(
            "creature"
        )
        self.mock_hyperlink_mgr.create_hyperlink.assert_called_once()

    def test_resolve_content_reference_without_hyperlink(self):
        """Test content reference resolution without hyperlink."""
        self.mock_hyperlink_mgr.should_create_hyperlink.return_value = False

        result = self.resolver.resolve_content_reference(
            content_type="spell", name="Fireball", context=self.context
        )

        assert result == "\\ref{ref_id_123}"

        # Should use basic cross-reference
        self.mock_cross_ref_mgr.create_latex_reference.assert_called_once()

    def test_resolve_content_reference_with_display_text(self):
        """Test content reference resolution with custom display text."""
        self.resolver.resolve_content_reference(
            content_type="creature",
            name="Dragon",
            context=self.context,
            display_text="Ancient Red Dragon",
        )

        # Should use display text in formatting
        call_args = self.mock_hyperlink_mgr.create_hyperlink.call_args
        assert "Ancient Red Dragon" in str(call_args)

    def test_resolve_content_reference_force_hyperlink(self):
        """Test content reference resolution with forced hyperlink."""
        # Set should_create_hyperlink to False but force_hyperlink=True should override
        self.mock_hyperlink_mgr.should_create_hyperlink.return_value = False

        self.resolver.resolve_content_reference(
            content_type="creature",
            name="Dragon",
            context=self.context,
            force_hyperlink=True,
        )

        # Should create hyperlink due to force_hyperlink=True even though should_create_hyperlink is False
        self.mock_hyperlink_mgr.create_hyperlink.assert_called_once()

    def test_apply_basic_formatting_all_types(self):
        """Test basic formatting for all content types."""
        test_cases = [
            ("creature", "Dragon", "\\textbf{Dragon}"),
            ("spell", "Fireball", "\\textit{Fireball}"),
            ("item", "Sword", "\\textit{Sword}"),
            ("class", "Fighter", "\\textbf{Fighter}"),
            ("feat", "Power Attack", "\\textbf{Power Attack}"),
            ("condition", "Poisoned", "\\textit{Poisoned}"),
            ("adventure", "Lost Mine", "\\textit{Lost Mine}"),
            ("book", "PHB", "\\textit{PHB}"),
            ("unknown", "Something", "Something"),  # No formatting
        ]

        for content_type, text, expected in test_cases:
            result = self.resolver._apply_basic_formatting(content_type, text)
            assert result == expected

    def test_should_include_page_ref_appendix_mode(self):
        """Test page reference inclusion in appendix mode."""
        self.context.appendix_mode = True

        result = self.resolver._should_include_page_ref("creature", self.context)

        assert result is False

    def test_should_include_page_ref_major_types(self):
        """Test page reference inclusion for major content types."""
        test_cases = [
            ("creature", "adventure", True),
            ("spell", "supplement", True),
            ("item", "adventure", True),
            ("class", "supplement", True),
            ("race", "adventure", True),
            ("feat", "supplement", True),
            ("unknown", "adventure", False),  # Not a major type
            ("creature", "general", False),  # Not adventure/supplement
        ]

        for content_type, doc_type, expected in test_cases:
            self.context.document_type = doc_type
            result = self.resolver._should_include_page_ref(content_type, self.context)
            assert result == expected

    def test_track_reference_relationship(self):
        """Test reference relationship tracking."""
        self.context.current_section = "Chapter 1"
        self.context.current_page = 42

        self.resolver._track_reference_relationship("ref_123", self.context)

        location = "Chapter 1:42"

        # Check forward reference tracking
        assert location in self.resolver.forward_references
        assert "ref_123" in self.resolver.forward_references[location]

        # Check backward reference tracking
        assert "ref_123" in self.resolver.backward_references
        assert location in self.resolver.backward_references["ref_123"]

    def test_track_reference_relationship_no_duplicates(self):
        """Test that reference relationship tracking avoids duplicates."""
        self.context.current_section = "Chapter 1"
        self.context.current_page = 42

        # Track same reference twice
        self.resolver._track_reference_relationship("ref_123", self.context)
        self.resolver._track_reference_relationship("ref_123", self.context)

        location = "Chapter 1:42"

        # Should only appear once
        assert self.resolver.forward_references[location].count("ref_123") == 1
        assert self.resolver.backward_references["ref_123"].count(location) == 1

    def test_create_definition_label(self):
        """Test definition label creation."""
        self.context.current_page = 25

        result = self.resolver.create_definition_label(
            content_type="creature", name="Dragon", context=self.context
        )

        assert result == "\\label{ref_id_123}"

        # Verify method calls
        self.mock_cross_ref_mgr.register_content.assert_called_once_with(
            "creature", "Dragon"
        )
        self.mock_cross_ref_mgr.create_latex_label.assert_called_once_with("ref_id_123")
        self.mock_content_tracker.set_definition_page.assert_called_once_with(
            "creature:Dragon", 25
        )

    def test_create_definition_label_no_cross_ref_manager(self):
        """Test definition label creation without cross-reference manager."""
        self.mock_tag_integration.cross_ref_manager = None

        result = self.resolver.create_definition_label(
            content_type="creature", name="Dragon", context=self.context
        )

        assert result == ""

    def test_resolve_adventure_reference_full(self):
        """Test adventure reference resolution with all details."""
        result = self.resolver.resolve_adventure_reference(
            adventure_name="Lost Mine of Phandelver",
            chapter="Chapter 1: Goblin Ambush",
            page="7",
            context=self.context,
        )

        # Should call resolve_content_reference with proper display text
        # The exact result depends on the mocked resolve_content_reference
        assert isinstance(result, str)

    def test_resolve_adventure_reference_chapter_only(self):
        """Test adventure reference resolution with chapter only."""
        result = self.resolver.resolve_adventure_reference(
            adventure_name="Lost Mine of Phandelver",
            chapter="Chapter 1: Goblin Ambush",
            context=self.context,
        )

        assert isinstance(result, str)

    def test_resolve_adventure_reference_page_only(self):
        """Test adventure reference resolution with page only."""
        result = self.resolver.resolve_adventure_reference(
            adventure_name="Lost Mine of Phandelver", page="7", context=self.context
        )

        assert isinstance(result, str)

    def test_resolve_adventure_reference_name_only(self):
        """Test adventure reference resolution with name only."""
        result = self.resolver.resolve_adventure_reference(
            adventure_name="Lost Mine of Phandelver", context=self.context
        )

        assert isinstance(result, str)

    def test_resolve_adventure_reference_default_context(self):
        """Test adventure reference resolution with default context."""
        result = self.resolver.resolve_adventure_reference(
            adventure_name="Lost Mine of Phandelver"
        )

        assert isinstance(result, str)

    def test_resolve_book_reference_with_page(self):
        """Test book reference resolution with page."""
        result = self.resolver.resolve_book_reference(
            book_name="Player's Handbook", page="123", context=self.context
        )

        assert isinstance(result, str)

    def test_resolve_book_reference_without_page(self):
        """Test book reference resolution without page."""
        result = self.resolver.resolve_book_reference(
            book_name="Player's Handbook", context=self.context
        )

        assert isinstance(result, str)

    def test_resolve_book_reference_default_context(self):
        """Test book reference resolution with default context."""
        result = self.resolver.resolve_book_reference(book_name="Player's Handbook")

        assert isinstance(result, str)

    def test_resolve_section_reference(self):
        """Test section reference resolution."""
        result = self.resolver.resolve_section_reference(
            section_name="Combat Rules", ref_type="nameref", context=self.context
        )

        assert result == "\\nameref{section-label}"

        # Verify method calls
        self.mock_hyperlink_mgr.create_section_reference.assert_called_once_with(
            text="Combat Rules", section_label="combat-rules", ref_type="nameref"
        )

    def test_resolve_section_reference_no_hyperlink_manager(self):
        """Test section reference resolution without hyperlink manager."""
        self.mock_tag_integration.hyperlink_manager = None

        result = self.resolver.resolve_section_reference(
            section_name="Combat Rules", context=self.context
        )

        assert result == "Combat Rules"

    def test_sanitize_section_label(self):
        """Test section label sanitization."""
        test_cases = [
            ("Combat Rules", "combat-rules"),
            ("Chapter 1: The Beginning", "chapter-1-the-beginning"),
            ("Special Characters! @#$%", "special-characters"),
            ("   Trimmed   ", "trimmed"),
            ("Multiple---Dashes", "multiple-dashes"),
            ("Numbers123AndLetters", "numbers123andletters"),
        ]

        for input_text, expected in test_cases:
            result = self.resolver._sanitize_section_label(input_text)
            assert result == expected

    def test_generate_forward_reference_list(self):
        """Test forward reference list generation."""
        # Setup test data
        self.resolver.backward_references["ref_123"] = ["loc1", "loc2", "loc3"]

        result = self.resolver.generate_forward_reference_list("ref_123")

        assert result == ["loc1", "loc2", "loc3"]

    def test_generate_forward_reference_list_empty(self):
        """Test forward reference list generation for unknown reference."""
        result = self.resolver.generate_forward_reference_list("unknown_ref")

        assert result == []

    def test_generate_backward_reference_list(self):
        """Test backward reference list generation."""
        # Setup test data
        self.resolver.forward_references["location"] = ["ref1", "ref2", "ref3"]

        result = self.resolver.generate_backward_reference_list("location")

        assert result == ["ref1", "ref2", "ref3"]

    def test_generate_backward_reference_list_empty(self):
        """Test backward reference list generation for unknown location."""
        result = self.resolver.generate_backward_reference_list("unknown_location")

        assert result == []

    def test_find_unresolved_references_no_cross_ref_manager(self):
        """Test finding unresolved references without cross-reference manager."""
        self.mock_tag_integration.cross_ref_manager = None

        result = self.resolver.find_unresolved_references()

        assert result == []

    def test_find_unresolved_references_with_issues(self):
        """Test finding unresolved references with actual issues."""
        # Setup mock reference data
        mock_ref_data = Mock()
        mock_ref_data.content_type = "creature"
        mock_ref_data.name = "Dragon"

        self.mock_cross_ref_mgr.get_all_references.return_value = {
            "ref_123": mock_ref_data
        }

        # Mock content tracker to return no content (unresolved)
        self.mock_content_tracker.get_latex_content.return_value = None

        result = self.resolver.find_unresolved_references()

        assert len(result) == 1
        assert result[0]["type"] == "unresolved_reference"
        assert result[0]["ref_id"] == "ref_123"
        assert result[0]["content_type"] == "creature"
        assert result[0]["name"] == "Dragon"
        assert "no definition" in result[0]["message"]

    def test_find_unresolved_references_with_content_no_definition_page(self):
        """Test finding unresolved references with content but no definition page."""
        # Setup mock reference data
        mock_ref_data = Mock()
        mock_ref_data.content_type = "creature"
        mock_ref_data.name = "Dragon"

        self.mock_cross_ref_mgr.get_all_references.return_value = {
            "ref_123": mock_ref_data
        }

        # Mock content tracker to return content without definition page
        mock_content = Mock()
        mock_content.definition_page = None
        self.mock_content_tracker.get_latex_content.return_value = mock_content

        result = self.resolver.find_unresolved_references()

        assert len(result) == 1
        assert result[0]["type"] == "unresolved_reference"

    def test_find_unresolved_references_resolved(self):
        """Test finding unresolved references when all are resolved."""
        # Setup mock reference data
        mock_ref_data = Mock()
        mock_ref_data.content_type = "creature"
        mock_ref_data.name = "Dragon"

        self.mock_cross_ref_mgr.get_all_references.return_value = {
            "ref_123": mock_ref_data
        }

        # Mock content tracker to return valid content
        mock_content = Mock()
        mock_content.definition_page = 42
        self.mock_content_tracker.get_latex_content.return_value = mock_content

        result = self.resolver.find_unresolved_references()

        assert result == []

    def test_generate_reference_report(self):
        """Test reference report generation."""
        # Setup test data
        self.resolver.reference_cache = {"ref1": "result1", "ref2": "result2"}
        self.resolver.forward_references = {"loc1": ["ref1"], "loc2": ["ref2"]}
        self.resolver.backward_references = {"ref1": ["loc1"], "ref2": ["loc2"]}
        self.resolver.unresolved_references = {"unresolved1", "unresolved2"}

        # Setup mock return values
        self.mock_cross_ref_mgr.get_reference_statistics.return_value = {
            "total_refs": 5
        }
        self.mock_content_tracker.get_latex_statistics.return_value = {
            "total_content": 10
        }

        mock_content = Mock()
        mock_content.name = "Dragon"
        mock_content.content_type = "creature"
        mock_content.usage_count = 15
        self.mock_content_tracker.get_most_referenced_content.return_value = [
            mock_content
        ]

        result = self.resolver.generate_reference_report()

        assert result["total_references"] == 2
        assert result["forward_references"] == 2
        assert result["backward_references"] == 2
        assert result["unresolved"] == 2
        assert result["cross_reference_stats"] == {"total_refs": 5}
        assert result["content_stats"] == {"total_content": 10}
        assert len(result["most_referenced"]) == 1
        assert result["most_referenced"][0]["name"] == "Dragon"
        assert result["most_referenced"][0]["type"] == "creature"
        assert result["most_referenced"][0]["usage_count"] == 15

    def test_generate_reference_report_no_managers(self):
        """Test reference report generation without managers."""
        self.mock_tag_integration.cross_ref_manager = None
        self.mock_tag_integration.content_tracker = None

        result = self.resolver.generate_reference_report()

        assert "cross_reference_stats" not in result
        assert "content_stats" not in result
        assert "most_referenced" in result
        assert result["most_referenced"] == []

    def test_clear_cache(self):
        """Test cache clearing."""
        # Setup test data
        self.resolver.reference_cache["key"] = "value"
        self.resolver.forward_references["loc"] = ["ref"]
        self.resolver.backward_references["ref"] = ["loc"]
        self.resolver.unresolved_references.add("unresolved")

        self.resolver.clear_cache()

        assert self.resolver.reference_cache == {}
        assert self.resolver.forward_references == {}
        assert self.resolver.backward_references == {}
        assert self.resolver.unresolved_references == set()

    def test_export_reference_data_for_compilation(self):
        """Test reference data export for compilation."""
        result = self.resolver.export_reference_data_for_compilation()

        expected_keys = [
            "required_packages",
            "preamble_commands",
            "cross_references",
            "appendix_data",
        ]
        for key in expected_keys:
            assert key in result

        assert result["required_packages"] == ["hyperref"]
        assert result["preamble_commands"] == ["\\usepackage{hyperref}"]
        assert result["cross_references"] == {}
        assert result["appendix_data"] == {}

    def test_export_reference_data_no_cross_ref_manager(self):
        """Test reference data export without cross-reference manager."""
        self.mock_tag_integration.cross_ref_manager = None

        result = self.resolver.export_reference_data_for_compilation()

        assert result["cross_references"] == {}


class TestReferenceResolverEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tag_integration = Mock()
        self.resolver = ReferenceResolver(self.mock_tag_integration)

    def test_context_with_hyperlinks_disabled(self):
        """Test reference resolution with hyperlinks disabled."""
        context = ReferenceContext(hyperlinks_enabled=False)

        # Setup minimal mocks
        mock_cross_ref_mgr = Mock()
        mock_cross_ref_mgr.register_content.return_value = "ref_123"
        mock_cross_ref_mgr.create_latex_reference.return_value = "\\ref{ref_123}"

        mock_hyperlink_mgr = Mock()
        mock_hyperlink_mgr.should_create_hyperlink.return_value = True

        self.mock_tag_integration.cross_ref_manager = mock_cross_ref_mgr
        self.mock_tag_integration.hyperlink_manager = mock_hyperlink_mgr

        self.resolver.resolve_content_reference(
            content_type="creature", name="Dragon", context=context
        )

        # Should not create hyperlink despite should_create_hyperlink returning True
        mock_hyperlink_mgr.create_hyperlink.assert_not_called()
        mock_cross_ref_mgr.create_latex_reference.assert_called_once()

    def test_context_with_cross_ref_disabled(self):
        """Test reference resolution with cross-references disabled."""
        context = ReferenceContext(cross_ref_enabled=False)

        # Setup minimal mocks
        mock_cross_ref_mgr = Mock()
        mock_cross_ref_mgr.register_content.return_value = "ref_123"
        mock_cross_ref_mgr.create_latex_reference.return_value = "\\text{Dragon}"

        self.mock_tag_integration.cross_ref_manager = mock_cross_ref_mgr
        self.mock_tag_integration.hyperlink_manager = None

        self.resolver.resolve_content_reference(
            content_type="creature", name="Dragon", context=context
        )

        # Should pass ref_type="text" when cross_ref_enabled is False
        call_args = mock_cross_ref_mgr.create_latex_reference.call_args
        assert call_args[1]["ref_type"] == "text"
