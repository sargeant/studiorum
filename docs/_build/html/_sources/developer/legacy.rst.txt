Legacy System Documentation
===========================

This document explains the legacy json2tex system and how it integrates with the modern 5e2pdf architecture.

Historical Context
-----------------

The original json2tex.py script was created to convert 5etools JSON data directly to LaTeX. While functional, it had several limitations:

- Monolithic design with tight coupling
- Limited extensibility for new content types
- No proper error handling or validation
- Difficult to test and maintain
- Command-line interface was basic

The modern 5e2pdf system addresses these issues while maintaining backwards compatibility.

Legacy System Architecture
-------------------------

Original json2tex.py Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   json2tex.py (single file)
   ├── Global variables and constants
   ├── JSON loading functions
   ├── Content parsing functions
   ├── LaTeX generation functions
   ├── Tag resolution (basic)
   └── Main CLI logic

Key Components:

- **Direct JSON parsing**: No validation or type safety
- **Inline LaTeX generation**: Mixed logic and output
- **Basic tag resolution**: Limited cross-referencing
- **Procedural design**: No object-oriented structure

Legacy Command-Line Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The original interface used simple flags:

.. code-block:: bash

   python json2tex.py [OPTIONS] INPUT_FILE

   Options:
     --adventure          Process as adventure
     --book              Process as book  
     --supplement        Process as supplement
     --with-images       Include images
     --no-images         Exclude images (default)
     --add-items         Include item appendices
     --no-items          Exclude item appendices
     --add-creatures     Include creature appendices  
     --no-creatures      Exclude creature appendices
     --help              Show help message
     --version           Show version

Legacy Compatibility Layer
--------------------------

Modern Implementation
~~~~~~~~~~~~~~~~~~~~

The modern system provides full backwards compatibility through ``src/cli/compat.py``:

.. code-block:: python

   class LegacyCompatLayer:
       """Provides backwards compatibility with json2tex.py commands."""
       
       def execute_legacy_command(self, args: List[str]) -> str:
           """Execute a legacy-style command using modern architecture."""
           # Parse legacy arguments
           parsed = self._parse_legacy_args(args)
           
           # Convert to modern command
           modern_result = self._execute_modern_equivalent(parsed)
           
           return modern_result

Argument Translation
~~~~~~~~~~~~~~~~~~~

Legacy arguments are mapped to modern equivalents:

.. code-block:: python

   LEGACY_MAPPING = {
       '--adventure': {'content_type': 'adventure'},
       '--book': {'content_type': 'book'},
       '--supplement': {'content_type': 'supplement'},
       '--with-images': {'include_images': True},
       '--no-images': {'include_images': False},
       '--add-items': {'include_items': True},
       '--no-items': {'include_items': False},
       '--add-creatures': {'include_creatures': True},
       '--no-creatures': {'include_creatures': False},
   }

Usage Examples
~~~~~~~~~~~~~

Legacy commands work identically to the original:

.. code-block:: bash

   # Legacy adventure conversion
   5e2pdf legacy --adventure --with-images adventure.json > output.tex

   # Legacy book conversion  
   5e2pdf legacy --book --no-images book.json > book.tex

   # Legacy supplement with appendices
   5e2pdf legacy --supplement --add-items --add-creatures supplement.json > supplement.tex

Migration Guide
--------------

Migrating from json2tex.py
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Step 1: Install 5e2pdf**

.. code-block:: bash

   pip install 5e2pdf

**Step 2: Test legacy compatibility**

.. code-block:: bash

   # Your existing command:
   python json2tex.py --adventure adventure.json > output.tex

   # Equivalent 5e2pdf command:
   5e2pdf legacy --adventure adventure.json > output.tex

**Step 3: Gradually adopt modern commands**

.. code-block:: bash

   # Modern equivalent with same output:
   5e2pdf convert adventure adventure.json --output output.tex

   # Modern command with additional features:
   5e2pdf convert adventure adventure.json \
     --title "My Adventure" \
     --images \
     --pdf

**Step 4: Update build scripts**

Replace calls to json2tex.py in Makefiles and scripts:

.. code-block:: bash

   # Old Makefile rule:
   %.tex: %.json
   	python json2tex.py --adventure $< > $@

   # New Makefile rule:
   %.tex: %.json
   	5e2pdf convert adventure $< --output $@

Behavioral Differences
~~~~~~~~~~~~~~~~~~~~~

While output is largely identical, there are some improvements:

**Error Handling:**
- Legacy: Silent failures or cryptic error messages
- Modern: Clear error messages with suggestions

**Performance:**
- Legacy: No caching, repeated parsing
- Modern: Intelligent caching and parallel processing

**Validation:**
- Legacy: No input validation
- Modern: Comprehensive validation with helpful error messages

**Output Quality:**
- Legacy: Basic LaTeX generation
- Modern: Improved formatting and D&D styling

Script Migration Examples
------------------------

Simple Conversion Script
~~~~~~~~~~~~~~~~~~~~~~~

**Legacy script:**

