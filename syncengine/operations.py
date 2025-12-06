"""Sync operations wrapper for unified upload/download interface."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_LOCAL_TRASH_DIR_NAME,
    DEFAULT_MULTIPART_THRESHOLD,
)
from .protocols import StorageClientProtocol
from .scanner import DestinationFile, SourceFile


def get_local_trash_path(
    sync_root: Path,
    trash_dir_name: str = DEFAULT_LOCAL_TRASH_DIR_NAME,
) -> Path:
    """Get the path to the local trash directory.

    Args:
        sync_root: Root directory of the sync operation
        trash_dir_name: Name of the trash directory

    Returns:
        Path to the local trash directory
    """
    return sync_root / trash_dir_name


def move_to_local_trash(
    file_path: Path,
    sync_root: Path,
    trash_dir_name: str = DEFAULT_LOCAL_TRASH_DIR_NAME,
) -> Path:
    """Move a file to the local trash directory.

    The file will be moved to the trash directory at the sync root,
    preserving its relative path structure. A timestamp is added to
    avoid name collisions when the same file is deleted multiple times.

    Args:
        file_path: Path to the file to move to trash
        sync_root: Root directory of the sync operation
        trash_dir_name: Name of the trash directory

    Returns:
        Path where the file was moved to

    Raises:
        FileNotFoundError: If the file does not exist
        OSError: If the file cannot be moved
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get the trash directory
    trash_dir = get_local_trash_path(sync_root, trash_dir_name)

    # Get the relative path from sync root
    try:
        relative_path = file_path.relative_to(sync_root)
    except ValueError:
        # File is not under sync_root, use just the filename
        relative_path = Path(file_path.name)

    # Create a timestamped trash path to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trash_path = trash_dir / f"{timestamp}" / relative_path

    # Ensure parent directory exists
    trash_path.parent.mkdir(parents=True, exist_ok=True)

    # Move the file
    shutil.move(str(file_path), str(trash_path))

    return trash_path


def rename_local_file(
    old_path: Path,
    new_path: Path,
) -> Path:
    """Rename/move a local file.

    Creates parent directories as needed and handles the rename atomically
    where possible.

    Args:
        old_path: Current path of the file
        new_path: New path for the file

    Returns:
        The new path

    Raises:
        FileNotFoundError: If the source file does not exist
        FileExistsError: If the target path already exists
        OSError: If the rename fails
    """
    if not old_path.exists():
        raise FileNotFoundError(f"Source file not found: {old_path}")

    if new_path.exists():
        raise FileExistsError(f"Target path already exists: {new_path}")

    # Ensure parent directory exists
    new_path.parent.mkdir(parents=True, exist_ok=True)

    # Rename the file
    old_path.rename(new_path)

    return new_path


class SyncOperations:
    """Unified operations for upload/download with common interface.

    This class provides a consistent API for sync operations that works
    with any cloud client implementing the StorageClientProtocol.
    """

    def __init__(
        self,
        client: StorageClientProtocol,
        local_trash_dir_name: str = DEFAULT_LOCAL_TRASH_DIR_NAME,
    ):
        """Initialize sync operations.

        Args:
            client: Cloud API client implementing StorageClientProtocol
            local_trash_dir_name: Name of the local trash directory
        """
        self.client = client
        self.local_trash_dir_name = local_trash_dir_name

    def upload_file(
        self,
        source_file: SourceFile,
        remote_path: str,
        storage_id: int = 0,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        multipart_threshold: int = DEFAULT_MULTIPART_THRESHOLD,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Any:
        """Upload a source file to destination storage.

        Args:
            source_file: Source file to upload
            remote_path: Remote path (relative path for the file)
            storage_id: Storage/workspace ID
            chunk_size: Chunk size for multipart uploads
            multipart_threshold: Threshold for using multipart upload
            progress_callback: Optional progress callback
                function(bytes_uploaded, total_bytes)

        Returns:
            Upload response from API
        """
        return self.client.upload_file(
            file_path=source_file.path,
            relative_path=remote_path,
            storage_id=storage_id,
            chunk_size=chunk_size,
            use_multipart_threshold=multipart_threshold,
            progress_callback=progress_callback,
        )

    def download_file(
        self,
        destination_file: DestinationFile,
        local_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Download a destination file to local storage.

        Args:
            destination_file: Destination file to download
            local_path: Local path where file should be saved
            progress_callback: Optional progress callback
                function(bytes_downloaded, total_bytes)

        Returns:
            Path where file was saved
        """
        # Ensure parent directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        return self.client.download_file(
            hash_value=destination_file.hash,
            output_path=local_path,
            progress_callback=progress_callback,
        )

    def delete_remote(
        self,
        destination_file: DestinationFile,
        permanent: bool = False,
    ) -> Any:
        """Delete a destination file.

        Args:
            destination_file: Destination file to delete
            permanent: If True, delete permanently; if False, move to trash

        Returns:
            Delete response from API
        """
        return self.client.delete_file_entries(
            entry_ids=[destination_file.id],
            delete_forever=permanent,
        )

    def delete_local(
        self,
        source_file: SourceFile,
        use_trash: bool = True,
        sync_root: Optional[Path] = None,
    ) -> None:
        """Delete a source file.

        When use_trash is True and sync_root is provided, the file is moved to
        the local trash directory at the sync root. This allows easy
        recovery of accidentally deleted files while keeping them out of sync.

        Args:
            source_file: Source file to delete
            use_trash: If True, move to local trash directory;
                if False, delete permanently
            sync_root: Root directory of the sync operation (required for trash)
        """
        if use_trash and sync_root is not None:
            # Move to local trash directory
            move_to_local_trash(source_file.path, sync_root, self.local_trash_dir_name)
            return

        # Permanent delete
        source_file.path.unlink()

    def rename_local(
        self,
        source_file: SourceFile,
        new_relative_path: str,
        sync_root: Path,
    ) -> Path:
        """Rename/move a source file.

        This is used when a destination rename is detected and needs to be
        propagated to the source filesystem.

        Args:
            source_file: Source file to rename
            new_relative_path: New relative path for the file
            sync_root: Root directory of the sync operation

        Returns:
            The new absolute path of the file

        Raises:
            FileNotFoundError: If the source file does not exist
            FileExistsError: If the target path already exists
            OSError: If the rename fails
        """
        # Convert forward slashes to OS-native path separators
        new_path = sync_root / Path(new_relative_path)
        return rename_local_file(source_file.path, new_path)

    def rename_remote(
        self,
        destination_file: DestinationFile,
        new_name: str,
        new_parent_id: Optional[int] = None,
    ) -> Any:
        """Rename/move a destination file.

        This is used when a source rename is detected and needs to be
        propagated to the destination storage.

        For simple renames (same folder, different name), uses update_file_entry.
        For moves (different folder), uses move_file_entries followed by rename.

        Args:
            destination_file: Destination file to rename
            new_name: New name for the file (just the filename, not full path)
            new_parent_id: New parent folder ID (for moves), or None to keep same parent

        Returns:
            Response from API
        """
        # If moving to a different folder, do the move first
        if new_parent_id is not None:
            self.client.move_file_entries(
                entry_ids=[destination_file.id],
                destination_id=new_parent_id,
            )

        # Rename the file
        return self.client.update_file_entry(
            entry_id=destination_file.id,
            name=new_name,
        )
