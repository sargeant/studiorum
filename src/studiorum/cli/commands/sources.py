"""DEPRECATED CLI commands for source management.

These commands are deprecated in favor of the new 'data' command group.
They continue to work for backward compatibility but will be removed in a future version.

Migration Guide:
- studiorum sources list    → studiorum data list
- studiorum sources add     → studiorum data add-homebrew
- studiorum sources remove  → studiorum data remove
- studiorum sources scan    → studiorum data scan
- studiorum sources update  → studiorum data scan
- studiorum sources info    → studiorum data status

Use 'studiorum data --help' for information about the new commands.
"""

import asyncio
import warnings
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from studiorum.cli.display_manager import display_manager
from studiorum.core.config.sources import (
    ContentSource,
    SourceType,
    get_config_manager,
    get_content_config,
)
from studiorum.core.sources import ContentSourceManager

console = display_manager.console

# Issue deprecation warning at module level
warnings.warn(
    "The 'sources' command is deprecated. Use 'data' command instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Update help text to indicate deprecation
app: typer.Typer = typer.Typer(
    help="""
[red]DEPRECATED[/red]: Source management commands.

⚠️  These commands are deprecated. Use 'studiorum data' instead:
  • sources list    → data list
  • sources add     → data add-homebrew
  • sources remove  → data remove
  • sources scan    → data scan
  • sources update  → data scan
  • sources info    → data status

This command group will be removed in a future version.
"""
)


def show_deprecation_warning(new_command: str) -> None:
    """Show deprecation warning with migration guidance."""
    console.print("[yellow]⚠️  DEPRECATION WARNING[/yellow]")
    console.print(f"The 'sources' command is deprecated. Use '{new_command}' instead.")
    console.print("Migration guide:")
    console.print("  • studiorum sources list    → studiorum data list")
    console.print("  • studiorum sources add     → studiorum data add-homebrew")
    console.print("  • studiorum sources remove  → studiorum data remove")
    console.print("  • studiorum sources scan    → studiorum data scan")
    console.print("  • studiorum sources update  → studiorum data scan")
    console.print("  • studiorum sources info    → studiorum data status")
    console.print("")


@app.command("list")
def list_sources() -> None:
    """DEPRECATED: List configured sources. Use 'studiorum data list' instead."""
    show_deprecation_warning("studiorum data list")

    config = get_content_config()

    if not config.content_sources:
        console.print("[yellow]No content sources configured.[/yellow]")
        console.print("Use [bold]studiorum sources add[/bold] to add sources.")
        return

    table = Table(title="Content Sources")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Priority", justify="center")
    table.add_column("Location/URL")

    for source in config.content_sources:
        status = "✅ Enabled" if source.enabled else "❌ Disabled"
        location = source.url if source.type == SourceType.GITHUB else str(source.path)

        table.add_row(
            source.name,
            source.type.value,
            status,
            str(source.priority),
            location or "Not set",
        )

    console.print(table)


@app.command("add")
def add_source(
    name: str = typer.Argument(..., help="Unique name for the source"),
    source_type: str = typer.Option(
        ..., "--type", "-t", help="Source type (github, directory)"
    ),
    url: str | None = typer.Option(None, "--url", "-u", help="URL for GitHub sources"),
    path: str | None = typer.Option(
        None, "--path", "-p", help="Path for directory sources"
    ),
    enabled: bool = typer.Option(
        True, "--enabled/--disabled", help="Enable or disable the source"
    ),
    priority: int = typer.Option(
        1, "--priority", help="Priority order (lower = higher priority)"
    ),
    auto_update: bool = typer.Option(
        True, "--auto-update/--no-auto-update", help="Enable automatic updates"
    ),
) -> None:
    """DEPRECATED: Add a source. Use 'studiorum data add-homebrew' instead."""
    show_deprecation_warning("studiorum data add-homebrew")

    # Validate source type
    try:
        source_type_enum = SourceType(source_type.lower())
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid source type '{source_type}'. Valid types: github, directory"
        )
        raise typer.Exit(1)

    # Validate required parameters
    if source_type_enum == SourceType.GITHUB and not url:
        console.print("[red]Error:[/red] URL is required for GitHub sources")
        raise typer.Exit(1)

    if source_type_enum == SourceType.DIRECTORY and not path:
        console.print("[red]Error:[/red] Path is required for directory sources")
        raise typer.Exit(1)

    # Validate directory path exists
    if source_type_enum == SourceType.DIRECTORY:
        # Already validated above via typer.Option, not a security assertion
        assert path is not None  # nosec B101
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            console.print(f"[red]Error:[/red] Directory does not exist: {dir_path}")
            raise typer.Exit(1)
        if not dir_path.is_dir():
            console.print(f"[red]Error:[/red] Path is not a directory: {dir_path}")
            raise typer.Exit(1)

    # Create source configuration
    try:
        source = ContentSource(
            name=name,
            type=source_type_enum,
            url=url,
            path=path,
            enabled=enabled,
            priority=priority,
            auto_update=auto_update,
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] Invalid source configuration: {e}")
        raise typer.Exit(1)

    # Add to configuration
    config_manager = get_config_manager()
    config = config_manager.get_config()

    try:
        config.add_source(source)
        config_manager.update_config(config)

        console.print(f"[green]✅ Successfully added source '{name}'[/green]")

        # Show the added source
        table = Table(title=f"Added Source: {name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Type", source.type.value)
        table.add_row("Enabled", "Yes" if source.enabled else "No")
        table.add_row("Priority", str(source.priority))
        table.add_row("Auto Update", "Yes" if source.auto_update else "No")

        if source.url:
            table.add_row("URL", source.url)
        if source.path:
            table.add_row("Path", str(source.path))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to add source: {e}")
        raise typer.Exit(1)


