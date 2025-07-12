CLI Reference
=============

Complete reference for all 5e2pdf command-line options and commands.

Global Options
--------------

These options are available for all commands:

.. code-block:: bash

   5e2pdf [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

``--verbose``
  Enable verbose output for debugging

``--help``
  Show help message and exit

``--version``
  Show version information

Main Commands
-------------

convert
~~~~~~~

Convert D&D content to LaTeX format.

**Subcommands:**

``adventure``
^^^^^^^^^^^^^

Convert adventure JSON files to LaTeX.

.. code-block:: bash

   5e2pdf convert adventure INPUT_FILE [OPTIONS]

**Arguments:**

- ``INPUT_FILE``: Path to the adventure JSON file

**Options:**

- ``--output, -o PATH``: Output LaTeX file path
- ``--title TEXT``: Custom document title
- ``--images / --no-images``: Include images (default: no images)
- ``--items / --no-items``: Include item lists (default: include)
- ``--creatures / --no-creatures``: Include creature lists (default: include)
- ``--pdf``: Compile to PDF after conversion

**Example:**

.. code-block:: bash

   5e2pdf convert adventure cos.json \\
     --output curse-of-strahd.tex \\
     --title "Curse of Strahd" \\
     --images \\
     --pdf

``book``
^^^^^^^^

Convert sourcebook JSON files to LaTeX.

.. code-block:: bash

   5e2pdf convert book INPUT_FILE [OPTIONS]

**Arguments:**

- ``INPUT_FILE``: Path to the book JSON file

**Options:**

- ``--output, -o PATH``: Output LaTeX file path
- ``--title TEXT``: Custom document title
- ``--images / --no-images``: Include images (default: no images)
- ``--index / --no-index``: Include index (default: include)
- ``--pdf``: Compile to PDF after conversion

**Example:**

.. code-block:: bash

   5e2pdf convert book phb.json \\
     --title "Player's Handbook" \\
     --images \\
     --index

``supplement``
^^^^^^^^^^^^^^

Convert miscellaneous content (spells, creatures, items) to LaTeX.

.. code-block:: bash

   5e2pdf convert supplement INPUT_FILE [OPTIONS]

**Arguments:**

- ``INPUT_FILE``: Path to the supplement JSON file

**Options:**

- ``--output, -o PATH``: Output LaTeX file path
- ``--title TEXT``: Custom document title
- ``--type TEXT``: Content types to include (can be used multiple times)
- ``--images / --no-images``: Include images (default: no images)
- ``--pdf``: Compile to PDF after conversion

**Example:**

.. code-block:: bash

   5e2pdf convert supplement mixed-content.json \\
     --type spell \\
     --type creature \\
     --title "Spell and Creature Collection"

list
~~~~

List and discover available content.

``files``
^^^^^^^^^

List available JSON files in data directories.

.. code-block:: bash

   5e2pdf list files [OPTIONS]

**Options:**

- ``--dir, -d PATH``: Directory to scan (default: standard data directories)
- ``--pattern, -p TEXT``: File pattern to match (default: ``*.json``)

**Example:**

.. code-block:: bash

   5e2pdf list files --dir ./homebrew --pattern "*.json"

``content``
^^^^^^^^^^^

List loaded content items.

.. code-block:: bash

   5e2pdf list content [OPTIONS]

**Options:**

- ``--type, -t TEXT``: Content type filter (spell, creature, item, adventure, book)
- ``--source, -s TEXT``: Filter by source book abbreviation
- ``--limit, -l INTEGER``: Limit number of results (default: 20)
- ``--search TEXT``: Search content names

**Example:**

.. code-block:: bash

   5e2pdf list content \\
     --type spell \\
     --source "PHB" \\
     --search "fire" \\
     --limit 10

``sources``
^^^^^^^^^^^

List available source books.

.. code-block:: bash

   5e2pdf list sources

info
~~~~

Show detailed information about content.

``content``
^^^^^^^^^^^

Show detailed information about a specific content item.

.. code-block:: bash

   5e2pdf info content NAME [OPTIONS]

**Arguments:**

- ``NAME``: Name of the content item

**Options:**

- ``--type, -t TEXT``: Content type hint (spell, creature, item)
- ``--source, -s TEXT``: Source book filter

**Example:**

.. code-block:: bash

   5e2pdf info content "Fireball" --type spell

``file``
^^^^^^^^

Show information about a JSON file.

.. code-block:: bash

   5e2pdf info file FILE_PATH

**Arguments:**

- ``FILE_PATH``: Path to the JSON file

**Example:**

.. code-block:: bash

   5e2pdf info file ./data/spells-phb.json

stats
~~~~~

Show content statistics and analytics.

.. code-block:: bash

   5e2pdf stats [OPTIONS]

**Options:**

- ``--by-source``: Group statistics by source book
- ``--by-type``: Group statistics by content type
- ``--detailed``: Show detailed statistics

**Example:**

.. code-block:: bash

   5e2pdf stats --by-source --detailed

quick
~~~~~

Quick single-file conversion with minimal configuration.

.. code-block:: bash

   5e2pdf quick INPUT_FILE [OPTIONS]

**Arguments:**

- ``INPUT_FILE``: Path to the JSON file

**Options:**

- ``--output, -o PATH``: Output file path
- ``--type, -t TEXT``: Content type hint (auto, adventure, book)
- ``--images``: Include images
- ``--pdf``: Compile to PDF

**Example:**

.. code-block:: bash

   5e2pdf quick spells.json --pdf --images

legacy
~~~~~~

Run commands with backwards compatibility for json2tex.py workflows.

.. code-block:: bash

   5e2pdf legacy [LEGACY_ARGS...]

**Legacy Arguments:**

- ``--adventure``: Process as adventure
- ``--book``: Process as book
- ``--with-images`` / ``--no-images``: Image handling
- ``--add-items`` / ``--no-items``: Include items
- ``--add-creatures`` / ``--no-creatures``: Include creatures
- ``--help``: Show legacy help
- ``--version``: Show legacy version

**Example:**

.. code-block:: bash

   5e2pdf legacy --adventure --with-images adventure.json > output.tex

serve
~~~~~

Start REST API server (future feature).

.. code-block:: bash

   5e2pdf serve [OPTIONS]

**Options:**

- ``--host TEXT``: Host to bind to (default: localhost)
- ``--port INTEGER``: Port to bind to (default: 8000)
- ``--reload``: Enable auto-reload

Output Files
------------

5e2pdf generates LaTeX files with the following characteristics:

- **UTF-8 encoding**: Full Unicode support for D&D content
- **XeLaTeX compatible**: Optimized for XeLaTeX compilation
- **Modular structure**: Easy to include in larger documents
- **D&D styling**: Matches official book formatting

To compile the generated LaTeX:

.. code-block:: bash

   xelatex output.tex

Configuration Files
------------------

5e2pdf looks for configuration files in these locations:

- Linux/macOS: ``~/.config/5e2pdf/config.yaml``
- Windows: ``%APPDATA%\\5e2pdf\\config.yaml``
- Project directory: ``./5e2pdf.yaml``

Example configuration:

.. code-block:: yaml

   # Data source configuration
   data_paths:
     - "./data"
     - "./homebrew"
     - "~/Documents/dnd-data"
   
   # Output configuration
   output:
     default_directory: "./output"
     include_images: false
     create_subdirectories: true
   
   # LaTeX configuration
   latex:
     engine: "xelatex"
     additional_packages:
       - "fontspec"
       - "microtype"
   
   # CLI defaults
   cli:
     default_limit: 20
     verbose: false

Environment Variables
--------------------

- ``5E2PDF_DATA_PATH``: Additional data directory paths (colon-separated)
- ``5E2PDF_OUTPUT_DIR``: Default output directory
- ``5E2PDF_CACHE_DIR``: Cache directory location
- ``5E2PDF_CONFIG``: Custom configuration file path

Exit Codes
----------

- ``0``: Success
- ``1``: General error (file not found, parsing error, etc.)
- ``2``: Command line argument error