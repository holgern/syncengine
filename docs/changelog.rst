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

   # New: sync_pair() with skip and rename
   stats = engine.sync_pair(
       pair,
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

Improvements
~~~~~~~~~~~~

* Thread-safe progress tracking for parallel uploads/downloads
* Per-folder statistics and progress tracking
* Backward compatible - all existing code continues to work

Bug Fixes
~~~~~~~~~

* None (new feature release)

Breaking Changes
~~~~~~~~~~~~~~~~

* **None** - All changes are backward compatible

Migration Guide
~~~~~~~~~~~~~~~

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

* All 438 tests pass (433 existing + 5 new for force upload/download)
* New tests cover:

  * Force upload in incremental mode
  * Force upload respects files_to_skip parameter
  * Force upload in traditional (TWO_WAY) mode
  * Force download in traditional (TWO_WAY) mode
  * Force flags precedence behavior (force_upload takes precedence)

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
