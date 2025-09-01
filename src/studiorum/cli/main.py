"""Main CLI application for studiorum."""

import asyncio
import json
from pathlib import Path

import typer
from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.config.loader import ConfigLoader, ConfigValidationError
from studiorum.core.config.unified_config import (
    reset_app_config,
    set_app_config,
)
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.logging.logger import setup_logging
from studiorum.core.models.content import BaseContent
from studiorum.core.result import is_error_result
from studiorum.core.services.access import get_app_config
from studiorum.core.text.tag_resolver import TagResolver
from studiorum.latex_engine import create_latex_engine
from studiorum.latex_engine.config import (
    CompilationConfig,
    LaTeXEngineEnum as LaTeXEngine,
)
from studiorum.latex_engine.core.compiler import LaTeXCompiler
from studiorum.renderers.core.interfaces import RenderingContext

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


def _create_latex_compiler() -> LaTeXCompiler:
    """Create a LaTeX compiler with configuration from settings.

    Returns:
        LaTeXCompiler configured with settings
    """
    config = get_app_config()

    # Create compilation configuration from unified config
    compilation_config = CompilationConfig(
        primary_engine=LaTeXEngine(config.rendering.latex.engine.primary_engine),
        fallback_engines=[
            LaTeXEngine(engine)
            for engine in config.rendering.latex.engine.fallback_engines
        ],
        timeout_seconds=config.rendering.latex.engine.timeout,
        max_passes=config.rendering.latex.engine.max_passes,
        show_progress=config.rendering.latex.engine.show_progress,
        keep_intermediate_files=config.rendering.latex.engine.keep_temp_files,
    )

    return LaTeXCompiler(compilation_config)


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
    config_file: Path = typer.Option(
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

    # Load configuration with optional file override
    try:
        if config_file:
            # Use ConfigLoader for file-based configuration
            config_loader = ConfigLoader()
            config_result = config_loader.load_with_overrides(
                config_file=config_file, env_overrides=True
            )
            if is_error_result(config_result):
                error = config_result.error
                rprint(f"[red]Error loading configuration: {error.message}[/red]")
                if error.suggestions:
                    rprint("[yellow]Suggestions:[/yellow]")
                    for suggestion in error.suggestions:
                        rprint(f"  - {suggestion}")
                raise typer.Exit(1)
            config = config_result.unwrap()
            # Update global config cache with loaded config
            set_app_config(config)
            if verbose or debug:
                rprint(f"[green]Configuration loaded from:[/green] {config_file}")
        else:
            # Use default configuration loading (environment + defaults)
            config = get_app_config()

        # Validate configuration at startup
        # This will trigger Pydantic validation and create directories
        _ = config.model_dump()
        if verbose or debug:
            logger = get_logger(__name__)
            logger.debug("Configuration loaded successfully")
            logger.debug(
                f"LaTeX engine: {config.rendering.latex.engine.primary_engine}"
            )
            logger.debug(f"Output path: {config.paths.output_path}")
            if config.mcp.enabled:
                logger.debug(
                    f"MCP server enabled on {config.mcp.host}:{config.mcp.port}"
                )
    except ConfigValidationError as e:
        rprint(f"[red]Configuration validation error:[/red] {e.message}")
        if e.errors:
            for error_msg in e.errors:
                rprint(f"  • {error_msg}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

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


@app.command("serve")
def serve_api() -> None:
    """
    🚀 **API Server** - Start REST API server (Future Feature)

    Launch a web API for converting 5e content remotely.
    """
    rprint("[yellow]API server feature coming in future release![/yellow]")
    rprint("For now, use the CLI commands.")


@app.command("quick")
def quick_convert(
    input_file: Path = typer.Argument(..., help="Input JSON file"),
    output_file: Path | None = typer.Option(None, "--output", "-o", help="Output file"),
    content_type: str = typer.Option(
        "auto", "--type", "-t", help="Content type (adventure, book, auto)"
    ),
    with_images: bool = typer.Option(
        False, "--images/--no-images", help="Include images"
    ),
    compile_pdf: bool = typer.Option(False, "--pdf", help="Compile to PDF"),
) -> None:
    """
    ⚡ **Quick Convert** - Fast single-file conversion

    Convert a single JSON file to LaTeX with minimal configuration.
    Perfect for quick conversions and testing.
    """

    def _quick_convert() -> None:
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Input file not found: {input_file}")
                raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                output_path = input_file.with_suffix(".tex")
            else:
                output_path = output_file

            # Load omnidexer and tag resolver
            with display_manager.progress("Initializing") as _:
                load_task = display_manager.add_task(
                    "[cyan]Initializing...", total=None
                )
                from studiorum.cli.utils import get_omnidexer, get_tag_resolver

                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Load content from file
            with open(input_file) as f:
                content = f.read()
                data = json.loads(content)

            # Simple content detection and loading
            content_items: list[BaseContent] = []
            for key, items in data.items():
                if isinstance(items, list):
                    for item_data in items:
                        # Add source info if missing
                        if "source" not in item_data:
                            item_data["source"] = {
                                "abbreviation": input_file.stem.upper(),
                                "name": input_file.stem.replace("-", " ").title(),
                            }

                        # Try to create appropriate model
                        if key in ["spell", "spells"]:
                            from studiorum.core.models.spells import Spell

                            content_items.append(Spell.model_validate(item_data))
                        elif key in ["monster", "monsters", "creature", "creatures"]:
                            from studiorum.core.models.creatures import Creature

                            content_items.append(Creature.model_validate(item_data))
                        elif key in ["item", "items"]:
                            from studiorum.core.models.items import Item

                            content_items.append(Item.model_validate(item_data))

            if not content_items:
                rprint("[yellow]Warning:[/yellow] No recognized content found in file")
                raise typer.Exit(1)

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": f"5e Content from {input_file.name}",
                    "include_images": with_images,
                    "include_toc": len(content_items) > 5,
                    "tag_resolver": tag_resolver,
                },
            )

            # Render document
            engine = create_latex_engine()
            with display_manager.progress("Rendering") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering document...", total=None
                )
                result = engine.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)

            rprint(
                f"[green]✓[/green] Converted {len(content_items)} items to {output_path}"
            )

            # Compile PDF if requested
            if compile_pdf and output_path.suffix == ".tex":
                pdf_path = output_path.with_suffix(".pdf")
                rprint(f"[cyan]Compiling PDF: {pdf_path}[/cyan]")

                try:
                    compiler = _create_latex_compiler()

                    # Read the LaTeX file content
                    with open(output_path, "r", encoding="utf-8") as f:
                        latex_content = f.read()

                    # Compile using the configured compiler
                    import asyncio

                    compilation_result = asyncio.run(
                        compiler.compile_document(
                            latex_content,
                            output_name=output_path.stem,
                            working_dir=output_path.parent,
                        )
                    )

                    if compilation_result.success:
                        rprint(
                            f"[green]✓[/green] PDF compiled: {compilation_result.output_file}"
                        )
                    else:
                        rprint(
                            f"[red]LaTeX compilation failed:[/red] {compilation_result.error_message or 'Unknown error'}"
                        )

                except Exception as e:
                    rprint(f"[red]Error compiling PDF:[/red] {e}")
                    if "not found" in str(e).lower():
                        rprint("[yellow]Install LaTeX to compile PDFs:[/yellow]")
                        rprint("On macOS: brew install --cask mactex")
                        rprint("On Ubuntu: sudo apt-get install texlive-full")

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _quick_convert()


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
