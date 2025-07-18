"""LaTeX template engine for D&D-style documents."""

from pathlib import Path
from typing import Any, Optional


class LaTeXTemplateEngine:
    """Template engine for LaTeX document generation.

    Provides built-in templates for D&D-style documents and supports
    custom template loading from files.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize template engine.

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.templates_dir = Path(self.config.get("templates_dir", "templates"))
        self._template_cache = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self):
        """Load built-in LaTeX templates."""

        self._template_cache["document_header"] = r"""
\documentclass[{font_size},{page_size}]{{book}}

% D&D 5e styling packages
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{geometry}}
\usepackage{{multicol}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{float}}
\usepackage{{array}}
\usepackage{{longtable}}
\usepackage{{booktabs}}
\usepackage{{enumitem}}
\usepackage{{fancyhdr}}
\usepackage{{titling}}
\usepackage{{titlesec}}

% Page geometry for D&D style
\geometry{{
    margin=0.75in,
    top=1in,
    bottom=1in
}}

% Colors (D&D 5e style)
\definecolor{{dndred}}{{RGB}}{{158, 0, 0}}
\definecolor{{dndgold}}{{RGB}}{{255, 215, 0}}
\definecolor{{dndbeige}}{{RGB}}{{250, 241, 224}}

% Custom fonts (if available)
{{% if fonts_dir %}}
\usepackage{{fontspec}}
\setmainfont{{BookSanity}}[
    Path = {fonts_dir}/,
    Extension = .otf,
    UprightFont = *,
    BoldFont = *-Bold,
    ItalicFont = *-Italic,
    BoldItalicFont = *-BoldItalic
]
{{% endif %}}

% Header styling
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[LE,RO]{{\thepage}}
\fancyhead[LO]{{\rightmark}}
\fancyhead[RE]{{\leftmark}}
\renewcommand{{\headrulewidth}}{{0.4pt}}

% Title formatting
\titleformat{{\chapter}}[display]
  {{\normalfont\huge\bfseries\color{{dndred}}}}
  {{\chaptertitlename\ \thechapter}}{{20pt}}{{\Huge}}
\titleformat{{\section}}
  {{\normalfont\Large\bfseries\color{{dndred}}}}
  {{\thesection}}{{1em}}{{}}
\titleformat{{\subsection}}
  {{\normalfont\large\bfseries}}
  {{\thesubsection}}{{1em}}{{}}

% Document metadata
\title{{{title}}}
{{% if subtitle %}}
\subtitle{{{subtitle}}}
{{% endif %}}
{{% if author %}}
\author{{{author}}}
{{% endif %}}
\date{{{date}}}

\begin{{document}}

% Title page
\maketitle
\thispagestyle{{empty}}
\clearpage
""".strip()

        self._template_cache["document_footer"] = r"""
\end{document}
""".strip()

        self._template_cache["table_of_contents"] = r"""
\tableofcontents
\clearpage
""".strip()

        self._template_cache["index"] = r"""
\chapter*{{{title}}}
\addcontentsline{{toc}}{{chapter}}{{{title}}}

\begin{{multicols}}{{2}}
{{% for entry in index_entries %}}
\textbf{{{entry.name}}} ({entry.type}) \dotfill {entry.source} \\
{{% endfor %}}
\end{{multicols}}
""".strip()

        # Content-specific templates
        self._template_cache["spell"] = r"""
\subsection{{{name}}}
\textit{{{level_text}}}

\textbf{{Casting Time:}} {casting_time} \\
\textbf{{Range:}} {range_text} \\
\textbf{{Components:}} {components_text} \\
\textbf{{Duration:}} {duration_text}

{description}

{{% if higher_levels %}}
\textbf{{At Higher Levels.}} {higher_levels}
{{% endif %}}
""".strip()

        self._template_cache["creature"] = r"""
\subsection{{{name}}}
\textit{{{size_text} {type_text}, {alignment_text}}}

\textbf{{Armor Class}} {ac_text} \\
\textbf{{Hit Points}} {hp_text} \\
\textbf{{Speed}} {speed_text}

\begin{{center}}
\begin{{tabular}}{{|c|c|c|c|c|c|}}
\hline
\textbf{{STR}} & \textbf{{DEX}} & \textbf{{CON}} & \textbf{{INT}} & \textbf{{WIS}} & \textbf{{CHA}} \\
\hline
{str_text} & {dex_text} & {con_text} & {int_text} & {wis_text} & {cha_text} \\
\hline
\end{{tabular}}
\end{{center}}

