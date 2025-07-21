"""Tests for tag resolution system."""

from typing import Any

import pytest

from dnd5e.core.indexer.tag_resolver import TagMatch, TagResolver  # type: ignore


class TestTagMatch:
    """Tests for TagMatch class."""

    def test_tag_match_parsing(self) -> None:
        """Test parsing tag content into components."""
        # Simple tag
        match = TagMatch.parse("spell", "fireball", "{@spell fireball}")
        assert match.tag_type == "spell"
        assert match.name == "fireball"
        assert match.source is None
        assert match.display_text is None

        # Tag with source
        match = TagMatch.parse("spell", "fireball|PHB", "{@spell fireball|PHB}")
        assert match.name == "fireball"
        assert match.source == "PHB"

        # Tag with display text
        match = TagMatch.parse(
            "spell", "fireball|PHB|magical fire", "{@spell fireball|PHB|magical fire}"
        )
        assert match.name == "fireball"
        assert match.source == "PHB"
        assert match.display_text == "magical fire"

        # Tag with page reference
        match = TagMatch.parse(
            "adventure",
            "chapter 1|CoS|Into the Mists|21",
            "{@adventure chapter 1|CoS|Into the Mists|21}",
        )
        assert match.name == "chapter 1"
        assert match.source == "CoS"
        assert match.display_text == "Into the Mists"
        assert match.page == "21"


