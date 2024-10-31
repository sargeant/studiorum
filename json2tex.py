#!/usr/bin/env python3

import GetOptions

from dndtex.Renderer import Renderer

def main():
    params_config = {
        'article':          {'data': False, 'short': 'a', 'long': 'article',        'default': False},
        'book':             {'data': False, 'short': 'b', 'long': 'book',           'default': None},
        'adventure':        {'data': False, 'short': 'v', 'long': 'adventure',      'default': None},
        'addCreatureList':  {'data': False, 'short': 'c', 'long': 'add-creatures',  'default': False},
        'addSpellList':     {'data': False, 'short': 's', 'long': 'add-spells',     'default': False},
        'noImages':         {'data': False, 'short': 'n', 'long': 'no-images',      'default': False},
        'includePart':      {'data': False, 'short': 't', 'long': 'part',           'default': False},
        'addItemList':      {'data': False, 'short': 'i', 'long': 'add-items',      'default': False},
        'imagePath':        {'data': True,  'short': 'p', 'long': 'images',         'default': None}
    }

    opt = GetOptions.get(params_config)
    options = opt['data']
    filename = opt['args'][0]

    renderer = Renderer(filename, options)
    renderer.render()
    
if __name__ == "__main__":
    main()
    