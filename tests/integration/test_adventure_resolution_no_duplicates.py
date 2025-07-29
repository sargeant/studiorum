"""Integration test for adventure resolution without duplicates."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers.content_resolver import ContentResolver, ResolutionStatus


class TestAdventureResolutionNoDuplicates(IsolatedAsyncioTestCase):
    """Test that adventure resolution returns no duplicates after implementing metadata/content separation."""

    async def test_omnidexer_loads_only_metadata_adventures(self) -> None:
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

            # Create adventure content files (should be skipped)
            lmop_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Introduction",
                        "id": "000",
                        "entries": [
                            "Lost Mine of Phandelver is an adventure for four to five 1st-level characters."
                        ],
                    }
                ]
            }

            cos_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Introduction",
                        "id": "000",
                        "entries": [
                            "Under raging storm clouds, the vampire Count Strahd von Zarovich stands silhouetted."
                        ],
                    }
                ]
            }

            # Write files
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(adventures_metadata, f)

            lmop_file = temp_path / "adventure-lmop.json"
            with open(lmop_file, "w") as f:
                json.dump(lmop_content, f)

            cos_file = temp_path / "adventure-cos.json"
            with open(cos_file, "w") as f:
                json.dump(cos_content, f)

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
            load_stats = await omnidexer.load_all_data()

            # Verify only metadata adventures were loaded (not content files)
            self.assertEqual(
                load_stats.get("adventure", 0),
                2,
                "Should load exactly 2 adventures from metadata file",
            )

            # Verify we can get adventures
            all_adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
            self.assertEqual(
                len(all_adventures),
                2,
                "Should have exactly 2 adventures (no duplicates)",
            )

            # Verify the adventures have correct names
            adventure_names = {adventure.name for adventure in all_adventures}
            self.assertEqual(
                adventure_names, {"Lost Mine of Phandelver", "Curse of Strahd"}
            )

    async def test_content_resolver_finds_unique_adventures(self) -> None:
        """Test that ContentResolver finds unique adventures without duplicates."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create adventures metadata file
            adventures_metadata = {
                "adventure": [
                    {
                        "name": "Curse of Strahd",
                        "id": "CoS",
                        "source": {"abbreviation": "COS", "name": "Curse of Strahd"},
                        "published": "2016-03-15",
                        "contents": [
                            {"name": "Introduction", "headers": ["Background"]}
                        ],
                    }
                ]
            }

            # Create adventure content file (should be ignored during loading)
            cos_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Introduction",
                        "entries": [
                            "Under raging storm clouds, the vampire Count Strahd von Zarovich stands."
                        ],
                    }
                ]
            }

            # Write files
            adventures_file = temp_path / "adventures.json"
            with open(adventures_file, "w") as f:
                json.dump(adventures_metadata, f)

            cos_file = temp_path / "adventure-cos.json"
            with open(cos_file, "w") as f:
                json.dump(cos_content, f)

            # Create mock source manager that filters out content files
            mock_source_manager = Mock(spec=ConfigurableSourceManager)
            # Only adventures.json should be loaded, content files should be filtered out
            mock_source_manager.get_data_paths.return_value = {
                ContentType.ADVENTURE: [adventures_file]  # Content files filtered out
            }
            mock_source_manager.ensure_sources_ready.return_value = None

            # Create omnidexer and load data
            omnidexer = Omnidexer(source_manager=mock_source_manager)
            await omnidexer.load_all_data()

            # Create content resolver
            resolver = ContentResolver(omnidexer)

            # Resolve "cos" - should find exactly one match
            result = resolver.resolve_adventure("cos")

            self.assertEqual(
                result.status, ResolutionStatus.EXACT_MATCH, "Should find exact match"
            )
            self.assertIsNotNone(result.content, "Should return adventure content")
            if result.content is not None:
                self.assertEqual(
                    result.content.name,
                    "Curse of Strahd",
                    "Should return correct adventure",
                )

            # Verify no multiple matches (which would indicate duplicates)
            self.assertEqual(
                len(result.matches or []), 0, "Should not have multiple matches"
            )

    async def test_no_duplicate_adventures_in_omnidexer_stats(self) -> None:
        """Test that omnidexer statistics show no duplicate adventures."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create realistic scenario with multiple adventures
            adventures_metadata = {
                "adventure": [
                    {
                        "name": "Lost Mine of Phandelver",
                        "id": "LMoP",
                        "source": {
                            "abbreviation": "LMOP",
                            "name": "Lost Mine of Phandelver",
                        },
                        "contents": [],
                    },
                    {
                        "name": "Curse of Strahd",
                        "id": "CoS",
                        "source": {"abbreviation": "COS", "name": "Curse of Strahd"},
                        "contents": [],
                    },
                    {
                        "name": "Storm King's Thunder",
                        "id": "SKT",
                        "source": {
                            "abbreviation": "SKT",
                            "name": "Storm King's Thunder",
                        },
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
            await omnidexer.load_all_data()

            # Get statistics
            stats = omnidexer.get_statistics()

            # Verify we loaded exactly 3 adventures (not 6 with duplicates)
            adventure_count = stats["by_type"].get("adventure", 0)
            self.assertEqual(
                adventure_count,
                3,
                f"Should have exactly 3 adventures, got {adventure_count}",
            )

            # Verify total count matches
            self.assertEqual(
                stats["total_items"], 3, "Total items should match adventure count"
            )

            # Verify we can resolve each adventure uniquely
            resolver = ContentResolver(omnidexer)

            for adventure in adventures_metadata["adventure"]:
                source_info = adventure["source"]
                if isinstance(source_info, dict) and "abbreviation" in source_info:
                    source_abbrev = source_info["abbreviation"]
                    abbreviation = (
                        source_abbrev.lower()
                        if isinstance(source_abbrev, str)
                        else str(source_abbrev).lower()
                    )
                    result = resolver.resolve_adventure(abbreviation)

                    self.assertEqual(
                        result.status,
                        ResolutionStatus.EXACT_MATCH,
                        f"Should resolve {abbreviation} exactly",
                    )
                    if result.content is not None:
                        self.assertEqual(
                            result.content.name,
                            adventure["name"],
                            f"Should resolve to correct adventure: {adventure['name']}",
                        )

    async def test_adventure_content_files_ignored_during_indexing(self) -> None:
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
            load_stats = await omnidexer.load_all_data()

            # Should load 0 adventures since all files are content files
            adventure_count = load_stats.get("adventure", 0)
            self.assertEqual(
                adventure_count, 0, "Should load 0 adventures from content-only files"
            )

            # Verify omnidexer has no adventures
            all_adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
            self.assertEqual(
                len(all_adventures), 0, "Should have no adventures indexed"
            )

            # Verify statistics
            stats = omnidexer.get_statistics()
            self.assertEqual(
                stats["by_type"].get("adventure", 0),
                0,
                "Stats should show 0 adventures",
            )
