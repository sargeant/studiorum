"""
Workflow configuration helpers for common D&D 5e use cases.

This module provides smart configuration presets for common D&D workflows,
returning partial ApplicationConfig dictionaries that can be applied as overrides
to the base configuration.
"""

from __future__ import annotations

from typing import Any


def get_spellbook_workflow_config(
    *,
    include_homebrew: bool = True,
    cleric_focused: bool = True,
    optimize_for_print: bool = False,
) -> dict[str, Any]:
    """
    Configuration optimized for spellbook generation.

    Provides settings ideal for creating spell reference documents with:
    - Cleric spells + homebrew sources by default
    - Optimal layout for spell lists and descriptions
    - Background settings optimized for readability

    Args:
        include_homebrew: Whether to include homebrew spell sources
        cleric_focused: Whether to optimize for cleric spell lists
        optimize_for_print: Whether to optimize for physical printing

    Returns:
        Partial ApplicationConfig dict for spellbook workflows

    Example:
        >>> config_overrides = get_spellbook_workflow_config(
        ...     include_homebrew=True,
        ...     optimize_for_print=True
        ... )
        >>> # Apply to base config
    """
    sources = ["xphb", "xmm"]  # Core sources
    if include_homebrew:
        sources.extend(["brew", "homebrew"])
    if cleric_focused:
        sources.extend(["tce", "xge"])  # Extended cleric options

    background = "none" if optimize_for_print else "full"

    return {
        "rendering": {
            "content": {
                "appendix_spells": True,
                "default_sources": sources,
                "include_images": not optimize_for_print,
            },
            "latex": {
                "document": {
                    "document_class": "dndarticle",
                    "class_options": ["justified", "twocolumn"],
                    "paper_size": "letter",
                    "background": background,
                    "high_contrast": optimize_for_print,
                    "two_column": True,
                    "show_toc": True,
                    "show_index": True,
                },
                "rendering": {
                    "appendix_organization": "alphabetical",
                    "enable_hyperlinks": not optimize_for_print,
                },
            },
        },
        "validation": {
            "strictness": "normal",
            "enable_summary": True,
        },
    }


def get_encounter_printing_workflow_config(
    *,
    paper_size: str = "a4",
    high_contrast: bool = True,
    include_images: bool = False,
) -> dict[str, Any]:
    """
    Configuration optimized for encounter printing.

    Provides settings ideal for printing encounter materials with:
    - A4 paper, no background for easy printing
    - Statblock-optimized formatting
    - Specific adventure content filtering

    Args:
        paper_size: Paper size for printing ("a4", "letter")
        high_contrast: Whether to use high contrast for better printing
        include_images: Whether to include images (usually False for printing)

    Returns:
        Partial ApplicationConfig dict for encounter printing workflows

    Example:
        >>> config_overrides = get_encounter_printing_workflow_config(
        ...     paper_size="a4",
        ...     high_contrast=True
        ... )
    """
    return {
        "rendering": {
            "content": {
                "appendix_creatures": True,
                "appendix_items": True,
                "default_sources": ["xphb", "xmm", "xdmg"],
                "include_images": include_images,
            },
            "latex": {
                "document": {
                    "document_class": "dndarticle",
                    "class_options": ["justified"],
                    "paper_size": paper_size,
                    "background": "none",
                    "high_contrast": high_contrast,
                    "two_column": False,
                    "show_toc": False,
                    "show_index": False,
                    "fancy_headers": False,
                },
                "rendering": {
                    "enable_hyperlinks": False,
                    "enable_cross_refs": False,
                    "auto_page_refs": True,
                    "appendix_organization": "type",
                },
            },
        },
        "validation": {
            "strictness": "lenient",  # More forgiving for quick printing
        },
    }


