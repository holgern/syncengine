[![PyPI - Version](https://img.shields.io/pypi/v/syncengine)](https://pypi.org/project/syncengine/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/syncengine)
![PyPI - Downloads](https://img.shields.io/pypi/dm/syncengine)
[![codecov](https://codecov.io/gh/holgern/syncengine/graph/badge.svg?token=iCHXwbjAXG)](https://codecov.io/gh/holgern/syncengine)

# syncengine

A flexible, bidirectional file synchronization engine for Python that supports multiple
sync modes and conflict resolution strategies.

## What is syncengine?

syncengine is a powerful file synchronization library that enables you to keep files
synchronized between two locations (source and destination). Unlike simple copy
operations, syncengine intelligently tracks file state, detects changes, handles
conflicts, and provides multiple synchronization modes to fit different use cases.

## Why is syncengine useful?

### Real-world Use Cases

1. **Cloud Storage Synchronization**

   - Sync local files with cloud storage (Dropbox, Google Drive, S3, etc.)
   - Implement custom cloud backup solutions
   - Build your own sync client with fine-grained control

2. **Backup Management**

   - Create one-way backup systems (never delete backed-up files)
   - Implement versioned backup strategies
   - Maintain disaster recovery copies

3. **Development Workflows**

   - Sync code between local development and remote servers
   - Mirror files to multiple deployment targets
   - Keep test environments synchronized with production data

4. **Content Distribution**
   - Distribute files from a master source to multiple destinations
   - Keep documentation or assets synchronized across systems
   - Manage multi-site content updates

### Key Features

- **Multiple Sync Modes**: Choose the behavior that fits your needs

  - `TWO_WAY`: Bidirectional sync with conflict detection
  - `SOURCE_TO_DESTINATION`: Mirror source to destination (typical one-way sync)
  - `SOURCE_BACKUP`: Protect source from deletions (upload-only backup)
  - `DESTINATION_TO_SOURCE`: Mirror destination to source (cloud download)
  - `DESTINATION_BACKUP`: Protect local backup from remote changes

- **Intelligent Change Detection** ✨ ENHANCED

  - Multiple comparison modes for different scenarios
  - Tracks file modifications via timestamps and sizes
  - Detects renames and moves
  - Identifies conflicts when both sides change

- **Comparison Modes** ✨ NEW

  - `HASH_THEN_MTIME`: Default - uses hash when available, falls back to mtime
  - `SIZE_ONLY`: For encrypted storage where hash is unavailable
  - `HASH_ONLY`: Strict content verification, ignores timestamps
  - `MTIME_ONLY`: Fast time-based sync without hash computation
  - `SIZE_AND_MTIME`: Balanced approach for reliable systems

- **Flexible Conflict Resolution**

  - Newest file wins
  - Source always wins
  - Destination always wins
  - Manual conflict handling

- **State Management**

  - Persistent state tracking across sync sessions
  - Resume interrupted syncs
  - Detect changes since last sync

- **Pattern-based Filtering**

  - Gitignore-style ignore patterns
  - Include/exclude specific files or directories
  - Control what gets synchronized

- **Progress Tracking** ✨ ENHANCED

  - Real-time file-level progress events for uploads **and downloads**
  - Byte-level transfer progress with speed and ETA
  - Per-folder statistics
  - Thread-safe for parallel operations
  - Rich progress bar support
  - Supports both `sync_pair()` and `download_folder()` methods

- **Force Upload/Download** ✨ NEW

  - Force re-upload/re-download files even when they match
  - Bypass hash/size comparison for replace operations
  - Perfect for duplicate handling and refresh scenarios
  - Works with all sync modes

- **Protocol Agnostic**
  - Works with any storage backend (local, S3, FTP, custom protocols)
  - Pluggable storage interface
  - Easy to extend for new storage types

## Quick Example

```python
from syncengine import SyncEngine, SyncMode, LocalStorageClient, SyncPair
from syncengine.models import ComparisonMode

# Create storage clients
source = LocalStorageClient("/path/to/source")
destination = LocalStorageClient("/path/to/destination")

# Create sync engine
engine = SyncEngine(mode=SyncMode.TWO_WAY)

# Create sync pair with SIZE_ONLY comparison (for encrypted storage)
pair = SyncPair(
    source_root="/path/to/source",
    destination_root="/path/to/destination",
    source_client=source,
    destination_client=destination,
    comparison_mode=ComparisonMode.SIZE_ONLY  # Files considered identical if sizes match
)

# Perform sync
stats = engine.sync_pair(pair)
print(f"Uploaded: {stats['uploads']}, Downloaded: {stats['downloads']}")
```

### Progress Tracking Example

Track upload and download progress in real-time:

```python
from syncengine import SyncProgressTracker, SyncProgressEvent
from pathlib import Path

def progress_callback(info):
    # Track uploads
    if info.event == SyncProgressEvent.UPLOAD_FILE_START:
        print(f"⬆️  Uploading: {info.file_path}")
    elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
        print(f"✓ Uploaded: {info.file_path}")

    # Track downloads
    elif info.event == SyncProgressEvent.DOWNLOAD_FILE_START:
        print(f"⬇️  Downloading: {info.file_path}")
    elif info.event == SyncProgressEvent.DOWNLOAD_FILE_COMPLETE:
        print(f"✓ Downloaded: {info.file_path}")

tracker = SyncProgressTracker(callback=progress_callback)

# Use with sync operations
stats = engine.sync_pair(pair, sync_progress_tracker=tracker)

# Use with folder downloads
stats = engine.download_folder(
    destination_path="/remote/folder",
    local_path=Path("/local/downloads"),
    sync_progress_tracker=tracker
)
```

## When to Use Each Sync Mode

| Mode                    | Use Case                     | Source Changes    | Destination Changes | Deletions                 |
| ----------------------- | ---------------------------- | ----------------- | ------------------- | ------------------------- |
| `TWO_WAY`               | Keep both sides in sync      | Upload            | Download            | Propagated both ways      |
| `SOURCE_TO_DESTINATION` | Mirror source to destination | Upload            | Ignored (deleted)   | Propagated to destination |
| `SOURCE_BACKUP`         | Backup source, never delete  | Upload            | Download            | Never delete source       |
| `DESTINATION_TO_SOURCE` | Mirror destination to source | Ignored (deleted) | Download            | Propagated to source      |
| `DESTINATION_BACKUP`    | Backup from destination      | Ignored           | Download            | Never delete local backup |

## When to Use Each Comparison Mode

Comparison modes control how syncengine determines if files are identical. Choose based
on your storage backend and performance needs:

| Mode              | Use Case                    | How It Works                                     | Best For                               |
| ----------------- | --------------------------- | ------------------------------------------------ | -------------------------------------- |
| `HASH_THEN_MTIME` | Default, balanced           | Compares hash if available, otherwise uses mtime | Most scenarios with reliable storage   |
| `SIZE_ONLY`       | Encrypted/untrusted storage | Only compares file sizes                         | Encrypted vaults, hash unavailable     |
| `HASH_ONLY`       | Strict verification         | Requires hash, ignores mtime                     | Content-critical applications          |
| `MTIME_ONLY`      | Fast sync                   | Only compares timestamps                         | Reliable systems, performance-critical |
| `SIZE_AND_MTIME`  | Balanced without hash       | Compares size AND timestamp                      | Systems without hash support           |

### Important Notes on Comparison Modes

**SIZE_ONLY and HASH_ONLY with TWO_WAY sync:**

- When files differ, these modes **cannot** use mtime to determine which is newer
- In `TWO_WAY` mode, different files result in **CONFLICT**
- In one-way modes (`SOURCE_TO_DESTINATION`, etc.), the sync direction determines which
  file wins
- This is intentional: these modes are chosen when mtime is unreliable

**Example: Encrypted Vault Sync**

```python
from syncengine.models import ComparisonMode, SyncMode

# Vault doesn't provide content hashes and mtime is upload time (not file mtime)
config = SyncConfig(comparison_mode=ComparisonMode.SIZE_ONLY)

# For initial upload, use SOURCE_TO_DESTINATION to avoid conflicts
engine = SyncEngine(mode=SyncMode.SOURCE_TO_DESTINATION)
engine.sync_pair(pair, config=config)

# Files with same size are considered identical, avoiding re-uploads
```

## Installation

```bash
pip install syncengine
```

Or for development:

```bash
git clone https://github.com/holgern/syncengine
cd syncengine
pip install -e .
```

## Benchmarks

The project includes comprehensive benchmarks that test all sync modes with various
scenarios. See [benchmarks/README.md](benchmarks/README.md) for details.

Run benchmarks:

```bash
python benchmarks/run_benchmarks.py
```

## Documentation

Full documentation is available at [Read the Docs](https://syncengine.readthedocs.io):

- [Quickstart Guide](https://syncengine.readthedocs.io/en/latest/quickstart.html) - Get
  started in minutes
- [API Reference](https://syncengine.readthedocs.io/en/latest/api_reference.html) -
  Complete API documentation
- [Examples](https://syncengine.readthedocs.io/en/latest/examples.html) - Real-world
  usage examples
- [Sync Modes](https://syncengine.readthedocs.io/en/latest/sync_modes.html) -
  Understanding sync strategies
- [Changelog](https://syncengine.readthedocs.io/en/latest/changelog.html) - Version
  history and updates

### Key Modules

- `syncengine/engine.py` - Main sync engine with force upload/download support
- `syncengine/modes.py` - Sync mode definitions
- `syncengine/models.py` - Data models including ComparisonMode enum
- `syncengine/progress.py` - Progress tracking API with upload/download event support
- `syncengine/comparator.py` - Change detection with configurable comparison strategies
- `syncengine/protocols.py` - Storage protocol interfaces
- `syncengine/config.py` - Configuration options

## Contributing

Contributions are welcome! Please ensure:

- Tests pass: `pytest tests/`
- Benchmarks pass: `python benchmarks/run_benchmarks.py`
- Code follows project style

## License

See LICENSE file for details.
