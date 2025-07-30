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
html_theme = "sphinxawesome_theme"

# Theme-specific options
html_theme_options = {
    "awesome_external_links": True,
    "awesome_headerlinks": True,
    "logo_light": None,  # Path to light mode logo
    "logo_dark": None,  # Path to dark mode logo
    "show_prev_next": True,
    "show_scrolltop": True,
    "globaltoc_includehidden": True,  # Updated from deprecated nav_include_hidden
    "main_nav_links": {
        "User Guide": "/user-guide/index",
        "API Reference": "/api/index",
        "Examples": "/examples/index",
        "Developer Docs": "/developer/index",
    },
    "extra_header_link_icons": {
        "repository on GitHub": {
            "link": "https://github.com/sargeant/5e2pdf/",
            "icon": (
                '<svg height="26px" style="margin-top:-2px;display:inline" '
                'viewBox="0 0 45 44" '
                'fill="currentColor" xmlns="http://www.w3.org/2000/svg">'
                '<path fill-rule="evenodd" clip-rule="evenodd" '
                'd="M22.477.927C10.485.927.76 10.65.76 22.647c0 9.596 6.223 17.736 '
                "14.853 20.608 1.087.2 1.483-.47 1.483-1.047 "
                "0-.516-.019-1.881-.03-3.693-6.04 "
                "1.312-7.315-2.912-7.315-2.912-.988-2.51-2.412-3.178-2.412-3.178-1.972-1.346.149-1.32.149-1.32 "
                "2.18.154 3.327 2.24 3.327 2.24 1.937 3.318 5.084 2.36 6.321 "
                "1.803.197-1.403.759-2.36 1.379-2.903-4.823-.548-9.894-2.412-9.894-10.734 "
                "0-2.37.847-4.31 2.236-5.828-.224-.55-.969-2.759.214-5.748 0 0 "
                "1.822-.584 5.972 2.226 1.732-.482 3.59-.722 5.437-.732 1.845.01 3.703.25 "
                "5.437.732 4.147-2.81 5.967-2.226 5.967-2.226 1.185 2.99.44 5.198.217 "
                "5.748 1.392 1.517 2.232 3.457 2.232 5.828 0 8.344-5.078 10.18-9.916 "
                "10.717.779.67 1.474 1.996 1.474 4.021 0 2.904-.027 5.247-.027 5.96 0 "
                '.58.392 1.256 1.493 1.044C37.981 40.375 44.2 32.24 44.2 22.647c0-11.996-9.726-21.72-21.722-21.72Z" '
                'fill="currentColor"/></svg>'
            ),
        },
    },
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
