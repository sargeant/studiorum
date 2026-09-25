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
    StrictUndefined,
    Template,
    Undefined,
    pass_context,
)
from jinja2.runtime import Context
from markupsafe import Markup

from studiorum.core.config.unified_config import (
    LaTeXConfig,
    LaTeXDocumentConfig,
    get_app_config,
)
from studiorum.core.models.creatures import Ability, Spellcasting
from studiorum.latex_engine.entries import (
    EntryRenderer,
    creature_ac_text,
    creature_senses_text,
)
from studiorum.renderers.escape import escape
from studiorum.renderers.tags import render


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


# An HTML entity in the output means Jinja escaped a string as HTML: it does
# that when a Markup value meets a plain string in ~, join or format
_HTML_ESCAPED = re.compile(r"(?<!\\)&(?:amp|lt|gt|quot|#34|#39);")


def as_latex(text: str) -> Markup:
    """Mark text as LaTeX, so templates print it as it is."""
    # Markup marks LaTeX here: nothing this environment renders is HTML
    return Markup(text)  # nosec B704


def _finalize(value: Any) -> Any:
    """Escape anything printed that is not already LaTeX (Markup) as text.

    None is an error rather than the word "None".
    """
    if value is None:
        raise ValueError("A template printed None; test for it or give a default")
    if hasattr(value, "__html__"):
        return value
    return as_latex(escape(value if isinstance(value, str) else str(value)))


def _safe_processed_name(obj: Any) -> Markup:
    """An ability's name with its tags rendered, or any object's name."""
    if isinstance(obj, Ability | Spellcasting):
        return as_latex(render(obj.name) if obj.name else "")
    if isinstance(obj, dict):
        return as_latex(escape(obj.get("name", "Unknown")))
    if hasattr(obj, "name"):
        return as_latex(escape(obj.name))
    return as_latex(escape(str(obj)))


@pass_context
def _entries(context: Context, value: Any) -> Markup:
    """LaTeX for entries, rendered with the template's rendering_context."""
    if isinstance(value, Undefined):
        return Markup("")
    rendering_context = context.get("rendering_context")
    if rendering_context is None:
        return as_latex(EntryRenderer().render(value))
    return as_latex(EntryRenderer.from_context(rendering_context).render(value))


def _latex(render_text: Callable[[Any], str | None]) -> Callable[[Any], Markup]:
    """A filter that returns LaTeX, marked so it is not escaped again."""
    return lambda value: as_latex(render_text(value) or "")


@cache
def environment() -> Environment:
    """The Jinja environment for every template, with LaTeX-friendly delimiters.

    Autoescape is on, with ``_finalize`` escaping as LaTeX what is printed:
    macro output, ``| safe`` values and the LaTeX filters pass through, and
    everything else is plain text. Undefined variables are errors.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=True,
        finalize=_finalize,
        undefined=StrictUndefined,
        block_start_string="<@",
        block_end_string="@>",
        variable_start_string="<#",
        variable_end_string="#>",
        comment_start_string="<#--",
        comment_end_string="--#>",
    )
    filters: dict[str, Callable[..., Any]] = {
        "safe_processed_name": _safe_processed_name,
        "processed_ac_text": _latex(creature_ac_text),
        "processed_senses": _latex(creature_senses_text),
        "entries": _entries,
    }
    env.filters.update(filters)
    return env


def check_output(latex: str) -> str:
    """The rendered LaTeX, or an error if Jinja escaped any of it as HTML."""
    if match := _HTML_ESCAPED.search(latex):
        start = max(match.start() - 60, 0)
        raise ValueError(
            f"Template output was escaped as HTML near: {latex[start : match.end()]!r}"
        )
    return latex


class LaTeXTemplateEngine:
    """Renders templates with the document class and options from the config.

    See ``environment()`` for how printed values are escaped.
    """

    def __init__(self) -> None:
        self.templates_dir = TEMPLATES_DIR
        # Start from the loaded configuration; convert commands pass their own
        self.latex_config = get_app_config().rendering.latex

        # Initialize the environment
        self.update_latex_config(None)

    def update_latex_config(self, latex_config: LaTeXConfig | None) -> None:
        """Update the LaTeX configuration.

        Args:
            latex_config: New LaTeX configuration to use
        """
        if latex_config is not None:
            self.latex_config = latex_config

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
        """Collapse runs of blank lines, and check nothing was escaped as HTML."""
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = re.sub(r"\n\n\n+", "\n\n", content)
        return check_output(content.strip())

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

        # Document-level settings only some documents set
        context: dict[str, Any] = {
            "title": None,
            "show_title_page": False,
            "use_frontmatter": False,
            **kwargs,
        }

        # Add DND-specific configuration
        context.update(
            {
                "document_class": document_class,
                "class_options": class_options,
                "content_type": content_type,
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
        """Render a document template with the configured document class and options."""
        context = self.create_dnd_template_context(content_type, **kwargs)
        return self.render_template(template_name, context)
