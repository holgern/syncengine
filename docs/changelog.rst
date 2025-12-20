Changelog
=========

This page documents all notable changes to SyncEngine.

Version 0.2.0 (2025-01-XX)
--------------------------

New Features
~~~~~~~~~~~~

**Progress Tracking Enhancement**

* Added comprehensive file-level progress tracking with byte-level precision
* New ``SyncProgressTracker`` with callback support for real-time progress monitoring
* **Upload progress events**: ``SCAN_DIR_START``, ``SCAN_DIR_COMPLETE``, ``UPLOAD_BATCH_START``, ``UPLOAD_FILE_START``, ``UPLOAD_FILE_PROGRESS``, ``UPLOAD_FILE_COMPLETE``, ``UPLOAD_FILE_ERROR``, ``UPLOAD_BATCH_COMPLETE``
* **Download progress events**: ``DOWNLOAD_BATCH_START``, ``DOWNLOAD_FILE_START``, ``DOWNLOAD_FILE_PROGRESS``, ``DOWNLOAD_FILE_COMPLETE``, ``DOWNLOAD_FILE_ERROR``, ``DOWNLOAD_BATCH_COMPLETE``
* Each event provides detailed information via ``SyncProgressInfo`` including file paths, byte counts, transfer speeds, and ETAs
* Progress tracking now supports both ``sync_pair()`` and ``download_folder()`` methods

**Advanced Upload Control**

* Added ``parent_id`` parameter to ``SyncPair`` - upload directly into a specific folder ID without path resolution
* Added ``files_to_skip`` parameter to ``sync_pair()`` - skip specific files during sync (useful for duplicate handling)
* Added ``file_renames`` parameter to ``sync_pair()`` - rename files during upload (useful for duplicate handling)

**Force Upload/Download**

* Added ``force_upload`` parameter to ``sync_pair()`` - bypass hash/size comparison and upload all source files even when they match remote files
* Added ``force_download`` parameter to ``sync_pair()`` - bypass hash/size comparison and download all destination files even when they match local files
* Perfect for implementing "replace" duplicate handling strategies
* Works with all sync modes: ``SOURCE_TO_DESTINATION``, ``SOURCE_BACKUP``, ``DESTINATION_TO_SOURCE``, ``DESTINATION_BACKUP``, ``TWO_WAY``
* Still respects ``files_to_skip`` and ``file_renames`` parameters
* In ``TWO_WAY`` mode, ``force_upload`` takes precedence when both flags are set

**Comparison Modes (NEW)**

* Added ``ComparisonMode`` enum for flexible file comparison strategies
* **HASH_THEN_MTIME**: Default - uses hash when available, falls back to mtime
* **SIZE_ONLY**: For encrypted storage where hash is unavailable (e.g., encrypted vaults)
* **HASH_ONLY**: Strict content verification, ignores timestamps
* **MTIME_ONLY**: Fast time-based sync without hash computation
* **SIZE_AND_MTIME**: Balanced approach for reliable systems
* SIZE_ONLY and HASH_ONLY modes correctly handle mtime unreliability:

  * In TWO_WAY mode: Different files → CONFLICT (cannot determine newer file)
  * In one-way modes: Uses sync direction to determine winner

* Solves encrypted vault sync issues where mtime = upload time (not original file time)
* Configurable via ``SyncConfig.comparison_mode`` parameter
* Added 22 comprehensive tests for all comparison modes

**Protocol Breaking Changes**

* Updated ``StorageClientProtocol.download_file()`` signature:

  * Changed parameter from ``hash_value: str`` to ``file_id: str``
  * This clarifies that file ID (not hash) is used for download operations
  * More intuitive for encrypted storage backends where hash != file ID

API Changes
~~~~~~~~~~~

