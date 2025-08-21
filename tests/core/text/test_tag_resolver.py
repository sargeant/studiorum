"""Tests for the new AST-based tag resolution system."""

# Import the new tag system components
from typing import Any

from studiorum.core.references.content_tracker import (  # type: ignore
    ContentTracker,
    TrackedContent,
)
from studiorum.core.text.tag_ast import (  # type: ignore
    CreatureTagNode,
    TextNode,
)
from studiorum.core.text.tag_parser import TagParser  # type: ignore
from studiorum.core.text.tag_resolver import TagResolver  # type: ignore


class MockTagNode:
    """Mock AST node for testing purposes."""

    def __init__(self, tag_type: str, original_text_span: Any = None):
        self.tag_type = tag_type
        self.children: list[Any] = []
        self.original_text_span = original_text_span


class MockTextNode:
    """Mock text node for testing purposes."""

    def __init__(self, text: str, original_text_span: Any = None):
        self.text = text
        self.original_text_span = original_text_span


class MockCreatureTagNode(MockTagNode):
    """Mock creature tag node for testing purposes."""

    def __init__(
        self,
        name: str,
        source: Any = None,
        display_text_nodes: Any = None,
        original_text_span: Any = None,
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
        self,
        name: str,
        source: Any = None,
        display_text_nodes: Any = None,
        original_text_span: Any = None,
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

    def __init__(self, expression: str, original_text_span: Any = None):
        super().__init__("dice", original_text_span)
        self.expression = expression


class TestTagParser:
    """Tests for the new lark-based tag parser."""

    def test_parser_handles_simple_text(self) -> None:
        """Test that plain text without tags is parsed correctly."""
        text = "This is plain text with no tags."
        parser: Any = TagParser()
        ast = parser.parse(text)

        assert len(ast.children) == 1
        assert isinstance(ast.children[0], TextNode)
        assert ast.children[0].text == text

    def test_parser_handles_simple_creature_tag(self) -> None:
        """Test parsing a simple creature tag."""
        text = "{@creature Ancient Red Dragon|MM}"
        parser: Any = TagParser()
        ast = parser.parse(text)

        assert len(ast.children) == 1
        assert isinstance(ast.children[0], CreatureTagNode)
        assert ast.children[0].name == "Ancient Red Dragon"
        assert ast.children[0].source == "MM"
        assert len(ast.children[0].display_text_nodes) == 1
        assert isinstance(ast.children[0].display_text_nodes[0], TextNode)
        assert ast.children[0].display_text_nodes[0].text == "Ancient Red Dragon"

    def test_parser_handles_creature_tag_with_display_text(self) -> None:
        """Test parsing creature tag with custom display text."""
        text = "{@creature Ancient Red Dragon|MM|great wyrm}"
        parser: Any = TagParser()
        ast = parser.parse(text)

        creature_node = ast.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Ancient Red Dragon"
        assert creature_node.source == "MM"
        assert len(creature_node.display_text_nodes) == 1
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "great wyrm"

    def test_parser_handles_mixed_content(self) -> None:
        """Test parsing text with multiple tags and plain text."""
        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        parser: Any = TagParser()
        ast = parser.parse(text)

        assert (
            len(ast.children) == 5
        )  # "Cast ", spell_tag, " at the ", creature_tag, "!"
        assert isinstance(ast.children[0], TextNode)
        assert ast.children[0].text == "Cast "

        from studiorum.core.text.tag_ast import SpellTagNode

        assert isinstance(ast.children[1], SpellTagNode)
        assert ast.children[1].name == "Fireball"

        assert isinstance(ast.children[2], TextNode)
        assert ast.children[2].text == " at the "

        assert isinstance(ast.children[3], CreatureTagNode)
        assert ast.children[3].name == "Ancient Red Dragon"

        assert isinstance(ast.children[4], TextNode)
        assert ast.children[4].text == "!"


class TestTagHandlers:
    """Tests for individual tag handlers."""


class TestTagRenderer:
    """Tests for the tag renderer/dispatcher."""


class TestContentTracker:
    """Tests for content tracking functionality."""

    def test_content_tracker_basic_tracking(self) -> None:
        """Test basic content tracking."""
        tracker: Any = ContentTracker()
        tracker.add_content("creature", "Ancient Red Dragon", "MM")
        tracker.add_content("spell", "Fireball", "PHB")

        tracked = tracker.get_tracked_content()
        assert len(tracked) == 2

        # Check that content exists (order may vary) - names preserve original case
        types_and_names = [(c.content_type, c.name, c.source) for c in tracked]
        assert ("creature", "Ancient Red Dragon", "MM") in types_and_names
        assert ("spell", "Fireball", "PHB") in types_and_names

    def test_content_tracker_deduplication(self) -> None:
        """Test that duplicate content is not tracked multiple times."""
        tracker: Any = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Fireball", "PHB")  # Duplicate
        tracker.add_content(
            "SPELL", "Fireball", "PHB"
        )  # Same but different case content_type

        tracked = tracker.get_tracked_content()
        assert len(tracked) == 1  # Should deduplicate

        content = tracked[0]
        assert content.content_type == "spell"  # Normalized to lowercase
        assert content.name == "Fireball"  # Preserves original case of first occurrence
        assert content.source == "PHB"

        # Check reference count is incremented for all three additions
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 3

        # Test that names are normalized to lowercase (same spell)
        tracker.add_content(
            "spell", "fireball", "PHB"
        )  # Same spell, different case input
        tracked = tracker.get_tracked_content()
        assert len(tracked) == 1  # Should still be deduplicated due to normalization

        # Verify reference count increased
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 4

        # Test with truly different name
        tracker.add_content("spell", "Lightning Bolt", "PHB")
        tracked = tracker.get_tracked_content()
        assert len(tracked) == 2  # Should now have two different spells

    def test_content_tracker_sorting(self) -> None:
        """Test that tracked content is returned in sorted order."""
        tracker: Any = ContentTracker()
        tracker.add_content("spell", "Zephyr Strike", "PHB")
        tracker.add_content("creature", "Ancient Red Dragon", "MM")
        tracker.add_content("spell", "Fireball", "PHB")

        tracked = tracker.get_tracked_content()

        # Should be sorted by: content_type, name, source
        expected_order = [
            ("creature", "Ancient Red Dragon", "MM"),  # Names preserve original case
            ("spell", "Fireball", "PHB"),
            ("spell", "Zephyr Strike", "PHB"),
        ]

        actual_order = [(c.content_type, c.name, c.source) for c in tracked]
        assert actual_order == expected_order

    def test_content_tracker_clear(self) -> None:
        """Test clearing tracked content."""
        tracker: Any = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("creature", "Dragon", "MM")
        assert len(tracker.get_tracked_content()) == 2
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 1

        tracker.clear()
        assert len(tracker.get_tracked_content()) == 0
        assert tracker.get_content_count("spell", "Fireball", "PHB") == 0
        assert len(tracker.get_content_types()) == 0

    def test_tracked_content_normalization(self) -> None:
        """Test TrackedContent normalization with field validators."""
        # Test content_type normalization (lowercase)
        content: Any = TrackedContent(
            content_type="SPELL", name="Fireball", source="PHB"
        )
        assert content.content_type == "spell"

        # Test name stripping (preserves original case)
        content2: Any = TrackedContent(
            content_type="spell", name="  Fireball  ", source="PHB"
        )
        assert (
            content2.name == "Fireball"
        )  # Names preserve original case, whitespace stripped

        # Test source stripping
        content3: Any = TrackedContent(
            content_type="spell", name="Fireball", source="  PHB  "
        )
        assert content3.source == "PHB"

        # Test page stripping
        content4: Any = TrackedContent(
            content_type="spell", name="Fireball", source="PHB", page="  123  "
        )
        assert content4.page == "123"

    def test_tracked_content_equality_and_hashing(self) -> None:
        """Test TrackedContent equality and hashing behavior."""
        content1: Any = TrackedContent(
            content_type="spell", name="Fireball", source="PHB"
        )
        content2: Any = TrackedContent(
            content_type="spell", name="Fireball", source="PHB"
        )
        content3: Any = TrackedContent(
            content_type="spell", name="Fireball", source="MM"
        )
        content4: Any = TrackedContent(
            content_type="creature", name="Fireball", source="PHB"
        )

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

    def test_tracked_content_to_tuple(self) -> None:
        """Test TrackedContent to_tuple method."""
        content: Any = TrackedContent(
            content_type="spell", name="Fireball", source="PHB", page="123"
        )
        tuple_result = content.to_tuple()
        assert tuple_result == (
            "spell",
            "fireball",
            "PHB",
        )  # Names normalized to lowercase

        # Test with None source
        content_no_source: Any = TrackedContent(
            content_type="spell", name="Fireball", source=None
        )
        tuple_result = content_no_source.to_tuple()
        assert tuple_result == (
            "spell",
            "fireball",
            None,
        )  # Names normalized to lowercase

    def test_get_tracked_content_by_type(self) -> None:
        """Test filtering tracked content by type."""
        tracker: Any = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB")
        tracker.add_content("spell", "Lightning Bolt", "PHB")
        tracker.add_content("creature", "Dragon", "MM")
        tracker.add_content("item", "Sword +1", "DMG")

        spell_content = tracker.get_tracked_content_by_type("spell")
        assert len(spell_content) == 2
        assert all(c.content_type == "spell" for c in spell_content)

        creature_content = tracker.get_tracked_content_by_type("creature")
        assert len(creature_content) == 1
        assert creature_content[0].name == "Dragon"  # Names preserve original case

        # Test case insensitive
        spell_content_upper = tracker.get_tracked_content_by_type("SPELL")
        assert len(spell_content_upper) == 2

        # Test non-existent type
        nonexistent = tracker.get_tracked_content_by_type("nonexistent")
        assert len(nonexistent) == 0

    def test_get_content_count(self) -> None:
        """Test getting reference counts for specific content."""
        tracker: Any = ContentTracker()

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

    def test_get_content_types(self) -> None:
        """Test getting all tracked content types."""
        tracker: Any = ContentTracker()

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

    def test_get_statistics(self) -> None:
        """Test getting tracking statistics."""
        tracker: Any = ContentTracker()

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

    def test_has_content(self) -> None:
        """Test checking if specific content exists."""
        tracker: Any = ContentTracker()
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

    def test_remove_content(self) -> None:
        """Test removing specific content."""
        tracker: Any = ContentTracker()
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

    def test_merge_tracker(self) -> None:
        """Test merging two trackers."""
        tracker1: Any = ContentTracker()
        tracker1.add_content("spell", "Fireball", "PHB")
        tracker1.add_content("creature", "Dragon", "MM")

        tracker2: Any = ContentTracker()
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

    def test_export_for_appendix(self) -> None:
        """Test exporting content for appendix generation."""
        tracker: Any = ContentTracker()
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
        assert spell_entry["name"] == "Fireball"  # Names preserve original case
        assert spell_entry["type"] == "spell"
        assert spell_entry["source"] == "PHB"
        assert spell_entry["page"] == "251"
        assert spell_entry["reference_count"] == 2

        # Check creature entry
        creature_entries = export["creature"]
        assert len(creature_entries) == 1
        creature_entry = creature_entries[0]
        assert (
            creature_entry["name"] == "Ancient Red Dragon"
        )  # Names preserve original case
        assert creature_entry["reference_count"] == 1

    def test_content_with_pages(self) -> None:
        """Test content tracking with page numbers."""
        tracker: Any = ContentTracker()
        tracker.add_content("spell", "Fireball", "PHB", "251")
        tracker.add_content("creature", "Dragon", "MM")  # No page

        content_list = tracker.get_tracked_content()

        # Find the entries (names preserve original case)
        fireball: Any = next(c for c in content_list if c.name == "Fireball")
        dragon: Any = next(c for c in content_list if c.name == "Dragon")

        assert fireball.page == "251"
        assert dragon.page is None

    def test_edge_cases(self) -> None:
        """Test edge cases and boundary conditions."""
        tracker: Any = ContentTracker()

        # Test with minimal valid strings (now that we have min_length=1)
        tracker.add_content("a", "b", "")  # Empty source is allowed but becomes None
        content_list = tracker.get_tracked_content()
        assert len(content_list) == 1
        assert content_list[0].content_type == "a"
        assert content_list[0].name == "b"
        assert content_list[0].source is None  # Empty string becomes None

        # None values for optional fields
        tracker.clear()
        tracker.add_content("spell", "Test", None, None)
        content_list = tracker.get_tracked_content()
        assert len(content_list) == 1
        assert content_list[0].source is None
        assert content_list[0].page is None

        # Test validation errors for empty required fields
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            tracker.add_content("", "Test", None)  # Empty content_type should fail
        with pytest.raises(ValidationError):
            tracker.add_content("spell", "", None)  # Empty name should fail


class TestTagResolverFacade:
    """Tests for the backward compatibility facade."""

    def test_facade_api_compatibility(self) -> None:
        """Test that the resolver provides the expected API."""
        resolver: Any = TagResolver()

        # Should have the core TagResolver API
        assert hasattr(resolver, "process_text")

        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        result = resolver.process_text(text)

        # Should produce the same output as the old system
        assert "\\textit{Fireball}" in result
        assert "\\textbf{Ancient Red Dragon}" in result

    def test_facade_new_functionality(self) -> None:
        """Test that the facade exposes new functionality."""
        resolver: Any = TagResolver()

        # Process some text with tags
        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        result = resolver.process_text(text)

        # Should process the text and return formatted output
        assert isinstance(result, str)
        # The actual content tracking would be handled by the renderer's content tracker
        # which isn't directly exposed through the TagResolver interface


class TestIntegrationScenarios:
    """Integration tests for complete tag processing scenarios."""
