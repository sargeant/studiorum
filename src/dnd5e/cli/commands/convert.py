"""Convert command for 5e2pdf CLI."""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path

import typer
from rich import print as rprint

from dnd5e.cli.config_factory import (
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
    get_with_creatures_default,
    get_with_images_default,
    get_with_index_default,
    get_with_items_default,
)
from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer, get_tag_resolver
from dnd5e.core.config.latex_config import LaTeXConfig
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler


class SpellSortMode(str, Enum):
    """Sorting modes for spell output."""

    LEVEL = "level"
    NAME = "name"


class ItemSortMode(str, Enum):
    """Sorting modes for item output."""

    TYPE = "type"
    NAME = "name"
    RARITY = "rarity"
    VALUE = "value"


app: typer.Typer = typer.Typer(help="Convert D&D content to LaTeX/PDF")
console = display_manager.console


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
    content_source: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Resolve input as either file path or content abbreviation.

    Args:
        content_source: Either a file path or content abbreviation
        content_type: The type of content to resolve

    Returns:
        Tuple of (content_items, source_description)

    Raises:
        typer.Exit: If content cannot be resolved or loaded
    """
    # Check if it's a file path
    file_path = Path(content_source)
    if file_path.is_file():
        return _load_from_file(file_path, content_type)

    # Otherwise, treat as content abbreviation
    # Initialize result to avoid UnboundLocalError
    result = None

    omnidexer = get_omnidexer()
    resolver = ContentResolver(omnidexer)

    if content_type.value == "adventure":
        result = resolver.resolve_adventure(content_source)
    elif content_type.value == "book":
        result = resolver.resolve_book(content_source)
    else:
        result = resolver.resolve_any(content_source, content_type)

    if result is None:
        raise ValueError(f"Failed to resolve content: {content_source}")

    return _handle_resolution_result(result, content_source, content_type)


def _load_from_file(
    file_path: Path, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Load content from a JSON file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
        data = json.loads(content)

    if content_type.value == "adventure":
        from dnd5e.core.models.adventures import Adventure

        # Get adventure data (could be nested)
        if "adventure" in data:
            adventure_items = data["adventure"]
        else:
            adventure_items = [data]

        content_items: list[BaseContent] = []
        for item in adventure_items:
            if isinstance(item, dict):
                content_items.append(Adventure.model_validate(item))

        if not content_items:
            rprint("[red]Error:[/red] No valid adventure content found")
            raise typer.Exit(1)

        return content_items, f"file: {file_path}"

    elif content_type.value == "book":
        from dnd5e.core.models.books import Book
        from dnd5e.core.models.chapter import Chapter
        from dnd5e.core.models.content import Source

        # Extract book metadata from filename if available
        book_id = file_path.stem.replace("book-", "").upper()
        book_name = f"Book: {book_id}"

        # Get book content sections
        book_sections = []
        if "data" in data:
            book_sections = data["data"]
        elif "book" in data:
            book_sections = data["book"]
        else:
            book_sections = [data] if isinstance(data, dict) else []

        # Convert sections to chapters
        chapters = []
        for section in book_sections:
            if isinstance(section, dict) and section.get("type") == "section":
                chapter = Chapter(
                    name=section.get("name", "Untitled Chapter"),
                    ordinal=None,
                    headers=None,
                    entries=section.get("entries", []),
                )
                chapters.append(chapter)

        # Create a complete book object
        book = Book(
            name=book_name,
            source=Source(abbreviation=book_id, name=book_name, page=None, url=None),
            id=book_id,
            metadata=None,
            published=None,
            author=None,
            cover=None,
            contents=chapters,
        )

        return [book], f"file: {file_path}"

    else:
        rprint(
            f"[red]Error:[/red] Unsupported content type for file loading: {content_type}"
        )
        raise typer.Exit(1)


def _handle_resolution_result(
    result: ContentResolutionResult, abbreviation: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Handle the result of content resolution."""
    if result.is_success and result.content:
        return [result.content], f"abbreviation: {abbreviation}"

    elif result.needs_user_selection and result.matches:
        rprint(f"[yellow]Multiple matches found for '{abbreviation}':[/yellow]")
        for i, content in enumerate(result.matches, 1):
            rprint(f"  {i}. {content.name} ({content.source.abbreviation})")
        rprint("Please be more specific or use the full file path.")
        raise typer.Exit(1)

    elif result.has_suggestions:
        content_name = content_type.value
        rprint(f"[red]Error:[/red] {content_name.title()} '{abbreviation}' not found.")
        rprint("[yellow]Did you mean one of these?[/yellow]")
        for suggestion in result.suggestions or []:
            rprint(f"  • {suggestion}")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see all available content."
        )
        raise typer.Exit(1)

    else:
        content_name = content_type.value
        rprint(f"[red]Error:[/red] {content_name.title()} '{abbreviation}' not found.")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see available content."
        )
        raise typer.Exit(1)


