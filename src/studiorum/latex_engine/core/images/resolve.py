"""Find the file for a 5etools image and make it one LaTeX can read.

5etools image paths are relative to a 5etools-img checkout, and every image
there is WebP, which no LaTeX engine reads. Anything that isn't PNG, JPEG or
PDF is converted to PNG once, into the cache directory, and scaled down to
MAX_WIDTH pixels (about 300 dpi across a letter page) since PNG is about ten
times the size of WebP. External URLs are downloaded into the cache first.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from studiorum.core.cache import cache_dir
from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.config.unified_config import ImageConfig
    from studiorum.core.models.creatures import Creature

logger = get_logger(__name__)

LATEX_READY = frozenset({".png", ".jpg", ".jpeg", ".pdf"})
MAX_WIDTH = 2400


@dataclass(frozen=True)
class ImageResolver:
    """Turns 5etools hrefs into paths for ``\\includegraphics``."""

    image_directory: Path | None
    cache_dir: Path

    @classmethod
    def from_config(cls, config: ImageConfig) -> ImageResolver:
        return cls(config.image_directory, config.cache_dir or cache_dir() / "images")

    def resolve(self, href: str | dict[str, Any] | None) -> Path | None:
        """A LaTeX-readable file for an href, or None if there is none.

        ``href`` is a 5etools href (``{"type": "internal", "path": ...}`` or
        ``{"type": "external", "url": ...}``) or a bare path or URL.
        """
        match href:
            case {"type": "external", "url": str(url)}:
                return self.fetch(url)
            case {"path": str(path)}:
                return self.find(path)
            case str() if href.startswith(("http://", "https://")):
                return self.fetch(href)
            case str() if href:
                return self.find(href)
        return None

    def find(self, path: str) -> Path | None:
        """The file for a path relative to the 5etools-img checkout."""
        if self.image_directory is None:
            return None
        source = self.image_directory / path
        if not source.is_file():
            logger.debug(f"Image not found: {source}")
            return None
        return self.latex_ready(source)

    def fetch(self, url: str) -> Path | None:
        """Download an external image into the cache, once."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"Not downloading {url}: only http and https are allowed")
            return None
        suffix = Path(parsed.path).suffix.lower() or ".img"
        target = self.cache_dir / "downloads" / f"{_digest(url)}{suffix}"
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            quoted = parsed._replace(
                path=urllib.parse.quote(urllib.parse.unquote(parsed.path))
            )
            try:
                # Only http and https reach here (checked above).
                with urllib.request.urlopen(quoted.geturl(), timeout=30) as response:  # nosec B310
                    data = response.read()
            except OSError as e:
                logger.warning(f"Could not download {url}: {e}")
                return None
            _write_atomically(target, data)
        return self.latex_ready(target)

    def latex_ready(self, source: Path) -> Path | None:
        """``source``, or a PNG copy of it in the cache if LaTeX can't read it."""
        if source.suffix.lower() in LATEX_READY:
            return source
        key = _digest(f"{source}@{MAX_WIDTH}")
        target = self.cache_dir / f"{_slug(source.stem)}-{key}.png"
        if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".partial")
        try:
            with Image.open(source) as image:
                alpha = "A" in image.getbands() or "transparency" in image.info
                png = image.convert("RGBA" if alpha else "RGB")
                if png.width > MAX_WIDTH:
                    height = round(png.height * MAX_WIDTH / png.width)
                    png = png.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
                png.save(partial, "PNG")
        except (OSError, Image.DecompressionBombError) as e:
            logger.warning(f"Could not convert {source} to PNG: {e}")
            partial.unlink(missing_ok=True)
            return None
        partial.replace(target)
        return target

    def token(self, creature: Creature) -> Path | None:
        """A creature's token, else its bestiary art, as a LaTeX-readable file."""
        return self.resolve(token_href(creature)) or self.find(
            f"bestiary/{creature.source.abbreviation}/{token_name(creature.name)}.webp"
        )


def token_href(creature: Creature) -> str | dict[str, Any]:
    """Where 5etools finds a creature's token (``Renderer.generic.getTokenUrl``)."""
    extra = creature.model_extra or {}
    if token := extra.get("token"):
        return f"bestiary/tokens/{token['source']}/{token_name(token['name'])}.webp"
    if token_ref := extra.get("tokenHref"):
        return dict(token_ref)
    source = creature.source.abbreviation
    return f"bestiary/tokens/{source}/{token_name(creature.name)}.webp"


def token_name(name: str) -> str:
    """5etools' ``Parser.nameToTokenName``: ASCII, without double quotes."""
    decomposed = unicodedata.normalize("NFD", name)
    ascii_name = re.sub("[̀-ͯ]", "", decomposed)
    return ascii_name.replace("Æ", "AE").replace("æ", "ae").replace('"', "")


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()[:10]


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", token_name(text)).strip("-") or "image"


def _write_atomically(target: Path, data: bytes) -> None:
    partial = target.with_suffix(target.suffix + ".partial")
    partial.write_bytes(data)
    partial.replace(target)
