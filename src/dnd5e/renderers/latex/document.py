"""LaTeX document renderer implementation."""

from pathlib import Path
from typing import Any

from ...core.models.content import BaseContent, ContentType
from ...core.models.document_metadata import DocumentMetadata, DocumentType
from ..base import DocumentRenderer, RenderContext, RenderingError
from .compilation_config import CompilationConfig, CompilationResult, LaTeXEngine
from .compiler import LaTeXCompiler
from .content import LaTeXContentRendererRegistry
from .content_organizer import ContentOrganizer
from .document_structure import DocumentStructureBuilder
from .template_engine import LaTeXTemplateEngine


class LaTeXDocumentRenderer(DocumentRenderer):
    """LaTeX document renderer that creates complete D&D-style documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize LaTeX document renderer.

        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.template_engine = LaTeXTemplateEngine(config)
        self.content_registry = LaTeXContentRendererRegistry()
        self.content_organizer = ContentOrganizer()
        self._structure_builder: DocumentStructureBuilder | None = None

        # Initialize LaTeX compiler
        self.compiler = LaTeXCompiler(self._create_compilation_config(config))

    @property
    def output_format(self) -> str:
        """Return the output format."""
        return "latex"

    def render(
        self, content: BaseContent, context: dict[str, Any] | None = None
    ) -> str:
        """Render a single content item as a minimal document.

        Args:
            content: Content to render
            context: Optional rendering context

        Returns:
            Complete LaTeX document
        """
        render_context = RenderContext(**(context or {}))
        return self.render_document([content], render_context)

    def render_document(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> str:
        """Render a complete LaTeX document.

        Args:
            content_items: List of content to include
            context: Rendering context

        Returns:
            Complete LaTeX document
        """
        try:
            # Check if structured document rendering is requested
            if hasattr(context, "metadata") and context.metadata:
                return self.render_structured_document(content_items, context)

            # Fallback to legacy document rendering
            return self.render_legacy_document(content_items, context)

        except Exception as e:
            raise RenderingError(f"Failed to render LaTeX document: {e}") from e

    def render_structured_document(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> str:
        """Render a structured LaTeX document using DocumentStructureBuilder.

        Args:
            content_items: List of content to include
            context: Rendering context with metadata

        Returns:
            Complete structured LaTeX document
        """
        # Get document metadata from context
        metadata = getattr(context, "metadata", None)
        if not metadata:
            # Create default metadata if none provided
            metadata = DocumentMetadata(
                title=context.title or "D&D 5e Content", document_type=DocumentType.BOOK
            )

        # Initialize structure builder
        self._structure_builder = DocumentStructureBuilder(metadata)
        self.content_organizer.document_type = metadata.document_type

        # Organize content and build structure
        self.content_organizer.organize_content(content_items)
        sections, document_context = self._structure_builder.build_document_structure(
            content_items, context
        )

        # Create template context
        template_context = self.template_engine.create_dnd_template_context(
            content_type=metadata.document_type.value
        )

        # Add document structure data
        template_context.update(document_context)
        template_context.update(
            {
                "show_title_page": True,
                "show_toc": metadata.include_toc,
                "show_index": metadata.include_index,
            }
        )

        # Render using appropriate template based on document type
        if metadata.document_type == DocumentType.ARTICLE:
            template_name = "article"
        else:
            template_name = "book"

        # Render the base document with structured sections
        # Remove content_type from template_context to avoid conflict with positional argument
        content_type = template_context.pop(
            "content_type", metadata.document_type.value
        )
        document = self.template_engine.render_dnd_template(
            template_name, content_type, **template_context
        )

        # Render individual content items within sections
        rendered_document = self._render_content_in_sections(
            document, sections, context
        )

        return rendered_document

    def render_legacy_document(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> str:
        """Render a document using the legacy approach.

        Args:
            content_items: List of content to include
            context: Rendering context

        Returns:
            Complete LaTeX document
        """
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

    def _render_content_in_sections(
        self, document: str, sections, context: RenderContext
    ) -> str:
        """Render content items within document sections.

        Args:
            document: Base document template
            sections: Document sections with content items
            context: Rendering context

        Returns:
            Document with content rendered in sections
        """
        from ...core.models.document_metadata import ContentSection

        # This is a placeholder implementation
        # In practice, we would need to replace section placeholders
        # with actual rendered content

        for section in sections:
            if isinstance(section, ContentSection) and section.content_items:
                # Render each content item in the section
                rendered_items = []
                for item in section.content_items:
                    rendered_item = self.render_content_item(item, context)
                    if rendered_item:
                        rendered_items.append(rendered_item)

                # For now, we'll append a comment indicating where content should go
                # Future enhancement would replace specific placeholders in the template
                content_placeholder = f"% Content for {section.title}"
                if content_placeholder in document:
                    document = document.replace(
                        content_placeholder, "\n".join(rendered_items)
                    )

        return document

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

        # Use legacy template engine for compatibility
        from .templates import LaTeXTemplateEngine as LegacyTemplateEngine

        legacy_engine = LegacyTemplateEngine()
        return legacy_engine.render_template("document_header", template_vars)

    def render_document_footer(self, context: RenderContext) -> str:
        """Render LaTeX document footer.

        Args:
            context: Rendering context

        Returns:
            LaTeX document footer
        """
        # Use legacy template engine for compatibility
        from .templates import LaTeXTemplateEngine as LegacyTemplateEngine

        legacy_engine = LegacyTemplateEngine()
        return legacy_engine.render_template("document_footer", {})

    def render_table_of_contents(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> str:
        """Render table of contents.

        Args:
            content_items: Content items to include
            context: Rendering context

        Returns:
            LaTeX table of contents
        """
        if not context.include_toc:
            return ""

        template_vars = {"content_items": content_items, "title": "Table of Contents"}

        # Use legacy template engine for compatibility
        from .templates import LaTeXTemplateEngine as LegacyTemplateEngine

        legacy_engine = LegacyTemplateEngine()
        return legacy_engine.render_template("table_of_contents", template_vars)

    def render_index(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> str:
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
            index_entries.append(
                {
                    "name": item.name,
                    "type": ContentType.from_content(item).value,
                    "source": str(item.source),
                }
            )

        template_vars = {
            "index_entries": sorted(index_entries, key=lambda x: x["name"].lower()),
            "title": "Index",
        }

        # Use legacy template engine for compatibility
        from .templates import LaTeXTemplateEngine as LegacyTemplateEngine

        legacy_engine = LegacyTemplateEngine()
        return legacy_engine.render_template("index", template_vars)

    def render_content_item(self, content: BaseContent, context: RenderContext) -> str:
        """Render an individual content item.

        Args:
            content: Content to render
            context: Rendering context

        Returns:
            Rendered content
        """
        try:
            content_type = ContentType.from_content(content)
        except ValueError:
            # If content type is unknown, use basic rendering as a fallback
            return self._render_basic_content(content, context)

        # Check if content should be included
        if not context.should_include_content_type(content_type.value):
            return ""

        # Get appropriate renderer
        renderer = self.content_registry.get_renderer(content_type)
        if not renderer:
            # Fallback to basic rendering if no specific renderer is found
            return self._render_basic_content(content, context)

        return renderer.render_content(content, context)

    def _render_basic_content(
        self, content: BaseContent, context: RenderContext
    ) -> str:
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
            "\\": r"\textbackslash{}",
            "{": r"\{",
            "}": r"\}",
            "$": r"\$",
            "&": r"\&",
            "%": r"\%",
            "#": r"\#",
            "^": r"\textasciicircum{}",
            "_": r"\_",
            "~": r"\textasciitilde{}",
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result

    def _create_compilation_config(
        self, config: dict[str, Any] | None = None
    ) -> CompilationConfig:
        """Create compilation configuration from renderer config.

        Args:
            config: Renderer configuration

        Returns:
            CompilationConfig instance
        """
        if not config:
            config = {}

        # Extract compilation-specific settings
        compilation_config = CompilationConfig()

        # Map renderer config to compilation config
        if "latex_engine" in config:
            engine_name = config["latex_engine"].lower()
            for engine in LaTeXEngine:
                if engine.value == engine_name:
                    compilation_config.primary_engine = engine
                    break

        if "compilation_timeout" in config:
            compilation_config.timeout_seconds = config["compilation_timeout"]

        if "max_passes" in config:
            compilation_config.max_passes = config["max_passes"]

        if "show_progress" in config:
            compilation_config.show_progress = config["show_progress"]

        if "keep_temp_files" in config:
            compilation_config.keep_intermediate_files = config["keep_temp_files"]

        if "output_dir" in config:
            compilation_config.output_dir = Path(config["output_dir"])

        return compilation_config

    def compile_to_pdf(
        self,
        content: BaseContent,
        output_path: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> CompilationResult:
        """Compile a single content item to PDF.

        Args:
            content: Content to compile
            output_path: Path for output PDF (auto-generated if None)
            context: Optional rendering context

        Returns:
            CompilationResult with compilation details
        """
        render_context = RenderContext(**(context or {}))
        latex_source = self.render_document([content], render_context)

        output_name = output_path.stem if output_path else content.name
        working_dir = output_path.parent if output_path else None

        return self.compiler.compile_document(latex_source, output_name, working_dir)

    def compile_document_to_pdf(
        self,
        content_items: list[BaseContent],
        output_path: Path | None = None,
        context: RenderContext | None = None,
    ) -> CompilationResult:
        """Compile multiple content items to PDF.

        Args:
            content_items: List of content to compile
            output_path: Path for output PDF (auto-generated if None)
            context: Optional rendering context

        Returns:
            CompilationResult with compilation details
        """
        if not context:
            context = RenderContext()

        # Generate LaTeX source
        latex_source = self.render_document(content_items, context)

        # Determine output configuration
        if output_path:
            output_name = output_path.stem
            working_dir = output_path.parent
        else:
            output_name = context.title or "document"
            working_dir = self.compiler.config.output_dir

        # Compile to PDF
        result = self.compiler.compile_document(latex_source, output_name, working_dir)

        # Move output file to requested location if needed
        if output_path and result.success and result.output_file:
            if result.output_file != output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                result.output_file.rename(output_path)
                result.output_file = output_path

        return result

    def validate_latex_environment(self) -> dict[str, bool]:
        """Validate the LaTeX compilation environment.

        Returns:
            Dictionary of validation results
        """
        return self.compiler.validate_environment()

    def get_available_engines(self) -> list:
        """Get available LaTeX engines.

        Returns:
            List of available LaTeX engines
        """
        return self.compiler.get_available_engines()
