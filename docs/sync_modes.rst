Sync Modes Reference
====================

SyncEngine supports five different synchronization modes, each designed for specific use cases. This page provides detailed information about each mode.

Quick Comparison
----------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 15 15 20

   * - Mode
     - Use Case
     - Upload
     - Download
     - Delete Behavior
   * - TWO_WAY
     - Keep both sides in sync
     - Yes
     - Yes
     - Both directions
   * - SOURCE_TO_DESTINATION
     - Mirror source to dest
     - Yes
     - No
     - Dest only
   * - SOURCE_BACKUP
     - Backup without deletes
     - Yes
     - No
     - Never delete source
   * - DESTINATION_TO_SOURCE
     - Mirror dest to source
     - No
     - Yes
     - Source only
   * - DESTINATION_BACKUP
     - Download without deletes
     - No
     - Yes
     - Never delete dest

TWO_WAY Mode
------------

**Use case**: Bidirectional synchronization where both sides should be kept in sync.

Behavior
~~~~~~~~

* **Uploads**: New/modified source files are uploaded to destination
* **Downloads**: New/modified destination files are downloaded to source
* **Source deletions**: Propagated to destination
* **Destination deletions**: Propagated to source
* **Renames/moves**: Applied to both sides
* **Conflicts**: Detected and resolved based on conflict resolution strategy

Example
~~~~~~~

.. code-block:: python

   from syncengine import SyncEngine, SyncMode, SyncPair

   pair = SyncPair(
       source_root="/home/user/documents",
       destination_root="/cloud/documents",
       source_client=local_client,
       destination_client=cloud_client,
       mode=SyncMode.TWO_WAY
   )

   stats = engine.sync_pair(pair)

Scenarios
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Change
     - Action
   * - Add file at source
     - Upload to destination
   * - Add file at destination
     - Download to source
   * - Modify file at source
     - Upload to destination
   * - Modify file at destination
     - Download to source
   * - Modify file at both sides
     - Conflict (resolve based on strategy)
   * - Delete file at source
     - Delete at destination
   * - Delete file at destination
     - Delete at source
   * - Rename file at source
     - Rename at destination
   * - Rename file at destination
     - Rename at source

Best Practices
~~~~~~~~~~~~~~

* Use with conflict resolution strategy (NEWEST_WINS, SOURCE_WINS, DESTINATION_WINS)
* Enable state management for efficient incremental syncs
* Monitor for conflicts and have a resolution plan
* Consider using ignore patterns for temporary files

Initial Sync Behavior
~~~~~~~~~~~~~~~~~~~~~

**Important**: The first time you sync with TWO_WAY mode (when no previous sync state exists), you must decide how to handle files that exist on only one side.

The Problem
^^^^^^^^^^^

On first sync, the sync engine cannot distinguish between:

* **"File was deleted locally"** (should delete from destination)
* **"File was added remotely"** (should download to local)

This ambiguity can lead to unexpected data loss if not handled carefully.

Initial Sync Preferences
^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``initial_sync_preference`` parameter to control first-sync behavior:

.. code-block:: python

   from syncengine import SyncEngine, SyncMode, SyncPair, InitialSyncPreference

   pair = SyncPair(
       source=Path("/local/folder"),
       destination="/cloud/folder",
       sync_mode=SyncMode.TWO_WAY
   )

   # Option 1: MERGE (default - safest)
   # Merges both sides without deletions
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.MERGE
   )
   # Result: Downloads destination files, uploads source files, NO deletions

   # Option 2: SOURCE_WINS
   # Source is authoritative, destination extras deleted
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.SOURCE_WINS
   )
   # Result: Uploads source files, DELETES destination-only files

   # Option 3: DESTINATION_WINS
   # Destination is authoritative, source extras deleted
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.DESTINATION_WINS
   )
   # Result: Downloads destination files, DELETES source-only files

**Default Behavior**: If not specified, ``MERGE`` is used for safety (no data loss).

Common Scenarios
^^^^^^^^^^^^^^^^

**Vault Restoration** (destination is master):

.. code-block:: python

   # Restore from cloud vault to empty local folder
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.DESTINATION_WINS
   )
   # Downloads all vault files to local

**First-Time Backup** (source is master):

.. code-block:: python

   # First backup of local files to empty cloud
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.SOURCE_WINS
   )
   # Uploads all local files to cloud

**Merging Two Directories**:

.. code-block:: python

   # Merge local and cloud files without losing anything
   stats = engine.sync_pair(
       pair,
       initial_sync_preference=InitialSyncPreference.MERGE  # or omit (default)
   )
   # Downloads cloud files, uploads local files, NO deletions

Risk Warnings
^^^^^^^^^^^^^

If you don't explicitly set a preference, the sync engine will detect risky patterns and warn you:

.. code-block:: text

   ⚠ WARNING: Destination has 100 files but source has only 5.
     Initial TWO_WAY sync will default to MERGE mode (no deletions).
     To make destination authoritative and delete source-only files:
       initial_sync_preference=InitialSyncPreference.DESTINATION_WINS

