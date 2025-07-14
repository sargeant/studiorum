### Project: 5e2pdf

**Vision:** An easy way to get a print-quality PDF from 5e.tools data quickly and easily.

**Background:** The project started as a hand-rolled Python script that became difficult to maintain. It has undergone a significant, AI-assisted refactoring effort to modernize its architecture, add documentation, and implement a comprehensive test suite. The project is now in a phase of end-to-end testing and bug-fixing to stabilize the workflow.

### Analysis of Current State

1.  **Modern Architecture (Legacy Code Removed):**
    *   **Note:** The original legacy scripts (`json2tex.py`, `gen-latex.py`, `tablejson2tex.py`, and `dndtex/` module) were removed in issue #20 to clean up the codebase.
    *   **Modern:** A robust architecture has been built in the `src/` directory. It is modular, type-safe, and built on modern Python principles. The shell script wrappers (`scripts/build.sh`) remain for convenience but now use the modern CLI internally.

2.  **Modern Architecture Core Components:**
    *   **CLI (`src/cli`):** A new command-line interface using `Typer` and `Rich` provides a user-friendly way to interact with the system. It includes commands for managing content sources, converting files, and viewing information. It's the main entry point for the new workflow.
    *   **Core Logic (`src/core`):** This is the heart of the new system.
        *   **Models (`Pydantic`):** Data from 5e.tools is validated and loaded into strongly-typed Pydantic models.
        *   **Omnidexer:** A sophisticated system for loading, indexing, and caching all 5e.tools content, enabling fast lookups and cross-referencing.
        *   **Tag Resolver:** A powerful engine to parse and render D&D-specific `{@tag}` syntax (e.g., `{@spell Fireball}`) into the correct LaTeX format.
        *   **Configuration:** A settings management system handles paths, sources, and other configurations.
    *   **Renderers (`src/renderers`):** A flexible rendering pipeline has been established, with the primary implementation being for LaTeX. The system is designed to be extensible for other formats in the future.
    *   **Document (`src/core/document.py`):** This acts as a central object that aggregates content to be rendered, decoupling the content itself from the final output format.

3.  **Dependencies and Tooling:**
    *   **Package Management:** The project uses `pyproject.toml`, indicating a move towards modern Python packaging standards. However, a `requirements.txt` file also exists, which seems to contain a much larger, potentially outdated or transitive, set of dependencies. The `README.md` recommends using `uv`, a newer, faster package manager.
    *   **Testing:** A significant investment has been made in testing, with `pytest` as the framework. The `tests/` directory is well-structured with `unit` and `integration` subdirectories.
    *   **Code Quality:** `ruff` for linting and `black` for formatting are configured, ensuring code consistency.

4.  **Workflow:**
    *   **Data Input:** The system is designed to pull data directly from `5e.tools` sources (via Git) or local directories, managed via the new CLI. This replaces the old method of manual symlinking.
    *   **Processing:** The user interacts via the `5e2pdf` CLI. The CLI commands use the Omnidexer to load data, the Tag Resolver to process text, and the Renderer to generate a `.tex` file.
    *   **Output:** The final output is a LaTeX file, which can then be compiled into a PDF using `xelatex`. The `quick convert` command can automate this final step.

### Summary & Next Steps

The project is in a strong position. The refactoring has created a solid, modern foundation that directly serves the project's vision. The legacy code is still present, which ensures backward compatibility but also represents technical debt that could be removed in the future.

The current focus on end-to-end testing is the correct next step. This will validate that the new, complex architecture correctly and reliably produces the desired print-quality PDFs, matching or exceeding the quality of the original system.
