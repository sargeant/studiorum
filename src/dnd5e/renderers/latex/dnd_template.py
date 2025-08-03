"""DND-5e-LaTeX-Template integration utilities.

This module provides functionality to detect, validate, and configure
the DND-5e-LaTeX-Template for use with 5e2pdf.
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()


class DNDTemplateManager:
    """Manages DND-5e-LaTeX-Template integration and configuration."""

    def __init__(self) -> None:
        """Initialize DND template manager."""
        self.template_files = [
            "dndbook.cls",
            "dndcore.def",
            "dndoptions.clo",
            "dnd.sty",
        ]
        self.required_packages = [
            "expl3",
            "fancyhdr",
            "geometry",
            "xcolor",
            "pgf",
            "tikz",
        ]

    def check_template_availability(self) -> tuple[bool, list[str]]:
        """Check if DND-5e-LaTeX-Template is available.

        Returns:
            Tuple of (is_available, missing_files)
        """
        from dnd5e.core.logging import get_logger

        logger = get_logger(__name__)

        logger.debug("Checking DND template availability")
        logger.debug(f"Required template files: {self.template_files}")

        missing_files = []

        for template_file in self.template_files:
            logger.debug(f"Checking for template file: {template_file}")
            if not self._find_template_file(template_file):
                logger.debug(f"Template file missing: {template_file}")
                missing_files.append(template_file)
            else:
                logger.debug(f"Template file found: {template_file}")

        is_available = len(missing_files) == 0
        logger.debug(f"Template availability result: {is_available}")
        if missing_files:
            logger.debug(f"Missing template files: {missing_files}")

        return is_available, missing_files

    def _find_template_file(self, filename: str) -> Path | None:
        """Find template file in LaTeX search paths.

        Args:
            filename: Name of template file to find

        Returns:
            Path to file if found, None otherwise
        """
        from dnd5e.core.logging import get_logger

        logger = get_logger(__name__)

        logger.debug(f"Looking for template file: {filename}")

        try:
            # Use kpsewhich to find file in LaTeX search paths
            logger.debug(f"Running kpsewhich {filename}")
            result = subprocess.run(
                ["kpsewhich", filename], capture_output=True, text=True, timeout=30
            )

            logger.debug(f"kpsewhich returncode: {result.returncode}")
            logger.debug(f"kpsewhich stdout: '{result.stdout.strip()}'")
            logger.debug(f"kpsewhich stderr: '{result.stderr.strip()}'")

            if result.returncode == 0 and result.stdout.strip():
                found_path = Path(result.stdout.strip())
                logger.debug(f"Found {filename} via kpsewhich at: {found_path}")
                return found_path
            else:
                logger.debug(f"kpsewhich failed to find {filename}")

        except subprocess.TimeoutExpired:
            logger.warning(f"kpsewhich timeout for {filename}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"kpsewhich error for {filename}: {e}")
        except FileNotFoundError:
            logger.warning(f"kpsewhich command not found when looking for {filename}")

        # Fallback: Check common installation directories (for CI environments)
        fallback_paths = [
            Path("/usr/share/texlive/texmf-local/tex/latex/dnd") / filename,
            Path("/usr/local/share/texmf/tex/latex/dnd") / filename,
            Path.home() / "texmf" / "tex" / "latex" / "dnd" / filename,
        ]

        logger.debug(f"Checking fallback paths for {filename}:")
        for path in fallback_paths:
            logger.debug(f"  Checking: {path} - exists: {path.exists()}")
            if path.exists():
                logger.debug(f"Found {filename} via fallback at: {path}")
                return path

        logger.debug(f"Template file {filename} not found in any location")
        return None

    def check_latex_installation(self) -> tuple[bool, str]:
        """Check if LaTeX is properly installed.

        Returns:
            Tuple of (is_installed, version_info)
        """
        try:
            # Check for LaTeX engine
            result = subprocess.run(
                ["pdflatex", "--version"], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                version_line = result.stdout.split("\n")[0]
                return True, version_line

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

        return False, "LaTeX not found"

    def check_required_packages(self) -> tuple[bool, list[str]]:
        """Check if required LaTeX packages are available.

        Returns:
            Tuple of (all_available, missing_packages)
        """
        missing_packages = []

        for package in self.required_packages:
            if not self._check_package_available(package):
                missing_packages.append(package)

        return len(missing_packages) == 0, missing_packages

    def _check_package_available(self, package: str) -> bool:
        """Check if a LaTeX package is available.

        Args:
            package: Name of package to check

        Returns:
            True if package is available
        """
        try:
            # Use kpsewhich to find package file
            result = subprocess.run(
                ["kpsewhich", f"{package}.sty"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            return result.returncode == 0 and bool(result.stdout.strip())

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            return False

    def get_texmf_paths(self) -> list[Path]:
        """Get LaTeX TEXMF paths where template could be installed.

        Returns:
            List of potential installation paths
        """
        paths = []

        try:
            # Get TEXMFHOME (user's personal tex directory)
            result = subprocess.run(
                ["kpsewhich", "--var-value=TEXMFHOME"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and result.stdout.strip():
                texmf_home = Path(result.stdout.strip())
                paths.append(texmf_home / "tex" / "latex" / "dnd")

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

        # Fallback to common user locations
        if not paths:
            home = Path.home()
            paths.extend(
                [
                    home / "texmf" / "tex" / "latex" / "dnd",
                    home / "Library" / "texmf" / "tex" / "latex" / "dnd",  # macOS
                    home / ".texlive" / "texmf-var" / "tex" / "latex" / "dnd",  # Linux
                ]
            )

        return paths

    def get_system_info(self) -> dict[str, str]:
        """Get system information for troubleshooting.

        Returns:
            Dictionary with system information
        """
        info = {
            "platform": sys.platform,
            "python_version": sys.version,
        }

        # Get LaTeX distribution info
        latex_available, latex_version = self.check_latex_installation()
        info["latex_available"] = str(latex_available)
        info["latex_version"] = latex_version

        # Get TeX Live version if available
        try:
            result = subprocess.run(
                ["tex", "--version"], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                tex_version = result.stdout.split("\n")[0]
                info["tex_version"] = tex_version

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            info["tex_version"] = "Not available"

        return info

    def create_installation_guide(self) -> str:
        """Create installation guide text.

        Returns:
            Installation guide as string
        """
        guide = """
