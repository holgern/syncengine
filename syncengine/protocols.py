"""Protocol definitions for storage-agnostic sync operations.

This module defines the protocols (interfaces) that storage service implementations
must adhere to in order to work with the syncengine library.

The protocols use Python's typing.Protocol for structural subtyping, meaning
any class that implements the required methods will be compatible without
needing to explicitly inherit from these protocols.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class FileEntryProtocol(Protocol):
    """Protocol for destination file entries from any storage service.

    This defines the minimum attributes required for a file entry
    to be used with syncengine.

    Attributes:
        id: Unique identifier for the file entry (persists across renames)
        type: Entry type - "file" or "folder"
        file_size: Size in bytes (0 for folders)
        hash: Content hash (e.g., MD5) for integrity verification
        name: File or folder name
        updated_at: ISO timestamp of last modification (optional)
    """

    @property
    def id(self) -> int:
        """Unique identifier for the file entry."""
        ...

    @property
    def type(self) -> str:
        """Entry type: 'file' or 'folder'."""
        ...

    @property
    def file_size(self) -> int:
        """File size in bytes."""
        ...

    @property
    def hash(self) -> str:
        """Content hash (e.g., MD5)."""
        ...

    @property
    def name(self) -> str:
        """File or folder name."""
        ...

    @property
    def updated_at(self) -> Optional[str]:
        """ISO timestamp of last modification."""
        ...


@runtime_checkable
class StorageClientProtocol(Protocol):
    """Protocol for storage service API clients.

    Any storage client that implements these methods can be used
    with syncengine for file synchronization.
    """

    def upload_file(
        self,
        file_path: Path,
        relative_path: str,
        storage_id: int = 0,
        chunk_size: int = ...,
        use_multipart_threshold: int = ...,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Any:
        """Upload a source file to destination storage.

        Args:
            file_path: Source path to the file to upload
            relative_path: Relative path in destination storage
                (determines folder structure)
            storage_id: Storage/workspace identifier (0 for default/personal)
            chunk_size: Chunk size for multipart uploads (bytes)
            use_multipart_threshold: File size threshold for multipart upload
            progress_callback: Callback for upload progress (bytes_uploaded,
            total_bytes)

        Returns:
            Upload result (implementation-specific)
        """
        ...

    def download_file(
        self,
        hash_value: str,
        output_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Download a file from destination storage.

        Args:
            hash_value: Content hash of the file to download
            output_path: Source path where file should be saved
            progress_callback: Callback for download progress (bytes_downloaded, total)

        Returns:
            Path where file was saved
        """
        ...

    def delete_file_entries(
        self,
        entry_ids: list[int],
        delete_forever: bool = False,
    ) -> Any:
        """Delete file entries from destination storage.

        Args:
            entry_ids: List of entry IDs to delete
            delete_forever: If True, permanently delete; if False, move to trash

        Returns:
            Delete result (implementation-specific)
        """
        ...

    def create_folder(
        self,
        name: str,
        parent_id: Optional[int] = None,
        storage_id: int = 0,
    ) -> dict[str, Any]:
        """Create a folder in destination storage.

        Args:
            name: Folder name (can include path separators for nested folders)
            parent_id: Parent folder ID (None for root)
            storage_id: Storage/workspace identifier (0 for default/personal)

        Returns:
            Dictionary with at least 'status' and 'id' keys
        """
        ...

    def resolve_path_to_id(
        self,
        path: str,
        storage_id: int = 0,
    ) -> Optional[int]:
        """Resolve a path to its folder ID.

        Args:
            path: Path to resolve (e.g., "Documents/Projects")
            storage_id: Storage/workspace identifier

        Returns:
            Folder ID if found, None otherwise
        """
        ...

    def move_file_entries(
        self,
        entry_ids: list[int],
        destination_id: int,
    ) -> Any:
        """Move file entries to a different folder.

        Args:
            entry_ids: List of entry IDs to move
            destination_id: Destination folder ID

        Returns:
            Move result (implementation-specific)
        """
        ...

    def update_file_entry(
        self,
        entry_id: int,
        name: str,
    ) -> Any:
        """Update a file entry (rename).

        Args:
            entry_id: ID of entry to update
            name: New name for the entry

        Returns:
            Update result (implementation-specific)
        """
        ...


@runtime_checkable
class FileEntriesManagerProtocol(Protocol):
    """Protocol for managing file entries in destination storage.

    This provides higher-level operations for working with storage,
    including recursive listing and folder management.
    """

    def find_folder_by_name(
        self, name: str, parent_id: int = 0
    ) -> Optional[FileEntryProtocol]:
        """Find a folder by name within a parent folder.

        Args:
            name: Folder name to find
            parent_id: Parent folder ID (0 for root)

        Returns:
            FileEntry if found, None otherwise
        """
        ...

    def get_all_recursive(
        self,
        folder_id: Optional[int],
        path_prefix: str,
    ) -> list[tuple[FileEntryProtocol, str]]:
        """Get all entries recursively under a folder.

        Args:
            folder_id: Folder ID to start from (None/0 for root)
            path_prefix: Prefix to add to relative paths

        Returns:
            List of (entry, relative_path) tuples
        """
        ...

    def iter_all_recursive(
        self,
        folder_id: Optional[int],
        path_prefix: str,
        batch_size: int,
    ) -> Iterator[list[tuple[FileEntryProtocol, str]]]:
        """Iterate over entries recursively in batches.

        Args:
            folder_id: Folder ID to start from (None/0 for root)
            path_prefix: Prefix to add to relative paths
            batch_size: Number of entries per batch

        Yields:
            Batches of (entry, relative_path) tuples
        """
        ...


