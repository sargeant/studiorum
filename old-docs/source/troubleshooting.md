# Troubleshooting

Common issues and solutions for 5e2pdf installation and usage.

## Quick Diagnostics

First, run the built-in diagnostics:

```bash
# Check overall system status
uv run 5e2pdf setup check

# Enable debug output for detailed information
uv run 5e2pdf --debug convert adventure cos
```

## Installation Issues

### Python and UV Problems

**Python Version Incompatible**
```bash
# Check Python version (must be 3.12+)
python --version
python3 --version

# Install correct version
brew install python@3.12  # macOS
sudo apt install python3.12  # Ubuntu
```

**UV Not Found or Not Working**
```bash
# Install or reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# Verify uv installation
uv --version
```

**5e2pdf Command Not Found**
```bash
# Always use uv run for development installation
uv run 5e2pdf --help

# Or activate the environment first
source .venv/bin/activate
5e2pdf --help
```

### LaTeX Installation Problems

**LaTeX Engines Missing**
```bash
# Test LaTeX installation
pdflatex --version
lualatex --version
xelatex --version

# Install LaTeX (choose your platform)
brew install --cask mactex                    # macOS
sudo apt install texlive-full                 # Ubuntu
sudo dnf install texlive-scheme-full         # Fedora
winget install MiKTeX.MiKTeX                  # Windows
```

**LaTeX PATH Issues**
```bash
# Check if LaTeX is in PATH
which pdflatex
which lualatex

# Add LaTeX to PATH (Linux example)
export PATH="/usr/local/texlive/2024/bin/x86_64-linux:$PATH"
echo 'export PATH="/usr/local/texlive/2024/bin/x86_64-linux:$PATH"' >> ~/.bashrc
```

## Configuration Issues

### Setup and Source Problems

**No Content Sources Configured**
```bash
# Run the setup wizard
uv run 5e2pdf setup wizard

# Or reset to defaults and reconfigure
uv run 5e2pdf setup reset
uv run 5e2pdf setup wizard
```

**Sources Not Loading**
```bash
# Check source status
uv run 5e2pdf sources list

# Update sources manually
uv run 5e2pdf sources update

# Check what content is available
uv run 5e2pdf stats overview
```

**Permission/Directory Issues**
```bash
# Check configuration directory
ls -la ~/.5e2pdf/

# Reset permissions if needed
chmod -R 755 ~/.5e2pdf/

# Check disk space
df -h ~/.5e2pdf/
```

## Content Conversion Issues

### Content Not Found

**Adventure/Book Not Available**
```bash
# List available content
uv run 5e2pdf list adventures
uv run 5e2pdf list books

# Check for typos in abbreviations
uv run 5e2pdf info content cos  # "cos" not "CoS"

# Check source status
uv run 5e2pdf sources list
```

**Content Loading Errors**
```bash
# Check content statistics
uv run 5e2pdf stats overview

# Verify sources have content
uv run 5e2pdf stats sources

# Try updating sources
uv run 5e2pdf sources update
```

### LaTeX Compilation Failures

**PDF Generation Fails**
```bash
# Test LaTeX generation without PDF compilation
uv run 5e2pdf convert adventure cos --output test.tex

# Check if .tex file is valid
cat test.tex | head -50

# Try manual LaTeX compilation
lualatex test.tex
```

**LaTeX Engine Errors**
```bash
# Try different LaTeX engines
uv run 5e2pdf convert adventure cos --pdf    # Uses default (LuaLaTeX)

# Check LaTeX log files in output directory
ls -la *.log
cat adventure.log  # Look for errors
```

**Missing LaTeX Packages**
```bash
# Install additional LaTeX packages
sudo tlmgr install collection-fontsextra     # Linux/macOS
sudo tlmgr install collection-latexrecommended

# Or install full distribution
sudo apt install texlive-full                # Ubuntu
brew install --cask mactex                   # macOS (full)
```

## Performance Issues

### Slow or Hanging Operations

**Long Loading Times**
```bash
# Check if sources are responding
uv run 5e2pdf sources list

# Try with limited concurrency
uv run 5e2pdf convert bulk cos lmop --concurrent 1

# Skip resource-intensive operations
uv run 5e2pdf convert adventure cos --no-images
```

**Memory Issues**
```bash
# Process files individually instead of bulk
uv run 5e2pdf convert adventure cos
uv run 5e2pdf convert adventure lmop

# Use quick mode for simple conversions
uv run 5e2pdf quick simple.json --type auto
```

**Disk Space Problems**
```bash
# Check available space
df -h ~/.5e2pdf/
df -h ./output/

# Clear cache if needed
rm -rf ~/.5e2pdf/cache/*
```

## Debug and Logging

### Enable Detailed Logging

```bash
# Debug mode for maximum information
uv run 5e2pdf --debug convert adventure cos

# Verbose mode for detailed progress
uv run 5e2pdf --verbose stats overview

# Check log files
ls -la ~/.5e2pdf/logs/
tail -f ~/.5e2pdf/logs/app.log
```

### Environment Variables for Debugging

