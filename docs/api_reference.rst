API Reference
=============

This page provides detailed API documentation for all public classes, functions, and constants in SyncEngine.

Core Classes
------------

SyncEngine
~~~~~~~~~~

.. class:: SyncEngine(client, entries_manager_factory, output=None, state_manager=None, pause_controller=None, concurrency_limits=None, spinner_factory=None, progress_bar_factory=None)

   Core sync engine that orchestrates file synchronization.

   :param StorageClientProtocol client: Storage API client
   :param Callable entries_manager_factory: Factory function that creates FileEntriesManagerProtocol instances
   :param OutputHandlerProtocol output: Output handler for displaying progress (optional)
   :param SyncStateManager state_manager: State manager for tracking sync history (optional)
   :param SyncPauseController pause_controller: Controller for pause/resume/cancel (optional)
   :param ConcurrencyLimits concurrency_limits: Concurrency limits for transfers and operations (optional)
   :param SpinnerFactoryProtocol spinner_factory: Factory for creating progress spinners (optional)
   :param ProgressBarFactoryProtocol progress_bar_factory: Factory for creating progress bars (optional)

   .. method:: sync_pair(pair: SyncPair) -> dict[str, int]

      Execute synchronization for a sync pair.

      :param SyncPair pair: Sync pair to synchronize
      :returns: Dictionary with sync statistics (uploads, downloads, deletes, etc.)
      :rtype: dict[str, int]

   .. method:: sync_pairs(pairs: list[SyncPair]) -> list[dict[str, int]]

      Execute synchronization for multiple sync pairs.

      :param list[SyncPair] pairs: List of sync pairs to synchronize
      :returns: List of sync statistics for each pair
      :rtype: list[dict[str, int]]

   .. method:: download_folder(destination_path: str, local_path: Path, sync_progress_tracker: Optional[SyncProgressTracker] = None, parallel: bool = False, use_rich_progress: bool = True) -> dict[str, int]

      Download a folder from destination to local filesystem.

      :param str destination_path: Path in destination storage
      :param Path local_path: Local path to download to
      :param SyncProgressTracker sync_progress_tracker: Optional progress tracker for monitoring download progress (new in v0.2.0)
      :param bool parallel: Whether to download files in parallel (default: False)
      :param bool use_rich_progress: Whether to display Rich progress bar (default: True, automatically disabled when sync_progress_tracker is provided)
      :returns: Dictionary with download statistics (downloads, errors, etc.)
      :rtype: dict[str, int]

      .. note::

         When ``sync_progress_tracker`` is provided, the Rich progress bar is automatically disabled to avoid UI conflicts. The tracker will emit detailed download events:
         ``DOWNLOAD_BATCH_START``, ``DOWNLOAD_FILE_START``, ``DOWNLOAD_FILE_PROGRESS``, ``DOWNLOAD_FILE_COMPLETE``, ``DOWNLOAD_FILE_ERROR``, ``DOWNLOAD_BATCH_COMPLETE``.

SyncPair
~~~~~~~~

.. class:: SyncPair(source_root, destination_root, source_client, destination_client, mode=SyncMode.TWO_WAY, ignore_manager=None, conflict_resolution=ConflictResolution.NEWEST_WINS)

   Represents a source-destination pair for synchronization.

   :param str source_root: Root path of source directory
   :param str destination_root: Root path of destination directory
   :param StorageClientProtocol source_client: Storage client for source
   :param StorageClientProtocol destination_client: Storage client for destination
   :param SyncMode mode: Synchronization mode (default: TWO_WAY)
   :param IgnoreFileManager ignore_manager: Ignore pattern manager (optional)
   :param ConflictResolution conflict_resolution: Conflict resolution strategy (default: NEWEST_WINS)

   .. attribute:: source_root

      Root path of source directory.

   .. attribute:: destination_root

      Root path of destination directory.

   .. attribute:: mode

      Synchronization mode.

   .. attribute:: ignore_manager

      Ignore pattern manager.

