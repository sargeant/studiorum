"""Fluff content models for liberal parsing of descriptive content."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from studiorum.core.logging import get_logger

from ..registry import content_type
from .content import BaseContent

logger = get_logger(__name__)


class FluffImage(BaseModel):
    """Represents an image in fluff content."""

    type: str = "image"
    href: dict[str, Any] | None = None
    credit: str | None = None

    def get_path(self) -> str | None:
        """Extract image path from nested structure."""
        if self.href and isinstance(self.href, dict):
            return self.href.get("path")
        return None


class FluffEntry(BaseModel):
    """Liberal model for fluff text entries."""

    model_config = ConfigDict(extra="allow")

    # Accept any structure - we'll extract text liberally
    content: str | dict[str, Any] | list[Any] = Field(default="")
    type: str | None = None
    name: str | None = None
    entries: str | dict[str, Any] | list[Any] | None = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        """Post-process content after model initialization."""
        # If entries field has content but content is empty, use entries
        if self.entries is not None and not self.content:
            self.content = self._extract_text_from_entries(self.entries)
        # If content is still empty/default and we got string data, use it directly
        elif not self.content and hasattr(self, "_raw_data"):
            self.content = self._raw_data

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v: Any) -> str:
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
                return str(v["text"])
        return str(v) if v else ""

    @staticmethod
    def _extract_text_from_entries(entries: Any) -> str:
        """Recursively extract text from nested entries."""
        text_parts = []
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, str):
                    text_parts.append(entry)
                elif isinstance(entry, dict):
                    # Handle structured dict entries (current 5etools format)
                    if "entries" in entry:
                        nested = FluffEntry._extract_text_from_entries(entry["entries"])
                        if nested:
                            text_parts.append(nested)
                    elif "text" in entry:
                        text_parts.append(entry["text"])
        elif isinstance(entries, str):
            text_parts.append(entries)
        return " ".join(text_parts)


@content_type(
    enum_value="fluff",
    file_patterns=["fluff"],
    statblock_tags=["fluff"],
    loader_type="fluff",
)
class BaseFluff(BaseContent):
    """Base fluff content with liberal parsing."""

    entries: list[FluffEntry] = Field(default_factory=list)
    images: list[FluffImage] = Field(default_factory=list)

    # Additional fields that might be present
    extra_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, v: Any) -> list[Any]:
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
                            fluff_entry = FluffEntry(
                                entries=entry["entries"],
                                **{k: v for k, v in entry.items() if k != "entries"},
                            )
                        else:
                            fluff_entry = FluffEntry(**entry)
                        parsed_entries.append(fluff_entry)
                    else:
                        # Treat as raw content - set content directly
                        parsed_entries.append(FluffEntry(content=str(entry)))
                except (ValidationError, TypeError, KeyError) as e:
                    logger.debug(f"Skipping invalid fluff entry: {entry} - {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error parsing fluff entry {entry}: {e}")
                    continue
            return parsed_entries
        else:
            # Single entry
            try:
                return [FluffEntry(content=v)]
            except (ValidationError, TypeError) as e:
                logger.debug(f"Failed to parse single fluff entry '{v}': {e}")
                return []

    @field_validator("images", mode="before")
    @classmethod
    def parse_images(cls, v: Any) -> list[Any]:
        """Liberal parsing of images field."""
        if not v:
            return []

        if isinstance(v, list):
            parsed_images = []
            for img in v:
                try:
                    if isinstance(img, dict):
                        parsed_images.append(FluffImage(**img))
                except (ValidationError, TypeError, KeyError) as e:
                    logger.debug(f"Skipping invalid image entry: {img} - {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error parsing image {img}: {e}")
                    continue
            return parsed_images
        return []

    def get_text(self) -> str:
        """Extract all descriptive text from entries using modern APIs."""
        text_parts = []
        for entry in self.entries:
            if entry.content:
                text_parts.append(str(entry.content))
        return "\n\n".join(text_parts)

    # Legacy method get_description_text removed - access .entries directly and use RecursiveEntryProcessor

    def get_image_paths(self) -> list[str]:
        """Get all image paths."""
        paths = []
        for img in self.images:
            path = img.get_path()
            if path:
                paths.append(path)
        return paths


@content_type(
    enum_value="spellFluff",
    file_patterns=[
        "spellFluff",
        "spell-fluff",
        "fluff-spell",
        "fluff-spells",
        "spells",
    ],
    statblock_tags=["spellFluff"],
    loader_type="fluff",
)
class SpellFluff(BaseFluff):
    """Fluff content specific to spells."""

    pass


@content_type(
    enum_value="creatureFluff",
    file_patterns=["fluff-bestiary", "creatureFluff", "creature-fluff"],
    statblock_tags=["creatureFluff"],
    loader_type="fluff",
)
class CreatureFluff(BaseFluff):
    """Fluff content specific to creatures/monsters."""

    pass


@content_type(
    enum_value="itemFluff",
    file_patterns=["fluff-items", "itemFluff", "item-fluff"],
    statblock_tags=["itemFluff"],
    loader_type="fluff",
)
class ItemFluff(BaseFluff):
    """Fluff content specific to items."""

    pass


@content_type(
    enum_value="raceFluff",
    file_patterns=["fluff-races", "raceFluff", "race-fluff"],
    statblock_tags=["raceFluff"],
    loader_type="fluff",
)
class RaceFluff(BaseFluff):
    """Fluff content specific to races."""

    pass


@content_type(
    enum_value="featFluff",
    file_patterns=["fluff-feats", "featFluff", "feat-fluff"],
    statblock_tags=["featFluff"],
    loader_type="fluff",
)
class FeatFluff(BaseFluff):
    """Fluff content specific to feats."""

    pass


@content_type(
    enum_value="classFluff",
    file_patterns=["fluff-class", "classFluff", "class-fluff"],
    statblock_tags=["classFluff"],
    loader_type="fluff",
)
class ClassFluff(BaseFluff):
    """Fluff content specific to classes."""

    pass


@content_type(
    enum_value="backgroundFluff",
    file_patterns=[
        "fluff-backgrounds",
        "backgroundFluff",
        "background-fluff",
    ],
    statblock_tags=["backgroundFluff"],
    loader_type="fluff",
)
class BackgroundFluff(BaseFluff):
    """Fluff content specific to backgrounds."""

    pass


@content_type(
    enum_value="optionalfeatureFluff",
    file_patterns=[
        "optionalfeatureFluff",
        "optionalfeature-fluff",
        "fluff-optionalfeatures",
    ],
    statblock_tags=["optionalfeatureFluff"],
    loader_type="fluff",
)
class OptionalFeatureFluff(BaseFluff):
    """Fluff content specific to optional features."""

    pass


@content_type(
    enum_value="vehicleFluff",
    file_patterns=["vehicleFluff", "vehicle-fluff", "fluff-vehicles"],
    statblock_tags=["vehicleFluff"],
    loader_type="fluff",
)
class VehicleFluff(BaseFluff):
    """Fluff content specific to vehicles."""

    pass


@content_type(
    enum_value="objectFluff",
    file_patterns=["objectFluff", "object-fluff", "fluff-objects"],
    statblock_tags=["objectFluff"],
    loader_type="fluff",
)
class ObjectFluff(BaseFluff):
    """Fluff content specific to objects."""

    pass


@content_type(
    enum_value="languageFluff",
    file_patterns=["languageFluff", "language-fluff", "fluff-languages"],
    statblock_tags=["languageFluff"],
    loader_type="fluff",
)
class LanguageFluff(BaseFluff):
    """Fluff content specific to languages."""

    pass


@content_type(
    enum_value="rewardFluff",
    file_patterns=["rewardFluff", "reward-fluff", "fluff-rewards"],
    statblock_tags=["rewardFluff"],
    loader_type="fluff",
)
class RewardFluff(BaseFluff):
    """Fluff content specific to rewards."""

    pass


@content_type(
    enum_value="conditionDiseaseFluff",
    file_patterns=[
        "conditionDiseaseFluff",
        "condition-disease-fluff",
        "fluff-conditionsdiseases",
    ],
    statblock_tags=["conditionDiseaseFluff"],
    loader_type="fluff",
)
class ConditionDiseaseFluff(BaseFluff):
    """Fluff content specific to conditions and diseases."""

    pass


@content_type(
    enum_value="trapHazardFluff",
    file_patterns=["trapHazardFluff", "trap-hazard-fluff", "fluff-trapshazards"],
    statblock_tags=["trapHazardFluff"],
    loader_type="fluff",
)
class TrapHazardFluff(BaseFluff):
    """Fluff content specific to traps and hazards."""

    pass


@content_type(
    enum_value="bastionFluff",
    file_patterns=["bastionFluff", "bastion-fluff", "fluff-bastions"],
    statblock_tags=["bastionFluff"],
    loader_type="fluff",
)
class BastionFluff(BaseFluff):
    """Fluff content specific to bastions."""

    pass


@content_type(
    enum_value="recipeFluff",
    file_patterns=["recipeFluff", "recipe-fluff", "fluff-recipes"],
    statblock_tags=["recipeFluff"],
    loader_type="fluff",
)
class RecipeFluff(BaseFluff):
    """Fluff content specific to recipes."""

    pass


@content_type(
    enum_value="charoptionFluff",
    file_patterns=["charoptionFluff", "charoption-fluff", "fluff-charcreationoptions"],
    statblock_tags=["charoptionFluff"],
    loader_type="fluff",
)
class CharoptionFluff(BaseFluff):
    """Fluff content specific to character creation options."""

    pass
