# Cookbook: Common Recipes

This cookbook provides ready-to-use examples for common 5e2pdf tasks.

## Recipe 1: Creating a Custom Spellbook for Your Character

**Goal**: Generate a PDF with only the spells your wizard character knows.

### Step 1: Create a spell list file

```yaml
# my-wizard-spells.yaml
character: "Elara the Wise"
level: 5
spells:
  cantrips:
    - fire bolt
    - mage hand
    - prestidigitation
  level_1:
    - detect magic
    - identify
    - magic missile
    - shield
    - sleep
  level_2:
    - misty step
    - scorching ray
    - web
  level_3:
    - counterspell
    - fireball
```

### Step 2: Convert specific spells

```bash
# Extract spell names and convert
cat my-wizard-spells.yaml | grep "    -" | sed 's/    - //' > spell-list.txt

# Convert each spell
while read spell; do
  5e2pdf convert spells "$spell" --output "spells/${spell// /-}.tex"
done < spell-list.txt
```

### Step 3: Create the spellbook document

```latex
% my-spellbook.tex
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}
\title{Elara's Spellbook}

\begin{document}
\maketitle

\chapter{Cantrips}
\input{spells/fire-bolt.tex}
\input{spells/mage-hand.tex}
\input{spells/prestidigitation.tex}

\chapter{1st Level Spells}
\input{spells/detect-magic.tex}
\input{spells/identify.tex}
\input{spells/magic-missile.tex}
\input{spells/shield.tex}
\input{spells/sleep.tex}

\chapter{2nd Level Spells}
\input{spells/misty-step.tex}
\input{spells/scorching-ray.tex}
\input{spells/web.tex}

\chapter{3rd Level Spells}
\input{spells/counterspell.tex}
\input{spells/fireball.tex}

\end{document}
```

### Step 4: Generate the PDF

```bash
# Set template path and compile
export TEXINPUTS=".:~/dnd-template//:"
pdflatex my-spellbook.tex
pdflatex my-spellbook.tex  # Run twice for references
open my-spellbook.pdf
```

## Recipe 2: Encounter Builder for a Specific Level Range

**Goal**: Create a reference document with all CR-appropriate monsters for a level 3-5 party.

### Script: encounter-builder.sh

```bash
#!/bin/bash
# encounter-builder.sh - Generate encounter reference for party level range

PARTY_LEVEL_MIN=3
PARTY_LEVEL_MAX=5

# CR ranges for different encounter difficulties
EASY_CR="0.125-1"
MEDIUM_CR="0.5-2"
HARD_CR="1-3"
DEADLY_CR="2-5"

# Create output directory
mkdir -p encounters

# Generate encounters by difficulty
echo "Generating Easy Encounters (CR $EASY_CR)..."
5e2pdf convert creatures \
  --cr "$EASY_CR" \
  --output encounters/easy-encounters.tex

echo "Generating Medium Encounters (CR $MEDIUM_CR)..."
5e2pdf convert creatures \
  --cr "$MEDIUM_CR" \
  --output encounters/medium-encounters.tex

echo "Generating Hard Encounters (CR $HARD_CR)..."
5e2pdf convert creatures \
  --cr "$HARD_CR" \
  --output encounters/hard-encounters.tex

echo "Generating Deadly Encounters (CR $DEADLY_CR)..."
5e2pdf convert creatures \
  --cr "$DEADLY_CR" \
  --output encounters/deadly-encounters.tex

# Create master document
cat > encounters/encounter-manual.tex << 'EOF'
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}
\title{Encounter Manual: Level 3-5 Party}

\begin{document}
\maketitle
\tableofcontents

\chapter{Easy Encounters}
\input{easy-encounters.tex}

\chapter{Medium Encounters}
\input{medium-encounters.tex}

\chapter{Hard Encounters}
\input{hard-encounters.tex}

\chapter{Deadly Encounters}
\input{deadly-encounters.tex}

\end{document}
EOF

# Compile the PDF
cd encounters
TEXINPUTS=".:~/dnd-template//:" pdflatex encounter-manual.tex
TEXINPUTS=".:~/dnd-template//:" pdflatex encounter-manual.tex
echo "✅ Encounter manual created: encounters/encounter-manual.pdf"
```

## Recipe 3: Campaign-Specific Reference Book

**Goal**: Create a comprehensive reference combining multiple adventures and supplemental content.

### Configuration: campaign-config.yaml

```yaml
# campaign-config.yaml
campaign: "Dragon Heist to Undermountain"

sources:
  adventures:
    - wdh  # Waterdeep: Dragon Heist
    - wdmm # Waterdeep: Dungeon of the Mad Mage

  supplements:
    - xgte  # Xanathar's Guide
    - tcoe  # Tasha's Cauldron

output:
  include_appendices: true
  include_maps: true
  include_handouts: true
```

### Conversion script

