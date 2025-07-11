"""Backwards compatibility layer for legacy json2tex.py commands."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import re

from src.core.loaders.omnidexer import Omnidexer
from src.core.indexer.tag_resolver import TagResolver
from src.renderers.base import RenderContext
from src.renderers.latex import LaTeXDocumentRenderer


class LegacyCompatLayer:
    """
    Provides backwards compatibility with the original json2tex.py script.
    
    This class parses legacy command line arguments and executes them using
    the modern architecture, maintaining full compatibility with existing
    scripts and workflows.
    """
    
    def __init__(self):
        self.omnidexer: Optional[Omnidexer] = None
        self.tag_resolver: Optional[TagResolver] = None
    
    async def _ensure_loaded(self):
        """Ensure omnidexer and tag resolver are loaded."""
        if self.omnidexer is None:
            self.omnidexer = Omnidexer()
            await self.omnidexer.load_all_data()
            self.tag_resolver = TagResolver(self.omnidexer)
    
    def execute_legacy_command(self, args: List[str]) -> str:
        """
        Execute a legacy json2tex.py command using modern architecture.
        
        Args:
            args: Command line arguments in legacy format
            
        Returns:
            Generated LaTeX content as string
        """
        try:
            # Parse legacy arguments
            parsed_args = self._parse_legacy_args(args)
            
            # Execute using modern architecture
            return asyncio.run(self._execute_modern_equivalent(parsed_args))
            
        except Exception as e:
            return f"% Error: {e}\n% Please check your command syntax\n"
    
    def _parse_legacy_args(self, args: List[str]) -> Dict[str, Any]:
        """
        Parse legacy command line arguments.
        
        Legacy format examples:
          --adventure --no-images file.json
          --book --with-images --add-items file.json
          --supplement --add-creatures file.json
        """
        parsed = {
            'content_type': 'auto',
            'input_file': None,
            'include_images': False,
            'include_items': True,
            'include_creatures': True,
            'include_spells': True,
            'include_toc': True,
            'include_index': False,
            'title': None,
            'output_format': 'latex'
        }
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            # Content type flags
            if arg in ['--adventure', '-a']:
                parsed['content_type'] = 'adventure'
            elif arg in ['--book', '-b']:
                parsed['content_type'] = 'book'
                parsed['include_index'] = True
            elif arg in ['--supplement', '-s']:
                parsed['content_type'] = 'supplement'
            
            # Image flags
            elif arg in ['--no-images', '--no-image']:
                parsed['include_images'] = False
            elif arg in ['--with-images', '--images', '--image']:
                parsed['include_images'] = True
            
            # Content inclusion flags
            elif arg in ['--add-items', '--items']:
                parsed['include_items'] = True
            elif arg in ['--no-items', '--no-item']:
                parsed['include_items'] = False
            elif arg in ['--add-creatures', '--creatures']:
                parsed['include_creatures'] = True
            elif arg in ['--no-creatures', '--no-creature']:
                parsed['include_creatures'] = False
            elif arg in ['--add-spells', '--spells']:
                parsed['include_spells'] = True
            elif arg in ['--no-spells', '--no-spell']:
                parsed['include_spells'] = False
            
            # Table of contents
            elif arg in ['--toc', '--table-of-contents']:
                parsed['include_toc'] = True
            elif arg in ['--no-toc', '--no-table-of-contents']:
                parsed['include_toc'] = False
            
            # Index
            elif arg in ['--index']:
                parsed['include_index'] = True
            elif arg in ['--no-index']:
                parsed['include_index'] = False
            
            # Title
            elif arg in ['--title', '-t']:
                if i + 1 < len(args):
                    parsed['title'] = args[i + 1]
                    i += 1
            
            # Help
            elif arg in ['--help', '-h']:
                return {'help': True}
            
            # Version
            elif arg in ['--version', '-v']:
                return {'version': True}
            
            # Input file (last positional argument)
            elif not arg.startswith('-'):
                parsed['input_file'] = arg
            
            i += 1
        
        return parsed
    
    async def _execute_modern_equivalent(self, parsed_args: Dict[str, Any]) -> str:
        """
        Execute the parsed legacy command using modern architecture.
        
        Args:
            parsed_args: Parsed legacy arguments
            
        Returns:
            Generated LaTeX content
        """
        # Handle help and version
        if parsed_args.get('help'):
            return self._get_legacy_help()
        
        if parsed_args.get('version'):
            return "5e2pdf v2.0.0 (Legacy Compatibility Mode)\n"
        
        # Validate input file
        input_file = parsed_args.get('input_file')
        if not input_file:
            raise ValueError("No input file specified")
        
        input_path = Path(input_file)
        if not input_path.exists():
            raise ValueError(f"Input file not found: {input_file}")
        
        # Ensure modern architecture is loaded
        await self._ensure_loaded()
        
        # Load and parse content
        content_items = await self._load_legacy_content(input_path, parsed_args)
        
        if not content_items:
            raise ValueError("No valid content found in input file")
        
        # Create render context
        context = RenderContext(
            title=parsed_args.get('title'),
            include_images=parsed_args.get('include_images', False),
            include_toc=parsed_args.get('include_toc', True),
            include_index=parsed_args.get('include_index', False),
            include_items=parsed_args.get('include_items', True),
            include_creatures=parsed_args.get('include_creatures', True),
            include_spells=parsed_args.get('include_spells', True),
            omnidexer=self.omnidexer,
            tag_resolver=self.tag_resolver
        )
        
        # Render using modern architecture
        renderer = LaTeXDocumentRenderer()
        return renderer.render_document(content_items, context)
    
    async def _load_legacy_content(self, input_path: Path, parsed_args: Dict[str, Any]) -> List[Any]:
        """
        Load content from legacy JSON file format.
        
        Args:
            input_path: Path to input JSON file
            parsed_args: Parsed command arguments
            
        Returns:
            List of content objects
        """
        # Load JSON data
        with open(input_path) as f:
            data = json.load(f)
        
        content_items = []
        content_type = parsed_args.get('content_type', 'auto')
        
        # Import content models
        from src.core.models.spells import Spell
        from src.core.models.creatures import Creature
        from src.core.models.items import Item
        from src.core.models.adventures import Adventure
        from src.core.models.books import Book
        
        # Type-specific loading
        if content_type == 'adventure':
            # Load as adventure
            if 'adventure' in data:
                adventure_data = data['adventure']
                if isinstance(adventure_data, list):
                    for item in adventure_data:
                        content_items.append(Adventure.model_validate(item))
                else:
                    content_items.append(Adventure.model_validate(adventure_data))
            else:
                # Treat entire file as adventure
                content_items.append(Adventure.model_validate(data))
        
        elif content_type == 'book':
            # Load as book
            if 'book' in data:
                book_data = data['book']
                if isinstance(book_data, list):
                    for item in book_data:
                        content_items.append(Book.model_validate(item))
                else:
                    content_items.append(Book.model_validate(book_data))
            else:
                # Treat entire file as book
                content_items.append(Book.model_validate(data))
        
        else:
            # Auto-detect or supplement - load various content types
            type_handlers = {
                'spell': Spell,
                'spells': Spell,
                'monster': Creature,
                'monsters': Creature,
                'creature': Creature,
                'creatures': Creature,
                'item': Item,
                'items': Item,
                'adventure': Adventure,
                'adventures': Adventure,
                'book': Book,
                'books': Book
            }
            
            for key, items in data.items():
                if key in type_handlers and isinstance(items, list):
                    model_class = type_handlers[key]
                    for item_data in items:
                        try:
                            # Add source info if missing
                            if isinstance(item_data, dict) and 'source' not in item_data:
                                item_data['source'] = {
                                    'abbreviation': input_path.stem.upper(),
                                    'name': input_path.stem.replace('-', ' ').title()
                                }
                            content_items.append(model_class.model_validate(item_data))
                        except Exception as e:
                            # Skip invalid items but continue processing
                            print(f"Warning: Failed to parse {key} item: {e}", file=sys.stderr)
        
        return content_items
    
    def _get_legacy_help(self) -> str:
        """Return legacy-style help text."""
        return """