```bash
# Enable detailed entry processing debug output
export DND5E_DEBUG_ENTRY_PROCESSING=1

# Strict mode - fail on unknown entry types
export DND5E_STRICT_ENTRY_PROCESSING=1

# Disable tag fallback - show raw tags when resolution fails
export DND5E_DISABLE_TAG_FALLBACK=1

# Set custom data path
export DND5E_DATA_PATH=/path/to/5etools/data

# Use custom config file
export DND5E_CONFIG_FILE=test-config.yaml

# Control LaTeX output
export DND5E_LATEX_QUIET=1  # Suppress LaTeX output
export DND5E_LATEX_VERBOSE=1  # Show all LaTeX output
```

### Managing Large Output

When debugging produces excessive output, use truncation:

```bash
# Limit output to first 100 lines
uv run 5e2pdf convert creatures --cr 1 | head -100

# Limit output to last 100 lines
uv run 5e2pdf convert creatures --cr 1 | tail -100

# Save to file for analysis
uv run 5e2pdf convert creatures --cr 1 > output.tex 2>&1

# Count lines in output
uv run 5e2pdf convert creatures --cr 1 | wc -l
```

### Common Error Patterns

**"ContentType not found" errors**
```bash
# Check available content types
uv run 5e2pdf stats overview

# List content in sources
uv run 5e2pdf list content --limit 10
```

**"Source not configured" errors**
```bash
# Verify source configuration
uv run 5e2pdf sources list

# Reconfigure sources
uv run 5e2pdf setup wizard
```

**"LaTeX command failed" errors**
```bash
# Check LaTeX installation
uv run 5e2pdf setup check

# Generate LaTeX without compilation
uv run 5e2pdf convert adventure cos --output test.tex

# Manually compile to see detailed errors
lualatex test.tex
```

## Platform-Specific Issues

### macOS

**Xcode Command Line Tools Missing**
```bash
xcode-select --install
```

**Homebrew Permission Issues**
```bash
sudo chown -R $(whoami) /usr/local/Homebrew/
brew doctor
```

**Apple Silicon Compatibility**
```bash
# Use Rosetta for x86 packages if needed
arch -x86_64 brew install texlive
```

### Linux

**Package Manager Issues**
```bash
# Update package lists
sudo apt update
sudo dnf update

# Install development headers
sudo apt install build-essential python3.12-dev
sudo dnf install gcc python3.12-devel
```

**Snap Package Conflicts**
```bash
# Remove conflicting snap packages
sudo snap remove --purge texlive
```

### Windows

**PATH Issues**
```powershell
# Check PATH in PowerShell
$env:PATH -split ';'

# Add directories to PATH permanently
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\texlive\bin", [EnvironmentVariableTarget]::User)
```

**WSL Compatibility**
```bash
# Use WSL2 for better compatibility
wsl --set-default-version 2
```

## Getting Additional Help

### Before Reporting Issues

1. **Run diagnostics**: `uv run 5e2pdf setup check`
2. **Check logs**: Look in `~/.5e2pdf/logs/app.log`
3. **Try debug mode**: `uv run 5e2pdf --debug`
4. **Verify installation**: Follow installation guide step-by-step

### Information to Include in Bug Reports

```bash
# System information
uv run 5e2pdf --version
python --version
uv --version
lualatex --version

# Configuration status
uv run 5e2pdf setup check
uv run 5e2pdf sources list

# Error logs (last 50 lines)
tail -50 ~/.5e2pdf/logs/app.log
```

### Community Support

- **GitHub Issues**: [5e2pdf Issues](https://github.com/sargeant/5e2pdf/issues)
- **Bug Reports**: Include system info, error logs, and steps to reproduce
- **Feature Requests**: Describe use case and expected behavior

## Testing Issues

### Test Environment Problems

**Tests Failing in Parallel**
```bash
# Run tests without parallelization
pytest -n 0  # or --dist=no

# Reset test environment
python -c "from dnd5e.test_utils import reset_test_environment; reset_test_environment()"

# Clear test cache
rm -rf .pytest_cache/
```

**Test Data Not Found**
```bash
# Ensure test data is available
export DND5E_CONFIG_FILE=test-config.yaml

# Check test isolation
grep "reset_test_environment" tests/**/*.py
```

**Integration Test Failures**
```bash
# Run only unit tests (fast)
make test

# Run LaTeX integration tests (requires LaTeX)
make test-latex-integration

# Skip tests requiring 5etools data
pytest -m "not needs_data"
```

### Using reset_test_environment()

When developing or debugging tests:

```python
from dnd5e.test_utils import reset_test_environment

def setup_method(self):
    """Setup for each test method."""
    reset_test_environment()
    # Additional setup...

def teardown_method(self):
    """Cleanup after each test."""
    reset_test_environment()
```

## Recovery Procedures

### Complete Reset

If all else fails, complete reset:

```bash
# Remove all 5e2pdf data
rm -rf ~/.5e2pdf/

# Reinstall 5e2pdf
cd 5e2pdf
uv sync --group dev --extra docs

# Run setup wizard
uv run 5e2pdf setup wizard

# Test basic functionality
uv run 5e2pdf stats overview
```

### Partial Reset

Reset only configuration:

```bash
# Reset configuration to defaults
uv run 5e2pdf setup reset

# Keep cache and logs intact
uv run 5e2pdf setup wizard
```

## Prevention Tips

- **Regular Updates**: Keep Python, UV, and LaTeX up to date
- **Disk Space**: Monitor available space in cache and output directories
- **Source Maintenance**: Periodically update content sources
- **System Monitoring**: Watch for permission or path changes
- **Backup Configuration**: Save working configurations before major changes
