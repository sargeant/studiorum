"""Book conversion command."""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path

import typer
from rich import print as rprint

from dnd5e.cli.config_factory import (
    get_appendix_creatures_default,
    get_appendix_items_default,
    get_appendix_spells_default,
    get_background_default,
    get_compile_pdf_default,
    get_concurrent_limit_default,
    get_document_class_default,
    get_font_size_default,
    get_fonts_default,
    get_high_contrast_default,
    get_justified_default,
    get_no_outline_default,
    get_two_column_default,
    get_with_images_default,
    get_with_index_default,
)
from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer, get_tag_resolver
from dnd5e.core.config.latex_config import LaTeXConfig
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler


def _create_latex_compiler() -> LaTeXCompiler:
    """Create a LaTeX compiler with configuration from unified config.

    Returns:
        LaTeXCompiler configured with unified application config
    """
    config = get_app_config()

    # Create compilation configuration from unified config
    compilation_config = CompilationConfig(
        primary_engine=LaTeXEngine(config.rendering.latex.engine.primary_engine),
        fallback_engines=[
            LaTeXEngine(engine)
            for engine in config.rendering.latex.engine.fallback_engines
        ],
        timeout_seconds=config.rendering.latex.engine.timeout,
        max_passes=config.rendering.latex.engine.max_passes,
        show_progress=config.rendering.latex.engine.show_progress,
        keep_intermediate_files=config.rendering.latex.engine.keep_temp_files,
    )

    return LaTeXCompiler(compilation_config)