5e2pdf Legacy Compatibility Mode

USAGE:
    5e2pdf legacy [OPTIONS] <input_file.json>

CONTENT TYPE OPTIONS:
    --adventure, -a     Process as adventure content
    --book, -b         Process as book content (enables index)
    --supplement, -s   Process as supplement/mixed content

IMAGE OPTIONS:
    --no-images        Don't include images (default)
    --with-images      Include images in output
    --images           Alias for --with-images

CONTENT FILTERING:
    --add-items        Include item lists (default)
    --no-items         Don't include items
    --add-creatures    Include creature lists (default)
    --no-creatures     Don't include creatures
    --add-spells       Include spell lists (default)
    --no-spells        Don't include spells

DOCUMENT OPTIONS:
    --toc              Include table of contents (default)
    --no-toc           Don't include table of contents
    --index            Include index
    --no-index         Don't include index (default)
    --title TITLE      Set document title

OTHER OPTIONS:
    --help, -h         Show this help
    --version, -v      Show version

EXAMPLES:
    # Convert adventure without images
    5e2pdf legacy --adventure --no-images adventure-cos.json
    
    # Convert book with images and index
    5e2pdf legacy --book --with-images --index book-phb.json
    
    # Convert supplement with only creatures
    5e2pdf legacy --supplement --no-items --no-spells creatures.json

COMPATIBILITY:
This legacy mode maintains full compatibility with the original json2tex.py
script while using the modern architecture for improved performance and
reliability.
"""


def create_legacy_wrapper():
    """
    Create a legacy wrapper script for backwards compatibility.
    
    This creates a json2tex.py script that calls the modern CLI
    in legacy mode, maintaining complete backwards compatibility.
    """
    wrapper_script = '''#!/usr/bin/env python3
"""
Legacy json2tex.py wrapper for backwards compatibility.

This script maintains compatibility with the original json2tex.py
while using the modern 5e2pdf architecture underneath.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Execute legacy command using modern CLI."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Path to modern CLI
    cli_path = script_dir / "src" / "cli" / "main.py"
    
    if not cli_path.exists():
        print("Error: Modern CLI not found. Please ensure 5e2pdf is properly installed.", file=sys.stderr)
        sys.exit(1)
    
    # Execute modern CLI in legacy mode
    cmd = ["python3", str(cli_path), "legacy"] + sys.argv[1:]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output to stdout (for redirection)
        if result.stdout:
            print(result.stdout, end="")
        
        # Print errors to stderr
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"Error executing modern CLI: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    return wrapper_script