Enums
-----

SyncMode
~~~~~~~~

.. class:: SyncMode

   Synchronization modes for different sync strategies.

   .. attribute:: TWO_WAY

      Bidirectional sync. Changes on either side are propagated to the other.

   .. attribute:: SOURCE_TO_DESTINATION

      One-way mirror from source to destination. Destination changes are overwritten.

   .. attribute:: SOURCE_BACKUP

      Upload-only backup. Never deletes from source.

   .. attribute:: DESTINATION_TO_SOURCE

      One-way mirror from destination to source. Source changes are overwritten.

   .. attribute:: DESTINATION_BACKUP

      Download-only backup. Never deletes from destination.

   .. classmethod:: from_string(value: str) -> SyncMode

      Parse sync mode from string, supporting abbreviations.

      :param str value: Mode string (full name or abbreviation)
      :returns: SyncMode enum value
      :rtype: SyncMode
      :raises ValueError: If mode string is not recognized

      Supported abbreviations:

      * ``tw`` → TWO_WAY
      * ``std`` → SOURCE_TO_DESTINATION
      * ``sb`` → SOURCE_BACKUP
      * ``dts`` → DESTINATION_TO_SOURCE
      * ``db`` → DESTINATION_BACKUP

   .. property:: allows_upload

      Check if this mode allows uploading files.

   .. property:: allows_download

      Check if this mode allows downloading files.

   .. property:: allows_source_delete

      Check if this mode allows deleting source files.

   .. property:: allows_destination_delete

      Check if this mode allows deleting destination files.

   .. property:: is_bidirectional

      Check if this mode syncs in both directions.

SyncAction
~~~~~~~~~~

.. class:: SyncAction

   Actions that can be taken for a file during sync.

   .. attribute:: UPLOAD_NEW

      Upload a new file to destination.

   .. attribute:: UPLOAD_UPDATE

      Upload changes to existing destination file.

   .. attribute:: UPLOAD_RESTORE

      Re-upload file that was deleted at destination.

   .. attribute:: DOWNLOAD_NEW

      Download a new file from destination.

   .. attribute:: DOWNLOAD_UPDATE

      Download changes to existing source file.

   .. attribute:: DOWNLOAD_RESTORE

      Re-download file that was deleted at source.

   .. attribute:: DELETE_SOURCE

      Delete file from source.

   .. attribute:: DELETE_DESTINATION

      Delete file from destination.

   .. attribute:: NO_ACTION

      File is already in sync, no action needed.

   .. attribute:: CONFLICT

      Manual resolution required.

State Management
----------------

SyncStateManager
~~~~~~~~~~~~~~~~

.. class:: SyncStateManager(state_dir: Path)

   Manages persistent sync state across sync sessions.

   :param Path state_dir: Directory to store state files

   .. method:: load_source_tree() -> SourceTree

      Load previous source state.

      :returns: Source tree from last sync
      :rtype: SourceTree

   .. method:: load_destination_tree() -> DestinationTree

      Load previous destination state.

      :returns: Destination tree from last sync
      :rtype: DestinationTree

   .. method:: save_source_tree(tree: SourceTree) -> None

      Save current source state.

      :param SourceTree tree: Source tree to save

   .. method:: save_destination_tree(tree: DestinationTree) -> None

      Save current destination state.

      :param DestinationTree tree: Destination tree to save

   .. method:: clear() -> None

      Clear all saved state.

SourceTree
~~~~~~~~~~

.. class:: SourceTree

   Tree structure representing source files.

   .. attribute:: items

      Dictionary mapping paths to SourceItemState.

DestinationTree
~~~~~~~~~~~~~~~

.. class:: DestinationTree

   Tree structure representing destination files.

   .. attribute:: items

      Dictionary mapping paths to DestinationItemState.

Ignore Patterns
---------------

IgnoreFileManager
~~~~~~~~~~~~~~~~~

