"""Tests for BaseConvertCommand architecture."""

from pathlib import Path
from unittest.mock import Mock, patch

from studiorum.cli.commands.convert.base import (
    AppendixMixin,
    BaseConvertCommand,
)


class TestBaseConvertCommand:
    """Test BaseConvertCommand class."""

    def test_init(self):
        """Test BaseConvertCommand initialization."""
        command = BaseConvertCommand()

        # Should have content reference manager
        assert hasattr(command, "_content_reference_manager")
        assert command._content_reference_manager is not None

    @patch("studiorum.cli.commands.convert.base.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    def test_apply_config_hierarchy_basic(
        self, mock_get_content_config, mock_get_app_config
    ):
        """Test basic config hierarchy application."""
        # Mock configurations matching actual config structure
        mock_app_config = Mock()
        mock_app_config.rendering.latex.document.paper_size = "a4paper"
        mock_app_config.rendering.latex.document.fonts = "default_fonts"
        mock_app_config.rendering.latex.document.background = "full"
        mock_app_config.rendering.latex.document.no_outline = False
        mock_app_config.rendering.latex.document.font_size = "10pt"
        mock_app_config.rendering.latex.document.high_contrast = False
        mock_app_config.rendering.latex.document.two_column = False
        mock_app_config.rendering.latex.document.justified_text = True
        mock_app_config.paths.output_path = Path("output")

        mock_get_app_config.return_value = mock_app_config

        # Don't mock user config - let it use the real empty default
        command = BaseConvertCommand()

        # Test hierarchy: CLI args override user config, user config overrides app config
        # Since user config has None values, app config should be used for most things
        config = command.apply_config_hierarchy(
            paper="legal",  # CLI arg - highest priority (overrides app config)
            # No fonts CLI arg - should fall back to app config since user config is None
        )

        assert config["paper_size"] == "legal"  # CLI override
        assert (
            config["fonts"] == "default_fonts"
        )  # App config fallback (user config is None)
        assert config["main_font"] is None  # main_font not in config structures
        assert config["title"] is None  # No title in config structures

    @patch("studiorum.cli.commands.convert.base.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    def test_apply_config_hierarchy_all_cli_args(
        self, mock_get_content_config, mock_get_app_config
    ):
        """Test config hierarchy with all CLI arguments provided."""
        # Mock configurations matching actual config structure
        mock_app_config = Mock()
        mock_app_config.rendering.latex.document.paper_size = "a4paper"
        mock_app_config.rendering.latex.document.fonts = "default_fonts"
        mock_app_config.rendering.latex.document.background = "full"
        mock_app_config.rendering.latex.document.no_outline = False
        mock_app_config.rendering.latex.document.font_size = "10pt"
        mock_app_config.rendering.latex.document.high_contrast = False
        mock_app_config.rendering.latex.document.two_column = False
        mock_app_config.rendering.latex.document.justified_text = True
        mock_app_config.paths.output_path = Path("output")

        mock_get_app_config.return_value = mock_app_config

        mock_user_config = Mock()
        mock_user_config.latex.paper_size = "letterpaper"
        # Create nested structure for fonts
        mock_fonts = Mock()
        mock_fonts.main_font = "User Font"
        mock_user_config.latex.fonts = mock_fonts
        mock_get_content_config.return_value = mock_user_config

        command = BaseConvertCommand()

        # All CLI args provided - should override everything
        config = command.apply_config_hierarchy(
            paper="legal",
            main_font="CLI Font",
            sans_font="CLI Sans",
            mono_font="CLI Mono",
            title="CLI Title",
            author="CLI Author",
            output_dir=Path("cli_output"),
        )

        assert config["paper_size"] == "legal"
        assert config["main_font"] == "CLI Font"
        assert config["sans_font"] == "CLI Sans"
        assert config["mono_font"] == "CLI Mono"
        assert config["title"] == "CLI Title"
        assert config["author"] == "CLI Author"
        assert config["output_directory"] == Path("cli_output")

    @patch("studiorum.cli.commands.convert.base.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    def test_apply_config_hierarchy_none_values(
        self, mock_get_content_config, mock_get_app_config
    ):
        """Test config hierarchy with None CLI values."""
        # Mock configurations matching actual config structure
        mock_app_config = Mock()
        mock_app_config.rendering.latex.document.paper_size = "a4paper"
        mock_app_config.rendering.latex.document.fonts = "default_fonts"
        mock_app_config.rendering.latex.document.background = "full"
        mock_app_config.rendering.latex.document.no_outline = False
        mock_app_config.rendering.latex.document.font_size = "10pt"
        mock_app_config.rendering.latex.document.high_contrast = False
        mock_app_config.rendering.latex.document.two_column = False
        mock_app_config.rendering.latex.document.justified_text = True
        mock_app_config.paths.output_path = Path("output")
        mock_get_app_config.return_value = mock_app_config

        mock_user_config = Mock()
        mock_user_config.latex.paper_size = "letterpaper"
        # Create nested structure for fonts
        mock_fonts = Mock()
        mock_fonts.main_font = "User Font"
        mock_user_config.latex.fonts = mock_fonts
        mock_get_content_config.return_value = mock_user_config

        command = BaseConvertCommand()

        # None CLI args should not override lower priorities
        config = command.apply_config_hierarchy(
            paper=None,  # Should use user config
            main_font=None,  # Should use user config
        )

        assert (
            config["paper_size"] == "a4paper"
        )  # App config fallback (user config is None)
        assert config["main_font"] is None  # main_font not in config structures

    @patch("studiorum.cli.utils.get_omnidexer")
    def test_get_content_loader_omnidexer_source(self, mock_get_omnidexer):
        """Test content loader with omnidexer source."""
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        command = BaseConvertCommand()

        with patch(
            "studiorum.cli.commands.convert.base.ContentLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            with patch(
                "studiorum.cli.commands.convert.base.create_omnidexer_source"
            ) as mock_create_source:
                mock_source = Mock()
                mock_create_source.return_value = mock_source

                loader = command.get_content_loader("spell", use_omnidexer=True)

                assert loader == mock_loader
                # Check that the content type is converted to ContentType enum
                from studiorum.core.models.content import ContentType

                expected_content_type = ContentType.SPELL
                # The method directly passes the omnidexer now, not a Success result
                actual_call = mock_create_source.call_args[0]
                assert actual_call[0] == mock_omnidexer
                assert actual_call[1] == expected_content_type
                mock_loader.add_source.assert_called_once_with(mock_source)

    def test_get_content_loader_file_sources(self):
        """Test content loader with file sources."""
        command = BaseConvertCommand()

        with patch(
            "studiorum.cli.commands.convert.base.ContentLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            with patch(
                "studiorum.cli.commands.convert.base.create_file_source"
            ) as mock_create_source:
                mock_source1 = Mock()
                mock_source2 = Mock()
                mock_create_source.side_effect = [mock_source1, mock_source2]

                file_paths = [Path("file1.json"), Path("file2.json")]
                loader = command.get_content_loader("creature", file_paths=file_paths)

                assert loader == mock_loader
                assert mock_create_source.call_count == 2
                assert mock_loader.add_source.call_count == 2

    @patch("studiorum.cli.utils.get_omnidexer")
    def test_get_content_reference_manager(self, mock_get_omnidexer):
        """Test getting content reference manager."""
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        command = BaseConvertCommand()

        # First call should create manager
        manager1 = command.get_content_reference_manager()
        assert manager1 is not None
        assert manager1.omnidexer == mock_omnidexer

        # Second call should return same instance
        manager2 = command.get_content_reference_manager()
        assert manager1 is manager2


