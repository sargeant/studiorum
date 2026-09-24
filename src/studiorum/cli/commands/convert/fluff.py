"""Narrative fluff for the creature, spell and item compendiums."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any

from rich import print as rprint

from studiorum.cli.display_manager import display_manager
from studiorum.core.logging import get_logger

from .options import option
from .run import split_csv

logger = get_logger(__name__)

PANEL = "Content Enhancement"

Fluff = Annotated[
    bool, option("--fluff", text="Include narrative fluff content", panel=PANEL)
]
FluffSections = Annotated[
    list[str] | None,
    option(
        "--fluff-sections",
        text="Specific fluff sections to include (e.g., 'lore,history,variants')",
        panel=PANEL,
    ),
]
FluffSources = Annotated[
    list[str] | None,
    option(
        "--fluff-sources",
        text="Filter fluff content by specific sources (e.g., 'MM,XPHB')",
        panel=PANEL,
    ),
]
FluffImages = Annotated[
    bool,
    option(
        "--with-fluff-images", text="Include images from fluff content", panel=PANEL
    ),
]


@dataclass
class FluffResult:
    """Fluff and fluff images by content name, as the templates read them."""

    fluff: dict[str, Any] = field(default_factory=dict)
    images: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def collect_fluff(
    omnidexer: Any,
    content: Sequence[Any],
    kind: str,
    *,
    sections: list[str] | None,
    sources: list[str] | None,
    with_images: bool,
    deduplicator: Any = None,
) -> FluffResult:
    """Match fluff to each piece of content and report what was found.

    ``kind`` is creature, spell or item. A deduplicator, when given, drops fluff
    already included for another piece of content (for example a shared lair).
    """
    from studiorum.core.services.fluff_image_extractor import FluffImageExtractor
    from studiorum.core.services.fluff_matcher import FluffMatcher

    matcher = FluffMatcher(omnidexer)
    match: Callable[..., Any] = getattr(matcher, f"match_{kind}_fluff")
    extractor = FluffImageExtractor(omnidexer) if with_images else None
    section_list = split_csv(sections)
    source_list = split_csv(sources, upper=True)
    result = FluffResult()
    found = image_count = 0

    with display_manager.progress("Processing fluff content") as _:
        task = display_manager.add_task(
            f"[cyan]Loading {kind} fluff...", total=len(content)
        )
        for i, item in enumerate(content):
            try:
                item_fluff = match(
                    item, allowed_sections=section_list, allowed_sources=source_list
                )
                if item_fluff:
                    found += 1
                    if deduplicator and not deduplicator.should_include(item_fluff):
                        logger.debug(
                            f"Duplicate fluff for {item.name}, references: "
                            f"{deduplicator.get_duplicate_references(item_fluff)}"
                        )
                    else:
                        result.fluff[item.name] = item_fluff
                        images = (
                            extractor.extract_images_from_fluff(item_fluff)
                            if extractor
                            else []
                        )
                        if images:
                            image_count += len(images)
                            result.images[item.name] = [img.to_dict() for img in images]
            except Exception as e:
                logger.debug(f"Failed to get fluff for {item.name}: {e}", exc_info=True)
            display_manager.update_task(task, completed=i + 1)

    if not found:
        rprint(f"[yellow]Warning:[/yellow] No fluff content found for any {kind}s")
        if section_list or source_list:
            rprint(
                "[yellow]Note:[/yellow] This might be due to section or source filtering"
            )
        return result

    rprint(f"[green]✓[/green] Found fluff content for {found} {kind}s")
    if section_list:
        rprint(f"[blue]ℹ[/blue] Filtered to sections: {', '.join(section_list)}")
    if source_list:
        rprint(f"[blue]ℹ[/blue] Filtered to sources: {', '.join(source_list)}")
    if image_count:
        rprint(f"[green]✓[/green] Extracted {image_count} images from fluff content")
    if deduplicator:
        duplicates = deduplicator.get_statistics()["duplicate_fluff_detected"]
        rprint(
            f"[blue]ℹ[/blue] Included {len(result.fluff)} unique fluff entries"
            + (f", deduplicated {duplicates} duplicates" if duplicates else "")
        )
    return result
