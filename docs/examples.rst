Examples
========

This page provides complete, working examples for common SyncEngine use cases.

Basic Examples
--------------

Simple Two-Way Sync
~~~~~~~~~~~~~~~~~~~~

The most basic usage - keep two directories in sync:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       LocalStorageClient,
       SyncStateManager
   )
   from pathlib import Path

   def simple_two_way_sync():
       """Simple two-way sync between two local directories."""

       # Create storage clients
       source_client = LocalStorageClient()
       dest_client = LocalStorageClient()

       # Create state manager
       state_manager = SyncStateManager(
           Path("/home/user/documents/.sync_state")
       )

       # Create entries manager factory
       def create_entries_manager(client, storage_id):
           return LocalEntriesManager(client)

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager,
           state_manager=state_manager
       )

       # Create sync pair
       pair = SyncPair(
           source_root="/home/user/documents",
           destination_root="/backup/documents",
           source_client=source_client,
           destination_client=dest_client,
           mode=SyncMode.TWO_WAY
       )

       # Perform sync
       stats = engine.sync_pair(pair)

       # Print results
       print(f"Sync complete!")
       print(f"  Uploaded: {stats['uploads']}")
       print(f"  Downloaded: {stats['downloads']}")
       print(f"  Deleted: {stats['deletes']}")
       print(f"  Renamed: {stats.get('renames', 0)}")

   if __name__ == "__main__":
       simple_two_way_sync()

One-Way Backup
~~~~~~~~~~~~~~

Backup files to cloud without deleting:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       LocalStorageClient,
       IgnoreFileManager
   )
   from pathlib import Path

   def backup_to_cloud():
       """One-way backup to cloud, never deleting from cloud."""

       # Create storage clients
       local_client = LocalStorageClient()
       cloud_client = MyCloudStorageClient()  # Your cloud implementation

       # Create ignore manager
       ignore_manager = IgnoreFileManager()
       ignore_manager.load_from_file(Path("/home/user/photos/.syncignore"))

       # Add additional patterns
       ignore_manager.add_pattern("*.tmp")
       ignore_manager.add_pattern(".DS_Store")

       # Create sync engine
       def create_entries_manager(client, storage_id):
           return CloudEntriesManager(client, storage_id)

       engine = SyncEngine(
           client=cloud_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair with SOURCE_BACKUP mode
       pair = SyncPair(
           source_root="/home/user/photos",
           destination_root="/backup/photos",
           source_client=local_client,
           destination_client=cloud_client,
           mode=SyncMode.SOURCE_BACKUP,
           ignore_manager=ignore_manager
       )

       # Perform backup
       stats = engine.sync_pair(pair)

       print(f"Backup complete!")
       print(f"  Files uploaded: {stats['uploads']}")
       print(f"  Files skipped: {stats.get('skipped', 0)}")

   if __name__ == "__main__":
        backup_to_cloud()

Initial Sync with TWO_WAY Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control first-time sync behavior when using TWO_WAY mode (new in v0.3.0):

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       InitialSyncPreference
   )
   from pathlib import Path

   def vault_restoration():
       """Restore files from cloud vault to local (cloud is master)."""

       # Create sync engine
       engine = SyncEngine(
           client=cloud_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/vault/documents",
           sync_mode=SyncMode.TWO_WAY,
           storage_id=0
       )

       # First sync: Download from vault, make destination authoritative
       stats = engine.sync_pair(
           pair,
           initial_sync_preference=InitialSyncPreference.DESTINATION_WINS
       )
       # Result: Downloads all vault files, deletes local-only files

       print(f"Vault restoration complete!")
       print(f"  Downloaded: {stats['downloads']} files")
       print(f"  Deleted local: {stats['deletes_local']} files")

       # Subsequent syncs: Normal TWO_WAY (bidirectional)
       stats2 = engine.sync_pair(pair)
       # Now syncs changes in both directions

   def first_time_backup():
       """First backup of local files to cloud (local is master)."""

       # Create sync engine
       engine = SyncEngine(
           client=cloud_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/photos"),
           destination="/backup/photos",
           sync_mode=SyncMode.TWO_WAY,
           storage_id=0
       )

       # First sync: Upload to cloud, make source authoritative
       stats = engine.sync_pair(
           pair,
           initial_sync_preference=InitialSyncPreference.SOURCE_WINS
       )
       # Result: Uploads all local files, deletes cloud-only files

       print(f"Initial backup complete!")
       print(f"  Uploaded: {stats['uploads']} files")
       print(f"  Deleted remote: {stats['deletes_remote']} files")

   def merge_directories():
       """Merge local and cloud files without losing anything."""

       # Create sync engine
       engine = SyncEngine(
           client=cloud_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/projects"),
           destination="/cloud/projects",
           sync_mode=SyncMode.TWO_WAY,
           storage_id=0
       )

       # First sync: Merge both sides (MERGE is default if omitted)
       stats = engine.sync_pair(
           pair,
           initial_sync_preference=InitialSyncPreference.MERGE  # or omit
       )
       # Result: Downloads cloud files, uploads local files, NO deletions

       print(f"Directory merge complete!")
       print(f"  Uploaded: {stats['uploads']} files")
       print(f"  Downloaded: {stats['downloads']} files")
       print(f"  Deletions: {stats['deletes_local'] + stats['deletes_remote']}")
       # Deletions will be 0 for MERGE mode

   if __name__ == "__main__":
       # Example 1: Restore from cloud vault
       vault_restoration()

       # Example 2: First backup to cloud
       first_time_backup()

       # Example 3: Merge without losing files
       merge_directories()

