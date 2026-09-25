"""Refactored CLI tests with reduced mocking using real test data."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.commands.convert import app
from studiorum.core.result import Success


@pytest.mark.cli
class TestConvertCommandsWithReducedMocking:
    """Test convert commands with minimal mocking and real test data."""

    def setup_method(self):
        """Set up test fixtures."""

        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent.parent.parent.parent / "test-data"

    def test_adventure_conversion_help(self):
        """Test adventure conversion help command without mocking."""
        result = self.runner.invoke(app, ["adventure", "--help"])

        assert result.exit_code == 0
        assert "Convert adventure" in result.stdout

    def test_book_conversion_help(self):
        """Test book conversion help command without mocking."""
        result = self.runner.invoke(app, ["book", "--help"])

        assert result.exit_code == 0
        assert "Convert book" in result.stdout

    def test_supplement_conversion_help(self):
        """Test supplement conversion help command without mocking."""
        result = self.runner.invoke(app, ["supplement", "--help"])

        assert result.exit_code == 0
        assert "Convert supplement" in result.stdout

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.run.build_pdf")
    def test_adventure_conversion_with_real_data_latex_only(
        self,
        mock_build_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test adventure conversion using real test data, only mocking LaTeX compiler."""
        # Mock omnidexer and tag resolver to avoid loading 5etools data in CI
        mock_omnidexer = Mock()
        mock_omnidexer.find = Mock(return_value=None)  # No cross-references found
        mock_omnidexer.get_all_by_type = Mock(return_value=[])
        mock_get_omnidexer.return_value = mock_omnidexer

        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve = Mock(
            side_effect=lambda text, _: text
        )  # Pass through tags unchanged
        mock_get_tag_resolver.return_value = mock_tag_resolver

        # Only mock LaTeX compilation (an external dependency)
        mock_build_pdf.return_value = Success(Path("/tmp/test.pdf"))

        # Mock display manager for clean output

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test LaTeX generation (no PDF) - use absolute paths for CI
            result = self.runner.invoke(
                app,
                ["adventure", str(test_file.absolute()), "--output", str(output_file)],
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX file was created
            assert output_file.exists(), (
                f"Expected LaTeX file {output_file} was not created"
            )

            # Verify LaTeX content contains expected elements
            latex_content = output_file.read_text()
            assert "Test Adventure" in latex_content
            assert "\\documentclass" in latex_content
            assert "\\begin{document}" in latex_content
            assert "\\end{document}" in latex_content

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.run.build_pdf")
    def test_book_conversion_with_real_data_latex_only(
        self,
        mock_build_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test book conversion using real test data, only mocking LaTeX compiler."""
        # Mock omnidexer and tag resolver to avoid loading 5etools data in CI
        mock_omnidexer = Mock()
        mock_omnidexer.find = Mock(return_value=None)  # No cross-references found
        mock_omnidexer.get_all_by_type = Mock(return_value=[])
        mock_get_omnidexer.return_value = mock_omnidexer

        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve = Mock(
            side_effect=lambda text, _: text
        )  # Pass through tags unchanged
        mock_get_tag_resolver.return_value = mock_tag_resolver

        # Only mock LaTeX compilation (an external dependency)
        mock_build_pdf.return_value = Success(Path("/tmp/test.pdf"))

        # Mock display manager for clean output

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "book-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_book.tex"

            # Test LaTeX generation (no PDF) - use absolute paths for CI
            result = self.runner.invoke(
                app, ["book", str(test_file.absolute()), "--output", str(output_file)]
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX file was created
            assert output_file.exists(), (
                f"Expected LaTeX file {output_file} was not created"
            )

            # Verify LaTeX content contains expected elements
            latex_content = output_file.read_text()
            assert "\\documentclass" in latex_content
            assert "\\begin{document}" in latex_content
            assert "\\end{document}" in latex_content

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @pytest.mark.requires_latex
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.run.compile_pdf")
    def test_pdf_compilation_uses_configured_compiler(
        self,
        mock_compile_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test that PDF compilation uses the configured LaTeX compiler."""
        # Mock omnidexer and tag resolver to avoid loading 5etools data in CI
        mock_omnidexer = Mock()
        mock_omnidexer.find = Mock(return_value=None)  # No cross-references found
        mock_omnidexer.get_all_by_type = Mock(return_value=[])
        mock_get_omnidexer.return_value = mock_omnidexer

        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve = Mock(
            side_effect=lambda text, _: text
        )  # Pass through tags unchanged
        mock_get_tag_resolver.return_value = mock_tag_resolver

        # Mock the compile_pdf function to avoid actual LaTeX compilation
        mock_compile_pdf.return_value = None

        # Mock display manager for clean output

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test PDF generation - use absolute paths for CI
            result = self.runner.invoke(
                app,
                [
                    "adventure",
                    str(test_file.absolute()),
                    "--output",
                    str(output_file),
                    "--pdf",
                ],
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify PDF compilation was called
            mock_compile_pdf.assert_called_once()

            # Verify the LaTeX file was created and contains proper content
            assert output_file.exists(), "LaTeX file should be created"
            latex_content = output_file.read_text()
            assert "Test Adventure" in latex_content  # From real test data
            assert "\\documentclass" in latex_content

    def test_invalid_file_path_error_handling(self):
        """Test error handling for invalid file paths without mocking."""
        nonexistent_file = "/path/that/does/not/exist.json"

        result = self.runner.invoke(app, ["adventure", nonexistent_file])

        # Command should fail gracefully
        assert result.exit_code != 0