.. code-block:: bash

   #!/bin/bash
   # convert-adventures.sh
   
   for file in adventures/*.json; do
       echo "Converting $file..."
       python json2tex.py --adventure --with-images "$file" > "output/$(basename "$file" .json).tex"
   done

**Modern equivalent:**

.. code-block:: bash

   #!/bin/bash
   # convert-adventures.sh
   
   for file in adventures/*.json; do
       echo "Converting $file..."
       5e2pdf convert adventure "$file" \
         --images \
         --output "output/$(basename "$file" .json).tex"
   done

**Modern enhanced version:**

.. code-block:: bash

   #!/bin/bash
   # convert-adventures.sh
   
   mkdir -p output/adventures
   
   for file in adventures/*.json; do
       name=$(basename "$file" .json)
       echo "Converting $name..."
       
       5e2pdf convert adventure "$file" \
         --title "$(echo "$name" | tr '-' ' ' | tr '[:lower:]' '[:upper:]')" \
         --images \
         --pdf \
         --output "output/adventures/$name.tex"
         
       if [ $? -eq 0 ]; then
           echo "✓ Successfully converted $name"
       else
           echo "✗ Failed to convert $name"
       fi
   done

Complex Build System
~~~~~~~~~~~~~~~~~~~~

**Legacy Makefile:**

.. code-block:: make

   # Old Makefile
   ADVENTURES = $(wildcard data/adventure/*.json)
   ADVENTURE_TEX = $(ADVENTURES:data/adventure/%.json=output/%.tex)

   all: $(ADVENTURE_TEX)

   output/%.tex: data/adventure/%.json
   	@mkdir -p output
   	python json2tex.py --adventure --with-images $< > $@
   	
   clean:
   	rm -f output/*.tex

**Modern Makefile:**

.. code-block:: make

   # New Makefile
   ADVENTURES = $(wildcard data/adventure/*.json)
   ADVENTURE_TEX = $(ADVENTURES:data/adventure/%.json=output/adventures/%.tex)
   ADVENTURE_PDF = $(ADVENTURE_TEX:.tex=.pdf)

   .PHONY: all tex pdf clean

   all: pdf

   tex: $(ADVENTURE_TEX)

   pdf: $(ADVENTURE_PDF)

   output/adventures/%.tex: data/adventure/%.json
   	@mkdir -p output/adventures
   	5e2pdf convert adventure $< \
   		--output $@ \
   		--images \
   		--title "$(shell basename $< .json | tr '-' ' ' | sed 's/\b\w/\u&/g')"

   output/adventures/%.pdf: output/adventures/%.tex
   	cd output/adventures && xelatex $(notdir $<)
   	
   clean:
   	rm -rf output/

Troubleshooting Legacy Issues
----------------------------

Common Migration Problems
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: "Command not found"**

.. code-block:: bash

   # Error
   bash: json2tex.py: command not found

   # Solution: Update script paths
   # Old: python json2tex.py
   # New: 5e2pdf legacy

**Problem: "Different output format"**

The modern system may produce slightly different LaTeX due to improvements. To get exact legacy output:

.. code-block:: bash

   # Use legacy mode for identical output
   5e2pdf legacy --adventure input.json > output.tex

**Problem: "Missing dependencies"**

.. code-block:: bash

   # Install all dependencies
   pip install 5e2pdf[legacy]

**Problem: "Performance differences"**

The modern system is generally faster due to caching, but initial runs may be slower as caches are built.

Legacy Code Reference
---------------------

Key Legacy Functions
~~~~~~~~~~~~~~~~~~~

For developers maintaining legacy compatibility, here are the key original functions and their modern equivalents:

**JSON Loading:**

.. code-block:: python

   # Legacy
   def load_json_file(filename):
       with open(filename, 'r') as f:
           return json.load(f)

   # Modern equivalent
   from src.core.loaders.json_loader import JSONLoader
   loader = JSONLoader()
   data = loader.load_file(filename)

**Adventure Processing:**

.. code-block:: python

   # Legacy
   def process_adventure(data):
       # Direct processing without validation
       return generate_adventure_latex(data)

   # Modern equivalent  
   from src.core.models.adventures import Adventure
   from src.renderers.latex.document import LaTeXDocumentRenderer
   
   adventure = Adventure.model_validate(data)
   renderer = LaTeXDocumentRenderer()
   return renderer.render_document([adventure], context)

**Tag Resolution:**

.. code-block:: python

   # Legacy
   def resolve_tags(text):
       # Basic regex replacement
       return re.sub(r'\{@(\w+) ([^}]+)\}', r'\\textbf{\2}', text)

   # Modern equivalent
   from src.core.indexer.tag_resolver import TagResolver
   
   resolver = TagResolver(omnidexer)
   return resolver.resolve_tags(text)

Deprecated Features
~~~~~~~~~~~~~~~~~~

Some legacy features are no longer supported in modern mode:

- **Global configuration variables**: Use configuration files instead
- **Direct LaTeX manipulation**: Use the rendering system
- **Hardcoded paths**: Use configurable data paths
- **Silent error handling**: Modern system provides detailed error messages

Future Considerations
--------------------

Legacy Support Timeline
~~~~~~~~~~~~~~~~~~~~~~

- **Phase 1** (Current): Full legacy compatibility maintained
- **Phase 2** (Future): Legacy mode marked as deprecated with warnings
- **Phase 3** (Future): Legacy mode requires explicit flag to enable
- **Phase 4** (Future): Legacy mode removed (major version bump)

Migration Assistance
~~~~~~~~~~~~~~~~~~~

Tools to help with migration:

.. code-block:: bash

   # Check compatibility
   5e2pdf legacy --check-compatibility script.sh

   # Generate modern equivalents
   5e2pdf legacy --migrate script.sh > modern-script.sh

   # Compare outputs
   5e2pdf legacy --compare-output old.json new.json

This ensures a smooth transition path for all users while encouraging adoption of the modern, more maintainable architecture.