"""Concrete implementations of reference parsers and resolvers.

This module provides specific implementations of the unified reference system
for the most common reference types in the 5e2pdf codebase.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from dnd5e.core.base_context import BaseContext
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.unified_references import (
    Reference,
    ReferenceFormat,
    ReferenceParser,
    ReferenceResolver,
    ReferenceType,
)

if TYPE_CHECKING:
    from dnd5e.core.loaders.omnidexer import Omnidexer

logger = logging.getLogger(__name__)


class SpellReferenceParser(ReferenceParser[BaseContent]):
    """Parser for {@spell ...} tags compatible with existing SpellReference system."""

    # Regex patterns for different spell reference formats
    SPELL_PATTERN = re.compile(r"\{@spell\s+([^}]+)\}", re.IGNORECASE)

    @property
    def supported_content_type(self) -> type[BaseContent]:
        return BaseContent

    def can_parse(self, text: str) -> bool:
        """Check if text contains {@spell ...} tags."""
        return bool(self.SPELL_PATTERN.search(text))

    def extract_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference[BaseContent]]:
        """Extract spell references from {@spell ...} tags."""
        references = []

        for match in self.SPELL_PATTERN.finditer(text):
            original_text = match.group(0)
            content = match.group(1).strip()

            # Parse the spell reference content
            # Format: "spell name" or "spell name|source" or "spell name|source|display text"
            parts = [part.strip() for part in content.split("|")]

            name = parts[0] if parts else ""
            source = parts[1] if len(parts) > 1 else None
            display_text = parts[2] if len(parts) > 2 else None

            if name:
                ref = Reference(
                    source=original_text,
                    target=name,
                    content_type=BaseContent,
                    source_book=source,
                    display_text=display_text,
                    reference_type=ReferenceType.CONTENT,
                    original_text=original_text,
                )
                references.append(ref)

        return references


class ContentReferenceResolver(ReferenceResolver[BaseContent]):
    """Resolver for content references using Omnidexer."""

    def __init__(self, omnidexer: Omnidexer | None = None):
        self.omnidexer = omnidexer

    @property
    def supported_content_type(self) -> type[BaseContent]:
        return BaseContent

    def resolve(
        self, ref: Reference[BaseContent], context: BaseContext | None = None
    ) -> BaseContent | None:
        """Resolve reference to actual content using Omnidexer."""
        if not self.omnidexer:
            # Try to get omnidexer from context
            if context and hasattr(context, "omnidexer") and context.omnidexer:
                self.omnidexer = context.omnidexer
            else:
                logger.warning(
                    f"No omnidexer available to resolve reference: {ref.target}"
                )
                return None

        try:
            # Try exact match first
            result = self.omnidexer.find(ContentType.SPELL, ref.target, ref.source_book)

            if result is None and ref.source_book is None:
                # Try without source constraint if no exact match
                result = self.omnidexer.find(ContentType.SPELL, ref.target, None)

            if result is None:
                logger.debug(
                    f"Could not resolve spell reference: {ref.target} from {ref.source_book}"
                )

            return result

        except Exception as e:
            logger.error(f"Error resolving reference {ref.target}: {e}")
            return None

    def format_reference(
        self,
        ref: Reference[BaseContent],
        format_type: ReferenceFormat,
        resolved_content: BaseContent | None = None,
        context: BaseContext | None = None,
    ) -> str:
        """Format reference for output."""
        if format_type == ReferenceFormat.LATEX:
            return self._format_latex(ref, resolved_content)
        elif format_type == ReferenceFormat.HTML:
            return self._format_html(ref, resolved_content)
        elif format_type == ReferenceFormat.MARKDOWN:
            return self._format_markdown(ref, resolved_content)
        else:
            return self._format_plain_text(ref, resolved_content)

    def _format_latex(
        self, ref: Reference[BaseContent], content: BaseContent | None
    ) -> str:
        """Format reference as LaTeX."""
        if content:
            # Use actual spell name and create a reference
            spell_name = getattr(content, "name", ref.target)
            if ref.latex_label:
                return f"\\hyperref[{ref.latex_label}]{{{spell_name}}}"
            else:
                return f"\\textit{{{spell_name}}}"
        else:
            # Fallback to display text or target
            display = ref.display_text or ref.target
            return f"\\textit{{{display}}}"

    def _format_html(
        self, ref: Reference[BaseContent], content: BaseContent | None
    ) -> str:
        """Format reference as HTML."""
        if content:
            spell_name = getattr(content, "name", ref.target)
            return f'<span class="spell-reference">{spell_name}</span>'
        else:
            display = ref.display_text or ref.target
            return f'<span class="spell-reference unresolved">{display}</span>'

    def _format_markdown(
        self, ref: Reference[BaseContent], content: BaseContent | None
    ) -> str:
        """Format reference as Markdown."""
        if content:
            spell_name = getattr(content, "name", ref.target)
            return f"*{spell_name}*"
        else:
            display = ref.display_text or ref.target
            return f"*{display}*"

    def _format_plain_text(
        self, ref: Reference[BaseContent], content: BaseContent | None
    ) -> str:
        """Format reference as plain text."""
        if content:
            return getattr(content, "name", ref.target)
        else:
            return ref.display_text or ref.target


class CrossReferenceParser(ReferenceParser[Any]):
    """Parser for cross-references within documents."""

    # Pattern for cross-reference markup (e.g., {@crossref creature|goblin})
    CROSSREF_PATTERN = re.compile(r"\{@(?:crossref|xref)\s+([^}]+)\}", re.IGNORECASE)

    @property
    def supported_content_type(self) -> type[Any]:
        return Any  # Cross-references can point to any content type

    def can_parse(self, text: str) -> bool:
        """Check if text contains cross-reference tags."""
        return bool(self.CROSSREF_PATTERN.search(text))

    def extract_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference[Any]]:
        """Extract cross-references from markup."""
        references = []

        for match in self.CROSSREF_PATTERN.finditer(text):
            original_text = match.group(0)
            content = match.group(1).strip()

            # Parse: "content_type|name" or "content_type|name|source"
            parts = [part.strip() for part in content.split("|")]

            if len(parts) >= 2:
                content_type_str = parts[0]
                name = parts[1]
                source = parts[2] if len(parts) > 2 else None

                ref = Reference(
                    source=original_text,
                    target=name,
                    content_type=Any,  # Will be resolved based on content_type_str
                    source_book=source,
                    reference_type=ReferenceType.CROSS_REF,
                    original_text=original_text,
                    context=content_type_str,  # Store content type in context
                )
                references.append(ref)

        return references


class CrossReferenceResolver(ReferenceResolver[Any]):
    """Resolver for cross-references using cross-reference manager."""

    def __init__(self, cross_ref_manager: Any = None):
        self.cross_ref_manager = cross_ref_manager

    @property
    def supported_content_type(self) -> type[Any]:
        return Any

    def resolve(
        self, ref: Reference[Any], context: BaseContext | None = None
    ) -> Any | None:
        """Resolve cross-reference using cross-reference manager."""
        if not self.cross_ref_manager:
            # Try to get from context
            if (
                context
                and hasattr(context, "cross_ref_manager")
                and context.cross_ref_manager
            ):
                self.cross_ref_manager = context.cross_ref_manager
            else:
                logger.warning(
                    f"No cross-reference manager available for: {ref.target}"
                )
                return None

        try:
            # Use the content type from context to determine lookup
            content_type_str = ref.context
            if content_type_str and hasattr(self.cross_ref_manager, "find_reference"):
                return self.cross_ref_manager.find_reference(
                    content_type_str, ref.target, ref.source_book
                )
            else:
                return None

        except Exception as e:
            logger.error(f"Error resolving cross-reference {ref.target}: {e}")
            return None

    def format_reference(
        self,
        ref: Reference[Any],
        format_type: ReferenceFormat,
        resolved_content: Any | None = None,
        context: BaseContext | None = None,
    ) -> str:
        """Format cross-reference for output."""
        if format_type == ReferenceFormat.LATEX:
            return self._format_latex_crossref(ref, resolved_content)
        else:
            return ref.display_text or ref.target

    def _format_latex_crossref(self, ref: Reference[Any], content: Any | None) -> str:
        """Format cross-reference as LaTeX."""
        if ref.latex_label:
            return f"\\hyperref[{ref.latex_label}]{{{ref.display_text or ref.target}}}"
        elif content and hasattr(content, "latex_label"):
            return (
                f"\\hyperref[{content.latex_label}]{{{ref.display_text or ref.target}}}"
            )
        else:
            return ref.display_text or ref.target


def create_default_reference_manager(omnidexer: Omnidexer | None = None) -> Any:
    """Create a reference manager with default parsers and resolvers.

    Args:
        omnidexer: Optional omnidexer for content resolution

    Returns:
        Configured ReferenceManager with common parsers and resolvers
    """
    from dnd5e.core.unified_references import ReferenceManager

    manager = ReferenceManager()

    # Register spell reference parser and resolver
    spell_parser = SpellReferenceParser()
    spell_resolver = ContentReferenceResolver(omnidexer)

    manager.register_parser(spell_parser)
    manager.register_resolver(spell_resolver)

    # Register cross-reference parser and resolver
    crossref_parser = CrossReferenceParser()
    crossref_resolver = CrossReferenceResolver()

    manager.register_parser(crossref_parser)
    manager.register_resolver(crossref_resolver)

    return manager