@app.command("remove")
def remove_source(
    name: str = typer.Argument(..., help="Name of the source to remove"),
    remove_data: bool = typer.Option(
        False, "--remove-data", help="Also remove cached data"
    ),
) -> None:
    """DEPRECATED: Remove a source. Use 'studiorum data remove' instead."""
    show_deprecation_warning("studiorum data remove")
    config_manager = get_config_manager()
    config = config_manager.get_config()

    # Check if source exists
    source = config.get_source_by_name(name)
    if not source:
        console.print(f"[red]Error:[/red] Source '{name}' not found")
        raise typer.Exit(1)

    # Confirm removal
    if not typer.confirm(f"Remove source '{name}'?"):
        console.print("Operation cancelled.")
        return

    # Remove cached data if requested
    if remove_data and source.type == SourceType.GITHUB:
        console.print(f"Removing cached data for '{name}'...")
        source_manager = ContentSourceManager(config)
        try:
            asyncio.run(source_manager.remove_source_data(name))
            console.print("[green]✅ Cached data removed[/green]")
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Failed to remove cached data: {e}"
            )

    # Remove from configuration
    if config.remove_source(name):
        config_manager.update_config(config)
        console.print(f"[green]✅ Successfully removed source '{name}'[/green]")
    else:
        console.print(f"[red]Error:[/red] Failed to remove source '{name}'")
        raise typer.Exit(1)


@app.command("update")
def update_sources(
    name: str | None = typer.Argument(None, help="Name of specific source to update"),
) -> None:
    """DEPRECATED: Update sources. Use 'studiorum data scan' instead."""
    show_deprecation_warning("studiorum data scan")
    config = get_content_config()
    source_manager = ContentSourceManager(config)

    def _update() -> bool:
        if name:
            # Update specific source
            console.print(f"Updating source '{name}'...")
            success = asyncio.run(source_manager.update_source(name))
            if success:
                console.print(f"[green]✅ Successfully updated '{name}'[/green]")
                return True
            else:
                console.print(f"[red]❌ Failed to update '{name}'[/red]")
                return False
        else:
            # Update all sources
            console.print("Updating all content sources...")
            try:
                asyncio.run(source_manager.ensure_all_sources())
                console.print("[green]✅ All sources updated successfully[/green]")
                return True
            except Exception as e:
                console.print(f"[red]❌ Failed to update sources: {e}[/red]")
                return False

    success = _update()
    if not success:
        raise typer.Exit(1)


