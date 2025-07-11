"""Main CLI application for 5e2pdf."""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich import print as rprint

from src.core.loaders.omnidexer import Omnidexer
from src.core.indexer.tag_resolver import TagResolver
from src.core.models.content import ContentType
from src.renderers.base import RenderContext
from src.renderers.latex import LaTeXDocumentRenderer

# Create the main Typer app
app = typer.Typer(
    name="5e2pdf",
    help="Convert D&D 5e JSON data to beautifully formatted LaTeX/PDF documents",
    rich_markup_mode="rich"
)

# Add console for rich output
console = Console()

# Global state
_omnidexer: Optional[Omnidexer] = None
_tag_resolver: Optional[TagResolver] = None


@app.command("version")
def show_version():
    """Show version information."""
    rprint("[bold blue]5e2pdf[/bold blue] [green]v2.0.0[/green] - Modern Architecture")
    rprint("Convert D&D 5e JSON → LaTeX → PDF")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
):
    """
    🎲 **5e2pdf** - Modern D&D 5e content converter
    
    Convert structured JSON data from 5e.tools into professional LaTeX documents
    that match the style of official D&D 5th edition books.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


async def get_omnidexer() -> Omnidexer:
    """Get or create the global omnidexer instance."""
    global _omnidexer
    if _omnidexer is None:
        _omnidexer = Omnidexer()
        with Progress() as progress:
            task = progress.add_task("[cyan]Loading content data...", total=None)
            await _omnidexer.load_all_data()
            progress.update(task, completed=100)
    return _omnidexer


async def get_tag_resolver() -> TagResolver:
    """Get or create the global tag resolver instance."""
    global _tag_resolver
    if _tag_resolver is None:
        omnidexer = await get_omnidexer()
        _tag_resolver = TagResolver(omnidexer)
    return _tag_resolver


# Import and mount CLI command modules
try:
    from src.cli.commands.convert import app as convert_app
    from src.cli.commands.list_content import app as list_app
    from src.cli.commands.info import app as info_app
    from src.cli.commands.stats import app as stats_app
    
    # Mount sub-applications
    app.add_typer(convert_app, name="convert")
    app.add_typer(list_app, name="list")
    app.add_typer(info_app, name="info")
    app.add_typer(stats_app, name="stats")
except ImportError as e:
    # Fallback placeholder commands if imports fail
    @app.command("convert")
    def convert_command():
        """Convert content to LaTeX/PDF (placeholder)."""
        rprint("[yellow]Convert command not yet implemented[/yellow]")
    
    @app.command("list") 
    def list_command():
        """List available content (placeholder)."""
        rprint("[yellow]List command not yet implemented[/yellow]")
    
    @app.command("info")
    def info_command():
        """Show content information (placeholder).""" 
        rprint("[yellow]Info command not yet implemented[/yellow]")
    
    @app.command("stats")
    def stats_command():
        """Show content statistics (placeholder)."""
        rprint("[yellow]Stats command not yet implemented[/yellow]")


@app.command("legacy")
def legacy_mode(
    args: List[str] = typer.Argument(..., help="Legacy command line arguments")
):
    """
    🔄 **Legacy Mode** - Run commands with backwards compatibility
    
    Execute legacy json2tex.py commands using the modern architecture.
    Maintains full compatibility with existing scripts and workflows.
    
    Examples:
      5e2pdf legacy --adventure --no-images data.json > output.tex
      5e2pdf legacy --book --with-images book.json > book.tex
    """
    from src.cli.compat import LegacyCompatLayer
    compat = LegacyCompatLayer()
    result = compat.execute_legacy_command(args)
    if result:
        console.print(result)


@app.command("serve")
def serve_api(
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload")
):
    """
    🚀 **API Server** - Start REST API server (Future Feature)
    
    Launch a web API for converting D&D content remotely.
    """
    rprint("[yellow]API server feature coming in future release![/yellow]")
    rprint("For now, use the CLI commands or legacy mode.")


@app.command("quick")
def quick_convert(
    input_file: Path = typer.Argument(..., help="Input JSON file"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    content_type: str = typer.Option("auto", "--type", "-t", 
                                   help="Content type (adventure, book, auto)"),
    with_images: bool = typer.Option(False, "--images", help="Include images"),
    compile_pdf: bool = typer.Option(False, "--pdf", help="Compile to PDF")
):
    """
    ⚡ **Quick Convert** - Fast single-file conversion
    
    Convert a single JSON file to LaTeX with minimal configuration.
    Perfect for quick conversions and testing.
    """
    async def _quick_convert():
        try:
            # Validate input
            if not input_file.exists():
                rprint(f"[red]Error:[/red] Input file not found: {input_file}")
                raise typer.Exit(1)
            
            # Determine output file
            if output_file is None:
                output_path = input_file.with_suffix('.tex')
            else:
                output_path = output_file
            
            # Load omnidexer and tag resolver
            with Progress() as progress:
                load_task = progress.add_task("[cyan]Initializing...", total=None)
                omnidexer = await get_omnidexer()
                tag_resolver = await get_tag_resolver()
                progress.update(load_task, completed=100)
            
            # Load content from file
            import json
            with open(input_file) as f:
                data = json.load(f)
            
            # Simple content detection and loading
            content_items = []
            for key, items in data.items():
                if isinstance(items, list):
                    for item_data in items:
                        # Add source info if missing
                        if 'source' not in item_data:
                            item_data['source'] = {
                                'abbreviation': input_file.stem.upper(),
                                'name': input_file.stem.replace('-', ' ').title()
                            }
                        
                        # Try to create appropriate model
                        if key in ['spell', 'spells']:
                            from src.core.models.spells import Spell
                            content_items.append(Spell.model_validate(item_data))
                        elif key in ['monster', 'monsters', 'creature', 'creatures']:
                            from src.core.models.creatures import Creature  
                            content_items.append(Creature.model_validate(item_data))
                        elif key in ['item', 'items']:
                            from src.core.models.items import Item
                            content_items.append(Item.model_validate(item_data))
            
            if not content_items:
                rprint("[yellow]Warning:[/yellow] No recognized content found in file")
                raise typer.Exit(1)
            
            # Create render context
            context = RenderContext(
                title=f"D&D Content from {input_file.name}",
                include_images=with_images,
                include_toc=len(content_items) > 5,
                omnidexer=omnidexer,
                tag_resolver=tag_resolver
            )
            
            # Render document
            renderer = LaTeXDocumentRenderer()
            with Progress() as progress:
                render_task = progress.add_task("[green]Rendering document...", total=None)
                result = renderer.render_document(content_items, context)
                progress.update(render_task, completed=100)
            
            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result, encoding='utf-8')
            
            rprint(f"[green]✓[/green] Converted {len(content_items)} items to {output_path}")
            
            # Compile PDF if requested
            if compile_pdf and output_path.suffix == '.tex':
                pdf_path = output_path.with_suffix('.pdf')
                rprint(f"[cyan]Compiling PDF: {pdf_path}[/cyan]")
                import subprocess
                try:
                    subprocess.run(['xelatex', '-output-directory', str(output_path.parent), 
                                  str(output_path)], check=True, capture_output=True)
                    rprint(f"[green]✓[/green] PDF compiled: {pdf_path}")
                except subprocess.CalledProcessError as e:
                    rprint(f"[red]Error compiling PDF:[/red] {e}")
                except FileNotFoundError:
                    rprint("[yellow]Warning:[/yellow] xelatex not found. Install LaTeX to compile PDFs.")
            
        except Exception as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_quick_convert())


if __name__ == "__main__":
    app()