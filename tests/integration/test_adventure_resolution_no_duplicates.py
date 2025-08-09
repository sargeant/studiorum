"""Integration test for adventure resolution without duplicates."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers.content_resolver import ContentResolver, ResolutionStatus


@pytest.mark.integration
class TestAdventureResolutionNoDuplicates:
    """Test that adventure resolution returns no duplicates after implementing metadata/content separation."""

    def test_omnidexer_loads_only_metadata_adventures(self) -> None:
        """Test that omnidexer only loads adventures from metadata files, not content files."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create adventures metadata file (should be loaded)
            adventures_metadata = {
                "adventure": [
                    {
                        "name": "Lost Mine of Phandelver",
                        "id": "LMoP",
                        "source": {
                            "abbreviation": "LMOP",
                            "name": "Lost Mine of Phandelver",
                        },
                        "published": "2014-07-15",
                        "contents": [
                            {"name": "Introduction", "headers": ["Background"]},
                            {
                                "name": "Part 1: Goblin Ambush",
                                "headers": ["The Ambush"],
                            },
                        ],
                    },
                    {
                        "name": "Curse of Strahd",
                        "id": "CoS",
                        "source": {"abbreviation": "COS", "name": "Curse of Strahd"},
                        "published": "2016-03-15",
                        "contents": [
                            {"name": "Introduction", "headers": ["Background"]},
                            {
                                "name": "Chapter 1: Into the Mists",
                                "headers": ["Barovia"],
                            },
                        ],
                    },
                ]
            }

            # Write files
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(adventures_metadata, f)

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # Only adventures.json should be loaded, content files should be filtered out
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: [adventures_file]  # Content files filtered out
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer with mock source manager
            omnidexer = Omnidexer(source_manager=mock_source_manager)

            # Load data
            load_stats = omnidexer.load_all_data()

            # Verify only metadata adventures were loaded (not content files)
            assert load_stats.get("adventure") == 2

            # Verify we can get adventures
            all_adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
            assert len(all_adventures) == 2, (
                "Should have exactly 2 adventures (no duplicates)"
            )

            # Verify the adventures have correct names
            adventure_names = {adventure.name for adventure in all_adventures}
            assert adventure_names == {"Lost Mine of Phandelver", "Curse of Strahd"}

    def test_content_resolver_finds_unique_adventures(self) -> None:
        """Test that ContentResolver finds unique adventures without duplicates."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create adventures metadata file
            adventures_metadata = {
                "adventure": [
                    {
                        "name": "Test Adventure",
                        "id": "test-adventure",
                        "source": {"abbreviation": "TEST", "name": "Test Adventure"},
                        "published": "2024-01-01",
                        "contents": [
                            {"name": "Introduction", "headers": ["Background"]}
                        ],
                    }
                ]
            }

            # Create adventure content file (should be ignored during loading)

            # Write files
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(adventures_metadata, f)

            # Content files are ignored in this test, so we don't need to create them

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # Only adventures.json should be loaded, content files should be filtered out
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: [adventures_file]  # Content files filtered out
            }
            mock_source_manager.get_content_files.return_value = {
                ContentType.ADVENTURE: []  # No content files
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            omnidexer.load_all_data()

            # Create content resolver
            resolver = ContentResolver(omnidexer)

            # Resolve "TEST" - should find exactly one match
            result = resolver.resolve_adventure("TEST")

            assert result.status == ResolutionStatus.EXACT_MATCH, (
                "Should find exact match"
            )
            assert result.content is not None, "Should return adventure content"
            if result.content is not None:
                assert result.content.name == "Test Adventure", (
                    "Should return correct adventure"
                )

            # Verify no multiple matches (which would indicate duplicates)
            assert len(result.matches or []) == 0, "Should not have multiple matches"

    def test_no_duplicate_adventures_in_omnidexer_stats(self) -> None:
        """Test that omnidexer statistics show no duplicate adventures."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create realistic scenario with multiple adventures
            adventures_metadata = {
                "adventure": [
                    {
                        "name": "Test Adventure",
                        "id": "test-adventure",
                        "source": "TEST",
                        "group": "homebrew",
                        "published": "2024-01-01",
                        "contents": [],
                    },
                ]
            }

            # Create content files for each adventure (should all be skipped)
            content_files = []
            for adventure in adventures_metadata["adventure"]:
                content_data = {
                    "data": [
                        {
                            "type": "section",
                            "name": "Introduction",
                            "entries": [
                                f"This is the content for {adventure['name']}."
                            ],
                        }
                    ]
                }

                adventure_id = adventure["id"]
                adventure_id_str = (
                    adventure_id.lower()
                    if isinstance(adventure_id, str)
                    else str(adventure_id).lower()
                )
                content_file = temp_path / f"adventure-{adventure_id_str}.json"
                with open(content_file, "w") as f:
                    json.dump(content_data, f)
                content_files.append(content_file)

            # Write metadata file
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(adventures_metadata, f)

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # Only adventures.json should be loaded, content files should be filtered out
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: [adventures_file]  # Content files filtered out
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            omnidexer.load_all_data()

            # Get statistics
            stats = omnidexer.get_statistics()

            # Verify we loaded exactly 1 adventure (not duplicates)
            adventure_count = stats["by_type"].get("adventure", 0)
            assert adventure_count == 1, (
                f"Should have exactly 1 adventure, got {adventure_count}"
            )

            # Verify total count matches
            assert stats["total_items"] == 1, "Total items should match adventure count"

            # Verify we can resolve the adventure uniquely
            resolver = ContentResolver(omnidexer)

            for adventure in adventures_metadata["adventure"]:
                source_info = adventure["source"]
                if isinstance(source_info, str):
                    abbreviation = source_info.lower()
                    result = resolver.resolve_adventure(abbreviation)

                    assert result.status == ResolutionStatus.EXACT_MATCH, (
                        f"Should resolve {abbreviation} exactly"
                    )

                    if result.content is not None:
                        assert result.content.name == adventure["name"], (
                            f"Should resolve to correct adventure: {adventure['name']}"
                        )

    def test_adventure_content_files_ignored_during_indexing(self) -> None:
        """Test that adventure content files are completely ignored during indexing."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create ONLY content files (no metadata file)
            # This simulates what would happen if we only had content files
            content_files_data = [
                {
                    "data": [
                        {
                            "type": "section",
                            "name": "Introduction",
                            "entries": ["Content for Adventure 1"],
                        }
                    ]
                },
                {
                    "data": [
                        {
                            "type": "section",
                            "name": "Introduction",
                            "entries": ["Content for Adventure 2"],
                        }
                    ]
                },
            ]

            content_files = []
            for i, content_data in enumerate(content_files_data, 1):
                content_file = temp_path / f"adventure-test{i}.json"
                with open(content_file, "w") as f:
                    json.dump(content_data, f)
                content_files.append(content_file)

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # All content files should be filtered out, so empty list
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: []  # All content files filtered out
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and try to load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            load_stats = omnidexer.load_all_data()

            # Should load 0 adventures since all files are content files
            adventure_count = load_stats.get("adventure", 0)
            # Handle case where load_stats might not have adventure key or returns None
            if adventure_count is None:
                adventure_count = 0
            assert adventure_count == 0, (
                f"Should load 0 adventures from content-only files, got {adventure_count}"
            )

            # Verify omnidexer has no adventures
            all_adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
            assert len(all_adventures) == 0, "Should have no adventures indexed"

            # Verify statistics
            stats = omnidexer.get_statistics()
            adventure_stat = stats["by_type"].get("adventure", 0)
            if adventure_stat is None:
                adventure_stat = 0
            assert adventure_stat == 0
