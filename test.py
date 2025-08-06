from dnd5e.core.loaders import Omnidexer
from dnd5e.renderers.latex import LaTeXDocumentRenderer

# Load D&D content
omnidexer = Omnidexer()
spells = omnidexer.find(content_type="spell", source="PHB")

# Render to LaTeX
renderer = LaTeXDocumentRenderer()
output = renderer.render_content(spells)
