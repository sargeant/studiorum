"""convert bulk: several adventures or books, one .tex file each."""

from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager
from studiorum.core.models.adventures import Adventure
from studiorum.core.models.content import ContentType
from studiorum.core.models.document_metadata import DocumentType
from studiorum.core.resolvers import ContentResolver
from studiorum.latex_engine.document import render_document

from . import options as opt
from .adventure import rendering_context
from .options import ConvertOptions
from .run import compile_pdf, conversion_errors, document_metadata


def bulk(
    ctx: typer.Context,
    content_list: Annotated[
        list[str], typer.Argument(help="List of adventure/book abbreviations")
    ],
    content_type: Annotated[
        str, typer.Option("--type", help="Content type (adventure, book, mixed)")
    ] = "adventure",
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-d", help="Output directory")
    ] = Path("output/bulk"),
    # Shared options, read through ctx.params by ConvertOptions
    pdf: opt.Pdf = None,
    toc: opt.Toc = None,
    index: opt.Index = None,
    images: opt.Images = None,
    document_class: opt.DocumentClass = None,
    paper: opt.Paper = None,
    two_column: opt.TwoColumn = None,
    justified: opt.Justified = None,
    fonts: opt.Fonts = None,
    font_size: opt.FontSize = None,
    background: opt.Background = None,
    outline: opt.Outline = None,
    high_contrast: opt.HighContrast = None,
    statblock: opt.Statblock = None,
) -> None:
    """
    ⚡ Convert several adventures or books, one .tex file each

    \\b
    Examples:
      studiorum convert bulk cos lmop hotdq --type adventure
      studiorum convert bulk phb mm dmg --type book
      studiorum convert bulk cos phb mm --type mixed
    """
    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        with display_manager.progress("Initializing") as _:
            task = display_manager.add_task("[cyan]Loading content data...", total=None)
            omnidexer = get_services().omnidexer
            resolver = ContentResolver(omnidexer)
            display_manager.update_task(task, completed=100)

        if content_type == "adventure":
            results = resolver.resolve_adventures_bulk(content_list)
        elif content_type == "book":
            results = resolver.resolve_books_bulk(content_list)
        elif content_type == "mixed":
            # A book's id, like PHB, marks it as a book; anything else is an adventure
            books = {
                str(book_id).lower()
                for book in omnidexer.get_all_by_type(ContentType.BOOK)
                if (book_id := getattr(book, "id", None))
            }
            results = resolver.resolve_multiple(
                [
                    (
                        a,
                        ContentType.BOOK
                        if a.lower() in books
                        else ContentType.ADVENTURE,
                    )
                    for a in content_list
                ]
            )
        else:
            rprint(f"[red]Error:[/red] Invalid content type: {content_type}")
            raise typer.Exit(1)

        for result in results:
            if not result.is_success:
                rprint(
                    f"[yellow]Warning:[/yellow] {result.query}: {result.status.value}"
                )
                if result.suggestions:
                    rprint(f"    Suggestions: {', '.join(result.suggestions[:3])}")
        resolved = [r for r in results if r.is_success and r.content]
        if not resolved:
            rprint("[red]Error:[/red] No content could be resolved")
            raise typer.Exit(1)

        output_dir.mkdir(parents=True, exist_ok=True)
        converted: list[str] = []
        failed: list[str] = []
        with display_manager.progress("Converting content") as _:
            task = display_manager.add_task(
                f"[green]Converting {len(resolved)} items...", total=len(resolved)
            )
            for result in resolved:
                content = result.content
                if content is None:
                    continue
                try:
                    kind = (
                        DocumentType.ADVENTURE
                        if isinstance(content, Adventure)
                        else DocumentType.BOOK
                    )
                    latex = render_document(
                        [content],
                        rendering_context(options, None),
                        document_metadata(options, content.name, kind),
                        latex_config=options.latex,
                    )
                    output_path = output_dir / f"{result.query}.tex"
                    output_path.write_text(latex, encoding="utf-8")
                    if options.compile_pdf:
                        compile_pdf(output_path)
                    converted.append(result.query)
                except Exception as e:
                    rprint(f"[red]Error converting {result.query}:[/red] {e}")
                    failed.append(result.query)
                display_manager.update_task(task, advance=1)

        rprint("\n[green]✓[/green] Bulk conversion completed:")
        rprint(f"  • Successfully converted: {len(converted)} items")
        if failed:
            rprint(f"  • Failed conversions: {len(failed)} items")
        rprint(f"  • Output directory: {output_dir}")
        for heading, names, mark in (
            ("[green]Successfully converted:[/green]", converted, "✓"),
            ("[red]Failed to convert:[/red]", failed, "✗"),
        ):
            if names:
                rprint(f"\n{heading}")
                for name in names:
                    rprint(f"  {mark} {name}")
