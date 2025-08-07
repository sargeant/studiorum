#!/usr/bin/env python3

"""Debug script to understand configuration issues."""

from unittest.mock import Mock, create_autospec

from dnd5e.core.indexer.content_tracker import ContentTracker
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.text.tag_ast import TagNode
from dnd5e.renderers.core.enhancers import LaTeXFormatEnhancer
from dnd5e.renderers.core.handlers import get_default_core_handlers
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.core.unified_renderer import StandardUnifiedRenderer


def main():
    """Debug the configuration and context issues."""
    # Create mock tag node
    node = Mock(spec=TagNode)
    node.tag_type = "creature"
    node.name = "Dragon"
    node.source = None
    node.page = None
    node.display_text = "Dragon"
    node.display_text_nodes = None

    # Set up context
    omnidexer = create_autospec(Omnidexer, spec_set=True)
    context = RenderingContext(output_format="latex", omnidexer=omnidexer, metadata={})

    print("=== Context Debug ===")
    print(f"Context metadata: {context.metadata}")
    print(f"Enhancement config: {context.metadata.get('enhancement_config')}")

    # Get core handler and extract content info
    core_handlers = get_default_core_handlers()
    creature_handler = None
    for handler in core_handlers:
        if handler.handles_tag_type("creature"):
            creature_handler = handler
            break

    content_info = creature_handler.extract_content_info(node, context)
    print(f"Content info: {content_info}")

    # Test LaTeX enhancer directly
    print("\n=== Direct LaTeX Enhancer Test ===")
    latex_enhancer = LaTeXFormatEnhancer()

    # Test with current context (should fail)
    result1 = latex_enhancer.enhance_content_reference(content_info, context)
    print(f"With current context: '{result1}'")

    # Test with proper config context
    print("\n=== Creating Unified Renderer ===")
    renderer = StandardUnifiedRenderer.create_latex_renderer(
        core_handlers,
        enable_hyperlinks=False,
        enable_content_tracking=False,
    )

    print(f"Renderer config: {renderer.config}")
    print(
        f"Config enable_latex_formatting: {getattr(renderer.config, 'enable_latex_formatting', 'NOT FOUND')}"
    )

    # Test with enhanced context from renderer
    print("\n=== Testing Enhanced Context ===")
    enhanced_context = renderer._create_enhanced_context(context)
    print(f"Enhanced metadata: {enhanced_context.metadata}")
    print(
        f"Enhancement config in enhanced context: {enhanced_context.metadata.get('enhancement_config')}"
    )

    if enhanced_context.metadata.get("enhancement_config"):
        config = enhanced_context.metadata.get("enhancement_config")
        print(
            f"Config enable_latex_formatting: {getattr(config, 'enable_latex_formatting', 'NOT FOUND')}"
        )

    # Test enhancer with enhanced context
    result2 = latex_enhancer.enhance_content_reference(content_info, enhanced_context)
    print(f"With enhanced context: '{result2}'")

    # Test unified renderer
    print("\n=== Full Unified Renderer ===")
    unified_result = renderer.render_tag(node, context)
    print(f"Unified result: '{unified_result}'")


if __name__ == "__main__":
    main()
