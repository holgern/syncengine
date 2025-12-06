"""Syncengine - Cloud-agnostic file synchronization library.

This library provides a flexible sync engine that can work with any cloud
storage provider. It supports bidirectional sync, rename detection, and
gitignore-style pattern matching.

Example usage:
    >>> from syncengine import SyncPair, SyncMode, DirectoryScanner
    >>> pair = SyncPair(
    ...     local=Path("/home/user/docs"),
    ...     remote="/Documents",
    ...     sync_mode=SyncMode.TWO_WAY
    ... )
    >>> scanner = DirectoryScanner()
    >>> files = scanner.scan_local(pair.local)
"""

from .comparator import FileComparator, SyncAction, SyncDecision
from .concurrency import ConcurrencyLimits, SyncPauseController, Semaphore
from .config import SyncConfigError, load_sync_pairs_from_json
from .constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_IGNORE_FILE_NAME,
    DEFAULT_LOCAL_TRASH_DIR_NAME,
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
from .modes import SyncMode
from .operations import SyncOperations
from .pair import SyncPair
from .progress import (
    SyncProgressEvent,
    SyncProgressInfo,
    SyncProgressTracker,
)
from .protocols import (
    CloudClientProtocol,
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
from .scanner import DirectoryScanner, LocalFile, RemoteFile
from .state import (
    LocalItemState,
    LocalTree,
    RemoteItemState,
    RemoteTree,
    SyncState,
    SyncStateManager,
    build_local_tree_from_files,
    build_remote_tree_from_files,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Engine
    "SyncEngine",
    # Modes
    "SyncMode",
    # Pair
    "SyncPair",
    # Scanner
    "DirectoryScanner",
    "LocalFile",
    "RemoteFile",
    # Comparator
    "FileComparator",
    "SyncAction",
    "SyncDecision",
    # Operations
    "SyncOperations",
    # State
    "SyncState",
    "SyncStateManager",
    "LocalTree",
    "RemoteTree",
    "LocalItemState",
    "RemoteItemState",
    "build_local_tree_from_files",
    "build_remote_tree_from_files",
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
    "DEFAULT_STATE_DIR_NAME",
    "format_size",
    # Protocols
    "FileEntryProtocol",
    "CloudClientProtocol",
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
