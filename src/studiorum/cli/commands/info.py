"""Info command for 5e2pdf CLI."""

from typing import cast

import typer
from rich import print as rprint
from rich.panel import Panel

from studiorum.cli.display_manager import display_manager
from studiorum.cli.utils import get_omnidexer
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.creatures import Creature
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.core.resolvers import ContentResolver
from studiorum.core.services.protocols import OmnidexerProtocol

app: typer.Typer = typer.Typer(help="Show detailed information about content")
console = display_manager.console

# Constants for D&D calculations and formatting
DND_ABILITY_BASE = 10  # Base value for ability score modifier calculation
DND_MODIFIER_DIVISOR = 2  # Divisor for ability score modifier calculation
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
TASK_COMPLETION_PERCENT = 100


@app.command("content")
def show_content_info(
    name_or_abbreviation: str = typer.Argument(
        ..., help="Content name or abbreviation (e.g., 'cos', 'phb')"
    ),
    content_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Content type (adventure, book, spell, creature, item)",
    ),
    source: str | None = typer.Option(None, "--source", "-s", help="Source book"),
) -> None:
    """
    🔍 Show detailed information about content

    Displays comprehensive details about adventures, books, spells, creatures,
    items, etc. Supports both content names and abbreviations.

    \b
    Examples:
      5e2pdf info content cos                    # Adventure by abbreviation
      5e2pdf info content phb                    # Book by abbreviation
      5e2pdf info content "Curse of Strahd"     # Adventure by name
      5e2pdf info content fireball --type spell # Spell by name
    """

    def _show_info() -> None:
        try:
            # Load omnidexer
            with display_manager.progress("Loading info data") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = get_omnidexer()
                display_manager.update_task(
                    load_task, completed=TASK_COMPLETION_PERCENT
                )

            # Create resolver for abbreviation lookup
            resolver = ContentResolver(cast(OmnidexerProtocol, omnidexer))
            content_item = None

            # First try abbreviation-based lookup for adventures and books
            if not content_type or content_type.lower() in ["adventure", "book"]:
                # Initialize result to avoid UnboundLocalError
                result = None

                # Try adventure abbreviation lookup
                if not content_type or content_type.lower() == "adventure":
                    result = resolver.resolve_adventure(name_or_abbreviation)
                    if result and result.is_success and result.content:
                        content_item = result.content

                # Try book abbreviation lookup if not found
                if not content_item and (
                    not content_type or content_type.lower() == "book"
                ):
                    result = resolver.resolve_book(name_or_abbreviation)
                    if result and result.is_success and result.content:
                        content_item = result.content

            # Fall back to traditional name-based search
            if not content_item:
                if content_type:
                    try:
                        ct = ContentType(content_type.lower())
                        content_item = omnidexer.find(ct, name_or_abbreviation, source)
                    except ValueError:
                        rprint(
                            f"[red]Error:[/red] Unknown content type: {content_type}"
                        )
                        rprint(
                            "Available types: adventure, book, spell, creature, item"
                        )
                        raise typer.Exit(1)
                else:
                    # Search all types by name
                    for ct in ContentType:
                        content_item = omnidexer.find(ct, name_or_abbreviation, source)
                        if content_item:
                            break

            if not content_item:
                rprint(f"[red]Error:[/red] Content not found: {name_or_abbreviation}")
                if source:
                    rprint(f"Searched in source: {source}")

                # Provide helpful suggestions
                if not content_type or content_type.lower() in ["adventure", "book"]:
                    rprint(
                        "\n[yellow]Try one of these commands to see available content:[/yellow]"
                    )
                    rprint("  5e2pdf list adventures    # Show available adventures")
                    rprint("  5e2pdf list books         # Show available books")
                return

            # Display detailed information
            _display_content_details(content_item)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _show_info()


