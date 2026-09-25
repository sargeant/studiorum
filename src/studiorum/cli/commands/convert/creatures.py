"""convert creatures: a bestiary or a token sheet."""

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.models.creatures import Creature
from studiorum.renderers.context import RenderingContext

from . import options as opt
from .fluff import (
    Fluff,
    FluffImages,
    FluffResult,
    FluffSections,
    FluffSources,
    collect_fluff,
)
from .options import ConvertOptions, option
from .run import (
    NameList,
    conversion_errors,
    document_metadata,
    load_data,
    read_names,
    report_collection,
    split_csv,
    write_document,
)

if TYPE_CHECKING:
    from studiorum.latex_engine.document import DocumentChapter

SELECT = "Search & Selection"
FILTER = "Advanced Filtering"
TOKENS = "Token Generation"


class CreatureSortMode(StrEnum):
    """Sorting modes for creature output."""

    CR = "cr"  # Group by challenge rating (default)
    TYPE = "type"  # Group by creature type
    GROUP = "group"  # Group by 5etools 'group' field
    NAME = "name"  # Alphabetical
    SIZE = "size"  # Group by size category
    ALIGNMENT = "alignment"  # Group by alignment


S, F, T, C = SELECT, FILTER, TOKENS, "Content Enhancement"
Strings = list[str] | None
Names = Annotated[Strings, typer.Argument(help="Creature names to include")]
Tokens = Annotated[
    bool,
    option("--tokens", text="Generate tokens instead of statblocks", panel=opt.OUTPUT),
]
FromFile = Annotated[
    Path | None,
    option("--from-file", text="Read creature names from file (one per line)", panel=S),
]
FromStdin = Annotated[
    bool, option("--from-stdin", text="Read creature names from stdin", panel=S)
]
CrRange = Annotated[
    str | None,
    option(
        "--cr", text="Challenge rating range (e.g., '1-5', '1/4-2', '10+')", panel=S
    ),
]
MinCr = Annotated[
    float | None, option("--min-cr", text="Minimum challenge rating", panel=S)
]
MaxCr = Annotated[
    float | None, option("--max-cr", text="Maximum challenge rating", panel=S)
]
Types = Annotated[
    Strings,
    option("--type", text="Creature types (humanoid,dragon,giant,etc.)", panel=S),
]
Tags = Annotated[
    Strings, option("--tag", text="Creature tags (demon,devil,aarakocra,etc.)", panel=S)
]
Sizes = Annotated[
    Strings,
    option(
        "--size",
        text="Creature sizes (tiny,small,medium,large,huge,gargantuan)",
        panel=S,
    ),
]
Alignments = Annotated[
    Strings, option("--alignment", text="Creature alignments", panel=S)
]
MinAc = Annotated[int | None, option("--min-ac", text="Minimum armor class", panel=F)]
MaxAc = Annotated[int | None, option("--max-ac", text="Maximum armor class", panel=F)]
MinHp = Annotated[int | None, option("--min-hp", text="Minimum hit points", panel=F)]
MaxHp = Annotated[int | None, option("--max-hp", text="Maximum hit points", panel=F)]
Maybe = bool | None
Spellcasting = Annotated[
    Maybe,
    option(
        "--spellcasting/--no-spellcasting",
        text="Filter by spellcasting ability",
        panel=F,
    ),
]
Legendary = Annotated[
    Maybe,
    option("--legendary/--no-legendary", text="Filter by legendary actions", panel=F),
]
Multiattack = Annotated[
    Maybe,
    option(
        "--multiattack/--no-multiattack", text="Filter by multiattack ability", panel=F
    ),
]
Reactions = Annotated[
    Maybe,
    option("--reactions/--no-reactions", text="Filter by reaction abilities", panel=F),
]
Fly = Annotated[
    Maybe, option("--fly/--no-fly", text="Filter by flying movement", panel=F)
]
Swim = Annotated[
    Maybe, option("--swim/--no-swim", text="Filter by swimming movement", panel=F)
]
Climb = Annotated[
    Maybe, option("--climb/--no-climb", text="Filter by climbing movement", panel=F)
]
Darkvision = Annotated[
    Maybe, option("--darkvision/--no-darkvision", text="Filter by darkvision", panel=F)
]
Blindsight = Annotated[
    Maybe, option("--blindsight/--no-blindsight", text="Filter by blindsight", panel=F)
]
Truesight = Annotated[
    Maybe, option("--truesight/--no-truesight", text="Filter by truesight", panel=F)
]
Speaks = Annotated[
    Strings,
    option(
        "--speaks", text="Languages creature speaks (e.g., Common,Draconic)", panel=F
    ),
]
Skills = Annotated[
    Strings,
    option("--skill", text="Skill proficiencies (e.g., stealth,perception)", panel=F),
]
Sources = Annotated[
    Strings,
    option("--sources", text="Source abbreviations (e.g., PHB,MM,VGM)", panel=F),
]
Sort = Annotated[
    CreatureSortMode,
    option("--sort", text="Sort mode for creature grouping", panel=opt.OUTPUT),
]
DryRun = Annotated[
    bool,
    option(
        "--dry-run",
        text="Show matching creatures without generating output",
        panel=opt.OUTPUT,
    ),
]
Spells = Annotated[
    bool,
    option(
        "--spells/--no-spells",
        text="Generate spellbook appendix with creature-referenced spells",
        panel=opt.OUTPUT,
    ),
]
DeduplicateFluff = Annotated[
    bool,
    option(
        "--deduplicate-fluff/--no-deduplicate-fluff",
        text="Deduplicate shared fluff content (e.g., dragon lairs)",
        panel=C,
    ),
]
CreatureLevel = Annotated[
    int,
    option(
        "--creature-level",
        text="Creature level for proficiency bonus scaling (1-20)",
        panel=C,
    ),
]
TokenCount = Annotated[
    int, option("--token-count", text="Default number of tokens per creature", panel=T)
]
TokenMargins = Annotated[
    float, option("--token-margins", text="Page margins in inches", panel=T)
]
TokenPaper = Annotated[
    str, option("--token-paper-size", text="Paper size (letter, a4)", panel=T)
]
ColumnsTiny = Annotated[
    int, option("--columns-tiny", text="Columns for tiny tokens", panel=T)
]
ColumnsSmall = Annotated[
    int, option("--columns-small", text="Columns for small tokens", panel=T)
]
ColumnsMedium = Annotated[
    int, option("--columns-medium", text="Columns for medium tokens", panel=T)
]
ColumnsLarge = Annotated[
    int, option("--columns-large", text="Columns for large tokens", panel=T)
]
ColumnsHuge = Annotated[
    int, option("--columns-huge", text="Columns for huge tokens", panel=T)
]
ColumnsGargantuan = Annotated[
    int, option("--columns-gargantuan", text="Columns for gargantuan tokens", panel=T)
]
TOKEN_SIZES = ("tiny", "small", "medium", "large", "huge", "gargantuan")


