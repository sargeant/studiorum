"""Spells conversion command."""

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
from dnd5e.core.models.spells import Spell
from dnd5e.renderers.core.interfaces import RenderingContext

from ..base import BaseConvertCommand
from ..shared import compile_pdf as compile_pdf_async


class SpellSortMode(str, Enum):
    """Sorting modes for spell output."""

    LEVEL = "level"
    NAME = "name"


def _render_spellbook(
    spells: list[Spell],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    spells_by_level: dict[int, list[Spell]],
    sort_mode: SpellSortMode,
    show_toc: bool,
) -> str:
    """Render spells using the spellbook template with flexible sorting."""
    from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

    # Sort levels based on sort mode
    if sort_mode == SpellSortMode.LEVEL:
        # Sort levels (cantrips first, then 1-9)
        sorted_levels = sorted(spells_by_level.keys())
    else:  # SpellSortMode.NAME
        # For name sorting, we have a single group at level 999
        sorted_levels = [999]

    # Create template engine and update with our LaTeX config
    template_engine = LaTeXTemplateEngine()
    template_engine.update_latex_config(latex_config)

    # Create DND template context with proper styling settings
    template_context = template_engine.create_dnd_template_context(
        content_type="spell",
        # Document metadata
        title=context.metadata.get("title", "Spell Collection"),
        metadata=context.metadata.get("document_metadata"),
        latex_config=latex_config,
        # Spellbook-specific data
        spells=spells,
        spells_by_level={level: spells_by_level[level] for level in sorted_levels},
        spell_count=len(spells),
        spell_summary=context.metadata.get("spell_summary", ""),
        sources_used=context.metadata.get("sources_used", []),
        show_spell_table_of_contents=show_toc,
        # Add helper functions
        ordinal=_ordinal_number,
    )

    # Render using spellbook template
    return template_engine.render_template("spellbook.tex.j2", template_context)


