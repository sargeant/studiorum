"""5etools image and gallery entries to the Studiorum image macros.

The layout lives in ``_image_render_block.tex.j2`` and
``_gallery_render_block.tex.j2``; this module finds the files and fills them in.
``text`` turns a 5etools string (a caption, which may hold tags) into LaTeX.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import cache
from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from jinja2 import Template

    from studiorum.renderers.context import RenderingContext

    from .resolve import ImageResolver

logger = get_logger(__name__)

WIDE_IMAGE_TYPES = frozenset({"map", "mapPlayer"})


def image(
    entry: dict[str, Any],
    context: RenderingContext,
    resolver: ImageResolver,
    text: Callable[[str], str],
) -> str:
    """LaTeX for a 5etools ``image`` entry."""
    title = entry.get("title") or ""
    if not context.metadata.get("include_images", True) or not entry.get("href"):
        return f"% Image placeholder: {title}" if title else "% Image placeholder"
    path = resolver.resolve(entry.get("href"))
    if path is None:
        return f"% Image not found: {_describe(entry.get('href'))}"
    return _template("_image_render_block.tex.j2").render(
        path=path.as_posix(),
        caption=text(title) if title else "",
        label=_label(entry),
        placement="wide" if entry.get("imageType") in WIDE_IMAGE_TYPES else "inline",
    )


def gallery(
    entry: dict[str, Any],
    context: RenderingContext,
    resolver: ImageResolver,
    text: Callable[[str], str],
) -> str:
    """LaTeX for a 5etools ``gallery`` entry: a grid, skipping missing images."""
    if not context.metadata.get("include_images", True):
        title = entry.get("title", entry.get("caption", ""))
        return f"% Gallery placeholder: {title}" if title else "% Gallery placeholder"
    found: list[dict[str, str]] = []
    missing: list[str] = []
    for member in entry.get("images", []):
        path = resolver.resolve(member.get("href"))
        if path is None:
            missing.append(f"% Image not found: {_describe(member.get('href'))}")
        else:
            caption = member.get("title")
            found.append(
                {"path": path.as_posix(), "caption": text(caption) if caption else ""}
            )
    if not found:
        return "\n".join(missing) or "% Empty gallery"
    caption = entry.get("caption") or entry.get("title")
    grid = _template("_gallery_render_block.tex.j2").render(
        images=found, caption=text(caption) if caption else ""
    )
    return "\n".join([*missing, grid])


def _label(entry: dict[str, Any]) -> str | None:
    """A label only from the entry's own id, which 5etools keeps unique."""
    entry_id = entry.get("id")
    if not entry_id:
        return None
    return "fig:" + re.sub(r"[^A-Za-z0-9]+", "-", str(entry_id)).strip("-").lower()


def _describe(href: Any) -> str:
    if isinstance(href, dict):
        return str(href.get("path") or href.get("url") or href)
    return str(href)


@cache
def _template(name: str) -> Template:
    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    return LaTeXTemplateEngine().env.get_template(name)