{{% if skills %}}
\textbf{{Skills}} {skills} \\
{{% endif %}}
{{% if damage_resistances %}}
\textbf{{Damage Resistances}} {damage_resistances} \\
{{% endif %}}
{{% if damage_immunities %}}
\textbf{{Damage Immunities}} {damage_immunities} \\
{{% endif %}}
{{% if condition_immunities %}}
\textbf{{Condition Immunities}} {condition_immunities} \\
{{% endif %}}
{{% if senses %}}
\textbf{{Senses}} {senses} \\
{{% endif %}}
{{% if languages %}}
\textbf{{Languages}} {languages} \\
{{% endif %}}
\textbf{{Challenge}} {cr_text} \\

{{% if traits %}}
{{% for trait in traits %}}
\textbf{{{trait.name}.}} {trait.description}
{{% endfor %}}
{{% endif %}}

{{% if actions %}}
\subsubsection*{{Actions}}
{{% for action in actions %}}
\textbf{{{action.name}.}} {action.description}
{{% endfor %}}
{{% endif %}}
""".strip()

        self._template_cache["item"] = r"""
\subsection{{{name}}}
\textit{{{type_text}{rarity_text}}}

{description}

{{% if properties %}}
\textbf{{Properties:}} {properties}
{{% endif %}}
""".strip()

    def render_template(self, template_name: str, variables: dict[str, Any]) -> str:
        """Render a template with the given variables.

        Args:
            template_name: Name of template to render
            variables: Variables to substitute in template

        Returns:
            Rendered template content
        """
        template = self._get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        return self._substitute_variables(template, variables)

    def _get_template(self, template_name: str) -> str | None:
        """Get template content by name.

        Args:
            template_name: Name of template

        Returns:
            Template content or None if not found
        """
        # Check cache first
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Try to load from file
        template_file = self.templates_dir / f"{template_name}.tex"
        if template_file.exists():
            content = template_file.read_text(encoding="utf-8")
            self._template_cache[template_name] = content
            return content

        return None

    def _substitute_variables(self, template: str, variables: dict[str, Any]) -> str:
        """Substitute variables in template using simple string formatting.

        Args:
            template: Template content
            variables: Variables to substitute

        Returns:
            Template with variables substituted
        """
        # Simple template variable substitution
        # For more complex templating, could use Jinja2 or similar
        result = template

        # First substitute variables
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(
                    placeholder, str(value) if value is not None else ""
                )

        # Handle conditional blocks (basic implementation)
        result = self._process_conditionals(result, variables)

        # Convert double braces to single braces for LaTeX
        result = result.replace("{{", "{").replace("}}", "}")

        return result

    def _process_conditionals(self, template: str, variables: dict[str, Any]) -> str:
        """Process basic conditional blocks in templates.

        Args:
            template: Template content
            variables: Variables for conditions

        Returns:
            Template with conditionals processed
        """
        import re

        # Handle {% if var %} blocks
        def replace_if_block(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # Simple truthiness check
            if condition in variables and variables[condition]:
                return content
            return ""

        # Process if blocks
        pattern = r"{%\s*if\s+(\w+)\s*%}(.*?){%\s*endif\s*%}"
        template = re.sub(pattern, replace_if_block, template, flags=re.DOTALL)

        # Handle {% for item in items %} blocks (basic implementation)
        def replace_for_block(match):
            var_name = match.group(1).strip()
            list_name = match.group(2).strip()
            content = match.group(3)

            if list_name not in variables:
                return ""

            items = variables[list_name]
            if not isinstance(items, list | tuple):
                return ""

            result_parts = []
            for item in items:
                # Create temporary variables for this iteration
                item_content = content
                if hasattr(item, "__dict__"):
                    # Object with attributes
                    for attr_name, attr_value in item.__dict__.items():
                        placeholder = f"{var_name}.{attr_name}"
                        item_content = item_content.replace(
                            "{" + placeholder + "}", str(attr_value)
                        )
                elif isinstance(item, dict):
                    # Dictionary
                    for key, value in item.items():
                        placeholder = f"{var_name}.{key}"
                        item_content = item_content.replace(
                            "{" + placeholder + "}", str(value)
                        )

                result_parts.append(item_content)

            return "\n".join(result_parts)

        # Process for blocks
        pattern = r"{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}"
        template = re.sub(pattern, replace_for_block, template, flags=re.DOTALL)

        return template