.. class:: IgnoreFileManager(patterns: list[str] = None)

   Manages gitignore-style ignore patterns.

   :param list[str] patterns: Initial list of patterns (optional)

   .. method:: add_pattern(pattern: str) -> None

      Add an ignore pattern.

      :param str pattern: Pattern to add (gitignore syntax)

   .. method:: load_from_file(file_path: Path) -> None

      Load patterns from a file.

      :param Path file_path: Path to ignore file

   .. method:: should_ignore(path: str) -> bool

      Check if a path should be ignored.

      :param str path: Path to check
      :returns: True if path should be ignored
      :rtype: bool

   .. method:: clear() -> None

      Clear all patterns.

IgnoreRule
~~~~~~~~~~

.. class:: IgnoreRule(pattern: str, is_negation: bool = False)

   Represents a single ignore pattern rule.

   :param str pattern: Pattern string
   :param bool is_negation: True if this is a negation rule (!)

   .. method:: matches(path: str) -> bool

      Check if this rule matches a path.

      :param str path: Path to check
      :returns: True if rule matches path
      :rtype: bool

Concurrency
-----------

ConcurrencyLimits
~~~~~~~~~~~~~~~~~

.. class:: ConcurrencyLimits(transfers: int = 5, operations: int = 10)

   Concurrency limits for sync operations.

   :param int transfers: Maximum concurrent uploads/downloads (default: 5)
   :param int operations: Maximum concurrent file operations (default: 10)

   .. attribute:: transfers

      Maximum concurrent uploads/downloads.

   .. attribute:: operations

      Maximum concurrent file operations.

SyncPauseController
~~~~~~~~~~~~~~~~~~~

.. class:: SyncPauseController()

   Controller for pausing, resuming, and canceling sync operations.

   .. method:: pause() -> None

      Pause sync operations.

   .. method:: resume() -> None

      Resume paused sync operations.

   .. method:: cancel() -> None

      Cancel sync operations.

   .. method:: is_paused() -> bool

      Check if sync is paused.

      :returns: True if paused
      :rtype: bool

   .. method:: is_cancelled() -> bool

      Check if sync is cancelled.

      :returns: True if cancelled
      :rtype: bool

   .. method:: wait_if_paused() -> None

      Block until sync is resumed or cancelled.

Progress Tracking
-----------------

SyncProgressTracker
~~~~~~~~~~~~~~~~~~~

