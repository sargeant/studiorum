"""Tests for the new AST-based tag resolution system."""

# Import the new tag system components
from dnd5e.core.indexer.content_tracker import ContentTracker, TrackedContent
from dnd5e.core.indexer.new_tag_resolver import TagResolverFacade
from dnd5e.core.indexer.tag_ast import (
    CreatureTagNode,
    TextNode,
)
from dnd5e.core.indexer.tag_parser import TagParser


class MockTagNode:
    """Mock AST node for testing purposes."""

    def __init__(self, tag_type: str, original_text_span=None):
        self.tag_type = tag_type
        self.children = []
        self.original_text_span = original_text_span


class MockTextNode:
    """Mock text node for testing purposes."""

    def __init__(self, text: str, original_text_span=None):
        self.text = text
        self.original_text_span = original_text_span


class MockCreatureTagNode(MockTagNode):
    """Mock creature tag node for testing purposes."""

    def __init__(
        self, name: str, source=None, display_text_nodes=None, original_text_span=None
    ):
        super().__init__("creature", original_text_span)
        self.name = name
        self.source = source
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [MockTextNode(name)]
        )
        self.children.extend(self.display_text_nodes)


class MockSpellTagNode(MockTagNode):
    """Mock spell tag node for testing purposes."""

    def __init__(
        self, name: str, source=None, display_text_nodes=None, original_text_span=None
    ):
        super().__init__("spell", original_text_span)
        self.name = name
        self.source = source
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [MockTextNode(name)]
        )
        self.children.extend(self.display_text_nodes)


class MockDiceTagNode(MockTagNode):
    """Mock dice tag node for testing purposes."""

    def __init__(self, expression: str, original_text_span=None):
        super().__init__("dice", original_text_span)
        self.expression = expression


class TestTagParser:
    """Tests for the new lark-based tag parser."""

    def test_parser_handles_simple_text(self):
        """Test that plain text without tags is parsed correctly."""
        text = "This is plain text with no tags."
        parser = TagParser()
        ast = parser.parse(text)

        assert len(ast.children) == 1
        assert isinstance(ast.children[0], TextNode)
        assert ast.children[0].text == text

    def test_parser_handles_simple_creature_tag(self):
        """Test parsing a simple creature tag."""
        text = "{@creature Ancient Red Dragon|MM}"
        parser = TagParser()
        ast = parser.parse(text)

        assert len(ast.children) == 1
        assert isinstance(ast.children[0], CreatureTagNode)
        assert ast.children[0].name == "Ancient Red Dragon"
        assert ast.children[0].source == "MM"
        assert len(ast.children[0].display_text_nodes) == 1
        assert ast.children[0].display_text_nodes[0].text == "Ancient Red Dragon"

    def test_parser_handles_creature_tag_with_display_text(self):
        """Test parsing creature tag with custom display text."""
        # parser = TagParser()
        # ast = parser.parse(text)
        #
        # creature_node = ast.children[0]
        # assert isinstance(creature_node, CreatureTagNode)
        # assert creature_node.name == "Ancient Red Dragon"
        # assert creature_node.source == "MM"
        # assert len(creature_node.display_text_nodes) == 1
        # assert creature_node.display_text_nodes[0].text == "great wyrm"
        pass  # Placeholder for now

    def test_parser_handles_nested_tags(self):
        """Test parsing nested tags within display text."""
        # This should parse to a creature tag with display_text containing both text and a bold tag
        # parser = TagParser()
        # ast = parser.parse(text)
        #
        # creature_node = ast.children[0]
        # assert isinstance(creature_node, CreatureTagNode)
        # assert len(creature_node.display_text_nodes) == 3  # "{@bold great}", " ", "wyrm"
        # assert isinstance(creature_node.display_text_nodes[0], BoldTagNode)
        # assert isinstance(creature_node.display_text_nodes[1], TextNode)
        # assert isinstance(creature_node.display_text_nodes[2], TextNode)
        pass  # Placeholder for now

    def test_parser_handles_mixed_content(self):
        """Test parsing text with multiple tags and plain text."""
        # parser = TagParser()
        # ast = parser.parse(text)
        #
        # assert len(ast.children) == 5  # "Cast ", spell_tag, " at the ", creature_tag, "!"
        # assert isinstance(ast.children[0], TextNode)
        # assert isinstance(ast.children[1], SpellTagNode)
        # assert isinstance(ast.children[2], TextNode)
        # assert isinstance(ast.children[3], CreatureTagNode)
        # assert isinstance(ast.children[4], TextNode)
        pass  # Placeholder for now

    def test_parser_handles_escaped_characters(self):
        """Test parsing tags with escaped pipes and braces."""
        # parser = TagParser()
        # ast = parser.parse(text)
        #
        # creature_node = ast.children[0]
        # assert creature_node.name == "Name|with|pipes"  # Escaped pipes should be unescaped
        # assert creature_node.display_text_nodes[0].text == "display}with}braces"  # Escaped braces
        pass  # Placeholder for now

    def test_parser_error_handling_malformed_tags(self):
        """Test parser error handling for malformed tags."""

        # parser = TagParser()
        # for case in malformed_cases:
        #     try:
        #         ast = parser.parse(case)
        #         # Parser should either recover gracefully or provide meaningful error
        #         assert ast is not None
        #     except TagParseError as e:
        #         # Should provide helpful error information
        #         assert "malformed" in str(e).lower() or "invalid" in str(e).lower()
        #         assert e.position is not None  # Should indicate where the error occurred
        pass  # Placeholder for now


