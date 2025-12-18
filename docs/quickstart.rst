Quickstart Guide
================

This guide will help you get started with SyncEngine in just a few minutes.

Installation
------------

First, install SyncEngine:

.. code-block:: bash

   pip install syncengine

Basic Usage
-----------

The simplest way to use SyncEngine is with local filesystem synchronization:

.. code-block:: python

   from syncengine import SyncEngine, SyncMode, LocalStorageClient, SyncPair

   # Create storage clients for source and destination
   source_client = LocalStorageClient("/home/user/documents")
   dest_client = LocalStorageClient("/home/user/backup")

   # Create sync engine with two-way sync mode
   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda client, storage_id: FileEntriesManager(client)
   )

   # Create a sync pair
   pair = SyncPair(
       source_root="/home/user/documents",
       destination_root="/home/user/backup",
       source_client=source_client,
       destination_client=dest_client,
       mode=SyncMode.TWO_WAY
   )

   # Perform synchronization
   stats = engine.sync_pair(pair)

   # Print results
   print(f"Uploaded: {stats['uploads']}")
   print(f"Downloaded: {stats['downloads']}")
   print(f"Deleted: {stats['deletes']}")

Understanding Sync Modes
-------------------------

SyncEngine supports five different sync modes:

TWO_WAY (Bidirectional Sync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keeps both sides in sync. Changes on either side are propagated to the other.

.. code-block:: python

   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/backup/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.TWO_WAY
   )

SOURCE_TO_DESTINATION (Mirror)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mirrors the source to destination. Destination changes are overwritten.

.. code-block:: python

   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/backup/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.SOURCE_TO_DESTINATION
   )

SOURCE_BACKUP (Upload-Only Backup)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Uploads new/changed files but never deletes from source.

.. code-block:: python

   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/backup/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.SOURCE_BACKUP
   )

DESTINATION_TO_SOURCE (Download Mirror)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mirrors destination to source. Source changes are overwritten.

.. code-block:: python

   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/cloud/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.DESTINATION_TO_SOURCE
   )

DESTINATION_BACKUP (Download-Only Backup)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Downloads new/changed files but never deletes from destination.

.. code-block:: python

   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/cloud/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.DESTINATION_BACKUP
   )

Using Ignore Patterns
----------------------

Exclude files from sync using gitignore-style patterns:

.. code-block:: python

   from syncengine import IgnoreFileManager

   # Create ignore manager
   ignore_manager = IgnoreFileManager()

   # Add patterns
   ignore_manager.add_pattern("*.tmp")
   ignore_manager.add_pattern(".git/")
   ignore_manager.add_pattern("node_modules/")

   # Or load from a .syncignore file
   ignore_manager.load_from_file("/home/user/docs/.syncignore")

   # Use with sync pair
   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/backup/docs",
       source_client=source,
       destination_client=dest,
       mode=SyncMode.TWO_WAY,
       ignore_manager=ignore_manager
   )

Progress Tracking
-----------------

Monitor sync progress with real-time file-level callbacks for both uploads and downloads:

Upload Progress Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo

   def on_progress(info: SyncProgressInfo):
       if info.event == SyncProgressEvent.UPLOAD_FILE_START:
           print(f"Uploading: {info.file_path}")

       elif info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS:
           progress = (info.current_file_bytes / info.current_file_total * 100) if info.current_file_total > 0 else 0
           print(f"  Progress: {progress:.1f}% ({info.current_file_bytes}/{info.current_file_total} bytes)")

       elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
           print(f"  Complete: {info.file_path}")

       elif info.event == SyncProgressEvent.UPLOAD_FILE_ERROR:
           print(f"  Error: {info.file_path} - {info.error_message}")

   # Create progress tracker
   tracker = SyncProgressTracker(callback=on_progress)

   # Use with sync_pair
   stats = engine.sync_pair(
       pair,
       sync_progress_tracker=tracker
   )

Download Progress Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track folder downloads with the same level of detail:

