"""Convert command for 5e2pdf CLI - modular version."""

import typer

from .adventure import adventure

# Create the main convert app
app = typer.Typer(help="Convert D&D content to LaTeX/PDF")

# Register commands
app.command("adventure")(adventure)

if __name__ == "__main__":
    app()