After First Sync
^^^^^^^^^^^^^^^^

After the first successful sync, normal TWO_WAY behavior applies:

* New files on either side are copied to the other
* Deletions on either side are propagated to the other
* Modifications are synced bidirectionally
* The ``initial_sync_preference`` parameter has no effect

SOURCE_TO_DESTINATION Mode
--------------------------

**Use case**: One-way mirror from source to destination. Source is the authoritative copy.

Behavior
~~~~~~~~

* **Uploads**: New/modified source files are uploaded to destination
* **Downloads**: Never downloads (destination changes ignored)
* **Source deletions**: Propagated to destination
* **Destination deletions**: Ignored (files re-uploaded from source)
* **Renames/moves**: Applied to destination only
* **Conflicts**: Cannot occur (source always wins)

Example
~~~~~~~

.. code-block:: python

   from syncengine import SyncMode, SyncPair

   pair = SyncPair(
       source_root="/home/user/website",
       destination_root="/var/www/html",
       source_client=local_client,
       destination_client=remote_client,
       mode=SyncMode.SOURCE_TO_DESTINATION
   )

   stats = engine.sync_pair(pair)

Scenarios
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Change
     - Action
   * - Add file at source
     - Upload to destination
   * - Add file at destination
     - Delete at destination (not in source)
   * - Modify file at source
     - Upload to destination
   * - Modify file at destination
     - Overwrite with source version
   * - Delete file at source
     - Delete at destination
   * - Delete file at destination
     - Re-upload from source
   * - Rename file at source
     - Rename at destination (old file deleted)

Best Practices
~~~~~~~~~~~~~~

* Use for deployment scenarios (dev → prod)
* Use for distributing files to multiple locations
* Ensure source is always the authoritative version
* Be careful with deletions (propagated to destination)

SOURCE_BACKUP Mode
------------------

**Use case**: Backup source to destination without ever deleting from source. Upload-only backup.

Behavior
~~~~~~~~

* **Uploads**: New/modified source files are uploaded to destination
* **Downloads**: Downloads destination changes to source
* **Source deletions**: NOT propagated to destination (backup preserved)
* **Destination deletions**: Ignored (files re-uploaded from source)
* **Renames/moves**: Applied to destination
* **Conflicts**: Source modifications win

Example
~~~~~~~

.. code-block:: python

   from syncengine import SyncMode, SyncPair

   pair = SyncPair(
       source_root="/home/user/photos",
       destination_root="/backup/photos",
       source_client=local_client,
       destination_client=backup_client,
       mode=SyncMode.SOURCE_BACKUP
   )

   stats = engine.sync_pair(pair)

Scenarios
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Change
     - Action
   * - Add file at source
     - Upload to destination
   * - Add file at destination
     - Download to source
   * - Modify file at source
     - Upload to destination
   * - Modify file at destination
     - Download to source
   * - Delete file at source
     - NO ACTION (backup preserved)
   * - Delete file at destination
     - Re-upload from source
   * - Rename file at source
     - Rename at destination (old backup kept)

Best Practices
~~~~~~~~~~~~~~

* Use for important data you never want to lose
* Great for photo/document backups
* Destination grows over time (deleted files remain)
* Periodically clean destination manually if needed
* Consider implementing versioning on destination

Use Cases
~~~~~~~~~

1. **Photo Backup**: Backup photos to cloud, never delete from cloud even if deleted locally
2. **Document Archive**: Archive important documents without risk of accidental deletion
3. **Code History**: Keep all versions of code files even if deleted from working directory

DESTINATION_TO_SOURCE Mode
--------------------------

**Use case**: One-way mirror from destination to source. Destination is the authoritative copy.

Behavior
~~~~~~~~

* **Uploads**: Never uploads (source changes ignored)
* **Downloads**: New/modified destination files are downloaded to source
* **Source deletions**: Ignored (files re-downloaded from destination)
* **Destination deletions**: Propagated to source
* **Renames/moves**: Applied to source only
* **Conflicts**: Cannot occur (destination always wins)

Example
~~~~~~~

.. code-block:: python

   from syncengine import SyncMode, SyncPair

   pair = SyncPair(
       source_root="/home/user/downloads",
       destination_root="/cloud/shared_files",
       source_client=local_client,
       destination_client=cloud_client,
       mode=SyncMode.DESTINATION_TO_SOURCE
   )

   stats = engine.sync_pair(pair)

Scenarios
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Change
     - Action
   * - Add file at source
     - Delete at source (not in destination)
   * - Add file at destination
     - Download to source
   * - Modify file at source
     - Overwrite with destination version
   * - Modify file at destination
     - Download to source
   * - Delete file at source
     - Re-download from destination
   * - Delete file at destination
     - Delete at source
   * - Rename file at destination
     - Rename at source (old file deleted)

Best Practices
~~~~~~~~~~~~~~

* Use for downloading content from authoritative remote source
* Use for receiving shared files from cloud
* Ensure destination is always the authoritative version
* Be careful with deletions (propagated to source)

