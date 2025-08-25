"""CLI commands for configuration management.

This module provides CLI commands for managing Studiorum's configuration,
including migration from old formats to the new three-tier data source
architecture.

Commands:
- show: Display current configuration with syntax highlighting
- migrate: Migrate from old to new configuration format
- validate: Validate current configuration for issues
- reset: Reset configuration to defaults

Integrates with the configuration migration system from Package 4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from studiorum.core.config.data_sources import DataSourcesConfig
from studiorum.core.config.migration import ConfigurationMigration
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create the config command group
config_app = typer.Typer(
    name="config",
    help="""
[bold cyan]Manage Studiorum configuration[/bold cyan]

Configuration management for Studiorum's settings, including the new
three-tier data source architecture and migration from older formats.

[bold]Common Usage:[/bold]
  [dim]# Show current configuration[/dim]
  studiorum config show

  [dim]# Show specific section[/dim]
  studiorum config show --section data_sources

  [dim]# Preview migration changes[/dim]
  studiorum config migrate --dry-run

  [dim]# Perform migration[/dim]
  studiorum config migrate

  [dim]# Validate configuration[/dim]
  studiorum config validate

  [dim]# Reset to defaults[/dim]
  studiorum config reset
""",
    rich_markup_mode="rich",
)


def _get_config_file_path() -> Path:
    """Get the configuration file path."""
    # Use the same logic as the app config system
    config_dir = Path.home() / ".studiorum"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


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

        # Get the application configuration
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


@config_app.command("migrate")
def migrate_config(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be migrated without changing anything"
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create backup of old configuration"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force migration even if new format detected"
    ),
) -> None:
    """Migrate configuration from old format to new three-tier structure.

    [bold]Examples:[/bold]
      [dim]# Preview migration changes[/dim]
      studiorum config migrate --dry-run

      [dim]# Perform migration with backup[/dim]
      studiorum config migrate

      [dim]# Force migration (skip format detection)[/dim]
      studiorum config migrate --force
    """
    try:
        # Load raw configuration to check for migration needs
        raw_config = _load_raw_config()
        migration = ConfigurationMigration()

        # Check if migration is needed
        if not migration.needs_migration(raw_config) and not force:
            console.print(
                "[green]✅ Configuration is already in new format, no migration needed.[/green]"
            )

            # Show deprecated patterns if any
            deprecated = migration.has_deprecated_patterns(raw_config)
            if deprecated:
                console.print(
                    "\n[yellow]Note: Some deprecated patterns were found:[/yellow]"
                )
                for pattern in deprecated:
                    console.print(f"  • {pattern}")
                console.print("\nConsider updating to new patterns when convenient.")

            return

        if dry_run:
            console.print(
                "[yellow]🔍 DRY RUN: Showing what would be migrated...[/yellow]"
            )

            # Preview migration
            preview = migration.preview_migration(raw_config)

            # Show migration report
            console.print(f"\n{preview['report']}")

            # Show what the new config would look like
            if preview["migration_log"]:
                console.print("\n[bold]New configuration preview:[/bold]")
                config_yaml = yaml.dump(
                    preview["migrated_config"], default_flow_style=False, indent=2
                )
                syntax = Syntax(config_yaml, "yaml", theme="monokai", line_numbers=True)
                console.print(
                    Panel(syntax, title="Migrated Configuration", expand=False)
                )

            console.print(
                "\n[yellow]Run without --dry-run to perform the migration.[/yellow]"
            )
            return

        # Create backup if requested
        config_file = _get_config_file_path()
        if backup and config_file.exists():
            backup_path = config_file.with_suffix(".yaml.backup")
            import shutil

            shutil.copy2(config_file, backup_path)
            console.print(f"[blue]📁 Created backup: {backup_path}[/blue]")

        # Perform migration
        console.print("[yellow]🔄 Migrating configuration...[/yellow]")
        migrated_config = migration.migrate_configuration(raw_config)

        # Convert to dictionary and save
        config_dict = {"data_sources": migrated_config.model_dump()}

        # Preserve other configuration sections that weren't migrated
        for key, value in raw_config.items():
            if key not in ["default_sources", "content", "paths", "processing"]:
                config_dict[key] = value

        _save_config(config_dict)

        # Show results
        report = migration.create_migration_report()
        console.print("\n[green]✅ Migration completed![/green]")
        console.print(report)

        console.print(f"\n[blue]Configuration saved to: {config_file}[/blue]")

    except Exception as e:
        logger.error(f"Error during migration: {e}")
        console.print(f"[red]Error during migration: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("validate")
def validate_config(
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix validation errors"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed validation info"
    ),
) -> None:
    """Validate current configuration.

    [bold]Examples:[/bold]
      [dim]# Basic validation[/dim]
      studiorum config validate

      [dim]# Detailed validation info[/dim]
      studiorum config validate --verbose

      [dim]# Attempt to fix issues[/dim]
      studiorum config validate --fix
    """
    try:
        console.print("[yellow]🔍 Validating configuration...[/yellow]")

        # Check for migration needs first
        raw_config = _load_raw_config()
        migration = ConfigurationMigration()

        if migration.needs_migration(raw_config):
            console.print(
                "[yellow]⚠️  Configuration needs migration to new format.[/yellow]"
            )
            console.print("Run 'studiorum config migrate' first.")
            raise typer.Exit(1)

        # Load and validate data sources configuration
        if "data_sources" not in raw_config:
            console.print("[yellow]⚠️  No data_sources configuration found.[/yellow]")
            console.print(
                "Run 'studiorum config migrate' to create initial configuration."
            )
            return

        try:
            data_config = DataSourcesConfig.model_validate(raw_config["data_sources"])
        except Exception as e:
            console.print(f"[red]❌ Configuration validation failed: {e}[/red]")
            if fix:
                console.print(
                    "\n[yellow]🔧 Auto-fix not available for parsing errors.[/yellow]"
                )
                console.print("Please correct the configuration manually.")
            raise typer.Exit(1)

        # Validate configuration
        validation_errors = data_config.validate_configuration()

        if validation_errors:
            console.print(
                f"[red]❌ Found {len(validation_errors)} validation errors:[/red]"
            )

            table = Table(title="Validation Issues")
            table.add_column("Issue", style="yellow")
            table.add_column("Severity", style="red")

            for error in validation_errors:
                severity = "Warning" if "not found" in error else "Error"
                table.add_row(error, severity)

            console.print(table)

            if fix:
                console.print("\n[yellow]🔧 Attempting to fix errors...[/yellow]")
                console.print(
                    "[yellow]Auto-fix not yet implemented. Please correct errors manually.[/yellow]"
                )
                console.print("\nSuggestions:")
                console.print("  • Check file paths exist")
                console.print("  • Verify URL formats")
                console.print("  • Review extension configurations")

            raise typer.Exit(1)
        else:
            console.print("[green]✅ Configuration is valid![/green]")

            if verbose:
                console.print("\n[cyan]Validation Details:[/cyan]")
                console.print(f"  • SRD enabled: {data_config.srd.enabled}")
                console.print(
                    f"  • Primary override: {data_config.primary_override.enabled}"
                )
                console.print(
                    f"  • Extensions: {len(data_config.extensions)} configured"
                )
                console.print(
                    f"  • Active extensions: {len(data_config.get_enabled_extensions())}"
                )
                console.print(
                    f"  • Attribution sources: {len(data_config.source_attribution.custom_sources)}"
                )

                if data_config.get_active_data_sources():
                    console.print("\n[cyan]Active Data Sources:[/cyan]")
                    for source in data_config.get_active_data_sources():
                        console.print(f"  • {source}")

    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        console.print(f"[red]Error validating configuration: {e}[/red]")
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
