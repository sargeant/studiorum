"""Shared utility functions for convert commands."""

import json
from pathlib import Path
from typing import Any, cast

import typer
from rich import print as rprint

from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.main import get_omnidexer
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.content import BaseContent, ContentType
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler

# JSON type alias for type safety
JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None


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
        # Use the model validation function for consistent behavior
        return _load_from_file_with_type(path, content_type)

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


def load_from_file(file_path: Path) -> JSONValue:
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


def _load_from_file_with_type(
    file_path: Path, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Load content from file with content type processing (for test compatibility)."""
    try:
        content_data = load_from_file(file_path)

        # Handle different content types
        if content_type == ContentType.BOOK:
            # Import Book model
            from dnd5e.core.models.books import Book

            # For books, validate through the Book model
            try:
                # Ensure the data has required fields
                book_data: dict[str, Any]
                if isinstance(content_data, dict):
                    book_data = dict(content_data)
                    if "name" not in book_data:
                        book_data["name"] = f"Book: {file_path.stem}"
                    if "source" not in book_data:
                        book_data["source"] = {
                            "abbreviation": "FILE",
                            "name": f"File: {file_path.name}",
                        }
                else:
                    book_data = content_data  # type: ignore[assignment]

                book = Book.model_validate(book_data)
                return [book], f"file: {file_path}"
            except Exception as e:
                rprint(f"[red]Error:[/red] Invalid book data in {file_path}: {e}")
                raise typer.Exit(1)
        elif content_type == ContentType.ADVENTURE:
            # Import Adventure model
            from dnd5e.core.models.adventures import Adventure

            # For adventures, handle the adventure array structure and create model instances
            if isinstance(content_data, dict) and "adventure" in content_data:
                adventures_data: dict[str, Any] = content_data
                adventures = adventures_data["adventure"]
                if not adventures:
                    rprint(f"[red]Error:[/red] No adventures found in {file_path}")
                    raise typer.Exit(1)

                # Validate each adventure through the model
                validated_adventures = []
                for adventure_data in adventures:
                    try:
                        adventure = Adventure.model_validate(adventure_data)
                        validated_adventures.append(adventure)
                    except Exception as e:
                        rprint(
                            f"[red]Error:[/red] Invalid adventure data in {file_path}: {e}"
                        )
                        raise typer.Exit(1)

                return cast(
                    list[BaseContent], validated_adventures
                ), f"file: {file_path}"
            else:
                # Single adventure object
                try:
                    adventure = Adventure.model_validate(content_data)
                    return cast(list[BaseContent], [adventure]), f"file: {file_path}"
                except Exception as e:
                    rprint(
                        f"[red]Error:[/red] Invalid adventure data in {file_path}: {e}"
                    )
                    raise typer.Exit(1)
        else:
            rprint(f"[red]Error:[/red] Unsupported content type: {content_type}")
            raise typer.Exit(1)

    except Exception as e:
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
