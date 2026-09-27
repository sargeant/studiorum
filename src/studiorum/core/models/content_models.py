"""The model class for each content type.

``CONTENT_MODELS`` is the one mapping from ``ContentType`` to the Pydantic
model that validates it. Adding a content type means adding the enum member
and a line here.
"""

from __future__ import annotations

from typing import Any

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.backgrounds import Background
from studiorum.core.models.baseitems import BaseItem
from studiorum.core.models.books import Book
from studiorum.core.models.charoption import CharacterOption
from studiorum.core.models.charoptiontype import CharacterOptionType
from studiorum.core.models.classes import Class, ClassFeature, SubclassFeature
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.creatures import Creature
from studiorum.core.models.cults import Boon, Cult
from studiorum.core.models.decks import Deck
from studiorum.core.models.deities import Deity
from studiorum.core.models.diseases import Disease
from studiorum.core.models.facilities import Facility
from studiorum.core.models.feats import Feat
from studiorum.core.models.fluff import (
    BackgroundFluff,
    BaseFluff,
    BastionFluff,
    CharoptionFluff,
    ClassFluff,
    ConditionDiseaseFluff,
    CreatureFluff,
    FeatFluff,
    ItemFluff,
    LanguageFluff,
    ObjectFluff,
    OptionalFeatureFluff,
    RaceFluff,
    RecipeFluff,
    RewardFluff,
    SpellFluff,
    TrapHazardFluff,
    VehicleFluff,
)
from studiorum.core.models.itemmastery import ItemMastery
from studiorum.core.models.itemproperties import ItemProperty
from studiorum.core.models.items import Item
from studiorum.core.models.languages import Language
from studiorum.core.models.legendarygroup import LegendaryGroup
from studiorum.core.models.magicvariant import MagicVariant
from studiorum.core.models.objects import Object
from studiorum.core.models.optional_features import OptionalFeature
from studiorum.core.models.psionic import Psionic
from studiorum.core.models.races import Race
from studiorum.core.models.recipes import Recipe
from studiorum.core.models.rewards import Reward
from studiorum.core.models.rule_types import Action, Condition, Hazard, Sense, Status
from studiorum.core.models.spells import Spell
from studiorum.core.models.subclasses import Subclass
from studiorum.core.models.subraces import Subrace
from studiorum.core.models.table import Table, TableGroup
from studiorum.core.models.traps import Trap
from studiorum.core.models.variantrule import VariantRule
from studiorum.core.models.vehicles import Vehicle, VehicleUpgrade

