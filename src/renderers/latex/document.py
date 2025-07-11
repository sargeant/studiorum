"""LaTeX document renderer implementation."""

from typing import List, Dict, Any
from pathlib import Path

from src.core.models.content import BaseContent, ContentType
from src.renderers.base import DocumentRenderer, RenderContext, RenderingError
from .templates import LaTeXTemplateEngine
from .content import LaTeXContentRendererRegistry


class LaTeXDocumentRenderer(DocumentRenderer):
    """LaTeX document renderer that creates complete D&D-style documents."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize LaTeX document renderer.
        
        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.template_engine = LaTeXTemplateEngine(config)
        self.content_registry = LaTeXContentRendererRegistry()
        
    @property
    def output_format(self) -> str:
        """Return the output format."""
        return "latex"
    
    def render(self, content: BaseContent, context: Dict[str, Any] = None) -> str:
        """Render a single content item as a minimal document.
        
        Args:
            content: Content to render
            context: Optional rendering context
            
        Returns:
            Complete LaTeX document
        """
        render_context = RenderContext(**(context or {}))
        return self.render_document([content], render_context)
    
    def render_document(self, content_items: List[BaseContent], 
                       context: RenderContext) -> str:
        """Render a complete LaTeX document.
        
        Args:
            content_items: List of content to include
            context: Rendering context
            
        Returns:
            Complete LaTeX document
        """
        try:
            # Build document sections
            sections = []
            
            # Document header
            sections.append(self.render_document_header(context))
            
            # Table of contents (if enabled)
            if context.include_toc and len(content_items) > 1:
                sections.append(self.render_table_of_contents(content_items, context))
            
            # Main content
            for item in content_items:
                sections.append(self.render_content_item(item, context))
            
            # Index (if enabled)
            if context.include_index:
                sections.append(self.render_index(content_items, context))
            
            # Document footer
            sections.append(self.render_document_footer(context))
            
            return "\n\n".join(filter(None, sections))
            
        except Exception as e:
            raise RenderingError(f"Failed to render LaTeX document: {e}") from e
    
    def render_document_header(self, context: RenderContext) -> str:
        """Render LaTeX document preamble and begin document.
        
        Args:
            context: Rendering context
            
        Returns:
            LaTeX document header
        """
        template_vars = {
            "title": context.title or "D&D 5e Content",
            "subtitle": context.subtitle or "",
            "author": context.author or "",
            "date": context.date or r"\today",
            "page_size": context.page_size,
            "font_size": context.font_size,
            "include_images": context.include_images,
            "fonts_dir": str(context.fonts_dir) if context.fonts_dir else None,
        }
        
        return self.template_engine.render_template("document_header", template_vars)
    
    def render_document_footer(self, context: RenderContext) -> str:
        """Render LaTeX document footer.
        
        Args:
            context: Rendering context
            
        Returns:
            LaTeX document footer
        """
        return self.template_engine.render_template("document_footer", {})
    
    def render_table_of_contents(self, content_items: List[BaseContent],
                                context: RenderContext) -> str:
        """Render table of contents.
        
        Args:
            content_items: Content items to include
            context: Rendering context
            
        Returns:
            LaTeX table of contents
        """
        if not context.include_toc:
            return ""
        
        template_vars = {
            "content_items": content_items,
            "title": "Table of Contents"
        }
        
        return self.template_engine.render_template("table_of_contents", template_vars)
    
    def render_index(self, content_items: List[BaseContent],
                    context: RenderContext) -> str:
        """Render document index.
        
        Args:
            content_items: Content items to index
            context: Rendering context
            
        Returns:
            LaTeX index
        """
        if not context.include_index:
            return ""
        
        # Build index entries
        index_entries = []
        for item in content_items:
            index_entries.append({
                "name": item.name,
                "type": ContentType.from_content(item).value,
                "source": str(item.source)
            })
        
        template_vars = {
            "index_entries": sorted(index_entries, key=lambda x: x["name"].lower()),
            "title": "Index"
        }
        
        return self.template_engine.render_template("index", template_vars)
    
    def render_content_item(self, content: BaseContent, context: RenderContext) -> str:
        """Render an individual content item.
        
        Args:
            content: Content to render
            context: Rendering context
            
        Returns:
            Rendered content
        """
        content_type = ContentType.from_content(content)
        
        # Check if content should be included
        if not context.should_include_content_type(content_type.value):
            return ""
        
        # Get appropriate renderer
        renderer = self.content_registry.get_renderer(content_type)
        if not renderer:
            # Fallback to basic rendering
            return self._render_basic_content(content, context)
        
        return renderer.render_content(content, context)
    
    def _render_basic_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render content using basic fallback formatting.
        
        Args:
            content: Content to render
            context: Rendering context
            
        Returns:
            Basic rendered content
        """
        escaped_name = self._escape_latex(content.name)
        source_text = self._escape_latex(str(content.source))
        
        return f"""
\\subsection{{{escaped_name}}}
\\textit{{Source: {source_text}}}

This content type is not yet fully supported by the rendering system.
"""
    
    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""
        
        replacements = {
            '\\': r'\textbackslash{}',
            '{': r'\{',
            '}': r'\}',
            '$': r'\$',
            '&': r'\&',
            '%': r'\%',
            '#': r'\#',
            '^': r'\textasciicircum{}',
            '_': r'\_',
            '~': r'\textasciitilde{}'
        }
        
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
        
        return result