.. code-block:: python

   from pathlib import Path
   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo

   def on_download_progress(info: SyncProgressInfo):
       if info.event == SyncProgressEvent.DOWNLOAD_BATCH_START:
           print(f"Starting download: {info.directory} ({info.folder_bytes_total} bytes)")

       elif info.event == SyncProgressEvent.DOWNLOAD_FILE_START:
           print(f"  Downloading: {info.file_path}")

       elif info.event == SyncProgressEvent.DOWNLOAD_FILE_PROGRESS:
           progress = (info.current_file_bytes / info.current_file_total * 100) if info.current_file_total > 0 else 0
           print(f"    Progress: {progress:.1f}%")

       elif info.event == SyncProgressEvent.DOWNLOAD_FILE_COMPLETE:
           print(f"  ✓ Complete: {info.file_path}")

       elif info.event == SyncProgressEvent.DOWNLOAD_FILE_ERROR:
           print(f"  ✗ Error: {info.file_path} - {info.error_message}")

       elif info.event == SyncProgressEvent.DOWNLOAD_BATCH_COMPLETE:
           print(f"Batch complete: {info.folder_files_downloaded} files downloaded")

   # Create progress tracker
   tracker = SyncProgressTracker(callback=on_download_progress)

   # Download folder with progress tracking
   stats = engine.download_folder(
       destination_path="/remote/folder",
       local_path=Path("/local/downloads"),
       sync_progress_tracker=tracker
   )

   print(f"Downloaded {stats['downloads']} files")

Advanced Upload Options
-----------------------

SyncEngine v0.2.0 adds advanced upload control features:

Upload to Specific Folder ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Upload directly into a folder without path resolution:

.. code-block:: python

   from syncengine import SyncPair, SyncMode
   from pathlib import Path

   # Upload into folder ID 1234
   pair = SyncPair(
       source=Path("/home/user/documents"),
       destination="/remote_folder",
       sync_mode=SyncMode.SOURCE_TO_DESTINATION,
       storage_id=0,
       parent_id=1234,  # Upload directly into this folder
   )

   stats = engine.sync_pair(pair)

Skip Specific Files
~~~~~~~~~~~~~~~~~~~

Skip files during upload (useful for duplicate handling):

.. code-block:: python

   # Skip specific files
   files_to_skip = {
       "folder/duplicate1.txt",
       "folder/duplicate2.txt",
   }

   stats = engine.sync_pair(
       pair,
       files_to_skip=files_to_skip
   )

Rename Files During Upload
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rename files during upload (useful for duplicate handling):

.. code-block:: python

   # Rename files during upload
   file_renames = {
       "old_name.txt": "new_name.txt",
       "folder/old.txt": "folder/renamed.txt",
   }

   stats = engine.sync_pair(
       pair,
       file_renames=file_renames
   )

Force Upload/Download Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Force re-upload or re-download files even when they appear identical (new in v0.2.0):

.. code-block:: python

   # Force upload all files (useful for "replace" operations)
   stats = engine.sync_pair(
       pair,
       force_upload=True,  # Bypass hash/size comparison
   )

   # Force download all files (useful for refreshing local copies)
   pair_download = SyncPair(
       source=Path("/home/user/documents"),
       destination="/cloud/documents",
       sync_mode=SyncMode.DESTINATION_TO_SOURCE,
       storage_id=0,
   )

   stats = engine.sync_pair(
       pair_download,
       force_download=True,  # Bypass hash/size comparison
   )

   # Force upload with duplicate handling
   stats = engine.sync_pair(
       pair,
       force_upload=True,          # Force upload all files
       files_to_skip={"temp.txt"},  # But still skip these
       file_renames={"old.txt": "new.txt"},  # And rename these
   )

**When to use force_upload/force_download:**

* **Replace duplicates**: When you want to replace existing files with identical content
* **Refresh files**: Update modification timestamps on remote/local files
* **Re-upload after errors**: Force re-upload files that failed previously
* **Sync metadata**: Update file metadata even when content is identical

**Sync mode compatibility:**

* ``force_upload`` works with: ``SOURCE_TO_DESTINATION``, ``SOURCE_BACKUP``, ``TWO_WAY``
* ``force_download`` works with: ``DESTINATION_TO_SOURCE``, ``DESTINATION_BACKUP``, ``TWO_WAY``
* In ``TWO_WAY`` mode, ``force_upload`` takes precedence if both flags are set

