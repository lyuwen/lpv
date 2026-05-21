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

    def __init__(self, total_lines: Optional[int], interval: float,
                 numeric: bool, name: Optional[str], quiet: bool, width: Optional[int]):
        self.total_lines = total_lines
        self.interval = interval
        self.numeric = numeric
        self.name = name
        self.quiet = quiet
        self.width = width or self._get_terminal_width()
        self.lines_processed = 0
        self.start_time = time.time()
        self.last_update = 0.0
        self.show_progress = sys.stderr.isatty() and not quiet

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

    def _calculate_rate(self, elapsed: float) -> float:
        """Calculate lines per second."""
        if elapsed < 0.001:
            return 0.0
        return self.lines_processed / elapsed

    def _calculate_eta(self, elapsed: float) -> Optional[float]:
        """Calculate estimated time remaining."""
        if not self.total_lines or self.lines_processed == 0:
            return None
        rate = self._calculate_rate(elapsed)
        if rate < 0.001:
            return None
        remaining = self.total_lines - self.lines_processed
        return remaining / rate

    def _render_progress_bar(self, elapsed: float) -> str:
        """Render progress bar for known-size mode."""
        if not self.total_lines:
            return self._render_stream_mode(elapsed)

        percentage = min(100, int(100 * self.lines_processed / self.total_lines))
        rate = self._calculate_rate(elapsed)
        eta = self._calculate_eta(elapsed)

        # Calculate progress bar width
        prefix = f"{self.name}: " if self.name else ""
        suffix = f" {percentage}% | {self.lines_processed}/{self.total_lines} lines | {rate:.0f} lines/s"
        if eta is not None:
            suffix += f" | ETA: {self._format_time(eta)}"

        available_width = self.width - len(prefix) - len(suffix) - 4  # 4 for " [] "
        bar_width = max(10, available_width)

        filled = int(bar_width * self.lines_processed / self.total_lines)
        bar = "=" * filled + ">" + " " * (bar_width - filled - 1)

        return f"{prefix}[{bar}]{suffix}"

    def _render_stream_mode(self, elapsed: float) -> str:
        """Render progress for stream mode (unknown size)."""
        rate = self._calculate_rate(elapsed)
        prefix = f"{self.name}: " if self.name else ""
        return f"{prefix}{self.lines_processed} lines | {rate:.0f} lines/s | elapsed: {self._format_time(elapsed)}"

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

        sys.stderr.write(f"\r{output}")
        sys.stderr.flush()

    def increment(self) -> None:
        """Increment line counter."""
        self.lines_processed += 1

    def finalize(self) -> None:
        """Show final statistics."""
        if not self.show_progress:
            return

        self.update(force=True)
        sys.stderr.write("\n")
        sys.stderr.flush()


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
                        progress.increment()
                        progress.update()
                break

            buffer += chunk
            lines = buffer.split(b'\n')
            buffer = lines[-1]  # Keep incomplete line in buffer

            for line in lines[:-1]:
                output_stream.write(line + b'\n')
                output_stream.flush()
                progress.increment()
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

