"""Template service implementation for LaTeX document generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.core.text.tag_resolver import TagResolver

logger = get_logger(__name__)


class TemplateService:
    """Template service for processing entries with explicit context passing.

    This service eliminates the need for stack inspection by providing
    explicit context passing for all template rendering operations.
    """

    def __init__(
        self,
        tag_resolver: TagResolver,
        omnidexer: Omnidexer,
    ) -> None:
        """Initialize the template service.

        Args:
            tag_resolver: Tag resolver service for processing tags
            omnidexer: Omnidexer service for content resolution
        """
        self.tag_resolver = tag_resolver
        self.omnidexer = omnidexer

    def get_service_name(self) -> str:
        """Return service name for debugging."""
        return "TemplateService"

    def render_entry_description(
        self,
        entry: Any,
        content_tracker: ContentTracker,
    ) -> str:
        """Render entry description with explicit context passing.

        This method provides a context-aware alternative to the problematic
        get_description_text() methods that used stack inspection.

        Args:
            entry: Entry object containing description data
            content_tracker: Content tracker for appendix generation

        Returns:
            Rendered description text suitable for LaTeX templates
        """
        if entry is None:
            return ""

        # Extract text from entry based on structure
        text = self._extract_text_from_entry(entry)
        if not text:
            return ""

        # Create rendering context with content tracker
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
            debug_mode=False,
        )

        # Process the text using the tag resolver with explicit context
        try:
            return self.tag_resolver.process_text(text, rendering_context)
        except Exception as e:
            logger.warning(f"Failed to process entry text: {e}")
            # Fallback to escaped raw text
            return self._escape_latex(text)

    def _extract_text_from_entry(self, entry: Any) -> str:
        """Extract text content from various entry formats.

        Args:
            entry: Entry object in various formats

        Returns:
            Extracted text content
        """
        if isinstance(entry, str):
            return entry

        if isinstance(entry, dict):
            # Handle common 5etools entry patterns
            if "entries" in entry and entry["entries"] is not None:
                # Recursively process nested entries
                parts = []
                # Include the name if present (for LaTeX formatting like \subsection{Name})
                if "name" in entry and entry["name"]:
                    parts.append(entry["name"])
                # Include the "by" field if present (author attribution)
                if "by" in entry and entry["by"]:
                    parts.append(f"by {entry['by']}")
                for sub_entry in entry["entries"]:
                    text = self._extract_text_from_entry(sub_entry)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)
            elif "text" in entry:
                # Include name if present for named text entries
                if "name" in entry and entry["name"]:
                    return f"{entry['name']} {entry['text']}"
                return entry["text"]
            elif "items" in entry and isinstance(entry["items"], list):
                # Handle list items
                parts = []
                for item in entry["items"]:
                    text = self._extract_text_from_entry(item)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)
            elif "entries" in entry and isinstance(entry["entries"], list):
                # Handle entries list
                parts = []
                for e in entry["entries"]:
                    text = self._extract_text_from_entry(e)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)

        # Handle objects with get_description_text method (like test mocks)
        if hasattr(entry, "get_description_text"):
            return entry.get_description_text()

        # Handle spellcasting objects specifically
        if hasattr(entry, "headerEntries") and hasattr(entry, "spells"):
            parts = []

            # Add header entries
            if entry.headerEntries:
                header_parts = []
                for header in entry.headerEntries:
                    header_parts.append(self._extract_text_from_entry(header))
                if header_parts:
                    parts.append(" ".join(header_parts))

            # Add spell lists if present
            if entry.spells:
                spell_parts = []
                for level, spell_group in entry.spells.items():
                    level_name = (
                        "Cantrips"
                        if level == "0"
                        else f"{level}{'st' if level == '1' else 'nd' if level == '2' else 'rd' if level == '3' else 'th'} level"
                    )
                    if hasattr(spell_group, "slots") and spell_group.slots:
                        level_name += f" ({spell_group.slots} slots)"

                    if hasattr(spell_group, "spells") and spell_group.spells:
                        spells_text = ", ".join(
                            str(spell) for spell in spell_group.spells
                        )
                        spell_parts.append(f"{level_name}: {spells_text}")

                if spell_parts:
                    # Join spell lists with double newline for paragraph breaks
                    parts.append("\n\n".join(spell_parts))

            # Add footer entries
            if hasattr(entry, "footerEntries") and entry.footerEntries:
                footer_parts = []
                for footer in entry.footerEntries:
                    footer_parts.append(self._extract_text_from_entry(footer))
                if footer_parts:
                    parts.append(" ".join(footer_parts))

            # Join major sections with paragraph breaks
            return "\n\n".join(parts)

        # Handle Pydantic models
        if hasattr(entry, "model_dump"):
            # Check for special attributes first
            if (
                hasattr(entry, "items")
                and entry.items
                and isinstance(entry.items, list)
            ):
                # Handle list items from Pydantic models
                parts = []
                for item in entry.items:
                    text = self._extract_text_from_entry(item)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)
            return self._extract_text_from_entry(entry.model_dump())

        # Handle list entries
        if isinstance(entry, list):
            parts = []
            for item in entry:
                text = self._extract_text_from_entry(item)
                if text:  # Only add non-empty text
                    parts.append(text)
            return " ".join(parts)

        # Handle None and empty cases
        if entry is None:
            return ""

        # Fallback to string representation
        return str(entry)

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters in text.

        Args:
            text: Text to escape

        Returns:
            LaTeX-escaped text
        """
        if not text:
            return text

        # Basic LaTeX escaping - this should be enhanced based on existing patterns
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "^": r"\textasciicircum{}",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "\\": r"\textbackslash{}",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text
