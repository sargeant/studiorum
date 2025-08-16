"""Cache management commands for the 5e2pdf CLI."""

import os
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.prompt import Confirm
from rich.table import Table

from dnd5e.cli.display_manager import display_manager
from dnd5e.core.cache import CacheManager

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
            "\n[yellow]💡 Recommendation:[/yellow] Cache is nearly full. Consider running [cyan]5e2pdf cache clear[/cyan] to free space."
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


@app.command()
def doctor() -> None:
    """Check cache health and provide recommendations."""

    console.print("[bold]🔍 Cache Health Check[/bold]\n")

    checks = []

    # Check 1: Directory exists and is writable
    try:
        cache = CacheManager.get_instance()
        cache_dir = Path(cache.directory)

        if cache_dir.exists() and cache_dir.is_dir():
            if os.access(cache_dir, os.W_OK):
                checks.append(
                    (
                        "Directory Access",
                        "✅",
                        "Cache directory is accessible and writable",
                    )
                )
            else:
                checks.append(
                    (
                        "Directory Access",
                        "❌",
                        f"Cache directory is not writable: {cache_dir}",
                    )
                )
        else:
            checks.append(
                (
                    "Directory Access",
                    "❌",
                    f"Cache directory does not exist: {cache_dir}",
                )
            )
    except Exception as e:
        checks.append(("Directory Access", "❌", f"Error accessing cache: {e}"))

    # Check 2: Database integrity
    try:
        stats = CacheManager.get_stats()
        entries = stats["total_entries"]
        checks.append(
            (
                "Database Integrity",
                "✅",
                f"Cache database is healthy ({entries:,} entries)",
            )
        )
    except Exception as e:
        checks.append(("Database Integrity", "❌", f"Cache database error: {e}"))

    # Check 3: Disk usage
    try:
        stats = CacheManager.get_stats()
        usage_pct = stats["total_size_mb"] / stats["max_size_mb"] * 100

        if usage_pct > 90:
            checks.append(
                (
                    "Disk Usage",
                    "⚠️",
                    f"Cache is {usage_pct:.1f}% full - consider clearing",
                )
            )
        elif usage_pct > 70:
            checks.append(
                ("Disk Usage", "⚠️", f"Cache is {usage_pct:.1f}% full - monitor usage")
            )
        else:
            checks.append(
                ("Disk Usage", "✅", f"Cache usage is healthy ({usage_pct:.1f}%)")
            )
    except Exception as e:
        checks.append(("Disk Usage", "❌", f"Could not check disk usage: {e}"))

    # Display results
    table = Table(title="Health Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for check_name, status, details in checks:
        table.add_row(check_name, status, details)

    console.print(table)

    # Recommendations
    error_count = sum(1 for _, status, _ in checks if status == "❌")
    warning_count = sum(1 for _, status, _ in checks if status == "⚠️")

    if error_count > 0:
        console.print(
            f"\n[red]❌ {error_count} error(s) found. Cache may not be working properly.[/red]"
        )
    elif warning_count > 0:
        console.print(
            f"\n[yellow]⚠️ {warning_count} warning(s) found. Consider taking action.[/yellow]"
        )
    else:
        console.print("\n[green]✅ All checks passed! Cache is healthy.[/green]")
