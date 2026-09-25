"""The steps every convert command shares: reading names, reporting errors,
writing the .tex file, compiling and opening the PDF."""

import os

# Using subprocess securely with validated paths via studiorum.core.security
import subprocess  # nosec B404
import sys
import traceback
from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import typer
from rich import print as rprint

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.loaders.content_sources import parse_enhanced_name_lines
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.document_metadata import DocumentMetadata, DocumentType
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.resolvers import ContentResolutionResult, ContentResolver
from studiorum.core.result import Error
from studiorum.core.security import ExecutableNotFoundError, get_platform_file_opener
from studiorum.latex_engine.latexmk import build_pdf

from .options import ConvertOptions


@contextmanager
def conversion_errors() -> Iterator[None]:
    """Turn an unexpected error into a one-line message and exit code 1.

    The traceback is printed only when STUDIORUM_DEBUG_TRACEBACK is set.
    """
    try:
        yield
    except typer.Exit:
        raise
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        if os.getenv("STUDIORUM_DEBUG_TRACEBACK") in {"1", "true", "True"}:
            traceback.print_exc()
        raise typer.Exit(1) from None


def load_data(kind: str) -> tuple[Any, Any]:
    """The omnidexer and tag resolver, loading the data set with a spinner."""
    with display_manager.progress("Loading content") as _:
        task = display_manager.add_task(f"[cyan]Loading {kind} data...", total=None)
        services = get_services()
        omnidexer, tag_resolver = services.omnidexer, services.tag_resolver
        display_manager.update_task(task, completed=100)
    return omnidexer, tag_resolver


def write_document(
    options: ConvertOptions, latex: str, default_output: Path, done: str
) -> Path:
    """Write the document, then compile and open it if asked.

    ``done`` starts the success message, for example "Bestiary generated".
    """
    if not latex:
        rprint("[red]Error:[/red] No LaTeX content was generated")
        raise typer.Exit(1)
    output_path = options.output or default_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex, encoding="utf-8")
    rprint(f"[green]✓[/green] {done}: {output_path}")
    if options.compile_pdf:
        compile_pdf(output_path, options.open_pdf)
    return output_path


def document_metadata(
    options: ConvertOptions,
    title: str,
    document_type: DocumentType = DocumentType.ADVENTURE,
    description: str | None = None,
) -> DocumentMetadata:
    """Metadata carrying the title and the toc and index choices."""
    return DocumentMetadata(
        title=title,
        document_type=document_type,
        include_toc=options.document.show_toc,
        include_index=options.document.show_index,
        description=description,
    )


def append_appendix(latex: str, sections: list[Any], *, gap_after: str) -> str:
    """Insert appendix sections before ``\\end{document}``.

    ContentSection has no ``content`` attribute, so the inserted text is always
    empty and only blank lines are added: these appendices have never rendered.
    Restructure Roadmap step 10 rebuilds document assembly.
    """
    if not sections:
        return latex
    text = "\n\n".join(s.content for s in sections if hasattr(s, "content"))
    if "\\end{document}" not in latex:
        return f"{latex}\n\n{text}"
    body, end = latex.rsplit("\\end{document}", 1)
    return f"{body}\n\n{text}{gap_after}\\end{{document}}{end}"


def compile_pdf(latex_path: Path, open_file: bool = False) -> None:
    """Compile a .tex file to a PDF beside it, and open the PDF if asked."""
    rprint(f"[cyan]Compiling PDF: {latex_path.with_suffix('.pdf')}[/cyan]")
    with display_manager.progress("Compiling PDF") as _:
        task = display_manager.add_task("[cyan]Running latexmk...", total=None)
        result = build_pdf(latex_path, get_app_config().rendering.latex.engine)
        display_manager.update_task(task, completed=100)
    if isinstance(result, Error):
        rprint("[red]✗[/red] Compilation failed")
        rprint(result.error)
        raise typer.Exit(1)
    pdf_path = result.unwrap()
    rprint(f"[green]✓[/green] PDF compiled: {pdf_path}")
    if open_file:
        open_in_viewer(pdf_path)


def open_in_viewer(path: Path) -> None:
    """Open a file with the platform's default application."""
    try:
        opener = get_platform_file_opener()
        if sys.platform == "win32":
            subprocess.run([opener, "/c", "start", "", str(path)], check=True)
        else:
            subprocess.run([opener, str(path)], check=True)
        rprint(f"[green]✓[/green] Opened PDF: {path}")
    except ExecutableNotFoundError as e:
        rprint(f"[yellow]Warning:[/yellow] Cannot open PDF - {e}")
    except subprocess.CalledProcessError:
        rprint(f"[yellow]Warning:[/yellow] Failed to open PDF: {path}")