Advanced Examples
-----------------

Progress Tracking with Rich UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monitor sync progress with a rich terminal UI using the new v0.2.0 progress tracking API:

Upload Progress with Rich UI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       SyncProgressTracker,
       SyncProgressEvent,
       SyncProgressInfo
   )
   from rich.progress import (
       Progress,
       SpinnerColumn,
       TextColumn,
       BarColumn,
       DownloadColumn,
       TransferSpeedColumn,
       TimeRemainingColumn
   )
   from pathlib import Path

   def sync_with_rich_progress():
       """Sync with rich progress UI."""

       # Create Rich progress display
       progress = Progress(
           SpinnerColumn(),
           TextColumn("[bold blue]{task.description}"),
           BarColumn(),
           DownloadColumn(),
           TransferSpeedColumn(),
           TimeRemainingColumn(),
       )

       progress.start()

       # Track tasks by directory
       tasks = {}

       def progress_callback(info: SyncProgressInfo):
           """Handle progress events."""

           if info.event == SyncProgressEvent.SCAN_DIR_START:
               print(f"📁 Scanning: {info.directory}")

           elif info.event == SyncProgressEvent.UPLOAD_BATCH_START:
               # Starting batch upload for a folder
               task = progress.add_task(
                   f"Uploading {info.directory}",
                   total=info.folder_bytes_total
               )
               tasks[info.directory] = task

           elif info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS:
               # File upload progress
               task_id = tasks.get(info.directory)
               if task_id is not None:
                   progress.update(
                       task_id,
                       completed=info.folder_bytes_uploaded,
                       description=f"Uploading {info.file_path}",
                   )

           elif info.event == SyncProgressEvent.UPLOAD_FILE_ERROR:
               print(f"❌ Error: {info.file_path} - {info.error_message}")

           elif info.event == SyncProgressEvent.UPLOAD_BATCH_COMPLETE:
               # Batch complete
               if info.directory in tasks:
                   progress.remove_task(tasks[info.directory])
                   del tasks[info.directory]

       # Create progress tracker
       tracker = SyncProgressTracker(callback=progress_callback)

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/backup/documents",
           sync_mode=SyncMode.SOURCE_TO_DESTINATION,
           storage_id=0
       )

       try:
           # Perform sync with progress tracking
           stats = engine.sync_pair(
               pair,
               sync_progress_tracker=tracker,
               max_workers=4
           )

           print(f"\n✓ Sync complete!")
           print(f"  Uploaded: {stats['uploads']} files")
           print(f"  Errors: {stats.get('errors', 0)} files")

       finally:
           progress.stop()

   if __name__ == "__main__":
       sync_with_rich_progress()

