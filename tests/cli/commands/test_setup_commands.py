"""Tests for setup CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.setup import app
from dnd5e.core.config.sources import ContentConfiguration, ContentSource, SourceType
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestSetupWizardCommand:
    """Test setup wizard command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock config
        self.mock_config = ContentConfiguration()
        self.mock_config.cache_dir = self.temp_dir / "cache"
        self.mock_config.config_dir = self.temp_dir / "config"

        # Create mock config manager
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_config.return_value = self.mock_config
        self.mock_config_manager.reset_to_defaults.return_value = self.mock_config
        self.mock_config_manager.update_config = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup.Prompt")
    @patch("dnd5e.cli.commands.setup._scan_content")
    def test_wizard_defaults_with_scan(
        self, mock_scan, mock_prompt, mock_confirm, mock_get_manager
    ):
        """Test setup wizard with defaults and content scan."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_prompt.ask.return_value = "1"  # Choose defaults
        mock_confirm.ask.side_effect = [True]  # Scan content

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        assert "Welcome to 5e2pdf Setup!" in result.stdout
        assert "Configuration complete!" in result.stdout

        self.mock_config_manager.reset_to_defaults.assert_called_once()
        mock_scan.assert_called_once()

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_wizard_defaults_without_scan(
        self, mock_prompt, mock_confirm, mock_get_manager
    ):
        """Test setup wizard with defaults but no content scan."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_prompt.ask.return_value = "1"  # Choose defaults
        mock_confirm.ask.side_effect = [False]  # Don't scan content

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        assert "5e2pdf sources scan" in result.stdout
        self.mock_config_manager.reset_to_defaults.assert_called_once()

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup.Prompt")
    @patch("dnd5e.cli.commands.setup._setup_custom")
    def test_wizard_custom_setup(
        self, mock_setup_custom, mock_prompt, mock_confirm, mock_get_manager
    ):
        """Test setup wizard with custom setup."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_prompt.ask.return_value = "2"  # Choose custom
        mock_confirm.ask.side_effect = [False]  # Don't scan content

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        mock_setup_custom.assert_called_once_with(self.mock_config_manager)

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup.Prompt")
    @patch("dnd5e.cli.commands.setup._setup_local")
    def test_wizard_local_setup(
        self, mock_setup_local, mock_prompt, mock_confirm, mock_get_manager
    ):
        """Test setup wizard with local setup."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_prompt.ask.return_value = "3"  # Choose local
        mock_confirm.ask.side_effect = [False]  # Don't scan content

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        mock_setup_local.assert_called_once_with(self.mock_config_manager)

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    def test_wizard_existing_sources_cancel(self, mock_confirm, mock_get_manager):
        """Test setup wizard with existing sources - user cancels."""
        # Add existing source
        existing_source = ContentSource(
            name="existing",
            type=SourceType.DIRECTORY,
            path=Path("/some/path"),
            enabled=True,
        )
        self.mock_config.content_sources = [existing_source]

        mock_get_manager.return_value = self.mock_config_manager
        mock_confirm.ask.return_value = False  # Don't reconfigure

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        assert "1 content sources configured" in result.stdout
        assert "Setup cancelled" in result.stdout

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_wizard_existing_sources_remove_and_reconfigure(
        self, mock_prompt, mock_confirm, mock_get_manager
    ):
        """Test setup wizard with existing sources - remove and reconfigure."""
        # Add existing source
        existing_source = ContentSource(
            name="existing",
            type=SourceType.DIRECTORY,
            path=Path("/some/path"),
            enabled=True,
        )
        self.mock_config.content_sources = [existing_source]

        mock_get_manager.return_value = self.mock_config_manager
        mock_confirm.ask.side_effect = [
            True,
            True,
            False,
        ]  # Reconfigure, remove existing, don't scan
        mock_prompt.ask.return_value = "1"  # Choose defaults

        result = self.runner.invoke(app, ["wizard"])

        assert result.exit_code == 0
        assert len(self.mock_config.content_sources) == 0  # Sources cleared
        self.mock_config_manager.reset_to_defaults.assert_called_once()


