# Image Placement (Manual Mode)

This page documents the Studiorum manual image placement system using LaTeX macros.

- Default output uses `\StudiorumImage{placement}{path}{caption}` with conservative sizing and `keepaspectratio`.
- Supported placements (Phase 1+2): `inline`, `pagewidth-top`, `pagewidth-bottom`, `fullpage`, `column-left`, `column-right`.
- Experimental (approximate fallback): `anchor-NW`, `anchor-NE`, `anchor-SW`, `anchor-SE`, `fullpage-nomargin`.
- Options: `label=fig:...`, `draft=true|false`, `caption=below|above|none`.
- Draft mode shows placeholders for faster compilation.

See also:

- User guide: [Images and Galleries](user-guide/images-and-galleries.md) for multi‑image layouts (grid, sequential, comparison, showcase).

Example:

```latex
% StudiorumImage placement options: inline, pagewidth-top, pagewidth-bottom, fullpage
% Documentation: https://studiorum.dev/image-placement/
% Auto-generated label: fig:ancient-red-dragon
\StudiorumImage[label=fig:ancient-red-dragon]{inline}{images/dragon.png}{Ancient Red Dragon}
```

Smart placement remains available behind `--placement-mode=smart` but is deprecated; manual macros are recommended.
