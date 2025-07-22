"""Semantic tag resolution - handles finding content without formatting."""

from collections.abc import Callable
from typing import Union

from ..logging import get_logger
from ..models.content import ContentType
from .tag_resolver import TagMatch
from .tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
    TagResolutionResult,
)

logger = get_logger(__name__)


class SemanticTagResolver:
    """Resolves tags to structured objects without applying any formatting.

    This class handles the semantic resolution phase - determining what a tag
    references and creating structured representations. It does NOT handle
    formatting like LaTeX escaping or applying style commands.
    """

    def __init__(self, context: TagContext):
        self.context = context
        self._tag_handlers: dict[str, Callable[[TagMatch], TagResolutionResult]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default semantic handlers for common content types."""
        self._tag_handlers.update(
            {
                # Content reference tags
                "creature": self._handle_creature_tag,
                "spell": self._handle_spell_tag,
                "item": self._handle_item_tag,
                "adventure": self._handle_adventure_tag,
                "book": self._handle_book_tag,
                "class": self._handle_class_tag,
                "background": self._handle_background_tag,
                "feat": self._handle_feat_tag,
                "race": self._handle_race_tag,
                # Pure formatting tags
                "dice": self._handle_dice_tag,
                "bold": self._handle_bold_tag,
                "italic": self._handle_italic_tag,
                "b": self._handle_bold_tag,  # Alias
                "i": self._handle_italic_tag,  # Alias
                # Special tags
                "damage": self._handle_damage_tag,
                "condition": self._handle_condition_tag,
                "skill": self._handle_skill_tag,
                "sense": self._handle_sense_tag,
                "hit": self._handle_hit_tag,
                "dc": self._handle_dc_tag,
                "filter": self._handle_filter_tag,
                "loader": self._handle_loader_tag,
                "note": self._handle_note_tag,
                "chance": self._handle_chance_tag,
                "coinflip": self._handle_coinflip_tag,
                "recharge": self._handle_recharge_tag,
            }
        )

    def register_tag_handler(
        self, tag_type: str, handler: Callable[[TagMatch], TagResolutionResult]
    ) -> None:
        """Register a custom semantic tag handler."""
        self._tag_handlers[tag_type] = handler
        logger.info(f"Registered semantic handler for tag type: {tag_type}")

    def resolve_tag(self, tag_match: TagMatch) -> TagResolutionResult:
        """Resolve a parsed tag to a structured object."""
        handler = self._tag_handlers.get(tag_match.tag_type)
        if not handler:
            logger.debug(f"No semantic handler for tag type: {tag_match.tag_type}")
            # Return display text or name as plain string fallback
            return tag_match.display_text or tag_match.name

        try:
            return handler(tag_match)
        except Exception as e:
            logger.error(f"Semantic handler failed for {tag_match.tag_type}: {e}")
            return tag_match.display_text or tag_match.name

    # Content Reference Handlers

    def _handle_creature_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@creature} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.CREATURE, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.CREATURE,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_spell_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@spell} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.SPELL, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.SPELL,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_item_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@item} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.ITEM, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.ITEM,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_adventure_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@adventure} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.ADVENTURE, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.ADVENTURE,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_book_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@book} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.BOOK, tag.name, tag.source)

        # Handle special case where display_text might be a page number
        display_text = tag.display_text
        page = tag.page

        if tag.display_text and tag.display_text.isdigit():
            # If display_text looks like a page number, use it as page
            page = tag.display_text
            display_text = None

        return ContentReference(
            content_type=ContentType.BOOK,
            name=tag.name,
            source=tag.source,
            display_text=display_text,
            page=page,
            resolved_content=content,
        )

    def _handle_class_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@class} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.CLASS, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.CLASS,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_background_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@background} tags - resolve to ContentReference."""
        content = self.context.find_content(
            ContentType.BACKGROUND, tag.name, tag.source
        )

        return ContentReference(
            content_type=ContentType.BACKGROUND,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_feat_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@feat} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.FEAT, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.FEAT,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    def _handle_race_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@race} tags - resolve to ContentReference."""
        content = self.context.find_content(ContentType.RACE, tag.name, tag.source)

        return ContentReference(
            content_type=ContentType.RACE,
            name=tag.name,
            source=tag.source,
            display_text=tag.display_text,
            page=tag.page,
            resolved_content=content,
        )

    # Formatting Handlers

    def _handle_dice_tag(self, tag: TagMatch) -> FormattingNode:
        """Handle {@dice} tags - formatting as monospace."""
        return FormattingNode(
            format_type=FormatType.MONOSPACE,
            content=tag.name,
        )

    def _handle_bold_tag(self, tag: TagMatch) -> FormattingNode:
        """Handle {@bold} and {@b} tags."""
        return FormattingNode(
            format_type=FormatType.BOLD,
            content=tag.name,
        )

    def _handle_italic_tag(self, tag: TagMatch) -> FormattingNode:
        """Handle {@italic} and {@i} tags."""
        return FormattingNode(
            format_type=FormatType.ITALIC,
            content=tag.name,
        )

    # Special Tags

    def _handle_damage_tag(self, tag: TagMatch) -> ContentReference | str:
        """Handle {@damage} tags - could be content reference or plain text."""
        # Try to resolve as content first (for damage types in content)
        content = self.context.find_content(ContentType.ITEM, tag.name, tag.source)
        if content:
            return ContentReference(
                content_type=ContentType.ITEM,
                name=tag.name,
                source=tag.source,
                display_text=tag.display_text,
                page=tag.page,
                resolved_content=content,
            )
        # Otherwise return as plain text
        return tag.display_text or tag.name

    def _handle_condition_tag(self, tag: TagMatch) -> FormattingNode | str:
        """Handle {@condition} tags - could be content reference."""
        # Try to find condition content
        # Note: ContentType.CONDITION doesn't exist yet, but this shows the pattern
        # For now, return as emphasis formatting
        return FormattingNode(
            format_type=FormatType.ITALIC,
            content=tag.display_text or tag.name,
        )

    def _handle_skill_tag(self, tag: TagMatch) -> str:
        """Handle {@skill} tags - return as plain text."""
        return tag.display_text or tag.name

    def _handle_sense_tag(self, tag: TagMatch) -> str:
        """Handle {@sense} tags - return as plain text."""
        return tag.display_text or tag.name

    def _handle_hit_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@hit} tags for attack rolls."""
        return SpecialTag(
            tag_type="hit",
            value=tag.name,
            display_text=tag.display_text,
        )

    def _handle_dc_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@dc} tags for difficulty class."""
        return SpecialTag(
            tag_type="dc",
            value=tag.name,
            display_text=tag.display_text,
        )

    def _handle_filter_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@filter} tags (usually omitted in text)."""
        return SpecialTag(
            tag_type="filter",
            value="",  # Filters are typically UI elements
            display_text=tag.display_text,
        )

    def _handle_loader_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@loader} tags (usually omitted in text)."""
        return SpecialTag(
            tag_type="loader",
            value="",  # Loaders are UI elements
            display_text=tag.display_text,
        )

    def _handle_note_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@note} tags."""
        return SpecialTag(
            tag_type="note",
            value=tag.name,
            display_text=tag.display_text,
        )

    def _handle_chance_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@chance} tags for probability."""
        return SpecialTag(
            tag_type="chance",
            value=tag.name,
            display_text=tag.display_text,
        )

    def _handle_coinflip_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@coinflip} tags."""
        return SpecialTag(
            tag_type="coinflip",
            value="50",
            display_text=tag.display_text,
        )

    def _handle_recharge_tag(self, tag: TagMatch) -> SpecialTag:
        """Handle {@recharge} tags."""
        # Normalize recharge values
        value = tag.name
        if "-" not in value:
            value = f"{value}--6"

        return SpecialTag(
            tag_type="recharge",
            value=value,
            display_text=tag.display_text,
        )
