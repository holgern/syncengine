# Syncengine Benchmarks

This directory contains benchmark scripts for testing and validating the behavior of all
5 sync modes in the syncengine library.

## Overview

The benchmark suite tests all sync modes using local filesystem operations, simulating
cloud storage with a local directory. This allows for fast, repeatable testing without
requiring actual cloud storage access.

## Files

### Core Scripts

- **`run_benchmarks.py`** - Main benchmark runner that executes all benchmarks and
  reports results
- **`test_utils.py`** - Shared utilities and mock classes used across all benchmarks

### Individual Mode Benchmarks

- **`benchmark_two_way.py`** - Tests TWO_WAY sync mode (bidirectional mirroring)
- **`benchmark_source_to_destination.py`** - Tests SOURCE_TO_DESTINATION mode
  (unidirectional upload with deletes)
- **`benchmark_source_backup.py`** - Tests SOURCE_BACKUP mode (upload only, no deletes)
- **`benchmark_destination_to_source.py`** - Tests DESTINATION_TO_SOURCE mode
  (unidirectional download with deletes)
- **`benchmark_destination_backup.py`** - Tests DESTINATION_BACKUP mode (download only,
  no deletes)

### Combined Benchmark

- **`benchmark_sync_modes.py`** - Legacy script that runs all 5 modes together in one
  test

## Sync Modes

### 1. TWO_WAY

Mirror every action in both directions. Changes from source are uploaded to destination,
and changes from destination are downloaded to source. Both deletions and additions are
synchronized bidirectionally.

**Initial Sync Preferences**: The TWO_WAY benchmark also demonstrates the three initial
sync preferences for first-time sync scenarios:

- **MERGE** (default): Merges both sides without deletions - safest option
- **SOURCE_WINS**: Treats source as authoritative, deletes destination-only files
- **DESTINATION_WINS**: Treats destination as authoritative, deletes source-only files

### 2. SOURCE_TO_DESTINATION

Mirror source actions to destination, including deletions. Destination changes are
ignored and never propagated back to source.

### 3. SOURCE_BACKUP

Only upload data to the destination. Never delete anything or act on destination
changes. Ideal for backup scenarios where you want to preserve everything that was ever
uploaded.

### 4. DESTINATION_TO_SOURCE

Mirror destination actions to source, including deletions. Source changes are ignored
and never propagated to destination.

### 5. DESTINATION_BACKUP

Only download data from the destination. Never delete anything at source or act on
source changes. Ideal for downloading backups where you want to preserve everything
locally.

## Usage

### Run All Benchmarks

```bash
python3 benchmarks/run_benchmarks.py
```

### Run Specific Benchmark

```bash
python3 benchmarks/run_benchmarks.py -b two_way
python3 benchmarks/run_benchmarks.py -b source_backup
python3 benchmarks/run_benchmarks.py -b destination_to_source
```

### Run with Verbose Output

```bash
python3 benchmarks/run_benchmarks.py -v
python3 benchmarks/run_benchmarks.py -b source_backup -v
```

### Run Individual Benchmark Directly

```bash
python3 benchmarks/benchmark_two_way.py
python3 benchmarks/benchmark_source_backup.py
```

## Benchmark Runner Features

The `run_benchmarks.py` script provides:

- **Auto-discovery**: Automatically finds all benchmark scripts
- **Error detection**: Captures and reports failures with context
- **Timing**: Measures execution time for each benchmark
- **Summary report**: Provides overview of passed/failed benchmarks
- **Verbose mode**: Shows full output from benchmarks when needed
- **Exit codes**: Returns 0 on success, 1 on failure (useful for CI/CD)

## Test Infrastructure

The `test_utils.py` module provides mock implementations that simulate cloud storage:

### Classes

- **`LocalFileEntry`**: Represents a file entry (simulates cloud file metadata)
- **`LocalStorageClient`**: Mock cloud storage client using local filesystem
- **`LocalEntriesManager`**: Manager for file entries in mock storage

### Helper Functions

- **`create_entries_manager_factory()`**: Factory for creating entries managers
- **`create_test_files()`**: Creates test files with random content
- **`count_files()`**: Counts files in a directory (excluding trash)

## Example Output

```
================================================================================
SYNCENGINE BENCHMARK RUNNER
================================================================================

Discovered 6 benchmark(s)
--------------------------------------------------------------------------------
✓ Destination Backup                       [0.13s] PASS
✓ Destination To Source                    [0.11s] PASS
✓ Source Backup                            [0.10s] PASS
✓ Source To Destination                    [0.10s] PASS
✓ Two Way                                  [0.11s] PASS
✓ Sync Modes                               [0.11s] PASS

================================================================================
BENCHMARK SUMMARY
================================================================================

Total benchmarks: 6
Passed: 6
Failed: 0
Total time: 0.66s

================================================================================
[SUCCESS] All benchmarks passed!
================================================================================
```

## Adding New Benchmarks

To add a new benchmark:

1. Create a new file `benchmark_<name>.py` in this directory
2. Import utilities from `test_utils`:
   ```python
   from benchmarks.test_utils import (
       LocalStorageClient,
       create_entries_manager_factory,
       create_test_files,
       count_files,
   )
   ```
3. Implement your benchmark function
4. Use `sys.exit(0)` for success, `sys.exit(1)` for failure
5. The benchmark runner will automatically discover and run it

## Notes

- All benchmarks use temporary directories that are automatically cleaned up
- Benchmarks are designed to be deterministic and repeatable
- The mock storage client simulates common cloud storage operations
- Each benchmark validates expected behavior with assertions
- Timing information helps identify performance regressions
