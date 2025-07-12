Quick Start Guide
=================

This guide will get you up and running with 5e2pdf in just a few minutes.

Your First Conversion
---------------------

Let's start by converting a simple spell or item file to LaTeX:

.. code-block:: bash

   # Quick convert a JSON file to LaTeX
   5e2pdf quick spells.json --output spells.tex

   # Convert and compile to PDF in one step
   5e2pdf quick spells.json --pdf

Exploring Available Content
---------------------------

Before converting, you might want to see what's available:

.. code-block:: bash

   # List available JSON files
   5e2pdf list files

   # List loaded content by type
   5e2pdf list content --type spell --limit 10

   # Search for specific content
   5e2pdf list content --search "fireball"

   # Show information about a specific item
   5e2pdf info content "Fireball"

Converting Adventures
--------------------

Adventures are the most complex content type and have dedicated commands:

.. code-block:: bash

   # Convert an adventure to LaTeX
   5e2pdf convert adventure adventure-cos.json

   # Specify output location and include images
   5e2pdf convert adventure adventure-cos.json \\
     --output ./output/cos.tex \\
     --images \\
     --title "Curse of Strahd"

   # Convert and compile to PDF
   5e2pdf convert adventure adventure-cos.json --pdf

Converting Books
---------------

Sourcebooks can be converted similarly:

.. code-block:: bash

   # Convert a sourcebook
   5e2pdf convert book phb.json --output phb.tex

   # Include index and images
   5e2pdf convert book phb.json \\
     --images \\
     --index \\
     --title "Player's Handbook"

Converting Supplements
---------------------

For miscellaneous content like spell lists or creature collections:

.. code-block:: bash

   # Convert all content types
   5e2pdf convert supplement spells-phb.json

   # Convert only specific content types
   5e2pdf convert supplement mixed-content.json \\
     --type spell \\
     --type item

Legacy Mode
-----------

If you have existing scripts that use the old json2tex.py format:

.. code-block:: bash

   # Run legacy commands
   5e2pdf legacy --adventure --no-images adventure.json > output.tex

   # Get help for legacy mode
   5e2pdf legacy --help

Working with Output
------------------

5e2pdf generates LaTeX files that you can:

1. **Compile to PDF**:

   .. code-block:: bash

      xelatex output.tex

2. **Edit in LaTeX editors** like TeXstudio, Overleaf, or VS Code

3. **Customize** by modifying the generated LaTeX code

4. **Include in larger documents** by using ``\\input{output.tex}``

Configuration Tips
-----------------

For frequently used options, create a configuration file:

.. code-block:: yaml

   # ~/.config/5e2pdf/config.yaml
   output:
     default_directory: "./output"
     include_images: true
   
   latex:
     engine: "xelatex"

Then your commands become simpler:

.. code-block:: bash

   # Uses configured defaults
   5e2pdf convert adventure adventure.json

Common Workflows
---------------

**Adventure Publishing Workflow**:

.. code-block:: bash

   # 1. Convert adventure with all features
   5e2pdf convert adventure my-adventure.json \\
     --images \\
     --items \\
     --creatures \\
     --title "My Custom Adventure"

   # 2. Compile to PDF
   cd output/adventures
   xelatex my-adventure.tex

**Spell Reference Workflow**:

.. code-block:: bash

   # Create a custom spell collection
   5e2pdf convert supplement spell-collection.json \\
     --type spell \\
     --title "Custom Spell Collection"

**Content Discovery Workflow**:

.. code-block:: bash

   # Find all creatures from a specific source
   5e2pdf list content \\
     --type creature \\
     --source "MM" \\
     --limit 50

   # Get detailed info about specific creatures
   5e2pdf info content "Ancient Red Dragon"

Next Steps
----------

- Read the :doc:`cli-reference` for complete command documentation
- Check out :doc:`examples` for more complex use cases
- Learn about the :doc:`../developer/architecture` if you want to contribute

Troubleshooting
--------------

**Command not found**: Make sure 5e2pdf is installed and in your PATH

**No content found**: Ensure you've set up the data sources correctly (see :doc:`installation`)

**LaTeX errors**: Check that you have XeLaTeX installed and the generated LaTeX is valid

**Slow performance**: The first run loads all data and builds indexes - subsequent runs are much faster