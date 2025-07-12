Examples
========

This page provides practical examples of using 5e2pdf for common tasks.

Basic Examples
--------------

Converting a Spell Collection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Convert a collection of spells
   5e2pdf convert supplement spells-phb.json \\
     --title "Player's Handbook Spells" \\
     --type spell

   # Result: A formatted LaTeX document with all PHB spells

Converting a Monster Manual
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Convert creatures with images
   5e2pdf convert supplement mm-creatures.json \\
     --title "Monster Manual Creatures" \\
     --type creature \\
     --images

Finding and Converting Specific Content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Find all fire-related spells
   5e2pdf list content --type spell --search "fire"

   # Get detailed info about a specific spell
   5e2pdf info content "Fireball"

   # Convert just fire spells (requires creating a custom JSON)
   5e2pdf quick fire-spells.json --title "Fire Magic"

Advanced Examples
----------------

Multi-Source Adventure Compilation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Convert main adventure
   5e2pdf convert adventure lost-mine-of-phandelver.json \\
     --title "The Lost Mine of Phandelver" \\
     --images \\
     --output lmop-main.tex

   # Convert additional creatures
   5e2pdf convert supplement lmop-creatures.json \\
     --type creature \\
     --title "Additional Creatures" \\
     --output lmop-creatures.tex

   # Convert magic items
   5e2pdf convert supplement lmop-items.json \\
     --type item \\
     --title "Magic Items" \\
     --output lmop-items.tex

   # Manually combine in LaTeX:
   # \\input{lmop-main}
   # \\input{lmop-creatures}  
   # \\input{lmop-items}

Custom Homebrew Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Organize your homebrew content
   mkdir homebrew
   
   # Create custom spells file
   cat > homebrew/my-spells.json << 'EOF'
   {
     "spell": [
       {
         "name": "Custom Fireball",
         "level": 3,
         "school": "V",
         "time": [{"number": 1, "unit": "action"}],
         "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
         "components": {"v": true, "s": true, "m": "a tiny ball of bat guano and sulfur"},
         "duration": [{"type": "instant"}],
         "entries": ["A custom version of the classic fireball spell."],
         "source": {"abbreviation": "HB", "name": "Homebrew"}
       }
     ]
   }
   EOF

   # Convert homebrew content
   5e2pdf convert supplement homebrew/my-spells.json \\
     --title "My Custom Spells" \\
     --type spell

Batch Processing Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   # batch-convert.sh - Convert multiple adventures

   ADVENTURES=(
     "adventure-cos.json:Curse of Strahd"
     "adventure-lmop.json:Lost Mine of Phandelver"  
     "adventure-hoard.json:Hoard of the Dragon Queen"
   )

   for adventure in "${ADVENTURES[@]}"; do
     file="${adventure%:*}"
     title="${adventure#*:}"
     
     echo "Converting $title..."
     5e2pdf convert adventure "$file" \\
       --title "$title" \\
       --images \\
       --pdf \\
       --output "adventures/${file%.json}.tex"
   done

   echo "All adventures converted!"

Integration Examples
-------------------

GitHub Actions Workflow
~~~~~~~~~~~~~~~~~~~~~~~

Create ``.github/workflows/build-docs.yml``:

