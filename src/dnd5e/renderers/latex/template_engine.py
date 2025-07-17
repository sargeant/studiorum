"""Jinja2-based LaTeX template engine for D&D-style documents."""

import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

import jinja2
from jinja2 import Environment, FileSystemLoader, Template


class LaTeXTemplateEngine:
    """Jinja2-based template engine for LaTeX document generation.

    Provides template loading, caching, and rendering with LaTeX-specific
    escaping and filters. Supports template inheritance and uses DND-5e-LaTeX-Template
    document classes.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize template engine.

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.templates_dir = Path(
            self.config.get("templates_dir", "src/dnd5e/renderers/latex/templates")
        )
        self.debug = self.config.get("debug", False)

        # Create templates directory if it doesn't exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
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
        self._template_cache = {}

    def _add_latex_filters(self):
        """Add LaTeX-specific filters to Jinja2 environment."""

        def latex_escape(value: str) -> str:
            """Escape LaTeX special characters."""
            if not isinstance(value, str):
                value = str(value)

            # Use unique placeholders to avoid double-escaping
            # 1. Replace special LaTeX commands with placeholders
            value = value.replace("\\", "__XBACKSLASHX__")
            value = value.replace("~", "__XTILDEX__")
            value = value.replace("^", "__XCARETX__")

            # 2. Escape remaining characters
            value = value.replace("&", r"\&")
            value = value.replace("%", r"\%")
            value = value.replace("$", r"\$")
            value = value.replace("#", r"\#")
            value = value.replace("_", r"\_")
            value = value.replace("{", r"\{")
            value = value.replace("}", r"\}")

            # 3. Replace placeholders with LaTeX commands
            value = value.replace("__XBACKSLASHX__", r"\textbackslash{}")
            value = value.replace("__XTILDEX__", r"\textasciitilde{}")
            value = value.replace("__XCARETX__", r"\textasciicircum{}")

            return value

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

        def dnd_ability_modifier(value: Union[int, str]) -> str:
            """Format ability score as modifier (+1, -2, etc.)."""
            try:
                score = int(value)
                modifier = (score - 10) // 2
                return f"+{modifier}" if modifier >= 0 else str(modifier)
            except (ValueError, TypeError):
                return str(value)

        def dnd_challenge_rating(value: Union[int, str, float]) -> str:
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

        def dnd_spell_level(value: Union[int, str]) -> str:
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

        # Register filters
        self.env.filters["latex_escape"] = latex_escape
        self.env.filters["latex_newlines"] = latex_newlines
        self.env.filters["latex_bold"] = latex_bold
        self.env.filters["latex_italic"] = latex_italic
        self.env.filters["latex_underline"] = latex_underline
        self.env.filters["latex_verbatim"] = latex_verbatim
        self.env.filters["dnd_ability_modifier"] = dnd_ability_modifier
        self.env.filters["dnd_challenge_rating"] = dnd_challenge_rating
        self.env.filters["dnd_spell_level"] = dnd_spell_level

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
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
        """Get template object by name with caching.

        Args:
            template_name: Name of template file

        Returns:
            Jinja2 Template object
        """
        if template_name not in self._template_cache:
            self._template_cache[template_name] = self.env.get_template(template_name)
        return self._template_cache[template_name]

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

    def clear_cache(self):
        """Clear template cache."""
        self._template_cache.clear()

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

    def create_template_context(self, **kwargs) -> Dict[str, Any]:
        """Create template context with common variables.

        Args:
            **kwargs: Additional context variables

        Returns:
            Template context dictionary
        """
        context = {
            "config": self.config,
            "debug": self.debug,
        }
        context.update(kwargs)
        return context
