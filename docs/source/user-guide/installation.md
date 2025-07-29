# Installation

This guide covers installing 5e2pdf and all required dependencies for PDF generation.

## Prerequisites

Before installing 5e2pdf, ensure you have:

- **Python 3.12 or later**
- **uv package manager** (recommended) or pip
- **LaTeX distribution** for PDF generation
- **Git** (for development installation)

### Python Installation

#### macOS
```bash
# Using Homebrew
brew install python@3.12

# Or using pyenv
pyenv install 3.12.0
pyenv global 3.12.0
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

#### Linux (RHEL/CentOS/Fedora)
```bash
# Fedora
sudo dnf install python3.12 python3.12-devel

# RHEL/CentOS (with EPEL)
sudo yum install python3.12 python3.12-devel
```

#### Windows
Download from [python.org](https://www.python.org/downloads/) or use:
```powershell
# Using winget
winget install Python.Python.3.12

# Using Chocolatey
choco install python --version=3.12.0
```

### UV Package Manager Installation

UV is the recommended package manager for 5e2pdf:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify installation
uv --version
```

## LaTeX Installation

PDF generation requires a LaTeX distribution. Choose based on your platform:

### macOS - MacTeX
```bash
# Full installation (4GB+)
brew install --cask mactex

# Or minimal installation
brew install --cask mactex-no-gui
```

### Linux - TeX Live
```bash
# Ubuntu/Debian
sudo apt install texlive-full

# Or minimal installation
sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra

# Fedora
sudo dnf install texlive-scheme-full

# Or minimal
sudo dnf install texlive-latex texlive-xetex texlive-luatex
```

### Windows - MiKTeX or TeX Live
```powershell
# MiKTeX (recommended for Windows)
winget install MiKTeX.MiKTeX

# Or TeX Live
winget install TeXLive.TeXLive
```

### Verify LaTeX Installation
```bash
# Test LaTeX engines
pdflatex --version
xelatex --version
lualatex --version
```

## 5e2pdf Installation

### Option 1: PyPI Installation (Stable)

```bash
# Install from PyPI
pip install 5e2pdf

# Or with uv (recommended)
uv tool install 5e2pdf
```

### Option 2: Development Installation

For the latest features or to contribute:

```bash
# Clone repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Install with uv (recommended)
uv sync --group dev --extra docs

# Or with pip
pip install -e ".[dev,docs]"
```

### Option 3: Container Installation

Using Docker for isolated environment:

```bash
# Pull container
docker pull ghcr.io/sargeant/5e2pdf:latest

# Run with volume mounting
docker run -v $(pwd):/workspace ghcr.io/sargeant/5e2pdf:latest
```

## Configuration

### Initial Setup

Run the setup command to configure 5e2pdf:

```bash
5e2pdf setup --interactive
```

This will:
- Create configuration directory (`~/.5e2pdf/`)
- Download content sources from 5e.tools
- Verify LaTeX installation
- Set up default templates

### Configuration Locations

5e2pdf uses these configuration files in order of priority:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`DND5E_*`)
3. **Project config**: `./5e2pdf.yaml`
4. **User config**: `~/.5e2pdf/config.yaml`
5. **System config**: `/etc/5e2pdf/config.yaml`
6. **Defaults** (lowest priority)

### Sample Configuration

Create `~/.5e2pdf/config.yaml`:

```yaml
# Data and caching
data_dir: "~/.5e2pdf/data"
cache_dir: "~/.5e2pdf/cache"
enable_cache: true

# LaTeX settings
latex:
  engine: "lualatex"
  paper_size: "letter"
  columns: 2
  font_family: "Times"

# Logging
log_level: "INFO"
log_file: "~/.5e2pdf/logs/app.log"
```

## Verify Installation

### Basic Verification

```bash
# Check installation
5e2pdf --version

# List available commands
5e2pdf --help

# Test data loading
5e2pdf list sources
```

### Full System Test

```bash
# Generate a test PDF
5e2pdf convert --source PHB --content-type spell --limit 5 --output test.pdf

# Check if PDF was created
ls -la test.pdf
```

### Performance Test

```bash
# Run performance benchmarks
5e2pdf stats --benchmark

# Test with different LaTeX engines
5e2pdf convert --latex-engine lualatex --source PHB --content-type spell --limit 1
```

## Troubleshooting

### Common Issues

#### Python Version Issues
```bash
# Check Python version
python --version
python3 --version

# Use specific Python version
python3.12 -m pip install 5e2pdf
```

#### LaTeX Not Found
```bash
# Check LaTeX installation
which pdflatex
which lualatex

# Add to PATH if needed (Linux/macOS)
export PATH="/usr/local/texlive/2024/bin/x86_64-linux:$PATH"
```

#### Permission Issues
```bash
# Fix permissions (Linux/macOS)
chmod +x ~/.local/bin/5e2pdf

# Use user installation
pip install --user 5e2pdf
```

#### Network Issues
```bash
# Use offline mode if needed
5e2pdf --offline convert --source-dir ./local-data
```

### Getting Help

If you encounter issues:

1. **Check logs**: `~/.5e2pdf/logs/app.log`
2. **Run diagnostics**: `5e2pdf setup --validate`
3. **Enable debug mode**: `5e2pdf --log-level DEBUG`
4. **Report bugs**: [GitHub Issues](https://github.com/sargeant/5e2pdf/issues)

### Performance Optimization

#### System Requirements

- **Minimum**: 4GB RAM, 2GB free disk space
- **Recommended**: 8GB RAM, 5GB free disk space
- **For large datasets**: 16GB RAM, 10GB+ free disk space

#### Optimization Tips

```bash
# Enable caching
5e2pdf config set enable_cache true

# Use faster LaTeX engine
5e2pdf config set latex.engine lualatex

# Parallel processing
5e2pdf config set parallel_workers 4
```

## Next Steps

After installation:

1. **Read the [Quickstart Guide](../quickstart.md)** for your first conversion
2. **Explore [Basic Usage](basic-usage.md)** for common workflows
3. **Check [Advanced Features](advanced-features.md)** for customization
4. **Review [Troubleshooting](troubleshooting.md)** for common issues

## Platform-Specific Notes

### macOS

- Use Homebrew for package management
- LuaLaTeX is recommended over PDFLaTeX
- Ensure Xcode Command Line Tools are installed

### Linux

- Install development headers for compiled dependencies
- Consider using system package manager for LaTeX
- Set appropriate file permissions for ~/.5e2pdf/

### Windows

- Use PowerShell or Command Prompt
- Consider WSL for Linux-like experience
- Ensure PATH includes Python and LaTeX binaries
- Some LaTeX packages may require manual installation

---

**Need help?** Join our community discussions or report issues on [GitHub](https://github.com/sargeant/5e2pdf/issues).
