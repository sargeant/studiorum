"""Tests for LaTeX compilation progress tracking."""

import time
from unittest.mock import Mock, patch

import pytest

from dnd5e.renderers.latex.progress_tracker import (
    CompilationProgress,
    NoProgressReporter,
    ProgressTracker,
    SimpleProgressReporter,
)

try:
    from dnd5e.renderers.latex.progress_tracker import RichProgressReporter

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class TestCompilationProgress:
    """Tests for compilation progress tracking."""

    def test_compilation_progress_initialization(self):
        """Test compilation progress initialization."""
        progress = CompilationProgress("lualatex", 3)

        assert progress.engine == "lualatex"
        assert progress.total_passes == 3
        assert progress.current_pass == 0
        assert progress.pass_description == ""
        assert progress.pass_progress == 0.0
        assert progress.pass_status == ""
        assert progress.overall_progress == 0.0
        assert progress.start_time == 0.0

    def test_update_overall_progress(self):
        """Test overall progress calculation."""
        progress = CompilationProgress("lualatex", 4)

        # First pass, 50% complete
        progress.current_pass = 1
        progress.pass_progress = 0.5
        progress.update_overall_progress()

        # Should be 12.5% overall (0 + 0.5/4)
        assert progress.overall_progress == 0.125

        # Second pass, 100% complete
        progress.current_pass = 2
        progress.pass_progress = 1.0
        progress.update_overall_progress()

        # Should be 50% overall (1/4 + 1.0/4)
        assert progress.overall_progress == 0.5

        # Final pass, 100% complete
        progress.current_pass = 4
        progress.pass_progress = 1.0
        progress.update_overall_progress()

        # Should be 100% overall
        assert progress.overall_progress == 1.0

    def test_update_overall_progress_edge_cases(self):
        """Test overall progress calculation edge cases."""
        # Zero passes
        progress = CompilationProgress("lualatex", 0)
        progress.update_overall_progress()
        assert progress.overall_progress == 0.0

        # Progress never exceeds 1.0
        progress = CompilationProgress("lualatex", 1)
        progress.current_pass = 1
        progress.pass_progress = 2.0  # Invalid value
        progress.update_overall_progress()
        assert progress.overall_progress == 1.0


class TestNoProgressReporter:
    """Tests for no-op progress reporter."""

    def test_no_op_methods(self):
        """Test that all methods are no-ops."""
        reporter = NoProgressReporter()

        # Should not raise any exceptions
        reporter.start_compilation("lualatex", 3)
        reporter.start_pass(1, "Initial compilation")
        reporter.update_pass_progress(0.5, "Processing")
        reporter.finish_pass(True, 30.0)
        reporter.finish_compilation(True, 90.0)
        reporter.show_error("Test error")

        # All methods should complete without error
        assert True


