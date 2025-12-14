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

Advanced Examples
-----------------

Progress Tracking with Rich UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monitor sync progress with a rich terminal UI:

.. code-block:: python

   from syncengine import (
       SyncEngine,
       SyncMode,
       SyncPair,
       SyncProgressTracker,
       SyncProgressEvent
   )
   from rich.console import Console
   from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

   class RichProgressUI:
       """Rich terminal UI for sync progress."""
       
       def __init__(self):
           self.console = Console()
           self.progress = Progress(
               SpinnerColumn(),
               TextColumn("[progress.description]{task.description}"),
               BarColumn(),
               TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
               console=self.console
           )
           self.current_task = None
       
       def on_progress(self, event: SyncProgressEvent):
           """Handle progress events."""
           if event.type == "scan_start":
               self.console.print("[bold blue]Starting file scan...[/]")
           
           elif event.type == "scan_complete":
               self.console.print(
                   f"[bold green]Scan complete:[/] {event.total} files"
               )
           
           elif event.type == "sync_start":
               self.console.print(
                   f"[bold blue]Starting sync of {event.total_files} files...[/]"
               )
               self.progress.start()
           
           elif event.type == "upload_start":
               self.current_task = self.progress.add_task(
                   f"Uploading {event.file_path}",
                   total=event.file_size
               )
           
           elif event.type == "upload_progress":
               self.progress.update(
                   self.current_task,
                   completed=event.bytes_transferred
               )
           
           elif event.type == "upload_complete":
               self.progress.remove_task(self.current_task)
           
           elif event.type == "download_start":
               self.current_task = self.progress.add_task(
                   f"Downloading {event.file_path}",
                   total=event.file_size
               )
           
           elif event.type == "download_progress":
               self.progress.update(
                   self.current_task,
                   completed=event.bytes_transferred
               )
           
           elif event.type == "download_complete":
               self.progress.remove_task(self.current_task)
           
           elif event.type == "sync_complete":
               self.progress.stop()
               self.console.print("\n[bold green]Sync complete![/]")
               self.console.print(f"  Uploaded: {event.stats['uploads']}")
               self.console.print(f"  Downloaded: {event.stats['downloads']}")
               self.console.print(f"  Deleted: {event.stats['deletes']}")

   def sync_with_progress():
       """Sync with rich progress UI."""
       
       # Create UI and progress tracker
       ui = RichProgressUI()
       tracker = SyncProgressTracker(callback=ui.on_progress)
       
       # Create sync engine with progress tracker
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager,
           progress_tracker=tracker
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

   if __name__ == "__main__":
       sync_with_progress()

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
