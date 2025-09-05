---
title: Known Issues
description: Current limitations and workarounds for studiorum
---

# Known Issues

While this code currently works, there are some rough edges and random things that need to be fixed. This is a non-exhaustive list.

- Some tables are just too long for the default handling and overrun pages (horizontially or vertically). You can fix this by editing the `.tex` output and playing with the layout or using \dndlongtable instead.
- DropCap at the start of chapters isn't handled at all; edit the `.tex` and play with `\DndDropCapLine{letter}{rest of all caps sentence}`
- Image support is there but broken; don't expect any images for now
- MCP support is experimental and often broken; my priority is getting the CLI solid for now, MCP later.
- Creature names are _always_ in bold, based on the original source data. This can get a bit exhausting when the same creature is mentioned repeatedily in narrative paragraphs. If it bugs you, edit the `.tex` and remove the `\textbf{}` wrapper around the text.
- Auto-installing the LaTeX template is half-baked; recommend you [install manually](https://github.com/ashonit/DND-5e-LaTeX-Template).
- If you use the same licensed fonts as WotC (`--fonts wotc`), the page numbers in the ToC have sizes that don't match each other. Fonts are not included as they are non-free.
- ~~Your data might uncover use of 5etools {@tag} data that might appear raw in the `.tex` output.~~ **Fixed:** Tag rendering has been improved to handle @homebrew, @creature, @spell, and @status tags properly.
- Race / Background / Class / Subclass rendering currently unsupported. Future plans to add this.
- LaTeX sometimes needs multiple passes to correctly render the background/footer and table of contents. Studiorum attempts to handle this, but sometimes you might find it needs another pass. Manually run `xelatex <output.tex>` yourself multiple times to get it rendering right.
- When using auto-generated appendices (`--spell`, `--creatures`, and `--items`) the labelling and ordering of appendices is mixed up. **New:** `--ultimate-appendix` provides recursive appendices as an alternative approach.
- Studiorum attempts to detect when a statblock is likely to be too big for a single column and switches to a wide one-column layout. Sometimes this detection gets it wrong and you'll find statblocks that run across two column or pages. You can fix by editing the `.tex` and putting `\onecolumn` right before the statblock, then `\twocolumn` immediately after. **Improved:** Better support for inset statblocks and homebrew content rendering.
