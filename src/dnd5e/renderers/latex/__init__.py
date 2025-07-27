"""LaTeX-specific renderers."""

# New EntryRenderer system
# Legacy renderers (deprecated - use EntryRenderers instead)
from .content import LaTeXCreatureRenderer, LaTeXItemRenderer, LaTeXSpellRenderer
from .document import LaTeXDocumentRenderer
from .entry_renderers import EntryRendererRegistry
from .template_engine import LaTeXTemplateEngine

__all__ = [
    "LaTeXDocumentRenderer",
    "LaTeXTemplateEngine",
    "EntryRendererRegistry",
    # Legacy (deprecated)
    "LaTeXSpellRenderer",
    "LaTeXCreatureRenderer",
    "LaTeXItemRenderer",
]
