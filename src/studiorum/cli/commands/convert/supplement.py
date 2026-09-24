"""convert supplement: spells, creatures and items from one JSON file."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print as rprint

from studiorum.core.models.document_metadata import DocumentType

from . import options as opt
from .adventure import render_document, rendering_context
from .options import ConvertOptions
from .run import conversion_errors, document_metadata, write_document


def _models() -> dict[str, Any]:
    from studiorum.core.models.creatures import Creature
    from studiorum.core.models.items import Item
    from studiorum.core.models.spells import Spell

    return {
        "spell": Spell,
        "spells": Spell,
        "monster": Creature,
        "monsters": Creature,
        "creature": Creature,
        "creatures": Creature,
        "item": Item,
        "items": Item,
    }


def supplement(
    ctx: typer.Context,
    input_file: Annotated[Path, typer.Argument(help="Supplement JSON file")],
    content_types: Annotated[
        list[str], typer.Option("--type", help="Content types to include")
    ] = ["all"],  # noqa: B006
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
    📄 Convert supplement JSON to LaTeX

    Converts various 5e content (spells, creatures, items) from 5e.tools JSON
    format into a formatted supplement document.
    """
    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        if not input_file.exists():
            rprint(f"[red]Error:[/red] Supplement file not found: {input_file}")
            raise typer.Exit(1)

        models = _models()
        content_items = []
        for key, entries in json.loads(input_file.read_text("utf-8")).items():
            if not isinstance(entries, list) or key not in models:
                continue
            if "all" not in content_types and key not in content_types:
                continue
            for entry in entries:
                entry.setdefault(
                    "source",
                    {
                        "abbreviation": input_file.stem.upper(),
                        "name": input_file.stem.replace("-", " ").title(),
                    },
                )
                try:
                    content_items.append(models[key].model_validate(entry))
                except Exception as e:
                    rprint(f"[yellow]Warning:[/yellow] Failed to parse {key} item: {e}")
        if not content_items:
            rprint("[red]Error:[/red] No valid content found")
            raise typer.Exit(1)

        heading = options.title or (
            f"Supplement: {input_file.stem.replace('-', ' ').title()}"
        )
        metadata = document_metadata(options, heading, DocumentType.BOOK)
        latex = render_document(
            content_items, rendering_context(options, metadata, None), "supplement"
        )
        write_document(
            options,
            latex,
            Path("output/supplements") / input_file.with_suffix(".tex").name,
            f"Supplement converted ({len(content_items)} items)",
        )
