# Error Handling & Troubleshooting Guide

This comprehensive guide helps developers and users diagnose and resolve issues with 5e2pdf, covering everything from LaTeX compilation errors to data processing problems.

## Quick Diagnosis

### Enable Debug Mode

For detailed troubleshooting information:

```bash
# Enable verbose logging
5e2pdf convert --verbose your-content.json

# Set debug level logging
LOG_LEVEL=DEBUG 5e2pdf convert your-content.json

# Save intermediate files for inspection
5e2pdf convert --keep-intermediate your-content.json
```

### Common Issue Categories

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| "File not found" during compilation | Missing LaTeX packages or DND template | Install missing packages |
| Unicode characters appear as boxes | Engine doesn't support Unicode | Use XeLaTeX or LuaLaTeX |
| Compilation hangs/times out | Complex content or infinite loop | Enable draft mode, reduce content |
| Empty or malformed output | Data parsing errors | Check source JSON validity |
| Missing images/figures | Asset path issues | Verify image paths and permissions |

## LaTeX Compilation Errors

### Error Categories and Solutions

#### Missing Package/File Errors

**Error Pattern**: `! LaTeX Error: File 'filename.sty' not found`

**Common Missing Packages**:
```bash
# Ubuntu/Debian
sudo apt-get install texlive-latex-extra texlive-fonts-extra texlive-xetex

# macOS (MacTeX)
# Usually includes all packages, but check:
tlmgr install dndbook fontspec geometry xcolor

# Windows (MiKTeX)
# Packages auto-install, but may need:
mpm --install=dndbook --install=fontspec
```

**DND-5e-LaTeX-Template Issues**:
```bash
# Check template installation
5e2pdf setup check-templates

# Install template manually
git clone https://github.com/ashonit/DND-5e-LaTeX-Template.git
# Follow template installation instructions
```

#### Font Errors

**Error Pattern**: `fontspec error: The font "FontName" cannot be found`

**Solutions**:
```latex
% In templates, check font availability
\IfFontExistsTF{Bookinsanity}{
    \setmainfont{Bookinsanity}
}{
    \setmainfont{Times New Roman}  % Fallback
}
```

**Debug font issues**:
```bash
# List available system fonts (XeLaTeX/LuaLaTeX)
fc-list : family | grep -i bookinsanity

# Check font loading in LaTeX
xelatex -interaction=nonstopmode test-fonts.tex
```

#### Template Errors

**Error Pattern**: `! Package dnd Error: Invalid argument`

**Common DND Template Issues**:

1. **Invalid document class options**:
   ```latex
   % Wrong
   \documentclass[invalidoption]{dndbook}

   % Correct
   \documentclass[bg,justified,twocolumn]{dndbook}
   ```

2. **Environment misuse**:
   ```latex
   % Wrong - missing end
   \begin{DndReadAloud}
   Text here...
   % Missing \end{DndReadAloud}

   % Wrong - incorrect nesting
   \begin{DndSidebar}
       \begin{DndReadAloud} % Can't nest these
       \end{DndReadAloud}
   \end{DndSidebar}
   ```

3. **Monster stat block errors**:
   ```latex
   % Common error - malformed stats
   \DndMonsterBasics[
       armor-class = 18 (Plate),  % Should be {18 (Plate)}
       hit-points = 52d8 + 16,    % Should be {52 (8d8 + 16)}
   ]
   ```

#### Syntax Errors

**Error Pattern**: `! Undefined control sequence`

**Common causes and fixes**:

1. **Unescaped special characters**:
   ```python
   # In Python code - ensure proper escaping
   from dnd5e.core.latex_utils import escape_latex_text

   safe_text = escape_latex_text(user_input)
   ```

2. **Template delimiter conflicts**:
   ```latex
   % LaTeX code with template delimiters
   <# variable #>  % Correct - processed by Jinja2

   % Raw LaTeX that conflicts
   \newcommand{\test}{<# not a variable #>}  % Wrong - escaping needed
   ```

3. **Missing imports in custom templates**:
   ```latex
   % Always include in custom templates
   \usepackage{dnd}
   \usepackage{fontspec}  % For XeLaTeX/LuaLaTeX
   ```

