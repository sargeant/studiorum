"""studiorum convert: 5e content to LaTeX, and optionally PDF."""

import typer

from .adventure import adventure
from .book import book
from .bulk import bulk
from .creatures import creatures
from .items import items
from .spells import spells
from .supplement import supplement

app: typer.Typer = typer.Typer(help="Convert 5e content to LaTeX/PDF")

app.command("adventure")(adventure)
app.command("book")(book)
app.command("bulk")(bulk)
app.command("creatures")(creatures)
app.command("items")(items)
app.command("spells")(spells)
app.command("supplement")(supplement)
