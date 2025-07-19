# Packaging and Distribution Strategy for 5e2pdf

This document outlines a review of the current project structure and a recommended strategy for packaging and distributing the `5e2pdf` command-line tool.

## 1. Overall Assessment

The project is in an excellent state to be packaged and distributed. The use of `pyproject.toml` with the `hatchling` build backend is a modern and highly recommended approach.

**Strengths:**
-   **`pyproject.toml`:** You are using the current standard for Python project definition and build configuration.
-   **`src` Layout:** The `src/` layout is a best practice that cleanly separates your package's source code from other project files (tests, docs, etc.).
-   **Script Entry Point:** You have correctly defined a script entry point under `[project.scripts]`. This is the standard mechanism that allows `pip`, `uv`, and other installers to create the `5e2pdf` executable in the user's `PATH`.

**Areas for Action:**
1.  **Redundant `bin/` directory:** The `[project.scripts]` entry makes the `bin/` directory obsolete for installation purposes. It should be removed to avoid confusion.

---

## 2. Key Recommendations

### 2.1. Remove the `bin` Directory

The line `5e2pdf = "src.cli.main:app"` in your `pyproject.toml` instructs the installer to create the command-line script automatically. The `bin/5e2pdf` script is not used in the packaging process and should be deleted to simplify the project structure.

---

## 3. Distribution Strategy

### 3.1. PyPI (for `pip` and `uv`)

PyPI (the Python Package Index) is the central repository for Python packages. Publishing here will make `5e2pdf` installable via `pip install 5e2pdf` or `uv pip install 5e2pdf`.

**Steps:**
1.  **Create accounts:** Make an account on [PyPI](https://pypi.org/) and [TestPyPI](https://test.pypi.org/).
2.  **Install build tools:** `uv pip install build twine`
3.  **Build the package:** `python -m build`
4.  **Upload to PyPI:** `twine upload dist/*`

### 3.2. Homebrew (for macOS users)

Homebrew is a popular package manager for macOS. Distributing via Homebrew involves creating a "formula".

**General Process:**
1.  **Create a GitHub Release:** After you've pushed your code to GitHub, create a new release. Upload the source tarball (`.tar.gz`) created by `python -m build`.
2.  **Create a Homebrew Formula:** The formula will download your release tarball and use `pip` to install it.
3.  **Post-Install Message:** You can add a message to your Homebrew formula telling users to run `5e2pdf setup` to complete the installation.

---

## 4. References: Popular Python CLI Tools

Studying how popular, well-maintained CLI tools are packaged is the best way to learn.

1.  **Ruff:** A high-performance linter. It's written in Rust but packaged for Python.
    -   [Ruff GitHub Repository](https://github.com/astral-sh/ruff)

2.  **Black:** The uncompromising Python code formatter. A pure Python project with a very clean packaging setup.
    -   [Black's `pyproject.toml`](https://github.com/psf/black/blob/main/pyproject.toml)

3.  **Click:** A foundational library for building command-line interfaces.
    -   [Click's `pyproject.toml`](https://github.com/pallets/click/blob/main/pyproject.toml)
