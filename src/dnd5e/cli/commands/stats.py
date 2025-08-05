"""Stats command for 5e2pdf CLI."""

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from dnd5e.cli.display_manager import display_manager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType

app: typer.Typer = typer.Typer(help="Show content statistics and analysis")
console = display_manager.console


@app.command("overview")
def show_overview() -> None:
    """
    📊 Show overall content statistics

    Displays a comprehensive overview of all loaded content including
    counts by type, source, and other metrics.
    """

    def _show_overview() -> None:
        try:
            # Load omnidexer
            with display_manager.progress("Loading stats data") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                omnidexer.load_all_data()
                display_manager.update_task(load_task, completed=100)

            # Get statistics
            stats = omnidexer.get_statistics()

            # Overview panel
            overview = f"""
[green]Total Items:[/green] {stats.get("total_items", 0)}
[green]Content Types:[/green] {len(stats.get("by_type", {}))}
[green]Source Books:[/green] {len(stats.get("by_source", {}))}
[green]Loaded Types:[/green] {", ".join(stats.get("loaded_types", []))}
"""

            console.print(
                Panel(
                    overview.strip(), title="📊 Content Overview", border_style="blue"
                )
            )

            # Content by type
            if "by_type" in stats:
                type_table = Table(title="📋 Content by Type")
                type_table.add_column("Content Type", style="cyan")
                type_table.add_column("Count", justify="right", style="green")
                type_table.add_column("Percentage", justify="right", style="yellow")

                total = stats["total_items"]
                for content_type, count in sorted(stats["by_type"].items()):
                    percentage = (count / total * 100) if total > 0 else 0
                    type_table.add_row(
                        content_type.title(), str(count), f"{percentage:.1f}%"
                    )

                console.print(type_table)

            # Content by source (top 10)
            if "by_source" in stats:
                source_table = Table(title="📚 Top Sources")
                source_table.add_column("Source", style="blue")
                source_table.add_column("Count", justify="right", style="green")

                sorted_sources = sorted(
                    stats["by_source"].items(), key=lambda x: x[1], reverse=True
                )
                for source, count in sorted_sources[:10]:
                    source_table.add_row(source, str(count))

                console.print(source_table)

                if len(sorted_sources) > 10:
                    rprint(
                        f"[dim]... and {len(sorted_sources) - 10} more sources[/dim]"
                    )

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _show_overview()


@app.command("content")
def show_content_stats(
    content_type: str = typer.Argument(..., help="Content type to analyze"),
) -> None:
    """
    🔍 Show detailed statistics for a specific content type

    Provides in-depth analysis of spells, creatures, items, etc.
    including breakdowns by various attributes.
    """

    def _show_content_stats() -> None:
        try:
            # Load omnidexer
            with display_manager.progress("Loading stats data") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                omnidexer.load_all_data()
                display_manager.update_task(load_task, completed=100)

            # Get content type
            try:
                ct = ContentType(content_type.lower())
            except ValueError:
                rprint(f"[red]Error:[/red] Unknown content type: {content_type}")
                rprint("Available types: spell, creature, item, adventure, book")
                raise typer.Exit(1)

            # Get all content of this type
            content_items = omnidexer.get_all_by_type(ct)

            if not content_items:
                rprint(f"[yellow]No {content_type} content found[/yellow]")
                return

            # Basic stats
            basic_stats = f"""
[green]Total {content_type.title()}s:[/green] {len(content_items)}
"""

            console.print(
                Panel(
                    basic_stats.strip(),
                    title=f"📊 {content_type.title()} Statistics",
                    border_style="green",
                )
            )

            # Type-specific analysis
            if ct == ContentType.SPELL:
                _analyze_spells(content_items)
            elif ct == ContentType.CREATURE:
                _analyze_creatures(content_items)
            elif ct == ContentType.ITEM:
                _analyze_items(content_items)

            # Source breakdown
            _show_source_breakdown(content_items, content_type)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _show_content_stats()


@app.command("sources")
def show_source_stats() -> None:
    """
    📚 Show statistics by source book

    Displays detailed breakdown of content by source book,
    showing what each book contributes to the collection.
    """

    def _show_source_stats() -> None:
        try:
            # Load omnidexer
            with display_manager.progress("Loading stats data") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = Omnidexer()
                omnidexer.load_all_data()
                display_manager.update_task(load_task, completed=100)

            # Get statistics
            stats = omnidexer.get_statistics()

            if "by_source" not in stats:
                rprint("[yellow]No source information available[/yellow]")
                return

            # Detailed source table
            source_table = Table(title="📚 Source Statistics")
            source_table.add_column("Source", style="blue")
            source_table.add_column("Count", justify="right", style="green")
            source_table.add_column("Percentage", justify="right", style="yellow")
            source_table.add_column("Primary Content", style="cyan")

            total_items = stats["total_items"]
            sorted_sources = sorted(
                stats["by_source"].items(), key=lambda x: x[1], reverse=True
            )

            for source, count in sorted_sources:
                percentage = (count / total_items * 100) if total_items > 0 else 0

                # Get primary content type for this source
                source_items = omnidexer.get_all_by_source(source)
                content_types: dict[str, int] = {}
                for item in source_items:
                    try:
                        ct = ContentType.from_content(item).value
                        content_types[ct] = content_types.get(ct, 0) + 1
                    except ValueError:
                        # Handle unknown content types (like BaseFluff)
                        ct_name = type(item).__name__.lower()
                        content_types[ct_name] = content_types.get(ct_name, 0) + 1

                primary_content = (
                    max(content_types.items(), key=lambda x: x[1])[0].title()
                    if content_types
                    else "Mixed"
                )

                source_table.add_row(
                    source, str(count), f"{percentage:.1f}%", primary_content
                )

            console.print(source_table)

        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _show_source_stats()


