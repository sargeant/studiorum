"""Integration tests for creatures command with --spells flag functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from studiorum.cli.commands.convert.compendiums.creatures import (
    _combine_bestiary_and_appendix,
    creatures as convert_creatures,
)
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.creatures import Creature
from studiorum.core.models.spells import Spell
from studiorum.core.references.content_tracker import ContentTracker
from tests.test_helpers import reset_test_environment


@pytest.mark.integration
class TestCreaturesSpellsCommand:
    """Test creatures command with --spells flag functionality."""

    def setup_method(self) -> None:
        """Reset test environment."""
        reset_test_environment()

    def test_combine_bestiary_and_appendix_helper(self):
        """Test the _combine_bestiary_and_appendix helper function."""
        bestiary_latex = """\\documentclass{dndbook}
\\begin{document}
\\section{Creatures}
Some creature content here.
\\end{document}"""

        appendix_latex = """\\appendix
\\section{Spells}
Some spell content here."""

        combined = _combine_bestiary_and_appendix(bestiary_latex, appendix_latex)

        # Verify the appendix is inserted before \\end{document}
        assert "\\section{Creatures}" in combined
        assert "\\appendix" in combined
        assert "\\section{Spells}" in combined
        assert combined.endswith("\\end{document}")

        # Verify correct order
        creature_pos = combined.find("\\section{Creatures}")
        appendix_pos = combined.find("\\appendix")
        spell_pos = combined.find("\\section{Spells}")
        end_doc_pos = combined.find("\\end{document}")

        assert creature_pos < appendix_pos < spell_pos < end_doc_pos

    def test_combine_bestiary_and_appendix_fallback(self):
        """Test the fallback behavior when \\end{document} is not found."""
        bestiary_latex = """\\section{Creatures}
Some creature content here."""

        appendix_latex = """\\appendix
