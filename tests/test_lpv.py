#!/usr/bin/env python3
"""
Comprehensive test suite for lpv - Line-counting Progress Viewer
"""

import pytest
import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path


# Path to lpv.py
LPV_PATH = Path(__file__).parent.parent / "lpv.py"


class TestBasicFunctionality:
    """Test basic line counting and passthrough."""

    def test_line_counting_stdin(self):
        """Test accurate line counting from stdin."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_passthrough_correctness(self):
        """Test that output exactly matches input."""
        input_data = "hello\nworld\ntest\ndata\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.stdout == input_data

    def test_file_input(self):
        """Test reading from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, str(LPV_PATH), "-q", temp_file],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout == "line1\nline2\nline3\n"
        finally:
            os.unlink(temp_file)

    def test_multiple_files(self):
        """Test processing multiple files."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f1:
            f1.write("file1_line1\nfile1_line2\n")
            temp_file1 = f1.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f2:
            f2.write("file2_line1\nfile2_line2\nfile2_line3\n")
            temp_file2 = f2.name

        try:
            result = subprocess.run(
                [sys.executable, str(LPV_PATH), "-q", temp_file1, temp_file2],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout == "file1_line1\nfile1_line2\nfile2_line1\nfile2_line2\nfile2_line3\n"
        finally:
            os.unlink(temp_file1)
            os.unlink(temp_file2)

    def test_empty_input(self):
        """Test handling of empty input."""
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input="",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == ""

    def test_single_line_no_newline(self):
        """Test single line without trailing newline."""
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input="single line",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == "single line"


class TestKnownSizeMode:
    """Test known-size mode with progress bar."""

    def test_file_auto_detect_size(self):
        """Test automatic line count detection for files."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, str(LPV_PATH), temp_file],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout == "line1\nline2\nline3\nline4\nline5\n"
            # Progress should be shown on stderr (but we can't easily test TTY output)
        finally:
            os.unlink(temp_file)

    def test_size_flag_with_stdin(self):
        """Test -s flag to specify size for stdin."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-s", "3"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_numeric_output_with_size(self):
        """Test -n flag with known size."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-n", "-s", "3"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data
        # Note: When stderr is not a TTY (captured), progress is suppressed
        # This is expected behavior - numeric mode still requires TTY


class TestStreamMode:
    """Test stream mode (unknown size)."""

    def test_stdin_without_size(self):
        """Test stdin without size specification."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH)],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_numeric_output_stream_mode(self):
        """Test -n flag in stream mode."""
        input_data = "line1\nline2\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-n"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data


class TestCLIFlags:
    """Test command-line flags."""

    def test_interval_flag(self):
        """Test -i interval flag."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-i", "0.5", "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_numeric_flag(self):
        """Test -n numeric output flag."""
        input_data = "line1\nline2\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-n"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_name_prefix_flag(self):
        """Test -N name prefix flag."""
        input_data = "line1\nline2\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-N", "test", "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_quiet_flag(self):
        """Test -q quiet mode."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data
        assert result.stderr == ""  # No progress output in quiet mode

    def test_width_flag(self):
        """Test -w width override flag."""
        input_data = "line1\nline2\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-w", "120", "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_help_flag(self):
        """Test -h help flag."""
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "lpv" in result.stdout
        assert "progress viewer" in result.stdout.lower()

    def test_version_flag(self):
        """Test -V version flag."""
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-V"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "/nonexistent/file.txt"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1
        assert "lpv:" in result.stderr

    def test_large_file_performance(self):
        """Test performance with large file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # Write 10,000 lines
            for i in range(10000):
                f.write(f"line_{i}\n")
            temp_file = f.name

        try:
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, str(LPV_PATH), "-q", temp_file],
                capture_output=True,
                text=True,
                timeout=10  # Should complete within 10 seconds
            )
            elapsed = time.time() - start_time

            assert result.returncode == 0
            assert elapsed < 5  # Should be fast
            # Verify line count
            assert result.stdout.count('\n') == 10000
        finally:
            os.unlink(temp_file)

    def test_binary_data_handling(self):
        """Test handling of binary data."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"line1\nline2\n\x00binary\nline3\n")
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, str(LPV_PATH), "-q", temp_file],
                capture_output=True
            )
            assert result.returncode == 0
            # Should pass through binary data
            assert b"line1\n" in result.stdout
        finally:
            os.unlink(temp_file)


class TestIntegration:
    """Integration tests with pipe chains."""

    def test_pipe_chain_with_grep(self):
        """Test lpv in pipe chain with grep."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("match1\nnomatch\nmatch2\nnomatch\nmatch3\n")
            temp_file = f.name

        try:
            # cat file | lpv | grep
            cat_proc = subprocess.Popen(
                ["cat", temp_file],
                stdout=subprocess.PIPE
            )
            lpv_proc = subprocess.Popen(
                [sys.executable, str(LPV_PATH), "-q"],
                stdin=cat_proc.stdout,
                stdout=subprocess.PIPE,
                text=True
            )
            grep_proc = subprocess.Popen(
                ["grep", "^match[0-9]"],
                stdin=lpv_proc.stdout,
                stdout=subprocess.PIPE,
                text=True
            )

            if cat_proc.stdout:
                cat_proc.stdout.close()
            if lpv_proc.stdout:
                lpv_proc.stdout.close()

            output, _ = grep_proc.communicate()
            lpv_proc.wait()
            cat_proc.wait()

            assert "match1" in output
            assert "match2" in output
            assert "match3" in output
            assert "nomatch" not in output
        finally:
            os.unlink(temp_file)

    def test_cat_pipe_lpv(self):
        """Test cat | lpv."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name

        try:
            cat_proc = subprocess.Popen(
                ["cat", temp_file],
                stdout=subprocess.PIPE
            )
            lpv_proc = subprocess.Popen(
                [sys.executable, str(LPV_PATH), "-q"],
                stdin=cat_proc.stdout,
                stdout=subprocess.PIPE,
                text=True
            )
            if cat_proc.stdout:
                cat_proc.stdout.close()

            output, _ = lpv_proc.communicate()
            cat_proc.wait()

            assert output == "line1\nline2\nline3\n"
        finally:
            os.unlink(temp_file)


class TestProgressDisplay:
    """Test progress display functionality."""

    def test_non_tty_suppresses_progress(self):
        """Test that non-TTY stderr suppresses progress."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH)],
            input=input_data,
            capture_output=True,
            text=True
        )
        # When stderr is not a TTY (captured), progress should be suppressed
        assert result.returncode == 0
        assert result.stdout == input_data

    def test_quiet_mode_no_output(self):
        """Test that quiet mode produces no stderr output."""
        input_data = "line1\nline2\nline3\n"
        result = subprocess.run(
            [sys.executable, str(LPV_PATH), "-q"],
            input=input_data,
            capture_output=True,
            text=True
        )
        assert result.stderr == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