class TestTagHandlers:
    """Tests for individual tag handlers."""

    def test_creature_handler(self):
        """Test creature tag handler rendering and content tracking."""
        # handler = CreatureTagHandler()
        # assert handler.handles("creature")
        # assert not handler.handles("spell")
        #
        # node = MockCreatureTagNode("Ancient Red Dragon", "MM")
        # context = MockRendererContext()
        # result = handler.render(node, context)
        #
        # assert result == "\\textbf{Ancient Red Dragon}"
        pass  # Placeholder for now

    def test_creature_handler_with_display_text(self):
        """Test creature handler with custom display text."""
        # handler = CreatureTagHandler()
        # display_nodes = [MockTextNode("great wyrm")]
        # node = MockCreatureTagNode("Ancient Red Dragon", "MM", display_nodes)
        # context = MockRendererContext()
        # result = handler.render(node, context)
        #
        # assert result == "\\textbf{great wyrm}"
        pass  # Placeholder for now

    def test_creature_handler_content_tracking(self):
        """Test creature handler content tracking."""
        # handler = CreatureTagHandler()
        # tracker = ContentTracker()
        # node = MockCreatureTagNode("Ancient Red Dragon", "MM")
        #
        # handler.track_content(node, tracker)
        # tracked = tracker.get_tracked_content()
        #
        # assert len(tracked) == 1
        # assert ("creature", "Ancient Red Dragon", "MM") in tracked
        pass  # Placeholder for now

    def test_spell_handler(self):
        """Test spell tag handler rendering."""
        # handler = SpellTagHandler()
        # assert handler.handles("spell")
        #
        # node = MockSpellTagNode("Fireball", "PHB")
        # context = MockRendererContext()
        # result = handler.render(node, context)
        #
        # assert result == "\\textit{Fireball}"
        pass  # Placeholder for now

    def test_dice_handler(self):
        """Test dice tag handler rendering."""
        # handler = DiceTagHandler()
        # assert handler.handles("dice")
        #
        # node = MockDiceTagNode("1d20+5")
        # context = MockRendererContext()
        # result = handler.render(node, context)
        #
        # assert result == "\\texttt{1d20+5}"
        pass  # Placeholder for now