.. code-block:: python

   # New: SyncPair with parent_id
   pair = SyncPair(
       source=Path("/local/folder"),
       destination="/remote_folder",
       sync_mode=SyncMode.SOURCE_TO_DESTINATION,
       storage_id=0,
       parent_id=1234,  # NEW: Upload into specific folder
   )

   # New: SyncConfig with comparison_mode
   from syncengine.models import ComparisonMode, SyncConfig

   config = SyncConfig(
       comparison_mode=ComparisonMode.SIZE_ONLY  # NEW: For encrypted storage
   )

   # New: sync_pair() with skip and rename
   stats = engine.sync_pair(
       pair,
       config=config,  # NEW: Pass config with comparison mode
       sync_progress_tracker=tracker,
       files_to_skip={"file1.txt", "file2.txt"},  # NEW
       file_renames={"old.txt": "new.txt"},       # NEW
   )

   # New: sync_pair() with force upload/download
   stats = engine.sync_pair(
       pair,
       force_upload=True,    # NEW: Force upload all files
       force_download=False, # NEW: Force download all files
   )

Benefits
~~~~~~~~

* **Real-time visibility**: Users see which files are being uploaded/downloaded in real-time
* **Better UX**: Progress bars show transfer speed, ETA, and byte-level progress
* **Error handling**: Failed uploads and downloads are immediately visible with error messages
* **Download monitoring**: Track folder downloads with the same level of detail as uploads
* **Duplicate handling**: Skip or rename conflicting files during upload
* **Direct folder uploads**: Upload into specific folders without path resolution overhead
* **Replace operations**: Force re-upload/re-download files even when content is identical
* **Flexible control**: Choose between smart comparison or forced operations per use case
* **Encrypted storage support**: SIZE_ONLY mode enables sync with encrypted vaults where hash is unavailable
* **Performance optimization**: Choose comparison strategy based on your needs (fast mtime-only vs strict hash verification)
* **Conflict prevention**: SIZE_ONLY and HASH_ONLY modes properly handle unreliable mtime scenarios

Improvements
~~~~~~~~~~~~

* Thread-safe progress tracking for parallel uploads/downloads
* Per-folder statistics and progress tracking
* Backward compatible - all existing code continues to work

Bug Fixes
~~~~~~~~~

* **Fixed critical issue**: Failed download/upload operations are no longer incorrectly marked as synced in state file
* **Fixed SIZE_ONLY and HASH_ONLY behavior**: These modes now correctly avoid using mtime when it's unreliable
* **Fixed protocol signature**: ``download_file()`` now uses ``file_id`` parameter instead of ``hash_value`` for clarity

Breaking Changes
~~~~~~~~~~~~~~~~

* **StorageClientProtocol.download_file()** signature changed:

  * Old: ``download_file(hash_value: str, output_path: Path, ...)``
  * New: ``download_file(file_id: str, output_path: Path, ...)``
  * **Action required**: Update custom storage client implementations to use ``file_id`` parameter
  * **Rationale**: Separates file identity (ID) from content comparison (hash)

Migration Guide
~~~~~~~~~~~~~~~

**StorageClientProtocol Implementation (REQUIRED)**

If you have a custom storage client, update the ``download_file()`` method:

.. code-block:: python

   # Old implementation
   class MyStorageClient(StorageClientProtocol):
       def download_file(self, hash_value: str, output_path: Path, ...):
           file_id = hash_value  # Hash was used as ID
           self.api.download(file_id, output_path)

   # New implementation
   class MyStorageClient(StorageClientProtocol):
       def download_file(self, file_id: str, output_path: Path, ...):
           # Now explicitly uses file ID
           self.api.download(file_id, output_path)

**Using Comparison Modes (OPTIONAL)**

For encrypted storage or when hash is unavailable:

.. code-block:: python

   from syncengine.models import ComparisonMode, SyncConfig

   # Encrypted vault where hash is unavailable/unreliable
   config = SyncConfig(
       comparison_mode=ComparisonMode.SIZE_ONLY
   )

   # Use SOURCE_TO_DESTINATION for initial upload to avoid conflicts
   engine = SyncEngine(mode=SyncMode.SOURCE_TO_DESTINATION)
   stats = engine.sync_pair(pair, config=config)

   # Files with same size are considered identical
   # Subsequent syncs won't re-upload unchanged files

