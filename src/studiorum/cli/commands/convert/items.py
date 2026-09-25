"""convert items: an item compendium."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.models.items import Item
from studiorum.renderers.context import RenderingContext, Style

from . import options as opt
from .fluff import Fluff, FluffImages, FluffSections, FluffSources, collect_fluff
from .options import ConvertOptions, option
from .run import (
    NameList,
    conversion_errors,
    document_metadata,
    load_data,
    read_names,
    report_collection,
    write_document,
)

SELECT = "Search & Selection"
PROPERTIES = "Item Properties"
EQUIPMENT = "Equipment Filtering"
RARITY_ORDER = ["common", "uncommon", "rare", "very rare", "legendary", "artifact"]


class ItemSortMode(StrEnum):
    """Sorting modes for item output."""

    TYPE = "type"
    NAME = "name"
    RARITY = "rarity"
    VALUE = "value"


S, P, E = SELECT, PROPERTIES, EQUIPMENT
Strings = list[str] | None
Maybe = bool | None
Names = Annotated[
    Strings,
    typer.Argument(
        help="Item names to include (e.g., 'bag of holding' 'sword of sharpness')"
    ),
]
FromFile = Annotated[
    Path | None,
    option("--from-file", text="Read item names from file (one per line)", panel=S),
]
FromStdin = Annotated[
    bool, option("--from-stdin", text="Read item names from stdin", panel=S)
]
Types = Annotated[
    Strings, option("--type", text="Item types (e.g., weapon,armor)", panel=S)
]
Magic = Annotated[bool, option("--magic", text="Include only magic items", panel=S)]
Mundane = Annotated[
    bool, option("--mundane", text="Include only non-magic items", panel=S)
]
Rarities = Annotated[
    Strings, option("--rarity", text="Item rarities (e.g., common,uncommon)", panel=P)
]
ValueRange = Annotated[
    str | None, option("--value", text="Value range (e.g., '1-10', '<100')", panel=P)
]
MaxValue = Annotated[
    float | None, option("--max-value", text="Maximum value in gp", panel=P)
]
MaxWeight = Annotated[
    float | None, option("--max-weight", text="Maximum weight in lbs", panel=P)
]
WeaponCategories = Annotated[
    Strings,
    option("--weapon-category", text="Weapon categories (martial,simple)", panel=E),
]
WeaponProperties = Annotated[
    Strings,
    option("--weapon-property", text="Weapon properties (finesse,versatile)", panel=E),
]
DamageTypes = Annotated[
    Strings, option("--damage-type", text="Damage types (fire,cold)", panel=E)
]
ArmorTypes = Annotated[
    Strings, option("--armor-type", text="Armor types (light,medium,heavy)", panel=E)
]
MinAc = Annotated[int | None, option("--min-ac", text="Minimum AC", panel=E)]
NoStrength = Annotated[
    bool, option("--no-strength-req", text="No STR requirement", panel=E)
]
NoStealth = Annotated[
    bool, option("--no-stealth", text="No stealth disadvantage", panel=E)
]
Attunement = Annotated[
    Maybe,
    option(
        "--attunement/--no-attunement", text="Filter by attunement requirement", panel=E
    ),
]
Charges = Annotated[
    Maybe, option("--charges/--no-charges", text="Filter by charges/uses", panel=E)
]
Consumable = Annotated[
    Maybe,
    option("--consumable/--permanent", text="Filter for consumable items", panel=E),
]
Sources = Annotated[
    Strings, option("--sources", text="Source abbreviations (PHB,DMG)", panel=E)
]
Sort = Annotated[
    ItemSortMode,
    option(
        "--sort",
        text="Sort order: 'type' (group by type, default), 'name' (alphabetical), 'rarity', or 'value'",
        panel=opt.OUTPUT,
    ),
]


def items(
    ctx: typer.Context,
    item_names: Names = None,
    from_file: FromFile = None,
    from_stdin: FromStdin = False,
    item_types: Types = None,
    magic: Magic = False,
    mundane: Mundane = False,
    rarities: Rarities = None,
    value_range: ValueRange = None,
    max_value: MaxValue = None,
    max_weight: MaxWeight = None,
    weapon_categories: WeaponCategories = None,
    weapon_properties: WeaponProperties = None,
    damage_types: DamageTypes = None,
    armor_types: ArmorTypes = None,
    min_ac: MinAc = None,
    no_strength_req: NoStrength = False,
    no_stealth_disadvantage: NoStealth = False,
    requires_attunement: Attunement = None,
    has_charges: Charges = None,
    consumable: Consumable = None,
    sources: Sources = None,
    sort: Sort = ItemSortMode.TYPE,
    fluff: Fluff = False,
    fluff_sections: FluffSections = None,
    fluff_sources: FluffSources = None,
    with_fluff_images: FluffImages = False,
    # Shared options, read through ctx.params by ConvertOptions
    output: opt.Output = None,
    title: opt.Title = None,
    pdf: opt.Pdf = None,
    open_pdf: opt.OpenPdf = False,
    toc: opt.Toc = None,
    index: opt.Index = None,
    images: opt.Images = None,
    document_class: opt.DocumentClass = None,
    paper: opt.Paper = None,
    two_column: opt.TwoColumn = None,
    justified: opt.Justified = None,
    fonts: opt.Fonts = None,
    font_size: opt.FontSize = None,
    background: opt.Background = None,
    outline: opt.Outline = None,
    high_contrast: opt.HighContrast = None,
    statblock: opt.Statblock = None,
) -> None:
    """
    🎒 Convert items to LaTeX item compendium

    Select items by name or file (a treasure hoard), or by type, rarity and
    value (a shop).

    \\b
    Examples:
      studiorum convert items "bag of holding" "sword of sharpness"
      studiorum convert items --from-file treasure-hoard.txt
      studiorum convert items --type weapon --rarity common,uncommon
      studiorum convert items --magic --attunement --sources DMG,XGE
      studiorum convert items --type armor --sort rarity
    """
    from studiorum.core.parsers.item_input import ItemInputParser

    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        omnidexer = load_data("item")

        names = read_names(item_names, from_file, from_stdin, "item")
        types = _parse(ItemInputParser.parse_type_list, item_types)
        parsed_rarities = _parse(ItemInputParser.parse_rarity_list, rarities)
        collector, result = _collect(
            omnidexer, ctx.params, names, types, parsed_rarities
        )
        report_collection(result, result.items, "item")
        found = _sort_items(result.items, sort, collector)

        rprint(f"[green]Found {result.total_count} items:[/green]")
        rprint(f"  {result.get_type_summary()}")
        rprint(f"  {result.get_rarity_summary()}")
        if result.sources_used:
            rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
        rprint()

        heading = "Item Compendium"
        if types and len(types) == 1:
            heading = f"{getattr(types[0], 'value', str(types[0])).title()} Collection"
        elif parsed_rarities and len(parsed_rarities) == 1:
            rarity = parsed_rarities[0]
            heading = f"{getattr(rarity, 'value', str(rarity)).title()} Items"
        heading = options.title or heading

        found_fluff = (
            collect_fluff(
                omnidexer,
                found,
                "item",
                sections=fluff_sections,
                sources=fluff_sources,
                with_images=with_fluff_images,
            )
            if fluff
            else None
        )
        context = RenderingContext(
            omnidexer=omnidexer,
            style=Style(content_type="item", images=options.images),
            fluff=found_fluff.fluff if found_fluff else {},
            fluff_images=(found_fluff.images if found_fluff else {})
            if with_fluff_images
            else None,
        )
        latex = _render_itemcompendium(found, context, options, heading, result, sort)
        write_document(
            options,
            latex,
            Path("output/items/itemcompendium.tex"),
            "Item compendium generated",
        )


def _parse(parser: Any, values: list[str] | None) -> list[Any] | None:
    """Run an ItemInputParser list parser over each repeated option value."""
    if not values:
        return None
    return [item for value in values for item in parser(value)]


def _collect(
    omnidexer: Any,
    params: dict[str, Any],
    names: NameList,
    types: list[Any] | None,
    rarities: list[Any] | None,
) -> tuple[Any, Any]:
    """Build the filter criteria from the command's parameters and collect."""
    from studiorum.core.models.item_filters import ItemFilterCriteria
    from studiorum.core.parsers.item_input import ItemInputParser
    from studiorum.core.services.item_collector import ItemCollector

    min_value, max_value = None, None
    if params["value_range"]:
        try:
            min_value, max_value = ItemInputParser.parse_value_range(
                params["value_range"]
            )
        except ValueError as e:
            rprint(f"[red]Error:[/red] Invalid value range: {e}")
            raise typer.Exit(1) from None
    lists = ("weapon_categories", "weapon_properties", "damage_types", "armor_types")
    scalars = (
        "max_weight",
        "min_ac",
        "no_strength_req",
        "no_stealth_disadvantage",
        "requires_attunement",
        "has_charges",
        "consumable",
    )
    try:
        criteria = ItemFilterCriteria(
            item_types=types,
            rarities=rarities,
            magic_only=params["magic"],
            mundane_only=params["mundane"],
            min_value=min_value,
            max_value=params["max_value"]
            if params["max_value"] is not None
            else max_value,
            sources=_parse(ItemInputParser.parse_source_list, params["sources"]),
            item_names=names.names or None,
            **{name: params[name] or None for name in lists},
            **{name: params[name] for name in scalars},
        )
    except ValueError as e:
        rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
        raise typer.Exit(1) from None

    collector = ItemCollector(omnidexer)
    with display_manager.progress("Collecting items") as _:
        task = display_manager.add_task("[cyan]Filtering items...", total=None)
        result = collector.collect_items(criteria)
        display_manager.update_task(task, completed=100)
    return collector, result


