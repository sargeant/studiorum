5e2pdf Documentation
====================

🎲 **5e2pdf** - Modern D&D 5e content converter

Convert structured JSON data from 5e.tools into professional LaTeX documents
that match the style of official D&D 5th edition books.

.. image:: https://img.shields.io/badge/python-3.11+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License

Features
--------

- 📖 **Adventure Conversion**: Transform adventure modules into beautifully formatted documents
- 📚 **Book Processing**: Convert sourcebooks with complete formatting and structure
- 🔍 **Content Indexing**: Advanced omnidexer system for cross-referencing content
- ⚡ **Modern CLI**: User-friendly command-line interface with rich output
- 🔄 **Legacy Support**: Backwards compatibility with existing json2tex workflows
- 🎨 **Professional Output**: LaTeX rendering that matches official D&D styling

Quick Start
-----------

.. code-block:: bash

   # Install 5e2pdf
   pip install 5e2pdf

   # Convert an adventure
   5e2pdf convert adventure adventure-data.json --output adventure.tex

   # Quick conversion with PDF compilation
   5e2pdf quick input.json --pdf

   # List available content
   5e2pdf list content --type spell --limit 10

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   user-guide/installation
   user-guide/quickstart
   user-guide/cli-reference
   user-guide/examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/core
   api/cli
   api/renderers
   api/models

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide:

   developer/architecture
   developer/contributing
   developer/testing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

