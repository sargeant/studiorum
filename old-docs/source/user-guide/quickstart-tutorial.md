# Quickstart Tutorial: Your First PDF in 30 Minutes

This tutorial will guide you through creating your first D&D 5e PDF from 5etools data. We'll start simple and build up to more complex examples.

## Prerequisites

Before starting, ensure you have:

1. **Python 3.11+** installed
2. **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
3. **5etools data** (we'll show you how to get this)
4. **LaTeX** (optional for PDF generation, required for final output)

## Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Install with uv (recommended)
uv pip install -e .

# Verify installation
5e2pdf --version
```

## Step 2: Getting 5etools Data

The tool needs 5etools JSON data to work. You have two options:

### Option A: Use the Mirror (Recommended for Testing)

```bash
# Clone the 5etools mirror
git clone https://github.com/5etools-mirror-2/5etools-mirror-2.github.io.git ~/5etools-data

# Configure 5e2pdf to use this data
export DND5E_DATA_PATH=~/5etools-data/data
```

### Option B: Use Local 5etools Installation

If you have 5etools running locally, point to its data directory:

```bash
export DND5E_DATA_PATH=/path/to/5etools/data
```

## Step 3: Your First Conversion - A Simple Spell

Let's start with something simple: converting a single spell to LaTeX.

```bash
# List available spells to confirm data is loaded
5e2pdf list spells | head -10

# Convert a single spell to LaTeX
5e2pdf convert spells "magic missile" --output magic-missile.tex

# Check the output
head -20 magic-missile.tex
```

Expected output:
```latex
\subsection{Magic Missile}
\label{spell:magic-missile}

\begin{DndSpellStats}
  Level: & 1st \\
  Casting Time: & 1 action \\
  Range: & 120 feet \\
  Components: & V, S \\
  Duration: & Instantaneous \\
\end{DndSpellStats}

You create three glowing darts of magical force...
```

## Step 4: Creating a Spellbook

Now let's create a complete spellbook for a wizard character:

```bash
# Convert all 1st level wizard spells
5e2pdf convert spells \
  --class wizard \
  --level 1 \
  --output wizard-level1-spells.tex

# Or create a full spellbook (levels 0-9)
5e2pdf convert spells \
  --class wizard \
  --output complete-wizard-spellbook.tex
```

## Step 5: Working with Creatures

Let's create a custom bestiary:

```bash
# List available creatures
5e2pdf list creatures --cr 1 | head -10

# Convert a single creature
5e2pdf convert creatures "goblin" --output goblin.tex

# Create a CR 1 encounter guide
5e2pdf convert creatures \
  --cr 1 \
  --output cr1-monsters.tex
```

## Step 6: Generating a Complete PDF

To generate a PDF, you need LaTeX installed. Here's the complete workflow:

```bash
# Install LaTeX (macOS)
brew install --cask mactex-no-gui

# Install LaTeX (Ubuntu/Debian)
sudo apt-get install texlive-full

# Clone the D&D 5e LaTeX template
git clone https://github.com/rpgtex/DND-5e-LaTeX-Template.git ~/dnd-template

# Create a complete document
cat > my-first-dnd-book.tex << 'EOF'
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}

\begin{document}

\chapter{Spells}
\input{wizard-level1-spells.tex}

\chapter{Creatures}
\input{goblin.tex}

\end{document}
EOF

# Compile to PDF
TEXINPUTS=".:~/dnd-template//:" pdflatex my-first-dnd-book.tex

# Open the PDF (macOS)
open my-first-dnd-book.pdf

# Or use the --open flag with 5e2pdf (if you have LaTeX)
5e2pdf convert creatures "goblin" --output goblin.pdf --open
```

## Step 7: Advanced Example - Custom Adventure

Let's create materials for a custom adventure:

```bash
# Create a directory for your adventure
mkdir my-adventure
cd my-adventure

# Generate encounter creatures (CR 1-3)
5e2pdf convert creatures \
  --cr 1-3 \
  --output encounters.tex

# Generate relevant spells
5e2pdf convert spells \
  --level 1-2 \
  --output available-spells.tex

# Generate magic items
5e2pdf convert items \
  --type "weapon" \
  --rarity "uncommon" \
  --output treasure.tex

# Create the master document
cat > adventure.tex << 'EOF'
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}

\begin{document}

\chapter{My First Adventure}

\section{Background}
The village of Greenhill has been plagued by goblin raids...

\chapter{Encounters}
\input{encounters.tex}

\chapter{Treasure}
\input{treasure.tex}

\appendix
\chapter{Spell Reference}
\input{available-spells.tex}

\end{document}
EOF

# Compile the complete adventure
TEXINPUTS=".:~/dnd-template//:" pdflatex adventure.tex
```

## Common Issues and Solutions

### Issue: "No data found"

**Solution**: Check your `DND5E_DATA_PATH` environment variable:
```bash
echo $DND5E_DATA_PATH
ls -la $DND5E_DATA_PATH
```

### Issue: "LaTeX Error: File `dndbook.cls' not found"

**Solution**: Ensure the D&D template is in your TEXINPUTS:
```bash
export TEXINPUTS=".:~/dnd-template//:"
```

### Issue: Large output files

**Solution**: Use filters to limit content:
```bash
# Limit output and pipe through head/tail
5e2pdf convert creatures --cr 1 | head -100
```

### Issue: PDF compilation fails

**Solution**: Check LaTeX logs:
```bash
# Run with error stopping disabled
pdflatex -interaction=nonstopmode adventure.tex

# Check the log
grep -A 5 "Error" adventure.log
```

## What's Next?

Now that you've created your first PDFs, explore more advanced features:

- [Working with Adventures](advanced-features.md#adventures) - Convert complete published adventures
- [Custom Formatting](advanced-features.md#formatting) - Customize the LaTeX output
- [Batch Processing](advanced-features.md#batch) - Process multiple files efficiently
- [Configuration Files](configuration.md) - Set up persistent preferences

## Quick Command Reference

```bash
# List content types
5e2pdf list [spells|creatures|items|adventures|books]

# Convert content
5e2pdf convert <type> <name> --output <file>

# Common filters
--class <class>      # Filter by class (spells)
--cr <range>         # Filter by CR (creatures)
--level <range>      # Filter by level (spells)
--type <type>        # Filter by type (items)
--rarity <rarity>    # Filter by rarity (items)

# Output options
--output <file>      # Save to file
--format [latex|pdf] # Output format
--open              # Open PDF after generation
```

## Tips for Success

1. **Start Small**: Begin with single items before attempting full books
2. **Use Filters**: Limit content to avoid overwhelming output
3. **Check Logs**: LaTeX errors often have helpful messages
4. **Save Templates**: Keep working .tex files as templates
5. **Version Control**: Track your custom content in git

## Getting Help

- Run `5e2pdf --help` for command options
- Check [Troubleshooting Guide](../troubleshooting.md) for common issues
- Review [examples/](../examples/) for more complex scenarios
- See [Configuration Guide](configuration.md) for customization

---

**Congratulations!** You've successfully created your first D&D 5e PDFs. From here, you can explore more advanced features, customize the output, or integrate 5e2pdf into your game preparation workflow.
