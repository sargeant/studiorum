"""Spells conversion command."""

import asyncio
import os
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from studiorum.cli.utils import resolve_option

if TYPE_CHECKING:
    from studiorum.core.interfaces import TagResolver
    from studiorum.core.references.content_reference_manager import (
        ContentReferenceManager,
    )
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
from studiorum.core.logging import get_logger
from studiorum.core.models.content import ContentType
from studiorum.core.models.spells import Spell
from studiorum.renderers.core.interfaces import RenderingContext

from ..base import AppendixMixin, BaseConvertCommand
from ..shared import compile_pdf as compile_pdf_async

# Module logger
logger = get_logger(__name__)


class SpellSortMode(str, Enum):
    """Sorting modes for spell output."""

    LEVEL = "level"
    NAME = "name"


def _combine_spellbook_and_appendix(
    spellbook_content: str, appendix_content: str | list[Any]
) -> str:
    """Combine spellbook and creature appendix content."""
    # Handle different possible return types from appendix generation
    if hasattr(appendix_content, "content"):
        # It's a ContentSection object
        appendix_latex = appendix_content.content
    elif isinstance(appendix_content, list) and len(appendix_content) > 0:
        # It's a list of ContentSection objects
        appendix_latex = "\n\n".join(
            section.content
            for section in appendix_content
            if hasattr(section, "content")
        )
    elif isinstance(appendix_content, str):
        # It's already a string
        appendix_latex = appendix_content
    else:
        # Fallback to string representation
        appendix_latex = str(appendix_content)

    # Find the end of main content (before \end{document})
    if "\\end{document}" in spellbook_content:
        main_content, document_end = spellbook_content.rsplit("\\end{document}", 1)
        return f"{main_content}\n\n{appendix_latex}\n\\end{{document}}{document_end}"
    else:
        return f"{spellbook_content}\n\n{appendix_latex}"


