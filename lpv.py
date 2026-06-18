#!/usr/bin/env python3
"""
lpv - Line-counting Progress Viewer
A pipe viewer that counts lines instead of bytes.
"""

import sys
import os
import argparse
import time
import signal
from typing import Optional, BinaryIO


__version__ = "0.1.0"


class ProgressDisplay:
    """Handles progress display on stderr."""

    # ANSI escape codes for cursor control
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'

    def __init__(self, total_lines: Optional[int], interval: float,
                 numeric: bool, name: Optional[str], quiet: bool, width: Optional[int]):
        self.total_lines = total_lines
        self.interval = interval
        self.numeric = numeric
        self.name = name
        self.quiet = quiet
        self.width = width or self._get_terminal_width()
        self.lines_processed = 0
        self.bytes_processed = 0
        self.start_time = time.time()
        self.last_update = 0.0
        self.show_progress = sys.stderr.isatty() and not quiet
        # Calculate max width needed for line count display
        # Allow for up to 10 digits if unknown, or actual digit count + 1
        self.max_lines_width = len(str(total_lines)) if total_lines else 10
        # Track the actual max width seen to handle overflow
        self._seen_max_lines_width = self.max_lines_width

    def _get_terminal_width(self) -> int:
        """Get terminal width, default to 80."""
        try:
            return os.get_terminal_size(sys.stderr.fileno()).columns
        except (OSError, AttributeError):
            return 80

    def _format_time(self, seconds: float) -> str:
        """Format seconds as H:MM:SS or M:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes as human-readable size with fixed width."""
        size = float(bytes_count)
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if size < 1024.0:
                if unit == 'B':
                    return f"{size:5.0f}{unit:>3}"
                return f"{size:5.1f}{unit:>3}"
            size /= 1024.0
        return f"{size:5.1f}PiB"

    def _format_rate(self, bytes_per_sec: float) -> str:
        """Format byte rate as human-readable throughput with fixed width."""
        for unit in ['B/s', 'KiB/s', 'MiB/s', 'GiB/s', 'TiB/s']:
            if bytes_per_sec < 1024.0:
                if unit == 'B/s':
                    return f"{bytes_per_sec:5.0f}{unit:>5}"
                return f"{bytes_per_sec:5.1f}{unit:>5}"
            bytes_per_sec /= 1024.0
        return f"{bytes_per_sec:5.1f}PiB/s"

    def _calculate_rate(self, elapsed: float) -> float:
        """Calculate lines per second."""
        if elapsed < 0.001:
            return 0.0
        return self.lines_processed / elapsed

    def _calculate_byte_rate(self, elapsed: float) -> float:
        """Calculate bytes per second."""
        if elapsed < 0.001:
            return 0.0
        return self.bytes_processed / elapsed

    def _calculate_eta(self, elapsed: float) -> Optional[float]:
        """Calculate estimated time remaining."""
        if not self.total_lines or self.lines_processed == 0:
            return None
        rate = self._calculate_rate(elapsed)
        if rate < 0.001:
            return None
        remaining = self.total_lines - self.lines_processed
        return remaining / rate

    def _format_number_fixed(self, value: int, width: int) -> str:
        """Format a number with fixed width, handling overflow gracefully."""
        s = str(value)
        if len(s) <= width:
            return s.rjust(width)
        # Update the seen max width for future renders
        self._seen_max_lines_width = max(self._seen_max_lines_width, len(s))
        # If overflow, still right-align but it will expand
        return s.rjust(width)

    def _format_rate_fixed(self, rate: float, width: int = 5) -> str:
        """Format a rate with fixed width, handling overflow gracefully."""
        s = f"{rate:.0f}"
        if len(s) <= width:
            return s.rjust(width)
        # If overflow, use compact notation
        if rate >= 1e6:
            compact = f"{rate/1e6:.1f}M"
            if len(compact) <= width:
                return compact.rjust(width)
        elif rate >= 1e3:
            compact = f"{rate/1e3:.1f}K"
            if len(compact) <= width:
                return compact.rjust(width)
        # Last resort: show as-is (will exceed width)
        return s.rjust(width)

    def _render_progress_bar(self, elapsed: float) -> str:
        """Render progress bar for known-size mode."""
        if not self.total_lines:
            return self._render_stream_mode(elapsed)

        percentage = min(100, int(100 * self.lines_processed / self.total_lines))
        rate = self._calculate_rate(elapsed)
        byte_rate = self._calculate_byte_rate(elapsed)

        prefix = f"{self.name}: " if self.name else ""

        # Build status parts with fixed-width fields using overflow-safe helpers
        lines_str = self._format_number_fixed(self.lines_processed, self.max_lines_width)
        rate_str = self._format_rate_fixed(rate, 5)
        time_str = self._format_time(elapsed)
        bytes_str = self._format_bytes(self.bytes_processed)
        rate_bytes_str = self._format_rate(byte_rate)

        # Format: "N lines R/s T | B [R] [====>  ] P%"
        # More compact: combine rates with their values
        stats = f"{lines_str} {rate_str}/s {time_str}"
        byte_info = f"{bytes_str} [{rate_bytes_str}]"
        bar_suffix = f" {percentage:3d}%"

        # Calculate available width for progress bar
        prefix_len = len(prefix)
        stats_len = len(stats)
        byte_info_len = len(byte_info)
        bar_suffix_len = len(bar_suffix)

        # Format: "{prefix}{stats} | {byte_info} [{bar}]{bar_suffix}"
        status_line_len = prefix_len + stats_len + 3 + byte_info_len + 3 + bar_suffix_len  # " | ", " [" and "]"
        available_for_bar = self.width - status_line_len

        if available_for_bar < 10:
            # Not enough space for bar, show compact format
            compact = f"{prefix}{lines_str} {rate_str}/s {time_str} | {bytes_str} {percentage:3d}%"
            if len(compact) <= self.width:
                return compact
            # Ultra-compact if still too long
            return f"{prefix}{lines_str} {bytes_str} {percentage:3d}%"

        # Render progress bar
        filled = int(available_for_bar * self.lines_processed / self.total_lines)
        bar = "=" * filled + ">" + " " * (available_for_bar - filled - 1)

        result = f"{prefix}{stats} | {byte_info} [{bar}]{bar_suffix}"

        # Ensure we don't exceed width
        if len(result) > self.width:
            result = result[:self.width]

        return result

    def _render_stream_mode(self, elapsed: float) -> str:
        """Render progress for stream mode (unknown size)."""
        rate = self._calculate_rate(elapsed)
        byte_rate = self._calculate_byte_rate(elapsed)
        prefix = f"{self.name}: " if self.name else ""

        # Build the status line with proper spacing and fixed-width fields using overflow-safe helpers
        lines_str = self._format_number_fixed(self.lines_processed, 10)
        rate_str = self._format_rate_fixed(rate, 6)
        parts = [
            f"{lines_str} lines",
            f"{rate_str} lines/s",
            f"elapsed: {self._format_time(elapsed)}",
            f"{self._format_bytes(self.bytes_processed)}",
            f"{self._format_time(elapsed)}",
            f"[{self._format_rate(byte_rate)}]"
        ]

        status = f"{prefix}{' | '.join(parts[:3])}    {' '.join(parts[3:])}"

        # Truncate if too long
        if len(status) > self.width:
            # Try without byte details first
            status = f"{prefix}{lines_str} lines | {rate_str} lines/s | {self._format_time(elapsed)} | {self._format_bytes(self.bytes_processed)}"
            if len(status) > self.width:
                # Minimal format
                status = f"{prefix}{lines_str} lines | {self._format_bytes(self.bytes_processed)}"
                if len(status) > self.width:
                    status = status[:self.width]

        return status

    def _render_numeric(self, elapsed: float) -> str:
        """Render numeric output for scripting."""
        rate = self._calculate_rate(elapsed)
        if self.total_lines:
            percentage = min(100, int(100 * self.lines_processed / self.total_lines))
            return f"{self.lines_processed} {self.total_lines} {percentage} {rate:.2f}"
        return f"{self.lines_processed} {rate:.2f}"

    def update(self, force: bool = False) -> None:
        """Update progress display if enough time has passed."""
        if not self.show_progress:
            return

        current_time = time.time()
        if not force and (current_time - self.last_update) < self.interval:
            return

        self.last_update = current_time
        elapsed = current_time - self.start_time

        if self.numeric:
            output = self._render_numeric(elapsed)
        elif self.total_lines:
            output = self._render_progress_bar(elapsed)
        else:
            output = self._render_stream_mode(elapsed)

        # Pad output to terminal width to maintain consistent size
        # This prevents display flickering from varying digit counts
        padded_output = output.ljust(self.width)
        sys.stderr.write(f"\r{padded_output}")
        sys.stderr.flush()

    def increment(self, byte_count: int = 0) -> None:
        """Increment line counter and add bytes."""
        self.lines_processed += 1
        self.bytes_processed += byte_count

    def finalize(self) -> None:
        """Show final statistics."""
        if not self.show_progress:
            return

        self.update(force=True)
        # Show cursor again and move to new line
        sys.stderr.write(f"{self.SHOW_CURSOR}\n")
        sys.stderr.flush()

    def show_initial(self) -> None:
        """Show initial progress state before any data arrives."""
        if not self.show_progress:
            return

        # Hide cursor
        sys.stderr.write(self.HIDE_CURSOR)
        sys.stderr.flush()

        # Show initial state with zero values
        elapsed = 0.0

        if self.numeric:
            output = self._render_numeric(elapsed)
        elif self.total_lines:
            output = self._render_progress_bar(elapsed)
        else:
            output = self._render_stream_mode(elapsed)

        # Pad output to terminal width
        padded_output = output.ljust(self.width)
        sys.stderr.write(f"\r{padded_output}")
        sys.stderr.flush()
        self.last_update = time.time()