def _analyze_spells(spells: list) -> dict:
    """Analyze spell-specific statistics."""
    from dnd5e.core.models.spells import Spell

    # Level distribution
    level_counts: dict[int, int] = {}
    school_counts: dict[str, int] = {}

    for spell in spells:
        if isinstance(spell, Spell):
            level_counts[spell.level] = level_counts.get(spell.level, 0) + 1
            school_counts[spell.school] = school_counts.get(spell.school, 0) + 1

    # Level table
    level_table = Table(title="⚡ Spells by Level")
    level_table.add_column("Level", style="cyan")
    level_table.add_column("Count", justify="right", style="green")
    level_table.add_column("Percentage", justify="right", style="yellow")

    total_spells = len(spells)
    for level in sorted(level_counts.keys()):
        count = level_counts[level]
        percentage = (count / total_spells * 100) if total_spells > 0 else 0
        level_name = "Cantrip" if level == 0 else f"Level {level}"
        level_table.add_row(level_name, str(count), f"{percentage:.1f}%")

    console.print(level_table)

    # School table
    school_table = Table(title="🏫 Spells by School")
    school_table.add_column("School", style="magenta")
    school_table.add_column("Count", justify="right", style="green")

    for school, count in sorted(school_counts.items()):
        school_table.add_row(school, str(count))

    console.print(school_table)

    return {
        "level_counts": level_counts,
        "school_counts": school_counts,
    }


def _analyze_creatures(creatures: list) -> dict:
    """Analyze creature-specific statistics."""
    from dnd5e.core.models.creatures import Creature

    # CR distribution
    cr_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}

    for creature in creatures:
        if isinstance(creature, Creature):
            cr = getattr(creature, "cr", "Unknown")
            cr_counts[cr] = cr_counts.get(cr, 0) + 1

            if creature.size:
                size = creature.size[0]
                size_counts[size] = size_counts.get(size, 0) + 1

            creature_type = str(creature.type)
            type_counts[creature_type] = type_counts.get(creature_type, 0) + 1

    # CR table (top 10)
    cr_table = Table(title="🐉 Creatures by Challenge Rating")
    cr_table.add_column("CR", style="red")
    cr_table.add_column("Count", justify="right", style="green")

    # Sort CRs numerically where possible
    def sort_cr(cr_str: str) -> float:
        try:
            if "/" in str(cr_str):
                # Handle fractional CRs like "1/2", "1/4"
                num, denom = str(cr_str).split("/")
                return float(num) / float(denom)
            return float(cr_str)
        except (ValueError, TypeError, ZeroDivisionError):
            # Put non-numeric CRs at the end for sorting
            return 999.0

    sorted_crs = sorted(cr_counts.items(), key=lambda x: sort_cr(x[0]))
    for cr, count in sorted_crs[:10]:
        cr_table.add_row(str(cr), str(count))

    console.print(cr_table)

    # Size table
    size_table = Table(title="📏 Creatures by Size")
    size_table.add_column("Size", style="blue")
    size_table.add_column("Count", justify="right", style="green")

    size_order = ["T", "S", "M", "L", "H", "G"]  # Tiny to Gargantuan
    size_names = {
        "T": "Tiny",
        "S": "Small",
        "M": "Medium",
        "L": "Large",
        "H": "Huge",
        "G": "Gargantuan",
    }

    for size_code in size_order:
        if size_code in size_counts:
            size_name = size_names.get(size_code, size_code)
            count = size_counts[size_code]
            size_table.add_row(size_name, str(count))

    console.print(size_table)

    return {
        "cr_counts": cr_counts,
        "size_counts": size_counts,
        "type_counts": type_counts,
    }


def _analyze_items(items: list) -> dict:
    """Analyze item-specific statistics."""
    from dnd5e.core.models.items import Item

    # Type and rarity distribution
    type_counts: dict[str, int] = {}
    rarity_counts: dict[str, int] = {}

    for item in items:
        if isinstance(item, Item):
            item_type = getattr(item, "type", "Unknown")
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

            rarity = getattr(item, "rarity", "Common")
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

    # Type table (top 10)
    type_table = Table(title="🎒 Items by Type")
    type_table.add_column("Type", style="cyan")
    type_table.add_column("Count", justify="right", style="green")

    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    for item_type, count in sorted_types[:10]:
        type_table.add_row(item_type, str(count))

    console.print(type_table)

    # Rarity table
    rarity_table = Table(title="💎 Items by Rarity")
    rarity_table.add_column("Rarity", style="yellow")
    rarity_table.add_column("Count", justify="right", style="green")

    rarity_order = ["common", "uncommon", "rare", "very rare", "legendary", "artifact"]
    for rarity in rarity_order:
        if rarity in rarity_counts:
            count = rarity_counts[rarity]
            rarity_table.add_row(rarity.title(), str(count))

    console.print(rarity_table)

    return {
        "type_counts": type_counts,
        "rarity_counts": rarity_counts,
    }


def _show_source_breakdown(content_items: list, content_type: str) -> None:
    """Show source breakdown for content items."""
    source_counts: dict[str, int] = {}

    for item in content_items:
        source = item.source.abbreviation
        source_counts[source] = source_counts.get(source, 0) + 1

    if source_counts:
        source_table = Table(title=f"📚 {content_type.title()}s by Source")
        source_table.add_column("Source", style="blue")
        source_table.add_column("Count", justify="right", style="green")
        source_table.add_column("Percentage", justify="right", style="yellow")

        total = len(content_items)
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)

        for source, count in sorted_sources:
            percentage = (count / total * 100) if total > 0 else 0
            source_table.add_row(source, str(count), f"{percentage:.1f}%")

        console.print(source_table)
