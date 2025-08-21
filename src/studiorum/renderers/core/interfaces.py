"""Core interfaces for the composition-based tag handling architecture.

This module defines the fundamental protocols and types for separating
business logic from presentation concerns in tag rendering.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from studiorum.core.text.tag_ast import TagNode

# Import these directly to avoid forward reference issues
from studiorum.core.models.content import ContentType
from studiorum.core.references.content_tracker import ContentTracker


class FormatStyle(str, Enum):
    """Visual formatting styles for content types."""

    BOLD = "bold"
    ITALIC = "italic"
    PLAIN = "plain"
    MONOSPACE = "monospace"
    EMPHASIS = "emphasis"


class TagValidationError(BaseModel):
    """Represents a validation error for a tag."""

    error_type: str = Field(description="Type of validation error")
    message: str = Field(min_length=1, description="Human-readable error message")
    tag_type: str = Field(
        min_length=1, description="Type of tag that failed validation"
    )
    tag_name: str | None = Field(
        default=None, description="Name of the tag that failed"
    )
    source: str | None = Field(default=None, description="Source context for the error")


class ContentReferenceInfo(BaseModel):
    """Information about a content reference for business logic processing."""

    name: str = Field(description="Content name")
    display_text: str = Field(description="Text to display (may differ from name)")
    source: str | None = Field(default=None, description="Source book/document")
    page: str | None = Field(default=None, description="Page number")
    content_type: ContentType | None = Field(
        default=None, description="Type of content"
    )
    format_style: FormatStyle = Field(
        default=FormatStyle.PLAIN, description="Visual formatting style"
    )


class RenderingContext(BaseModel):
    """Context information provided to tag handlers during rendering."""

    model_config = {"arbitrary_types_allowed": True}

    # Core rendering context
    output_format: str = Field(description="Target output format (latex, html, etc)")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")

    # Service dependencies (injected)
    omnidexer: Any = Field(default=None, description="Content indexer for validation")
    content_tracker: Any = Field(
        default=None, description="Tracks content for appendices"
    )
    tag_resolver: Any = Field(
        default=None, description="Tag resolver for processing text content"
    )

    # Additional context data
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )


@runtime_checkable
class TagHandler(Protocol):
    """Protocol defining the core tag handler interface.

    Core handlers contain only business logic - no presentation-specific formatting.
    They extract content information and apply business rules, returning structured
    data that can be enhanced by presentation layers.
    """

    # Compatibility attribute for systems that expect it
    supported_tags: list[str]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler can process the given tag type.

        Args:
            tag_type: The type of tag to check

        Returns:
            True if this handler can process the tag type
        """
        ...

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content information from a tag node.

        This method contains the core business logic for processing tag content,
        including display text extraction, page reference handling, and formatting rules.

        Args:
            node: The parsed tag node
            context: Rendering context with services and metadata

        Returns:
            Structured information about the content reference
        """
        ...

    def should_include_page_reference(self, page: str | None) -> bool:
        """Determine if a page reference should be included in output.

        Business rule: Don't show page "1" in references.

        Args:
            page: Page number string or None

        Returns:
            True if page reference should be included
        """
        ...

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Validate that a content reference exists and is accessible.

        Args:
            node: The tag node to validate
            context: Rendering context with omnidexer for validation

        Returns:
            List of validation errors (empty if valid)
        """
        ...

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Register content with tracker for appendix generation.

        Args:
            node: The tag node to track
            context: Rendering context with content tracker
        """
        ...


@runtime_checkable
class TagHandlerEnhancer(Protocol):
    """Protocol for enhancement layers that add presentation-specific formatting.

    Enhancers take structured content information and apply format-specific
    enhancements like LaTeX commands, HTML tags, hyperlinks, etc.
    """

    def enhance_content_reference(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply presentation enhancements to content reference information.

        Args:
            content_info: Structured content information from core handler
            context: Rendering context for format-specific decisions

        Returns:
            Enhanced string with presentation-specific formatting
        """
        ...

    def get_enhancement_priority(self) -> int:
        """Get the priority order for this enhancer in the pipeline.

        Lower numbers run first. Typical priorities:
        - 100: Base formatting (bold, italic)
        - 200: Cross-references and hyperlinks
        - 300: Content tracking
        - 400: Validation and error handling

        Returns:
            Priority number for pipeline ordering
        """
        ...


