"""Pydantic models for character classes."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from .content import BaseContent, ContentType

if TYPE_CHECKING:
    from ..interfaces import DeepIndexable


class ClassFeature(BaseContent):
    """A feature for a character class."""

    # Core identification fields
    class_name: str = Field(..., alias="className")
    class_source: str = Field(..., alias="classSource")
    level: int

    # Optional detailed fields (from the separate classFeature definitions)
    page: int | None = None
    entries: list[Any] = Field(default_factory=list)
    header: int | None = None
    srd: bool | None = None
    basic_rules: bool | None = Field(default=None, alias="basicRules")


class SubclassFeature(BaseContent):
    """A feature for a character subclass."""

    # Core identification fields
    class_name: str = Field(..., alias="className")
    class_source: str = Field(..., alias="classSource")
    subclass_short_name: str = Field(..., alias="subclassShortName")
    subclass_source: str = Field(..., alias="subclassSource")
    level: int

    # Optional detailed fields
    page: int | None = None
    entries: list[Any] = Field(default_factory=list)
    header: int | None = None
    srd: bool | None = None
    basic_rules: bool | None = Field(default=None, alias="basicRules")


class Subclass(BaseModel):
    """A subclass for a character."""

    name: str
    short_name: str = Field(..., alias="shortName")
    source: str
    class_name: str = Field(..., alias="className")
    class_source: str = Field(..., alias="classSource")
    subclass_features: list[str] = Field(..., alias="subclassFeatures")


class Class(BaseContent):
    """A character class."""

    # Core fields - optional for sidekicks
    hd: dict[str, int] | None = None
    proficiency: list[str] | None = None
    class_features: list[Any] | None = Field(default=None, alias="classFeatures")

    # Sidekick identification
    is_sidekick: bool | None = Field(default=None, alias="isSidekick")

    # Optional fields
    spellcasting_ability: str | None = Field(default=None, alias="spellcastingAbility")
    caster_progression: str | None = Field(default=None, alias="casterProgression")
    cantrip_progression: list[int] | None = Field(
        default=None, alias="cantripProgression"
    )
    spells_known_progression: list[int] | None = Field(
        default=None, alias="spellsKnownProgression"
    )
    starting_proficiencies: dict[str, Any] | None = Field(
        default=None, alias="startingProficiencies"
    )
    starting_equipment: dict[str, Any] | None = Field(
        default=None, alias="startingEquipment"
    )
    multiclassing: dict[str, Any] | None = None
    subclasses: list[Subclass] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields_for_regular_classes(self) -> "Class":
        """Validate that required fields are present for regular (non-sidekick) classes."""
        # If this is not a sidekick class, certain fields are required
        if not self.is_sidekick:
            missing_fields = []
            if self.hd is None:
                missing_fields.append("hd")
            if self.proficiency is None:
                missing_fields.append("proficiency")
            if self.class_features is None:
                missing_fields.append("classFeatures")

            if missing_fields:
                raise ValueError(
                    f"Regular classes require these fields: {', '.join(missing_fields)}"
                )

        return self

    def get_deep_index_entries(self, omnidexer: Any) -> list[BaseContent]:
        """Return class features and subclass features for deep indexing."""
        from ..interfaces import DeepIndexable

        nested_content: list[BaseContent] = []

        # Parse class features from the classFeatures array
        if self.class_features:
            for feature_ref in self.class_features:
                if isinstance(feature_ref, str):
                    # Parse string format: "FeatureName|ClassName||Level" or "FeatureName|ClassName||Level|Source"
                    feature = self._parse_class_feature_reference(feature_ref)
                    if feature:
                        nested_content.append(feature)
                elif isinstance(feature_ref, dict) and feature_ref.get(
                    "gainSubclassFeature"
                ):
                    # This is a subclass feature marker, parse it as a class feature
                    class_feature_ref = feature_ref.get("classFeature", "")
                    if class_feature_ref:
                        feature = self._parse_class_feature_reference(class_feature_ref)
                        if feature:
                            nested_content.append(feature)

        # Parse subclass features from each subclass
        for subclass in self.subclasses:
            for feature_ref in subclass.subclass_features:
                # Parse subclass feature format: "FeatureName|ClassName||SubclassName||Level"
                subclass_feature = self._parse_subclass_feature_reference(
                    feature_ref, subclass
                )
                if subclass_feature:
                    nested_content.append(subclass_feature)

        return nested_content

    def _parse_class_feature_reference(self, feature_ref: str) -> ClassFeature | None:
        """Parse a class feature reference string into a ClassFeature object."""
        try:
            # Format: "FeatureName|ClassName||Level" or "FeatureName|ClassName||Level|Source"
            parts = feature_ref.split("|")
            if len(parts) < 4:
                return None

            feature_name = parts[0]
            class_name = parts[1]
            # parts[2] is empty (double pipe separator)
            level_str = parts[3]
            source_abbrev = parts[4] if len(parts) > 4 else self.source.abbreviation

            try:
                level = int(level_str)
            except ValueError:
                return None

            return ClassFeature(
                name=feature_name,
                source={"abbreviation": source_abbrev, "name": source_abbrev},
                className=class_name,
                classSource=self.source.abbreviation,
                level=level,
            )
        except (IndexError, ValueError):
            return None

    def _parse_subclass_feature_reference(
        self, feature_ref: str, subclass: Subclass
    ) -> SubclassFeature | None:
        """Parse a subclass feature reference string into a SubclassFeature object."""
        try:
            # Format: "FeatureName|ClassName||SubclassName||Level"
            parts = feature_ref.split("|")
            if len(parts) < 5:
                return None

            feature_name = parts[0]
            class_name = parts[1]
            # parts[2] is empty (double pipe separator)
            # parts[3] is subclass_name (not used directly, taken from subclass parameter)
            # parts[4] is empty (double pipe separator)
            level_str = parts[5] if len(parts) > 5 else ""

            try:
                level = int(level_str)
            except ValueError:
                return None

            return SubclassFeature(
                name=feature_name,
                source={"abbreviation": subclass.source, "name": subclass.source},
                className=class_name,
                classSource=self.source.abbreviation,
                subclassShortName=subclass.short_name,
                subclassSource=subclass.source,
                level=level,
            )
        except (IndexError, ValueError):
            return None
