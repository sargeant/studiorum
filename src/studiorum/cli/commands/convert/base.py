"""Base classes and mixins for convert commands."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from studiorum.cli.config_factory import (
    get_compile_pdf_default,
    get_document_class_default,
    get_fonts_default,
    get_with_images_default,
)
from studiorum.core.config.sources import get_content_config
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
        from studiorum.cli.async_bridge import get_omnidexer_sync

        omnidexer = get_omnidexer_sync()
        self._content_reference_manager = ContentReferenceManager(omnidexer)

    def _safe_getattr(self, obj: Any, attr_path: str) -> Any:
        """Safely get nested attribute, returning None if any part is missing."""
        try:
            result = obj
            for attr in attr_path.split("."):
                result = getattr(result, attr)
            return result
        except AttributeError:
            return None

    @staticmethod
    def get_common_parameters() -> dict[str, Any]:
        """Return common parameter definitions."""
        return {
            "output_file": typer.Option(
                None, "--output", "-o", help="Output LaTeX file"
            ),
            "title": typer.Option(None, "--title", help="Document title"),
            "compile_pdf": typer.Option(
                get_compile_pdf_default(),
                "--pdf",
                help="Compile to PDF after conversion",
            ),
        }

    def apply_config_hierarchy(self, **cli_args: Any) -> dict[str, Any]:
        """Apply configuration hierarchy: CLI args > user config > app defaults."""
        app_config = get_app_config()
        user_config = get_content_config()

        # Extract CLI values
        paper = cli_args.get("paper")
        fonts = cli_args.get("fonts")
        background = cli_args.get("background")
        no_outline = cli_args.get("no_outline")
        font_size = cli_args.get("font_size")
        high_contrast = cli_args.get("high_contrast")
        two_column = cli_args.get("two_column")
        justified = cli_args.get("justified")

        # Extract additional CLI values
        title = cli_args.get("title")
        author = cli_args.get("author")
        main_font = cli_args.get("main_font")
        sans_font = cli_args.get("sans_font")
        mono_font = cli_args.get("mono_font")
        output_dir = cli_args.get("output_dir")

        # Apply hierarchy for each configuration option
        actual_config = {
            "paper_size": (
                paper
                or self._safe_getattr(user_config, "latex.paper_size")
                or app_config.rendering.latex.document.paper_size
            ),
            "fonts": (
                fonts
                or self._safe_getattr(user_config, "latex.fonts")
                or app_config.rendering.latex.document.fonts
            ),
            "main_font": (
                main_font
                or self._safe_getattr(user_config, "latex.fonts.main_font")
                or None  # No specific main_font in app config structure
            ),
            "sans_font": (
                sans_font
                or self._safe_getattr(user_config, "latex.fonts.sans_font")
                or None  # No specific sans_font in app config structure
            ),
            "mono_font": (
                mono_font
                or self._safe_getattr(user_config, "latex.fonts.mono_font")
                or None  # No specific mono_font in app config structure
            ),
            "title": (
                title
                or self._safe_getattr(user_config, "latex.title")
                or None  # No title in app config document structure
            ),
            "author": (
                author
                or self._safe_getattr(user_config, "latex.author")
                or None  # No author in app config document structure
            ),
            "margin_top": (
                cli_args.get("margin_top")
                or self._safe_getattr(user_config, "latex.margin_top")
                or "1in"  # Default margin
            ),
            "margin_bottom": (
                cli_args.get("margin_bottom")
                or self._safe_getattr(user_config, "latex.margin_bottom")
                or "1in"  # Default margin
            ),
            "margin_left": (
                cli_args.get("margin_left")
                or self._safe_getattr(user_config, "latex.margin_left")
                or "1in"  # Default margin
            ),
            "margin_right": (
                cli_args.get("margin_right")
                or self._safe_getattr(user_config, "latex.margin_right")
                or "1in"  # Default margin
            ),
            "output_directory": (
                output_dir
                or self._safe_getattr(user_config, "output_directory")
                or app_config.paths.output_path
            ),
            "background": (
                background
                or self._safe_getattr(user_config, "latex.background")
                or app_config.rendering.latex.document.background
            ),
            "no_outline": (
                no_outline
                if no_outline is not None
                else self._safe_getattr(user_config, "latex.no_outline")
                if self._safe_getattr(user_config, "latex.no_outline") is not None
                else app_config.rendering.latex.document.no_outline
            ),
            "font_size": (
                font_size
                or self._safe_getattr(user_config, "latex.font_size")
                or app_config.rendering.latex.document.font_size
            ),
            "high_contrast": (
                high_contrast
                if high_contrast is not None
                else self._safe_getattr(user_config, "latex.high_contrast")
                if self._safe_getattr(user_config, "latex.high_contrast") is not None
                else app_config.rendering.latex.document.high_contrast
            ),
            "two_column": (
                two_column
                if two_column is not None
                else self._safe_getattr(user_config, "latex.two_column")
                if self._safe_getattr(user_config, "latex.two_column") is not None
                else app_config.rendering.latex.document.two_column
            ),
            "justified": (
                justified
                if justified is not None
                else self._safe_getattr(user_config, "latex.justified")
                if self._safe_getattr(user_config, "latex.justified") is not None
                else app_config.rendering.latex.document.justified_text
            ),
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
        from studiorum.cli.async_bridge import get_omnidexer_sync

        loader = ContentLoader()

        if use_omnidexer:
            from studiorum.core.models.content import ContentType

            omnidexer = get_omnidexer_sync()
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

    def validate_output_directory(self, output_dir: Path) -> None:
        """Validate and create output directory if needed."""
        from studiorum.core.errors.architecture_errors import ConfigurationError

        if output_dir.exists():
            if not output_dir.is_dir():
                raise ConfigurationError(
                    f"Output path {output_dir} exists but is not a directory",
                    config_key="output_directory",
                    config_source="cli",
                )
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

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
                elif result.warnings:
                    rprint(f"[yellow]Warnings for {source_name}:[/yellow]")
                    for warning in result.warnings:
                        rprint(f"  - {warning}")

        # Load content
        content_items = loader.load_all()

        if not content_items:
            raise ValueError("No valid content loaded from any source")

        return content_items


class LaTeXMixin:
    """Mixin for LaTeX-specific parameters."""

    @staticmethod
    def get_latex_parameter_definitions() -> dict[str, Any]:
        """Return LaTeX parameter definitions."""
        return {
            "with_images": typer.Option(
                get_with_images_default(),
                "--images/--no-images",
                help="Include images",
                rich_help_panel="Visual Styling",
            ),
            "document_class": typer.Option(
                get_document_class_default(),
                "--document-class",
                help="LaTeX document class (dndbook, dndarticle)",
                rich_help_panel="Document Layout",
            ),
            "paper": typer.Option(
                None,
                "--paper",
                help="Paper size (letter, a4, a5)",
                rich_help_panel="Document Layout",
            ),
            "fonts": typer.Option(
                get_fonts_default(),
                "--fonts",
                help="Font package to use (wotc, dmsguild)",
                rich_help_panel="Visual Styling",
            ),
            "no_outline": typer.Option(
                None,
                "--no-outline",
                help="Disable document outline",
                rich_help_panel="Visual Styling",
            ),
            "font_size": typer.Option(
                None,
                "--font-size",
                help="Base font size (10pt, 11pt, 12pt)",
                rich_help_panel="Visual Styling",
            ),
            "background": typer.Option(
                None,
                "--background",
                "--bg",
                help="Background style (full, none, print)",
                rich_help_panel="Visual Styling",
            ),
            "high_contrast": typer.Option(
                None,
                "--high-contrast",
                help="Use high contrast mode",
                rich_help_panel="Visual Styling",
            ),
            "two_column": typer.Option(
                None,
                "--two-column/--one-column",
                help="Use two-column layout",
                rich_help_panel="Document Layout",
            ),
            "justified": typer.Option(
                None,
                "--justified/--not-justified",
                help="Justify text columns",
                rich_help_panel="Document Layout",
            ),
        }

    def get_latex_parameters(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get LaTeX parameters from config (instance method)."""
        params = {
            "paper_size": config.get("paper_size", "letterpaper"),
            "title": config.get("title"),
            "author": config.get("author"),
            "margin_top": config.get("margin_top", "1in"),
            "margin_bottom": config.get("margin_bottom", "1in"),
            "margin_left": config.get("margin_left", "1in"),
            "margin_right": config.get("margin_right", "1in"),
        }

        # Handle fonts
        main_font = config.get("main_font")
        sans_font = config.get("sans_font")
        mono_font = config.get("mono_font")

        if main_font or sans_font or mono_font:
            params["use_custom_fonts"] = True
            params["main_font"] = main_font
            params["sans_font"] = sans_font
            params["mono_font"] = mono_font
        else:
            params["use_custom_fonts"] = False

        return params

    def get_latex_context_parameters(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get LaTeX parameters from config for context."""
        return self.get_latex_parameters(config)

    def prepare_latex_context(
        self, config: dict[str, Any], content: list[Any]
    ) -> dict[str, Any]:
        """Prepare LaTeX context from config and content."""
        context = self.get_latex_context_parameters(config)
        context["content"] = content
        context["show_title_page"] = self.should_include_title_page(config)
        context["include_toc"] = self.should_include_toc(config, content)
        return context

    def should_include_title_page(self, config: dict[str, Any]) -> bool:
        """Determine if title page should be included."""
        title = config.get("title")
        return bool(title and title.strip())

    def should_include_toc(self, config: dict[str, Any], content: list[Any]) -> bool:
        """Determine if table of contents should be included."""
        # Check explicit config first
        include_toc = config.get("include_toc")
        if include_toc is not None:
            return bool(include_toc)

        # Default: include TOC for multiple items
        return len(content) > 1


class AppendixMixin:
    """Mixin for appendix generation functionality with unified reference tracking."""

    def __init__(self) -> None:
        """Initialize the appendix mixin."""
        from studiorum.cli.async_bridge import get_omnidexer_sync

        if not hasattr(self, "_content_reference_manager"):
            omnidexer = get_omnidexer_sync()
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

    def generate_legacy_appendices(
        self,
        reference_manager: ContentReferenceManager,
        appendix_flags: Any,
        template_engine: Any,
        omnidexer: Any,
    ) -> Any:
        """Legacy appendix generation for backward compatibility.

        Args:
            reference_manager: ContentReferenceManager with tracked references
            appendix_flags: Flags indicating which appendices to generate
            template_engine: Template engine for rendering
            omnidexer: Omnidexer for content resolution

        Returns:
            Generated appendix content as LaTeX string
        """
        from studiorum.core.services.appendix_generator import AppendixGenerator

        # Use the ContentTracker from the reference manager for backward compatibility
        content_tracker = reference_manager.get_content_tracker()

        # Create appendix generator
        appendix_generator = AppendixGenerator(
            omnidexer=omnidexer, template_engine=template_engine
        )

        # Generate appendices using existing system
        return appendix_generator.generate_appendices(content_tracker, appendix_flags)


# Helper functions for parameter combinations
def get_all_convert_parameters() -> dict[str, Any]:
    """Get all convert command parameters combined."""
    params = {}
    params.update(BaseConvertCommand.get_common_parameters())
    params.update(LaTeXMixin.get_latex_parameter_definitions())
    return params