class TestSimpleProgressReporter:
    """Tests for simple progress reporter."""

    def test_simple_reporter_workflow(self):
        """Test complete workflow with simple reporter."""
        reporter = SimpleProgressReporter()

        # Should initialize correctly
        assert reporter.current_pass == 0
        assert reporter.total_passes == 0
        assert reporter.start_time == 0.0

        # Test workflow
        with patch("builtins.print") as mock_print:
            reporter.start_compilation("lualatex", 3)
            assert reporter.total_passes == 3
            assert reporter.start_time > 0

            reporter.start_pass(1, "Initial compilation")
            assert reporter.current_pass == 1

            reporter.update_pass_progress(0.5, "Processing")
            # Simple reporter doesn't show sub-pass progress

            reporter.finish_pass(True, 25.0)

            reporter.finish_compilation(True, 75.0)

            # Check that print was called
            assert mock_print.call_count >= 3

            # Check some expected output
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Starting LaTeX compilation" in call for call in print_calls)
            assert any("SUCCESS" in call for call in print_calls)

    def test_simple_reporter_error_display(self):
        """Test error display in simple reporter."""
        reporter = SimpleProgressReporter()

        with patch("builtins.print") as mock_print:
            reporter.show_error("Test error message")

            mock_print.assert_called_once_with("ERROR: Test error message")

    def test_simple_reporter_failure(self):
        """Test failure reporting in simple reporter."""
        reporter = SimpleProgressReporter()

        with patch("builtins.print") as mock_print:
            reporter.start_compilation("lualatex", 2)
            reporter.start_pass(1, "Initial compilation")
            reporter.finish_pass(False, 10.0)
            reporter.finish_compilation(False, 10.0)

            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("✗" in call for call in print_calls)
            assert any("FAILED" in call for call in print_calls)


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestRichProgressReporter:
    """Tests for rich progress reporter."""

    def test_rich_reporter_initialization(self):
        """Test rich reporter initialization."""
        with patch("dnd5e.renderers.latex.progress_tracker.Console"):
            reporter = RichProgressReporter()
            assert reporter.console is not None
            assert reporter.progress is None
            assert reporter.main_task is None
            assert reporter.pass_task is None

    def test_rich_reporter_with_custom_console(self):
        """Test rich reporter with custom console."""
        mock_console = Mock()
        reporter = RichProgressReporter(mock_console)
        assert reporter.console == mock_console

    def test_rich_reporter_workflow(self):
        """Test complete workflow with rich reporter."""
        mock_console = Mock()

        with patch(
            "dnd5e.renderers.latex.progress_tracker.Progress"
        ) as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress

            reporter = RichProgressReporter(mock_console)

            # Test workflow
            reporter.start_compilation("lualatex", 3)
            assert reporter.total_passes == 3
            assert reporter.start_time > 0

            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called()

            reporter.start_pass(1, "Initial compilation")
            assert reporter.current_pass == 1

            reporter.update_pass_progress(0.5, "Processing")
            mock_progress.update.assert_called()

            reporter.finish_pass(True, 25.0)

            reporter.finish_compilation(True, 75.0)
            mock_progress.stop.assert_called_once()

    def test_rich_reporter_error_display(self):
        """Test error display in rich reporter."""
        mock_console = Mock()
        reporter = RichProgressReporter(mock_console)

        reporter.show_error("Test error message")
        mock_console.print.assert_called_once()

        # Check that error formatting is applied
        call_args = mock_console.print.call_args[0][0]
        assert "Error:" in call_args
        assert "Test error message" in call_args

    def test_rich_reporter_unavailable(self):
        """Test rich reporter when rich is not available."""
        with patch("dnd5e.renderers.latex.progress_tracker.RICH_AVAILABLE", False):
            with pytest.raises(ImportError, match="Rich library not available"):
                RichProgressReporter()