def split_csv(values: list[str] | None, *, upper: bool = False) -> list[str] | None:
    """Flatten repeated, comma-separated option values; None if there are none."""
    if not values:
        return None
    items = [part.strip() for value in values for part in value.split(",")]
    return [item.upper() for item in items] if upper else items


@dataclass
class NameList:
    """Names given on the command line, in a file or on stdin."""

    names: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    total: int = 0


def read_names(
    args: list[str] | None,
    from_file: Path | None,
    from_stdin: bool,
    kind: str,
    key: Callable[[str, str | None], Hashable] = lambda name, _source: name,
) -> NameList:
    """Collect names from arguments, then ``--from-file``, then ``--from-stdin``.

    Lines read ``[count] name[|source]``. Within each input, an entry whose
    ``key`` was already seen adds to the count but not to the names.
    """
    result = NameList(names=list(args or []))
    inputs: list[tuple[str, list[str]]] = []
    if from_file:
        if not from_file.is_file():
            rprint(f"[red]Error:[/red] File does not exist: {from_file}")
            raise typer.Exit(1)
        inputs.append((str(from_file), from_file.read_text("utf-8").splitlines()))
    if from_stdin:
        if sys.stdin.isatty():
            rprint("[red]Error:[/red] No input provided via stdin")
            raise typer.Exit(1)
        inputs.append(("stdin", list(sys.stdin)))

    for label, lines in inputs:
        entries = parse_enhanced_name_lines(lines)
        if not entries and label == "stdin":
            rprint(f"[red]Error:[/red] No {kind} names found in stdin")
            raise typer.Exit(1)
        seen: set[Hashable] = set()
        added: list[str] = []
        for count, name, source in entries:
            if key(name, source) not in seen:
                seen.add(key(name, source))
                added.append(name)
            result.counts[name] = result.counts.get(name, 0) + count
            result.total += count
            if source:
                result.sources[name] = source
        result.names.extend(added)
        rprint(f"[green]Loaded {len(added)} unique {kind}s from {label}[/green]")
    if result.sources:
        rprint(
            f"[blue]ℹ[/blue] Found source specifications for {len(result.sources)} {kind}s"
        )
    return result


class Collected(Protocol):
    unresolved_names: list[str]
    suggestions: dict[str, list[str]]


def report_collection(result: Collected, found: list[Any], kind: str) -> None:
    """Warn about names that matched nothing; exit if nothing matched at all."""
    if result.unresolved_names:
        rprint(
            f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} {kind}s could not be found:"
        )
        for name in result.unresolved_names:
            rprint(f"  • {name}")
            if result.suggestions.get(name):
                rprint(f"    Suggestions: {', '.join(result.suggestions[name][:3])}")
        rprint()
    if not found:
        rprint(f"[red]Error:[/red] No {kind}s found matching criteria")
        if result.unresolved_names and any(result.suggestions.values()):
            rprint(
                f"[yellow]Try using one of the suggested {kind} names above.[/yellow]"
            )
        raise typer.Exit(1)


def resolve_content_or_file(
    source: str,
    content_type: ContentType,
    *,
    progress_callback: ProgressCallback | None = None,
) -> tuple[list[BaseContent], str]:
    """Load an adventure or book from a JSON file, or look it up by abbreviation.

    Returns the content and a description of where it came from.
    """
    from studiorum.core.loaders.content_sources import (
        ContentLoader,
        create_file_source,
    )

    path = Path(source)
    if path.is_file():
        loader = ContentLoader()
        file_source = create_file_source(path, content_type)
        validation = file_source.validate()
        if not validation.is_valid:
            for error in validation.errors:
                rprint(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)
        for warning in validation.warnings:
            rprint(f"[yellow]Warning:[/yellow] {warning}")
        loader.add_source(file_source)
        try:
            content_items = loader.load_all()
        except Exception as e:
            rprint(
                f"[red]Error:[/red] Failed to load {content_type.value} from {path}: {e}"
            )
            raise typer.Exit(1) from None
        if not content_items:
            rprint(f"[red]Error:[/red] No {content_type.value} content found in {path}")
            raise typer.Exit(1)
        return content_items, f"file: {path}"

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
    """The resolved content, or suggestions and exit code 1."""
    if result.is_success and result.content:
        return [result.content], f"abbreviation: {query}"

    content_name = content_type.value
    if result.suggestions:
        rprint("[yellow]Did you mean?[/yellow]")
        for suggestion in result.suggestions[:5]:
            rprint(f"  • {suggestion}")
        rprint(
            f"Run [bold]studiorum list {content_name}s[/bold] to see all available content."
        )
        raise typer.Exit(1)

    rprint(f"[red]Error:[/red] {content_name.title()} '{query}' not found.")
    rprint(f"Run [bold]studiorum list {content_name}s[/bold] to see available content.")
    raise typer.Exit(1)
