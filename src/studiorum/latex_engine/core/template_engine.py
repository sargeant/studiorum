"""Jinja2-based LaTeX template engine for 5e-style documents."""

import re
from pathlib import Path
from typing import Any

import jinja2
from jinja2 import Environment, FileSystemLoader, Template

from studiorum.core.config.latex_config import LaTeXConfig, get_default_latex_config
from studiorum.core.latex_utils import (
    contains_dangerous_latex,
    escape_latex_text,
    validate_safe_latex,
)
from studiorum.core.types import LaTeXConfig as LaTeXConfigDict, TemplateData

from .dnd_template import DNDTemplateManager, check_dnd_template_status


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
        # Get templates directory from config or use default relative to this module
        templates_dir = self.config.get("templates_dir")
        if templates_dir:
            self.templates_dir = Path(str(templates_dir))
        else:
            # Use absolute path relative to latex_engine module's location
            self.templates_dir = Path(__file__).parent.parent / "templates"
        self.debug = self.config.get("debug", False)

        # Initialize LaTeX configuration
        self.latex_config = get_default_latex_config()

        # Initialize the environment
        self.update_latex_config(None)

    def update_latex_config(self, latex_config: LaTeXConfig | None) -> None:
        """Update the LaTeX configuration.

        Args:
            latex_config: New LaTeX configuration to use
        """
        if latex_config is not None:
            self.latex_config = latex_config

        # Initialize DND template manager
        self.dnd_manager = DNDTemplateManager()

        # Create templates directory if it doesn't exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            # Disable HTML autoescape - inappropriate for LaTeX output
            # LaTeX has different special characters than HTML and requires custom escaping
            # Security: All user input must be properly escaped using latex_escape filter
            autoescape=False,  # nosec B701
            # Use different delimiters to avoid conflicts with LaTeX
            block_start_string="<@",
            block_end_string="@>",
            variable_start_string="<#",
            variable_end_string="#>",
            comment_start_string="<#--",
            comment_end_string="--#>",
        )

        # Add LaTeX-specific filters
        self._add_latex_filters()

        # Template cache

    def _add_latex_filters(self) -> None:
        """Add LaTeX-specific filters to Jinja2 environment."""

        def latex_escape(value: str) -> str:
            """Escape LaTeX special characters and Unicode characters."""
            if not isinstance(value, str):
                value = str(value)
            return escape_latex_text(value)

        def latex_newlines(value: str) -> str:
            """Convert newlines to LaTeX line breaks."""
            if not isinstance(value, str):
                value = str(value)
            return value.replace("\n", r" \\ ")

        def latex_bold(value: str) -> str:
            """Wrap text in LaTeX bold formatting."""
            if not isinstance(value, str):
                value = str(value)
            return f"\\textbf{{{value}}}"

        def latex_italic(value: str) -> str:
            """Wrap text in LaTeX italic formatting."""
            if not isinstance(value, str):
                value = str(value)
            return f"\\textit{{{value}}}"

        def latex_underline(value: str) -> str:
            """Wrap text in LaTeX underline formatting."""
            if not isinstance(value, str):
                value = str(value)
            return f"\\underline{{{value}}}"

        def latex_verbatim(value: str) -> str:
            """Wrap text in LaTeX verbatim environment."""
            if not isinstance(value, str):
                value = str(value)
            return f"\\verb|{value}|"

        def latex_safe_check(value: str) -> str:
            """Check if content is safe and return warning if not."""
            if not isinstance(value, str):
                value = str(value)

            if contains_dangerous_latex(value):
                # Log security issue but don't fail rendering
                # In production, this might trigger security alerts
                from studiorum.core.logging import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "Potentially dangerous LaTeX content detected: %s",
                    value[:100] + "..." if len(value) > 100 else value,
                )
                return f"% SECURITY WARNING: Dangerous content detected\n{escape_latex_text(value)}"

            return value

        def dnd_ability_modifier(value: int | str) -> str:
            """Format ability score as modifier (+1, -2, etc.)."""
            try:
                score = int(value)
                modifier = (score - 10) // 2
                return f"+{modifier}" if modifier >= 0 else str(modifier)
            except (ValueError, TypeError):
                return str(value)

        def dnd_challenge_rating(value: int | str | float) -> str:
            """Format challenge rating for display."""
            try:
                cr = float(value)
                if cr < 1:
                    return f"1/{int(1 / cr)}"
                elif cr == int(cr):
                    return str(int(cr))
                else:
                    return str(cr)
            except (ValueError, TypeError):
                return str(value)

        def dnd_spell_level(value: int | str) -> str:
            """Format spell level for display."""
            try:
                level = int(value)
                if level == 0:
                    return "Cantrip"
                elif level == 1:
                    return "1st-level"
                elif level == 2:
                    return "2nd-level"
                elif level == 3:
                    return "3rd-level"
                else:
                    return f"{level}th-level"
            except (ValueError, TypeError):
                return str(value)

        def markdown_to_latex(value: str) -> str:
            """Convert basic Markdown formatting to LaTeX equivalents."""
            if not isinstance(value, str):
                value = str(value)

            # Convert **bold** to \textbf{}
            value = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", value)

            # Convert *italic* to \textit{}
            value = re.sub(r"\*(.*?)\*", r"\\textit{\1}", value)

            # Convert `code` to \texttt{}
            value = re.sub(r"`(.*?)`", r"\\texttt{\1}", value)

            # Convert bullet points to itemize
            if "•" in value or value.strip().startswith("- "):
                lines = value.split("\n")
                processed_lines = []
                in_list = False

                for line in lines:
                    line = line.strip()
                    if line.startswith("•") or line.startswith("-"):
                        if not in_list:
                            processed_lines.append("\\begin{itemize}")
                            in_list = True
                        # Remove bullet and add item
                        item_text = (
                            line[1:].strip() if line.startswith(("•", "-")) else line
                        )
                        processed_lines.append(f"\\item {item_text}")
                    else:
                        if in_list:
                            processed_lines.append("\\end{itemize}")
                            in_list = False
                        if line:  # Don't add empty lines
                            processed_lines.append(line)

                if in_list:
                    processed_lines.append("\\end{itemize}")

                value = "\n".join(processed_lines)

            return value

        def clean_jinja_comments(value: str) -> str:
            """Remove Jinja2 comment syntax and clean up unwanted formatting from source data."""
            if not isinstance(value, str):
                value = str(value)

            # Remove {#itemEntry ...} patterns that appear in 5e.tools data
            value = re.sub(r"\{#itemEntry[^}]*\}", "", value)

            # Remove any other stray Jinja2 comment patterns
            value = re.sub(r"\{#[^}]*\}", "", value)

            # Clean up markdown formatting that shouldn't be in descriptions
            # Remove **Spells** headers since we handle spells with tables
            value = re.sub(r"\*\*Spells\*\*\s*", "", value)
            value = re.sub(r"\*\*Regaining Charges\*\*\s*", "", value)

            # Clean up extra whitespace left behind, preserving paragraph breaks
            value = re.sub(r"\n\s*\n\s*\n", "\n\n", value)
            # Normalize horizontal whitespace but preserve newlines
            value = re.sub(
                r"[ \t]+", " ", value
            )  # Only collapse spaces and tabs, not newlines
            value = value.strip()

            return value

        def dnd_smallcaps(value: str) -> str:
            """Convert '5e' text to LaTeX small-caps, replacing \textbf{} commands from {@b} tags."""
            if not isinstance(value, str):
                value = str(value)

            # Replace LaTeX bold commands around 5e text with small-caps
            # Note: This runs after tag processing, so {@b} tags are already converted to \textbf{}
            patterns = [
                # Handle \textbf{5e} -> \textsc{5e}
                (
                    r"\\textbf\{5e\}",
                    r"\\textsc{5e}",
                ),
                # Handle \textbf{5e} -> \textsc{5e}
                (r"\\textbf\{5e\}", r"\\textsc{5e}"),
                # Handle cases where ampersand might not be escaped yet
                (
                    r"\\textbf\{5e\}",
                    r"\\textsc{5e}",
                ),
                (r"\\textbf\{5e\}", r"\\textsc{5e}"),
                # Fallback for untagged instances (preserve existing behavior)
                (
                    r"(?<!\\textbf\{)5e(?!\})",
                    r"\\textsc{5e}",
                ),
                (r"(?<!\\textbf\{)5e(?!\})", r"\\textsc{5e}"),
                # Handle unescaped fallbacks too
                (
                    r"(?<!\\textbf\{)5e(?!\})",
                    r"\\textsc{5e}",
                ),
                (r"(?<!\\textbf\{)5e(?!\})", r"\\textsc{5e}"),
            ]

            for pattern, replacement in patterns:
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)

            return value

        def safe_processed_name(obj: Any) -> str:
            """Safely get processed name from object or dict."""
            if hasattr(obj, "get_processed_name"):
                try:
                    return obj.get_processed_name()
                except (AttributeError, TypeError, ValueError):
                    # Method exists but failed - continue to fallback
                    pass

            # Fallback to name attribute for dicts or objects
            if isinstance(obj, dict):
                return obj.get("name", "Unknown")
            elif hasattr(obj, "name"):
                return obj.name
            else:
                return str(obj)

        # Register filters
        self.env.filters["latex_escape"] = latex_escape
        self.env.filters["latex_newlines"] = latex_newlines
        self.env.filters["latex_bold"] = latex_bold
        self.env.filters["latex_italic"] = latex_italic
        self.env.filters["latex_underline"] = latex_underline
        self.env.filters["latex_verbatim"] = latex_verbatim
        self.env.filters["latex_safe_check"] = latex_safe_check
        self.env.filters["dnd_ability_modifier"] = dnd_ability_modifier
        self.env.filters["dnd_challenge_rating"] = dnd_challenge_rating
        self.env.filters["dnd_spell_level"] = dnd_spell_level
        self.env.filters["markdown_to_latex"] = markdown_to_latex
        self.env.filters["clean_jinja_comments"] = clean_jinja_comments
        self.env.filters["dnd_smallcaps"] = dnd_smallcaps
        self.env.filters["safe_processed_name"] = safe_processed_name

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

            # Render template with context
            rendered = template.render(context)

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
            from ...cli.services import get_cli_template_service

            context["template_service"] = get_cli_template_service()

        if "content_tracker" not in kwargs:
            from ...core.references.content_tracker import ContentTracker

            context["content_tracker"] = ContentTracker()

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
        # Get content-specific configuration
        content_config = self.latex_config.get_content_type_config(content_type)

        # Create base context
        context = self.create_template_context(**kwargs)

        # Add DND-specific configuration
        context.update(
            {
                "document_class": content_config["document_class"],
                "class_options": content_config["class_options"],
                "content_type": content_type,
                "use_dnd_template": True,
                "dnd_template_available": self.check_dnd_template_availability(),
            }
        )

        # Add LaTeX document configuration
        doc_config = self.latex_config.document
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
                "show_toc": doc_config.include_toc,
                "show_index": doc_config.include_index,
                "enable_index": doc_config.include_index,
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
