"""CLI commands for data repository management.

This module provides the new 'data' command group that replaces the deprecated
'sources' commands, focusing specifically on data repository management
(GitHub repos, local directories) while maintaining clear separation from
content attribution concerns.

Commands:
- list: Show configured data repositories
- set-primary: Set primary data override (replaces SRD)
- add-homebrew: Add homebrew extension repository
- add-url: Add URL-based extension repository
- remove: Remove data repository
- scan: Re-index all repositories
- status: Show detailed repository status
- check: Validate repository configurations

Integrates with the new DataSourceManager from Package 1 foundation refactoring.
"""

from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from studiorum.core.config import get_app_config
from studiorum.core.container import get_global_container
from studiorum.core.logging import get_logger
from studiorum.core.services.protocols import SourceManagerProtocol

logger = get_logger(__name__)
console = Console()


def _get_config_file_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".studiorum"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def _load_config() -> dict[str, Any]:
    """Load configuration from file to show current state."""
    try:
        app_config = get_app_config().model_dump()

        # Check if we have a config file with overrides
        config_file = _get_config_file_path()
        if config_file.exists():
            with open(config_file, "r") as f:
                content = f.read()

            # Simple check for primary override being enabled
            if "primary_override:" in content and "enabled: true" in content:
                # Extract values from file
                lines = content.split("\n")
                in_primary = False
                path = None
                description = None

                for line in lines:
                    if "primary_override:" in line:
                        in_primary = True
                    elif in_primary:
                        if line.strip().startswith("path:") and "null" not in line:
                            path = line.split(":", 1)[1].strip()
                        elif (
                            line.strip().startswith("description:")
                            and "null" not in line
                        ):
                            description = line.split(":", 1)[1].strip()
                        elif (
                            line.strip()
                            and not line.startswith("  ")
                            and not line.startswith("    ")
                        ):
                            break

                if path:
                    app_config["data_sources"]["primary_override"]["enabled"] = True
                    app_config["data_sources"]["primary_override"]["path"] = path
                    app_config["data_sources"]["primary_override"]["type"] = (
                        "5etools-compatible"
                    )
                    if description:
                        app_config["data_sources"]["primary_override"][
                            "description"
                        ] = description

        return app_config

    except Exception:
        # Fallback structure
        return {
            "data_sources": {
                "srd": {"enabled": True},
                "primary_override": {"enabled": False},
                "extensions": [],
            }
        }


def _save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_file = _get_config_file_path()
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)


# Create the data command group
data_app = typer.Typer(
    name="data",
    help="""
[bold cyan]Manage data repositories[/bold cyan]

Studiorum uses a three-tier data model:
  [green]1. SRD Data[/green]     - Bundled System Reference Document content
  [yellow]2. Primary Data[/yellow] - Optional full 5etools dataset (replaces SRD)
  [blue]3. Extensions[/blue]    - Homebrew and custom content (additive)

[bold]Common Usage:[/bold]
  [dim]# List current data sources[/dim]
  studiorum data list

  [dim]# Upgrade to full 5etools data[/dim]
  studiorum data set-primary ~/Code/5etools-src/data

  [dim]# Add homebrew content[/dim]
  studiorum data add-homebrew ~/.studiorum/my-homebrew

  [dim]# Add remote content[/dim]
  studiorum data add-url https://example.com/spells.json

  [dim]# Check repository status[/dim]
  studiorum data status
""",
    rich_markup_mode="rich",
)