@app.command("file")
def show_file_info(
    file_path: str = typer.Argument(..., help="Path to JSON file"),
) -> None:
    """
    📄 Show information about a JSON file

    Analyzes a JSON file and shows what content it contains,
    structure, and statistics.
    """
    import json
    from pathlib import Path

    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            rprint(f"[red]Error:[/red] File not found: {file_path}")
            raise typer.Exit(1)

        # Load JSON
        with open(file_path_obj) as f:
            data = json.load(f)

        # Analyze structure
        content_stats = {}
        total_items = 0

        for key, value in data.items():
            if isinstance(value, list):
                content_stats[key] = len(value)
                total_items += len(value)
            elif isinstance(value, dict):
                content_stats[key] = 1
                total_items += 1

        # Display info
        panel_content = f"""
[green]File:[/green] {file_path_obj.name}
[green]Size:[/green] {_format_file_size(file_path_obj.stat().st_size)}
[green]Total Items:[/green] {total_items}

[cyan]Content Breakdown:[/cyan]
"""

        for content_type, count in sorted(content_stats.items()):
            panel_content += f"  • {content_type}: {count} items\n"

        console.print(
            Panel(
                panel_content.strip(), title="📄 File Information", border_style="blue"
            )
        )

        # Show sample items
        if content_stats:
            rprint("\n[cyan]Sample Content:[/cyan]")
            sample_count = 0
            for key, items in data.items():
                if isinstance(items, list) and items and sample_count < 3:
                    sample_item = items[0]
                    if isinstance(sample_item, dict) and "name" in sample_item:
                        rprint(f"  • {key}: {sample_item['name']}")
                        sample_count += 1

    except json.JSONDecodeError as e:
        rprint(f"[red]Error:[/red] Invalid JSON file: {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _display_content_details(item: BaseContent) -> None:
    """Display detailed information about a content item."""

    content_type = ContentType.from_content(item)

    # Basic info panel
    basic_info = f"""
[green]Name:[/green] {item.name}
[green]Type:[/green] {content_type.value.title()}
[green]Source:[/green] {item.source.name} ({item.source.abbreviation})
"""
    if item.source.page:
        basic_info += f"[green]Page:[/green] {item.source.page}\n"

    console.print(
        Panel(basic_info.strip(), title=f"📋 {item.name}", border_style="green")
    )

    # Type-specific details
    if isinstance(item, Spell):
        _display_spell_details(item)
    elif isinstance(item, Creature):
        _display_creature_details(item)
    elif isinstance(item, Item):
        _display_item_details(item)


def _display_spell_details(spell: Spell) -> None:
    """Display detailed spell information."""
    details = f"""
[cyan]Level:[/cyan] {spell.get_level_text()}
[cyan]School:[/cyan] {spell.school}
[cyan]Casting Time:[/cyan] {spell.get_casting_time_text()}
[cyan]Range:[/cyan] {spell.get_range_text()}
[cyan]Components:[/cyan] {spell.get_components_text()}
[cyan]Duration:[/cyan] {spell.get_duration_text()}
"""

    console.print(Panel(details.strip(), title="⚡ Spell Details", border_style="blue"))

    # Description
    if spell.entries:
        description = "\n".join(str(entry) for entry in spell.entries)
        console.print(Panel(description, title="📖 Description", border_style="yellow"))

    # Higher levels
    if spell.higher_level:
        higher_text = " ".join(str(entry) for entry in spell.higher_level)
        console.print(
            Panel(higher_text, title="📈 At Higher Levels", border_style="magenta")
        )


def _display_creature_details(creature: Creature) -> None:
    """Display detailed creature information."""
    size = creature.size[0] if creature.size else "Medium"
    cr = getattr(creature, "cr", "Unknown")

    details = f"""
[cyan]Size:[/cyan] {size}
[cyan]Type:[/cyan] {creature.type}
[cyan]Challenge Rating:[/cyan] {cr}
[cyan]Armor Class:[/cyan] {creature.ac[0] if creature.ac else "Unknown"}
[cyan]Hit Points:[/cyan] {creature.hp if creature.hp else "Unknown"}
[cyan]Speed:[/cyan] {creature.speed if creature.speed else "Unknown"}
"""

    console.print(
        Panel(details.strip(), title="🐉 Creature Details", border_style="red")
    )

    # Ability scores
    abilities = f"""
[cyan]STR:[/cyan] {creature.strength} ({(creature.strength - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
[cyan]DEX:[/cyan] {creature.dexterity} ({(creature.dexterity - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
[cyan]CON:[/cyan] {creature.constitution} ({(creature.constitution - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
[cyan]INT:[/cyan] {creature.intelligence} ({(creature.intelligence - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
[cyan]WIS:[/cyan] {creature.wisdom} ({(creature.wisdom - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
[cyan]CHA:[/cyan] {creature.charisma} ({(creature.charisma - DND_ABILITY_BASE) // DND_MODIFIER_DIVISOR:+d})
"""

    console.print(
        Panel(abilities.strip(), title="💪 Ability Scores", border_style="green")
    )


def _display_item_details(item: Item) -> None:
    """Display detailed item information."""
    item_type = getattr(item, "type", "Item")
    rarity = getattr(item, "rarity", None)

    details = f"[cyan]Type:[/cyan] {item_type}\n"
    if rarity:
        details += f"[cyan]Rarity:[/cyan] {rarity}\n"

    console.print(
        Panel(details.strip(), title="🎒 Item Details", border_style="yellow")
    )

    # Description
    if hasattr(item, "entries") and item.entries:
        description = "\n".join(str(entry) for entry in item.entries)
        console.print(Panel(description, title="📖 Description", border_style="blue"))


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.1f} KB"
    else:
        return f"{size_bytes / BYTES_PER_MB:.1f} MB"
