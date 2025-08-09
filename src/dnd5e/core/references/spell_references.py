"""Spell reference parsing utilities."""

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from ..logging import get_logger

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer
    from ..models.content import BaseContent

logger = get_logger(__name__)


class SpellReference(BaseModel):
    """Represents a parsed spell reference."""

    name: str = Field(min_length=1, description="Name of the spell")
    source: str | None = Field(None, description="Source abbreviation")
    display_text: str | None = Field(None, description="Custom display text")
    original_tag: str = Field(default="", description="Original tag text")

    @field_validator("original_tag")
    @classmethod
    def validate_tag_format(cls, v: str) -> str:
        """Validate that the original tag follows expected format."""
        if v and not v.startswith("{@spell"):
            raise ValueError(f"Invalid spell tag format: {v}")
        return v

    def __str__(self) -> str:
        """String representation of the spell reference."""
        if self.display_text:
            return self.display_text
        if self.source:
            return f"{self.name} ({self.source})"
        return self.name


class SpellReferenceParser:
    """Parser for extracting spell references from text."""

    # Regex to match {@spell ...} tags
    SPELL_TAG_PATTERN = re.compile(
        r"\{@spell\s+([^}]+)\}", re.IGNORECASE | re.MULTILINE
    )

    @classmethod
    def extract_spell_references(cls, text: str) -> list[SpellReference]:
        """Extract all spell references from text.

        Args:
            text: Text to parse for spell references

        Returns:
            List of parsed spell references
        """
        references = []
        matches = cls.SPELL_TAG_PATTERN.findall(text)

        for match in matches:
            try:
                reference = cls._parse_spell_tag(match)
                if reference:
                    references.append(reference)
            except Exception as e:
                logger.warning(f"Failed to parse spell reference '{match}': {e}")

        return references

    @classmethod
    def _parse_spell_tag(cls, tag_content: str) -> SpellReference | None:
        """Parse individual spell tag content.

        Handles formats:
        - "spell name"
        - "spell name|source"
        - "spell name|source|display text"

        Args:
            tag_content: Content inside {@spell ...} tag

        Returns:
            Parsed spell reference or None if invalid
        """
        if not tag_content.strip():
            return None

        # Split by pipe separator
        parts = [part.strip() for part in tag_content.split("|")]

        if len(parts) == 1:
            # Format: "spell name"
            name = parts[0]
            return SpellReference(name=name, original_tag=f"{{@spell {tag_content}}}")
        elif len(parts) == 2:
            # Format: "spell name|source"
            name, source = parts
            return SpellReference(
                name=name, source=source, original_tag=f"{{@spell {tag_content}}}"
            )
        elif len(parts) == 3:
            # Format: "spell name|source|display text"
            name, source, display_text = parts
            return SpellReference(
                name=name,
                source=source,
                display_text=display_text,
                original_tag=f"{{@spell {tag_content}}}",
            )
        else:
            logger.warning(
                f"Unexpected spell reference format with {len(parts)} parts: {tag_content}"
            )
            # Use first three parts and ignore the rest
            spell_name = parts[0]
            spell_source = parts[1] if len(parts) > 1 else None
            spell_display_text = parts[2] if len(parts) > 2 else None

            return SpellReference(
                name=spell_name,
                source=spell_source,
                display_text=spell_display_text,
                original_tag=f"{{@spell {tag_content}}}",
            )


class SpellReferenceResolver:
    """Resolves spell references to actual spell objects."""

    def __init__(self, omnidexer: "Omnidexer"):
        self.omnidexer = omnidexer

    def resolve_spell_references(
        self, references: list[SpellReference]
    ) -> list["BaseContent"]:
        """Resolve spell references to actual spell objects.

        Args:
            references: List of spell references to resolve

        Returns:
            List of resolved spell objects (may be empty if not found)
        """
        from ..models.content import ContentType

        resolved_spells = []

        for ref in references:
            try:
                # Try exact match first
                spell = self.omnidexer.find(ContentType.SPELL, ref.name, ref.source)

                if spell:
                    resolved_spells.append(spell)
                    logger.debug(f"Resolved spell reference: {ref}")
                else:
                    # Try without source if we had one
                    if ref.source:
                        spell = self.omnidexer.find(ContentType.SPELL, ref.name)
                        if spell:
                            resolved_spells.append(spell)
                            logger.debug(f"Resolved spell reference (no source): {ref}")
                            continue

                    # Try fuzzy matching
                    fuzzy_matches = self.omnidexer.search(
                        ref.name, ContentType.SPELL, limit=1
                    )
                    if fuzzy_matches:
                        resolved_spells.append(fuzzy_matches[0])
                        logger.debug(f"Resolved spell reference (fuzzy): {ref}")
                    else:
                        logger.warning(f"Could not resolve spell reference: {ref}")

            except Exception as e:
                logger.error(f"Error resolving spell reference {ref}: {e}")

        return resolved_spells
