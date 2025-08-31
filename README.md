# Studiorum: Content toolkit for players of 5e compatible RPGs

[![Test Status](https://img.shields.io/github/actions/workflow/status/sargeant/studiorum/tests.yml)](https://github.com/sargeant/studiorum/actions)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/sargeant/studiorum/graph/badge.svg?token=2BXDX48UO8)](https://codecov.io/gh/sargeant/studiorum)

> [!CAUTION]
> This project is under development. Some features are buggy; some don't work at at all. Check back for v1.0 soon.

## What is this?

Studiorum is a Python project to process data from the 5e.tools website for the 5th edition of the world's most popular roleplaying game. It provides both a CLI and MCP interface to query data and build print-quality PDFs.

For full usage, check out the [Studiorum website](https://studiorum.dev/).

## Known Issues

While this code currently works, there are some rough edges and random things that need to be fixed. This is a non-exhaustive list.

- Some tables are just too long for the default handling and overrun pages (horizontially or vertically). You can fix this by editing the `.tex` output and playing with the layout or using \dndlongtable instead.
- DropCap at the start of chapters isn't handled at all; edit the `.tex` and play with `\DndDropCapLine{letter}{rest of all caps sentence}`
- Image support is there but broken; don't expect any images for now
- MCP support is experimental and often broken; my priority is getting the CLI solid for now, MCP later.
- Creature names are _always_ in bold, based on the original source data. This can get a bit exhausting when the same creature is mentioned repeatedily in narrative paragraphs. If it bugs you, edit the `.tex` and remove the `\textbf{}` wrapper around the text.
- Auto-installing the LaTeX template is half-baked; recommend you [install manually](https://github.com/ashonit/DND-5e-LaTeX-Template).
- If you use the same licensed fonts as WotC (`--fonts wotc`), the page numbers in the ToC have sizes that don't match each other. Fonts are not included as they are non-free.
- Your data might uncover use of 5etools {@tag} data that might appear raw in the `.tex` output. Please report if you encounter.
- Race / Background / Class / Subclass rendering currently unsupported. Future plans to add this.
- LaTeX sometimes needs multiple passes to correctly render the background/footer and table of contents. Studiorum attempts to handle this, but sometimes you might find it needs another pass. Manually run `xelatex <output.tex>` yourself multiple times to get it rendering right.
- When using auto-generated appendices (`--spell`, `--creatures`, and `--items`) the labelling and ordering of appendices is mixed up.
- Studiorum attempts to detect when a statblock is likely to be too big for a single column and switches to a wide one-column layout. Sometimes this detection gets it wrong and you'll find statblocks that run across two column or pages. You can fix by editing the `.tex` and putting `\onecolumn` right before the statblock, then `\twocolumn` immediately after.

## Data

The primary data used by this tool is the SRD. You can replace the primary data source with your own homebrew content compatible with the 5etools format using: `studiorum data set-primary <path to data directory>`

Additional single homebrew files can be added with `studiorum data add-homebrew <path>` or `studiorum data add-url <url>`

## Acknowledgements

This project wouldn't have been possible without the excellent LaTeX templates from [rpgtex](https://github.com/rpgtex/DND-5e-LaTeX-Template) and [ashonit](https://github.com/ashonit/DND-5e-LaTeX-Template).

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

The [System Reference Document](https://www.dndbeyond.com/srd) (SRD) v5.2.1 is included and licened under [Creative Commons: CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/deed.en) from Wizards of the Coast LLC.

## Disclaimer

Studiorum is an independent tool that provides a structured query interface and PDF rendering for the D&D™ System Reference Document (SRD) and with 5th edition compatible data from homebrew resources. D&D is a trademark of Wizards of the Coast LLC. This tool is not affiliated with or endorsed by Wizards of the Coast.
