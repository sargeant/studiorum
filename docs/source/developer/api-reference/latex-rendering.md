# LaTeX Rendering API Documentation

## Table of Contents

This page covers the LaTeX rendering system APIs:

- [LaTeXDocumentRenderer](#latexdocumentrenderer)
- [LaTeXTemplateEngine](#latextemplateengine)
- [RecursiveEntryProcessor](#recursiveentryprocessor)
- [ContentProcessor Classes](#contentprocessor-classes)
- [LaTeXCompiler](#latexcompiler)
- [Configuration Classes](#configuration-classes)
- [Error Handling](#error-handling)
- [Unicode Utilities](#unicode-utilities)

## Overview

The LaTeX rendering system provides a comprehensive API for transforming D&D content into professional PDF documents. The system is designed with modularity and extensibility in mind, allowing developers to customize every aspect of the rendering process.

### Key Features

- **Template-based rendering** with Jinja2 integration
- **Multi-engine compilation** (PDFLaTeX, XeLaTeX, LuaLaTeX)
- **Comprehensive error handling** and diagnostics
- **Unicode support** with LaTeX character mapping
- **Performance optimization** with caching and efficient processing

## LaTeXDocumentRenderer

**Location**: `src/dnd5e/renderers/latex/document.py`

The main orchestrator class for LaTeX document generation.

### Constructor

```python
def __init__(self, config: dict[str, Any] | None = None) -> None
```

Creates a new LaTeX document renderer with the specified configuration.

**Parameters:**
- `config` (dict[str, Any] | None): Configuration options for the renderer

**Example:**
```python
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer

# Basic initialization
renderer = LaTeXDocumentRenderer()

# With custom configuration
renderer = LaTeXDocumentRenderer({
    "templates_dir": "custom/templates",
    "use_dnd_template": True,
    "debug": True
})
```

### Core Methods

#### render

```python
def render(
    self,
    content: BaseContent,
    context: dict[str, Any] | None = None
) -> str
```

Renders a single content item as a minimal LaTeX document.

**Parameters:**
- `content` (BaseContent): Content object to render
- `context` (dict[str, Any] | None): Optional rendering context

**Returns:**
- `str`: Complete LaTeX document as string

**Example:**
```python
from dnd5e.core.models.spells import Spell

spell = Spell(name="Fireball", level=3, ...)
latex_output = renderer.render(spell)
```

#### render_document

```python
def render_document(
    self,
    content_items: Sequence[BaseContent],
    metadata: DocumentMetadata | None = None
) -> str
```

Renders multiple content items as a complete document with proper structure.

**Parameters:**
- `content_items` (Sequence[BaseContent]): List of content objects to render
- `metadata` (DocumentMetadata | None): Document metadata and settings

**Returns:**
- `str`: Complete LaTeX document with document structure

**Example:**
```python
from dnd5e.core.models.document_metadata import DocumentMetadata, DocumentType

metadata = DocumentMetadata(
    title="My Spell Collection",
    author="Dungeon Master",
    document_type=DocumentType.SUPPLEMENT
)

latex_doc = renderer.render_document(spell_list, metadata)
```

#### compile_to_pdf

```python
def compile_to_pdf(
    self,
    latex_content: str,
    output_path: Path
) -> CompilationResult
```

Compiles LaTeX content to PDF file.

**Parameters:**
- `latex_content` (str): LaTeX source code
- `output_path` (Path): Output PDF file path

**Returns:**
- `CompilationResult`: Compilation result with success status and errors

**Example:**
```python
from pathlib import Path

result = renderer.compile_to_pdf(latex_content, Path("output.pdf"))
if result.success:
    print(f"PDF generated: {result.output_path}")
else:
    print(f"Compilation failed: {result.errors}")
```

### Properties

#### output_format

```python
@property
def output_format(self) -> str
```

Returns the output format identifier ("latex").

**Returns:**
- `str`: Always returns "latex"

## LaTeXTemplateEngine

**Location**: `src/dnd5e/renderers/latex/template_engine.py`

Jinja2-based template engine with LaTeX-specific customizations.

### Constructor

```python
def __init__(self, config: dict[str, Any] | None = None) -> None
```

Initializes the template engine with LaTeX-specific settings.

**Parameters:**
- `config` (dict[str, Any] | None): Configuration options

**Configuration Options:**
- `templates_dir` (str): Template directory path
- `debug` (bool): Enable debug mode
- `cache_size` (int): Template cache size
- `auto_reload` (bool): Auto-reload templates in development

### Core Methods

#### render_template

```python
def render_template(
    self,
    template_name: str,
    context: dict[str, Any]
) -> str
```

Renders a template with the given context.

**Parameters:**
- `template_name` (str): Name of template file
- `context` (dict[str, Any]): Template variables

**Returns:**
- `str`: Rendered template content

**Example:**
```python
from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

engine = LaTeXTemplateEngine()
output = engine.render_template("spell_entry.tex.j2", {
    "spell": spell_object,
    "formatted_level": "3rd-level"
})
```

#### get_template

```python
def get_template(self, template_name: str) -> Template
```

Retrieves a compiled template object.

**Parameters:**
- `template_name` (str): Name of template file

**Returns:**
- `Template`: Jinja2 template object

### Template Filters

The template engine provides several LaTeX-specific filters:

#### latex_escape

```python
def latex_escape(value: str) -> str
```

Escapes LaTeX special characters and Unicode characters.

**Usage in templates:**
```latex
<# spell.description | latex_escape #>
```

#### dnd_ability_modifier

```python
def dnd_ability_modifier(score: int) -> str
```

Formats ability scores as modifiers (+2, -1, etc.).

**Usage in templates:**
```latex
<# creature.str | dnd_ability_modifier #>  <!-- +3 -->
```

#### dnd_challenge_rating

```python
def dnd_challenge_rating(cr: str | int | float) -> str
```

Formats challenge rating values.

**Usage in templates:**
```latex
<# creature.cr | dnd_challenge_rating #>  <!-- 1/4, 2, 10, etc. -->
```

#### dnd_spell_level

```python
def dnd_spell_level(level: int) -> str
```

Formats spell levels with proper ordinals.

**Usage in templates:**
```latex
<# spell.level | dnd_spell_level #>  <!-- Cantrip, 1st-level, etc. -->
```

## RecursiveEntryProcessor

**Location**: `src/dnd5e/renderers/latex/entry_processor.py`

Processes 5etools entry structures recursively into LaTeX content.

### Constructor

```python
def __init__(
    self,
    use_dnd_template: bool = True,
    validation_mode: ValidationMode | None = None
) -> None
```

Initializes the entry processor.

**Parameters:**
- `use_dnd_template` (bool): Whether to use DND template environments
- `validation_mode` (ValidationMode | None): Override validation mode

### Core Methods

#### process_entries

```python
def process_entries(
    self,
    entries: list[str | dict[str, Any]],
    context: RenderContext
) -> list[str]
```

Processes a list of entries into LaTeX content.

**Parameters:**
- `entries` (list): List of entry objects (strings or dicts)
- `context` (RenderContext): Rendering context with shared state

**Returns:**
- `list[str]`: List of processed LaTeX strings

**Example:**
```python
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor
from dnd5e.renderers.base import RenderContext

processor = RecursiveEntryProcessor()
context = RenderContext()

entries = [
    "This is plain text.",
    {
        "type": "insetReadaloud",
        "entries": ["You hear a strange noise..."]
    }
]

latex_output = processor.process_entries(entries, context)
```

#### get_processing_statistics

```python
def get_processing_statistics(self) -> dict[str, Any]
```

Returns processing statistics for performance monitoring.

**Returns:**
- `dict[str, Any]`: Statistics including entries processed, errors, etc.

## ContentProcessor Classes

**Location**: `src/dnd5e/renderers/latex/content_processor.py`

Base classes and implementations for enhanced content processing.

### ContentProcessor (Abstract Base)

```python
class ContentProcessor(ABC):
    @abstractmethod
    def process(self, content: BaseContent, context: RenderContext) -> dict[str, Any]:
        """Process content and return enhanced data."""
        pass

    @abstractmethod
    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports the content type."""
        pass
```

### SpellProcessor

Processes spell content with enhanced semantic information.

#### process

```python
def process(self, content: Spell, context: RenderContext) -> dict[str, Any]
```

**Returns enhanced spell data:**
- `spell_level_ordinal` (str): Formatted spell level
- `is_cantrip` (bool): Whether spell is a cantrip
- `is_ritual` (bool): Whether spell can be cast as ritual
- `damage_dice` (str | None): Extracted damage dice
- `concentration_required` (bool): Whether concentration is required
- `class_availability` (list[str]): Classes that can cast the spell

### CreatureProcessor

Processes creature content with computed statistics.

#### process

```python
def process(self, content: Creature, context: RenderContext) -> dict[str, Any]
```

**Returns enhanced creature data:**
- `proficiency_bonus` (int): Calculated proficiency bonus
- `ability_modifiers` (dict[str, int]): All ability modifiers
- `cr_category` (str): Challenge rating category
- `passive_perception` (int): Calculated passive perception
- `is_spellcaster` (bool): Whether creature can cast spells
- `is_legendary` (bool): Whether creature has legendary actions

## LaTeXCompiler

**Location**: `src/dnd5e/renderers/latex/compiler.py`

Multi-engine LaTeX compiler with comprehensive error handling.

### Constructor

```python
def __init__(self, config: CompilationConfig | None = None) -> None
```

Initializes compiler with configuration.

**Parameters:**
- `config` (CompilationConfig | None): Compilation configuration

### Core Methods

#### compile_document

```python
def compile_document(
    self,
    latex_content: str,
    output_name: str = "document",
    working_dir: Path | None = None
) -> CompilationResult
```

Compiles LaTeX document to PDF with multi-pass support.

**Parameters:**
- `latex_content` (str): LaTeX source code
- `output_name` (str): Base name for output files
- `working_dir` (Path | None): Working directory for compilation

**Returns:**
- `CompilationResult`: Detailed compilation result

**Example:**
```python
from dnd5e.renderers.latex.compiler import LaTeXCompiler
from dnd5e.renderers.latex.compilation_config import CompilationConfig, LaTeXEngine

config = CompilationConfig(
    primary_engine=LaTeXEngine.XELATEX,
    max_passes=3,
    timeout_seconds=120
)

compiler = LaTeXCompiler(config)
result = compiler.compile_document(latex_content, "my_document")

if result.success:
    print(f"Compilation successful: {result.output_path}")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

#### get_available_engines

```python
def get_available_engines(self) -> list[LaTeXEngine]
```

Returns list of available LaTeX engines on the system.

**Returns:**
- `list[LaTeXEngine]`: Available engines

## Configuration Classes

### CompilationConfig

**Location**: `src/dnd5e/renderers/latex/compilation_config.py`

Configuration for LaTeX compilation process.

#### Fields

```python
@dataclass
class CompilationConfig:
    # Engine configuration
    primary_engine: LaTeXEngine = LaTeXEngine.LUALATEX
    fallback_engines: list[LaTeXEngine] = field(default_factory=lambda: [
        LaTeXEngine.XELATEX,
        LaTeXEngine.PDFLATEX
    ])

    # Compilation behavior
    mode: CompilationMode = CompilationMode.NORMAL
    max_passes: int = 4
    timeout_seconds: int = 300

    # Output configuration
    output_dir: Path | None = None
    keep_intermediate_files: bool = False
    verbose_logging: bool = False

    # Engine-specific options
    engine_options: dict[str, list[str]] = field(default_factory=dict)

    # Progress tracking
    show_progress: bool = True
    progress_style: str = "rich"  # "rich", "simple", "none"
```

#### Methods

```python
def get_engine_command(self, engine: LaTeXEngine) -> list[str]
```

Gets the complete command for a LaTeX engine.

```python
def validate(self) -> list[str]
```

Validates configuration and returns list of error messages.

### LaTeXEngine (Enum)

```python
class LaTeXEngine(Enum):
    LUALATEX = "lualatex"
    XELATEX = "xelatex"
    PDFLATEX = "pdflatex"
```

### CompilationResult

```python
@dataclass
class CompilationResult:
    success: bool
    output_path: Path | None
    errors: list[LaTeXError]
    warnings: list[LaTeXError]
    compilation_time: float
    passes_completed: int
    engine_used: LaTeXEngine
```

## Error Handling

### LaTeXError

**Location**: `src/dnd5e/renderers/latex/error_parser.py`

Represents a LaTeX error or warning with context.

```python
@dataclass
class LaTeXError:
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    file_path: str | None = None
    line_number: int | None = None
    context: str | None = None
    suggestion: str | None = None
```

### ErrorSeverity (Enum)

```python
class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
```

### ErrorCategory (Enum)

```python
class ErrorCategory(Enum):
    MISSING_PACKAGE = "missing_package"
    MISSING_FILE = "missing_file"
    SYNTAX_ERROR = "syntax_error"
    FONT_ERROR = "font_error"
    TEMPLATE_ERROR = "template_error"
    COMPILATION_ERROR = "compilation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN = "unknown"
```

### LaTeXErrorParser

Parses LaTeX compilation logs to extract structured error information.

#### parse_log

```python
def parse_log(
    self,
    log_content: str,
    log_file_path: Path | None = None
) -> list[LaTeXError]
```

Parses log content and extracts errors.

**Parameters:**
- `log_content` (str): Content of LaTeX log file
- `log_file_path` (Path | None): Path to log file for context

**Returns:**
- `list[LaTeXError]`: Parsed errors and warnings

#### analyze_compilation_failure

```python
def analyze_compilation_failure(
    self,
    return_code: int,
    stdout: str,
    stderr: str,
    timeout_occurred: bool = False
) -> list[LaTeXError]
```

Analyzes compilation failure and generates error reports.

## Unicode Utilities

**Location**: `src/dnd5e/renderers/latex/unicode_mappings.py`

Utilities for handling Unicode characters in LaTeX output.

### Functions

#### escape_latex_text

```python
def escape_latex_text(text: str) -> str
```

Escapes LaTeX special characters and maps Unicode characters.

**Parameters:**
- `text` (str): Input text with potential special characters

**Returns:**
- `str`: LaTeX-safe text

**Example:**
```python
from dnd5e.renderers.latex.unicode_mappings import escape_latex_text

unsafe_text = "Cost: 50gp & "special" components"
safe_text = escape_latex_text(unsafe_text)
# Result: "Cost: 50gp \\& ``special'' components"
```

#### get_unmapped_unicode_chars

```python
def get_unmapped_unicode_chars(text: str) -> set[str]
```

Identifies Unicode characters without LaTeX mappings.

**Parameters:**
- `text` (str): Text to analyze

**Returns:**
- `set[str]`: Set of unmapped Unicode characters

### Constants

#### LATEX_SPECIAL_CHARS

```python
LATEX_SPECIAL_CHARS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "^": r"\textasciicircum{}",
    "_": r"\_",
    "~": r"\textasciitilde{}",
}
```

#### UNICODE_TO_LATEX

```python
UNICODE_TO_LATEX: dict[str, str] = {
    # Smart quotes
    chr(0x201C): "``",  # Left double quotation mark
    chr(0x201D): "''",  # Right double quotation mark

    # Dashes
    chr(0x2014): "---",  # Em dash
    chr(0x2013): "--",   # En dash

    # Mathematical symbols
    chr(0x00B0): r"\textdegree{}",  # Degree sign
    chr(0x00B1): r"\textpm{}",      # Plus-minus sign

    # Currency symbols
    chr(0x20AC): r"\texteuro{}",    # Euro sign
    # ... many more mappings
}
```

## Usage Examples

### Complete Document Generation

```python
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer
from dnd5e.core.models.spells import Spell
from dnd5e.core.models.document_metadata import DocumentMetadata
from pathlib import Path

# Create renderer
renderer = LaTeXDocumentRenderer({
    "use_dnd_template": True,
    "debug": False
})

# Prepare content
spells = [
    Spell(name="Fireball", level=3, ...),
    Spell(name="Magic Missile", level=1, ...),
]

metadata = DocumentMetadata(
    title="Spell Compendium",
    author="DM",
    document_type="supplement"
)

# Generate and compile
latex_content = renderer.render_document(spells, metadata)
result = renderer.compile_to_pdf(latex_content, Path("spells.pdf"))

if result.success:
    print(f"Generated PDF: {result.output_path}")
else:
    for error in result.errors:
        print(f"Compilation error: {error}")
```

### Custom Template with Processing

```python
from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine
from dnd5e.renderers.latex.content_processor import SpellProcessor
from dnd5e.renderers.base import RenderContext

# Initialize components
engine = LaTeXTemplateEngine()
processor = SpellProcessor()

# Process content
context = RenderContext()
enhanced_data = processor.process(spell, context)

# Render with template
template_context = {
    "spell": spell,
    **enhanced_data
}

output = engine.render_template("custom_spell.tex.j2", template_context)
```

### Error Handling and Debugging

```python
from dnd5e.renderers.latex.compiler import LaTeXCompiler
from dnd5e.renderers.latex.error_parser import LaTeXErrorParser

compiler = LaTeXCompiler()
result = compiler.compile_document(latex_content)

if not result.success:
    print("Compilation failed:")

    for error in result.errors:
        print(f"  {error.severity.value.upper()}: {error.message}")
        if error.suggestion:
            print(f"    Suggestion: {error.suggestion}")
        if error.file_path and error.line_number:
            print(f"    Location: {error.file_path}:{error.line_number}")
```

## Performance Considerations

### Template Caching

Templates are automatically cached for performance. Control caching behavior:

```python
engine = LaTeXTemplateEngine({
    "cache_size": 200,      # Number of templates to cache
    "cache_timeout": 3600,  # Cache timeout in seconds
    "auto_reload": False    # Disable for production
})
```

### Compilation Optimization

Optimize compilation for different scenarios:

```python
# Fast compilation for development
dev_config = CompilationConfig(
    primary_engine=LaTeXEngine.PDFLATEX,
    max_passes=1,
    timeout_seconds=30
)

# High-quality compilation for production
prod_config = CompilationConfig(
    primary_engine=LaTeXEngine.XELATEX,
    max_passes=3,
    timeout_seconds=300,
    engine_options={
        "xelatex": ["-interaction=nonstopmode", "-halt-on-error"]
    }
)
```

### Memory Management

For processing large datasets:

```python
# Process in batches
def render_large_dataset(content_items, batch_size=50):
    results = []

    for i in range(0, len(content_items), batch_size):
        batch = content_items[i:i + batch_size]
        batch_result = renderer.render_document(batch)
        results.append(batch_result)

        # Optional: clear caches between batches
        renderer.template_engine._template_cache.clear()

    return results
```

## Thread Safety

The LaTeX rendering system components have the following thread safety characteristics:

- **LaTeXDocumentRenderer**: Thread-safe for read operations, not for configuration changes
- **LaTeXTemplateEngine**: Template cache is thread-safe
- **LaTeXCompiler**: Not thread-safe (creates temporary files), use separate instances per thread
- **ContentProcessor classes**: Stateless and thread-safe

For concurrent usage:

```python
import concurrent.futures

def render_content_item(item):
    # Create separate renderer instance per thread
    renderer = LaTeXDocumentRenderer()
    return renderer.render(item)

# Process items concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(render_content_item, content_items))
```
