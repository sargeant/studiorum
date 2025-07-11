import warnings

import dndtex
from dndtex import Util
from dndtex.log import logging


class DndTag:
    wrap_command = None
    static_string = None

    def __init__(
        self, args, creatureList=None, spellList=None, renderer=None, itemList=None
    ):
        self.args = args
        firstArg = self.args[0] if self.args is not None else ""
        self.creatureList = creatureList
        self.spellList = spellList
        self.itemList = itemList
        self.renderer = renderer

        if self.wrap_command:
            self.content = f"\\{self.wrap_command}{{{firstArg}}}"
        elif self.static_string:
            self.content = self.static_string
        else:
            self.content = f"{firstArg}"

        self.setup()

    def get_content(self):
        return self.content

    def setup(self):
        pass


class recharge(DndTag):
    def get_content(self):
        count = int(self.args[0]) if self.args else 6

        if count < 6:
            return f"(Recharge {count}\\textendash 6)"
        else:
            return f"(Recharge {count})"


class legroup(DndTag):
    pass


class unknown(DndTag):
    pass


class sup(DndTag):
    wrap_command = "textsuperscript"


class note(DndTag):
    static_string = ""


class area(DndTag):
    pass


class bold(DndTag):
    wrap_command = "textbf"


class b(bold):
    pass


class italic(DndTag):
    wrap_command = "textit"


class i(italic):
    pass


class creature(DndTag):
    def get_content(self):
        name = self.args[0].lower()
        source = "mm"
        display_name = self.args[0]
        if len(self.args) > 1:
            source = self.args[1].lower()
        self.creatureList[name] = source
        if len(self.args) == 3:  # Don't textbf if it has a display name.
            return self.args[2]

        return f"\\textbf{{{display_name}}}"


class quickref(DndTag):
    pass


class deck(DndTag):
    def get_content(self):
        if len(self.args) == 3:
            return self.args[2]
        else:
            return self.args[0]


class skillCheck(DndTag):
    def get_content(self):
        modifier = int(self.args[0].split(" ")[1])
        return f"{modifier:+}"


class ability(DndTag):
    def get_content(self):
        modifier = int(self.args[1])
        return f"{modifier:+}"


class savingThrow(DndTag):
    def get_content(self):
        modifier = int(self.args[0].split(" ")[1])
        return f"{modifier:+}"


class dice(DndTag):
    def setup(self):
        if self.args[0].startswith("d"):
            self.args[0] = f"1{self.args[0]}"


class damage(dice):
    pass


class spell(italic):
    def get_content(self):
        name = self.args[0].lower()
        source = "phb"
        if len(self.args) > 1:
            source = self.args[1].lower()

        self.spellList.add((name, source))
        return self.content


class strikeout(DndTag):
    wrap_command = "sout"


class s(strikeout):
    pass


class h(DndTag):
    static_string = "\\textsl{Hit:} "


class hit(DndTag):
    def get_content(self):
        if isinstance(self.args[0], str):
            return self.args[0]
        toHit = int(self.args[0])
        return f"{toHit:+}"


class chance(DndTag):
    def get_content(self):
        return self.args[-1]


class atk(DndTag):
    def get_content(self):
        atk = self.args[0].strip()
        map = {
            "mw,rw": "\\textsl{Melee or Ranged Weapon Attack:}",
            "rw": "\\textsl{Ranged Weapon Attack:}",
            "mw": "\\textsl{Melee Weapon Attack:}",
            "ms": "\\textsl{Melee Spell Attack:}",
            "rs": "\\textsl{Ranged Spell Attack:}",
            "ms,rs": "\\textsl{Melee or Ranged Spell Attack:}",
            "mp": "\\textsl{Melee Psionic Attack:}",
            "rp": "\\textsl{Ranged Psionic Attack:}",
            "mp,rp": "\\textsl{Melee or Ranged Psionic Attack:}",
            "m": "\\textsl{Melee Attack?}",
        }
        logging.debug(self.args)
        return map[atk]


class dc(DndTag):
    def get_content(self):
        return f"DC {self.args[0]}"


