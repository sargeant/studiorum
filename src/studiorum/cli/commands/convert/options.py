"""The options every convert command shares, and the ConvertOptions they build.

Each command lists the options it takes as parameters typed with the aliases
below, then calls ``ConvertOptions.from_context(ctx)``, which reads them from
the Click context by name. A flag left unset falls through to the loaded
configuration, so booleans are tri-state (``--flag/--no-flag``, default None).
"""

from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel, ConfigDict, ValidationError
from rich import print as rprint

from studiorum.core.config.unified_config import (
    LaTeXConfig,
    LaTeXDocumentConfig,
    get_app_config,
)

OUTPUT = "Output Control"
LAYOUT = "Document Layout"
STYLE = "Visual Styling"


def option(*names: str, text: str, panel: str) -> Any:
    """A typer.Option with its help text and help panel."""
    return typer.Option(*names, help=text, rich_help_panel=panel)


Output = Annotated[
    Path | None, option("--output", "-o", text="Output LaTeX file", panel=OUTPUT)
]
Title = Annotated[str | None, option("--title", text="Document title", panel=OUTPUT)]
Pdf = Annotated[
    bool | None,
    option(
        "--pdf/--no-pdf",
        text="Compile to PDF after conversion [default: from config]",
        panel=OUTPUT,
    ),
]
OpenPdf = Annotated[
    bool,
    option(
        "--open", text="Open PDF file after compilation (requires --pdf)", panel=OUTPUT
    ),
]
Toc = Annotated[
    bool | None,
    option(
        "--toc/--no-toc",
        text="Show table of contents [default: from config]",
        panel=OUTPUT,
    ),
]
Index = Annotated[
    bool | None,
    option(
        "--index/--no-index",
        text="Include an index [default: from config]",
        panel=OUTPUT,
    ),
]
Images = Annotated[
    bool | None,
    option(
        "--images/--no-images",
        text="Include images [default: from config]",
        panel=STYLE,
    ),
]
DocumentClass = Annotated[
    str | None,
    option(
        "--document-class",
        text="LaTeX document class (dndbook, dndarticle)",
        panel=LAYOUT,
    ),
]
Paper = Annotated[
    str | None, option("--paper", text="Paper size (letter, a4, a5)", panel=LAYOUT)
]
TwoColumn = Annotated[
    bool | None,
    option("--two-column/--one-column", text="Use two-column layout", panel=LAYOUT),
]
Justified = Annotated[
    bool | None,
    option("--justified/--not-justified", text="Justify text columns", panel=LAYOUT),
]
Fonts = Annotated[
    str | None,
    option("--fonts", text="Font package to use (wotc, dmsguild)", panel=STYLE),
]
FontSize = Annotated[
    str | None,
    option("--font-size", text="Base font size (10pt, 11pt, 12pt)", panel=STYLE),
]
Background = Annotated[
    str | None,
    option(
        "--background", "--bg", text="Background style (full, none, print)", panel=STYLE
    ),
]
Outline = Annotated[
    bool | None,
    option("--outline/--no-outline", text="Draw the document outline", panel=STYLE),
]
HighContrast = Annotated[
    bool | None,
    option(
        "--high-contrast/--no-high-contrast", text="Use high contrast mode", panel=STYLE
    ),
]
Statblock = Annotated[
    str | None,
    option(
        "--statblock", text="Statblock style (2014/classic/2024/modern)", panel=STYLE
    ),
]

# Command parameter name -> LaTeXDocumentConfig field
_DOCUMENT_FIELDS = {
    "document_class": "document_class",
    "paper": "paper_size",
    "font_size": "font_size",
    "background": "background",
    "high_contrast": "high_contrast",
    "two_column": "two_column",
    "justified": "justified_text",
    "fonts": "fonts",
    "statblock": "statblock",
    "toc": "show_toc",
    "index": "show_index",
}


class ConvertOptions(BaseModel):
    """What a convert command was asked for, with config filling the gaps."""

    model_config = ConfigDict(frozen=True)

    output: Path | None = None
    title: str | None = None
    compile_pdf: bool = False
    open_pdf: bool = False
    images: bool = False
    latex: LaTeXConfig

    @property
    def document(self) -> LaTeXDocumentConfig:
        return self.latex.document

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "ConvertOptions":
        """Build from command parameters; any missing or None use the config."""
        config = get_app_config()
        overrides = {
            field: params[name]
            for name, field in _DOCUMENT_FIELDS.items()
            if params.get(name) is not None
        }
        if params.get("outline") is not None:
            overrides["no_outline"] = not params["outline"]
        try:
            document = LaTeXDocumentConfig.model_validate(
                config.rendering.latex.document.model_dump() | overrides
            )
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(part) for part in error["loc"])
                rprint(f"[red]Error:[/red] {field}: {error['msg']}")
            raise typer.Exit(1) from None

        def pick(name: str, default: bool) -> bool:
            value = params.get(name)
            return default if value is None else bool(value)

        return cls(
            output=params.get("output"),
            title=params.get("title"),
            compile_pdf=pick("pdf", config.rendering.compilation.auto_compile_pdf),
            open_pdf=pick("open_pdf", False),
            images=pick("images", config.rendering.content.include_images),
            latex=config.rendering.latex.model_copy(update={"document": document}),
        )

    @classmethod
    def from_context(cls, ctx: typer.Context) -> "ConvertOptions":
        """Build from the parameters of the command being run."""
        return cls.from_params(ctx.params)
