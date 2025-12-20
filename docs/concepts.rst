Core Concepts
=============

This section covers the fundamental concepts in SyncEngine.

File State and Change Detection
--------------------------------

SyncEngine maintains three views of your files:

1. **Source State**: Current files in the source location
2. **Destination State**: Current files in the destination location
3. **Last Known State**: Files as they were during the last sync

By comparing these three states, SyncEngine can determine what happened to each file:

* **Created**: File exists now but didn't exist in last state
* **Modified**: File exists now with different content than last state
* **Deleted**: File existed in last state but doesn't exist now
* **Renamed/Moved**: File with same content exists at different path
* **Unchanged**: File exists with same content as last state
* **Conflict**: File was modified in both locations since last sync

State Comparison Matrix
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Last State
     - Source
     - Destination
     - Interpretation
   * - None
     - Exists
     - None
     - Created at source
   * - None
     - None
     - Exists
     - Created at destination
   * - Exists
     - Modified
     - Same
     - Modified at source
   * - Exists
     - Same
     - Modified
     - Modified at destination
   * - Exists
     - Modified
     - Modified
     - Conflict (both changed)
   * - Exists
     - None
     - Same
     - Deleted at source
   * - Exists
     - Same
     - None
     - Deleted at destination
   * - Exists
     - None
     - None
     - Deleted both sides

Comparison Modes
----------------

Comparison modes control how SyncEngine determines if two files are identical. This is crucial for
deciding whether to skip a file or sync it.

Available Comparison Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~

SyncEngine provides five comparison modes, each optimized for different scenarios:

**HASH_THEN_MTIME** (Default)

Balanced approach that uses hash when available, falls back to mtime:

.. code-block:: python

   from syncengine.models import ComparisonMode, SyncConfig

   config = SyncConfig(
       comparison_mode=ComparisonMode.HASH_THEN_MTIME
   )

How it works:

1. Compare file sizes first (fast check)
2. If both files have hash values, compare hashes
3. If hash unavailable, compare modification times
4. Files with matching hash are considered identical, even if mtime differs

**SIZE_ONLY**

Only compares file sizes, ignores hash and mtime:

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.SIZE_ONLY
   )

How it works:

1. Files with same size are considered identical
2. Hash and mtime are completely ignored
3. When sizes differ in TWO_WAY mode → CONFLICT (cannot determine newer file)
4. When sizes differ in one-way mode → Uses sync direction

Use cases:

* Encrypted storage where hash is unavailable or unreliable
* Cloud vaults where mtime is upload time, not original file time
* Scenarios where hash computation is too expensive

**HASH_ONLY**

Strict content verification using only hash, ignores size and mtime:

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.HASH_ONLY
   )

How it works:

1. Only compares content hashes
2. Raises error if hash is unavailable
3. When hashes differ in TWO_WAY mode → CONFLICT (cannot determine newer file)
4. When hashes differ in one-way mode → Uses sync direction

Use cases:

* Content-critical applications requiring strict verification
* Systems where mtime is completely unreliable
* Hash is always available and trusted

**MTIME_ONLY**

Fast time-based sync without hash computation:

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.MTIME_ONLY
   )

How it works:

1. Only compares modification times (±2 second tolerance)
2. Ignores file size and hash
3. When mtimes differ → Newer file wins

Use cases:

* Performance-critical scenarios with reliable timestamps
* Large files where hash computation is expensive
* Systems with accurate clock synchronization

**SIZE_AND_MTIME**

Balanced approach for systems without hash support:

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.SIZE_AND_MTIME
   )

How it works:

1. Files must match in BOTH size AND mtime (±2 second tolerance)
2. Hash is completely ignored
3. When files differ → Newer file wins (uses mtime)

Use cases:

* Storage backends that don't provide content hashes
* Reliable systems with accurate timestamps
* Balance between performance and accuracy

Comparison Mode Behavior Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Mode
     - Files Match If
     - Files Differ Direction
     - Best For
   * - HASH_THEN_MTIME
     - Size equal AND (hash equal OR hash unavailable)
     - Uses mtime to determine newer
     - Most scenarios (default)
   * - SIZE_ONLY
     - Size equal
     - TWO_WAY: CONFLICT, One-way: sync direction
     - Encrypted vaults, unreliable mtime
   * - HASH_ONLY
     - Hash equal
     - TWO_WAY: CONFLICT, One-way: sync direction
     - Content-critical, unreliable mtime
   * - MTIME_ONLY
     - Mtime equal (±2s)
     - Uses mtime to determine newer
     - Performance-critical, reliable clocks
   * - SIZE_AND_MTIME
     - Size equal AND mtime equal (±2s)
     - Uses mtime to determine newer
     - No hash support, reliable timestamps

