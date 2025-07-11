import json
import os
import re
import subprocess
import sys
import unicodedata
from pprint import pprint

from dndtex.log import logging


class DndTexError(Exception):
    pass


class DndTexUnhandled(DndTexError):
    pass


SZ_FULL = {
    "F": "Fine",
    "D": "Diminutive",
    "T": "Tiny",
    "S": "Small",
    "M": "Medium",
    "L": "Large",
    "H": "Huge",
    "G": "Gargantuan",
    "C": "Colossal",
    "V": "Varies",
}

ALIGN_FULL = {
    "L": "lawful",
    "N": "neutral",
    "NX": "neutral (law/chaos axis)",
    "NY": "neutral (good/evil axis)",
    "C": "chaotic",
    "G": "good",
    "E": "evil",
    "U": "unaligned",
    "A": "any alignment",
}

SCHOOL_FULL = {
    "A": "Abjuration",
    "V": "Evocation",
    "E": "Enchantment",
    "I": "Illusion",
    "D": "Divination",
    "N": "Necromancy",
    "T": "Transmutation",
    "C": "Conjuration",
    "P": "Psionic",
}

## Unsure if I'll need this...
# Parser.SP_TM_ACTION = "action";
# Parser.SP_TM_B_ACTION = "bonus";
# Parser.SP_TM_REACTION = "reaction";
# Parser.SP_TM_ROUND = "round";
# Parser.SP_TM_MINS = "minute";
# Parser.SP_TM_HRS = "hour";
# Parser.SP_TM_SPECIAL = "special";
# Parser.SP_TIME_SINGLETONS = [Parser.SP_TM_ACTION, Parser.SP_TM_B_ACTION, Parser.SP_TM_REACTION, Parser.SP_TM_ROUND];
# Parser.SP_TIME_TO_FULL = {
# 	[Parser.SP_TM_ACTION]: "Action",
# 	[Parser.SP_TM_B_ACTION]: "Bonus Action",
# 	[Parser.SP_TM_REACTION]: "Reaction",
# 	[Parser.SP_TM_ROUND]: "Rounds",
# 	[Parser.SP_TM_MINS]: "Minutes",
# 	[Parser.SP_TM_HRS]: "Hours",
# 	[Parser.SP_TM_SPECIAL]: "Special",
# };