CONTENT_MODELS: dict[ContentType, type[BaseContent]] = {
    ContentType.ADVENTURE: Adventure,
    ContentType.BOOK: Book,
    ContentType.CREATURE: Creature,
    ContentType.ITEM: Item,
    ContentType.SPELL: Spell,
    ContentType.BACKGROUND: Background,
    ContentType.BASEITEM: BaseItem,
    ContentType.CHAROPTION: CharacterOption,
    ContentType.CHAROPTIONTYPE: CharacterOptionType,
    ContentType.CLASS_FEATURE: ClassFeature,
    ContentType.SUBCLASS_FEATURE: SubclassFeature,
    ContentType.CLASS: Class,
    ContentType.CULT: Cult,
    ContentType.BOON: Boon,
    ContentType.DECK: Deck,
    ContentType.DEITY: Deity,
    ContentType.DISEASE: Disease,
    ContentType.FACILITY: Facility,
    ContentType.FEAT: Feat,
    ContentType.FLUFF: BaseFluff,
    ContentType.SPELL_FLUFF: SpellFluff,
    ContentType.CREATURE_FLUFF: CreatureFluff,
    ContentType.ITEM_FLUFF: ItemFluff,
    ContentType.RACE_FLUFF: RaceFluff,
    ContentType.FEAT_FLUFF: FeatFluff,
    ContentType.CLASS_FLUFF: ClassFluff,
    ContentType.BACKGROUND_FLUFF: BackgroundFluff,
    ContentType.OPTIONALFEATURE_FLUFF: OptionalFeatureFluff,
    ContentType.VEHICLE_FLUFF: VehicleFluff,
    ContentType.OBJECT_FLUFF: ObjectFluff,
    ContentType.LANGUAGE_FLUFF: LanguageFluff,
    ContentType.REWARD_FLUFF: RewardFluff,
    ContentType.CONDITIONDISEASE_FLUFF: ConditionDiseaseFluff,
    ContentType.TRAPHAZARD_FLUFF: TrapHazardFluff,
    ContentType.BASTION_FLUFF: BastionFluff,
    ContentType.RECIPE_FLUFF: RecipeFluff,
    ContentType.CHAROPTION_FLUFF: CharoptionFluff,
    ContentType.ITEM_MASTERY: ItemMastery,
    ContentType.ITEM_PROPERTY: ItemProperty,
    ContentType.LEGENDARYGROUP: LegendaryGroup,
    ContentType.MAGICVARIANT: MagicVariant,
    ContentType.OBJECT: Object,
    ContentType.OPTIONALFEATURE: OptionalFeature,
    ContentType.PSIONIC: Psionic,
    ContentType.RACE: Race,
    ContentType.RECIPE: Recipe,
    ContentType.REWARD: Reward,
    ContentType.ACTION: Action,
    ContentType.CONDITION: Condition,
    ContentType.SENSE: Sense,
    ContentType.HAZARD: Hazard,
    ContentType.STATUS: Status,
    ContentType.SUBCLASS: Subclass,
    ContentType.SUBRACE: Subrace,
    ContentType.TABLE: Table,
    ContentType.TABLE_GROUP: TableGroup,
    ContentType.TRAP: Trap,
    ContentType.VARIANTRULE: VariantRule,
    ContentType.VEHICLE: Vehicle,
    ContentType.VEHICLE_UPGRADE: VehicleUpgrade,
    ContentType.LANGUAGE: Language,
}

FLUFF_TYPES: frozenset[ContentType] = frozenset(
    ct for ct, model in CONTENT_MODELS.items() if issubclass(model, BaseFluff)
)

_TYPE_BY_MODEL: dict[type[BaseContent], ContentType] = {
    model: ct for ct, model in CONTENT_MODELS.items()
}


def create_content(data: dict[str, Any], content_type: ContentType) -> BaseContent:
    """Validate ``data`` as ``content_type``'s model."""
    model = CONTENT_MODELS.get(content_type)
    if model is None:
        raise ValueError(f"Unsupported content type: {content_type}")
    return model.model_validate(data)


def content_type_of(content: BaseContent) -> ContentType:
    """The content type of ``content``, by its exact class, else its nearest base."""
    exact = _TYPE_BY_MODEL.get(type(content))
    if exact is not None:
        return exact
    for model, content_type in _TYPE_BY_MODEL.items():
        if isinstance(content, model):
            return content_type
    raise ValueError(f"Unknown content type for {type(content)}")


