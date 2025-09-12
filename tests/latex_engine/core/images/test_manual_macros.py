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


def test_emits_studiorum_image_macro_manual_mode() -> None:
    ctx = make_context(include_images=True, placement_mode="manual")
    proc = RecursiveEntryProcessor()
    img_entry = {
        "type": "image",
        "href": "images/dragon.png",
        "title": "Ancient Red Dragon",
    }

    out = proc.process_entry_dict(img_entry, ctx)

    assert "\\StudiorumImage" in out
    assert "StudiorumImage placement options" in out
    # Auto label should be derived from title
    assert "fig:ancient-red-dragon" in out


def test_macro_draft_flag_when_images_disabled() -> None:
    ctx = make_context(include_images=False, placement_mode="manual")
    proc = RecursiveEntryProcessor()
    img_entry = {"type": "image", "href": "images/map.png", "title": "Dungeon Map"}

    out = proc.process_entry_dict(img_entry, ctx)

    # Options should include draft=true
    assert (
        "[label=fig:dungeon-map,draft=true]" in out
        or "[draft=true,label=fig:dungeon-map]" in out
    )
