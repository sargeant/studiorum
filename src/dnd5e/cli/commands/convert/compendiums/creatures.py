"""Creatures conversion command."""

import asyncio
import os
from enum import Enum
from pathlib import Path

import typer
from rich import print as rprint

from dnd5e.cli.config_factory import (
    get_compile_pdf_default,
    get_document_class_default,
    get_with_images_default,
)
from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.utils import get_omnidexer, get_tag_resolver
from dnd5e.core.config.latex_config import LaTeXConfig
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.models.creatures import Creature
from dnd5e.core.references.content_tracker import ContentTracker
from dnd5e.renderers.core.interfaces import RenderingContext

from ..base import AppendixMixin, BaseConvertCommand
from ..shared import compile_pdf as compile_pdf_async


class CreatureSortMode(str, Enum):
    """Sorting modes for creature output."""

    CR = "cr"  # Group by challenge rating (default)
    TYPE = "type"  # Group by creature type
    NAME = "name"  # Alphabetical
    SIZE = "size"  # Group by size category
    ALIGNMENT = "alignment"  # Group by alignment


def _sort_creatures(
    creatures: list[Creature], sort_mode: CreatureSortMode
) -> list[Creature]:
    """Sort creatures based on the specified sort mode."""
    if sort_mode == CreatureSortMode.CR:
        # Sort by CR first, then by name
        def cr_sort_key(creature: Creature) -> tuple[float, str]:
            cr_value = 0.0
            if hasattr(creature, "cr") and creature.cr:
                cr_str = str(creature.cr)
                try:
                    if "/" in cr_str:
                        num, den = cr_str.split("/")
                        cr_value = float(num) / float(den)
                    else:
                        cr_value = float(cr_str)
                except (ValueError, ZeroDivisionError):
                    cr_value = 999.0  # Put invalid CRs at the end
            return (cr_value, creature.name.lower())

        return sorted(creatures, key=cr_sort_key)

    elif sort_mode == CreatureSortMode.TYPE:
        # Sort by creature type, then by name
        def type_sort_key(creature: Creature) -> tuple[str, str]:
            type_str = "unknown"
            if hasattr(creature, "type") and creature.type:
                if isinstance(creature.type, dict):
                    type_str = creature.type.get("type", "unknown")
                else:
                    type_str = str(creature.type)
            return (type_str.lower(), creature.name.lower())

        return sorted(creatures, key=type_sort_key)

    elif sort_mode == CreatureSortMode.SIZE:
        # Sort by size, then by name
        size_order = {
            "tiny": 0,
            "small": 1,
            "medium": 2,
            "large": 3,
            "huge": 4,
            "gargantuan": 5,
        }

        def size_sort_key(creature: Creature) -> tuple[int, str]:
            size_value = 999  # Default for unknown sizes
            if hasattr(creature, "size") and creature.size:
                size_str = str(creature.size).lower()
                size_value = size_order.get(size_str, 999)
            return (size_value, creature.name.lower())

        return sorted(creatures, key=size_sort_key)

    elif sort_mode == CreatureSortMode.ALIGNMENT:
        # Sort by alignment, then by name
        def alignment_sort_key(creature: Creature) -> tuple[str, str]:
            alignment_str = "unknown"
            if hasattr(creature, "alignment") and creature.alignment:
                if isinstance(creature.alignment, list):
                    alignment_str = " ".join(str(a) for a in creature.alignment)
                else:
                    alignment_str = str(creature.alignment)
            return (alignment_str.lower(), creature.name.lower())

        return sorted(creatures, key=alignment_sort_key)

    else:  # CreatureSortMode.NAME
        # Sort alphabetically by name
        return sorted(creatures, key=lambda c: c.name.lower())


def _combine_bestiary_and_appendix(bestiary_latex: str, appendix_latex: str) -> str:
    """Combine bestiary and spell appendix LaTeX content."""
    # Find the end of the document body in bestiary
    if "\\end{document}" in bestiary_latex:
        # Insert appendix before \end{document}
        parts = bestiary_latex.rsplit("\\end{document}", 1)
        return f"{parts[0]}\n\n{appendix_latex}\n\n\\end{{document}}{parts[1]}"
    else:
        # Fallback: append appendix
        return f"{bestiary_latex}\n\n{appendix_latex}"


