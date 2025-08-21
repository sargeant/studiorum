"""Items conversion command."""

import asyncio
import os
from enum import Enum
from pathlib import Path

import typer
from rich import print as rprint

from studiorum.cli.config_factory import (
    get_compile_pdf_default,
    get_document_class_default,
    get_with_images_default,
)
from studiorum.cli.display_manager import display_manager
from studiorum.cli.utils import get_omnidexer, get_tag_resolver
from studiorum.core.config.latex_config import LaTeXConfig
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.models.items import Item
from studiorum.renderers.core.interfaces import RenderingContext

from ..base import BaseConvertCommand
from ..shared import compile_pdf as compile_pdf_async


class ItemSortMode(str, Enum):
    """Sorting modes for item output."""

    TYPE = "type"
    NAME = "name"
    RARITY = "rarity"
    VALUE = "value"


def _render_itemcompendium(
    items: list[Item],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    sort_mode: ItemSortMode,
    show_toc: bool,
) -> str:
    """Render items using the itemcompendium template with flexible sorting."""
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    # Group items based on sort mode for template rendering
    if sort_mode == ItemSortMode.TYPE:
        # Group items by type
        items_by_group: dict[str, list[Item]] = {}
        for item in items:
            item_type = item.get_type_text()
            if item_type not in items_by_group:
                items_by_group[item_type] = []
            items_by_group[item_type].append(item)

        # Sort groups by type name
        sorted_groups = sorted(items_by_group.items())

    elif sort_mode == ItemSortMode.RARITY:
        # Group items by rarity
        items_by_group = {}
        rarity_order = [
            "common",
            "uncommon",
            "rare",
            "very rare",
            "legendary",
            "artifact",
        ]

        for item in items:
            rarity = item.get_rarity_text() or "common"
            if rarity not in items_by_group:
                items_by_group[rarity] = []
            items_by_group[rarity].append(item)

        # Sort groups by rarity order
        sorted_groups = []
        for rarity in rarity_order:
            if rarity in items_by_group:
                sorted_groups.append((rarity, items_by_group[rarity]))
        # Add any remaining rarities
        for rarity, items_list in items_by_group.items():
            if rarity not in rarity_order:
                sorted_groups.append((rarity, items_list))

    else:  # NAME or VALUE - single flat group
        sorted_groups = [("All Items", items)]

    # Create template engine and update with our LaTeX config
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(latex_config)

    # Create DND template context with proper styling settings
    template_context = template_engine.create_dnd_template_context(
        content_type="item",
        # Document metadata
        title=context.metadata.get("title", "Item Compendium"),
        metadata=context.metadata.get("document_metadata"),
        latex_config=latex_config,
        # Itemcompendium-specific data
        items=items,
        items_by_group=dict(sorted_groups),
        item_count=len(items),
        type_summary=context.metadata.get("type_summary", ""),
        rarity_summary=context.metadata.get("rarity_summary", ""),
        sources_used=context.metadata.get("sources_used", []),
        show_item_table_of_contents=show_toc,
    )

    # Render using itemcompendium template
    return template_engine.render_template("itemcompendium.tex.j2", template_context)