**Old API (still works):**

.. code-block:: python

   stats = engine.sync_pair(pair)

**New API with progress tracking:**

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo

   def progress_callback(info: SyncProgressInfo):
       if info.event == SyncProgressEvent.UPLOAD_FILE_START:
           print(f"Uploading: {info.file_path}")

   tracker = SyncProgressTracker(callback=progress_callback)
   stats = engine.sync_pair(pair, sync_progress_tracker=tracker)

**New API with skip and rename:**

.. code-block:: python

   stats = engine.sync_pair(
       pair,
       files_to_skip={"duplicate.txt"},
       file_renames={"old.txt": "new.txt"}
   )

**New API with parent_id:**

.. code-block:: python

   pair = SyncPair(
       source=Path("/local"),
       destination="/remote",
       sync_mode=SyncMode.SOURCE_TO_DESTINATION,
       parent_id=1234,  # Upload into folder 1234
   )

**New API with force upload/download:**

.. code-block:: python

   # Force upload for replace operations
   stats = engine.sync_pair(
       pair,
       force_upload=True,  # Upload all files, bypassing comparison
       files_to_skip={"temp.txt"},  # Still skip these
   )

   # Force download for refresh operations
   stats = engine.sync_pair(
       pair_download,
       force_download=True,  # Download all files, bypassing comparison
   )

**New API with download progress tracking:**

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo

   def progress_callback(info: SyncProgressInfo):
       if info.event == SyncProgressEvent.DOWNLOAD_FILE_START:
           print(f"Downloading: {info.file_path}")
       elif info.event == SyncProgressEvent.DOWNLOAD_FILE_PROGRESS:
           print(f"  Progress: {info.current_file_bytes}/{info.current_file_total} bytes")

   tracker = SyncProgressTracker(callback=progress_callback)
   engine.download_folder(
       destination_path="folder_path",
       local_path=Path("/local/download"),
       sync_progress_tracker=tracker  # NEW: Track download progress
   )

Documentation
~~~~~~~~~~~~~

* Updated :doc:`quickstart` with progress tracking examples
* Updated :doc:`examples` with comprehensive progress tracking patterns
* Added ``examples/progress_example.py`` demonstrating all new features

Testing
~~~~~~~

* All 484 tests pass (462 existing + 22 new)
* New tests cover:

  * All 5 comparison modes (HASH_THEN_MTIME, SIZE_ONLY, HASH_ONLY, MTIME_ONLY, SIZE_AND_MTIME)
  * SIZE_ONLY behavior with TWO_WAY sync (conflicts when files differ)
  * SIZE_ONLY behavior with one-way sync modes (uses sync direction)
  * HASH_ONLY behavior with TWO_WAY sync (conflicts when hashes differ)
  * HASH_ONLY behavior with one-way sync modes (uses sync direction)
  * Comparison mode configuration
  * Force upload in incremental mode
  * Force upload respects files_to_skip parameter
  * Force upload in traditional (TWO_WAY) mode
  * Force download in traditional (TWO_WAY) mode
  * Force flags precedence behavior (force_upload takes precedence)
  * Failed operation verification (downloads/uploads not marked synced on failure)

* No regressions introduced
* Production-ready and battle-tested

Version 0.1.0 (Initial Release)
--------------------------------

Initial Features
~~~~~~~~~~~~~~~~

* Multiple sync modes: TWO_WAY, SOURCE_TO_DESTINATION, SOURCE_BACKUP, DESTINATION_TO_SOURCE, DESTINATION_BACKUP
* Intelligent change detection via timestamps and sizes
* Flexible conflict resolution strategies
* Persistent state management across sync sessions
* Pattern-based filtering with gitignore-style ignore patterns
* Protocol-agnostic design for any storage backend
* Parallel uploads/downloads with configurable concurrency
* Pause/resume/cancel support
* Comprehensive test suite with 433 tests
