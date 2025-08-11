# Installation

This guide covers installing 5e2pdf and all required dependencies for PDF generation.

## Prerequisites

Before installing 5e2pdf, ensure you have:

- **Python 3.12 or later**
- **uv package manager**
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

UV is the required package manager for 5e2pdf:

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

### Development Installation

Currently, 5e2pdf is only available through development installation:

```bash
# Clone repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Install with uv (recommended)
uv sync --group dev --extra docs

# Activate the environment
source .venv/bin/activate

# Or on Windows
.venv\Scripts\activate
```

### Verify Installation

```bash
# Check installation
uv run 5e2pdf --version

# Or if environment is activated
5e2pdf --version

# List available commands
uv run 5e2pdf --help
```

## Initial Setup

### Configuration Wizard

Run the setup wizard to configure content sources:

```bash
uv run 5e2pdf setup wizard
```

This will:
- Guide you through content source configuration
- Set up default directories
- Verify LaTeX installation
- Download initial content data

### Manual Setup Options

```bash
# Check current setup status
uv run 5e2pdf setup check

# Reset to defaults
uv run 5e2pdf setup reset
```

## Content Sources

5e2pdf requires D&D content data from sources like 5e.tools. The setup wizard will help configure this.

### Default Sources

The setup wizard can configure default sources including:
- System Reference Document (SRD) data
- Local directories with JSON files
- GitHub repositories with content

### Source Management

```bash
# List configured sources
uv run 5e2pdf sources list

# Add new source
uv run 5e2pdf sources add

# Update sources
uv run 5e2pdf sources update
```

## Test Installation

### Basic Test

```bash
# Test basic functionality
uv run 5e2pdf list sources

# Test content loading
uv run 5e2pdf stats overview
```

### Full Conversion Test

After setting up sources:

```bash
# Test adventure conversion
uv run 5e2pdf convert adventure cos --output test.tex

# Test with PDF compilation
uv run 5e2pdf convert adventure lmop --pdf --output test-pdf.tex
```

## Troubleshooting Installation

### Common Issues

#### Python Version Issues
```bash
# Check Python version
python --version
python3 --version

# Use specific Python version if needed
python3.12 -m pip install uv
```

#### UV Not Found
```bash
# Ensure uv is in PATH
echo $PATH

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc
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
pip install --user uv
```

### Getting Help

If you encounter issues:

1. **Check setup**: `uv run 5e2pdf setup check`
2. **Run diagnostics**: `uv run 5e2pdf setup wizard`
3. **Enable debug mode**: `uv run 5e2pdf --debug`
4. **Report bugs**: [GitHub Issues](https://github.com/sargeant/5e2pdf/issues)

## System Requirements

### Minimum Requirements

- **RAM**: 4GB
- **Disk Space**: 2GB free (LaTeX installation + content)
- **Python**: 3.12+
- **LaTeX**: Any modern distribution

### Recommended

- **RAM**: 8GB
- **Disk Space**: 5GB free
- **LaTeX**: Full TeX Live or MacTeX installation

## Next Steps

After successful installation:

1. **Run setup wizard**: `uv run 5e2pdf setup wizard`
2. **Explore commands**: `uv run 5e2pdf --help`
3. **Read basic usage**: [Basic Usage](basic-usage.md)
4. **Convert your first content**: `uv run 5e2pdf convert adventure cos`

## Platform-Specific Notes

### macOS
- Use Homebrew for package management
- LuaLaTeX works best on Apple Silicon
- Ensure Xcode Command Line Tools are installed: `xcode-select --install`

### Linux
- Install development headers for compiled dependencies
- Use system package manager for LaTeX when possible
- Ensure Python development packages are installed

### Windows
- Use PowerShell or Command Prompt
- Consider WSL2 for better compatibility
- Ensure PATH includes Python, uv, and LaTeX binaries
- Some LaTeX packages may require manual installation

---

**Need help?** Visit our [GitHub Issues](https://github.com/sargeant/5e2pdf/issues) to report problems or ask questions.
