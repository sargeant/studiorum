#!/usr/bin/env python3
"""Script to fix async test issues by updating test methods and calls."""

import re
from pathlib import Path


def fix_test_file(
    file_path: Path, replacements: list[tuple[str, str]], add_async_mark: bool = False
):
    """Apply a list of (old, new) replacements to a file."""
    content = file_path.read_text()

    # Add async mark if needed
    if add_async_mark and "pytestmark = pytest.mark.asyncio" not in content:
        # Find import statements and add the mark after them
        import_pattern = r"(import pytest\n)"
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern,
                r"\1\n# Ensure async tests work properly\npytestmark = pytest.mark.asyncio\n",
                content,
            )
        else:
            # Fallback: add at beginning of imports
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import pytest") or line.startswith("from"):
                    lines.insert(i + 1, "\n# Ensure async tests work properly")
                    lines.insert(i + 2, "pytestmark = pytest.mark.asyncio")
                    break
            content = "\n".join(lines)

    for old, new in replacements:
        content = content.replace(old, new)

    file_path.write_text(content)
    print(f"Fixed {len(replacements)} issues in {file_path}")


# Fix tests/core/resolvers/test_content_resolver.py
resolver_test_fixes = [
    # Test method signatures
    ("def test_resolve_book_exact_match(", "async def test_resolve_book_exact_match("),
    (
        "def test_resolve_adventure_multiple_matches_picks_preferred(",
        "async def test_resolve_adventure_multiple_matches_picks_preferred(",
    ),
    (
        "def test_resolve_adventure_no_match_with_suggestions(",
        "async def test_resolve_adventure_no_match_with_suggestions(",
    ),
    (
        "def test_resolve_adventure_empty_abbreviation(",
        "async def test_resolve_adventure_empty_abbreviation(",
    ),
    (
        "def test_resolve_adventure_whitespace_abbreviation(",
        "async def test_resolve_adventure_whitespace_abbreviation(",
    ),
    (
        "def test_resolve_adventure_no_content_available(",
        "async def test_resolve_adventure_no_content_available(",
    ),
    (
        "def test_resolve_adventure_fuzzy_match(",
        "async def test_resolve_adventure_fuzzy_match(",
    ),
    (
        "def test_resolve_any_with_content_type(",
        "async def test_resolve_any_with_content_type(",
    ),
    (
        "def test_resolve_any_without_content_type(",
        "async def test_resolve_any_without_content_type(",
    ),
    (
        "def test_resolve_content_source_without_abbreviation(",
        "async def test_resolve_content_source_without_abbreviation(",
    ),
    (
        "def test_fuzzy_matching_multiple_results(",
        "async def test_fuzzy_matching_multiple_results(",
    ),
    (
        "def test_search_fallback_no_fuzzy_matches(",
        "async def test_search_fallback_no_fuzzy_matches(",
    ),
    # Method calls that need await
    (
        'result = resolver.resolve_book("phb")',
        'result = await resolver.resolve_book("phb")',
    ),
    (
        'result = resolver.resolve_adventure("test")',
        'result = await resolver.resolve_adventure("test")',
    ),
    (
        'result = resolver.resolve_adventure("nonexistent")',
        'result = await resolver.resolve_adventure("nonexistent")',
    ),
    (
        'result = resolver.resolve_adventure("")',
        'result = await resolver.resolve_adventure("")',
    ),
    (
        'result = resolver.resolve_adventure("   ")',
        'result = await resolver.resolve_adventure("   ")',
    ),
    (
        'result = resolver.resolve_adventure("tst")',
        'result = await resolver.resolve_adventure("tst")',
    ),
    (
        'result = resolver.resolve_any("test", ContentType.ADVENTURE)',
        'result = await resolver.resolve_any("test", ContentType.ADVENTURE)',
    ),
    (
        'result = resolver.resolve_any("test")',
        'result = await resolver.resolve_any("test")',
    ),
    (
        "result = resolver.resolve_adventure(preferred_adventure.source.abbreviation)",
        "result = await resolver.resolve_adventure(preferred_adventure.source.abbreviation)",
    ),
    (
        'result = resolver.resolve_adventure("multiple")',
        'result = await resolver.resolve_adventure("multiple")',
    ),
    (
        'result = resolver.resolve_adventure("similar")',
        'result = await resolver.resolve_adventure("similar")',
    ),
]

# Fix tests/renderers/latex/test_compiler.py
compiler_test_fixes = [
    # Test method signatures
    ("def test_compile_document_simple(", "async def test_compile_document_simple("),
    (
        "def test_compile_document_with_working_dir(",
        "async def test_compile_document_with_working_dir(",
    ),
    (
        "def test_compile_simple_document_no_latex(",
        "async def test_compile_simple_document_no_latex(",
    ),
    (
        "def test_compile_with_dependency_error(",
        "async def test_compile_with_dependency_error(",
    ),
    (
        "def test_compile_with_engine_fallback(",
        "async def test_compile_with_engine_fallback(",
    ),
    (
        "def test_check_dependencies_success(",
        "async def test_check_dependencies_success(",
    ),
    (
        "def test_check_dependencies_missing_packages(",
        "async def test_check_dependencies_missing_packages(",
    ),
    (
        "def test_check_dependencies_file_error(",
        "async def test_check_dependencies_file_error(",
    ),
    # Method calls that need await
    (
        'result = self.compiler.compile_document(latex_content, "test")',
        'result = await self.compiler.compile_document(latex_content, "test")',
    ),
    (
        'self.compiler.compile_document(latex_content, "test", working_dir)',
        'await self.compiler.compile_document(latex_content, "test", working_dir)',
    ),
    (
        "dependencies = self.compiler._check_dependencies(tex_file)",
        "dependencies = await self.compiler._check_dependencies(tex_file)",
    ),
]