Download Progress with Rich UI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Monitor folder downloads with rich progress UI:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncProgressTracker,
       SyncProgressEvent,
       SyncProgressInfo
   )
   from rich.progress import (
       Progress,
       SpinnerColumn,
       TextColumn,
       BarColumn,
       DownloadColumn,
       TransferSpeedColumn,
       TimeRemainingColumn
   )
   from pathlib import Path

   def download_with_rich_progress():
       """Download folder with rich progress UI."""

       # Create Rich progress display
       progress = Progress(
           SpinnerColumn(),
           TextColumn("[bold green]{task.description}"),
           BarColumn(),
           DownloadColumn(),
           TransferSpeedColumn(),
           TimeRemainingColumn(),
       )

       progress.start()

       # Track current download task
       current_task = None

       def progress_callback(info: SyncProgressInfo):
           """Handle download progress events."""
           nonlocal current_task

           if info.event == SyncProgressEvent.DOWNLOAD_BATCH_START:
               # Starting batch download
               current_task = progress.add_task(
                   f"Downloading {info.directory}",
                   total=info.folder_bytes_total
               )

           elif info.event == SyncProgressEvent.DOWNLOAD_FILE_PROGRESS:
               # File download progress
               if current_task is not None:
                   progress.update(
                       current_task,
                       completed=info.folder_bytes_downloaded,
                       description=f"Downloading {info.file_path}",
                   )

           elif info.event == SyncProgressEvent.DOWNLOAD_FILE_ERROR:
               print(f"\n❌ Error: {info.file_path} - {info.error_message}")

           elif info.event == SyncProgressEvent.DOWNLOAD_BATCH_COMPLETE:
               # Batch complete
               if current_task is not None:
                   progress.remove_task(current_task)
                   current_task = None

       # Create progress tracker
       tracker = SyncProgressTracker(callback=progress_callback)

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       try:
           # Download folder with progress tracking
           stats = engine.download_folder(
               destination_path="/remote/documents",
               local_path=Path("/home/user/downloads"),
               sync_progress_tracker=tracker
           )

           print(f"\n✓ Download complete!")
           print(f"  Downloaded: {stats['downloads']} files")
           print(f"  Errors: {stats.get('errors', 0)} files")

       finally:
           progress.stop()

   if __name__ == "__main__":
       download_with_rich_progress()

Combined Upload and Download Progress
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Handle both upload and download events in a single callback:

.. code-block:: python

   from syncengine import SyncProgressTracker, SyncProgressEvent, SyncProgressInfo
   from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

   def unified_progress_callback():
       """Single callback for both upload and download progress."""

       progress = Progress(
           SpinnerColumn(),
           TextColumn("[bold]{task.description}"),
           BarColumn(),
       )

       progress.start()
       tasks = {}

       def handle_progress(info: SyncProgressInfo):
           """Handle both upload and download events."""

           # Upload events
           if info.event == SyncProgressEvent.UPLOAD_BATCH_START:
               task = progress.add_task(
                   f"⬆️  Uploading {info.directory}",
                   total=info.folder_bytes_total
               )
               tasks[('upload', info.directory)] = task

           elif info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS:
               task_id = tasks.get(('upload', info.directory))
               if task_id is not None:
                   progress.update(task_id, completed=info.folder_bytes_uploaded)

           elif info.event == SyncProgressEvent.UPLOAD_BATCH_COMPLETE:
               task_id = tasks.get(('upload', info.directory))
               if task_id is not None:
                   progress.remove_task(task_id)
                   del tasks[('upload', info.directory)]

           # Download events
           elif info.event == SyncProgressEvent.DOWNLOAD_BATCH_START:
               task = progress.add_task(
                   f"⬇️  Downloading {info.directory}",
                   total=info.folder_bytes_total
               )
               tasks[('download', info.directory)] = task

           elif info.event == SyncProgressEvent.DOWNLOAD_FILE_PROGRESS:
               task_id = tasks.get(('download', info.directory))
               if task_id is not None:
                   progress.update(task_id, completed=info.folder_bytes_downloaded)

           elif info.event == SyncProgressEvent.DOWNLOAD_BATCH_COMPLETE:
               task_id = tasks.get(('download', info.directory))
               if task_id is not None:
                   progress.remove_task(task_id)
                   del tasks[('download', info.directory)]

           # Error events
           elif info.event in (SyncProgressEvent.UPLOAD_FILE_ERROR,
                              SyncProgressEvent.DOWNLOAD_FILE_ERROR):
               print(f"\n❌ Error: {info.file_path} - {info.error_message}")

       return handle_progress, progress

   # Usage
   callback, progress_display = unified_progress_callback()
   tracker = SyncProgressTracker(callback=callback)

   try:
       # Use for both sync and download operations
       engine.sync_pair(pair, sync_progress_tracker=tracker)
       engine.download_folder(path, local, sync_progress_tracker=tracker)
   finally:
       progress_display.stop()

