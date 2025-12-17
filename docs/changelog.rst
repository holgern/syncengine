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
* Progress events include: ``SCAN_DIR_START``, ``SCAN_DIR_COMPLETE``, ``UPLOAD_BATCH_START``, ``UPLOAD_FILE_START``, ``UPLOAD_FILE_PROGRESS``, ``UPLOAD_FILE_COMPLETE``, ``UPLOAD_FILE_ERROR``, ``UPLOAD_BATCH_COMPLETE``
* Each event provides detailed information via ``SyncProgressInfo`` including file paths, byte counts, transfer speeds, and ETAs

**Advanced Upload Control**

* Added ``parent_id`` parameter to ``SyncPair`` - upload directly into a specific folder ID without path resolution
* Added ``files_to_skip`` parameter to ``sync_pair()`` - skip specific files during sync (useful for duplicate handling)
* Added ``file_renames`` parameter to ``sync_pair()`` - rename files during upload (useful for duplicate handling)

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

Benefits
~~~~~~~~

* **Real-time visibility**: Users see which files are being uploaded/downloaded in real-time
* **Better UX**: Progress bars show transfer speed, ETA, and byte-level progress
* **Error handling**: Failed uploads are immediately visible with error messages
* **Duplicate handling**: Skip or rename conflicting files during upload
* **Direct folder uploads**: Upload into specific folders without path resolution overhead

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

Documentation
~~~~~~~~~~~~~

* Updated :doc:`quickstart` with progress tracking examples
* Updated :doc:`examples` with comprehensive progress tracking patterns
* Added ``examples/progress_example.py`` demonstrating all new features

Testing
~~~~~~~

* All 433 existing tests pass
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
