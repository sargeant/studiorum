"""Cache management commands for the studiorum CLI."""

import typer
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.prompt import Confirm

from studiorum.cli.display_manager import display_manager
from studiorum.core.cache import CacheManager

app = typer.Typer(help="Manage disk cache")
console = display_manager.console


@app.command()
def show() -> None:
    """Show disk cache information and statistics."""

    # Get cache stats
    stats = CacheManager.get_stats()

    # Overview Panel
    size_mb = stats["total_size_mb"]
    max_mb = stats["max_size_mb"]
    usage_pct = (size_mb / max_mb * 100) if max_mb > 0 else 0

    overview = f"""[green]Cache Directory:[/green] {stats["cache_dir"]}
[green]Current Size:[/green] {size_mb:.1f} MB
[green]Size Limit:[/green] {max_mb:.0f} MB
[green]Usage:[/green] {usage_pct:.1f}%
[green]Total Entries:[/green] {stats["total_entries"]:,}"""

    console.print(Panel(overview, title="🗄️  Disk Cache", border_style="blue"))

    # Usage bar
    progress = Progress(
        TextColumn("[bold blue]Disk Usage"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed:.1f}/{task.total:.0f} MB"),
        console=console,
    )

    with progress:
        progress.add_task("", completed=size_mb, total=max_mb)
        console.print("")  # Simple spacing instead of tasks table

    # Recommendations
    if usage_pct > 80:
        console.print(
            "\n[yellow]💡 Recommendation:[/yellow] Cache is nearly full. Consider running [cyan]studiorum cache clear[/cyan] to free space."
        )
    elif usage_pct < 10:
        console.print(
            "\n[green]✨ Status:[/green] Cache has plenty of space available."
        )


@app.command()
def clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Clear the disk cache."""

    # Get current stats
    stats = CacheManager.get_stats()
    size_mb = stats["total_size_mb"]
    entries = stats["total_entries"]

    if size_mb == 0:
        console.print("[yellow]Cache is already empty.[/yellow]")
        return

    # Show what will be cleared
    console.print("[yellow]This will clear:[/yellow]")
    console.print(f"  • {entries:,} cached entries")
    console.print(f"  • {size_mb:.1f} MB disk space")
    console.print(f"  • Directory: {stats['cache_dir']}")

    # Confirmation
    if not yes:
        if not Confirm.ask("\n[red]Are you sure you want to clear the cache?[/red]"):
            console.print("[dim]Cache clearing cancelled.[/dim]")
            return

    # Clear with progress
    with console.status("[bold green]Clearing cache..."):
        CacheManager.clear()

    # Report results
    console.print("[green]✅ Cache cleared successfully![/green]")
    console.print(f"[dim]Freed {size_mb:.1f} MB of disk space[/dim]")