Upload with Skip and Rename
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Upload files with duplicate handling using skip and rename features (new in v0.2.0):

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       SyncProgressTracker,
       SyncProgressEvent,
       SyncProgressInfo
   )
   from pathlib import Path

   def upload_with_duplicate_handling():
       """Upload with skip and rename support."""

       # Files to skip (e.g., duplicates)
       files_to_skip = {
           "folder/duplicate1.txt",
           "folder/duplicate2.txt",
       }

       # Files to rename during upload
       file_renames = {
           "old_name.txt": "new_name.txt",
           "folder/conflict.txt": "folder/conflict_renamed.txt",
       }

       # Simple progress callback
       def progress_callback(info: SyncProgressInfo):
           if info.event == SyncProgressEvent.UPLOAD_FILE_START:
               print(f"⬆️  Uploading: {info.file_path}")
           elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
               print(f"✓ Complete: {info.file_path}")

       # Create progress tracker
       tracker = SyncProgressTracker(callback=progress_callback)

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/backup",
           sync_mode=SyncMode.SOURCE_TO_DESTINATION,
           storage_id=0
       )

       # Execute with skip and rename
       stats = engine.sync_pair(
           pair,
           sync_progress_tracker=tracker,
           files_to_skip=files_to_skip,      # Skip these files
           file_renames=file_renames,        # Rename during upload
           max_workers=4,
       )

       print(f"\n✓ Upload complete!")
       print(f"  Uploaded: {stats['uploads']} files")
       print(f"  Skipped: {stats.get('skips', 0)} files")

   if __name__ == "__main__":
       upload_with_duplicate_handling()

Upload to Specific Folder ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Upload directly into a specific folder without path resolution (new in v0.2.0):

.. code-block:: python

   from syncengine import SyncEngine, SyncMode, SyncPair
   from pathlib import Path

   def upload_to_folder_id():
       """Upload into folder ID 1234."""

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair with parent_id
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/remote_folder",
           sync_mode=SyncMode.SOURCE_TO_DESTINATION,
           storage_id=0,
           parent_id=1234,  # Upload into this folder
       )

       # Execute upload
       stats = engine.sync_pair(pair)

       print(f"Uploaded: {stats['uploads']} files into folder 1234")

   if __name__ == "__main__":
       upload_to_folder_id()