Use Cases
~~~~~~~~~

1. **Cloud Download**: Download files from cloud to local (cloud is master)
2. **Shared Folders**: Receive updates from shared team folder
3. **Content Distribution**: Download content from master repository

DESTINATION_BACKUP Mode
------------------------

**Use case**: Backup destination to source without ever deleting from destination. Download-only backup.

Behavior
~~~~~~~~

* **Uploads**: Never uploads (source changes ignored)
* **Downloads**: New/modified destination files are downloaded to source
* **Source deletions**: Ignored (files re-downloaded from destination)
* **Destination deletions**: NOT propagated to source (backup preserved)
* **Renames/moves**: Applied to source
* **Conflicts**: Destination modifications win

Example
~~~~~~~

.. code-block:: python

   from syncengine import SyncMode, SyncPair

   pair = SyncPair(
       source_root="/home/user/backup",
       destination_root="/cloud/important_data",
       source_client=local_client,
       destination_client=cloud_client,
       mode=SyncMode.DESTINATION_BACKUP
   )

   stats = engine.sync_pair(pair)

Scenarios
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Change
     - Action
   * - Add file at source
     - NO ACTION (ignored)
   * - Add file at destination
     - Download to source
   * - Modify file at source
     - Overwrite with destination version
   * - Modify file at destination
     - Download to source
   * - Delete file at source
     - Re-download from destination
   * - Delete file at destination
     - NO ACTION (backup preserved)
   * - Rename file at destination
     - Rename at source (old backup kept)

Best Practices
~~~~~~~~~~~~~~

* Use for backing up remote data locally
* Great for disaster recovery scenarios
* Source grows over time (deleted remote files remain)
* Periodically clean source manually if needed
* Consider implementing versioning on source

Use Cases
~~~~~~~~~

1. **Cloud Backup**: Backup cloud data locally, keep deleted files
2. **Disaster Recovery**: Maintain local copy of critical remote data
3. **Archive**: Download and preserve historical data from remote source

Choosing the Right Mode
------------------------

Decision Tree
~~~~~~~~~~~~~

.. code-block:: text

   Do you need bidirectional sync?
   ├─ Yes → TWO_WAY
   └─ No → Do you need to upload or download?
       ├─ Upload → Do you want to delete from destination?
       │   ├─ Yes → SOURCE_TO_DESTINATION
       │   └─ No → SOURCE_BACKUP
       └─ Download → Do you want to delete from source?
           ├─ Yes → DESTINATION_TO_SOURCE
           └─ No → DESTINATION_BACKUP

Common Scenarios
~~~~~~~~~~~~~~~~

**Development Workflow**

* Local dev → Production server: ``SOURCE_TO_DESTINATION``
* Production → Local dev: ``DESTINATION_TO_SOURCE``
* Local ↔ Remote dev: ``TWO_WAY``

**Backup Scenarios**

* Local → Cloud backup (never delete): ``SOURCE_BACKUP``
* Cloud → Local backup (never delete): ``DESTINATION_BACKUP``
* Mirror backup: ``SOURCE_TO_DESTINATION`` or ``DESTINATION_TO_SOURCE``

**Content Management**

* Master → Distribution: ``SOURCE_TO_DESTINATION``
* Team shared folder: ``TWO_WAY``
* Content download: ``DESTINATION_TO_SOURCE``

Mode Properties
---------------

You can check mode properties programmatically:

.. code-block:: python

   from syncengine import SyncMode

   mode = SyncMode.TWO_WAY

   # Check capabilities
   print(f"Allows upload: {mode.allows_upload}")
   print(f"Allows download: {mode.allows_download}")
   print(f"Allows source delete: {mode.allows_source_delete}")
   print(f"Allows dest delete: {mode.allows_destination_delete}")
   print(f"Is bidirectional: {mode.is_bidirectional}")

   # Check scan requirements
   print(f"Requires source scan: {mode.requires_source_scan}")
   print(f"Requires dest scan: {mode.requires_destination_scan}")

Mode Aliases
------------

SyncEngine supports friendly aliases for modes:

.. code-block:: python

   from syncengine import SyncMode

   # These are equivalent:
   mode = SyncMode.from_string("twoWay")
   mode = SyncMode.from_string("tw")

   mode = SyncMode.from_string("sourceToDestination")
   mode = SyncMode.from_string("std")
   mode = SyncMode.from_string("localtocloud")

   mode = SyncMode.from_string("destinationToSource")
   mode = SyncMode.from_string("dts")
   mode = SyncMode.from_string("cloudtolocal")

   mode = SyncMode.from_string("sourceBackup")
   mode = SyncMode.from_string("sb")
   mode = SyncMode.from_string("localbackup")

   mode = SyncMode.from_string("destinationBackup")
   mode = SyncMode.from_string("db")
   mode = SyncMode.from_string("cloudbackup")

Next Steps
----------

* :doc:`concepts` - Deep dive into state management and conflict resolution
* :doc:`examples` - Example code for each mode
* :doc:`api_reference` - Complete API documentation
