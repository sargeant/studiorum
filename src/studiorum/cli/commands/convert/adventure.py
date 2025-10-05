"""Adventure conversion command."""

import asyncio
import json
import os
from pathlib import Path

import typer
from rich import print as rprint

from studiorum.cli.config_factory import (
    get_appendix_creatures_default,
    get_appendix_items_default,
    get_appendix_spells_default,
    get_compile_pdf_default,
    get_document_class_default,
    get_fonts_default,
    get_with_images_default,
)
from studiorum.cli.display_manager import display_manager
from studiorum.cli.utils import get_content_list_writer, get_omnidexer, get_tag_resolver
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.resolvers import ContentResolutionResult, ContentResolver
from studiorum.core.result import Error, Success
from studiorum.latex_engine import create_latex_engine
from studiorum.renderers.core.interfaces import RenderingContext

from .base import BaseConvertCommand
from .shared import (
    compile_pdf as compile_pdf_async,
    handle_resolution_result,
    resolve_content_or_file,
)


def adventure(
    content_source: str = typer.Argument(
        ..., help="Adventure abbreviation (e.g., 'cos') or file path"
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output LaTeX file",
        rich_help_panel="Output Control",
    ),
    title: str | None = typer.Option(
        None, "--title", help="Document title", rich_help_panel="Output Control"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(),
        "--images/--no-images",
        help="Include images",
        rich_help_panel="Content Options",
    ),
    chapters: str | None = typer.Option(
        None,
        "--chapters",
        help="Chapter numbers to convert (e.g., '1,5,8-9'). Always sorted.",
        rich_help_panel="Content Options",
    ),
    with_introduction: bool = typer.Option(
        False,
        "--with-introduction",
        help="Include introduction when filtering chapters",
        rich_help_panel="Content Options",
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(),
        "--pdf",
        help="Compile to PDF after conversion",
        rich_help_panel="Output Control",
    ),
    open_pdf: bool = typer.Option(
        False,
        "--open",
        help="Open PDF file after compilation (requires --pdf)",
        rich_help_panel="Output Control",
    ),
    # LaTeX document class options
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
        rich_help_panel="Document Layout",
    ),
    paper: str | None = typer.Option(
        None,
        "--paper",
        help="Paper size (letter, a4, a5)",
        rich_help_panel="Document Layout",
    ),
    fonts: str | None = typer.Option(
        get_fonts_default(),
        "--fonts",
        help="Font package to use (wotc, dmsguild)",
        rich_help_panel="Visual Styling",
    ),
    no_outline: bool | None = typer.Option(
        None,
        "--no-outline",
        help="Disable document outline",
        rich_help_panel="Visual Styling",
    ),
    font_size: str | None = typer.Option(
        None,
        "--font-size",
        help="Base font size (10pt, 11pt, 12pt)",
        rich_help_panel="Visual Styling",
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
        rich_help_panel="Visual Styling",
    ),
    high_contrast: bool | None = typer.Option(
        None,
        "--high-contrast",
        help="Use high contrast mode",
        rich_help_panel="Visual Styling",
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
        rich_help_panel="Document Layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
        rich_help_panel="Document Layout",
    ),
    statblock: str | None = typer.Option(
        None,
        "--statblock",
        help="Statblock style (2014/classic/2024/modern)",
        rich_help_panel="Visual Styling",
    ),
    # Appendix options
    appendix_spells: bool = typer.Option(
        get_appendix_spells_default(),
        "--spells/--no-spells",
        help="Generate spells appendix with all referenced spells",
        rich_help_panel="Appendices",
    ),
    appendix_items: bool = typer.Option(
        get_appendix_items_default(),
        "--items/--no-items",
        help="Generate items appendix with all referenced items",
        rich_help_panel="Appendices",
    ),
    appendix_creatures: bool = typer.Option(
        get_appendix_creatures_default(),
        "--creatures/--no-creatures",
        help="Generate creatures appendix with all referenced creatures",
        rich_help_panel="Appendices",
    ),
    ultimate_appendix: bool = typer.Option(
        False,
        "--ultimate-appendix",
        help="Generate recursive appendices (creatures include spells, spells include creatures)",
        rich_help_panel="Appendices",
    ),
    # Level scaling for tiered creatures
    creature_level: int = typer.Option(
        1,
        "--creature-level",
        help="Creature level for proficiency bonus scaling (1-20)",
        rich_help_panel="Appendices",
    ),
    # Content output options
    output_spells: Path | None = typer.Option(
        None,
        "--output-spells",
        help="Save list of referenced spells to file",
        rich_help_panel="Content Output",
    ),
    output_creatures: Path | None = typer.Option(
        None,
        "--output-creatures",
        help="Save list of referenced creatures to file",
        rich_help_panel="Content Output",
    ),
    output_items: Path | None = typer.Option(
        None,
        "--output-items",
        help="Save list of referenced items to file",
        rich_help_panel="Content Output",
    ),
) -> None:
    """
    📖 Convert adventure to LaTeX

    Converts a 5e adventure to a beautifully formatted LaTeX document
    matching official book styling.

    \\b
    Examples:
      studiorum convert adventure cos              # Use abbreviation
      studiorum convert adventure /path/to/cos.json  # Use file path
      studiorum list adventures                    # See available content
    """

    def _convert() -> None:
        result = None  # Initialize to avoid UnboundLocalError
        try:
            # Load content and resolve with progress reporting
            with display_manager.progress("Loading content") as _:
                from studiorum.cli.progress_adapter import create_progress_adapter

                # Create progress adapter to bridge DisplayManager to service layer
                progress_adapter = create_progress_adapter(display_manager)

                # Resolve content source (file or abbreviation) with progress
                content_items, source_desc = resolve_content_or_file(
                    content_source,
                    ContentType("adventure"),
                    progress_callback=progress_adapter,
                )

                # Get omnidexer and tag resolver (omnidexer already loaded by resolve_content_or_file)
                omnidexer = (
                    get_omnidexer()
                )  # Get cached instance since data is already loaded
                tag_resolver = get_tag_resolver()

            # Apply chapter filter if specified
            chapter_numbers: list[int] | None = None
            if chapters:
                try:
                    from studiorum.core.models.adventures import Adventure
                    from studiorum.core.utils.chapters import (
                        filter_adventure_chapters,
                        parse_chapter_spec,
                    )

                    chapter_numbers = parse_chapter_spec(chapters)

                    # Type guard: ensure we have an Adventure
                    if not isinstance(content_items[0], Adventure):
                        rprint(
                            "[red]Error:[/red] Chapter filtering only works with adventures"
                        )
                        raise typer.Exit(1)

                    filtered_adventure, warnings = filter_adventure_chapters(
                        content_items[0],
                        chapter_numbers,
                        include_introduction=with_introduction,
                    )

                    # Replace content with filtered version
                    content_items[0] = filtered_adventure

                    # Display what we're doing
                    chapter_list = ", ".join(str(n) for n in chapter_numbers)
                    rprint(f"[green]Filtering to chapters:[/green] {chapter_list}")
                    if with_introduction:
                        rprint("[green]Including:[/green] Introduction")

                    # Display warnings
                    for warning in warnings:
                        rprint(f"[yellow]Warning:[/yellow] {warning}")

                except ValueError as e:
                    rprint(f"[red]Error:[/red] {e}")
                    raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                if "file:" in source_desc:
                    # Use input filename for file-based sources
                    base_name = Path(content_source).stem
                else:
                    # Use content name for abbreviation-based sources
                    base_name = content_source

                # Add chapter suffix if filtering
                if chapters and chapter_numbers is not None:
                    chapter_suffix = "-ch" + "-".join(str(n) for n in chapter_numbers)
                    input_name = f"{base_name}{chapter_suffix}.tex"
                else:
                    input_name = f"{base_name}.tex"

                output_path = Path("output/adventures") / input_name
            else:
                output_path = output_file

            # Create LaTeX configuration using base class
            command_instance = BaseConvertCommand()
            config = command_instance.apply_config_hierarchy(
                paper=paper,
                fonts=fonts,
                background=background,
                no_outline=no_outline,
                font_size=font_size,
                high_contrast=high_contrast,
                two_column=two_column,
                justified=justified,
                statblock=statblock,
            )

            # Import legacy config classes for backward compatibility
            from studiorum.core.config.latex_config import (
                LaTeXConfig,
                LaTeXDocumentConfig,
            )

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=config["paper_size"],
                font_size=config["font_size"],
                background=config["background"],
                high_contrast=config["high_contrast"],
                two_column=config["two_column"],
                justified_text=config["justified"],
                fonts=config["fonts"],
                no_outline=config["no_outline"],
                statblock=config["statblock"],
            )
            latex_config = LaTeXConfig(document=latex_doc_config)

            # Create document metadata for adventure
            from studiorum.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            metadata = DocumentMetadata(
                title=title or f"{content_items[0].name}",
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,
                include_toc=True,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=None,
                use_parts=False,
            )

            # Create content tracker for appendix generation
            from studiorum.core.references.content_tracker import ContentTracker

            content_tracker = ContentTracker()

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                content_tracker=content_tracker,
                tag_resolver=tag_resolver,
                metadata={
                    "title": title or f"{content_items[0].name}",
                    "include_images": with_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "content_tracker": content_tracker,
                    "appendix_spells": appendix_spells,
                    "appendix_items": appendix_items,
                    "appendix_creatures": appendix_creatures,
                    "ultimate_appendix": ultimate_appendix,
                    "creature_level": creature_level,
                    "_source_adventure": content_items[
                        0
                    ],  # Pass for chapter number lookup
                },
            )

            # Render document
            engine = create_latex_engine()
            with display_manager.progress("Rendering adventure") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering adventure...", total=None
                )
                result = engine.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                rprint(
                    f"[green]✓[/green] Adventure converted ({source_desc}): {output_path}"
                )
            else:
                rprint("[red]Error:[/red] No content was generated")
                raise typer.Exit(1)

            # Write content output files if requested
            _write_content_outputs(
                content_tracker=content_tracker,
                title=title or f"{content_items[0].name}",
                output_spells=output_spells,
                output_creatures=output_creatures,
                output_items=output_items,
            )

            # Compile PDF if requested
            if compile_pdf:
                asyncio.run(compile_pdf_async(output_path, open_pdf))

        except typer.Exit:
            # Re-raise typer.Exit cleanly to avoid double error messages
            raise
        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            # Only print traceback when explicitly requested for local diagnostics
            if os.getenv("STUDIORUM_DEBUG_TRACEBACK") in {"1", "true", "True"}:
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()


