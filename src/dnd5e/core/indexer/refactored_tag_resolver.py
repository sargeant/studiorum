"""Refactored tag resolver that separates semantic resolution from formatting."""

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, Union

from ..loaders.omnidexer import Omnidexer
from ..logging import get_logger
from .semantic_resolver import SemanticTagResolver
from .tag_resolver import TagMatch
from .tag_types import TagContext, TagResolutionResult

if TYPE_CHECKING:
    from .tag_resolver import TagResolver

logger = get_logger(__name__)


class RefactoredTagResolver:
    """Tag resolver that separates semantic resolution from presentation formatting.

    This class coordinates between:
    1. SemanticTagResolver - handles content lookup and creates structured objects
    2. TagRenderer - converts structured objects to formatted output

    This maintains the same interface as the original TagResolver for backward
    compatibility while enabling support for multiple output formats.
    """

    # Pattern matches: {@creature Strahd von Zarovich|CoS|the vampire lord}
    TAG_PATTERN = re.compile(r"{@(\w+)\s+([^}]+)}")

    def __init__(self, omnidexer: Omnidexer, renderer: "TagRenderer | None" = None):
        """Initialize with omnidexer and optional renderer.

        Args:
            omnidexer: Content indexer for resolving references
            renderer: Tag renderer for formatting output. If None, a default
                     LaTeX renderer will be created lazily.
        """
        self.omnidexer = omnidexer
        self._renderer = renderer

        # Create semantic resolver with context
        context = TagContext(omnidexer=omnidexer)
        self.semantic_resolver = SemanticTagResolver(context)

    @property
    def renderer(self) -> "TagRenderer":
        """Get the tag renderer, creating default LaTeX renderer if needed."""
        if self._renderer is None:
            from ...renderers.latex.tag_renderer import LaTeXTagRenderer

            self._renderer = LaTeXTagRenderer()
        return self._renderer

    def set_renderer(self, renderer: "TagRenderer") -> None:
        """Set a custom tag renderer."""
        self._renderer = renderer

    def register_tag_handler(
        self, tag_type: str, handler: Callable[[TagMatch], TagResolutionResult]
    ) -> None:
        """Register a custom semantic tag handler.

        Note: This registers handlers for semantic resolution only.
        Formatting is handled by the renderer.
        """
        self.semantic_resolver.register_tag_handler(tag_type, handler)
        logger.info(f"Registered handler for tag type: {tag_type}")

    def process_text(self, text: str) -> str:
        """Process text and resolve all tags to formatted output.

        This is the main interface method that maintains compatibility
        with the original TagResolver.
        """
        if not text or "{@" not in text:
            return text

        def replace_tag(match: re.Match[str]) -> str:
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

    def resolve_to_object(self, text: str) -> list[TagResolutionResult]:
        """Resolve tags to structured objects without formatting.

        This is a new method that exposes the intermediate representation,
        useful for unit testing and alternative renderers.

        Returns:
            List of resolved objects and plain text segments
        """
        if not text or "{@" not in text:
            return [text]

        results: list[TagResolutionResult] = []
        last_end = 0

        for match in self.TAG_PATTERN.finditer(text):
            # Add text before this match
            if match.start() > last_end:
                results.append(text[last_end : match.start()])

            # Resolve the tag
            try:
                tag_match = TagMatch.parse(
                    match.group(1),  # tag_type
                    match.group(2),  # content
                    match.group(0),  # full_match
                )
                resolved = self.semantic_resolver.resolve_tag(tag_match)
                results.append(resolved)
            except Exception as e:
                logger.warning(f"Failed to resolve tag {match.group(0)}: {e}")
                results.append(match.group(0))  # Return original if resolution fails

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            results.append(text[last_end:])

        return results

    def _resolve_tag(self, tag_match: TagMatch) -> str:
        """Resolve a parsed tag through semantic resolution and formatting.

        This is the internal method that coordinates the two-phase process:
        1. Semantic resolution to structured object
        2. Rendering to formatted string
        """
        # Phase 1: Semantic resolution
        resolved = self.semantic_resolver.resolve_tag(tag_match)

        # Phase 2: Rendering
        return self.renderer.render(resolved)


# For backward compatibility, create a factory function
def create_tag_resolver(
    omnidexer: Omnidexer,
    use_refactored: bool = False,
    renderer: "TagRenderer | None" = None,
) -> "TagResolver | RefactoredTagResolver":
    """Factory function to create tag resolver.

    Args:
        omnidexer: Content indexer
        use_refactored: If True, use the new refactored resolver
        renderer: Optional custom renderer (only used with refactored resolver)

    Returns:
        Appropriate tag resolver instance
    """
    if use_refactored:
        return RefactoredTagResolver(omnidexer, renderer)
    else:
        from .tag_resolver import TagResolver

        return TagResolver(omnidexer)


# Type hint for renderer interface
class TagRenderer(Protocol):
    """Protocol defining the interface for tag renderers."""

    def render(self, result: TagResolutionResult) -> str:
        """Render a tag resolution result to formatted string."""
        ...