#### Compilation Timeout

**Error**: Process hangs or times out during compilation

**Debugging steps**:

1. **Enable draft mode**:
   ```python
   # In Python
   config = CompilationConfig(
       mode=CompilationMode.DRAFT,
       timeout_seconds=60
   )
   ```

2. **Reduce content complexity**:
   ```bash
   # Test with minimal content first
   5e2pdf convert --limit 5 large-adventure.json
   ```

3. **Check for infinite loops**:
   ```latex
   % Common culprit - recursive includes
   \input{file-that-includes-itself}

   % Or template recursion
   <@ for item in items @>
       <@ for subitem in item.items @>  <!-- Potential infinite nesting -->
   ```

### Compilation Optimization

#### Engine Selection

```python
# Choose optimal engine for content
engines_by_feature = {
    'unicode_heavy': LaTeXEngine.XELATEX,
    'simple_ascii': LaTeXEngine.PDFLATEX,  # Fastest
    'complex_fonts': LaTeXEngine.LUALATEX,
    'dnd_template': LaTeXEngine.XELATEX,   # Recommended
}
```

#### Performance Tuning

```python
# Compilation configuration for performance
config = CompilationConfig(
    max_passes=2,              # Reduce passes for speed
    timeout_seconds=120,       # Reasonable timeout
    keep_intermediate_files=False,  # Save disk space
    engine_options={
        'xelatex': [
            '-interaction=nonstopmode',
            '-halt-on-error',      # Stop on first error
            '-no-shell-escape',    # Disable for security/speed
        ]
    }
)
```

## Data Processing Errors

### 5etools Format Issues

#### Entry Type Validation

**Error**: `UnknownEntryTypeError: Unknown entry type: 'customType'`

**Solutions**:
```python
# 1. Add to entry registry (if legitimate type)
from dnd5e.core.entry_registry import register_entry_type

register_entry_type('customType', processor_function)

# 2. Enable liberal validation (for testing)
processor = RecursiveEntryProcessor(
    validation_mode=ValidationMode.LIBERAL
)

# 3. Filter out unknown types in preprocessing
def clean_entries(entries):
    valid_entries = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get('type') in KNOWN_TYPES:
            valid_entries.append(entry)
        elif isinstance(entry, str):
            valid_entries.append(entry)  # Text entries are always valid
    return valid_entries
```

#### Malformed Content

**Error**: `MalformedEntryError: Expected dict, got str`

**Common patterns and fixes**:
```python
# Robust entry processing
def safe_process_entry(entry):
    try:
        if isinstance(entry, str):
            return entry  # Plain text
        elif isinstance(entry, dict):
            return process_dict_entry(entry)
        elif isinstance(entry, list):
            return [safe_process_entry(e) for e in entry]
        else:
            logger.warning(f"Unexpected entry type: {type(entry)}")
            return str(entry)  # Convert to string as fallback
    except Exception as e:
        logger.error(f"Failed to process entry: {e}")
        return f"[Processing Error: {e}]"
```

#### Content Resolution Failures

**Error**: Content not found or fuzzy matching fails

**Debugging steps**:
```python
# 1. Check omnidexer status
indexer = Omnidexer()
adventures = await indexer.load_adventures("adventures.json")
print(f"Loaded {len(adventures)} adventures")

# 2. List available content
for adventure in adventures:
    print(f"ID: {adventure.id}, Name: {adventure.name}")

# 3. Test fuzzy matching
resolver = ContentResolver(fuzzy_threshold=0.4)  # Lower threshold
matches = resolver.find_similar_names("CoS")
print(f"Fuzzy matches: {matches}")

# 4. Check content merger cache
merger = ContentMerger()
stats = merger.get_cache_statistics()
print(f"Cache hits: {stats.hits}, misses: {stats.misses}")
```

### Unicode and Character Issues

#### Character Mapping Problems

**Error**: Unmapped Unicode characters in output