```bash
#!/bin/bash
# build-campaign.sh

# Convert primary adventures
5e2pdf convert adventure wdh \
  --output campaign/dragon-heist.tex \
  --no-appendix  # We'll create a combined appendix

5e2pdf convert adventure wdmm \
  --output campaign/undermountain.tex \
  --no-appendix

# Extract relevant content from supplements
5e2pdf convert spells \
  --source xgte \
  --output campaign/xanathar-spells.tex

5e2pdf convert items \
  --source tcoe \
  --type wondrous \
  --output campaign/tasha-items.tex

# Generate combined appendices
5e2pdf convert creatures \
  --source "wdh,wdmm" \
  --output campaign/all-creatures.tex

5e2pdf convert items \
  --source "wdh,wdmm" \
  --output campaign/all-items.tex

# Create the campaign book
cat > campaign/campaign-book.tex << 'EOF'
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}
\title{Dragon Heist to Undermountain: Complete Campaign}

\begin{document}
\maketitle
\tableofcontents

\part{Waterdeep: Dragon Heist}
\input{dragon-heist.tex}

\part{Dungeon of the Mad Mage}
\input{undermountain.tex}

\part{Supplemental Content}
\chapter{Additional Spells}
\input{xanathar-spells.tex}

\chapter{Magic Items}
\input{tasha-items.tex}

\appendix
\chapter{Creature Statistics}
\input{all-creatures.tex}

\chapter{Magic Item Reference}
\input{all-items.tex}

\end{document}
EOF
```

## Recipe 4: Quick NPC Generator

**Goal**: Generate a collection of NPCs with specific class/level combinations.

### Python script: npc-generator.py

```python
#!/usr/bin/env python3
"""Generate NPC stat blocks for common character builds."""

import subprocess
import json
from pathlib import Path

# NPC configurations
npcs = [
    {"name": "Town Guard", "base": "guard", "mods": {"hp": 15, "ac": 16}},
    {"name": "Veteran Soldier", "base": "veteran", "mods": {"hp": 65}},
    {"name": "Court Wizard", "base": "mage", "mods": {"spells": ["counterspell", "teleport"]}},
    {"name": "Master Thief", "base": "assassin", "mods": {"skills": {"stealth": "+11"}}},
    {"name": "Temple Priest", "base": "priest", "mods": {"spells": ["heal", "flame strike"]}},
]

def generate_npc(npc_config):
    """Generate LaTeX for a single NPC."""
    name = npc_config["name"]
    base = npc_config["base"]

    # Get base creature
    cmd = f"5e2pdf convert creatures '{base}' --output 'npcs/{name}.tex'"
    subprocess.run(cmd, shell=True)

    # Modify the generated file with custom stats
    tex_file = Path(f"npcs/{name}.tex")
    if tex_file.exists():
        content = tex_file.read_text()

        # Apply modifications
        for key, value in npc_config.get("mods", {}).items():
            # Simple replacement logic (extend as needed)
            if key == "hp":
                content = content.replace(
                    f"Hit Points: & {base_hp}",
                    f"Hit Points: & {value}"
                )

        # Update name
        content = content.replace(f"\\subsection{{{base.title()}}}",
                                f"\\subsection{{{name}}}")

        tex_file.write_text(content)
        print(f"✅ Generated: {name}")

# Generate all NPCs
Path("npcs").mkdir(exist_ok=True)
for npc in npcs:
    generate_npc(npc)

# Create NPC collection document
collection = Path("npcs/npc-collection.tex")
collection.write_text(r"""
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}
\title{NPC Collection}

\begin{document}
\maketitle

\chapter{Common NPCs}
""" + "\n".join([f"\\input{{{npc['name']}.tex}}" for npc in npcs]) + r"""

\end{document}
""")

print("📚 NPC collection created: npcs/npc-collection.tex")
```

## Recipe 5: Session Prep Automation

**Goal**: Automatically generate session materials based on adventure progress.

### Session prep configuration

```yaml
# session-prep.yaml
session: 5
adventure: lmop
current_chapter: "Wave Echo Cave"

prepare:
  encounters:
    - black spider
    - bugbear
    - doppelganger

  spells_to_reference:
    - spider climb
    - web
    - magic missile

  items_party_might_find:
    - lightbringer
    - staff of defense
    - gauntlets of ogre power

  npcs:
    - nundro rockseeker
    - black spider
```

### Automation script