def resolve_content_or_file(
    source: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Resolve content source to content objects.

    Args:
        source: File path or content abbreviation
        content_type: Type of content to resolve

    Returns:
        tuple of (content_items, source_description)

    Raises:
        typer.Exit: If content cannot be resolved
    """
    omnidexer = get_omnidexer()

    # Check if it's a file path
    path = Path(source)
    if path.is_file():
        content_data = _load_from_file(path)
        if isinstance(content_data, list):
            return content_data, f"file: {path}"
        else:
            return [content_data], f"file: {path}"

    # Try to resolve as abbreviation
    resolver = ContentResolver(omnidexer)
    if content_type == ContentType.ADVENTURE:
        result = resolver.resolve_adventure(source)
    elif content_type == ContentType.BOOK:
        result = resolver.resolve_book(source)
    else:
        rprint(f"[red]Error:[/red] Unsupported content type: {content_type}")
        raise typer.Exit(1)

    return _handle_resolution_result(result, source, content_type)


def _load_from_file(file_path: Path) -> BaseContent | list[BaseContent]:
    """Load content from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle both single objects and arrays
        if isinstance(data, list):
            return data  # type: ignore[return-value,no-any-return]
        else:
            return data  # type: ignore[return-value,no-any-return]

    except (json.JSONDecodeError, FileNotFoundError) as e:
        rprint(f"[red]Error:[/red] Failed to load file {file_path}: {e}")
        raise typer.Exit(1)


def _handle_resolution_result(
    result: ContentResolutionResult, query: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Handle content resolution result."""
    if result.is_success and result.content:
        return [result.content], f"abbreviation: {query}"

    elif result.suggestions:
        content_name = content_type.value
        rprint("[yellow]Did you mean?[/yellow]")
        for suggestion in result.suggestions[:5]:
            rprint(f"  • {suggestion}")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see all available content."
        )
        raise typer.Exit(1)

    else:
        content_name = content_type.value
        rprint(f"[red]Error:[/red] {content_name.title()} '{query}' not found.")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see available content."
        )
        raise typer.Exit(1)


async def _compile_pdf(latex_path: Path) -> None:
    """Compile LaTeX to PDF using configured LaTeX compiler."""
    rprint(f"[cyan]Compiling PDF: {latex_path.with_suffix('.pdf')}[/cyan]")

    try:
        compiler = _create_latex_compiler()

        # Read the LaTeX file content
        with open(latex_path, "r", encoding="utf-8") as f:
            latex_content = f.read()

        with display_manager.progress("Compiling PDF") as _:
            compile_task = display_manager.add_task(
                "[cyan]Running LaTeX compilation...", total=None
            )

            # Use the configured compiler instead of hardcoded xelatex
            result = await compiler.compile_document(
                latex_content,
                output_name=latex_path.stem,
                working_dir=latex_path.parent,
            )

            display_manager.update_task(compile_task, completed=100)

        if result.success:
            rprint(f"[green]✓[/green] PDF compiled: {latex_path.with_suffix('.pdf')}")
        else:
            rprint("[red]✗[/red] Compilation failed")
            if result.error_message:
                rprint(f"[red]Error:[/red] {result.error_message}")
            if result.warnings:
                for warning in result.warnings:
                    rprint(f"[yellow]Warning:[/yellow] {warning}")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]Error during PDF compilation:[/red] {e}")
        raise typer.Exit(1)


def book(
    content_source: str = typer.Argument(
        ..., help="Book abbreviation (e.g., 'phb') or file path"
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output LaTeX file",
        rich_help_panel="Output Control",
    ),
    title: str | None = typer.Option(
        None, "--title", help="Document title", rich_help_panel="Output Control"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(),
        "--images/--no-images",
        help="Include images",
        rich_help_panel="Content Options",
    ),
    with_index: bool = typer.Option(
        get_with_index_default(),
        "--index/--no-index",
        help="Include index",
        rich_help_panel="Content Options",
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(),
        "--pdf",
        help="Compile to PDF after conversion",
        rich_help_panel="Output Control",
    ),
    # LaTeX document class options
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
        rich_help_panel="Document Layout",
    ),
    paper: str | None = typer.Option(
        None,
        "--paper",
        help="Paper size (letter, a4, a5)",
        rich_help_panel="Document Layout",
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(),
        "--fonts",
        help="Font package to use (wotc, dmsguild)",
        rich_help_panel="Visual Styling",
    ),
    no_outline: bool | None = typer.Option(
        None,
        "--no-outline",
        help="Disable document outline",
        rich_help_panel="Visual Styling",
    ),
    font_size: str | None = typer.Option(
        None,
        "--font-size",
        help="Base font size (10pt, 11pt, 12pt)",
        rich_help_panel="Visual Styling",
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
        rich_help_panel="Visual Styling",
    ),
    high_contrast: bool | None = typer.Option(
        None,
        "--high-contrast",
        help="Use high contrast mode",
        rich_help_panel="Visual Styling",
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
        rich_help_panel="Document Layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
        rich_help_panel="Document Layout",
    ),
    # Appendix options
    appendix_spells: bool = typer.Option(
        get_appendix_spells_default(),
        "--spells/--no-spells",
        help="Generate spells appendix with all referenced spells",
        rich_help_panel="Appendices",
    ),
    appendix_items: bool = typer.Option(
        get_appendix_items_default(),
        "--items/--no-items",
        help="Generate items appendix with all referenced items",
        rich_help_panel="Appendices",
    ),
    appendix_creatures: bool = typer.Option(
        get_appendix_creatures_default(),
        "--creatures/--no-creatures",
        help="Generate creatures appendix with all referenced creatures",
        rich_help_panel="Appendices",
    ),
) -> None:
    """
    📚 Convert book to LaTeX

    Converts a D&D sourcebook to a beautifully formatted LaTeX document
    matching official book styling.

    \\b
    Examples:
      5e2pdf convert book phb                   # Use abbreviation
      5e2pdf convert book /path/to/phb.json     # Use file path
      5e2pdf list books                         # See available content
    """

    def _convert() -> None:
        result = None  # Initialize to avoid UnboundLocalError
        try:
            # Resolve content source (file or abbreviation)
            content_items, source_desc = resolve_content_or_file(
                content_source, ContentType("book")
            )

            # Determine output file
            if output_file is None:
                if "file:" in source_desc:
                    # Use input filename for file-based sources
                    input_name = Path(content_source).with_suffix(".tex").name
                else:
                    # Use content name for abbreviation-based sources
                    input_name = f"{content_source}.tex"
                output_path = Path("output/books") / input_name
            else:
                output_path = output_file

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Create LaTeX configuration with user config preferences
            from dnd5e.core.config.sources import get_content_config

            app_config = get_app_config()
            user_config = get_content_config()

            # Apply configuration hierarchy: CLI args > user config > app defaults
            actual_paper_size = (
                paper
                or user_config.latex.paper_size
                or app_config.rendering.latex.document.paper_size
            )
            actual_fonts = (
                fonts
                or user_config.latex.fonts
                or app_config.rendering.latex.document.fonts
            )
            actual_background = (
                background
                or user_config.latex.background
                or app_config.rendering.latex.document.background
            )
            actual_no_outline = (
                no_outline
                if no_outline is not None
                else user_config.latex.no_outline
                if user_config.latex.no_outline is not None
                else app_config.rendering.latex.document.no_outline
            )
            actual_font_size = (
                font_size
                or user_config.latex.font_size
                or app_config.rendering.latex.document.font_size
            )
            actual_high_contrast = (
                high_contrast
                if high_contrast is not None
                else user_config.latex.high_contrast
                if user_config.latex.high_contrast is not None
                else app_config.rendering.latex.document.high_contrast
            )
            actual_two_column = (
                two_column
                if two_column is not None
                else user_config.latex.two_column
                if user_config.latex.two_column is not None
                else app_config.rendering.latex.document.two_column
            )
            actual_justified = (
                justified
                if justified is not None
                else user_config.latex.justified
                if user_config.latex.justified is not None
                else app_config.rendering.latex.document.justified_text
            )

            # Import legacy config classes for backward compatibility
            from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=actual_paper_size,
                font_size=actual_font_size,
                background=actual_background,
                high_contrast=actual_high_contrast,
                two_column=actual_two_column,
                justified_text=actual_justified,
                fonts=actual_fonts,
                no_outline=actual_no_outline,
            )
            latex_config = LaTeXConfig(document=latex_doc_config)

            # Create document metadata for proper DND template rendering
            from dnd5e.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            # Get book title - handle both dict and object formats
            if hasattr(content_items[0], "name"):
                book_title = content_items[0].name
            elif isinstance(content_items[0], dict):
                book_title = content_items[0].get("name", "Player's Handbook")
            else:
                book_title = "Player's Handbook"

            metadata = DocumentMetadata(
                title=title or book_title,
                document_type=DocumentType.BOOK,
                include_toc=True,
                include_index=with_index,
            )

            # Create content tracker for appendix generation
            from dnd5e.core.references.content_tracker import ContentTracker

            content_tracker = ContentTracker()

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                content_tracker=content_tracker,
                tag_resolver=tag_resolver,
                metadata={
                    "title": title or f"Book: {book_title}",
                    "include_images": with_images,
                    "include_toc": True,
                    "include_index": with_index,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "content_tracker": content_tracker,
                    "appendix_spells": appendix_spells,
                    "appendix_items": appendix_items,
                    "appendix_creatures": appendix_creatures,
                },
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with display_manager.progress("Rendering book") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering book...", total=None
                )
                result = renderer.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                rprint(
                    f"[green]✓[/green] Book converted ({source_desc}): {output_path}"
                )
            else:
                rprint("[red]Error:[/red] No content was generated")
                raise typer.Exit(1)

            # Compile PDF if requested
            if compile_pdf:
                asyncio.run(_compile_pdf(output_path))

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()