def _write_content_outputs(
    *,
    content_tracker: ContentTracker,
    title: str,
    output_spells: Path | None,
    output_creatures: Path | None,
    output_items: Path | None,
) -> None:
    """Write content output files based on tracked content.

    Args:
        content_tracker: ContentTracker instance with tracked content
        title: Title to include in file headers
        output_spells: Optional path for spells output file
        output_creatures: Optional path for creatures output file
        output_items: Optional path for items output file
    """

    # Check if any output options were specified
    output_requests = [
        ("spell", output_spells),
        ("creature", output_creatures),
        ("item", output_items),
    ]

    # Filter to only requested outputs
    requested_outputs = [
        (content_type, path)
        for content_type, path in output_requests
        if path is not None
    ]

    if not requested_outputs:
        # No output files requested, nothing to do
        return

    # Get ContentListWriter service
    content_list_writer = get_content_list_writer()

    # Write each requested content type
    for content_type, output_path in requested_outputs:
        result = content_list_writer.write_content_list(
            content_tracker=content_tracker,
            output_path=output_path,
            content_type_filter=content_type,
            title=title,
            sort_by_count=True,  # Sort by usage frequency
        )

        if isinstance(result, Success):
            count = result.unwrap()
            rprint(
                f"[green]✓[/green] {content_type.title()} list written: {output_path} ({count} entries)"
            )
        elif isinstance(result, Error):
            error_msg = str(result.error)
            rprint(f"[red]Error writing {content_type} list:[/red] {error_msg}")
            # Don't exit on content output errors - they're optional features
