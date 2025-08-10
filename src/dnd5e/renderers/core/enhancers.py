"""Enhancement layers for tag rendering pipeline.

This module provides specialized enhancers that apply presentation-specific
formatting to structured content information. Each enhancer focuses on a
single responsibility within the rendering pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dnd5e.core.latex_utils import escape_latex_text
from dnd5e.core.logging import get_logger

from .interfaces import (
    ContentReferenceInfo,
    FormatStyle,
    RenderingContext,
    TagHandlerEnhancer,
)

if TYPE_CHECKING:
    from dnd5e.core.references.content_tracker import ContentTracker
    from dnd5e.core.references.hyperlink_manager import HyperlinkManager

logger = get_logger(__name__)


class LaTeXFormatEnhancer:
    """Applies LaTeX formatting based on content type and format style."""

    def __init__(self, priority: int = 100) -> None:
        """Initialize the LaTeX format enhancer.

        Args:
            priority: Pipeline priority (100 = base formatting)
        """
        self.priority = priority

    def get_enhancement_priority(self) -> int:
        """Get pipeline priority for LaTeX formatting."""
        return self.priority

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply LaTeX formatting based on content format style.

        Args:
            content_info: Structured content information
            context: Rendering context with configuration

        Returns:
            LaTeX-formatted text with appropriate commands
        """
        # Check if LaTeX formatting is enabled
        config = context.metadata.get("enhancement_config")
        if not config or not getattr(config, "enable_latex_formatting", True):
            return self._escape_latex(content_info.display_text)

        # Apply format style
        display_text = self._escape_latex(content_info.display_text)
        formatted_text = self._apply_format_style(
            display_text, content_info.format_style
        )

        # Add page reference if present and appropriate for this content type
        if content_info.page and self._should_include_page_reference(
            content_info.content_type, content_info.page
        ):
            formatted_text = self._add_page_reference(
                formatted_text, content_info.page, content_info.content_type
            )

        return formatted_text

    def _apply_format_style(self, text: str, format_style: FormatStyle) -> str:
        """Apply LaTeX formatting based on format style."""
        if format_style == FormatStyle.BOLD:
            return f"\\textbf{{{text}}}"
        elif format_style == FormatStyle.ITALIC:
            return f"\\textit{{{text}}}"
        elif format_style == FormatStyle.MONOSPACE:
            return f"\\texttt{{{text}}}"
        elif format_style == FormatStyle.EMPHASIS:
            return f"\\emph{{{text}}}"
        else:  # PLAIN
            return text

    def _add_page_reference(self, text: str, page: str, content_type: Any) -> str:
        """Add page reference in the appropriate format."""
        # Convert ContentType to string for comparison if needed
        if hasattr(content_type, "value"):
            # Handle ContentType enum
            content_type_str = content_type.value.lower()
        elif hasattr(content_type, "name"):
            # Handle ContentType enum with name attribute
            content_type_str = content_type.name.lower()
        else:
            # Handle string or other types
            content_type_str = str(content_type).lower() if content_type else ""

        if content_type_str in ("adventure", "contenttype.adventure"):
            return f"{text} (p. {page})"
        elif content_type_str in ("book", "contenttype.book"):
            return f"{text}, p. {page}"
        else:
            return f"{text} (p. {page})"

    def _should_include_page_reference(self, content_type: Any, page: str) -> bool:
        """Determine if page references should be included for this content type.

        Based on legacy handler behavior:
        - Adventure handlers include page references (but not page "1")
        - Book handlers include ALL page references (including page "1")
        - Basic content handlers (creature, spell, item, etc.) do not
        """
        # Convert ContentType to string for comparison if needed
        if hasattr(content_type, "value"):
            # Handle ContentType enum
            content_type_str = content_type.value.lower()
        elif hasattr(content_type, "name"):
            # Handle ContentType enum with name attribute
            content_type_str = content_type.name.lower()
        else:
            # Handle string or other types
            content_type_str = str(content_type).lower() if content_type else ""

        # Check content type and apply appropriate page logic
        if content_type_str in ("adventure", "contenttype.adventure"):
            # Adventures: include page references except for page "1"
            return page != "1"
        elif content_type_str in ("book", "contenttype.book"):
            # Books: include ALL page references, even page "1"
            return True
        else:
            # All other content types: no page references
            return False

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters."""
        return escape_latex_text(text)


class HyperlinkEnhancer:
    """Applies hyperlink generation for cross-references."""

    def __init__(self, priority: int = 200) -> None:
        """Initialize the hyperlink enhancer.

        Args:
            priority: Pipeline priority (200 = hyperlinks after formatting)
        """
        self.priority = priority

    def get_enhancement_priority(self) -> int:
        """Get pipeline priority for hyperlink generation."""
        return self.priority

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply hyperlink generation if enabled and appropriate.

        Args:
            content_info: Structured content information
            context: Rendering context with hyperlink manager

        Returns:
            Text with hyperlinks applied or original text if not applicable
        """
        # Get hyperlink manager from context
        hyperlink_manager: HyperlinkManager | None = context.metadata.get(
            "hyperlink_manager"
        )

        # Check if hyperlinks are enabled
        config = context.metadata.get("enhancement_config")
        if not config or not getattr(config, "enable_hyperlinks", True):
            return content_info.display_text

        if not hyperlink_manager:
            logger.debug("No hyperlink manager available")
            return content_info.display_text

        # Check if this content type should have hyperlinks
        content_type_str = self._get_content_type_str(content_info.content_type)
        if not hyperlink_manager.should_create_hyperlink(content_type_str):
            return content_info.display_text

        # Generate cross-reference ID
        ref_id = self._generate_ref_id(content_info)

        try:
            # Create hyperlink with appropriate styling
            hyperlinked_text = hyperlink_manager.create_hyperlink(
                text=content_info.display_text,
                ref_id=ref_id,
                content_type=content_type_str,
            )

            return hyperlinked_text

        except Exception as e:
            logger.warning(f"Failed to create hyperlink for {content_info.name}: {e}")
            return content_info.display_text

    def _get_content_type_str(self, content_type: Any) -> str:
        """Get content type as string, handling different formats."""
        if content_type is None:
            return "content"

        if hasattr(content_type, "value"):
            # Handle ContentType enum
            return str(content_type.value).lower()
        elif hasattr(content_type, "name"):
            # Handle ContentType enum with name attribute
            return str(content_type.name).lower()
        else:
            # Handle string or other types
            return str(content_type).lower()

    def _generate_ref_id(self, content_info: ContentReferenceInfo) -> str:
        """Generate a reference ID for cross-referencing."""
        # Create a sanitized reference ID
        content_type_str = self._get_content_type_str(content_info.content_type)
        name_sanitized = content_info.name.lower().replace(" ", "-").replace("'", "")

        if content_info.source:
            source_sanitized = content_info.source.lower().replace(" ", "-")
            return f"{content_type_str}:{name_sanitized}:{source_sanitized}"
        else:
            return f"{content_type_str}:{name_sanitized}"


