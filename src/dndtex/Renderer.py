"""Render json from 5e.tools into LaTeX for printing"""

import json
import re
import requests
import os

from dndtex import *
from dndtex.log import logging
from dndtex.InTextTagRenderer import InTextTagRenderer


class Renderer:
    def __init__(self, path, options):
        self.lines = []
        self.env_level = 0
        self.passedChapterHeading = False
        self.inAppendix = False
        self.creatures = []
        self.isArticle = options.get("article")
        self.addCreatureList = options.get("addCreatureList")
        self.addSpellList = options.get("addSpellList")
        self.addItemList = options.get("addItemList")
        self.imagePath = options.get("imagePath", "")
        self.processedImagePath = "images"
        self.includeImages = not options.get("noImages")
        self.includePartSection = options.get("includePart")
        self.useDropCap = False

        self.packages = [
            ["inputenc", "utf8"],
            "tabulary",
            ["ulem", "normalem"],
            "color,soul",
            "float",
            "caption",
            "wrapfig",
            "tocloft",
            ["multitoc", "toc"],
            ["hyperref", "hidelinks"],
            # "minitoc"
        ]

        self.init_document()
        fh = open(path, "r", encoding="utf8")
        json_data = json.load(fh)
        fh.close()
        if "data" in json_data:
            self._data = json_data["data"]
        elif options.get("book"):
            self._data = json_data["bookData"][0]["data"]
        elif options.get("adventure"):
            self._data = json_data["adventureData"][0]["data"]
        logging.debug("Data: %d", len(self._data))

    def init_document(self):
        document_type = "dndarticle" if self.isArticle else "dndbook"

        self.lines.append(
            f"\\documentclass[10pt,a4paper,twoside,bg=print,twocolumn,openany,nodeprecatedcode]{{{document_type}}}"
        )
        for package in self.packages:
            if isinstance(package, str):
                self.lines.append(r"\usepackage{%s}" % package)
            else:
                self.lines.append(r"\usepackage[%s]{%s}" % (package[1], package[0]))

        self.lines.append("\\raggedbottom")
        self.lines.append("\\extrafloats{2000}")
        self.lines.append("\\cftsetindents{section}{0em}{0em}")
        self.lines.append("\\cftsetindents{subsection}{0em}{0em}")
        self.lines.append("\\cftsetindents{subsubsection}{0.2em}{0em}")

        self.lines.append("\\setcounter{tocdepth}{1}")
        self.lines.append("\\renewcommand*{\\multicolumntoc}{3}")

        self.lines += [
            "\\setlist[description]{nolistsep,listparindent=3pt,topsep=6pt}",
            # "\\definecolor {mytable} {HTML} {f4edd8}",
            # "\\definecolor {mycomment} {HTML} {ffffff}",
            # "\\definecolor {mysidebar} {HTML} {d0cfc2}",
            # "\\definecolor {myreadaloud} {HTML} {d9e8f1}",
            # "\\definecolor {myreadaloudborder} {HTML} {5a6173}",
            # "\\definecolor {mypagenum} {HTML} {2a2d2e}",
            # "\\DndSetComplexThemeColor[mytable][mycomment][mysidebar][myreadaloud][myreadaloudborder][titlered][titlegold][titlegold]"
            # "\\title{"
            # " \\Huge \scshape \\nodesto\\fontsize{50}{40}\\selectfont",
            # " Encyclopedia Exandria \\\\",
            # " \\medskip",
            # " \\nodesto",
            # " \\medskip\\Huge",
            # " A compendium of the Critical Role world}"
            "\\date{}",
        ]

        self.lines.append("\\begin{document}")

        if not self.isArticle:
            self.lines.append("\\frontmatter")
            # self.lines.append("\\maketitle")
            self.lines.append("\\tableofcontents")
            self.lines.append("\\mainmatter")

    def render(self):
        for section in self._data:
            self.lines.extend(self.renderRecursive(-1, section))

        if self.addItemList:
            self.lines.append("\\chapter{Magic Items}")
            self.lines.append("{@itemList}")

        if self.addCreatureList:
            self.lines.append("\\chapter*{Printable Statblocks}")
            self.lines.append(
                "\\setlist[description]{nolistsep,listparindent=3pt,topsep=6pt,font={\\bfseries\\sffamily\\small}}"
            )
            self.lines.append("\\pagestyle{empty}")
            self.lines.append("{@creatureList}")

        if self.addSpellList:
            self.lines.append("\\chapter{Spells}")
            # self.lines.append("\\minitoc")
            self.lines.append("{@spellList}")

        self.lines.append("\\end{document}")

        self.lines = [InTextTagRenderer.renderLine(line, self) for line in self.lines]

        print("\n".join(self.lines))

    def renderRecursive(self, depth, data):
        lines = []
        depth = depth + 1
        if isinstance(data, str):
            if self.passedChapterHeading and not self.inAppendix:
                if not data.startswith("{@"):  # Skip the tag at the start
                    if self.useDropCap:
                        data = self.addDropCap(data)
            tag_expanded_data = InTextTagRenderer.renderLine(data, self)
            lines.append(self.escapeTex(tag_expanded_data))
            lines.append("")
        elif isinstance(data, int):
            return self.renderRecursive(depth, str(data))
        elif isinstance(data, list):
            for entry in data:
                lines += self.renderRecursive(depth, entry)
        elif data.get("type") == "section" or data.get("type") == "entries":
            lines += self.renderSection(depth, data)
        elif data.get("type") == "inset":
            lines += self.renderInset(depth, data)
        elif data.get("type") == "insetReadaloud":
            lines += self.renderReadAloudInset(depth, data)
        elif data.get("type") == "table":
            lines += self.renderTable(data)
        elif data.get("type") == "list":
            lines += self.renderList(data)
        elif data.get("type") == "quote":
            lines += self.renderQuote(data)
        elif data.get("type") == "image":
            if self.includeImages:
                lines += self.renderImage(data)
        elif data.get("type") == "statblockInline":
            lines += self.renderStatblock(data)
        elif data.get("type") == "statblock":
            lines += self.renderStatblock(data)
        elif data.get("type") == "row":
            lines.extend(data.get("row"))
        elif data.get("type") == "cell":
            lines += self.renderCell(data)
        elif data.get("type") == "gallery":
            if self.includeImages:
                lines += self.renderGallery(data)
        elif data.get("type") in ("flowchart"):
            lines += self.renderFlowchart(data)
        else:
            logging.warning("Data type not implemented: %s", data)
        return lines

    def renderDeity(self, data):
        lines = []
        lines.append(f"\\subsubsection{{{data['name']}}}")
        # lines.append(f"\\paragraph{{Alignment:}}")
        # lines.append(Util.alignment_string(data['alignment']).title())
        # if "altNames" in data:
        #     lines.append(f"\\paragraph{{Alternate Names:}}")
        #     lines.append(", ".join(data['altNames']))
        # if "category" in data:
        #     lines.append(f"\\paragraph{{Category:}}")
        #     lines.append(data['category'])
        # lines.append(f"\\paragraph{{Domains:}}")
        # lines.append(", ".join(data['domains']))
        # lines.append(f"\\paragraph{{Pantheon:}}")
        # lines.append(data['pantheon'])
        # lines.append(f"\\paragraph{{Province:}}")
        # lines.append(data['province'])
        lines += self.renderRecursive(5, data["entries"])
        if "symbol" in data:
            lines.append("\\subparagraph{Symbol}")
            lines.append(data["symbol"])

        # We're calling this from a tag-hack to lookup deity data that happens
        # after the first InTextTagRenderer, so we call it again.
        lines = [InTextTagRenderer.renderLine(line, self) for line in lines]

        return "\n".join(lines)

    def renderFlowchart(self, data):
        # transform the data into a list
        logging.debug(data)
        return []

    def renderGallery(self, data):
        lines = []
        for image in data["images"]:
            lines += self.renderImage(image)
        return lines

    def renderCell(self, data):
        lines = []
        logging.debug(data)
        roll = data.get("roll")
        if roll:
            if "exact" in roll:
                lines.append(str(roll["exact"]))
            else:
                min = roll["min"]
                max = roll["max"]
                lines.append(f"{min}\u2014{max}")
        else:
            lines.append(data["entry"])
        return lines

    def renderSection(self, depth, data):
        titles = [
            # "part",
            "chapter",
            "section",
            "subsection",
            "subsubsection",
            "subparagraph",
        ]
        if self.isArticle:
            titles.pop(0)  ## Articles don't have chapters...
        if self.includePartSection:
            titles.insert(0, "part")

        lines = []

        if (
            data.get("name")
            and data.get("name").startswith("Appendix")
            and not self.inAppendix
        ):
            # lines += ["\\onecolumn"]
            lines += ["\\appendix"]
            self.inAppendix = True

        if depth == 0:
            self.passedChapterHeading = True
            if data.get("name").find("Introduction") >= 0:
                titles[0] = "chapter*"
                lines.append(f"\\addcontentsline{{toc}}{{chapter}}{{{data['name']}}}")
                upper_name = data["name"].upper()
                lines.append(f"\\markboth{{{upper_name}}}{{{upper_name}}}")
                # toc & markboth missing

        if "name" in data:
            if depth > len(titles) - 1:
                logging.info(
                    "Depth of renderSection exceeds titles: %d %s",
                    len(titles),
                    data["name"],
                )
                depth = len(titles) - 1

            data["name"] = re.sub(r"^Chapter .*: ", "", data.get("name"))
            data["name"] = re.sub(r"^Appendix .*: ", "", data.get("name"))

            section_name = self.escapeTex(data.get("name"))
            if section_name[-1] == ".":
                section_name = section_name[:-1]
            lines.append(f"\\{titles[depth]}{{{section_name}}}")

        for section in data.get("entries"):
            lines += self.renderRecursive(depth, section)
        return lines

    def renderTable(self, data):
        lines = []
        useLongTable = False
        titles = data.get("colLabels")
        alignmentStr = self.getAlignmentsStr(data.get("colStyles"))
        table_type = "DndTable"
        if useLongTable:
            table_type = "dndlongtable"
        if "caption" in data:
            lines += [
                str(
                    f"\\begin{{{table_type}}}[header=@CAPTION]".replace(
                        "@CAPTION", data.get("caption")
                    )
                    + alignmentStr
                    + "\n"
                )
            ]
        else:
            lines += [f"\n\\begin{{{table_type}}}" + alignmentStr + "\n"]
        if titles:
            lines += [str(" & ".join(titles) + "\\\\")]
        for row in data.get("rows"):
            if isinstance(row, list):
                row = ["".join(self.renderRecursive(1, cell)) for cell in row]
            elif isinstance(row, dict):
                row = self.renderRecursive(1, row)
            lines += [" & ".join(map(self.escapeTex, row)) + "\\\\"]
        lines += [str(f"\\end{{{table_type}}}\n")]
        return lines

    """
    Renders an inset. The content of the inset is passed through renderRecursive again.
    """

    def renderInset(self, depth, data):
        lines = []
        name = ""
        if "name" in data:
            name = self.escapeTex(data.get("name"))
        lines += ["\\begin{DndSidebar}[float=!b]{" + name + "}"]
        for section in data.get("entries"):
            lines += self.renderRecursive(depth, section)
            lines.append("\n")
        lines += ["\\end{DndSidebar}\n"]
        return lines

    def renderComment(self, data):
        lines = []
        name = ""
        if "name" in data:
            name = self.escapeTex(data.get("name"))
        lines += ["\\begin{DndComment}{" + name + "}"]
        for section in data.get("entries"):
            lines += self.renderRecursive(6, section)
            lines.append("\n")
        lines += ["\\end{DndComment}\n"]
        return lines

    """
    Renders a read aloud inset. The content of the inset is passed through renderRecursive again.
    """

    def renderReadAloudInset(self, depth, data):
        name = ""
        lines = []
        self.env_level += 1
        if "name" in data:
            name = self.escapeTex(data.get("name"))
        lines += ["\\begin{DndReadAloud}{" + name + "}"]
        for section in data.get("entries"):
            lines += self.renderRecursive(depth, section)
        lines += ["\\end{DndReadAloud}\n"]
        self.env_level -= 1
        return lines

    def renderList(self, data, depth=0):
        lines = []
        style = data.get("style")
        columns = data.get("columns")
        name = self.escapeTex(data.get("name"))

        if style == "list-hang-notitle" or style == "list-hang":
            list_type = "description"
        else:
            list_type = "itemize"

        if name:
            lines.append(
                f"{{\\par \\vspace {{ 9pt plus 3pt minus 3pt }} \\noindent  \\DndFontTableTitle{{{name}}} \\nopagebreak }}"
            )

        lines += [f"\n\\begin{{{list_type}}}"]

        if columns:
            lines.append(f"\\begin{{multicols}}{{{columns}}}")

        for item in data.get("items"):
            if isinstance(item, str):
                item = self.escapeTex(item)
                lines.append("\\item " + item)
            else:
                if item.get("type") == "list":
                    lines += self.renderList(item, depth)
                elif item.get("type") == "entries":
                    lines += self.renderRecursive(depth, item)
                elif item.get("type") == "item":
                    lines += self.renderListItem(item, depth, list_type)
                elif item.get("type") == "image":
                    lines += self.renderImage(item)
                elif item.get("type") == "statblock":
                    lines += self.renderStatblock(item)
                elif (
                    item.get("type") == "inset"
                ):  # What? Who puts an inset as a list item?!
                    # Lets try a DndComment and see what we get.
                    lines += self.renderComment(item)
                elif item.get("type") == "insetReadaloud":
                    lines += self.renderReadAloudInset(depth, item)
                else:
                    raise (DndTexUnhandled(item))

        if columns:
            lines.append("\\end{multicols}\n")

        lines += [f"\\end{{{list_type}}}\n"]

        return lines

    def renderListItem(self, item, depth, list_type):
        lines = []
        append = "."
        name = self.escapeTex(item.get("name"))
        if len(name) > 1 and name[-1] in (".", ":", ";", "?", "!"):
            append = ""
        if list_type == "description":
            lines.append(f"\\item[{name}{append}]")
        elif list_type == "itemize":
            lines.append(f"\\item{{{name}{append}}}")

        if "entry" in item:
            lines.append(self.escapeTex(item.get("entry")))
        elif "entries" in item:
            for entry in item.get("entries"):
                lines += self.renderRecursive(depth, entry)
        return lines

    def renderQuote(self, data):
        """
        Renders the quote environment.
        """
        lines = []
        lines += ["\\DndQuote%", "{}"]
        for line in data.get("entries"):
            line = self.escapeTex(line)
            lines += ["{''" + line + "''}"]
        if data.get("by"):
            lines += ["{" + data.get("by") + "}"]
        else:
            lines += ["{}"]
        return lines

    def renderImage(self, data, options=None):
        lines = []
        if options:
            lines = [f"\\begin{{figure}}[{options}]"]
        image_type = data["href"]["type"]
        if image_type == "external":
            image_url = data["href"]["url"]
            src_image_path = (
                f"{self.processedImagePath}/downloaded/{os.path.basename(image_url)}"
            )
            os.makedirs(os.path.dirname(src_image_path), exist_ok=True)

            fh = open(src_image_path, "wb")
            response = requests.get(image_url)
            fh.write(response.content)
            fh.close()

        elif image_type == "internal":
            src_image_path = self.imagePath + "/" + data["href"]["path"]
        else:
            logging.debug(data)
            raise DndTexUnhandled(f"Unknown image type {image_type}")

        target_image_path = Util.convertImage(src_image_path)

        lines.append(f"\\includegraphics[width=0.4\\textwidth]{{{target_image_path}}}")
        if options:
            lines.append("\\end{figure}")
        return lines

    def renderStatblock(self, data):
        """
        Renders statblocks
        """
        tag = data.get("tag")
        if tag in ("variantrule", "sense", "condition", "hazard", "action", "status"):
            name = data["name"]
            source = data["source"]
            extra_data = Util.load_extra_data(tag, name, source)
            lines = [f"\\subsection{{{name}}}"]
            lines += self.renderRecursive(4, extra_data)  # TODO: Hardcoded depth?
            return lines
        if data.get("type") == "statblockInline":
            creature_data = data["data"]
        else:
            creature_data = Util.findCreatureData(data["name"], data["source"])
        if not creature_data:
            logging.warning(
                f"Could not findCreatureData for {data['name']} ({data['source']})"
            )
            return [data["name"]]
        creature = Creature(creature_data)
        return creature.renderCreature(self)

    def addDropCap(self, line):
        if not line:
            return ""
        first_char = line[0]
        rest_chars = line[1:]
        self.passedChapterHeading = False
        return f"\\DndDropCapLine{{{first_char}}}{{}}{rest_chars}\n"

    @staticmethod
    def getAlignmentsStr(alignments):
        alignKey = {
            "text-align-left": "X",
            "text-align-center": "c",
            "text-align-right": "r",
        }
        out = []
        if not alignments:
            return "{}"
        for alignment in alignments:
            try:
                if alignment in alignKey:
                    out.append(alignKey.get(alignment))
                elif alignment.startswith("col-"):
                    if alignment.endswith(" text-center"):
                        out.append("c")
                    else:
                        out.append("X")
                else:
                    out.append("X")
            except:
                out.append("X")
        return "{" + "".join(out) + "}"

    def escapeTex(self, input):
        if input is None:
            return ""
        return (
            input.replace("&", "\\&")
            .replace("&quot;", '"')
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("#", "\\#")
        )
