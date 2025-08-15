"""Convert command for 5e2pdf CLI - modular version."""

import typer

from .adventure import adventure
from .book import book
from .bulk import bulk
from .compendiums.creatures import creatures
from .compendiums.items import items
from .compendiums.spells import spells
from .shared import (
    compile_pdf as _compile_pdf,
    handle_resolution_result as _handle_resolution_result,
    load_from_file as _load_from_file,
    resolve_content_or_file,
)
from .supplement import supplement

# Create the main convert app
app: typer.Typer = typer.Typer(help="Convert D&D content to LaTeX/PDF")

# Register commands
app.command("adventure")(adventure)
app.command("book")(book)
app.command("bulk")(bulk)
app.command("creatures")(creatures)
app.command("items")(items)
app.command("spells")(spells)
app.command("supplement")(supplement)

if __name__ == "__main__":
    app()