# Integration test fixes
integration_test_fixes = [
    # Test method signatures
    (
        "def test_resolve_adventure_test_full_flow(",
        "async def test_resolve_adventure_test_full_flow(",
    ),
    (
        "def test_resolve_adventure_missing_content_file(",
        "async def test_resolve_adventure_missing_content_file(",
    ),
    (
        "def test_resolve_nonexistent_adventure(",
        "async def test_resolve_nonexistent_adventure(",
    ),
    (
        "def test_multiple_adventures_loaded(",
        "async def test_multiple_adventures_loaded(",
    ),
    # Method calls that need await
    (
        'result = resolver.resolve_adventure("TEST")',
        'result = await resolver.resolve_adventure("TEST")',
    ),
    (
        'result = resolver.resolve_adventure("test")',
        'result = await resolver.resolve_adventure("test")',
    ),
    (
        'result = resolver.resolve_adventure("nonexistent")',
        'result = await resolver.resolve_adventure("nonexistent")',
    ),
    (
        'test_adventure_result = resolver.resolve_adventure("TEST")',
        'test_adventure_result = await resolver.resolve_adventure("TEST")',
    ),
]

# Book resolution test fixes
book_test_fixes = [
    # Method calls that need await
    (
        'result = resolver.resolve_book("TEST")',
        'result = await resolver.resolve_book("TEST")',
    ),
    (
        'result = resolver.resolve_book("nonexistent")',
        'result = await resolver.resolve_book("nonexistent")',
    ),
    (
        'book_result = resolver.resolve_book("TEST")',
        'book_result = await resolver.resolve_book("TEST")',
    ),
    (
        'adventure_result = resolver.resolve_adventure("TEST")',
        'adventure_result = await resolver.resolve_adventure("TEST")',
    ),
    (
        'result1 = resolver.resolve_book("TEST")',
        'result1 = await resolver.resolve_book("TEST")',
    ),
    (
        'result2 = resolver.resolve_book("TEST")',
        'result2 = await resolver.resolve_book("TEST")',
    ),
    (
        'result = resolver.resolve_book("TEST")',
        'result = await resolver.resolve_book("TEST")',
    ),
]

# Performance test fixes
performance_test_fixes = [
    # Test method signatures
    (
        "def test_content_resolution_performance(",
        "async def test_content_resolution_performance(",
    ),
    ("def test_caching_effectiveness(", "async def test_caching_effectiveness("),
    # Method calls that need await
    (
        'adventure = resolver.resolve_adventure("TEST")',
        'adventure = await resolver.resolve_adventure("TEST")',
    ),
    (
        'book = resolver.resolve_book("TEST")',
        'book = await resolver.resolve_book("TEST")',
    ),
    (
        'result1 = resolver.resolve_adventure("TEST")',
        'result1 = await resolver.resolve_adventure("TEST")',
    ),
    (
        'result2 = resolver.resolve_adventure("TEST")',
        'result2 = await resolver.resolve_adventure("TEST")',
    ),
]

# Content merger test fixes
content_merger_fixes = [
    # Test method signatures
    (
        "def test_load_content_file_not_found(",
        "async def test_load_content_file_not_found(",
    ),
    (
        "def test_load_content_file_success(",
        "async def test_load_content_file_success(",
    ),
    (
        "def test_load_content_file_malformed_json(",
        "async def test_load_content_file_malformed_json(",
    ),
    (
        "def test_case_insensitive_file_matching(",
        "async def test_case_insensitive_file_matching(",
    ),
    # Method calls that need await
    (
        'result = content_merger.load_content_file(ContentType.ADVENTURE, "nonexistent")',
        'result = await content_merger.load_content_file(ContentType.ADVENTURE, "nonexistent")',
    ),
    (
        'result = content_merger.load_content_file(ContentType.ADVENTURE, "CoS")',
        'result = await content_merger.load_content_file(ContentType.ADVENTURE, "CoS")',
    ),
    (
        'result2 = content_merger.load_content_file(ContentType.ADVENTURE, "CoS")',
        'result2 = await content_merger.load_content_file(ContentType.ADVENTURE, "CoS")',
    ),
]

# Apply fixes to all files
try:
    # Already done: fix_test_file(Path("tests/core/resolvers/test_content_resolver.py"), resolver_test_fixes, add_async_mark=True)
    fix_test_file(
        Path("tests/renderers/latex/test_compiler.py"),
        compiler_test_fixes,
        add_async_mark=True,
    )
    fix_test_file(
        Path("tests/integration/test_adventure_resolution.py"),
        integration_test_fixes,
        add_async_mark=True,
    )
    fix_test_file(
        Path("tests/integration/test_book_resolution.py"),
        book_test_fixes,
        add_async_mark=True,
    )
    fix_test_file(
        Path("tests/performance/test_content_loading_performance.py"),
        performance_test_fixes,
        add_async_mark=True,
    )

    # Check if content merger tests exist
    content_merger_path = Path("tests/core/loaders/test_content_merger.py")
    if content_merger_path.exists():
        fix_test_file(content_merger_path, content_merger_fixes, add_async_mark=True)

    print("✅ All async test fixes applied successfully!")
except Exception as e:
    print(f"❌ Error applying fixes: {e}")