@pytest.mark.cli
class TestSetupHelperFunctions:
    """Test setup helper functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock config
        self.mock_config = ContentConfiguration()
        self.mock_config.cache_dir = self.temp_dir / "cache"
        self.mock_config.config_dir = self.temp_dir / "config"
        self.mock_config.content_sources = []

        # Create mock config manager
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_config.return_value = self.mock_config
        self.mock_config_manager.reset_to_defaults.return_value = self.mock_config
        self.mock_config_manager.update_config = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("dnd5e.cli.commands.setup.console")
    def test_setup_defaults(self, mock_console):
        """Test _setup_defaults function."""
        from dnd5e.cli.commands.setup import _setup_defaults

        # Add a test source to the config that reset_to_defaults returns
        test_source = ContentSource(
            name="srd", type=SourceType.DIRECTORY, path=Path("srd-data"), enabled=True
        )
        self.mock_config.content_sources = [test_source]

        _setup_defaults(self.mock_config_manager)

        self.mock_config_manager.reset_to_defaults.assert_called_once()
        mock_console.print.assert_called()

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Confirm")
    def test_setup_custom_with_defaults(self, mock_confirm, mock_console):
        """Test _setup_custom function including defaults."""
        from dnd5e.cli.commands.setup import _setup_custom

        mock_confirm.ask.side_effect = [True, False]  # Include defaults, don't add more

        _setup_custom(self.mock_config_manager)

        # Should have added SRD source
        assert len(self.mock_config.content_sources) == 1
        assert self.mock_config.content_sources[0].name == "srd"
        self.mock_config_manager.update_config.assert_called_once()

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Confirm")
    @patch("dnd5e.cli.commands.setup._add_source_interactive")
    def test_setup_custom_with_additional_sources(
        self, mock_add_source, mock_confirm, mock_console
    ):
        """Test _setup_custom function with additional sources."""
        from dnd5e.cli.commands.setup import _setup_custom

        mock_confirm.ask.side_effect = [
            False,
            True,
            False,
        ]  # No defaults, add source, stop
        mock_add_source.return_value = True

        _setup_custom(self.mock_config_manager)

        mock_add_source.assert_called_once_with(self.mock_config)
        self.mock_config_manager.update_config.assert_called_once()

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_setup_local_valid_directory(self, mock_prompt, mock_console):
        """Test _setup_local function with valid directory."""
        from dnd5e.cli.commands.setup import _setup_local

        # Create test directory
        test_dir = self.temp_dir / "test_content"
        test_dir.mkdir()

        mock_prompt.ask.side_effect = [str(test_dir), "test-local", "done"]

        _setup_local(self.mock_config_manager)

        assert len(self.mock_config.content_sources) == 1
        assert self.mock_config.content_sources[0].name == "test-local"
        assert self.mock_config.content_sources[0].type == SourceType.DIRECTORY
        self.mock_config_manager.update_config.assert_called_once()

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_setup_local_invalid_path(self, mock_prompt, mock_console):
        """Test _setup_local function with invalid path."""
        from dnd5e.cli.commands.setup import _setup_local

        mock_prompt.ask.side_effect = ["/nonexistent/path", "done"]

        _setup_local(self.mock_config_manager)

        assert len(self.mock_config.content_sources) == 0
        # Should not update config since no sources added
        mock_console.print.assert_any_call("[yellow]No sources configured![/yellow]")

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_setup_local_not_directory(self, mock_prompt, mock_console):
        """Test _setup_local function with file instead of directory."""
        from dnd5e.cli.commands.setup import _setup_local

        # Create test file
        test_file = self.temp_dir / "test_file.txt"
        test_file.write_text("test")

        mock_prompt.ask.side_effect = [str(test_file), "done"]

        _setup_local(self.mock_config_manager)

        assert len(self.mock_config.content_sources) == 0
        # Check that error was printed, but be flexible about path format
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any(
            "[red]Error:[/red] Path is not a directory:" in str(call) for call in calls
        )

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_github_success(self, mock_prompt, mock_console):
        """Test _add_source_interactive function with GitHub source."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        mock_prompt.ask.side_effect = [
            "test-github",  # name
            "github",  # type
            "https://github.com/test/repo.git",  # url
            "main",  # branch
        ]

        result = _add_source_interactive(self.mock_config)

        assert result is True
        assert len(self.mock_config.content_sources) == 1
        source = self.mock_config.content_sources[0]
        assert source.name == "test-github"
        assert source.type == SourceType.GITHUB
        assert source.url == "https://github.com/test/repo.git"
        assert source.branch == "main"

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_github_duplicate_name(
        self, mock_prompt, mock_console
    ):
        """Test _add_source_interactive function with duplicate name."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        # Add existing source
        existing_source = ContentSource(
            name="existing",
            type=SourceType.DIRECTORY,
            path=Path("/some/path"),
            enabled=True,
        )
        self.mock_config.content_sources = [existing_source]

        mock_prompt.ask.return_value = "existing"  # Duplicate name

        result = _add_source_interactive(self.mock_config)

        assert result is False
        assert len(self.mock_config.content_sources) == 1  # No new source added
        mock_console.print.assert_any_call(
            "[red]Error:[/red] Source 'existing' already exists"
        )

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_directory_success(self, mock_prompt, mock_console):
        """Test _add_source_interactive function with directory source."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        # Create test directory
        test_dir = self.temp_dir / "test_content"
        test_dir.mkdir()

        mock_prompt.ask.side_effect = [
            "test-dir",  # name
            "directory",  # type
            str(test_dir),  # path
        ]

        result = _add_source_interactive(self.mock_config)

        assert result is True
        assert len(self.mock_config.content_sources) == 1
        source = self.mock_config.content_sources[0]
        assert source.name == "test-dir"
        assert source.type == SourceType.DIRECTORY
        # Compare resolved paths to handle symlink differences
        assert source.path.resolve() == test_dir.resolve()

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_directory_invalid_path(
        self, mock_prompt, mock_console
    ):
        """Test _add_source_interactive function with invalid directory."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        mock_prompt.ask.side_effect = [
            "test-dir",  # name
            "directory",  # type
            "/nonexistent/path",  # invalid path
        ]

        result = _add_source_interactive(self.mock_config)

        assert result is False
        assert len(self.mock_config.content_sources) == 0
        mock_console.print.assert_any_call(
            "[red]Error:[/red] Invalid directory: /nonexistent/path"
        )


@pytest.mark.cli
class TestScanContentFunction:
    """Test _scan_content function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock config
        self.mock_config = ContentConfiguration()
        self.mock_config.cache_dir = self.temp_dir / "cache"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("dnd5e.cli.commands.setup.get_content_config")
    @patch("dnd5e.cli.commands.setup.ContentSourceManager")
    @patch("dnd5e.cli.commands.setup.console")
    def test_scan_content_success(
        self, mock_console, mock_manager_class, mock_get_config
    ):
        """Test successful content scan."""
        from dnd5e.cli.commands.setup import _scan_content

        mock_get_config.return_value = self.mock_config

        # Mock source manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_all_sources = AsyncMock()
        mock_manager.build_content_index = AsyncMock()
        mock_manager.get_statistics = Mock(
            return_value={
                "total_files": 42,
                "total_sources": 2,
                "sources": [
                    {"name": "srd", "type": "directory", "file_count": 25},
                    {"name": "custom", "type": "github", "file_count": 17},
                ],
            }
        )

        _scan_content()

        mock_manager.ensure_all_sources.assert_called_once()
        mock_manager.build_content_index.assert_called_once()
        # Check that the downloading message was printed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Downloading and scanning content" in str(call) for call in calls)

    @patch("dnd5e.cli.commands.setup.get_content_config")
    @patch("dnd5e.cli.commands.setup.ContentSourceManager")
    @patch("dnd5e.cli.commands.setup.console")
    def test_scan_content_error(
        self, mock_console, mock_manager_class, mock_get_config
    ):
        """Test content scan with error."""
        from dnd5e.cli.commands.setup import _scan_content

        mock_get_config.return_value = self.mock_config

        # Mock source manager with error
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_all_sources.side_effect = Exception("Network error")

        _scan_content()

        mock_console.print.assert_any_call(
            "[red]❌ Error during scan: Network error[/red]"
        )