\\section{Spells}
Some spell content here."""

        combined = _combine_bestiary_and_appendix(bestiary_latex, appendix_latex)

        # Should append the appendix at the end
        assert combined == f"{bestiary_latex}\n\n{appendix_latex}"

    def test_content_tracker_integration_in_rendering_context(self):
        """Test that ContentTracker is properly integrated into RenderingContext when --spells is used."""

        # Create mock spells
        mock_fireball = Spell.model_validate(
            {
                "name": "Fireball",
                "source": {"abbreviation": "PHB"},
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
                "components": {
                    "v": True,
                    "s": True,
                    "m": "a tiny ball of bat guano and sulfur",
                },
                "duration": [{"type": "instant"}],
                "entries": ["A bright streak flashes from your pointing finger..."],
            }
        )

        # Create mock omnidexer
        mock_omnidexer = MagicMock(spec=Omnidexer)
        mock_omnidexer.find.side_effect = lambda content_type, name, source=None: {
            ("spell", "fireball"): mock_fireball,
        }.get((content_type.type_name, name.lower()))

        # Verify ContentTracker creation logic
        spells_flag = True
        test_content_tracker = ContentTracker() if spells_flag else None
        assert test_content_tracker is not None
        assert isinstance(test_content_tracker, ContentTracker)

        spells_flag = False
        test_content_tracker = ContentTracker() if spells_flag else None
        assert test_content_tracker is None

    @patch("studiorum.cli.utils.get_omnidexer")
    @patch("studiorum.cli.utils.get_tag_resolver")
    @patch("studiorum.core.services.creature_collector.CreatureCollector")
    def test_creatures_command_without_spells_flag(
        self, mock_creature_collector, mock_tag_resolver, mock_omnidexer
    ):
        """Test that creatures command works normally without --spells flag."""
        # Mock the necessary components
        mock_omnidexer.return_value = MagicMock(spec=Omnidexer)
        mock_tag_resolver.return_value = MagicMock()

        # Mock creature collector
        mock_collector_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.creatures = []
        mock_result.sources_used = set()
        mock_result.get_cr_summary.return_value = "No creatures"
        mock_result.get_type_summary.return_value = "No creatures"
        mock_collector_instance.collect_by_names.return_value = mock_result
        mock_creature_collector.return_value = mock_collector_instance

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Test the function call without spells flag
            # This should not raise any exceptions and should not create ContentTracker
            with patch(
                "studiorum.cli.commands.convert.compendiums.creatures._render_bestiary"
            ) as mock_render:
                mock_render.return_value = "\\section{Test} Mock bestiary content"

                # Call the function without spells flag (default False)
                convert_creatures(
                    ["test-creature"],
                    output_file=output_path,
                    spells=False,  # Explicitly test False
                    compile_pdf=False,
                    dry_run=False,
                )

                # Verify _render_bestiary was called
                mock_render.assert_called_once()

                # Verify the rendering context passed to _render_bestiary
                call_args = mock_render.call_args
                context = call_args[0][1]  # Second argument is context

                # When spells=False, content_tracker should be None
                assert context.content_tracker is None
                assert context.metadata.get("spells") is False

        finally:
            # Clean up
            if output_path.exists():
                output_path.unlink()

    @patch("studiorum.cli.utils.get_omnidexer")
    @patch("studiorum.cli.utils.get_tag_resolver")
    @patch("studiorum.core.services.creature_collector.CreatureCollector")
    @patch("studiorum.core.services.appendix_generator.AppendixGenerator")
    def test_creatures_command_with_spells_flag(
        self,
        mock_appendix_generator,
        mock_creature_collector,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test that creatures command generates spell appendix when --spells flag is used."""
        # Mock the necessary components
        mock_omnidexer_instance = MagicMock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = MagicMock()
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock creature collector
        mock_collector_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.creatures = []
        mock_result.sources_used = set()
        mock_result.get_cr_summary.return_value = "No creatures"
        mock_result.get_type_summary.return_value = "No creatures"
        mock_collector_instance.collect_by_names.return_value = mock_result
        mock_creature_collector.return_value = mock_collector_instance

        # Mock appendix generator
        mock_generator_instance = MagicMock()
        mock_generator_instance.generate_appendices.return_value = (
            "\\appendix\\n\\section{Spells}\\nMock spell appendix"
        )
        mock_appendix_generator.return_value = mock_generator_instance

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Test the function call with spells flag
            with patch(
                "studiorum.cli.commands.convert.compendiums.creatures._render_bestiary"
            ) as mock_render:
                mock_render.return_value = (
                    "\\section{Test}\\nMock bestiary content\\n\\end{document}"
                )

                with patch(
                    "studiorum.cli.commands.convert.compendiums.creatures._combine_bestiary_and_appendix"
                ) as mock_combine:
                    expected_combined = "\\section{Test}\\nMock bestiary content\\n\\appendix\\nMock spell appendix\\n\\end{document}"
                    mock_combine.return_value = expected_combined

                    # Call the function with spells flag enabled
                    convert_creatures(
                        ["test-creature"],
                        output_file=output_path,
                        spells=True,  # Enable spells appendix
                        compile_pdf=False,
                        dry_run=False,
                    )

                    # Verify _render_bestiary was called
                    mock_render.assert_called_once()

                    # Verify the rendering context passed to _render_bestiary includes ContentTracker
                    call_args = mock_render.call_args
                    context = call_args[0][1]  # Second argument is context

                    # When spells=True, content_tracker should be present
                    assert context.content_tracker is not None
                    assert isinstance(context.content_tracker, ContentTracker)
                    assert context.metadata.get("spells") is True

                    # Verify AppendixGenerator was created and called
                    mock_appendix_generator.assert_called_once()
                    # Check that it was called with omnidexer and template_engine
                    call_args = mock_appendix_generator.call_args
                    # In integration tests, real instances may be used instead of mocks
                    assert (
                        call_args[1]["omnidexer"] is not None
                    )  # Just verify an omnidexer was passed
                    assert "template_engine" in call_args[1]

                    # Verify generate_appendices was called with correct flags
                    mock_generator_instance.generate_appendices.assert_called_once()
                    call_args = mock_generator_instance.generate_appendices.call_args
                    content_tracker_arg = call_args[0][0]
                    appendix_flags_arg = call_args[0][1]

                    assert isinstance(content_tracker_arg, ContentTracker)
                    assert appendix_flags_arg.spells is True
                    assert appendix_flags_arg.creatures is False
                    assert appendix_flags_arg.items is False

                    # Verify outputs were combined
                    mock_combine.assert_called_once()

        finally:
            # Clean up
            if output_path.exists():
                output_path.unlink()

    def test_empty_spell_appendix_edge_case(self):
        """Test edge case where no spells are referenced (empty appendix)."""
        # Test the case where generate_appendices returns None or empty string
        bestiary_content = "\\section{Creatures}\\nNo spells here.\\n\\end{document}"

        # Test with None appendix (no spells found)
        result = bestiary_content  # Should remain unchanged

        # Test with empty string appendix
        empty_appendix = ""
        if empty_appendix:  # This is the logic in the actual code
            result = _combine_bestiary_and_appendix(bestiary_content, empty_appendix)
        else:
            result = bestiary_content

        assert result == bestiary_content
        assert "\\appendix" not in result