class TestTagRenderer:
    """Tests for the tag renderer/dispatcher."""

    def test_renderer_registration(self):
        """Test tag handler registration."""
        # renderer = TagRenderer()
        # handler = CreatureTagHandler()
        # renderer.register_handler(handler)
        #
        # assert "creature" in renderer._handlers
        # assert renderer._handlers["creature"] == handler
        pass  # Placeholder for now

    def test_renderer_text_node(self):
        """Test rendering text nodes."""
        # renderer = TagRenderer()
        # context = MockRendererContext()
        # node = MockTextNode("plain text")
        # result = renderer.render_node(node, context)
        #
        # assert result == "plain text"
        pass  # Placeholder for now

    def test_renderer_tag_node(self):
        """Test rendering tag nodes."""
        # renderer = TagRenderer()
        # renderer.register_handler(CreatureTagHandler())
        # context = MockRendererContext()
        #
        # node = MockCreatureTagNode("Ancient Red Dragon", "MM")
        # result = renderer.render_node(node, context)
        #
        # assert result == "\\textbf{Ancient Red Dragon}"
        pass  # Placeholder for now

    def test_renderer_unknown_tag_fallback(self):
        """Test fallback for unknown tag types."""
        # renderer = TagRenderer()
        # context = MockRendererContext()
        #
        # node = MockTagNode("unknown_type")
        # result = renderer.render_node(node, context)
        #
        # # Should fallback to original tag format or error message
        # assert "{@unknown_type" in result or "unknown" in result.lower()
        pass  # Placeholder for now