def items(
    # Direct item names as positional arguments
    item_names: list[str] = typer.Argument(
        None, help="Item names to include (e.g., 'bag of holding' 'sword of sharpness')"
    ),
    # Input sources
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        help="Read item names from file (one per line)",
        rich_help_panel="Search & Selection",
    ),
    from_stdin: bool = typer.Option(
        False,
        "--from-stdin",
        help="Read item names from stdin",
        rich_help_panel="Search & Selection",
    ),
    # Type-based filtering
    item_types: list[str] = typer.Option(
        None,
        "--type",
        help="Item types (e.g., weapon,armor)",
        rich_help_panel="Search & Selection",
    ),
    magic: bool = typer.Option(
        False,
        "--magic",
        help="Include only magic items",
        rich_help_panel="Search & Selection",
    ),
    mundane: bool = typer.Option(
        False,
        "--mundane",
        help="Include only non-magic items",
        rich_help_panel="Search & Selection",
    ),
    # Rarity filtering
    rarities: list[str] = typer.Option(
        None,
        "--rarity",
        help="Item rarities (e.g., common,uncommon)",
        rich_help_panel="Item Properties",
    ),
    # Value filtering
    value_range: str | None = typer.Option(
        None,
        "--value",
        help="Value range (e.g., '1-10', '<100')",
        rich_help_panel="Item Properties",
    ),
    max_value: float | None = typer.Option(
        None,
        "--max-value",
        help="Maximum value in gp",
        rich_help_panel="Item Properties",
    ),
    # Weight filtering
    max_weight: float | None = typer.Option(
        None,
        "--max-weight",
        help="Maximum weight in lbs",
        rich_help_panel="Item Properties",
    ),
    # Weapon filtering
    weapon_categories: list[str] = typer.Option(
        None,
        "--weapon-category",
        help="Weapon categories (martial,simple)",
        rich_help_panel="Equipment Filtering",
    ),
    weapon_properties: list[str] = typer.Option(
        None,
        "--weapon-property",
        help="Weapon properties (finesse,versatile)",
        rich_help_panel="Equipment Filtering",
    ),
    damage_types: list[str] = typer.Option(
        None,
        "--damage-type",
        help="Damage types (fire,cold)",
        rich_help_panel="Equipment Filtering",
    ),
    # Armor filtering
    armor_types: list[str] = typer.Option(
        None,
        "--armor-type",
        help="Armor types (light,medium,heavy)",
        rich_help_panel="Equipment Filtering",
    ),
    min_ac: int | None = typer.Option(
        None, "--min-ac", help="Minimum AC", rich_help_panel="Equipment Filtering"
    ),
    no_strength_req: bool = typer.Option(
        False,
        "--no-strength-req",
        help="No STR requirement",
        rich_help_panel="Equipment Filtering",
    ),
    no_stealth_disadvantage: bool = typer.Option(
        False,
        "--no-stealth",
        help="No stealth disadvantage",
        rich_help_panel="Equipment Filtering",
    ),
    # Magic item filtering
    requires_attunement: bool | None = typer.Option(
        None,
        "--attunement/--no-attunement",
        help="Filter by attunement requirement",
        rich_help_panel="Equipment Filtering",
    ),
    has_charges: bool | None = typer.Option(
        None,
        "--charges/--no-charges",
        help="Filter by charges/uses",
        rich_help_panel="Equipment Filtering",
    ),
    consumable: bool | None = typer.Option(
        None,
        "--consumable/--permanent",
        help="Filter for consumable items",
        rich_help_panel="Equipment Filtering",
    ),
    # Source filtering
    sources: list[str] = typer.Option(
        None,
        "--sources",
        help="Source abbreviations (PHB,DMG)",
        rich_help_panel="Equipment Filtering",
    ),
    # Standard document options
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output LaTeX file",
        rich_help_panel="Output Control",
    ),
    title: str | None = typer.Option(
        None, "--title", help="Document title", rich_help_panel="Output Control"
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(),
        "--pdf",
        help="Compile to PDF after conversion",
        rich_help_panel="Output Control",
    ),
    open_pdf: bool = typer.Option(
        False,
        "--open",
        help="Open PDF file after compilation (requires --pdf)",
        rich_help_panel="Output Control",
    ),
    # LaTeX document class options (inherited from other convert commands)
    document_class: str = typer.Option(
        get_document_class_default(),
        "--document-class",
        help="LaTeX document class (dndbook, dndarticle)",
        rich_help_panel="Document Layout",
    ),
    paper: str | None = typer.Option(
        None,
        "--paper",
        help="Paper size (letter, a4, a5)",
        rich_help_panel="Document Layout",
    ),
    fonts: str | None = typer.Option(
        None,
        "--fonts",
        help="Font package to use (wotc, dmsguild)",
        rich_help_panel="Visual Styling",
    ),
    no_outline: bool | None = typer.Option(
        None,
        "--no-outline",
        help="Disable document outline",
        rich_help_panel="Visual Styling",
    ),
    font_size: str | None = typer.Option(
        None,
        "--font-size",
        help="Base font size (10pt, 11pt, 12pt)",
        rich_help_panel="Visual Styling",
    ),
    background: str | None = typer.Option(
        None,
        "--background",
        "--bg",
        help="Background style (full, none, print)",
        rich_help_panel="Visual Styling",
    ),
    high_contrast: bool | None = typer.Option(
        None,
        "--high-contrast",
        help="Use high contrast mode",
        rich_help_panel="Visual Styling",
    ),
    two_column: bool | None = typer.Option(
        None,
        "--two-column/--one-column",
        help="Use two-column layout",
        rich_help_panel="Document Layout",
    ),
    justified: bool | None = typer.Option(
        None,
        "--justified/--not-justified",
        help="Justify text columns",
        rich_help_panel="Document Layout",
    ),
    with_images: bool = typer.Option(
        get_with_images_default(),
        "--images/--no-images",
        help="Include images",
        rich_help_panel="Visual Styling",
    ),
    sort: ItemSortMode = typer.Option(
        ItemSortMode.TYPE,
        "--sort",
        help="Sort order: 'type' (group by type, default), 'name' (alphabetical), 'rarity', or 'value'",
        rich_help_panel="Output Control",
    ),
    show_toc: bool = typer.Option(
        True,
        "--toc/--no-toc",
        help="Show table of contents (default: enabled)",
        rich_help_panel="Output Control",
    ),
) -> None:
    """
    🎒 Convert items to LaTeX item compendium

    Create beautifully formatted item compendiums from 5e.tools item data.
    Supports both specific item lists (treasure hoard use case) and
    type/rarity-based filtering (shop/equipment use case).

    \\b
    Examples:
      # Specific items (treasure hoard use case)
      5e2pdf convert items "bag of holding" "sword of sharpness" "potion of healing"
      5e2pdf convert items --from-file treasure-hoard.txt

      # Type-based filtering (shop use case)
      5e2pdf convert items --type weapon --rarity common,uncommon
      5e2pdf convert items --type "adventuring gear" --max-value 10

      # Magic item filtering
      5e2pdf convert items --magic --attunement --sources DMG,XGE
      5e2pdf convert items --rarity rare,very rare --charges

      # Sorting options
      5e2pdf convert items --type weapon --sort type     # Group by type (default)
      5e2pdf convert items --type armor --sort rarity    # Group by rarity
      5e2pdf convert items --magic --sort value          # Sort by value
    """

    def _convert() -> None:
        try:
            # Import item-specific modules
            from studiorum.core.models.item_filters import ItemFilterCriteria
            from studiorum.core.parsers.item_input import ItemInputParser
            from studiorum.core.services.item_collector import ItemCollector

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading item data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Parse input sources and build criteria
            all_item_names = []

            # Collect item names from arguments
            if item_names:
                all_item_names.extend(item_names)

            # Collect from file using ContentLoader system
            if from_file:
                command_instance = BaseConvertCommand()
                file_items = command_instance.get_name_list_from_file(from_file, "item")
                all_item_names.extend(file_items)
                rprint(
                    f"[green]Loaded {len(file_items)} items from {from_file}[/green]"
                )

            # Collect from stdin using ContentLoader system
            if from_stdin:
                try:
                    import sys

                    if sys.stdin.isatty():
                        rprint("[red]Error:[/red] No input provided via stdin")
                        raise typer.Exit(1)

                    stdin_lines = []
                    for line in sys.stdin:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Handle inline comments
                            if "#" in line:
                                line = line.split("#", 1)[0].strip()
                            if line:
                                stdin_lines.append(line)

                    if not stdin_lines:
                        rprint("[red]Error:[/red] No item names found in stdin")
                        raise typer.Exit(1)

                    all_item_names.extend(stdin_lines)
                    rprint(f"[green]Loaded {len(stdin_lines)} items from stdin[/green]")
                except KeyboardInterrupt:
                    rprint("[red]Error:[/red] Input interrupted")
                    raise typer.Exit(1)

            # Parse value range if provided
            min_value, max_value_parsed = None, None
            if value_range:
                try:
                    min_value, max_value_parsed = ItemInputParser.parse_value_range(
                        value_range
                    )
                except ValueError as e:
                    rprint(f"[red]Error:[/red] Invalid value range: {e}")
                    raise typer.Exit(1)

            # Use max_value option if provided, otherwise use parsed max_value
            effective_max_value = (
                max_value if max_value is not None else max_value_parsed
            )

            # Parse type list
            parsed_types = None
            if item_types:
                parsed_types = []
                for type_list in item_types:
                    parsed_types.extend(ItemInputParser.parse_type_list(type_list))

            # Parse rarity list
            parsed_rarities = None
            if rarities:
                parsed_rarities = []
                for rarity_list in rarities:
                    parsed_rarities.extend(
                        ItemInputParser.parse_rarity_list(rarity_list)
                    )

            # Parse source list
            parsed_sources = None
            if sources:
                parsed_sources = []
                for src_list in sources:
                    parsed_sources.extend(ItemInputParser.parse_source_list(src_list))

            # Build filter criteria
            try:
                criteria = ItemFilterCriteria(
                    item_types=parsed_types,
                    rarities=parsed_rarities,
                    magic_only=magic,
                    mundane_only=mundane,
                    min_value=min_value,
                    max_value=effective_max_value,
                    max_weight=max_weight,
                    weapon_categories=weapon_categories,
                    weapon_properties=weapon_properties,
                    damage_types=damage_types,
                    armor_types=armor_types,
                    min_ac=min_ac,
                    no_strength_req=no_strength_req,
                    no_stealth_disadvantage=no_stealth_disadvantage,
                    requires_attunement=requires_attunement,
                    has_charges=has_charges,
                    consumable=consumable,
                    sources=parsed_sources,
                    item_names=all_item_names if all_item_names else None,
                )
            except ValueError as e:
                rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
                raise typer.Exit(1)

            # Collect items using ItemCollector
            collector = ItemCollector(omnidexer)

            with display_manager.progress("Collecting items") as _:
                collect_task = display_manager.add_task(
                    "[cyan]Filtering items...", total=None
                )
                result = collector.collect_items(criteria)
                display_manager.update_task(collect_task, completed=100)

            # Handle unresolved items
            if result.unresolved_names:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} items could not be found:"
                )
                for name in result.unresolved_names:
                    rprint(f"  • {name}")
                    if name in result.suggestions and result.suggestions[name]:
                        rprint(
                            f"    Suggestions: {', '.join(result.suggestions[name][:3])}"
                        )
                rprint()

            if not result.items:
                rprint("[red]Error:[/red] No items found matching criteria")
                if result.unresolved_names and any(result.suggestions.values()):
                    rprint(
                        "[yellow]Try using one of the suggested item names above.[/yellow]"
                    )
                raise typer.Exit(1)

            # Sort items based on the sort mode
            if sort == ItemSortMode.TYPE:
                # Sort by type, then alphabetically (default behavior)
                sorted_items = sorted(
                    result.items,
                    key=lambda i: (i.get_type_text().lower(), i.name.lower()),
                )
            elif sort == ItemSortMode.RARITY:
                # Sort by rarity, then alphabetically
                rarity_order = {
                    "common": 0,
                    "uncommon": 1,
                    "rare": 2,
                    "very rare": 3,
                    "legendary": 4,
                    "artifact": 5,
                }
                sorted_items = sorted(
                    result.items,
                    key=lambda i: (
                        rarity_order.get(i.get_rarity_text().lower(), 99),
                        i.name.lower(),
                    ),
                )
            elif sort == ItemSortMode.VALUE:
                # Sort by value, then alphabetically
                def get_sort_value(item: Item) -> tuple[float, str]:
                    # Get value in GP for sorting, use 0 for items without value
                    value_gp = collector._get_item_value_in_gp(item) or 0.0
                    return (value_gp, item.name.lower())

                sorted_items = sorted(result.items, key=get_sort_value)
            else:  # ItemSortMode.NAME
                # Sort alphabetically by name only
                sorted_items = sorted(result.items, key=lambda i: i.name.lower())

            rprint(f"[green]Found {result.total_count} items:[/green]")
            rprint(f"  {result.get_type_summary()}")
            rprint(f"  {result.get_rarity_summary()}")
            if result.sources_used:
                rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
            rprint()

            # Determine output file
            if output_file is None:
                output_path = Path("output/items") / "itemcompendium.tex"
            else:
                output_path = output_file

            # Create LaTeX configuration using base class
            command_instance = BaseConvertCommand()
            config = command_instance.apply_config_hierarchy(
                paper=paper,
                fonts=fonts,
                background=background,
                no_outline=no_outline,
                font_size=font_size,
                high_contrast=high_contrast,
                two_column=two_column,
                justified=justified,
            )

            from studiorum.core.config.latex_config import (
                LaTeXConfig,
                LaTeXDocumentConfig,
            )

            latex_doc_config = LaTeXDocumentConfig(
                document_class=document_class,
                paper_size=config["paper_size"],
                font_size=config["font_size"],
                background=config["background"],
                high_contrast=config["high_contrast"],
                two_column=config["two_column"],
                justified_text=config["justified"],
                fonts=config["fonts"],
                no_outline=config["no_outline"],
            )
            latex_config = LaTeXConfig(document=latex_doc_config)

            # Create document metadata
            from studiorum.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            item_title = title or "Item Compendium"
            if parsed_types and len(parsed_types) == 1:
                type_name = str(parsed_types[0])
                if hasattr(parsed_types[0], "value"):
                    type_name = parsed_types[0].value
                item_title = title or f"{type_name.title()} Collection"
            elif parsed_rarities and len(parsed_rarities) == 1:
                rarity_name = str(parsed_rarities[0])
                if hasattr(parsed_rarities[0], "value"):
                    rarity_name = parsed_rarities[0].value
                item_title = title or f"{rarity_name.title()} Items"

            metadata = DocumentMetadata(
                title=item_title,
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,  # Use adventure type for now
                include_toc=True,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=f"Collection of {len(sorted_items)} items",
                use_parts=False,
            )

            # Create render context with itemcompendium-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": item_title,
                    "include_images": with_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "item_count": len(sorted_items),
                    "type_summary": result.get_type_summary(),
                    "rarity_summary": result.get_rarity_summary(),
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "itemcompendium",  # Use itemcompendium template
                },
            )

            # Render document using custom itemcompendium rendering
            with display_manager.progress("Rendering item compendium") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering item compendium...", total=None
                )
                latex_result = _render_itemcompendium(
                    sorted_items,
                    context,
                    latex_config,
                    sort,
                    show_toc,
                )
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if latex_result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(latex_result)
                rprint(f"[green]✓[/green] Item compendium generated: {output_path}")
            else:
                rprint("[red]Error:[/red] No LaTeX content was generated")
                raise typer.Exit(1)

            # Compile PDF if requested
            if compile_pdf:
                asyncio.run(compile_pdf_async(output_path, open_pdf))

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()
