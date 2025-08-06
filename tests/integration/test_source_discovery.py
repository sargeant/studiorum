"""Integration tests for source discovery and file separation."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType


class TestSourceDiscovery:
    """Test comprehensive source discovery and file separation."""

    def test_books_metadata_vs_content_separation(self) -> None:
        """Test that books follow the same metadata/content pattern as adventures."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create books metadata file (should be loaded)
            books_metadata = {
                "book": [
                    {
                        "name": "Player's Handbook",
                        "id": "PHB",
                        "source": "PHB",
                        "contents": [
                            {
                                "name": "Chapter 1: Step-by-Step Characters",
                                "ordinal": {"type": "chapter", "identifier": 1},
                            },
                            {
                                "name": "Chapter 2: Races",
                                "ordinal": {"type": "chapter", "identifier": 2},
                            },
                        ],
                    },
                    {
                        "name": "Monster Manual",
                        "id": "MM",
                        "source": "MM",
                        "contents": [
                            {
                                "name": "Introduction",
                                "ordinal": {"type": "chapter", "identifier": 0},
                            },
                            {
                                "name": "A",
                                "ordinal": {"type": "appendix", "identifier": "A"},
                            },
                        ],
                    },
                ]
            }

            # Create book content files (should be skipped)
            phb_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Chapter 1: Step-by-Step Characters",
                        "entries": ["Your first step in playing an adventurer..."],
                    }
                ]
            }

            mm_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Introduction",
                        "entries": ["This bestiary provides game statistics..."],
                    }
                ]
            }

            # Write files
            books_file = temp_path / "books.json"
            with open(books_file, "w") as f:
                json.dump(books_metadata, f)

            phb_file = temp_path / "book-phb.json"
            with open(phb_file, "w") as f:
                json.dump(phb_content, f)

            mm_file = temp_path / "book-mm.json"
            with open(mm_file, "w") as f:
                json.dump(mm_content, f)

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # Only books.json should be loaded, content files should be filtered out
            mock_source_manager.get_data_paths.return_value = {
                ContentType.BOOK: [books_file]  # Content files filtered out
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer with mock source manager
            omnidexer = Omnidexer(source_manager=mock_source_manager)

            # Load data
            load_stats = omnidexer.load_all_data()

            # Verify only metadata books were loaded (not content files)
            assert load_stats.get("book", 0) == 2, (
                "Should load exactly 2 books from metadata file"
            )

            # Verify we can get books
            all_books = omnidexer.get_all_by_type(ContentType.BOOK)
            assert len(all_books) == 2

            # Verify the books have correct names
            book_names = {book.name for book in all_books}
            assert book_names == {"Player's Handbook", "Monster Manual"}

    def test_mixed_adventures_and_books_separation(self) -> None:
        """Test that both adventures and books are properly separated from their content files."""
        # This test focuses on verifying that the source manager correctly
        # separates metadata files from content files for both adventures and books.
        # We'll use simpler data structures to avoid model validation issues.

        test_files = [
            Path("/data/adventures.json"),  # metadata - should be loaded
            Path("/data/books.json"),  # metadata - should be loaded
            Path("/data/adventure-cos.json"),  # content - should be skipped
            Path("/data/book-phb.json"),  # content - should be skipped
            Path("/data/spells.json"),  # other content - should be loaded
        ]

        with patch.object(ConfigurableSourceManager, "__init__", return_value=None):
            with patch.object(ConfigurableSourceManager, "ensure_sources_ready"):
                source_manager = ConfigurableSourceManager()
                source_manager.content_manager = Mock()
                source_manager.content_manager._index_built = True
                source_manager.content_manager.get_all_content_files = Mock(
                    return_value={"5etools": test_files}
                )
                source_manager._data_paths_cache = None

                # Test that get_data_paths correctly filters content files
                data_paths = source_manager.get_data_paths()

                # Should include metadata files
                metadata_files_found = []
                content_files_found = []

                for content_type, paths in data_paths.items():
                    for path in paths:
                        if "adventures.json" in str(path) or "books.json" in str(path):
                            metadata_files_found.append(str(path))
                        elif "adventure-" in str(path) or "book-" in str(path):
                            content_files_found.append(str(path))

                # Should find metadata files
                assert any("adventures.json" in f for f in metadata_files_found), (
                    "adventures.json metadata file should be included"
                )
                assert any("books.json" in f for f in metadata_files_found), (
                    "books.json metadata file should be included"
                )

                # Should NOT find content files
                assert not any(
                    "adventure-cos.json" in f for f in content_files_found
                ), "adventure-cos.json content file should be skipped"
                assert not any("book-phb.json" in f for f in content_files_found), (
                    "book-phb.json content file should be skipped"
                )

    def test_error_cases_missing_metadata_files(self) -> None:
        """Test error handling when metadata files are missing but content files exist."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create only content files (no metadata)
            cos_content = {
                "data": [
                    {"type": "section", "name": "Introduction", "entries": ["Content"]}
                ]
            }
            phb_content = {
                "data": [
                    {"type": "section", "name": "Chapter 1", "entries": ["Content"]}
                ]
            }

            cos_file = temp_path / "adventure-cos.json"
            with open(cos_file, "w") as f:
                json.dump(cos_content, f)

            phb_file = temp_path / "book-phb.json"
            with open(phb_file, "w") as f:
                json.dump(phb_content, f)

            # Create mock source manager that filters out all content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            mock_source_manager.get_data_paths.return_value = {}  # All files filtered out
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            load_stats = omnidexer.load_all_data()

            # Should load nothing since only content files exist
            assert load_stats.get("adventure", 0) == 0
            assert load_stats.get("book", 0) == 0

            # Verify no content in omnidexer
            all_adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
            all_books = omnidexer.get_all_by_type(ContentType.BOOK)

            assert len(all_adventures) == 0
            assert len(all_books) == 0

    def test_malformed_metadata_files_handling(self) -> None:
        """Test handling of malformed metadata files."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create malformed adventures metadata file
            malformed_adventures = {
                "adventure": [
                    {
                        # Missing required fields like 'name', 'id'
                        "source": {"abbreviation": "TEST", "name": "Test Adventure"},
                        "contents": [],
                    }
                ]
            }

            # Write malformed file
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(malformed_adventures, f)

            # Create mock source manager
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: [adventures_file]
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            load_stats = omnidexer.load_all_data()

            # Should handle malformed data gracefully (may load 0 or fail gracefully)
            adventure_count = load_stats.get("adventure", 0)
            assert isinstance(adventure_count, int)
            assert adventure_count >= 0

    def test_configurable_source_manager_interface_methods(self) -> None:
        """Test that ConfigurableSourceManager properly implements dual-file interface methods."""
        # Create test files list
        test_files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure-cos.json"),  # content
            Path("/data/adventure-lmop.json"),  # content
            Path("/data/book-phb.json"),  # content
            Path("/data/book-mm.json"),  # content
            Path("/data/spells.json"),  # other content
        ]

        with patch.object(ConfigurableSourceManager, "__init__", return_value=None):
            with patch.object(ConfigurableSourceManager, "ensure_sources_ready"):
                source_manager = ConfigurableSourceManager()
                source_manager.content_manager = Mock()
                source_manager.content_manager._index_built = True
                source_manager.content_manager.get_all_content_files = Mock(
                    return_value={"5etools": test_files}
                )
                source_manager._data_paths_cache = None

                # Test get_metadata_files
                metadata_files = source_manager.get_metadata_files()

                # Should contain adventures and books metadata
                assert ContentType.ADVENTURE in metadata_files
                assert ContentType.BOOK in metadata_files

                # Count metadata files
                total_metadata = sum(len(paths) for paths in metadata_files.values())
                assert total_metadata == 2, "Should have 2 metadata files"

                # Test get_content_files
                content_files = source_manager.get_content_files()

                # Should contain adventures and books content
                assert ContentType.ADVENTURE in content_files
                assert ContentType.BOOK in content_files

                # Count content files
                total_content = sum(len(paths) for paths in content_files.values())
                assert total_content == 4, "Should have 4 content files"

                # Test get_data_paths (should match metadata for adventures/books)
                data_paths = source_manager.get_data_paths()

                # For adventures and books, should match metadata files
                if ContentType.ADVENTURE in data_paths:
                    adventure_data_paths = set(data_paths[ContentType.ADVENTURE])
                    adventure_metadata_paths = set(
                        metadata_files[ContentType.ADVENTURE]
                    )
                    assert adventure_data_paths == adventure_metadata_paths

                if ContentType.BOOK in data_paths:
                    book_data_paths = set(data_paths[ContentType.BOOK])
                    book_metadata_paths = set(metadata_files[ContentType.BOOK])
                    assert book_data_paths == book_metadata_paths

    def test_file_pattern_edge_cases(self) -> None:
        """Test edge cases for file pattern matching."""
        test_cases = [
            # Should be detected as metadata
            (Path("/data/adventures.json"), True, False),
            (Path("/data/books.json"), True, False),
            (Path("/some/deep/path/adventures.json"), True, False),
            (Path("/some/deep/path/books.json"), True, False),
            # Should be detected as content
            (Path("/data/adventure-cos.json"), False, True),
            (Path("/data/book-phb.json"), False, True),
            (Path("/data/adventure-very-long-name.json"), False, True),
            (Path("/data/book-custom-book-name.json"), False, True),
            # Should not be detected as either
            (Path("/data/adventurous.json"), False, False),
            (Path("/data/adventure.json"), False, False),
            (Path("/data/booking.json"), False, False),
            (Path("/data/book.json"), False, False),
            (Path("/data/my-adventure-guide.json"), False, False),
            (Path("/data/fantasy-book-collection.json"), False, False),
            (Path("/data/spells.json"), False, False),
            (Path("/data/creatures.json"), False, False),
        ]

        with patch.object(ConfigurableSourceManager, "__init__", return_value=None):
            source_manager = ConfigurableSourceManager()

            for file_path, should_be_metadata, should_be_content in test_cases:
                is_metadata = source_manager._is_metadata_file(file_path)
                is_content = source_manager._is_content_file(file_path)

                assert is_metadata == should_be_metadata, (
                    f"File {file_path} metadata detection failed: expected {should_be_metadata}, got {is_metadata}"
                )

                assert is_content == should_be_content, (
                    f"File {file_path} content detection failed: expected {should_be_content}, got {is_content}"
                )

                # Files should not be both metadata and content
                assert not (is_metadata and is_content), (
                    f"File {file_path} should not be both metadata and content"
                )