class TestContentTracker:
    """Tests for content tracking functionality."""

    def test_content_tracker_basic_tracking(self):
        """Test basic content tracking."""
        tracker = ContentTracker()
        tracker.add_content("creature", "Ancient Red Dragon", "MM")
        tracker.add_content("spell", "Fireball", "PHB")

        tracked = tracker.get_tracked_content()
        assert len(tracked) == 2

        # Check that content exists (order may vary)
        types_and_names = [(c.content_type, c.name, c.source) for c in tracked]
        assert ("creature", "Ancient Red Dragon", "MM") in types_and_names
        assert ("spell", "Fireball", "PHB") in types_and_names

    def test_content_tracker_deduplication(self):
        """Test that duplicate content is not tracked multiple times."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Fireball", "PHB")  # Duplicate
        tracker.add_content(
            "SPELL", "Fireball", "PHB"
        )  # Same but different case content_type

        tracked = tracker.get_tracked_content()
        assert len(tracked) == 1  # Should deduplicate

        content = tracked[0]
        assert content.content_type == "spell"  # Normalized to lowercase
        assert content.name == "Fireball"
        assert content.source == "PHB"

        # Check reference count is incremented for all three additions
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 3

        # Test that names are case-sensitive (different names)
        tracker.add_content("spell", "fireball", "PHB")  # Different case name
        tracked = tracker.get_tracked_content()
        assert len(tracked) == 2  # Should now have two different spells

        # Verify both entries
        names = [c.name for c in tracked]
        assert "Fireball" in names
        assert "fireball" in names

    def test_content_tracker_sorting(self):
        """Test that tracked content is returned in sorted order."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Zephyr Strike", "PHB")
        tracker.add_content("creature", "Ancient Red Dragon", "MM")
        tracker.add_content("spell", "Fireball", "PHB")

        tracked = tracker.get_tracked_content()

        # Should be sorted by: content_type, name, source
        expected_order = [
            ("creature", "Ancient Red Dragon", "MM"),
            ("spell", "Fireball", "PHB"),
            ("spell", "Zephyr Strike", "PHB"),
        ]

        actual_order = [(c.content_type, c.name, c.source) for c in tracked]
        assert actual_order == expected_order

    def test_content_tracker_clear(self):
        """Test clearing tracked content."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("creature", "Dragon", "MM")
        assert len(tracker.get_tracked_content()) == 2
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 1

        tracker.clear()
        assert len(tracker.get_tracked_content()) == 0
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 0
        assert len(tracker.get_content_types()) == 0

    def test_tracked_content_normalization(self):
        """Test TrackedContent normalization in __post_init__."""
        # Test content_type normalization (lowercase)
        content = TrackedContent("SPELL", "Fireball", "PHB")
        assert content.content_type == "spell"

        # Test name stripping
        content = TrackedContent("spell", "  Fireball  ", "PHB")
        assert content.name == "Fireball"

        # Test source stripping
        content = TrackedContent("spell", "Fireball", "  PHB  ")
        assert content.source == "PHB"

        # Test page stripping
        content = TrackedContent("spell", "Fireball", "PHB", "  123  ")
        assert content.page == "123"

    def test_tracked_content_equality_and_hashing(self):
        """Test TrackedContent equality and hashing behavior."""
        content1 = TrackedContent("spell", "Fireball", "PHB")
        content2 = TrackedContent("spell", "Fireball", "PHB")
        content3 = TrackedContent("spell", "Fireball", "MM")
        content4 = TrackedContent("creature", "Fireball", "PHB")

        # Test equality
        assert content1 == content2
        assert content1 != content3  # Different source
        assert content1 != content4  # Different type
        assert content1 != "not a TrackedContent"

        # Test hashing (important for set operations)
        assert hash(content1) == hash(content2)
        assert hash(content1) != hash(content3)

        # Test in sets
        content_set = {content1, content2, content3}
        assert len(content_set) == 2  # content1 and content2 are duplicates

    def test_tracked_content_to_tuple(self):
        """Test TrackedContent to_tuple method."""
        content = TrackedContent("spell", "Fireball", "PHB", "123")
        tuple_result = content.to_tuple()
        assert tuple_result == ("spell", "Fireball", "PHB")

        # Test with None source
        content_no_source = TrackedContent("spell", "Fireball", None)
        tuple_result = content_no_source.to_tuple()
        assert tuple_result == ("spell", "Fireball", None)

    def test_get_tracked_content_by_type(self):
        """Test filtering tracked content by type."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Lightning Bolt", "PHB")
        tracker.add_content("creature", "Dragon", "MM")
        tracker.add_content("item", "Sword +1", "DMG")

        spell_content = tracker.get_tracked_content_by_type("spell")
        assert len(spell_content) == 2
        assert all(c.content_type == "spell" for c in spell_content)

        creature_content = tracker.get_tracked_content_by_type("creature")
        assert len(creature_content) == 1
        assert creature_content[0].name == "Dragon"

        # Test case insensitive
        spell_content_upper = tracker.get_tracked_content_by_type("SPELL")
        assert len(spell_content_upper) == 2

        # Test non-existent type
        nonexistent = tracker.get_tracked_content_by_type("nonexistent")
        assert len(nonexistent) == 0

    def test_get_content_count(self):
        """Test getting reference counts for specific content."""
        tracker = ContentTracker()

        # Add same content multiple times
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Fireball", "PHB")

        # Test count retrieval
        count = tracker.get_content_count("spell", "Fireball", "PHB")
        assert count == 3

        # Test case insensitive type
        count_upper = tracker.get_content_count("SPELL", "Fireball", "PHB")
        assert count_upper == 3

        # Test non-existent content
        count_none = tracker.get_content_count("spell", "Nonexistent", "PHB")
        assert count_none == 0

        # Test with whitespace in name
        count_whitespace = tracker.get_content_count("spell", "  Fireball  ", "PHB")
        assert count_whitespace == 3

    def test_get_content_types(self):
        """Test getting all tracked content types."""
        tracker = ContentTracker()

        # Empty tracker
        assert tracker.get_content_types() == []

        # Add various types
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("creature", "Dragon", "MM")
        tracker.add_content("spell", "Lightning Bolt", "PHB")
        tracker.add_content("item", "Sword", "DMG")

        types = tracker.get_content_types()
        assert set(types) == {"creature", "item", "spell"}
        assert types == sorted(types)  # Should be sorted

    def test_get_statistics(self):
        """Test getting tracking statistics."""
        tracker = ContentTracker()

        # Empty tracker
        stats = tracker.get_statistics()
        assert stats["total_unique_content"] == 0
        assert stats["total_references"] == 0

        # Add content
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Fireball", "PHB")  # Duplicate reference
        tracker.add_content("spell", "Lightning Bolt", "PHB")
        tracker.add_content("creature", "Dragon", "MM")

        stats = tracker.get_statistics()
        assert stats["total_unique_content"] == 3  # 2 spells + 1 creature
        assert stats["total_references"] == 4  # Fireball counted twice
        assert stats["spell_count"] == 2
        assert stats["creature_count"] == 1

    def test_has_content(self):
        """Test checking if specific content exists."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")

        # Test existing content
        assert tracker.has_content("spell", "Fireball", "PHB")

        # Test case insensitive type
        assert tracker.has_content("SPELL", "Fireball", "PHB")

        # Test non-existent content
        assert not tracker.has_content("spell", "Lightning Bolt", "PHB")
        assert not tracker.has_content("creature", "Fireball", "PHB")
        assert not tracker.has_content("spell", "Fireball", "MM")

        # Test with None source
        tracker.add_content("spell", "Cantrip", None)
        assert tracker.has_content("spell", "Cantrip", None)
        assert not tracker.has_content("spell", "Cantrip", "PHB")

    def test_remove_content(self):
        """Test removing specific content."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Lightning Bolt", "PHB")

        # Test successful removal
        removed = tracker.remove_content("spell", "Fireball", "PHB")
        assert removed is True
        assert not tracker.has_content("spell", "Fireball", "PHB")
        assert len(tracker.get_tracked_content()) == 1

        # Test count is also removed
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 0

        # Test removing non-existent content
        removed = tracker.remove_content("spell", "Nonexistent", "PHB")
        assert removed is False

        # Remaining content should be unaffected
        assert tracker.has_content("spell", "Lightning Bolt", "PHB")

    def test_merge_tracker(self):
        """Test merging two trackers."""
        tracker1 = ContentTracker()
        tracker1.add_content("spell", "Fireball", "PHB")
        tracker1.add_content("creature", "Dragon", "MM")

        tracker2 = ContentTracker()
        tracker2.add_content("spell", "Lightning Bolt", "PHB")
        tracker2.add_content("spell", "Fireball", "PHB")  # Duplicate
        tracker2.add_content("item", "Sword", "DMG")

        tracker1.merge_tracker(tracker2)

        # Check all content is present
        all_content = tracker1.get_tracked_content()
        assert len(all_content) == 4  # 2 spells + 1 creature + 1 item

        # Check reference counts are updated
        assert tracker1.get_content_count("spell", "Fireball", "PHB") == 2
        assert tracker1.get_content_count("spell", "Lightning Bolt", "PHB") == 1

    def test_export_for_appendix(self):
        """Test exporting content for appendix generation."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB", "251")
        tracker.add_content("spell", "Fireball", "PHB")  # Duplicate reference
        tracker.add_content("creature", "Ancient Red Dragon", "MM", "98")

        export = tracker.export_for_appendix()

        # Check structure
        assert "spell" in export
        assert "creature" in export

        # Check spell entry
        spell_entries = export["spell"]
        assert len(spell_entries) == 1
        spell_entry = spell_entries[0]
        assert spell_entry["name"] == "Fireball"
        assert spell_entry["type"] == "spell"
        assert spell_entry["source"] == "PHB"
        assert spell_entry["page"] == "251"
        assert spell_entry["reference_count"] == 2

        # Check creature entry
        creature_entries = export["creature"]
        assert len(creature_entries) == 1
        creature_entry = creature_entries[0]
        assert creature_entry["name"] == "Ancient Red Dragon"
        assert creature_entry["reference_count"] == 1

    def test_content_with_pages(self):
        """Test content tracking with page numbers."""
        tracker = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB", "251")
        tracker.add_content("creature", "Dragon", "MM")  # No page

        content_list = tracker.get_tracked_content()

        # Find the entries
        fireball = next(c for c in content_list if c.name == "Fireball")
        dragon = next(c for c in content_list if c.name == "Dragon")

        assert fireball.page == "251"
        assert dragon.page is None

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        tracker = ContentTracker()

        # Empty strings
        tracker.add_content("", "", "")
        content_list = tracker.get_tracked_content()
        assert len(content_list) == 1
        assert content_list[0].content_type == ""
        assert content_list[0].name == ""
        assert content_list[0].source == ""

        # None values
        tracker.clear()
        tracker.add_content("spell", "Test", None, None)
        content_list = tracker.get_tracked_content()
        assert len(content_list) == 1
        assert content_list[0].source is None
        assert content_list[0].page is None


class TestTagResolverFacade:
    """Tests for the backward compatibility facade."""

    def test_facade_api_compatibility(self):
        """Test that the facade maintains the old API."""
        facade = TagResolverFacade()

        # Should have the same method as the old TagResolver
        assert hasattr(facade, "process_text")

        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        result = facade.process_text(text)

        # Should produce the same output as the old system
        assert "\\textit{Fireball}" in result
        assert "\\textbf{Ancient Red Dragon}" in result

    def test_facade_new_functionality(self):
        """Test that the facade exposes new functionality."""
        facade = TagResolverFacade()

        # Process some text with tags
        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        facade.process_text(text)

        # Should be able to get tracked content
        tracked = facade.get_tracked_content_for_appendix()
        assert len(tracked) == 2
        assert ("creature", "Ancient Red Dragon", "MM") in tracked
        assert ("spell", "Fireball", "PHB") in tracked


class TestIntegrationScenarios:
    """Integration tests for complete tag processing scenarios."""

    def test_complex_document_processing(self):
        """Test processing a complex document with multiple tag types."""

        # facade = TagResolverFacade()
        # result = facade.process_text(document)
        #
        # # Check that all tags are processed correctly
        # assert "\\textbf{great wyrm}" in result
        # assert "\\textit{Fireball}" in result
        # assert "\\texttt{8d6}" in result
        # assert "DC 19" in result
        # assert "+14" in result
        # assert "The Village (p. 45)" in result
        #
        # # Check content tracking
        # tracked = facade.get_tracked_content_for_appendix()
        # expected_tracked = {
        #     ("creature", "Ancient Red Dragon", "MM"),
        #     ("spell", "Fireball", "PHB"),
        #     ("adventure", "Chapter 3", "CoS"),
        # }
        # assert set(tracked) == expected_tracked
        pass  # Placeholder for now

    def test_performance_with_large_document(self):
        """Test performance with a large document containing many tags."""
        # Create a large document with 1000 tags
        tags = [f"{{@spell Spell{i}|PHB}}" for i in range(1000)]
        " ".join(tags)

        # facade = TagResolverFacade()
        #
        # import time
        # start_time = time.time()
        # result = facade.process_text(document)
        # end_time = time.time()
        #
        # # Should complete in reasonable time (adjust threshold as needed)
        # assert end_time - start_time < 5.0  # 5 seconds threshold
        #
        # # Should track all unique spells
        # tracked = facade.get_tracked_content_for_appendix()
        # assert len(tracked) == 1000
        pass  # Placeholder for now

    def test_error_recovery(self):
        """Test that the system recovers gracefully from parsing errors."""

        # facade = TagResolverFacade()
        # result = facade.process_text(document)
        #
        # # Should process valid tags and handle malformed ones gracefully
        # assert "\\textit{Fireball}" in result
        # assert "\\textbf{Dragon}" in result
        # assert isinstance(result, str)  # Should not crash
        pass  # Placeholder for now