Important: SIZE_ONLY and HASH_ONLY with TWO_WAY Sync
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using ``SIZE_ONLY`` or ``HASH_ONLY`` comparison modes with ``TWO_WAY`` sync mode,
files that differ will result in **CONFLICT** because:

* These modes are chosen specifically when **mtime is unreliable**
* Without reliable mtime, the engine cannot determine which file is newer
* In one-way sync modes, the sync direction determines which file wins

Example: Encrypted Vault Sync
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncEngine
   from syncengine.models import ComparisonMode, SyncConfig
   from syncengine.modes import SyncMode

   # Vault doesn't provide content hashes
   # Vault mtime is upload time, not original file mtime
   config = SyncConfig(
       comparison_mode=ComparisonMode.SIZE_ONLY
   )

   # For initial upload, use SOURCE_TO_DESTINATION
   # This avoids conflicts since sync direction is clear
   engine = SyncEngine(mode=SyncMode.SOURCE_TO_DESTINATION)
   stats = engine.sync_pair(pair, config=config)

   # Files with same size are considered identical
   # No re-uploads on subsequent syncs!

Example: Strict Content Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.HASH_ONLY
   )

   # Requires hash on both sides
   # Ignores timestamps completely
   # Ensures content integrity
   stats = engine.sync_pair(pair, config=config)

Example: Fast Time-Based Sync
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = SyncConfig(
       comparison_mode=ComparisonMode.MTIME_ONLY
   )

   # Skips hash computation for large files
   # Relies on accurate timestamps
   # Much faster for large datasets
   stats = engine.sync_pair(pair, config=config)

Sync Actions
------------

Based on the detected changes and the sync mode, SyncEngine determines which actions to take:

Upload Actions
~~~~~~~~~~~~~~

* ``UPLOAD_NEW``: Upload a new file to destination
* ``UPLOAD_UPDATE``: Upload changes to an existing destination file
* ``UPLOAD_RESTORE``: Re-upload a file that was deleted at destination

Download Actions
~~~~~~~~~~~~~~~~

* ``DOWNLOAD_NEW``: Download a new file from destination
* ``DOWNLOAD_UPDATE``: Download changes to an existing source file
* ``DOWNLOAD_RESTORE``: Re-download a file that was deleted at source

Delete Actions
~~~~~~~~~~~~~~

* ``DELETE_SOURCE``: Delete a file from source
* ``DELETE_DESTINATION``: Delete a file from destination

Other Actions
~~~~~~~~~~~~~

* ``NO_ACTION``: File is already in sync, no action needed
* ``CONFLICT``: Manual resolution required

Rename and Move Detection
--------------------------

SyncEngine can detect when files are renamed or moved (not just deleted and re-added):

How It Works
~~~~~~~~~~~~

1. Scanner creates a hash of each file's content
2. When comparing states, files are matched by content hash
3. If a file with the same hash appears at a different path, it's recognized as a rename/move
4. The rename/move is replicated to the other side instead of delete+upload

Benefits
~~~~~~~~

* Faster sync (no re-upload of large files)
* Preserves file history/metadata
* More accurate representation of changes
* Reduced bandwidth usage

Example:

.. code-block:: python

   # Before sync:
   # Source: /docs/report.pdf (hash: abc123)
   # Destination: /docs/report.pdf (hash: abc123)

   # User renames at source:
   # Source: /docs/annual_report_2024.pdf (hash: abc123)

   # After sync with rename detection:
   # Source: /docs/annual_report_2024.pdf (hash: abc123)
   # Destination: /docs/annual_report_2024.pdf (hash: abc123)
   # Action: RENAME (not DELETE + UPLOAD)

Conflict Resolution
-------------------

Conflicts occur when the same file is modified in both locations since the last sync.

Conflict Resolution Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NEWEST_WINS** (default)

The file with the most recent modification time wins:

.. code-block:: python

   from syncengine import ConflictResolution

   pair = SyncPair(
       ...,
       conflict_resolution=ConflictResolution.NEWEST_WINS
   )

