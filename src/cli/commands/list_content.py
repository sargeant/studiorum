"""List command for 5e2pdf CLI."""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint

from src.core.loaders.omnidexer import Omnidexer
from src.core.models.content import ContentType

app = typer.Typer(help="List available D&D content")
console = Console()


@app.command("files")
def list_files(
    directory: Optional[Path] = typer.Option(None, "--dir", "-d", help="Directory to scan"),
    pattern: str = typer.Option("*.json", "--pattern", "-p", help="File pattern to match"),
):
    """
    📁 List available JSON files
    
    Shows all JSON files available for conversion in the specified directory
    or default data directories.
    """
    if directory is None:
        # Default directories
        directories = [
            Path("json_data/adventures"),
            Path("json_data/books"), 
            Path("json_data/supplements"),
            Path("data/adventure"),
            Path("data/book"),
            Path("homebrew")
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
        rprint("Make sure you have cloned the 5etools-src repository and created symlinks:")
        rprint("  ln -s ../5etools-src/data data")
    else:
        console.print(table)
        rprint(f"\n[dim]Found {total_files} files[/dim]")


@app.command("content")
def list_content(
    content_type: Optional[str] = typer.Option(None, "--type", "-t", 
                                              help="Content type (spell, creature, item, etc.)"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source book"),
    limit: int = typer.Option(20, "--limit", "-l", help="Limit number of results"),
    search: Optional[str] = typer.Option(None, "--search", help="Search content names"),
):
    """
    📋 List loaded content items
    
    Shows content that has been loaded into the omnidexer system.
    Useful for finding specific spells, creatures, items, etc.
    """
    async def _list_content():
        try:
            # Load omnidexer
            with Progress() as progress:
                load_task = progress.add_task("[cyan]Loading content data...", total=None)
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                progress.update(load_task, completed=100)
            
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
                stats = omnidexer.get_statistics()
                content_items = []
                for ct in ContentType:
                    content_items.extend(omnidexer.get_all_by_type(ct))
            
            # Apply filters
            if source:
                content_items = [item for item in content_items 
                               if item.source.abbreviation.lower() == source.lower()]
            
            if search:
                search_lower = search.lower()
                content_items = [item for item in content_items 
                               if search_lower in item.name.lower()]
            
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
                    item.name,
                    content_type_val.title(),
                    str(item.source),
                    details
                )
            
            console.print(table)
            
            if len(content_items) == limit:
                rprint(f"\n[dim]Showing first {limit} results. Use --limit to see more.[/dim]")
                
        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_list_content())


@app.command("sources")
def list_sources():
    """
    📚 List available source books
    
    Shows all source books that have content loaded in the system.
    """
    async def _list_sources():
        try:
            # Load omnidexer
            with Progress() as progress:
                load_task = progress.add_task("[cyan]Loading content data...", total=None)
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                progress.update(load_task, completed=100)
            
            # Get statistics
            stats = omnidexer.get_statistics()
            
            if 'by_source' not in stats:
                rprint("[yellow]No source information available[/yellow]")
                return
            
            # Display sources
            table = Table(title="📚 Available Sources")
            table.add_column("Abbreviation", style="cyan")
            table.add_column("Content Count", justify="right", style="green")
            
            for source, count in sorted(stats['by_source'].items()):
                table.add_row(source, str(count))
            
            console.print(table)
            rprint(f"\n[dim]Total sources: {len(stats['by_source'])}[/dim]")
            
        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_list_sources())


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _get_content_details(item) -> str:
    """Get brief details about a content item."""
    from src.core.models.spells import Spell
    from src.core.models.creatures import Creature
    from src.core.models.items import Item
    
    if isinstance(item, Spell):
        return f"Level {item.level} {item.school}"
    elif isinstance(item, Creature):
        size = item.size[0] if item.size else "Medium"
        cr = getattr(item, 'cr', 'Unknown')
        return f"{size}, CR {cr}"
    elif isinstance(item, Item):
        item_type = getattr(item, 'type', 'Item')
        rarity = getattr(item, 'rarity', None)
        if rarity:
            return f"{item_type}, {rarity}"
        return item_type
    else:
        return ""