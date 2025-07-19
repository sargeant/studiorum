# Release Management Workflow

This document outlines the recommended workflow for managing releases in this project, combining automated version bumping, changelog generation with Release Drafter, and a clear review and approval process.

## Goal

To provide an easy, yet robust, workflow for creating new releases/versions, ensuring consistency across version definitions, automated changelog assembly, and a structured review process before publishing.

## Prerequisites

Before starting a release, ensure you have:

*   **Git**: For version control.
*   **GitHub CLI (`gh`)**: Useful for interacting with GitHub (e.g., viewing workflow runs).
*   **`uv`**: For running Python scripts within the project's virtual environment.
*   **Clean Working Directory**: All changes should be committed or stashed.
*   **Up-to-date `main` branch**: Ensure your local `main` branch is synchronized with `origin/main`.

## Workflow Steps

### 1. Branching Strategy

This workflow assumes a GitHub Flow-like branching strategy where `main` is the stable branch representing the latest release. All new features and bug fixes are developed on separate branches and merged into `main` via Pull Requests.

### 2. Prepare for Release

Before initiating the release process, ensure the `main` branch is in a releasable state:

*   **Sync `main`**:
    ```bash
    git checkout main
    git pull origin main
    ```
*   **Run Tests**: Ensure all tests pass.
    ```bash
    uv run pytest
    ```
*   **Run Linting/Formatting**: Ensure code adheres to standards.
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```

### 3. Bump Version

Use the `scripts/bump_version.py` script to increment the project's semantic version. This script updates the `version` in `pyproject.toml` and `__version__` in `src/dnd5e/__init__.py`.

Choose the appropriate part to bump: `major`, `minor`, or `patch`.

*   **Bump Patch Version (most common)**:
    ```bash
    uv run scripts/bump_version.py patch
    ```
*   **Bump Minor Version**:
    ```bash
    uv run scripts/bump_version.py minor
    ```
*   **Bump Major Version**:
    ```bash
    uv run scripts/bump_version.py major
    ```

### 4. Commit Version Bump

After running the bump script, commit the version changes. Use a clear commit message, typically following Conventional Commits.

```bash
git add pyproject.toml src/dnd5e/__init__.py
git commit -m "chore(release): Bump version to X.Y.Z"
```
(Replace `X.Y.Z` with the new version number.)

### 5. Push to `main`

Push the version bump commit to the `main` branch. This action will trigger the Release Drafter GitHub Action.

```bash
git push origin main
```

### 6. Release Drafter Action

Upon pushing to `main`, the `Release Drafter` GitHub Action (`.github/workflows/release-drafter.yml`) will automatically run.

*   It will analyze merged Pull Requests since the last release.
*   It will categorize changes based on labels (e.g., `feature`, `bug`, `chore`, `docs`) as defined in `.github/release-drafter.yml`.
*   It will create a **draft release** on GitHub, pre-populating the release notes with the assembled changelog.

You can monitor the workflow run status in your GitHub repository under the "Actions" tab.

### 7. Review and Edit Changelog

Navigate to your GitHub repository's "Releases" page. You will see a new "Draft" release.

*   **Review**: Carefully read the automatically generated release notes.
*   **Edit**:
    *   Ensure clarity, conciseness, and correct grammar.
    *   Add any additional context or important notes not captured by the automated process.
    *   Reorder items if necessary for better flow.
    *   Remove any irrelevant entries (e.g., internal-only changes if `skip-changelog` label was missed).
    *   Verify that the version number in the draft release matches the one you bumped to.

### 8. Approve and Publish Release

Once you are satisfied with the draft release notes:

*   Click the "Publish release" button on the GitHub draft release page.
*   This action will:
    *   Create a new Git tag (e.g., `vX.Y.Z`) pointing to the commit that triggered the Release Drafter.
    *   Publish the release notes, making them visible to users.

### 9. Post-Release (Optional but Recommended)

To prepare for future development and avoid potential version conflicts:

*   **Bump to Next Development Version**: Immediately after publishing a release, consider bumping the `patch` version and appending a development suffix (e.g., `0.1.1-dev`). This signifies that `main` is now working towards the next iteration.
    *   Manually edit `pyproject.toml` and `src/dnd5e/__init__.py` to `X.Y.Z-dev` (e.g., `0.1.1-dev`).
    *   Commit this change: `git commit -m "chore: Prepare for next development cycle"`
    *   Push this commit.

## Key Tools

*   `scripts/bump_version.py`: Centralized script for version management.
*   GitHub Release Drafter: Automates changelog generation.
*   Git: Core version control.
*   GitHub Releases: Platform for publishing releases.

## Best Practices

*   **Conventional Commits/PR Labels**: Encourage developers to use clear, conventional commit messages and apply appropriate labels to Pull Requests (e.g., `feature`, `bug`, `chore`, `docs`). This is crucial for Release Drafter to accurately categorize changes.
*   **Small, Frequent Releases**: Aim for smaller, more frequent releases to make changelog generation and review easier.
*   **Test Thoroughly**: Always ensure the `main` branch is stable and all tests pass before initiating a release.
*   **Review Drafts**: Never publish a release without a thorough manual review of the generated changelog.