Force Upload/Download for Replace Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Force re-upload or re-download files to replace existing copies (new in v0.2.0):

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       SyncProgressTracker,
       SyncProgressEvent,
       SyncProgressInfo
   )
   from pathlib import Path

   def replace_existing_files():
       """Replace existing files using force_upload."""

       # Detect which files exist on remote (your duplicate detection logic)
       remote_duplicates = detect_remote_duplicates(local_files)

       # Determine if force upload is needed
       force_upload = len(remote_duplicates) > 0

       # Optional: Files to skip (user chose "skip" action)
       files_to_skip = {
           "file1.txt",  # User wants to skip this
           "file2.txt",
       }

       # Optional: Files to rename (user chose "rename" action)
       file_renames = {
           "conflict.txt": "conflict (1).txt",
       }

       # Progress callback
       def progress_callback(info: SyncProgressInfo):
           if info.event == SyncProgressEvent.UPLOAD_FILE_START:
               print(f"⬆️  Uploading: {info.file_path}")
           elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
               print(f"✓ Complete: {info.file_path}")

       # Create progress tracker
       tracker = SyncProgressTracker(callback=progress_callback)

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/backup",
           sync_mode=SyncMode.SOURCE_TO_DESTINATION,
           storage_id=0
       )

       # Upload with force (replaces existing files)
       stats = engine.sync_pair(
           pair,
           sync_progress_tracker=tracker,
           force_upload=force_upload,      # Force upload for replace
           files_to_skip=files_to_skip,    # Still skip these
           file_renames=file_renames,      # And rename these
           max_workers=4,
       )

       print(f"\n✓ Replace complete!")
       print(f"  Uploaded: {stats['uploads']} files")
       print(f"  Skipped: {stats.get('skips', 0)} files")

       # Now delete old duplicates (optional)
       if force_upload and remote_duplicates:
           print(f"  Deleting {len(remote_duplicates)} old duplicates...")
           for entry_id in remote_duplicates:
               client.delete_entries([entry_id])

   def force_download_refresh():
       """Force download all files to refresh local copies."""

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair for download
       pair = SyncPair(
           source=Path("/home/user/documents"),
           destination="/cloud/documents",
           sync_mode=SyncMode.DESTINATION_TO_SOURCE,
           storage_id=0
       )

       # Force download all files (even if they match local)
       stats = engine.sync_pair(
           pair,
           force_download=True,  # Bypass comparison, download all
       )

       print(f"Downloaded: {stats['downloads']} files (forced refresh)")

   if __name__ == "__main__":
       # Example 1: Replace existing files with force upload
       replace_existing_files()

       # Example 2: Refresh local files with force download
       force_download_refresh()

Pause/Resume/Cancel Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control sync execution with pause, resume, and cancel:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncPair,
       SyncMode,
       SyncPauseController
   )
   import threading
   import time
   import signal
   import sys

   class ControlledSync:
       """Sync with pause/resume/cancel support."""

       def __init__(self):
           self.controller = SyncPauseController()
           self.engine = SyncEngine(
               client=dest_client,
               entries_manager_factory=create_entries_manager,
               pause_controller=self.controller
           )
           self.sync_thread = None

       def start_sync(self, pair: SyncPair):
           """Start sync in background thread."""
           def run():
               print("Starting sync...")
               stats = self.engine.sync_pair(pair)
               print(f"Sync complete: {stats}")

           self.sync_thread = threading.Thread(target=run)
           self.sync_thread.start()

       def pause(self):
           """Pause sync."""
           print("Pausing sync...")
           self.controller.pause()
           print("Sync paused")

       def resume(self):
           """Resume sync."""
           print("Resuming sync...")
           self.controller.resume()
           print("Sync resumed")

       def cancel(self):
           """Cancel sync."""
           print("Cancelling sync...")
           self.controller.cancel()
           print("Sync cancelled")

       def wait(self):
           """Wait for sync to complete."""
           if self.sync_thread:
               self.sync_thread.join()

   def main():
       """Main function with signal handlers."""
       sync = ControlledSync()

       # Set up signal handlers
       def handle_sigusr1(signum, frame):
           sync.pause()

       def handle_sigusr2(signum, frame):
           sync.resume()

       def handle_sigint(signum, frame):
           sync.cancel()
           sys.exit(0)

       signal.signal(signal.SIGUSR1, handle_sigusr1)
       signal.signal(signal.SIGUSR2, handle_sigusr2)
       signal.signal(signal.SIGINT, handle_sigint)

       # Create sync pair
       pair = SyncPair(
           source_root="/home/user/documents",
           destination_root="/backup/documents",
           source_client=source_client,
           destination_client=dest_client,
           mode=SyncMode.TWO_WAY
       )

       # Start sync
       sync.start_sync(pair)

       # Wait for sync to complete
       sync.wait()

   if __name__ == "__main__":
       main()

Multiple Sync Pairs
~~~~~~~~~~~~~~~~~~~

