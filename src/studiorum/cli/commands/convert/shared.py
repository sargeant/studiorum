"""Shared utility functions for convert commands."""

# Using subprocess securely with validated paths via studiorum.core.security
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.resolvers import ContentResolutionResult, ContentResolver
from studiorum.core.security import ExecutableNotFoundError, get_platform_file_opener
from studiorum.latex_engine.config.compilation import CompilationConfig, LaTeXEngine
from studiorum.latex_engine.core.compiler import LaTeXCompiler


def create_latex_compiler() -> LaTeXCompiler:
    """Create a LaTeX compiler with configuration from unified config.

    Returns:
        LaTeXCompiler configured with unified application config

    Raises:
        typer.Exit: If configuration validation fails
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

    # Validate configuration for early error detection
    validation_errors = compilation_config.validate_config()
    if validation_errors:
        rprint("[red]LaTeX configuration errors:[/red]")
        for error in validation_errors:
            rprint(f"  [red]•[/red] {error}")
        rprint("\n[yellow]Suggestions:[/yellow]")
        rprint("  • Use XeLaTeX or LuaLaTeX for fontspec package support")
        rprint("  • Remove fontspec from required packages if using PDFLaTeX")
        rprint("  • Check your configuration in ~/.studiorum/config.yaml")
        raise typer.Exit(1)

    return LaTeXCompiler(compilation_config)


async def compile_pdf(latex_path: Path, open_file: bool = False) -> None:
    """Compile LaTeX to PDF using configured LaTeX compiler.

    Args:
        latex_path: Path to the LaTeX file to compile
        open_file: Whether to open the PDF file after successful compilation
    """
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
            pdf_path = latex_path.with_suffix(".pdf")
            rprint(f"[green]✓[/green] PDF compiled: {pdf_path}")
            # Show warnings but don't treat them as fatal errors
            if result.warnings:
                for warning in result.warnings:
                    rprint(f"[yellow]Warning:[/yellow] {warning}")

            # Open the PDF file if requested
            if open_file and pdf_path.exists():
                try:
                    # Use secure executable path resolution to prevent B607 vulnerabilities
                    if sys.platform == "darwin" or sys.platform.startswith(
                        "linux"
                    ):  # macOS
                        opener = get_platform_file_opener()
                        subprocess.run([opener, str(pdf_path)], check=True)
                        rprint(f"[green]✓[/green] Opened PDF: {pdf_path}")
                    elif sys.platform == "win32":  # Windows
                        cmd_path = get_platform_file_opener()
                        subprocess.run(
                            [cmd_path, "/c", "start", "", str(pdf_path)], check=True
                        )
                        rprint(f"[green]✓[/green] Opened PDF: {pdf_path}")
                    else:
                        rprint(
                            f"[yellow]Warning:[/yellow] Cannot open PDF on platform {sys.platform}"
                        )
                except ExecutableNotFoundError as e:
                    rprint(f"[yellow]Warning:[/yellow] Cannot open PDF - {e}")
                except subprocess.CalledProcessError:
                    rprint(f"[yellow]Warning:[/yellow] Failed to open PDF: {pdf_path}")
                except Exception as e:
                    rprint(f"[yellow]Warning:[/yellow] Error opening PDF: {e}")
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
    source: str,
    content_type: ContentType,
    *,
    progress_callback: ProgressCallback | None = None,
) -> tuple[list[BaseContent], str]:
    """Resolve content source to content objects using unified ContentLoader.

    Args:
        source: File path or content abbreviation
        content_type: Type of content to resolve
        progress_callback: Optional progress callback for data loading

    Returns:
        tuple of (content_items, source_description)

    Raises:
        typer.Exit: If content cannot be resolved
    """
    from studiorum.core.loaders.content_sources import (
        ContentLoader,
        create_file_source,
    )

    # Check if it's a file path
    path = Path(source)
    if path.is_file():
        # Use ContentLoader for unified error handling and validation
        loader = ContentLoader()
        file_source = create_file_source(path, content_type)

        # Validate the source
        validation = file_source.validate()
        if not validation.is_valid:
            for error in validation.errors:
                rprint(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Show warnings if any
        for warning in validation.warnings:
            rprint(f"[yellow]Warning:[/yellow] {warning}")

        loader.add_source(file_source)

        try:
            content_items = loader.load_all()
            if not content_items:
                rprint(
                    f"[red]Error:[/red] No {content_type.value} content found in {path}"
                )
                raise typer.Exit(1)
            return content_items, f"file: {path}"
        except Exception as e:
            rprint(
                f"[red]Error:[/red] Failed to load {content_type.value} from {path}: {e}"
            )
            raise typer.Exit(1)

    # Try to resolve as abbreviation using omnidexer with progress
    omnidexer = get_services().load_omnidexer(progress_callback)
    resolver = ContentResolver(omnidexer)

    if content_type == ContentType.ADVENTURE:
        result = resolver.resolve_adventure(source)
    elif content_type == ContentType.BOOK:
        result = resolver.resolve_book(source)
    else:
        rprint(f"[red]Error:[/red] Unsupported content type: {content_type}")
        raise typer.Exit(1)

    return handle_resolution_result(result, source, content_type)


def handle_resolution_result(
    result: ContentResolutionResult, query: str, content_type: ContentType
) -> tuple[list[BaseContent], str]:
    """Handle content resolution result."""
    if result.is_success and result.content:
        return [result.content], f"abbreviation: {query}"

    if result.suggestions:
        content_name = content_type.value
        rprint("[yellow]Did you mean?[/yellow]")
        for suggestion in result.suggestions[:5]:
            rprint(f"  • {suggestion}")
        rprint(
            f"Run [bold]studiorum list {content_name}s[/bold] to see all available content."
        )
        raise typer.Exit(1)

    content_name = content_type.value
    rprint(f"[red]Error:[/red] {content_name.title()} '{query}' not found.")
    rprint(f"Run [bold]studiorum list {content_name}s[/bold] to see available content.")
    raise typer.Exit(1)


def resolve_option[T](value: T) -> T:
    """Resolve a Typer OptionInfo/ArgumentInfo to its default value if needed.

    When CLI functions are called directly from tests, parameters that are
    defined with typer.Option() or typer.Argument() are passed as the
    OptionInfo/ArgumentInfo objects themselves rather than their resolved
    values. This function extracts the default value when needed.

    Args:
        value: Either a regular value or a Typer OptionInfo/ArgumentInfo object

    Returns:
        The resolved value (either the input value or its default)

    Example:
        ```python
        # In CLI function:
        def my_command(
            file: Path | None = typer.Option(None, "--file")
        ):
            # Resolve for test compatibility
            file = resolve_option(file)
            # Now file is always Path | None, never OptionInfo
        ```
    """
    # Check if this is a Typer Option/Argument object by looking for 'default' attribute
    # We avoid importing typer.models.OptionInfo to keep this lightweight
    # and avoid circular dependencies
    if hasattr(value, "default"):
        # This is a Typer Option/Argument: call its factory, else take its default
        factory = getattr(value, "default_factory", None)
        if factory is not None:
            return factory()  # type: ignore[no-any-return]
        return value.default  # type: ignore[attr-defined,no-any-return]
    # Regular value, return as-is
    return value


def resolve_options(**kwargs: Any) -> dict[str, Any]:
    """Resolve multiple Typer OptionInfo objects at once.

    Convenience function for resolving multiple parameters in one call.

    Args:
        **kwargs: Named parameters to resolve

    Returns:
        Dictionary with same keys but resolved values

    Example:
        ```python
        # In CLI function:
        def my_command(
            file: Path | None = typer.Option(None),
            name: str = typer.Option("default")
        ):
            # Resolve all at once
            resolved = resolve_options(file=file, name=name)
            file = resolved["file"]
            name = resolved["name"]
        ```
    """
    return {key: resolve_option(value) for key, value in kwargs.items()}
