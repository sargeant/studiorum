"""Main CLI application for studiorum."""

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.config.unified_config import (
    ConfigFileNotFoundError,
    load_config,
    reset_app_config,
    set_app_config,
)
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.logging.logger import setup_logging
from studiorum.renderers.core.tag_resolver import TagResolver

logger = get_logger(__name__)

# Create the main Typer app
app: typer.Typer = typer.Typer(
    name="studiorum",
    help="""
Studiorum - 5e content processing toolkit

[bold]Key Commands:[/bold]
  [cyan]data[/cyan]      Manage data repositories (SRD, primary data, homebrew)
  [cyan]config[/cyan]    Manage configuration settings
  [cyan]convert[/cyan]   Convert content to LaTeX/PDF
  [cyan]info[/cyan]      Get information about content

Use 'studiorum COMMAND --help' for detailed help on any command.
""",
    rich_markup_mode="rich",
)

# Use shared console from display manager
console = display_manager.console

# Service container for dependency injection
# This replaces the global state variables with proper DI


@app.command("version")
def show_version() -> None:
    """Show version information."""
    rprint(
        "[bold blue]studiorum[/bold blue] [green]v2.0.0[/green] - Modern Architecture"
    )
    rprint("Convert 5e JSON → LaTeX → PDF")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug output (most verbose)"
    ),
    config_file: Path | None = typer.Option(
        None,
        "--config-file",
        "-c",
        help="Load configuration from YAML file",
        exists=False,  # Don't require file to exist (allows None)
    ),
) -> None:
    """
    🎲 **studiorum** - Modern 5e content converter

    Convert structured JSON data from 5e.tools into professional LaTeX documents
    that match the style of official 5th edition books.
    """
    # Reset global state to ensure clean execution for each command
    # This prevents validation contamination between CLI runs
    reset_cli_globals()
    reset_app_config()  # Reset config cache to allow new config loading

    try:
        config = load_config(config_file)
    except ConfigFileNotFoundError as e:
        rprint(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    except (yaml.YAMLError, ValidationError) as e:
        rprint(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    set_app_config(config)
    if config_file and (verbose or debug):
        rprint(f"[green]Configuration loaded from:[/green] {config_file}")

    # Determine log level priority: debug > verbose > config default
    if debug:
        log_level = "DEBUG"
    elif verbose:
        log_level = "INFO"
    else:
        log_level = config.logging.level

    # Convert log level to debug flag for new logging system
    debug_mode = log_level in ["DEBUG", "INFO"]
    setup_logging(debug=debug_mode, console_min_level=log_level.lower())

    logger = get_logger(__name__)
    if debug:
        logger.info("Enabled debug mode")
    elif verbose:
        logger.info("Enabled verbose mode")


# Import and mount CLI command modules
try:
    from studiorum.cli.commands.cache import app as cache_app
    from studiorum.cli.commands.config import config_app
    from studiorum.cli.commands.convert import app as convert_app
    from studiorum.cli.commands.data import data_app
    from studiorum.cli.commands.info import app as info_app
    from studiorum.cli.commands.list_content import app as list_app
    from studiorum.cli.commands.mcp import mcp_app
    from studiorum.cli.commands.setup import app as setup_app
    from studiorum.cli.commands.stats import app as stats_app

    # Mount sub-applications
    app.add_typer(cache_app, name="cache")
    app.add_typer(config_app, name="config")
    app.add_typer(convert_app, name="convert")
    app.add_typer(data_app, name="data")
    app.add_typer(list_app, name="list")
    app.add_typer(mcp_app, name="mcp")
    app.add_typer(info_app, name="info")
    app.add_typer(setup_app, name="setup")
    app.add_typer(stats_app, name="stats")
except ImportError as e:
    # If command imports fail, the CLI will not have these commands available
    # This is acceptable as it indicates a serious installation issue
    logger.error(f"Failed to import CLI commands: {e}")
    logger.error("CLI functionality will be limited")


def get_omnidexer() -> Omnidexer:
    """Get the omnidexer instance from the service container.

    This function provides backward compatibility for tests that expect
    these functions to be available from studiorum.cli.main.
    """
    from studiorum.cli.utils import get_omnidexer as _get_omnidexer

    return _get_omnidexer()


def get_tag_resolver() -> TagResolver:
    """Get the tag resolver instance from the service container.

    This function provides backward compatibility for tests that expect
    these functions to be available from studiorum.cli.main.
    """
    from studiorum.cli.utils import get_tag_resolver as _get_tag_resolver

    return _get_tag_resolver()


def reset_cli_globals() -> None:
    """Reset CLI global variables for testing.

    This function clears the global state maintained by the CLI module
    to ensure clean test isolation.
    """
    from studiorum.cli.utils import reset_cli_services
    from studiorum.core.services.container import ServiceContainer

    # Reset the global container for clean state
    ServiceContainer.reset_global_instance()

    # Reset CLI service singletons to ensure clean state per command
    reset_cli_services()


if __name__ == "__main__":
    app()
