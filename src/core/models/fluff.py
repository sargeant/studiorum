"""Fluff content models for liberal parsing of descriptive content."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class FluffImage(BaseModel):
    """Represents an image in fluff content."""

    type: str = "image"
    href: Optional[Dict[str, Any]] = None
    credit: Optional[str] = None

    def get_path(self) -> Optional[str]:
        """Extract image path from nested structure."""
        if self.href and isinstance(self.href, dict):
            return self.href.get("path")
        return None


class FluffEntry(BaseModel):
    """Liberal model for fluff text entries."""

    # Accept any structure - we'll extract text liberally
    content: Union[str, Dict[str, Any], List[Any]] = Field(default="")
    type: Optional[str] = None
    name: Optional[str] = None
    entries: Optional[Union[str, Dict[str, Any], List[Any]]] = Field(default=None)

    def model_post_init(self, __context):
        """Post-process content after model initialization."""
        # If entries field has content but content is empty, use entries
        if self.entries is not None and not self.content:
            self.content = self._extract_text_from_entries(self.entries)
        # If content is still empty/default and we got string data, use it directly
        elif not self.content and hasattr(self, '_raw_data'):
            self.content = self._raw_data

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v):
        """Extract text content from various structures."""
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            # Extract text from list of entries
            text_parts = []
            for item in v:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    # Try to extract text from nested structures
                    if "entries" in item:
                        nested_text = cls._extract_text_from_entries(item["entries"])
                        if nested_text:
                            text_parts.append(nested_text)
                    elif "text" in item:
                        text_parts.append(item["text"])
            return " ".join(text_parts)
        elif isinstance(v, dict):
            # Try to extract text from dict structure
            if "entries" in v:
                return cls._extract_text_from_entries(v["entries"])
            elif "text" in v:
                return v["text"]
        return str(v) if v else ""

    @staticmethod
    def _extract_text_from_entries(entries) -> str:
        """Recursively extract text from nested entries."""
        text_parts = []
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, str):
                    text_parts.append(entry)
                elif isinstance(entry, dict):
                    if "entries" in entry:
                        nested = FluffEntry._extract_text_from_entries(entry["entries"])
                        if nested:
                            text_parts.append(nested)
                    elif "text" in entry:
                        text_parts.append(entry["text"])
        elif isinstance(entries, str):
            text_parts.append(entries)
        return " ".join(text_parts)


class BaseFluff(BaseModel):
    """Base fluff content with liberal parsing."""

    name: str
    source: Union[str, Dict[str, str]]
    entries: List[FluffEntry] = Field(default_factory=list)
    images: List[FluffImage] = Field(default_factory=list)

    # Additional fields that might be present
    extra_data: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("source", mode="before")
    @classmethod
    def parse_source(cls, v):
        """Handle both string and dict source formats."""
        if isinstance(v, str):
            return {"abbreviation": v, "name": v}
        return v

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, v):
        """Liberal parsing of entries field."""
        if not v:
            return []

        if isinstance(v, list):
            parsed_entries = []
            for entry in v:
                try:
                    if isinstance(entry, dict):
                        # For dict entries, pass the entries field if it exists
                        if "entries" in entry:
                            fluff_entry = FluffEntry(entries=entry["entries"], **{k: v for k, v in entry.items() if k != "entries"})
                        else:
                            fluff_entry = FluffEntry(**entry)
                        parsed_entries.append(fluff_entry)
                    else:
                        # Treat as raw content - set content directly
                        parsed_entries.append(FluffEntry(content=str(entry)))
                except Exception:
                    # Skip invalid entries but keep going
                    continue
            return parsed_entries
        else:
            # Single entry
            try:
                return [FluffEntry(content=v)]
            except Exception:
                return []

    @field_validator("images", mode="before")
    @classmethod
    def parse_images(cls, v):
        """Liberal parsing of images field."""
        if not v:
            return []

        if isinstance(v, list):
            parsed_images = []
            for img in v:
                try:
                    if isinstance(img, dict):
                        parsed_images.append(FluffImage(**img))
                except Exception:
                    # Skip invalid images but keep going
                    continue
            return parsed_images
        return []

    def get_description_text(self) -> str:
        """Extract all descriptive text from entries."""
        text_parts = []
        for entry in self.entries:
            if entry.content:
                text_parts.append(str(entry.content))
        return "\n\n".join(text_parts)

    def get_image_paths(self) -> List[str]:
        """Get all image paths."""
        paths = []
        for img in self.images:
            path = img.get_path()
            if path:
                paths.append(path)
        return paths


class SpellFluff(BaseFluff):
    """Fluff content specific to spells."""

    pass


class CreatureFluff(BaseFluff):
    """Fluff content specific to creatures/monsters."""

    pass


class ItemFluff(BaseFluff):
    """Fluff content specific to items."""

    pass
