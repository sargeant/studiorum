import re
from pathlib import Path

from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.renderers.core.interfaces import RenderingContext


def make_context(
    include_images: bool = True, placement_mode: str = "manual"
) -> RenderingContext:
    return RenderingContext(
        output_format="latex",
        debug_mode=False,
        omnidexer=None,
        content_tracker=None,
        tag_resolver=None,
        metadata={
            "include_images": include_images,
            "placement_mode": placement_mode,
            "layout_mode": "twocolumn",
        },
    )


def test_emits_simple_image_command_manual_mode() -> None:
    ctx = make_context(include_images=True, placement_mode="manual")
    proc = RecursiveEntryProcessor()
    img_entry = {
        "type": "image",
        "href": "images/dragon.png",
        "title": "Ancient Red Dragon",
    }

    out = proc.process_entry_dict(img_entry, ctx)

    # Should emit the new simple inline command and an auto-label comment
    assert "\\StudiorumImageInline" in out
    assert "Auto-generated label" in out
    # Auto label should be derived from title
    assert "fig:ancient-red-dragon" in out


def test_label_is_appended_when_present() -> None:
    ctx = make_context(include_images=False, placement_mode="manual")
    proc = RecursiveEntryProcessor()
    img_entry = {"type": "image", "href": "images/map.png", "title": "Dungeon Map"}

    out = proc.process_entry_dict(img_entry, ctx)

    # Label should appear as the optional trailing argument
    assert "]" in out and "[fig:dungeon-map]" in out
