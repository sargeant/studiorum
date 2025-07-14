import argparse
import re
from pathlib import Path

import semver


def bump_version(part: str):
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

    print(f"Version bumped to {new_version_str}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bump project version")
    parser.add_argument(
        "part",
        choices=["major", "minor", "patch"],
        help="Which part of the version to bump",
    )
    args = parser.parse_args()
    bump_version(args.part)
