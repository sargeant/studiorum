# Image Placement (Simple Commands)

Studiorum uses small, explicit LaTeX commands. Pick the shape by name; keep arguments consistent.

Commands

- `\StudiorumImageInline[.8]{file}{caption}[label]` — inline, non‑floating.
- `\StudiorumImageFloat[.8]{file}{caption}[label]` — standard float `[htbp]`.
- `\StudiorumImageWide[.8]{file}{caption}[label]` — two‑column span in `twocolumn`.
- `\StudiorumImageFullpage[.95]{file}{caption}[label]` — dedicated page; keeps aspect.
- `\StudiorumImageFullpageBleed{file}{caption}[label]` — fills physical page (may distort).

Star forms remove caption and label: add `*` (e.g., `\StudiorumImageInline*{file}{}`), or use `...NoCaption` aliases.

Examples

```latex
% Inline, default width
\StudiorumImageInline{images/dragon.png}{Ancient Red Dragon}

% Float at 60% column width with label
\StudiorumImageFloat[.6]{images/loot.png}{Recovered treasure}[fig:loot]

% Two-column wide (in twocolumn documents)
\StudiorumImageWide{images/panorama.png}{Mountain panorama}

% Full page (keeps aspect)
\StudiorumImageFullpage{images/cover.jpg}{Cover art}

% Full page bleed (edge‑to‑edge; may distort)
\StudiorumImageFullpageBleed{images/plate.jpg}{Plate title}
```

See also: [Images and Galleries](user-guide/images-and-galleries.md) for multi‑image layouts.

Notes

- Width fraction defaults to 1.0 of line/column width (or `\textwidth` for wide/full‑page).
- Prefer the simple commands; advanced users can copy and customize these macros as needed.