class ContentTrackerEnhancer:
    """Tracks content references for appendix generation."""

    def __init__(self, priority: int = 300) -> None:
        """Initialize the content tracker enhancer.

        Args:
            priority: Pipeline priority (300 = content tracking after presentation)
        """
        self.priority = priority

    def get_enhancement_priority(self) -> int:
        """Get pipeline priority for content tracking."""
        return self.priority

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Track content reference for appendix generation.

        Args:
            content_info: Structured content information
            context: Rendering context with content tracker

        Returns:
            Original display text (tracking is a side effect)
        """
        # Get content tracker from context
        content_tracker: ContentTracker | None = context.metadata.get("content_tracker")

        # Check if content tracking is enabled
        config = context.metadata.get("enhancement_config")
        if not config or not getattr(config, "enable_content_tracking", True):
            return content_info.display_text

        if not content_tracker:
            logger.debug("No content tracker available")
            return content_info.display_text

        try:
            # Track the content reference
            content_type_str = self._get_content_type_str(content_info.content_type)
            content_tracker.add_content(
                content_type=content_type_str,
                name=content_info.name,
                source=content_info.source,
                page=content_info.page,
            )

            logger.debug(f"Tracked {content_type_str}: {content_info.name}")

        except Exception as e:
            logger.warning(f"Failed to track content {content_info.name}: {e}")

        # Content tracking is a side effect - return original text
        return content_info.display_text

    def _get_content_type_str(self, content_type: Any) -> str:
        """Get content type as string, handling different formats."""
        if content_type is None:
            return "content"

        if hasattr(content_type, "value"):
            # Handle ContentType enum
            return str(content_type.value).lower()
        elif hasattr(content_type, "name"):
            # Handle ContentType enum with name attribute
            return str(content_type.name).lower()
        else:
            # Handle string or other types
            return str(content_type).lower()


class ValidationEnhancer:
    """Provides validation and error handling for content references."""

    def __init__(self, priority: int = 400) -> None:
        """Initialize the validation enhancer.

        Args:
            priority: Pipeline priority (400 = validation last)
        """
        self.priority = priority

    def get_enhancement_priority(self) -> int:
        """Get pipeline priority for validation."""
        return self.priority

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply validation and error handling.

        Args:
            content_info: Structured content information
            context: Rendering context with omnidexer

        Returns:
            Original text or error marker if validation fails
        """
        # Only perform validation in debug mode
        if not context.debug_mode:
            return content_info.display_text

        # Check if omnidexer is available for validation
        if not context.omnidexer:
            return content_info.display_text

        try:
            # Validate that the content exists
            content_type_str = self._get_content_type_str(content_info.content_type)

            # Simple validation - check if name looks reasonable
            if not content_info.name or not content_info.name.strip():
                logger.warning(f"Empty content name for {content_type_str}")
                return f"[EMPTY:{content_info.display_text}]"

            # Additional validations can be added here

        except Exception as e:
            logger.warning(f"Validation error for {content_info.name}: {e}")

        return content_info.display_text

    def _get_content_type_str(self, content_type: Any) -> str:
        """Get content type as string, handling different formats."""
        if content_type is None:
            return "content"

        if hasattr(content_type, "value"):
            # Handle ContentType enum
            return str(content_type.value).lower()
        elif hasattr(content_type, "name"):
            # Handle ContentType enum with name attribute
            return str(content_type.name).lower()
        else:
            # Handle string or other types
            return str(content_type).lower()


