"""Convert command for 5e2pdf CLI."""

import asyncio
import json
import os
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
    get_justified_default,
    get_no_outline_default,
    get_paper_size_default,
    get_two_column_default,
    get_with_creatures_default,
    get_with_images_default,
    get_with_index_default,
    get_with_items_default,
)
from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer, get_tag_resolver
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler

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

    if content_type == ContentType.ADVENTURE:
        result = resolver.resolve_adventure(content_source)
    elif content_type == ContentType.BOOK:
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

    if content_type == ContentType.ADVENTURE:
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

    elif content_type == ContentType.BOOK:
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
    paper_size: str | None = typer.Option(
        None, "--paper-size", help="Paper size (letterpaper, a4paper, a5paper)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str = typer.Option(
        get_font_size_default(), "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        get_background_default(),
        "--background",
        "--bg",
        help="Background style (print, none, full)",
    ),
    two_column: bool = typer.Option(
        get_two_column_default(),
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool = typer.Option(
        get_justified_default(),
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
                content_source, ContentType.ADVENTURE
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

            # Create LaTeX configuration from unified config
            app_config = get_app_config()
            actual_paper_size = (
                paper_size or app_config.rendering.latex.document.paper_size
            )
            actual_fonts = fonts or app_config.rendering.latex.document.fonts
            actual_no_outline = no_outline  # Boolean option uses direct value

            # Import legacy config classes for backward compatibility
            from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=actual_paper_size,
                font_size=font_size,
                background=background,
                two_column=two_column,
                justified_text=justified,
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
    paper_size: str | None = typer.Option(
        None, "--paper-size", help="Paper size (letterpaper, a4paper, a5paper)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str = typer.Option(
        get_font_size_default(), "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        get_background_default(),
        "--background",
        "--bg",
        help="Background style (print, none, full)",
    ),
    two_column: bool = typer.Option(
        get_two_column_default(),
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool = typer.Option(
        get_justified_default(),
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
                content_source, ContentType.BOOK
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

            # Create LaTeX configuration from unified config
            app_config = get_app_config()
            actual_paper_size = (
                paper_size or app_config.rendering.latex.document.paper_size
            )
            actual_fonts = fonts or app_config.rendering.latex.document.fonts
            actual_no_outline = no_outline  # Boolean option uses direct value

            # Import legacy config classes for backward compatibility
            from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=actual_paper_size,
                font_size=font_size,
                background=background,
                two_column=two_column,
                justified_text=justified,
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
    paper_size: str | None = typer.Option(
        None, "--paper-size", help="Paper size (letterpaper, a4paper, a5paper)"
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(), "--fonts", help="Font package to use (wotc, dmsguild)"
    ),
    no_outline: bool = typer.Option(
        get_no_outline_default(), "--no-outline", help="Disable document outline"
    ),
    font_size: str = typer.Option(
        get_font_size_default(), "--font-size", help="Base font size (10pt, 11pt, 12pt)"
    ),
    background: str | None = typer.Option(
        get_background_default(),
        "--background",
        "--bg",
        help="Background style (print, none, full)",
    ),
    two_column: bool = typer.Option(
        get_two_column_default(),
        "--two-column/--one-column",
        help="Use two-column layout",
    ),
    justified: bool = typer.Option(
        get_justified_default(),
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

            # Create LaTeX configuration from unified config
            app_config = get_app_config()
            actual_paper_size = (
                paper_size or app_config.rendering.latex.document.paper_size
            )
            actual_fonts = fonts or app_config.rendering.latex.document.fonts
            actual_no_outline = no_outline  # Boolean option uses direct value

            # Import legacy config classes for backward compatibility
            from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=actual_paper_size,
                font_size=font_size,
                background=background,
                two_column=two_column,
                justified_text=justified,
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
                            mixed_requests.append((abbrev, ContentType.BOOK))
                        else:
                            mixed_requests.append((abbrev, ContentType.ADVENTURE))
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
