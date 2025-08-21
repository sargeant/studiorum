"""MCP configuration tools for D&D 5e project.

This module provides natural language configuration capabilities through MCP tools,
enabling users to interact with the application configuration using intuitive commands
like "Set sources to SRD only" or "Configure for A4 printing".

Key Features:
- Natural language configuration commands
- Workflow-specific helpers with smart defaults
- Named preset management (save/load configurations)
- Integration with existing ApplicationConfig and MCPConfig
- Request-scoped configuration with AsyncRequestContext
- Comprehensive validation and error handling
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from studiorum.core.logging import get_logger

from ...core.config.unified_config import (
    ApplicationConfig,
    CompilationConfig,
    ContentConfig,
    LaTeXDocumentConfig,
    LaTeXEngineConfig,
    LaTeXRenderingConfig,
    LoggingConfig,
    MCPConfig,
    PathsConfig,
    ProcessingConfig,
    RenderingConfig,
    ValidationConfig,
    get_app_config,
    set_app_config,
)
from ...core.context import AsyncRequestContext
from ...core.error_types import (
    ConfigurationError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
    ValidationError as DnDValidationError,
)
from ...core.result import Error, Result, Success

logger = get_logger(__name__)


# Response models for structured MCP tool returns
class ConfigurationResponse(BaseModel):
    """Standard response format for configuration operations."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Human-readable result message")
    updated_fields: list[str] = Field(
        default_factory=list,
        description="List of configuration fields that were modified",
    )
    errors: list[str] = Field(
        default_factory=list, description="List of validation or processing errors"
    )
    current_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Current configuration state (relevant sections only)",
    )


class PresetInfo(BaseModel):
    """Information about a configuration preset."""

    name: str = Field(description="Preset name")
    description: str = Field(description="Human-readable description")
    created_at: str = Field(description="Creation timestamp")
    config_sections: list[str] = Field(
        description="List of configuration sections included in preset"
    )


# Preset storage location
_PRESETS_DIR = Path.home() / ".config" / "dnd5e" / "presets"


def _ensure_presets_dir() -> Path:
    """Ensure the presets directory exists and return its path."""
    _PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return _PRESETS_DIR


def _get_current_config_dict(config: ApplicationConfig) -> dict[str, Any]:
    """Get a serializable representation of the current configuration."""
    return {
        "logging": config.logging.model_dump(),
        "paths": {
            "data_path": str(config.paths.data_path)
            if config.paths.data_path
            else None,
            "assets_path": str(config.paths.assets_path),
            "output_path": str(config.paths.output_path),
            "build_path": str(config.paths.build_path),
            "font_dir": str(config.paths.font_dir) if config.paths.font_dir else None,
        },
        "processing": config.processing.model_dump(),
        "validation": config.validation.model_dump(),
        "rendering": {
            "template_dir": str(config.rendering.template_dir)
            if config.rendering.template_dir
            else None,
            "output_format": config.rendering.output_format,
            "debug": config.rendering.debug,
            "strict_mode": config.rendering.strict_mode,
            "content": config.rendering.content.model_dump(),
            "compilation": config.rendering.compilation.model_dump(),
            "latex": {
                "engine": config.rendering.latex.engine.model_dump(),
                "document": config.rendering.latex.document.model_dump(),
                "rendering": config.rendering.latex.rendering.model_dump(),
            },
        },
        "mcp": config.mcp.model_dump(),
    }


