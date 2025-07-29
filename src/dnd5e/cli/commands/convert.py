"""Convert command for 5e2pdf CLI."""

import asyncio
import json
import subprocess
from pathlib import Path

import aiofiles
import typer
from rich import print as rprint

from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer, get_tag_resolver
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer

app: typer.Typer = typer.Typer(help="Convert D&D content to LaTeX/PDF")
console = display_manager.console


async def resolve_content_or_file(
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
        return await _load_from_file(file_path, content_type)

    # Special case: for known book abbreviations, try direct file loading first
    # This ensures we get the full content including entries
    if content_type == ContentType.BOOK and content_source.lower() == "phb":
        phb_file_path = Path("/Users/sam/Code/5etools-src/data/book/book-phb.json")
        if phb_file_path.is_file():
            return await _load_from_file(phb_file_path, content_type)

    # Otherwise, treat as content abbreviation
    omnidexer = await get_omnidexer()
    resolver = ContentResolver(omnidexer)

    if content_type == ContentType.ADVENTURE:
        result = resolver.resolve_adventure(content_source)
    elif content_type == ContentType.BOOK:
        result = resolver.resolve_book(content_source)
    else:
        result = resolver.resolve_any(content_source, content_type)

    return await _handle_resolution_result(result, content_source, content_type)


async def _load_from_file(
    file_path: Path, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Load content from a JSON file."""
    async with aiofiles.open(file_path) as f:
        content = await f.read()
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
        from dnd5e.core.models.books import Book, BookChapter
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
                chapter = BookChapter(
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


async def _handle_resolution_result(
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
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    with_items: bool = typer.Option(
        True, "--items/--no-items", help="Include item lists"
    ),
    with_creatures: bool = typer.Option(
        True, "--creatures/--no-creatures", help="Include creature lists"
    ),
    compile_pdf: bool = typer.Option(
        False, "--pdf", help="Compile to PDF after conversion"
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

    async def _convert() -> None:
        try:
            # Resolve content source (file or abbreviation)
            content_items, source_desc = await resolve_content_or_file(
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
                omnidexer = await get_omnidexer()
                tag_resolver = await get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Create document metadata for adventure
            from ...core.models.document_metadata import DocumentMetadata, DocumentType

            metadata = DocumentMetadata(
                title=title or f"Adventure: {content_items[0].name}",
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
            context = RenderContext(
                title=title or f"Adventure: {content_items[0].name}",
                include_images=with_images,
                include_toc=True,
                include_items=with_items,
                include_creatures=with_creatures,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata=metadata,
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
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            rprint(
                f"[green]✓[/green] Adventure converted ({source_desc}): {output_path}"
            )

            # Compile PDF if requested
            if compile_pdf:
                await _compile_pdf(output_path)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_convert())


@app.command("book")
def convert_book(
    content_source: str = typer.Argument(
        ..., help="Book abbreviation (e.g., 'phb') or file path"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    with_index: bool = typer.Option(True, "--index/--no-index", help="Include index"),
    compile_pdf: bool = typer.Option(
        False, "--pdf", help="Compile to PDF after conversion"
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

    async def _convert() -> None:
        try:
            # Resolve content source (file or abbreviation)
            content_items, source_desc = await resolve_content_or_file(
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
                omnidexer = await get_omnidexer()
                tag_resolver = await get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

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
            context = RenderContext(
                title=title or f"Book: {book_title}",
                include_images=with_images,
                include_toc=True,
                include_index=with_index,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
                metadata=metadata,
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
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            rprint(f"[green]✓[/green] Book converted ({source_desc}): {output_path}")

            # Compile PDF if requested
            if compile_pdf:
                await _compile_pdf(output_path)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_convert())


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
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    compile_pdf: bool = typer.Option(
        False, "--pdf", help="Compile to PDF after conversion"
    ),
) -> None:
    """
    📄 Convert supplement JSON to LaTeX

    Converts various D&D content (spells, creatures, items) from 5e.tools JSON
    format into a formatted supplement document.
    """

    async def _convert() -> None:
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
                omnidexer = await get_omnidexer()
                tag_resolver = await get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Load supplement content
            async with aiofiles.open(input_file) as f:
                content = await f.read()
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

            # Create render context
            context = RenderContext(
                title=title
                or f"Supplement: {input_file.stem.replace('-', ' ').title()}",
                include_images=with_images,
                include_toc=len(content_items) > 10,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
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
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            rprint(
                f"[green]✓[/green] Supplement converted ({len(content_items)} items): {output_path}"
            )

            # Compile PDF if requested
            if compile_pdf:
                await _compile_pdf(output_path)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_convert())


async def _compile_pdf(latex_path: Path) -> None:
    """Compile LaTeX to PDF using xelatex."""

    pdf_path = latex_path.with_suffix(".pdf")
    rprint(f"[cyan]Compiling PDF: {pdf_path}[/cyan]")

    try:
        with display_manager.progress("Compiling PDF") as _:
            compile_task = display_manager.add_task(
                "[cyan]Running xelatex...", total=None
            )
            subprocess.run(
                [
                    "xelatex",
                    "-output-directory",
                    str(latex_path.parent),
                    "-interaction=nonstopmode",
                    str(latex_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            display_manager.update_task(compile_task, completed=100)

        rprint(f"[green]✓[/green] PDF compiled successfully: {pdf_path}")

    except subprocess.CalledProcessError as e:
        rprint("[red]LaTeX compilation failed:[/red]")
        rprint(f"[dim]{e.stderr}[/dim]")

    except FileNotFoundError:
        rprint(
            "[yellow]Warning:[/yellow] xelatex not found. Install LaTeX to compile PDFs."
        )
        rprint("On macOS: brew install --cask mactex")
        rprint("On Ubuntu: sudo apt-get install texlive-xetex")
