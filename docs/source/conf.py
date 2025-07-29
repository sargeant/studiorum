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


# -- Project information -----------------------------------------------------

project = "5e2pdf"
copyright_ = "2025, Sam Sargeant"  # renamed to avoid shadowing builtin
author = "Sam Sargeant"

# The full version, including alpha/beta/rc tags
release = "0.3.1"
version = "0.3.1"


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
]

# Configure Mermaid to use fence syntax (GitHub compatible)
myst_fence_as_directive = ["mermaid"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"

# Theme-specific options
html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "light_css_variables": {
        "color-brand-primary": "#2563eb",
        "color-brand-content": "#2563eb",
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        "font-stack--monospace": "JetBrains Mono, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",
        "color-brand-content": "#60a5fa",
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        "font-stack--monospace": "JetBrains Mono, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    },
    "source_repository": "https://github.com/sargeant/5e2pdf/",
    "source_branch": "main",
    "source_directory": "docs/source/",
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
mermaid_init_js = "mermaid.initialize({startOnLoad:true, theme:'default'});"

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
