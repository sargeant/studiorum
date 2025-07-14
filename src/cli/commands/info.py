"""Info command for 5e2pdf CLI."""

import asyncio
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from src.core.loaders.omnidexer import Omnidexer
from src.core.models.content import ContentType

app = typer.Typer(help="Show detailed information about content")
console = Console()


@app.command("content")
def show_content_info(
    name: str = typer.Argument(..., help="Name of the content item"),
    content_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Content type (spell, creature, item)"
    ),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source book"),
):
    """
    🔍 Show detailed information about a specific content item

    Displays comprehensive details about spells, creatures, items, etc.
    including all attributes and formatted descriptions.
    """

    async def _show_info():
        try:
            # Load omnidexer
            with Progress() as progress:
                load_task = progress.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                await omnidexer.load_all_data()
                progress.update(load_task, completed=100)

            # Find content
            content_item = None

            if content_type:
                try:
                    ct = ContentType(content_type.lower())
                    content_item = omnidexer.find(ct, name, source)
                except ValueError:
                    rprint(f"[red]Error:[/red] Unknown content type: {content_type}")
                    raise typer.Exit(1)
            else:
                # Search all types
                for ct in ContentType:
                    content_item = omnidexer.find(ct, name, source)
                    if content_item:
                        break

            if not content_item:
                rprint(f"[red]Error:[/red] Content not found: {name}")
                if source:
                    rprint(f"Searched in source: {source}")
                return

            # Display detailed information
            _display_content_details(content_item)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_show_info())


@app.command("file")
def show_file_info(
    file_path: str = typer.Argument(..., help="Path to JSON file"),
):
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


def _display_content_details(item):
    """Display detailed information about a content item."""
    from src.core.models.creatures import Creature
    from src.core.models.items import Item
    from src.core.models.spells import Spell

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


def _display_spell_details(spell):
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
        description = "\n".join(spell.entries)
        console.print(Panel(description, title="📖 Description", border_style="yellow"))

    # Higher levels
    if spell.higher_level:
        higher_text = " ".join(spell.higher_level)
        console.print(
            Panel(higher_text, title="📈 At Higher Levels", border_style="magenta")
        )


def _display_creature_details(creature):
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
[cyan]STR:[/cyan] {creature.strength} ({(creature.strength - 10) // 2:+d})
[cyan]DEX:[/cyan] {creature.dexterity} ({(creature.dexterity - 10) // 2:+d})
[cyan]CON:[/cyan] {creature.constitution} ({(creature.constitution - 10) // 2:+d})
[cyan]INT:[/cyan] {creature.intelligence} ({(creature.intelligence - 10) // 2:+d})
[cyan]WIS:[/cyan] {creature.wisdom} ({(creature.wisdom - 10) // 2:+d})
[cyan]CHA:[/cyan] {creature.charisma} ({(creature.charisma - 10) // 2:+d})
"""

    console.print(
        Panel(abilities.strip(), title="💪 Ability Scores", border_style="green")
    )


def _display_item_details(item):
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
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