class TestProgressTracker:
    """Tests for progress tracker."""

    def test_progress_tracker_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(style="simple")

        assert tracker.style == "simple"
        assert tracker._reporter is not None
        assert isinstance(tracker._reporter, SimpleProgressReporter)

    def test_progress_tracker_none_style(self):
        """Test progress tracker with none style."""
        tracker = ProgressTracker(style="none")

        assert isinstance(tracker._reporter, NoProgressReporter)

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
    def test_progress_tracker_rich_style(self):
        """Test progress tracker with rich style."""
        tracker = ProgressTracker(style="rich")

        assert isinstance(tracker._reporter, RichProgressReporter)

    def test_progress_tracker_rich_fallback(self):
        """Test progress tracker falls back when rich unavailable."""
        with patch("dnd5e.renderers.latex.progress_tracker.RICH_AVAILABLE", False):
            tracker = ProgressTracker(style="rich")

            # Should fall back to no-op reporter
            assert isinstance(tracker._reporter, NoProgressReporter)

    def test_compilation_context_manager(self):
        """Test compilation context manager."""
        tracker = ProgressTracker(style="simple")

        with patch.object(tracker._reporter, "start_compilation") as mock_start:
            with patch.object(tracker._reporter, "finish_compilation") as mock_finish:
                with tracker.compilation("lualatex", 3) as ctx:
                    assert ctx == tracker
                    assert tracker._progress.engine == "lualatex"
                    assert tracker._progress.total_passes == 3
                    assert tracker._progress.start_time > 0

                mock_start.assert_called_once_with("lualatex", 3)
                mock_finish.assert_called_once()

                # Check success parameter
                finish_args = mock_finish.call_args[0]
                assert finish_args[0] is True  # success
                assert finish_args[1] > 0  # duration

    def test_compilation_context_manager_with_exception(self):
        """Test compilation context manager with exception."""
        tracker = ProgressTracker(style="simple")

        with patch.object(tracker._reporter, "start_compilation") as mock_start:
            with patch.object(tracker._reporter, "finish_compilation") as mock_finish:
                with pytest.raises(RuntimeError):
                    with tracker.compilation("lualatex", 3):
                        raise RuntimeError("Test error")

                mock_start.assert_called_once()
                mock_finish.assert_called_once()

    def test_compilation_pass_context_manager(self):
        """Test compilation pass context manager."""
        tracker = ProgressTracker(style="simple")

        # Initialize compilation first
        tracker._progress = CompilationProgress("lualatex", 3)

        with patch.object(tracker._reporter, "start_pass") as mock_start:
            with patch.object(tracker._reporter, "finish_pass") as mock_finish:
                with tracker.compilation_pass(2, "Cross-references") as ctx:
                    assert ctx == tracker
                    assert tracker._progress.current_pass == 2
                    assert tracker._progress.pass_description == "Cross-references"
                    assert tracker._progress.pass_progress == 0.0

                mock_start.assert_called_once_with(2, "Cross-references")
                mock_finish.assert_called_once()

                # Check success parameter
                finish_args = mock_finish.call_args[0]
                assert finish_args[0] is True  # success
                assert finish_args[1] > 0  # duration

    def test_compilation_pass_context_manager_with_exception(self):
        """Test compilation pass context manager with exception."""
        tracker = ProgressTracker(style="simple")
        tracker._progress = CompilationProgress("lualatex", 3)

        with patch.object(tracker._reporter, "start_pass") as mock_start:
            with patch.object(tracker._reporter, "finish_pass") as mock_finish:
                with pytest.raises(RuntimeError):
                    with tracker.compilation_pass(1, "Initial"):
                        raise RuntimeError("Pass failed")

                mock_start.assert_called_once()
                mock_finish.assert_called_once()

                # Check failure parameter
                finish_args = mock_finish.call_args[0]
                assert finish_args[0] is False  # success = False

                # Check that failure flag is set
                assert hasattr(tracker, "_compilation_failed")

    def test_update_progress(self):
        """Test progress update."""
        tracker = ProgressTracker(style="simple")
        tracker._progress = CompilationProgress("lualatex", 3)

        with patch.object(tracker._reporter, "update_pass_progress") as mock_update:
            tracker.update_progress(0.7, "Processing files")

            assert tracker._progress.pass_progress == 0.7
            assert tracker._progress.pass_status == "Processing files"

            mock_update.assert_called_once_with(0.7, "Processing files")

    def test_show_error(self):
        """Test error display."""
        tracker = ProgressTracker(style="simple")

        with patch.object(tracker._reporter, "show_error") as mock_error:
            tracker.show_error("Test error message")

            mock_error.assert_called_once_with("Test error message")

    def test_progress_property(self):
        """Test progress property access."""
        tracker = ProgressTracker(style="simple")

        # Should return the internal progress object
        progress = tracker.progress
        assert isinstance(progress, CompilationProgress)
        assert progress == tracker._progress

    def test_full_workflow_integration(self):
        """Test full workflow integration."""
        tracker = ProgressTracker(style="simple")

        with patch.object(tracker._reporter, "start_compilation"):
            with patch.object(tracker._reporter, "finish_compilation"):
                with patch.object(tracker._reporter, "start_pass"):
                    with patch.object(tracker._reporter, "finish_pass"):
                        with patch.object(tracker._reporter, "update_pass_progress"):
                            # Full workflow
                            with tracker.compilation("lualatex", 2):
                                with tracker.compilation_pass(1, "Initial"):
                                    tracker.update_progress(0.5, "Half done")
                                    tracker.update_progress(1.0, "Complete")

                                with tracker.compilation_pass(2, "Final"):
                                    tracker.update_progress(1.0, "Done")

                            # All methods should have been called
                            assert tracker._reporter.start_compilation.call_count == 1
                            assert tracker._reporter.finish_compilation.call_count == 1
                            assert tracker._reporter.start_pass.call_count == 2
                            assert tracker._reporter.finish_pass.call_count == 2
                            assert (
                                tracker._reporter.update_pass_progress.call_count == 3
                            )
