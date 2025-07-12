"""JSON data loader with Pydantic validation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import ValidationError

from ..config.settings import get_logger
from ..models.content import ContentType
from .base import DataLoader, T

logger = get_logger(__name__)


class JsonDataLoader(DataLoader[T]):
    """Loads and validates JSON data using Pydantic models."""

    def __init__(self, model_class: Type[T], content_type: ContentType):
        self.model_class = model_class
        self.content_type = content_type

    async def load(self, path: Path) -> List[T]:
        """Load JSON file and validate against Pydantic model."""
        try:
            logger.info(f"Loading {self.content_type.value} data from {path}")

            # Read JSON file
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Extract content based on file structure
            content_list = self._extract_content(data, path)

            # Validate each item
            validated_content = []
            for item in content_list:
                try:
                    # Skip copy-template items that reference other content
                    if self._is_copy_template(item):
                        logger.debug(
                            f"Skipping copy-template item {item.get('name', 'unknown')} in {path}"
                        )
                        continue

                    # Ensure source information is present
                    item = self._ensure_source_info(item, path)

                    # Add missing required fields with reasonable defaults
                    item = self._add_missing_required_fields(item)

                    validated_item = self.model_class.model_validate(item)
                    validated_content.append(validated_item)
                except ValidationError as e:
                    logger.warning(
                        f"Validation failed for item {item.get('name', 'unknown')} in {path}: {e}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error validating item in {path}: {e}")

            logger.info(
                f"Successfully loaded {len(validated_content)} {self.content_type.value} items from {path}"
            )
            return validated_content

        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return []

    def get_content_type(self) -> ContentType:
        return self.content_type

    def get_model_class(self) -> Type[T]:
        return self.model_class

    def _extract_content(
        self, data: Dict[str, Any], path: Path
    ) -> List[Dict[str, Any]]:
        """Extract content list from various JSON structures."""
        # Handle different JSON structures from 5etools

        # Check if this is a Foundry VTT format file and skip it
        if self._is_foundry_file(path, data):
            logger.debug(f"Skipping Foundry VTT format file: {path}")
            return []

        # Check if this is a template file and skip it
        if self._is_template_file(path, data):
            logger.debug(f"Skipping template file: {path}")
            return []

        # Check if this is a fluff file and handle with liberal parsing
        if self._is_fluff_file(path, data):
            return self._extract_fluff_content(data, path)

        # Direct content arrays
        if self.content_type == ContentType.SPELL and "spell" in data:
            return data["spell"]
        elif self.content_type == ContentType.CREATURE and "monster" in data:
            return data["monster"]
        elif self.content_type == ContentType.ITEM and "item" in data:
            return data["item"]
        elif self.content_type == ContentType.ADVENTURE:
            if "adventure" in data:
                return data["adventure"]
            elif "adventureData" in data:
                # Handle adventure data format
                adventure_data = data["adventureData"]
                if isinstance(adventure_data, list) and adventure_data:
                    return adventure_data
            return []
        elif self.content_type == ContentType.BOOK:
            if "book" in data:
                return data["book"]
            elif "bookData" in data:
                # Handle book data format
                book_data = data["bookData"]
                if isinstance(book_data, list) and book_data:
                    return book_data
            return []
        elif self.content_type == ContentType.FEAT and "feat" in data:
            return data["feat"]
        elif self.content_type == ContentType.RACE and "race" in data:
            return data["race"]
        elif self.content_type == ContentType.BACKGROUND and "background" in data:
            return data["background"]
        elif self.content_type == ContentType.CLASS and "class" in data:
            return data["class"]

        # Generic fallbacks
        content_type_name = self.content_type.value
        if content_type_name in data:
            return data[content_type_name]

        # Try plural forms
        plural_name = content_type_name + "s"
        if plural_name in data:
            return data[plural_name]

        # If the data itself is a list, use it directly
        if isinstance(data, list):
            return data

        # Look for any list in the data as a fallback
        for key, value in data.items():
            if isinstance(value, list) and value:
                logger.debug(
                    f"Using '{key}' array as content for {self.content_type.value}"
                )
                return value

        logger.warning(f"No content found for {self.content_type.value} in {path}")
        return []

    def _ensure_source_info(self, item: Dict[str, Any], path: Path) -> Dict[str, Any]:
        """Ensure item has source information."""
        if "source" not in item:
            # Try to infer source from filename
            source_abbrev = self._infer_source_from_path(path)
            item["source"] = {
                "abbreviation": source_abbrev,
                "name": source_abbrev,  # Will be resolved later by source manager
            }
        elif isinstance(item["source"], str):
            # Convert string source to proper format
            source_abbrev = item["source"]
            item["source"] = {"abbreviation": source_abbrev, "name": source_abbrev}

        return item

    def _add_missing_required_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Add missing required fields with reasonable defaults."""
        # Handle missing fields for different content types
        if self.content_type == ContentType.CREATURE:
            # Add missing alignment field for creatures
            if "alignment" not in item:
                item["alignment"] = ["N"]  # Default to Neutral
                logger.debug(
                    f"Added default alignment for creature {item.get('name', 'unknown')}"
                )

        elif self.content_type == ContentType.ITEM:
            # Add missing type field for items
            if "type" not in item:
                item_type = self._infer_item_type(item)
                item["type"] = item_type
                logger.debug(
                    f"Added inferred type '{item_type}' for item {item.get('name', 'unknown')}"
                )

        return item

    def _infer_source_from_path(self, path: Path) -> str:
        """Infer source abbreviation from file path."""
        filename = path.stem.lower()

        # Common source patterns in filenames
        source_patterns = {
            "phb": "PHB",
            "mm": "MM",
            "dmg": "DMG",
            "scag": "SCAG",
            "vgm": "VGM",
            "xge": "XGE",
            "mtf": "MTF",
            "tce": "TCE",
            "cos": "CoS",
            "player": "PHB",
            "monster": "MM",
            "dungeon": "DMG",
        }

        for pattern, source in source_patterns.items():
            if pattern in filename:
                return source

        # Fallback: use filename as source
        return path.stem.upper()

    def _is_foundry_file(self, path: Path, data: Dict[str, Any]) -> bool:
        """Check if this is a Foundry VTT format file."""
        filename = path.name.lower()

        # Check filename patterns
        if "foundry" in filename:
            return True

        # Check for Foundry-specific data structure
        # Foundry files often have content with 'system', 'activities', or '_id' fields
        for content_array in data.values():
            if isinstance(content_array, list) and content_array:
                first_item = content_array[0]
                if isinstance(first_item, dict):
                    foundry_indicators = [
                        "system",
                        "activities",
                        "_id",
                        "migrationVersion",
                        "folder",
                    ]
                    if any(indicator in first_item for indicator in foundry_indicators):
                        return True

        return False

    def _is_template_file(self, path: Path, data: Dict[str, Any]) -> bool:
        """Check if this is a template file containing incomplete creature data."""
        filename = path.name.lower()

        # Only check filename patterns for explicit template markers
        if "template" in filename and "creature" in filename:
            return True

        # For creature files only, check if content looks like templates
        if self.content_type != ContentType.CREATURE:
            return False

        # Check if this file contains template-like data structures
        # Templates often have incomplete creature data or special markers
        for content_array in data.values():
            if isinstance(content_array, list) and content_array:
                # Check if ALL items in the array look like templates
                template_items = 0
                total_items = 0

                for item in content_array[:5]:  # Check first 5 items
                    if not isinstance(item, dict):
                        continue

                    total_items += 1

                    # Check for explicit template indicators
                    template_indicators = [
                        "template",
                        "inherit",
                        "_template",
                        "isTemplate",
                    ]
                    if any(indicator in item for indicator in template_indicators):
                        template_items += 1
                        continue

                    # Check if most required creature fields are missing (indicates template)
                    required_fields = ["size", "type", "alignment", "ac", "hp", "speed"]
                    missing_count = sum(
                        1 for field in required_fields if field not in item
                    )
                    if (
                        missing_count >= 5
                    ):  # If missing almost all required fields, likely a template
                        template_items += 1

                # Only mark as template if most items look like templates
                if total_items > 0 and template_items / total_items >= 0.8:
                    return True

        return False

    def _is_copy_template(self, item: Dict[str, Any]) -> bool:
        """Check if this item is a copy-template that references other content."""
        # Check for 5etools copy mechanism
        if "_copy" in item:
            return True

        # Check for NPC/template markers that indicate incomplete data
        if item.get("isNpc"):
            # For NPCs, check if they have basic stat requirements
            # If they're missing AC, HP, and ability scores, they're likely stub entries
            required_creature_fields = [
                "ac",
                "hp",
                "str",
                "dex",
                "con",
                "int",
                "wis",
                "cha",
            ]
            missing_count = sum(
                1 for field in required_creature_fields if field not in item
            )

            # If missing most required creature fields, it's likely a stub/template
            if missing_count >= 6:  # Missing most creature stats
                return True

            # Also check for NPCs that only have basic identity info
            if not any(field in item for field in ["ac", "hp"]):
                return True

        return False

    def _is_fluff_file(self, path: Path, data: Dict[str, Any]) -> bool:
        """Check if this is a fluff data file."""
        filename = path.name.lower()

        # Check filename patterns
        if "fluff" in filename:
            return True

        # Check for fluff data keys
        fluff_keys = [
            "spellFluff",
            "monsterFluff",
            "itemFluff",
            "adventureFluff",
            "bookFluff",
            "fluff",
        ]

        for key in fluff_keys:
            if key in data:
                return True

        return False

    def _extract_fluff_content(
        self, data: Dict[str, Any], path: Path
    ) -> List[Dict[str, Any]]:
        """Extract fluff content with liberal parsing."""
        # Map content types to their fluff keys
        fluff_key_map = {
            ContentType.SPELL: ["spellFluff", "spell_fluff"],
            ContentType.CREATURE: ["monsterFluff", "monster_fluff", "creatureFluff"],
            ContentType.ITEM: ["itemFluff", "item_fluff"],
        }

        # Try specific fluff keys for this content type
        if self.content_type in fluff_key_map:
            for fluff_key in fluff_key_map[self.content_type]:
                if fluff_key in data and isinstance(data[fluff_key], list):
                    logger.debug(
                        f"Found {len(data[fluff_key])} fluff items in {fluff_key}"
                    )
                    return self._process_fluff_items(data[fluff_key], path)

        # Try generic fluff keys
        for key in ["fluff", "fluffData"]:
            if key in data and isinstance(data[key], list):
                logger.debug(f"Found {len(data[key])} fluff items in {key}")
                return self._process_fluff_items(data[key], path)

        # Look for any key containing "fluff"
        for key, value in data.items():
            if "fluff" in key.lower() and isinstance(value, list):
                logger.debug(f"Found {len(value)} fluff items in {key}")
                return self._process_fluff_items(value, path)

        logger.debug(f"No fluff content found in {path}")
        return []

    def _process_fluff_items(
        self, fluff_items: List[Dict[str, Any]], path: Path
    ) -> List[Dict[str, Any]]:
        """Process fluff items to make them compatible with main content models."""
        processed_items = []

        for item in fluff_items:
            if not isinstance(item, dict):
                continue

            # Skip items without names
            if not item.get("name"):
                continue

            try:
                # Create a liberal version of the item that might validate
                processed_item = self._make_fluff_compatible(item, path)
                if processed_item:
                    processed_items.append(processed_item)
            except Exception as e:
                logger.debug(
                    f"Skipping fluff item {item.get('name', 'unknown')} in {path}: {e}"
                )

        return processed_items

    def _make_fluff_compatible(
        self, fluff_item: Dict[str, Any], path: Path
    ) -> Optional[Dict[str, Any]]:
        """Convert fluff item to be compatible with main content model."""
        # Start with the fluff item
        item = fluff_item.copy()

        # Add missing required fields based on content type
        if self.content_type == ContentType.SPELL:
            # Add minimal spell fields if missing
            item.setdefault("level", 0)  # Cantrip by default
            item.setdefault("school", "T")  # Transmutation by default
            item.setdefault("time", [{"number": 1, "unit": "action"}])
            item.setdefault("range", {"type": "self"})
            item.setdefault("components", {"v": True})
            item.setdefault("duration", [{"type": "instant"}])

            # Use fluff entries as spell description if no entries exist
            if not item.get("entries"):
                fluff_text = self._extract_fluff_text(fluff_item)
                if fluff_text:
                    item["entries"] = [fluff_text]
                else:
                    item["entries"] = ["Fluff content - see original source."]

        elif self.content_type == ContentType.CREATURE:
            # Add minimal creature fields if missing
            item.setdefault("size", ["M"])  # Medium by default
            item.setdefault("type", "humanoid")
            item.setdefault("alignment", ["N"])  # Neutral by default
            item.setdefault("ac", [{"ac": 10}])
            item.setdefault("hp", {"average": 1, "formula": "1d4"})
            item.setdefault("speed", {"walk": 30})

            # Basic ability scores
            for ability in ["str", "dex", "con", "int", "wis", "cha"]:
                item.setdefault(ability, 10)

            item.setdefault("cr", "0")

        elif self.content_type == ContentType.ITEM:
            # Add minimal item fields if missing
            item.setdefault("type", "G")  # Generic item by default

        return item

    def _extract_fluff_text(self, fluff_item: Dict[str, Any]) -> str:
        """Extract descriptive text from fluff item."""
        text_parts = []

        # Try to extract from entries
        entries = fluff_item.get("entries", [])
        if entries:
            text_parts.extend(self._extract_text_from_entries(entries))

        # Try other text fields
        for field in ["text", "description", "flavor"]:
            if field in fluff_item and isinstance(fluff_item[field], str):
                text_parts.append(fluff_item[field])

        return " ".join(text_parts) if text_parts else ""

    def _extract_text_from_entries(self, entries) -> List[str]:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                text_parts.extend(self._extract_text_from_entries(entry))
        elif isinstance(entries, dict):
            # Handle different entry types
            if "entries" in entries:
                text_parts.extend(self._extract_text_from_entries(entries["entries"]))
            elif "text" in entries:
                text_parts.append(entries["text"])
            # Add name if present
            if "name" in entries:
                text_parts.append(f"**{entries['name']}**")
        elif isinstance(entries, str):
            text_parts.append(entries)

        return text_parts

    def _infer_item_type(self, item: Dict[str, Any]) -> str:
        """Infer item type from name patterns and properties."""
        name = item.get("name", "").lower()

        # Check for explicit type indicators in item properties
        if item.get("damage") or item.get("weaponCategory"):
            return "W"  # Weapon

        if item.get("ac") or item.get("armorType"):
            return "A"  # Armor

        if item.get("stealth") is not None or "shield" in name:
            return "S"  # Shield

        # Check rarity - if it's magical, likely wondrous item
        rarity = item.get("rarity", "").lower()
        if rarity in ["uncommon", "rare", "very rare", "legendary", "artifact"]:
            # Check for specific magical item types first
            if any(pattern in name for pattern in ["ring", "band"]):
                return "RG"  # Ring
            elif any(pattern in name for pattern in ["rod", "scepter"]):
                return "RD"  # Rod
            elif any(pattern in name for pattern in ["staff", "quarterstaff"]):
                return "ST"  # Staff
            elif any(pattern in name for pattern in ["wand"]):
                return "WD"  # Wand
            elif any(pattern in name for pattern in ["potion", "elixir", "philter"]):
                return "P"  # Potion
            elif any(
                pattern in name
                for pattern in [
                    "scroll",
                    "tome",
                    "book",
                    "manual",
                    "compendium",
                    "grimoire",
                ]
            ):
                return "SC"  # Scroll/Book
            elif any(
                pattern in name
                for pattern in [
                    "amulet",
                    "necklace",
                    "pendant",
                    "cloak",
                    "robe",
                    "boots",
                    "gloves",
                    "gauntlets",
                    "belt",
                    "circlet",
                    "crown",
                    "helm",
                    "helmet",
                    "bracers",
                    "tattoo",
                ]
            ):
                return "W"  # Wondrous Item (wearable)
            else:
                return "W"  # Default to wondrous item for magical items

        # Pattern-based detection for name patterns
        weapon_patterns = [
            "sword",
            "blade",
            "dagger",
            "knife",
            "axe",
            "hammer",
            "mace",
            "club",
            "staff",
            "spear",
            "lance",
            "pike",
            "bow",
            "crossbow",
            "javelin",
            "dart",
            "sling",
            "whip",
            "flail",
            "glaive",
            "halberd",
            "trident",
            "scimitar",
            "rapier",
            "shortsword",
            "longsword",
            "greatsword",
            "handaxe",
            "battleaxe",
            "greataxe",
            "light hammer",
            "warhammer",
            "maul",
            "morningstar",
            "war pick",
            "quarterstaff",
        ]

        armor_patterns = [
            "armor",
            "mail",
            "plate",
            "leather",
            "studded",
            "chain",
            "scale",
            "splint",
            "breastplate",
            "half plate",
            "ring mail",
            "chain mail",
            "scale mail",
            "hide armor",
            "padded armor",
        ]

        shield_patterns = ["shield", "buckler"]

        tool_patterns = [
            "kit",
            "tools",
            "thieves",
            "artisan",
            "disguise",
            "forgery",
            "herbalism",
            "navigator",
            "poisoner",
            "alchemist",
            "brewer",
            "calligrapher",
            "carpenter",
            "cartographer",
            "cobbler",
            "cook",
            "glassblower",
            "jeweler",
            "leatherworker",
            "mason",
            "painter",
            "potter",
            "smith",
            "tinker",
            "weaver",
            "woodcarver",
        ]

        # Check weapon patterns
        if any(pattern in name for pattern in weapon_patterns):
            return "W"  # Weapon

        # Check armor patterns
        if any(pattern in name for pattern in armor_patterns):
            return "A"  # Armor

        # Check shield patterns
        if any(pattern in name for pattern in shield_patterns):
            return "S"  # Shield

        # Check tool patterns
        if any(pattern in name for pattern in tool_patterns):
            return "T"  # Tool

        # Check for adventuring gear patterns
        gear_patterns = [
            "rope",
            "torch",
            "lantern",
            "oil",
            "rations",
            "waterskin",
            "bedroll",
            "blanket",
            "tent",
            "backpack",
            "pouch",
            "sack",
            "chest",
            "barrel",
            "bottle",
            "vial",
            "flask",
            "jug",
            "pitcher",
            "ball bearings",
            "caltrops",
            "candle",
            "chain",
            "chalk",
            "crowbar",
            "grappling hook",
            "ladder",
            "lock",
            "manacles",
            "mirror",
            "piton",
            "pole",
            "pulley",
            "sealing wax",
            "shovel",
            "signal whistle",
            "string",
            "tinderbox",
        ]

        if any(pattern in name for pattern in gear_patterns):
            return "G"  # Adventuring Gear

        # Check for mount/vehicle patterns
        if any(
            pattern in name
            for pattern in [
                "horse",
                "pony",
                "mule",
                "camel",
                "elephant",
                "cart",
                "wagon",
                "ship",
                "boat",
            ]
        ):
            return "MNT"  # Mount or Vehicle

        # Check for treasure patterns
        if any(
            pattern in name
            for pattern in [
                "gem",
                "jewel",
                "coin",
                "gold",
                "silver",
                "platinum",
                "copper",
                "treasure",
                "art object",
            ]
        ):
            return "TRE"  # Treasure

        # Special cases based on name prefixes/suffixes
        if name.startswith(("+1", "+2", "+3")) or "enhancement" in name:
            # Enhanced items - determine base type
            if any(pattern in name for pattern in weapon_patterns):
                return "W"  # Enhanced weapon
            elif any(pattern in name for pattern in armor_patterns + shield_patterns):
                return "A"  # Enhanced armor/shield
            else:
                return "W"  # Default to wondrous item for enhanced items

        # Default fallback based on common D&D item categorization
        if "magic" in name or rarity:
            return "W"  # Wondrous Item for magical items

        # Final fallback
        return "G"  # Generic adventuring gear