Complete Example with All Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from syncengine import SyncEngine, SyncPair, SyncMode
   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo

   def progress_callback(info: SyncProgressInfo):
       """Display upload progress."""
       if info.event == SyncProgressEvent.UPLOAD_FILE_START:
           print(f"⬆️  Uploading: {info.file_path}")
       elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
           print(f"✓ Complete: {info.file_path}")

   # Create sync engine
   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda c, sid: FileEntriesManager(c)
   )

   # Create sync pair with parent_id
   pair = SyncPair(
       source=Path("/home/user/documents"),
       destination="/backup",
       sync_mode=SyncMode.SOURCE_TO_DESTINATION,
       storage_id=0,
       parent_id=1234,  # Upload into specific folder
   )

   # Create progress tracker
   tracker = SyncProgressTracker(callback=progress_callback)

   # Execute with all features
   stats = engine.sync_pair(
       pair,
       sync_progress_tracker=tracker,
       files_to_skip={"temp.txt"},
       file_renames={"old.txt": "new.txt"},
       force_upload=False,  # Set to True to force upload all files
       max_workers=4,
   )

   print(f"Uploaded: {stats['uploads']} files")

State Management
----------------

SyncEngine automatically tracks state to enable efficient incremental syncs:

.. code-block:: python

   from syncengine import SyncStateManager

   # State is stored in .sync_state directory by default
   state_manager = SyncStateManager("/home/user/docs/.sync_state")

   # Use with engine
   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda c, sid: FileEntriesManager(c),
       state_manager=state_manager
   )

   # First sync - compares all files
   stats = engine.sync_pair(pair)

   # Second sync - only processes changes since last sync
   stats = engine.sync_pair(pair)  # Much faster!

Concurrency Control
-------------------

Control how many concurrent operations are allowed:

.. code-block:: python

   from syncengine import ConcurrencyLimits

   # Limit concurrent transfers and operations
   limits = ConcurrencyLimits(
       transfers=5,      # Max 5 concurrent uploads/downloads
       operations=10     # Max 10 concurrent file operations
   )

   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda c, sid: FileEntriesManager(c),
       concurrency_limits=limits
   )

Pause/Resume/Cancel
-------------------

Control sync execution:

.. code-block:: python

   from syncengine import SyncPauseController

   controller = SyncPauseController()

   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda c, sid: FileEntriesManager(c),
       pause_controller=controller
   )

   # Start sync in background thread
   import threading
   sync_thread = threading.Thread(target=engine.sync_pair, args=(pair,))
   sync_thread.start()

   # Pause sync
   controller.pause()

   # Resume sync
   controller.resume()

   # Cancel sync
   controller.cancel()

Error Handling
--------------

Handle errors gracefully:

.. code-block:: python

   from syncengine import SyncEngine, SyncConfigError

   try:
       stats = engine.sync_pair(pair)
   except SyncConfigError as e:
       print(f"Configuration error: {e}")
   except Exception as e:
       print(f"Sync error: {e}")

Working with Cloud Storage
---------------------------

To sync with cloud storage, implement the ``StorageClientProtocol``:

.. code-block:: python

   from syncengine.protocols import StorageClientProtocol
   from pathlib import Path
   from typing import Optional, Callable, Any

   class MyCloudClient(StorageClientProtocol):
       def upload_file(
           self,
           file_path: Path,
           relative_path: str,
           storage_id: int = 0,
           chunk_size: int = 5242880,
           use_multipart_threshold: int = 52428800,
           progress_callback: Optional[Callable[[int, int], None]] = None
       ) -> Any:
           # Implement upload logic
           pass

       def download_file(
           self,
           hash_value: str,
           output_path: Path,
           progress_callback: Optional[Callable[[int, int], None]] = None
       ) -> Path:
           # Implement download logic
           pass

       # ... implement other required methods

   # Use your custom client
   cloud_client = MyCloudClient()
   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="/cloud/docs",
       source_client=local_client,
       destination_client=cloud_client,
       mode=SyncMode.TWO_WAY
   )

Next Steps
----------

* :doc:`concepts` - Deep dive into core concepts
* :doc:`sync_modes` - Detailed explanation of sync modes
* :doc:`protocols` - Learn how to implement custom storage backends
* :doc:`examples` - More advanced examples
* :doc:`api_reference` - Complete API documentation
