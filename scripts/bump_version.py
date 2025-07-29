import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import semver


def find_latest_draft():
    """Find the latest Release Drafter draft release.

    Returns:
        dict | None: Draft release info with id, name, tag_name, body, or None if no draft exists
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "repos/sargeant/5e2pdf/releases",
                "--jq",
                ".[] | select(.draft == true)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return None

        # Parse the first (latest) draft release
        draft_data = json.loads(result.stdout.strip().split("\n")[0])
        return {
            "id": draft_data["id"],
            "name": draft_data["name"],
            "tag_name": draft_data["tag_name"],
            "body": draft_data["body"],
        }

    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not find Release Drafter draft: {e}", file=sys.stderr)
        return None


def update_release_draft(version_str: str, dry_run: bool = False):
    """Update the latest Release Drafter draft with new version info.

    Args:
        version_str: New version string (e.g., "1.2.3")
        dry_run: If True, show what would be updated without making changes

    Returns:
        bool: True if update succeeded, False otherwise
    """
    draft = find_latest_draft()
    if not draft:
        print("No Release Drafter draft found to update", file=sys.stderr)
        return False

    new_name = f"v{version_str}"
    new_tag = f"v{version_str}"

    print("Found Release Drafter draft:")
    print(f"  Current name: {draft['name']}")
    print(f"  Current tag:  {draft['tag_name']}")
    print(f"  New name:     {new_name}")
    print(f"  New tag:      {new_tag}")

    if dry_run:
        print("Dry run - no changes made")
        return True

    try:
        # Update the draft release via GitHub API
        update_data = {
            "name": new_name,
            "tag_name": new_tag,
            "body": draft["body"],  # Preserve existing release notes
        }

        subprocess.run(
            [
                "gh",
                "api",
                f"repos/sargeant/5e2pdf/releases/{draft['id']}",
                "--method",
                "PATCH",
                "--input",
                "-",
            ],
            input=json.dumps(update_data),
            text=True,
            capture_output=True,
            check=True,
        )

        print(f"✅ Successfully updated Release Drafter draft to {new_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update Release Drafter draft: {e}", file=sys.stderr)
        if e.stderr:
            print(f"Error details: {e.stderr}", file=sys.stderr)
        return False


def bump_version(part: str, update_draft: bool = False, dry_run: bool = False):
    """Bump version in project files and optionally update Release Drafter draft.

    Args:
        part: Version part to bump ('major', 'minor', 'patch')
        update_draft: Whether to update Release Drafter draft with new version
        dry_run: If True, show what would be changed without making changes

    Returns:
        str: New version string
    """
    pyproject_path = Path("pyproject.toml")
    init_py_path = Path("src/dnd5e/__init__.py")

    # Read pyproject.toml
    pyproject_content = pyproject_path.read_text()
    current_version_match = re.search(r'version = "(\d+\.\d+\.\d+)"', pyproject_content)
    if not current_version_match:
        raise ValueError("Version not found in pyproject.toml")

    current_version_str = current_version_match.group(1)
    current_version = semver.Version.parse(current_version_str)

    if part == "major":
        new_version = current_version.bump_major()
    elif part == "minor":
        new_version = current_version.bump_minor()
    elif part == "patch":
        new_version = current_version.bump_patch()
    else:
        raise ValueError(f"Invalid part: {part}. Must be 'major', 'minor', or 'patch'.")

    new_version_str = str(new_version)

    print(f"Version bump: {current_version_str} → {new_version_str}")

    if dry_run:
        print("Dry run - would update:")
        print(f"  - {pyproject_path}")
        print(f"  - {init_py_path}")
        if update_draft:
            update_release_draft(new_version_str, dry_run=True)
        return new_version_str

    # Update pyproject.toml
    new_pyproject_content = re.sub(
        r'version = "\d+\.\d+\.\d+"',
        f'version = "{new_version_str}"',
        pyproject_content,
    )
    pyproject_path.write_text(new_pyproject_content)

    # Update src/dnd5e/__init__.py
    init_py_content = init_py_path.read_text()
    new_init_py_content = re.sub(
        r'__version__ = "\d+\.\d+\.\d+"',
        f'__version__ = "{new_version_str}"',
        init_py_content,
    )
    init_py_path.write_text(new_init_py_content)

    print(f"✅ Version bumped to {new_version_str}")

    # Update Release Drafter draft if requested
    if update_draft:
        update_release_draft(new_version_str, dry_run=dry_run)

    return new_version_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bump project version with optional Release Drafter integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bump_version.py patch                    # Bump patch version only
  python bump_version.py minor --update-draft    # Bump minor version and update Release Drafter draft
  python bump_version.py major --dry-run         # Show what would be updated without making changes
        """,
    )
    parser.add_argument(
        "part",
        choices=["major", "minor", "patch"],
        help="Which part of the version to bump",
    )
    parser.add_argument(
        "--update-draft",
        action="store_true",
        help="Update the latest Release Drafter draft with new version info",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )

    args = parser.parse_args()

    try:
        result = bump_version(
            args.part, update_draft=args.update_draft, dry_run=args.dry_run
        )
        if not args.dry_run:
            print(f"\n🎉 Version successfully updated to {result}")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
