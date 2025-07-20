"""Setup wizard CLI command."""

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from dnd5e.core.config.sources import (
    ContentSource,
    SourceType,
    get_config_manager,
    get_content_config,
)
from dnd5e.core.sources import ContentSourceManager

console = Console()
app = typer.Typer(help="Setup and configuration wizard")


@app.command("wizard")
def setup_wizard() -> None:
    """Interactive setup wizard for first-time configuration."""
    console.print(
        Panel.fit(
            "[bold blue]🎲 Welcome to 5e2pdf Setup![/bold blue]\n\n"
            "This wizard will help you configure content sources for 5e2pdf.\n"
            "You can add GitHub repositories, local directories, or use defaults.",
            title="Setup Wizard",
            border_style="blue",
        )
    )

    config_manager = get_config_manager()
    config = config_manager.get_config()

    # Check if already configured
    if config.content_sources:
        console.print(
            f"\n[yellow]You already have {len(config.content_sources)} content sources configured.[/yellow]"
        )

        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")

        for source in config.content_sources:
            status = "✅ Enabled" if source.enabled else "❌ Disabled"
            table.add_row(source.name, source.type.value, status)

        console.print(table)

        if not Confirm.ask("\nDo you want to reconfigure sources?"):
            console.print(
                "Setup cancelled. Use [bold]5e2pdf sources[/bold] to manage sources."
            )
            return

        if Confirm.ask("Remove existing sources?"):
            config.content_sources.clear()

    # Setup options
    console.print("\n[bold]Setup Options:[/bold]")
    console.print("1. [cyan]Use defaults[/cyan] - System Reference Document (SRD) data")
    console.print("2. [cyan]Custom setup[/cyan] - Configure sources manually")
    console.print("3. [cyan]Local only[/cyan] - Use existing local directories")

    choice = Prompt.ask("\nChoose setup option", choices=["1", "2", "3"], default="1")

    if choice == "1":
        _setup_defaults(config_manager)
    elif choice == "2":
        _setup_custom(config_manager)
    elif choice == "3":
        _setup_local(config_manager)

    # Final steps
    console.print("\n[bold green]✅ Configuration complete![/bold green]")

    if Confirm.ask("\nDownload and scan content now?"):
        _scan_content()
    else:
        console.print("\nTo download and scan content later, run:")
        console.print("[bold]5e2pdf sources scan[/bold]")


def _setup_defaults(config_manager: Any) -> None:
    """Set up default sources."""
    console.print("\n[cyan]Setting up default sources...[/cyan]")

    config = config_manager.reset_to_defaults()

    table = Table(title="Default Sources Configured")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("URL")

    for source in config.content_sources:
        table.add_row(source.name, source.type.value, source.url or "")

    console.print(table)


def _setup_custom(config_manager: Any) -> None:
    """Set up custom sources."""
    console.print("\n[cyan]Custom setup - Add sources manually[/cyan]")

    config = config_manager.get_config()

    # Ask about defaults first
    if Confirm.ask("Include default sources (SRD)?"):
        config.add_source(
            ContentSource(
                name="srd",
                type=SourceType.DIRECTORY,
                path=Path("srd-data"),
                enabled=True,
                priority=1,
            )
        )

        console.print("[green]✅ Added default sources[/green]")

    # Add custom sources
    while Confirm.ask("\nAdd additional source?"):
        _add_source_interactive(config)

    config_manager.update_config(config)