.. code-block:: yaml

   name: Build D&D Documents
   on:
     push:
       paths:
         - 'data/**'
         - 'homebrew/**'

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.11'
         
         - name: Install dependencies
           run: |
             pip install 5e2pdf
             sudo apt-get install texlive-xetex
         
         - name: Convert adventures
           run: |
             mkdir -p output
             5e2pdf convert adventure data/adventure-cos.json --pdf
         
         - name: Upload artifacts
           uses: actions/upload-artifact@v3
           with:
             name: dnd-documents
             path: output/*.pdf

Makefile Integration
~~~~~~~~~~~~~~~~~~~

Create a ``Makefile`` for common tasks:

.. code-block:: make

   # Makefile for D&D content processing
   
   DATA_DIR = data
   OUTPUT_DIR = output
   HOMEBREW_DIR = homebrew

   .PHONY: all adventures books clean

   all: adventures books supplements

   adventures:
   	@echo "Converting adventures..."
   	@mkdir -p $(OUTPUT_DIR)/adventures
   	@for file in $(DATA_DIR)/adventure/*.json; do \\
   		5e2pdf convert adventure "$$file" \\
   			--output "$(OUTPUT_DIR)/adventures/$$(basename $$file .json).tex" \\
   			--images; \\
   	done

   books:
   	@echo "Converting books..."
   	@mkdir -p $(OUTPUT_DIR)/books
   	@for file in $(DATA_DIR)/book/*.json; do \\
   		5e2pdf convert book "$$file" \\
   			--output "$(OUTPUT_DIR)/books/$$(basename $$file .json).tex" \\
   			--images --index; \\
   	done

   supplements:
   	@echo "Converting homebrew..."
   	@mkdir -p $(OUTPUT_DIR)/supplements
   	@for file in $(HOMEBREW_DIR)/*.json; do \\
   		5e2pdf convert supplement "$$file" \\
   			--output "$(OUTPUT_DIR)/supplements/$$(basename $$file .json).tex"; \\
   	done

   pdfs: all
   	@echo "Compiling PDFs..."
   	@find $(OUTPUT_DIR) -name "*.tex" -exec xelatex -output-directory={} {} \\;

   clean:
   	@echo "Cleaning output..."
   	@rm -rf $(OUTPUT_DIR)/*

Docker Integration
~~~~~~~~~~~~~~~~~

Create a ``Dockerfile`` for containerized processing:

.. code-block:: dockerfile

   FROM python:3.11-slim

   # Install LaTeX
   RUN apt-get update && apt-get install -y \\
       texlive-xetex \\
       texlive-fonts-recommended \\
       texlive-fonts-extra \\
       && rm -rf /var/lib/apt/lists/*

   # Install 5e2pdf
   RUN pip install 5e2pdf

   WORKDIR /workspace

   # Default command
   CMD ["5e2pdf", "--help"]

Usage:

.. code-block:: bash

   # Build the image
   docker build -t 5e2pdf .

   # Run conversions
   docker run --rm -v $(pwd):/workspace 5e2pdf \\
     convert adventure adventure.json --pdf

Content Creation Examples
------------------------

Creating a Custom Adventure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "adventure": [
       {
         "name": "The Haunted Tavern",
         "id": "haunted-tavern",
         "source": {
           "abbreviation": "HT", 
           "name": "The Haunted Tavern"
         },
         "level": {"min": 1, "max": 3},
         "contents": [
           {
             "name": "Introduction",
             "entries": [
               "Welcome to the Haunted Tavern, a short adventure for characters of 1st to 3rd level.",
               "The party arrives at a seemingly abandoned tavern on a dark and stormy night..."
             ]
           },
           {
             "name": "The Tavern",
             "entries": [
               "The tavern appears empty, but strange sounds come from upstairs...",
               {
                 "type": "entries",
                 "name": "Ground Floor",
                 "entries": ["Description of the main room..."]
               }
             ]
           }
         ]
       }
     ]
   }

Creating a Spell Compendium
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "spell": [
       {
         "name": "Mystical Shield",
         "level": 1,
         "school": "A",
         "time": [{"number": 1, "unit": "action"}],
         "range": {"type": "point", "distance": {"type": "self"}},
         "components": {"v": true, "s": true},
         "duration": [{"type": "timed", "duration": {"type": "hour", "amount": 1}}],
         "entries": [
           "A shimmering field of magical force surrounds you, granting protection against attacks.",
           "You gain a +2 bonus to AC for the duration."
         ],
         "classes": {
           "fromClassList": [
             {"name": "Wizard", "source": "PHB"},
             {"name": "Sorcerer", "source": "PHB"}
           ]
         },
         "source": {"abbreviation": "HB", "name": "Homebrew Spells"}
       }
     ]
   }

Performance Tips
---------------

Large Dataset Processing
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # For large datasets, use caching
   export 5E2PDF_CACHE_DIR=/tmp/5e2pdf-cache

   # Process in chunks for memory efficiency
   5e2pdf list content --limit 100 --type spell | \\
     while read spell; do
       5e2pdf info content "$spell" >> spell-details.txt
     done

Optimizing LaTeX Compilation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Use parallel compilation for multiple files
   find output/ -name "*.tex" | xargs -P 4 -I {} xelatex {}

   # Or use latexmk for automatic rebuilds
   latexmk -xelatex -pvc output/adventure.tex

Troubleshooting Examples
-----------------------

Debug Missing Content
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check what's loaded
   5e2pdf list sources

   # Verify data paths
   5e2pdf list files --dir ./data

   # Test specific content
   5e2pdf info content "Fireball" --type spell

Handle Encoding Issues
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Ensure UTF-8 encoding
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8

   # Check file encoding
   file -bi data/adventure/*.json

Fix LaTeX Compilation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run with verbose LaTeX output
   xelatex -interaction=nonstopmode -file-line-error adventure.tex

   # Check for missing packages
   grep "! LaTeX Error" adventure.log