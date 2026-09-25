"""convert adventure: an adventure, whole or by chapter."""

from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print as rprint

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.document_metadata import DocumentMetadata
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.result import Error, Success
from studiorum.core.services.appendix_generator import AppendixFlags
from studiorum.latex_engine.document import render_document as render_latex
from studiorum.renderers.context import RenderingContext, Style

from . import options as opt
from .options import ConvertOptions, option
from .run import (
    conversion_errors,
    document_metadata,
    resolve_content_or_file,
    write_document,
)

APPENDICES = "Appendices"
CONTENT = "Content Options"
LISTS = "Content Output"


A = APPENDICES
AppendixSpells = Annotated[
    bool | None,
    option(
        "--spells/--no-spells",
        text="Generate spells appendix with all referenced spells [default: from config]",
        panel=A,
    ),
]
AppendixItems = Annotated[
    bool | None,
    option(
        "--items/--no-items",
        text="Generate items appendix with all referenced items [default: from config]",
        panel=A,
    ),
]
AppendixCreatures = Annotated[
    bool | None,
    option(
        "--creatures/--no-creatures",
        text="Generate creatures appendix with all referenced creatures [default: from config]",
        panel=A,
    ),
]
UltimateAppendix = Annotated[
    bool,
    option(
        "--ultimate-appendix",
        text="Also add what appendix entries refer to (a creature's spells, a spell's creatures); all three appendices unless the flags choose",
        panel=A,
    ),
]
Chapters = Annotated[
    str | None,
    option(
        "--chapters",
        text=(
            "Chapter numbers to convert (e.g., '1,5,8-9'). Always sorted. "
            "For anthology adventures with no numbered chapters, numbers refer "
            "to positional order (skipping introductions)."
        ),
        panel=CONTENT,
    ),
]
WithIntroduction = Annotated[
    bool,
    option(
        "--with-introduction",
        text="Include introduction when filtering chapters",
        panel=CONTENT,
    ),
]
CreatureLevel = Annotated[
    int,
    option(
        "--creature-level",
        text="Creature level for proficiency bonus scaling (1-20)",
        panel=A,
    ),
]
OutputSpells = Annotated[
    Path | None,
    option(
        "--output-spells", text="Save list of referenced spells to file", panel=LISTS
    ),
]
OutputCreatures = Annotated[
    Path | None,
    option(
        "--output-creatures",
        text="Save list of referenced creatures to file",
        panel=LISTS,
    ),
]
OutputItems = Annotated[
    Path | None,
    option("--output-items", text="Save list of referenced items to file", panel=LISTS),
]


def adventure(
    ctx: typer.Context,
    content_source: Annotated[
        str, typer.Argument(help="Adventure abbreviation (e.g., 'cos') or file path")
    ],
    chapters: Chapters = None,
    with_introduction: WithIntroduction = False,
    appendix_spells: AppendixSpells = None,
    appendix_items: AppendixItems = None,
    appendix_creatures: AppendixCreatures = None,
    ultimate_appendix: UltimateAppendix = False,
    creature_level: CreatureLevel = 1,
    output_spells: OutputSpells = None,
    output_creatures: OutputCreatures = None,
    output_items: OutputItems = None,
    # Shared options, read through ctx.params by ConvertOptions
    output: opt.Output = None,
    title: opt.Title = None,
    pdf: opt.Pdf = None,
    open_pdf: opt.OpenPdf = False,
    toc: opt.Toc = None,
    index: opt.Index = None,
    images: opt.Images = None,
    document_class: opt.DocumentClass = None,
    paper: opt.Paper = None,
    two_column: opt.TwoColumn = None,
    justified: opt.Justified = None,
    fonts: opt.Fonts = None,
    font_size: opt.FontSize = None,
    background: opt.Background = None,
    outline: opt.Outline = None,
    high_contrast: opt.HighContrast = None,
    statblock: opt.Statblock = None,
) -> None:
    """
    📖 Convert adventure to LaTeX

    Converts a 5e adventure to a beautifully formatted LaTeX document
    matching official book styling.

    \\b
    Examples:
      studiorum convert adventure cos              # Use abbreviation
      studiorum convert adventure /path/to/cos.json  # Use file path
      studiorum convert adventure cos --chapters 1-3 --creatures
      studiorum list adventures                    # See available content
    """
    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        content_items, source_desc = load_content(content_source, ContentType.ADVENTURE)
        base_name = (
            Path(content_source).stem if "file:" in source_desc else content_source
        )
        if chapters:
            numbers = _filter_chapters(content_items, chapters, with_introduction)
            base_name += "-ch" + "-".join(str(n) for n in numbers)

        heading = options.title or content_items[0].name
        tracker = ContentTracker()
        latex = render_document(
            content_items,
            rendering_context(options, tracker, creature_level),
            document_metadata(options, heading),
            options,
            appendix_flags(
                appendix_spells, appendix_items, appendix_creatures, ultimate_appendix
            ),
            "adventure",
        )
        _write_content_lists(
            tracker,
            heading,
            {
                "spell": output_spells,
                "creature": output_creatures,
                "item": output_items,
            },
        )
        write_document(
            options,
            latex,
            Path("output/adventures") / f"{base_name}.tex",
            f"Adventure converted ({source_desc})",
        )