```bash
#!/bin/bash
# prep-session.sh - Generate session materials

SESSION_NUM=5
PREP_FILE="session-prep.yaml"
OUTPUT_DIR="session-$SESSION_NUM"

mkdir -p "$OUTPUT_DIR"

echo "📝 Preparing Session $SESSION_NUM materials..."

# Extract creatures for encounters
echo "Converting encounter creatures..."
grep -A 10 "encounters:" "$PREP_FILE" | grep "    -" | while read -r line; do
  creature=$(echo "$line" | sed 's/    - //')
  5e2pdf convert creatures "$creature" \
    --output "$OUTPUT_DIR/encounter-${creature// /-}.tex"
done

# Extract referenced spells
echo "Converting referenced spells..."
grep -A 10 "spells_to_reference:" "$PREP_FILE" | grep "    -" | while read -r line; do
  spell=$(echo "$line" | sed 's/    - //')
  5e2pdf convert spells "$spell" \
    --output "$OUTPUT_DIR/spell-${spell// /-}.tex"
done

# Extract items
echo "Converting treasure items..."
grep -A 10 "items_party_might_find:" "$PREP_FILE" | grep "    -" | while read -r line; do
  item=$(echo "$line" | sed 's/    - //')
  5e2pdf convert items "$item" \
    --output "$OUTPUT_DIR/item-${item// /-}.tex"
done

# Create session reference document
cat > "$OUTPUT_DIR/session-$SESSION_NUM-reference.tex" << 'EOF'
\documentclass[letterpaper,twocolumn,openany,nodeprecatedcode]{dndbook}
\title{Session 5: Wave Echo Cave}

\begin{document}
\maketitle

\chapter{Encounters}
\input{encounter-black-spider.tex}
\input{encounter-bugbear.tex}
\input{encounter-doppelganger.tex}

\chapter{Spell Reference}
\input{spell-spider-climb.tex}
\input{spell-web.tex}
\input{spell-magic-missile.tex}

\chapter{Treasure}
\input{item-lightbringer.tex}
\input{item-staff-of-defense.tex}
\input{item-gauntlets-of-ogre-power.tex}

\end{document}
EOF

# Compile the reference
cd "$OUTPUT_DIR"
TEXINPUTS=".:~/dnd-template//:" pdflatex "session-$SESSION_NUM-reference.tex"

echo "✅ Session materials ready: $OUTPUT_DIR/session-$SESSION_NUM-reference.pdf"

# Open the PDF
open "session-$SESSION_NUM-reference.pdf"
```

## Tips and Tricks

### Batch Processing

```bash
# Convert all adventures in parallel
ls ~/.5e2pdf/sources/*/adventure/*.json | parallel -j 4 \
  '5e2pdf convert adventure {/.} --output adventures/{/.}.tex'
```

### Custom Filters

```bash
# Create a function for common filters
function convert_by_school() {
  local school=$1
  5e2pdf convert spells \
    --filter "school=$school" \
    --output "spells-$school.tex"
}

# Use it
convert_by_school "evocation"
convert_by_school "necromancy"
```

### Integration with Make

```makefile
# Makefile for D&D content generation

ADVENTURES = cos lmop skt
BOOKS = phb dmg mm

.PHONY: all adventures books clean

all: adventures books

adventures: $(ADVENTURES:%=output/%.pdf)

books: $(BOOKS:%=output/%.pdf)

output/%.pdf: output/%.tex
	cd output && TEXINPUTS=".:~/dnd-template//:" pdflatex $*.tex

output/%.tex:
	5e2pdf convert adventure $* --output $@

clean:
	rm -rf output/*
```

## Advanced Techniques

### Content Merging

```python
#!/usr/bin/env python3
"""Merge multiple sources into a single document."""

from pathlib import Path
import subprocess

def merge_latex_files(files, output):
    """Merge multiple LaTeX files, removing duplicates."""
    seen_content = set()
    merged = []

    for file in files:
        content = Path(file).read_text()
        lines = content.split('\n')

        for line in lines:
            # Skip duplicate subsections
            if line.startswith('\\subsection'):
                if line in seen_content:
                    continue
                seen_content.add(line)
            merged.append(line)

    Path(output).write_text('\n'.join(merged))
    print(f"✅ Merged {len(files)} files into {output}")

# Example usage
merge_latex_files(
    Path("spells").glob("*.tex"),
    "merged-spells.tex"
)
```

### Dynamic Content Generation

```bash
#!/bin/bash
# Generate content based on party composition

PARTY=("wizard:5" "fighter:5" "cleric:5" "rogue:5")

for member in "${PARTY[@]}"; do
  class="${member%:*}"
  level="${member#*:}"

  echo "Generating content for Level $level $class..."

  # Get class-appropriate spells
  5e2pdf convert spells \
    --class "$class" \
    --level "0-$(($level/2))" \
    --output "party/${class}-spells.tex"

  # Get level-appropriate items
  5e2pdf convert items \
    --rarity "$([ $level -lt 5 ] && echo 'common,uncommon' || echo 'uncommon,rare')" \
    --output "party/${class}-items.tex"
done
```

## Related Resources

- [Configuration Reference](configuration-reference.md)
- [Quickstart Tutorial](quickstart-tutorial.md)
- [CLI Reference](../library-reference/cli.md)
- [LaTeX Templates](https://github.com/rpgtex/DND-5e-LaTeX-Template)
