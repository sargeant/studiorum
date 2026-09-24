"""studiorum data: show where the 5etools data comes from.

The data directories and homebrew are set in the configuration file:

    data:
      dirs:
        - ~/Code/5etools-src/data
      homebrew:
        - ~/homebrew/my-creatures.json
"""

import typer
from rich.table import Table

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager

data_app = typer.Typer(
    name="data",
    help="Show the configured data directories and homebrew.",
    no_args_is_help=True,
)


@data_app.command("show")
def show() -> None:
    """Show the data directories and homebrew, in load order, with their files.

    Set them in the configuration file under data.dirs and data.homebrew.
    Earlier entries win when two define the same entity.
    """
    data = get_services().data
    table = Table(title="Data, in load order")
    table.add_column("Kind", style="cyan")
    table.add_column("Path")
    table.add_column("Files", justify="right")

    for data_dir in data.dirs:
        found = data_dir.root.is_dir()
        files = str(len(data_dir.entity_files())) if found else "[red]missing[/red]"
        table.add_row("data directory", str(data_dir.root), files)
    for path in data.homebrew:
        if path.is_dir():
            files = str(len(list(path.rglob("*.json"))))
        else:
            files = "1" if path.is_file() else "[red]missing[/red]"
        table.add_row("homebrew", str(path), files)

    console = display_manager.console
    if not data.dirs and not data.homebrew:
        console.print("No data configured. Set data.dirs in the configuration file.")
        raise typer.Exit(1)
    console.print(table)
