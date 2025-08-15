"""Shared utility functions for convert commands."""

import json
from pathlib import Path

import typer
from rich import print as rprint

from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler


def create_latex_compiler() -> LaTeXCompiler:
    """Create a LaTeX compiler with configuration from unified config.

    Returns:
        LaTeXCompiler configured with unified application config
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


async def compile_pdf(latex_path: Path) -> None:
    """Compile LaTeX to PDF using configured LaTeX compiler."""
    rprint(f"[cyan]Compiling PDF: {latex_path.with_suffix('.pdf')}[/cyan]")

    result = None  # Initialize to avoid UnboundLocalError
    try:
        compiler = create_latex_compiler()

        # Read the LaTeX file content
        with open(latex_path, "r", encoding="utf-8") as f:
            latex_content = f.read()

        with display_manager.progress("Compiling PDF") as _:
            compile_task = display_manager.add_task(
                "[cyan]Running LaTeX compilation...", total=None
            )

            # Use the configured compiler instead of hardcoded xelatex
            result = await compiler.compile_document(
                latex_content,
                output_name=latex_path.stem,
                working_dir=latex_path.parent,
            )

            display_manager.update_task(compile_task, completed=100)

        if result and result.success:
            rprint(f"[green]✓[/green] PDF compiled: {latex_path.with_suffix('.pdf')}")
        else:
            rprint("[red]✗[/red] Compilation failed")
            if result and result.error_message:
                rprint(f"[red]Error:[/red] {result.error_message}")
            if result and result.warnings:
                for warning in result.warnings:
                    rprint(f"[yellow]Warning:[/yellow] {warning}")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]Error during PDF compilation:[/red] {e}")
        raise typer.Exit(1)


def resolve_content_or_file(
    source: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Resolve content source to content objects.

    Args:
        source: File path or content abbreviation
        content_type: Type of content to resolve

    Returns:
        tuple of (content_items, source_description)

    Raises:
        typer.Exit: If content cannot be resolved
    """
    omnidexer = get_omnidexer()

    # Check if it's a file path
    path = Path(source)
    if path.is_file():
        content_data = load_from_file(path)
        if isinstance(content_data, list):
            return content_data, f"file: {path}"
        else:
            return [content_data], f"file: {path}"

    # Try to resolve as abbreviation
    resolver = ContentResolver(omnidexer)
    if content_type == ContentType.ADVENTURE:
        result = resolver.resolve_adventure(source)
    elif content_type == ContentType.BOOK:
        result = resolver.resolve_book(source)
    else:
        rprint(f"[red]Error:[/red] Unsupported content type: {content_type}")
        raise typer.Exit(1)

    return handle_resolution_result(result, source, content_type)


def load_from_file(file_path: Path) -> BaseContent | list[BaseContent]:
    """Load content from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle both single objects and arrays
        if isinstance(data, list):
            return data  # type: ignore[return-value,no-any-return]
        else:
            return data  # type: ignore[return-value,no-any-return]

    except (json.JSONDecodeError, FileNotFoundError) as e:
        rprint(f"[red]Error:[/red] Failed to load file {file_path}: {e}")
        raise typer.Exit(1)


def handle_resolution_result(
    result: ContentResolutionResult, query: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Handle content resolution result."""
    if result.is_success and result.content:
        return [result.content], f"abbreviation: {query}"

    elif result.suggestions:
        content_name = content_type.value
        rprint("[yellow]Did you mean?[/yellow]")
        for suggestion in result.suggestions[:5]:
            rprint(f"  • {suggestion}")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see all available content."
        )
        raise typer.Exit(1)

    else:
        content_name = content_type.value
        rprint(f"[red]Error:[/red] {content_name.title()} '{query}' not found.")
        rprint(
            f"Run [bold]5e2pdf list {content_name}s[/bold] to see available content."
        )
        raise typer.Exit(1)