def _sort_items(
    items: list[Item], sort_mode: ItemSortMode, collector: Any
) -> list[Item]:
    """Sort by the sort mode, then by name."""
    rank = {rarity: i for i, rarity in enumerate(RARITY_ORDER)}
    keys: dict[ItemSortMode, Any] = {
        ItemSortMode.TYPE: lambda i: i.get_kind_text().lower(),
        ItemSortMode.RARITY: lambda i: rank.get(i.get_rarity_text().lower(), 99),
        ItemSortMode.VALUE: lambda i: collector._get_item_value_in_gp(i) or 0.0,
        ItemSortMode.NAME: lambda i: "",
    }
    key = keys[sort_mode]
    return sorted(items, key=lambda i: (key(i), i.name.lower()))


def _group_items(items: list[Item], sort_mode: ItemSortMode) -> dict[str, list[Item]]:
    """The compendium's headings and the items under each."""
    groups: dict[str, list[Item]] = {}
    if sort_mode == ItemSortMode.TYPE:
        for item in items:
            groups.setdefault(item.get_kind_text(), []).append(item)
        return dict(sorted(groups.items()))
    if sort_mode == ItemSortMode.RARITY:
        for item in items:
            groups.setdefault(item.get_rarity_text() or "common", []).append(item)
        known = [(r, groups[r]) for r in RARITY_ORDER if r in groups]
        return dict(
            known + [(r, g) for r, g in groups.items() if r not in RARITY_ORDER]
        )
    return {"All Items": items}


def _render_itemcompendium(
    items: list[Item],
    context: RenderingContext,
    options: ConvertOptions,
    heading: str,
    result: Any,
    sort_mode: ItemSortMode,
) -> str:
    """Render items using the itemcompendium template."""
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(options.latex)
    template_context = template_engine.create_dnd_template_context(
        content_type="item",
        title=heading,
        metadata=document_metadata(options, heading),
        latex_config=options.latex,
        items=items,
        items_by_group=_group_items(items, sort_mode),
        item_count=len(items),
        type_summary=result.get_type_summary(),
        rarity_summary=result.get_rarity_summary(),
        sources_used=list(result.sources_used or []),
        show_item_table_of_contents=options.document.show_toc,
        rendering_context=context,
    )
    with display_manager.progress("Rendering item compendium") as _:
        task = display_manager.add_task(
            "[green]Rendering item compendium...", total=None
        )
        latex = template_engine.render_template(
            "itemcompendium.tex.j2", template_context
        )
        display_manager.update_task(task, completed=100)
    return latex
