"""Tests for BaseConvertCommand architecture."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.cli.commands.convert.base import (
    AppendixMixin,
    BaseConvertCommand,
    LaTeXMixin,
)
from studiorum.core.error_types import ConfigurationError, MCPException
from studiorum.core.result import Success
from tests.test_helpers import reset_test_environment


class TestBaseConvertCommand:
    """Test BaseConvertCommand class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

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

    def test_validate_output_directory_exists(self):
        """Test output directory validation for existing directory."""
        command = BaseConvertCommand()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                # Should not raise exception
                command.validate_output_directory(Path("existing_dir"))

    def test_validate_output_directory_not_exists(self):
        """Test output directory validation creates directory."""
        command = BaseConvertCommand()

        mock_path = Mock()
        mock_path.exists.return_value = False

        with patch.object(mock_path, "mkdir") as mock_mkdir:
            command.validate_output_directory(mock_path)
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_validate_output_directory_not_directory(self):
        """Test output directory validation fails for non-directory."""
        command = BaseConvertCommand()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=False):
                with pytest.raises(MCPException) as exc_info:
                    command.validate_output_directory(Path("not_a_dir"))

                assert "not a directory" in str(exc_info.value)
                assert isinstance(exc_info.value.mcp_error, ConfigurationError)


class TestLaTeXMixin:
    """Test LaTeXMixin class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_get_latex_parameters_basic(self):
        """Test basic LaTeX parameter generation."""
        mixin = LaTeXMixin()

        config = {
            "paper_size": "letterpaper",
            "main_font": "Times",
            "sans_font": "Arial",
            "mono_font": "Courier",
            "title": "Test Document",
            "author": "Test Author",
            "margin_top": "1in",
            "margin_bottom": "1in",
            "margin_left": "1in",
            "margin_right": "1in",
        }

        params = mixin.get_latex_parameters(config)

        assert params["paper_size"] == "letterpaper"
        assert params["use_custom_fonts"] is True
        assert params["main_font"] == "Times"
        assert params["sans_font"] == "Arial"
        assert params["mono_font"] == "Courier"
        assert params["title"] == "Test Document"
        assert params["author"] == "Test Author"
        assert params["margin_top"] == "1in"

    def test_get_latex_parameters_no_fonts(self):
        """Test LaTeX parameters without custom fonts."""
        mixin = LaTeXMixin()

        config = {"paper_size": "a4paper", "title": "Test Document"}

        params = mixin.get_latex_parameters(config)

        assert params["paper_size"] == "a4paper"
        assert params["use_custom_fonts"] is False
        assert params.get("main_font") is None

    def test_prepare_latex_context(self):
        """Test LaTeX context preparation."""
        mixin = LaTeXMixin()

        config = {"paper_size": "letterpaper", "title": "Test Document"}

        content = [Mock(), Mock()]

        context = mixin.prepare_latex_context(config, content)

        assert "paper_size" in context
        assert "title" in context
        assert context["content"] == content
        assert "show_title_page" in context
        assert "include_toc" in context

    def test_should_include_title_page(self):
        """Test title page inclusion logic."""
        mixin = LaTeXMixin()

        # Should include if title provided
        assert mixin.should_include_title_page({"title": "Test"}) is True

        # Should not include if no title
        assert mixin.should_include_title_page({}) is False
        assert mixin.should_include_title_page({"title": None}) is False
        assert mixin.should_include_title_page({"title": ""}) is False

    def test_should_include_toc(self):
        """Test table of contents inclusion logic."""
        mixin = LaTeXMixin()

        # Default should be True for multiple content items
        content = [Mock(), Mock(), Mock()]
        assert mixin.should_include_toc({}, content) is True

        # Should be False for single item
        single_content = [Mock()]
        assert mixin.should_include_toc({}, single_content) is False

        # Should respect explicit config
        assert mixin.should_include_toc({"include_toc": False}, content) is False
        assert mixin.should_include_toc({"include_toc": True}, single_content) is True


class TestAppendixMixin:
    """Test AppendixMixin class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

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


@pytest.mark.integration
class TestBaseConvertCommandIntegration:
    """Integration tests for BaseConvertCommand architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    @patch("studiorum.cli.commands.convert.base.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch("studiorum.cli.utils.get_omnidexer")
    def test_full_command_workflow(
        self, mock_get_omnidexer, mock_get_content_config, mock_get_app_config
    ):
        """Test complete command workflow."""
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
        mock_get_content_config.return_value = mock_user_config

        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Create command with all mixins for full workflow test
        class TestCommand(BaseConvertCommand, LaTeXMixin, AppendixMixin):
            pass

        command = TestCommand()

        # 1. Apply config hierarchy
        config = command.apply_config_hierarchy(title="CLI Title")
        assert config["title"] == "CLI Title"
        assert (
            config["paper_size"] == "a4paper"
        )  # App config fallback (user config is None)

        # 2. Get content loader
        with patch(
            "studiorum.cli.commands.convert.base.ContentLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            loader = command.get_content_loader("spell", use_omnidexer=True)
            assert loader == mock_loader

        # 3. Get reference manager
        ref_manager = command.get_content_reference_manager()
        assert ref_manager.omnidexer == mock_omnidexer

        # 4. Validate output directory
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                command.validate_output_directory(Path("test_output"))

        # 5. Prepare LaTeX context
        content = [Mock(), Mock()]
        latex_context = command.prepare_latex_context(config, content)
        assert latex_context["title"] == "CLI Title"
        assert latex_context["content"] == content

        # 6. Track references and generate appendices
        command.track_content_references(content)
        command.generate_appendices()
        # Test passes if no exceptions raised

    def test_mixin_combination(self):
        """Test combining BaseConvertCommand with mixins."""

        class TestCommand(BaseConvertCommand, LaTeXMixin, AppendixMixin):
            """Test command combining all mixins."""

            pass

        command = TestCommand()

        # Should have all functionality
        assert hasattr(command, "apply_config_hierarchy")
        assert hasattr(command, "get_latex_parameters")
        assert hasattr(command, "generate_appendices")
        assert hasattr(command, "get_content_reference_manager")

        # Test method resolution order works correctly
        config = {"paper_size": "a4paper", "title": "Test"}
        content = [Mock()]

        with patch("studiorum.cli.commands.convert.base.get_app_config"):
            with patch("studiorum.core.config.sources.get_content_config"):
                # Should not raise any method resolution conflicts
                latex_params = command.get_latex_parameters(config)
                latex_context = command.prepare_latex_context(config, content)

                assert "paper_size" in latex_params
                assert "content" in latex_context
