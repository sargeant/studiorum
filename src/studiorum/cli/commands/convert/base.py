"""Base classes and mixins for convert commands."""

from pathlib import Path
from typing import Any

import typer

from studiorum.cli.config_factory import (
    get_compile_pdf_default,
)
from studiorum.cli.context import get_services
from studiorum.core.config.unified_config import get_app_config
from studiorum.core.loaders.content_sources import (
    ContentLoader,
    create_file_source,
    create_omnidexer_source,
    create_stdin_source,
)
from studiorum.core.logging import get_logger
from studiorum.core.references.content_reference_manager import (
    ContentReferenceManager,
    ReferenceTrackingTagResolver,
)


class BaseConvertCommand:
    """Base class for all conversion commands."""

    def __init__(self) -> None:
        """Initialize the base convert command."""
        omnidexer = get_services().omnidexer
        self._content_reference_manager = ContentReferenceManager(omnidexer)

    @staticmethod
    def get_common_parameters() -> dict[str, Any]:
        """Return common parameter definitions."""
        return {
            "output_file": typer.Option(
                None, "--output", "-o", help="Output LaTeX file"
            ),
            "title": typer.Option(None, "--title", help="Document title"),
            "compile_pdf": typer.Option(
                ...,
                "--pdf",
                help="Compile to PDF after conversion",
                default_factory=get_compile_pdf_default,
            ),
        }

    def apply_config_hierarchy(self, **cli_args: Any) -> dict[str, Any]:
        """Apply configuration hierarchy: CLI args > app config."""
        app_config = get_app_config()

        # Extract CLI values
        paper = cli_args.get("paper")
        fonts = cli_args.get("fonts")
        background = cli_args.get("background")
        no_outline = cli_args.get("no_outline")
        font_size = cli_args.get("font_size")
        high_contrast = cli_args.get("high_contrast")
        two_column = cli_args.get("two_column")
        justified = cli_args.get("justified")
        statblock = cli_args.get("statblock")

        # Extract additional CLI values
        title = cli_args.get("title")
        author = cli_args.get("author")
        main_font = cli_args.get("main_font")
        sans_font = cli_args.get("sans_font")
        mono_font = cli_args.get("mono_font")
        output_dir = cli_args.get("output_dir")

        # Apply hierarchy for each configuration option
        actual_config = {
            "paper_size": (paper or app_config.rendering.latex.document.paper_size),
            "fonts": (fonts or app_config.rendering.latex.document.fonts),
            "main_font": (
                main_font or None  # No specific main_font in app config structure
            ),
            "sans_font": (
                sans_font or None  # No specific sans_font in app config structure
            ),
            "mono_font": (
                mono_font or None  # No specific mono_font in app config structure
            ),
            "title": (
                title or None  # No title in app config document structure
            ),
            "author": (
                author or None  # No author in app config document structure
            ),
            "margin_top": (
                cli_args.get("margin_top") or "1in"  # Default margin
            ),
            "margin_bottom": (
                cli_args.get("margin_bottom") or "1in"  # Default margin
            ),
            "margin_left": (
                cli_args.get("margin_left") or "1in"  # Default margin
            ),
            "margin_right": (
                cli_args.get("margin_right") or "1in"  # Default margin
            ),
            "output_directory": (output_dir or app_config.paths.output_path),
            "background": (
                background or app_config.rendering.latex.document.background
            ),
            "no_outline": (
                no_outline
                if no_outline is not None
                else app_config.rendering.latex.document.no_outline
            ),
            "font_size": (font_size or app_config.rendering.latex.document.font_size),
            "high_contrast": (
                high_contrast
                if high_contrast is not None
                else app_config.rendering.latex.document.high_contrast
            ),
            "two_column": (
                two_column
                if two_column is not None
                else app_config.rendering.latex.document.two_column
            ),
            "justified": (
                justified
                if justified is not None
                else app_config.rendering.latex.document.justified_text
            ),
            "statblock": (statblock or app_config.rendering.latex.document.statblock),
        }

        return actual_config

    def get_content_loader(
        self,
        content_type: str,
        file_paths: list[Path] | None = None,
        use_omnidexer: bool = False,
        use_stdin: bool = False,
    ) -> ContentLoader:
        """Get a content loader configured with the specified sources."""

        loader = ContentLoader()

        if use_omnidexer:
            from studiorum.core.models.content import ContentType

            omnidexer = get_services().omnidexer
            # Convert string to ContentType enum
            content_type_enum = ContentType(content_type.lower())
            source = create_omnidexer_source(omnidexer, content_type_enum)
            loader.add_source(source)

        if file_paths:
            for file_path in file_paths:
                file_source = create_file_source(file_path)
                loader.add_source(file_source)

        if use_stdin:
            stdin_source = create_stdin_source()
            loader.add_source(stdin_source)

        return loader

    def get_content_reference_manager(self) -> ContentReferenceManager:
        """Get the content reference manager."""
        return self._content_reference_manager

    def create_content_loader(self) -> ContentLoader:
        """Create a unified content loader.

        Returns:
            ContentLoader instance for managing multiple content sources
        """
        return ContentLoader()

    def add_file_source(
        self, loader: ContentLoader, file_path: Any, content_type: Any = None
    ) -> None:
        """Add a file source to the content loader.

        Args:
            loader: ContentLoader instance
            file_path: Path to the JSON file
            content_type: Optional content type filter
        """
        from pathlib import Path

        source = create_file_source(Path(file_path), content_type)
        loader.add_source(source)

    def add_omnidexer_source(
        self, loader: ContentLoader, omnidexer: Any, content_type: Any
    ) -> None:
        """Add an omnidexer source to the content loader.

        Args:
            loader: ContentLoader instance
            omnidexer: The omnidexer instance
            content_type: Content type to load
        """
        source = create_omnidexer_source(omnidexer, content_type)
        loader.add_source(source)

    def add_stdin_source(self, loader: ContentLoader, content_type: Any = None) -> None:
        """Add a stdin source to the content loader.

        Args:
            loader: ContentLoader instance
            content_type: Optional content type filter
        """
        source = create_stdin_source(content_type)
        loader.add_source(source)

    def get_name_list_from_file(self, file_path: Path, content_type: str) -> list[str]:
        """Load a list of content names from a file using ContentLoader.

        Args:
            file_path: Path to file containing names (one per line)
            content_type: Type of content (for validation and metadata)

        Returns:
            List of content names

        Raises:
            typer.Exit: If file cannot be loaded or validated
        """
        import typer
        from rich import print as rprint

        from studiorum.core.loaders.content_sources import create_name_list_source
        from studiorum.core.models.content import ContentType

        try:
            content_type_enum = ContentType(content_type.lower())
        except ValueError:
            rprint(f"[red]Error:[/red] Invalid content type: {content_type}")
            raise typer.Exit(1)

        name_source = create_name_list_source(file_path, content_type_enum)

        # Validate the source
        validation = name_source.validate()
        if not validation.is_valid:
            for error in validation.errors:
                rprint(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Show warnings if any
        for warning in validation.warnings:
            rprint(f"[yellow]Warning:[/yellow] {warning}")

        try:
            names = name_source.load()
            return names
        except Exception as e:
            rprint(f"[red]Error:[/red] Failed to load names from {file_path}: {e}")
            raise typer.Exit(1)

    def get_enhanced_name_list_from_file(
        self, file_path: Path, content_type: str
    ) -> list[tuple[int, str, str | None]]:
        """Load enhanced name list with count and source information.

        This method extends get_name_list_from_file() to return structured data
        that includes count and source information parsed from the file.

        Args:
            file_path: Path to file containing names with optional counts and sources
            content_type: Type of content (for validation and metadata)

        Returns:
            List of tuples containing (count, name, source) where:
            - count: Number of items (defaults to 1 if not specified)
            - name: The content name
            - source: Source abbreviation (None if not specified)

        Raises:
            typer.Exit: If file cannot be loaded or validated

        Examples:
            Input file formats supported:
            - "Goblin" → (1, "Goblin", None)
            - "3 Goblin" → (3, "Goblin", None)
            - "Goblin|MM" → (1, "Goblin", "MM")
            - "3 Goblin|MM" → (3, "Goblin", "MM")
        """
        import typer
        from rich import print as rprint

        from studiorum.core.loaders.content_sources import create_name_list_source
        from studiorum.core.models.content import ContentType

        try:
            content_type_enum = ContentType(content_type.lower())
        except ValueError:
            rprint(f"[red]Error:[/red] Invalid content type: {content_type}")
            raise typer.Exit(1)

        name_source = create_name_list_source(file_path, content_type_enum)

        # Validate the source
        validation = name_source.validate()
        if not validation.is_valid:
            for error in validation.errors:
                rprint(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Show warnings if any
        for warning in validation.warnings:
            rprint(f"[yellow]Warning:[/yellow] {warning}")

        try:
            # Use the new structured loading method
            structured_data = name_source.load_structured()
            return structured_data
        except Exception as e:
            rprint(
                f"[red]Error:[/red] Failed to load enhanced names from {file_path}: {e}"
            )
            raise typer.Exit(1)

    def get_enhanced_name_list_from_stdin(
        self, content_type: str
    ) -> list[tuple[int, str, str | None]]:
        """Load enhanced name list with count and source information from stdin.

        Mirrors :meth:`get_enhanced_name_list_from_file` but reads from stdin,
        applying the same ``[count] name[|source]`` parsing rules so the two
        input modes behave identically.

        Args:
            content_type: Type of content (for error messages and consistency).

        Returns:
            List of tuples containing (count, name, source).

        Raises:
            typer.Exit: If stdin is a TTY or no usable names were found.
        """
        import sys

        import typer
        from rich import print as rprint

        from studiorum.core.loaders.content_sources import parse_enhanced_name_lines

        if sys.stdin.isatty():
            rprint("[red]Error:[/red] No input provided via stdin")
            raise typer.Exit(1)

        try:
            lines = list(sys.stdin)
        except KeyboardInterrupt:
            rprint("[red]Error:[/red] Input interrupted")
            raise typer.Exit(1)

        structured_data = parse_enhanced_name_lines(lines)

        if not structured_data:
            rprint(f"[red]Error:[/red] No {content_type} names found in stdin")
            raise typer.Exit(1)

        return structured_data

    def validate_and_load_content(
        self, loader: ContentLoader, show_validation: bool = True
    ) -> Any:
        """Validate sources and load content with error handling.

        Args:
            loader: ContentLoader with configured sources
            show_validation: Whether to display validation results

        Returns:
            List of loaded content items

        Raises:
            ValueError: If validation fails or no content is loaded
        """
        # Validate all sources
        validation_results = loader.validate_all()

        if show_validation:
            from rich import print as rprint

            for source_name, result in validation_results.items():
                if not result.is_valid:
                    rprint(f"[red]Validation failed for {source_name}:[/red]")
                    for error in result.errors:
                        rprint(f"  - {error}")
                    raise ValueError(f"Content source validation failed: {source_name}")
                if result.warnings:
                    rprint(f"[yellow]Warnings for {source_name}:[/yellow]")
                    for warning in result.warnings:
                        rprint(f"  - {warning}")

        # Load content
        content_items = loader.load_all()

        if not content_items:
            raise ValueError("No valid content loaded from any source")

        return content_items


class AppendixMixin:
    """Mixin for appendix generation functionality with unified reference tracking."""

    def __init__(self) -> None:
        """Initialize the appendix mixin."""

        if not hasattr(self, "_content_reference_manager"):
            omnidexer = get_services().omnidexer
            self._content_reference_manager = ContentReferenceManager(omnidexer)

        self.logger = get_logger(self.__class__.__name__)

    def get_content_reference_manager(self) -> ContentReferenceManager:
        """Get the content reference manager."""
        return self._content_reference_manager

    def track_content_references(
        self, content: list[Any], context: str = "main content"
    ) -> None:
        """Track references from content items."""
        reference_manager = self.get_content_reference_manager()

        for item in content:
            try:
                reference_manager.track_deep_index_references(item, context)
            except Exception as e:
                # Graceful degradation - continue processing other items
                # Log the error for debugging but don't fail the entire process
                self.logger.debug(
                    f"Failed to track references for item in {context}: {e}. "
                    f"Item type: {type(item).__name__}. Continuing gracefully."
                )

    def generate_appendices(self) -> dict[str, Any]:
        """Generate appendices from tracked references."""
        reference_manager = self.get_content_reference_manager()

        # Get references by type
        spell_refs = reference_manager.get_unique_references_by_type("spell")
        creature_refs = reference_manager.get_unique_references_by_type("creature")
        item_refs = reference_manager.get_unique_references_by_type("item")

        # Generate appendices
        appendices: dict[str, Any] = {
            "has_appendices": bool(spell_refs or creature_refs or item_refs),
            "spell_appendix": None,
            "creature_appendix": None,
            "item_appendix": None,
        }

        if spell_refs:
            appendices["spell_appendix"] = "Spell appendix content"

        if creature_refs:
            appendices["creature_appendix"] = "Creature appendix content"

        if item_refs:
            appendices["item_appendix"] = "Item appendix content"

        return appendices

    @staticmethod
    def add_appendix_arguments(func: Any) -> Any:
        """Decorator to add appendix arguments to command functions."""
        # This is a placeholder for future appendix arguments
        # Will be expanded when implementing unified reference system
        return func

    def create_reference_manager(
        self, omnidexer: Any = None
    ) -> ContentReferenceManager:
        """Create a unified content reference manager.

        Args:
            omnidexer: The omnidexer instance for content resolution

        Returns:
            ContentReferenceManager instance for tracking all content references
        """
        return ContentReferenceManager(omnidexer=omnidexer)

    def create_reference_tracking_tag_resolver(
        self, tag_resolver: Any, reference_manager: ContentReferenceManager
    ) -> ReferenceTrackingTagResolver:
        """Create a tag resolver that automatically tracks references.

        Args:
            tag_resolver: The original tag resolver
            reference_manager: The content reference manager to track with

        Returns:
            ReferenceTrackingTagResolver that wraps the original resolver
        """
        return ReferenceTrackingTagResolver(tag_resolver, reference_manager)

    def track_deep_index_references(
        self,
        reference_manager: ContentReferenceManager,
        content_items: list[Any],
        context: str = "content processing",
    ) -> None:
        """Track references from deep indexing of content items.

        Args:
            reference_manager: The content reference manager
            content_items: List of content items to deep index
            context: Context description for tracking
        """
        from studiorum.core.interfaces import DeepIndexable

        for content in content_items:
            if isinstance(content, DeepIndexable):
                reference_manager.track_deep_index_references(content, context)