class Util:
    @staticmethod
    def load_extra_data(kind, name, source):
        file_name_map = {
            "variantrule": "variantrules",
            "sense": "senses",
            "condition": "conditionsdiseases",
            "hazard": "trapshazards",
            "action": "actions",
            "feat": "feats",
            "optionalfeature": "optionalfeatures",
            "status": "conditionsdiseases",
        }

        file_name = f"data/{file_name_map[kind]}.json"
        logging.debug(
            "searching for extra data from %s for %s (%s)", file_name, name, source
        )
        try:
            fh = open(file_name, encoding="utf8")
            json_data = json.load(fh)
        except FileNotFoundError:
            logging.warning(f"File not found: {file_name}")
            return None
        fh.close()

        for kind in json_data.keys():
            for item in json_data[kind]:
                if (
                    item["name"].lower() == name.lower()
                    and item["source"].lower() == source.lower()
                ):
                    return item["entries"]

        logging.error(f"Could not find {name} ({source}) in {file_name}")
        return None

    @staticmethod
    def alignment_string(data):
        if not data:
            return ""

        if isinstance(data, str):
            return data

        if isinstance(data, dict):
            alignment = Util.alignment_string(data["alignment"])
            chance = data.get("chance")
            if chance:
                return f"{alignment} ({chance}\\%)"
            else:
                return alignment

        if len(data) == 1:
            logging.debug("Data: %s", data)
            return Util.alignment_string(data[0])

        if len(data) == 2:
            if type(data[0]) is dict:
                return " ".join(map(Util.alignment_string, data))

            return " ".join(map(lambda x: ALIGN_FULL[x], data))

        if len(data) == 3:
            if "NX" in data and "NY" in data and "N" in data:
                return "any neutral alignment"

        if len(data) == 4:
            if "L" not in data and "NX" not in data:
                return "any chaotic alignment"
            if "E" not in data and "NY" not in data:
                return "any good alignment"
            if "G" not in data and "NY" not in data:
                return "any evil alignment"
            if "C" not in data and "NX" not in data:
                return "any lawful alignment"

        if len(data) == 5:
            if "G" not in data:
                return "any non-good alignment"
            if "E" not in data:
                return "any non-evil alignment"
            if "L" not in data:
                return "any non-lawful alignment"
            if "C" not in data:
                return "any non-chaotic alignment"

        raise (DndTexError("Unknown alignment " + str(data)))

    @staticmethod
    def findCreatureData(name, source):
        logging.debug("searching for %s (%s)", name, source)
        if not source:
            source = "mm"
        source_file_map = {
            "whereevillives": "../5etools-homebrew/creature/MCDM Productions; Flee, Mortals!.json"
        }
        file_name = f"data/bestiary/bestiary-{source.lower()}.json"
        if source in source_file_map:
            file_name = source_file_map[source]

        try:
            fh = open(file_name, encoding="utf8")
            json_data = json.load(fh).get("monster")
        except FileNotFoundError:
            logging.warning(f"File not found: {file_name}")
            return None
        fh.close()
        for creature in json_data:
            if creature["name"].lower() == name.lower():
                if "_copy" in creature:
                    c = Util.findCreatureData(
                        creature["_copy"]["name"], creature["_copy"]["source"]
                    )
                    c["name"] = name.title()
                    c["copyFrom"] = creature["_copy"]
                    logging.debug("Original: %s", creature)
                    logging.debug("New: %s", c)
                    return c
                return creature

    @staticmethod
    def _loadItemsFromJSON(file_name):
        try:
            fh = open(file_name, encoding="utf8")
            json_data = json.load(fh)
        except FileNotFoundError:
            logging.warning(f"File not found: {file_name}")
            return None
        fh.close()
        return json_data

    @staticmethod
    def _itemMatch(item, name, source):
        result = (
            item["name"].lower() == name.lower()
            and item["source"].lower() == source.lower()
        )
        # logging.debug("%s/%s == %s/%s %s", name, source, item['name'], item['source'], result)
        return result

    @staticmethod
    def findItemData(name, source):
        if not source:
            source = "xdmg"
        base_item = Util.findBaseItemData(name, source)
        file_name = "data/items.json"
        json_data = Util._loadItemsFromJSON(file_name)
        data = json_data["item"]
        if "itemGroup" in json_data:
            data += json_data["itemGroup"]

        logging.debug("Searching for item %s (%s)", name, source)
        for item in data:
            if Util._itemMatch(item, name, source):
                if "_copy" in item:
                    name = item["_copy"]["name"]
                    source = item["_copy"]["source"]
                    logging.warning("Item data has _copy material - not implemented")
                    return Util.findItemData(name, source)

                if base_item:
                    logging.warning("Oh I have a base_item!")
                    item["entries"] = base_item["entriesTemplate"]

                return item

        logging.warning("Failed to find %s (%s)", name, source)

    @staticmethod
    def findBaseItemData(name, source):
        if not source:
            source = "xdmg"
        file_name = "data/items-base.json"
        json_data = Util._loadItemsFromJSON(file_name)
        data = json_data["itemEntry"]

        logging.debug("Searching for base item %s (%s)", name, source)
        for item in data:
            if Util._itemMatch(item, name, source):
                if "_copy" in item:
                    name = item["_copy"]["name"]
                    source = item["_copy"]["source"]
                    logging.warning(
                        "Item %s has _copy material - not implemented", name
                    )
                    return Util.findBaseItemData(name, source)
                return item

    @staticmethod
    def findDeityData(name, pantheon, source):
        file_name = "data/deities.json"
        logging.debug("Loading deity %s", name)
        try:
            fh = open(file_name, encoding="utf8")
            json_data = json.load(fh).get("deity")
        except FileNotFoundError:
            logging.warning(f"File not found: {file_name}")
            return None
        fh.close()
        for deity in json_data:
            if (
                deity["name"].lower() == name.lower()
                and deity["source"].lower() == source.lower()
                and deity["pantheon"] == pantheon
            ):
                logging.debug("Found: %s", deity)
                return deity

        logging.warning("Failed to find %s (%s)", name, source)

    @staticmethod
    def findSpellData(name, source):
        if not source:
            source = "phb"
        file_name = f"data/spells/spells-{source.lower()}.json"
        try:
            fh = open(file_name, encoding="utf8")
            json_data = json.load(fh).get("spell")
        except FileNotFoundError:
            logging.warning("File not found %s", file_name)
            return None
        fh.close()
        for spell in json_data:
            if spell["name"].lower() == name.lower():
                if "_copy" in spell:
                    name = spell["_copy"]["name"]
                    source = spell["_copy"]["source"]
                    return Util.findSpellData(name, source)
                return spell

    @staticmethod
    def remove_tag(tag_string):
        if isinstance(tag_string, dict):
            tag_string = tag_string["entry"]
        match = re.search("{@(.*?) (.*?)}", tag_string)
        if not match:
            return tag_string
        tag_arguments = match.group(2).split("|")
        return tag_string.replace(match.group(0), tag_arguments[0])

    @staticmethod
    def make_ordinal(n):
        n = int(n)
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        else:
            suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
        return str(n) + suffix

    @staticmethod
    def joinConjunct(source, multi_str, duo_str):
        if len(source) == 1:
            return source[0]
        if len(source) == 2:
            return duo_str.join(source)
        else:
            return ", or ".join(
                [f"{multi_str} ".join(source[:-1]), source[-1]]
                if len(source) > 2
                else source
            )

    @staticmethod
    def convertImage(src):
        if not os.path.exists(src):
            logging.warning("Cannot convert image that does not exist: %s", src)
            return None
        if src.endswith(".webp"):
            # Take last couple of dirs?
            dest = "images/" + src.replace(".webp", ".png")

            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest):
                convert_command = ("dwebp", src, "-o", dest)
                logging.info("converting %s", src)
                convert_result = subprocess.run(
                    convert_command, check=True, capture_output=True
                )
                if convert_result.returncode != 0:
                    logging.warning("failed: %s", convert_result.stdout)
        else:
            return src

        return dest