# DND-5e-LaTeX-Template Installation Guide

## Prerequisites
1. Install a full LaTeX distribution:
   - **Ubuntu/Debian**: `sudo apt-get install texlive-full`
   - **macOS**: Install MacTeX via Homebrew: `brew install mactex`
   - **Windows**: Install MiKTeX from https://miktex.org/

## Installation Methods

### Method 1: User Install (Recommended)
1. Clone or download the DND-5e-LaTeX-Template repository
2. Copy template files to your TEXMFHOME directory:
   ```bash
   # Find your TEXMFHOME directory
   kpsewhich --var-value=TEXMFHOME

   # Create directory and copy files
   mkdir -p ~/texmf/tex/latex/dnd
   cp *.cls *.sty *.def *.clo ~/texmf/tex/latex/dnd/
   ```

### Method 2: Project-Level Install
1. Clone template to your project's lib/ directory:
   ```bash
   git clone https://github.com/ashonit/DND-5e-LaTeX-Template.git lib/dnd
   ```
2. Set TEXINPUTS when compiling:
   ```bash
   TEXINPUTS=./lib/dnd: pdflatex document.tex
   ```

## Verification
Test the installation:
```bash
# Check if template classes are found
kpsewhich dndbook.cls
kpsewhich dndarticle.cls
```

