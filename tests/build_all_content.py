#!/usr/bin/env python3
"""
Build All Content Test Script

This script attempts to build ALL adventures and books to LaTeX format
to identify content issues during development. This is NOT part of the
pytest suite - it's a developer workflow tool for finding lurking issues.

PURPOSE:
- Build all available adventures and books in the 5etools data
- Collect and report errors systematically
- Generate LaTeX output files for inspection
- Identify content parsing, rendering, or reference resolution issues
- Provide comprehensive error reporting and statistics

USAGE:
    # Test everything (may take 10+ minutes)
    uv run python tests/build_all_content.py

    # Quick sample test
    uv run python tests/build_all_content.py --limit 5 --summary-only

    # Test only adventures, show progress
    uv run python tests/build_all_content.py --adventures-only --verbose

    # Test books with custom output directory
    uv run python tests/build_all_content.py --books-only --output-dir ./test-output

OPTIONS:
    --adventures-only    Build only adventures
    --books-only        Build only books
    --limit N           Build only first N items of each type
    --output-dir PATH   Directory to save output files (default: /tmp/5e2pdf-test-*)
    --images            Enable image processing (default: disabled for speed)
    --stop-on-error     Stop building after first error (default: continue)
    --verbose           Show detailed progress and error output
    --summary-only      Only show final summary, suppress build progress

OUTPUT:
- LaTeX files saved to output directory (one per content item)
- Comprehensive summary report showing success/failure counts
- Detailed JSON report with full error information and statistics
- Console output showing which specific items failed and why

TYPICAL WORKFLOW:
1. Run with --limit 10 --summary-only first to check for systemic issues
2. If issues found, run with --verbose on smaller subsets to debug
3. Use --books-only or --adventures-only to isolate content type issues
4. Examine generated LaTeX files to verify rendering quality
5. Check JSON report for detailed error analysis and patterns
"""

import argparse
import sys
import tempfile
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dnd5e.cli.commands.convert import resolve_content_or_file
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex import LaTeXDocumentRenderer


