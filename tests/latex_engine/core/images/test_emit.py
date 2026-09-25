"""Tests for emit.py through the entry renderer: 5etools images to macros."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from studiorum.latex_engine.core.images.resolve import ImageResolver
from studiorum.latex_engine.entries import EntryRenderer


@pytest.fixture
def renderer(tmp_path: Path) -> EntryRenderer:
    img = tmp_path / "5etools-img"
    for name in ("Sword Coast.webp", "Player.webp", "Barkskin.webp"):
        (img / "adventure").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 2)).save(img / "adventure" / name, "WEBP")
    return EntryRenderer(images=ImageResolver(img, tmp_path / "c"))


def render(
    renderer: EntryRenderer, entry: dict[str, Any], include_images: bool = True
) -> str:
    renderer.style = replace(renderer.style, images=include_images)
    return renderer.entry(entry).strip()


def href(name: str) -> dict[str, str]:
    return {"type": "internal", "path": f"adventure/{name}"}


def test_image_becomes_inline_macro_with_converted_png(
    renderer: EntryRenderer,
) -> None:
    out = render(
        renderer,
        {"type": "image", "href": href("Barkskin.webp"), "title": "Bark & Skin"},
    )

    assert out.startswith("\\StudiorumImageInline{")
    assert out.endswith(".png}{Bark \\& Skin}")
    assert "webp" not in out


def test_map_becomes_wide(renderer: EntryRenderer) -> None:
    entry = {"type": "image", "href": href("Sword Coast.webp"), "imageType": "map"}
    assert render(renderer, entry).startswith("\\StudiorumImageWide*{")


def test_label_only_from_id(renderer: EntryRenderer) -> None:
    entry = {"type": "image", "href": href("Player.webp"), "title": "Map", "id": "0a1"}
    assert render(renderer, entry).endswith("{Map}[fig:0a1]")


def test_missing_image_is_a_comment(renderer: EntryRenderer) -> None:
    entry = {"type": "image", "href": href("Gone.webp"), "title": "Gone"}
    assert render(renderer, entry) == "% Image not found: adventure/Gone.webp"


def test_images_off_keeps_placeholders(renderer: EntryRenderer) -> None:
    image = {"type": "image", "href": href("Player.webp"), "title": "Dungeon Map"}
    gallery = {"type": "gallery", "images": [image]}
    assert (
        render(renderer, image, include_images=False)
        == "% Image placeholder: Dungeon Map"
    )
    assert render(renderer, gallery, include_images=False) == "% Gallery placeholder"


def test_gallery_is_a_grid_skipping_missing(renderer: EntryRenderer) -> None:
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
    out = render(renderer, gallery)

    assert out.startswith("% Image not found: adventure/Gone.webp\n\\begin{figure}")
    assert out.count("\\begin{subfigure}{0.48\\linewidth}") == 2
    assert "\\caption{Player Version}" in out
    assert "\\hfill" in out
    assert out.endswith("\\end{figure}")


def test_caption_tags_are_resolved(renderer: EntryRenderer) -> None:
    entry = {
        "type": "image",
        "href": href("Player.webp"),
        "title": "Laylee may not handle {@creature Myla|DoSI}'s fire.",
    }

    assert render(renderer, entry).endswith(
        "{Laylee may not handle \\textbf{Myla}'s fire.}"
    )