def _ordinal_number(n: int) -> str:
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
    if 10 <= n <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def spells(
    # Direct spell names as positional arguments
    spell_names: list[str] = typer.Argument(
        None, help="Spell names to include (e.g., 'fireball' 'magic missile')"
    ),
    # Input sources
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        help="Read spell names from file (one per line)",
        rich_help_panel="Search & Selection",
    ),
    from_stdin: bool = typer.Option(
        False,
        "--from-stdin",
        help="Read spell names from stdin",
        rich_help_panel="Search & Selection",
    ),
    # Class-based filtering
    classes: list[str] = typer.Option(
        None,
        "--class",
        help="Spellcaster classes (e.g., wizard,cleric)",
        rich_help_panel="Search & Selection",
    ),
    level: str | None = typer.Option(
        None,
        "--level",
        help="Level range (e.g., '1-5', '3+', '0' for cantrips)",
        rich_help_panel="Search & Selection",
    ),
    max_level: int | None = typer.Option(
        None,
        "--max-level",
        help="Maximum spell level (0-9)",
        rich_help_panel="Search & Selection",
    ),
    # School and component filtering
    schools: list[str] = typer.Option(
        None,
        "--school",
        help="Schools of magic (e.g., evocation,abjuration)",
        rich_help_panel="Spell Properties",
    ),
    verbal: bool | None = typer.Option(
        None,
        "--verbal/--no-verbal",
        help="Filter by verbal components",
        rich_help_panel="Spell Properties",
    ),
    somatic: bool | None = typer.Option(
        None,
        "--somatic/--no-somatic",
        help="Filter by somatic components",
        rich_help_panel="Spell Properties",
    ),
    material: bool | None = typer.Option(
        None,
        "--material/--no-material",
        help="Filter by material components",
        rich_help_panel="Spell Properties",
    ),
    no_material: bool = typer.Option(
        False,
        "--no-material",
        help="Exclude spells with material components",
        rich_help_panel="Spell Properties",
    ),
    concentration: bool | None = typer.Option(
        None,
        "--concentration/--no-concentration",
        help="Filter by concentration",
        rich_help_panel="Spell Properties",
    ),
    ritual: bool | None = typer.Option(
        None,
        "--ritual/--no-ritual",
        help="Filter by ritual casting",
        rich_help_panel="Spell Properties",
    ),
    # Combat filtering
    damage_types: list[str] = typer.Option(
        None,
        "--damage-type",
        help="Damage types (e.g., fire,cold)",
        rich_help_panel="Combat & Effects",
    ),
    saving_throws: list[str] = typer.Option(
        None,
        "--save",
        help="Saving throw types (e.g., dex,wis)",
        rich_help_panel="Combat & Effects",
    ),
    attack_spells: bool | None = typer.Option(
        None,
        "--attack-spell/--no-attack-spell",
        help="Filter for spell attack rolls",
        rich_help_panel="Combat & Effects",
    ),
    # Source filtering
    sources: list[str] = typer.Option(
        None,
        "--sources",
        help="Source abbreviations (e.g., PHB,XGE)",
        rich_help_panel="Combat & Effects",
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
    sort: SpellSortMode = typer.Option(
        SpellSortMode.LEVEL,
        "--sort",
        help="Sort order: 'level' (group by level, default) or 'name' (alphabetical)",
        rich_help_panel="Output Control",
    ),
    show_toc: bool = typer.Option(
        True,
        "--toc/--no-toc",
        help="Show table of contents (default: enabled)",
        rich_help_panel="Output Control",
    ),
    include_optional: bool = typer.Option(
        False,
        "--optional-spells",
        help="Include optional/variant class spells",
        rich_help_panel="Output Control",
    ),
) -> None:
    """
    🔮 Convert spells to LaTeX spell book

    Create beautifully formatted spell books from 5e.tools spell data.
    Supports both specific spell lists (wizard use case) and class-based
    filtering (cleric use case) with advanced filtering options.

    \\b
    Examples:
      # Specific spells (wizard use case)
      5e2pdf convert spells "fireball" "magic missile" "counterspell"
      5e2pdf convert spells --from-file my-spells.txt

      # Class-based filtering (cleric use case)
      5e2pdf convert spells --class cleric --level 1-5
      5e2pdf convert spells --class wizard,sorcerer --max-level 3

      # Advanced filtering
      5e2pdf convert spells --class wizard --school evocation --level 1-9
      5e2pdf convert spells --damage-type fire --no-material
      5e2pdf convert spells --concentration --sources PHB,XGE

      # Sorting options
      5e2pdf convert spells --class wizard --sort level   # Group by level (default)
      5e2pdf convert spells --class wizard --sort name    # Alphabetical order
    """

    def _convert() -> None:
        try:
            # Import spell-specific modules
            from dnd5e.core.models.spell_filters import SpellFilterCriteria
            from dnd5e.core.parsers.spell_input import SpellInputParser
            from dnd5e.core.services.spell_collector import SpellCollector

            # Load omnidexer and tag resolver
            with display_manager.progress("Loading content") as _:
                load_task = display_manager.add_task(
                    "[cyan]Loading spell data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                display_manager.update_task(load_task, completed=100)

            # Parse input sources and build criteria
            all_spell_names = []

            # Collect spell names from arguments
            if spell_names:
                all_spell_names.extend(spell_names)

            # Collect from file
            if from_file:
                if not from_file.exists():
                    rprint(f"[red]Error:[/red] Spell file not found: {from_file}")
                    raise typer.Exit(1)

                file_spells = SpellInputParser.parse_spell_names_from_file(from_file)
                all_spell_names.extend(file_spells)
                rprint(
                    f"[green]Loaded {len(file_spells)} spells from {from_file}[/green]"
                )

            # Collect from stdin
            if from_stdin:
                stdin_spells = SpellInputParser.parse_spell_names_from_stdin()
                all_spell_names.extend(stdin_spells)
                rprint(f"[green]Loaded {len(stdin_spells)} spells from stdin[/green]")

            # Parse level range if provided
            min_level, max_level_parsed = None, None
            if level:
                try:
                    min_level, max_level_parsed = SpellInputParser.parse_level_range(
                        level
                    )
                except ValueError as e:
                    rprint(f"[red]Error:[/red] Invalid level range: {e}")
                    raise typer.Exit(1)

            # Use max_level option if provided, otherwise use parsed max_level
            effective_max_level = (
                max_level if max_level is not None else max_level_parsed
            )

            # Parse class list
            parsed_classes = None
            if classes:
                parsed_classes = []
                for cls_list in classes:
                    parsed_classes.extend(SpellInputParser.parse_class_list(cls_list))

            # Parse source list
            parsed_sources = None
            if sources:
                parsed_sources = []
                for src_list in sources:
                    parsed_sources.extend(SpellInputParser.parse_source_list(src_list))

            # Build filter criteria
            try:
                criteria = SpellFilterCriteria(
                    min_level=min_level,
                    max_level=effective_max_level,
                    classes=parsed_classes,
                    include_optional=include_optional,
                    schools=schools,
                    has_verbal=verbal,
                    has_somatic=somatic,
                    has_material=material,
                    no_material=no_material,
                    concentration=concentration,
                    ritual=ritual,
                    damage_types=damage_types,
                    saving_throws=saving_throws,
                    attack_spells=attack_spells,
                    sources=parsed_sources,
                    spell_names=all_spell_names if all_spell_names else None,
                )
            except ValueError as e:
                rprint(f"[red]Error:[/red] Invalid filter criteria: {e}")
                raise typer.Exit(1)

            # Collect spells using SpellCollector
            collector = SpellCollector(omnidexer)

            with display_manager.progress("Collecting spells") as _:
                collect_task = display_manager.add_task(
                    "[cyan]Filtering spells...", total=None
                )
                result = collector.collect_spells(criteria)
                display_manager.update_task(collect_task, completed=100)

            # Handle unresolved spells
            if result.unresolved_names:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(result.unresolved_names)} spells could not be found:"
                )
                for name in result.unresolved_names:
                    rprint(f"  • {name}")
                    if name in result.suggestions and result.suggestions[name]:
                        rprint(
                            f"    Suggestions: {', '.join(result.suggestions[name][:3])}"
                        )
                rprint()

            if not result.spells:
                rprint("[red]Error:[/red] No spells found matching criteria")
                if result.unresolved_names and any(result.suggestions.values()):
                    rprint(
                        "[yellow]Try using one of the suggested spell names above.[/yellow]"
                    )
                raise typer.Exit(1)

            # Sort spells based on the sort mode
            if sort == SpellSortMode.LEVEL:
                # Sort by level, then alphabetically (default behavior)
                sorted_spells = sorted(
                    result.spells, key=lambda s: (s.level, s.name.lower())
                )

                # Group spells by level for template rendering
                spells_by_level: dict[int, list[Spell]] = {}
                for spell in sorted_spells:
                    spell_level = spell.level
                    if spell_level not in spells_by_level:
                        spells_by_level[spell_level] = []
                    spells_by_level[spell_level].append(spell)
            else:  # SpellSortMode.NAME
                # Sort alphabetically by name only
                sorted_spells = sorted(result.spells, key=lambda s: s.name.lower())

                # Create a single flat "group" for template (level 999 ensures it's last)
                spells_by_level = {999: sorted_spells}

            rprint(f"[green]Found {result.total_count} spells:[/green]")
            rprint(f"  {result.get_level_summary()}")
            if result.sources_used:
                rprint(f"  Sources: {', '.join(sorted(result.sources_used))}")
            rprint()

            # Determine output file
            if output_file is None:
                output_path = Path("output/spells") / "spellbook.tex"
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

            spell_title = title or "Spell Collection"
            if parsed_classes and len(parsed_classes) == 1:
                spell_title = title or f"{parsed_classes[0].title()} Spell Book"
            elif parsed_classes:
                spell_title = (
                    title
                    or f"Spell Collection ({', '.join(c.title() for c in parsed_classes)})"
                )

            metadata = DocumentMetadata(
                title=spell_title,
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
                description=f"Collection of {len(sorted_spells)} spells",
                use_parts=False,
            )

            # Create render context with spellbook-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": spell_title,
                    "include_images": with_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "spell_count": len(sorted_spells),
                    "spell_summary": result.get_level_summary(),
                    "spells_by_level": spells_by_level,
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "spellbook",  # Use spellbook template
                },
            )

            # Render document using custom spellbook rendering
            with display_manager.progress("Rendering spellbook") as _:
                render_task = display_manager.add_task(
                    "[green]Rendering spellbook...", total=None
                )
                latex_result = _render_spellbook(
                    sorted_spells,
                    context,
                    latex_config,
                    spells_by_level,
                    sort,
                    show_toc,
                )
                display_manager.update_task(render_task, completed=100)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if latex_result:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(latex_result)
                rprint(f"[green]✓[/green] Spellbook generated: {output_path}")
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