class Spell:
    def __init__(self, data):
        self._data = data
        self.name = data["name"]
        self.source = data["source"]
        self.level = data["level"]
        self.school = SCHOOL_FULL[data["school"]]
        self.time = self._strTime()
        self.range = self._strRange()
        self.components = self._strComponents()
        self.duration = self._strDuration()
        self.entries = data["entries"]

        if self.level == 0:
            self.type = f"{self.school} cantrip"
        else:
            self.type = f"{Util.make_ordinal(self.level)} level {self.school}"

    def _strTime(self):
        if len(self._data["time"]) > 1:
            raise DndTexUnhandled("Time array")

        number = self._data["time"][0]["number"]
        unit = self._data["time"][0]["unit"]

        return f"{number} {unit}"

    def _strRange(self):
        range = self._data["range"]
        type = range["type"]
        singleton_unit = {"feet": "foot", "yards": "yard", "miles": "mile"}

        if type == "special":
            return "Special"
        elif type == "point":
            dist = range["distance"]
            if dist == "plane":
                return "Unlimited on the same plane"
            if dist["type"] in ("self", "sight", "unlimited", "touch"):
                return dist["type"].title()
            else:
                if dist["amount"] == 1:
                    dist["type"] = singleton_unit[dist["type"]]
                return f"{dist['amount']} {dist['type']}"
        else:
            amount = range["distance"]["amount"]
            distance_type = range["distance"]["type"]
            if amount == 1:
                distance_type = singleton_unit[distance_type]

            return f"Self ({amount} {distance_type} {type})"
        # return `Self
        #      (${size.amount}-${Parser.getSingletonUnit(size.type)}
        #       ${Parser.spRangeToFull._getAreaStyleString(range)}
        #       ${range.type === Parser.RNG_CYLINDER
        #           ? `${size.amountSecondary != null && size.typeSecondary != null ? `, ${size.amountSecondary}-${Parser.getSingletonUnit(size.typeSecondary)}-high` : ""} cylinder` : ""})`;

    def _strComponents(self):
        c = self._data["components"]
        out = []

        if c.get("v"):
            out.append("V")
        if c.get("s"):
            out.append("S")
        if c.get("m"):
            m = c.get("m")
            if isinstance(m, dict):
                out.append(c.get("m").get("text"))
            else:
                out.append(m)
        if not out:
            return "None"

        return ", ".join(out)

    def _strDuration(self):
        hasSubOr = False

        def _process(d):
            if d["type"] == "special":
                return "Special"
            elif d["type"] == "instant":
                if d.get("condition"):
                    cond = f" ({d.get('condition')})"
                else:
                    cond = ""
                return f"Instantaneous{cond}"
            elif d["type"] == "timed":
                dur = d["duration"]
                bits = []
                if dur["amount"] > 1:
                    dur["type"] = dur["type"] + "s"
                duration = f"{dur['amount']} {dur['type']}"
                if d.get("concentration"):
                    bits.append("Concentration, up to ")
                elif d["duration"].get("upTo"):
                    bits.append("Up to ")
                bits_string = "".join(bits)
                return f"{bits_string}{duration}"
            elif d["type"] == "permanent":
                if d.get("ends"):
                    end_type = {
                        "dispel": "dispelled",
                        "trigger": "triggered",
                        "discharge": "discharged",
                    }
                    endsToJoin = map(lambda x: end_type[x], d.get("ends"))
                    # hasSubOr = hasSubOr or len(endsToJoin) > 1
                    until = " or ".join(endsToJoin)
                    return f"Until {until}"

                return "Permanent -- check book"

            return "something else -- check book"

        out = map(_process, self._data["duration"])
        return ", ".join(out)

    def _strScalingLevelDice(self):
        return "This spell does extra damage at higher levels, but I cannot tell you how much"

    def render(self, renderer):
        lines = []
        lines = [f"\\addcontentsline{{toc}}{{section}}{{{self.name}}}"]
        lines.append("\n\n\\DndSpellHeader%")
        lines.append(f"{{{self.name}}}")
        lines.append(f"{{{self.type}}}")
        lines.append(f"{{{self.time}}}")
        lines.append(f"{{{self.range}}}")
        lines.append(f"{{{self.components}}}")
        lines.append(f"{{{self.duration}}}")

        lines += renderer.renderRecursive(3, self.entries)

        return lines


