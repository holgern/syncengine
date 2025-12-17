SyncEngine Documentation
========================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   introduction
   quickstart
   concepts
   sync_modes
   protocols
   api_reference
   examples
   benchmarks
   changelog

Welcome to SyncEngine
---------------------

SyncEngine is a flexible, bidirectional file synchronization engine for Python that supports multiple sync modes and conflict resolution strategies.

Key Features
------------

* **Multiple Sync Modes**: TWO_WAY, SOURCE_TO_DESTINATION, SOURCE_BACKUP, DESTINATION_TO_SOURCE, DESTINATION_BACKUP
* **Intelligent Change Detection**: Tracks file modifications via timestamps and sizes, detects renames and moves
* **Flexible Conflict Resolution**: Newest file wins, source always wins, destination always wins, or manual handling
* **State Management**: Persistent state tracking across sync sessions, resume interrupted syncs
* **Pattern-based Filtering**: Gitignore-style ignore patterns for fine-grained control
* **Protocol Agnostic**: Works with any storage backend through pluggable storage interfaces
* **Progress Tracking**: Real-time file-level progress with byte-level tracking, transfer speed, and ETA
* **Advanced Upload Control**: Skip specific files, rename during upload, and upload directly to folder IDs

Quick Example
-------------

.. code-block:: python

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
