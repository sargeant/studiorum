#!/usr/bin/env python
"""Fix parallel test execution issues by improving test isolation."""

import re
from pathlib import Path


def fix_test_data_omnidexer_fixture():
    """Make test_data_omnidexer fixture properly isolated for parallel execution."""
    conftest_path = Path("tests/conftest.py")
    content = conftest_path.read_text()

    # Find and replace the test_data_omnidexer fixture to add proper isolation
    old_fixture = '''@pytest.fixture
def test_data_omnidexer() -> Omnidexer:
    """Omnidexer using test-data and srd-data sources."""
    import asyncio

    # Use full reset sequence for complete isolation
    reset_test_environment()'''

    new_fixture = '''@pytest.fixture
def test_data_omnidexer() -> Omnidexer:
    """Omnidexer using test-data and srd-data sources."""
    import asyncio
    import uuid

    # Use full reset sequence for complete isolation
    reset_test_environment()

    # CRITICAL: Force a fresh service container for each test to avoid parallel contamination
    from dnd5e.core.container import reset_global_container
    reset_global_container()'''

    if old_fixture in content:
        content = content.replace(old_fixture, new_fixture)
        conftest_path.write_text(content)
        print("✓ Fixed test_data_omnidexer fixture isolation")
    else:
        print("⚠ Could not find expected fixture pattern - may already be fixed")


def add_setup_method_to_integration_tests():
    """Ensure all integration tests have proper setup methods."""
    test_files = [
        "tests/integration/test_book_resolution.py",
        "tests/integration/test_adventure_conversion.py",
        "tests/integration/test_book_conversion.py",
    ]

    for test_file in test_files:
        path = Path(test_file)
        if not path.exists():
            continue

        content = path.read_text()

        # Check if setup_method exists but might be incomplete
        if "def setup_method" in content and "reset_global_container()" not in content:
            # Add extra reset after reset_test_environment()
            content = re.sub(
                r"(reset_test_environment\(\))",
                r"""\1

        # Extra isolation for parallel execution
        from dnd5e.core.container import reset_global_container
        reset_global_container()""",
                content,
            )
            path.write_text(content)
            print(f"✓ Enhanced setup_method in {test_file}")


def create_pytest_ini_for_better_isolation():
    """Create pytest.ini with better isolation settings."""
    pytest_ini_content = """[pytest]
# Pytest configuration for better test isolation

# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Parallel execution settings
addopts =
    -ra
    --strict-markers
    --strict-config
    --tb=short
    # Use process isolation for better test isolation
    -n auto
    --dist=loadscope
    # Force new processes for each test group
    --max-worker-restart=1

# Test paths
testpaths = tests

# Markers
markers =
    fast: marks tests as fast (<1s execution, unit tests)
    medium: marks tests as medium (1-10s execution, integration tests)
    slow: marks tests as slow (>10s execution, full system tests)
    performance: marks performance tests
    integration: marks integration tests
    needs_data: marks tests that require 5etools data
"""

    pytest_ini_path = Path("pytest.ini")
    pytest_ini_path.write_text(pytest_ini_content)
    print("✓ Created pytest.ini with better isolation settings")


def update_pyproject_for_isolation():
    """Update pyproject.toml to use better isolation settings."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Find the pytest configuration section
    old_config = """"-n", "auto",  # Enable parallel test execution
    # Note: Parallel execution confirmed working - failures are pre-existing mocking issues"""

    new_config = """"-n", "auto",  # Enable parallel test execution
    "--dist", "loadscope",  # Group tests by module for better isolation
    "--max-worker-restart", "1",  # Force new processes to avoid contamination
    # Note: Enhanced isolation for parallel execution"""

    if old_config in content:
        content = content.replace(old_config, new_config)
        pyproject_path.write_text(content)
        print("✓ Updated pyproject.toml with better isolation settings")
    else:
        print("⚠ Could not find expected pytest config - may already be updated")


def main():
    """Apply all fixes for parallel test reliability."""
    print("Applying fixes for parallel test execution...\n")

    fix_test_data_omnidexer_fixture()
    add_setup_method_to_integration_tests()
    update_pyproject_for_isolation()

    print("\n=== Fixes Applied ===")
    print("The following changes have been made:")
    print("1. Enhanced test_data_omnidexer fixture isolation")
    print("2. Added extra container resets to integration tests")
    print("3. Updated pytest configuration for better parallel isolation")
    print("\nNext steps:")
    print("1. Run 'make test' to verify fixes")
    print(
        "2. If tests still fail, consider running with --dist=no to disable parallel execution"
    )
    print("3. Monitor for any remaining intermittent failures")


if __name__ == "__main__":
    main()