# The 5etools JSON property each content type is read from. Base items load as
# items, as they always have; bestiary templates and item types are read by the
# loader but not indexed.
PROP_TYPES: dict[str, ContentType] = {
    "adventure": ContentType.ADVENTURE,
    "book": ContentType.BOOK,
    "monster": ContentType.CREATURE,
    "item": ContentType.ITEM,
    "baseitem": ContentType.ITEM,
    "itemGroup": ContentType.ITEM,
    "spell": ContentType.SPELL,
    "background": ContentType.BACKGROUND,
    "charoption": ContentType.CHAROPTION,
    "classFeature": ContentType.CLASS_FEATURE,
    "subclassFeature": ContentType.SUBCLASS_FEATURE,
    "class": ContentType.CLASS,
    "subclass": ContentType.SUBCLASS,
    "cult": ContentType.CULT,
    "boon": ContentType.BOON,
    "deck": ContentType.DECK,
    "deity": ContentType.DEITY,
    "disease": ContentType.DISEASE,
    "facility": ContentType.FACILITY,
    "feat": ContentType.FEAT,
    "spellFluff": ContentType.SPELL_FLUFF,
    "monsterFluff": ContentType.CREATURE_FLUFF,
    "itemFluff": ContentType.ITEM_FLUFF,
    "raceFluff": ContentType.RACE_FLUFF,
    "featFluff": ContentType.FEAT_FLUFF,
    "classFluff": ContentType.CLASS_FLUFF,
    "backgroundFluff": ContentType.BACKGROUND_FLUFF,
    "optionalfeatureFluff": ContentType.OPTIONALFEATURE_FLUFF,
    "vehicleFluff": ContentType.VEHICLE_FLUFF,
    "objectFluff": ContentType.OBJECT_FLUFF,
    "languageFluff": ContentType.LANGUAGE_FLUFF,
    "rewardFluff": ContentType.REWARD_FLUFF,
    "conditionFluff": ContentType.CONDITIONDISEASE_FLUFF,
    "diseaseFluff": ContentType.CONDITIONDISEASE_FLUFF,
    "trapFluff": ContentType.TRAPHAZARD_FLUFF,
    "hazardFluff": ContentType.TRAPHAZARD_FLUFF,
    "facilityFluff": ContentType.BASTION_FLUFF,
    "recipeFluff": ContentType.RECIPE_FLUFF,
    "charoptionFluff": ContentType.CHAROPTION_FLUFF,
    "itemMastery": ContentType.ITEM_MASTERY,
    "itemProperty": ContentType.ITEM_PROPERTY,
    "legendaryGroup": ContentType.LEGENDARYGROUP,
    "magicvariant": ContentType.MAGICVARIANT,
    "object": ContentType.OBJECT,
    "optionalfeature": ContentType.OPTIONALFEATURE,
    "psionic": ContentType.PSIONIC,
    "race": ContentType.RACE,
    "subrace": ContentType.SUBRACE,
    "recipe": ContentType.RECIPE,
    "reward": ContentType.REWARD,
    "action": ContentType.ACTION,
    "condition": ContentType.CONDITION,
    "sense": ContentType.SENSE,
    "hazard": ContentType.HAZARD,
    "status": ContentType.STATUS,
    "table": ContentType.TABLE,
    "tableGroup": ContentType.TABLE_GROUP,
    "trap": ContentType.TRAP,
    "variantrule": ContentType.VARIANTRULE,
    "vehicle": ContentType.VEHICLE,
    "vehicleUpgrade": ContentType.VEHICLE_UPGRADE,
    "language": ContentType.LANGUAGE,
}

# What each 5etools tag names, and the source when it gives none: 5etools'
# Parser.TAG_TO_PROPS and each tag's defaultSource
TAG_TYPES: dict[str, tuple[ContentType, str]] = {
    "action": (ContentType.ACTION, "PHB"),
    "background": (ContentType.BACKGROUND, "PHB"),
    "charoption": (ContentType.CHAROPTION, "MOT"),
    "class": (ContentType.CLASS, "PHB"),
    "condition": (ContentType.CONDITION, "PHB"),
    "creature": (ContentType.CREATURE, "MM"),
    "deck": (ContentType.DECK, "DMG"),
    "deity": (ContentType.DEITY, "PHB"),
    "disease": (ContentType.DISEASE, "DMG"),
    "facility": (ContentType.FACILITY, "XDMG"),
    "feat": (ContentType.FEAT, "PHB"),
    "hazard": (ContentType.HAZARD, "DMG"),
    "item": (ContentType.ITEM, "DMG"),
    "language": (ContentType.LANGUAGE, "PHB"),
    "object": (ContentType.OBJECT, "DMG"),
    "optfeature": (ContentType.OPTIONALFEATURE, "PHB"),
    "race": (ContentType.RACE, "PHB"),
    "recipe": (ContentType.RECIPE, "HF"),
    "reward": (ContentType.REWARD, "DMG"),
    "sense": (ContentType.SENSE, "PHB"),
    "spell": (ContentType.SPELL, "PHB"),
    "status": (ContentType.STATUS, "PHB"),
    "subclass": (ContentType.SUBCLASS, "PHB"),
    "table": (ContentType.TABLE, "DMG"),
    "trap": (ContentType.TRAP, "DMG"),
    "variantrule": (ContentType.VARIANTRULE, "DMG"),
    "vehicle": (ContentType.VEHICLE, "GoS"),
    "vehupgrade": (ContentType.VEHICLE_UPGRADE, "GoS"),
}