class TestAppendixMixin:
    """Test AppendixMixin class."""

    def test_init(self):
        """Test AppendixMixin initialization."""
        mixin = AppendixMixin()

        # Should have content reference manager
        assert hasattr(mixin, "_content_reference_manager")

    @patch("studiorum.cli.utils.get_omnidexer")
    def test_get_content_reference_manager(self, mock_get_omnidexer):
        """Test getting content reference manager."""
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        mixin = AppendixMixin()

        manager = mixin.get_content_reference_manager()
        assert manager is not None
        assert manager.omnidexer == mock_omnidexer

    def test_track_content_references(self):
        """Test tracking content references."""
        mixin = AppendixMixin()

        # Mock content with deep indexing capability
        mock_content1 = Mock()
        mock_content1.name = "Content 1"

        mock_content2 = Mock()
        mock_content2.name = "Content 2"

        content = [mock_content1, mock_content2]

        with patch.object(mixin, "get_content_reference_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            mixin.track_content_references(content, "test context")

            # Should try to track each content item
            assert mock_manager.track_deep_index_references.call_count == 2

    def test_generate_appendices(self):
        """Test appendix generation."""
        mixin = AppendixMixin()

        with patch.object(mixin, "get_content_reference_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            # Mock reference manager returns
            mock_spell_refs = [Mock(), Mock()]
            mock_creature_refs = [Mock()]
            mock_manager.get_unique_references_by_type.side_effect = lambda t: {
                "spell": mock_spell_refs,
                "creature": mock_creature_refs,
                "item": [],
            }.get(t, [])

            appendices = mixin.generate_appendices()

            assert appendices["has_appendices"] is True
            assert appendices["spell_appendix"] == "Spell appendix content"
            assert appendices["creature_appendix"] == "Creature appendix content"
            assert appendices["item_appendix"] is None

    def test_generate_appendices_no_references(self):
        """Test appendix generation with no references."""
        mixin = AppendixMixin()

        with patch.object(mixin, "get_content_reference_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            # No references found
            mock_manager.get_unique_references_by_type.return_value = []

            appendices = mixin.generate_appendices()

            assert appendices["has_appendices"] is False
            assert appendices["spell_appendix"] is None
            assert appendices["creature_appendix"] is None
            assert appendices["item_appendix"] is None
