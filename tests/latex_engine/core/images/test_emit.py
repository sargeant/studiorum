"""Tests for emit.py through the entry processor: 5etools images to macros."""

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.latex_engine.core.images.resolve import ImageResolver
from studiorum.renderers.context import RenderingContext


def context(include_images: bool = True) -> RenderingContext:
    return RenderingContext(
        output_format="latex",
        omnidexer=None,
        content_tracker=None,
        tag_resolver=None,
        metadata={"include_images": include_images},
    )


@pytest.fixture
def processor(tmp_path: Path) -> RecursiveEntryProcessor:
    img = tmp_path / "5etools-img"
    for name in ("Sword Coast.webp", "Player.webp", "Barkskin.webp"):
        (img / "adventure").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 2)).save(img / "adventure" / name, "WEBP")
    return RecursiveEntryProcessor(image_resolver=ImageResolver(img, tmp_path / "c"))


def render(processor: RecursiveEntryProcessor, entry: dict[str, Any], **kw: Any) -> str:
    return processor.process_entry_dict(entry, context(**kw)).strip()


def href(name: str) -> dict[str, str]:
    return {"type": "internal", "path": f"adventure/{name}"}


def test_image_becomes_inline_macro_with_converted_png(
    processor: RecursiveEntryProcessor,
) -> None:
    out = render(
        processor,
        {"type": "image", "href": href("Barkskin.webp"), "title": "Bark & Skin"},
    )

    assert out.startswith("\\StudiorumImageInline{")
    assert out.endswith(".png}{Bark \\& Skin}")
    assert "webp" not in out


def test_map_becomes_wide(processor: RecursiveEntryProcessor) -> None:
    entry = {"type": "image", "href": href("Sword Coast.webp"), "imageType": "map"}
    assert render(processor, entry).startswith("\\StudiorumImageWide*{")


def test_label_only_from_id(processor: RecursiveEntryProcessor) -> None:
    entry = {"type": "image", "href": href("Player.webp"), "title": "Map", "id": "0a1"}
    assert render(processor, entry).endswith("{Map}[fig:0a1]")


def test_missing_image_is_a_comment(processor: RecursiveEntryProcessor) -> None:
    entry = {"type": "image", "href": href("Gone.webp"), "title": "Gone"}
    assert render(processor, entry) == "% Image not found: adventure/Gone.webp"


def test_images_off_keeps_placeholders(processor: RecursiveEntryProcessor) -> None:
    image = {"type": "image", "href": href("Player.webp"), "title": "Dungeon Map"}
    gallery = {"type": "gallery", "images": [image]}
    assert (
        render(processor, image, include_images=False)
        == "% Image placeholder: Dungeon Map"
    )
    assert render(processor, gallery, include_images=False) == "% Gallery placeholder"


def test_gallery_is_a_grid_skipping_missing(processor: RecursiveEntryProcessor) -> None:
    gallery = {
        "type": "gallery",
        "images": [
            {
                "type": "image",
                "href": href("Sword Coast.webp"),
                "title": "The Sword Coast",
            },
            {"type": "image", "href": href("Player.webp"), "title": "Player Version"},
            {"type": "image", "href": href("Gone.webp")},
        ],
    }
    out = render(processor, gallery)

    assert out.startswith("% Image not found: adventure/Gone.webp\n\\begin{figure}")
    assert out.count("\\begin{subfigure}{0.48\\linewidth}") == 2
    assert "\\caption{Player Version}" in out
    assert "\\hfill" in out
    assert out.endswith("\\end{figure}")


def test_caption_tags_are_resolved(processor: RecursiveEntryProcessor) -> None:
    class Tags:
        def process_text(self, text: str, context: Any) -> str:
            return text.replace("{@creature Myla|DoSI}", "\\textbf{Myla}")

    ctx = RenderingContext(output_format="latex", tag_resolver=Tags())
    entry = {
        "type": "image",
        "href": href("Player.webp"),
        "title": "Laylee may not handle {@creature Myla|DoSI}'s fire.",
    }

    out = processor.process_entry_dict(entry, ctx).strip()

    assert out.endswith("{Laylee may not handle \\textbf{Myla}'s fire.}")