class Item:
    def __init__(self, data):
        self._data = data or None
        if not data:
            return
        self.name = data["name"]
        self.source = data["source"]

        damagePartsPre = []
        damageParts = []
        if "ac" in data:
            item_type = data.get("bardingType") or data.get("type")
            dexterityMax = (
                2
                if item_type == "MA" and not data.get("dexterityMax")
                else data.get("dexterityMax")
            )
            isAddDex = data.get("dexterityMax") or item_type in ("HA", "S")

            prefix = "+" if item_type == "S" else ""
            suffix = (
                f" + Dex{f' (max {dexterityMax})' if dexterityMax else ''}"
                if isAddDex
                else ""
            )

            damageParts.append(f"AC {prefix}{data.get('ac')}{suffix}")

        if data.get("acSpecial"):
            damageParts.append(
                data["acSpecial"] if data.get("ac") else f"AC {data['acSpecial']}"
            )

        if data.get("dmg1"):
            damageParts.append(data.get("dmg1"))

        if data.get("speed"):
            damageParts.append(f"Speed: {data['speed']}")

        if data.get("carryingCapacity"):
            damageParts.append(f"Carrying Capacity: {data['carryingCapacity']}")

        # TODO: Vehicles

        damage = [", ".join(damagePartsPre), ", ".join(damageParts)]

        self.damage = "\n".join(filter(None, damage))
        self.damageType = data.get("dmgType", "")

        self.entries = data.get("entries")

        typeRarity = data.get("rarity").title()
        if (
            typeRarity == "None"
        ):  # This isn't a python None, the JSON contains "none" as a word
            typeRarity = ""
        if data.get("wondrous"):
            typeRarity = f"Wondrous item, {typeRarity}"
        if data.get("reqAttune"):
            attunement = data.get("reqAttune")
            if type(attunement) is str:
                attunement = f"requires attunement {attunement}"
            else:
                attunement = "requires attunement"
            typeRarity = f"{typeRarity} ({attunement})"
        self.typeRarity = typeRarity
        self.tierText = f"{data.get('tier')} tier" if data.get("tier") else ""

        # const [typeRarityText, subTypeText, tierText] = Renderer.item.getTypeRarityAndAttunementText(item);
        # const textLeft = [Parser.itemValueToFullMultiCurrency(item), Parser.itemWeightToFull(item)].filter(Boolean).join(", ").uppercaseFirst();
        # const textRight = [damage, damageType, propertiesTxt].filter(Boolean).join(" ");

        logging.debug(data)

    def render(self, renderer):
        if not self._data:
            logging.warning("No data to render")
            return []
        if not self.entries:
            return []

        lines = [f"\\DndItemHeader{{{self.name}}}{{{self.typeRarity}}}"]
        if "entries" in self._data:
            lines += renderer.renderRecursive(3, self._data["entries"])

        return lines


