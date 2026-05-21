#!/usr/bin/env python3
"""
Unit tests for lpv that import the module directly for coverage.
"""

import sys
import io
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import lpv
sys.path.insert(0, str(Path(__file__).parent.parent))

import lpv


class TestProgressDisplay:
    """Test ProgressDisplay class."""

    def test_init_with_total_lines(self):
        """Test initialization with known total lines."""
        progress = lpv.ProgressDisplay(
            total_lines=100,
            interval=0.1,
            numeric=False,
            name=None,
            quiet=False,
            width=80
        )
        assert progress.total_lines == 100
        assert progress.interval == 0.1
        assert progress.lines_processed == 0

    def test_init_without_total_lines(self):
        """Test initialization for stream mode."""
        progress = lpv.ProgressDisplay(
            total_lines=None,
            interval=0.1,
            numeric=False,
            name=None,
            quiet=False,
            width=80
        )
        assert progress.total_lines is None

    def test_increment(self):
        """Test line counter increment."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        assert progress.lines_processed == 0
        progress.increment()
        assert progress.lines_processed == 1
        progress.increment()
        assert progress.lines_processed == 2

    def test_format_time(self):
        """Test time formatting."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        assert progress._format_time(45) == "0:45"
        assert progress._format_time(125) == "2:05"
        assert progress._format_time(3665) == "1:01:05"

    def test_calculate_rate(self):
        """Test rate calculation."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.lines_processed = 100
        rate = progress._calculate_rate(10.0)
        assert rate == 10.0

    def test_calculate_rate_zero_elapsed(self):
        """Test rate calculation with zero elapsed time."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.lines_processed = 100
        rate = progress._calculate_rate(0.0)
        assert rate == 0.0

    def test_calculate_eta(self):
        """Test ETA calculation."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.lines_processed = 50
        eta = progress._calculate_eta(10.0)
        assert eta == 10.0  # 50 lines remaining at 5 lines/s = 10s

    def test_calculate_eta_no_total(self):
        """Test ETA calculation without total lines."""
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)
        progress.lines_processed = 50
        eta = progress._calculate_eta(10.0)
        assert eta is None

    def test_render_progress_bar(self):
        """Test progress bar rendering."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.lines_processed = 50
        output = progress._render_progress_bar(10.0)
        assert "50%" in output
        assert "50/100" in output
        assert "lines/s" in output

    def test_render_stream_mode(self):
        """Test stream mode rendering."""
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)
        progress.lines_processed = 42
        output = progress._render_stream_mode(10.0)
        assert "42 lines" in output
        assert "lines/s" in output
        assert "elapsed:" in output

    def test_render_numeric(self):
        """Test numeric output rendering."""
        progress = lpv.ProgressDisplay(100, 0.1, True, None, True, 80)
        progress.lines_processed = 50
        output = progress._render_numeric(10.0)
        parts = output.split()
        assert parts[0] == "50"  # lines processed
        assert parts[1] == "100"  # total lines
        assert parts[2] == "50"  # percentage

    def test_render_numeric_stream_mode(self):
        """Test numeric output in stream mode."""
        progress = lpv.ProgressDisplay(None, 0.1, True, None, True, 80)
        progress.lines_processed = 42
        output = progress._render_numeric(10.0)
        parts = output.split()
        assert parts[0] == "42"  # lines processed

    def test_name_prefix(self):
        """Test name prefix in output."""
        progress = lpv.ProgressDisplay(None, 0.1, False, "test", True, 80)
        progress.lines_processed = 10
        output = progress._render_stream_mode(1.0)
        assert output.startswith("test:")


