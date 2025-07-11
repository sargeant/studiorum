"""Tag resolution system for processing {@type name|source|display} tags."""

import re
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass

from ..loaders.omnidexer import Omnidexer
from ..models.content import ContentType
from ..config.settings import get_logger

logger = get_logger(__name__)


@dataclass
class TagMatch:
    """Represents a parsed tag match."""

    tag_type: str
    name: str
    source: Optional[str] = None
    display_text: Optional[str] = None
    page: Optional[str] = None
    full_match: str = ""

    @classmethod
    def parse(cls, tag_type: str, content: str, full_match: str) -> "TagMatch":
        """Parse tag content into components."""
        # Split content by | separator
        parts = [part.strip() for part in content.split("|")]

        name = parts[0] if parts else ""
        source = parts[1] if len(parts) > 1 and parts[1] else None
        display_text = parts[2] if len(parts) > 2 and parts[2] else None
        page = parts[3] if len(parts) > 3 and parts[3] else None

        return cls(
            tag_type=tag_type,
            name=name,
            source=source,
            display_text=display_text,
            page=page,
            full_match=full_match,
        )


class TagResolver:
    """Resolves {@type name|source|display} tags to actual content references."""

    # Pattern matches: {@creature Strahd von Zarovich|CoS|the vampire lord}
    TAG_PATTERN = re.compile(r"{@(\w+)\s+([^}]+)}")

    def __init__(self, omnidexer: Omnidexer):
        self.omnidexer = omnidexer
        self._tag_handlers: Dict[str, Callable[[TagMatch], str]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default tag handlers for common content types."""
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
                # Formatting tags
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

    def register_tag_handler(self, tag_type: str, handler: Callable[[TagMatch], str]):
        """Register a custom tag handler."""
        self._tag_handlers[tag_type] = handler
        logger.info(f"Registered handler for tag type: {tag_type}")

    def process_text(self, text: str) -> str:
        """Process text and resolve all tags to formatted output."""
        if not text or "{@" not in text:
            return text

        def replace_tag(match):
            try:
                tag_match = TagMatch.parse(
                    match.group(1),  # tag_type
                    match.group(2),  # content
                    match.group(0),  # full_match
                )
                return self._resolve_tag(tag_match)
            except Exception as e:
                logger.warning(f"Failed to resolve tag {match.group(0)}: {e}")
                return match.group(0)  # Return original if resolution fails

        return self.TAG_PATTERN.sub(replace_tag, text)

    def _resolve_tag(self, tag_match: TagMatch) -> str:
        """Resolve a parsed tag to formatted output."""
        handler = self._tag_handlers.get(tag_match.tag_type)
        if not handler:
            logger.debug(f"No handler for tag type: {tag_match.tag_type}")
            # Return display text or name as fallback
            return tag_match.display_text or tag_match.name

        try:
            return handler(tag_match)
        except Exception as e:
            logger.error(f"Handler failed for {tag_match.tag_type}: {e}")
            return tag_match.display_text or tag_match.name

    # Content Reference Handlers

    def _handle_creature_tag(self, tag: TagMatch) -> str:
        """Handle {@creature} tags."""
        content = self.omnidexer.find(ContentType.CREATURE, tag.name, tag.source)
        if not content:
            logger.debug(
                f"Creature not found: {tag.name} ({tag.source or 'any source'})"
            )
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textbf{{{self._escape_latex(display)}}}"

    def _handle_spell_tag(self, tag: TagMatch) -> str:
        """Handle {@spell} tags."""
        content = self.omnidexer.find(ContentType.SPELL, tag.name, tag.source)
        if not content:
            logger.debug(f"Spell not found: {tag.name} ({tag.source or 'any source'})")
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textit{{{self._escape_latex(display)}}}"

    def _handle_item_tag(self, tag: TagMatch) -> str:
        """Handle {@item} tags."""
        content = self.omnidexer.find(ContentType.ITEM, tag.name, tag.source)
        if not content:
            logger.debug(f"Item not found: {tag.name} ({tag.source or 'any source'})")
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textit{{{self._escape_latex(display)}}}"

    def _handle_adventure_tag(self, tag: TagMatch) -> str:
        """Handle {@adventure} tags."""
        display = tag.display_text or tag.name
        if tag.page:
            return f"{self._escape_latex(display)} (p. {tag.page})"
        return self._escape_latex(display)

    def _handle_book_tag(self, tag: TagMatch) -> str:
        """Handle {@book} tags."""
        display = tag.display_text or tag.name
        if tag.page:
            return f"{self._escape_latex(display)}, p. {tag.page}"
        return self._escape_latex(display)

    def _handle_class_tag(self, tag: TagMatch) -> str:
        """Handle {@class} tags."""
        display = tag.display_text or tag.name
        return f"\\textbf{{{self._escape_latex(display)}}}"

    def _handle_background_tag(self, tag: TagMatch) -> str:
        """Handle {@background} tags."""
        display = tag.display_text or tag.name
        return self._escape_latex(display)

    def _handle_feat_tag(self, tag: TagMatch) -> str:
        """Handle {@feat} tags."""
        display = tag.display_text or tag.name
        return f"\\textbf{{{self._escape_latex(display)}}}"

    def _handle_race_tag(self, tag: TagMatch) -> str:
        """Handle {@race} tags."""
        display = tag.display_text or tag.name
        return self._escape_latex(display)

    # Formatting Handlers

    def _handle_dice_tag(self, tag: TagMatch) -> str:
        """Handle {@dice} tags."""
        return f"\\texttt{{{self._escape_latex(tag.name)}}}"

    def _handle_bold_tag(self, tag: TagMatch) -> str:
        """Handle {@bold} and {@b} tags."""
        return f"\\textbf{{{self._escape_latex(tag.name)}}}"

    def _handle_italic_tag(self, tag: TagMatch) -> str:
        """Handle {@italic} and {@i} tags."""
        return f"\\textit{{{self._escape_latex(tag.name)}}}"

    # Special Tags

    def _handle_damage_tag(self, tag: TagMatch) -> str:
        """Handle {@damage} tags."""
        return self._escape_latex(tag.name)

    def _handle_condition_tag(self, tag: TagMatch) -> str:
        """Handle {@condition} tags."""
        display = tag.display_text or tag.name
        return f"\\textit{{{self._escape_latex(display)}}}"

    def _handle_skill_tag(self, tag: TagMatch) -> str:
        """Handle {@skill} tags."""
        display = tag.display_text or tag.name
        return self._escape_latex(display)

    def _handle_sense_tag(self, tag: TagMatch) -> str:
        """Handle {@sense} tags."""
        display = tag.display_text or tag.name
        return self._escape_latex(display)

    def _handle_hit_tag(self, tag: TagMatch) -> str:
        """Handle {@hit} tags for attack rolls."""
        return f"+{tag.name}"

    def _handle_dc_tag(self, tag: TagMatch) -> str:
        """Handle {@dc} tags for difficulty class."""
        return f"DC {tag.name}"

    def _handle_filter_tag(self, tag: TagMatch) -> str:
        """Handle {@filter} tags (usually omitted in text)."""
        return ""  # Filters are typically UI elements, omit from text

    def _handle_loader_tag(self, tag: TagMatch) -> str:
        """Handle {@loader} tags (usually omitted in text)."""
        return ""  # Loaders are UI elements, omit from text

    def _handle_note_tag(self, tag: TagMatch) -> str:
        """Handle {@note} tags."""
        return f"({self._escape_latex(tag.name)})"

    def _handle_chance_tag(self, tag: TagMatch) -> str:
        """Handle {@chance} tags for probability."""
        return f"{tag.name}\\%"

    def _handle_coinflip_tag(self, tag: TagMatch) -> str:
        """Handle {@coinflip} tags."""
        return "50\\%"

    def _handle_recharge_tag(self, tag: TagMatch) -> str:
        """Handle {@recharge} tags."""
        if "-" in tag.name:
            return f"(Recharge {tag.name})"
        else:
            return f"(Recharge {tag.name}--6)"

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters in text."""
        if not text:
            return ""

        # LaTeX special characters that need escaping
        latex_chars = {
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "^": "\\textasciicircum{}",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "\\": "\\textbackslash{}",
        }

        result = text
        for char, escape in latex_chars.items():
            result = result.replace(char, escape)

        return result


class LaTeXTagResolver(TagResolver):
    """Tag resolver specialized for LaTeX output."""

    def __init__(self, omnidexer: Omnidexer):
        super().__init__(omnidexer)
        # LaTeX-specific handlers can be added here

    def _handle_creature_tag(self, tag: TagMatch) -> str:
        """Enhanced creature tag handling for LaTeX."""
        content = self.omnidexer.find(ContentType.CREATURE, tag.name, tag.source)
        if not content:
            logger.debug(
                f"Creature not found: {tag.name} ({tag.source or 'any source'})"
            )
            display = tag.display_text or tag.name
            return f"\\textbf{{{self._escape_latex(display)}}}"

        display = tag.display_text or content.name
        # Could add page references, stats, etc. here
        return f"\\textbf{{{self._escape_latex(display)}}}"

    def _handle_spell_tag(self, tag: TagMatch) -> str:
        """Enhanced spell tag handling for LaTeX."""
        content = self.omnidexer.find(ContentType.SPELL, tag.name, tag.source)
        if not content:
            logger.debug(f"Spell not found: {tag.name} ({tag.source or 'any source'})")
            display = tag.display_text or tag.name
            return f"\\textit{{{self._escape_latex(display)}}}"

        display = tag.display_text or content.name
        # Could add spell level information here
        return f"\\textit{{{self._escape_latex(display)}}}"
