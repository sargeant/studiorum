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
This tool is under development and not in a fully working state.
```

## Overview

5e2pdf is a Python CLI tool that transforms the D&D 5e JSON datasets from 5e.tools into high-quality PDF documents using LaTeX. Whether you're a DM preparing for sessions or a player creating reference materials, 5e2pdf provides the tools to create custom, print-ready D&D content.

## Under Development

This tool is a work in progress. Not all features are working, however it can:

- Load and parse the full 5e.tools data source, or any homebrew source
- Generate a `.tex` document for books/adventures that will build using the [DND-5e-LaTeX-Template from ashonit](https://github.com/ashonit/DND-5e-LaTeX-Template)

The content is 95% complete for adventures, 70% for books.

This was built for the purpose of generating PDFs, however you could use the `dnd5e` Python library to generate whatever content you wish.

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
pip install git+https://github.com/sargeant/5e2pdf#egg=5e2pdf
~~~
(PyPI coming later)
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
5e2pdf convert book phb
~~~
```

```{grid-item-card}
:text-align: center
:class-header: highlight-card
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/map.svg" alt="Map icon"></span> Create Adventures

~~~bash
5e2pdf convert adventure lmop
~~~
```
````

## Documentation

````{grid} 1 1 2 2
:gutter: 3

```{grid-item-card}
:link: http://5e2pdf.sargeant.net.nz/user-guide
:link-type: doc
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/academic-cap.svg" alt="Academic cap icon"></span> User Guide
+++
Complete guide for users getting started with 5e2pdf
```

```{grid-item-card}
:link: http://5e2pdf.sargeant.net.nz/developer
:link-type: doc
:text-align: center
:class-title: sd-card-title-large

<span class="heroicon"><img src="/_static/icons/wrench.svg" alt="Wrench icon"></span> API Reference
+++
Developer documentation and API reference for `dnd5e`
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
*Over-engineered for a niche use case* -- Claude Sonnet 4
```