@app.command("info")
def source_info(
    name: str = typer.Argument(..., help="Name of the source to show info for"),
) -> None:
    """DEPRECATED: Show source info. Use 'studiorum data status' instead."""
    show_deprecation_warning("studiorum data status")
    config = get_content_config()
    source_manager = ContentSourceManager(config)

    # Build content index if needed
    def _get_info() -> dict | None:
        asyncio.run(source_manager.build_content_index())
        return source_manager.get_source_info(name)

    info = _get_info()

    if not info:
        console.print(f"[red]Error:[/red] Source '{name}' not found")
        raise typer.Exit(1)

    # Create info panel
    info_text = []
    info_text.append(f"[bold]Type:[/bold] {info['type']}")
    info_text.append(
        f"[bold]Status:[/bold] {'Enabled' if info['enabled'] else 'Disabled'}"
    )
    info_text.append(f"[bold]Priority:[/bold] {info['priority']}")
    info_text.append(
        f"[bold]Auto Update:[/bold] {'Yes' if info['auto_update'] else 'No'}"
    )
    info_text.append(f"[bold]File Count:[/bold] {info['file_count']}")

    if "url" in info:
        info_text.append(f"[bold]URL:[/bold] {info['url']}")
    if "path" in info:
        info_text.append(f"[bold]Path:[/bold] {info['path']}")
    if "branch" in info:
        info_text.append(f"[bold]Branch:[/bold] {info['branch']}")
    if "local_path" in info:
        info_text.append(f"[bold]Local Path:[/bold] {info['local_path']}")
    if "commit_hash" in info:
        info_text.append(f"[bold]Latest Commit:[/bold] {info['commit_hash'][:8]}")
    if "last_commit_date" in info:
        info_text.append(f"[bold]Last Updated:[/bold] {info['last_commit_date']}")

    panel = Panel(
        "\n".join(info_text),
        title=f"Source: {name}",
        title_align="left",
        border_style="blue",
    )

    console.print(panel)


@app.command("scan")
def scan_content() -> None:
    """DEPRECATED: Scan content. Use 'studiorum data scan' instead."""
    show_deprecation_warning("studiorum data scan")
    config = get_content_config()
    source_manager = ContentSourceManager(config)

    def _scan() -> None:
        console.print("Ensuring all sources are available...")
        asyncio.run(source_manager.ensure_all_sources())

        console.print("Scanning content files...")
        asyncio.run(source_manager.build_content_index(force_rebuild=True))

        # Show statistics
        stats = source_manager.get_statistics()

        table = Table(title="Content Scan Results")
        table.add_column("Source", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Files", justify="right", style="green")

        for source_info in stats["sources"]:
            table.add_row(
                source_info["name"], source_info["type"], str(source_info["file_count"])
            )

        console.print(table)
        console.print(
            f"\n[bold green]Total: {stats['total_files']} files from {stats['total_sources']} sources[/bold green]"
        )

    _scan()


@app.command("defaults")
def setup_defaults() -> None:
    """DEPRECATED: Set up defaults. Use 'studiorum data' commands instead."""
    show_deprecation_warning("studiorum data list")
    config_manager = get_config_manager()

    if typer.confirm("This will reset to default sources. Continue?"):
        config = config_manager.reset_to_defaults()
        console.print("[green]✅ Default content sources configured:[/green]")

        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("URL")

        for source in config.content_sources:
            table.add_row(source.name, source.type.value, source.url or "")

        console.print(table)
        console.print(
            "\nRun [bold]studiorum sources scan[/bold] to download and index content."
        )
    else:
        console.print("Operation cancelled.")
