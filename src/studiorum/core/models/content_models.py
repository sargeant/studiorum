"""The model class for each content type.

``CONTENT_MODELS`` is the one mapping from ``ContentType`` to the Pydantic
model that validates it. Adding a content type means adding the enum member
and a line here.
"""

from __future__ import annotations

from typing import Any

from .adventures import Adventure
from .backgrounds import Background
from .baseitems import BaseItem
from .books import Book
from .charoption import CharacterOption
from .charoptiontype import CharacterOptionType
from .classes import Class, ClassFeature, SubclassFeature
from .content import BaseContent, ContentType
from .creatures import Creature
from .cults import Boon, Cult
from .decks import Deck
from .deities import Deity
from .diseases import Disease
from .facilities import Facility
from .feats import Feat
from .fluff import (
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
from .itemmastery import ItemMastery
from .itemproperties import ItemProperty
from .items import Item
from .legendarygroup import LegendaryGroup
from .magicvariant import MagicVariant
from .objects import Object
from .optional_features import OptionalFeature
from .psionic import Psionic
from .races import Race
from .recipes import Recipe
from .rewards import Reward
from .rule_types import Action, Condition, Hazard, Sense, Status
from .spells import Spell
from .subclasses import Subclass
from .subraces import Subrace
from .table import Table, TableGroup
from .traps import Trap
from .variantrule import VariantRule
from .vehicles import Vehicle

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