Sync multiple directory pairs in parallel:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncPair,
       SyncMode,
       ConcurrencyLimits
   )
   from concurrent.futures import ThreadPoolExecutor, as_completed

   def sync_multiple_pairs():
       """Sync multiple directory pairs in parallel."""

       # Create sync engine with concurrency limits
       limits = ConcurrencyLimits(transfers=3, operations=10)
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager,
           concurrency_limits=limits
       )

       # Define sync pairs
       pairs = [
           SyncPair(
               source_root="/home/user/documents",
               destination_root="/backup/documents",
               source_client=source_client,
               destination_client=dest_client,
               mode=SyncMode.TWO_WAY
           ),
           SyncPair(
               source_root="/home/user/photos",
               destination_root="/backup/photos",
               source_client=source_client,
               destination_client=dest_client,
               mode=SyncMode.SOURCE_BACKUP
           ),
           SyncPair(
               source_root="/home/user/music",
               destination_root="/backup/music",
               source_client=source_client,
               destination_client=dest_client,
               mode=SyncMode.SOURCE_TO_DESTINATION
           )
       ]

       # Sync all pairs in parallel
       with ThreadPoolExecutor(max_workers=3) as executor:
           # Submit all sync jobs
           futures = {
               executor.submit(engine.sync_pair, pair): pair
               for pair in pairs
           }

           # Collect results as they complete
           for future in as_completed(futures):
               pair = futures[future]
               try:
                   stats = future.result()
                   print(f"\nSync complete for {pair.source_root}:")
                   print(f"  Uploaded: {stats['uploads']}")
                   print(f"  Downloaded: {stats['downloads']}")
                   print(f"  Deleted: {stats['deletes']}")
               except Exception as e:
                   print(f"\nSync failed for {pair.source_root}: {e}")

   if __name__ == "__main__":
       sync_multiple_pairs()

Conflict Resolution
~~~~~~~~~~~~~~~~~~~

Handle conflicts with custom resolution logic:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncPair,
       SyncMode,
       ConflictResolution
   )

   def resolve_conflict(source_file, dest_file):
       """Custom conflict resolution function.

       Args:
           source_file: Source file info
           dest_file: Destination file info

       Returns:
           'source', 'destination', or 'skip'
       """
       print(f"\nConflict detected: {source_file.path}")
       print(f"  Source modified: {source_file.mtime}")
       print(f"  Destination modified: {dest_file.mtime}")
       print(f"  Source size: {source_file.size} bytes")
       print(f"  Destination size: {dest_file.size} bytes")

       # Custom logic: choose larger file
       if source_file.size > dest_file.size:
           print("  Resolution: Using source (larger)")
           return 'source'
       elif dest_file.size > source_file.size:
           print("  Resolution: Using destination (larger)")
           return 'destination'
       else:
           # Same size, use newer
           if source_file.mtime > dest_file.mtime:
               print("  Resolution: Using source (newer)")
               return 'source'
           else:
               print("  Resolution: Using destination (newer)")
               return 'destination'

   def sync_with_conflict_resolution():
       """Sync with custom conflict resolution."""

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair with manual conflict resolution
       pair = SyncPair(
           source_root="/home/user/documents",
           destination_root="/backup/documents",
           source_client=source_client,
           destination_client=dest_client,
           mode=SyncMode.TWO_WAY,
           conflict_resolution=ConflictResolution.MANUAL,
           conflict_handler=resolve_conflict
       )

       # Perform sync
       stats = engine.sync_pair(pair)

       print(f"\nSync complete!")
       print(f"  Conflicts resolved: {stats.get('conflicts', 0)}")

   if __name__ == "__main__":
       sync_with_conflict_resolution()

Configuration File
~~~~~~~~~~~~~~~~~~

Load sync configuration from JSON:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       load_sync_pairs_from_json,
       SyncConfigError
   )
   from pathlib import Path
   import json

   # Create config file
   config = {
       "pairs": [
           {
               "source_root": "/home/user/documents",
               "destination_root": "/backup/documents",
               "mode": "twoWay",
               "ignore_patterns": ["*.tmp", ".DS_Store"]
           },
           {
               "source_root": "/home/user/photos",
               "destination_root": "/backup/photos",
               "mode": "sourceBackup"
           }
       ]
   }

   # Save config
   config_path = Path("sync_config.json")
   with open(config_path, 'w') as f:
       json.dump(config, f, indent=2)

   # Load and use config
   try:
       pairs = load_sync_pairs_from_json(config_path)

       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       for pair in pairs:
           print(f"Syncing {pair.source_root}...")
           stats = engine.sync_pair(pair)
           print(f"  Complete: {stats}")

   except SyncConfigError as e:
       print(f"Config error: {e}")

