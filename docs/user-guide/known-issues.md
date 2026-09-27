---
title: Known Issues
description: Current limitations and workarounds for studiorum
---

# Known Issues

Studiorum works, but it has rough edges. This list isn't exhaustive.

- Some tables are too long or too wide for the page and run off it. Edit the `.tex` output and adjust the layout, or use `\dndlongtable` instead.
- Chapters don't open with a drop cap. Edit the `.tex` and add `\DndDropCapLine{letter}{rest of all caps sentence}`.
- Maps inside a 5etools gallery render at half a column each, which is small for a dungeon map.
- MCP support is new and has had little use from real clients.
- Creature names are always bold, as in the source data. That gets tiring when a creature is named again and again in a paragraph; edit the `.tex` and remove the `\textbf{}` around the name if it bothers you.
- Studiorum doesn't install the LaTeX template. [Install it manually](https://github.com/ashonit/DND-5e-LaTeX-Template); `studiorum doctor` checks that it's found.
- With the licensed WotC fonts (`--fonts wotc`), the page numbers in the table of contents come out in different sizes. The fonts aren't included, as they aren't free.
- There are no convert commands for races, backgrounds, classes or subclasses. They render only where a book embeds them.
- Studiorum guesses when a creature's statblock is too big for one column and gives it both columns. The guess is sometimes wrong, and a statblock runs across two columns or pages. Edit the `.tex` and put `\onecolumn` right before the statblock and `\twocolumn` right after it.
- A tooltip in the 5etools data (`{@tip}`), such as a ship's miles per day, doesn't print.
