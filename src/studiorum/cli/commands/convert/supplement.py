"""Supplement conversion command."""

import asyncio
import json
import os
from pathlib import Path

import typer
from rich import print as rprint

from studiorum.cli.config_factory import (
    get_compile_pdf_default,
    get_document_class_default,
    get_fonts_default,
    get_with_images_default,
)
from studiorum.cli.display_manager import display_manager
from studiorum.cli.utils import get_omnidexer, get_tag_resolver
from studiorum.latex_engine import create_latex_engine
from studiorum.renderers.core.interfaces import RenderingContext

from .base import BaseConvertCommand
from .shared import compile_pdf as compile_pdf_async


def supplement(
    input_file: Path = typer.Argument(..., help="Supplement JSON file"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output LaTeX file"
    ),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    content_types: list[str] = typer.Option(
        ["all"], "--type", help="Content types to include"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(),
        "--images/--no-images",
        help="Include images",
        rich_help_panel="Visual Styling",
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
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
) -> None:
    """
    📄 Convert supplement JSON to LaTeX

    Converts various 5e content (spells, creatures, items) from 5e.tools JSON
    format into a formatted supplement document.
    """

    def _convert() -> None:
        result = None  # Initialize to avoid UnboundLocalError
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Supplement file not found: {input_file}")
                raise typer.Exit(1)

            # Determine output file
            if output_file is None:
                output_path = (
                    Path("output/supplements") / input_file.with_suffix(".tex").name
                )
            else:
                output_path = output_file

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Load supplement content
            with open(input_file, encoding="utf-8") as f:
                content = f.read()
                supplement_data = json.loads(content)

            # Parse various content types
            content_items = []

            # Import models
            from studiorum.core.models.creatures import Creature
            from studiorum.core.models.items import Item
            from studiorum.core.models.spells import Spell

            # Process different content types
            type_handlers = {
                "spell": Spell,
                "spells": Spell,
                "monster": Creature,
                "monsters": Creature,
                "creature": Creature,
                "creatures": Creature,
                "item": Item,
                "items": Item,
            }

            for key, items in supplement_data.items():
                if isinstance(items, list) and key in type_handlers:
                    if "all" in content_types or key in content_types:
                        model_class = type_handlers[key]
                        for item_data in items:
                            try:
                                # Add source info if missing
                                if "source" not in item_data:
                                    item_data["source"] = {
                                        "abbreviation": input_file.stem.upper(),
                                        "name": input_file.stem.replace(
                                            "-", " "
                                        ).title(),
                                    }
                                content_items.append(
                                    model_class.model_validate(item_data)  # type: ignore[attr-defined]
                                )
                            except Exception as e:
                                rprint(
                                    f"[yellow]Warning:[/yellow] Failed to parse {key} item: {e}"
                                )

            if not content_items:
                rprint("[red]Error:[/red] No valid content found")
                raise typer.Exit(1)

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

            # Create render context
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": title
                    or f"Supplement: {input_file.stem.replace('-', ' ').title()}",
                    "include_images": with_images,
                    "include_toc": len(content_items) > 10,
                    "tag_resolver": tag_resolver,
                    "latex_config": latex_config,
                },
            )

            # Render document
            engine = create_latex_engine()
            with display_manager.progress("Rendering supplement") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering supplement...", total=None
                )
                result = engine.render_document(content_items, context)
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                rprint(
                    f"[green]✓[/green] Supplement converted ({len(content_items)} items): {output_path}"
                )
            else:
                rprint("[red]Error:[/red] No content was generated")
                raise typer.Exit(1)

            # Compile PDF if requested
            if compile_pdf:
                asyncio.run(compile_pdf_async(output_path))

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()
