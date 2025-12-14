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

Monitor sync progress with callbacks:

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent

   def on_progress(event: SyncProgressEvent):
       if event.type == "upload_progress":
           print(f"Uploading {event.file_path}: {event.bytes_transferred}/{event.total_bytes}")
       elif event.type == "download_progress":
           print(f"Downloading {event.file_path}: {event.bytes_transferred}/{event.total_bytes}")
       elif event.type == "complete":
           print(f"Sync complete: {event.stats}")

   # Create progress tracker
   tracker = SyncProgressTracker(callback=on_progress)

   # Use with engine
   engine = SyncEngine(
       client=dest_client,
       entries_manager_factory=lambda c, sid: FileEntriesManager(c),
       progress_tracker=tracker
   )

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