def _render_bestiary(
    creatures: list[Creature],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    sort_mode: CreatureSortMode,
    show_toc: bool,
) -> str:
    """Render creatures using the bestiary template with grouping."""
    from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

    # Group creatures by sort mode
    creatures_by_group: dict[str, list[Creature]] = {}

    if sort_mode == CreatureSortMode.CR:
        # Group by CR ranges: 0, 1/8-1/4, 1/2-1, 2-4, 5-10, 11-16, 17-20, 21+
        cr_groups: dict[str, list[Creature]] = {
            "CR 0": [],
            "CR 1/8-1/4": [],
            "CR 1/2-1": [],
            "CR 2-4": [],
            "CR 5-10": [],
            "CR 11-16": [],
            "CR 17-20": [],
            "CR 21+": [],
        }

        for creature in creatures:
            cr_value = 0.0
            if hasattr(creature, "cr") and creature.cr:
                cr_str = str(creature.cr)
                try:
                    if "/" in cr_str:
                        num, den = cr_str.split("/")
                        cr_value = float(num) / float(den)
                    else:
                        cr_value = float(cr_str)
                except (ValueError, ZeroDivisionError):
                    cr_value = 999.0

            if cr_value == 0:
                cr_groups["CR 0"].append(creature)
            elif 0.125 <= cr_value <= 0.25:
                cr_groups["CR 1/8-1/4"].append(creature)
            elif 0.5 <= cr_value <= 1:
                cr_groups["CR 1/2-1"].append(creature)
            elif 2 <= cr_value <= 4:
                cr_groups["CR 2-4"].append(creature)
            elif 5 <= cr_value <= 10:
                cr_groups["CR 5-10"].append(creature)
            elif 11 <= cr_value <= 16:
                cr_groups["CR 11-16"].append(creature)
            elif 17 <= cr_value <= 20:
                cr_groups["CR 17-20"].append(creature)
            else:
                cr_groups["CR 21+"].append(creature)

        # Only include groups that have creatures
        creatures_by_group = {k: v for k, v in cr_groups.items() if v}

    elif sort_mode == CreatureSortMode.TYPE:
        # Group by creature type
        for creature in creatures:
            type_str = "Unknown"
            if hasattr(creature, "type") and creature.type:
                if isinstance(creature.type, dict):
                    type_str = creature.type.get("type", "unknown")
                else:
                    type_str = str(creature.type)

            type_title = type_str.title()
            if type_title not in creatures_by_group:
                creatures_by_group[type_title] = []
            creatures_by_group[type_title].append(creature)

    else:  # NAME, SIZE, ALIGNMENT - single flat group
        creatures_by_group = {"All Creatures": creatures}

    # Create template engine and update with our LaTeX config
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(latex_config)

    # Create DND template context with proper styling settings
    template_context = template_engine.create_dnd_template_context(
        content_type="creature",
        # Document metadata
        title=context.metadata.get("title", "Creature Bestiary"),
        metadata=context.metadata.get("document_metadata"),
        latex_config=latex_config,
        # Bestiary-specific data
        creatures=creatures,
        creatures_by_group=creatures_by_group,
        creature_count=len(creatures),
        cr_summary=context.metadata.get("cr_summary", ""),
        type_summary=context.metadata.get("type_summary", ""),
        sources_used=context.metadata.get("sources_used", []),
        show_creature_table_of_contents=show_toc,
    )

    # Render using bestiary template
    return template_engine.render_template("bestiary.tex.j2", template_context)