# Factory functions for common loaders
def create_spell_loader() -> JsonDataLoader:
    """Create a spell data loader."""
    from ..models.spells import Spell

    return JsonDataLoader(Spell, ContentType.SPELL)


def create_creature_loader() -> JsonDataLoader:
    """Create a creature data loader."""
    from ..models.creatures import Creature

    return JsonDataLoader(Creature, ContentType.CREATURE)


def create_item_loader() -> JsonDataLoader:
    """Create an item data loader."""
    from ..models.items import Item

    return JsonDataLoader(Item, ContentType.ITEM)


def create_adventure_loader() -> JsonDataLoader:
    """Create an adventure data loader."""
    from ..models.adventures import Adventure

    return JsonDataLoader(Adventure, ContentType.ADVENTURE)


def create_book_loader() -> JsonDataLoader:
    """Create a book data loader."""
    from ..models.books import Book

    return JsonDataLoader(Book, ContentType.BOOK)


def create_feat_loader() -> JsonDataLoader:
    """Create a feat data loader."""
    from ..models.feats import Feat

    return JsonDataLoader(Feat, ContentType.FEAT)


def create_race_loader() -> JsonDataLoader:
    """Create a race data loader."""
    from ..models.races import Race

    return JsonDataLoader(Race, ContentType.RACE)


def create_background_loader() -> JsonDataLoader:
    """Create a background data loader."""
    from ..models.backgrounds import Background

    return JsonDataLoader(Background, ContentType.BACKGROUND)


def create_class_loader() -> JsonDataLoader:
    """Create a class data loader."""
    from ..models.classes import Class

    return JsonDataLoader(Class, ContentType.CLASS)
