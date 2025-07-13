"""Convert command for 5e2pdf CLI."""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress

from src.core.indexer.tag_resolver import TagResolver
from src.core.loaders.omnidexer import Omnidexer
from src.renderers.base import RenderContext
from src.renderers.latex import LaTeXDocumentRenderer

app = typer.Typer(help="Convert D&D content to LaTeX/PDF")
console = Console()


@app.command("adventure")
def convert_adventure(
    input_file: Path = typer.Argument(..., help="Adventure JSON file"),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Document title"),
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
):
    """
    📖 Convert adventure JSON to LaTeX

    Converts a D&D adventure from 5e.tools JSON format into a beautifully
    formatted LaTeX document matching official book styling.
    """

    async def _convert():
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Adventure file not found: {input_file}")
                raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                output_path = (
                    Path("output/adventures") / input_file.with_suffix(".tex").name
                )
            else:
                output_path = output_file

            # Load omnidexer and tag resolver
            with Progress() as progress:
                load_task = progress.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                tag_resolver = TagResolver(omnidexer)
                progress.update(load_task, completed=100)

            # Load adventure content
            import json

            with open(input_file) as f:
                adventure_data = json.load(f)

            # Parse adventure
            from src.core.models.adventures import Adventure

            # Get adventure data (could be nested)
            if "adventure" in adventure_data:
                adventure_items = adventure_data["adventure"]
            else:
                adventure_items = [adventure_data]

            content_items = []
            for item in adventure_items:
                if isinstance(item, dict):
                    content_items.append(Adventure.model_validate(item))

            if not content_items:
                rprint("[red]Error:[/red] No valid adventure content found")
                raise typer.Exit(1)

            # Create render context
            context = RenderContext(
                title=title or f"Adventure: {content_items[0].name}",
                include_images=with_images,
                include_toc=True,
                include_items=with_items,
                include_creatures=with_creatures,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with Progress() as progress:
                render_task = progress.add_task(
                    "[green]Rendering adventure...", total=None
                )
                result = renderer.render_document(content_items, context)
                progress.update(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result, encoding="utf-8")

            rprint(f"[green]✓[/green] Adventure converted: {output_path}")

            # Compile PDF if requested
            if compile_pdf:
                await _compile_pdf(output_path)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_convert())


@app.command("book")
def convert_book(
    input_file: Path = typer.Argument(..., help="Book JSON file"),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Document title"),
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    with_index: bool = typer.Option(True, "--index/--no-index", help="Include index"),
    compile_pdf: bool = typer.Option(
        False, "--pdf", help="Compile to PDF after conversion"
    ),
):
    """
    📚 Convert book JSON to LaTeX

    Converts a D&D sourcebook from 5e.tools JSON format into a beautifully
    formatted LaTeX document matching official book styling.
    """

    async def _convert():
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Book file not found: {input_file}")
                raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                output_path = Path("output/books") / input_file.with_suffix(".tex").name
            else:
                output_path = output_file

            # Load omnidexer and tag resolver
            with Progress() as progress:
                load_task = progress.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                tag_resolver = TagResolver(omnidexer)
                progress.update(load_task, completed=100)

            # Load book content
            import json

            with open(input_file) as f:
                book_data = json.load(f)

            # Parse book
            from src.core.models.books import Book, BookChapter

            # Extract book metadata from filename if available
            book_id = input_file.stem.replace("book-", "").upper()
            book_name = title or f"Book: {book_id}"

            # Get book content sections
            book_sections = []
            if "data" in book_data:
                book_sections = book_data["data"]
            elif "book" in book_data:
                book_sections = book_data["book"]
            else:
                book_sections = [book_data] if isinstance(book_data, dict) else []

            # Convert sections to chapters
            chapters = []
            for section in book_sections:
                if isinstance(section, dict) and section.get("type") == "section":
                    chapter = BookChapter(
                        name=section.get("name", "Untitled Chapter"),
                        entries=section.get("entries", []),
                    )
                    chapters.append(chapter)

            # Create a complete book object
            book = Book(
                name=book_name,
                source={"abbreviation": book_id},
                id=book_id,
                contents=chapters,
            )

            content_items = [book]

            if not content_items:
                rprint("[red]Error:[/red] No valid book content found")
                raise typer.Exit(1)

            # Create render context
            context = RenderContext(
                title=title or f"Book: {content_items[0].name}",
                include_images=with_images,
                include_toc=True,
                include_index=with_index,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver,
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with Progress() as progress:
                render_task = progress.add_task("[green]Rendering book...", total=None)
                result = renderer.render_document(content_items, context)
                progress.update(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result, encoding="utf-8")

            rprint(f"[green]✓[/green] Book converted: {output_path}")

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
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Document title"),
    content_types: List[str] = typer.Option(
        ["all"], "--type", help="Content types to include"
    ),
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    compile_pdf: bool = typer.Option(
        False, "--pdf", help="Compile to PDF after conversion"
    ),
):
    """
    📄 Convert supplement JSON to LaTeX

    Converts various D&D content (spells, creatures, items) from 5e.tools JSON
    format into a formatted supplement document.
    """

    async def _convert():
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
            with Progress() as progress:
                load_task = progress.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                tag_resolver = TagResolver(omnidexer)
                progress.update(load_task, completed=100)

            # Load supplement content
            import json

            with open(input_file) as f:
                supplement_data = json.load(f)

            # Parse various content types
            content_items = []

            # Import models
            from src.core.models.creatures import Creature
            from src.core.models.items import Item
            from src.core.models.spells import Spell

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
                                    model_class.model_validate(item_data)
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
            with Progress() as progress:
                render_task = progress.add_task(
                    "[green]Rendering supplement...", total=None
                )
                result = renderer.render_document(content_items, context)
                progress.update(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result, encoding="utf-8")

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


async def _compile_pdf(latex_path: Path):
    """Compile LaTeX to PDF using xelatex."""
    import subprocess

    pdf_path = latex_path.with_suffix(".pdf")
    rprint(f"[cyan]Compiling PDF: {pdf_path}[/cyan]")

    try:
        with Progress() as progress:
            compile_task = progress.add_task("[cyan]Running xelatex...", total=None)
            result = subprocess.run(
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
            progress.update(compile_task, completed=100)

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