def creatures(
    # Direct selection
    creature_names: list[str] = typer.Argument(None, help="Creature names to include"),
    # Input sources
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        help="Read creature names from file (one per line)",
        rich_help_panel="Search & Selection",
    ),
    from_stdin: bool = typer.Option(
        False,
        "--from-stdin",
        help="Read creature names from stdin",
        rich_help_panel="Search & Selection",
    ),
    # CR filtering
    cr_range: str | None = typer.Option(
        None,
        "--cr",
        help="Challenge rating range (e.g., '1-5', '1/4-2', '10+')",
        rich_help_panel="Search & Selection",
    ),
    min_cr: float | None = typer.Option(
        None,
        "--min-cr",
        help="Minimum challenge rating",
        rich_help_panel="Search & Selection",
    ),
    max_cr: float | None = typer.Option(
        None,
        "--max-cr",
        help="Maximum challenge rating",
        rich_help_panel="Search & Selection",
    ),
    # Type filtering (CRITICAL for ContentTracker)
    creature_types: list[str] = typer.Option(
        None,
        "--type",
        help="Creature types (humanoid,dragon,giant,etc.)",
        rich_help_panel="Search & Selection",
    ),
    creature_tags: list[str] = typer.Option(
        None,
        "--tag",
        help="Creature tags (demon,devil,aarakocra,etc.)",
        rich_help_panel="Search & Selection",
    ),
    sizes: list[str] = typer.Option(
        None,
        "--size",
        help="Creature sizes (tiny,small,medium,large,huge,gargantuan)",
        rich_help_panel="Search & Selection",
    ),
    alignments: list[str] = typer.Option(
        None,
        "--alignment",
        help="Creature alignments",
        rich_help_panel="Search & Selection",
    ),
    # Combat filtering
    min_ac: int | None = typer.Option(
        None,
        "--min-ac",
        help="Minimum armor class",
        rich_help_panel="Advanced Filtering",
    ),
    max_ac: int | None = typer.Option(
        None,
        "--max-ac",
        help="Maximum armor class",
        rich_help_panel="Advanced Filtering",
    ),
    min_hp: int | None = typer.Option(
        None,
        "--min-hp",
        help="Minimum hit points",
        rich_help_panel="Advanced Filtering",
    ),
    max_hp: int | None = typer.Option(
        None,
        "--max-hp",
        help="Maximum hit points",
        rich_help_panel="Advanced Filtering",
    ),
    # Special abilities
    has_spellcasting: bool | None = typer.Option(
        None,
        "--spellcasting/--no-spellcasting",
        help="Filter by spellcasting ability",
        rich_help_panel="Advanced Filtering",
    ),
    has_legendary: bool | None = typer.Option(
        None,
        "--legendary/--no-legendary",
        help="Filter by legendary actions",
        rich_help_panel="Advanced Filtering",
    ),
    has_multiattack: bool | None = typer.Option(
        None,
        "--multiattack/--no-multiattack",
        help="Filter by multiattack ability",
        rich_help_panel="Advanced Filtering",
    ),
    has_reactions: bool | None = typer.Option(
        None,
        "--reactions/--no-reactions",
        help="Filter by reaction abilities",
        rich_help_panel="Advanced Filtering",
    ),
    # Movement and senses (HIGH VALUE from Gemini)
    has_fly_speed: bool | None = typer.Option(
        None,
        "--fly/--no-fly",
        help="Filter by flying movement",
        rich_help_panel="Advanced Filtering",
    ),
    has_swim_speed: bool | None = typer.Option(
        None,
        "--swim/--no-swim",
        help="Filter by swimming movement",
        rich_help_panel="Advanced Filtering",
    ),
    has_climb_speed: bool | None = typer.Option(
        None,
        "--climb/--no-climb",
        help="Filter by climbing movement",
        rich_help_panel="Advanced Filtering",
    ),
    has_darkvision: bool | None = typer.Option(
        None,
        "--darkvision/--no-darkvision",
        help="Filter by darkvision",
        rich_help_panel="Advanced Filtering",
    ),
    has_blindsight: bool | None = typer.Option(
        None,
        "--blindsight/--no-blindsight",
        help="Filter by blindsight",
        rich_help_panel="Advanced Filtering",
    ),
    has_truesight: bool | None = typer.Option(
        None,
        "--truesight/--no-truesight",
        help="Filter by truesight",
        rich_help_panel="Advanced Filtering",
    ),
    # Communication and skills
    speaks_language: list[str] = typer.Option(
        None,
        "--speaks",
        help="Languages creature speaks (e.g., Common,Draconic)",
        rich_help_panel="Advanced Filtering",
    ),
    has_skill: list[str] = typer.Option(
        None,
        "--skill",
        help="Skill proficiencies (e.g., stealth,perception)",
        rich_help_panel="Advanced Filtering",
    ),
    # Source filtering
    sources: list[str] = typer.Option(
        None,
        "--sources",
        help="Source abbreviations (e.g., PHB,MM,VGM)",
        rich_help_panel="Advanced Filtering",
    ),
    # Sorting and TOC
    sort: CreatureSortMode = typer.Option(
        CreatureSortMode.CR,
        "--sort",
        help="Sort mode for creature grouping",
        rich_help_panel="Output Control",
    ),
    show_toc: bool = typer.Option(
        True,
        "--toc/--no-toc",
        help="Show table of contents",
        rich_help_panel="Output Control",
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
    # Utility options (HIGH VALUE from Gemini)
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show matching creatures without generating output",
        rich_help_panel="Output Control",
    ),
    # LaTeX document formatting options (same as convert_spells)
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
    # Appendix options
    spells: bool = typer.Option(
        False,
        "--spells/--no-spells",
        help="Generate spellbook appendix with creature-referenced spells",
        rich_help_panel="Output Control",
    ),
) -> None:
    """
    🐉 Convert creatures to LaTeX bestiary

    Create beautifully formatted creature compendiums from 5e.tools data.
    Supports encounter building, DM reference, and adventure appendices.

    \\b
    Examples:
      # Specific creatures (encounter building)
      5e2pdf convert creatures "Ancient Red Dragon" "Kobold" "Fire Elemental"
      5e2pdf convert creatures --from-file encounter-creatures.txt

      # CR-based filtering (DM reference)
      5e2pdf convert creatures --cr 1-5
      5e2pdf convert creatures --min-cr 10

      # Type-based filtering (adventure appendices)
      5e2pdf convert creatures --type dragon,fiend --cr 5-15
      5e2pdf convert creatures --type humanoid

      # Advanced filtering (combat and abilities)
      5e2pdf convert creatures --legendary --min-cr 15
      5e2pdf convert creatures --fly --darkvision --type beast
      5e2pdf convert creatures --spellcasting --type humanoid

      # Sorting options
      5e2pdf convert creatures --type dragon --sort cr     # Group by CR (default)
      5e2pdf convert creatures --cr 1-5 --sort type       # Group by creature type
      5e2pdf convert creatures --legendary --sort name     # Alphabetical
    """

    def _convert() -> None:
        try:
            # Import creature-specific modules
            from dnd5e.core.models.creature_filters import CreatureFilterCriteria
            from dnd5e.core.parsers.creature_input import (
                parse_cr_range,
                parse_creature_names_from_file,
                parse_creature_names_from_stdin,
            )
            from dnd5e.core.services.creature_collector import CreatureCollector

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading creature data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Parse input sources and build criteria
            all_creature_names = []

            # Collect creature names from arguments
            if creature_names:
                all_creature_names.extend(creature_names)

            # Collect from file
            if from_file:
                if not from_file.exists():
                    rprint(f"[red]Error:[/red] Creature file not found: {from_file}")
                    raise typer.Exit(1)

                try:
                    file_creatures = parse_creature_names_from_file(from_file)
                    all_creature_names.extend(file_creatures)
                    rprint(
                        f"[green]Loaded {len(file_creatures)} creatures from {from_file}[/green]"
                    )
                except (FileNotFoundError, PermissionError, ValueError) as e:
                    rprint(f"[red]Error reading file:[/red] {e}")
                    raise typer.Exit(1)

            # Collect from stdin
            if from_stdin:
                try:
                    stdin_creatures = parse_creature_names_from_stdin()
                    all_creature_names.extend(stdin_creatures)
                    rprint(
                        f"[green]Loaded {len(stdin_creatures)} creatures from stdin[/green]"
                    )
                except ValueError as e:
                    rprint(f"[red]Error reading stdin:[/red] {e}")
                    raise typer.Exit(1)

            # Parse CR range if provided
            min_cr_parsed, max_cr_parsed = None, None
            if cr_range:
                try:
                    min_cr_parsed, max_cr_parsed = parse_cr_range(cr_range)
                except ValueError as e:
                    rprint(f"[red]Error:[/red] Invalid CR range: {e}")
                    raise typer.Exit(1)

            # Use explicit min/max CR if provided, otherwise use parsed values
            effective_min_cr = min_cr if min_cr is not None else min_cr_parsed
            effective_max_cr = max_cr if max_cr is not None else max_cr_parsed

            # Parse lists (split by comma if needed)
            parsed_sources = None
            if sources:
                parsed_sources = []
                for src_list in sources:
                    parsed_sources.extend([s.strip() for s in src_list.split(",")])

            parsed_creature_types = None
            if creature_types:
                parsed_creature_types = []
                for type_list in creature_types:
                    parsed_creature_types.extend(
                        [t.strip() for t in type_list.split(",")]
                    )

            parsed_creature_tags = None
            if creature_tags:
                parsed_creature_tags = []
                for tag_list in creature_tags:
                    parsed_creature_tags.extend(
                        [t.strip() for t in tag_list.split(",")]
                    )

            parsed_sizes = None
            if sizes:
                parsed_sizes = []
                for size_list in sizes:
                    parsed_sizes.extend([s.strip() for s in size_list.split(",")])

            parsed_alignments = None
            if alignments:
                parsed_alignments = []
                for align_list in alignments:
                    parsed_alignments.extend([a.strip() for a in align_list.split(",")])

            parsed_speaks_language = None
            if speaks_language:
                parsed_speaks_language = []
                for lang_list in speaks_language:
                    parsed_speaks_language.extend(
                        [lang.strip() for lang in lang_list.split(",")]
                    )

            parsed_has_skill = None
            if has_skill:
                parsed_has_skill = []
                for skill_list in has_skill:
                    parsed_has_skill.extend([s.strip() for s in skill_list.split(",")])

            # Build filter criteria
            try:
                criteria = CreatureFilterCriteria(
                    min_cr=effective_min_cr,
                    max_cr=effective_max_cr,
                    cr_range=cr_range,
                    creature_types=parsed_creature_types,
                    creature_tags=parsed_creature_tags,
                    sizes=parsed_sizes,
                    alignments=parsed_alignments,
                    min_ac=min_ac,
                    max_ac=max_ac,
                    min_hp=min_hp,
                    max_hp=max_hp,
                    has_spellcasting=has_spellcasting,
                    has_legendary_actions=has_legendary,
                    has_multiattack=has_multiattack,
                    has_reactions=has_reactions,
                    has_fly_speed=has_fly_speed,
                    has_swim_speed=has_swim_speed,
                    has_climb_speed=has_climb_speed,
                    has_darkvision=has_darkvision,
                    has_blindsight=has_blindsight,
                    has_truesight=has_truesight,
                    speaks_language=parsed_speaks_language,
                    has_skill=parsed_has_skill,
                    sources=parsed_sources,
                    creature_names=all_creature_names if all_creature_names else None,
                )
            except ValueError as e:
                rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
                raise typer.Exit(1)

            # Collect creatures using CreatureCollector
            collector = CreatureCollector(omnidexer)

            with display_manager.progress("Collecting creatures") as _:
                collect_task = display_manager.add_task(
                    "[cyan]Filtering creatures...", total=None
                )
                result = collector.collect_creatures(criteria)
                display_manager.update_task(collect_task, completed=100)

            # Handle unresolved creatures
            if result.unresolved_names:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} creatures could not be found:"
                )
                for name in result.unresolved_names:
                    rprint(f"  • {name}")
                    if name in result.suggestions and result.suggestions[name]:
                        rprint(
                            f"    Suggestions: {', '.join(result.suggestions[name][:3])}"
                        )
                rprint()

            if not result.creatures:
                rprint("[red]Error:[/red] No creatures found matching criteria")
                if result.unresolved_names and any(result.suggestions.values()):
                    rprint(
                        "[yellow]Try using one of the suggested creature names above.[/yellow]"
                    )
                raise typer.Exit(1)

            # Handle dry run
            if dry_run:
                rprint(f"[green]Found {result.total_count} creatures:[/green]")
                rprint(f"  {result.get_cr_summary()}")
                rprint(f"  {result.get_type_summary()}")
                if result.sources_used:
                    rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
                rprint("\n[yellow]Dry run completed - no output generated[/yellow]")
                return

            # Sort creatures based on the sort mode
            sorted_creatures = _sort_creatures(result.creatures, sort)

            rprint(f"[green]Found {result.total_count} creatures:[/green]")
            rprint(f"  {result.get_cr_summary()}")
            rprint(f"  {result.get_type_summary()}")
            if result.sources_used:
                rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
            rprint()

            # Determine output file
            if output_file is None:
                output_path = Path("output/creatures") / "bestiary.tex"
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

            from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig

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
            from dnd5e.core.models.document_metadata import (
                DocumentMetadata,
                DocumentType,
            )

            creature_title = title or "Creature Bestiary"
            if parsed_creature_types and len(parsed_creature_types) == 1:
                creature_title = title or f"{parsed_creature_types[0].title()} Bestiary"
            elif parsed_creature_types:
                type_names = [t.title() for t in parsed_creature_types]
                creature_title = title or f"Bestiary ({', '.join(type_names)})"

            metadata = DocumentMetadata(
                title=creature_title,
                subtitle=None,
                short_title=None,
                editor=None,
                date=None,
                version=None,
                edition=None,
                publisher=None,
                document_type=DocumentType.ADVENTURE,  # Use adventure type for now
                include_toc=show_toc,
                include_index=False,
                include_bibliography=False,
                include_glossary=False,
                cover=None,
                logo_path=None,
                subject=None,
                description=f"Collection of {len(sorted_creatures)} creatures",
                use_parts=False,
            )

            # Create ContentTracker for spell reference tracking if needed
            # Create unified reference manager for spell tracking
            appendix_mixin = AppendixMixin()
            reference_manager = (
                appendix_mixin.create_reference_manager(omnidexer) if spells else None
            )
            content_tracker = (
                reference_manager.get_content_tracker() if reference_manager else None
            )

            # Create render context with bestiary-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                content_tracker=content_tracker,
                metadata={
                    "title": creature_title,
                    "include_images": with_images,
                    "include_toc": show_toc,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "creature_count": len(sorted_creatures),
                    "cr_summary": result.get_cr_summary(),
                    "type_summary": result.get_type_summary(),
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "bestiary",  # Use bestiary template
                    "spells": spells,  # Pass flag to rendering pipeline
                },
            )

            # Render document using custom bestiary rendering
            with display_manager.progress("Rendering bestiary") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering bestiary...", total=None
                )
                latex_result = _render_bestiary(
                    sorted_creatures,
                    context,
                    latex_config,
                    sort,
                    show_toc,
                )
                display_manager.update_task(render_task, completed=100)

            # Generate spell appendix if requested
            if spells and content_tracker:
                from dnd5e.core.services.appendix_generator import (
                    AppendixFlags,
                    AppendixGenerator,
                )
                from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

                # Create template engine for appendix generation
                template_engine = LaTeXTemplateEngine()

                # Create appendix flags
                appendix_flags = AppendixFlags(
                    spells=True, creatures=False, items=False
                )

                # Unified Reference Tracking:
                # Use the unified reference system to automatically track spell references
                with display_manager.progress("Extracting spell references") as _:
                    appendix_mixin.track_deep_index_references(
                        reference_manager,
                        sorted_creatures,
                        context="creature spellcasting abilities",
                    )

                # Generate spell appendix using unified system
                spell_appendix = appendix_mixin.generate_appendices(
                    reference_manager, appendix_flags, template_engine, omnidexer
                )

                # Combine outputs if appendix was generated
                if spell_appendix:
                    # Debug: check what type we got back
                    with display_manager.progress("Processing appendix") as _:
                        # Handle different possible return types
                        if hasattr(spell_appendix, "content"):
                            # It's an AppendixSection object
                            appendix_content = spell_appendix.content
                        elif (
                            isinstance(spell_appendix, list) and len(spell_appendix) > 0
                        ):
                            # It's a list of AppendixSection objects
                            appendix_content = "\n\n".join(
                                section.content
                                for section in spell_appendix
                                if hasattr(section, "content")
                            )
                        elif isinstance(spell_appendix, str):
                            # It's already a string
                            appendix_content = spell_appendix
                        else:
                            # Fallback to string representation
                            appendix_content = str(spell_appendix)

                    latex_result = _combine_bestiary_and_appendix(
                        latex_result, appendix_content
                    )

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if latex_result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(latex_result)
                rprint(f"[green]✓[/green] Bestiary generated: {output_path}")
            else:
                rprint("[red]Error:[/red] No LaTeX content was generated")
                raise typer.Exit(1)

            # Compile PDF if requested
            if compile_pdf:
                asyncio.run(compile_pdf_async(output_path))

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()
