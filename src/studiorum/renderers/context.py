"""The context the entry processor and templates pass down while rendering."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RenderingContext(BaseModel):
    """Services and metadata for rendering entries and tags."""

    model_config = {"arbitrary_types_allowed": True}

    output_format: str = Field(description="Target output format (latex, html, etc)")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")

    omnidexer: Any = Field(default=None, description="Content indexer for validation")
    content_tracker: Any = Field(
        default=None, description="Tracks content for appendices"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )
