"""LaTeX document renderer implementation."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ...core.latex_utils import escape_latex_text
from ...core.models.content import BaseContent, ContentType
from ...core.models.document_metadata import (
    ContentSection,
    DocumentMetadata,
    DocumentType,
)
from ...core.types import LaTeXConfig, RenderContext as RenderContextType
from ..base import DocumentRenderer, RenderContext, RenderingError
from .compilation_config import CompilationConfig, CompilationResult, LaTeXEngine
from .compiler import LaTeXCompiler
from .content_organizer import ContentOrganizer
from .document_structure import DocumentStructureBuilder
from .entry_renderers import EntryRendererRegistry
from .template_engine import LaTeXTemplateEngine


class LaTeXDocumentRenderer(DocumentRenderer):
    """LaTeX document renderer that creates complete D&D-style documents."""

    def __init__(self, config: LaTeXConfig | None = None):
        """Initialize LaTeX document renderer.

        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.template_engine = LaTeXTemplateEngine(config)
        self.entry_registry = EntryRendererRegistry()
        self.content_organizer = ContentOrganizer()
        self._structure_builder: DocumentStructureBuilder | None = None

        # Initialize LaTeX compiler
        self.compiler = LaTeXCompiler(self._create_compilation_config(config))

    @property
    def output_format(self) -> str:
        """Return the output format."""
        return "latex"

    def render(
        self, content: BaseContent, context: RenderContextType | None = None
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
        self, content_items: Sequence[BaseContent], context: RenderContext
    ) -> str:
        """Render a complete LaTeX document.

        Args:
            content_items: List of content to include
            context: Rendering context

        Returns:
            Complete LaTeX document
        """
        try:
            # Always use structured document rendering
            return self.render_structured_document(content_items, context)

        except Exception as e:
            raise RenderingError(f"Failed to render LaTeX document: {e}") from e

    def render_structured_document(
        self, content_items: Sequence[BaseContent], context: RenderContext
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
                title=context.title or "D&D 5e Content",
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.BOOK,
                include_toc=True,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=None,
                use_parts=False,
            )

        # Initialize structure builder
        self._structure_builder = DocumentStructureBuilder(metadata)
        self.content_organizer.document_type = metadata.document_type

        # Organize content and build structure
        content_list = list(content_items)
        self.content_organizer.organize_content(content_list)
        sections, document_context = self._structure_builder.build_document_structure(
            content_list, context
        )

        # Update template engine with LaTeX config from context if available
        if hasattr(context, "latex_config") and context.latex_config:
            self.template_engine.update_latex_config(context.latex_config)

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

    def _render_content_in_sections(
        self, document: str, sections: list[ContentSection], context: RenderContext
    ) -> str:
        """Render content items within document sections.

        Args:
            document: Base document template
            sections: Document sections with content items
            context: Rendering context

        Returns:
            Document with content rendered in sections
        """
        for section in sections:
            if isinstance(section, ContentSection) and section.content_items:
                # Render each content item and replace individual placeholders
                for item in section.content_items:
                    rendered_item = self.render_content_item(item, context)
                    if rendered_item:
                        # Create placeholder pattern that matches section template output
                        if isinstance(item, str):
                            placeholder_pattern = "% Content: String Entry (str)"
                        elif isinstance(item, dict):
                            item_name = item.get("name", "Unknown")
                            # Apply LaTeX escaping to match template output
                            escaped_name = self._escape_latex(item_name)
                            placeholder_pattern = f"% Content: {escaped_name} (dict)"
                        else:
                            # For actual model objects
                            item_name = getattr(item, "name", "Unknown")
                            escaped_name = self._escape_latex(item_name)
                            item_class = item.__class__.__name__
                            placeholder_pattern = (
                                f"% Content: {escaped_name} ({item_class})"
                            )

                        # Replace the specific placeholder with rendered content
                        # Use replace with count=1 to only replace the first occurrence
                        if placeholder_pattern in document:
                            document = document.replace(
                                placeholder_pattern, rendered_item, 1
                            )

                # Also try the generic content placeholder for compatibility
                content_placeholder = f"% Content for {section.title}"
                if content_placeholder in document:
                    rendered_items = []
                    for item in section.content_items:
                        rendered_item = self.render_content_item(item, context)
                        if rendered_item:
                            rendered_items.append(rendered_item)
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

        return self.template_engine.render_template("document_header", template_vars)

    def render_document_footer(self, context: RenderContext) -> str:
        """Render LaTeX document footer.

        Args:
            context: Rendering context

        Returns:
            LaTeX document footer
        """
        return self.template_engine.render_template("document_footer", {})

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

        return self.template_engine.render_template("table_of_contents", template_vars)

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
            # Handle both dict and object formats for item name
            if hasattr(item, "name"):
                item_name = item.name
            elif isinstance(item, dict):
                item_name = item.get("name", "Unnamed Item")
            else:
                item_name = "Unnamed Item"

            # Handle both dict and object formats for item source
            if hasattr(item, "source"):
                item_source = str(item.source)
            elif isinstance(item, dict):
                source_data = item.get("source", {})
                if isinstance(source_data, dict):
                    item_source = source_data.get("abbreviation", "Unknown")
                else:
                    item_source = str(source_data)
            else:
                item_source = "Unknown"

            index_entries.append(
                {
                    "name": item_name,
                    "type": ContentType.from_content(item).value,
                    "source": item_source,
                }
            )

        template_vars = {
            "index_entries": sorted(index_entries, key=lambda x: x["name"].lower()),
            "title": "Index",
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
        try:
            content_type = ContentType.from_content(content)
        except ValueError:
            # If content type is unknown, use basic rendering as a fallback
            return self._render_basic_content(content, context)

        # Check if content should be included
        if not context.should_include_content_type(content_type.value):
            return ""

        # Use EntryRenderer system
        try:
            entry_renderer = self.entry_registry.get_renderer(content_type.value)
            return entry_renderer.render(content, context)
        except ValueError:
            # EntryRenderer not found, use basic fallback rendering
            return self._render_basic_content(content, context)

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
        # Check if this is a raw book entry that should be processed recursively
        if isinstance(content, dict | str) and self._is_book_entry(content, context):
            return self._render_book_entry(content, context)
        # Check if this is a raw adventure entry that should be processed recursively
        if isinstance(content, dict | str) and self._is_adventure_entry(
            content, context
        ):
            return self._render_adventure_entry(content, context)
        # Handle both dict and object formats for content name
        if hasattr(content, "name"):
            content_name = content.name
        elif isinstance(content, dict):
            content_name = content.get("name", "Unnamed Content")
        else:
            content_name = "Unnamed Content"

        # Handle both dict and object formats for content source
        if hasattr(content, "source"):
            content_source = str(content.source)
        elif isinstance(content, dict):
            source_data = content.get("source", {})
            if isinstance(source_data, dict):
                content_source = source_data.get("abbreviation", "Unknown")
            else:
                content_source = str(source_data)
        else:
            content_source = "Unknown"

        escaped_name = self._escape_latex(content_name)
        source_text = self._escape_latex(content_source)

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
        return escape_latex_text(text)

    def _is_book_entry(self, content: Any, context: RenderContext) -> bool:
        """Check if content is a raw book entry that should be processed recursively.

        Args:
            content: Content to check
            context: Rendering context

        Returns:
            True if this appears to be a book entry
        """
        # Check if we're in a book document context
        if not hasattr(context, "metadata") or not context.metadata:
            return False

        if context.metadata.document_type != DocumentType.BOOK:
            return False

        # Check if content looks like a book entry
        if isinstance(content, str):
            return True  # Raw text entries from book chapters
        elif isinstance(content, dict):
            # Dict entries with typical book entry structure
            return any(key in content for key in ["type", "entries", "name"])

        return False

    def _is_adventure_entry(self, content: Any, context: RenderContext) -> bool:
        """Check if content is a raw adventure entry.

        Args:
            content: Content to check
            context: Rendering context

        Returns:
            True if content is a raw adventure entry
        """
        # Check if we're in an adventure document context
        if not hasattr(context, "metadata") or not context.metadata:
            return False

        if context.metadata.document_type != DocumentType.ADVENTURE:
            return False

        # Check if content looks like an adventure entry
        if isinstance(content, str):
            return True  # Raw text entries from adventure chapters
        elif isinstance(content, dict):
            # Dict entries with typical adventure entry structure
            return any(key in content for key in ["type", "entries", "name"])

        return False

    def _render_adventure_entry(self, content: Any, context: RenderContext) -> str:
        """Render a raw adventure entry using RecursiveEntryProcessor.

        Args:
            content: Raw adventure entry (string or dict)
            context: Rendering context

        Returns:
            Rendered LaTeX content
        """
        # Import here to avoid circular imports
        from .entry_processor import RecursiveEntryProcessor

        # Use DND template for adventure entries
        processor = RecursiveEntryProcessor(use_dnd_template=True)

        if isinstance(content, str):
            # Process string content with tags
            if hasattr(context, "tag_resolver") and context.tag_resolver:
                return context.tag_resolver.process_text(content)
            else:
                return self._escape_latex(content)
        elif isinstance(content, dict):
            # Process dict entry - use same approach as book rendering
            return processor.process_entry_dict(content, context)
        else:
            return ""

    def _render_book_entry(self, content: Any, context: RenderContext) -> str:
        """Render a raw book entry using RecursiveEntryProcessor.

        Args:
            content: Raw book entry (string or dict)
            context: Rendering context

        Returns:
            Rendered LaTeX content
        """
        # Import here to avoid circular imports
        from .entry_processor import RecursiveEntryProcessor

        # Use DND template for book entries
        processor = RecursiveEntryProcessor(use_dnd_template=True)

        if isinstance(content, str):
            # Process string content with tags
            if hasattr(context, "tag_resolver") and context.tag_resolver:
                return context.tag_resolver.process_text(content)
            else:
                return self._escape_latex(content)
        elif isinstance(content, dict):
            # Process dict entry
            return processor.process_entry_dict(content, context)
        else:
            return str(content)

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

        if "output_dir" in config and config["output_dir"] is not None:
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
        content_items: Sequence[BaseContent],
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
        working_dir: Path | None
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
