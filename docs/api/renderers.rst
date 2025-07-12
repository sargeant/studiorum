Rendering System
================

This section documents the rendering system that converts D&D content to LaTeX.

Base Renderer Components
------------------------

Abstract base classes and interfaces for the rendering system.

.. automodule:: src.renderers.base.renderer
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.renderers.base.context
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.renderers.base.document
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.renderers.base.content
   :members:
   :undoc-members:
   :show-inheritance:

LaTeX Renderers
---------------

Concrete implementations for LaTeX document generation.

Document Renderer
~~~~~~~~~~~~~~~~~

The main document renderer that coordinates the entire rendering process.

.. automodule:: src.renderers.latex.document
   :members:
   :undoc-members:
   :show-inheritance:

Content Renderers
~~~~~~~~~~~~~~~~~

Specialized renderers for different types of D&D content.

.. automodule:: src.renderers.latex.content
   :members:
   :undoc-members:
   :show-inheritance:

Template System
~~~~~~~~~~~~~~~

LaTeX template management and customization.

.. automodule:: src.renderers.latex.templates
   :members:
   :undoc-members:
   :show-inheritance: