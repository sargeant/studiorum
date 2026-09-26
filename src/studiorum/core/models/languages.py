"""Languages."""

from typing import Any

from pydantic import Field

from .content import BaseContent


class Language(BaseContent):
    """A language: its kind, who speaks it and its script."""

    type: str | None = Field(None, description="standard, exotic, rare or secret")
    typical_speakers: list[str] | None = Field(None, alias="typicalSpeakers")
    origin: str | None = None
    script: str | None = None
    dialects: list[str] | None = None
    entries: list[Any] = Field(default_factory=list)
