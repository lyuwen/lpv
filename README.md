# lpv - Line-counting Progress Viewer

[![Unit Tests](https://github.com/lyuwen/lpv/actions/workflows/test.yml/badge.svg)](https://github.com/lyuwen/lpv/actions/workflows/test.yml)

A pipe viewer that counts lines instead of bytes, similar to `pv` but line-oriented.

## Features

- **Known-size mode**: Shows progress bar with percentage, ETA, and throughput when input size is known
- **Stream mode**: Shows line count and throughput for unknown-size streams
- **Flexible output**: Numeric mode for scripting, named progress for multiple streams
- **Efficient**: Binary I/O with chunked processing for high performance

## Installation

### As a standalone script

```bash
chmod +x lpv.py
cp lpv.py /usr/local/bin/lpv
```

### As a pip package

```bash
pip install -e .
```

## Usage

```bash
# Show progress for a file
lpv file.txt

# Stream mode (unknown size)
cat file.txt | lpv

# Stream with known size
cat file.txt | lpv -s 1000

# Numeric output for scripting
lpv -n file.txt

# Named progress
lpv -N "parsing" data.csv | python process.py

# Quiet mode (no progress display)
lpv -q file.txt
```

## Options

```
-s, --size SIZE     Expected total line count (enables progress bar for stdin)
-i, --interval SEC  Update interval in seconds (default: 0.1)
-n, --numeric       Output percentages numerically (for scripting)
-N, --name NAME     Prefix output with NAME
-q, --quiet         No progress display (just passthrough)
-w, --width WIDTH   Terminal width override
-h, --help          Show help
-V, --version       Show version
```

## Examples

### Basic usage

```bash
# Count lines while processing
cat large_file.txt | lpv | grep "pattern" > results.txt
```

### With known size

```bash
# Pre-count lines for progress bar
LINES=$(wc -l < data.txt)
cat data.txt | lpv -s $LINES | process_data.sh
```

### Multiple streams

```bash
# Named progress for clarity
lpv -N "input" data.csv | process.py | lpv -N "output" > results.csv
```

### Scripting

```bash
# Numeric output: lines_processed total_lines percentage rate
lpv -n -s 1000 data.txt | while read lines total pct rate; do
  echo "Progress: $pct% ($lines/$total lines at $rate lines/s)"
done
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=lpv --cov-report=term-missing
```

## Requirements

- Python 3.7+
- No external dependencies for core functionality
- pytest and pytest-cov for testing

## License

MIT