class TestTagResolver:
    """Tests for TagResolver class."""

    def test_tag_resolver_creation(self, loaded_omnidexer: Any) -> None:
        """Test basic tag resolver creation."""
        resolver: Any = TagResolver(loaded_omnidexer)
        assert resolver is not None
        assert len(resolver._tag_handlers) > 0

    def test_custom_handler_registration(self, loaded_omnidexer: Any) -> None:
        """Test registering custom tag handlers."""
        resolver: Any = TagResolver(loaded_omnidexer)

        def custom_handler(tag: TagMatch) -> str:
            return f"CUSTOM:{tag.name}"

        resolver.register_tag_handler("custom", custom_handler)
        assert "custom" in resolver._tag_handlers

    @pytest.mark.asyncio
    async def test_simple_text_passthrough(self, tag_resolver: Any) -> None:
        """Test that text without tags passes through unchanged."""
        resolver = tag_resolver
        text = "This is plain text with no tags."
        result = resolver.process_text(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_creature_tag_resolution(self, tag_resolver: Any) -> None:
        """Test creature tag resolution."""
        resolver = tag_resolver
        text = "The {@creature Ancient Red Dragon|MM} attacks!"
        result = resolver.process_text(text)

        # Should contain the creature name in bold
        assert "Ancient Red Dragon" in result
        assert "\\textbf{" in result
        assert "}" in result

    @pytest.mark.asyncio
    async def test_spell_tag_resolution(self, tag_resolver: Any) -> None:
        """Test spell tag resolution."""
        resolver = tag_resolver
        text = "She casts {@spell Fireball|PHB}."
        result = resolver.process_text(text)

        # Should contain the spell name in italics
        assert "Fireball" in result
        assert "\\textit{" in result
        assert "}" in result

    @pytest.mark.asyncio
    async def test_tag_with_display_text(self, tag_resolver: Any) -> None:
        """Test tag resolution with custom display text."""
        resolver = tag_resolver
        text = "The {@creature Ancient Red Dragon|MM|great wyrm} is ancient."
        result = resolver.process_text(text)

        # Should use display text instead of actual name
        assert "great wyrm" in result
        assert "Ancient Red Dragon" not in result

    @pytest.mark.asyncio
    async def test_unknown_content_fallback(self, tag_resolver: Any) -> None:
        """Test fallback for unknown content."""
        resolver = tag_resolver
        text = "The {@creature Unknown Creature|PHB} appears."
        result = resolver.process_text(text)

        # Should fall back to name
        assert "Unknown Creature" in result

    @pytest.mark.asyncio
    async def test_formatting_tags(self, tag_resolver: Any) -> None:
        """Test formatting tags like bold, italic, dice."""
        resolver = tag_resolver
        test_cases = [
            ("Make a {@dice 1d20} roll.", "\\texttt{1d20}"),
            ("The {@bold important text} is highlighted.", "\\textbf{important text}"),
            ("This is {@italic emphasized text}.", "\\textit{emphasized text}"),
            ("Short {@b bold} and {@i italic} text.", "\\textbf{bold}"),
        ]

        for input_text, expected_content in test_cases:
            result = resolver.process_text(input_text)
            assert expected_content in result

    @pytest.mark.asyncio
    async def test_special_tags(self, tag_resolver: Any) -> None:
        """Test special formatting tags."""
        resolver = tag_resolver
        test_cases = [
            ("Make a {@hit 7} attack.", "+7"),
            ("The save DC is {@dc 15}.", "DC 15"),
            ("It has a {@chance 25} chance.", "25\\%"),
            ("The ability {@recharge 5} is powerful.", "(Recharge 5--6)"),
            ("This {@recharge 4-6} recharges.", "(Recharge 4-6)"),
        ]

        for input_text, expected_content in test_cases:
            result = resolver.process_text(input_text)
            assert expected_content in result

    @pytest.mark.asyncio
    async def test_latex_escaping(self, tag_resolver: Any) -> None:
        """Test LaTeX character escaping."""
        resolver = tag_resolver
        # Test with content that needs escaping
        text = "The {@bold 50% chance & $100 cost} is important."
        result = resolver.process_text(text)

        # Should escape LaTeX special characters
        assert "\\%" in result
        assert "\\&" in result
        assert "\\$" in result

    @pytest.mark.asyncio
    async def test_multiple_tags_in_text(self, tag_resolver: Any) -> None:
        """Test processing multiple tags in same text."""
        resolver = tag_resolver
        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        result = resolver.process_text(text)

        # Both tags should be processed
        assert "\\textit{Fireball}" in result
        assert "\\textbf{Ancient Red Dragon}" in result

    @pytest.mark.asyncio
    async def test_nested_tags_handling(self, tag_resolver: Any) -> None:
        """Test that nested tags are handled appropriately."""
        resolver = tag_resolver
        # Note: Real nested tags are complex, this tests basic handling
        text = "The {@creature Ancient Red Dragon|MM} casts {@spell Fireball|PHB}."
        result = resolver.process_text(text)

        # Should process both tags
        assert "Ancient Red Dragon" in result
        assert "Fireball" in result

    @pytest.mark.asyncio
    async def test_malformed_tag_handling(self, tag_resolver: Any) -> None:
        """Test handling of malformed tags."""
        resolver = tag_resolver
        test_cases = [
            "{@spell}",  # Missing content
            "{@spell |PHB}",  # Empty name
            "{@unknown_tag test}",  # Unknown tag type
            "{@spell fireball",  # Missing closing brace
        ]

        for malformed_tag in test_cases:
            text = f"This has a {malformed_tag} in it."
            result = resolver.process_text(text)

            # Should not crash and should contain the original text
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_tag_without_source_resolution(self, tag_resolver: Any) -> None:
        """Test resolving tags without specifying source."""
        resolver = tag_resolver
        text = "Cast {@spell Fireball} to deal damage."
        result = resolver.process_text(text)

        # Should find and format the spell
        assert "\\textit{Fireball}" in result

    @pytest.mark.asyncio
    async def test_filter_and_loader_tag_omission(self, tag_resolver: Any) -> None:
        """Test that filter and loader tags are omitted from output."""
        resolver = tag_resolver
        text = "This {@filter Spells|spell=fireball} and {@loader content} should be hidden."
        result = resolver.process_text(text)

        # Filter and loader content should be removed
        assert "filter" not in result.lower()
        assert "loader" not in result.lower()
        assert (
            "This  and  should be hidden." in result
        )  # Double spaces from removed content

    @pytest.mark.asyncio
    async def test_adventure_and_book_tags(self, tag_resolver: Any) -> None:
        """Test adventure and book reference tags."""
        resolver = tag_resolver
        test_cases = [
            ("See {@adventure Curse of Strahd|CoS}.", "Curse of Strahd"),
            (
                "Refer to {@book Player's Handbook|PHB|123}.",
                "Player's Handbook, p. 123",
            ),
            (
                "In {@adventure Chapter 1|CoS|Into the Mists|21}.",
                "Into the Mists (p. 21)",
            ),
        ]

        for input_text, expected_content in test_cases:
            result = resolver.process_text(input_text)
            assert expected_content in result
