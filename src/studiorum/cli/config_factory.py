"""CLI configuration factory for getting defaults from unified config."""

from ..core.config.unified_config import get_app_config


# Helper functions for specific defaults
def get_document_class_default() -> str:
    """Get default document class from config."""
    return get_app_config().rendering.latex.document.document_class


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