.. class:: SyncProgressTracker(callback: Callable[[SyncProgressEvent], None])

   Tracks and reports sync progress.

   :param Callable callback: Callback function for progress events

   .. method:: on_scan_start() -> None

      Called when file scanning starts.

   .. method:: on_scan_progress(scanned: int, total: int) -> None

      Called during file scanning.

      :param int scanned: Number of files scanned
      :param int total: Total files to scan

   .. method:: on_scan_complete(total: int) -> None

      Called when file scanning completes.

      :param int total: Total files scanned

   .. method:: on_sync_start(total_files: int) -> None

      Called when sync operations start.

      :param int total_files: Total files to sync

   .. method:: on_upload_start(file_path: str, file_size: int) -> None

      Called when file upload starts.

      :param str file_path: Path of file being uploaded
      :param int file_size: Size of file in bytes

   .. method:: on_upload_progress(file_path: str, bytes_transferred: int, total_bytes: int) -> None

      Called during file upload.

      :param str file_path: Path of file being uploaded
      :param int bytes_transferred: Bytes uploaded so far
      :param int total_bytes: Total bytes to upload

   .. method:: on_upload_complete(file_path: str) -> None

      Called when file upload completes.

      :param str file_path: Path of file uploaded

   .. method:: on_download_start(file_path: str, file_size: int) -> None

      Called when file download starts.

      :param str file_path: Path of file being downloaded
      :param int file_size: Size of file in bytes

   .. method:: on_download_progress(file_path: str, bytes_transferred: int, total_bytes: int) -> None

      Called during file download.

      :param str file_path: Path of file being downloaded
      :param int bytes_transferred: Bytes downloaded so far
      :param int total_bytes: Total bytes to download

   .. method:: on_download_complete(file_path: str) -> None

      Called when file download completes.

      :param str file_path: Path of file downloaded

   .. method:: on_download_batch_start(directory: str, num_files: int, total_bytes: int) -> None

      Called when batch download for a folder starts.

      :param str directory: Directory being downloaded
      :param int num_files: Number of files to download
      :param int total_bytes: Total bytes to download

   .. method:: on_download_file_start(file_path: str, file_size: int) -> None

      Called when individual file download starts.

      :param str file_path: Path of file being downloaded
      :param int file_size: Size of file in bytes

   .. method:: on_download_file_progress(file_path: str, bytes_downloaded: int, total_bytes: int) -> None

      Called during file download with progress updates.

      :param str file_path: Path of file being downloaded
      :param int bytes_downloaded: Bytes downloaded so far
      :param int total_bytes: Total bytes to download

   .. method:: on_download_file_complete(file_path: str) -> None

      Called when file download completes successfully.

      :param str file_path: Path of file downloaded

   .. method:: on_download_file_error(file_path: str, error: Exception) -> None

      Called when file download fails.

      :param str file_path: Path of file that failed
      :param Exception error: Error that occurred

   .. method:: on_download_batch_complete(directory: str, num_downloaded: int) -> None

      Called when batch download completes.

      :param str directory: Directory that was downloaded
      :param int num_downloaded: Number of files successfully downloaded

   .. method:: create_download_progress_callback(file_path: str) -> Callable[[int, int], None]

      Create a progress callback for download operations.

      :param str file_path: Path of file being downloaded
      :returns: Progress callback function
      :rtype: Callable[[int, int], None]

   .. method:: on_sync_complete(stats: dict[str, int]) -> None

      Called when all sync operations complete.

      :param dict stats: Sync statistics

SyncProgressEvent
~~~~~~~~~~~~~~~~~

.. class:: SyncProgressEvent

   Event types for progress callbacks.

   **Scan Events:**

   .. attribute:: SCAN_DIR_START

      Directory scanning started.

   .. attribute:: SCAN_DIR_COMPLETE

      Directory scanning completed.

   **Upload Events:**

   .. attribute:: UPLOAD_BATCH_START

      Batch upload for a folder started.

   .. attribute:: UPLOAD_FILE_START

      Individual file upload started.

   .. attribute:: UPLOAD_FILE_PROGRESS

      File upload progress update.

   .. attribute:: UPLOAD_FILE_COMPLETE

      File upload completed successfully.

   .. attribute:: UPLOAD_FILE_ERROR

      File upload failed.

   .. attribute:: UPLOAD_BATCH_COMPLETE

      Batch upload completed.

   **Download Events:**

   .. attribute:: DOWNLOAD_BATCH_START

      Batch download for a folder started.

   .. attribute:: DOWNLOAD_FILE_START

      Individual file download started.

   .. attribute:: DOWNLOAD_FILE_PROGRESS

      File download progress update.

   .. attribute:: DOWNLOAD_FILE_COMPLETE

      File download completed successfully.

   .. attribute:: DOWNLOAD_FILE_ERROR

      File download failed.

   .. attribute:: DOWNLOAD_BATCH_COMPLETE

      Batch download completed.

SyncProgressInfo
~~~~~~~~~~~~~~~~