@runtime_checkable
class OutputHandlerProtocol(Protocol):
    """Protocol for output/logging handlers.

    This abstracts the output mechanism so syncengine can work with
    different UI frameworks (CLI, GUI, headless).

    Attributes:
        quiet: If True, suppress non-essential output
    """

    @property
    def quiet(self) -> bool:
        """Whether to suppress non-essential output."""
        ...

    def info(self, message: str) -> None:
        """Display an informational message."""
        ...

    def success(self, message: str) -> None:
        """Display a success message."""
        ...

    def error(self, message: str) -> None:
        """Display an error message."""
        ...

    def warning(self, message: str) -> None:
        """Display a warning message."""
        ...

    def print(self, message: str) -> None:
        """Print a raw message without formatting."""
        ...


class SpinnerContextProtocol(Protocol):
    """Protocol for spinner context managers returned by SpinnerFactory."""

    def update(self, description: str) -> None:
        """Update the spinner description.

        Args:
            description: New description text
        """
        ...

    def __enter__(self) -> "SpinnerContextProtocol":
        """Enter context manager."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        ...


class SpinnerFactoryProtocol(Protocol):
    """Protocol for creating spinner/progress indicators.

    This allows injecting different UI frameworks for progress display.
    Implementations can use Rich, tqdm, or any other progress library.
    """

    @contextmanager
    def create_spinner(
        self,
        description: str,
        transient: bool = True,
    ) -> Iterator[SpinnerContextProtocol]:
        """Create a spinner context manager.

        Args:
            description: Initial description for the spinner
            transient: If True, remove spinner after completion

        Yields:
            SpinnerContext that can be updated

        Examples:
            >>> with factory.create_spinner("Loading...") as spinner:
            ...     # Do work
            ...     spinner.update("Still loading...")
        """
        ...


class DefaultOutputHandler:
    """Default output handler that prints to stdout.

    This is a minimal implementation for when no custom output handler
    is provided.
    """

    def __init__(self, quiet: bool = False) -> None:
        """Initialize default output handler.

        Args:
            quiet: If True, suppress non-essential output
        """
        self._quiet = quiet

    @property
    def quiet(self) -> bool:
        """Whether to suppress non-essential output."""
        return self._quiet

    def info(self, message: str) -> None:
        """Display an informational message."""
        if not self._quiet:
            print(f"[INFO] {message}")

    def success(self, message: str) -> None:
        """Display a success message."""
        if not self._quiet:
            print(f"[OK] {message}")

    def error(self, message: str) -> None:
        """Display an error message."""
        print(f"[ERROR] {message}")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        print(f"[WARN] {message}")

    def print(self, message: str) -> None:
        """Print a raw message without formatting."""
        print(message)


class NullSpinnerContext:
    """Null spinner context that does nothing (for headless operation)."""

    def update(self, description: str) -> None:
        """Update description (no-op)."""
        pass

    def __enter__(self) -> "NullSpinnerContext":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        pass


class NullSpinnerFactory:
    """Null spinner factory that creates no-op spinners.

    Use this for headless operation or testing.
    """

    @contextmanager
    def create_spinner(
        self,
        description: str,
        transient: bool = True,
    ) -> Iterator[NullSpinnerContext]:
        """Create a null spinner that does nothing.

        Args:
            description: Initial description (ignored)
            transient: Whether spinner is transient (ignored)

        Yields:
            NullSpinnerContext
        """
        yield NullSpinnerContext()


class ProgressBarTaskProtocol(Protocol):
    """Protocol for a progress bar task that can be updated."""

    @property
    def task_id(self) -> Any:
        """Get the task identifier."""
        ...

    def update(self, advance: int = 0, description: Optional[str] = None) -> None:
        """Update the progress bar.

        Args:
            advance: Number of steps to advance
            description: Optional new description
        """
        ...


class ProgressBarContextProtocol(Protocol):
    """Protocol for progress bar context managers."""

    def add_task(self, description: str, total: Optional[int] = None) -> Any:
        """Add a new task to the progress bar.

        Args:
            description: Task description
            total: Total number of steps (None for indeterminate)

        Returns:
            Task identifier
        """
        ...

    def update(
        self, task_id: Any, advance: int = 0, description: Optional[str] = None
    ) -> None:
        """Update a task's progress.

        Args:
            task_id: Task identifier from add_task
            advance: Number of steps to advance
            description: Optional new description
        """
        ...

    def __enter__(self) -> "ProgressBarContextProtocol":
        """Enter context manager."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        ...


class ProgressBarFactoryProtocol(Protocol):
    """Protocol for creating progress bars.

    This allows injecting different UI frameworks for progress display.
    """

    @contextmanager
    def create_progress_bar(self) -> Iterator[ProgressBarContextProtocol]:
        """Create a progress bar context manager.

        Yields:
            ProgressBarContext that can have tasks added and updated

        Examples:
            >>> with factory.create_progress_bar() as progress:
            ...     task = progress.add_task("Processing...", total=100)
            ...     for i in range(100):
            ...         # Do work
            ...         progress.update(task, advance=1)
        """
        ...


class NullProgressBarContext:
    """Null progress bar context that does nothing (for headless operation)."""

    def add_task(self, description: str, total: Optional[int] = None) -> int:
        """Add a task (returns dummy task id)."""
        return 0

    def update(
        self, task_id: Any, advance: int = 0, description: Optional[str] = None
    ) -> None:
        """Update progress (no-op)."""
        pass

    def __enter__(self) -> "NullProgressBarContext":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        pass


class NullProgressBarFactory:
    """Null progress bar factory that creates no-op progress bars.

    Use this for headless operation or testing.
    """

    @contextmanager
    def create_progress_bar(self) -> Iterator[NullProgressBarContext]:
        """Create a null progress bar that does nothing.

        Yields:
            NullProgressBarContext
        """
        yield NullProgressBarContext()
