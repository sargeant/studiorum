"""convert book: a sourcebook."""

from pathlib import Path
from typing import Annotated

import typer

from studiorum.core.models.content import ContentType
from studiorum.core.models.document_metadata import DocumentType
from studiorum.core.references.content_tracker import ContentTracker

from . import options as opt
from .adventure import (
    AppendixCreatures,
    AppendixItems,
    AppendixSpells,
    UltimateAppendix,
    load_content,
    render_document,
    rendering_context,
)
from .options import ConvertOptions
from .run import conversion_errors, document_metadata, write_document


def book(
    ctx: typer.Context,
    content_source: Annotated[
        str, typer.Argument(help="Book abbreviation (e.g., 'phb') or file path")
    ],
    appendix_spells: AppendixSpells = None,
    appendix_items: AppendixItems = None,
    appendix_creatures: AppendixCreatures = None,
    ultimate_appendix: UltimateAppendix = False,
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
    📚 Convert book to LaTeX

    Converts a 5e sourcebook to a beautifully formatted LaTeX document
    matching official book styling.

    \\b
    Examples:
      studiorum convert book phb                   # Use abbreviation
      studiorum convert book /path/to/phb.json     # Use file path
      studiorum list books                         # See available content
    """
    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        content_items, source_desc = load_content(content_source, ContentType.BOOK)
        name = content_items[0].name
        metadata = document_metadata(options, options.title or name, DocumentType.BOOK)
        context = rendering_context(
            options,
            metadata,
            ContentTracker(),
            title=options.title or f"Book: {name}",
            appendix_spells=appendix_spells,
            appendix_items=appendix_items,
            appendix_creatures=appendix_creatures,
            ultimate_appendix=ultimate_appendix,
        )
        latex = render_document(content_items, context, "book")
        file_name = (
            Path(content_source).with_suffix(".tex").name
            if "file:" in source_desc
            else f"{content_source}.tex"
        )
        write_document(
            options,
            latex,
            Path("output/books") / file_name,
            f"Book converted ({source_desc})",
        )
