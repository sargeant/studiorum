"""Base classes and mixins for convert commands."""

from typing import Any

import typer

from dnd5e.cli.config_factory import (
    get_compile_pdf_default,
    get_document_class_default,
    get_fonts_default,
    get_with_images_default,
)
from dnd5e.core.config.sources import get_content_config
from dnd5e.core.config.unified_config import get_app_config
from dnd5e.core.references.content_reference_manager import (
    ContentReferenceManager,
    ReferenceTrackingTagResolver,
)


class BaseConvertCommand:
    """Base class for all conversion commands."""

    @staticmethod
    def get_common_parameters():
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

    def apply_config_hierarchy(self, **cli_args) -> dict[str, Any]:
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

        # Apply hierarchy for each configuration option
        actual_config = {
            "paper_size": (
                paper
                or user_config.latex.paper_size
                or app_config.rendering.latex.document.paper_size
            ),
            "fonts": (
                fonts
                or user_config.latex.fonts
                or app_config.rendering.latex.document.fonts
            ),
            "background": (
                background
                or user_config.latex.background
                or app_config.rendering.latex.document.background
            ),
            "no_outline": (
                no_outline
                if no_outline is not None
                else user_config.latex.no_outline
                if user_config.latex.no_outline is not None
                else app_config.rendering.latex.document.no_outline
            ),
            "font_size": (
                font_size
                or user_config.latex.font_size
                or app_config.rendering.latex.document.font_size
            ),
            "high_contrast": (
                high_contrast
                if high_contrast is not None
                else user_config.latex.high_contrast
                if user_config.latex.high_contrast is not None
                else app_config.rendering.latex.document.high_contrast
            ),
            "two_column": (
                two_column
                if two_column is not None
                else user_config.latex.two_column
                if user_config.latex.two_column is not None
                else app_config.rendering.latex.document.two_column
            ),
            "justified": (
                justified
                if justified is not None
                else user_config.latex.justified
                if user_config.latex.justified is not None
                else app_config.rendering.latex.document.justified_text
            ),
        }

        return actual_config


class LaTeXMixin:
    """Mixin for LaTeX-specific parameters."""

    @staticmethod
    def get_latex_parameters():
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


class AppendixMixin:
    """Mixin for appendix generation functionality with unified reference tracking."""

    @staticmethod
    def add_appendix_arguments(func):
        """Decorator to add appendix arguments to command functions."""
        # This is a placeholder for future appendix arguments
        # Will be expanded when implementing unified reference system
        return func

    def create_reference_manager(self, omnidexer=None):
        """Create a unified content reference manager.

        Args:
            omnidexer: The omnidexer instance for content resolution

        Returns:
            ContentReferenceManager instance for tracking all content references
        """
        return ContentReferenceManager(omnidexer=omnidexer)

    def create_reference_tracking_tag_resolver(self, tag_resolver, reference_manager):
        """Create a tag resolver that automatically tracks references.

        Args:
            tag_resolver: The original tag resolver
            reference_manager: The content reference manager to track with

        Returns:
            ReferenceTrackingTagResolver that wraps the original resolver
        """
        return ReferenceTrackingTagResolver(tag_resolver, reference_manager)

    def track_deep_index_references(
        self, reference_manager, content_items, context="content processing"
    ):
        """Track references from deep indexing of content items.

        Args:
            reference_manager: The content reference manager
            content_items: List of content items to deep index
            context: Context description for tracking
        """
        from dnd5e.core.interfaces import DeepIndexable

        for content in content_items:
            if isinstance(content, DeepIndexable):
                reference_manager.track_deep_index_references(content, context)

    def generate_appendices(
        self, reference_manager, appendix_flags, template_engine, omnidexer
    ):
        """Unified appendix generation using the reference manager.

        Args:
            reference_manager: ContentReferenceManager with tracked references
            appendix_flags: Flags indicating which appendices to generate
            template_engine: Template engine for rendering
            omnidexer: Omnidexer for content resolution

        Returns:
            Generated appendix content as LaTeX string
        """
        from dnd5e.core.services.appendix_generator import AppendixGenerator

        # Use the ContentTracker from the reference manager for backward compatibility
        content_tracker = reference_manager.get_content_tracker()

        # Create appendix generator
        appendix_generator = AppendixGenerator(
            omnidexer=omnidexer, template_engine=template_engine
        )

        # Generate appendices using existing system
        return appendix_generator.generate_appendices(content_tracker, appendix_flags)


# Helper functions for parameter combinations
def get_all_convert_parameters():
    """Get all convert command parameters combined."""
    params = {}
    params.update(BaseConvertCommand.get_common_parameters())
    params.update(LaTeXMixin.get_latex_parameters())
    return params