class creatureList(DndTag):
    def get_content(self):
        lines = []
        tokens = {}
        columns_for = {
            "Unknown": 7,
            "Tiny": 7,
            "Small": 7,
            "Medium": 7,
            "Large": 3,
            "Huge": 2,
            "Gargantuan": 1,
        }
        count = 0
        clear_freq = 20
        lst = open("creature-list.json", "w", encoding="utf8")
        for name, source in sorted(self.creatureList.items()):
            lst.write(f'"{{@creature {name}|{source}}}",\n')

            cData = Util.findCreatureData(name, source)
            if not cData:
                logging.error("Could not find %s (%s)", name, source)
                continue

            c = dndtex.Creature(cData)
            if not c._data:
                warnings.warn(
                    f"Failed to locate creature: {name} ({source})", UserWarning
                )
            else:
                if c.token:
                    size = c.size
                    if size in ("Tiny", "Small"):
                        size = "Medium"

                    if size not in tokens:
                        if size not in columns_for:
                            size = "Unknown"
                        tokens[size] = []

                    tokens[size].append(c.token)
                # try:
                lines += c.renderCreature(self.renderer)
                count += 1
                if count % clear_freq == 0:
                    lines.append("\\clearpage")
                # except(AttributeError):
                #     warnings.warn(f"Failed to find referenced creature: {name} ({source})",UserWarning)
        for line in lines:
            if not isinstance(line, str):
                logging.warning("Not a string: %s", line)

        lst.close()

        if tokens:
            token_lines = [
                r"""
\documentclass{article}
\usepackage{graphicx}
\usepackage{multicol}
\usepackage{pgffor}
\usepackage{tikz}
\usepackage[a4paper, margin=0.4cm]{geometry} 
\usepackage{onimage}
\usepackage{contour}
\usepackage{fontspec}
\geometry{left=0.5cm, right=0.5cm, top=0.5cm, bottom=0.5cm}
\newfontfamily{\dndsans}{scala-sans-regular.otf}[%
    BoldFont=scala-sans-bold.otf,%
    ItalicFont=scala-sans-regular-italic.otf,%
    BoldItalicFont=scala-sans-bold-italic.otf
]
\begin{document}
\newcounter{tokencount}
\newcounter{currentcol}
\newcount\numcols
\newlength{\SizeTiny}
\setlength{\SizeTiny}{1.05in}
\newlength{\SizeMedium}
\setlength{\SizeMedium}{1.05in}
\newlength{\SizeLarge}
\setlength{\SizeLarge}{2.05in}
\newlength{\SizeHuge}
\setlength{\SizeHuge}{3.05in}
\newlength{\SizeGargantuan}
\setlength{\SizeGargantuan}{4.05in}
\setlength{\columnsep}{10pt}

                """.lstrip()
            ]
            for size, images in tokens.items():
                columns = columns_for[size]
                token_lines += [
                    "\\newpage",
                    f"\\numcols={columns}",
                    f"\\setlength{{\\columnwidth}}{{\\Size{size}}}",
                    "\\setcounter{currentcol}{0}",
                ]

                for img in images:
                    token_lines += [
                        f"%%\n%%%%\n%%%%%%\n%%%%%%%% {size} {img}",
                        "\\setcounter{tokencount}{ 1 }",
                        "\\foreach \\i in {1,...,\\thetokencount}",
                        " \\ifnum\\value{currentcol}=0\\noindent\\fi",
                        "\\begin{minipage}[t]{\\columnwidth}",
                        f" \\begin{{tikzonimage}}[width=\\columnwidth]{{{img}}}[inner sep=0pt]%[tsx/show help lines]",
                        "\\ifnum\\value{tokencount}>1",
                        "  \\node[at={( 0.666,0.245 )},text=white]{\\contour{black}{\\large\\dndsans{\\i}}};",
                        "\\fi",
                        "\\end{tikzonimage}",
                        "\\end{minipage}",
                        "\\stepcounter{currentcol}",
                        "\\ifnum\\value{currentcol}=\\numexpr\\numcols\\relax",
                        "  \\setcounter{currentcol}{0} \\par",
                        "\\fi",
                    ]

            token_lines.append("\\end{document}")
            t = open("tokens.tex", "w", encoding="UTF8")
            t.write("\n".join(token_lines))
            t.close()

        return "\n".join(lines)


class itemList(DndTag):
    def get_content(self):
        lines = []
        lst = open("item-list.json", "w", encoding="utf8")
        for name, source in sorted(self.itemList.items()):
            lst.write(f'"{{@item {name}|{source}}}",\n')

            i = dndtex.Item(Util.findItemData(name, source))
            if not i:
                warnings.warn(f"Failed to locate item: {name} ({source})", UserWarning)
            else:
                lines += i.render(self.renderer)
        for line in lines:
            if not isinstance(line, str):
                logging.warning("Not a string: %s", line)

        lst.close()

        return "\n".join(lines)


class spellList(DndTag):
    def get_content(self):
        lines = []
        for name, source in sorted(self.spellList):
            s = dndtex.Spell(Util.findSpellData(name, source))
            if not s:
                logging.warning("Failed to locate spell: %s (%s))", name, source)
            else:
                lines += s.render(self.renderer)

        for line in lines:
            if not isinstance(line, str):
                logging.warning("Not a string: %s", line)

        return "\n".join(lines)


class item(DndTag):
    def get_content(self):
        name = self.args[0].strip()
        source = self.args[1] if len(self.args) > 1 else "dmg"
        self.itemList[name] = source

        if len(self.args) == 3:  # Don't textbf if it's got an alias.
            return name

        return "\\textit{" + name + "}"


class variantrule(DndTag):
    def get_content(self):
        name = self.args[0].strip()
        return name


class itemEntry(DndTag):
    def get_content(self):
        # Load named item
        # Return entries of that item
        logging.debug("itemEntry: %s", self.args[0])
        itemData = Util.findBaseItemData(self.args[0], self.args[1])
        if not itemData:
            logging.warning(
                "Failed to lookup itemEntry for %s (%s)", self.args[0], self.args[1]
            )
            return ""
        return "\n\n".join(itemData["entriesTemplate"])


class condition(DndTag):
    pass


class action(DndTag):
    pass


class skill(DndTag):
    pass


class sense(DndTag):
    pass


class card(DndTag):
    pass


class hazard(DndTag):
    pass


class race(DndTag):
    pass


class status(DndTag):
    pass


class background(DndTag):
    pass


class adventure(DndTag):
    pass


class book(italic):
    pass