**Detection and resolution**:
```python
# Enable Unicode character logging
from dnd5e.renderers.latex.unicode_mappings import (
    get_unmapped_unicode_chars,
    UNICODE_TO_LATEX
)

# Check for problematic characters
def audit_content_unicode(text: str):
    unmapped = get_unmapped_unicode_chars(text)
    if unmapped:
        logger.warning(f"Unmapped Unicode characters: {unmapped}")

    # Suggest mappings
    for char in unmapped:
        logger.info(f"Consider adding mapping: '{char}' (U+{ord(char):04X})")

# Add custom mappings
CUSTOM_MAPPINGS = {
    '™': r'\texttrademark{}',
    '©': r'\textcopyright{}',
    '®': r'\textregistered{}',
}

UNICODE_TO_LATEX.update(CUSTOM_MAPPINGS)
```

#### Encoding Issues

**Error**: File encoding problems during processing

**Solutions**:
```python
# Robust file reading
import chardet

def read_with_encoding_detection(file_path: Path) -> str:
    """Read file with automatic encoding detection."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()

    # Detect encoding
    encoding_info = chardet.detect(raw_data)
    encoding = encoding_info['encoding']
    confidence = encoding_info['confidence']

    if confidence < 0.8:
        logger.warning(f"Low confidence ({confidence:.2f}) for encoding {encoding}")

    # Decode with fallback
    try:
        return raw_data.decode(encoding)
    except UnicodeDecodeError:
        logger.warning(f"Failed to decode with {encoding}, trying UTF-8")
        return raw_data.decode('utf-8', errors='replace')
```

## Performance Issues

### Memory Usage

#### High Memory Consumption

**Symptoms**: Process uses excessive RAM, system becomes unresponsive

**Diagnosis**:
```python
import psutil
import logging

def monitor_memory_usage():
    """Monitor memory usage during processing."""
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024

    if memory_mb > 500:  # 500MB threshold
        logger.warning(f"High memory usage: {memory_mb:.1f}MB")

        # Get memory breakdown
        children = process.children(recursive=True)
        for child in children:
            child_memory = child.memory_info().rss / 1024 / 1024
            logger.info(f"Child process {child.pid}: {child_memory:.1f}MB")

# Use in processing loops
for i, item in enumerate(large_content_list):
    if i % 100 == 0:  # Check every 100 items
        monitor_memory_usage()
    process_item(item)
```

**Optimization strategies**:
```python
# 1. Use generators instead of lists
def process_content_generator(items):
    for item in items:
        yield process_item(item)

# 2. Clear caches periodically
merger = ContentMerger(cache_size=50)  # Smaller cache
if len(processed_items) % 1000 == 0:
    merger.clear_cache()

# 3. Process in batches
def process_in_batches(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        yield process_batch(batch)

        # Force garbage collection
        import gc
        gc.collect()
```

### Slow Processing

#### Profiling Performance

**Setup profiling**:
```python
import cProfile
import pstats
from pathlib import Path

def profile_conversion(content_file: Path):
    """Profile document conversion performance."""

    # Create profiler
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        # Run conversion
        result = convert_document(content_file)

    finally:
        profiler.disable()

    # Save profile data
    profile_file = content_file.with_suffix('.prof')
    profiler.dump_stats(str(profile_file))

    # Print top time consumers
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result

# Analyze with visualization tools
# pip install snakeviz
# snakeviz profile.prof
```

**Common bottlenecks and solutions**:

1. **Template rendering**:
   ```python
   # Enable template caching
   template_engine = LaTeXTemplateEngine({
       'cache_size': 200,
       'cache_timeout': 3600,
   })
   ```

2. **Content resolution**:
   ```python
   # Batch resolve instead of individual lookups
   resolver = ContentResolver()
   content_batch = resolver.resolve_batch(content_ids)
   ```

3. **File I/O**:
   ```python
   # Use async I/O for large files
   import asyncio
   import aiofiles

   async def load_large_content(file_path: Path):
       async with aiofiles.open(file_path) as f:
           return await f.read()
   ```

## Debug Mode and Logging

### Enabling Comprehensive Debugging

#### Command-Line Options

```bash
# Maximum verbosity
LOG_LEVEL=DEBUG 5e2pdf --verbose convert content.json

# Keep all intermediate files
5e2pdf convert --keep-intermediate --debug-templates content.json

# Save compilation logs
5e2pdf convert --save-logs --log-dir ./debug-logs content.json
```

#### Programmatic Debug Configuration