@pytest.mark.cli
class TestCheckSetupCommand:
    """Test check setup command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock config
        self.mock_config = ContentConfiguration()
        self.mock_config.cache_dir = self.temp_dir / "cache"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("dnd5e.cli.commands.setup.get_content_config")
    def test_check_setup_no_sources(self, mock_get_config):
        """Test check setup with no sources configured."""
        self.mock_config.content_sources = []
        mock_get_config.return_value = self.mock_config

        result = self.runner.invoke(app, ["check"])

        assert result.exit_code == 1
        assert "No content sources configured" in result.stdout
        assert "5e2pdf setup wizard" in result.stdout

    @patch("dnd5e.cli.commands.setup.get_content_config")
    @patch("dnd5e.cli.commands.setup.ContentSourceManager")
    def test_check_setup_success(self, mock_manager_class, mock_get_config):
        """Test successful setup check."""
        # Add test source
        test_source = ContentSource(
            name="test",
            type=SourceType.DIRECTORY,
            path=Path("/test/path"),
            enabled=True,
        )
        self.mock_config.content_sources = [test_source]
        mock_get_config.return_value = self.mock_config

        # Mock source manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_all_sources = AsyncMock()
        mock_manager.build_content_index = AsyncMock()
        mock_manager.get_statistics = Mock(
            return_value={"total_files": 25, "total_sources": 1}
        )

        result = self.runner.invoke(app, ["check"])

        # Debug output if test fails
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.stdout}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "1 content sources configured" in result.stdout
        assert "25 content files available" in result.stdout

    @patch("dnd5e.cli.commands.setup.get_content_config")
    @patch("dnd5e.cli.commands.setup.ContentSourceManager")
    def test_check_setup_error(self, mock_manager_class, mock_get_config):
        """Test setup check with error."""
        # Add test source
        test_source = ContentSource(
            name="test",
            type=SourceType.DIRECTORY,
            path=Path("/test/path"),
            enabled=True,
        )
        self.mock_config.content_sources = [test_source]
        mock_get_config.return_value = self.mock_config

        # Mock source manager with error
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_all_sources.side_effect = Exception("Source error")

        result = self.runner.invoke(app, ["check"])

        assert result.exit_code == 1
        assert "Setup check failed: Source error" in result.stdout
        assert "5e2pdf setup wizard" in result.stdout


@pytest.mark.cli
class TestResetSetupCommand:
    """Test reset setup command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.mock_config_manager = Mock()

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    def test_reset_setup_confirmed(self, mock_confirm, mock_get_manager):
        """Test reset setup when user confirms."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_confirm.ask.return_value = True

        result = self.runner.invoke(app, ["reset"])

        assert result.exit_code == 0
        assert "Configuration reset to defaults" in result.stdout
        assert "5e2pdf sources scan" in result.stdout
        self.mock_config_manager.reset_to_defaults.assert_called_once()

    @patch("dnd5e.cli.commands.setup.get_config_manager")
    @patch("dnd5e.cli.commands.setup.Confirm")
    def test_reset_setup_cancelled(self, mock_confirm, mock_get_manager):
        """Test reset setup when user cancels."""
        mock_get_manager.return_value = self.mock_config_manager
        mock_confirm.ask.return_value = False

        result = self.runner.invoke(app, ["reset"])

        assert result.exit_code == 0
        assert "Reset cancelled" in result.stdout
        self.mock_config_manager.reset_to_defaults.assert_not_called()


@pytest.mark.cli
class TestSetupEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_config = ContentConfiguration()
        self.mock_config.content_sources = []

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_github_validation_error(
        self, mock_prompt, mock_console
    ):
        """Test _add_source_interactive with ContentSource validation error."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        mock_prompt.ask.side_effect = [
            "test-github",  # name
            "github",  # type
            "",  # empty URL (will cause validation error)
            "main",  # branch
        ]

        result = _add_source_interactive(self.mock_config)

        assert result is False
        assert len(self.mock_config.content_sources) == 0
        # Should print error message about validation failure

    @patch("dnd5e.cli.commands.setup.console")
    @patch("dnd5e.cli.commands.setup.Prompt")
    def test_add_source_interactive_directory_validation_error(
        self, mock_prompt, mock_console
    ):
        """Test _add_source_interactive with directory source validation error."""
        from dnd5e.cli.commands.setup import _add_source_interactive

        # Create test file instead of directory
        test_file = self.temp_dir / "test_file.txt"
        test_file.write_text("test")

        # Mock the path validation to make it seem like directory exists initially
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=False),
        ):
            mock_prompt.ask.side_effect = [
                "test-dir",  # name
                "directory",  # type
                str(test_file),  # file path instead of directory
            ]

            result = _add_source_interactive(self.mock_config)

            assert result is False
            assert len(self.mock_config.content_sources) == 0

    def test_setup_local_with_exception_handling(self):
        """Test _setup_local handles exceptions during source addition."""
        from dnd5e.cli.commands.setup import _setup_local

        mock_config_manager = Mock()
        mock_config = Mock()
        mock_config.content_sources = []
        mock_config.add_source.side_effect = ValueError("Invalid source configuration")
        mock_config_manager.get_config.return_value = mock_config

        # Create test directory
        test_dir = self.temp_dir / "test_content"
        test_dir.mkdir()

        with (
            patch("dnd5e.cli.commands.setup.Prompt") as mock_prompt,
            patch("dnd5e.cli.commands.setup.console") as mock_console,
        ):
            mock_prompt.ask.side_effect = [str(test_dir), "test-local", "done"]

            _setup_local(mock_config_manager)

            # Should handle the exception and print error
            mock_console.print.assert_any_call(
                "[red]Error:[/red] Invalid source configuration"
            )