def create_latex_enhancement_pipeline() -> list[TagHandlerEnhancer]:
    """Create a standard LaTeX enhancement pipeline.

    Returns:
        List of enhancers configured for LaTeX output
    """
    return [
        LaTeXFormatEnhancer(priority=100),  # Base formatting first
        HyperlinkEnhancer(priority=200),  # Hyperlinks after formatting
        ContentTrackerEnhancer(priority=300),  # Content tracking
        ValidationEnhancer(priority=400),  # Validation last
    ]


def create_plain_text_enhancement_pipeline() -> list[TagHandlerEnhancer]:
    """Create a minimal enhancement pipeline for plain text output.

    Returns:
        List of enhancers configured for plain text output
    """
    return [
        ContentTrackerEnhancer(priority=300),  # Just track content
        ValidationEnhancer(priority=400),  # And validate
    ]


class CompositeEnhancer:
    """Combines multiple enhancers with conditional application."""

    def __init__(self, enhancers: list[TagHandlerEnhancer]) -> None:
        """Initialize with a list of enhancers.

        Args:
            enhancers: List of enhancers to combine
        """
        self.enhancers = sorted(enhancers, key=lambda e: e.get_enhancement_priority())

    def get_enhancement_priority(self) -> int:
        """Get the lowest priority (runs first) of constituent enhancers."""
        return (
            min(e.get_enhancement_priority() for e in self.enhancers)
            if self.enhancers
            else 999
        )

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply all enhancers in priority order.

        Args:
            content_info: Structured content information
            context: Rendering context

        Returns:
            Text enhanced by all applicable enhancers
        """
        result = content_info.display_text

        # Apply each enhancer in sequence
        for enhancer in self.enhancers:
            try:
                enhanced = enhancer.enhance_content_reference(content_info, context)
                if enhanced:  # Only update if enhancer produced output
                    result = enhanced
                    # Update content_info for next enhancer
                    content_info = ContentReferenceInfo(
                        name=content_info.name,
                        display_text=result,
                        source=content_info.source,
                        page=content_info.page,
                        content_type=content_info.content_type,
                        format_style=content_info.format_style,
                    )
            except Exception as e:
                logger.warning(f"Enhancement failed in {type(enhancer).__name__}: {e}")
                continue

        return result
