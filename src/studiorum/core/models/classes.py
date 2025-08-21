"""Pydantic models for character classes."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from ..registry import content_type
from .content import BaseContent, Source
from .entry_types import Entry

if TYPE_CHECKING:
    pass


class SkillChoice(BaseModel):
    """Skill choice selection for starting proficiencies."""

    choose: dict[str, Any] | None = Field(None, description="Choice structure")
    any: int | None = Field(None, description="Number of any skills to choose")


class StartingProficiencies(BaseModel):
    """Starting proficiencies for a character class."""

    armor: list[str | dict[str, Any]] | None = Field(
        None, description="Armor proficiencies"
    )
    weapons: list[str | dict[str, Any]] | None = Field(
        None, description="Weapon proficiencies"
    )
    tools: list[str] | None = Field(None, description="Tool proficiencies")
    skills: list[str | SkillChoice] | None = Field(
        None, description="Skill proficiencies or choices"
    )
    saves: list[str] | None = Field(None, description="Saving throw proficiencies")
    languages: list[str] | None = Field(None, description="Language proficiencies")


class EquipmentOption(BaseModel):
    """Equipment option choice structure."""

    a: list[str | dict[str, Any]] | None = Field(None, description="Option A items")
    b: list[str | dict[str, Any]] | None = Field(None, description="Option B items")
    c: list[str | dict[str, Any]] | None = Field(None, description="Option C items")
    d: list[str | dict[str, Any]] | None = Field(None, description="Option D items")


class StartingEquipment(BaseModel):
    """Starting equipment for a character class."""

    additional_from_background: bool | None = Field(
        None,
        alias="additionalFromBackground",
        description="Gets additional equipment from background",
    )
    default: list[str] | None = Field(
        None, description="Default equipment descriptions"
    )
    default_data: list[EquipmentOption] | None = Field(
        None, alias="defaultData", description="Structured equipment options"
    )
    gold_alternative: str | None = Field(
        None,
        alias="goldAlternative",
        description="Gold alternative for buying equipment",
    )


class MulticlassingRequirements(BaseModel):
    """Multiclassing ability score requirements."""

    strength: int | None = Field(None, alias="str", description="Strength requirement")
    dexterity: int | None = Field(
        None, alias="dex", description="Dexterity requirement"
    )
    constitution: int | None = Field(
        None, alias="con", description="Constitution requirement"
    )
    intelligence: int | None = Field(
        None, alias="int", description="Intelligence requirement"
    )
    wisdom: int | None = Field(None, alias="wis", description="Wisdom requirement")
    charisma: int | None = Field(None, alias="cha", description="Charisma requirement")
    # Support "or" requirements
    or_: list[dict[str, int]] | None = Field(
        None, alias="or", description="Alternative requirements"
    )


class MulticlassingProficiencies(BaseModel):
    """Proficiencies gained from multiclassing."""

    armor: list[str | dict[str, Any]] | None = Field(
        None, description="Armor proficiencies gained"
    )
    weapons: list[str | dict[str, Any]] | None = Field(
        None, description="Weapon proficiencies gained"
    )
    tools: list[str] | None = Field(None, description="Tool proficiencies gained")
    skills: list[str | SkillChoice] | None = Field(
        None, description="Skill proficiencies gained"
    )


class Multiclassing(BaseModel):
    """Multiclassing rules for a character class."""

    requirements: MulticlassingRequirements | None = Field(
        None, description="Ability score requirements for multiclassing"
    )
    proficiencies_gained: MulticlassingProficiencies | None = Field(
        None,
        alias="proficienciesGained",
        description="Proficiencies gained when multiclassing into this class",
    )
    spell_slot_level_div: int | None = Field(
        None,
        alias="spellSlotLevelDiv",
        description="Spell slot level divisor for multiclass spellcasting",
    )
    caster_progression: str | None = Field(
        None,
        alias="casterProgression",
        description="Caster progression type for multiclassing",
    )


@content_type(
    enum_value="classFeature",
    file_patterns=["classFeature", "classfeature"],
    statblock_tags=["classFeature"],
    loader_type="json",
)
class ClassFeature(BaseContent):
    """A feature for a character class."""

    # Core identification fields
    class_name: str = Field(..., alias="className")
    class_source: str = Field(..., alias="classSource")
    level: int

    # Optional detailed fields (from the separate classFeature definitions)
    page: int | None = None
    entries: list[Entry] = Field(default_factory=list)
    header: int | None = None
    srd: bool | None = None
    basic_rules: bool | None = Field(default=None, alias="basicRules")


@content_type(
    enum_value="subclassFeature",
    file_patterns=["subclassFeature", "subclassfeature"],
    statblock_tags=["subclassFeature"],
    loader_type="json",
)
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
    entries: list[Entry] = Field(default_factory=list)
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


@content_type(
    enum_value="class",
    file_patterns=["class", "classes"],
    statblock_tags=["class"],
    loader_type="json",
)
class Class(BaseContent):
    """A character class."""

    # Core fields - optional for sidekicks
    hd: dict[str, int] | None = None
    proficiency: list[str] | None = None
    class_features: list[str | dict[str, Any]] | None = Field(
        default=None, alias="classFeatures"
    )

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
    starting_proficiencies: StartingProficiencies | None = Field(
        default=None, alias="startingProficiencies"
    )
    starting_equipment: StartingEquipment | None = Field(
        default=None, alias="startingEquipment"
    )
    multiclassing: Multiclassing | None = None
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
                source=Source(abbreviation=source_abbrev, name=source_abbrev),
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
            if len(parts) < 6:
                return None

            feature_name = parts[0]
            class_name = parts[1]
            # parts[2] is empty (double pipe separator)
            # parts[3] is subclass_name (not used directly, taken from subclass parameter)
            # parts[4] is empty (double pipe separator)
            level_str = parts[5]

            try:
                level = int(level_str)
            except ValueError:
                return None

            return SubclassFeature(
                name=feature_name,
                source=Source(abbreviation=subclass.source, name=subclass.source),
                className=class_name,
                classSource=self.source.abbreviation,
                subclassShortName=subclass.short_name,
                subclassSource=subclass.source,
                level=level,
            )
        except (IndexError, ValueError):
            return None