```python
from dnd5e.core.logging import setup_logging
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer

# Configure detailed logging
setup_logging(level="DEBUG")

# Enable debug features
renderer = LaTeXDocumentRenderer({
    'debug': True,
    'template_debug': True,
    'validation_mode': 'strict',
    'error_tracking': True,
    'save_intermediate_files': True,
})

# Process with full error tracking
try:
    result = renderer.render_document(content_items)
except Exception as e:
    # Get detailed error context
    if hasattr(e, 'entry'):
        print(f"Failed entry: {e.entry}")
    if hasattr(e, 'source'):
        print(f"Source: {e.source}")
    if hasattr(e, 'parent_name'):
        print(f"Parent: {e.parent_name}")

    # Get processing statistics
    from dnd5e.core.entry_registry import print_processing_statistics
    print_processing_statistics()
```

#### Log Analysis

**Understanding log patterns**:
```python
# Common log levels and meanings
LOGGING_GUIDE = {
    'DEBUG': 'Detailed flow information, variable values, cache operations',
    'INFO': 'General progress, successful operations, statistics',
    'WARNING': 'Recoverable issues, fallback behavior, data quality problems',
    'ERROR': 'Processing failures, missing data, compilation errors',
    'CRITICAL': 'System failures, unrecoverable errors'
}

# Useful log filtering
# Show only errors and warnings
grep -E "(ERROR|WARNING)" debug.log

# Show template rendering issues
grep "template" debug.log | grep -E "(ERROR|WARNING)"

# Show entry processing problems
grep "entry" debug.log | grep -E "(UnknownEntryType|ValidationError)"
```

### Custom Error Handlers

#### Adding Application-Specific Error Patterns

```python
from dnd5e.renderers.latex.error_parser import LaTeXErrorParser, LaTeXError, ErrorSeverity, ErrorCategory

class CustomErrorParser(LaTeXErrorParser):
    """Extended error parser with custom patterns."""

    def _build_error_patterns(self):
        patterns = super()._build_error_patterns()

        # Add custom patterns
        custom_patterns = [
            {
                "pattern": re.compile(r"5e2pdf error: (.+)"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.TEMPLATE_ERROR,
                "extract": lambda m: f"5e2pdf processing error: {m.group(1)}",
            },
            {
                "pattern": re.compile(r"Adventure '(.+?)' not found"),
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.MISSING_FILE,
                "extract": lambda m: f"Adventure '{m.group(1)}' could not be loaded",
            },
        ]

        return patterns + custom_patterns

    def _build_suggestion_rules(self):
        rules = super()._build_suggestion_rules()

        # Add custom suggestions
        rules.update({
            ErrorCategory.MISSING_FILE: [
                "Check that all source files are present",
                "Verify file paths are correct",
                "Run '5e2pdf setup check-sources' to validate data files"
            ],
            ErrorCategory.TEMPLATE_ERROR: [
                "Check template syntax and variable names",
                "Ensure all required template variables are provided",
                "Verify template inheritance is correct"
            ],
        })

        return rules
```

## Environment-Specific Issues

### Operating System Differences

#### Windows-Specific Issues

**Path separator problems**:
```python
# Always use Path objects for cross-platform compatibility
from pathlib import Path

# Wrong
template_path = "templates\\base.tex.j2"  # Breaks on Unix

# Correct
template_path = Path("templates") / "base.tex.j2"
```

**LaTeX installation issues**:
```bash
# MiKTeX console errors
# 1. Run as administrator
# 2. Refresh package database
# 3. Update all packages
miktex packages update-all

# TeX Live on Windows
tlmgr update --self --all
```

#### macOS-Specific Issues

**Font permissions**:
```bash
# Fix font cache issues
sudo atsutil databases -remove
atsutil server -shutdown
atsutil server -ping
```

**XCode command line tools**:
```bash
# Ensure development tools are installed
xcode-select --install
```

#### Linux Distribution Differences

**Package management variations**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install texlive-full python3-dev

# CentOS/RHEL/Fedora
sudo yum install texlive-scheme-full python3-devel
# or
sudo dnf install texlive-scheme-full python3-devel

