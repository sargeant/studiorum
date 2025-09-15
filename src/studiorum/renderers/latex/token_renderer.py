"""LaTeX token renderer for 5e creature tokens."""

from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.models.tokens import TokenSheet

logger = get_logger(__name__)


class TokenRenderer:
    """Renders token sheets to LaTeX."""

    def __init__(self) -> None:
        """Initialize token renderer."""
        logger.debug("TokenRenderer initialized")

    def render(self, token_sheet: "TokenSheet") -> str:
        """Render token sheet to LaTeX.

        Args:
            token_sheet: Token sheet data to render

        Returns:
            LaTeX document string
        """
        logger.debug(
            f"Rendering token sheet with {token_sheet.get_total_token_count()} tokens"
        )

        # Build LaTeX document
        latex_parts = []

        # Document setup
        latex_parts.append(self._render_document_header(token_sheet))

        # Token macro definitions
        latex_parts.append(self._render_token_macros())

        # Document content
        latex_parts.append("\\begin{document}")
        latex_parts.append("\\pagestyle{empty}")

        # Render tokens by size
        size_order = token_sheet.get_size_order()
        for i, size in enumerate(size_order):
            tokens = token_sheet.get_tokens_for_size(size)
            if tokens:
                latex_parts.append(self._render_size_section(size, tokens, token_sheet))

                # Add page break between sizes (except last)
                if i < len(size_order) - 1:
                    latex_parts.append("\\clearpage")

        latex_parts.append("\\end{document}")

        return "\n\n".join(latex_parts)

    def _render_document_header(self, token_sheet: "TokenSheet") -> str:
        """Render LaTeX document header and preamble."""
        paper_size = token_sheet.paper_size.lower()
        margins = token_sheet.margins

        return f"""\\documentclass[{paper_size}paper]{{article}}
\\usepackage[margin={margins}in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{tikz}}
\\usepackage{{xcolor}}
\\usepackage{{multicol}}
\\usepackage{{calc}}
\\usepackage{{ifthen}}

% Memory optimization for large token sheets
\\pgfmathsetmacro{{\\pgfpictureid}}{{0}}
\\tikzset{{every picture/.style={{execute at end picture={{\\global\\let\\pgfpictureid\\relax}}}}}}

% Disable page numbers
\\pagestyle{{empty}}
\\setlength{{\\parindent}}{{0pt}}

% Grid size constants (1 inch = 1 grid square)
\\newlength{{\\gridsize}}
\\setlength{{\\gridsize}}{{1in}}

% Token size definitions
\\newlength{{\\tinysize}}\\setlength{{\\tinysize}}{{0.5\\gridsize}}
\\newlength{{\\smallsize}}\\setlength{{\\smallsize}}{{0.75\\gridsize}}
\\newlength{{\\mediumsize}}\\setlength{{\\mediumsize}}{{1\\gridsize}}
\\newlength{{\\largesize}}\\setlength{{\\largesize}}{{2\\gridsize}}
\\newlength{{\\hugesize}}\\setlength{{\\hugesize}}{{3\\gridsize}}
\\newlength{{\\gargantuansize}}\\setlength{{\\gargantuansize}}{{4\\gridsize}}"""

    def _render_token_macros(self) -> str:
        """Render LaTeX token macro definitions."""
        return """% Token counter for numbering
\\newcounter{tokencount}

% Simple token macro
\\newcommand{\\StudiorumToken}[4][medium]{%
  % #1 = size (tiny/small/medium/large/huge/gargantuan)
  % #2 = image path
  % #3 = count
  % #4 = creature name
  \\setcounter{tokencount}{0}%
  \\whiledo{\\value{tokencount} < #3}{%
    \\stepcounter{tokencount}%
    \\begin{tikzpicture}[baseline=(current bounding box.center)]
      % Set token radius based on size
      \\ifthenelse{\\equal{#1}{tiny}}{%
        \\def\\tokenradius{0.25in}%
        \\def\\tokenwidth{0.5in}%
      }{}%
      \\ifthenelse{\\equal{#1}{small}}{%
        \\def\\tokenradius{0.375in}%
        \\def\\tokenwidth{0.75in}%
      }{}%
      \\ifthenelse{\\equal{#1}{medium}}{%
        \\def\\tokenradius{0.5in}%
        \\def\\tokenwidth{1in}%
      }{}%
      \\ifthenelse{\\equal{#1}{large}}{%
        \\def\\tokenradius{1in}%
        \\def\\tokenwidth{2in}%
      }{}%
      \\ifthenelse{\\equal{#1}{huge}}{%
        \\def\\tokenradius{1.5in}%
        \\def\\tokenwidth{3in}%
      }{}%
      \\ifthenelse{\\equal{#1}{gargantuan}}{%
        \\def\\tokenradius{2in}%
        \\def\\tokenwidth{4in}%
      }{}%

      % Only render if image path is provided
      \\ifthenelse{\\equal{#2}{}}{%
        % No image - render placeholder circle with creature name
        \\draw[line width=1pt, gray] (0,0) circle (\\tokenradius);
        \\node[align=center, font=\\sffamily\\tiny, text width=\\tokenwidth-0.2in] at (0,0) {#4};
      }{%
        % Render actual image token with clipping
        % Use path picture instead of scope to reduce memory usage
        \\pgfmathsetmacro{\\tokenimagewidth}{2.2*\\tokenradius/1in}
        \\path[draw, line width=0.5pt,
          path picture={
            \\node at (path picture bounding box.center) {
              \\includegraphics[width=\\tokenimagewidth in, keepaspectratio]{#2}
            };
          }] (0,0) circle (\\tokenradius);
      }

      % Add number if count > 1
      \\ifnum#3>1
        \\ifthenelse{\\equal{#1}{tiny}}{%
          \\node[fill=black, text=white, circle, inner sep=1pt, font=\\sffamily\\bfseries\\tiny] at (0.15in, -0.15in) {\\thetokencount};%
        }{}%
        \\ifthenelse{\\equal{#1}{small}}{%
          \\node[fill=black, text=white, circle, inner sep=1pt, font=\\sffamily\\bfseries\\scriptsize] at (0.2in, -0.2in) {\\thetokencount};%
        }{}%
        \\ifthenelse{\\equal{#1}{medium}}{%
          \\node[fill=black, text=white, circle, inner sep=1pt, font=\\sffamily\\bfseries\\scriptsize] at (0.3in, -0.3in) {\\thetokencount};%
        }{}%
        \\ifthenelse{\\equal{#1}{large}}{%
          \\node[fill=black, text=white, circle, inner sep=2pt, font=\\sffamily\\bfseries\\small] at (0.6in, -0.6in) {\\thetokencount};%
        }{}%
        \\ifthenelse{\\equal{#1}{huge}}{%
          \\node[fill=black, text=white, circle, inner sep=2pt, font=\\sffamily\\bfseries\\normalsize] at (0.9in, -0.9in) {\\thetokencount};%
        }{}%
        \\ifthenelse{\\equal{#1}{gargantuan}}{%
          \\node[fill=black, text=white, circle, inner sep=3pt, font=\\sffamily\\bfseries\\large] at (1.2in, -1.2in) {\\thetokencount};%
        }{}%
      \\fi

      % Add cutting guides for small tokens
      \\ifthenelse{\\equal{#1}{tiny} \\OR \\equal{#1}{small}}{%
        \\draw[gray, dashed, very thin] (0,0) circle (0.5in);  % 1" guide circle
      }{}
    \\end{tikzpicture}%
    \\hspace{0.1in}%
  }%
}"""

    def _render_size_section(
        self, size: str, tokens: list, token_sheet: "TokenSheet"
    ) -> str:
        """Render a section for tokens of a specific size."""
        from studiorum.core.models.tokens import TokenData

        # Get column count for this size
        columns = token_sheet.column_config.get(size, 1)

        # Section header
        section_parts = [f"\\section*{{{size.title()} Creatures}}"]

        # Start multicols if more than 1 column
        if columns > 1:
            section_parts.append(f"\\begin{{multicols}}{{{columns}}}")

        # Render each token
        for i, token in enumerate(tokens):
            if isinstance(token, TokenData):
                # Use actual image path if available
                image_path = (
                    str(token.image_path)
                    if token.image_path and token.image_path.exists()
                    else ""
                )

                section_parts.append(
                    f"\\StudiorumToken[{size}]{{{image_path}}}{{{token.count}}}{{{token.creature_name}}}"
                )

                # Add memory management for large batches
                # Clear page after every 20 tokens to prevent memory overflow
                if (i + 1) % 20 == 0 and i < len(tokens) - 1:
                    if columns > 1:
                        section_parts.append("\\end{multicols}")
                    section_parts.append("\\clearpage")
                    section_parts.append(f"\\begin{{multicols}}{{{columns}}}")

        # End multicols if started
        if columns > 1:
            section_parts.append("\\end{multicols}")

        return "\n".join(section_parts)

    def get_supported_sizes(self) -> list[str]:
        """Get list of supported token sizes."""
        return ["tiny", "small", "medium", "large", "huge", "gargantuan"]

    def get_default_columns(self) -> dict[str, int]:
        """Get default column configuration for each size."""
        return {
            "tiny": 6,
            "small": 6,
            "medium": 5,
            "large": 3,
            "huge": 2,
            "gargantuan": 1,
        }