class Creature:
    def __init__(self, data):
        if not data:
            raise DndTexError("Creature() initialised without data")
        self._data = data
        self._copyFrom = data.get("copyFrom")
        self.name = data["name"]
        self.source = data["source"]
        self.size = self._strSize(data["size"])
        self.kind = self._strKind(data["type"])
        self.alignment = Util.alignment_string(data.get("alignment", "U"))
        self.ac = self._strAc(data["ac"])
        self.hp = self._strHp(data["hp"])
        self.speed = self._strSpeed(data["speed"])
        self.str = data["str"]
        self.dex = data["dex"]
        self.con = data["con"]
        self.int = data["int"]
        self.wis = data["wis"]
        self.cha = data["cha"]
        self.saves = None
        self.skills = None
        self.vulnerable = None
        self.resist = None
        self.immune = None
        self.conditionImmune = None
        self.senses = None
        self.languages = None
        self.cr = None
        self.traits = []
        self.actions = []
        self.bonus_actions = []
        self.reactions = []
        self.legendary = []
        self.legendaryActions = None
        self.lairActions = None
        self.regionalEffects = None
        self.spellcasting = []
        self.actions = []
        self.fluff = []
        self.images = []
        self.token = None
        self.wide = False

        if "save" in data:
            self.saves = self._strAbility(data["save"])

        if "skill" in data:
            self.skills = self._strAbility(data["skill"])

        if "vulnerable" in data:
            self.vulnerable = self._strDamageType(data["vulnerable"], "vulnerable")

        if "resist" in data:
            self.resist = self._strDamageType(data["resist"], "resist")

        if "immune" in data:
            self.immune = self._strDamageType(data["immune"], "immune")

        if "conditionImmune" in data:
            self.conditionImmune = self._strCondition(data["conditionImmune"])

        if "senses" in data:
            data["senses"].append(f"passive perception {data['passive']}")
            self.senses = ", ".join(data["senses"])

        if "languages" in data:
            self.languages = ", ".join(data["languages"])

        if "cr" in data:
            if isinstance(data["cr"], dict):
                self.cr = data["cr"]["cr"]  # Flee mortals...
            else:
                self.cr = str(data["cr"])

        if "trait" in data:
            self.traits = data["trait"]

        if "spellcasting" in data:
            self.spellcasting = data["spellcasting"]

        if "action" in data:
            self.actions = data["action"]

        if "reaction" in data:
            self.reactions = data["reaction"]

        if "bonus" in data:
            self.bonus_actions = data["bonus"]

        if "legendary" in data:
            self.wide = True
            self.legendary = data["legendary"]
            self.legendaryActions = data.get("legendaryActions", 3)
            self.legendaryHeader = data.get("legendaryHeader")
            if not self.legendaryHeader:
                self.legendaryHeader = f"{self.name} can take {self.legendaryActions} legendary action{'s' if self.legendaryActions > 1 else ''}, choosing from the options below. Only one legendary action can be used at a time and only at the end of another creature's turn. {self.name} regains spent legendary actions at the start of its turn."

        if "legendaryGroup" in data:
            self.wide = True
            groups = json.load(
                open("data/bestiary/legendarygroups.json", encoding="utf8")
            )
            for group in groups.get("legendaryGroup"):
                if data["name"] == group["name"] and data["source"] == group["source"]:
                    self.lairActions = group.get("lairActions")
                    self.regionalEffects = group.get("regionalEffects")
                    break

        if data.get("hasToken"):
            self.token = self._getTokenImgPath()
        if data.get("hasFluff"):
            self._loadFluff()

    def _getTokenImgPath(self, mediaDir="5eimages"):
        ent = self._data
        if "tokenUrl" in ent:
            return ent["tokenUrl"]
        if "token" in ent:
            return Util.convertImage(
                f"{mediaDir}/{ent['token']['source']}/{self._nameToTokenName(ent['token']['name'])}.webp"
            )
        if "tokenHref" in ent:
            raise (DndTexError("Don't know how to handle tokenHref"))

        return Util.convertImage(
            f"{mediaDir}/bestiary/tokens/{ent['source']}/{self._nameToTokenName(ent['name'])}.webp"
        )

    def _nameToTokenName(self, name):
        return (
            unicodedata.normalize("NFKD", name)
            .encode("ASCII", "ignore")
            .decode()
            .replace('"', "")
        )

    def _loadFluff(self):
        file_name = f"data/bestiary/fluff-bestiary-{self.source.lower()}.json"
        fh = open(file_name, encoding="utf8")
        fluffData = json.load(fh)
        fh.close()

        for fluff in fluffData["monsterFluff"]:
            if fluff["name"].lower() == self.name.lower():
                self.images = fluff["images"] if "images" in fluff else []
                self.fluff = fluff["entries"] if "entries" in fluff else []

    def _strSize(self, size):
        if len(size) == 1:
            return SZ_FULL[size[0]]
        else:
            return " or ".join(map(lambda x: SZ_FULL[x], size))

    def _strTag(self, tag):
        if isinstance(tag, str):
            return tag
        return ""

    def _strKind(self, data):
        if isinstance(data, str):
            return data
        if "tags" in data:
            return f"{data['type']} ({', '.join(map(self._strTag, data['tags']))})"
        else:
            return f"{data['type']}"

    def _ac_part(self, data):
        if isinstance(data, int):
            return str(data)

        if isinstance(data, list):
            if len(data) > 2:
                pprint(data)
                raise (Exception)
            data = data[0]

        if data.get("special"):
            return data.get("special")

        s = str(data["ac"])
        if "from" in data:
            s = s + f" ({data['from'][0]})"
        if "condition" in data:
            s = s + " " + data["condition"]

        return s

    def _strAc(self, data):
        if isinstance(data, int):
            return str(data)

        ac = ""
        first = data.pop(0)
        ac = self._ac_part(first)

        if len(data) > 0:
            more = []
            for more_ac in data:
                more.append(self._ac_part(more_ac))
            ac = f"{ac} ({', '.join(more)})"

        return ac

    def _strHp(self, data):
        if data.get("special"):
            return data.get("special")
        return data["formula"]

    def _strSpeed(self, data):
        walk = data.get("walk")
        if isinstance(walk, dict):
            results = [f"{walk['number']} ft. {walk.get('condition')}"]
        else:
            results = [str(data.get("walk", "0")) + " ft."]
        for key in data:
            if key == "walk":
                continue
            if key == "canHover":
                continue
            if isinstance(data[key], dict):
                d = data[key]
                results.append(f"{key} {d['number']} ft. \\textit{{{d['condition']}}}")
            else:
                results.append(f"{key} {data[key]} ft.")
        return ", ".join(results)

    def _strAbility(self, data):
        return ", ".join(map(lambda x: f"{x.title()} {data[x]}", data))

    def _strDamageType(self, data, dmg_type, sep=", "):
        condition_seen = False
        results = []

        for dmg in data:
            if isinstance(dmg, str):
                results.append(dmg)
            elif isinstance(dmg, dict):
                if "special" in dmg:
                    results.append(dmg["special"])
                else:
                    type_str = self._strDamageType(dmg[dmg_type], dmg_type)
                    results.append(f"{type_str} {dmg['note']}")
                    condition_seen = True
            else:
                types = ", ".join(dmg[dmg_type])
                results.append(f"{types} {dmg['note']}")
                condition_seen = True

        if condition_seen and len(results) > 1:
            sep = "; "

        return sep.join(results)

    def _strCondition(self, data):
        out = []
        sep = ", "
        has_note = False
        for cond in data:
            if isinstance(cond, dict):
                has_note = True
                sub_cond = self._strCondition(cond["conditionImmune"])
                note = cond.get("note")
                out.append(f"{sub_cond} {note}")
            else:
                out.append(cond.split("|")[0])

        if has_note and len(out) > 1:
            sep = "; "
        return sep.join(out)

    def _comma_list_string(self, seq, sep):
        return " and ".join(
            [f"{sep} ".join(seq[:-1]), seq[-1]] if len(seq) > 2 else seq
        )

    def renderCreature(self, renderer):
        c = self
        lines = []
        options = "float=t"

        if c.wide:
            options = "float*=b,width=\\textwidth + 8pt"
        lines.append(f"\n\\begin{{DndMonster}}[{options}]{{{c.name}}}")
        # lines.append(f"\\addcontentsline{{toc}}{{section}}{{{c.name}}}")
        if c.wide:
            lines.append("\\begin{multicols}{2}")
        lines.append(f"\\DndMonsterType{{{c.size} {c.kind}, {c.alignment}}}")

        lines.append("\\DndMonsterBasics[")
        lines.append(f"armor-class = {{{c.ac}}},")
        lines.append(f"hit-points = {{\\DndDice{{{c.hp}}}}},")
        lines.append(f"speed = {{{c.speed}}}")
        lines.append("]")

        lines.append("\\DndMonsterAbilityScores[")
        lines.append(f" str = {c.str},")
        lines.append(f" dex = {c.dex},")
        lines.append(f" con = {c.con},")
        lines.append(f" int = {c.int},")
        lines.append(f" wis = {c.wis},")
        lines.append(f" cha = {c.cha}")
        lines.append("]")

        lines.append("\\DndMonsterDetails[")
        if c.saves:
            lines.append(f"saving-throws = {{{c.saves}}},")
        if c.skills:
            lines.append(f"skills = {{{c.skills}}},")
        if c.vulnerable:
            lines.append(f"damage-vulnerabilities = {{{c.vulnerable}}},")
        if c.resist:
            lines.append(f"damage-resistances = {{{c.resist}}},")
        if c.immune:
            lines.append(f"damage-immunities = {{{c.immune}}},")
        if c.conditionImmune:
            lines.append(f"condition-immunities = {{{c.conditionImmune}}},")
        if c.senses:
            lines.append(f"senses = {{{c.senses}}},")
        if c.languages:
            lines.append(f"languages = {{{c.languages}}},")
        if c.cr:
            lines.append(f"challenge = {c.cr},")
        lines.append("]")

        if c._copyFrom:
            lines.append(
                "\\DndMonsterAction{Copy Warning}\nThis content has been copied from another creature, but the data replacement hasn't been run. Check details.\n"
            )

        if c.traits:
            for trait in c.traits:
                lines.append(f"\\DndMonsterAction{{{trait['name']}}}")
                lines += renderer.renderRecursive(0, trait["entries"])

        if c.spellcasting:
            for spellcasting in c.spellcasting:
                name = spellcasting["name"]
                cast_type = (
                    "DndInnateSpellLevel"
                    if name == "Innate Spellcasting"
                    else "DndMonsterSpellLevel"
                )
                lines.append(f"\\DndMonsterAction{{{name}}}")
                for header in spellcasting["headerEntries"]:
                    lines.append(header)
                lines.append("\\begin{DndMonsterSpells}")
                if "will" in spellcasting:
                    spell_list = Util.remove_tag(", ".join(spellcasting["will"]))
                    lines.append(f"  \\DndInnateSpellLevel{{{spell_list}}}")
                if "daily" in spellcasting:
                    for freq in spellcasting["daily"].keys():
                        number = freq[:-1]
                        spell_list = Util.remove_tag(
                            ", ".join(spellcasting["daily"][freq])
                        )
                        lines.append(
                            f"  \\DndInnateSpellLevel[{number}]{{{spell_list}}}"
                        )

                if "spells" in spellcasting:
                    for level in range(9):
                        level = str(level)
                        if level not in spellcasting["spells"]:
                            continue
                        spell_list = Util.remove_tag(
                            ", ".join(spellcasting["spells"][level]["spells"])
                        )
                        if level == "0":
                            lines.append(f"  \\{cast_type}{{{spell_list}}}")
                        else:
                            slots = ""
                            if "slots" in spellcasting["spells"][level]:
                                slots = (
                                    "["
                                    + str(spellcasting["spells"][level]["slots"])
                                    + "]"
                                )
                            lines.append(
                                f"   \\{cast_type}[{level}]{slots}{{{spell_list}}}"
                            )

                lines.append("\\end{DndMonsterSpells}")

        if c.actions:
            lines.append("\\DndMonsterSection{Actions}")
            for action in c.actions:
                lines.append(f"\\DndMonsterAction{{{action['name']}}}")
                lines += list(renderer.renderRecursive(0, action["entries"]))

        if c.bonus_actions:
            lines.append("\\DndMonsterSection{Bonus Actions}")
            for action in c.bonus_actions:
                lines.append(f"\\DndMonsterAction{{{action['name']}}}")
                lines += list(renderer.renderRecursive(0, action["entries"]))

        if c.reactions:
            lines.append("\\DndMonsterSection{Reactions}")
            for reaction in c.reactions:
                lines.append(f"\\DndMonsterAction{{{reaction['name']}}}")
                lines += list(renderer.renderRecursive(0, reaction["entries"]))

        if c.legendary:
            lines.append("\\DndMonsterSection{Legendary Actions}")
            lines += list(renderer.renderRecursive(0, c.legendaryHeader))
            lines.append("\\begin{DndMonsterLegendaryActions}")
            for la in c.legendary:
                content = "\n".join(renderer.renderRecursive(0, la["entries"]))
                lines.append(
                    f"\\DndMonsterLegendaryAction{{{la['name']}}}{{{content}}}"
                )
            lines.append("\\end{DndMonsterLegendaryActions}")

        if c.lairActions:
            lines.append("\\DndMonsterSection{Lair Actions}")
            lines += list(renderer.renderRecursive(0, c.lairActions))

        if c.regionalEffects:
            lines.append("\\DndMonsterSection{Regional Effects}")
            lines += list(renderer.renderRecursive(0, c.regionalEffects))

        if c.wide:
            lines.append("\\end{multicols}")

        lines.append("\\end{DndMonster}\n\n")

        # if c.fluff:
        #     lines += list(renderer.renderRecursive(3, c.fluff))

        # if c.images:
        #     for img in c.images:
        #         lines += renderer.renderImage(img, float='h')

        return lines
