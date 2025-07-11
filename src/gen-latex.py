#!/usr/bin/env python3

import sys
import GetOptions

from dndtex.Renderer import Renderer


def main():
    params_config = {
        "article": {
            "false": True,
            "data": False,
            "short": "a",
            "long": "article",
            "default": False,
        }
    }
    opt = GetOptions.get(params_config)
    options = opt["data"]
    filename = opt["args"][0]

    renderer = Renderer(filename, article=options.get("article", False))
    renderer.render()
    # renderer.makePDF(sys.argv[2])


if __name__ == "__main__":
    main()
