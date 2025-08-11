"""Main CLI application for 5e2pdf."""

import asyncio
import json
import logging
from pathlib import Path

import typer
from rich import print as rprint

from dnd5e.cli.display_manager import display_manager
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.logging.logger import setup_logging
from dnd5e.core.models.content import BaseContent
from dnd5e.core.text.tag_resolver import TagResolver
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler

logger = logging.getLogger(__name__)

# Create the main Typer app
app: typer.Typer = typer.Typer(
    name="5e2pdf",
    help="Convert D&D 5e JSON data to beautifully formatted LaTeX/PDF documents",
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
    rprint("[bold blue]5e2pdf[/bold blue] [green]v2.0.0[/green] - Modern Architecture")
    rprint("Convert D&D 5e JSON → LaTeX → PDF")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug output (most verbose)"
    ),
) -> None:
    """
    🎲 **5e2pdf** - Modern D&D 5e content converter

    Convert structured JSON data from 5e.tools into professional LaTeX documents
    that match the style of official D&D 5th edition books.
    """
    config = get_app_config()

    # Validate configuration at startup
    try:
        # This will trigger Pydantic validation and create directories
        _ = config.model_dump()
        if verbose or debug:
            logger = logging.getLogger(__name__)
            logger.info("Configuration loaded successfully")
            logger.info(f"LaTeX engine: {config.rendering.latex.engine.primary_engine}")
            logger.info(f"Output path: {config.paths.output_path}")
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

    setup_logging(level=log_level)

    if debug:
        logging.info("Enabled debug mode")
    elif verbose:
        logging.info("Enabled verbose mode")


def get_omnidexer() -> Omnidexer:
    """Get the omnidexer instance from the service container."""
    from dnd5e.core.container import get_global_container

    container = get_global_container()
    return container.get_omnidexer()


def get_tag_resolver() -> TagResolver:
    """Get the tag resolver instance from the service container."""
    from dnd5e.core.container import get_global_container

    container = get_global_container()
    return container.get_tag_resolver()


# Import and mount CLI command modules
try:
    from dnd5e.cli.commands.convert import app as convert_app
    from dnd5e.cli.commands.info import app as info_app
    from dnd5e.cli.commands.list_content import app as list_app
    from dnd5e.cli.commands.setup import app as setup_app
    from dnd5e.cli.commands.sources import app as sources_app
    from dnd5e.cli.commands.stats import app as stats_app

    # Mount sub-applications
    app.add_typer(convert_app, name="convert")
    app.add_typer(list_app, name="list")
    app.add_typer(info_app, name="info")
    app.add_typer(setup_app, name="setup")
    app.add_typer(sources_app, name="sources")
    app.add_typer(stats_app, name="stats")
except ImportError as e:
    # If command imports fail, the CLI will not have these commands available
    # This is acceptable as it indicates a serious installation issue
    logger.error(f"Failed to import CLI commands: {e}")
    logger.error("CLI functionality will be limited")


@app.command("serve")
def serve_api(
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """
    🚀 **API Server** - Start REST API server (Future Feature)

    Launch a web API for converting D&D content remotely.
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
                            from dnd5e.core.models.spells import Spell

                            content_items.append(Spell.model_validate(item_data))
                        elif key in ["monster", "monsters", "creature", "creatures"]:
                            from dnd5e.core.models.creatures import Creature

                            content_items.append(Creature.model_validate(item_data))
                        elif key in ["item", "items"]:
                            from dnd5e.core.models.items import Item

                            content_items.append(Item.model_validate(item_data))

            if not content_items:
                rprint("[yellow]Warning:[/yellow] No recognized content found in file")
                raise typer.Exit(1)

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": f"D&D Content from {input_file.name}",
                    "include_images": with_images,
                    "include_toc": len(content_items) > 5,
                    "tag_resolver": tag_resolver,
                },
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            with display_manager.progress("Rendering") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering document...", total=None
                )
                result = renderer.render_document(content_items, context)
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


def reset_cli_globals() -> None:
    """Reset CLI global variables for testing.

    This function clears the global state maintained by the CLI module
    to ensure clean test isolation.
    """
    from dnd5e.core.container import reset_global_container

    reset_global_container()


if __name__ == "__main__":
    app()