def load_content(source: str, content_type: ContentType) -> tuple[list[Any], str]:
    """Resolve an abbreviation or file, reporting data-loading progress."""
    from studiorum.cli.progress_adapter import create_progress_adapter

    with display_manager.progress("Loading content") as _:
        return resolve_content_or_file(
            source,
            content_type,
            progress_callback=create_progress_adapter(display_manager),
        )


def rendering_context(
    options: ConvertOptions, tracker: ContentTracker | None, creature_level: int = 1
) -> RenderingContext:
    """The context an adventure or book renders its entries with."""
    return RenderingContext(
        content_tracker=tracker,
        omnidexer=get_services().omnidexer,
        style=Style(
            book=True,
            images=options.images,
            statblock=options.latex.document.statblock_year,
        ),
        creature_level=creature_level,
    )


def appendix_flags(
    spells: bool | None,
    items: bool | None,
    creatures: bool | None,
    recursive: bool = False,
) -> AppendixFlags:
    """The appendices asked for; a flag not given takes the config default.

    Recursive appendices with no flags given are all three.
    """
    if recursive and spells is None and items is None and creatures is None:
        spells = items = creatures = True
    content = get_app_config().rendering.content
    return AppendixFlags(
        spells=content.appendix_spells if spells is None else spells,
        items=content.appendix_items if items is None else items,
        creatures=content.appendix_creatures if creatures is None else creatures,
        recursive=recursive,
    )


def render_document(
    content: list[BaseContent],
    context: RenderingContext,
    metadata: DocumentMetadata,
    options: ConvertOptions,
    appendices: AppendixFlags,
    kind: str,
) -> str:
    """Render content as a LaTeX document with a progress spinner."""
    with display_manager.progress(f"Rendering {kind}") as _:
        task = display_manager.add_task(f"[green]Rendering {kind}...", total=None)
        latex = render_latex(
            content,
            context,
            metadata,
            appendices=appendices,
            latex_config=options.latex,
        )
        display_manager.update_task(task, completed=100)
    return latex


def _filter_chapters(
    content_items: list[Any], chapters: str, with_introduction: bool
) -> list[int]:
    """Replace the adventure with the chosen chapters; return their numbers."""
    from studiorum.core.models.adventures import Adventure
    from studiorum.core.utils.chapters import (
        filter_adventure_chapters,
        parse_chapter_spec,
    )

    try:
        numbers = parse_chapter_spec(chapters)
        if not isinstance(content_items[0], Adventure):
            rprint("[red]Error:[/red] Chapter filtering only works with adventures")
            raise typer.Exit(1)
        content_items[0], warnings = filter_adventure_chapters(
            content_items[0], numbers, include_introduction=with_introduction
        )
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    rprint(
        f"[green]Filtering to chapters:[/green] {', '.join(str(n) for n in numbers)}"
    )
    if with_introduction:
        rprint("[green]Including:[/green] Introduction")
    for warning in warnings:
        rprint(f"[yellow]Warning:[/yellow] {warning}")
    return numbers


def _write_content_lists(
    tracker: ContentTracker, title: str, paths: dict[str, Path | None]
) -> None:
    """Write the requested lists of referenced spells, creatures and items.

    A failure is reported but does not fail the command.
    """
    for content_type, output_path in paths.items():
        if output_path is None:
            continue
        result = get_services().content_list_writer.write_content_list(
            content_tracker=tracker,
            output_path=output_path,
            content_type_filter=content_type,
            title=title,
            sort_by_count=True,
        )
        if isinstance(result, Success):
            rprint(
                f"[green]✓[/green] {content_type.title()} list written: "
                f"{output_path} ({result.unwrap()} entries)"
            )
        elif isinstance(result, Error):
            rprint(f"[red]Error writing {content_type} list:[/red] {result.error}")