@data_app.command("list")
def list_repositories() -> None:
    """List all configured data repositories."""
    try:
        # Load configuration to show actual data source settings
        config = _load_config()
        data_sources = config.get("data_sources", {})

        # SRD data (always present)
        srd_config = data_sources.get(
            "srd", {"enabled": True, "path": "bundled://srd-data"}
        )

        # Primary override
        primary = data_sources.get("primary_override", {})

        # Extensions
        extensions = data_sources.get("extensions", [])

        # Create main table
        table = Table(title="Data Repository Configuration")
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Type", style="yellow")
        table.add_column("Location", style="green")
        table.add_column("Description", style="dim")

        # Add SRD row
        srd_status = "🟢 Active" if srd_config.get("enabled", True) else "🔴 Disabled"
        if primary.get("enabled", False):
            srd_status = "🟡 Overridden"
        table.add_row(
            "SRD",
            srd_status,
            "Bundled",
            srd_config.get("path", "bundled://srd-data"),
            srd_config.get("description", "System Reference Document content"),
        )

        # Add primary override if configured
        if primary.get("enabled", False):
            table.add_row(
                "Primary Override",
                "🟢 Active",
                primary.get("type", "5etools-compatible"),
                primary.get("path", "Not set"),
                primary.get("description", "Primary data override"),
            )

        # Add extensions
        for i, ext in enumerate(extensions):
            if isinstance(ext, dict):
                table.add_row(
                    f"Extension {i + 1}",
                    "🟢 Active" if ext.get("enabled", True) else "🔴 Disabled",
                    ext.get("type", "Extension"),
                    ext.get("path", ext.get("source", "Unknown")),
                    ext.get("description", "Extension repository"),
                )

        console.print(table)

        # Summary panel
        total_sources = 1  # SRD always counts
        if primary.get("enabled", False):
            total_sources += 1
        total_sources += len(
            [
                ext
                for ext in extensions
                if isinstance(ext, dict) and ext.get("enabled", True)
            ]
        )

        summary = Panel(
            f"[bold]Total Active Sources:[/bold] {total_sources}\n"
            f"[bold]SRD Status:[/bold] {'Overridden' if primary.get('enabled', False) else 'Active'}\n"
            f"[bold]Primary Override:[/bold] {'Configured' if primary.get('enabled', False) else 'Not set'}\n"
            f"[bold]Extensions:[/bold] {len(extensions)}",
            title="📊 Repository Summary",
            expand=False,
        )
        console.print(summary)

    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        console.print(f"[red]Error listing repositories: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("set-primary")
def set_primary(
    path: str = typer.Argument(..., help="Path to 5etools-compatible data directory"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Repository description"
    ),
) -> None:
    """Set primary data override (replaces bundled SRD data).

    [bold]Examples:[/bold]
      [dim]# Use local 5etools repository[/dim]
      studiorum data set-primary ~/Code/5etools-src/data

      [dim]# Use custom data with description[/dim]
      studiorum data set-primary /opt/custom-data -d "Production dataset"

    [yellow]Note:[/yellow] Primary data replaces the bundled SRD content entirely.
    Use extensions for additive content instead.
    """
    try:
        # Validate path exists
        data_path = Path(path).expanduser().resolve()
        if not data_path.exists():
            console.print(f"[red]Error: Path does not exist: {data_path}[/red]")
            raise typer.Exit(1)

        if not data_path.is_dir():
            console.print(f"[red]Error: Path is not a directory: {data_path}[/red]")
            raise typer.Exit(1)

        # Load current configuration
        config = _load_config()

        # Ensure data_sources section exists
        if "data_sources" not in config:
            config["data_sources"] = {}

        # Update primary_override configuration
        config["data_sources"]["primary_override"] = {
            "enabled": True,
            "type": "5etools-compatible",
            "path": str(data_path),
            "source": str(data_path),  # This is what is_primary_enabled() checks
            "description": description or f"Primary data from {data_path}",
            "branch": None,
        }

        # Save updated configuration
        _save_config(config)

        # Force config reload to make changes take effect immediately
        try:
            from studiorum.core.config.unified_config import reset_app_config

            reset_app_config()
            console.print(
                f"[green]✓ Primary data source configured and activated: {data_path}[/green]"
            )
        except Exception:
            console.print(
                f"[green]✓ Primary data source configured: {data_path}[/green]"
            )
            console.print("[yellow]Note: Restart CLI to apply changes[/yellow]")

        if description:
            console.print(f"[dim]Description: {description}[/dim]")

    except Exception as e:
        logger.error(f"Error setting primary data source: {e}")
        console.print(f"[red]Error setting primary data source: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("add-homebrew")
def add_homebrew(
    path: str = typer.Argument(..., help="Path to homebrew directory or file"),
    name: str | None = typer.Option(None, "--name", "-n", help="Repository name"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Repository description"
    ),
) -> None:
    """Add homebrew extension repository.

    [bold]Examples:[/bold]
      [dim]# Add homebrew directory[/dim]
      studiorum data add-homebrew ~/.studiorum/my-homebrew

      [dim]# Add with custom name[/dim]
      studiorum data add-homebrew /path/to/homebrew --name "custom-brew" -d "My custom content"
    """
    try:
        # Validate path exists
        homebrew_path = Path(path).expanduser().resolve()
        if not homebrew_path.exists():
            console.print(f"[red]Error: Path does not exist: {homebrew_path}[/red]")
            raise typer.Exit(1)

        # Generate name if not provided
        repo_name = name or f"homebrew-{homebrew_path.name}"

        console.print(f"[yellow]Adding homebrew repository: {repo_name}[/yellow]")
        console.print(f"[dim]Path: {homebrew_path}[/dim]")
        console.print(
            "[dim]Note: This command will be fully implemented with content source configuration in Package 4.[/dim]"
        )
        console.print(
            f"[green]✓ Homebrew repository path validated: {repo_name}[/green]"
        )

        if description:
            console.print(f"[dim]Description: {description}[/dim]")

    except Exception as e:
        logger.error(f"Error adding homebrew repository: {e}")
        console.print(f"[red]Error adding homebrew repository: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("add-url")
def add_url(
    url: str = typer.Argument(..., help="URL to JSON content file"),
    name: str | None = typer.Option(None, "--name", "-n", help="Repository name"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Repository description"
    ),
) -> None:
    """Add URL-based extension repository.

    [bold]Examples:[/bold]
      [dim]# Add remote content[/dim]
      studiorum data add-url https://example.com/homebrew-spells.json

      [dim]# Add with custom name[/dim]
      studiorum data add-url https://example.com/content.json --name "remote-brew"
    """
    try:
        import urllib.parse

        # Validate URL format
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            console.print(
                f"[red]Error: Invalid URL scheme. Must use http or https: {url}[/red]"
            )
            raise typer.Exit(1)

        # Generate name if not provided
        repo_name = name or f"url-{parsed.netloc.replace('.', '-')}"

        console.print(f"[yellow]Adding URL repository: {repo_name}[/yellow]")
        console.print(f"[dim]URL: {url}[/dim]")
        console.print(
            "[dim]Note: This command will be fully implemented with content source configuration in Package 4.[/dim]"
        )
        console.print(f"[green]✓ URL repository validated: {repo_name}[/green]")

        if description:
            console.print(f"[dim]Description: {description}[/dim]")

    except Exception as e:
        logger.error(f"Error adding URL repository: {e}")
        console.print(f"[red]Error adding URL repository: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("remove")
def remove_repository(
    name: str = typer.Argument(..., help="Repository name to remove"),
) -> None:
    """Remove a data repository.

    [bold]Examples:[/bold]
      [dim]# Remove homebrew repository[/dim]
      studiorum data remove homebrew-custom

      [dim]# Remove URL repository[/dim]
      studiorum data remove url-example-com
    """
    try:
        # Prevent removing SRD repository
        if name.lower() in ["srd", "system-reference-document", "bundled"]:
            console.print("[red]Error: Cannot remove bundled SRD repository.[/red]")
            console.print(
                "Use 'studiorum data set-primary' to override with different data instead."
            )
            raise typer.Exit(1)

        # Confirm removal
        if not typer.confirm(f"Remove repository '{name}'?"):
            console.print("Cancelled.")
            return

        console.print(f"[yellow]Removing repository: {name}[/yellow]")
        console.print(
            "[dim]Note: This command will be fully implemented with content source configuration in Package 4.[/dim]"
        )
        console.print(f"[green]✓ Repository removal validated: {name}[/green]")

    except Exception as e:
        logger.error(f"Error removing repository: {e}")
        console.print(f"[red]Error removing repository: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("scan")
def scan_repositories() -> None:
    """Scan and index all configured repositories.

    [bold]Examples:[/bold]
      [dim]# Rebuild content index[/dim]
      studiorum data scan
    """
    try:
        console.print("[yellow]Scanning data repositories...[/yellow]")

        container = get_global_container()
        manager = container.get_service_sync(SourceManagerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        # Clear cache to force rebuild
        manager.clear_cache()

        # Get refreshed statistics
        stats = manager.get_source_statistics()

        console.print("[green]✓ Scan complete[/green]")
        console.print(f"  Content Types: {stats.get('content_types', 0)}")
        console.print(f"  Total Files: {stats.get('total_files', 0)}")

        # Show breakdown by type
        if "by_type" in stats and stats["by_type"]:
            console.print("\n[cyan]Content by Type:[/cyan]")
            for content_type, file_count in stats["by_type"].items():
                console.print(f"  • {content_type}: {file_count} files")

    except Exception as e:
        logger.error(f"Error scanning repositories: {e}")
        console.print(f"[red]Error scanning repositories: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("status")
def show_status() -> None:
    """Show detailed status of data repositories.

    [bold]Examples:[/bold]
      [dim]# Show detailed repository status[/dim]
      studiorum data status
    """
    try:
        container = get_global_container()
        manager = container.get_service_sync(SourceManagerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        stats = manager.get_source_statistics()

        # Overall status panel
        status_panel = Panel(
            f"[bold]Service Name:[/bold] {manager.get_service_name()}\n"
            f"[bold]Is Initialized:[/bold] {'Yes' if stats.get('is_initialized', False) else 'No'}\n"
            f"[bold]Enabled Sources:[/bold] {stats.get('enabled_sources', 0)}\n"
            f"[bold]Content Types:[/bold] {stats.get('content_types', 0)}\n"
            f"[bold]Total Files:[/bold] {stats.get('total_files', 0)}",
            title="Data Source System Status",
            expand=False,
        )
        console.print(status_panel)

        # Content breakdown table
        if "by_type" in stats and stats["by_type"]:
            table = Table(title="Content Type Details")
            table.add_column("Content Type", style="cyan")
            table.add_column("Files", justify="right", style="green")
            table.add_column("Status", style="yellow")

            for content_type, file_count in stats["by_type"].items():
                status_text = "✓ Indexed" if file_count > 0 else "• Empty"
                table.add_row(content_type, str(file_count), status_text)

            console.print(table)
        else:
            console.print(
                "\n[yellow]No content indexed. Run 'studiorum data scan' to build index.[/yellow]"
            )

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        console.print(f"[red]Error getting status: {e}[/red]")
        raise typer.Exit(1)


@data_app.command("check")
def check_repositories() -> None:
    """Validate all repository configurations.

    [bold]Examples:[/bold]
      [dim]# Validate all repositories[/dim]
      studiorum data check
    """
    try:
        console.print("[yellow]Checking repository configurations...[/yellow]")

        container = get_global_container()
        manager = container.get_service_sync(SourceManagerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        # Basic service validation
        stats = manager.get_source_statistics()

        console.print(f"\n[cyan]Service Check: {manager.get_service_name()}[/cyan]")

        # Check initialization status
        if stats.get("is_initialized", False):
            console.print("  [green]✓ Service initialized[/green]")
        else:
            console.print(
                "  [yellow]⚠ Service not initialized - run 'studiorum data scan'[/yellow]"
            )

        # Check for content
        total_files = stats.get("total_files", 0)
        if total_files > 0:
            console.print(f"  [green]✓ {total_files} content files indexed[/green]")
        else:
            console.print("  [yellow]⚠ No content files found[/yellow]")

        # Check content types
        content_types = stats.get("content_types", 0)
        if content_types > 0:
            console.print(f"  [green]✓ {content_types} content types available[/green]")
        else:
            console.print("  [yellow]⚠ No content types registered[/yellow]")

        # Overall assessment
        if stats.get("is_initialized") and total_files > 0 and content_types > 0:
            console.print("\n[green]✓ All repository checks passed[/green]")
        else:
            console.print("\n[yellow]Repository configuration needs attention[/yellow]")
            console.print(
                "Run 'studiorum data scan' to initialize or rebuild content index."
            )

    except Exception as e:
        logger.error(f"Error checking repositories: {e}")
        console.print(f"[red]Error checking repositories: {e}[/red]")
        raise typer.Exit(1)
