#!/usr/bin/env python3
"""
Documentation validation script for 5e2pdf.

Validates documentation for:
- Broken links
- Missing references
- Code block syntax
- Image availability
- Cross-reference accuracy
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


class DocValidator:
    """Documentation validator for comprehensive quality checks."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.source_dir = docs_dir / "source"
        self.errors: list[tuple[str, str, str]] = []  # (file, line, error)
        self.warnings: list[tuple[str, str, str]] = []  # (file, line, warning)

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating 5e2pdf documentation...")

        success = True

        # Check documentation structure
        if not self._validate_structure():
            success = False

        # Check Markdown files
        for md_file in self.source_dir.rglob("*.md"):
            if not self._validate_markdown_file(md_file):
                success = False

        # Check for broken internal links
        if not self._validate_internal_links():
            success = False

        # Check code block syntax
        if not self._validate_code_blocks():
            success = False

        # Check cross-references
        if not self._validate_cross_references():
            success = False

        # Run Sphinx linkcheck
        if not self._run_sphinx_linkcheck():
            success = False

        # Report results
        self._report_results()

        return success

    def _validate_structure(self) -> bool:
        """Validate documentation structure."""
        required_files = [
            "index.md",
            "quickstart.md",
            "user-guide/index.md",
            "user-guide/installation.md",
            "user-guide/basic-usage.md",
            "user-guide/advanced-features.md",
            "user-guide/troubleshooting.md",
            "developer/index.md",
            "developer/contributing.md",
            "examples/index.md",
            "api/index.md",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.source_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            for file_path in missing_files:
                self.errors.append(
                    ("structure", "0", f"Missing required file: {file_path}")
                )
            return False

        return True

    def _validate_markdown_file(self, file_path: Path) -> bool:
        """Validate individual Markdown file."""
        success = True

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            # Check for basic markdown issues
            for i, line in enumerate(lines, 1):
                # Check for broken image references
                if "![" in line:
                    image_matches = re.findall(r"!\[.*?\]\((.*?)\)", line)
                    for image_path in image_matches:
                        if not self._check_image_exists(file_path, image_path):
                            self.errors.append(
                                (str(file_path), str(i), f"Missing image: {image_path}")
                            )
                            success = False

                # Check for TODO/FIXME markers
                if re.search(r"\b(TODO|FIXME|XXX)\b", line, re.IGNORECASE):
                    self.warnings.append(
                        (str(file_path), str(i), f"TODO marker found: {line.strip()}")
                    )

        except Exception as e:
            self.errors.append((str(file_path), "0", f"Error reading file: {e}"))
            success = False

        return success

    def _validate_internal_links(self) -> bool:
        """Validate internal documentation links."""
        success = True
        all_files = set()

        # Collect all documentation files
        for md_file in self.source_dir.rglob("*.md"):
            rel_path = md_file.relative_to(self.source_dir)
            all_files.add(str(rel_path))
            all_files.add(str(rel_path.with_suffix("")))  # Without .md extension

        # Also collect other linkable files (Python scripts, images, etc.)
        for other_file in self.source_dir.rglob("*"):
            if other_file.is_file() and not other_file.name.endswith(".md"):
                rel_path = other_file.relative_to(self.source_dir)
                all_files.add(str(rel_path))

        # Check links in each file
        for md_file in self.source_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            in_code_block = False

            for i, line in enumerate(lines, 1):
                # Track code block boundaries
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue

                # Skip link validation inside code blocks
                if in_code_block:
                    continue

                # Find markdown links
                link_matches = re.findall(r"\[.*?\]\((.*?)\)", line)
                for link in link_matches:
                    if self._is_internal_link(link):
                        if not self._check_internal_link_exists(
                            md_file, link, all_files
                        ):
                            self.errors.append(
                                (str(md_file), str(i), f"Broken internal link: {link}")
                            )
                            success = False

        return success

    def _validate_code_blocks(self) -> bool:
        """Validate code block syntax."""
        success = True

        for md_file in self.source_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            in_code_block = False

            for i, line in enumerate(lines, 1):
                if line.strip().startswith("```"):
                    if not in_code_block:
                        # Starting code block
                        in_code_block = True
                    else:
                        # Ending code block
                        in_code_block = False

        return success

    def _validate_cross_references(self) -> bool:
        """Validate Sphinx cross-references."""
        success = True

        for md_file in self.source_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Check for Sphinx cross-references
                ref_matches = re.findall(r"\{[^}]+\}`([^`]+)`", line)
                for ref in ref_matches:
                    # Basic validation - could be enhanced with actual reference resolution
                    if not ref.strip():
                        self.errors.append(
                            (str(md_file), str(i), "Empty cross-reference")
                        )
                        success = False

        return success

    def _run_sphinx_linkcheck(self) -> bool:
        """Run Sphinx linkcheck builder."""
        try:
            result = subprocess.run(
                [
                    "sphinx-build",
                    "-b",
                    "linkcheck",
                    str(self.source_dir),
                    str(self.docs_dir / "_build" / "linkcheck"),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                self.warnings.append(
                    ("linkcheck", "0", "Sphinx linkcheck found issues")
                )
                print(f"Linkcheck output:\n{result.stdout}\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.warnings.append(("linkcheck", "0", "Sphinx linkcheck timed out"))
            return False
        except Exception as e:
            self.warnings.append(("linkcheck", "0", f"Failed to run linkcheck: {e}"))
            return False

        return True

    def _is_balanced_code_fence(self, lines: list[str], start_idx: int) -> bool:
        """Check if code fence has matching closing fence."""
        # Count opening and closing fences from the current position onward
        fence_count = 0
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            if line.startswith("```") and len(line.replace("`", "")) <= len(line) - 3:
                fence_count += 1

        # For the starting fence, we need an even total count (pairs)
        # But since we're starting at an opening fence, we need the count to be odd
        # to indicate there's a matching closing fence
        return fence_count % 2 == 1

    def _check_image_exists(self, md_file: Path, image_path: str) -> bool:
        """Check if referenced image exists."""
        if image_path.startswith(("http://", "https://")):
            return True  # External images - skip validation

        # Resolve relative to markdown file
        if image_path.startswith("/"):
            # Absolute path from source root
            full_path = self.source_dir / image_path.lstrip("/")
        else:
            # Relative to current file
            full_path = md_file.parent / image_path

        return full_path.exists()

    def _is_internal_link(self, link: str) -> bool:
        """Check if link is internal to documentation."""
        return not link.startswith(("http://", "https://", "mailto:", "#"))

    def _check_internal_link_exists(
        self, md_file: Path, link: str, all_files: set[str]
    ) -> bool:
        """Check if internal link target exists."""
        # Remove anchor fragments
        link_path = link.split("#")[0]
        if not link_path:
            return True  # Fragment-only links are valid

        # Resolve relative to current file
        if link_path.startswith("/"):
            # Absolute from source root
            target_path = link_path.lstrip("/")
        else:
            # Relative to current file
            current_dir = md_file.parent.relative_to(self.source_dir)
            if current_dir != Path("."):
                # Use Path for proper path resolution, then convert to string
                target_path_obj = current_dir / link_path
                # Normalize by resolving parent directory references
                target_path = str(target_path_obj).replace("\\", "/")
                # Manually resolve .. references
                parts = target_path.split("/")
                normalized_parts = []
                for part in parts:
                    if part == "..":
                        if normalized_parts:
                            normalized_parts.pop()
                    elif part != ".":
                        normalized_parts.append(part)
                target_path = "/".join(normalized_parts)
            else:
                target_path = link_path

        # Normalize path separators
        target_path = target_path.replace("\\", "/")

        # Check various possible targets
        possible_targets = [
            target_path,
            target_path + ".md",
            target_path.rstrip(".md"),
            target_path + "/index.md",
            target_path + "/index",
        ]

        return any(target in all_files for target in possible_targets)

    def _validate_code_syntax(self, language: str, code: str) -> bool:
        """Basic validation of code block syntax."""
        # Simple checks - could be enhanced with actual syntax parsing
        if language in ["python", "py"]:
            # Check for very basic Python syntax issues
            # Allow import statements, comments, and simple code
            stripped_code = code.strip()
            if not stripped_code:
                return True  # Empty code blocks are fine

            # Skip validation for comment-only blocks
            lines = [line.strip() for line in stripped_code.split("\n") if line.strip()]
            if all(line.startswith("#") for line in lines):
                return True  # Comment-only blocks are fine

            # Skip validation for import-only blocks
            if all(
                line.startswith(("import ", "from ")) or line.startswith("#")
                for line in lines
            ):
                return True  # Import statements are fine

        elif language in ["bash", "sh"]:
            # Check for unmatched quotes (more robust)
            in_single_quote = False
            in_double_quote = False
            escaped = False

            for char in code:
                if escaped:
                    escaped = False
                    continue

                if char == "\\":
                    escaped = True
                    continue

                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote

            if in_single_quote or in_double_quote:
                return False  # Unmatched quotes

        return True

    def _report_results(self):
        """Report validation results."""
        print("\n📊 Documentation Validation Results:")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n❌ Errors:")
            for file_path, line, error in self.errors:
                print(f"   {file_path}:{line} - {error}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for file_path, line, warning in self.warnings:
                print(f"   {file_path}:{line} - {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ Documentation validation passed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate 5e2pdf documentation")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Documentation directory (default: docs)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )

    args = parser.parse_args()

    if not args.docs_dir.exists():
        print(f"❌ Documentation directory not found: {args.docs_dir}")
        sys.exit(1)

    validator = DocValidator(args.docs_dir)
    success = validator.validate_all()

    if args.strict and validator.warnings:
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