.. class:: SyncProgressInfo

   Progress information object passed to callbacks.

   .. attribute:: event

      Event type (SyncProgressEvent enum value).

   .. attribute:: file_path

      File path (for file-specific events).

   .. attribute:: directory

      Directory path (for batch events).

   .. attribute:: current_file_bytes

      Bytes transferred for current file.

   .. attribute:: current_file_total

      Total bytes for current file.

   .. attribute:: folder_bytes_uploaded

      Bytes uploaded in current folder.

   .. attribute:: folder_bytes_downloaded

      Bytes downloaded in current folder.

   .. attribute:: folder_bytes_total

      Total bytes for current folder.

   .. attribute:: folder_files_uploaded

      Files uploaded in current folder.

   .. attribute:: folder_files_downloaded

      Files downloaded in current folder.

   .. attribute:: total_bytes_uploaded

      Total bytes uploaded across all operations.

   .. attribute:: total_bytes_downloaded

      Total bytes downloaded across all operations.

   .. attribute:: total_files_uploaded

      Total files uploaded across all operations.

   .. attribute:: total_files_downloaded

      Total files downloaded across all operations.

   .. attribute:: error_message

      Error message (for error events).

   .. attribute:: stats

      Sync statistics (for sync_complete event).

Configuration
-------------

SyncConfig
~~~~~~~~~~

.. class:: SyncConfig

   Configuration for sync operations.

   .. attribute:: chunk_size

      Chunk size for uploads in bytes (default: 5MB).

   .. attribute:: multipart_threshold

      File size threshold for multipart uploads in bytes (default: 50MB).

   .. attribute:: max_retries

      Maximum number of retries for failed operations (default: 3).

   .. attribute:: retry_delay

      Delay between retries in seconds (default: 1.0).

.. function:: load_sync_pairs_from_json(file_path: Path) -> list[SyncPair]

   Load sync pairs from a JSON configuration file.

   :param Path file_path: Path to JSON config file
   :returns: List of configured sync pairs
   :rtype: list[SyncPair]
   :raises SyncConfigError: If config file is invalid

   Example JSON format::

      {
        "pairs": [
          {
            "source_root": "/home/user/documents",
            "destination_root": "/backup/documents",
            "mode": "twoWay"
          }
        ]
      }

Constants
---------

.. data:: DEFAULT_CHUNK_SIZE

   Default chunk size for uploads (5MB).

.. data:: DEFAULT_MULTIPART_THRESHOLD

   Default file size threshold for multipart uploads (50MB).

.. data:: DEFAULT_MAX_RETRIES

   Default maximum number of retries (3).

.. data:: DEFAULT_RETRY_DELAY

   Default delay between retries in seconds (1.0).

.. data:: DEFAULT_TRANSFERS_LIMIT

   Default maximum concurrent transfers (5).

.. data:: DEFAULT_OPERATIONS_LIMIT

   Default maximum concurrent operations (10).

.. data:: DEFAULT_BATCH_SIZE

   Default batch size for operations (100).

.. data:: DEFAULT_IGNORE_FILE_NAME

   Default ignore file name (".syncignore").

.. data:: DEFAULT_STATE_DIR_NAME

   Default state directory name (".sync_state").

.. function:: format_size(bytes: int) -> str

   Format byte size in human-readable form.

   :param int bytes: Size in bytes
   :returns: Formatted size string (e.g., "1.5 MB")
   :rtype: str

   Example::

      >>> format_size(1536)
      "1.5 KB"
      >>> format_size(5242880)
      "5.0 MB"

Exceptions
----------

.. exception:: SyncConfigError

   Raised when sync configuration is invalid.

.. exception:: SyncOperationError

   Raised when a sync operation fails.

.. exception:: StorageError

   Raised when a storage operation fails.

Protocols
---------

See :doc:`protocols` for detailed protocol documentation.

* ``StorageClientProtocol`` - Interface for storage backends
* ``FileEntryProtocol`` - Interface for file/folder metadata
* ``FileEntriesManagerProtocol`` - Interface for managing file collections
* ``OutputHandlerProtocol`` - Interface for output handling
* ``SpinnerFactoryProtocol`` - Interface for progress spinners
* ``ProgressBarFactoryProtocol`` - Interface for progress bars

Next Steps
----------

* :doc:`examples` - See complete usage examples
* :doc:`protocols` - Learn about implementing storage backends
* :doc:`concepts` - Understand core concepts