class EnhancementPipeline:
    """Manages a pipeline of enhancers for structured content processing."""

    def __init__(self, enhancers: list[TagHandlerEnhancer]) -> None:
        """Initialize the enhancement pipeline.

        Args:
            enhancers: List of enhancers to apply in sequence
        """
        # Sort enhancers by priority
        self.enhancers = sorted(enhancers, key=lambda e: e.get_enhancement_priority())

    def apply_enhancements(
        self, content_info: ContentReferenceInfo, context: RenderingContext
    ) -> str:
        """Apply all enhancements in priority order.

        Args:
            content_info: Structured content information
            context: Rendering context

        Returns:
            Fully enhanced output string
        """
        # Start with the base content and update it progressively
        current_info = content_info

        # Apply each enhancer in sequence, building upon previous results
        for enhancer in self.enhancers:
            try:
                enhanced = enhancer.enhance_content_reference(current_info, context)
                if enhanced:  # Only update if enhancer produced output
                    # Create new content info with updated display text for next enhancer
                    current_info = ContentReferenceInfo(
                        name=current_info.name,
                        display_text=enhanced,  # Use enhanced text for next enhancer
                        source=current_info.source,
                        page=current_info.page,
                        content_type=current_info.content_type,
                        format_style=current_info.format_style,
                    )
            except Exception as e:
                # Log enhancement errors but don't fail the whole pipeline
                from studiorum.core.logging import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Enhancement failed in {type(enhancer).__name__}: {e}")
                continue

        return current_info.display_text


class EnhancementConfiguration(BaseModel):
    """Configuration for enhancement pipeline behavior."""

    model_config = {"arbitrary_types_allowed": True}

    # Format-specific settings
    output_format: str = Field(description="Target output format")
    enable_hyperlinks: bool = Field(
        default=True, description="Enable hyperlink generation"
    )
    enable_content_tracking: bool = Field(
        default=True, description="Enable content tracking"
    )
    enable_latex_formatting: bool = Field(
        default=True, description="Enable LaTeX text formatting"
    )

    # Format style mappings
    format_style_mapping: dict[str, FormatStyle] = Field(
        default_factory=lambda: {
            "creature": FormatStyle.BOLD,
            "class": FormatStyle.PLAIN,
            "feat": FormatStyle.PLAIN,
            "spell": FormatStyle.ITALIC,
            "item": FormatStyle.ITALIC,
            "condition": FormatStyle.PLAIN,
            "variantrule": FormatStyle.PLAIN,
            "race": FormatStyle.PLAIN,
            "background": FormatStyle.PLAIN,
            "adventure": FormatStyle.ITALIC,
            "book": FormatStyle.ITALIC,
        },
        description="Mapping of content types to formatting styles",
    )

    # Hyperlink manager and content tracker (injected)
    hyperlink_manager: Any = Field(
        default=None, description="Hyperlink manager service"
    )
    content_tracker: Any = Field(default=None, description="Content tracker service")