def get_adventure_creation_workflow_config(
    *,
    source_limit: list[str] | None = None,
    include_all_appendices: bool = True,
    optimize_for_screen: bool = False,
) -> dict[str, Any]:
    """
    Configuration optimized for adventure creation.

    Provides settings ideal for creating comprehensive adventure documents with:
    - Source limitations for consistency
    - Content type selections for complete adventures
    - Document structure optimization for readability

    Args:
        source_limit: List of allowed sources for consistency (None = all core)
        include_all_appendices: Whether to include all appendix types
        optimize_for_screen: Whether to optimize for screen reading vs print

    Returns:
        Partial ApplicationConfig dict for adventure creation workflows

    Example:
        >>> config_overrides = get_adventure_creation_workflow_config(
        ...     source_limit=["phb", "mm", "dmg"],
        ...     include_all_appendices=True
        ... )
    """
    if source_limit is None:
        source_limit = ["xphb", "xmm", "xdmg", "xge", "tce"]

    background = "full" if optimize_for_screen else "print"

    return {
        "rendering": {
            "content": {
                "appendix_spells": include_all_appendices,
                "appendix_items": include_all_appendices,
                "appendix_creatures": include_all_appendices,
                "default_sources": source_limit,
                "include_images": True,
            },
            "latex": {
                "document": {
                    "document_class": "dndbook",
                    "class_options": ["justified", "twocolumn"],
                    "paper_size": "letter",
                    "background": background,
                    "high_contrast": False,
                    "two_column": True,
                    "show_toc": True,
                    "show_index": True,
                    "fancy_headers": True,
                },
                "rendering": {
                    "enable_hyperlinks": True,
                    "enable_cross_refs": True,
                    "auto_page_refs": True,
                    "appendix_organization": "source",
                },
            },
        },
        "validation": {
            "strictness": "strict",  # Higher standards for published adventures
            "enable_summary": True,
        },
        "processing": {
            "enable_caching": True,  # Important for large adventures
            "cache_ttl": 7200,  # Longer cache for stable content
        },
    }


def get_character_sheet_workflow_config(
    *,
    player_optimized: bool = True,
    include_references: bool = True,
    compact_layout: bool = False,
) -> dict[str, Any]:
    """
    Configuration optimized for character sheet generation.

    Provides settings ideal for creating player reference materials with:
    - Player-optimized layouts and content selection
    - Reference information inclusion for gameplay
    - Form-fillable friendly formatting options

    Args:
        player_optimized: Whether to optimize content selection for players
        include_references: Whether to include rule references and tables
        compact_layout: Whether to use compact layout for more content per page

    Returns:
        Partial ApplicationConfig dict for character sheet workflows

    Example:
        >>> config_overrides = get_character_sheet_workflow_config(
        ...     player_optimized=True,
        ...     include_references=True
        ... )
    """
    # Player-focused sources (exclude DM-only content)
    sources = (
        ["xphb", "xge", "tce", "scag"] if player_optimized else ["xphb", "xmm", "xdmg"]
    )

    class_options = ["justified"]
    if compact_layout:
        class_options.append("twocolumn")

    return {
        "rendering": {
            "content": {
                "appendix_spells": include_references,
                "appendix_items": include_references,
                "appendix_creatures": False,  # Usually not needed for character sheets
                "default_sources": sources,
                "include_images": not compact_layout,
            },
            "latex": {
                "document": {
                    "document_class": "dndarticle",
                    "class_options": class_options,
                    "paper_size": "letter",
                    "background": "print",  # Good for form-fillable
                    "high_contrast": False,
                    "two_column": compact_layout,
                    "show_toc": include_references,
                    "show_index": include_references,
                    "fancy_headers": not compact_layout,
                },
                "rendering": {
                    "enable_hyperlinks": True,
                    "enable_cross_refs": include_references,
                    "auto_page_refs": include_references,
                    "appendix_organization": "alphabetical",
                },
            },
        },
        "validation": {
            "strictness": "normal",
            "enable_summary": False,  # Less verbose for player use
        },
    }