def count_lines_in_file(filepath: str) -> Optional[int]:
    """Count total lines in a file efficiently."""
    try:
        with open(filepath, 'rb') as f:
            count = 0
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                count += chunk.count(b'\n')
            return count
    except (OSError, IOError):
        return None


def process_stream(input_stream: BinaryIO, output_stream: BinaryIO,
                   progress: ProgressDisplay) -> None:
    """Process input stream line by line, updating progress."""
    try:
        buffer = b''
        while True:
            chunk = input_stream.read(4096)
            if not chunk:
                # Handle any remaining data in buffer
                if buffer:
                    output_stream.write(buffer)
                    if b'\n' in buffer or buffer:
                        progress.increment(len(buffer))
                        progress.update()
                break

            buffer += chunk
            lines = buffer.split(b'\n')
            buffer = lines[-1]  # Keep incomplete line in buffer

            for line in lines[:-1]:
                line_with_newline = line + b'\n'
                output_stream.write(line_with_newline)
                output_stream.flush()
                progress.increment(len(line_with_newline))
                progress.update()

    except BrokenPipeError:
        # Downstream closed, exit gracefully
        pass
    except KeyboardInterrupt:
        # Show final stats on Ctrl+C
        progress.finalize()
        sys.exit(130)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog='lpv',
        description='Line-counting progress viewer - like pv but for lines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lpv file.txt              # Show progress for file
  cat file.txt | lpv        # Stream mode (unknown size)
  cat file.txt | lpv -s 1000  # Stream with known size
  lpv -n file.txt           # Numeric output for scripting
        """
    )

    parser.add_argument('files', nargs='*', metavar='FILE',
                        help='Input files (default: stdin)')
    parser.add_argument('-s', '--size', type=int, metavar='SIZE',
                        help='Expected total line count')
    parser.add_argument('-i', '--interval', type=float, default=0.1, metavar='SEC',
                        help='Update interval in seconds (default: 0.1)')
    parser.add_argument('-n', '--numeric', action='store_true',
                        help='Numeric output for scripting')
    parser.add_argument('-N', '--name', type=str, metavar='NAME',
                        help='Prefix output with NAME')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='No progress display')
    parser.add_argument('-w', '--width', type=int, metavar='WIDTH',
                        help='Terminal width override')
    parser.add_argument('-V', '--version', action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    # Determine total line count
    total_lines = args.size
    if not total_lines and args.files:
        # Try to count lines in files
        total_lines = 0
        for filepath in args.files:
            count = count_lines_in_file(filepath)
            if count is None:
                total_lines = None
                break
            total_lines += count

    # Setup progress display
    progress = ProgressDisplay(
        total_lines=total_lines,
        interval=args.interval,
        numeric=args.numeric,
        name=args.name,
        quiet=args.quiet,
        width=args.width
    )

    # Show initial state before data arrives
    progress.show_initial()

    # Handle SIGPIPE gracefully
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    try:
        if args.files:
            # Process files
            for filepath in args.files:
                try:
                    with open(filepath, 'rb') as f:
                        process_stream(f, sys.stdout.buffer, progress)
                except (OSError, IOError) as e:
                    sys.stderr.write(f"\nlpv: {filepath}: {e}\n")
                    return 1
        else:
            # Process stdin
            process_stream(sys.stdin.buffer, sys.stdout.buffer, progress)

        progress.finalize()
        return 0

    except KeyboardInterrupt:
        progress.finalize()
        return 130


if __name__ == '__main__':
    sys.exit(main())