**SOURCE_WINS**

Source file always wins conflicts:

.. code-block:: python

   pair = SyncPair(
       ...,
       conflict_resolution=ConflictResolution.SOURCE_WINS
   )

**DESTINATION_WINS**

Destination file always wins conflicts:

.. code-block:: python

   pair = SyncPair(
       ...,
       conflict_resolution=ConflictResolution.DESTINATION_WINS
   )

**MANUAL**

Conflicts are reported but not resolved automatically:

.. code-block:: python

   def handle_conflict(conflict_info):
       print(f"Conflict: {conflict_info.path}")
       print(f"Source modified: {conflict_info.source_mtime}")
       print(f"Destination modified: {conflict_info.dest_mtime}")
       # Return 'source', 'destination', or 'skip'
       return 'source'

   pair = SyncPair(
       ...,
       conflict_resolution=ConflictResolution.MANUAL,
       conflict_handler=handle_conflict
   )

Ignore Patterns
---------------

SyncEngine uses gitignore-style patterns to exclude files from sync.

Pattern Syntax
~~~~~~~~~~~~~~

* ``*.tmp`` - Ignore all .tmp files
* ``*.log`` - Ignore all .log files
* ``/build/`` - Ignore build directory at root
* ``build/`` - Ignore all build directories
* ``**/node_modules/`` - Ignore node_modules anywhere
* ``!important.log`` - Don't ignore important.log (negation)
* ``*.py[cod]`` - Ignore .pyc, .pyo, .pyd files
* ``#comment`` - Comments (ignored)

Creating an Ignore File
~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.syncignore`` file in your source root:

.. code-block:: text

   # Ignore compiled Python files
   *.pyc
   __pycache__/

   # Ignore OS files
   .DS_Store
   Thumbs.db

   # Ignore development files
   .vscode/
   .idea/
   *.swp

   # Ignore build artifacts
   build/
   dist/
   *.egg-info/

   # Ignore logs
   *.log

   # But keep important logs
   !critical.log

Using Ignore Patterns Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import IgnoreFileManager

   ignore_manager = IgnoreFileManager()

   # Add individual patterns
   ignore_manager.add_pattern("*.tmp")
   ignore_manager.add_pattern("*.log")

   # Load from file
   ignore_manager.load_from_file(".syncignore")

   # Check if path should be ignored
   if ignore_manager.should_ignore("test.tmp"):
       print("File is ignored")

   # Use with sync pair
   pair = SyncPair(
       ...,
       ignore_manager=ignore_manager
   )

State Management
----------------

State management is crucial for efficient incremental syncs.

State Directory Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   .sync_state/
   ├── source_tree.json       # Last known source state
   ├── destination_tree.json  # Last known destination state
   └── sync_metadata.json     # Sync metadata

State Files
~~~~~~~~~~~

**source_tree.json**

Stores information about each file in the source:

.. code-block:: json

   {
     "path/to/file.txt": {
       "hash": "abc123...",
       "size": 1024,
       "mtime": 1609459200.0,
       "is_dir": false
     }
   }

**destination_tree.json**

Stores information about each file in the destination:

.. code-block:: json

   {
     "path/to/file.txt": {
       "id": 12345,
       "hash": "abc123...",
       "size": 1024,
       "mtime": 1609459200.0,
       "is_dir": false
     }
   }

State Manager API
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncStateManager

   # Create state manager
   state_manager = SyncStateManager("/path/to/.sync_state")

   # Load previous state
   source_tree = state_manager.load_source_tree()
   dest_tree = state_manager.load_destination_tree()

   # Save new state after sync
   state_manager.save_source_tree(new_source_tree)
   state_manager.save_destination_tree(new_dest_tree)

   # Clear state (force full resync)
   state_manager.clear()

Concurrency and Performance
----------------------------

SyncEngine uses concurrent operations for efficiency.

Concurrency Model
~~~~~~~~~~~~~~~~~

SyncEngine uses two types of concurrency limits:

1. **Transfer Limit**: Maximum concurrent uploads/downloads
2. **Operations Limit**: Maximum concurrent file operations (list, delete, etc.)

.. code-block:: python

   from syncengine import ConcurrencyLimits

   limits = ConcurrencyLimits(
       transfers=5,      # Max 5 concurrent uploads/downloads
       operations=10     # Max 10 concurrent file operations
   )

