#!/usr/bin/env python3

"""Debug script to understand enhancement pipeline issues."""

from unittest.mock import Mock, create_autospec

from dnd5e.core.indexer.content_tracker import ContentTracker
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.text.tag_ast import TagNode
from dnd5e.renderers.core.enhancers import create_latex_enhancement_pipeline
from dnd5e.renderers.core.handlers import get_default_core_handlers
from dnd5e.renderers.core.interfaces import EnhancementPipeline, RenderingContext
from dnd5e.renderers.core.unified_renderer import StandardUnifiedRenderer


def main():
    """Debug the enhancement pipeline step by step."""
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

    # Get core handler and extract content info
    core_handlers = get_default_core_handlers()
    creature_handler = None
    for handler in core_handlers:
        if handler.handles_tag_type("creature"):
            creature_handler = handler
            break

    print("=== Step 1: Core Handler ===")
    content_info = creature_handler.extract_content_info(node, context)
    print(f"Content info: {content_info}")
    print(f"Format style: {content_info.format_style}")
    print(f"Display text: '{content_info.display_text}'")

    print("\n=== Step 2: Create Enhancement Pipeline ===")
    enhancers = create_latex_enhancement_pipeline()
    print(f"Number of enhancers: {len(enhancers)}")
    for i, enhancer in enumerate(enhancers):
        print(
            f"  {i}: {type(enhancer).__name__} (priority: {enhancer.get_enhancement_priority()})"
        )

    pipeline = EnhancementPipeline(enhancers)
    print(f"Pipeline enhancers: {len(pipeline.enhancers)}")

    print("\n=== Step 3: Test Each Enhancer ===")
    result = content_info.display_text
    print(f"Starting result: '{result}'")

    for i, enhancer in enumerate(pipeline.enhancers):
        print(f"\n--- Enhancer {i}: {type(enhancer).__name__} ---")
        try:
            enhanced = enhancer.enhance_content_reference(content_info, context)
            print(f"Enhanced result: '{enhanced}'")
            print(f"Truthy: {bool(enhanced)}")
            if enhanced:
                result = enhanced
                print(f"Updated result: '{result}'")
            else:
                print("Not applied (falsy result)")
        except Exception as e:
            print(f"Error: {e}")

    print("\n=== Final Result ===")
    print(f"Final result: '{result}'")

    # Now test the full pipeline
    print("\n=== Full Pipeline Test ===")
    pipeline_result = pipeline.apply_enhancements(content_info, context)
    print(f"Pipeline result: '{pipeline_result}'")

    # Test with unified renderer
    print("\n=== Unified Renderer Test ===")
    renderer = StandardUnifiedRenderer.create_latex_renderer(
        core_handlers,
        enable_hyperlinks=False,
        enable_content_tracking=False,
    )
    unified_result = renderer.render_tag(node, context)
    print(f"Unified result: '{unified_result}'")


if __name__ == "__main__":
    main()