## Troubleshooting
- Ensure LaTeX distribution is complete (use full installations)
- Check that template files are in a directory LaTeX can find
- Verify TEXMFHOME is set correctly
- For project-level installs, ensure TEXINPUTS includes the template directory
"""
        return guide.strip()

    def print_status_report(self) -> None:
        """Print comprehensive status report."""
        console.print("\n[bold blue]DND-5e-LaTeX-Template Status Report[/bold blue]")
        console.print("=" * 50)

        # System info
        info = self.get_system_info()
        console.print("\n[bold]System Information[/bold]")
        console.print(f"Platform: {info['platform']}")
        console.print(f"LaTeX Available: {info['latex_available']}")
        console.print(f"LaTeX Version: {info['latex_version']}")

        # Template availability
        template_available, missing_files = self.check_template_availability()
        console.print("\n[bold]Template Status[/bold]")

        if template_available:
            console.print("[green]✓ DND-5e-LaTeX-Template is available[/green]")
        else:
            console.print("[red]✗ DND-5e-LaTeX-Template not found[/red]")
            console.print(f"Missing files: {', '.join(missing_files)}")

        # Package availability
        packages_available, missing_packages = self.check_required_packages()
        console.print("\n[bold]Required Packages[/bold]")

        if packages_available:
            console.print("[green]✓ All required packages available[/green]")
        else:
            console.print("[red]✗ Missing required packages[/red]")
            console.print(f"Missing: {', '.join(missing_packages)}")

        # Installation paths
        paths = self.get_texmf_paths()
        console.print("\n[bold]Potential Installation Paths[/bold]")
        for path in paths:
            exists = path.exists()
            status = "[green]✓[/green]" if exists else "[yellow]?[/yellow]"
            console.print(f"{status} {path}")


def check_dnd_template_status() -> bool:
    """Quick check if DND template is ready for use.

    Returns:
        True if template is ready, False otherwise
    """
    from dnd5e.core.logging import get_logger

    logger = get_logger(__name__)

    logger.debug("Performing DND template status check")
    manager = DNDTemplateManager()

    # Check LaTeX installation
    logger.debug("Checking LaTeX installation")
    latex_available, latex_version = manager.check_latex_installation()
    logger.debug(f"LaTeX available: {latex_available}, version: {latex_version}")
    if not latex_available:
        logger.debug("LaTeX not available - template check failed")
        return False

    # Check template availability
    logger.debug("Checking template file availability")
    template_available, missing_files = manager.check_template_availability()
    logger.debug(f"Template available: {template_available}")
    if not template_available:
        logger.debug(f"Template files missing: {missing_files} - template check failed")
        return False

    # Check required packages
    logger.debug("Checking required LaTeX packages")
    packages_available, missing_packages = manager.check_required_packages()
    logger.debug(f"Packages available: {packages_available}")
    if not packages_available:
        logger.debug(f"Missing packages: {missing_packages} - template check failed")

    final_result = packages_available
    logger.debug(f"Final DND template status: {final_result}")
    return final_result


def get_dnd_document_class_options() -> dict[str, dict[str, str]]:
    """Get available document class options.

    Returns:
        Dictionary mapping class names to their options
    """
    return {
        "dndbook": {
            "bg": "Enable background images and footer decorations",
            "justified": "Justify text columns for professional appearance",
            "fancy": "Add full-page background for part separators",
            "highcontrast": "Print-friendly high contrast styling",
            "10pt": "Set base font size to 10 points",
            "11pt": "Set base font size to 11 points (default)",
            "12pt": "Set base font size to 12 points",
            "a4paper": "Use A4 paper size",
            "letterpaper": "Use US Letter paper size (default)",
            "twocolumn": "Use two-column layout",
            "onecolumn": "Use single-column layout (default)",
        },
        "dndarticle": {
            "bg": "Enable background images and footer decorations",
            "justified": "Justify text columns for professional appearance",
            "highcontrast": "Print-friendly high contrast styling",
            "10pt": "Set base font size to 10 points",
            "11pt": "Set base font size to 11 points (default)",
            "12pt": "Set base font size to 12 points",
            "a4paper": "Use A4 paper size",
            "letterpaper": "Use US Letter paper size (default)",
            "twocolumn": "Use two-column layout",
            "onecolumn": "Use single-column layout (default)",
        },
    }


def get_recommended_class_options(content_type: str) -> list[str]:
    """Get recommended class options for different content types.

    Args:
        content_type: Type of content (book, supplement, reference, etc.)

    Returns:
        List of recommended class options
    """
    recommendations = {
        "book": ["bg", "justified", "twocolumn"],
        "supplement": ["bg", "justified", "twocolumn"],
        "reference": ["bg", "justified", "twocolumn"],
        "article": ["bg", "justified", "onecolumn"],
        "adventure": ["bg", "justified", "twocolumn", "fancy"],
        "homebrew": ["bg", "justified", "twocolumn"],
    }

    return recommendations.get(content_type, ["bg", "justified"])
