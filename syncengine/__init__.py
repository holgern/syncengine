"""Syncengine - Storage-agnostic file synchronization library.

This library provides a flexible sync engine that can work with any storage
provider. It supports bidirectional sync, rename detection, and
gitignore-style pattern matching.

Example usage:
    >>> from syncengine import SyncPair, SyncMode, DirectoryScanner
    >>> pair = SyncPair(
    ...     source=Path("/home/user/docs"),
    ...     destination="/Documents",
    ...     sync_mode=SyncMode.TWO_WAY
    ... )
    >>> scanner = DirectoryScanner()
    >>> files = scanner.scan_source(pair.source)
"""

from .comparator import FileComparator, SyncAction, SyncDecision
from .concurrency import ConcurrencyLimits, SyncPauseController, Semaphore
from .config import SyncConfigError, load_sync_pairs_from_json
from .constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_IGNORE_FILE_NAME,
    DEFAULT_LOCAL_TRASH_DIR_NAME,
    DEFAULT_SOURCE_TRASH_DIR_NAME,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MULTIPART_THRESHOLD,
    DEFAULT_OPERATIONS_LIMIT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_STATE_DIR_NAME,
    DEFAULT_TRANSFERS_LIMIT,
    FUTURE_RESULT_TIMEOUT,
    format_size,
)
from .engine import SyncEngine
from .ignore import IgnoreFileManager, IgnoreRule, load_ignore_file
from .models import FileEntry, SyncConfig
from .modes import SyncMode, InitialSyncPreference
from .operations import SyncOperations
from .pair import SyncPair
from .progress import (
    SyncProgressEvent,
    SyncProgressInfo,
    SyncProgressTracker,
)
from .protocols import (
    StorageClientProtocol,
    DefaultOutputHandler,
    FileEntriesManagerProtocol,
    FileEntryProtocol,
    NullProgressBarContext,
    NullProgressBarFactory,
    NullSpinnerContext,
    NullSpinnerFactory,
    OutputHandlerProtocol,
    ProgressBarContextProtocol,
    ProgressBarFactoryProtocol,
    ProgressBarTaskProtocol,
    SpinnerContextProtocol,
    SpinnerFactoryProtocol,
)
from .scanner import DirectoryScanner, SourceFile, DestinationFile
from .state import (
    SourceItemState,
    SourceTree,
    DestinationItemState,
    DestinationTree,
    SyncState,
    SyncStateManager,
    build_source_tree_from_files,
    build_destination_tree_from_files,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Engine
    "SyncEngine",
    # Modes
    "SyncMode",
    "InitialSyncPreference",
    # Pair
    "SyncPair",
    # Scanner
    "DirectoryScanner",
    "SourceFile",
    "DestinationFile",
    # Comparator
    "FileComparator",
    "SyncAction",
    "SyncDecision",
    # Operations
    "SyncOperations",
    # State
    "SyncState",
    "SyncStateManager",
    "SourceTree",
    "DestinationTree",
    "SourceItemState",
    "DestinationItemState",
    "build_source_tree_from_files",
    "build_destination_tree_from_files",
    # Ignore
    "IgnoreFileManager",
    "IgnoreRule",
    "load_ignore_file",
    # Config
    "SyncConfigError",
    "load_sync_pairs_from_json",
    # Models
    "FileEntry",
    "SyncConfig",
    # Constants
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_MULTIPART_THRESHOLD",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "FUTURE_RESULT_TIMEOUT",
    "DEFAULT_TRANSFERS_LIMIT",
    "DEFAULT_OPERATIONS_LIMIT",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_IGNORE_FILE_NAME",
    "DEFAULT_LOCAL_TRASH_DIR_NAME",
    "DEFAULT_SOURCE_TRASH_DIR_NAME",
    "DEFAULT_STATE_DIR_NAME",
    "format_size",
    # Protocols
    "FileEntryProtocol",
    "StorageClientProtocol",
    "FileEntriesManagerProtocol",
    "OutputHandlerProtocol",
    "SpinnerContextProtocol",
    "SpinnerFactoryProtocol",
    "ProgressBarContextProtocol",
    "ProgressBarFactoryProtocol",
    "ProgressBarTaskProtocol",
    "DefaultOutputHandler",
    "NullSpinnerContext",
    "NullSpinnerFactory",
    "NullProgressBarContext",
    "NullProgressBarFactory",
    # Concurrency
    "Semaphore",
    "SyncPauseController",
    "ConcurrencyLimits",
    # Progress
    "SyncProgressEvent",
    "SyncProgressInfo",
    "SyncProgressTracker",
]
