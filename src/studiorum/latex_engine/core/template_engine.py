"""Jinja2-based LaTeX template engine for 5e-style documents."""

import re
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

import jinja2
from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    Undefined,
    pass_context,
)
from jinja2.runtime import Context

from studiorum.core.config.unified_config import (
    LaTeXConfig,
    LaTeXDocumentConfig,
    get_app_config,
)
from studiorum.core.logging import get_logger
from studiorum.core.models.creatures import Ability, Spellcasting
from studiorum.core.types import LaTeXConfig as LaTeXConfigDict
from studiorum.renderers.escape import escape

from ..services.template_service import active_template_service
from . import model_text
from .dnd_template import DNDTemplateManager, check_dnd_template_status


def _active_tag_resolver() -> Any:
    """The active template service's tag resolver, or None if there is none."""
    try:
        service = active_template_service()
    except Exception:
        return None
    return service.tag_resolver if service is not None else None


def _active_omnidexer_and_tag_resolver() -> tuple[Any, Any]:
    """The active template service's omnidexer and tag resolver, or (None, None)."""
    try:
        service = active_template_service()
    except Exception:
        return None, None
    if service is None:
        return None, None
    return service.omnidexer, service.tag_resolver


def _class_for_content_type(
    doc: LaTeXDocumentConfig, content_type: str
) -> tuple[str, list[str]]:
    """The document class and options for a kind of document.

    Adventures, sourcebooks, supplements and references always use dndbook, and
    supplements and references drop the fancy option. Articles use dndarticle in
    one column.
    """
    document_class: str = doc.document_class
    options = doc.class_options()
    if content_type in ("adventure", "sourcebook"):
        document_class = "dndbook"
    elif content_type in ("supplement", "reference"):
        document_class = "dndbook"
        options = [opt for opt in options if opt != "fancy"]
    elif content_type == "article":
        document_class = "dndarticle"
        options = ["onecolumn" if opt == "twocolumn" else opt for opt in options]
    return document_class, options


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _latex_escape(value: Any) -> str:
    """Escape a value as LaTeX text."""
    return escape(value if isinstance(value, str) else str(value))


def _processed_ac_text(creature: Any) -> str:
    """Creature AC with tags in armour sources resolved."""
    return model_text.creature_ac_text(creature, _active_tag_resolver())


def _processed_senses(creature: Any) -> str | None:
    """Creature senses with tags resolved."""
    return model_text.creature_senses_text(creature, _active_tag_resolver())


def _safe_processed_name(obj: Any) -> str:
    """Safely get processed name from object or dict."""
    if isinstance(obj, (Ability, Spellcasting)):
        omnidexer, tag_resolver = _active_omnidexer_and_tag_resolver()
        return model_text.ability_name_text(obj, omnidexer, tag_resolver)
    if hasattr(obj, "get_processed_name"):
        try:
            return obj.get_processed_name()
        except (AttributeError, TypeError, ValueError):
            # Method exists but failed - continue to fallback
            pass

    # Fallback to name attribute for dicts or objects
    if isinstance(obj, dict):
        return obj.get("name", "Unknown")
    if hasattr(obj, "name"):
        return obj.name
    return str(obj)


@pass_context
def _entries(context: Context, value: Any) -> str:
    """LaTeX for entries, rendered with the template's rendering_context."""
    from studiorum.latex_engine.entries import EntryRenderer

    if isinstance(value, Undefined):
        return ""
    rendering_context = context.get("rendering_context")
    if rendering_context is None:
        return EntryRenderer().render(value)
    return EntryRenderer.from_context(rendering_context).render(value)