class TestCountLinesInFile:
    """Test count_lines_in_file function."""

    def test_count_lines_normal_file(self):
        """Test counting lines in a normal file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name

        try:
            count = lpv.count_lines_in_file(temp_file)
            assert count == 3
        finally:
            os.unlink(temp_file)

    def test_count_lines_empty_file(self):
        """Test counting lines in empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name

        try:
            count = lpv.count_lines_in_file(temp_file)
            assert count == 0
        finally:
            os.unlink(temp_file)

    def test_count_lines_no_trailing_newline(self):
        """Test counting lines without trailing newline."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3")
            temp_file = f.name

        try:
            count = lpv.count_lines_in_file(temp_file)
            assert count == 2  # Only 2 newlines
        finally:
            os.unlink(temp_file)

    def test_count_lines_nonexistent_file(self):
        """Test counting lines in nonexistent file."""
        count = lpv.count_lines_in_file("/nonexistent/file.txt")
        assert count is None


class TestProcessStream:
    """Test process_stream function."""

    def test_process_stream_basic(self):
        """Test basic stream processing."""
        input_data = b"line1\nline2\nline3\n"
        input_stream = io.BytesIO(input_data)
        output_stream = io.BytesIO()
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)

        lpv.process_stream(input_stream, output_stream, progress)

        assert output_stream.getvalue() == input_data
        assert progress.lines_processed == 3

    def test_process_stream_empty(self):
        """Test processing empty stream."""
        input_stream = io.BytesIO(b"")
        output_stream = io.BytesIO()
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)

        lpv.process_stream(input_stream, output_stream, progress)

        assert output_stream.getvalue() == b""
        assert progress.lines_processed == 0

    def test_process_stream_no_trailing_newline(self):
        """Test processing stream without trailing newline."""
        input_data = b"line1\nline2\nline3"
        input_stream = io.BytesIO(input_data)
        output_stream = io.BytesIO()
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)

        lpv.process_stream(input_stream, output_stream, progress)

        assert output_stream.getvalue() == input_data
        assert progress.lines_processed == 3  # 2 newlines + final buffer

    def test_process_stream_binary_data(self):
        """Test processing binary data."""
        input_data = b"\x00\x01\x02\n\xff\xfe\xfd\n"
        input_stream = io.BytesIO(input_data)
        output_stream = io.BytesIO()
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)

        lpv.process_stream(input_stream, output_stream, progress)

        assert output_stream.getvalue() == input_data
        assert progress.lines_processed == 2

    def test_process_stream_large_lines(self):
        """Test processing stream with large lines."""
        # Create a line larger than the chunk size (4096)
        large_line = b"x" * 10000 + b"\n"
        input_stream = io.BytesIO(large_line)
        output_stream = io.BytesIO()
        progress = lpv.ProgressDisplay(None, 0.1, False, None, True, 80)

        lpv.process_stream(input_stream, output_stream, progress)

        assert output_stream.getvalue() == large_line
        assert progress.lines_processed == 1


class TestProgressDisplayUpdate:
    """Test ProgressDisplay update method."""

    def test_update_quiet_mode(self):
        """Test update does nothing in quiet mode."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.lines_processed = 50

        # Should not raise any errors
        progress.update()
        progress.update(force=True)

    def test_update_respects_interval(self):
        """Test update respects interval timing."""
        progress = lpv.ProgressDisplay(100, 10.0, False, None, True, 80)
        progress.show_progress = True
        progress.lines_processed = 50

        with patch('sys.stderr.write'):
            with patch('sys.stderr.flush'):
                # First update should happen
                progress.update(force=True)

                # Second update should be skipped (interval not elapsed)
                progress.update(force=False)

    def test_finalize(self):
        """Test finalize method."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, True, 80)
        progress.show_progress = True
        progress.lines_processed = 100

        with patch('sys.stderr.write') as mock_write:
            with patch('sys.stderr.flush'):
                progress.finalize()

        # Should have been called (update + newline)
        assert mock_write.called

    def test_get_terminal_width_fallback(self):
        """Test terminal width fallback."""
        with patch('os.get_terminal_size', side_effect=OSError()):
            progress = lpv.ProgressDisplay(100, 0.1, False, None, False, None)
            assert progress.width == 80

    def test_update_with_progress_bar(self):
        """Test update with progress bar display."""
        progress = lpv.ProgressDisplay(100, 0.1, False, None, False, 80)
        progress.show_progress = True
        progress.lines_processed = 50

        with patch('sys.stderr.write') as mock_write:
            with patch('sys.stderr.flush'):
                progress.update(force=True)

        assert mock_write.called

    def test_update_stream_mode(self):
        """Test update in stream mode."""
        progress = lpv.ProgressDisplay(None, 0.1, False, None, False, 80)
        progress.show_progress = True
        progress.lines_processed = 42

        with patch('sys.stderr.write') as mock_write:
            with patch('sys.stderr.flush'):
                progress.update(force=True)

        assert mock_write.called

    def test_update_numeric_mode(self):
        """Test update in numeric mode."""
        progress = lpv.ProgressDisplay(100, 0.1, True, None, False, 80)
        progress.show_progress = True
        progress.lines_processed = 50

        with patch('sys.stderr.write') as mock_write:
            with patch('sys.stderr.flush'):
                progress.update(force=True)

        assert mock_write.called


class TestMainLogic:
    """Test main function logic paths."""

    def test_file_error_handling(self):
        """Test that file errors are handled properly."""
        # Test with nonexistent file
        with patch('sys.argv', ['lpv', '/nonexistent/file.txt']):
            with patch('sys.stderr.write'):
                result = lpv.main()

        assert result == 1
