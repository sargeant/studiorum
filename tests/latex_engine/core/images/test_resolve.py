"""Tests for resolve.py: finding 5etools images and making them LaTeX-readable."""

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from studiorum.core.models.creatures import Creature
from studiorum.latex_engine.core.images import resolve
from studiorum.latex_engine.core.images.resolve import (
    ImageResolver,
    token_href,
    token_name,
)


def write_image(path: Path, fmt: str = "WEBP", mode: str = "RGB") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    colour = (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0)
    Image.new(mode, (4, 2), colour).save(path, fmt)
    return path


@pytest.fixture
def resolver(tmp_path: Path) -> ImageResolver:
    return ImageResolver(tmp_path / "5etools-img", tmp_path / "cache")


def test_webp_converts_to_png_in_the_cache(resolver: ImageResolver) -> None:
    assert resolver.image_directory is not None
    write_image(resolver.image_directory / "adventure/LMoP/The Sword Coast.webp")

    found = resolver.resolve(
        {"type": "internal", "path": "adventure/LMoP/The Sword Coast.webp"}
    )

    assert found is not None
    assert found.parent == resolver.cache_dir
    assert found.name.startswith("The-Sword-Coast-")
    with Image.open(found) as image:
        assert image.format == "PNG"
        assert image.size == (4, 2)


def test_conversion_happens_once(resolver: ImageResolver) -> None:
    assert resolver.image_directory is not None
    write_image(resolver.image_directory / "a.webp")
    first = resolver.find("a.webp")
    assert first is not None
    mtime = first.stat().st_mtime_ns

    assert resolver.find("a.webp") == first
    assert first.stat().st_mtime_ns == mtime


def test_transparency_is_kept(resolver: ImageResolver) -> None:
    assert resolver.image_directory is not None
    write_image(resolver.image_directory / "token.webp", mode="RGBA")
    found = resolver.find("token.webp")
    assert found is not None
    with Image.open(found) as image:
        assert image.mode == "RGBA"


def test_wide_images_are_scaled_down(
    resolver: ImageResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert resolver.image_directory is not None
    monkeypatch.setattr(resolve, "MAX_WIDTH", 2)
    write_image(resolver.image_directory / "map.webp")
    found = resolver.find("map.webp")
    assert found is not None
    with Image.open(found) as image:
        assert image.size == (2, 1)


def test_png_is_used_in_place(resolver: ImageResolver) -> None:
    assert resolver.image_directory is not None
    source = write_image(resolver.image_directory / "map.png", fmt="PNG")
    assert resolver.find("map.png") == source


@pytest.mark.parametrize("href", [None, "", {"type": "internal"}, "missing.webp"])
def test_nothing_to_find(resolver: ImageResolver, href: Any) -> None:
    assert resolver.resolve(href) is None


def test_no_image_directory(tmp_path: Path) -> None:
    assert ImageResolver(None, tmp_path).find("a.webp") is None


def test_external_url_is_downloaded_once(
    resolver: ImageResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, "WEBP")
    requested: list[str] = []

    def urlopen(url: str, timeout: float) -> io.BytesIO:
        requested.append(url)
        return io.BytesIO(buffer.getvalue())

    monkeypatch.setattr(resolve.urllib.request, "urlopen", urlopen)
    href = {"type": "external", "url": "https://example.com/tokens/Big Bad.webp"}

    first = resolver.resolve(href)
    second = resolver.resolve(href)

    assert first is not None
    assert first == second
    assert first.suffix == ".png"
    assert requested == ["https://example.com/tokens/Big%20Bad.webp"]


def test_only_http_is_downloaded(resolver: ImageResolver) -> None:
    assert resolver.fetch("file:///etc/passwd") is None


def creature(**extra: Any) -> Creature:
    return Creature.model_validate(
        {
            "name": "Goblin",
            "source": "MM",
            "size": ["S"],
            "type": "humanoid",
            "ac": [15],
            "hp": {"average": 7, "formula": "2d6"},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 10,
            "wis": 8,
            "cha": 8,
            "cr": "1/4",
            **extra,
        }
    )


def test_token_href_follows_5etools() -> None:
    assert token_href(creature()) == "bestiary/tokens/MM/Goblin.webp"
    assert (
        token_href(creature(token={"name": "Goblin Boss", "source": "MPMM"}))
        == "bestiary/tokens/MPMM/Goblin Boss.webp"
    )
    external = {"type": "external", "url": "https://example.com/g.webp"}
    assert token_href(creature(tokenHref=external)) == external


def test_token_name_is_ascii_without_quotes() -> None:
    assert token_name('Æthelred "the" Méd') == "AEthelred the Med"
