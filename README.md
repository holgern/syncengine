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

- **Intelligent Change Detection**

  - Tracks file modifications via timestamps and sizes
  - Detects renames and moves
  - Identifies conflicts when both sides change

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

- **Protocol Agnostic**
  - Works with any storage backend (local, S3, FTP, custom protocols)
  - Pluggable storage interface
  - Easy to extend for new storage types

## Quick Example

```python
from syncengine import SyncEngine, SyncMode, LocalStorageClient, SyncPair

# Create storage clients
source = LocalStorageClient("/path/to/source")
destination = LocalStorageClient("/path/to/destination")

# Create sync engine
engine = SyncEngine(mode=SyncMode.TWO_WAY)

# Create sync pair
pair = SyncPair(
    source_root="/path/to/source",
    destination_root="/path/to/destination",
    source_client=source,
    destination_client=destination
)

# Perform sync
stats = engine.sync_pair(pair)
print(f"Uploaded: {stats['uploads']}, Downloaded: {stats['downloads']}")
```

## When to Use Each Sync Mode

| Mode                    | Use Case                     | Source Changes    | Destination Changes | Deletions                 |
| ----------------------- | ---------------------------- | ----------------- | ------------------- | ------------------------- |
| `TWO_WAY`               | Keep both sides in sync      | Upload            | Download            | Propagated both ways      |
| `SOURCE_TO_DESTINATION` | Mirror source to destination | Upload            | Ignored (deleted)   | Propagated to destination |
| `SOURCE_BACKUP`         | Backup source, never delete  | Upload            | Download            | Never delete source       |
| `DESTINATION_TO_SOURCE` | Mirror destination to source | Ignored (deleted) | Download            | Propagated to source      |
| `DESTINATION_BACKUP`    | Backup from destination      | Ignored           | Download            | Never delete local backup |

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

For detailed API documentation, see the individual module docstrings:

- `syncengine/engine.py` - Main sync engine
- `syncengine/modes.py` - Sync mode definitions
- `syncengine/comparator.py` - Change detection logic
- `syncengine/protocols.py` - Storage protocol interfaces
- `syncengine/config.py` - Configuration options

## Contributing

Contributions are welcome! Please ensure:

- Tests pass: `pytest tests/`
- Benchmarks pass: `python benchmarks/run_benchmarks.py`
- Code follows project style

## License

See LICENSE file for details.