class ContentBuilder:
    """Builds all adventures and books, collecting errors."""

    def __init__(
        self,
        output_dir: Path | None = None,
        no_images: bool = True,
        continue_on_error: bool = True,
        verbose: bool = False,
        summary_only: bool = False,
    ):
        self.output_dir = output_dir or Path(tempfile.mkdtemp(prefix="5e2pdf-test-"))
        self.no_images = no_images
        self.continue_on_error = continue_on_error
        self.verbose = verbose
        self.summary_only = summary_only

        self.results: dict[str, list[dict[str, Any]]] = {"adventures": [], "books": []}
        self.errors: dict[str, list[dict[str, Any]]] = {"adventures": [], "books": []}

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.summary_only:
            print(f"Output directory: {self.output_dir}")
            print(f"Images: {'disabled' if no_images else 'enabled'}")
            print(f"Continue on error: {continue_on_error}")
            print("-" * 60)

    def build_content(
        self,
        content_type: ContentType,
        content_list: list[Any],
        type_name: str,
        limit: int | None = None,
    ) -> None:
        """Build all content of a specific type."""
        if limit:
            content_list = content_list[:limit]

        if not self.summary_only:
            print(f"\n=== Building {len(content_list)} {type_name} ===")

        for i, content in enumerate(content_list, 1):
            content_id = getattr(content, "id", "unknown")
            content_name = content.name

            if not self.summary_only:
                print(f"\n[{i}/{len(content_list)}] {content_id}: {content_name}")

            try:
                # Build the content
                success = self._build_single_content(
                    content_type, content_id, content_name
                )

                result = {
                    "id": content_id,
                    "name": content_name,
                    "success": success,
                    "index": i,
                }
                self.results[type_name.lower()].append(result)

                if not self.summary_only:
                    status = "✓ SUCCESS" if success else "✗ FAILED"
                    print(f"    {status}")

            except Exception as e:
                error_info = {
                    "id": content_id,
                    "name": content_name,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "index": i,
                }
                self.errors[type_name.lower()].append(error_info)

                if not self.summary_only:
                    print(f"    ✗ ERROR: {e}")
                    if self.verbose:
                        print(f"    Traceback: {traceback.format_exc()}")

                if not self.continue_on_error:
                    raise

    def _build_single_content(
        self, content_type: ContentType, content_id: str, content_name: str
    ) -> bool:
        """Build a single piece of content to LaTeX."""
        try:
            # Create output filename
            safe_id = content_id.replace("|", "-").replace(":", "-")
            output_file = self.output_dir / f"{safe_id}.tex"

            # Use the resolve_content_or_file function like the CLI does
            content_items, source_desc = resolve_content_or_file(
                content_id, content_type
            )

            if not content_items:
                if self.verbose and not self.summary_only:
                    print(f"    No content resolved for {content_id}")
                return False

            # Create a simple render context (minimal requirements)
            from dnd5e.cli.main import get_omnidexer, get_tag_resolver

            omnidexer = get_omnidexer()
            tag_resolver = get_tag_resolver()

            context = RenderingContext(
                output_format="latex",
                omnidexer=omnidexer,
                metadata={
                    "title": content_name,
                    "include_images": not self.no_images,
                    "include_toc": True,
                    "tag_resolver": tag_resolver,
                },
            )

            # Render document
            renderer = LaTeXDocumentRenderer()
            result = renderer.render_document(content_items, context)

            if result:
                # Write output
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result)
                return True
            else:
                if self.verbose and not self.summary_only:
                    print(f"    No LaTeX content generated for {content_id}")
                return False

        except Exception as e:
            if self.verbose and not self.summary_only:
                print(f"    Build error: {e}")
            return False

    def print_summary(self) -> None:
        """Print a comprehensive summary of results."""
        print("\n" + "=" * 80)
        print("BUILD ALL CONTENT - SUMMARY REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output directory: {self.output_dir}")

        # Count totals
        total_adventures = len(self.results["adventures"]) + len(
            self.errors["adventures"]
        )
        total_books = len(self.results["books"]) + len(self.errors["books"])
        success_adventures = len(
            [r for r in self.results["adventures"] if r["success"]]
        )
        success_books = len([r for r in self.results["books"] if r["success"]])

        print("\n--- OVERVIEW ---")
        print(
            f"Adventures: {success_adventures}/{total_adventures} successful ({total_adventures - success_adventures} failed)"
        )
        print(
            f"Books:      {success_books}/{total_books} successful ({total_books - success_books} failed)"
        )
        print(
            f"Total:      {success_adventures + success_books}/{total_adventures + total_books} successful"
        )

        # Adventure errors
        if self.errors["adventures"]:
            print(f"\n--- ADVENTURE ERRORS ({len(self.errors['adventures'])}) ---")
            for error in self.errors["adventures"]:
                print(f"• {error['id']}: {error['name']}")
                print(f"  Error: {error['error']}")
                if self.verbose:
                    print(f"  Traceback:\n{error['traceback']}")

        # Book errors
        if self.errors["books"]:
            print(f"\n--- BOOK ERRORS ({len(self.errors['books'])}) ---")
            for error in self.errors["books"]:
                print(f"• {error['id']}: {error['name']}")
                print(f"  Error: {error['error']}")
                if self.verbose:
                    print(f"  Traceback:\n{error['traceback']}")

        # Failed builds (different from errors - these built but failed)
        failed_adventures = [r for r in self.results["adventures"] if not r["success"]]
        failed_books = [r for r in self.results["books"] if not r["success"]]

        if failed_adventures:
            print(f"\n--- FAILED ADVENTURE BUILDS ({len(failed_adventures)}) ---")
            for result in failed_adventures:
                print(f"• {result['id']}: {result['name']}")

        if failed_books:
            print(f"\n--- FAILED BOOK BUILDS ({len(failed_books)}) ---")
            for result in failed_books:
                print(f"• {result['id']}: {result['name']}")

        # Success cases
        if success_adventures > 0:
            print(f"\n--- SUCCESSFUL ADVENTURES ({success_adventures}) ---")
            successful = [r for r in self.results["adventures"] if r["success"]][:10]
            for result in successful:
                print(f"• {result['id']}: {result['name']}")
            if success_adventures > 10:
                print(f"  ... and {success_adventures - 10} more")

        if success_books > 0:
            print(f"\n--- SUCCESSFUL BOOKS ({success_books}) ---")
            successful = [r for r in self.results["books"] if r["success"]][:10]
            for result in successful:
                print(f"• {result['id']}: {result['name']}")
            if success_books > 10:
                print(f"  ... and {success_books - 10} more")

        print(f"\nOutput files saved to: {self.output_dir}")
        print("=" * 80)

    def save_detailed_report(self) -> Path:
        """Save a detailed JSON report of all results."""
        report_file = self.output_dir / "build_report.json"

        import json

        report_data = {
            "generated": datetime.now().isoformat(),
            "output_dir": str(self.output_dir),
            "settings": {
                "no_images": self.no_images,
                "continue_on_error": self.continue_on_error,
                "verbose": self.verbose,
            },
            "results": self.results,
            "errors": self.errors,
            "summary": {
                "total_adventures": len(self.results["adventures"])
                + len(self.errors["adventures"]),
                "total_books": len(self.results["books"]) + len(self.errors["books"]),
                "successful_adventures": len(
                    [r for r in self.results["adventures"] if r["success"]]
                ),
                "successful_books": len(
                    [r for r in self.results["books"] if r["success"]]
                ),
                "error_adventures": len(self.errors["adventures"]),
                "error_books": len(self.errors["books"]),
            },
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Build all adventures and books to find content issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("USAGE:")[1] if "USAGE:" in __doc__ else None,
    )

    parser.add_argument(
        "--adventures-only", action="store_true", help="Build only adventures"
    )
    parser.add_argument("--books-only", action="store_true", help="Build only books")
    parser.add_argument(
        "--limit", type=int, metavar="N", help="Build only first N items of each type"
    )
    parser.add_argument(
        "--output-dir", type=Path, metavar="PATH", help="Directory to save output files"
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Enable image processing (default: disabled)",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop building after first error"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show final summary, suppress build output",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.adventures_only and args.books_only:
        parser.error("Cannot specify both --adventures-only and --books-only")

    # Initialize builder
    builder = ContentBuilder(
        output_dir=args.output_dir,
        no_images=not args.images,
        continue_on_error=not args.stop_on_error,
        verbose=args.verbose,
        summary_only=args.summary_only,
    )

    try:
        # Load all content
        if not args.summary_only:
            print("Loading content from omnidexer...")

        omnidexer = Omnidexer()
        omnidexer.load_all_data()

        # Get content lists
        adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
        books = omnidexer.get_all_by_type(ContentType.BOOK)

        # Filter out test content
        adventures = [
            a for a in adventures if not getattr(a, "id", "").startswith("test-")
        ]
        books = [b for b in books if not getattr(b, "id", "").startswith("test-")]

        # Build content
        if not args.books_only:
            builder.build_content(
                ContentType.ADVENTURE, adventures, "Adventures", args.limit
            )

        if not args.adventures_only:
            builder.build_content(ContentType.BOOK, books, "Books", args.limit)

        # Print summary and save report
        builder.print_summary()
        report_file = builder.save_detailed_report()
        print(f"\nDetailed JSON report saved: {report_file}")

    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user")
        builder.print_summary()
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