def creatures(  # nosec B107: "letter" is token_paper_size, not a password
    ctx: typer.Context,
    creature_names: Names = None,
    tokens: Tokens = False,
    from_file: FromFile = None,
    from_stdin: FromStdin = False,
    cr_range: CrRange = None,
    min_cr: MinCr = None,
    max_cr: MaxCr = None,
    creature_types: Types = None,
    creature_tags: Tags = None,
    sizes: Sizes = None,
    alignments: Alignments = None,
    min_ac: MinAc = None,
    max_ac: MaxAc = None,
    min_hp: MinHp = None,
    max_hp: MaxHp = None,
    has_spellcasting: Spellcasting = None,
    has_legendary: Legendary = None,
    has_multiattack: Multiattack = None,
    has_reactions: Reactions = None,
    has_fly_speed: Fly = None,
    has_swim_speed: Swim = None,
    has_climb_speed: Climb = None,
    has_darkvision: Darkvision = None,
    has_blindsight: Blindsight = None,
    has_truesight: Truesight = None,
    speaks_language: Speaks = None,
    has_skill: Skills = None,
    sources: Sources = None,
    sort: Sort = CreatureSortMode.CR,
    dry_run: DryRun = False,
    spells: Spells = False,
    fluff: Fluff = False,
    deduplicate_fluff: DeduplicateFluff = True,
    fluff_sections: FluffSections = None,
    fluff_sources: FluffSources = None,
    with_fluff_images: FluffImages = False,
    creature_level: CreatureLevel = 1,
    token_count: TokenCount = 1,
    columns_tiny: ColumnsTiny = 6,
    columns_small: ColumnsSmall = 6,
    columns_medium: ColumnsMedium = 5,
    columns_large: ColumnsLarge = 3,
    columns_huge: ColumnsHuge = 2,
    columns_gargantuan: ColumnsGargantuan = 1,
    token_margins: TokenMargins = 0.25,
    token_paper_size: TokenPaper = "letter",
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
    🐉 Convert creatures to LaTeX bestiary or token sheets

    Select creatures by name, file or filter, then render a bestiary grouped by
    --sort, or with --tokens a printable token sheet.

    \\b
    Examples:
      studiorum convert creatures "Ancient Red Dragon" "Kobold"
      studiorum convert creatures --from-file encounter-creatures.txt
      studiorum convert creatures --type dragon,fiend --cr 5-15 --sort type
      studiorum convert creatures --legendary --min-cr 15
      studiorum convert creatures "Goblin" "Orc" --tokens --token-count 4
      studiorum convert creatures "Aboleth" --fluff --fluff-sections "lair,regional"
    """
    options = ConvertOptions.from_context(ctx)
    with conversion_errors():
        omnidexer = load_data("creature")

        names = read_names(
            creature_names,
            from_file,
            from_stdin,
            "creature",
            key=(lambda n, _s: n) if tokens else (lambda n, s: (n, s or "default")),
        )
        if tokens and names.total:
            rprint(f"[blue]ℹ[/blue] Total tokens to generate: {names.total}")
        result = _collect(omnidexer, ctx.params, names)
        report_collection(result, result.creatures, "creature")
        _print_summary(result)
        if dry_run:
            rprint("\n[yellow]Dry run completed - no output generated[/yellow]")
            return
        rprint()
        found = _sort_creatures(result.creatures, sort)

        if tokens:
            columns: dict[str, int] = {
                size: ctx.params[f"columns_{size}"] for size in TOKEN_SIZES
            }
            latex = _render_tokens(
                found, names, token_count, token_paper_size, token_margins, columns
            )
            write_document(
                options,
                latex,
                Path("output/creatures/tokens.tex"),
                "Token sheet generated",
            )
            return

        references = None
        if spells:
            from studiorum.core.references.content_reference_manager import (
                ContentReferenceManager,
            )

            references = ContentReferenceManager(omnidexer=omnidexer)
        tracker = references.get_content_tracker() if references else None
        found_fluff = _fluff(omnidexer, found, ctx.params, tracker) if fluff else None
        context = RenderingContext(
            output_format="latex",
            omnidexer=omnidexer,
            content_tracker=tracker,
            metadata={
                "title": _heading(options, creature_types),
                "include_images": options.images,
                "template": "bestiary",
                "fluff": found_fluff.fluff if found_fluff else {},
                "fluff_images": found_fluff.images if found_fluff else {},
                "fluff_images_enabled": with_fluff_images,
                "creature_level": creature_level,
            },
        )
        appendices = _spell_appendix(context, references, found) if references else None
        latex = _render_bestiary(found, context, options, result, sort, appendices)
        write_document(
            options, latex, Path("output/creatures/bestiary.tex"), "Bestiary generated"
        )


def _heading(options: ConvertOptions, creature_types: list[str] | None) -> str:
    """The title: --title, else named after the creature types asked for."""
    types = split_csv(creature_types)
    if options.title:
        return options.title
    if types and len(types) == 1:
        return f"{types[0].title()} Bestiary"
    if types:
        return f"Bestiary ({', '.join(t.title() for t in types)})"
    return "Creature Bestiary"


def _fluff(
    omnidexer: Any, creatures: list[Creature], params: dict[str, Any], tracker: Any
) -> FluffResult:
    """Fluff by creature name, with shared fluff such as lairs included once."""
    deduplicator = None
    if params["deduplicate_fluff"]:
        from studiorum.core.services.fluff_deduplicator import (
            DeduplicationStrategy,
            FluffDeduplicator,
        )

        deduplicator = FluffDeduplicator(
            strategy=DeduplicationStrategy.STRICT, content_tracker=tracker
        )
    return collect_fluff(
        omnidexer,
        creatures,
        "creature",
        sections=params["fluff_sections"],
        sources=params["fluff_sources"],
        with_images=params["with_fluff_images"],
        deduplicator=deduplicator,
    )


def _collect(omnidexer: Any, params: dict[str, Any], names: NameList) -> Any:
    """Build the filter criteria from the command's parameters and collect."""
    from studiorum.core.models.creature_filters import CreatureFilterCriteria
    from studiorum.core.parsers.creature_input import parse_cr_range
    from studiorum.core.services.creature_collector import CreatureCollector

    min_cr, max_cr = None, None
    if params["cr_range"]:
        try:
            min_cr, max_cr = parse_cr_range(params["cr_range"])
        except ValueError as e:
            rprint(f"[red]Error:[/red] Invalid CR range: {e}")
            raise typer.Exit(1) from None

    flags = (
        "min_ac",
        "max_ac",
        "min_hp",
        "max_hp",
        "has_spellcasting",
        "has_multiattack",
        "has_reactions",
        "has_fly_speed",
        "has_swim_speed",
        "has_climb_speed",
        "has_darkvision",
        "has_blindsight",
        "has_truesight",
    )
    try:
        criteria = CreatureFilterCriteria(
            min_cr=params["min_cr"] if params["min_cr"] is not None else min_cr,
            max_cr=params["max_cr"] if params["max_cr"] is not None else max_cr,
            cr_range=params["cr_range"],
            creature_types=split_csv(params["creature_types"]),
            creature_tags=split_csv(params["creature_tags"]),
            sizes=split_csv(params["sizes"]),
            alignments=split_csv(params["alignments"]),
            has_legendary_actions=params["has_legendary"],
            speaks_language=split_csv(params["speaks_language"]),
            has_skill=split_csv(params["has_skill"]),
            sources=split_csv(params["sources"], upper=True),
            creature_names=names.names or None,
            creature_source_map=names.sources or None,
            **{flag: params[flag] for flag in flags},
        )
    except ValueError as e:
        rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
        raise typer.Exit(1) from None

    with display_manager.progress("Collecting creatures") as _:
        task = display_manager.add_task("[cyan]Filtering creatures...", total=None)
        result = CreatureCollector(omnidexer).collect_creatures(criteria)
        display_manager.update_task(task, completed=100)
    return result


def _print_summary(result: Any) -> None:
    rprint(f"[green]Found {result.total_count} creatures:[/green]")
    rprint(f"  {result.get_cr_summary()}")
    rprint(f"  {result.get_type_summary()}")
    if result.sources_used:
        rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")


def _cr_value(creature: Creature) -> float:
    """The challenge rating as a number; 0 if unset and 999 if unreadable."""
    if not getattr(creature, "cr", None):
        return 0.0
    cr = str(creature.cr)
    try:
        if "/" in cr:
            num, den = cr.split("/")
            return float(num) / float(den)
        return float(cr)
    except (ValueError, ZeroDivisionError):
        return 999.0


def _type_name(creature: Creature, default: str) -> str:
    if not getattr(creature, "type", None):
        return default
    if isinstance(creature.type, dict):
        return str(creature.type.get("type", "unknown"))
    return str(creature.type)


def _groups(creature: Creature) -> list[str]:
    group = getattr(creature, "group", None)
    if not group:
        return []
    return [str(g) for g in group] if isinstance(group, list) else [str(group)]


SIZE_ORDER = {size: i for i, size in enumerate(TOKEN_SIZES)}


def _sort_creatures(
    creatures: list[Creature], sort_mode: CreatureSortMode
) -> list[Creature]:
    """Sort by the sort mode, then by name."""

    def alignment(c: Creature) -> str:
        value = getattr(c, "alignment", None)
        if not value:
            return "unknown"
        return (
            " ".join(str(a) for a in value) if isinstance(value, list) else str(value)
        )

    keys: dict[CreatureSortMode, Any] = {
        CreatureSortMode.CR: _cr_value,
        CreatureSortMode.TYPE: lambda c: _type_name(c, "unknown").lower(),
        CreatureSortMode.GROUP: lambda c: (_groups(c) or ["ungrouped"])[0].lower(),
        CreatureSortMode.SIZE: lambda c: SIZE_ORDER.get(
            str(getattr(c, "size", "") or "").lower(), 999
        ),
        CreatureSortMode.ALIGNMENT: lambda c: alignment(c).lower(),
        CreatureSortMode.NAME: lambda c: "",
    }
    key = keys[sort_mode]
    return sorted(creatures, key=lambda c: (key(c), c.name.lower()))


CR_BANDS = [
    ("CR 0", lambda cr: cr == 0),
    ("CR 1/8-1/4", lambda cr: 0.125 <= cr <= 0.25),
    ("CR 1/2-1", lambda cr: 0.5 <= cr <= 1),
    ("CR 2-4", lambda cr: 2 <= cr <= 4),
    ("CR 5-10", lambda cr: 5 <= cr <= 10),
    ("CR 11-16", lambda cr: 11 <= cr <= 16),
    ("CR 17-20", lambda cr: 17 <= cr <= 20),
]


def _group_creatures(
    creatures: list[Creature], sort_mode: CreatureSortMode
) -> dict[str, list[Creature]]:
    """The bestiary's headings and the creatures under each."""
    groups: dict[str, list[Creature]] = {}
    if sort_mode == CreatureSortMode.CR:
        for band in [*(b for b, _ in CR_BANDS), "CR 21+"]:
            groups[band] = []
        for creature in creatures:
            cr = _cr_value(creature)
            band = next((b for b, test in CR_BANDS if test(cr)), "CR 21+")
            groups[band].append(creature)
        return {band: members for band, members in groups.items() if members}
    if sort_mode == CreatureSortMode.TYPE:
        for creature in creatures:
            groups.setdefault(_type_name(creature, "Unknown").title(), []).append(
                creature
            )
        return groups
    if sort_mode == CreatureSortMode.GROUP:
        for creature in creatures:
            for name in _groups(creature) or ["Ungrouped"]:
                groups.setdefault(name.strip() or "Ungrouped", []).append(creature)
        return groups
    return {"All Creatures": creatures}


def _render_bestiary(
    creatures: list[Creature],
    context: RenderingContext,
    options: ConvertOptions,
    result: Any,
    sort_mode: CreatureSortMode,
    appendices: Callable[[], list["DocumentChapter"]] | None = None,
) -> str:
    """Render creatures using the bestiary template with grouping."""
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    heading = context.metadata["title"]
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(options.latex)
    template_context = template_engine.create_dnd_template_context(
        content_type="creature",
        title=heading,
        metadata=document_metadata(options, heading),
        latex_config=options.latex,
        rendering_context=context,
        creatures=creatures,
        creatures_by_group=_group_creatures(creatures, sort_mode),
        creature_count=len(creatures),
        cr_summary=result.get_cr_summary(),
        type_summary=result.get_type_summary(),
        sources_used=list(result.sources_used or []),
        show_creature_table_of_contents=options.document.show_toc,
    )
    if appendices is not None:
        template_context["appendices"] = appendices
    with display_manager.progress("Rendering bestiary") as _:
        task = display_manager.add_task("[green]Rendering bestiary...", total=None)
        latex = template_engine.render_template("bestiary.tex.j2", template_context)
        display_manager.update_task(task, completed=100)
    return latex


def _render_tokens(
    creatures: list[Creature],
    names: NameList,
    token_count: int,
    paper_size: str,
    margins: float,
    columns: dict[str, int],
) -> str:
    """Render a printable sheet of creature tokens."""
    from studiorum.cli.context import get_services
    from studiorum.core.models.tokens import TokenSheet
    from studiorum.latex_engine.core.images.resolve import ImageResolver
    from studiorum.renderers.latex.token_renderer import TokenRenderer

    with display_manager.progress("Generating tokens") as _:
        task = display_manager.add_task("[green]Rendering token sheet...", total=None)
        sheet = TokenSheet.from_creatures(
            creatures,
            ImageResolver.from_config(get_services().config.image).token,
            default_count=token_count,
            paper_size=paper_size,
            margins=margins,
            column_config=columns,
            creature_counts=names.counts or None,
        )
        latex = TokenRenderer().render(sheet)
        display_manager.update_task(task, completed=100)
    return latex


def _spell_appendix(
    context: RenderingContext, references: Any, creatures: list[Creature]
) -> Callable[[], list["DocumentChapter"]]:
    """The appendix of spells the creatures cast, built once the body is rendered."""

    def appendices() -> list["DocumentChapter"]:
        from studiorum.core.interfaces import DeepIndexable
        from studiorum.core.services.appendix_generator import (
            AppendixFlags,
            AppendixGenerator,
        )
        from studiorum.latex_engine.document import appendices_as_chapters

        with display_manager.progress("Extracting spell references") as _:
            for creature in creatures:
                if isinstance(creature, DeepIndexable):
                    references.track_deep_index_references(
                        creature, "creature spellcasting abilities"
                    )
        found = AppendixGenerator(omnidexer=context.omnidexer).generate_appendices(
            references.get_content_tracker(), AppendixFlags(spells=True)
        )
        return appendices_as_chapters(found, context)

    return appendices