@cache
def environment() -> Environment:
    """The Jinja environment for every template, with LaTeX-friendly delimiters.

    Autoescape is off: templates escape plain text with the latex_escape filter.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # nosec B701
        block_start_string="<@",
        block_end_string="@>",
        variable_start_string="<#",
        variable_end_string="#>",
        comment_start_string="<#--",
        comment_end_string="--#>",
    )
    filters: dict[str, Callable[..., Any]] = {
        "latex_escape": _latex_escape,
        "safe_processed_name": _safe_processed_name,
        "processed_ac_text": _processed_ac_text,
        "processed_senses": _processed_senses,
        "entries": _entries,
    }
    env.filters.update(filters)
    return env


class LaTeXTemplateEngine:
    """Jinja2-based template engine for LaTeX document generation.

    Provides template loading, caching, and rendering with LaTeX-specific
    escaping and filters. Supports template inheritance and uses DND-5e-LaTeX-Template
    document classes.

    Security Note:
        HTML autoescape is disabled as it's inappropriate for LaTeX output.
        LaTeX has different special characters than HTML ({, }, $, &, %, #, ^, _, ~, \\)
        and requires custom escaping logic.

        IMPORTANT: All user-provided content must be escaped using the latex_escape
        filter to prevent LaTeX injection attacks. Template developers should:
        - Use {{ variable | latex_escape }} for all user input
        - Mark trusted content as safe: {{ trusted_content | safe }}
        - Validate input before template rendering
        - Never allow user control of template structure
    """

    def __init__(self, config: LaTeXConfigDict | None = None):
        """Initialize template engine.

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.templates_dir = TEMPLATES_DIR
        self.debug = self.config.get("debug", False)

        # Start from the loaded configuration; convert commands pass their own
        self.latex_config = get_app_config().rendering.latex

        # Initialize the environment
        self.update_latex_config(None)

        # Logger
        self._logger = get_logger(__name__)

    def update_latex_config(self, latex_config: LaTeXConfig | None) -> None:
        """Update the LaTeX configuration.

        Args:
            latex_config: New LaTeX configuration to use
        """
        if latex_config is not None:
            self.latex_config = latex_config

        # Initialize DND template manager
        self.dnd_manager = DNDTemplateManager()

        self.env = environment()

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of template to render (with or without .tex.j2 extension)
            context: Variables to pass to template

        Returns:
            Rendered template content

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateSyntaxError: If template has syntax errors
        """
        try:
            # Ensure template name has correct extension
            if not template_name.endswith(".tex.j2"):
                template_name += ".tex.j2"

            # Get template from cache or load from file
            template = self._get_template(template_name)

            # Render template with a context that includes required defaults
            merged_context = self.create_template_context(**context)
            rendered = template.render(merged_context)

            # Post-process rendered output if needed
            return self._post_process_output(rendered)

        except jinja2.TemplateNotFound as e:
            raise FileNotFoundError(
                f"Template '{template_name}' not found in {self.templates_dir}"
            ) from e
        except jinja2.TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error in '{template_name}': {e}") from e
        except Exception as e:
            raise RuntimeError(
                f"Error rendering template '{template_name}': {e}"
            ) from e

    def _get_template(self, template_name: str) -> Template:
        """Get template object by name.

        Args:
            template_name: Name of template file

        Returns:
            Jinja2 Template object
        """
        return self.env.get_template(template_name)

    def _post_process_output(self, content: str) -> str:
        """Post-process rendered template output.

        Args:
            content: Rendered template content

        Returns:
            Post-processed content
        """
        # Remove excessive blank lines
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        # Ensure proper spacing around LaTeX environments
        content = re.sub(r"\\begin\{([^}]+)\}", r"\n\\begin{\1}", content)
        content = re.sub(r"\\end\{([^}]+)\}", r"\\end{\1}\n", content)

        # Clean up any remaining triple newlines
        content = re.sub(r"\n\n\n+", "\n\n", content)

        return content.strip()

    def validate_template(self, template_name: str) -> bool:
        """Validate template syntax without rendering.

        Args:
            template_name: Name of template to validate

        Returns:
            True if template is valid, False otherwise
        """
        try:
            if not template_name.endswith(".tex.j2"):
                template_name += ".tex.j2"
            self._get_template(template_name)
            return True
        except Exception:
            return False

    def list_templates(self) -> list[str]:
        """List all available templates.

        Returns:
            List of template names (without .tex.j2 extension)
        """
        templates = []
        for template_file in self.templates_dir.glob("*.tex.j2"):
            # Remove .tex.j2 extension to get template name
            template_name = template_file.name.replace(".tex.j2", "")
            templates.append(template_name)
        return sorted(templates)

    def get_template_path(self, template_name: str) -> Path:
        """Get full path to template file.

        Args:
            template_name: Name of template

        Returns:
            Path to template file
        """
        if not template_name.endswith(".tex.j2"):
            template_name += ".tex.j2"
        return self.templates_dir / template_name

    def template_exists(self, template_name: str) -> bool:
        """Check if template exists.

        Args:
            template_name: Name of template to check

        Returns:
            True if template exists, False otherwise
        """
        return self.get_template_path(template_name).exists()

    def create_template_context(self, **kwargs: Any) -> dict[str, Any]:
        """Create template context with common variables.

        Args:
            **kwargs: Additional context variables

        Returns:
            Template context dictionary
        """
        context: dict[str, Any] = {
            "config": self.config,
            "debug": self.debug,
        }

        # Add template services if not already provided
        if "template_service" not in kwargs:
            context["template_service"] = active_template_service()

        if "content_tracker" not in kwargs:
            from ...core.references.content_tracker import ContentTracker

            context["content_tracker"] = ContentTracker()

        # Provide a default RenderingContext when not explicitly supplied
        if "rendering_context" not in kwargs and "rendering_context" not in context:
            try:
                from studiorum.renderers.context import RenderingContext as RC

                tmpl_service = context.get("template_service")
                context["rendering_context"] = RC(
                    output_format="latex",
                    omnidexer=getattr(tmpl_service, "omnidexer", None),
                    content_tracker=context.get("content_tracker"),
                    tag_resolver=getattr(tmpl_service, "tag_resolver", None),
                    debug_mode=bool(self.debug),
                    metadata=dict(kwargs.get("metadata", {}) or {}),
                )
            except Exception:
                # Non-fatal: log and continue; missing context will surface at render
                self._logger.debug(
                    "Failed to initialize rendering_context default in template context",
                    exc_info=True,
                )

        context.update(kwargs)
        return context

    def check_dnd_template_availability(self) -> bool:
        """Check if DND-5e-LaTeX-Template is available.

        Returns:
            True if template is available and ready to use
        """
        return check_dnd_template_status()

    def get_dnd_template_status(self) -> dict[str, Any]:
        """Get detailed DND template status information.

        Returns:
            Dictionary with template status details
        """
        template_available, missing_files = (
            self.dnd_manager.check_template_availability()
        )
        latex_available, latex_version = self.dnd_manager.check_latex_installation()
        packages_available, missing_packages = (
            self.dnd_manager.check_required_packages()
        )

        return {
            "template_available": template_available,
            "missing_template_files": missing_files,
            "latex_available": latex_available,
            "latex_version": latex_version,
            "packages_available": packages_available,
            "missing_packages": missing_packages,
            "system_info": self.dnd_manager.get_system_info(),
        }

    def create_dnd_template_context(
        self, content_type: str = "book", **kwargs: Any
    ) -> dict[str, Any]:
        """Create template context optimized for DND template usage.

        Args:
            content_type: Type of content being rendered
            **kwargs: Additional context variables

        Returns:
            Template context with DND-specific configuration
        """
        doc_config = self.latex_config.document
        document_class, class_options = _class_for_content_type(
            doc_config, content_type
        )

        # Create base context
        context = self.create_template_context(**kwargs)

        # Add DND-specific configuration
        context.update(
            {
                "document_class": document_class,
                "class_options": class_options,
                "content_type": content_type,
                "use_dnd_template": True,
                "dnd_template_available": self.check_dnd_template_availability(),
            }
        )

        # Add LaTeX document configuration
        context.update(
            {
                "font_scheme": doc_config.font_scheme,
                "paper_size": doc_config.paper_size,
                "font_size": doc_config.font_size,
                "background": doc_config.background,
                "enable_background": doc_config.background is not None,
                "high_contrast": doc_config.high_contrast,
                "justified_text": doc_config.justified_text,
                "fancy_headers": doc_config.fancy_headers,
                "two_column": doc_config.two_column,
                "show_toc": doc_config.show_toc,
                "show_index": doc_config.show_index,
                "enable_index": doc_config.show_index,
                "numbered_sections": True,  # Enable LaTeX native chapter/section numbering
            }
        )

        return context

    def render_dnd_template(
        self, template_name: str, content_type: str = "book", **kwargs: Any
    ) -> str:
        """Render template with DND-specific configuration.

        Args:
            template_name: Name of template to render
            content_type: Type of content being rendered
            **kwargs: Additional context variables

        Returns:
            Rendered template content

        Raises:
            RuntimeError: If DND template is not available
        """
        # Check DND template availability
        if not self.check_dnd_template_availability():
            raise RuntimeError(
                "DND-5e-LaTeX-Template is not available. "
                "Please install the template before rendering."
            )

        # Create DND-optimized context
        context = self.create_dnd_template_context(content_type, **kwargs)

        # Render template
        return self.render_template(template_name, context)

    def get_installation_guide(self) -> str:
        """Get DND template installation guide.

        Returns:
            Installation guide text
        """
        return self.dnd_manager.create_installation_guide()

    def print_dnd_status_report(self) -> None:
        """Print comprehensive DND template status report."""
        self.dnd_manager.print_status_report()
