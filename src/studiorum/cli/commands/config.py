"""CLI commands for configuration management.

This module provides CLI commands for managing Studiorum's configuration.

Commands:
- show: Display current configuration with syntax highlighting
- validate: Validate current configuration for issues
- reset: Reset configuration to defaults
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from studiorum.core.config.data_sources import DataSourcesConfig
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create the config command group
config_app = typer.Typer(
    name="config",
    help="""
[bold cyan]Manage Studiorum configuration[/bold cyan]

Configuration management for Studiorum's settings and three-tier data source architecture.

[bold]Common Usage:[/bold]
  [dim]# Show current configuration[/dim]
  studiorum config show

  [dim]# Show specific section[/dim]
  studiorum config show --section data_sources

  [dim]# Reset to defaults[/dim]
  studiorum config reset
""",
    rich_markup_mode="rich",
)


def _get_config_file_path() -> Path:
    """Get the configuration file path."""
    from studiorum.core.config.unified_config import get_default_config_path

    return get_default_config_path()


def _load_raw_config() -> dict[str, Any]:
    """Load raw configuration as dictionary."""
    config_file = _get_config_file_path()
    if not config_file.exists():
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}


def _convert_objects_to_strings(data: Any) -> Any:
    """Convert Path objects and Enums to strings to prevent !!python serialization."""
    from enum import Enum
    from pathlib import Path

    if isinstance(data, Path):
        return str(data)
    if isinstance(data, Enum):
        return data.value
    if isinstance(data, dict):
        return {key: _convert_objects_to_strings(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_convert_objects_to_strings(item) for item in data]
    return data


def _save_config(config_data: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_file = _get_config_file_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config_data, f, default_flow_style=False, indent=2, sort_keys=False
            )
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise typer.Exit(1)


@config_app.command("show")
def show_config(
    section: str | None = typer.Option(
        None, "--section", "-s", help="Show specific section only"
    ),
    output_format: str = typer.Option(
        "yaml", "--format", "-f", help="Output format (yaml, json)"
    ),
    path_only: bool = typer.Option(
        False, "--path-only", help="Show config file path only"
    ),
) -> None:
    """Show current configuration."""
    try:
        config_file = _get_config_file_path()

        if path_only:
            console.print(str(config_file))
            return

        # Get the application configuration (now loads from file automatically)
        app_config = get_app_config()

        if section:
            # Check if section exists
            if not hasattr(app_config, section):
                console.print(f"[red]Unknown configuration section: {section}[/red]")

                # Show available sections
                available = [
                    attr
                    for attr in dir(app_config)
                    if not attr.startswith("_")
                    and not callable(getattr(app_config, attr))
                ]
                if available:
                    console.print(
                        f"[yellow]Available sections:[/yellow] {', '.join(available)}"
                    )
                raise typer.Exit(1)

            section_data = getattr(app_config, section)
            if hasattr(section_data, "model_dump"):
                section_data = section_data.model_dump()
            title = f"Configuration Section: {section}"
        else:
            section_data = app_config.model_dump()
            title = "Complete Configuration"

        # Convert Python objects to strings to prevent !!python serialization
        section_data = _convert_objects_to_strings(section_data)

        # Format output
        if output_format == "yaml":
            config_text = yaml.dump(
                section_data, default_flow_style=False, indent=2, sort_keys=False
            )
            syntax = Syntax(config_text, "yaml", theme="monokai", line_numbers=True)
        elif output_format == "json":
            config_text = json.dumps(section_data, indent=2, default=str)
            syntax = Syntax(config_text, "json", theme="monokai", line_numbers=True)
        else:
            console.print(
                f"[red]Unknown format: {output_format}. Use 'yaml' or 'json'.[/red]"
            )
            raise typer.Exit(1)

        panel = Panel(syntax, title=title, expand=False)
        console.print(panel)

    except Exception as e:
        logger.error(f"Error showing configuration: {e}")
        console.print(f"[red]Error showing configuration: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("reset")
def reset_config(
    section: str | None = typer.Option(
        None, "--section", "-s", help="Reset specific section only"
    ),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Reset configuration to defaults.

    [bold]Examples:[/bold]
      [dim]# Reset entire configuration[/dim]
      studiorum config reset

      [dim]# Reset specific section[/dim]
      studiorum config reset --section data_sources

      [dim]# Reset without confirmation[/dim]
      studiorum config reset --yes
    """
    try:
        if not confirm:
            if section:
                if not typer.confirm(f"Reset '{section}' section to defaults?"):
                    console.print("Cancelled.")
                    return
            else:
                if not typer.confirm("Reset entire configuration to defaults?"):
                    console.print("Cancelled.")
                    return

        if section:
            if section == "data_sources":
                console.print(
                    f"[yellow]🔄 Resetting '{section}' section to defaults...[/yellow]"
                )

                # Load existing config and reset just the data_sources section
                raw_config = _load_raw_config()
                default_data_config = DataSourcesConfig()
                raw_config["data_sources"] = default_data_config.model_dump()
                _save_config(raw_config)

                console.print(
                    f"[green]✅ '{section}' section reset to defaults.[/green]"
                )
            else:
                console.print(f"[red]Unknown section: {section}[/red]")
                console.print("Available sections: data_sources")
                raise typer.Exit(1)
        else:
            console.print(
                "[yellow]🔄 Resetting entire configuration to defaults...[/yellow]"
            )

            # Create new default configuration
            default_data_config = DataSourcesConfig()
            config_dict = {"data_sources": default_data_config.model_dump()}
            _save_config(config_dict)

            console.print("[green]✅ Configuration reset to defaults.[/green]")

        config_file = _get_config_file_path()
        console.print(f"[blue]Configuration saved to: {config_file}[/blue]")

    except Exception as e:
        logger.error(f"Error resetting configuration: {e}")
        console.print(f"[red]Error resetting configuration: {e}[/red]")
        raise typer.Exit(1)
