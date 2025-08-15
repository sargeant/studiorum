"""Convert command for 5e2pdf CLI - modular version."""

import typer

from .adventure import adventure
from .book import book
from .bulk import bulk
from .compendiums.items import items
from .compendiums.spells import spells
from .supplement import supplement

# Create the main convert app
app = typer.Typer(help="Convert D&D content to LaTeX/PDF")

# Register commands
app.command("adventure")(adventure)
app.command("book")(book)
app.command("bulk")(bulk)
app.command("items")(items)
app.command("spells")(spells)
app.command("supplement")(supplement)

if __name__ == "__main__":
    app()