Integration Examples
--------------------

AWS S3 Integration
~~~~~~~~~~~~~~~~~~

See :doc:`protocols` for complete S3 implementation.

.. code-block:: python

   from syncengine import SyncEngine, SyncPair, SyncMode
   from my_s3_client import S3StorageClient, S3EntriesManager

   def sync_to_s3():
       """Sync local files to AWS S3."""

       # Create S3 client
       s3_client = S3StorageClient(
           bucket='my-backup-bucket',
           prefix='documents',
           region_name='us-west-2'
       )

       # Create entries manager factory
       def create_entries_manager(client, storage_id):
           return S3EntriesManager(client, 'my-backup-bucket', 'documents')

       # Create sync engine
       engine = SyncEngine(
           client=s3_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source_root="/home/user/documents",
           destination_root="",
           source_client=local_client,
           destination_client=s3_client,
           mode=SyncMode.SOURCE_TO_DESTINATION
       )

       # Sync to S3
       stats = engine.sync_pair(pair)
       print(f"Synced to S3: {stats}")

   if __name__ == "__main__":
       sync_to_s3()

Google Drive Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from syncengine import SyncEngine, SyncPair, SyncMode
   from my_gdrive_client import GDriveStorageClient, GDriveEntriesManager

   def sync_to_gdrive():
       """Sync local files to Google Drive."""

       # Create Google Drive client
       gdrive_client = GDriveStorageClient(
           credentials_path='credentials.json',
           root_folder_id='your-folder-id'
       )

       # Create entries manager factory
       def create_entries_manager(client, storage_id):
           return GDriveEntriesManager(client, storage_id)

       # Create sync engine
       engine = SyncEngine(
           client=gdrive_client,
           entries_manager_factory=create_entries_manager
       )

       # Create sync pair
       pair = SyncPair(
           source_root="/home/user/documents",
           destination_root="Documents",
           source_client=local_client,
           destination_client=gdrive_client,
           mode=SyncMode.TWO_WAY
       )

       # Sync to Google Drive
       stats = engine.sync_pair(pair)
       print(f"Synced to Google Drive: {stats}")

   if __name__ == "__main__":
       sync_to_gdrive()

Scheduled Sync
~~~~~~~~~~~~~~

Run sync on a schedule using APScheduler:

.. code-block:: python

   from syncengine import SyncEngine, SyncPair, SyncMode
   from apscheduler.schedulers.blocking import BlockingScheduler
   import logging

   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s'
   )
   logger = logging.getLogger(__name__)

   def scheduled_sync():
       """Perform scheduled sync."""
       try:
           logger.info("Starting scheduled sync...")

           # Create sync engine
           engine = SyncEngine(
               client=dest_client,
               entries_manager_factory=create_entries_manager
           )

           # Create sync pair
           pair = SyncPair(
               source_root="/home/user/documents",
               destination_root="/backup/documents",
               source_client=source_client,
               destination_client=dest_client,
               mode=SyncMode.TWO_WAY
           )

           # Perform sync
           stats = engine.sync_pair(pair)

           logger.info(f"Sync complete: {stats}")

       except Exception as e:
           logger.error(f"Sync failed: {e}", exc_info=True)

   def main():
       """Run scheduled sync."""
       scheduler = BlockingScheduler()

       # Schedule sync every hour
       scheduler.add_job(
           scheduled_sync,
           'interval',
           hours=1,
           id='hourly_sync'
       )

       # Schedule sync at 2 AM daily
       scheduler.add_job(
           scheduled_sync,
           'cron',
           hour=2,
           id='daily_sync'
       )

       logger.info("Starting scheduler...")
       try:
           scheduler.start()
       except (KeyboardInterrupt, SystemExit):
           logger.info("Scheduler stopped")

   if __name__ == "__main__":
       main()

Next Steps
----------

* :doc:`api_reference` - Complete API documentation
* :doc:`protocols` - Implement custom storage backends
* :doc:`concepts` - Deep dive into core concepts
* :doc:`sync_modes` - Understand sync modes
