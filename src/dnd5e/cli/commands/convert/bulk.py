"""Bulk conversion command."""

import asyncio
import os
from pathlib import Path
from typing import cast

import typer
from rich import print as rprint

from dnd5e.cli.config_factory import (
    get_compile_pdf_default,
    get_concurrent_limit_default,
    get_with_images_default,
)
from dnd5e.cli.display_manager import display_manager
from dnd5e.cli.utils import get_omnidexer, get_tag_resolver
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers import ContentResolutionResult, ContentResolver
from dnd5e.core.services.protocols import OmnidexerProtocol
from dnd5e.latex_engine import create_latex_engine
from dnd5e.renderers.core.interfaces import RenderingContext

from .shared import compile_pdf as compile_pdf_async


def bulk(
    content_list: list[str] = typer.Argument(
        ..., help="List of adventure/book abbreviations or file paths"
    ),
    content_type: str = typer.Option(
        "adventure", "--type", help="Content type (adventure, book, mixed)"
    ),
    output_dir: Path = typer.Option(
        Path("output/bulk"), "--output-dir", "-d", help="Output directory"
    ),
    with_images: bool = typer.Option(
        get_with_images_default(),
        "--images/--no-images",
        help="Include images",
        rich_help_panel="Visual Styling",
    ),
    compile_pdf: bool = typer.Option(
        get_compile_pdf_default(), "--pdf", help="Compile to PDF after conversion"
    ),
    concurrent_limit: int = typer.Option(
        get_concurrent_limit_default(),
        "--concurrent",
        help="Maximum concurrent operations",
    ),
) -> None:
    """
    ⚡ Convert multiple content items using optimized bulk operations

    Uses async bulk resolution for significantly faster processing when
    converting multiple adventures, books, or mixed content.

    \\b
    Examples:
      5e2pdf convert bulk cos lmop hotdq --type adventure
      5e2pdf convert bulk phb mm dmg --type book
      5e2pdf convert bulk cos phb mm --type mixed
    """

    def _bulk_convert() -> None:
        try:
            # Load omnidexer and resolver
            with display_manager.progress("Initializing") as _:
                init_task = display_manager.add_task(
                    "[cyan]Loading content data...", total=None
                )
                omnidexer = get_omnidexer()
                tag_resolver = get_tag_resolver()
                resolver = ContentResolver(cast(OmnidexerProtocol, omnidexer))
                display_manager.update_task(init_task, completed=100)

            # Perform bulk resolution based on content type
            with display_manager.progress("Resolving content") as _:
                resolve_task = display_manager.add_task(
                    f"[cyan]Resolving {len(content_list)} items...",
                    total=len(content_list),
                )

                if content_type == "adventure":
                    results = resolver.resolve_adventures_bulk(content_list)
                elif content_type == "book":
                    results = resolver.resolve_books_bulk(content_list)
                elif content_type == "mixed":
                    # For mixed content, try to determine types from abbreviations
                    mixed_requests = []
                    for abbrev in content_list:
                        # Simple heuristic: common book abbreviations
                        if abbrev.lower() in [
                            "phb",
                            "mm",
                            "dmg",
                            "xgte",
                            "tcoe",
                            "vgtm",
                            "mtof",
                        ]:
                            mixed_requests.append((abbrev, ContentType("book")))
                        else:
                            mixed_requests.append((abbrev, ContentType("adventure")))
                    results = resolver.resolve_multiple(mixed_requests)
                else:
                    rprint(f"[red]Error:[/red] Invalid content type: {content_type}")
                    raise typer.Exit(1)

                display_manager.update_task(resolve_task, completed=len(content_list))

            # Filter successful results
            successful_results = [r for r in results if r.is_success and r.content]
            failed_results = [r for r in results if not r.is_success]

            if failed_results:
                rprint(
                    f"[yellow]Warning:[/yellow] {len(failed_results)} items failed to resolve:"
                )
                for result in failed_results:
                    rprint(f"  • {result.query}: {result.status.value}")
                    if result.suggestions:
                        rprint(f"    Suggestions: {', '.join(result.suggestions[:3])}")

            if not successful_results:
                rprint("[red]Error:[/red] No content could be resolved")
                raise typer.Exit(1)

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def convert_single_item(
                result: ContentResolutionResult,
            ) -> tuple[str, bool]:
                """Convert a single content item with concurrency control."""
                async with semaphore:
                    try:
                        content = result.content
                        if content is None:
                            return result.query, False

                        output_filename = f"{result.query}.tex"
                        output_path = output_dir / output_filename

                        # Create render context
                        context = RenderingContext(
                            output_format="latex",
                            omnidexer=omnidexer,
                            metadata={
                                "title": f"{content.name}",
                                "include_images": with_images,
                                "include_toc": True,
                                "tag_resolver": tag_resolver,
                            },
                        )

                        # Render document
                        engine = create_latex_engine()
                        latex_result = engine.render_document([content], context)

                        # Write output
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(latex_result)

                        # Compile PDF if requested
                        if compile_pdf:
                            asyncio.run(compile_pdf_async(output_path))

                        return result.query, True
                    except Exception as e:
                        rprint(f"[red]Error converting {result.query}:[/red] {e}")
                        return result.query, False

            # Process all items concurrently with progress tracking
            with display_manager.progress("Converting content") as _:
                convert_task = display_manager.add_task(
                    f"[green]Converting {len(successful_results)} items...",
                    total=len(successful_results),
                )

                # Create conversion tasks
                conversion_tasks = [
                    convert_single_item(result) for result in successful_results
                ]

                # Process with progress updates
                async def process_conversions() -> list[tuple[str, bool]]:
                    completed_results = []
                    for task in asyncio.as_completed(conversion_tasks):
                        item_name, success = await task
                        completed_results.append((item_name, success))
                        display_manager.update_task(convert_task, advance=1)
                    return completed_results

                completed_results = asyncio.run(process_conversions())

            # Report results
            successful_conversions = [
                name for name, success in completed_results if success
            ]
            failed_conversions = [
                name for name, success in completed_results if not success
            ]

            rprint("\n[green]✓[/green] Bulk conversion completed:")
            rprint(f"  • Successfully converted: {len(successful_conversions)} items")
            if failed_conversions:
                rprint(f"  • Failed conversions: {len(failed_conversions)} items")
            rprint(f"  • Output directory: {output_dir}")

            if successful_conversions:
                rprint("\n[green]Successfully converted:[/green]")
                for name in successful_conversions:
                    rprint(f"  ✓ {name}")

            if failed_conversions:
                rprint("\n[red]Failed to convert:[/red]")
                for name in failed_conversions:
                    rprint(f"  ✗ {name}")

        except Exception as e:
            import traceback

            rprint(f"[red]Error:[/red] {e}")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                # In CI, print full traceback for debugging
                traceback.print_exc()
            raise typer.Exit(1)

    _bulk_convert()
