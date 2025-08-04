---
layout: landing
description: Convert D&D 5e JSON data from 5e.tools to beautifully formatted LaTeX/PDF documents
---

# 5e2pdf

```{toctree}
:hidden:
:caption: For Users

quickstart
user-guide/index
```

```{toctree}
:hidden:
:caption: For Developers
:max_depth: 2

developer/index
developer/contributing
api/index
```

```{rst-class} lead
Convert D&D 5e JSON data from [5e.tools](https://5e.tools) to beautifully formatted LaTeX/PDF documents.
```

```{warning}
This tool is under active development and not yet in a fully working state.
```

## Overview

5e2pdf is a Python CLI tool that transforms the comprehensive D&D 5e JSON datasets from 5e.tools into professional-quality PDF documents using LaTeX. Whether you're a DM preparing for sessions or a player creating reference materials, 5e2pdf provides the tools to create custom, print-ready D&D content.

## Key Features

````{grid} 1 2 2 2
:gutter: 3

```{grid-item-card}
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/book-open.svg" alt="Book icon"></span> Wide Content Support
+++
Works with all 5e.tools JSON data including spells, creatures, items, adventures, and more
```

```{grid-item-card}
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/sparkles.svg" alt="Sparkles icon"></span> Professional Typography
+++
LaTeX-based rendering for publication-quality output with beautiful formatting
```

```{grid-item-card}
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/adjustments-horizontal.svg" alt="Adjustments icon"></span> Flexible Output
+++
Generate PDFs for specific content types, sources, or custom collections
```

```{grid-item-card}
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/document-text.svg" alt="Document icon"></span> Developer Documentation
+++
Documentation for coders who want to extend or enhance
```
````

## Quick Start

Get up and running with 5e2pdf in minutes:

````{grid} 1 1 2 2
:gutter: 2

```{grid-item-card}
:text-align: center
:class-header: highlight-card
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/arrow-down-tray.svg" alt="Download icon"></span> Install

~~~bash
pip install 5e2pdf
~~~
```

```{grid-item-card}
:text-align: center
:class-header: highlight-card
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/cog-6-tooth.svg" alt="Settings icon"></span> Setup Sources

~~~bash
5e2pdf setup wizard
~~~
```

```{grid-item-card}
:text-align: center
:class-header: highlight-card
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/document-duplicate.svg" alt="Document icon"></span> Generate a Book

~~~bash
5e2pdf convert book phb --pdf --a4
~~~
```

```{grid-item-card}
:text-align: center
:class-header: highlight-card
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/map.svg" alt="Map icon"></span> Create Adventures

~~~bash
5e2pdf convert adventure lmop --pdf
~~~
```
````

## Getting Started

````{grid} 1 1 3 3
:gutter: 3

```{grid-item-card}
:link: user-guide/index
:link-type: doc
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/academic-cap.svg" alt="Academic cap icon"></span> User Guide
+++
Complete guide for users getting started with 5e2pdf
```

```{grid-item-card}
:link: api/index
:link-type: doc
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/wrench.svg" alt="Wrench icon"></span> API Reference
+++
Comprehensive API documentation and references
```

```{grid-item-card}
:link: examples/index
:link-type: doc
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/light-bulb.svg" alt="Light bulb icon"></span> Examples
+++
Practical examples and tutorials to get you started
```
````

````{grid} 1 1 2 2
:gutter: 3
:class-container: action-section

```{grid-item-card}
:text-align: center
:class-header: action-button

[<span class="heroicon"><img src="/_static/icons/rocket-launch.svg" alt="Rocket icon"></span> Get Started](quickstart)
+++
Start using 5e2pdf today
```

```{grid-item-card}
:text-align: center
:class-header: action-button

[<span class="heroicon"><img src="/_static/icons/bug-ant.svg" alt="Bug icon"></span> Report Issues](https://github.com/sargeant/5e2pdf/issues)
+++
Help improve 5e2pdf
```
````

## Project Information

````{grid} 1 2 4 4
:gutter: 2

```{grid-item-card} GitHub
:text-align: center

[sargeant/5e2pdf](https://github.com/sargeant/5e2pdf)
```

```{grid-item-card} Version
:text-align: center

{{version}}
```

```{grid-item-card} Python
:text-align: center

3.12+
```

```{grid-item-card} License
:text-align: center

MIT
```
````

```{rst-class} text-center lead
*Built with ❤️ for the D&D community*
```
