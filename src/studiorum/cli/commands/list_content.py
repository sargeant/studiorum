"""List command for 5e2pdf CLI."""

from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.table import Table

from studiorum.cli.display_manager import display_manager
from studiorum.cli.utils import get_omnidexer
from studiorum.core.models.content import ContentType

app: typer.Typer = typer.Typer(help="List available D&D content")
console = display_manager.console

# Constants for formatting
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024


@app.command("files")
def list_files(
    directory: Path | None = typer.Option(
        None, "--dir", "-d", help="Directory to scan"
    ),
    pattern: str = typer.Option(
        "*.json", "--pattern", "-p", help="File pattern to match"
    ),
) -> None:
    """
    📁 List available JSON files

    Shows all JSON files available for conversion in the specified directory
    or default data directories.
    """
    if directory is None:
        # Default directories
        directories = [
            Path("srd-data/adventure"),
            Path("srd-data/book"),
            Path("homebrew"),
        ]
    else:
        directories = [directory]

    table = Table(title="📁 Available JSON Files")
    table.add_column("Type", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Size", justify="right", style="blue")

    total_files = 0

    for dir_path in directories:
        if dir_path.exists():
            files = list(dir_path.glob(pattern))
            for file_path in sorted(files):
                file_type = dir_path.name.title()
                file_size = file_path.stat().st_size
                size_str = _format_file_size(file_size)
                table.add_row(file_type, str(file_path), size_str)
                total_files += 1

    if total_files == 0:
        rprint("[yellow]No JSON files found in search directories[/yellow]")
        rprint("Make sure you have SRD data available. Run the extraction script:")
        rprint("  python extract_srd_content.py")
    else:
        console.print(table)
        rprint(f"\n[dim]Found {total_files} files[/dim]")


@app.command("content")
def list_content(
    content_type: str | None = typer.Option(
        None, "--type", "-t", help="Content type (spell, creature, item, etc.)"
    ),
    source: str | None = typer.Option(
        None, "--source", "-s", help="Filter by source book"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Limit number of results"),
    search: str | None = typer.Option(None, "--search", help="Search content names"),
) -> None:
    """
    📋 List loaded content items

    Shows content that has been loaded into the omnidexer system.
    Useful for finding specific spells, creatures, items, etc.
    """

    def _list_content() -> None:
        try:
            # Load omnidexer (get_omnidexer handles its own progress display)
            omnidexer = get_omnidexer()

            # Filter content
            if content_type:
                try:
                    ct = ContentType(content_type.lower())
                    content_items = omnidexer.get_all_by_type(ct)
                except ValueError:
                    rprint(f"[red]Error:[/red] Unknown content type: {content_type}")
                    rprint("Available types: spell, creature, item, adventure, book")
                    raise typer.Exit(1)
            else:
                # Get all content
                omnidexer.get_statistics()
                content_items = []
                for ct in ContentType:
                    content_items.extend(omnidexer.get_all_by_type(ct))

            # Apply filters
            if source:
                content_items = [
                    item
                    for item in content_items
                    if item.source.abbreviation.lower() == source.lower()
                ]

            if search:
                search_lower = search.lower()
                content_items = [
                    item for item in content_items if search_lower in item.name.lower()
                ]

            # Sort and limit
            content_items = sorted(content_items, key=lambda x: x.name)[:limit]

            if not content_items:
                rprint("[yellow]No content found matching criteria[/yellow]")
                return

            # Display results
            table = Table(title=f"📋 Content Items ({len(content_items)} shown)")
            table.add_column("Name", style="green")
            table.add_column("Type", style="cyan")
            table.add_column("Source", style="blue")
            table.add_column("Details", style="dim")

            for item in content_items:
                content_type_val = ContentType.from_content(item).value
                details = _get_content_details(item)
                table.add_row(
                    item.name, content_type_val.title(), str(item.source), details
                )

            console.print(table)

            if len(content_items) == limit:
                rprint(
                    f"\n[dim]Showing first {limit} results. Use --limit to see more.[/dim]"
                )

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _list_content()


@app.command("sources")
def list_sources() -> None:
    """
    📚 List available source books

    Shows all source books that have content loaded in the system.
    """

    def _list_sources() -> None:
        try:
            # Load omnidexer (get_omnidexer handles its own progress display)
            omnidexer = get_omnidexer()

            # Get statistics
            stats = omnidexer.get_statistics()

            if "by_source" not in stats:
                rprint("[yellow]No source information available[/yellow]")
                return

            # Display sources
            table = Table(title="📚 Available Sources")
            table.add_column("Abbreviation", style="cyan")
            table.add_column("Content Count", justify="right", style="green")

            for source, count in sorted(stats["by_source"].items()):
                table.add_row(source, str(count))

            console.print(table)
            rprint(f"\n[dim]Total sources: {len(stats['by_source'])}[/dim]")

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _list_sources()


@app.command("adventures")
def list_adventures() -> None:
    """
    📖 List all available adventures

    Shows all adventures loaded in the system with their abbreviations,
    making it easy to use them with convert commands.
    """

    def _list_adventures() -> None:
        try:
            # Load omnidexer (get_omnidexer handles its own progress display)
            omnidexer = get_omnidexer()

            # Get all adventures
            adventures = omnidexer.get_all_by_type(ContentType("adventure"))

            if not adventures:
                rprint("[yellow]No adventures found in the system[/yellow]")
                rprint("Make sure adventure data is loaded properly.")
                return

            # Display adventures table
            table = Table(title=f"📖 Available Adventures ({len(adventures)})")
            table.add_column("Abbreviation", style="cyan", min_width=8)
            table.add_column("Name", style="green")
            table.add_column("Source", style="blue")

            for adventure in sorted(
                adventures, key=lambda x: x.source.abbreviation.lower()
            ):
                abbrev = adventure.source.abbreviation.lower()
                name = adventure.name
                source = adventure.source.name
                table.add_row(abbrev, name, source)

            console.print(table)
            rprint("\n[dim]Use: 5e2pdf convert adventure <abbreviation>[/dim]")

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _list_adventures()


@app.command("books")
def list_books() -> None:
    """
    📚 List all available books

    Shows all books loaded in the system with their abbreviations,
    making it easy to use them with convert commands.
    """

    def _list_books() -> None:
        try:
            # Load omnidexer (get_omnidexer handles its own progress display)
            omnidexer = get_omnidexer()

            # Get all books
            books = omnidexer.get_all_by_type(ContentType("book"))

            if not books:
                rprint("[yellow]No books found in the system[/yellow]")
                rprint("Make sure book data is loaded properly.")
                return

            # Display books table
            table = Table(title=f"📚 Available Books ({len(books)})")
            table.add_column("Abbreviation", style="cyan", min_width=8)
            table.add_column("Name", style="green")
            table.add_column("Source", style="blue")

            for book in sorted(books, key=lambda x: x.source.abbreviation.lower()):
                abbrev = book.source.abbreviation.lower()
                name = book.name
                source = book.source.name
                table.add_row(abbrev, name, source)

            console.print(table)
            rprint("\n[dim]Use: 5e2pdf convert book <abbreviation>[/dim]")

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _list_books()


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.1f} KB"
    else:
        return f"{size_bytes / BYTES_PER_MB:.1f} MB"


def _get_content_details(item: Any) -> str:
    """Get brief details about a content item."""
    from studiorum.core.models.creatures import Creature
    from studiorum.core.models.items import Item
    from studiorum.core.models.spells import Spell

    if isinstance(item, Spell):
        return f"Level {item.level} {item.school}"
    elif isinstance(item, Creature):
        size = item.size[0] if item.size else "Medium"
        cr = getattr(item, "cr", "Unknown")
        return f"{size}, CR {cr}"
    elif isinstance(item, Item):
        item_type = getattr(item, "type", "Item")
        rarity = getattr(item, "rarity", None)
        if rarity:
            return f"{item_type}, {rarity}"
        return item_type
    else:
        return ""
