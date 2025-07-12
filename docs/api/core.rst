Core Components
===============

This section documents the core components of the 5e2pdf system.

Data Models
-----------

The core data models represent D&D content types and provide validation.

.. automodule:: src.core.models.content
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.models.spells
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.models.creatures
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.models.items
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.models.adventures
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.models.books
   :members:
   :undoc-members:
   :show-inheritance:

Loaders and Indexing
--------------------

The omnidexer system loads and indexes D&D content for efficient access.

.. automodule:: src.core.loaders.omnidexer
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.loaders.json_loader
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.loaders.source_manager
   :members:
   :undoc-members:
   :show-inheritance:

Tag Resolution
--------------

The tag resolver handles cross-references and inline content formatting.

.. automodule:: src.core.indexer.tag_resolver
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.indexer.reference_index
   :members:
   :undoc-members:
   :show-inheritance:

Caching System
--------------

Performance optimization through intelligent caching.

.. automodule:: src.core.cache
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
-------------

Configuration management and settings.

.. automodule:: src.core.config.settings
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.core.config.paths
   :members:
   :undoc-members:
   :show-inheritance: