"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document) are in another directory, add these
# directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

import dnd5e

# -- Project information -----------------------------------------------------

project = "5e2pdf"
copyright_ = "2025, Sam Sargeant"  # renamed to avoid shadowing builtin
author = "Sam Sargeant"

# The full version, including alpha/beta/rc tags
release = version = dnd5e.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "myst_parser",  # Markdown support
    "sphinxcontrib.mermaid",  # Mermaid diagrams
    "sphinx.ext.autodoc",  # Auto-generate API docs
    "sphinx.ext.viewcode",  # Add source code links
    "sphinx.ext.napoleon",  # Google/NumPy docstring support
    "sphinx_copybutton",  # Copy button for code blocks
    "sphinx.ext.intersphinx",  # Links to other documentation
    "sphinx.ext.todo",  # Todo support
    "sphinx.ext.autosummary",  # Auto-generate summary tables
    "sphinx.ext.autosectionlabel",  # Auto-generate section labels
    "sphinx.ext.duration",  # Build duration tracking
    "sphinx.ext.graphviz",  # Graphviz diagrams
    "sphinx_design",  # Landing page layout and design components
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The root toctree document (Sphinx 8.x best practice)
root_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# MyST configuration for GitHub-compatible Mermaid
myst_enable_extensions = [
    "colon_fence",  # ::: fences
    "deflist",  # Definition lists
    "html_image",  # HTML img tags
    "tasklist",  # Task lists
    "linkify",  # Auto-link URLs
    "substitution",  # Text substitutions
    "attrs_inline",  # Inline attributes
    "attrs_block",  # Block attributes
]

# Configure Mermaid to use fence syntax (GitHub compatible)
myst_fence_as_directive = ["mermaid"]

# Auto-section labeling for cross-references
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

# Auto-summary configuration
autosummary_generate = True
autosummary_imported_members = True

myst_substitutions = {"version": version}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "shibuya"

# Theme-specific options
html_theme_options = {
    # Color and appearance
    "accent_color": "blue",  # Modern blue accent color
    "dark_code": True,  # Dark mode for code blocks
    # Logo configuration (when available)
    "light_logo": None,  # Path to light mode logo
    "dark_logo": None,  # Path to dark mode logo
    # Social media and external links
    "github_url": "https://github.com/sargeant/5e2pdf",
    # Navigation links
    "nav_links": [
        {
            "title": "Documentation",
            "children": [
                {
                    "title": "User Guide",
                    "url": "/user-guide/index",
                    "summary": "Getting started and basic usage",
                },
                {
                    "title": "API Reference",
                    "url": "/api/index",
                    "summary": "Complete API documentation",
                },
                {
                    "title": "Developer Docs",
                    "url": "/developer/index",
                    "summary": "Architecture and implementation guides",
                },
            ],
        },
        {
            "title": "Examples",
            "url": "/examples/index",
            "summary": "Usage examples and tutorials",
        },
    ],
    # Table of contents configuration
    "toctree_collapse": False,  # Keep TOC expanded
    "toctree_maxdepth": 3,  # Reasonable depth for navigation
    "toctree_titles_only": False,  # Show full section names
    "toctree_includehidden": True,  # Include hidden sections
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom CSS files
html_css_files = [
    "css/custom.css",
]

# HTML title
html_title = f"{project} v{version}"

# Favicon
html_favicon = None  # Add path to favicon if available

# Logo
html_logo = None  # Add path to logo if available

# Show source link
html_show_sourcelink = True
html_copy_source = True
html_show_sphinx = False


# -- Options for Mermaid ----------------------------------------------------

# Mermaid configuration
mermaid_output_format = "raw"  # Best for web deployment
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    themeVariables: {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }
});
"""

# Mermaid version
mermaid_version = "10.6.1"


# -- Options for LaTeX/PDF output -------------------------------------------

latex_engine = "xelatex"  # Better Unicode support

latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "11pt",
    "preamble": r"""
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
\usepackage{graphicx}
\usepackage{xcolor}
\definecolor{VerbatimColor}{rgb}{0.95,0.95,0.95}
""",
    "fncychap": "\\usepackage[Bjarne]{fncychap}",
    "printindex": "\\footnotesize\\raggedright\\printindex",
}

# LaTeX PDF configuration
latex_documents = [
    ("index", "5e2pdf-docs.tex", "5e2pdf Documentation", "Sam Sargeant", "manual"),
]

latex_logo = None  # Path to logo file if desired
latex_show_pagerefs = True
latex_show_urls = "footnote"


# -- Extension configuration -------------------------------------------------

# Napoleon settings for docstring parsing
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc configuration
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": False,
    "special-members": "__init__",
    "inherited-members": True,
    "show-inheritance": True,
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# Todo configuration
todo_include_todos = True

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True
copybutton_remove_prompts = True