def _setup_local(config_manager: Any) -> None:
    """Set up local directory sources only."""
    console.print("\n[cyan]Local setup - Add local directories[/cyan]")

    config = config_manager.get_config()

    while True:
        path_str = Prompt.ask(
            "\nEnter path to local JSON directory (or 'done' to finish)"
        )

        if path_str.lower() == "done":
            break

        path = Path(path_str).expanduser().resolve()

        if not path.exists():
            console.print(f"[red]Error:[/red] Path does not exist: {path}")
            continue

        if not path.is_dir():
            console.print(f"[red]Error:[/red] Path is not a directory: {path}")
            continue

        name = Prompt.ask("Enter name for this source", default=path.name)

        try:
            config.add_source(
                ContentSource(
                    name=name,
                    type=SourceType.DIRECTORY,
                    path=path,
                    enabled=True,
                    priority=len(config.content_sources) + 1,
                )
            )
            console.print(f"[green]✅ Added local source '{name}'[/green]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    if not config.content_sources:
        console.print("[yellow]No sources configured![/yellow]")
        return

    config_manager.update_config(config)


def _add_source_interactive(config: Any) -> bool:
    """Interactively add a source to config."""
    name = Prompt.ask("Source name")

    if config.get_source_by_name(name):
        console.print(f"[red]Error:[/red] Source '{name}' already exists")
        return

    source_type = Prompt.ask("Source type", choices=["github", "directory"])

    if source_type == "github":
        url = Prompt.ask("GitHub repository URL")
        branch = Prompt.ask("Branch", default="master")

        try:
            config.add_source(
                ContentSource(
                    name=name,
                    type=SourceType.GITHUB,
                    url=url,
                    branch=branch,
                    enabled=True,
                    priority=len(config.content_sources) + 1,
                )
            )
            console.print(f"[green]✅ Added GitHub source '{name}'[/green]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    elif source_type == "directory":
        path_str = Prompt.ask("Directory path")
        path = Path(path_str).expanduser().resolve()

        if not path.exists() or not path.is_dir():
            console.print(f"[red]Error:[/red] Invalid directory: {path}")
            return

        try:
            config.add_source(
                ContentSource(
                    name=name,
                    type=SourceType.DIRECTORY,
                    path=path,
                    enabled=True,
                    priority=len(config.content_sources) + 1,
                )
            )
            console.print(f"[green]✅ Added directory source '{name}'[/green]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def _scan_content() -> None:
    """Download and scan content."""
    console.print("\n[cyan]Downloading and scanning content...[/cyan]")

    config = get_content_config()
    source_manager = ContentSourceManager(config)

    async def _do_scan() -> None:
        try:
            await source_manager.ensure_all_sources()
            await source_manager.build_content_index()

            stats = source_manager.get_statistics()

            table = Table(title="Content Scan Results")
            table.add_column("Source", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Files", justify="right", style="green")

            for source_info in stats["sources"]:
                table.add_row(
                    source_info["name"],
                    source_info["type"],
                    str(source_info["file_count"]),
                )

            console.print(table)
            console.print(
                f"\n[bold green]✅ Ready! {stats['total_files']} files from {stats['total_sources']} sources[/bold green]"
            )

        except Exception as e:
            console.print(f"[red]❌ Error during scan: {e}[/red]")

    asyncio.run(_do_scan())


@app.command("check")
def check_setup() -> None:
    """Check current setup and configuration."""
    config = get_content_config()

    if not config.content_sources:
        console.print("[red]❌ No content sources configured[/red]")
        console.print("Run [bold]5e2pdf setup wizard[/bold] to get started.")
        raise typer.Exit(1)

    console.print(
        f"[green]✅ {len(config.content_sources)} content sources configured[/green]"
    )

    # Check source availability
    source_manager = ContentSourceManager(config)

    async def _check() -> None:
        try:
            await source_manager.ensure_all_sources()
            await source_manager.build_content_index()

            stats = source_manager.get_statistics()

            console.print(
                f"[green]✅ {stats['total_files']} content files available[/green]"
            )

            # Show summary
            table = Table(title="Setup Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details")

            table.add_row(
                "Content Sources",
                "✅ Configured",
                f"{len(config.content_sources)} sources",
            )
            table.add_row(
                "Content Files", "✅ Available", f"{stats['total_files']} files"
            )
            table.add_row("Cache Directory", "✅ Ready", str(config.cache_dir))

            console.print(table)

        except Exception as e:
            console.print(f"[red]❌ Setup check failed: {e}[/red]")
            console.print("Run [bold]5e2pdf setup wizard[/bold] to reconfigure.")
            raise typer.Exit(1)

    asyncio.run(_check())


@app.command("reset")
def reset_setup() -> None:
    """Reset configuration to defaults."""
    if not Confirm.ask("This will reset all configuration to defaults. Continue?"):
        console.print("Reset cancelled.")
        return

    config_manager = get_config_manager()
    config_manager.reset_to_defaults()

    console.print("[green]✅ Configuration reset to defaults[/green]")
    console.print("Run [bold]5e2pdf sources scan[/bold] to download content.")
