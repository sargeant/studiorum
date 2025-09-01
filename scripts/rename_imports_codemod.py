#!/usr/bin/env python3
"""
Safe AST-based import transformation using libcst.
Transforms dnd5e -> studiorum imports while preserving code structure.
"""

import sys
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand


class RenameImportsCodemod(VisitorBasedCodemodCommand):
    """Transform all dnd5e imports to studiorum using concrete syntax tree."""

    DESCRIPTION: str = "Rename dnd5e imports to studiorum"

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform 'from dnd5e.x import y' to 'from studiorum.x import y'"""
        if updated_node.module:
            module_parts = []
            current = updated_node.module

            # Handle dotted module names
            if isinstance(current, cst.Attribute):
                while isinstance(current, cst.Attribute):
                    module_parts.insert(0, current.attr.value)
                    current = current.value
                if isinstance(current, cst.Name) and current.value == "dnd5e":
                    module_parts.insert(0, "studiorum")
                    new_module = cst.Name("studiorum")
                    for part in module_parts[1:]:
                        new_module = cst.Attribute(
                            value=new_module, attr=cst.Name(part)
                        )
                    return updated_node.with_changes(module=new_module)
            elif isinstance(current, cst.Name) and current.value == "dnd5e":
                return updated_node.with_changes(module=cst.Name("studiorum"))

        return updated_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import:
        """Transform 'import dnd5e' to 'import studiorum'"""
        new_names = []
        for name_item in updated_node.names:
            if isinstance(name_item.name, cst.Name) and name_item.name.value == "dnd5e":
                new_names.append(name_item.with_changes(name=cst.Name("studiorum")))
            elif isinstance(name_item.name, cst.Attribute):
                # Handle dotted imports like 'import dnd5e.core'
                parts = []
                current = name_item.name
                while isinstance(current, cst.Attribute):
                    parts.insert(0, current.attr.value)
                    current = current.value
                if isinstance(current, cst.Name) and current.value == "dnd5e":
                    parts.insert(0, "studiorum")
                    new_name = cst.Name("studiorum")
                    for part in parts[1:]:
                        new_name = cst.Attribute(value=new_name, attr=cst.Name(part))
                    new_names.append(name_item.with_changes(name=new_name))
                else:
                    new_names.append(name_item)
            else:
                new_names.append(name_item)

        return (
            updated_node.with_changes(names=new_names)
            if new_names != updated_node.names
            else updated_node
        )


def transform_file(file_path: Path) -> bool:
    """Transform a single Python file. Returns True if changes were made."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Parse and transform using libcst
        tree = cst.parse_module(source)
        context = CodemodContext()
        codemod = RenameImportsCodemod(context)

        transformed_tree = tree.visit(codemod)

        # Check if any changes were made
        if transformed_tree.code != source:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(transformed_tree.code)
            print(f"✅ Transformed: {file_path}")
            return True
        else:
            print(f"- No changes: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error transforming {file_path}: {e}")
        return False


def main():
    """Transform all Python files in src/ and tests/"""
    total_files = 0
    transformed_files = 0

    # Process source files
    for py_file in Path("src").rglob("*.py"):
        total_files += 1
        if transform_file(py_file):
            transformed_files += 1

    # Process test files
    for py_file in Path("tests").rglob("*.py"):
        total_files += 1
        if transform_file(py_file):
            transformed_files += 1

    # Process conftest.py
    conftest = Path("conftest.py")
    if conftest.exists():
        total_files += 1
        if transform_file(conftest):
            transformed_files += 1

    print(f"\n📊 Summary: {transformed_files}/{total_files} files transformed")
    return transformed_files > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