class UnifiedTagRenderer:
    """Unified renderer combining core handlers with enhancement pipeline.

    This is the main integration point that orchestrates the separation of
    concerns between business logic and presentation formatting.
    """

    def __init__(
        self,
        core_handlers: list[TagHandler],
        enhancement_pipeline: EnhancementPipeline,
        config: EnhancementConfiguration | None = None,
    ) -> None:
        """Initialize the unified renderer.

        Args:
            core_handlers: List of core business logic handlers
            enhancement_pipeline: Pipeline for presentation enhancements
            config: Enhancement configuration options
        """
        self.core_handlers = core_handlers
        self.enhancement_pipeline = enhancement_pipeline
        self.config = config or EnhancementConfiguration(output_format="latex")

    def render_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Render a tag using the unified architecture.

        Process:
        1. Find appropriate core handler for tag type
        2. Extract structured content information (business logic)
        3. Apply enhancement pipeline (presentation logic)
        4. Handle validation and content tracking

        Args:
            node: Parsed tag node
            context: Rendering context

        Returns:
            Fully rendered tag output
        """
        # Find core handler for this tag type
        tag_type = getattr(
            node, "tag_type", str(type(node).__name__).replace("TagNode", "").lower()
        )

        core_handler = None
        for handler in self.core_handlers:
            if handler.handles_tag_type(tag_type):
                core_handler = handler
                break

        if not core_handler:
            # Fallback for unhandled tag types
            return self._render_unknown_tag(node, context)

        try:
            # Check if this is a formatting handler that returns direct results
            if hasattr(core_handler, "process_tag"):
                # For formatting handlers, get the result directly
                result = core_handler.process_tag(node, context)

                # If it returns a FormattingNode or SpecialTag, render it with LaTeX renderer
                from studiorum.core.text.tag_types import FormattingNode, SpecialTag

                if isinstance(result, FormattingNode | SpecialTag):
                    from studiorum.renderers.latex.tag_renderer import LaTeXTagRenderer

                    latex_renderer = LaTeXTagRenderer()
                    return latex_renderer.render(result)
                elif isinstance(result, str):
                    # Direct string result - return as-is
                    return result

            # Step 1: Extract core content information (business logic)
            content_info = core_handler.extract_content_info(node, context)

            # Step 2: Validate content if validation is enabled
            validation_errors = core_handler.validate_content_reference(node, context)
            if validation_errors and context.debug_mode:
                # In debug mode, log validation errors
                from studiorum.core.logging import get_logger

                logger = get_logger(__name__)
                for error in validation_errors:
                    logger.warning(f"Tag validation: {error.message}")

            # Step 3: Track content for appendices
            core_handler.track_content_for_appendix(node, context)

            # Step 4: Apply enhancement pipeline (presentation logic)
            # Create enhanced context with configuration
            enhanced_context = self._create_enhanced_context(context)
            return self.enhancement_pipeline.apply_enhancements(
                content_info, enhanced_context
            )

        except Exception as e:
            # Error handling - return safe fallback
            from studiorum.core.logging import get_logger

            logger = get_logger(__name__)
            logger.error(f"Error rendering tag {tag_type}: {e}")
            return self._render_error_fallback(node, e)

    def _create_enhanced_context(
        self, base_context: RenderingContext
    ) -> RenderingContext:
        """Create enhanced context with configuration data."""
        enhanced_metadata = base_context.metadata.copy()
        enhanced_metadata.update(
            {
                "enhancement_config": self.config,
                "hyperlink_manager": self.config.hyperlink_manager,
                # Prioritize content tracker from base context over config
                "content_tracker": base_context.content_tracker
                or self.config.content_tracker,
            }
        )

        return RenderingContext(
            output_format=base_context.output_format,
            debug_mode=base_context.debug_mode,
            omnidexer=base_context.omnidexer,
            content_tracker=base_context.content_tracker,
            metadata=enhanced_metadata,
        )

    def _render_unknown_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Fallback rendering for unknown tag types."""
        # For unknown tags, try to extract meaningful content instead of showing TagNode(...)
        if hasattr(node, "name") and node.name:
            # Use the name attribute if available (most common case)
            # Escape LaTeX special characters since this content will be included in LaTeX output
            name = str(node.name)
            if context.output_format.lower() == "latex":
                from studiorum.core.latex_utils import escape_latex_text

                name = escape_latex_text(name)
            return name
        elif hasattr(node, "tag_type") and node.tag_type:
            # For tags without names, show the tag type in a readable format
            tag_type = node.tag_type.replace("_", " ").title()
            return f"[{tag_type}]"
        else:
            # Last resort fallback
            return "[Unknown Tag]"

    def _render_error_fallback(self, node: TagNode, error: Exception) -> str:
        """Safe fallback when rendering fails."""
        # Return something safe that won't break document compilation
        fallback_text = getattr(node, "name", "[ERROR]")
        return f"[{fallback_text}]"