# Arch Linux
sudo pacman -S texlive-most python
```

### Container and CI Issues

#### Docker Environment

**Common Dockerfile patterns**:
```dockerfile
FROM python:3.12-slim

# Install LaTeX and dependencies
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-xetex \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install fonts
COPY fonts/ /usr/share/fonts/truetype/custom/
RUN fc-cache -fv

# Install 5e2pdf
COPY . /app
WORKDIR /app
RUN pip install -e .

# Run tests
RUN 5e2pdf setup check-installation
```

**CI/CD considerations**:
```yaml
# GitHub Actions example
- name: Setup LaTeX
  uses: xu-cheng/latex-action@v2
  with:
    root_file: test.tex

- name: Install 5e2pdf dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y texlive-xetex
    pip install -e .

- name: Run tests with timeout
  run: |
    timeout 300 python -m pytest tests/
```

## Recovery Strategies

### Graceful Degradation

#### Fallback Content Processing

```python
def process_with_fallbacks(content_item):
    """Process content with multiple fallback strategies."""

    strategies = [
        ('full_processing', lambda: full_process(content_item)),
        ('simplified_processing', lambda: simple_process(content_item)),
        ('text_only', lambda: extract_text_only(content_item)),
        ('minimal_stub', lambda: create_stub(content_item)),
    ]

    for strategy_name, strategy_func in strategies:
        try:
            result = strategy_func()
            if strategy_name != 'full_processing':
                logger.warning(f"Used fallback strategy: {strategy_name}")
            return result

        except Exception as e:
            logger.debug(f"Strategy {strategy_name} failed: {e}")
            continue

    # All strategies failed
    logger.error(f"All processing strategies failed for {content_item}")
    return create_error_placeholder(content_item)
```

#### Partial Document Generation

```python
def generate_partial_document(content_items, max_errors=10):
    """Generate document even if some items fail."""

    successful_items = []
    failed_items = []
    error_count = 0

    for item in content_items:
        try:
            processed_item = process_item(item)
            successful_items.append(processed_item)

        except Exception as e:
            error_count += 1
            failed_items.append((item, str(e)))

            if error_count >= max_errors:
                logger.error(f"Too many errors ({error_count}), stopping processing")
                break

    # Generate document with successful items
    if successful_items:
        document = generate_document(successful_items)

        # Add error appendix
        if failed_items:
            error_appendix = generate_error_appendix(failed_items)
            document += error_appendix

        return document
    else:
        raise RuntimeError("No content could be processed successfully")
```

### Data Recovery

#### Backup and Restoration

```python
class ContentBackupManager:
    """Manages content backups during processing."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(exist_ok=True)

    def backup_content(self, content_id: str, content_data: dict):
        """Backup content before processing."""
        backup_file = self.backup_dir / f"{content_id}.backup.json"

        with open(backup_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'content_id': content_id,
                'data': content_data
            }, f, indent=2)

    def restore_content(self, content_id: str) -> dict:
        """Restore content from backup."""
        backup_file = self.backup_dir / f"{content_id}.backup.json"

        if not backup_file.exists():
            raise FileNotFoundError(f"No backup found for {content_id}")

        with open(backup_file) as f:
            backup = json.load(f)
            return backup['data']
```

## Getting Help

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share solutions
- **Documentation**: Check latest documentation for updates

### Diagnostic Information

When reporting issues, include:

```bash
# System information
5e2pdf --version
python --version
latex --version  # or xelatex --version

# System details
uname -a  # Linux/macOS
systeminfo  # Windows

# Installation check
5e2pdf setup check-installation --verbose

# Recent logs (last 50 lines)
tail -50 ~/.local/share/5e2pdf/logs/latest.log
```

### Issue Templates

**Bug Report Template**:
```markdown
## Bug Description
Brief description of the issue

## Steps to Reproduce
1. Command run: `5e2pdf convert ...`
2. Content file: [attach or describe]
3. Expected vs actual behavior

## Environment
- 5e2pdf version:
- Python version:
- OS and version:
- LaTeX distribution:

## Logs
```
[paste relevant log output]
```

## Additional Context
Any other relevant information
```

For complex issues, consider creating a minimal reproducible example with the smallest possible content file that demonstrates the problem.