async def get_configuration(
    context: AsyncRequestContext | None = None,
) -> Result[ConfigurationResponse, MCPError]:
    """Read current application configuration settings.

    This tool provides access to the current configuration state, allowing users
    to understand what settings are currently active. Useful for checking current
    paper size, enabled sources, LaTeX engine settings, etc.

    Natural language examples:
    - "What are my current settings?"
    - "Show me the LaTeX configuration"
    - "What paper size am I using?"

    Args:
        context: Optional async request context for request isolation

    Returns:
        Result containing current configuration or error
    """
    try:
        # Get current configuration (context config takes precedence)
        if context and context.user_config:
            config = context.user_config
        else:
            config = get_app_config()

        current_dict = _get_current_config_dict(config)

        response = ConfigurationResponse(
            success=True,
            message="Current configuration retrieved successfully",
            current_config=current_dict,
        )

        return Success(response)

    except Exception as e:
        logger.exception("Failed to get configuration")
        error = MCPError(
            message=f"Failed to read configuration: {str(e)}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(error)


async def update_configuration(
    updates: dict[str, Any], context: AsyncRequestContext | None = None
) -> Result[ConfigurationResponse, MCPError]:
    """Modify application configuration settings with validation.

    This tool allows updating any configuration setting with full validation.
    Supports nested configuration updates using dot notation or nested dictionaries.

    Natural language examples:
    - "Set log level to DEBUG"
    - "Change paper size to A4"
    - "Enable PDF compilation"
    - "Set LaTeX engine to XeLaTeX"

    Args:
        updates: Dictionary of configuration updates to apply
        context: Optional async request context for request isolation

    Returns:
        Result containing updated configuration or validation errors
    """
    try:
        # Get current configuration
        if context and context.user_config:
            config = context.user_config
        else:
            config = get_app_config()

        # Create a copy for updates
        config_dict = config.model_dump()
        updated_fields = []
        errors = []

        # Apply updates
        for key, value in updates.items():
            try:
                # Handle nested keys with dot notation
                if "." in key:
                    keys = key.split(".")
                    current = config_dict
                    for nested_key in keys[:-1]:
                        if nested_key not in current:
                            current[nested_key] = {}
                        current = current[nested_key]
                    current[keys[-1]] = value
                else:
                    config_dict[key] = value

                updated_fields.append(key)

            except Exception as e:
                errors.append(f"Failed to update {key}: {str(e)}")

        # Validate the updated configuration
        try:
            updated_config = ApplicationConfig(**config_dict)
        except ValidationError as ve:
            validation_errors = []
            for err_detail in ve.errors():
                field_path = ".".join(str(loc) for loc in err_detail["loc"])
                validation_errors.append(f"{field_path}: {err_detail['msg']}")

            response = ConfigurationResponse(
                success=False,
                message="Configuration validation failed",
                errors=validation_errors,
                current_config=_get_current_config_dict(config),
            )
            return Success(response)

        # Apply the validated configuration
        if context:
            context.user_config = updated_config
        else:
            set_app_config(updated_config)

        response = ConfigurationResponse(
            success=True,
            message=f"Successfully updated {len(updated_fields)} configuration settings",
            updated_fields=updated_fields,
            errors=errors,
            current_config=_get_current_config_dict(updated_config),
        )

        return Success(response)

    except Exception as e:
        logger.exception("Failed to update configuration")
        mcp_error = MCPError(
            message=f"Failed to update configuration: {str(e)}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(mcp_error)


async def configure_paper_layout(
    paper_size: Literal["letter", "a4", "a5"] = "a4",
    background: Literal["full", "none", "print"] = "print",
    high_contrast: bool = True,
    two_column: bool = True,
    context: AsyncRequestContext | None = None,
) -> Result[ConfigurationResponse, MCPError]:
    """Configure paper size, background, and formatting for printing.

    This tool provides smart defaults for different paper layouts and printing scenarios.
    Optimizes settings for print quality, readability, and paper efficiency.

    Natural language examples:
    - "Configure for A4 printing"
    - "Set up for US letter with full background"
    - "Optimize for black and white printing"
    - "Configure for print-friendly layout"

    Args:
        paper_size: Paper size to use (letter, a4, a5)
        background: Background style (full, none, print)
        high_contrast: Whether to use high contrast mode for printing
        two_column: Whether to use two-column layout
        context: Optional async request context for request isolation

    Returns:
        Result containing updated paper configuration
    """
    try:
        # Build updates dictionary with Any values to allow mixed types
        updates: dict[str, Any] = {
            "rendering.latex.document.paper_size": paper_size,
            "rendering.latex.document.background": background,
            "rendering.latex.document.high_contrast": high_contrast,
            "rendering.latex.document.two_column": two_column,
        }

        # Add paper-specific optimizations
        if paper_size == "a5":
            # Smaller paper needs single column and smaller font
            updates["rendering.latex.document.two_column"] = False
            updates["rendering.latex.document.font_size"] = "10pt"
            updates["rendering.latex.document.class_options"] = ["justified"]
        elif paper_size == "letter":
            # Letter size optimizations
            updates["rendering.latex.document.font_size"] = "11pt"
        elif paper_size == "a4":
            # A4 optimizations
            updates["rendering.latex.document.font_size"] = "11pt"

        # Print-friendly adjustments
        if background == "print":
            updates["rendering.latex.document.high_contrast"] = True
            updates["rendering.latex.document.fancy_headers"] = False

        result = await update_configuration(updates, context)

        if result.is_success():
            response = result.unwrap()
            response.message = f"Paper layout configured for {paper_size.upper()} with {background} background"

        return result

    except Exception as e:
        logger.exception("Failed to configure paper layout")
        error = MCPError(
            message=f"Failed to configure paper layout: {str(e)}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(error)


async def configure_spellbook_generation(
    include_spell_appendix: bool = True,
    alphabetical_organization: bool = True,
    enable_cross_refs: bool = True,
    show_index: bool = True,
    context: AsyncRequestContext | None = None,
) -> Result[ConfigurationResponse, MCPError]:
    """Configure smart defaults for spellbook generation workflows.

    This tool optimizes settings specifically for creating spell compendiums and
    spellbooks with proper organization, cross-referencing, and appendices.

    Natural language examples:
    - "Set up for spellbook generation"
    - "Configure spell appendix with cross-references"
    - "Optimize for spell compendium creation"
    - "Enable alphabetical spell organization"

    Args:
        include_spell_appendix: Whether to generate spell appendices
        alphabetical_organization: Whether to organize spells alphabetically
        enable_cross_refs: Whether to enable spell cross-references
        show_index: Whether to include alphabetical index
        context: Optional async request context for request isolation

    Returns:
        Result containing updated spellbook configuration
    """
    try:
        updates: dict[str, Any] = {
            "rendering.content.appendix_spells": include_spell_appendix,
            "rendering.latex.rendering.enable_cross_refs": enable_cross_refs,
            "rendering.latex.rendering.auto_page_refs": enable_cross_refs,
            "rendering.latex.document.show_index": show_index,
            "rendering.latex.document.show_toc": True,  # Always useful for spellbooks
        }

        if alphabetical_organization:
            updates["rendering.latex.rendering.appendix_organization"] = "alphabetical"
        else:
            updates["rendering.latex.rendering.appendix_organization"] = "type"

        result = await update_configuration(updates, context)

        if result.is_success():
            response = result.unwrap()
            response.message = "Spellbook generation configured with optimized settings"

        return result

    except Exception as e:
        logger.exception("Failed to configure spellbook generation")
        error = MCPError(
            message=f"Failed to configure spellbook generation: {str(e)}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(error)


async def configure_encounter_printing(
    optimize_for_print: bool = True,
    include_creature_appendix: bool = True,
    high_contrast: bool = True,
    single_column: bool = False,
    context: AsyncRequestContext | None = None,
) -> Result[ConfigurationResponse, MCPError]:
    """Configure optimized settings for encounter statblock printing.

    This tool provides print-friendly defaults for encounter sheets and creature
    statblocks, focusing on readability and efficient paper usage.

    Natural language examples:
    - "Set up for encounter printing"
    - "Configure creature statblocks for print"
    - "Optimize for black and white encounter sheets"
    - "Set up print-friendly monster manual"

    Args:
        optimize_for_print: Whether to optimize for print quality
        include_creature_appendix: Whether to generate creature appendices
        high_contrast: Whether to use high contrast mode
        single_column: Whether to force single-column layout
        context: Optional async request context for request isolation

    Returns:
        Result containing updated encounter printing configuration
    """
    try:
        updates: dict[str, Any] = {
            "rendering.content.appendix_creatures": include_creature_appendix,
            "rendering.latex.document.high_contrast": high_contrast,
        }

        if optimize_for_print:
            updates["rendering.latex.document.background"] = "print"
            updates["rendering.latex.document.fancy_headers"] = False
            updates["rendering.latex.rendering.enable_hyperlinks"] = (
                False  # Not needed for print
            )

        if single_column:
            updates["rendering.latex.document.two_column"] = False
            updates["rendering.latex.document.class_options"] = ["justified"]
        else:
            updates["rendering.latex.document.two_column"] = True
            updates["rendering.latex.document.class_options"] = [
                "justified",
                "twocolumn",
            ]

        result = await update_configuration(updates, context)

        if result.is_success():
            response = result.unwrap()
            response.message = "Encounter printing configured with optimized settings"

        return result

    except Exception as e:
        logger.exception("Failed to configure encounter printing")
        error = MCPError(
            message=f"Failed to configure encounter printing: {str(e)}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(error)


async def add_content_source(
    sources: list[str],
    replace_existing: bool = False,
    context: AsyncRequestContext | None = None,
) -> Result[ConfigurationResponse, MCPError]:
    """Add or manage D&D content sources for data resolution.

    This tool manages the list of content sources used for resolving D&D content
    references. Sources should use standard 5etools abbreviations.

    Natural language examples:
    - "Add Tasha's Cauldron to sources"
    - "Set sources to SRD only"
    - "Add DMG and PHB to content sources"
    - "Replace sources with core books only"

    Args:
        sources: List of source abbreviations to add (e.g., ["phb", "dmg", "mm"])
        replace_existing: Whether to replace existing sources or add to them
        context: Optional async request context for request isolation

    Returns:
        Result containing updated source configuration
    """
    try:
        # Get current configuration
        if context and context.user_config:
            config = context.user_config
        else:
            config = get_app_config()

        current_sources = config.rendering.content.default_sources.copy()

        if replace_existing:
            new_sources = sources
        else:
            # Add new sources, avoiding duplicates
            new_sources = current_sources.copy()
            for source in sources:
                if source not in new_sources:
                    new_sources.append(source)

        updates: dict[str, Any] = {"rendering.content.default_sources": new_sources}

        # Also update context sources if provided
        if context:
            context.sources = new_sources

        result = await update_configuration(updates, context)

        if result.is_success():
            response = result.unwrap()
            action = "replaced" if replace_existing else "updated"
            response.message = f"Content sources {action}: {', '.join(new_sources)}"

        return result

    except Exception as e:
        logger.exception("Failed to add content source")
        error = MCPError(
            message=f"Failed to add content source: {str(e)}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.CONFIGURATION,
        )
        return Error(error)


async def save_user_preferences(
    preset_name: str, description: str = "", context: AsyncRequestContext | None = None
) -> Result[ConfigurationResponse, MCPError]:
    """Save current configuration as a named preset for later use.

    This tool allows users to save their current configuration settings as a named
    preset that can be loaded later. Useful for different workflows or output formats.

    Natural language examples:
    - "Save current settings as 'Print Setup'"
    - "Save this configuration as 'Spellbook Layout'"
    - "Create preset called 'DM Screen' with current settings"

    Args:
        preset_name: Name for the preset (alphanumeric and spaces allowed)
        description: Optional description of what this preset is for
        context: Optional async request context for request isolation

    Returns:
        Result containing save operation status
    """
    try:
        # Validate preset name
        if not preset_name.strip():
            error = MCPError(
                message="Preset name cannot be empty",
                error_code=MCPErrorCode.INVALID_PARAMS,
                category=ErrorCategory.USER_ERROR,
            )
            return Error(error)

        # Get current configuration
        if context and context.user_config:
            config = context.user_config
        else:
            config = get_app_config()

        # Prepare preset data
        preset_data = {
            "name": preset_name.strip(),
            "description": description.strip(),
            "created_at": "",  # Will be set by timestamp
            "config": _get_current_config_dict(config),
        }

        # Ensure presets directory exists
        presets_dir = _ensure_presets_dir()

        # Create safe filename
        safe_name = "".join(
            c for c in preset_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        preset_file = presets_dir / f"{safe_name}.json"

        # Add timestamp
        from datetime import datetime

        preset_data["created_at"] = datetime.now().isoformat()

        # Save preset
        with preset_file.open("w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2)

        response = ConfigurationResponse(
            success=True,
            message=f"Configuration preset '{preset_name}' saved successfully",
            current_config={"preset_file": str(preset_file)},
        )

        return Success(response)

    except Exception as e:
        logger.exception("Failed to save user preferences")
        error = MCPError(
            message=f"Failed to save preset: {str(e)}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.IO,
        )
        return Error(error)


async def load_user_preferences(
    preset_name: str, context: AsyncRequestContext | None = None
) -> Result[ConfigurationResponse, MCPError]:
    """Load a previously saved configuration preset.

    This tool loads a named configuration preset, applying all the saved settings
    to the current configuration. Useful for switching between different workflows.

    Natural language examples:
    - "Load my 'Print Setup' preferences"
    - "Apply the 'Spellbook Layout' configuration"
    - "Switch to 'DM Screen' settings"

    Args:
        preset_name: Name of the preset to load
        context: Optional async request context for request isolation

    Returns:
        Result containing loaded configuration or error if preset not found
    """
    try:
        # Ensure presets directory exists
        presets_dir = _ensure_presets_dir()

        # Create safe filename
        safe_name = "".join(
            c for c in preset_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        preset_file = presets_dir / f"{safe_name}.json"

        if not preset_file.exists():
            # Try to find similar preset names
            available_presets = []
            for file in presets_dir.glob("*.json"):
                try:
                    with file.open("r", encoding="utf-8") as f:
                        preset_data = json.load(f)
                        available_presets.append(preset_data.get("name", file.stem))
                except (OSError, json.JSONDecodeError, KeyError) as e:
                    # Log the specific error but continue processing other presets
                    logger.debug(
                        f"Skipping invalid preset file {file}: {e}",
                        extra={"preset_file": str(file), "error": str(e)},
                    )
                    continue

            error_msg = f"Preset '{preset_name}' not found"
            if available_presets:
                error_msg += f". Available presets: {', '.join(available_presets)}"

            error = MCPError(
                message=error_msg,
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            return Error(error)

        # Load preset data
        with preset_file.open("r", encoding="utf-8") as f:
            preset_data = json.load(f)

        config_data = preset_data.get("config", {})

        # Validate and apply configuration
        try:
            loaded_config = ApplicationConfig(**config_data)
        except ValidationError as ve:
            validation_errors = []
            for err_detail in ve.errors():
                field_path = ".".join(str(loc) for loc in err_detail["loc"])
                validation_errors.append(f"{field_path}: {err_detail['msg']}")

            response = ConfigurationResponse(
                success=False,
                message="Preset configuration is invalid",
                errors=validation_errors,
            )
            return Success(response)

        # Apply the loaded configuration
        if context:
            context.user_config = loaded_config
        else:
            set_app_config(loaded_config)

        response = ConfigurationResponse(
            success=True,
            message=f"Configuration preset '{preset_name}' loaded successfully",
            current_config=_get_current_config_dict(loaded_config),
        )

        return Success(response)

    except Exception as e:
        logger.exception("Failed to load user preferences")
        error = MCPError(
            message=f"Failed to load preset: {str(e)}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.IO,
        )
        return Error(error)