@app.command("adventure")
def convert_adventure(
    content_source: str = typer.Argument(
        ..., help="Adventure abbreviation (e.g., 'cos') or file path"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    with_items: bool = typer.Option(
        get_with_items_default(), "--items/--no-items", help="Include item lists"
    ),
    with_creatures: bool = typer.Option(
        get_with_creatures_default(),
        "--creatures/--no-creatures",
        help="Include creature lists",
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    # LaTeX document class options
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
    ),
    paper: str | None = typer.Option(
        None, "--paper", help="Paper size (letter, a4, a5)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str | None = typer.Option(
        None, "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
    ),
    high_contrast: bool | None = typer.Option(
        None, "--high-contrast", help="Use high contrast mode"
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
    ),
) -> None:
    """
    📖 Convert adventure to LaTeX

    Converts a D&D adventure to a beautifully formatted LaTeX document
    matching official book styling.

    \b
    Examples:
      5e2pdf convert adventure cos              # Use abbreviation
      5e2pdf convert adventure /path/to/cos.json  # Use file path
      5e2pdf list adventures                    # See available content
    """

    def _convert() -> None:
        result = None  # Initialize to avoid UnboundLocalError
        try:
            # Resolve content source (file or abbreviation)
            content_items, source_desc = resolve_content_or_file(
                content_source, ContentType("adventure")
            )

            # Determine output file
            if output_file is None:
                if "file:" in source_desc:
                    # Use input filename for file-based sources
                    input_name = Path(content_source).with_suffix(".tex").name
                else:
                    # Use content name for abbreviation-based sources
                    input_name = f"{content_source}.tex"
                output_path = Path("output/adventures") / input_name
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

            # Create document metadata for adventure
            from ...core.models.document_metadata import DocumentMetadata, DocumentType

            metadata = DocumentMetadata(
                title=title or f"{content_items[0].name}",
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,
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

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": title or f"{content_items[0].name}",
                    "include_images": with_images,
                    "include_toc": True,
                    "include_items": with_items,
                    "include_creatures": with_creatures,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                },
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with display_manager.progress("Rendering adventure") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering adventure...", total=None
                )
                result = renderer.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                rprint(
                    f"[green]✓[/green] Adventure converted ({source_desc}): {output_path}"
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


@app.command("book")
def convert_book(
    content_source: str = typer.Argument(
        ..., help="Book abbreviation (e.g., 'phb') or file path"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    with_index: bool = typer.Option(
        get_with_index_default(), "--index/--no-index", help="Include index"
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    # LaTeX document class options
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
    ),
    paper: str | None = typer.Option(
        None, "--paper", help="Paper size (letter, a4, a5)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str | None = typer.Option(
        None, "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
    ),
    high_contrast: bool | None = typer.Option(
        None, "--high-contrast", help="Use high contrast mode"
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
    ),
) -> None:
    """
    📚 Convert book to LaTeX

    Converts a D&D sourcebook to a beautifully formatted LaTeX document
    matching official book styling.

    \b
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

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": title or f"Book: {book_title}",
                    "include_images": with_images,
                    "include_toc": True,
                    "include_index": with_index,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
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


@app.command("supplement")
def convert_supplement(
    input_file: Path = typer.Argument(..., help="Supplement JSON file"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    content_types: list[str] = typer.Option(
        ["all"], "--type", help="Content types to include"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    # LaTeX document class options
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
    ),
    paper: str | None = typer.Option(
        None, "--paper", help="Paper size (letter, a4, a5)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str | None = typer.Option(
        None, "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
    ),
    high_contrast: bool | None = typer.Option(
        None, "--high-contrast", help="Use high contrast mode"
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
    ),
) -> None:
    """
    📄 Convert supplement JSON to LaTeX

    Converts various D&D content (spells, creatures, items) from 5e.tools JSON
    format into a formatted supplement document.
    """

    def _convert() -> None:
        result = None  # Initialize to avoid UnboundLocalError
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Supplement file not found: {input_file}")
                raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                output_path = (
                    Path("output/supplements") / input_file.with_suffix(".tex").name
                )
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

            # Load supplement content
            with open(input_file, encoding="utf-8") as f:
                content = f.read()
                supplement_data = json.loads(content)

            # Parse various content types
            content_items = []

            # Import models
            from dnd5e.core.models.creatures import Creature
            from dnd5e.core.models.items import Item
            from dnd5e.core.models.spells import Spell

            # Process different content types
            type_handlers = {
                "spell": Spell,
                "spells": Spell,
                "monster": Creature,
                "monsters": Creature,
                "creature": Creature,
                "creatures": Creature,
                "item": Item,
                "items": Item,
            }

            for key, items in supplement_data.items():
                if isinstance(items, list) and key in type_handlers:
                    if "all" in content_types or key in content_types:
                        model_class = type_handlers[key]
                        for item_data in items:
                            try:
                                # Add source info if missing
                                if "source" not in item_data:
                                    item_data["source"] = {
                                        "abbreviation": input_file.stem.upper(),
                                        "name": input_file.stem.replace(
                                            "-", " "
                                        ).title(),
                                    }
                                content_items.append(
                                    model_class.model_validate(item_data)  # type: ignore[attr-defined]
                                )
                            except Exception as e:
                                rprint(
                                    f"[yellow]Warning:[/yellow] Failed to parse {key} item: {e}"
                                )

            if not content_items:
                rprint("[red]Error:[/red] No valid content found")
                raise typer.Exit(1)

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

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": title
                    or f"Supplement: {input_file.stem.replace('-', ' ').title()}",
                    "include_images": with_images,
                    "include_toc": len(content_items) > 10,
                    "tag_resolver": tag_resolver,
                    "latex_config": latex_config,
                },
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with display_manager.progress("Rendering supplement") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering supplement...", total=None
                )
                result = renderer.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                rprint(
                    f"[green]✓[/green] Supplement converted ({len(content_items)} items): {output_path}"
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


@app.command("bulk")
def convert_bulk(
    content_list: list[str] = typer.Argument(
        ..., help="List of adventure/book abbreviations or file paths"
    ),
    content_type: str = typer.Option(
        "adventure", "--type", help="Content type (adventure, book, mixed)"
    ),
    output_dir: Path = typer.Option(
        Path("output/bulk"), "--output-dir", "-d", help="Output directory"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    concurrent_limit: int = typer.Option(
        get_concurrent_limit_default(),
        "--concurrent",
        help="Maximum concurrent operations",
    ),
) -> None:
    """
    ⚡ Convert multiple content items using optimized bulk operations

    Uses async bulk resolution for significantly faster processing when
    converting multiple adventures, books, or mixed content.

    \b
    Examples:
      5e2pdf convert bulk cos lmop hotdq --type adventure
      5e2pdf convert bulk phb mm dmg --type book
      5e2pdf convert bulk cos phb mm --type mixed
    """

    def _bulk_convert() -> None:
        try:
            # Load omnidexer and resolver
            with display_manager.progress("Initializing") as _:
                init_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                resolver = ContentResolver(omnidexer)
                display_manager.update_task(init_task, completed=100)

            # Perform bulk resolution based on content type
            with display_manager.progress("Resolving content") as _:
                resolve_task = display_manager.add_task(
                    f"[cyan]Resolving {len(content_list)} items...",
                    total=len(content_list),
                )

                if content_type == "adventure":
                    results = resolver.resolve_adventures_bulk(content_list)
                elif content_type == "book":
                    results = resolver.resolve_books_bulk(content_list)
                elif content_type == "mixed":
                    # For mixed content, try to determine types from abbreviations
                    mixed_requests = []
                    for abbrev in content_list:
                        # Simple heuristic: common book abbreviations
                        if abbrev.lower() in [
                            "phb",
                            "mm",
                            "dmg",
                            "xgte",
                            "tcoe",
                            "vgtm",
                            "mtof",
                        ]:
                            mixed_requests.append((abbrev, ContentType("book")))
                        else:
                            mixed_requests.append((abbrev, ContentType("adventure")))
                    results = resolver.resolve_multiple(mixed_requests)
                else:
                    rprint(f"[red]Error:[/red] Invalid content type: {content_type}")
                    raise typer.Exit(1)

                display_manager.update_task(resolve_task, completed=len(content_list))

            # Filter successful results
            successful_results = [r for r in results if r.is_success and r.content]
            failed_results = [r for r in results if not r.is_success]

            if failed_results:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(failed_results)} items failed to resolve:"
                )
                for result in failed_results:
                    rprint(f"  • {result.query}: {result.status.value}")
                    if result.suggestions:
                        rprint(f"    Suggestions: {', '.join(result.suggestions[:3])}")

            if not successful_results:
                rprint("[red]Error:[/red] No content could be resolved")
                raise typer.Exit(1)

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def convert_single_item(
                result: ContentResolutionResult,
            ) -> tuple[str, bool]:
                """Convert a single content item with concurrency control."""
                async with semaphore:
                    try:
                        content = result.content
                        if content is None:
                            return result.query, False

                        output_filename = f"{result.query}.tex"
                        output_path = output_dir / output_filename

                        # Create render context
                        context = RenderingContext(
                            output_format="latex",
                            omnidexer=omnidexer,
                            metadata={
                                "title": f"{content.name}",
                                "include_images": with_images,
                                "include_toc": True,
                                "tag_resolver": tag_resolver,
                            },
                        )

                        # Render document
                        renderer = LaTeXDocumentRenderer()
                        latex_result = renderer.render_document([content], context)

                        # Write output
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(latex_result)

                        # Compile PDF if requested
                        if compile_pdf:
                            asyncio.run(_compile_pdf(output_path))

                        return result.query, True
                    except Exception as e:
                        rprint(f"[red]Error converting {result.query}:[/red] {e}")
                        return result.query, False

            # Process all items concurrently with progress tracking
            with display_manager.progress("Converting content") as _:
                convert_task = display_manager.add_task(
                    f"[green]Converting {len(successful_results)} items...",
                    total=len(successful_results),
                )

                # Create conversion tasks
                conversion_tasks = [
                    convert_single_item(result) for result in successful_results
                ]

                # Process with progress updates
                async def process_conversions() -> list[tuple[str, bool]]:
                    completed_results = []
                    for task in asyncio.as_completed(conversion_tasks):
                        item_name, success = await task
                        completed_results.append((item_name, success))
                        display_manager.update_task(convert_task, advance=1)
                    return completed_results

                completed_results = asyncio.run(process_conversions())

            # Report results
            successful_conversions = [
                name for name, success in completed_results if success
            ]
            failed_conversions = [
                name for name, success in completed_results if not success
            ]

            rprint("\n[green]✓[/green] Bulk conversion completed:")
            rprint(f"  • Successfully converted: {len(successful_conversions)} items")
            if failed_conversions:
                rprint(f"  • Failed conversions: {len(failed_conversions)} items")
            rprint(f"  • Output directory: {output_dir}")

            if successful_conversions:
                rprint("\n[green]Successfully converted:[/green]")
                for name in successful_conversions:
                    rprint(f"  ✓ {name}")

            if failed_conversions:
                rprint("\n[red]Failed to convert:[/red]")
                for name in failed_conversions:
                    rprint(f"  ✗ {name}")

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _bulk_convert()


@app.command("spells")
def convert_spells(
    # Direct spell names as positional arguments
    spell_names: list[str] = typer.Argument(
        None, help="Spell names to include (e.g., 'fireball' 'magic missile')"
    ),
    # Input sources
    from_file: Path | None = typer.Option(
        None, "--from-file", help="Read spell names from file (one per line)"
    ),
    from_stdin: bool = typer.Option(
        False, "--from-stdin", help="Read spell names from stdin"
    ),
    # Class-based filtering
    classes: list[str] = typer.Option(
        None, "--class", help="Spellcaster classes (e.g., wizard,cleric)"
    ),
    level: str | None = typer.Option(
        None, "--level", help="Level range (e.g., '1-5', '3+', '0' for cantrips)"
    ),
    max_level: int | None = typer.Option(
        None, "--max-level", help="Maximum spell level (0-9)"
    ),
    # School and component filtering
    schools: list[str] = typer.Option(
        None, "--school", help="Schools of magic (e.g., evocation,abjuration)"
    ),
    verbal: bool | None = typer.Option(
        None, "--verbal/--no-verbal", help="Filter by verbal components"
    ),
    somatic: bool | None = typer.Option(
        None, "--somatic/--no-somatic", help="Filter by somatic components"
    ),
    material: bool | None = typer.Option(
        None, "--material/--no-material", help="Filter by material components"
    ),
    no_material: bool = typer.Option(
        False, "--no-material", help="Exclude spells with material components"
    ),
    concentration: bool | None = typer.Option(
        None, "--concentration/--no-concentration", help="Filter by concentration"
    ),
    ritual: bool | None = typer.Option(
        None, "--ritual/--no-ritual", help="Filter by ritual casting"
    ),
    # Combat filtering
    damage_types: list[str] = typer.Option(
        None, "--damage-type", help="Damage types (e.g., fire,cold)"
    ),
    saving_throws: list[str] = typer.Option(
        None, "--save", help="Saving throw types (e.g., dex,wis)"
    ),
    attack_spells: bool | None = typer.Option(
        None, "--attack-spell/--no-attack-spell", help="Filter for spell attack rolls"
    ),
    # Source filtering
    sources: list[str] = typer.Option(
        None, "--sources", help="Source abbreviations (e.g., PHB,XGE)"
    ),
    # Standard document options
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    # LaTeX document class options (inherited from other convert commands)
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
    ),
    paper: str | None = typer.Option(
        None, "--paper", help="Paper size (letter, a4, a5)"
    ),
    fonts: str | None = typer.Option(
        None, "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool | None = typer.Option(
        None, "--no-outline", help="Disable document outline"
    ),
    font_size: str | None = typer.Option(
        None, "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
    ),
    high_contrast: bool | None = typer.Option(
        None, "--high-contrast", help="Use high contrast mode"
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
    ),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    sort: SpellSortMode = typer.Option(
        SpellSortMode.LEVEL,
        "--sort",
        help="Sort order: 'level' (group by level, default) or 'name' (alphabetical)",
    ),
    show_toc: bool = typer.Option(
        True, "--toc/--no-toc", help="Show table of contents (default: enabled)"
    ),
    include_optional: bool = typer.Option(
        False, "--optional-spells", help="Include optional/variant class spells"
    ),
) -> None:
    """
    🔮 Convert spells to LaTeX spell book

    Create beautifully formatted spell books from 5e.tools spell data.
    Supports both specific spell lists (wizard use case) and class-based
    filtering (cleric use case) with advanced filtering options.

    \b
    Examples:
      # Specific spells (wizard use case)
      5e2pdf convert spells "fireball" "magic missile" "counterspell"
      5e2pdf convert spells --from-file my-spells.txt

      # Class-based filtering (cleric use case)
      5e2pdf convert spells --class cleric --level 1-5
      5e2pdf convert spells --class wizard,sorcerer --max-level 3

      # Advanced filtering
      5e2pdf convert spells --class wizard --school evocation --level 1-9
      5e2pdf convert spells --damage-type fire --no-material
      5e2pdf convert spells --concentration --sources PHB,XGE

      # Sorting options
      5e2pdf convert spells --class wizard --sort level   # Group by level (default)
      5e2pdf convert spells --class wizard --sort name    # Alphabetical order
    """

    def _convert() -> None:
        try:
            # Import spell-specific modules
            from dnd5e.core.models.spell_filters import SpellFilterCriteria
            from dnd5e.core.parsers.spell_input import SpellInputParser
            from dnd5e.core.services.spell_collector import SpellCollector

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading spell data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Parse input sources and build criteria
            all_spell_names = []

            # Collect spell names from arguments
            if spell_names:
                all_spell_names.extend(spell_names)

            # Collect from file
            if from_file:
                if not from_file.exists():
                    rprint(f"[red]Error:[/red] Spell file not found: {from_file}")
                    raise typer.Exit(1)

                file_spells = SpellInputParser.parse_spell_names_from_file(from_file)
                all_spell_names.extend(file_spells)
                rprint(
                    f"[green]Loaded {len(file_spells)} spells from {from_file}[/green]"
                )

            # Collect from stdin
            if from_stdin:
                stdin_spells = SpellInputParser.parse_spell_names_from_stdin()
                all_spell_names.extend(stdin_spells)
                rprint(f"[green]Loaded {len(stdin_spells)} spells from stdin[/green]")

            # Parse level range if provided
            min_level, max_level_parsed = None, None
            if level:
                try:
                    min_level, max_level_parsed = SpellInputParser.parse_level_range(
                        level
                    )
                except ValueError as e:
                    rprint(f"[red]Error:[/red] Invalid level range: {e}")
                    raise typer.Exit(1)

            # Use max_level option if provided, otherwise use parsed max_level
            effective_max_level = (
                max_level if max_level is not None else max_level_parsed
            )

            # Parse class list
            parsed_classes = None
            if classes:
                parsed_classes = []
                for cls_list in classes:
                    parsed_classes.extend(SpellInputParser.parse_class_list(cls_list))

            # Parse source list
            parsed_sources = None
            if sources:
                parsed_sources = []
                for src_list in sources:
                    parsed_sources.extend(SpellInputParser.parse_source_list(src_list))

            # Build filter criteria
            try:
                criteria = SpellFilterCriteria(
                    min_level=min_level,
                    max_level=effective_max_level,
                    classes=parsed_classes,
                    include_optional=include_optional,
                    schools=schools,
                    has_verbal=verbal,
                    has_somatic=somatic,
                    has_material=material,
                    no_material=no_material,
                    concentration=concentration,
                    ritual=ritual,
                    damage_types=damage_types,
                    saving_throws=saving_throws,
                    attack_spells=attack_spells,
                    sources=parsed_sources,
                    spell_names=all_spell_names if all_spell_names else None,
                )
            except ValueError as e:
                rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
                raise typer.Exit(1)

            # Collect spells using SpellCollector
            collector = SpellCollector(omnidexer)

            with display_manager.progress("Collecting spells") as _:
                collect_task = display_manager.add_task(
                    "[cyan]Filtering spells...", total=None
                )
                result = collector.collect_spells(criteria)
                display_manager.update_task(collect_task, completed=100)

            # Handle unresolved spells
            if result.unresolved_names:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} spells could not be found:"
                )
                for name in result.unresolved_names:
                    rprint(f"  • {name}")
                    if name in result.suggestions and result.suggestions[name]:
                        rprint(
                            f"    Suggestions: {', '.join(result.suggestions[name][:3])}"
                        )
                rprint()

            if not result.spells:
                rprint("[red]Error:[/red] No spells found matching criteria")
                if result.unresolved_names and any(result.suggestions.values()):
                    rprint(
                        "[yellow]Try using one of the suggested spell names above.[/yellow]"
                    )
                raise typer.Exit(1)

            # Sort spells based on the sort mode
            if sort == SpellSortMode.LEVEL:
                # Sort by level, then alphabetically (default behavior)
                sorted_spells = sorted(
                    result.spells, key=lambda s: (s.level, s.name.lower())
                )

                # Group spells by level for template rendering
                spells_by_level: dict[int, list[Spell]] = {}
                for spell in sorted_spells:
                    spell_level = spell.level
                    if spell_level not in spells_by_level:
                        spells_by_level[spell_level] = []
                    spells_by_level[spell_level].append(spell)
            else:  # SpellSortMode.NAME
                # Sort alphabetically by name only
                sorted_spells = sorted(result.spells, key=lambda s: s.name.lower())

                # Create a single flat "group" for template (level 999 ensures it's last)
                spells_by_level = {999: sorted_spells}

            rprint(f"[green]Found {result.total_count} spells:[/green]")
            rprint(f"  {result.get_level_summary()}")
            if result.sources_used:
                rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
            rprint()

            # Determine output file
            if output_file is None:
                output_path = Path("output/spells") / "spellbook.tex"
            else:
                output_path = output_file

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

            # Create document metadata
            from dnd5e.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            spell_title = title or "Spell Collection"
            if parsed_classes and len(parsed_classes) == 1:
                spell_title = title or f"{parsed_classes[0].title()} Spell Book"
            elif parsed_classes:
                spell_title = (
                    title
                    or f"Spell Collection ({', '.join(c.title() for c in parsed_classes)})"
                )

            metadata = DocumentMetadata(
                title=spell_title,
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,  # Use adventure type for now
                include_toc=True,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=f"Collection of {len(sorted_spells)} spells",
                use_parts=False,
            )

            # Create render context with spellbook-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": spell_title,
                    "include_images": with_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "spell_count": len(sorted_spells),
                    "spell_summary": result.get_level_summary(),
                    "spells_by_level": spells_by_level,
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "spellbook",  # Use spellbook template
                },
            )

            # Render document using custom spellbook rendering
            with display_manager.progress("Rendering spellbook") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering spellbook...", total=None
                )
                latex_result = _render_spellbook(
                    sorted_spells,
                    context,
                    latex_config,
                    spells_by_level,
                    sort,
                    show_toc,
                )
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if latex_result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(latex_result)
                rprint(f"[green]✓[/green] Spellbook generated: {output_path}")
            else:
                rprint("[red]Error:[/red] No LaTeX content was generated")
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


@app.command("items")
def convert_items(
    # Direct item names as positional arguments
    item_names: list[str] = typer.Argument(
        None, help="Item names to include (e.g., 'bag of holding' 'sword of sharpness')"
    ),
    # Input sources
    from_file: Path | None = typer.Option(
        None, "--from-file", help="Read item names from file (one per line)"
    ),
    from_stdin: bool = typer.Option(
        False, "--from-stdin", help="Read item names from stdin"
    ),
    # Type-based filtering
    item_types: list[str] = typer.Option(
        None, "--type", help="Item types (e.g., weapon,armor)"
    ),
    magic: bool = typer.Option(False, "--magic", help="Include only magic items"),
    mundane: bool = typer.Option(
        False, "--mundane", help="Include only non-magic items"
    ),
    # Rarity filtering
    rarities: list[str] = typer.Option(
        None, "--rarity", help="Item rarities (e.g., common,uncommon)"
    ),
    # Value filtering
    value_range: str | None = typer.Option(
        None, "--value", help="Value range (e.g., '1-10', '<100')"
    ),
    max_value: float | None = typer.Option(
        None, "--max-value", help="Maximum value in gp"
    ),
    # Weight filtering
    max_weight: float | None = typer.Option(
        None, "--max-weight", help="Maximum weight in lbs"
    ),
    # Weapon filtering
    weapon_categories: list[str] = typer.Option(
        None, "--weapon-category", help="Weapon categories (martial,simple)"
    ),
    weapon_properties: list[str] = typer.Option(
        None, "--weapon-property", help="Weapon properties (finesse,versatile)"
    ),
    damage_types: list[str] = typer.Option(
        None, "--damage-type", help="Damage types (fire,cold)"
    ),
    # Armor filtering
    armor_types: list[str] = typer.Option(
        None, "--armor-type", help="Armor types (light,medium,heavy)"
    ),
    min_ac: int | None = typer.Option(None, "--min-ac", help="Minimum AC"),
    no_strength_req: bool = typer.Option(
        False, "--no-strength-req", help="No STR requirement"
    ),
    no_stealth_disadvantage: bool = typer.Option(
        False, "--no-stealth", help="No stealth disadvantage"
    ),
    # Magic item filtering
    requires_attunement: bool | None = typer.Option(
        None, "--attunement/--no-attunement", help="Filter by attunement requirement"
    ),
    has_charges: bool | None = typer.Option(
        None, "--charges/--no-charges", help="Filter by charges/uses"
    ),
    consumable: bool | None = typer.Option(
        None, "--consumable/--permanent", help="Filter for consumable items"
    ),
    # Source filtering
    sources: list[str] = typer.Option(
        None, "--sources", help="Source abbreviations (PHB,DMG)"
    ),
    # Standard document options
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    # LaTeX document class options (inherited from other convert commands)
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
    ),
    paper: str | None = typer.Option(
        None, "--paper", help="Paper size (letter, a4, a5)"
    ),
    fonts: str | None = typer.Option(
        None, "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool | None = typer.Option(
        None, "--no-outline", help="Disable document outline"
    ),
    font_size: str | None = typer.Option(
        None, "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
    ),
    high_contrast: bool | None = typer.Option(
        None, "--high-contrast", help="Use high contrast mode"
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
    ),
    with_images: bool = typer.Option(
        get_with_images_default(), "--images/--no-images", help="Include images"
    ),
    sort: ItemSortMode = typer.Option(
        ItemSortMode.TYPE,
        "--sort",
        help="Sort order: 'type' (group by type, default), 'name' (alphabetical), 'rarity', or 'value'",
    ),
    show_toc: bool = typer.Option(
        True, "--toc/--no-toc", help="Show table of contents (default: enabled)"
    ),
) -> None:
    """
    🎒 Convert items to LaTeX item compendium

    Create beautifully formatted item compendiums from 5e.tools item data.
    Supports both specific item lists (treasure hoard use case) and
    type/rarity-based filtering (shop/equipment use case).

    \b
    Examples:
      # Specific items (treasure hoard use case)
      5e2pdf convert items "bag of holding" "sword of sharpness" "potion of healing"
      5e2pdf convert items --from-file treasure-hoard.txt

      # Type-based filtering (shop use case)
      5e2pdf convert items --type weapon --rarity common,uncommon
      5e2pdf convert items --type "adventuring gear" --max-value 10

      # Magic item filtering
      5e2pdf convert items --magic --attunement --sources DMG,XGE
      5e2pdf convert items --rarity rare,very rare --charges

      # Sorting options
      5e2pdf convert items --type weapon --sort type     # Group by type (default)
      5e2pdf convert items --type armor --sort rarity    # Group by rarity
      5e2pdf convert items --magic --sort value          # Sort by value
    """

    def _convert() -> None:
        try:
            # Import item-specific modules
            from dnd5e.core.models.item_filters import ItemFilterCriteria
            from dnd5e.core.parsers.item_input import ItemInputParser
            from dnd5e.core.services.item_collector import ItemCollector

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading item data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Parse input sources and build criteria
            all_item_names = []

            # Collect item names from arguments
            if item_names:
                all_item_names.extend(item_names)

            # Collect from file
            if from_file:
                if not from_file.exists():
                    rprint(f"[red]Error:[/red] Item file not found: {from_file}")
                    raise typer.Exit(1)

                file_items = ItemInputParser.parse_item_names_from_file(from_file)
                all_item_names.extend(file_items)
                rprint(
                    f"[green]Loaded {len(file_items)} items from {from_file}[/green]"
                )

            # Collect from stdin
            if from_stdin:
                stdin_items = ItemInputParser.parse_item_names_from_stdin()
                all_item_names.extend(stdin_items)
                rprint(f"[green]Loaded {len(stdin_items)} items from stdin[/green]")

            # Parse value range if provided
            min_value, max_value_parsed = None, None
            if value_range:
                try:
                    min_value, max_value_parsed = ItemInputParser.parse_value_range(
                        value_range
                    )
                except ValueError as e:
                    rprint(f"[red]Error:[/red] Invalid value range: {e}")
                    raise typer.Exit(1)

            # Use max_value option if provided, otherwise use parsed max_value
            effective_max_value = (
                max_value if max_value is not None else max_value_parsed
            )

            # Parse type list
            parsed_types = None
            if item_types:
                parsed_types = []
                for type_list in item_types:
                    parsed_types.extend(ItemInputParser.parse_type_list(type_list))

            # Parse rarity list
            parsed_rarities = None
            if rarities:
                parsed_rarities = []
                for rarity_list in rarities:
                    parsed_rarities.extend(
                        ItemInputParser.parse_rarity_list(rarity_list)
                    )

            # Parse source list
            parsed_sources = None
            if sources:
                parsed_sources = []
                for src_list in sources:
                    parsed_sources.extend(ItemInputParser.parse_source_list(src_list))

            # Build filter criteria
            try:
                criteria = ItemFilterCriteria(
                    item_types=parsed_types,
                    rarities=parsed_rarities,
                    magic_only=magic,
                    mundane_only=mundane,
                    min_value=min_value,
                    max_value=effective_max_value,
                    max_weight=max_weight,
                    weapon_categories=weapon_categories,
                    weapon_properties=weapon_properties,
                    damage_types=damage_types,
                    armor_types=armor_types,
                    min_ac=min_ac,
                    no_strength_req=no_strength_req,
                    no_stealth_disadvantage=no_stealth_disadvantage,
                    requires_attunement=requires_attunement,
                    has_charges=has_charges,
                    consumable=consumable,
                    sources=parsed_sources,
                    item_names=all_item_names if all_item_names else None,
                )
            except ValueError as e:
                rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
                raise typer.Exit(1)

            # Collect items using ItemCollector
            collector = ItemCollector(omnidexer)

            with display_manager.progress("Collecting items") as _:
                collect_task = display_manager.add_task(
                    "[cyan]Filtering items...", total=None
                )
                result = collector.collect_items(criteria)
                display_manager.update_task(collect_task, completed=100)

            # Handle unresolved items
            if result.unresolved_names:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} items could not be found:"
                )
                for name in result.unresolved_names:
                    rprint(f"  • {name}")
                    if name in result.suggestions and result.suggestions[name]:
                        rprint(
                            f"    Suggestions: {', '.join(result.suggestions[name][:3])}"
                        )
                rprint()

            if not result.items:
                rprint("[red]Error:[/red] No items found matching criteria")
                if result.unresolved_names and any(result.suggestions.values()):
                    rprint(
                        "[yellow]Try using one of the suggested item names above.[/yellow]"
                    )
                raise typer.Exit(1)

            # Sort items based on the sort mode
            if sort == ItemSortMode.TYPE:
                # Sort by type, then alphabetically (default behavior)
                sorted_items = sorted(
                    result.items,
                    key=lambda i: (i.get_type_text().lower(), i.name.lower()),
                )
            elif sort == ItemSortMode.RARITY:
                # Sort by rarity, then alphabetically
                rarity_order = {
                    "common": 0,
                    "uncommon": 1,
                    "rare": 2,
                    "very rare": 3,
                    "legendary": 4,
                    "artifact": 5,
                }
                sorted_items = sorted(
                    result.items,
                    key=lambda i: (
                        rarity_order.get(i.get_rarity_text().lower(), 99),
                        i.name.lower(),
                    ),
                )
            elif sort == ItemSortMode.VALUE:
                # Sort by value, then alphabetically
                def get_sort_value(item: Item) -> tuple[float, str]:
                    # Get value in GP for sorting, use 0 for items without value
                    value_gp = collector._get_item_value_in_gp(item) or 0.0
                    return (value_gp, item.name.lower())

                sorted_items = sorted(result.items, key=get_sort_value)
            else:  # ItemSortMode.NAME
                # Sort alphabetically by name only
                sorted_items = sorted(result.items, key=lambda i: i.name.lower())

            rprint(f"[green]Found {result.total_count} items:[/green]")
            rprint(f"  {result.get_type_summary()}")
            rprint(f"  {result.get_rarity_summary()}")
            if result.sources_used:
                rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
            rprint()

            # Determine output file
            if output_file is None:
                output_path = Path("output/items") / "itemcompendium.tex"
            else:
                output_path = output_file

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

            # Create document metadata
            from dnd5e.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            item_title = title or "Item Compendium"
            if parsed_types and len(parsed_types) == 1:
                type_name = str(parsed_types[0])
                if hasattr(parsed_types[0], "value"):
                    type_name = parsed_types[0].value
                item_title = title or f"{type_name.title()} Collection"
            elif parsed_rarities and len(parsed_rarities) == 1:
                rarity_name = str(parsed_rarities[0])
                if hasattr(parsed_rarities[0], "value"):
                    rarity_name = parsed_rarities[0].value
                item_title = title or f"{rarity_name.title()} Items"

            metadata = DocumentMetadata(
                title=item_title,
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,  # Use adventure type for now
                include_toc=True,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=f"Collection of {len(sorted_items)} items",
                use_parts=False,
            )

            # Create render context with itemcompendium-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": item_title,
                    "include_images": with_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "item_count": len(sorted_items),
                    "type_summary": result.get_type_summary(),
                    "rarity_summary": result.get_rarity_summary(),
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "itemcompendium",  # Use itemcompendium template
                },
            )

            # Render document using custom itemcompendium rendering
            with display_manager.progress("Rendering item compendium") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering item compendium...", total=None
                )
                latex_result = _render_itemcompendium(
                    sorted_items,
                    context,
                    latex_config,
                    sort,
                    show_toc,
                )
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if latex_result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(latex_result)
                rprint(f"[green]✓[/green] Item compendium generated: {output_path}")
            else:
                rprint("[red]Error:[/red] No LaTeX content was generated")
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


def _render_itemcompendium(
    items: list[Item],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    sort_mode: ItemSortMode,
    show_toc: bool,
) -> str:
    """Render items using the itemcompendium template with flexible sorting."""
    from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

    # Group items based on sort mode for template rendering
    if sort_mode == ItemSortMode.TYPE:
        # Group items by type
        items_by_group: dict[str, list[Item]] = {}
        for item in items:
            item_type = item.get_type_text()
            if item_type not in items_by_group:
                items_by_group[item_type] = []
            items_by_group[item_type].append(item)

        # Sort groups by type name
        sorted_groups = sorted(items_by_group.items())

    elif sort_mode == ItemSortMode.RARITY:
        # Group items by rarity
        items_by_group = {}
        rarity_order = [
            "common",
            "uncommon",
            "rare",
            "very rare",
            "legendary",
            "artifact",
        ]

        for item in items:
            rarity = item.get_rarity_text() or "common"
            if rarity not in items_by_group:
                items_by_group[rarity] = []
            items_by_group[rarity].append(item)

        # Sort groups by rarity order
        sorted_groups = []
        for rarity in rarity_order:
            if rarity in items_by_group:
                sorted_groups.append((rarity, items_by_group[rarity]))
        # Add any remaining rarities
        for rarity, items_list in items_by_group.items():
            if rarity not in rarity_order:
                sorted_groups.append((rarity, items_list))

    else:  # NAME or VALUE - single flat group
        sorted_groups = [("All Items", items)]

    # Create template engine and update with our LaTeX config
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(latex_config)

    # Create DND template context with proper styling settings
    template_context = template_engine.create_dnd_template_context(
        content_type="item",
        # Document metadata
        title=context.metadata.get("title", "Item Compendium"),
        metadata=context.metadata.get("document_metadata"),
        latex_config=latex_config,
        # Itemcompendium-specific data
        items=items,
        items_by_group=dict(sorted_groups),
        item_count=len(items),
        type_summary=context.metadata.get("type_summary", ""),
        rarity_summary=context.metadata.get("rarity_summary", ""),
        sources_used=context.metadata.get("sources_used", []),
        show_item_table_of_contents=show_toc,
    )

    # Render using itemcompendium template
    return template_engine.render_template("itemcompendium.tex.j2", template_context)


def _render_spellbook(
    spells: list[Spell],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    spells_by_level: dict[int, list[Spell]],
    sort_mode: SpellSortMode,
    show_toc: bool,
) -> str:
    """Render spells using the spellbook template with flexible sorting."""
    from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

    # Sort levels based on sort mode
    if sort_mode == SpellSortMode.LEVEL:
        # Sort levels (cantrips first, then 1-9)
        sorted_levels = sorted(spells_by_level.keys())
    else:  # SpellSortMode.NAME
        # For name sorting, we have a single group at level 999
        sorted_levels = [999]

    # Create template engine and update with our LaTeX config
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(latex_config)

    # Create DND template context with proper styling settings
    template_context = template_engine.create_dnd_template_context(
        content_type="spell",
        # Document metadata
        title=context.metadata.get("title", "Spell Collection"),
        metadata=context.metadata.get("document_metadata"),
        latex_config=latex_config,
        # Spellbook-specific data
        spells=spells,
        spells_by_level={level: spells_by_level[level] for level in sorted_levels},
        spell_count=len(spells),
        spell_summary=context.metadata.get("spell_summary", ""),
        sources_used=context.metadata.get("sources_used", []),
        show_spell_table_of_contents=show_toc,
        # Add helper functions
        ordinal=_ordinal_number,
    )

    # Render using spellbook template
    return template_engine.render_template("spellbook.tex.j2", template_context)


def _ordinal_number(n: int) -> str:
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
    if 10 <= n <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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
            rprint(f"[green]✓[/green] PDF compiled successfully: {result.output_file}")
        else:
            rprint(
                f"[red]LaTeX compilation failed:[/red] {result.error_message or 'Unknown error'}"
            )

    except Exception as e:
        rprint(f"[red]LaTeX compilation failed:[/red] {e}")
        if "not found" in str(e).lower():
            rprint("[yellow]Install LaTeX to compile PDFs:[/yellow]")
            rprint("On macOS: brew install --cask mactex")
            rprint("On Ubuntu: sudo apt-get install texlive-full")