Choosing Limits
~~~~~~~~~~~~~~~

**Transfer Limit**

* Too high: May saturate bandwidth, cause timeouts
* Too low: Underutilizes bandwidth, slower sync
* Recommended: 3-10 depending on bandwidth and file sizes

**Operations Limit**

* Too high: May overwhelm storage API, cause rate limiting
* Too low: Slower listing/deletion of many small files
* Recommended: 10-50 depending on storage API limits

Performance Tips
~~~~~~~~~~~~~~~~

1. **Use state management**: Dramatically speeds up incremental syncs
2. **Optimize concurrency**: Balance based on your use case
3. **Use ignore patterns**: Skip unnecessary files
4. **Choose appropriate sync mode**: Don't use TWO_WAY if you only need one-way
5. **Monitor progress**: Use progress callbacks to identify bottlenecks

Pause, Resume, and Cancel
--------------------------

Control sync execution at runtime.

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncPauseController
   import threading

   controller = SyncPauseController()
   engine = SyncEngine(
       ...,
       pause_controller=controller
   )

   # Start sync in background
   def run_sync():
       stats = engine.sync_pair(pair)
       print(f"Sync complete: {stats}")

   sync_thread = threading.Thread(target=run_sync)
   sync_thread.start()

   # Pause sync
   controller.pause()
   print("Sync paused")

   # Resume sync
   controller.resume()
   print("Sync resumed")

   # Cancel sync
   controller.cancel()
   print("Sync cancelled")

   sync_thread.join()

Pause Behavior
~~~~~~~~~~~~~~

When paused:

* Current operations complete
* No new operations start
* State is preserved
* Can resume at any time

Cancel Behavior
~~~~~~~~~~~~~~~

When cancelled:

* Current operations complete
* No new operations start
* State is saved (partial sync)
* Cannot resume (need to start new sync)

Progress Tracking
-----------------

Monitor sync progress with detailed callbacks.

Progress Events
~~~~~~~~~~~~~~~

SyncEngine emits various progress events:

* ``scan_start``: Starting to scan files
* ``scan_progress``: Scanning progress
* ``scan_complete``: Scan complete
* ``sync_start``: Starting sync operations
* ``upload_start``: Starting upload
* ``upload_progress``: Upload progress (bytes transferred)
* ``upload_complete``: Upload complete
* ``download_start``: Starting download
* ``download_progress``: Download progress (bytes transferred)
* ``download_complete``: Download complete
* ``delete_start``: Starting delete
* ``delete_complete``: Delete complete
* ``sync_complete``: All sync operations complete

Progress Callback
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent

   def on_progress(event: SyncProgressEvent):
       if event.type == "upload_progress":
           percent = (event.bytes_transferred / event.total_bytes) * 100
           print(f"Uploading {event.file_path}: {percent:.1f}%")

       elif event.type == "download_progress":
           percent = (event.bytes_transferred / event.total_bytes) * 100
           print(f"Downloading {event.file_path}: {percent:.1f}%")

       elif event.type == "sync_complete":
           print(f"Sync complete: {event.stats}")

   tracker = SyncProgressTracker(callback=on_progress)
   engine = SyncEngine(
       ...,
       progress_tracker=tracker
   )

Custom Progress UI
~~~~~~~~~~~~~~~~~~

You can build custom progress UIs using the progress callbacks:

.. code-block:: python

   class ProgressUI:
       def __init__(self):
           self.current_file = None
           self.total_files = 0
           self.completed_files = 0

       def on_progress(self, event: SyncProgressEvent):
           if event.type == "sync_start":
               self.total_files = event.total_files
               print(f"Starting sync of {self.total_files} files")

           elif event.type == "upload_start":
               self.current_file = event.file_path
               print(f"Uploading: {self.current_file}")

           elif event.type == "upload_complete":
               self.completed_files += 1
               print(f"Completed {self.completed_files}/{self.total_files}")

           # ... handle other events

   ui = ProgressUI()
   tracker = SyncProgressTracker(callback=ui.on_progress)

Next Steps
----------

* :doc:`sync_modes` - Detailed explanation of each sync mode
* :doc:`protocols` - Implement custom storage backends
* :doc:`examples` - Advanced usage examples
* :doc:`api_reference` - Complete API documentation
