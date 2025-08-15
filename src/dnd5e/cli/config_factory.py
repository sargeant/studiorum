"""CLI configuration factory for getting defaults from unified config."""

from typing import Any

from ..core.config.unified_config import get_app_config


def get_cli_defaults() -> dict[str, Any]:
    """Get CLI parameter defaults from unified config."""
    config = get_app_config()
    return {
        # Document structure
        "document_class": config.rendering.latex.document.document_class,
        "font_size": config.rendering.latex.document.font_size,
        "background": config.rendering.latex.document.background,
        "two_column": config.rendering.latex.document.two_column,
        "justified": config.rendering.latex.document.justified_text,
        # Content inclusion
        "with_images": config.rendering.content.include_images,
        "with_index": config.rendering.latex.document.show_index,
        # Appendix generation
        "appendix_spells": config.rendering.content.appendix_spells,
        "appendix_items": config.rendering.content.appendix_items,
        "appendix_creatures": config.rendering.content.appendix_creatures,
        # Font and outline options
        "fonts": config.rendering.latex.document.fonts,
        "no_outline": config.rendering.latex.document.no_outline,
        # Compilation
        "compile_pdf": config.rendering.compilation.auto_compile_pdf,
        # Processing
        "concurrent_limit": config.processing.max_workers,
    }


def get_config_default(field_name: str) -> Any:
    """Get a specific config default by field name."""
    defaults = get_cli_defaults()
    return defaults.get(field_name)


# Helper functions for specific defaults
def get_document_class_default() -> str:
    """Get default document class from config."""
    return get_app_config().rendering.latex.document.document_class


def get_font_size_default() -> str:
    """Get default font size from config."""
    return get_app_config().rendering.latex.document.font_size


def get_background_default() -> str:
    """Get default background from config."""
    return get_app_config().rendering.latex.document.background


def get_high_contrast_default() -> bool:
    """Get default high contrast setting from config."""
    return get_app_config().rendering.latex.document.high_contrast


def get_two_column_default() -> bool:
    """Get default two column setting from config."""
    return get_app_config().rendering.latex.document.two_column


def get_justified_default() -> bool:
    """Get default justified text setting from config."""
    return get_app_config().rendering.latex.document.justified_text


def get_with_images_default() -> bool:
    """Get default include images setting from config."""
    return get_app_config().rendering.content.include_images


def get_with_index_default() -> bool:
    """Get default include index setting from config."""
    return get_app_config().rendering.latex.document.show_index


def get_compile_pdf_default() -> bool:
    """Get default compile PDF setting from config."""
    return get_app_config().rendering.compilation.auto_compile_pdf


def get_concurrent_limit_default() -> int:
    """Get default concurrent limit from config."""
    return get_app_config().processing.max_workers


def get_fonts_default() -> str | None:
    """Get default fonts setting from config."""
    return get_app_config().rendering.latex.document.fonts


def get_no_outline_default() -> bool:
    """Get default no outline setting from config."""
    return get_app_config().rendering.latex.document.no_outline


def get_appendix_spells_default() -> bool:
    """Get default appendix spells setting from config."""
    return get_app_config().rendering.content.appendix_spells


def get_appendix_items_default() -> bool:
    """Get default appendix items setting from config."""
    return get_app_config().rendering.content.appendix_items


def get_appendix_creatures_default() -> bool:
    """Get default appendix creatures setting from config."""
    return get_app_config().rendering.content.appendix_creatures


def get_default_sources() -> list[str]:
    """Get default sources for content resolution from config."""
    return get_app_config().rendering.content.default_sources
