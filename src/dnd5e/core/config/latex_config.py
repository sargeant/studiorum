"""LaTeX-specific configuration for 5e2pdf."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator


class LaTeXDocumentConfig(BaseModel):
    """Configuration for LaTeX document generation."""

    # Document class selection
    document_class: str = Field(
        default="dndbook",
        description="LaTeX document class to use (dndbook, dndarticle)",
    )

    # Class options
    class_options: list[str] = Field(
        default_factory=lambda: ["bg", "justified", "twocolumn"],
        description="List of class options to pass to document class",
    )

    # Font configuration
    font_scheme: str = Field(
        default="dmsguild",
        description="Font scheme to use (dmsguild, commercial, system)",
    )

    # Paper and layout
    paper_size: str = Field(
        default="letterpaper", description="Paper size (letterpaper, a4paper, a5paper)"
    )

    font_size: str = Field(
        default="11pt", description="Base font size (10pt, 11pt, 12pt)"
    )

    # Visual options
    enable_background: bool = Field(
        default=True, description="Enable background images and decorations"
    )

    high_contrast: bool = Field(
        default=False, description="Use high contrast mode for printing"
    )

    justified_text: bool = Field(default=True, description="Justify text columns")

    fancy_headers: bool = Field(
        default=False, description="Enable fancy headers for adventure-style documents"
    )

    # Content options
    two_column: bool = Field(default=True, description="Use two-column layout")

    include_toc: bool = Field(default=True, description="Include table of contents")

    include_index: bool = Field(default=False, description="Include index")

    # Custom options
    custom_class_options: list[str] = Field(
        default_factory=list, description="Additional custom class options"
    )

    @validator("document_class")
    def validate_document_class(cls, v):
        """Validate document class selection."""
        valid_classes = ["dndbook", "dndarticle"]
        if v not in valid_classes:
            raise ValueError(f"Document class must be one of: {valid_classes}")
        return v

    @validator("font_scheme")
    def validate_font_scheme(cls, v):
        """Validate font scheme selection."""
        valid_schemes = ["dmsguild", "commercial", "system"]
        if v not in valid_schemes:
            raise ValueError(f"Font scheme must be one of: {valid_schemes}")
        return v

    @validator("paper_size")
    def validate_paper_size(cls, v):
        """Validate paper size selection."""
        valid_sizes = ["letterpaper", "a4paper", "a5paper"]
        if v not in valid_sizes:
            raise ValueError(f"Paper size must be one of: {valid_sizes}")
        return v

    @validator("font_size")
    def validate_font_size(cls, v):
        """Validate font size selection."""
        valid_sizes = ["10pt", "11pt", "12pt"]
        if v not in valid_sizes:
            raise ValueError(f"Font size must be one of: {valid_sizes}")
        return v

    def get_class_options_list(self) -> list[str]:
        """Get complete list of class options for document class.

        Returns:
            List of class options to pass to LaTeX
        """
        options = []

        # Add configured class options
        options.extend(self.class_options)

        # Add paper size and font size
        options.extend([self.paper_size, self.font_size])

        # Add conditional options based on boolean flags
        if self.enable_background:
            if "bg" not in options:
                options.append("bg")
        else:
            options = [opt for opt in options if opt != "bg"]

        if self.high_contrast:
            options.append("highcontrast")

        if self.justified_text:
            if "justified" not in options:
                options.append("justified")
        else:
            options = [opt for opt in options if opt != "justified"]

        if self.fancy_headers:
            options.append("fancy")

        if self.two_column:
            options.append("twocolumn")
        else:
            options.append("onecolumn")

        # Add custom options
        options.extend(self.custom_class_options)

        # Remove duplicates while preserving order
        seen = set()
        unique_options = []
        for option in options:
            if option not in seen:
                seen.add(option)
                unique_options.append(option)

        return unique_options


class LaTeXEngineConfig(BaseModel):
    """Configuration for LaTeX engine and compilation."""

    # Engine selection
    engine: str = Field(
        default="pdflatex",
        description="LaTeX engine to use (pdflatex, lualatex, xelatex)",
    )

    # Compilation options
    shell_escape: bool = Field(
        default=False, description="Enable shell escape for advanced features"
    )

    interaction_mode: str = Field(
        default="nonstopmode",
        description="LaTeX interaction mode (nonstopmode, batchmode, scrollmode)",
    )

    # Output options
    output_format: str = Field(
        default="pdf", description="Output format (pdf, dvi, ps)"
    )

    output_directory: Path | None = Field(
        default=None, description="Output directory for LaTeX files"
    )

    # Timeout and performance
    timeout: int = Field(default=300, description="Compilation timeout in seconds")

    max_iterations: int = Field(
        default=3, description="Maximum compilation iterations for cross-references"
    )

    # Debugging
    halt_on_error: bool = Field(
        default=False, description="Halt compilation on first error"
    )

    verbose: bool = Field(default=False, description="Enable verbose output")

    @validator("engine")
    def validate_engine(cls, v):
        """Validate LaTeX engine selection."""
        valid_engines = ["pdflatex", "lualatex", "xelatex"]
        if v not in valid_engines:
            raise ValueError(f"LaTeX engine must be one of: {valid_engines}")
        return v

    @validator("interaction_mode")
    def validate_interaction_mode(cls, v):
        """Validate interaction mode."""
        valid_modes = ["nonstopmode", "batchmode", "scrollmode", "errorstopmode"]
        if v not in valid_modes:
            raise ValueError(f"Interaction mode must be one of: {valid_modes}")
        return v

    def get_compilation_command(self, tex_file: Path) -> list[str]:
        """Get LaTeX compilation command.

        Args:
            tex_file: Path to TeX file to compile

        Returns:
            List of command arguments
        """
        command = [self.engine]

        # Add interaction mode
        command.append(f"-interaction={self.interaction_mode}")

        # Add shell escape if enabled
        if self.shell_escape:
            command.append("-shell-escape")

        # Add output directory if specified
        if self.output_directory:
            command.extend(["-output-directory", str(self.output_directory)])

        # Add halt on error if enabled
        if self.halt_on_error:
            command.append("-halt-on-error")

        # Add the source file
        command.append(str(tex_file))

        return command


class LaTeXTemplateConfig(BaseModel):
    """Configuration for LaTeX template system."""

    # Template paths
    template_dir: Path = Field(
        default_factory=lambda: Path("src/dnd5e/renderers/latex/templates"),
        description="Directory containing LaTeX templates",
    )

    dnd_template_dir: Path | None = Field(
        default=None, description="Directory containing DND-5e-LaTeX-Template files"
    )

    # Template selection
    default_template: str = Field(
        default="book", description="Default template to use for documents"
    )

    # Template options
    template_cache_enabled: bool = Field(
        default=True, description="Enable template caching"
    )

    template_debug: bool = Field(default=False, description="Enable template debugging")

    # Content type mappings
    content_type_templates: dict[str, str] = Field(
        default_factory=lambda: {
            "adventure": "book",
            "sourcebook": "book",
            "supplement": "supplement",
            "reference": "reference",
            "article": "article",
            "homebrew": "supplement",
        },
        description="Mapping of content types to templates",
    )

    # DND template integration
    use_dnd_template: bool = Field(
        default=True, description="Use DND-5e-LaTeX-Template document classes"
    )

    check_template_availability: bool = Field(
        default=True, description="Check template availability before compilation"
    )

    def get_template_for_content_type(self, content_type: str) -> str:
        """Get template name for content type.

        Args:
            content_type: Type of content

        Returns:
            Template name to use
        """
        return self.content_type_templates.get(content_type, self.default_template)


class LaTeXConfig(BaseModel):
    """Complete LaTeX configuration."""

    document: LaTeXDocumentConfig = Field(
        default_factory=LaTeXDocumentConfig, description="Document configuration"
    )

    engine: LaTeXEngineConfig = Field(
        default_factory=LaTeXEngineConfig, description="Engine configuration"
    )

    template: LaTeXTemplateConfig = Field(
        default_factory=LaTeXTemplateConfig, description="Template configuration"
    )

    def get_content_type_config(self, content_type: str) -> dict[str, str | list[str]]:
        """Get optimized configuration for specific content type.

        Args:
            content_type: Type of content being rendered

        Returns:
            Configuration dictionary optimized for content type
        """
        config = {
            "template": self.template.get_template_for_content_type(content_type),
            "document_class": self.document.document_class,
            "class_options": self.document.get_class_options_list(),
        }

        # Content-specific optimizations
        if content_type in ["adventure", "sourcebook"]:
            config["document_class"] = "dndbook"
            if self.document.fancy_headers:
                config["class_options"].append("fancy")

        elif content_type in ["supplement", "reference"]:
            config["document_class"] = "dndbook"
            # Supplements typically don't need fancy headers
            config["class_options"] = [
                opt for opt in config["class_options"] if opt != "fancy"
            ]

        elif content_type == "article":
            config["document_class"] = "dndarticle"
            # Articles are typically single-column
            config["class_options"] = [
                opt if opt != "twocolumn" else "onecolumn"
                for opt in config["class_options"]
            ]

        return config


def get_default_latex_config() -> LaTeXConfig:
    """Get default LaTeX configuration.

    Returns:
        Default LaTeX configuration
    """
    return LaTeXConfig()


def get_latex_config_for_content_type(content_type: str) -> LaTeXConfig:
    """Get LaTeX configuration optimized for content type.

    Args:
        content_type: Type of content being rendered

    Returns:
        LaTeX configuration optimized for content type
    """
    config = get_default_latex_config()

    # Apply content-specific optimizations
    if content_type in ["adventure", "sourcebook"]:
        config.document.fancy_headers = True
        config.document.include_toc = True
        config.document.two_column = True

    elif content_type in ["supplement", "reference"]:
        config.document.fancy_headers = False
        config.document.include_toc = True
        config.document.two_column = True

    elif content_type == "article":
        config.document.document_class = "dndarticle"
        config.document.fancy_headers = False
        config.document.include_toc = False
        config.document.two_column = False

    return config