def _render_spellbook(
    spells: list[Spell],
    context: RenderingContext,
    latex_config: LaTeXConfig,
    spells_by_level: dict[int, list[Spell]],
    sort_mode: SpellSortMode,
    show_toc: bool,
) -> str:
    """Render spells using the spellbook template with flexible sorting."""
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

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
        # Pass rendering context for proper tag tracking
        rendering_context=context,
    )

    # Provide entry_processor for shape-aware entry rendering in templates
    from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor

    template_context["entry_processor"] = RecursiveEntryProcessor(use_dnd_template=True)

    # Ensure sectioning depth for spells: mark rendering_context with content_type="spell"
    try:
        from studiorum.renderers.core.interfaces import RenderingContext as RC

        spell_metadata = dict(context.metadata or {})
        spell_metadata["content_type"] = "spell"
        template_context["rendering_context"] = RC(
            output_format=context.output_format,
            debug_mode=context.debug_mode,
            omnidexer=context.omnidexer,
            content_tracker=context.content_tracker,
            tag_resolver=context.tag_resolver,
            metadata=spell_metadata,
        )
    except Exception as e:
        # Non-fatal: keep original context; log for diagnostics
        logger.debug(
            "Failed to set spell rendering_context content_type: %s",
            e,
            exc_info=True,
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
    statblock: str | None = typer.Option(
        None,
        "--statblock",
        help="Statblock style (2014/classic/2024/modern)",
        rich_help_panel="Visual Styling",
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
    # Appendix options
    creatures: bool = typer.Option(
        False,
        "--creatures/--no-creatures",
        help="Generate creatures appendix with spell-referenced creatures",
        rich_help_panel="Output Control",
    ),
    # Fluff content options (Phase 5 enhancements)
    fluff: bool = typer.Option(
        False,
        "--fluff",
        help="Include narrative fluff content",
        rich_help_panel="Content Enhancement",
    ),
    fluff_sections: list[str] = typer.Option(
        None,
        "--fluff-sections",
        help="Specific fluff sections to include (e.g., 'lore,history,variants')",
        rich_help_panel="Content Enhancement",
    ),
    fluff_sources: list[str] = typer.Option(
        None,
        "--fluff-sources",
        help="Filter fluff content by specific sources (e.g., 'PHB,XPHB')",
        rich_help_panel="Content Enhancement",
    ),
    with_fluff_images: bool = typer.Option(
        False,
        "--with-fluff-images",
        help="Include images from fluff content (prepares for future image system)",
        rich_help_panel="Content Enhancement",
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
      studiorum convert spells "fireball" "magic missile" "counterspell"
      studiorum convert spells --from-file my-spells.txt

      # Class-based filtering (cleric use case)
      studiorum convert spells --class cleric --level 1-5
      studiorum convert spells --class wizard,sorcerer --max-level 3

      # Advanced filtering
      studiorum convert spells --class wizard --school evocation --level 1-9
      studiorum convert spells --damage-type fire --no-material
      studiorum convert spells --concentration --sources PHB,XGE

      # Sorting options
      studiorum convert spells --class wizard --sort level   # Group by level (default)
      studiorum convert spells --class wizard --sort name    # Alphabetical order
    """

    def _convert() -> None:
        try:
            # Handle test calls - resolve ALL Typer OptionInfo objects when called directly
            # This is necessary when tests call CLI functions directly, bypassing Typer's
            # normal parameter resolution. In normal CLI usage, these are already resolved.
            nonlocal spell_names, from_file, from_stdin, classes, level, max_level
            nonlocal \
                schools, \
                verbal, \
                somatic, \
                material, \
                no_material, \
                concentration, \
                ritual
            nonlocal damage_types, saving_throws, attack_spells, sources
            nonlocal output_file, title, compile_pdf, open_pdf
            nonlocal document_class, paper, fonts, no_outline, font_size, background
            nonlocal high_contrast, two_column, justified, statblock, with_images
            nonlocal sort, show_toc, include_optional, creatures
            nonlocal fluff, fluff_sections, fluff_sources, with_fluff_images

            # Resolve all parameters using the resolve_option utility
            spell_names = resolve_option(spell_names)
            from_file = resolve_option(from_file)
            from_stdin = resolve_option(from_stdin)
            classes = resolve_option(classes)
            level = resolve_option(level)
            max_level = resolve_option(max_level)
            schools = resolve_option(schools)
            verbal = resolve_option(verbal)
            somatic = resolve_option(somatic)
            material = resolve_option(material)
            no_material = resolve_option(no_material)
            concentration = resolve_option(concentration)
            ritual = resolve_option(ritual)
            damage_types = resolve_option(damage_types)
            saving_throws = resolve_option(saving_throws)
            attack_spells = resolve_option(attack_spells)
            sources = resolve_option(sources)
            output_file = resolve_option(output_file)
            title = resolve_option(title)
            compile_pdf = resolve_option(compile_pdf)
            open_pdf = resolve_option(open_pdf)
            document_class = resolve_option(document_class)
            paper = resolve_option(paper)
            fonts = resolve_option(fonts)
            no_outline = resolve_option(no_outline)
            font_size = resolve_option(font_size)
            background = resolve_option(background)
            high_contrast = resolve_option(high_contrast)
            two_column = resolve_option(two_column)
            justified = resolve_option(justified)
            statblock = resolve_option(statblock)
            with_images = resolve_option(with_images)
            sort = resolve_option(sort)
            show_toc = resolve_option(show_toc)
            include_optional = resolve_option(include_optional)
            creatures = resolve_option(creatures)
            fluff = resolve_option(fluff)
            fluff_sections = resolve_option(fluff_sections)
            fluff_sources = resolve_option(fluff_sources)
            with_fluff_images = resolve_option(with_fluff_images)

            # Import spell-specific modules
            from studiorum.core.models.spell_filters import SpellFilterCriteria
            from studiorum.core.parsers.spell_input import SpellInputParser
            from studiorum.core.services.spell_collector import SpellCollector

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

            # Collect from file using enhanced ContentLoader system
            if from_file:
                command_instance = BaseConvertCommand()
                file_spell_data = command_instance.get_enhanced_name_list_from_file(
                    from_file, "spell"
                )

                # Process enhanced file data - extract names and handle count/source
                file_spells = []
                total_spell_count = 0
                source_info = {}

                for count, name, source in file_spell_data:
                    # For spells, we just need the unique names (ignore count for content lists)
                    if name not in file_spells:
                        file_spells.append(name)

                    # Track total count for progress reporting
                    total_spell_count += count

                    # Track source information for potential use in filtering
                    if source:
                        source_info[name] = source

                all_spell_names.extend(file_spells)
                rprint(
                    f"[green]Loaded {len(file_spells)} unique spells from {from_file}[/green]"
                )
                if total_spell_count != len(file_spells):
                    rprint(
                        f"[blue]ℹ[/blue] Total spell references: {total_spell_count} (including duplicates)"
                    )
                if source_info:
                    rprint(
                        f"[blue]ℹ[/blue] Found source specifications for {len(source_info)} spells"
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
                        rprint("[red]Error:[/red] No spell names found in stdin")
                        raise typer.Exit(1)

                    all_spell_names.extend(stdin_lines)
                    rprint(
                        f"[green]Loaded {len(stdin_lines)} spells from stdin[/green]"
                    )
                except KeyboardInterrupt:
                    rprint("[red]Error:[/red] Input interrupted")
                    raise typer.Exit(1)

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
                statblock=statblock,
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
                statblock=config["statblock"],
            )
            latex_config = LaTeXConfig(document=latex_doc_config)

            # Create document metadata
            from studiorum.core.models.document_metadata import (
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

            # Parse fluff sections and sources for Phase 5
            parsed_fluff_sections = None
            if fluff_sections:
                parsed_fluff_sections = []
                for section_list in fluff_sections:
                    parsed_fluff_sections.extend(
                        [s.strip() for s in section_list.split(",")]
                    )

            parsed_fluff_sources = None
            if fluff_sources:
                parsed_fluff_sources = []
                for source_list in fluff_sources:
                    parsed_fluff_sources.extend(
                        [s.strip().upper() for s in source_list.split(",")]
                    )

            # Process fluff content if requested
            spell_fluff_map = {}
            spell_image_map = {}
            if fluff:
                with display_manager.progress("Processing fluff content") as _:
                    fluff_task = display_manager.add_task(
                        "[cyan]Loading spell fluff...", total=len(sorted_spells)
                    )

                    # Initialize Phase 5 services
                    from studiorum.core.services.fluff_image_extractor import (
                        FluffImageExtractor,
                    )
                    from studiorum.core.services.fluff_matcher import FluffMatcher

                    fluff_matcher = FluffMatcher(omnidexer)
                    image_extractor = (
                        FluffImageExtractor(omnidexer) if with_fluff_images else None
                    )

                    fluff_found_count = 0
                    total_fluff_images = 0

                    for i, spell in enumerate(sorted_spells):
                        try:
                            # Use enhanced fluff matcher with Phase 5 features
                            spell_fluff = fluff_matcher.match_spell_fluff(
                                spell,
                                allowed_sections=parsed_fluff_sections,
                                allowed_sources=parsed_fluff_sources,
                            )
                            if spell_fluff:
                                spell_fluff_map[spell.name] = spell_fluff
                                fluff_found_count += 1

                                # Extract images if requested
                                if image_extractor:
                                    spell_images = (
                                        image_extractor.extract_images_from_fluff(
                                            spell_fluff
                                        )
                                    )
                                    if spell_images:
                                        total_fluff_images += len(spell_images)
                                        # Store image info for rendering pipeline
                                        spell_image_map[spell.name] = [
                                            img.to_dict() for img in spell_images
                                        ]
                        except Exception as e:
                            # Gracefully handle fluff lookup errors
                            logger.debug(
                                f"Failed to get fluff for {spell.name}: {e}",
                                exc_info=True,
                            )

                        display_manager.update_task(fluff_task, completed=i + 1)

                    display_manager.update_task(
                        fluff_task, completed=len(sorted_spells)
                    )

                    if fluff_found_count > 0:
                        rprint(
                            f"[green]✓[/green] Found fluff content for {fluff_found_count} spells"
                        )

                        # Report section filtering if applied
                        if parsed_fluff_sections:
                            rprint(
                                f"[blue]ℹ[/blue] Filtered to sections: {', '.join(parsed_fluff_sections)}"
                            )

                        # Report source filtering if applied
                        if parsed_fluff_sources:
                            rprint(
                                f"[blue]ℹ[/blue] Filtered to sources: {', '.join(parsed_fluff_sources)}"
                            )

                        # Report image extraction if performed
                        if with_fluff_images and total_fluff_images > 0:
                            rprint(
                                f"[green]✓[/green] Extracted {total_fluff_images} images from fluff content"
                            )
                    else:
                        rprint(
                            "[yellow]Warning:[/yellow] No fluff content found for any spells"
                        )
                        if parsed_fluff_sections or parsed_fluff_sources:
                            rprint(
                                "[yellow]Note:[/yellow] This might be due to section or source filtering"
                            )

            # Create ContentTracker for creature reference tracking if needed
            appendix_mixin = AppendixMixin()
            reference_manager = (
                appendix_mixin.create_reference_manager(omnidexer)
                if creatures
                else None
            )
            content_tracker = (
                reference_manager.get_content_tracker() if reference_manager else None
            )

            # Create render context with spellbook-specific data
            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                content_tracker=content_tracker,
                tag_resolver=tag_resolver,
                metadata={
                    "title": spell_title,
                    "include_images": with_images,
                    "include_toc": True,
                    "document_metadata": metadata,
                    "latex_config": latex_config,
                    "spell_count": len(sorted_spells),
                    "spell_summary": result.get_level_summary(),
                    "spells_by_level": spells_by_level,
                    "sources_used": list(result.sources_used)
                    if result.sources_used
                    else [],
                    "template": "spellbook",  # Use spellbook template
                    "creatures": creatures,  # Pass flag to rendering pipeline
                    "fluff": spell_fluff_map
                    if fluff
                    else {},  # Pass fluff data to rendering pipeline
                    "fluff_images": spell_image_map
                    if fluff
                    else {},  # Pass fluff image data to rendering pipeline
                    "fluff_sections": parsed_fluff_sections,  # Pass section filtering info
                    "fluff_sources": parsed_fluff_sources,  # Pass source filtering info
                    "fluff_images_enabled": with_fluff_images,  # Pass image extraction flag
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

            # Generate creature appendix if requested
            if creatures and content_tracker:
                from studiorum.core.services.appendix_generator import (
                    AppendixFlags,
                    AppendixGenerator,
                )

                # Generate creature appendix (reference tracking happens automatically during template rendering)
                appendix_flags = AppendixFlags(
                    creatures=True, spells=False, items=False
                )
                appendix_generator = AppendixGenerator(omnidexer)
                creature_appendix = appendix_generator.generate_appendices(
                    content_tracker, appendix_flags
                )

                # Combine outputs
                if creature_appendix:
                    latex_result = _combine_spellbook_and_appendix(
                        latex_result, creature_appendix
                    )

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
                asyncio.run(compile_pdf_async(output_path, open_pdf))

        except typer.Exit:
            # Re-raise typer.Exit cleanly to avoid double error messages
            raise
        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("STUDIORUM_DEBUG_TRACEBACK") in {"1", "true", "True"}:
                traceback.print_exc()
            raise typer.Exit(1)

    _convert()
