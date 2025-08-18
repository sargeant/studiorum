#!/usr/bin/env python3
"""
Minimal test to isolate what causes book loading corruption in test environment.
"""


def test_fresh_python_session():
    """Test book loading in fresh Python session"""
    print("=== Fresh Python Session Test ===")

    from dnd5e.core.loaders.omnidexer import Omnidexer

    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    books = omnidexer.get_all_by_type("book")
    adventures = omnidexer.get_all_by_type("adventure")

    print(f"Books: {len(books)}")
    print(f"Adventures: {len(adventures)}")
    return len(books), len(adventures)


def test_after_test_imports():
    """Test book loading after importing test modules"""
    print("\n=== After Test Environment Imports ===")

    # Import modules that might affect global state
    import os

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    # Import test environment reset
    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.omnidexer import Omnidexer

    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    books = omnidexer.get_all_by_type("book")
    adventures = omnidexer.get_all_by_type("adventure")

    print(f"Books: {len(books)}")
    print(f"Adventures: {len(adventures)}")
    return len(books), len(adventures)


def test_with_container():
    """Test using service container like in tests"""
    print("\n=== With Service Container ===")

    import os

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.container import get_global_container, reset_global_container

    reset_global_container()

    container = get_global_container()
    omnidexer = container.get_omnidexer()

    books = omnidexer.get_all_by_type("book")
    adventures = omnidexer.get_all_by_type("adventure")

    print(f"Books: {len(books)}")
    print(f"Adventures: {len(adventures)}")
    return len(books), len(adventures)


def test_config_comparison():
    """Compare test vs production config loading"""
    print("\n=== Config Comparison ===")

    # Test production config
    print("Production config:")
    from dnd5e.core.loaders.omnidexer import Omnidexer as ProdOmnidexer

    prod_omnidexer = ProdOmnidexer()
    prod_omnidexer.load_all_data()

    prod_books = prod_omnidexer.get_all_by_type("book")
    prod_adventures = prod_omnidexer.get_all_by_type("adventure")
    print(f"  Books: {len(prod_books)}")
    print(f"  Adventures: {len(prod_adventures)}")

    # Test config
    print("Test config:")
    import os

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from dnd5e.core.loaders.omnidexer import Omnidexer as TestOmnidexer

    test_omnidexer = TestOmnidexer()
    test_omnidexer.load_all_data()

    test_books = test_omnidexer.get_all_by_type("book")
    test_adventures = test_omnidexer.get_all_by_type("adventure")
    print(f"  Books: {len(test_books)}")
    print(f"  Adventures: {len(test_adventures)}")

    return (len(prod_books), len(prod_adventures)), (
        len(test_books),
        len(test_adventures),
    )


if __name__ == "__main__":
    try:
        # Test 1: Fresh session
        fresh_books, fresh_adventures = test_fresh_python_session()

        # Test 2: After test imports
        test_books, test_adventures = test_after_test_imports()

        # Test 3: With container
        container_books, container_adventures = test_with_container()

        # Test 4: Config comparison
        (prod_books, prod_adventures), (config_books, config_adventures) = (
            test_config_comparison()
        )

        print("\n=== Summary ===")
        print(f"Fresh session:     Books={fresh_books}, Adventures={fresh_adventures}")
        print(f"After test import: Books={test_books}, Adventures={test_adventures}")
        print(
            f"With container:    Books={container_books}, Adventures={container_adventures}"
        )
        print(f"Prod config:       Books={prod_books}, Adventures={prod_adventures}")
        print(
            f"Test config:       Books={config_books}, Adventures={config_adventures}"
        )

        # Identify the corruption point
        if fresh_books > 0 and test_books == 0:
            print("\n❌ CORRUPTION: Book loading fails after test environment imports")
        elif test_books > 0 and container_books == 0:
            print("\n❌ CORRUPTION: Book loading fails with service container")
        elif config_books == 0:
            print("\n❌ CORRUPTION: Test config prevents book loading")
        else:
            print("\n✅ No corruption detected - unexpected results")

    except Exception as e:
        print(f"\n💥 Error during testing: {e}")
        import traceback

        traceback.print_exc()
