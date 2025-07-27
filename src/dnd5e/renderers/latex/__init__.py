"""LaTeX-specific renderers."""

# Legacy imports for backward compatibility (deprecated)
from .content import (
    LaTeXAdventureRenderer,
    LaTeXBackgroundRenderer,
    LaTeXBookRenderer,
    LaTeXClassRenderer,
    LaTeXContentRenderer,
    LaTeXCreatureRenderer,
    LaTeXFeatRenderer,
    LaTeXItemRenderer,
    LaTeXRaceRenderer,
    LaTeXSpellRenderer,
)
from .document import LaTeXDocumentRenderer
from .entry_renderers import EntryRendererRegistry
from .template_engine import LaTeXTemplateEngine

__all__ = [
    "LaTeXDocumentRenderer",
    "LaTeXTemplateEngine",
    "EntryRendererRegistry",
    # Legacy (deprecated) - use EntryRendererRegistry instead
    "LaTeXContentRenderer",
    "LaTeXSpellRenderer",
    "LaTeXCreatureRenderer",
    "LaTeXItemRenderer",
    "LaTeXClassRenderer",
    "LaTeXRaceRenderer",
    "LaTeXAdventureRenderer",
    "LaTeXBackgroundRenderer",
    "LaTeXFeatRenderer",
    "LaTeXBookRenderer",
]