def get_dm_reference_workflow_config(
    *,
    screen_optimized: bool = True,
    quick_reference: bool = True,
    include_tables: bool = True,
) -> dict[str, Any]:
    """
    Configuration optimized for DM reference materials.

    Provides settings ideal for creating DM screen and quick reference with:
    - Quick-reference formatting and content selection
    - Table and rule optimization for easy lookup
    - Screen-friendly layouts and hyperlink navigation

    Args:
        screen_optimized: Whether to optimize for screen reading vs print
        quick_reference: Whether to prioritize quick lookup over completeness
        include_tables: Whether to include rules tables and references

    Returns:
        Partial ApplicationConfig dict for DM reference workflows

    Example:
        >>> config_overrides = get_dm_reference_workflow_config(
        ...     screen_optimized=True,
        ...     quick_reference=True
        ... )
    """
    # DM-focused sources with full rule coverage
    sources = ["xphb", "xmm", "xdmg", "xge", "tce"]

    background = "full" if screen_optimized else "none"
    layout = [] if quick_reference else ["justified", "twocolumn"]

    return {
        "rendering": {
            "content": {
                "appendix_spells": include_tables,
                "appendix_items": include_tables,
                "appendix_creatures": include_tables,
                "default_sources": sources,
                "include_images": not quick_reference,
            },
            "latex": {
                "document": {
                    "document_class": "dndarticle",
                    "class_options": layout,
                    "paper_size": "letter",
                    "background": background,
                    "high_contrast": False,
                    "two_column": not quick_reference,
                    "show_toc": True,
                    "show_index": True,
                    "fancy_headers": not quick_reference,
                },
                "rendering": {
                    "enable_hyperlinks": True,
                    "enable_cross_refs": True,
                    "auto_page_refs": True,
                    "appendix_organization": "type",
                },
            },
        },
        "validation": {
            "strictness": "normal",
            "enable_summary": True,
        },
        "processing": {
            "enable_caching": True,
            "cache_ttl": 3600,  # Standard caching for reference materials
        },
    }


def get_homebrew_workflow_config(
    *,
    include_official: bool = True,
    strict_validation: bool = False,
    optimize_for_sharing: bool = True,
) -> dict[str, Any]:
    """
    Configuration optimized for homebrew content creation.

    Provides settings ideal for creating and sharing homebrew content with:
    - Flexible source mixing (homebrew + official)
    - Configurable validation for homebrew flexibility
    - Sharing-optimized formatting and presentation

    Args:
        include_official: Whether to include official sources alongside homebrew
        strict_validation: Whether to use strict validation (may break homebrew)
        optimize_for_sharing: Whether to optimize for digital sharing vs print

    Returns:
        Partial ApplicationConfig dict for homebrew workflows

    Example:
        >>> config_overrides = get_homebrew_workflow_config(
        ...     include_official=True,
        ...     strict_validation=False
        ... )
    """
    sources = ["homebrew", "brew"]
    if include_official:
        sources.extend(["xphb", "xmm", "xdmg"])

    background = "full" if optimize_for_sharing else "print"
    strictness = "strict" if strict_validation else "lenient"

    return {
        "rendering": {
            "content": {
                "appendix_spells": True,
                "appendix_items": True,
                "appendix_creatures": True,
                "default_sources": sources,
                "include_images": True,
            },
            "latex": {
                "document": {
                    "document_class": "dndbook",
                    "class_options": ["justified", "twocolumn"],
                    "paper_size": "letter",
                    "background": background,
                    "high_contrast": False,
                    "two_column": True,
                    "show_toc": True,
                    "show_index": True,
                    "fancy_headers": True,
                },
                "rendering": {
                    "enable_hyperlinks": optimize_for_sharing,
                    "enable_cross_refs": True,
                    "auto_page_refs": True,
                    "appendix_organization": "alphabetical",
                },
            },
        },
        "validation": {
            "strictness": strictness,
            "enable_summary": True,
            "max_duplicate_errors": 3,  # More tolerance for homebrew iterations
        },
        "processing": {
            "enable_caching": False,  # Disable caching for active homebrew development
        },
    }


# Convenience function to list all available workflows
def get_available_workflows() -> dict[str, str]:
    """
    Get a mapping of available workflow functions to their descriptions.

    Returns:
        Dictionary mapping workflow function names to descriptions

    Example:
        >>> workflows = get_available_workflows()
        >>> for name, desc in workflows.items():
        ...     print(f"{name}: {desc}")
    """
    return {
        "get_spellbook_workflow_config": "Spellbook generation with cleric focus and homebrew support",
        "get_encounter_printing_workflow_config": "Encounter materials optimized for physical printing",
        "get_adventure_creation_workflow_config": "Comprehensive adventure documents with full appendices",
        "get_character_sheet_workflow_config": "Player reference materials and character sheets",
        "get_dm_reference_workflow_config": "DM screen and quick reference materials",
        "get_homebrew_workflow_config": "Homebrew content creation with flexible validation",
    }
