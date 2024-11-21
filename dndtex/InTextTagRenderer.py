import re
from dndtex.tags import *
from dndtex import DndTexError
from dndtex.log import logging
from dndtex import Util

class InTextTagRenderer:
    creatureList = dict()
    spellList = set()
    itemList = dict()
    '''
    Resolves all tags in a string
    '''
    @staticmethod
    def renderLine(line, renderer):
        # special case, single tag on one line?
        OneLineTagPattern = r"^\{(?P<type>[@#])(?P<tag>.*?) (?P<args>.*?)\}$"
        standalone_tag = re.search(OneLineTagPattern, line)
        if standalone_tag:
            tag_name = standalone_tag.group('tag')
            tag_args = standalone_tag.group('args')
            if tag_name == "optfeature":
                return "\\paragraph{Optional Feature}\n" + tag_args
            elif tag_name == "deity":
                parts = tag_args.split('|')
                deityData = Util.findDeityData(parts[0], parts[1], parts[2])
                return renderer.renderDeity(deityData)
                
        TagPattern = r"\{[@#].*?\}"
        tags = re.findall(TagPattern, line)
        while tags:
            for tag_string in tags:
                if not isinstance(tag_string, str):
                    logging.error("Searching tag_string but it's a dict? %s", tag_string)
                match = re.search(r"\{(?P<type>[@#])(?P<name>.*?) (?P<args>.*?)\}", tag_string)
                if not match:
                    match = re.search(r"\{(?P<type>[@#])(?P<name>.*?)\}", tag_string)
                    if not match:
                        raise DndTexError(f"Failed to handle tag: '{tag_string}'")
                    tag_arguments = None
                else:
                    # logging.debug("Got line: %s", line)
                    # logging.debug("Matched: %s %s %s", match.group('type'), match.group('name'), match.group('args'))
                    tag_arguments = match.group('args').split('|')
                tag_name = match.group('name')
                if tag_name not in globals():
                    logging.warning("Tag %s is not implemented: %s(%s)", match.group('type'), tag_name, tag_arguments)
                    tag_name = 'unknown'
                tag = globals()[tag_name](tag_arguments, creatureList=InTextTagRenderer.creatureList,
                                          spellList=InTextTagRenderer.spellList, renderer=renderer,
                                          itemList=InTextTagRenderer.itemList)
                content = tag.get_content()
                line = line.replace(tag_string, content)
            tags = re.findall(TagPattern, line)
        return line
