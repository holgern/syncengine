Introduction
============

What is SyncEngine?
-------------------

SyncEngine is a powerful file synchronization library that enables you to keep files synchronized between two locations (source and destination). Unlike simple copy operations, SyncEngine intelligently tracks file state, detects changes, handles conflicts, and provides multiple synchronization modes to fit different use cases.

Why is SyncEngine useful?
--------------------------

Real-world Use Cases
~~~~~~~~~~~~~~~~~~~~

**Cloud Storage Synchronization**

* Sync local files with cloud storage (Dropbox, Google Drive, S3, etc.)
* Implement custom cloud backup solutions
* Build your own sync client with fine-grained control

**Backup Management**

* Create one-way backup systems (never delete backed-up files)
* Implement versioned backup strategies
* Maintain disaster recovery copies

**Development Workflows**

* Sync code between local development and remote servers
* Mirror files to multiple deployment targets
* Keep test environments synchronized with production data

**Content Distribution**

* Distribute files from a master source to multiple destinations
* Keep documentation or assets synchronized across systems
* Manage multi-site content updates

Architecture
------------

SyncEngine uses a protocol-based architecture that separates the synchronization logic from the storage implementation. This allows it to work with any storage backend (local filesystem, S3, FTP, custom cloud APIs) through simple protocol interfaces.

Key Components
~~~~~~~~~~~~~~

1. **SyncEngine**: Core orchestrator that manages the synchronization process
2. **SyncModes**: Different strategies for handling changes and conflicts
3. **StorageClientProtocol**: Interface for storage backends
4. **FileComparator**: Logic for detecting changes and determining actions
5. **SyncOperations**: Executes upload/download/delete operations
6. **SyncStateManager**: Tracks file history across sync sessions
7. **DirectoryScanner**: Efficiently scans and indexes files
8. **IgnoreFileManager**: Handles gitignore-style patterns

Design Principles
-----------------

Storage Agnostic
~~~~~~~~~~~~~~~~

SyncEngine doesn't care where your files are stored. It works through protocol interfaces, so you can sync between any storage systems - local filesystem, cloud storage, FTP servers, or custom implementations.

State-Based Sync
~~~~~~~~~~~~~~~~

Instead of simple file comparison, SyncEngine maintains state about previous sync operations. This enables it to:

* Detect renames and moves (not just add/delete)
* Identify conflicts when both sides change
* Resume interrupted syncs
* Handle partial syncs efficiently

Flexible Modes
~~~~~~~~~~~~~~

Different use cases need different behaviors. SyncEngine provides multiple sync modes with well-defined semantics for handling changes, deletions, and conflicts.

Concurrent Operations
~~~~~~~~~~~~~~~~~~~~~

SyncEngine uses concurrent operations for uploads and downloads with configurable limits, making it efficient for syncing large numbers of files.

Installation
------------

Install from PyPI:

.. code-block:: bash

   pip install syncengine

Or for development:

.. code-block:: bash

   git clone https://github.com/holgern/syncengine
   cd syncengine
   pip install -e .

Requirements
~~~~~~~~~~~~

* Python 3.9 or higher
* No required dependencies (storage clients may have their own dependencies)

License
-------

See the LICENSE file in the repository for details.

Contributing
------------

Contributions are welcome! Please ensure:

* Tests pass: ``pytest tests/``
* Benchmarks pass: ``python benchmarks/run_benchmarks.py``
* Code follows project style (ruff/black formatting)

Next Steps
----------

* :doc:`quickstart` - Get started with a simple example
* :doc:`concepts` - Understand core concepts
* :doc:`sync_modes` - Learn about different sync modes
* :doc:`protocols` - Implement your own storage backend
