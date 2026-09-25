"""convert spells: a spellbook."""

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.models.spells import Spell
from studiorum.renderers.context import RenderingContext

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

if TYPE_CHECKING:
    from studiorum.latex_engine.document import DocumentChapter

SELECT = "Search & Selection"
PROPERTIES = "Spell Properties"
COMBAT = "Combat & Effects"


class SpellSortMode(StrEnum):
    """Sorting modes for spell output."""

    LEVEL = "level"
    NAME = "name"


S, P, C = SELECT, PROPERTIES, COMBAT
Strings = list[str] | None
Maybe = bool | None
Names = Annotated[
    Strings,
    typer.Argument(help="Spell names to include (e.g., 'fireball' 'magic missile')"),
]
FromFile = Annotated[
    Path | None,
    option("--from-file", text="Read spell names from file (one per line)", panel=S),
]
FromStdin = Annotated[
    bool, option("--from-stdin", text="Read spell names from stdin", panel=S)
]
Classes = Annotated[
    Strings,
    option("--class", text="Spellcaster classes (e.g., wizard,cleric)", panel=S),
]
Level = Annotated[
    str | None,
    option(
        "--level", text="Level range (e.g., '1-5', '3+', '0' for cantrips)", panel=S
    ),
]
MaxLevel = Annotated[
    int | None, option("--max-level", text="Maximum spell level (0-9)", panel=S)
]
Schools = Annotated[
    Strings,
    option("--school", text="Schools of magic (e.g., evocation,abjuration)", panel=P),
]
Verbal = Annotated[
    Maybe, option("--verbal/--no-verbal", text="Filter by verbal components", panel=P)
]
Somatic = Annotated[
    Maybe,
    option("--somatic/--no-somatic", text="Filter by somatic components", panel=P),
]
Material = Annotated[
    Maybe,
    option("--material/--no-material", text="Filter by material components", panel=P),
]
Concentration = Annotated[
    Maybe,
    option(
        "--concentration/--no-concentration", text="Filter by concentration", panel=P
    ),
]
Ritual = Annotated[
    Maybe, option("--ritual/--no-ritual", text="Filter by ritual casting", panel=P)
]
DamageTypes = Annotated[
    Strings, option("--damage-type", text="Damage types (e.g., fire,cold)", panel=C)
]
Saves = Annotated[
    Strings, option("--save", text="Saving throw types (e.g., dex,wis)", panel=C)
]
AttackSpells = Annotated[
    Maybe,
    option(
        "--attack-spell/--no-attack-spell",
        text="Filter for spell attack rolls",
        panel=C,
    ),
]
Sources = Annotated[
    Strings, option("--sources", text="Source abbreviations (e.g., PHB,XGE)", panel=C)
]
Sort = Annotated[
    SpellSortMode,
    option(
        "--sort",
        text="Sort order: 'level' (group by level, default) or 'name' (alphabetical)",
        panel=opt.OUTPUT,
    ),
]
Optional = Annotated[
    bool,
    option(
        "--optional-spells",
        text="Include optional/variant class spells",
        panel=opt.OUTPUT,
    ),
]
Creatures = Annotated[
    bool,
    option(
        "--creatures/--no-creatures",
        text="Generate creatures appendix with spell-referenced creatures",
        panel=opt.OUTPUT,
    ),
]


