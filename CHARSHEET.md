# Character Sheet Generation Feature

This document outlines the plan for implementing a character sheet generation feature within the 5e2pdf project.

## I. Core Components & Analysis

### 1. Content Loading & Rules Engine

**Analysis:**
The project currently loads D&D content (races, classes, feats, spells, etc.) using `src/core/loaders/json_loader.py` and validates it against Pydantic models defined in `src/core/models/`. This provides a robust foundation for accessing D&D data.

**Gap:**
While content is loaded, there isn't an explicit "rules engine" to apply D&D character creation rules (e.g., calculating ability modifiers, hit points, proficiencies based on race/class choices, applying feats, etc.). This logic needs to be implemented.

**Conclusion:**
We will leverage the existing Pydantic models and build new Python logic to apply D&D character creation rules. This keeps the implementation within the current Python ecosystem and utilizes the already validated data.

### 2. User Interaction (CLI)

**Analysis:**
The project is a CLI tool (`bin/5e2pdf`). User prompting for character creation will need to be text-based.

**Gap:**
There is no existing interactive prompting mechanism for complex user input (e.g., choosing from lists, entering text, confirming choices).

**Conclusion:**
For initial implementation, we will use Python's built-in `input()` for basic prompts. If the interaction becomes too cumbersome or requires more advanced features (like auto-completion or structured menus), we can consider integrating a richer CLI library like `Typer` or `prompt_toolkit` in a future iteration.

### 3. Player Character (PC) Data Storage

**Analysis:**
There is no existing mechanism for storing dynamic character data.

**Gap:**
We need a way to represent a Player Character object and persist it across sessions.

**Conclusion:**
Storing Player Character data as a JSON file is the most straightforward and consistent approach, aligning with the project's existing use of JSON for content. We will define a new Pydantic model, `PlayerCharacter`, to represent the character's data structure, allowing for easy serialization and deserialization to/from JSON.

### 4. Short-Form Content Generation

**Analysis:**
The existing `src/dndtex/tags.py` and `InTextTagRenderer.py` suggest a system for rendering structured text. The `entries` fields in `Race` and `Class` models contain descriptive text.

**Gap:**
We need to extract specific, concise pieces of information (e.g., "Darkvision 60ft", "Proficiency Bonus +2", "Strength 15 (+2)") from the loaded content and calculated stats, and format them for display on a character sheet.

**Conclusion:**
We will create dedicated functions or methods within the new `PlayerCharacter` model or a `CharacterSheetGenerator` class to format these pieces of information into short, displayable strings suitable for the character sheet.

### 5. PDF Generation (Character Sheet Template)

**Analysis:**
The project uses LaTeX for PDF generation (`src/dndtex/`, `gen-latex.py`, `json2tex.py`). This indicates that a LaTeX-based character sheet is a feasible approach.

**Gap:**
There is no existing LaTeX template specifically for character sheets.

**Conclusion:**
We will create a new LaTeX template (`.tex` file) specifically designed for D&D 5e character sheets. This template will define the layout and include placeholders for character data. We will then modify or extend the existing LaTeX compilation process to use this new template and inject the generated character data.

## II. Detailed Implementation Plan

### Phase 1: Data Modeling and Core Logic

1.  **Define `PlayerCharacter` Pydantic Model:**
    *   Create a new file: `src/core/models/character.py`.
    *   Define a `PlayerCharacter` Pydantic model to hold all character-related data (name, race, class, ability scores, proficiencies, features, equipment, etc.). This model will compose existing models like `Race` and `Class` where appropriate.
    *   Include fields for derived stats (e.g., hit points, AC, initiative, proficiency bonus) that will be calculated.

2.  **Implement Character Creation Rules Engine:**
    *   Create a new file: `src/character_creator.py`.
    *   This module will contain functions to:
        *   Calculate ability score modifiers.
        *   Determine proficiency bonus based on level.
        *   Calculate hit points based on class and Constitution.
        *   Derive skill proficiencies, saving throw proficiencies, etc., from race and class data.
        *   Handle feature application (e.g., Darkvision from race).
        *   Manage equipment and inventory.

### Phase 2: User Interaction (CLI)

1.  **Create Character Creation CLI Command:**
    *   Modify `src/cli/main.py` (or create a new CLI module if `main.py` is too large) to add a new command, e.g., `5e2pdf character create`.
    *   Implement a step-by-step interactive process:
        *   Prompt for character name.
        *   List available races (loaded via `JsonDataLoader`) and prompt for choice.
        *   List available classes and prompt for choice.
        *   Prompt for ability scores (e.g., point buy or roll).
        *   Handle class-specific choices (e.g., subclass, fighting style, spell choices).
        *   Handle race-specific choices (e.g., ability score increases, subraces).
        *   Confirm choices with the user.

2.  **Integrate Content Loaders:**
    *   Use `create_race_loader()`, `create_class_loader()`, etc., from `src/core/loaders/json_loader.py` to load available content for user choices.

### Phase 3: Data Persistence

1.  **Save/Load Player Character Data:**
    *   In `src/character_creator.py`, implement functions to:
        *   Save a `PlayerCharacter` instance to a JSON file (e.g., in a new `output/characters/` directory).
        *   Load a `PlayerCharacter` instance from a JSON file.

### Phase 4: Character Sheet PDF Generation

1.  **Design LaTeX Character Sheet Template:**
    *   Create a new LaTeX template file: `assets/latex/character_sheet_template.tex`.
    *   Design the layout of a standard D&D 5e character sheet using LaTeX commands.
    *   Define placeholders (e.g., `\charactername{}` `\strengthscore{}` `\skillproficiency{Acrobatics}{}`) that will be replaced with actual character data.

2.  **Implement Character Sheet Renderer:**
    *   Create a new file: `src/renderers/latex/character_sheet_renderer.py`.
    *   This module will:
        *   Take a `PlayerCharacter` instance as input.
        *   Map the `PlayerCharacter` data to the placeholders in `character_sheet_template.tex`.
        *   Generate the final LaTeX content string.

3.  **Integrate with PDF Generation Pipeline:**
    *   Modify `src/gen-latex.py` or create a new script (e.g., `src/gen-character-sheet.py`) to:
        *   Load a `PlayerCharacter` from its JSON file.
        *   Use the `CharacterSheetRenderer` to generate the LaTeX content.
        *   Compile the LaTeX content into a PDF using a shell command (e.g., `pdflatex`).
        *   Save the generated PDF to `output/characters/`.

### Phase 5: Testing and Refinement

1.  **Unit Tests:**
    *   Write unit tests for the `PlayerCharacter` model, character creation rules, and the character sheet renderer.
2.  **Integration Tests:**
    *   Write integration tests for the full character creation and PDF generation workflow.
3.  **Refinement:**
    *   Iteratively improve the CLI user experience.
    *   Refine the LaTeX template for better visual appeal and accuracy.
    *   Add error handling and validation throughout the process.