def spells(
    ctx: typer.Context,
    spell_names: Names = None,
    from_file: FromFile = None,
    from_stdin: FromStdin = False,
    classes: Classes = None,
    level: Level = None,
    max_level: MaxLevel = None,
    schools: Schools = None,
    verbal: Verbal = None,
    somatic: Somatic = None,
    material: Material = None,
    concentration: Concentration = None,
    ritual: Ritual = None,
    damage_types: DamageTypes = None,
    saving_throws: Saves = None,
    attack_spells: AttackSpells = None,
    sources: Sources = None,
    sort: Sort = SpellSortMode.LEVEL,
    include_optional: Optional = False,
    creatures: Creatures = False,
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
    🔮 Convert spells to LaTeX spell book

    Select spells by name or file (the wizard's list), or by class and level
    (the cleric's list), and narrow them with the property filters.

    \\b
    Examples:
      studiorum convert spells "fireball" "magic missile" "counterspell"
      studiorum convert spells --from-file my-spells.txt
      studiorum convert spells --class cleric --level 1-5
      studiorum convert spells --class wizard --school evocation --sort name
      studiorum convert spells --damage-type fire --no-material
    """
    from studiorum.core.parsers.spell_input import SpellInputParser

    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        omnidexer = load_data("spell")

        names = read_names(spell_names, from_file, from_stdin, "spell")
        parsed_classes = _parse(SpellInputParser.parse_class_list, classes)
        result = _collect(omnidexer, ctx.params, names, parsed_classes)
        report_collection(result, result.spells, "spell")

        if sort == SpellSortMode.LEVEL:
            found = sorted(result.spells, key=lambda s: (s.level, s.name.lower()))
            by_level: dict[int, list[Spell]] = {}
            for spell in found:
                by_level.setdefault(spell.level, []).append(spell)
        else:
            found = sorted(result.spells, key=lambda s: s.name.lower())
            by_level = {999: found}  # one flat group

        rprint(f"[green]Found {result.total_count} spells:[/green]")
        rprint(f"  {result.get_level_summary()}")
        if result.sources_used:
            rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
        rprint()

        heading = "Spell Collection"
        if parsed_classes and len(parsed_classes) == 1:
            heading = f"{parsed_classes[0].title()} Spell Book"
        elif parsed_classes:
            heading = (
                f"Spell Collection ({', '.join(c.title() for c in parsed_classes)})"
            )
        heading = options.title or heading

        found_fluff = (
            collect_fluff(
                omnidexer,
                found,
                "spell",
                sections=fluff_sections,
                sources=fluff_sources,
                with_images=with_fluff_images,
            )
            if fluff
            else None
        )
        tracker = None
        if creatures:
            from studiorum.core.references.content_reference_manager import (
                ContentReferenceManager,
            )

            tracker = ContentReferenceManager(omnidexer=omnidexer).get_content_tracker()
        context = RenderingContext(
            output_format="latex",
            omnidexer=omnidexer,
            content_tracker=tracker,
            metadata={
                "title": heading,
                "include_images": options.images,
                "template": "spellbook",
                "content_type": "spell",
                "fluff": found_fluff.fluff if found_fluff else {},
                "fluff_images": found_fluff.images if found_fluff else {},
                "fluff_images_enabled": with_fluff_images,
            },
        )
        latex = _render_spellbook(
            found,
            by_level,
            context,
            options,
            heading,
            result,
            _creature_appendix(context) if tracker else None,
        )
        write_document(
            options, latex, Path("output/spells/spellbook.tex"), "Spellbook generated"
        )


def _creature_appendix(
    context: RenderingContext,
) -> Callable[[], list["DocumentChapter"]]:
    """The appendix of creatures the spells name, built once the body is rendered."""

    def appendices() -> list["DocumentChapter"]:
        from studiorum.core.services.appendix_generator import (
            AppendixFlags,
            AppendixGenerator,
        )
        from studiorum.latex_engine.document import appendices_as_chapters

        found = AppendixGenerator(context.omnidexer).generate_appendices(
            context.content_tracker, AppendixFlags(creatures=True)
        )
        return appendices_as_chapters(found, context)

    return appendices


def _parse(parser: Any, values: list[str] | None) -> list[Any] | None:
    """Run a SpellInputParser list parser over each repeated option value."""
    if not values:
        return None
    return [item for value in values for item in parser(value)]


def _collect(
    omnidexer: Any, params: dict[str, Any], names: NameList, classes: list[str] | None
) -> Any:
    """Build the filter criteria from the command's parameters and collect."""
    from studiorum.core.models.spell_filters import SpellFilterCriteria
    from studiorum.core.parsers.spell_input import SpellInputParser
    from studiorum.core.services.spell_collector import SpellCollector

    min_level, max_level = None, None
    if params["level"]:
        try:
            min_level, max_level = SpellInputParser.parse_level_range(params["level"])
        except ValueError as e:
            rprint(f"[red]Error:[/red] Invalid level range: {e}")
            raise typer.Exit(1) from None
    try:
        criteria = SpellFilterCriteria(
            min_level=min_level,
            max_level=params["max_level"]
            if params["max_level"] is not None
            else max_level,
            classes=classes,
            include_optional=params["include_optional"],
            schools=params["schools"] or None,
            has_verbal=params["verbal"],
            has_somatic=params["somatic"],
            has_material=params["material"],
            concentration=params["concentration"],
            ritual=params["ritual"],
            damage_types=params["damage_types"] or None,
            saving_throws=params["saving_throws"] or None,
            attack_spells=params["attack_spells"],
            sources=_parse(SpellInputParser.parse_source_list, params["sources"]),
            spell_names=names.names or None,
        )
    except ValueError as e:
        rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
        raise typer.Exit(1) from None

    with display_manager.progress("Collecting spells") as _:
        task = display_manager.add_task("[cyan]Filtering spells...", total=None)
        result = SpellCollector(omnidexer).collect_spells(criteria)
        display_manager.update_task(task, completed=100)
    return result


def _ordinal_number(n: int) -> str:
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
    suffix = "th" if 10 <= n <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _render_spellbook(
    spells: list[Spell],
    by_level: dict[int, list[Spell]],
    context: RenderingContext,
    options: ConvertOptions,
    heading: str,
    result: Any,
    appendices: Callable[[], list["DocumentChapter"]] | None = None,
) -> str:
    """Render spells using the spellbook template."""
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(options.latex)
    template_context = template_engine.create_dnd_template_context(
        content_type="spell",
        title=heading,
        metadata=document_metadata(options, heading),
        latex_config=options.latex,
        spells=spells,
        spells_by_level={level: by_level[level] for level in sorted(by_level)},
        spell_count=len(spells),
        spell_summary=result.get_level_summary(),
        sources_used=list(result.sources_used or []),
        show_spell_table_of_contents=options.document.show_toc,
        ordinal=_ordinal_number,
        rendering_context=context,
    )
    if appendices is not None:
        template_context["appendices"] = appendices
    with display_manager.progress("Rendering spellbook") as _:
        task = display_manager.add_task("[green]Rendering spellbook...", total=None)
        latex = template_engine.render_template("spellbook.tex.j2", template_context)
        display_manager.update_task(task, completed=100)
    return latex
